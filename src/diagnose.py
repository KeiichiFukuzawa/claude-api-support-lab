"""Send one small Messages API request and explain what happened.

Usage examples:
    python -m src.diagnose                         # one small valid request
    python -m src.diagnose --scenario bad-model    # reproduce a 404 on purpose
    python -m src.diagnose --model claude-haiku-5-5 --max-tokens 16

What it does:
- Sends exactly one request. Automatic retries are OFF (max_retries=0),
  so you see the first response and no extra requests are sent.
- Prints the HTTP status, error type, message, request ID, and advice.
- Writes one JSON line per run to logs/diagnose-YYYY-MM-DD.jsonl.
- Never writes the API key or the prompt text.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

from src.error_catalog import CATALOG, ErrorInfo, classify
from src.redact import describe_prompt, redact_obj

DEFAULT_MODEL = "claude-haiku-5-5"  # smallest current model (docs/sources.md)
DEFAULT_MAX_TOKENS = 16
DEFAULT_PROMPT = "Reply with the word OK."
DEFAULT_LOG_DIR = "logs"

# Values used by the safe "reproduce on purpose" scenarios.
FAKE_API_KEY = "invalid-key-for-diagnose-test"  # not a real key, not even the real format
MISSING_MODEL = "claude-model-that-does-not-exist"

SCENARIOS = {
    "normal": "Send one small valid request.",
    "bad-key": "Use a fake API key. Expected result: 401.",
    "bad-model": "Use a model name that does not exist. Expected result: 404.",
    "bad-param": "Send max_tokens = -1. Expected result: 400.",
}

# We keep only headers that help debugging. We do not keep account IDs
# (anthropic-organization-id, anthropic-workspace-id), because logs may be shared.
RECORDED_HEADERS = ("request-id", "retry-after", "x-should-retry", "cf-ray")
RECORDED_HEADER_PREFIXES = ("anthropic-ratelimit-", "anthropic-priority-", "anthropic-fast-")

EXIT_OK = 0
EXIT_API_ERROR = 1
EXIT_CONFIG_ERROR = 2


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def pick_headers(headers: Any) -> dict[str, str]:
    """Keep only the useful response headers."""
    picked: dict[str, str] = {}
    for name, value in headers.items():
        lower = name.lower()
        if lower in RECORDED_HEADERS or lower.startswith(RECORDED_HEADER_PREFIXES):
            picked[lower] = value
    return dict(sorted(picked.items()))


def build_request(scenario: str, model: str, max_tokens: int, prompt: str) -> dict[str, Any]:
    """Build the request parameters for one scenario."""
    if scenario == "bad-model":
        model = MISSING_MODEL
    if scenario == "bad-param":
        max_tokens = -1
    return {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }


def make_client(api_key: str, http_client: Any = None) -> anthropic.Anthropic:
    """Create a client with retries off, so one run sends one request."""
    return anthropic.Anthropic(
        api_key=api_key,
        max_retries=0,
        timeout=60.0,
        http_client=http_client,
    )


def request_summary(params: dict[str, Any], prompt: str) -> dict[str, Any]:
    """Describe the request without the prompt text."""
    return {
        "endpoint": "POST /v1/messages",
        "model": params["model"],
        "max_tokens": params["max_tokens"],
        "message_count": len(params["messages"]),
        **describe_prompt(prompt),
    }


def run_diagnosis(
    client: anthropic.Anthropic,
    params: dict[str, Any],
    *,
    scenario: str,
    prompt: str,
) -> dict[str, Any]:
    """Send the request once and return a log record (not yet redacted)."""
    started = utc_now()
    t0 = time.monotonic()
    record: dict[str, Any] = {
        "log_id": uuid.uuid4().hex[:12],
        "timestamp": started.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "tool": "diagnose",
        "scenario": scenario,
        "sdk": f"anthropic-python {anthropic.__version__}",
        "python": sys.version.split()[0],
        "max_retries": 0,
        "request": request_summary(params, prompt),
    }

    try:
        raw = client.messages.with_raw_response.create(**params)
    except anthropic.APITimeoutError as exc:
        record.update(_transport_failure("timeout", exc))
    except anthropic.APIConnectionError as exc:
        record.update(_transport_failure("connection", exc))
    except anthropic.APIStatusError as exc:
        record.update(_status_failure(exc))
    else:
        message = raw.parse()
        record.update(
            {
                "outcome": "success",
                "http_status": raw.status_code,
                "request_id": raw.headers.get("request-id") or message._request_id,
                "headers": pick_headers(raw.headers),
                "response": {
                    "model": message.model,
                    "stop_reason": message.stop_reason,
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                },
            }
        )

    record["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
    return record


def _transport_failure(kind: str, exc: Exception) -> dict[str, Any]:
    info = classify(None, transport_error=kind)
    text = f"{type(exc).__name__}: {exc}"
    if exc.__cause__ is not None:
        # The underlying network error is often the most useful part.
        text += f" Cause: {type(exc.__cause__).__name__}: {exc.__cause__}"
    return {
        "outcome": "error",
        "http_status": None,
        "error_type": None,
        "error_message": text,
        "request_id": None,
        "headers": {},
        "classification": {"key": info.key, "title": info.title, "retryable": info.retryable},
    }


def _status_failure(exc: anthropic.APIStatusError) -> dict[str, Any]:
    body = exc.body if isinstance(exc.body, dict) else None
    error = body.get("error") if body and isinstance(body.get("error"), dict) else {}
    details = error.get("details") if isinstance(error.get("details"), dict) else {}

    if body is not None:
        message = error.get("message")
        body_format = "json"
    else:
        # Some errors (for example 413 from Cloudflare) may not be JSON.
        message = str(exc.body)[:300] if exc.body else None
        body_format = "non-json"

    error_code = details.get("error_code")
    info = classify(exc.status_code, message=message, error_code=error_code)
    return {
        "outcome": "error",
        "http_status": exc.status_code,
        "error_type": exc.type or error.get("type"),
        "error_message": message,
        "error_code": error_code,
        "body_format": body_format,
        "request_id": exc.request_id or (body or {}).get("request_id"),
        "body_request_id": (body or {}).get("request_id"),
        "headers": pick_headers(exc.response.headers),
        "classification": {"key": info.key, "title": info.title, "retryable": info.retryable},
    }


def rate_limit_notes(record: dict[str, Any]) -> list[str]:
    """Explain the 429-related headers in plain words."""
    headers = record.get("headers", {})
    notes: list[str] = []
    retry_after = headers.get("retry-after")
    if retry_after is not None:
        notes.append(f"retry-after: {retry_after} -> wait {retry_after} seconds before you retry.")
    else:
        notes.append("retry-after: (not present)")
        if record.get("error_code") == "enforced_spend_limit_reached":
            notes.append(
                "No retry-after and error_code = enforced_spend_limit_reached: "
                "this is the monthly spend cap. Retrying will not help."
            )
        else:
            notes.append("Without retry-after, use exponential backoff and check the Limits page.")

    ratelimit = {k: v for k, v in headers.items() if k.startswith("anthropic-ratelimit-")}
    if not ratelimit:
        notes.append("anthropic-ratelimit-* headers: (not present)")
    for name, value in ratelimit.items():
        mark = "   <- at zero" if name.endswith("-remaining") and value.strip() == "0" else ""
        notes.append(f"{name}: {value}{mark}")
    return notes


def format_report(record: dict[str, Any], info: ErrorInfo | None) -> str:
    """Make the text that we print on the screen."""
    req = record["request"]
    lines = [
        "=" * 60,
        f"Scenario    : {record['scenario']}",
        f"Request     : {req['endpoint']} model={req['model']} max_tokens={req['max_tokens']} "
        f"prompt_chars={req['prompt_chars']}",
        f"Time (UTC)  : {record['timestamp']}",
    ]

    if record["outcome"] == "success":
        resp = record["response"]
        lines += [
            "Result      : SUCCESS",
            f"HTTP status : {record['http_status']}",
            f"Request ID  : {record['request_id']}",
            f"Model       : {resp['model']}",
            f"Stop reason : {resp['stop_reason']}",
            f"Tokens      : input={resp['input_tokens']} output={resp['output_tokens']}",
            "=" * 60,
        ]
        return "\n".join(lines)

    status = record["http_status"]
    lines += [
        "Result      : ERROR",
        f"HTTP status : {status if status is not None else '(no response)'}"
        + (f" ({record['error_type']})" if record.get("error_type") else ""),
        f"Request ID  : {record.get('request_id') or '(none)'}",
        f"Message     : {record.get('error_message') or '(none)'}",
    ]
    if record.get("error_code"):
        lines.append(f"Error code  : {record['error_code']}")
    if info is not None:
        lines += [
            f"Category    : {info.title}",
            f"Retry?      : {info.retryable}",
            "",
            "Likely causes:",
            *[f"  - {c}" for c in info.likely_causes],
            "",
            "Next checks:",
            *[f"  {i}. {c}" for i, c in enumerate(info.next_checks, 1)],
        ]
    if status == 429:
        lines += ["", "Rate limit headers:", *[f"  {n}" for n in rate_limit_notes(record)]]
    lines.append("=" * 60)
    return "\n".join(lines)


def write_log(record: dict[str, Any], log_dir: str | Path) -> Path:
    """Append one JSON line. The record must already be redacted."""
    path = Path(log_dir)
    path.mkdir(parents=True, exist_ok=True)
    day = record["timestamp"][:10]
    log_file = path / f"diagnose-{day}.jsonl"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return log_file


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.diagnose",
        description="Send one small Claude API request and explain the result.",
    )
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default="normal",
        help="normal = valid request; bad-key = 401; bad-model = 404; bad-param = 400.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model ID (default: {DEFAULT_MODEL}).")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="Default: 16.")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt text. It is never logged.")
    parser.add_argument("--log-dir", default=DEFAULT_LOG_DIR, help="Default: logs")
    parser.add_argument("--no-log", action="store_true", help="Do not write a log line.")
    parser.add_argument("--json", action="store_true", help="Print the log record as JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, http_client: Any = None) -> int:
    args = parse_args(argv)

    if args.scenario == "bad-key":
        api_key = FAKE_API_KEY
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            print(
                "ANTHROPIC_API_KEY is not set.\n"
                "Set it in your shell (export ANTHROPIC_API_KEY=...) or in a .env file.\n"
                "No request was sent.",
                file=sys.stderr,
            )
            return EXIT_CONFIG_ERROR

    params = build_request(args.scenario, args.model, args.max_tokens, args.prompt)
    client = make_client(api_key, http_client=http_client)
    record = run_diagnosis(client, params, scenario=args.scenario, prompt=args.prompt)

    # Redact before anything leaves this function.
    record = redact_obj(record, extra_secrets=[api_key])

    info = CATALOG[record["classification"]["key"]] if record["outcome"] == "error" else None

    if args.json:
        print(json.dumps(record, indent=2, ensure_ascii=False))
    else:
        print(format_report(record, info))

    if not args.no_log:
        log_file = write_log(record, args.log_dir)
        print(f"Log saved   : {log_file} (log_id={record['log_id']})")

    return EXIT_OK if record["outcome"] == "success" else EXIT_API_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
