# Case study: 401 authentication_error: the API key is not valid

> This is a self-made reproduction with the real Claude API, not a real customer case.
> Run on 2026-10-18T14:34:01Z (UTC) with anthropic-python 1.13.0, retries off.

## 1. Steps to reproduce

1. Install the project: `pip install -e ".[dev]"`.
2. No real key is needed. The tool sends a fake key (`invalid-key-for-diagnose-test`) on purpose.
3. Run: `python -m src.diagnose --scenario bad-key`.
4. Expected result: HTTP 401 (`authentication_error`).

## 2. Log excerpt (masked)

The log never has the API key or the prompt text. The prompt is shown by its length only (`prompt_chars`).

```json
{
  "log_id": "dcd3eae819ce",
  "timestamp": "2026-10-18T14:34:01Z",
  "tool": "diagnose",
  "scenario": "bad-key",
  "sdk": "anthropic-python 1.13.0",
  "python": "3.13.16",
  "max_retries": 0,
  "request": {
    "endpoint": "POST /v1/messages",
    "model": "claude-haiku-5-5",
    "max_tokens": 16,
    "message_count": 1,
    "prompt_chars": 23
  },
  "outcome": "error",
  "http_status": 401,
  "error_type": "authentication_error",
  "error_message": "invalid x-api-key",
  "error_code": null,
  "body_format": "json",
  "request_id": "req_011Cg9sHMbtgUcFzarquWxAb",
  "body_request_id": "req_011Cg9sHMbtgUcFzarquWxAb",
  "headers": {
    "cf-ray": "a4c842ed38dd7b81-ATL",
    "request-id": "req_011Cg9sHMbtgUcFzarquWxAb",
    "x-should-retry": "false"
  },
  "classification": {
    "key": "401",
    "title": "Authentication failed",
    "retryable": "no (fix the key first)"
  },
  "elapsed_ms": 81
}
```

## 3. Cause

The API key in the `x-api-key` header is not a valid key. The API rejected the request at the authentication step. The message was `invalid x-api-key`.

## 4. Fix

1. Check that the right key is set in the same process that sends the request.
2. Check the key on the API keys page in the Claude Console. Make sure it is active and not expired.
3. If you are not sure, create a new key and test with one small request.

## 5. How to prevent it

- Read the key from one place only (for example, `ANTHROPIC_API_KEY`). Avoid copies in many config files.
- Give test keys a short expiration, and delete them after use.
- Run one small check request after you deploy or rotate a key.

## 6. What I learned from the real response

- The response had a request ID, even though authentication failed.
- The response had `x-should-retry: false`. The SDK reads this header, so it does not retry this error.
- It was the fastest of the three errors (81 ms on my run). It fails before the model runs.

## 7. Example escalation report

In real support, this error is usually solved with the customer, without engineering.
The report below shows the format. It was made with `python -m src.escalate --log-id dcd3eae819ce ...`.

````markdown
# Escalation report: Authentication failed (401)

> Facts and hypotheses are in separate sections. Facts come from the log. Hypotheses are not confirmed.

## 1. Summary
A Messages API request to model `claude-haiku-5-5` failed with 401 (authentication_error) at 2026-10-18T14:34:01Z. Category: Authentication failed.

## 2. What the customer tried to do
Self-made reproduction (not a real customer): send one Messages API request with a key that is not valid.

## 3. Facts (from the log)
| Item | Value |
|---|---|
| HTTP status | 401 (authentication_error) |
| Error type | `authentication_error` |
| Error message | invalid x-api-key |
| Error code | `-` |
| Request ID | `req_011Cg9sHMbtgUcFzarquWxAb` |
| Model | `claude-haiku-5-5` |
| Time (UTC) | 2026-10-18T14:34:01Z |
| Endpoint | `POST /v1/messages` |
| max_tokens | 16 |
| SDK | anthropic-python 1.13.0 |
| Log ID | `dcd3eae819ce` |

Response headers we kept:
- `cf-ray: a4c842ed38dd7b81-ATL`
- `request-id: req_011Cg9sHMbtgUcFzarquWxAb`
- `x-should-retry: false`

## 4. Steps to reproduce
1. Clone this repository and install it: `pip install -e ".[dev]"`.
2. No real API key is needed. This scenario uses a fake key on purpose.
3. Run: `python -m src.diagnose --scenario bad-key --model claude-haiku-5-5 --max-tokens 16`.
4. Same request without the tool: `POST /v1/messages` with model `claude-haiku-5-5`, max_tokens `16`, 1 user message (23 characters; text not included).
5. Expected result: HTTP 401 (authentication_error).

## 5. What we already checked
- Sent one request with anthropic-python 1.13.0 (Python 3.13.16). Automatic retries were off (max_retries=0), so this is the first response.
- The response had a request ID. It is in the Facts table.
- Ran the bad-key scenario on purpose with a fake key (invalid-key-for-diagnose-test).

## 6. Likely cause (hypothesis, not confirmed)
- The API key is missing, mistyped, or has extra spaces or line breaks.
- The API key was revoked, deleted, or has expired.
- The key is read from a different environment variable or file than expected.

Retry advice from the docs: no (fix the key first).

## 7. Customer impact
Example only. In a real case: every request from the app fails until the key is fixed.

## 8. What we need from engineering
Example only. A 401 is usually solved by the customer without engineering. Escalate only if a key that is active in the Console still gets 401.

## 9. Reporter
Support lab (personal project)
````
