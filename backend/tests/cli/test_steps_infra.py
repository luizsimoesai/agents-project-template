"""Tests for step_postgres + step_migrations.

External commands (docker compose, alembic) are mocked at the
subprocess level. We don't try to actually bring Postgres up; the
goal is to verify the orchestration choices.
"""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest

from src.cli.bootstrap import step_migrations, step_postgres


def _ok(stdout: str = "") -> MagicMock:
    res = MagicMock(spec=subprocess.CompletedProcess)
    res.returncode = 0
    res.stdout = stdout
    res.stderr = ""
    return res


def test_step_postgres_skips_when_already_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        # First call is `docker compose ps postgres --format {{.Health}}`
        if "ps" in cmd:
            return _ok("healthy\n")
        return _ok()

    monkeypatch.setattr("src.cli.bootstrap.subprocess.run", fake_run)
    step_postgres()
    # Only the ps call happened; no `up` call.
    assert all("up" not in cmd for cmd in calls)


def test_step_postgres_starts_when_unhealthy(monkeypatch: pytest.MonkeyPatch) -> None:
    states = iter(["", "starting\n", "healthy\n"])

    def fake_run(cmd, **kwargs):
        if "ps" in cmd:
            return _ok(next(states))
        return _ok()

    sleep_calls: list[float] = []
    monkeypatch.setattr("src.cli.bootstrap.subprocess.run", fake_run)
    monkeypatch.setattr("src.cli.bootstrap.time.sleep", sleep_calls.append)
    step_postgres()
    # At least one sleep happened while waiting.
    assert len(sleep_calls) >= 1


def test_step_postgres_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, **kwargs):
        return _ok("starting\n")

    # time.monotonic returns 0 then 1000 (well past 60s deadline).
    times = iter([0, 1000])
    monkeypatch.setattr("src.cli.bootstrap.subprocess.run", fake_run)
    monkeypatch.setattr("src.cli.bootstrap.time.sleep", lambda _: None)
    monkeypatch.setattr("src.cli.bootstrap.time.monotonic", lambda: next(times))
    with pytest.raises(RuntimeError, match="did not become healthy"):
        step_postgres()


def test_step_postgres_docker_not_running(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("docker")

    monkeypatch.setattr("src.cli.bootstrap.subprocess.run", fake_run)
    with pytest.raises(RuntimeError, match="Docker daemon"):
        step_postgres()


def test_step_migrations_skips_when_at_head(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "current" in cmd:
            return _ok("c4f7d2a8e1b3 (head)\n")
        if "heads" in cmd:
            return _ok("c4f7d2a8e1b3 (head)\n")
        return _ok()

    monkeypatch.setattr("src.cli.bootstrap.subprocess.run", fake_run)
    step_migrations()
    assert all("upgrade" not in cmd for cmd in calls)


def test_step_migrations_runs_when_behind(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if "current" in cmd:
            return _ok("oldrev\n")
        if "heads" in cmd:
            return _ok("c4f7d2a8e1b3\n")
        return _ok()

    monkeypatch.setattr("src.cli.bootstrap.subprocess.run", fake_run)
    step_migrations()
    assert any("upgrade" in cmd for cmd in calls)
