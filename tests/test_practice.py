"""Tests for the offline practice mode. No API calls."""

from __future__ import annotations

from src.error_catalog import CATALOG
from src.practice import (
    CASES,
    category_choices,
    check_choice,
    expected_info,
    main,
    pick_case,
    render_answer,
    render_ticket,
    run_quiz,
)


def test_every_case_matches_its_expected_key():
    for case in CASES:
        assert expected_info(case).key == case.key, case.case_id


def test_case_ids_are_unique_and_keys_exist():
    ids = [c.case_id for c in CASES]
    assert len(ids) == len(set(ids))
    assert all(c.key in CATALOG for c in CASES)


def test_same_seed_gives_same_case():
    assert pick_case(seed=5) == pick_case(seed=5)


def test_choices_contain_the_right_answer_once():
    for case in CASES:
        choices = category_choices(case, seed=1)
        assert len(choices) == 4
        assert sum(1 for c in choices if c.key == case.key) == 1


def test_ticket_has_log_and_languages():
    case = pick_case(case_id="429-burst")
    assert "retry-after" in render_ticket(case, "en")
    assert "お客様" in render_ticket(case, "ja")


def test_answer_has_catalog_advice_and_no_key_request():
    case = pick_case(case_id="429-cap")
    text = render_answer(case)
    assert "Monthly spend cap reached" in text
    assert "Do not promise a fix time" in text


def test_quiz_marks_right_and_wrong():
    case = pick_case(case_id="401-newkey")
    choices = category_choices(case, seed=2)
    right = next(i for i, c in enumerate(choices, 1) if c.key == case.key)
    wrong = 1 if right != 1 else 2
    assert check_choice(case, case.key)
    assert run_quiz(case, 2, "en", input_fn=lambda _p: str(right), out=lambda *_: None)
    assert not run_quiz(case, 2, "en", input_fn=lambda _p: str(wrong), out=lambda *_: None)
    assert not run_quiz(case, 2, "en", input_fn=lambda _p: "abc", out=lambda *_: None)


def test_cli_list_show_and_unknown_case(capsys):
    assert main(["--list"]) == 0
    assert "429-burst" in capsys.readouterr().out
    assert main(["--case", "429-burst", "--show"]) == 0
    assert "Answer:" in capsys.readouterr().out
    assert main(["--case", "nope"]) == 1
