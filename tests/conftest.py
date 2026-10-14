"""Shared test helpers.

We never call the real API here. A fake HTTP layer (httpx2.MockTransport)
returns responses that look like real API errors.
"""

from __future__ import annotations

from typing import Any, Callable

import anthropic
import httpx2
import pytest

FAKE_ENV_KEY = "sk-ant-api03-TESTKEY-not-real-0123456789"


def error_body(status_type: str, message: str, request_id: str | None, details: dict | None = None) -> dict:
    error: dict[str, Any] = {"type": status_type, "message": message}
    if details:
        error["details"] = details
    body: dict[str, Any] = {"type": "error", "error": error}
    if request_id:
        body["request_id"] = request_id
    return body


SUCCESS_BODY = {
    "id": "msg_test",
    "type": "message",
    "role": "assistant",
    "model": "claude-haiku-5-5",
    "content": [{"type": "text", "text": "OK"}],
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {"input_tokens": 12, "output_tokens": 2},
}


class FakeAPI:
    """Counts requests and returns one prepared response."""

    def __init__(self, handler: Callable[[httpx2.Request], httpx2.Response]):
        self.handler = handler
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        return self.handler(request)

    def http_client(self) -> anthropic.DefaultHttpxClient:
        return anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(self))


def json_response(status: int, body: dict, headers: dict | None = None) -> Callable:
    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(status, json=body, headers=headers or {})

    return handler


@pytest.fixture(autouse=True)
def fake_env_key(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> str | None:
    """Every mock test sees a fake key, never a real one. Live tests keep the real key."""
    if request.node.get_closest_marker("live"):
        return None
    monkeypatch.setenv("ANTHROPIC_API_KEY", FAKE_ENV_KEY)
    return FAKE_ENV_KEY
