"""Mock tests for diagnose.py: classification, screen output, and logs.

These errors are hard or unsafe to cause on purpose (429, 500, 529, 413 ...),
so a fake HTTP layer returns realistic error responses instead.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx2
import pytest

from src import diagnose
from src.error_catalog import CATALOG, classify
from tests.conftest import FAKE_ENV_KEY, SUCCESS_BODY, FakeAPI, error_body, json_response

SECRET_PROMPT = "SECRET-PROMPT-TEXT-do-not-log"

RATE_LIMIT_HEADERS = {
    "request-id": "req_test_429",
    "retry-after": "17",
    "anthropic-ratelimit-requests-limit": "50",
    "anthropic-ratelimit-requests-remaining": "0",
    "anthropic-ratelimit-requests-reset": "2026-10-14T12:00:17Z",
    "anthropic-ratelimit-input-tokens-remaining": "41000",
    "anthropic-organization-id": "org-should-not-be-logged",
}
RATE_LIMIT_BODY = error_body("rate_limit_error", "rate limit exceeded", "req_test_429")

# (case id, status, body, headers, expected catalog key)
CASES = [
    ("400", 400, error_body("invalid_request_error", "max_tokens: must be >= 0", "req_400"),
     {"request-id": "req_400"}, "400"),
    ("400-spend-limit", 400,
     error_body("invalid_request_error",
                "You have reached your specified API usage limits. You will regain access on 2026-11-01.",
                "req_400s"),
     {"request-id": "req_400s"}, "400_spend_limit"),
    ("401", 401, error_body("authentication_error", "invalid x-api-key", "req_401"),
     {"request-id": "req_401"}, "401"),
    ("402", 402, error_body("billing_error", "billing issue", "req_402"),
     {"request-id": "req_402"}, "402"),
    ("403", 403, error_body("permission_error", "not allowed", "req_403"),
     {"request-id": "req_403"}, "403"),
    ("404", 404, error_body("not_found_error", "model: claude-x", "req_404"),
     {"request-id": "req_404"}, "404"),
    ("409", 409, error_body("conflict_error", "conflict", "req_409"),
     {"request-id": "req_409"}, "409"),
    ("429", 429, RATE_LIMIT_BODY, RATE_LIMIT_HEADERS, "429"),
    ("429-spend-cap", 429,
     error_body("rate_limit_error", "You have reached your API usage limits.", "req_cap",
                details={"error_code": "enforced_spend_limit_reached"}),
     {"request-id": "req_cap"}, "429_spend_cap"),
    ("500", 500, error_body("api_error", "Internal server error", "req_500"),
     {"request-id": "req_500"}, "500"),
    ("504", 504, error_body("timeout_error", "timeout", "req_504"),
     {"request-id": "req_504"}, "504"),
    ("529", 529, error_body("overloaded_error", "Overloaded", "req_529"),
     {"request-id": "req_529"}, "529"),
    ("503-unknown", 503, error_body("some_new_error", "new kind of error", "req_503"),
     {"request-id": "req_503"}, "unknown"),
]


def run(fake: FakeAPI, tmp_path: Path, capsys, *args: str) -> tuple[int, str, list[dict]]:
    argv = ["--log-dir", str(tmp_path), "--prompt", SECRET_PROMPT, *args]
    code = diagnose.main(argv, http_client=fake.http_client())
    out = capsys.readouterr().out
    records = []
    for f in tmp_path.glob("*.jsonl"):
        records += [json.loads(line) for line in f.read_text().splitlines()]
    return code, out, records


@pytest.mark.parametrize("case_id,status,body,headers,expected_key", CASES, ids=[c[0] for c in CASES])
def test_error_is_classified_printed_and_logged(case_id, status, body, headers, expected_key, tmp_path, capsys):
    fake = FakeAPI(json_response(status, body, headers))
    code, out, records = run(fake, tmp_path, capsys)

    # One request only. The SDK would retry 429 and 5xx twice by default.
    assert len(fake.requests) == 1
    assert code == diagnose.EXIT_API_ERROR

    info = CATALOG[expected_key]
    assert f"HTTP status : {status}" in out
    assert info.title in out
    assert body["request_id"] in out

    assert len(records) == 1
    rec = records[0]
    assert rec["outcome"] == "error"
    assert rec["http_status"] == status
    assert rec["error_type"] == body["error"]["type"]
    assert rec["request_id"] == body["request_id"]
    assert rec["classification"]["key"] == expected_key

    # Secrets and prompt text never reach the screen or the log.
    log_text = json.dumps(rec)
    for text in (out, log_text):
        assert FAKE_ENV_KEY not in text
        assert SECRET_PROMPT not in text
    assert rec["request"]["prompt_chars"] == len(SECRET_PROMPT)
    assert "anthropic-organization-id" not in rec["headers"]


def test_429_shows_retry_after_and_zero_remaining(tmp_path, capsys):
    fake = FakeAPI(json_response(429, RATE_LIMIT_BODY, RATE_LIMIT_HEADERS))
    _, out, records = run(fake, tmp_path, capsys)
    assert "retry-after: 17 -> wait 17 seconds" in out
    assert "anthropic-ratelimit-requests-remaining: 0   <- at zero" in out
    assert "anthropic-ratelimit-input-tokens-remaining: 41000" in out
    assert records[0]["headers"]["retry-after"] == "17"


def test_429_spend_cap_says_retry_will_not_help(tmp_path, capsys):
    body = error_body("rate_limit_error", "You have reached your API usage limits.", "req_cap",
                      details={"error_code": "enforced_spend_limit_reached"})
    fake = FakeAPI(json_response(429, body, {"request-id": "req_cap"}))
    _, out, records = run(fake, tmp_path, capsys)
    assert "retry-after: (not present)" in out
    assert "monthly spend cap. Retrying will not help." in out
    assert records[0]["error_code"] == "enforced_spend_limit_reached"


def test_413_with_non_json_body_and_no_request_id(tmp_path, capsys):
    def handler(_request):
        return httpx2.Response(413, text="<html>413 Request Entity Too Large</html>")

    fake = FakeAPI(handler)
    code, out, records = run(fake, tmp_path, capsys)
    assert code == diagnose.EXIT_API_ERROR
    assert "Request too large" in out
    assert "Request ID  : (none)" in out
    rec = records[0]
    assert rec["body_format"] == "non-json"
    assert rec["request_id"] is None
    assert rec["classification"]["key"] == "413"


@pytest.mark.parametrize(
    "exc,expected_key",
    [(httpx2.ConnectError("no route to host"), "connection"), (httpx2.ReadTimeout("read timed out"), "timeout")],
)
def test_transport_errors_have_no_status(exc, expected_key, tmp_path, capsys):
    def handler(_request):
        raise exc

    fake = FakeAPI(handler)
    code, out, records = run(fake, tmp_path, capsys)
    assert code == diagnose.EXIT_API_ERROR
    assert len(fake.requests) == 1
    assert "HTTP status : (no response)" in out
    assert CATALOG[expected_key].title in out
    assert records[0]["classification"]["key"] == expected_key
    assert records[0]["http_status"] is None


def test_success_is_logged_with_usage(tmp_path, capsys):
    fake = FakeAPI(json_response(200, SUCCESS_BODY, {"request-id": "req_ok"}))
    code, out, records = run(fake, tmp_path, capsys)
    assert code == diagnose.EXIT_OK
    assert "Result      : SUCCESS" in out
    rec = records[0]
    assert rec["outcome"] == "success"
    assert rec["request_id"] == "req_ok"
    assert rec["response"]["output_tokens"] == 2


def test_missing_key_sends_nothing(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    fake = FakeAPI(json_response(200, SUCCESS_BODY))
    code = diagnose.main(["--log-dir", str(tmp_path)], http_client=fake.http_client())
    assert code == diagnose.EXIT_CONFIG_ERROR
    assert fake.requests == []
    assert "ANTHROPIC_API_KEY is not set" in capsys.readouterr().err
    assert list(tmp_path.glob("*.jsonl")) == []


@pytest.mark.parametrize(
    "scenario,check",
    [
        ("bad-key", lambda req, body: req.headers["x-api-key"] == diagnose.FAKE_API_KEY),
        ("bad-model", lambda req, body: body["model"] == diagnose.MISSING_MODEL),
        ("bad-param", lambda req, body: body["max_tokens"] == -1),
        ("normal", lambda req, body: body["model"] == diagnose.DEFAULT_MODEL and body["max_tokens"] == 16),
    ],
)
def test_scenarios_build_the_expected_request(scenario, check, tmp_path, capsys):
    fake = FakeAPI(json_response(200, SUCCESS_BODY))
    run(fake, tmp_path, capsys, "--scenario", scenario)
    req = fake.requests[0]
    assert check(req, json.loads(req.content))


def test_no_log_option_writes_nothing(tmp_path, capsys):
    fake = FakeAPI(json_response(200, SUCCESS_BODY))
    diagnose.main(["--log-dir", str(tmp_path), "--no-log"], http_client=fake.http_client())
    assert list(tmp_path.glob("*.jsonl")) == []


def test_classify_unknown_status_falls_back():
    assert classify(418).key == "unknown"
    assert classify(None).key == "connection"
