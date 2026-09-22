import pytest
from pydantic import ValidationError

from src.modules.llm.config import LLMSettings
from src.modules.llm.presets import DEFAULT_PRESETS, parse_llm_presets


def test_blank_uses_code_defaults():
    parsed = parse_llm_presets("")
    assert parsed["reply"].temperature == 0.8
    assert parsed["reply"].top_p == 0.95
    assert parsed["reply"].max_tokens == 1024
    assert parsed["rag"].temperature == 0.1
    assert parsed["rag"].top_p == 1.0
    assert parsed["rag"].max_tokens == 512
    assert parsed["extract"].temperature == 0.0
    assert parsed["extract"].max_tokens == 1024
    assert set(parsed) == {"reply", "rag", "extract"}


def test_partial_json_overrides_one_field():
    parsed = parse_llm_presets('{"reply": {"temperature": 0.9}}')
    assert parsed["reply"].temperature == 0.9
    assert parsed["reply"].top_p == DEFAULT_PRESETS["reply"].top_p
    assert parsed["rag"].temperature == 0.1


def test_rejects_bad_values():
    for raw in (
        "{",
        '{"nope": {"temperature": 0.1}}',
        '{"reply": {"seed": 1}}',
        '{"reply": {"temperature": 2.1}}',
        '{"reply": {"temperature": -0.1}}',
        '{"reply": {"top_p": 1.1}}',
        '{"reply": {"max_tokens": 0}}',
        '{"reply": {"max_tokens": 1.5}}',
    ):
        with pytest.raises(ValueError):
            parse_llm_presets(raw)


def test_settings_fail_on_bad_presets(monkeypatch):
    monkeypatch.setenv("LLM_PRESETS", '{"reply": {"temperature": 9}}')
    with pytest.raises(ValidationError):
        LLMSettings()


def test_settings_presets_match_parser(monkeypatch):
    monkeypatch.setenv("LLM_PRESETS", '{"extract": {"max_tokens": 256}}')
    settings = LLMSettings()
    assert settings.presets()["extract"].max_tokens == 256
    assert settings.presets()["reply"].temperature == 0.8
