"""Prompt resources reject paths and render only explicitly templated text."""

import pytest

from src.utils import prompt_loader


@pytest.fixture
def prompt_resources(tmp_path, monkeypatch):
    folder = tmp_path / "llm" / "prompts"
    folder.mkdir(parents=True)
    (folder / "sample.md").write_text("History: {messages}", encoding="utf-8")
    (folder / "raw.md").write_text('{"emotion": 0}', encoding="utf-8")
    monkeypatch.setattr(prompt_loader, "_MODULES", tmp_path)
    prompt_loader.load_prompt.cache_clear()
    yield
    prompt_loader.load_prompt.cache_clear()


@pytest.mark.parametrize(
    "name,module",
    [("../secret", "llm"), ("sample", "../core"), ("/etc/passwd", "llm"), ("sample.md", "llm")],
)
def test_prompt_paths_cannot_escape_module_resources(name, module):
    with pytest.raises(ValueError, match="identifiers"):
        prompt_loader.load_prompt(name, module=module)


def test_prompt_rendering_preserves_message_braces(prompt_resources):
    assert (
        prompt_loader.render_prompt("sample", messages='user: {"value": 1}')
        == 'History: user: {"value": 1}'
    )


def test_raw_prompt_json_is_not_interpreted_as_template(prompt_resources):
    assert prompt_loader.load_prompt("raw") == '{"emotion": 0}'


def test_missing_template_argument_is_reported(prompt_resources):
    with pytest.raises(KeyError, match="messages"):
        prompt_loader.render_prompt("sample")
