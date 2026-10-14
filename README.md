# claude-api-support-lab

A small lab for Claude API support work: **find the cause of an API error, write it down, and escalate it well.**

> This is a personal learning project. It is **not** a replacement for real support experience.

## Purpose

I made this repository for my application to a Product Support Specialist role at Anthropic.
It shows how I:

1. **Isolate** an API error: status code, error type, request ID, likely cause, next check.
2. **Document** it: a troubleshooting guide, case studies, and customer reply templates.
3. **Escalate** it: a report that an engineer can act on without asking basic questions.

## What is inside

| Path | What it is |
|---|---|
| `src/diagnose.py` | CLI. Sends one small Messages API request, explains the result, and writes a JSON Lines log. |
| `src/escalate.py` | CLI. Turns one log record into an escalation report (Markdown). |
| `src/error_catalog.py` | One shared table of errors: likely causes, next checks, what to ask the customer. |
| `src/redact.py` | Hides API keys. Keeps only the length of the prompt. |
| `tests/` | Mock tests (default) and live tests (opt-in). |
| `docs/troubleshooting.md` | Status code table: symptom → causes → checks → fix → what to ask. |
| `docs/escalation-report-template.md` | Report template and writing rules. |
| `docs/reply-templates.md` | Customer reply samples (401, 429, 400, incident). |
| `docs/case-studies/` | Errors that I reproduced with the real API. |
| `docs/sources.md` | The official docs I checked, with URLs. |
| `docs/pre-publish-checklist.md` | How to check for keys and personal data before publishing. |
| `docs/interview-notes.md` | Short facts about this project for interviews. |

## Setup

You need Python 3.11 or newer.

```bash
git clone https://github.com/KeiichiFukuzawa/claude-api-support-lab.git
cd claude-api-support-lab
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Set your API key. Choose one way:

```bash
# Way 1: set it in your shell
export ANTHROPIC_API_KEY="your key here"

# Way 2: use a .env file (it is in .gitignore)
cp .env.example .env        # then put your key in .env
set -a; source .env; set +a
```

Never put the key in code, logs, or commits.

## Usage

### 1. Diagnose one request

```bash
python -m src.diagnose                         # one small valid request
python -m src.diagnose --scenario bad-key      # reproduce 401 (uses a fake key)
python -m src.diagnose --scenario bad-model    # reproduce 404
python -m src.diagnose --scenario bad-param    # reproduce 400 (max_tokens = -1)
python -m src.diagnose --model claude-haiku-5-5 --max-tokens 16
python -m src.diagnose --json                  # print the log record as JSON
```

The default model is `claude-haiku-5-5`, the smallest current model. The default `max_tokens` is 16.
Each run writes one line to `logs/diagnose-YYYY-MM-DD.jsonl`.

Example output. **This comes from a mock test, not from a real API call:**

```text
============================================================
Scenario    : normal
Request     : POST /v1/messages model=claude-haiku-5-5 max_tokens=16 prompt_chars=23
Time (UTC)  : 2026-10-14T16:43:04Z
Result      : ERROR
HTTP status : 429 (rate_limit_error)
Request ID  : req_test429
Message     : Number of request tokens has exceeded your per-minute rate limit
Category    : Rate limit reached
Retry?      : yes, after the retry-after time

Likely causes:
  - Too many requests or tokens per minute for the organization's tier (RPM, ITPM, OTPM).
  - A sharp increase in traffic hit acceleration limits.
  - A workspace rate limit is lower than the organization limit.

Next checks:
  1. Read the retry-after header and wait that many seconds before retrying.
  2. Read the anthropic-ratelimit-* headers to see which limit is at 0.
  3. Check the Limits page in the Console for the tier and current limits.
  4. Check if the client retries too fast or sends many requests at once.

Rate limit headers:
  retry-after: 12 -> wait 12 seconds before you retry.
  anthropic-ratelimit-requests-limit: 50
  anthropic-ratelimit-requests-remaining: 0   <- at zero
============================================================
```

Exit codes: `0` success, `1` API error, `2` setup problem (for example, no API key).

### 2. Make an escalation report

```bash
python -m src.escalate                                   # latest failure in logs/
python -m src.escalate --request-id req_011C...          # pick one record
python -m src.escalate \
  --goal "Classify support tickets with a small model" \
  --impact "Batch job stopped for 2 hours" \
  --checked "Status page showed no incident" \
  --ask "Please check server logs for this request ID" \
  --out reports/case.md
```

Facts (status, request ID, time, model, steps to reproduce) come from the log.
Things only a person knows come from the options. Missing parts show `TODO`.

### 3. Run the tests

```bash
pytest              # mock tests only. No API calls, no cost.
pytest -m live -v   # live tests. Real API calls. See below first.
```

Live tests send 4 requests, one each, with retries off:

| Test | Request | Expected |
|---|---|---|
| bad key | fake key | 401 |
| bad model | model that does not exist | 404 |
| bad param | `max_tokens = -1` | 400 |
| normal | `claude-haiku-5-5`, `max_tokens = 16` | 200 |

Only the normal request should create a charge, and it is very small.
Claude Haiku 5.5 costs $0.10 per million input tokens and $0.50 per million output tokens.
I did not find a sentence in the docs that says failed requests are free. See `docs/sources.md`.

## Design decisions

- **Retries are off in `diagnose.py`.** The SDK retries 429 and 5xx twice by default. Turning retries off shows the first response and sends no extra requests.
- **One shared error table.** The screen, the reports, and the tests all read `src/error_catalog.py`. The advice cannot drift apart.
- **Two kinds of 429.** A normal rate limit has `retry-after`. A monthly spend cap has no `retry-after` and has `error_code = enforced_spend_limit_reached`. Waiting does not fix the second one, so the tool says so.
- **413 may have no request ID.** Cloudflare returns 413 before the API. The tool and the report handle a missing request ID.
- **Keep only useful headers.** Logs keep `request-id`, `retry-after`, `x-should-retry`, `cf-ray`, and `anthropic-ratelimit-*`. They do not keep organization or workspace IDs.
- **Hide secrets twice.** Records are redacted before they are printed or saved. Reports are redacted again at the end.
- **Facts and guesses are apart.** Reports have a "Facts" section and a "Likely cause (hypothesis)" section.
- **No load on purpose.** 429 and 529 are tested with mocks. I never send many requests to cause them.
- **Docs first.** Error codes, headers, model IDs, and SDK behavior come from the official docs, not memory. See `docs/sources.md`.

## Limitations

- **This is a personal learning project. It is not a replacement for real support experience.**
- It covers the Messages API without streaming. Errors that arrive in the middle of a stream (SSE) are not covered.
- It covers the Claude API only. Amazon Bedrock, Google Cloud, and Microsoft Foundry are not covered.
- The error table is based on the docs as of 2026-10-14. The API can add new error types.
- Only some errors can be reproduced safely with the real API. The others are tested with mocks. `docs/case-studies/README.md` shows which is which.

## Security notes

- The API key is read only from the `ANTHROPIC_API_KEY` environment variable.
- `.env`, `logs/`, and `reports/` are in `.gitignore`.
- Logs and reports never include the API key or the prompt text. The prompt is described by its length only.
- Before publishing, follow `docs/pre-publish-checklist.md`.
- If a key ever leaks, revoke it in the Claude Console first.

---

## 日本語の要約

Claude API のサポート業務を想定した、個人の学習用リポジトリです。
API エラーの「切り分け」「文書化」「エスカレーション」の力を示すために作りました。

- `src/diagnose.py`: API に小さなリクエストを1回だけ送ります。エラーの分類、想定原因、次に確認すること、request-id を表示し、ログに残します。キーとプロンプト本文は残しません。
- `src/escalate.py`: ログから、エンジニア向けのエスカレーション報告書を作ります。事実と推測は分けて書きます。
- テスト: 通常はモックだけで動きます(費用なし)。実 API を使うテストは `pytest -m live` のときだけ動きます。
- 429 と 529 は、大量のリクエストで起こすことはしません。モックで検証しています。
- **実務のサポート経験の代わりになるものではありません。**
