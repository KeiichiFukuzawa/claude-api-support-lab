# Troubleshooting guide

One row per status code.
Read it from left to right: symptom → possible causes → how to check → fix → what to ask the customer.

Source: the official [Errors](https://platform.claude.com/docs/en/api/errors) and
[Rate limits](https://platform.claude.com/docs/en/api/rate-limits) pages, checked on 2026-10-14
(see [sources.md](sources.md)). The same advice is in `src/error_catalog.py`.

## Always collect these first

- The **request ID** (`request-id` header, starts with `req_`).
- The **time** of the error, with time zone.
- The **model name** in the request.
- A **request summary** without the prompt text: endpoint, `max_tokens`, number of messages, SDK and version.
- **How often** it happens: one time, sometimes, or every time.

Never ask for the full API key. Never ask for the prompt text unless it is truly needed.

## Client errors (4xx)

| Status | Symptom | Possible causes | How to check | Fix | Ask the customer |
|---|---|---|---|---|---|
| **400** `invalid_request_error` | Every request fails at once. Same error each time. | A required field is missing or wrong (`model`, `max_tokens`, `messages`). A parameter is not supported by the model. Invalid JSON. | Read `error.message`. It usually names the field. Compare the body with the Messages API reference. | Fix the named field. Remove parameters that the model does not support. | Request ID, model, request body without the prompt text, SDK and version. |
| **400** (spend limit you set) | Requests stop with a message that starts "You have reached your specified ... usage limits". | The organization or a workspace reached a spend limit that the customer set. | Read the message. It says when access resumes. Check Settings > Billing. | Raise or remove the spend limit. | Did someone set or change a spend limit recently? |
| **401** `authentication_error` | Every request fails. Often right after setup or a deploy. | Key missing, mistyped, has extra spaces or a line break, revoked, or expired. Key is read from the wrong place. | Check that `ANTHROPIC_API_KEY` is set in the same process. Check the key status in the Console. | Set the correct key. Create a new key if needed. | Where the key is stored. Did it work before? When did it stop? Last 4 characters only, if needed. |
| **402** `billing_error` | Requests fail with a billing message. | Payment details have a problem. | Check Settings > Billing in the Console (or AWS Marketplace). | Update the payment details. | Did the payment method change or expire? |
| **403** `permission_error` | Some requests fail, others work. | The key has no permission for this resource. Workspace or organization settings block it. An access rule (for example, region) blocks it. | Read `error.message`. Check which workspace the key belongs to. Check organization settings. | Change the access settings, or use a key from the right workspace. | Which workspace the key is in. Did it work before? |
| **404** `not_found_error` | Fails every time for one model or URL. | Model name typo or wrong format. Retired model. Model not available to the organization. Wrong endpoint path. | Compare the model name with the Models overview page. Call `GET /v1/models`. Check the URL path. | Use an exact current model ID. Fix the path. | The full endpoint URL. Where the model name comes from (code, config, env var). |
| **409** `conflict_error` | Fails when two requests change the same thing. | The resource was changed at the same time. A unique value is already used. | Read `error.message`. Look for parallel requests. | Resolve the conflict, then retry. | Endpoint and resource ID. |
| **413** `request_too_large` | Fails only for big requests (large files or long history). | The body is over the limit (32 MB for the Messages API). Large base64 images or PDFs. | Measure the body size in bytes. Note: Cloudflare returns this before the API, so there may be **no request ID**. | Make the request smaller: resize images, split documents, shorten history. | Approximate body size. Number and size of files. Time of the error. |
| **429** `rate_limit_error` | Fails under load. Works again after a short wait. | Over RPM, input tokens per minute, or output tokens per minute. A sudden traffic jump (acceleration limits). A low workspace limit. | Read `retry-after`. Read `anthropic-ratelimit-*` headers to find the limit at 0. Check the Limits page. | Wait `retry-after` seconds. Retry with backoff. Spread traffic. Request a higher tier if needed. | `retry-after` and `anthropic-ratelimit-*` headers. Requests per minute. Retry logic. |
| **429** (monthly spend cap) | All requests fail. Waiting does not help. | The organization reached its tier's monthly spend cap. | `error.details.error_code` is `enforced_spend_limit_reached`. There is **no** `retry-after`. The message says when access resumes. | Request a higher tier, or wait until the date in the message. | Do they need access before that date? |

## Server errors (5xx and 529)

| Status | Symptom | Possible causes | How to check | Fix | Ask the customer |
|---|---|---|---|---|---|
| **500** `api_error` | Random failures. The same request may work on retry. | An unexpected error inside Anthropic's systems. | Check the status page. Count how many requests fail. | Retry with exponential backoff. Escalate if it continues. | Several request IDs and times. How often it happens. |
| **504** `timeout_error` | Long requests fail. Short requests work. | Processing took too long. Large `max_tokens` without streaming. | Check if streaming is used. Check `max_tokens`. | Use streaming or the Message Batches API for long requests. | `max_tokens` value. Do they use streaming? |
| **529** `overloaded_error` | Many users see failures at the same time. | High traffic across all users. | Check the status page. | Retry with exponential backoff. Escalate if it lasts long. | How long it lasted. How many requests failed. Request IDs. |

## No HTTP status

| Case | Symptom | Possible causes | How to check | Fix | Ask the customer |
|---|---|---|---|---|---|
| Connection error | The client cannot reach the API. No status, no request ID. | Proxy, firewall, VPN, or DNS problem. Connection closed early. | Try to reach `api.anthropic.com` from the same machine. Check proxy settings. | Fix the network path. | Full error text (without the key). Network setup. |
| Client timeout | The client gives up before a response. | Client timeout too short. Slow network. | Check the client timeout and `max_tokens`. | Raise the timeout. Use streaming for long outputs. | Timeout value. `max_tokens`. |

## Notes about retries

- The official SDK retries some errors automatically: connection errors, 408, 409, 429, and 5xx. It retries **twice** by default.
- So "one failure" in the customer's app may be **three** real requests. Keep this in mind when you count errors.
- `src/diagnose.py` turns retries off (`max_retries=0`) to see the first response clearly.
