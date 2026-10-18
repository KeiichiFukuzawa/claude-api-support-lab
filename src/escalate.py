"""Make an escalation report (Markdown) for engineers from one diagnose log record.

Usage examples:
    python -m src.escalate                                # latest failure in logs/
    python -m src.escalate --log-id 3f2a9c1b7d4e          # one record by log_id
    python -m src.escalate --request-id req_011C...       # one record by request ID
    python -m src.escalate --goal "Summarize support tickets" \
        --impact "Batch job stopped for 2 hours" \
        --checked "Key is set in the same shell" --out reports/case.md

Facts come from the log. Things only a person knows (goal, impact, what was checked,
what we need) come from the options. If an option is missing, the report shows TODO.
The report never includes the API key, personal data, or the prompt text.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from src.diagnose import DEFAULT_LOG_DIR
from src.error_catalog import CATALOG, ErrorInfo
from src.redact import redact_text

TODO = "TODO: fill in before sending."


class RecordNotFound(Exception):
    pass


def read_records(log_dir: str | Path) -> list[dict[str, Any]]:
    """Read every JSON line from logs/*.jsonl, oldest first."""
    records: list[dict[str, Any]] = []
    for path in sorted(Path(log_dir).glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # skip broken lines, keep going
    records.sort(key=lambda r: r.get("timestamp", ""))
    return records


def select_record(
    records: list[dict[str, Any]],
    *,
    log_id: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Pick one record. Default: the latest failure."""
    if log_id:
        matches = [r for r in records if r.get("log_id") == log_id]
    elif request_id:
        matches = [r for r in records if r.get("request_id") == request_id]
    else:
        matches = [r for r in records if r.get("outcome") == "error"]
    if not matches:
        raise RecordNotFound("No matching log record was found.")
    return matches[-1]


def _cell(value: Any) -> str:
    """Make a value safe for one Markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else f"- {TODO}"


def _numbered(items: list[str]) -> str:
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))


def reproduction_steps(record: dict[str, Any]) -> list[str]:
    """Numbered steps that an engineer can follow without asking us."""
    req = record["request"]
    scenario = record.get("scenario", "normal")
    cmd = ["python -m src.diagnose", f"--scenario {scenario}"]
    if scenario not in ("bad-model",):
        cmd.append(f"--model {req['model']}")
    if scenario not in ("bad-param",):
        cmd.append(f"--max-tokens {req['max_tokens']}")

    key_step = (
        "No real API key is needed. This scenario uses a fake key on purpose."
        if scenario == "bad-key"
        else "Set ANTHROPIC_API_KEY in your shell (the key is not included in this report)."
    )
    status = record.get("http_status")
    expected = (
        f"HTTP {status} ({record.get('error_type')})" if status is not None else "no HTTP response"
    )
    return [
        "Clone this repository and install it: `pip install -e \".[dev]\"`.",
        key_step,
        f"Run: `{' '.join(cmd)}`.",
        f"Same request without the tool: `{req['endpoint']}` with model `{req['model']}`, "
        f"max_tokens `{req['max_tokens']}`, {req['message_count']} user message "
        f"({req['prompt_chars']} characters; text not included).",
        f"Expected result: {expected}.",
    ]


def auto_checked(record: dict[str, Any]) -> list[str]:
    """Facts that the diagnose tool itself confirmed."""
    items = [
        f"Sent one request with {record.get('sdk', 'the SDK')} "
        f"(Python {record.get('python', '?')}). Automatic retries were off "
        f"(max_retries={record.get('max_retries', '?')}), so this is the first response.",
    ]
    if record.get("request_id"):
        items.append("The response had a request ID. It is in the Facts table.")
    elif record.get("http_status") is not None:
        items.append("The response had no request ID header.")
    headers = record.get("headers", {})
    if record.get("http_status") == 429:
        if "retry-after" in headers:
            items.append(f"The retry-after header was present: {headers['retry-after']} seconds.")
        else:
            items.append("The retry-after header was not present.")
    return items


def build_report(
    record: dict[str, Any],
    *,
    goal: str | None = None,
    impact: str | None = None,
    checked: list[str] | None = None,
    ask: str | None = None,
    reporter: str | None = None,
) -> str:
    """Return the report as Markdown text."""
    if record.get("outcome") != "error":
        raise ValueError("This record is a success. Pick a failed request.")

    info: ErrorInfo = CATALOG.get(record["classification"]["key"], CATALOG["unknown"])
    req = record["request"]
    status = record.get("http_status")
    status_text = f"{status} ({record.get('error_type')})" if status is not None else "No HTTP response"
    headers = record.get("headers", {})
    header_lines = [f"`{k}: {v}`" for k, v in headers.items()] or ["(none recorded)"]

    summary = (
        f"A Messages API request to model `{req['model']}` failed with {status_text} "
        f"at {record['timestamp']}. Category: {info.title}."
    )

    report = f"""# Escalation report: {info.title} ({status if status is not None else 'no status'})

> Facts and hypotheses are in separate sections. Facts come from the log. Hypotheses are not confirmed.

## 1. Summary
{summary}

## 2. What the customer tried to do
{goal or TODO}

## 3. Facts (from the log)
| Item | Value |
|---|---|
| HTTP status | {status_text} |
| Error type | `{record.get('error_type') or '-'}` |
| Error message | {_cell(record.get('error_message') or '-')} |
| Error code | `{record.get('error_code') or '-'}` |
| Request ID | `{record.get('request_id') or 'none'}` |
| Model | `{req['model']}` |
| Time (UTC) | {record['timestamp']} |
| Endpoint | `{req['endpoint']}` |
| max_tokens | {req['max_tokens']} |
| SDK | {record.get('sdk', '-')} |
| Log ID | `{record.get('log_id', '-')}` |

Response headers we kept:
{_bullets(header_lines)}

## 4. Steps to reproduce
{_numbered(reproduction_steps(record))}

## 5. What we already checked
{_bullets(auto_checked(record) + list(checked or []))}

## 6. Likely cause (hypothesis, not confirmed)
{_bullets(info.likely_causes)}

Retry advice from the docs: {info.retryable}.

## 7. Customer impact
{impact or TODO}

## 8. What we need from engineering
{ask or TODO}

## 9. Reporter
{reporter or TODO}
"""
    # Last safety net: never let a key slip into the report.
    return redact_text(report)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.escalate",
        description="Make an escalation report from a diagnose log record.",
    )
    parser.add_argument("--log-dir", default=DEFAULT_LOG_DIR, help="Default: logs")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--log-id", help="Pick the record with this log_id.")
    group.add_argument("--request-id", help="Pick the record with this request ID.")
    parser.add_argument("--goal", help="What the customer tried to do.")
    parser.add_argument("--impact", help="Customer impact.")
    parser.add_argument("--checked", action="append", help="Something already checked (repeatable).")
    parser.add_argument("--ask", help="What we need from engineering.")
    parser.add_argument("--reporter", help="Your name or team.")
    parser.add_argument("--out", help="Write the report to this file instead of the screen.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        record = select_record(
            read_records(args.log_dir), log_id=args.log_id, request_id=args.request_id
        )
        report = build_report(
            record,
            goal=args.goal,
            impact=args.impact,
            checked=args.checked,
            ask=args.ask,
            reporter=args.reporter,
        )
    except (RecordNotFound, ValueError) as exc:
        print(f"{exc} Run `python -m src.diagnose` first, or check --log-dir.", file=sys.stderr)
        return 1

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report saved: {out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
