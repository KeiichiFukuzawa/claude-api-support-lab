# Case studies

Two kinds of files:

- **Live (01–03)**: errors that I **reproduced with the real API**.
- **Simulated (04–06)**: hand-written from the official docs, with made-up request IDs. They are **not** reproductions. Each file says so on its first lines.

I never call a simulated case a reproduction.

## Status

| Error | How it is verified | Case study |
|---|---|---|
| 401 authentication_error | Live, 2026-10-18 (fake key) | [01-401-authentication-error.md](01-401-authentication-error.md) |
| 404 not_found_error | Live, 2026-10-18 (model that does not exist) | [02-404-model-not-found.md](02-404-model-not-found.md) |
| 400 invalid_request_error | Live, 2026-10-18 (`max_tokens = -1`) | [03-400-invalid-max-tokens.md](03-400-invalid-max-tokens.md) |
| 429 rate limit | **Simulated** (docs + mock classification) | [04-429-rate-limit-simulated.md](04-429-rate-limit-simulated.md) |
| 403 permission_error | **Simulated** | [05-403-permission-simulated.md](05-403-permission-simulated.md) |
| 529 overloaded_error | **Simulated** | [06-529-overloaded-simulated.md](06-529-overloaded-simulated.md) |
| 402, 409, 413, 500, 504 | Mock tests only (`tests/test_classify.py`) and `src/practice.py` | None. **Not** reproduced with the real API. |

Each live error was sent once with the CLI and once with `pytest -m live`, with retries off.
A normal request (`claude-haiku-5-5`, `max_tokens = 16`) also returned 200 in both runs.

Why some errors are mock-only:

- **429 and 529**: causing them needs a lot of traffic. That costs money and adds load to a shared service. I will not do that.
- **413**: it needs a request body over 32 MB.
- **500, 504**: I cannot cause them on purpose.
- **402, 403, 409**: they depend on account billing or settings that I should not change for a test.
