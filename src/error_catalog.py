"""One shared table of Claude API errors.

diagnose.py (screen output), escalate.py (reports), and the tests all use this table,
so the advice stays the same everywhere.

Source: https://platform.claude.com/docs/en/api/errors and
https://platform.claude.com/docs/en/api/rate-limits (checked 2026-10-14, see docs/sources.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ErrorInfo:
    key: str
    status: int | None
    error_type: str | None
    title: str
    retryable: str  # "yes", "no", or a short note such as "yes, after retry-after"
    likely_causes: list[str] = field(default_factory=list)
    next_checks: list[str] = field(default_factory=list)
    ask_customer: list[str] = field(default_factory=list)


# Things we ask for in almost every case.
_BASIC_ASK = [
    "The request ID (request-id header, starts with req_).",
    "The time of the error, with time zone.",
    "The model name in the request.",
]

CATALOG: dict[str, ErrorInfo] = {
    "400": ErrorInfo(
        key="400",
        status=400,
        error_type="invalid_request_error",
        title="Invalid request",
        retryable="no (fix the request first)",
        likely_causes=[
            "A required field is missing or has a wrong value (model, max_tokens, messages).",
            "A parameter is not supported by this model (for example, a thinking or tool_choice setting).",
            "The request body is not valid JSON.",
            "A spend limit that the organization set itself was reached (the message starts with 'You have reached your specified').",
        ],
        next_checks=[
            "Read error.message. It usually names the bad field.",
            "Compare the request body with the Messages API reference.",
            "Check that the parameters are supported by the model in the request.",
            "If the message mentions usage limits, check Settings > Billing in the Console.",
        ],
        ask_customer=_BASIC_ASK + [
            "The request body without the prompt text (field names and values).",
            "The SDK name and version, if they use an SDK.",
        ],
    ),
    "400_spend_limit": ErrorInfo(
        key="400_spend_limit",
        status=400,
        error_type="invalid_request_error",
        title="Self-set spend limit reached",
        retryable="no (raise or remove the limit)",
        likely_causes=[
            "The organization or workspace reached a spend limit that the customer set.",
        ],
        next_checks=[
            "Read error.message. It says when access resumes.",
            "Check Settings > Billing in the Console (spend limits).",
            "Check workspace spend limits if the message says 'workspace'.",
        ],
        ask_customer=_BASIC_ASK + [
            "Did someone in the organization set or change a spend limit recently?",
        ],
    ),
    "401": ErrorInfo(
        key="401",
        status=401,
        error_type="authentication_error",
        title="Authentication failed",
        retryable="no (fix the key first)",
        likely_causes=[
            "The API key is missing, mistyped, or has extra spaces or line breaks.",
            "The API key was revoked, deleted, or has expired.",
            "The key is read from a different environment variable or file than expected.",
        ],
        next_checks=[
            "Check that ANTHROPIC_API_KEY is set in the same shell or process that sends the request.",
            "Check the key status in the Console (API keys page). Do not ask the customer to send the key.",
            "Create a new key and test with one small request.",
        ],
        ask_customer=_BASIC_ASK + [
            "Where the key is stored (environment variable, secret manager, config file).",
            "Did the key work before? When did it stop working?",
            "The last 4 characters of the key only, if needed to match it in the Console. Never the full key.",
        ],
    ),
    "402": ErrorInfo(
        key="402",
        status=402,
        error_type="billing_error",
        title="Billing problem",
        retryable="no (fix billing first)",
        likely_causes=[
            "There is a problem with the payment details or billing information.",
        ],
        next_checks=[
            "Check payment details in the Console (Settings > Billing).",
            "On Claude Platform on AWS, check AWS Marketplace.",
        ],
        ask_customer=_BASIC_ASK + [
            "Did the payment method change or expire recently?",
        ],
    ),
    "403": ErrorInfo(
        key="403",
        status=403,
        error_type="permission_error",
        title="Permission denied",
        retryable="no (fix access first)",
        likely_causes=[
            "The API key does not have permission for this resource.",
            "The organization or workspace settings do not allow this action.",
            "An access requirement (for example, a region rule) blocked the request.",
        ],
        next_checks=[
            "Read error.message. It often says what to do.",
            "Check the organization and workspace settings in the Console.",
            "Check which workspace the key belongs to.",
        ],
        ask_customer=_BASIC_ASK + [
            "Which workspace the key belongs to.",
            "Did this request work before with the same key?",
        ],
    ),
    "404": ErrorInfo(
        key="404",
        status=404,
        error_type="not_found_error",
        title="Not found",
        retryable="no (fix the model name or URL first)",
        likely_causes=[
            "The model name has a typo or uses a wrong format.",
            "The model was retired, or the organization cannot use it.",
            "The endpoint path or a resource ID in the URL is wrong.",
        ],
        next_checks=[
            "Compare the model name with the Models overview page, letter by letter.",
            "List the models the key can use (GET /v1/models).",
            "Check the endpoint path (for example, /v1/messages).",
        ],
        ask_customer=_BASIC_ASK + [
            "The full endpoint URL (no key, no prompt).",
            "Where the model name comes from (code, config, environment variable).",
        ],
    ),
    "409": ErrorInfo(
        key="409",
        status=409,
        error_type="conflict_error",
        title="Conflict",
        retryable="yes (after the conflict is resolved)",
        likely_causes=[
            "The resource was changed by another request at the same time.",
            "A value that must be unique is already in use.",
        ],
        next_checks=[
            "Read error.message to see which resource is in conflict.",
            "Check for parallel requests that change the same resource.",
        ],
        ask_customer=_BASIC_ASK + [
            "Which endpoint and resource ID were used.",
        ],
    ),
    "413": ErrorInfo(
        key="413",
        status=413,
        error_type="request_too_large",
        title="Request too large",
        retryable="no (make the request smaller)",
        likely_causes=[
            "The request body is larger than the limit (32 MB for the Messages API).",
            "Large images or documents are sent as base64 in the body.",
        ],
        next_checks=[
            "Check the size of the request body in bytes.",
            "Check for large base64 images or PDFs.",
            "Note: Cloudflare returns this error before the API, so a request ID may be missing.",
        ],
        ask_customer=[
            "The time of the error, with time zone.",
            "The approximate size of the request body, and the number and size of attached files.",
            "The request ID, if there is one (it may be missing for 413).",
        ],
    ),
    "429": ErrorInfo(
        key="429",
        status=429,
        error_type="rate_limit_error",
        title="Rate limit reached",
        retryable="yes, after the retry-after time",
        likely_causes=[
            "Too many requests or tokens per minute for the organization's tier (RPM, ITPM, OTPM).",
            "A sharp increase in traffic hit acceleration limits.",
            "A workspace rate limit is lower than the organization limit.",
        ],
        next_checks=[
            "Read the retry-after header and wait that many seconds before retrying.",
            "Read the anthropic-ratelimit-* headers to see which limit is at 0.",
            "Check the Limits page in the Console for the tier and current limits.",
            "Check if the client retries too fast or sends many requests at once.",
        ],
        ask_customer=_BASIC_ASK + [
            "The retry-after and anthropic-ratelimit-* response headers.",
            "How many requests per minute they send, and if traffic grew suddenly.",
            "Their retry logic (how long they wait between retries).",
        ],
    ),
    "429_spend_cap": ErrorInfo(
        key="429_spend_cap",
        status=429,
        error_type="rate_limit_error",
        title="Monthly spend cap reached",
        retryable="no (retrying will not help until access resumes)",
        likely_causes=[
            "The organization reached the monthly spend cap of its usage tier.",
        ],
        next_checks=[
            "Confirm error.details.error_code is enforced_spend_limit_reached.",
            "Confirm there is no retry-after header.",
            "Read error.message. It says when access resumes.",
            "Check Settings > Billing and the Limits page in the Console.",
        ],
        ask_customer=_BASIC_ASK + [
            "Do they need access before the date in the message? (They can request a higher tier.)",
        ],
    ),
    "500": ErrorInfo(
        key="500",
        status=500,
        error_type="api_error",
        title="Internal server error",
        retryable="yes, with exponential backoff",
        likely_causes=[
            "An unexpected error inside Anthropic's systems.",
        ],
        next_checks=[
            "Retry with exponential backoff.",
            "Check the status page for an incident.",
            "If it keeps happening, escalate with the request IDs and times.",
        ],
        ask_customer=_BASIC_ASK + [
            "How often it happens (one time, or many times).",
            "Several request IDs, if it happened more than once.",
        ],
    ),
    "504": ErrorInfo(
        key="504",
        status=504,
        error_type="timeout_error",
        title="Request timed out",
        retryable="yes (consider streaming)",
        likely_causes=[
            "The request took too long to process.",
            "A large max_tokens value without streaming.",
        ],
        next_checks=[
            "Check if the request uses streaming.",
            "Check max_tokens and the expected output length.",
            "Consider the streaming Messages API or the Message Batches API.",
        ],
        ask_customer=_BASIC_ASK + [
            "The max_tokens value and if they use streaming.",
        ],
    ),
    "529": ErrorInfo(
        key="529",
        status=529,
        error_type="overloaded_error",
        title="API overloaded",
        retryable="yes, with exponential backoff",
        likely_causes=[
            "The API has high traffic across all users.",
        ],
        next_checks=[
            "Retry with exponential backoff.",
            "Check the status page.",
            "If it lasts a long time, collect request IDs and times and escalate.",
        ],
        ask_customer=_BASIC_ASK + [
            "How long it has lasted and how many requests failed.",
        ],
    ),
    "connection": ErrorInfo(
        key="connection",
        status=None,
        error_type=None,
        title="Could not connect to the API",
        retryable="yes",
        likely_causes=[
            "A network, proxy, firewall, or DNS problem on the client side.",
            "The connection was closed before a response came back.",
        ],
        next_checks=[
            "Check that api.anthropic.com is reachable from the same machine.",
            "Check proxy and firewall settings.",
            "Note: there is no HTTP status and no request ID, because no response came back.",
        ],
        ask_customer=[
            "The time of the error, with time zone.",
            "The full error text from the client (with the key removed).",
            "Network setup: proxy, VPN, corporate firewall.",
        ],
    ),
    "timeout": ErrorInfo(
        key="timeout",
        status=None,
        error_type=None,
        title="Client-side timeout",
        retryable="yes",
        likely_causes=[
            "The client timeout is shorter than the time the request needs.",
            "A slow or unstable network.",
        ],
        next_checks=[
            "Check the client timeout setting.",
            "Consider streaming for long outputs.",
        ],
        ask_customer=[
            "The time of the error, with time zone.",
            "The client timeout value and max_tokens.",
        ],
    ),
    "unknown": ErrorInfo(
        key="unknown",
        status=None,
        error_type=None,
        title="Unknown error",
        retryable="unknown",
        likely_causes=[
            "This status code is not in our table. The API can add new error types.",
        ],
        next_checks=[
            "Read error.type and error.message.",
            "Check the Errors page in the docs for new codes.",
        ],
        ask_customer=_BASIC_ASK,
    ),
}


def classify(
    status: int | None,
    *,
    message: str | None = None,
    error_code: str | None = None,
    transport_error: str | None = None,
) -> ErrorInfo:
    """Pick the table entry for one failed request.

    status: HTTP status code, or None when no response came back.
    message: error.message from the body (used to find special 400 cases).
    error_code: error.details.error_code from the body (used to find the spend cap 429).
    transport_error: "connection" or "timeout" when there is no HTTP response.
    """
    if status is None:
        return CATALOG.get(transport_error or "connection", CATALOG["connection"])

    if status == 429 and error_code == "enforced_spend_limit_reached":
        return CATALOG["429_spend_cap"]

    if status == 400 and message and message.startswith("You have reached your specified"):
        return CATALOG["400_spend_limit"]

    return CATALOG.get(str(status), CATALOG["unknown"])
