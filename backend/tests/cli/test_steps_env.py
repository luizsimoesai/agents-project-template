"""Tests for the env-mutating steps: env file copy, JWT secret, DB password."""
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli.bootstrap import (
    step_db_password,
    step_env_file,
    step_jwt_secret,
    step_ollama,
)

_SECRET_LEN = 64


def test_step_env_file_copies_when_missing(tmp_path: Path) -> None:
    example = tmp_path / ".env.example"
    example.write_text("FOO=bar\n")
    target = tmp_path / ".env"
    step_env_file(env_path=target, example_path=example)
    assert target.exists()
    assert target.read_text() == "FOO=bar\n"


def test_step_env_file_no_op_when_present(tmp_path: Path) -> None:
    example = tmp_path / ".env.example"
    example.write_text("EXAMPLE=true\n")
    target = tmp_path / ".env"
    target.write_text("EXISTING=keep\n")
    step_env_file(env_path=target, example_path=example)
    assert target.read_text() == "EXISTING=keep\n"


def test_step_jwt_secret_generates_when_missing(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    target.write_text("JWT_SECRET_KEY=\n")
    step_jwt_secret(env_path=target)
    parsed = {}
    for line in target.read_text().splitlines():
        if line.startswith("JWT_SECRET_KEY="):
            parsed = {"JWT_SECRET_KEY": line.split("=", 1)[1]}
    assert len(parsed["JWT_SECRET_KEY"]) == _SECRET_LEN


def test_step_jwt_secret_no_op_when_present(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    existing = "a" * _SECRET_LEN
    target.write_text(f"JWT_SECRET_KEY={existing}\n")
    step_jwt_secret(env_path=target)
    assert f"JWT_SECRET_KEY={existing}" in target.read_text()


def test_step_jwt_secret_regenerates_if_too_short(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    target.write_text("JWT_SECRET_KEY=short\n")
    step_jwt_secret(env_path=target)
    line = next(
        ln for ln in target.read_text().splitlines() if ln.startswith("JWT_SECRET_KEY=")
    )
    assert len(line.split("=", 1)[1]) == _SECRET_LEN


def test_step_db_password_prompts_when_missing(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    target.write_text("POSTGRES_PASSWORD=\n")
    with patch("src.cli.bootstrap.Prompt.ask", return_value="hunter2-strong"):
        step_db_password(env_path=target, interactive=True, env_value=None)
    assert "POSTGRES_PASSWORD=hunter2-strong" in target.read_text()


def test_step_db_password_uses_env_var_in_non_interactive(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    target.write_text("POSTGRES_PASSWORD=\n")
    step_db_password(env_path=target, interactive=False, env_value="ci-pw")
    assert "POSTGRES_PASSWORD=ci-pw" in target.read_text()


def test_step_db_password_aborts_when_non_interactive_and_missing(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".env"
    target.write_text("POSTGRES_PASSWORD=\n")
    with pytest.raises(RuntimeError, match="POSTGRES_PASSWORD"):
        step_db_password(env_path=target, interactive=False, env_value=None)


def test_step_db_password_no_op_when_present(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    target.write_text("POSTGRES_PASSWORD=existing\n")
    # No prompt patched — would raise if prompt was reached.
    step_db_password(env_path=target, interactive=True, env_value=None)
    assert "POSTGRES_PASSWORD=existing" in target.read_text()


def test_step_ollama_interactive_writes_model_and_base_url(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OLLAMA_MODEL=\n")
    with patch("src.cli.bootstrap.Confirm.ask", return_value=True), patch(
        "src.cli.bootstrap.Prompt.ask", return_value="llama3.2"
    ):
        step_ollama(env_path=env_path, interactive=True, env_value=None)
    text = env_path.read_text()
    assert "OLLAMA_MODEL=llama3.2" in text
    assert "OLLAMA_BASE_URL=http://localhost:11434" in text


def test_step_ollama_interactive_decline_writes_nothing(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OLLAMA_MODEL=\n")
    with patch("src.cli.bootstrap.Confirm.ask", return_value=False):
        step_ollama(env_path=env_path, interactive=True, env_value=None)
    assert "OLLAMA_BASE_URL" not in env_path.read_text()


def test_step_ollama_skips_when_already_configured(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OLLAMA_MODEL=mistral\n")
    with patch("src.cli.bootstrap.Confirm.ask") as confirm:
        step_ollama(env_path=env_path, interactive=True, env_value=None)
    confirm.assert_not_called()


def test_step_ollama_non_interactive_reads_env_value(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OLLAMA_MODEL=\n")
    step_ollama(env_path=env_path, interactive=False, env_value="phi3")
    assert "OLLAMA_MODEL=phi3" in env_path.read_text()


def test_step_ollama_non_interactive_skips_when_absent(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OLLAMA_MODEL=\n")
    step_ollama(env_path=env_path, interactive=False, env_value=None)
    assert "OLLAMA_BASE_URL" not in env_path.read_text()


def test_step_ollama_preserves_existing_base_url(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OLLAMA_MODEL=\nOLLAMA_BASE_URL=http://gpu-box:11434\n")
    with patch("src.cli.bootstrap.Confirm.ask", return_value=True), patch(
        "src.cli.bootstrap.Prompt.ask", return_value="llama3.2"
    ):
        step_ollama(env_path=env_path, interactive=True, env_value=None)
    text = env_path.read_text()
    assert "OLLAMA_MODEL=llama3.2" in text
    assert "OLLAMA_BASE_URL=http://gpu-box:11434" in text
    assert "localhost" not in text
