# Sources

I checked these official pages before I wrote the code and the docs.
I did not rely on memory for error codes, model names, rate limits, headers, or SDK behavior.

- Checked on: 2026-10-14
- Note: `docs.claude.com` now redirects to `platform.claude.com`. The URLs below are the pages I actually read.

## Pages and what I took from them

| Page | URL | What I used |
|---|---|---|
| Errors | https://platform.claude.com/docs/en/api/errors | Status code list (400, 401, 402, 403, 404, 409, 413, 429, 500, 504, 529). Error body shape (`type`, `error.type`, `error.message`, `request_id`). The `request-id` header. The SDK retries twice by default. 413 comes from Cloudflare before the request reaches the API. 32 MB limit for the Messages API. |
| Rate limits | https://platform.claude.com/docs/en/api/rate-limits | `retry-after` and `anthropic-ratelimit-*` headers. A spend-cap 429 has no `retry-after` and has `error.details.error_code = enforced_spend_limit_reached`. A spend limit that you set yourself returns 400, not 429. Acceleration limits can cause 429. |
| API overview | https://platform.claude.com/docs/en/api/overview | Response headers: `request-id`, `anthropic-organization-id`, `anthropic-workspace-id`. `anthropic-workspace-id` is absent when the request fails before authentication completes. |
| Versions | https://platform.claude.com/docs/en/api/versioning | The `anthropic-version` header. The SDK sends `2023-06-01`. Error `type` values can grow over time. |
| Models overview | https://platform.claude.com/docs/en/about-claude/models/overview | Current model IDs. The smallest current model is Claude Haiku 5.5 (`claude-haiku-5-5`). |
| Pricing | https://platform.claude.com/docs/en/about-claude/pricing | Claude Haiku 5.5: $0.10 per million input tokens and $0.50 per million output tokens (prompts up to 100,000 tokens). |
| Messages API reference | https://platform.claude.com/docs/en/api/messages | Required body fields (`model`, `max_tokens`, `messages`). `max_tokens` has a minimum of 0, so a negative value is invalid. |
| Python SDK | https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python | Exception classes per status code. `max_retries` (default 2, set 0 to disable). Retried errors: connection errors, 408, 409, 429, and >=500. Timeout default is 10 minutes. The SDK uses `httpx2`. Custom `http_client` for tests. |

## Things I checked in the installed SDK (anthropic 1.13.0)

The docs page lists the main exception classes. I also read the installed SDK code to confirm some details:

- `APIStatusError` has `status_code`, `request_id` (from the `request-id` header), `type` (from `error.type` in the body), `body`, and `response`.
- The SDK maps 413 to `RequestTooLargeError` and 529 to `OverloadedError`. Other 5xx codes map to `InternalServerError`.
- The SDK also reads an `x-should-retry` response header when it decides to retry.

## What I did not find in the docs

- I did not find a sentence that says "failed requests are not billed".
  The pricing page bills per input and output token.
  A request that the API rejects before the model runs should use no tokens.
  This is my assumption. I will check the Usage page in the Claude Console after the live tests.
