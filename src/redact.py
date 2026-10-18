"""Hide secrets before anything is printed, logged, or put in a report.

Rules:
- API keys are never written anywhere. We replace them with a fixed marker.
- Prompt text is never written. We keep only its length.
"""

from __future__ import annotations

import os
import re
from typing import Any

REDACTED = "[REDACTED]"

# Anthropic API keys start with "sk-ant-". We also catch bearer tokens.
_KEY_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]+"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)(x-api-key[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+"),
]


def redact_text(text: str, extra_secrets: list[str] | None = None) -> str:
    """Return `text` with API keys and known secret values replaced."""
    if not text:
        return text

    secrets = list(extra_secrets or [])
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        secrets.append(env_key)

    # Replace exact secret values first (longest first, so parts are not left behind).
    for secret in sorted({s for s in secrets if s and len(s) >= 8}, key=len, reverse=True):
        text = text.replace(secret, REDACTED)

    for pattern in _KEY_PATTERNS:
        if pattern.groups:
            text = pattern.sub(lambda m: m.group(1) + REDACTED, text)
        else:
            text = pattern.sub(REDACTED, text)
    return text


def redact_obj(value: Any, extra_secrets: list[str] | None = None) -> Any:
    """Redact every string inside a dict / list structure."""
    if isinstance(value, str):
        return redact_text(value, extra_secrets)
    if isinstance(value, dict):
        return {k: redact_obj(v, extra_secrets) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_obj(v, extra_secrets) for v in value]
    return value


def describe_prompt(prompt: str) -> dict[str, int]:
    """Describe a prompt without keeping its text."""
    return {"prompt_chars": len(prompt)}
