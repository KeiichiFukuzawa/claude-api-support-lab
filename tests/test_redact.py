from src.redact import REDACTED, describe_prompt, redact_obj, redact_text
from tests.conftest import FAKE_ENV_KEY


def test_masks_anthropic_key_pattern():
    text = "auth failed for sk-ant-api03-abcDEF_123-xyz please check"
    out = redact_text(text)
    assert "sk-ant-api03" not in out
    assert REDACTED in out


def test_masks_exact_env_key_value():
    out = redact_text(f"key was {FAKE_ENV_KEY}!")
    assert FAKE_ENV_KEY not in out


def test_masks_extra_secret_that_does_not_look_like_a_key():
    out = redact_text("value=my-custom-secret-1234", extra_secrets=["my-custom-secret-1234"])
    assert "my-custom-secret-1234" not in out


def test_masks_bearer_and_x_api_key_headers():
    out = redact_text('Authorization: Bearer abc.def.ghi123 x-api-key: "zzzzzzzzzz"')
    assert "abc.def.ghi123" not in out
    assert "zzzzzzzzzz" not in out
    assert "Bearer" in out  # the label stays, only the value is hidden


def test_redact_obj_walks_nested_structures():
    data = {"a": ["sk-ant-api03-zzz"], "b": {"c": "ok"}, "n": 3}
    out = redact_obj(data)
    assert out == {"a": [REDACTED], "b": {"c": "ok"}, "n": 3}


def test_short_values_are_not_treated_as_secrets():
    # Very short "secrets" would replace normal words, so we ignore them.
    assert redact_text("ok ok", extra_secrets=["ok"]) == "ok ok"


def test_describe_prompt_keeps_only_length():
    assert describe_prompt("hello world") == {"prompt_chars": 11}
