# Case study (simulated): 403 permission_error for one key only

> **This is a simulated case. It was NOT reproduced with the real API.**
> Classification is checked by a mock test. The real cause depends on the account, so this case ends with questions, not a conclusion.
> The log below is hand-written from the official docs (see `../sources.md`). The request IDs are made up (`req_EXAMPLE...`).

## 1. Scenario
A new teammate's key fails with an error on a request that works with another key in the same company.

## 2. Log excerpt (made up, masked)

```text
HTTP 403 permission_error
request-id: req_EXAMPLE002
```

## 3. Cause (hypothesis based on the docs)
- Possible: the key belongs to a different workspace with other settings.
- Possible: an organization rule does not allow this action or resource.
- Not confirmed: which one. I need the workspace and the exact message.

## 4. Fix
1. Ask which workspace each key belongs to (do not ask for the key itself).
2. Compare organization and workspace settings in the Console.
3. Test one small request with a key from the working workspace.

## 5. Prevention
Document which workspace each key belongs to when keys are handed out.

## 6. What I learned
403 is not 401: the key is valid, but the action is not allowed. I should not tell the customer to make a new key before I know the workspace.

## 7. Example escalation report (short form)
- Goal: use the same request as a colleague.
- Facts: 403, one key only, request ID given.
- Hypothesis: workspace or organization settings.
- Ask: please check server-side permission logs for this request ID.
