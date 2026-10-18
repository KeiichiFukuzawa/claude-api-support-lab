"""Mock tests for escalate.py: picking a record and building the report."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src import diagnose, escalate
from tests.conftest import FAKE_ENV_KEY, SUCCESS_BODY, FakeAPI, error_body, json_response

SECRET_PROMPT = "SECRET-PROMPT-TEXT-do-not-report"


def make_log(tmp_path: Path, status: int, body: dict, headers: dict, scenario: str = "normal") -> dict:
    """Create one real log line by running diagnose against the fake API."""
    fake = FakeAPI(json_response(status, body, headers))
    diagnose.main(
        ["--log-dir", str(tmp_path), "--prompt", SECRET_PROMPT, "--scenario", scenario],
        http_client=fake.http_client(),
    )
    lines = []
    for f in tmp_path.glob("*.jsonl"):
        lines += f.read_text().splitlines()
    return json.loads(lines[-1])


@pytest.fixture
def rate_limit_record(tmp_path, capsys) -> dict:
    record = make_log(
        tmp_path,
        429,
        error_body("rate_limit_error", "rate limit exceeded", "req_esc_429"),
        {"request-id": "req_esc_429", "retry-after": "30", "anthropic-ratelimit-requests-remaining": "0"},
    )
    capsys.readouterr()
    return record


REQUIRED_SECTIONS = [
    "## 1. Summary",
    "## 2. What the customer tried to do",
    "## 3. Facts (from the log)",
    "## 4. Steps to reproduce",
    "## 5. What we already checked",
    "## 6. Likely cause (hypothesis, not confirmed)",
    "## 7. Customer impact",
    "## 8. What we need from engineering",
]


def test_report_has_all_sections_and_facts(rate_limit_record):
    report = escalate.build_report(rate_limit_record)
    for section in REQUIRED_SECTIONS:
        assert section in report
    assert "`req_esc_429`" in report
    assert "429 (rate_limit_error)" in report
    assert "`claude-haiku-5-5`" in report
    assert rate_limit_record["timestamp"] in report
    assert "The retry-after header was present: 30 seconds." in report


def test_missing_human_input_shows_todo(rate_limit_record):
    report = escalate.build_report(rate_limit_record)
    assert report.count(escalate.TODO) >= 3  # goal, impact, ask (and reporter)


def test_human_input_is_used(rate_limit_record):
    report = escalate.build_report(
        rate_limit_record,
        goal="Classify support tickets",
        impact="Batch job stopped for 2 hours",
        checked=["Status page showed no incident"],
        ask="Please confirm the workspace limit",
        reporter="Support team",
    )
    assert escalate.TODO not in report
    assert "Classify support tickets" in report
    assert "- Status page showed no incident" in report


def test_reproduction_steps_are_numbered_and_have_expected_result(rate_limit_record):
    report = escalate.build_report(rate_limit_record)
    steps = report.split("## 4. Steps to reproduce")[1].split("## 5.")[0]
    assert "1. " in steps and "5. " in steps
    assert "Expected result: HTTP 429 (rate_limit_error)." in steps
    assert "python -m src.diagnose --scenario normal --model claude-haiku-5-5 --max-tokens 16" in steps


def test_report_never_contains_key_or_prompt(rate_limit_record):
    # Even if a key somehow got into a log record, the report hides it.
    poisoned = dict(rate_limit_record, error_message=f"bad key {FAKE_ENV_KEY} sk-ant-api03-leak")
    report = escalate.build_report(poisoned)
    assert FAKE_ENV_KEY not in report
    assert "sk-ant-api03-leak" not in report
    assert SECRET_PROMPT not in report
    assert f"{len(SECRET_PROMPT)} characters" in report


def test_select_latest_failure_skips_success(tmp_path, capsys):
    make_log(tmp_path, 404, error_body("not_found_error", "model: x", "req_old"), {"request-id": "req_old"})
    make_log(tmp_path, 401, error_body("authentication_error", "invalid x-api-key", "req_new"),
             {"request-id": "req_new"})
    make_log(tmp_path, 200, SUCCESS_BODY, {"request-id": "req_ok"})
    capsys.readouterr()

    records = escalate.read_records(tmp_path)
    assert len(records) == 3
    assert escalate.select_record(records)["request_id"] == "req_new"
    assert escalate.select_record(records, request_id="req_old")["http_status"] == 404
    log_id = records[0]["log_id"]
    assert escalate.select_record(records, log_id=log_id)["log_id"] == log_id
    with pytest.raises(escalate.RecordNotFound):
        escalate.select_record(records, request_id="req_missing")


def test_success_record_is_rejected(tmp_path, capsys):
    record = make_log(tmp_path, 200, SUCCESS_BODY, {"request-id": "req_ok"})
    with pytest.raises(ValueError):
        escalate.build_report(record)


def test_413_report_without_request_id(tmp_path, capsys):
    import httpx2

    fake = FakeAPI(lambda _req: httpx2.Response(413, text="<html>413</html>"))
    diagnose.main(["--log-dir", str(tmp_path)], http_client=fake.http_client())
    record = escalate.select_record(escalate.read_records(tmp_path))
    report = escalate.build_report(record)
    assert "| Request ID | `none` |" in report
    assert "The response had no request ID header." in report


def test_main_writes_report_file(rate_limit_record, tmp_path, capsys):
    out_file = tmp_path / "reports" / "case.md"
    code = escalate.main(["--log-dir", str(tmp_path), "--out", str(out_file)])
    assert code == 0
    assert out_file.exists()
    assert "# Escalation report: Rate limit reached (429)" in out_file.read_text()


def test_main_with_empty_log_dir(tmp_path, capsys):
    code = escalate.main(["--log-dir", str(tmp_path / "empty")])
    assert code == 1
    assert "No matching log record" in capsys.readouterr().err
