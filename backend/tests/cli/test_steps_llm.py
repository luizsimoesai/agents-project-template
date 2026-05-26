"""Tests for step_llm_keys (interactive + non-interactive)."""
from pathlib import Path
from unittest.mock import patch

from src.cli.bootstrap import step_llm_keys


def _env(tmp_path: Path, body: str = "") -> Path:
    p = tmp_path / ".env"
    p.write_text(body)
    return p


def test_step_llm_keys_interactive_yes_anthropic(tmp_path: Path) -> None:
    env_path = _env(tmp_path)
    with (
        patch("src.cli.bootstrap.Confirm.ask", side_effect=[True, False, False]),
        patch("src.cli.bootstrap.Prompt.ask", return_value="real-key"),
    ):
        step_llm_keys(env_path=env_path, interactive=True, env_values={})
    assert "ANTHROPIC_API_KEY=real-key" in env_path.read_text()
    assert "OPENAI_API_KEY" not in env_path.read_text()


def test_step_llm_keys_interactive_skips_already_configured(tmp_path: Path) -> None:
    env_path = _env(tmp_path, "ANTHROPIC_API_KEY=already-set\n")
    # Confirm.ask should NOT be called for anthropic (already configured).
    confirm_calls: list = []

    def fake_confirm(*args, **kwargs):
        confirm_calls.append(args)
        return False  # decline openai + openrouter

    with patch("src.cli.bootstrap.Confirm.ask", side_effect=fake_confirm):
        step_llm_keys(env_path=env_path, interactive=True, env_values={})
    # Exactly 2 confirms: openai + openrouter (anthropic was skipped).
    expected_calls = 2
    assert len(confirm_calls) == expected_calls


def test_step_llm_keys_non_interactive_writes_from_env(tmp_path: Path) -> None:
    env_path = _env(tmp_path)
    step_llm_keys(
        env_path=env_path,
        interactive=False,
        env_values={"ANTHROPIC_API_KEY": "k1", "OPENAI_API_KEY": "k2"},
    )
    text = env_path.read_text()
    assert "ANTHROPIC_API_KEY=k1" in text
    assert "OPENAI_API_KEY=k2" in text


def test_step_llm_keys_non_interactive_ignores_placeholders(tmp_path: Path) -> None:
    env_path = _env(tmp_path)
    step_llm_keys(
        env_path=env_path,
        interactive=False,
        env_values={"OPENAI_API_KEY": "sk-...", "ANTHROPIC_API_KEY": ""},
    )
    text = env_path.read_text()
    assert "OPENAI_API_KEY=sk-..." not in text
    assert "ANTHROPIC_API_KEY" not in text


def test_step_llm_keys_interactive_no_for_all(tmp_path: Path) -> None:
    env_path = _env(tmp_path)
    with patch("src.cli.bootstrap.Confirm.ask", return_value=False):
        step_llm_keys(env_path=env_path, interactive=True, env_values={})
    # No keys written.
    assert "API_KEY" not in env_path.read_text()
