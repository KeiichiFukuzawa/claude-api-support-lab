"""Live tests. They call the real Claude API.

They do NOT run by default. Run them only on purpose:
    pytest -m live -v

What they send (one request each, retries off):
- bad key   -> expect 401 (fake key, does not use your key)
- bad model -> expect 404
- bad param -> expect 400 (max_tokens = -1)
- normal    -> expect 200 with the smallest model and max_tokens = 16

We never send many requests to cause 429 or 529. Those are tested with mocks.
"""

from __future__ import annotations

import json
import os

import pytest

from src import diagnose

pytestmark = pytest.mark.live

needs_key = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"), reason="ANTHROPIC_API_KEY is not set"
)


def run_live(tmp_path, *args: str) -> dict:
    code = diagnose.main(["--log-dir", str(tmp_path), *args])
    lines = []
    for f in tmp_path.glob("*.jsonl"):
        lines += f.read_text().splitlines()
    record = json.loads(lines[-1])
    record["_exit_code"] = code
    return record


def test_live_bad_key_returns_401(tmp_path):
    rec = run_live(tmp_path, "--scenario", "bad-key")
    assert rec["http_status"] == 401
    assert rec["error_type"] == "authentication_error"
    assert rec["request_id"], "the API should send a request-id header"


@needs_key
def test_live_bad_model_returns_404(tmp_path):
    rec = run_live(tmp_path, "--scenario", "bad-model")
    assert rec["http_status"] == 404
    assert rec["error_type"] == "not_found_error"
    assert rec["request_id"]


@needs_key
def test_live_bad_param_returns_400(tmp_path):
    rec = run_live(tmp_path, "--scenario", "bad-param")
    assert rec["http_status"] == 400
    assert rec["error_type"] == "invalid_request_error"
    assert rec["request_id"]


@needs_key
def test_live_normal_request_succeeds(tmp_path):
    rec = run_live(tmp_path, "--scenario", "normal")
    assert rec["_exit_code"] == diagnose.EXIT_OK
    assert rec["http_status"] == 200
    assert rec["response"]["output_tokens"] <= 16
