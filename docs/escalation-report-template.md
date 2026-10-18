# Escalation report template

Use this template when you send a Claude API problem to engineers.
`python -m src.escalate` fills in most of it from a diagnose log.
You fill in the parts marked TODO.

## Writing rules

1. **Keep facts and guesses apart.**
   Facts go in "Facts". Guesses go in "Likely cause". Write "hypothesis" next to a guess.
2. **Write the steps to reproduce as a numbered list.**
   One action per step. Write the exact command or request. Write the expected result.
3. **Answer the next question before it is asked.**
   Include the request ID, the time with time zone, the model name, the endpoint, and the SDK version.
   The engineer should not need to come back to you for basic facts.
4. **Never include secrets or personal data.**
   No API keys (not even part of a key in the body text), no prompt text, no customer names or emails.
   Describe the prompt by its size only (for example, "1 user message, 23 characters").
5. **Say what you already checked.**
   This saves time. Engineers will not repeat the same checks.
6. **Ask for one clear thing.**
   For example: "Please check the server logs for this request ID and tell us why it returned 500."
7. **Write the impact in numbers when you can.**
   For example: "About 30% of requests failed for 2 hours. A batch job for 5,000 tickets stopped."

## Template

```markdown
# Escalation report: <category> (<HTTP status>)

## 1. Summary
<One or two sentences. What failed, when, and how.>

## 2. What the customer tried to do
<The goal in plain words. Example: "Classify support tickets with a small model.">

## 3. Facts (from the log)
| Item | Value |
|---|---|
| HTTP status | <for example, 404 (not_found_error)> |
| Error type | <error.type> |
| Error message | <error.message> |
| Error code | <error.details.error_code, if any> |
| Request ID | <req_...> |
| Model | <model ID in the request> |
| Time (UTC) | <YYYY-MM-DDTHH:MM:SSZ> |
| Endpoint | <POST /v1/messages> |
| max_tokens | <value> |
| SDK | <name and version> |

Response headers we kept:
- <request-id, retry-after, anthropic-ratelimit-* ...>

## 4. Steps to reproduce
1. <Setup step>
2. <The exact command or request>
3. <Expected result>

## 5. What we already checked
- <Check 1 and its result>
- <Check 2 and its result>

## 6. Likely cause (hypothesis, not confirmed)
- <Hypothesis 1>
- <Hypothesis 2>

## 7. Customer impact
<Who is affected, how many requests, since when, business impact.>

## 8. What we need from engineering
<One clear request.>

## 9. Reporter
<Name or team.>
```

## Before you send it

- [ ] The request ID is there (or the report says why it is missing, for example 413 or a connection error).
- [ ] The time has a time zone.
- [ ] Facts and hypotheses are in separate sections.
- [ ] The steps to reproduce are numbered and have an expected result.
- [ ] No API key, no prompt text, no personal data.
- [ ] There are no TODO lines left.
