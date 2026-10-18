# Reply templates for customers

Short, polite replies with a clear next step.
Replace the parts in `<angle brackets>`.

Rules I follow in every reply:

- Thank the customer, then say what we found in one sentence.
- Give clear next steps, as a numbered list.
- Ask only for what we need. Never ask for the full API key.
- Say when we will reply next, if we are still working on it.

---

## 1. Authentication error (401)

**Subject:** Re: 401 authentication_error on the Claude API

Hi <name>,

Thank you for the details and the request ID.

The request was rejected because the API key was not accepted (`401 authentication_error`).
This usually means the key is missing, has a typo or an extra space, or was revoked.

Please try these steps:

1. Check that `ANTHROPIC_API_KEY` is set in the same environment that sends the request.
2. Check the key on the API keys page in the Claude Console. Make sure it is active.
3. If you are not sure, create a new key and test with one small request.

Please do not send us your API key. If we need to find the key, the last 4 characters are enough.

If it still fails, please reply with the new request ID and the time of the error (with time zone).

Best regards,
<your name>

---

## 2. Rate limit (429)

**Subject:** Re: 429 rate_limit_error during peak hours

Hi <name>,

Thank you for reporting this.

Your requests hit a rate limit (`429 rate_limit_error`).
This means your organization sent more requests or tokens per minute than your current limit allows.

Here is what we suggest:

1. Read the `retry-after` header in the error response. Wait that many seconds before you retry.
2. Use retries with exponential backoff. Avoid retrying many requests at the same time.
3. Spread traffic more evenly. A sudden jump in traffic can also cause 429 errors.
4. Check your current limits on the Limits page in the Claude Console. You can request a higher tier there.

If you still see 429 errors after these changes, please send us:

- 2 or 3 request IDs and their times (with time zone)
- the `retry-after` and `anthropic-ratelimit-*` headers from one failed response
- your approximate requests per minute at that time

Best regards,
<your name>

---

## 3. Invalid request (400)

**Subject:** Re: 400 invalid_request_error

Hi <name>,

Thank you for sending the request ID.

The API rejected the request because one of the parameters is not valid (`400 invalid_request_error`).
The error message says: "<error.message>".

To fix it:

1. Change `<field name>` to <valid value or range>.
2. Send the request again.

You can find the full list of parameters in the Messages API reference: https://platform.claude.com/docs/en/api/messages

If the error continues, please reply with the new request ID and the request body without the prompt text.

Best regards,
<your name>

---

## 4. Service incident (500 / 529)

**Subject:** Re: Errors from the Claude API

Hi <name>,

Thank you for your patience, and I am sorry for the trouble.

We are aware of elevated errors on the Claude API (`<500 api_error / 529 overloaded_error>`) that started at <time, time zone>.
Our engineers are working on it. You can follow updates on the status page: <status page URL>.

What you can do now:

1. Retry failed requests with exponential backoff.
2. Keep the request IDs and times of failed requests.
3. If a job can wait, pause it and run it again after the incident is resolved.

I will update you by <time, time zone>, or sooner if the status changes.
If you see errors after the incident is resolved, please reply with the request IDs and times.

Best regards,
<your name>
