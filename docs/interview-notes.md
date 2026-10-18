# Interview notes

Short facts about this project. No extra claims.

## (a) What I built

- A CLI (`src/diagnose.py`) that sends one small Messages API request.
- It shows the HTTP status, error type, message, request ID, likely causes, and next checks.
- For 429, it shows `retry-after` and the `anthropic-ratelimit-*` headers.
- It writes one JSON line per run. The log has no API key and no prompt text.
- A CLI (`src/escalate.py`) that turns one log record into an escalation report for engineers.
- A troubleshooting table, an escalation report template, and four customer reply templates.
- 43 mock tests, and 4 live tests that run only with `pytest -m live`.

## (b) Errors I reproduced and what I learned

I reproduced three errors with the real API on 2026-10-18. Each was sent once with the CLI and once with pytest.

- **401** `authentication_error` with a fake key. Message: `invalid x-api-key`.
- **404** `not_found_error` with a model name that does not exist. Message: `model: claude-model-that-does-not-exist`.
- **400** `invalid_request_error` with `max_tokens = -1`. Message: `max_tokens: must be greater than or equal to 0`.
- A normal request with `claude-haiku-5-5` and `max_tokens = 16` returned 200.

What I learned from the real responses:

- Every error response had a `request-id` header, even the 401.
- All three errors had `x-should-retry: false`. The SDK reads this header and does not retry them.
- The error responses had no `anthropic-ratelimit-*` headers. The successful response had them.
- The 400 and 404 messages start with the field name. Reading `error.message` first finds the cause fast.

Errors I did **not** reproduce: 402, 403, 409, 413, 429, 500, 504, 529. I tested them with mocks only.

What I learned from the official docs:

- A 429 can mean two things. A rate limit has `retry-after`. A monthly spend cap has no `retry-after` and has `error_code = enforced_spend_limit_reached`.
- A spend limit that the customer sets returns 400, not 429.
- 413 comes from Cloudflare before the API, so the request ID can be missing.
- The SDK retries 429 and 5xx twice by default. One failure in an app can mean three requests.

## (c) Design choices

- Retries are off in the diagnose tool, to see the first response and avoid extra requests.
- One shared error table for the screen, the reports, and the tests.
- Reports keep facts and hypotheses in separate sections.
- Secrets are hidden before printing or saving, and again at the end of each report.
- Logs keep only useful headers. They do not keep organization or workspace IDs.
- I did not cause 429 or 529 with heavy traffic. I used mocks.
- Live tests used the smallest model and `max_tokens = 16`.
- I checked error codes, headers, model IDs, and SDK behavior in the official docs first.
