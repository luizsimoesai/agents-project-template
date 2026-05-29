"""End-to-end smoke + idempotency test for the bootstrap wizard.

External boundaries (Docker, Alembic, real DB) are mocked. The goal is
to prove the orchestration sequence and that a second run is a no-op.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from src.cli import bootstrap

_SECRET_LEN = 64


def test_bootstrap_help_runs_on_fresh_clone(tmp_path: Path) -> None:
    """``python -m src.cli.bootstrap --help`` must work with no .env and no
    settings env vars — the exact state of a fresh clone.

    Regression: bootstrap imported ``_hash_password`` at module top level,
    which eagerly instantiated ``Settings()`` (via ``src.core.security`` ->
    ``src.core.settings``) and crashed with a pydantic ValidationError
    before the wizard could create .env. Run in a subprocess because the
    test suite's conftest pre-populates these env vars in-process, masking
    the bug.
    """
    backend_root = Path(__file__).resolve().parents[2]
    clean_env = {
        k: v
        for k, v in os.environ.items()
        if k not in {"JWT_SECRET_KEY", "POSTGRES_PASSWORD", "DATABASE_URL"}
    }
    clean_env["PYTHONPATH"] = str(backend_root)
    result = subprocess.run(
        [sys.executable, "-m", "src.cli.bootstrap", "--help"],
        cwd=tmp_path,  # no .env here, so Settings() can't hydrate from file
        env=clean_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"bootstrap --help crashed on a fresh clone:\n{result.stderr}"
    )
    assert "bootstrap" in result.stdout.lower()


def _mk_env_files(tmp_path: Path) -> tuple[Path, Path]:
    example = tmp_path / ".env.example"
    example.write_text(
        "# header\n"
        "AUTH_TYPE=custom\n"
        "JWT_SECRET_KEY=\n"
        "POSTGRES_PASSWORD=\n"
        "MODEL=\n"
        "# ANTHROPIC_API_KEY=\n"
        "# OPENAI_API_KEY=\n"
        "# OPENROUTER_API_KEY=\n",
    )
    seeds = tmp_path / "seeds" / "models.yaml"
    seeds.parent.mkdir()
    seeds.write_text(
        """
models:
  - display_name: A
    model_id: anthropic:a
    provider: anthropic
    is_default: true
""",
    )
    return example, seeds


def _ok(stdout: str = "") -> MagicMock:
    res = MagicMock(spec=subprocess.CompletedProcess)
    res.returncode = 0
    res.stdout = stdout
    res.stderr = ""
    return res


def test_bootstrap_full_run_then_idempotent_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    example, seeds = _mk_env_files(tmp_path)
    env_path = tmp_path / ".env"

    # Redirect the module's path constants to our temp paths.
    monkeypatch.setattr(bootstrap, "_BACKEND_ROOT", tmp_path)
    monkeypatch.setattr(bootstrap, "_ENV_PATH", env_path)
    monkeypatch.setattr(bootstrap, "_ENV_EXAMPLE_PATH", example)
    monkeypatch.setattr(bootstrap, "_SEEDS_PATH", seeds)

    # docker compose ps -> healthy; everything else -> ok.
    def fake_run(cmd, **kwargs):
        if "ps" in cmd:
            return _ok("healthy\n")
        if "current" in cmd:
            return _ok("rev1 (head)\n")
        if "heads" in cmd:
            return _ok("rev1 (head)\n")
        return _ok()

    monkeypatch.setattr("src.cli.bootstrap.subprocess.run", fake_run)

    # Replace _run_db_steps with a counting stub — we don't need real DB here.
    db_calls: list[dict] = []

    async def fake_db_steps(**kwargs):
        db_calls.append(kwargs)
        return False  # catalog not empty

    monkeypatch.setattr("src.cli.bootstrap._run_db_steps", fake_db_steps)

    # Run 1: non-interactive with required env vars set.
    monkeypatch.setenv("POSTGRES_PASSWORD", "ci-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "real-anthropic")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "super-strong-pw")

    code = bootstrap.main(["--non-interactive"])
    assert code == 0
    # .env was written with the captured values.
    text = env_path.read_text()
    assert "POSTGRES_PASSWORD=ci-secret" in text
    assert "ANTHROPIC_API_KEY=real-anthropic" in text
    assert "JWT_SECRET_KEY=" in text
    # Hex secret, 64 chars.
    secret_line = next(
        ln for ln in text.splitlines() if ln.startswith("JWT_SECRET_KEY=")
    )
    assert len(secret_line.split("=", 1)[1]) == _SECRET_LEN
    # DB steps ran exactly once.
    assert len(db_calls) == 1
    assert db_calls[0]["providers"] == {"anthropic"}
    # No Ollama configured in this non-interactive run.
    assert db_calls[0]["ollama_model"] is None

    # Run 2: re-run. .env is already fully populated; should still exit 0,
    # write nothing new, and call DB steps once more (idempotent at the
    # SQL layer — exercised in test_steps_db tests, here we only assert
    # that orchestration does not crash on a fully-configured project).
    before = env_path.read_text()
    code2 = bootstrap.main(["--non-interactive"])
    after = env_path.read_text()
    assert code2 == 0
    assert before == after, "second run must not mutate .env"


def test_bootstrap_non_interactive_aborts_when_required_env_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    example, seeds = _mk_env_files(tmp_path)
    env_path = tmp_path / ".env"
    monkeypatch.setattr(bootstrap, "_BACKEND_ROOT", tmp_path)
    monkeypatch.setattr(bootstrap, "_ENV_PATH", env_path)
    monkeypatch.setattr(bootstrap, "_ENV_EXAMPLE_PATH", example)
    monkeypatch.setattr(bootstrap, "_SEEDS_PATH", seeds)
    monkeypatch.setattr(
        "src.cli.bootstrap.subprocess.run", lambda *a, **kw: _ok("healthy\n")
    )

    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.delenv("BOOTSTRAP_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)

    code = bootstrap.main(["--non-interactive"])
    assert code == 1


def test_print_complete_warns_when_catalog_empty() -> None:
    buf = io.StringIO()
    bootstrap._print_complete(Console(file=buf, width=100), catalog_empty=True)
    assert "No LLM model configured" in buf.getvalue()


def test_print_complete_no_warning_when_catalog_has_model() -> None:
    buf = io.StringIO()
    bootstrap._print_complete(Console(file=buf, width=100), catalog_empty=False)
    assert "No LLM model configured" not in buf.getvalue()
