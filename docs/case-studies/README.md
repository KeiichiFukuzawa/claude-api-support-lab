# Case studies

One file per error that I **reproduced with the real API**.
I do not write a case study for an error that I did not reproduce.

## Status

| Error | How it is verified | Case study |
|---|---|---|
| 401 authentication_error | Live, 2026-10-18 (fake key) | [01-401-authentication-error.md](01-401-authentication-error.md) |
| 404 not_found_error | Live, 2026-10-18 (model that does not exist) | [02-404-model-not-found.md](02-404-model-not-found.md) |
| 400 invalid_request_error | Live, 2026-10-18 (`max_tokens = -1`) | [03-400-invalid-max-tokens.md](03-400-invalid-max-tokens.md) |
| 402, 403, 409, 413, 429, 500, 504, 529 | Mock tests only (`tests/test_classify.py`) | None. These were **not** reproduced with the real API. |

Each live error was sent once with the CLI and once with `pytest -m live`, with retries off.
A normal request (`claude-haiku-5-5`, `max_tokens = 16`) also returned 200 in both runs.

Why some errors are mock-only:

- **429 and 529**: causing them needs a lot of traffic. That costs money and adds load to a shared service. I will not do that.
- **413**: it needs a request body over 32 MB.
- **500, 504**: I cannot cause them on purpose.
- **402, 403, 409**: they depend on account billing or settings that I should not change for a test.
