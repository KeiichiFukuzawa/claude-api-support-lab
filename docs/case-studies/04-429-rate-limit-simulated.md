# Case study (simulated): 429 rate_limit_error after a traffic jump

> **This is a simulated case. It was NOT reproduced with the real API.**
> Classification of this case is checked by a mock test (`tests/test_classify.py`) and by `python -m src.practice --case 429-burst`.
> The log below is hand-written from the official docs (see `../sources.md`). The request IDs are made up (`req_EXAMPLE...`).

## 1. Scenario
A customer starts 200 parallel requests and many fail a few seconds later. Before that, they sent about 10 requests per minute.

## 2. Log excerpt (made up, masked)

```text
HTTP 429 rate_limit_error
retry-after: 12
anthropic-ratelimit-requests-remaining: 0
request-id: req_EXAMPLE007
```

## 3. Cause (hypothesis based on the docs)
- `retry-after` is present, so this is a normal rate limit, not the monthly spend cap.
- `requests-remaining: 0` points to the requests-per-minute limit. A sharp increase can also hit acceleration limits.
- Not confirmed: the customer's real tier and limits (check the Limits page).

## 4. Fix
1. Wait for `retry-after` seconds before retrying, with exponential backoff and jitter.
2. Limit parallel requests (a queue or a worker pool).
3. Raise traffic slowly, not all at once.

## 5. Prevention
Read `anthropic-ratelimit-*` headers and slow down before the limit is at 0. Ask the customer about their retry logic.

## 6. What I learned
429 has two kinds. Without `retry-after` and with `enforced_spend_limit_reached`, waiting does not help (see `../troubleshooting.md`). I must check headers before I give advice.

## 7. Example escalation report (short form)
- Goal: classify support tickets in a batch.
- Facts: 429, `retry-after: 12`, requests-remaining 0.
- Hypothesis: RPM limit or acceleration limit.
- Ask: please confirm the tier limits for this organization.
