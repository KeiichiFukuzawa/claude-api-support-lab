# Case studies

One file per error that I **reproduced with the real API**.
I do not write a case study for an error that I did not reproduce.

## Status

| Error | How it is verified | Case study |
|---|---|---|
| 401 authentication_error | Planned: live (fake key) | Not yet. Live tests have not been run. |
| 404 not_found_error | Planned: live (model that does not exist) | Not yet. Live tests have not been run. |
| 400 invalid_request_error | Planned: live (`max_tokens = -1`) | Not yet. Live tests have not been run. |
| 402, 403, 409, 413, 429, 500, 504, 529 | Mock tests only (`tests/test_classify.py`) | None. These were **not** reproduced with the real API. |

Why some errors are mock-only:

- **429 and 529**: causing them needs a lot of traffic. That costs money and adds load to a shared service. I will not do that.
- **413**: it needs a request body over 32 MB.
- **500, 504**: I cannot cause them on purpose.
- **402, 403, 409**: they depend on account billing or settings that I should not change for a test.
