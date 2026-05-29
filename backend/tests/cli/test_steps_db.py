"""Tests for the async DB steps: step_admin + step_seed_models."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.cli.bootstrap import step_admin, step_seed_models
from src.models.llm_model import LLMModel
from src.models.user import User


def _execute_returning(value):
    """Build an `execute` mock whose .scalar_one_or_none() returns `value`."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.all.return_value = []
    result.scalars.return_value.all.return_value = []
    execute = AsyncMock(return_value=result)
    return execute


@pytest.fixture
def session() -> AsyncMock:
    s = AsyncMock(spec=AsyncSession)
    s.add = MagicMock()
    return s


async def test_step_admin_skips_when_admin_exists(session: AsyncMock) -> None:
    session.execute = _execute_returning(MagicMock(spec=User))
    await step_admin(
        session=session,
        interactive=True,
        env_email=None,
        env_password=None,
    )
    session.add.assert_not_called()
    session.commit.assert_not_called()


async def test_step_admin_creates_in_non_interactive(session: AsyncMock) -> None:
    session.execute = _execute_returning(None)
    await step_admin(
        session=session,
        interactive=False,
        env_email="root@example.com",
        env_password="super-secure-pw",
    )
    session.add.assert_called_once()
    added = session.add.call_args.args[0]
    assert added.email == "root@example.com"
    assert added.is_admin is True
    assert added.is_active is True
    # Stored hash must NOT equal the plaintext password.
    assert added.password_hash != "super-secure-pw"
    session.commit.assert_awaited_once()


async def test_step_admin_non_interactive_missing_env(session: AsyncMock) -> None:
    session.execute = _execute_returning(None)
    with pytest.raises(RuntimeError, match="BOOTSTRAP_ADMIN_EMAIL"):
        await step_admin(
            session=session,
            interactive=False,
            env_email=None,
            env_password="any-strong-pw",
        )


async def test_step_admin_non_interactive_password_too_short(
    session: AsyncMock,
) -> None:
    session.execute = _execute_returning(None)
    with pytest.raises(RuntimeError, match=">= 8"):
        await step_admin(
            session=session,
            interactive=False,
            env_email="a@b.c",
            env_password="short",
        )


async def test_step_admin_interactive_loops_on_short_password(
    session: AsyncMock,
) -> None:
    session.execute = _execute_returning(None)
    # First password too short, second OK; first confirm matches second pw.
    prompts = iter(["a@b.c", "short", "longerpassword", "longerpassword"])
    with patch(
        "src.cli.bootstrap.Prompt.ask",
        side_effect=lambda *a, **kw: next(prompts),
    ):
        await step_admin(
            session=session,
            interactive=True,
            env_email=None,
            env_password=None,
        )
    assert session.add.called
    added = session.add.call_args.args[0]
    assert added.email == "a@b.c"


async def test_step_admin_interactive_loops_on_mismatch(session: AsyncMock) -> None:
    session.execute = _execute_returning(None)
    prompts = iter(
        ["a@b.c", "longpassword", "mismatched-confirm", "longpassword", "longpassword"]
    )
    with patch(
        "src.cli.bootstrap.Prompt.ask",
        side_effect=lambda *a, **kw: next(prompts),
    ):
        await step_admin(
            session=session,
            interactive=True,
            env_email=None,
            env_password=None,
        )
    added = session.add.call_args.args[0]
    assert added.email == "a@b.c"


async def test_step_seed_models_inserts_filtered_entries(
    session: AsyncMock, tmp_path: Path
) -> None:
    seeds_path = tmp_path / "models.yaml"
    seeds_path.write_text(
        """
models:
  - display_name: A
    model_id: anthropic:a
    provider: anthropic
    is_default: true
  - display_name: B
    model_id: openai:b
    provider: openai
""",
    )
    # No existing models in DB.
    existing_result = MagicMock()
    existing_result.all.return_value = []
    session.execute = AsyncMock(return_value=existing_result)

    await step_seed_models(
        session=session,
        seeds_path=seeds_path,
        providers={"anthropic"},
    )
    # Only the anthropic entry should be inserted.
    assert session.add.call_count == 1
    added = session.add.call_args.args[0]
    assert isinstance(added, LLMModel)
    assert added.model_id == "anthropic:a"
    assert added.is_default is True
    session.commit.assert_awaited_once()


async def test_step_seed_models_skips_when_all_present(
    session: AsyncMock, tmp_path: Path
) -> None:
    seeds_path = tmp_path / "models.yaml"
    seeds_path.write_text(
        """
models:
  - display_name: A
    model_id: anthropic:a
    provider: anthropic
""",
    )
    # DB already contains anthropic:a.
    existing_result = MagicMock()
    existing_result.all.return_value = [("anthropic:a",)]
    session.execute = AsyncMock(return_value=existing_result)

    await step_seed_models(
        session=session,
        seeds_path=seeds_path,
        providers={"anthropic"},
    )
    session.add.assert_not_called()


async def test_step_seed_models_no_providers_no_op(
    session: AsyncMock, tmp_path: Path
) -> None:
    seeds_path = tmp_path / "models.yaml"
    seeds_path.write_text(
        """
models:
  - display_name: A
    model_id: anthropic:a
    provider: anthropic
""",
    )
    existing_result = MagicMock()
    existing_result.all.return_value = []
    session.execute = AsyncMock(return_value=existing_result)

    await step_seed_models(
        session=session,
        seeds_path=seeds_path,
        providers=set(),
    )
    session.add.assert_not_called()
    session.commit.assert_not_called()


async def test_step_seed_models_promotes_default(
    session: AsyncMock, tmp_path: Path
) -> None:
    """When the YAML's default-marked entry's provider is unavailable,
    the first surviving entry must be inserted with is_default=True."""
    seeds_path = tmp_path / "models.yaml"
    seeds_path.write_text(
        """
models:
  - display_name: A
    model_id: anthropic:a
    provider: anthropic
    is_default: true
  - display_name: B
    model_id: openai:b
    provider: openai
""",
    )
    existing_result = MagicMock()
    existing_result.all.return_value = []
    session.execute = AsyncMock(return_value=existing_result)

    await step_seed_models(
        session=session,
        seeds_path=seeds_path,
        providers={"openai"},
    )
    added = session.add.call_args.args[0]
    assert added.model_id == "openai:b"
    assert added.is_default is True


async def test_step_seed_models_seeds_ollama_as_default_when_no_cloud(
    session: AsyncMock, tmp_path: Path
) -> None:
    seeds_path = tmp_path / "models.yaml"
    seeds_path.write_text(
        """
models:
  - display_name: A
    model_id: anthropic:a
    provider: anthropic
    is_default: true
""",
    )
    existing_result = MagicMock()
    existing_result.all.return_value = []
    session.execute = AsyncMock(return_value=existing_result)

    await step_seed_models(
        session=session,
        seeds_path=seeds_path,
        providers=set(),  # no cloud providers
        ollama_model="llama3.2",
        ollama_base_url="http://localhost:11434",
    )
    assert session.add.call_count == 1
    added = session.add.call_args.args[0]
    assert added.model_id == "ollama:llama3.2"
    assert added.provider == "ollama"
    assert added.base_url == "http://localhost:11434"
    assert added.is_default is True


async def test_step_seed_models_ollama_not_default_when_cloud_present(
    session: AsyncMock, tmp_path: Path
) -> None:
    seeds_path = tmp_path / "models.yaml"
    seeds_path.write_text(
        """
models:
  - display_name: A
    model_id: anthropic:a
    provider: anthropic
    is_default: true
""",
    )
    existing_result = MagicMock()
    existing_result.all.return_value = []
    session.execute = AsyncMock(return_value=existing_result)

    await step_seed_models(
        session=session,
        seeds_path=seeds_path,
        providers={"anthropic"},
        ollama_model="llama3.2",
    )
    added_by_id = {
        c.args[0].model_id: c.args[0] for c in session.add.call_args_list
    }
    assert added_by_id["anthropic:a"].is_default is True
    assert added_by_id["ollama:llama3.2"].is_default is False


async def test_step_seed_models_empty_when_nothing_configured(
    session: AsyncMock, tmp_path: Path
) -> None:
    seeds_path = tmp_path / "models.yaml"
    seeds_path.write_text(
        """
models:
  - display_name: A
    model_id: anthropic:a
    provider: anthropic
""",
    )
    existing_result = MagicMock()
    existing_result.all.return_value = []
    session.execute = AsyncMock(return_value=existing_result)

    await step_seed_models(
        session=session,
        seeds_path=seeds_path,
        providers=set(),
        ollama_model=None,
    )
    session.add.assert_not_called()
    session.commit.assert_not_called()
