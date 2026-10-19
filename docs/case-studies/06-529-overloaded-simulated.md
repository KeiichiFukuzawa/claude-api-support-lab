# Case study (simulated): 529 overloaded_error in the afternoon

> **This is a simulated case. It was NOT reproduced with the real API.**
> Classification is checked by a mock test. I never cause 529 on purpose.
> The log below is hand-written from the official docs (see `../sources.md`). The request IDs are made up (`req_EXAMPLE...`).

## 1. Scenario
Many requests fail with `overloaded` for several hours. The customer did not change their code.

## 2. Log excerpt (made up, masked)

```text
HTTP 529 overloaded_error
request-id: req_EXAMPLE011
```

## 3. Cause (hypothesis based on the docs)
- The API has high traffic across all users. This is not caused by the customer's key or code.
- Not confirmed: whether there is an incident (check the status page).

## 4. Fix
1. Retry with exponential backoff.
2. Check the status page.
3. If it lasts a long time, collect several request IDs with times and escalate.

## 5. Prevention
Keep retries limited and add a fallback or queue so the customer's service does not stop.

## 6. What I learned
I should not blame the customer for 529, and I should not promise when it will end.

## 7. Example escalation report (short form)
- Goal: normal production calls.
- Facts: 529 for N requests, times in UTC, several request IDs.
- Hypothesis: high load on the API.
- Ask: please confirm if there is a known incident.
