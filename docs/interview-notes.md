# Interview notes

Short facts about this project. No extra claims.

> Status: draft. Part (b) will be updated after the live tests.

## (a) What I built

- A CLI (`src/diagnose.py`) that sends one small Messages API request.
- It shows the HTTP status, error type, message, request ID, likely causes, and next checks.
- For 429, it shows `retry-after` and the `anthropic-ratelimit-*` headers.
- It writes one JSON line per run. The log has no API key and no prompt text.
- A CLI (`src/escalate.py`) that turns one log record into an escalation report for engineers.
- A troubleshooting table, an escalation report template, and four customer reply templates.
- 43 mock tests. 4 live tests that run only with `pytest -m live`.

## (b) Errors I reproduced and what I learned

- Live tests: **not run yet.** No error has been reproduced with the real API so far.
- Mock tests cover 400, 401, 402, 403, 404, 409, 413, 429, 500, 504, 529, connection errors, and timeouts.
- Things I learned from the official docs while building this:
  - A 429 can mean two different things. A rate limit has `retry-after`. A monthly spend cap has no `retry-after` and has `error_code = enforced_spend_limit_reached`.
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
- I checked error codes, headers, model IDs, and SDK behavior in the official docs first.
