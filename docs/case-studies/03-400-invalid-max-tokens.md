# Case study: 400 invalid_request_error: max_tokens is negative

> This is a self-made reproduction with the real Claude API, not a real customer case.
> Run on 2026-10-18T14:34:04Z (UTC) with anthropic-python 1.13.0, retries off.

## 1. Steps to reproduce

1. Install the project: `pip install -e ".[dev]"`.
2. Set `ANTHROPIC_API_KEY` to a valid key. The tool sends `max_tokens = -1`.
3. Run: `python -m src.diagnose --scenario bad-param`.
4. Expected result: HTTP 400 (`invalid_request_error`).

## 2. Log excerpt (masked)

The log never has the API key or the prompt text. The prompt is shown by its length only (`prompt_chars`).

```json
{
  "log_id": "0550aa184348",
  "timestamp": "2026-10-18T14:34:04Z",
  "tool": "diagnose",
  "scenario": "bad-param",
  "sdk": "anthropic-python 1.13.0",
  "python": "3.13.16",
  "max_retries": 0,
  "request": {
    "endpoint": "POST /v1/messages",
    "model": "claude-haiku-5-5",
    "max_tokens": -1,
    "message_count": 1,
    "prompt_chars": 23
  },
  "outcome": "error",
  "http_status": 400,
  "error_type": "invalid_request_error",
  "error_message": "max_tokens: must be greater than or equal to 0",
  "error_code": null,
  "body_format": "json",
  "request_id": "req_011Cg9sHbAU13WqtmCNGgJTt",
  "body_request_id": "req_011Cg9sHbAU13WqtmCNGgJTt",
  "headers": {
    "cf-ray": "a4c84300ce4945c2-ATL",
    "request-id": "req_011Cg9sHbAU13WqtmCNGgJTt",
    "x-should-retry": "false"
  },
  "classification": {
    "key": "400",
    "title": "Invalid request",
    "retryable": "no (fix the request first)"
  },
  "elapsed_ms": 213
}
```

## 3. Cause

`max_tokens` must be 0 or more (the Messages API reference says minimum: 0). The message named the field: `max_tokens: must be greater than or equal to 0`.

## 4. Fix

1. Set `max_tokens` to a positive number that fits the expected answer length.
2. Send the request again.

## 5. How to prevent it

- Check request values before you send them (for example, `max_tokens > 0`).
- Do not compute `max_tokens` from other numbers without a lower limit.
- Log the request summary (without the prompt), so a bad value is easy to find.

## 6. What I learned from the real response

- The message starts with the field name (`max_tokens:`). Reading `error.message` first is the fastest check for a 400.
- The same request with `max_tokens = 16` returned 200.
- The response had a request ID and `x-should-retry: false`.

## 7. Example escalation report

In real support, this error is usually solved with the customer, without engineering.
The report below shows the format. It was made with `python -m src.escalate --log-id 0550aa184348 ...`.

````markdown
# Escalation report: Invalid request (400)

> Facts and hypotheses are in separate sections. Facts come from the log. Hypotheses are not confirmed.

## 1. Summary
A Messages API request to model `claude-haiku-5-5` failed with 400 (invalid_request_error) at 2026-10-18T14:34:04Z. Category: Invalid request.

## 2. What the customer tried to do
Self-made reproduction (not a real customer): send one Messages API request with max_tokens = -1.

## 3. Facts (from the log)
| Item | Value |
|---|---|
| HTTP status | 400 (invalid_request_error) |
| Error type | `invalid_request_error` |
| Error message | max_tokens: must be greater than or equal to 0 |
| Error code | `-` |
| Request ID | `req_011Cg9sHbAU13WqtmCNGgJTt` |
| Model | `claude-haiku-5-5` |
| Time (UTC) | 2026-10-18T14:34:04Z |
| Endpoint | `POST /v1/messages` |
| max_tokens | -1 |
| SDK | anthropic-python 1.13.0 |
| Log ID | `0550aa184348` |

Response headers we kept:
- `cf-ray: a4c84300ce4945c2-ATL`
- `request-id: req_011Cg9sHbAU13WqtmCNGgJTt`
- `x-should-retry: false`

## 4. Steps to reproduce
1. Clone this repository and install it: `pip install -e ".[dev]"`.
2. Set ANTHROPIC_API_KEY in your shell (the key is not included in this report).
3. Run: `python -m src.diagnose --scenario bad-param --model claude-haiku-5-5`.
4. Same request without the tool: `POST /v1/messages` with model `claude-haiku-5-5`, max_tokens `-1`, 1 user message (23 characters; text not included).
5. Expected result: HTTP 400 (invalid_request_error).

## 5. What we already checked
- Sent one request with anthropic-python 1.13.0 (Python 3.13.16). Automatic retries were off (max_retries=0), so this is the first response.
- The response had a request ID. It is in the Facts table.
- Ran the bad-param scenario on purpose.
- The same request with max_tokens = 16 returned 200 (request ID req_011Cg9sHi6S3EidUjbPwAXRt).

## 6. Likely cause (hypothesis, not confirmed)
- A required field is missing or has a wrong value (model, max_tokens, messages).
- A parameter is not supported by this model (for example, a thinking or tool_choice setting).
- The request body is not valid JSON.
- A spend limit that the organization set itself was reached (the message starts with 'You have reached your specified').

Retry advice from the docs: no (fix the request first).

## 7. Customer impact
Example only. In a real case: every request with this setting fails at once.

## 8. What we need from engineering
Example only. A 400 with a clear field message is usually solved by the customer. Escalate only if a request that matches the API reference still returns 400.

## 9. Reporter
Support lab (personal project)
````
