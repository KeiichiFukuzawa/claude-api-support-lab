# Case study: 404 not_found_error: the model name does not exist

> This is a self-made reproduction with the real Claude API, not a real customer case.
> Run on 2026-10-18T14:34:02Z (UTC) with anthropic-python 1.13.0, retries off.

## 1. Steps to reproduce

1. Install the project: `pip install -e ".[dev]"`.
2. Set `ANTHROPIC_API_KEY` to a valid key. The tool sends the model name `claude-model-that-does-not-exist`.
3. Run: `python -m src.diagnose --scenario bad-model`.
4. Expected result: HTTP 404 (`not_found_error`).

## 2. Log excerpt (masked)

The log never has the API key or the prompt text. The prompt is shown by its length only (`prompt_chars`).

```json
{
  "log_id": "1eaa96ce6916",
  "timestamp": "2026-10-18T14:34:02Z",
  "tool": "diagnose",
  "scenario": "bad-model",
  "sdk": "anthropic-python 1.13.0",
  "python": "3.13.16",
  "max_retries": 0,
  "request": {
    "endpoint": "POST /v1/messages",
    "model": "claude-model-that-does-not-exist",
    "max_tokens": 16,
    "message_count": 1,
    "prompt_chars": 23
  },
  "outcome": "error",
  "http_status": 404,
  "error_type": "not_found_error",
  "error_message": "model: claude-model-that-does-not-exist",
  "error_code": null,
  "body_format": "json",
  "request_id": "req_011Cg9sHU6ZgKvRJvYep8vaN",
  "body_request_id": "req_011Cg9sHU6ZgKvRJvYep8vaN",
  "headers": {
    "cf-ray": "a4c842f64c40270f-ATL",
    "request-id": "req_011Cg9sHU6ZgKvRJvYep8vaN",
    "x-should-retry": "false"
  },
  "classification": {
    "key": "404",
    "title": "Not found",
    "retryable": "no (fix the model name or URL first)"
  },
  "elapsed_ms": 359
}
```

## 3. Cause

The model name in the request does not match any model that this key can use. The message named the field and the value: `model: claude-model-that-does-not-exist`.

## 4. Fix

1. Copy the exact model ID from the Models overview page (for example, `claude-haiku-5-5`).
2. Call `GET /v1/models` with the same key to see which models it can use.
3. Send the request again with the correct ID.

## 5. How to prevent it

- Keep the model ID in one config value, not in many places in the code.
- Check model IDs against `GET /v1/models` when the app starts or in CI.
- Watch the model deprecation page, so a retired model does not surprise you.

## 6. What I learned from the real response

- The message starts with `model:` and shows the value that was sent. This makes the cause clear.
- The same key and the same request with `claude-haiku-5-5` returned 200. This shows the key was fine and only the model name was wrong.
- The response had a request ID and `x-should-retry: false`.

## 7. Example escalation report

In real support, this error is usually solved with the customer, without engineering.
The report below shows the format. It was made with `python -m src.escalate --log-id 1eaa96ce6916 ...`.

````markdown
# Escalation report: Not found (404)

> Facts and hypotheses are in separate sections. Facts come from the log. Hypotheses are not confirmed.

## 1. Summary
A Messages API request to model `claude-model-that-does-not-exist` failed with 404 (not_found_error) at 2026-10-18T14:34:02Z. Category: Not found.

## 2. What the customer tried to do
Self-made reproduction (not a real customer): send one Messages API request with a model name that does not exist.

## 3. Facts (from the log)
| Item | Value |
|---|---|
| HTTP status | 404 (not_found_error) |
| Error type | `not_found_error` |
| Error message | model: claude-model-that-does-not-exist |
| Error code | `-` |
| Request ID | `req_011Cg9sHU6ZgKvRJvYep8vaN` |
| Model | `claude-model-that-does-not-exist` |
| Time (UTC) | 2026-10-18T14:34:02Z |
| Endpoint | `POST /v1/messages` |
| max_tokens | 16 |
| SDK | anthropic-python 1.13.0 |
| Log ID | `1eaa96ce6916` |

Response headers we kept:
- `cf-ray: a4c842f64c40270f-ATL`
- `request-id: req_011Cg9sHU6ZgKvRJvYep8vaN`
- `x-should-retry: false`

## 4. Steps to reproduce
1. Clone this repository and install it: `pip install -e ".[dev]"`.
2. Set ANTHROPIC_API_KEY in your shell (the key is not included in this report).
3. Run: `python -m src.diagnose --scenario bad-model --max-tokens 16`.
4. Same request without the tool: `POST /v1/messages` with model `claude-model-that-does-not-exist`, max_tokens `16`, 1 user message (23 characters; text not included).
5. Expected result: HTTP 404 (not_found_error).

## 5. What we already checked
- Sent one request with anthropic-python 1.13.0 (Python 3.13.16). Automatic retries were off (max_retries=0), so this is the first response.
- The response had a request ID. It is in the Facts table.
- Ran the bad-model scenario on purpose.
- The same key and the same request with model claude-haiku-5-5 returned 200 (request ID req_011Cg9sHi6S3EidUjbPwAXRt).

## 6. Likely cause (hypothesis, not confirmed)
- The model name has a typo or uses a wrong format.
- The model was retired, or the organization cannot use it.
- The endpoint path or a resource ID in the URL is wrong.

Retry advice from the docs: no (fix the model name or URL first).

## 7. Customer impact
Example only. In a real case: all requests that use this model name fail.

## 8. What we need from engineering
Example only. Escalate only if a model listed by GET /v1/models for this key still returns 404.

## 9. Reporter
Support lab (personal project)
````
