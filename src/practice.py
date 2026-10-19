"""Offline practice mode: read a ticket and log excerpt, guess the category, then check.

No API calls, no key, no cost. Answers come from the shared table in error_catalog.py.

Usage examples:
    python -m src.practice                  # one random case, interactive
    python -m src.practice --seed 3         # same case every time
    python -m src.practice --list           # show all case IDs
    python -m src.practice --case 429-burst # pick one case
    python -m src.practice --lang en        # English only (default: ja+en)
    python -m src.practice --show           # show the answer at once (no quiz)

These cases are written by me for practice. They are not real customer cases and
were not reproduced with the real API.
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass

from src.error_catalog import CATALOG, ErrorInfo, classify


@dataclass(frozen=True)
class Case:
    case_id: str
    key: str  # expected key in CATALOG
    ticket_en: str
    ticket_ja: str
    log: str  # masked log excerpt
    status: int | None = None
    message: str | None = None
    error_code: str | None = None
    transport_error: str | None = None


CASES: list[Case] = [
    Case(
        "401-newkey", "401",
        "My script worked yesterday. Today every call fails. I did not change the code.",
        "昨日まで動いていたスクリプトが、今日は全部失敗します。コードは変えていません。",
        "HTTP 401 authentication_error\nmessage: invalid x-api-key\nrequest-id: req_EXAMPLE001",
        status=401,
    ),
    Case(
        "403-workspace", "403",
        "Our new teammate's key gets an error on the same request that works for me.",
        "新しいメンバーのキーだけ、私と同じリクエストでエラーになります。",
        "HTTP 403 permission_error\nmessage: (permission denied)\nrequest-id: req_EXAMPLE002",
        status=403,
    ),
    Case(
        "404-model", "404",
        "After I copied the model name from a blog post, I get an error.",
        "ブログからモデル名をコピーしたら、エラーが出るようになりました。",
        "HTTP 404 not_found_error\nmessage: model: (name from the blog)\nrequest-id: req_EXAMPLE003",
        status=404,
    ),
    Case(
        "400-param", "400",
        "The request fails right away. I only changed max_tokens.",
        "リクエストがすぐ失敗します。変えたのは max_tokens だけです。",
        "HTTP 400 invalid_request_error\nmessage: max_tokens: must be greater than or equal to 0\nrequest-id: req_EXAMPLE004",
        status=400,
        message="max_tokens: must be greater than or equal to 0",
    ),
    Case(
        "400-selflimit", "400_spend_limit",
        "Everything stopped at the same time. We had no outage notice from you.",
        "全部が同時に止まりました。障害のお知らせは出ていませんよね？",
        "HTTP 400 invalid_request_error\nmessage: You have reached your specified ... usage limits.\nrequest-id: req_EXAMPLE005",
        status=400,
        message="You have reached your specified workspace API usage limits.",
    ),
    Case(
        "402-billing", "402",
        "Our card was renewed last week. Since then the API stops.",
        "先週カードを更新しました。それ以降、APIが止まります。",
        "HTTP 402 billing_error\nrequest-id: req_EXAMPLE006",
        status=402,
    ),
    Case(
        "413-pdf", "413",
        "Uploading a big PDF fails. Smaller files are fine.",
        "大きいPDFだけアップロードに失敗します。小さいファイルは大丈夫です。",
        "HTTP 413 request_too_large\nrequest-id: (none)",
        status=413,
    ),
    Case(
        "429-burst", "429",
        "We started a batch of 200 parallel requests and many fail after a few seconds.",
        "並列200件のバッチを始めたら、数秒後から多くが失敗します。",
        "HTTP 429 rate_limit_error\nretry-after: 12\nanthropic-ratelimit-requests-remaining: 0\nrequest-id: req_EXAMPLE007",
        status=429,
    ),
    Case(
        "429-cap", "429_spend_cap",
        "We get 429, but waiting and retrying never helps. There is no retry-after.",
        "429が出ますが、待って再試行しても直りません。retry-afterもありません。",
        "HTTP 429 rate_limit_error\nerror_code: enforced_spend_limit_reached\n(no retry-after)\nrequest-id: req_EXAMPLE008",
        status=429,
        error_code="enforced_spend_limit_reached",
    ),
    Case(
        "500-once", "500",
        "One request failed with an internal error. The same request worked a minute later.",
        "1件だけ内部エラーになりました。1分後に同じリクエストは通りました。",
        "HTTP 500 api_error\nrequest-id: req_EXAMPLE009",
        status=500,
    ),
    Case(
        "504-long", "504",
        "Long summaries time out. max_tokens is 60000 and streaming is off.",
        "長い要約だけタイムアウトします。max_tokensは60000で、ストリーミングはオフです。",
        "HTTP 504 timeout_error\nrequest-id: req_EXAMPLE010",
        status=504,
    ),
    Case(
        "529-peak", "529",
        "Many requests fail with 'overloaded' this afternoon. Our code did not change.",
        "午後から 'overloaded' で多くが失敗します。コードは変えていません。",
        "HTTP 529 overloaded_error\nrequest-id: req_EXAMPLE011",
        status=529,
    ),
    Case(
        "net-proxy", "connection",
        "It only fails from our office network. It works from home.",
        "社内ネットワークからだけ失敗します。自宅では動きます。",
        "No HTTP response\nclient error: connection error\nrequest-id: (none)",
        transport_error="connection",
    ),
]

CASE_BY_ID = {c.case_id: c for c in CASES}


def expected_info(case: Case) -> ErrorInfo:
    """The catalog entry for a case. Uses the same classify() as the real tool."""
    return classify(
        case.status,
        message=case.message,
        error_code=case.error_code,
        transport_error=case.transport_error,
    )


def pick_case(seed: int | None = None, case_id: str | None = None) -> Case:
    if case_id:
        if case_id not in CASE_BY_ID:
            raise KeyError(f"Unknown case: {case_id}. Use --list.")
        return CASE_BY_ID[case_id]
    return random.Random(seed).choice(CASES)


def category_choices(case: Case, seed: int | None = None, n: int = 4) -> list[ErrorInfo]:
    """The right category plus n-1 others, in a stable order for one seed."""
    rng = random.Random(f"{seed}-{case.case_id}")
    right = expected_info(case)
    others = [i for k, i in CATALOG.items() if k not in (right.key, "unknown")]
    picks = rng.sample(others, n - 1) + [right]
    rng.shuffle(picks)
    return picks


def render_ticket(case: Case, lang: str = "ja+en") -> str:
    parts = []
    if lang in ("ja", "ja+en"):
        parts.append(f"お客様: {case.ticket_ja}")
    if lang in ("en", "ja+en"):
        parts.append(f"Customer: {case.ticket_en}")
    parts.append("\nLog:\n" + "\n".join("  " + line for line in case.log.splitlines()))
    return "\n".join(parts)


def render_answer(case: Case) -> str:
    info = expected_info(case)
    lines = [
        f"Answer: {info.title} ({info.key})",
        f"Retry?: {info.retryable}",
        "\nLikely causes:",
        *[f"  - {x}" for x in info.likely_causes],
        "\nNext checks:",
        *[f"  {i}. {x}" for i, x in enumerate(info.next_checks, 1)],
        "\nAsk the customer:",
        *[f"  - {x}" for x in info.ask_customer],
        "\nReply checklist (write your own reply, then compare):",
        "  [ ] Say what you understood, in one sentence.",
        "  [ ] Say what you checked or what the log shows (facts).",
        "  [ ] Give one next step the customer can do now.",
        "  [ ] Ask only for what you need (see the list above).",
        "  [ ] Do not promise a fix time. Do not ask for the API key.",
    ]
    return "\n".join(lines)


def check_choice(case: Case, chosen_key: str) -> bool:
    return chosen_key == expected_info(case).key


def run_quiz(case: Case, seed: int | None, lang: str, input_fn=input, out=print) -> bool:
    out(render_ticket(case, lang))
    choices = category_choices(case, seed)
    out("\nWhich category is this?")
    for i, info in enumerate(choices, 1):
        out(f"  {i}. {info.title} ({info.key})")
    raw = input_fn("Number: ").strip()
    ok = raw.isdigit() and 1 <= int(raw) <= len(choices) and check_choice(case, choices[int(raw) - 1].key)
    out("\nCorrect." if ok else "\nNot this one.")
    input_fn("\nWrite your next check and your reply on paper. Press Enter to see the answer. ")
    out(render_answer(case))
    return ok


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m src.practice", description="Offline practice mode.")
    p.add_argument("--seed", type=int, help="Same seed, same case.")
    p.add_argument("--case", help="Case ID (see --list).")
    p.add_argument("--lang", choices=["ja", "en", "ja+en"], default="ja+en")
    p.add_argument("--list", action="store_true", help="List case IDs.")
    p.add_argument("--show", action="store_true", help="Show ticket and answer without the quiz.")
    args = p.parse_args(argv)

    if args.list:
        for c in CASES:
            print(f"{c.case_id:16} {expected_info(c).title}")
        return 0
    try:
        case = pick_case(args.seed, args.case)
    except KeyError as exc:
        print(exc.args[0], file=sys.stderr)
        return 1
    if args.show:
        print(render_ticket(case, args.lang))
        print()
        print(render_answer(case))
        return 0
    try:
        run_quiz(case, args.seed, args.lang)
    except (EOFError, KeyboardInterrupt):
        print()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
