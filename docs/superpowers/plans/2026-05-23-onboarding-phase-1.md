# Onboarding & Template Launch — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `task bootstrap` a one-command wizard that takes a fresh clone from zero to a running backend (admin created, models seeded), and sanitise `.env.example` and `docker-compose.yml` so the surrounding config no longer contradicts itself.

**Architecture:** A single Python module `backend/src/cli/bootstrap.py` exposes pure helpers (env-file parsing, YAML loading, placeholder detection) plus async step functions (Postgres bring-up, migrations, admin insert, model seed). The CLI entry point sequences eight steps and is invoked via `task bootstrap`. Each step is idempotent — re-runs perform fast skip-checks and exit silently. Tests cover helpers with `tmp_path`, DB steps with `AsyncMock(spec=AsyncSession)` (matching the project's `mock_session` fixture pattern), and external commands with `monkeypatch.setattr` on `subprocess.run`.

**Tech Stack:** Python 3.12, `rich` (interactive prompts + panels), `pyyaml` (seed catalogue parsing), SQLAlchemy async (existing), `subprocess` for Docker/Alembic invocation, taskipy (existing) for the `task bootstrap` entry, pytest with `asyncio_mode=auto` (existing).

**Spec:** [`docs/superpowers/specs/2026-05-23-onboarding-and-template-launch-design.md`](../specs/2026-05-23-onboarding-and-template-launch-design.md)

**Out of scope for this plan:** Front C (README rewrite, LICENSE, CI) and Front D (frontend empty states) — separate plans after Phase 1 lands.

---

## File map

| Path | Action | Responsibility |
|---|---|---|
| `backend/.env.example` | Modify | Sane defaults, English-only comments, no live placeholders |
| `backend/docker-compose.yml` | Modify | Fail-fast on missing `POSTGRES_PASSWORD` |
| `backend/tests/test_env_example_safety.py` | Create | Regression guard for placeholder API keys |
| `backend/pyproject.toml` | Modify | Add `rich`, `pyyaml`; register `task bootstrap` |
| `backend/seeds/models.yaml` | Create | Curated LLM catalogue (5 entries) |
| `backend/src/cli/__init__.py` | Create | Empty (package marker) |
| `backend/src/cli/bootstrap.py` | Create | Wizard: helpers + 8 step functions + `main()` |
| `backend/tests/cli/__init__.py` | Create | Empty (package marker) |
| `backend/tests/cli/test_env_file.py` | Create | Tests for `parse_env_file`, `update_env_file` |
| `backend/tests/cli/test_helpers.py` | Create | Tests for `is_placeholder`, `generate_jwt_secret`, `configured_providers` |
| `backend/tests/cli/test_seed_loader.py` | Create | Tests for `load_seed_catalogue`, `filter_seeds_by_providers` |
| `backend/tests/cli/test_steps_env.py` | Create | Tests for env/jwt/db-password/llm-keys steps |
| `backend/tests/cli/test_steps_infra.py` | Create | Tests for postgres/migrations steps (subprocess mocked) |
| `backend/tests/cli/test_steps_db.py` | Create | Tests for admin + seed-models steps (DB mocked) |
| `backend/tests/cli/test_bootstrap_flow.py` | Create | Smoke E2E + idempotency (second run is no-op) |
| `backend/tests/cli/test_bootstrap_non_interactive.py` | Create | `--non-interactive` mode and error paths |
| `README.md` | Modify | Single-line pointer to `task bootstrap` (full rewrite in Phase 2) |

---

## Task 1: Sanitise `.env.example` (Front B.1 + B.3)

**Files:**
- Create: `backend/tests/test_env_example_safety.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: Write the failing regression test**

Create `backend/tests/test_env_example_safety.py`:

```python
"""Regression guard for `.env.example`.

Catches the anti-pattern of an uncommented placeholder LLM API key (e.g.
`OPENAI_API_KEY=sk-...`) sneaking back into the example file. Such a value
looks configured to humans skimming the file but fails at first LLM call.
"""
from pathlib import Path

ENV_EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"

_FORBIDDEN_VALUE_SUBSTRINGS = ("sk-...", "pk-...", "your-key-here", "...")


def _uncommented_value_lines(text: str) -> list[tuple[int, str]]:
    """Yield (lineno, line) for lines that assign a value (KEY=VALUE) and
    are not commented out."""
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.lstrip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        out.append((i, raw))
    return out


def test_env_example_has_no_placeholder_api_keys() -> None:
    text = ENV_EXAMPLE.read_text()
    offenders: list[str] = []
    for lineno, line in _uncommented_value_lines(text):
        _, _, value = line.partition("=")
        value = value.strip()
        if any(bad in value for bad in _FORBIDDEN_VALUE_SUBSTRINGS):
            offenders.append(f"  L{lineno}: {line.rstrip()}")
    assert not offenders, (
        "Uncommented placeholder values in .env.example "
        "(comment them out or remove):\n" + "\n".join(offenders)
    )


def test_env_example_auth_type_is_custom() -> None:
    text = ENV_EXAMPLE.read_text()
    for lineno, line in _uncommented_value_lines(text):
        if line.lstrip().startswith("AUTH_TYPE="):
            _, _, value = line.partition("=")
            value = value.strip().split("#", 1)[0].strip()
            assert value == "custom", (
                f"L{lineno}: AUTH_TYPE must default to 'custom' "
                f"(template assumes JWT everywhere); got {value!r}"
            )
            return
    raise AssertionError("AUTH_TYPE not found in .env.example")
```

- [ ] **Step 2: Run the test to verify it fails**

Run from `backend/`:
```bash
uv run pytest tests/test_env_example_safety.py -v
```

Expected: both tests FAIL. The first hits `OPENAI_API_KEY=sk-...` and the Langfuse `pk-...`/`sk-...` lines. The second hits `AUTH_TYPE=noop`.

- [ ] **Step 3: Rewrite `.env.example`**

Replace the file at `backend/.env.example` with the new content (English-only, sane defaults). Use Edit for each block:

Edit 1 — header:
- old: `# --- Application Settings ---\nPROJECT_NAME=backend\nVERSION="0.1.0"\nDEBUG=true`
- new: keep identical (already English).

Edit 2 — auth section:
- old:
  ```
  # --- Authentication ---
  AUTH_TYPE=noop  # noop, custom
  ```
- new:
  ```
  # --- Authentication ---
  # Aegra auth mode. `custom` enables this template's JWT handler.
  # `noop` disables authentication entirely — do NOT use except in isolated dev.
  AUTH_TYPE=custom
  ```

Edit 3 — model default:
- old:
  ```
  # Default model used when no model is selected per-thread.
  # Format: provider/model  (e.g. anthropic/claude-sonnet-4-6, openai/gpt-4o, ollama/llama3)
  MODEL=ollama/gpt-oss:120b-cloud
  ```
- new:
  ```
  # Default model used when an assistant does not specify one.
  # Format: provider:model (e.g. anthropic:claude-sonnet-4-6, openai:gpt-4o-mini).
  # Leave empty so `task bootstrap` selects one based on configured providers.
  MODEL=
  ```

Edit 4 — LLM providers block:
- old:
  ```
  # --- LLM Providers ---
  OPENAI_API_KEY=sk-...
  # ANTHROPIC_API_KEY=...
  # TOGETHER_API_KEY=...
  # OPENROUTER_API_KEY=...
  ```
- new:
  ```
  # --- LLM Providers ---
  # Configure AT LEAST ONE. `task bootstrap` prompts and writes the values here.
  # All are commented out by default so the wizard does not mistake placeholders
  # for real keys. (TOGETHER_API_KEY is removed; no Together models are in the
  # seed catalogue. Re-add it manually if you extend seeds/models.yaml.)
  # OPENAI_API_KEY=
  # ANTHROPIC_API_KEY=
  # OPENROUTER_API_KEY=
  ```

Edit 5 — Langfuse keys:
- old:
  ```
  # Note: uses LANGFUSE_BASE_URL (not HOST) to match SDK standards
  LANGFUSE_BASE_URL=https://cloud.langfuse.com
  LANGFUSE_PUBLIC_KEY=pk-...
  LANGFUSE_SECRET_KEY=sk-...
  ```
- new:
  ```
  # Note: uses LANGFUSE_BASE_URL (not HOST) to match SDK standards
  LANGFUSE_BASE_URL=https://cloud.langfuse.com
  # LANGFUSE_PUBLIC_KEY=
  # LANGFUSE_SECRET_KEY=
  ```

- [ ] **Step 4: Run tests to verify they pass**

Run from `backend/`:
```bash
uv run pytest tests/test_env_example_safety.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/.env.example backend/tests/test_env_example_safety.py
git commit -m "chore(env): sane defaults in .env.example + regression test

- AUTH_TYPE=custom (matches the JWT handler this template ships)
- Comment out all LLM API keys; task bootstrap will fill them in
- MODEL left empty; task bootstrap picks based on configured providers
- Drop TOGETHER_API_KEY (no Together models in seed catalogue)
- Comment out Langfuse pk-.../sk-... placeholders
- New tests/test_env_example_safety.py guards against regressions"
```

---

## Task 2: Fail-fast `docker-compose.yml` (Front B.2)

**Files:**
- Modify: `backend/docker-compose.yml`

- [ ] **Step 1: Edit the postgres service**

In `backend/docker-compose.yml`, change:
```yaml
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-backend_secret}
```
to (both occurrences — postgres service `environment` block AND backend service `environment` block):
```yaml
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required (set in .env via task bootstrap)}
```

- [ ] **Step 2: Verify the new syntax with a configured env**

Run from `backend/`:
```bash
POSTGRES_PASSWORD=anything docker compose config > /dev/null && echo OK
```

Expected: prints `OK`.

- [ ] **Step 3: Verify the new syntax fails without env**

Run from `backend/` (in a subshell with the var explicitly unset, to avoid pulling it from `.env`):
```bash
( unset POSTGRES_PASSWORD && docker compose --env-file /dev/null config > /dev/null )
echo "exit: $?"
```

Expected: exit non-zero (10 typically), with stderr mentioning `POSTGRES_PASSWORD is required`.

- [ ] **Step 4: Commit**

```bash
git add backend/docker-compose.yml
git commit -m "fix(docker): fail fast when POSTGRES_PASSWORD is missing

Previous default 'backend_secret' contradicted settings.py which refuses
to boot without POSTGRES_PASSWORD. The :? syntax aborts docker compose
with a clear message instead of starting a misconfigured stack."
```

---

## Task 3: Add deps + register `task bootstrap`

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add `rich` and `pyyaml` to dependencies**

In `backend/pyproject.toml`, locate the `dependencies = [` block and add two entries (alphabetised position is fine):

```toml
dependencies = [
    "aegra-cli>=0.9.2",
    "langgraph>=1.0.8",
    "langchain>=0.3.14",
    "langchain-openai>=0.3.0",
    "langchain-anthropic>=0.3.12",
    "langchain-ollama>=1.0.1",
    "sqlalchemy>=2.0.48",
    "alembic>=1.18.4",
    "pydantic-settings>=2.13.1",
    "asyncpg>=0.31.0",
    "bcrypt>=4.0.0",
    "python-jose[cryptography]>=3.5.0",
    "python-multipart>=0.0.22",
    "email-validator>=2.3.0",
    "deepagents>=0.5.9",
    "langchain-openrouter>=0.2.3",
    "slowapi>=0.1.9",
    "pyyaml>=6.0",
    "rich>=14.0.0",
]
```

- [ ] **Step 2: Register the taskipy entry**

In `[tool.taskipy.tasks]`, add (preserving existing entries):

```toml
[tool.taskipy.tasks]
lint = 'ruff check && mypy .'
format = 'ruff format'
run = 'uv run aegra dev'
bootstrap = 'uv run python -m src.cli.bootstrap'
pre_test = 'task lint'
test = 'pytest -s -x --cov=src -vv'
post_test = 'coverage html'
```

- [ ] **Step 3: Lock and install**

Run from `backend/`:
```bash
uv sync
```

Expected: lockfile updates; `rich` and `pyyaml` install without error.

- [ ] **Step 4: Verify taskipy sees the entry**

Run from `backend/`:
```bash
uv run task --list 2>&1 | grep bootstrap
```

Expected: line containing `bootstrap`.

(Running `task bootstrap` itself will fail with `No module named 'src.cli'` until Task 6 — that's fine.)

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "chore(deps): add rich + pyyaml; register 'task bootstrap'

Prepares for the interactive bootstrap wizard. Wiring only — module
itself lands in subsequent commits."
```

---

## Task 4: Create the seed catalogue

**Files:**
- Create: `backend/seeds/models.yaml`

- [ ] **Step 1: Create the seeds directory and file**

Create `backend/seeds/models.yaml`:

```yaml
# Curated LLM catalogue used by `task bootstrap`.
#
# Wizard inserts only entries whose `provider` matches a configured API key.
# Ollama is always included (no API key required).
#
# `is_default: true` is allowed on AT MOST ONE entry (validated at load time).
# If the default-marked entry's provider is not configured, the wizard
# promotes the first surviving entry to default and prints a warning.

models:
  - display_name: "Claude Sonnet 4.6"
    model_id: "anthropic:claude-sonnet-4-6"
    provider: "anthropic"
    description: "Anthropic's flagship balanced reasoning model"
    is_default: true

  - display_name: "Claude Haiku 4.5"
    model_id: "anthropic:claude-haiku-4-5"
    provider: "anthropic"
    description: "Faster, cheaper Claude for high-volume workloads"

  - display_name: "GPT-4o"
    model_id: "openai:gpt-4o"
    provider: "openai"
    description: "OpenAI's flagship multimodal model"

  - display_name: "GPT-4o mini"
    model_id: "openai:gpt-4o-mini"
    provider: "openai"
    description: "Affordable, fast OpenAI option"

  - display_name: "Llama 3.2 (local)"
    model_id: "ollama:llama3.2"
    provider: "ollama"
    description: "Local Llama via Ollama — no API key required"
```

- [ ] **Step 2: Commit**

```bash
git add backend/seeds/models.yaml
git commit -m "feat(seeds): curated LLM catalogue for task bootstrap

Five entries spanning Anthropic, OpenAI, and Ollama. Wizard filters by
configured providers and inserts via on-conflict-skip. Update this file
to evolve the catalogue — no Python change required."
```

---

## Task 5: Pure helpers — `is_placeholder`, `generate_jwt_secret`, `configured_providers`

**Files:**
- Create: `backend/src/cli/__init__.py`
- Create: `backend/src/cli/bootstrap.py` (skeleton)
- Create: `backend/tests/cli/__init__.py`
- Create: `backend/tests/cli/test_helpers.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/src/cli/__init__.py` (empty file) and `backend/tests/cli/__init__.py` (empty file), then create `backend/tests/cli/test_helpers.py`:

```python
"""Unit tests for the pure helpers in src/cli/bootstrap."""
import re

import pytest

from src.cli.bootstrap import (
    configured_providers,
    generate_jwt_secret,
    is_placeholder,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", True),
        ("   ", True),
        ("sk-...", True),
        ("pk-...", True),
        ("your-key-here", True),
        ("...", True),
        ("sk-realbutfake", False),
        ("sk-abc123XYZdef456", False),
        ("anything-else", False),
    ],
)
def test_is_placeholder(value: str, expected: bool) -> None:
    assert is_placeholder(value) is expected


def test_generate_jwt_secret_is_64_hex_chars() -> None:
    secret = generate_jwt_secret()
    assert len(secret) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", secret)


def test_generate_jwt_secret_is_unique() -> None:
    # secrets.token_hex(32) gives 256 bits; collision probability is
    # negligible. Two calls must differ.
    assert generate_jwt_secret() != generate_jwt_secret()


def test_configured_providers_always_includes_ollama() -> None:
    assert configured_providers({}) == {"ollama"}


def test_configured_providers_detects_real_keys() -> None:
    env = {
        "ANTHROPIC_API_KEY": "real-anthropic-key",
        "OPENAI_API_KEY": "sk-real-openai-key",
        "OPENROUTER_API_KEY": "sk-or-real",
    }
    assert configured_providers(env) == {"ollama", "anthropic", "openai", "openrouter"}


def test_configured_providers_ignores_placeholders() -> None:
    env = {
        "ANTHROPIC_API_KEY": "",
        "OPENAI_API_KEY": "sk-...",
        "OPENROUTER_API_KEY": "your-key-here",
    }
    assert configured_providers(env) == {"ollama"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_helpers.py -v
```

Expected: ImportError / ModuleNotFoundError because `src/cli/bootstrap.py` does not exist.

- [ ] **Step 3: Implement the helpers**

Create `backend/src/cli/bootstrap.py`:

```python
"""Interactive bootstrap wizard for the agents-project-template.

Run via `task bootstrap`. Idempotent: re-runs skip already-configured
steps. See `docs/superpowers/specs/2026-05-23-onboarding-and-template-launch-design.md`
for the full design.
"""
from __future__ import annotations

import secrets

_PLACEHOLDER_VALUES = frozenset({"", "...", "sk-...", "pk-...", "your-key-here"})

_PROVIDER_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def is_placeholder(value: str) -> bool:
    """Return True if ``value`` looks like an unconfigured placeholder.

    Used by every step to decide whether to skip-or-prompt. Whitespace-only
    and the canonical placeholder strings count as placeholder; real keys
    (even fake-looking ones like 'sk-realbutfake') do not.
    """
    return value.strip() in _PLACEHOLDER_VALUES


def generate_jwt_secret() -> str:
    """Return a 64-hex-char random secret (256 bits of entropy)."""
    return secrets.token_hex(32)


def configured_providers(env: dict[str, str]) -> set[str]:
    """Return the set of LLM providers whose API key is non-placeholder in ``env``.

    Ollama is always included — it needs no API key (just a local daemon
    or a configured base URL).
    """
    providers = {"ollama"}
    for provider, var in _PROVIDER_KEY_ENV.items():
        if not is_placeholder(env.get(var, "")):
            providers.add(provider)
    return providers
```

- [ ] **Step 4: Run the tests to verify they pass**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_helpers.py -v
```

Expected: all 11 cases PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/__init__.py backend/src/cli/bootstrap.py backend/tests/cli/__init__.py backend/tests/cli/test_helpers.py
git commit -m "feat(cli): pure helpers for bootstrap wizard

- is_placeholder: detect unconfigured value strings
- generate_jwt_secret: 64 hex chars from secrets.token_hex(32)
- configured_providers: map env vars to LLM provider set"
```

---

## Task 6: `.env` file parser

**Files:**
- Modify: `backend/src/cli/bootstrap.py`
- Create: `backend/tests/cli/test_env_file.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/cli/test_env_file.py`:

```python
"""Tests for parse_env_file (read-only) and update_env_file (in-place mutate)."""
from pathlib import Path

import pytest

from src.cli.bootstrap import parse_env_file, update_env_file


def test_parse_env_file_basic(tmp_path: Path) -> None:
    f = tmp_path / ".env"
    f.write_text("FOO=bar\nBAZ=qux\n")
    assert parse_env_file(f) == {"FOO": "bar", "BAZ": "qux"}


def test_parse_env_file_skips_comments_and_blanks(tmp_path: Path) -> None:
    f = tmp_path / ".env"
    f.write_text("# header\n\nFOO=bar\n# BAR=commented\nBAZ=qux\n")
    assert parse_env_file(f) == {"FOO": "bar", "BAZ": "qux"}


def test_parse_env_file_handles_equals_in_value(tmp_path: Path) -> None:
    f = tmp_path / ".env"
    f.write_text("DSN=postgresql://u:p@h/db?foo=bar\n")
    assert parse_env_file(f) == {"DSN": "postgresql://u:p@h/db?foo=bar"}


def test_parse_env_file_missing_file_returns_empty(tmp_path: Path) -> None:
    assert parse_env_file(tmp_path / "does-not-exist") == {}


def test_update_env_file_creates_missing_file(tmp_path: Path) -> None:
    f = tmp_path / ".env"
    update_env_file(f, {"NEW": "value"})
    assert f.read_text() == "NEW=value\n"


def test_update_env_file_replaces_existing_value(tmp_path: Path) -> None:
    f = tmp_path / ".env"
    f.write_text("FOO=old\nBAR=keep\n")
    update_env_file(f, {"FOO": "new"})
    text = f.read_text()
    assert "FOO=new\n" in text
    assert "FOO=old" not in text
    assert "BAR=keep\n" in text


def test_update_env_file_uncomments_commented_key(tmp_path: Path) -> None:
    f = tmp_path / ".env"
    f.write_text("# FOO=template\nBAR=keep\n")
    update_env_file(f, {"FOO": "real"})
    text = f.read_text()
    assert "FOO=real\n" in text
    assert "# FOO=template" not in text
    assert "BAR=keep\n" in text


def test_update_env_file_appends_unknown_key(tmp_path: Path) -> None:
    f = tmp_path / ".env"
    f.write_text("FOO=bar\n")
    update_env_file(f, {"NEW": "v"})
    text = f.read_text()
    assert text == "FOO=bar\nNEW=v\n"


def test_update_env_file_preserves_comments_and_order(tmp_path: Path) -> None:
    f = tmp_path / ".env"
    f.write_text(
        "# header\nFOO=bar\n\n# section\nBAZ=qux\n",
    )
    update_env_file(f, {"NEW": "v"})
    text = f.read_text()
    # Original lines untouched, NEW appended
    assert text == "# header\nFOO=bar\n\n# section\nBAZ=qux\nNEW=v\n"


def test_update_env_file_multiple_updates(tmp_path: Path) -> None:
    f = tmp_path / ".env"
    f.write_text("# FOO=tmpl\nBAR=old\n")
    update_env_file(f, {"FOO": "f", "BAR": "b", "NEW": "n"})
    text = f.read_text()
    assert "FOO=f\n" in text
    assert "BAR=b\n" in text
    assert "NEW=n\n" in text
    assert "BAR=old" not in text
    assert "# FOO=tmpl" not in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_env_file.py -v
```

Expected: ImportError on `parse_env_file` and `update_env_file`.

- [ ] **Step 3: Implement the parser and updater**

Append to `backend/src/cli/bootstrap.py` (after `configured_providers`):

```python
from pathlib import Path


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a ``.env`` file into a ``{key: value}`` dict.

    Skips blank lines and comments. Splits on the FIRST ``=`` only, so
    values containing ``=`` (URLs, query strings) are preserved verbatim.
    Returns ``{}`` if the file does not exist.
    """
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value
    return result


def update_env_file(path: Path, updates: dict[str, str]) -> None:
    """Apply ``updates`` to a ``.env`` file in place.

    For each ``(key, value)``:

    * If an uncommented ``KEY=...`` line exists, its value is replaced.
    * If only a commented ``# KEY=...`` line exists, that line is rewritten
      as an uncommented assignment with the new value.
    * Otherwise the assignment is appended to the end of the file.

    Comments, blank lines, and line order are preserved for everything not
    being updated. Creates the file (with just the new assignments) if it
    does not yet exist.
    """
    if not path.exists():
        path.write_text(
            "".join(f"{k}={v}\n" for k, v in updates.items())
        )
        return

    new_lines: list[str] = []
    handled: set[str] = set()
    for raw in path.read_text().splitlines(keepends=True):
        replaced = False
        stripped = raw.lstrip()
        # Strip trailing newline for matching but keep for emission.
        body = stripped.rstrip("\n")
        for key, value in updates.items():
            if key in handled:
                continue
            # Uncommented KEY=...
            if body.startswith(f"{key}="):
                new_lines.append(f"{key}={value}\n")
                handled.add(key)
                replaced = True
                break
            # Commented "# KEY=..." (optional whitespace after the #).
            if body.startswith("#"):
                rest = body.lstrip("#").lstrip()
                if rest.startswith(f"{key}="):
                    new_lines.append(f"{key}={value}\n")
                    handled.add(key)
                    replaced = True
                    break
        if not replaced:
            new_lines.append(raw)

    for key, value in updates.items():
        if key not in handled:
            new_lines.append(f"{key}={value}\n")

    path.write_text("".join(new_lines))
```

Also add `from pathlib import Path` to the imports at the top of the file (move it up next to the other top-level imports — Ruff `I` rule will catch any disorder; run `task format` after editing if needed).

- [ ] **Step 4: Run the tests to verify they pass**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_env_file.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py backend/tests/cli/test_env_file.py
git commit -m "feat(cli): parse_env_file + update_env_file with preservation

update_env_file edits .env in place: replaces uncommented values,
uncomments commented placeholders, appends unknown keys at the end.
Preserves comments, blank lines, and ordering for everything else."
```

---

## Task 7: Seed catalogue loader + provider filter

**Files:**
- Modify: `backend/src/cli/bootstrap.py`
- Create: `backend/tests/cli/test_seed_loader.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/cli/test_seed_loader.py`:

```python
"""Tests for load_seed_catalogue + filter_seeds_by_providers."""
from pathlib import Path

import pytest

from src.cli.bootstrap import filter_seeds_by_providers, load_seed_catalogue


def _write_yaml(tmp_path: Path, body: str) -> Path:
    f = tmp_path / "models.yaml"
    f.write_text(body)
    return f


def test_load_seed_catalogue_basic(tmp_path: Path) -> None:
    f = _write_yaml(
        tmp_path,
        """
models:
  - display_name: "A"
    model_id: "anthropic:a"
    provider: "anthropic"
    is_default: true
  - display_name: "B"
    model_id: "openai:b"
    provider: "openai"
""",
    )
    catalogue = load_seed_catalogue(f)
    assert len(catalogue) == 2
    assert catalogue[0]["model_id"] == "anthropic:a"
    assert catalogue[0]["is_default"] is True


def test_load_seed_catalogue_rejects_multiple_defaults(tmp_path: Path) -> None:
    f = _write_yaml(
        tmp_path,
        """
models:
  - model_id: a
    provider: anthropic
    display_name: A
    is_default: true
  - model_id: b
    provider: openai
    display_name: B
    is_default: true
""",
    )
    with pytest.raises(ValueError, match="at most one"):
        load_seed_catalogue(f)


def test_load_seed_catalogue_missing_models_key(tmp_path: Path) -> None:
    f = _write_yaml(tmp_path, "other: data\n")
    assert load_seed_catalogue(f) == []


def test_filter_seeds_keeps_matching_providers() -> None:
    seeds = [
        {"model_id": "a", "provider": "anthropic", "display_name": "A", "is_default": True},
        {"model_id": "b", "provider": "openai", "display_name": "B"},
        {"model_id": "c", "provider": "ollama", "display_name": "C"},
    ]
    filtered = filter_seeds_by_providers(seeds, {"anthropic", "ollama"})
    assert [m["model_id"] for m in filtered] == ["a", "c"]


def test_filter_seeds_promotes_default_when_original_dropped() -> None:
    seeds = [
        {"model_id": "a", "provider": "anthropic", "display_name": "A", "is_default": True},
        {"model_id": "b", "provider": "openai", "display_name": "B"},
    ]
    filtered = filter_seeds_by_providers(seeds, {"openai"})
    assert len(filtered) == 1
    assert filtered[0]["model_id"] == "b"
    assert filtered[0]["is_default"] is True


def test_filter_seeds_keeps_existing_default_when_present() -> None:
    seeds = [
        {"model_id": "a", "provider": "anthropic", "display_name": "A", "is_default": True},
        {"model_id": "b", "provider": "openai", "display_name": "B"},
    ]
    filtered = filter_seeds_by_providers(seeds, {"anthropic", "openai"})
    assert [m["model_id"] for m in filtered] == ["a", "b"]
    assert filtered[0]["is_default"] is True
    assert filtered[1].get("is_default") in (False, None)


def test_filter_seeds_empty_when_no_match() -> None:
    seeds = [{"model_id": "a", "provider": "anthropic", "display_name": "A"}]
    assert filter_seeds_by_providers(seeds, {"openai"}) == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_seed_loader.py -v
```

Expected: ImportError on `load_seed_catalogue` and `filter_seeds_by_providers`.

- [ ] **Step 3: Implement loader and filter**

Append to `backend/src/cli/bootstrap.py`:

```python
import yaml


def load_seed_catalogue(path: Path) -> list[dict]:
    """Load and validate the model seed catalogue.

    Returns the list under the top-level ``models`` key (or ``[]`` if
    missing). Raises ``ValueError`` if more than one entry has
    ``is_default: true``.
    """
    data = yaml.safe_load(path.read_text()) or {}
    models = data.get("models") or []
    defaults = [m for m in models if m.get("is_default")]
    if len(defaults) > 1:
        raise ValueError(
            f"models.yaml: at most one entry may have is_default: true; "
            f"found {len(defaults)} ({', '.join(m['model_id'] for m in defaults)})"
        )
    return list(models)


def filter_seeds_by_providers(
    seeds: list[dict], providers: set[str]
) -> list[dict]:
    """Keep entries whose ``provider`` is in ``providers``.

    Guarantees that the returned list has exactly one ``is_default: True``
    entry when non-empty: if the originally-defaulted entry was filtered
    out, the first survivor is promoted. Original dicts are not mutated;
    a shallow-copied dict is substituted when promotion is needed.
    """
    filtered = [m for m in seeds if m.get("provider") in providers]
    if not filtered:
        return []
    if any(m.get("is_default") for m in filtered):
        return filtered
    promoted = {**filtered[0], "is_default": True}
    return [promoted, *filtered[1:]]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_seed_loader.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py backend/tests/cli/test_seed_loader.py
git commit -m "feat(cli): seed catalogue loader + provider filter

- load_seed_catalogue: parse YAML, validate at-most-one is_default
- filter_seeds_by_providers: drop entries without configured providers,
  promote first survivor to default if original default was filtered"
```

---

## Task 8: Pure step orchestrators — env file, JWT secret, DB password

**Files:**
- Modify: `backend/src/cli/bootstrap.py`
- Create: `backend/tests/cli/test_steps_env.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/cli/test_steps_env.py`:

```python
"""Tests for the env-mutating steps: env file copy, JWT secret, DB password."""
from pathlib import Path
from unittest.mock import patch

import pytest

from src.cli.bootstrap import (
    step_db_password,
    step_env_file,
    step_jwt_secret,
)


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
    assert len(parsed["JWT_SECRET_KEY"]) == 64


def test_step_jwt_secret_no_op_when_present(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    existing = "a" * 64
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
    assert len(line.split("=", 1)[1]) == 64


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


def test_step_db_password_aborts_when_non_interactive_and_missing(tmp_path: Path) -> None:
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_steps_env.py -v
```

Expected: ImportError on `step_env_file`, `step_jwt_secret`, `step_db_password`.

- [ ] **Step 3: Implement the step orchestrators**

Append to `backend/src/cli/bootstrap.py`. (You also need to import `Prompt` and `Console` from `rich` at the top — move all imports to the top per Ruff `I` rule.)

Final import block at the top of `bootstrap.py` should be:

```python
from __future__ import annotations

import secrets
from pathlib import Path

import yaml
from rich.console import Console
from rich.prompt import Confirm, Prompt
```

Append the step functions:

```python
def step_env_file(*, env_path: Path, example_path: Path, console: Console | None = None) -> None:
    """Step 1/8: ensure ``.env`` exists, copying from ``.env.example`` if missing."""
    console = console or Console()
    console.print("[bold cyan][1/8][/] .env file")
    if env_path.exists():
        console.print("      [dim]✓ already exists, skipping[/]")
        return
    if not example_path.exists():
        raise FileNotFoundError(
            f".env.example not found at {example_path}; cannot bootstrap"
        )
    env_path.write_text(example_path.read_text())
    console.print(f"      [green]✓[/] Copied {example_path.name} → {env_path.name}")


def step_jwt_secret(*, env_path: Path, console: Console | None = None) -> None:
    """Step 2/8: generate a JWT secret if the .env value is empty or too short."""
    console = console or Console()
    console.print("[bold cyan][2/8][/] JWT secret")
    current = parse_env_file(env_path).get("JWT_SECRET_KEY", "")
    if len(current) >= 32 and not is_placeholder(current):
        console.print("      [dim]✓ already configured, skipping[/]")
        return
    secret = generate_jwt_secret()
    update_env_file(env_path, {"JWT_SECRET_KEY": secret})
    console.print("      [green]✓[/] Wrote 64-char secret to .env")


def step_db_password(
    *,
    env_path: Path,
    interactive: bool,
    env_value: str | None,
    console: Console | None = None,
) -> None:
    """Step 3/8: ensure POSTGRES_PASSWORD is set.

    Interactive: prompts (hidden) if missing. Non-interactive: reads from
    ``env_value`` (typically ``os.environ["POSTGRES_PASSWORD"]``) and
    aborts with ``RuntimeError`` if neither source is available.
    """
    console = console or Console()
    console.print("[bold cyan][3/8][/] Database password")
    current = parse_env_file(env_path).get("POSTGRES_PASSWORD", "")
    if not is_placeholder(current):
        console.print("      [dim]✓ already configured, skipping[/]")
        return
    if interactive:
        value = Prompt.ask(
            "      ? POSTGRES_PASSWORD is empty. Enter a password",
            password=True,
        )
    else:
        if not env_value:
            raise RuntimeError(
                "Non-interactive bootstrap requires POSTGRES_PASSWORD in the "
                "environment (or set it in .env before running)."
            )
        value = env_value
    update_env_file(env_path, {"POSTGRES_PASSWORD": value})
    console.print("      [green]✓[/] Saved to .env")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_steps_env.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py backend/tests/cli/test_steps_env.py
git commit -m "feat(cli): env/jwt/db-password step orchestrators

Three idempotent steps:
- step_env_file: copy .env.example -> .env if missing
- step_jwt_secret: generate secret if absent or shorter than 32 chars
- step_db_password: prompt (interactive) or read env var (non-interactive)"
```

---

## Task 9: LLM provider keys step

**Files:**
- Modify: `backend/src/cli/bootstrap.py`
- Create: `backend/tests/cli/test_steps_llm.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/cli/test_steps_llm.py`:

```python
"""Tests for step_llm_keys (interactive + non-interactive)."""
import os
from pathlib import Path
from unittest.mock import patch

from src.cli.bootstrap import step_llm_keys


def _env(tmp_path: Path, body: str = "") -> Path:
    p = tmp_path / ".env"
    p.write_text(body)
    return p


def test_step_llm_keys_interactive_yes_anthropic(tmp_path: Path) -> None:
    env_path = _env(tmp_path)
    with patch("src.cli.bootstrap.Confirm.ask", side_effect=[True, False, False]):
        with patch("src.cli.bootstrap.Prompt.ask", return_value="real-key"):
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
    # Exactly two confirms: openai + openrouter (anthropic was skipped).
    assert len(confirm_calls) == 2


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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_steps_llm.py -v
```

Expected: ImportError on `step_llm_keys`.

- [ ] **Step 3: Implement the step**

Append to `backend/src/cli/bootstrap.py`:

```python
_PROVIDER_DISPLAY = {
    "anthropic": ("Anthropic", "ANTHROPIC_API_KEY"),
    "openai": ("OpenAI", "OPENAI_API_KEY"),
    "openrouter": ("OpenRouter", "OPENROUTER_API_KEY"),
}


def step_llm_keys(
    *,
    env_path: Path,
    interactive: bool,
    env_values: dict[str, str],
    console: Console | None = None,
) -> None:
    """Step 4/8: collect LLM provider API keys.

    For each provider whose key is missing or placeholder in ``.env``:

    * Interactive: ask Yes/No, then prompt for the key (hidden).
    * Non-interactive: write the value from ``env_values`` if present and
      non-placeholder; otherwise skip silently.

    Already-configured providers are skipped in both modes.
    """
    console = console or Console()
    console.print("[bold cyan][4/8][/] LLM provider keys")
    current = parse_env_file(env_path)
    updates: dict[str, str] = {}
    for _provider, (label, var) in _PROVIDER_DISPLAY.items():
        if not is_placeholder(current.get(var, "")):
            console.print(f"      [dim]✓ {label}: already configured, skipping[/]")
            continue
        if interactive:
            wants = Confirm.ask(
                f"      ? Do you have a {label} API key?", default=False
            )
            if not wants:
                console.print(f"      [dim]Skipped {label}[/]")
                continue
            value = Prompt.ask(f"      ? Paste your {label} key", password=True)
            updates[var] = value
            console.print(f"      [green]✓[/] Saved {var}")
        else:
            value = env_values.get(var, "")
            if is_placeholder(value):
                continue
            updates[var] = value
            console.print(f"      [green]✓[/] Saved {var} from environment")
    if updates:
        update_env_file(env_path, updates)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_steps_llm.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py backend/tests/cli/test_steps_llm.py
git commit -m "feat(cli): LLM provider keys step

Asks per-provider in interactive mode (skips already-configured),
reads from env_values in non-interactive mode. Placeholder values
(sk-..., empty) are ignored in both modes."
```

---

## Task 10: Postgres + migrations steps

**Files:**
- Modify: `backend/src/cli/bootstrap.py`
- Create: `backend/tests/cli/test_steps_infra.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/cli/test_steps_infra.py`:

```python
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


def test_step_postgres_skips_when_already_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_steps_infra.py -v
```

Expected: ImportError on `step_postgres`, `step_migrations`.

- [ ] **Step 3: Implement the steps**

Append to `backend/src/cli/bootstrap.py`. Add to the top imports:

```python
import subprocess
import time
```

Append the step implementations:

```python
_POSTGRES_HEALTH_TIMEOUT_SECS = 60
_POSTGRES_POLL_INTERVAL_SECS = 2


def _postgres_health() -> str:
    """Return the container's Health value (e.g. 'healthy', 'starting', '')."""
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "ps",
                "postgres",
                "--format",
                "{{.Health}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as err:
        raise RuntimeError(
            "Docker daemon not reachable. Start Docker Desktop and re-run."
        ) from err
    return result.stdout.strip().lower()


def step_postgres(*, console: Console | None = None) -> None:
    """Step 5/8: ensure the Postgres container is running and healthy."""
    console = console or Console()
    console.print("[bold cyan][5/8][/] PostgreSQL container")
    if _postgres_health() == "healthy":
        console.print("      [dim]✓ already healthy, skipping[/]")
        return
    console.print("      ⟳ Starting postgres via docker compose...")
    subprocess.run(
        ["docker", "compose", "up", "postgres", "-d"],
        check=False,
        capture_output=True,
        text=True,
    )
    deadline = time.monotonic() + _POSTGRES_HEALTH_TIMEOUT_SECS
    while time.monotonic() < deadline:
        if _postgres_health() == "healthy":
            console.print("      [green]✓[/] Postgres is healthy on :5432")
            return
        time.sleep(_POSTGRES_POLL_INTERVAL_SECS)
    raise RuntimeError(
        "Postgres did not become healthy in 60s. "
        "Check 'docker compose logs postgres'."
    )


def step_migrations(*, console: Console | None = None) -> None:
    """Step 6/8: run alembic upgrade head if not already at head."""
    console = console or Console()
    console.print("[bold cyan][6/8][/] Database migrations")
    current = subprocess.run(
        ["uv", "run", "alembic", "current"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    heads = subprocess.run(
        ["uv", "run", "alembic", "heads"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    # `alembic current` prints "<rev> (head)" when at head; compare the
    # first whitespace-delimited token on each side for a robust check.
    current_rev = current.split()[0] if current else ""
    heads_rev = heads.split()[0] if heads else ""
    if current_rev and current_rev == heads_rev:
        console.print("      [dim]✓ schema up to date, skipping[/]")
        return
    console.print("      ⟳ Running alembic upgrade head...")
    subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        check=True,
    )
    console.print("      [green]✓[/] Schema up to date")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_steps_infra.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py backend/tests/cli/test_steps_infra.py
git commit -m "feat(cli): postgres + migrations step orchestrators

- step_postgres: bring up + poll healthcheck (60s timeout, 2s interval)
- step_migrations: skip when alembic current == heads, else upgrade
Both wrap docker / alembic shellouts and emit Rich-formatted progress."
```

---

## Task 11: Admin user step (async DB)

**Files:**
- Modify: `backend/src/cli/bootstrap.py`
- Create: `backend/tests/cli/test_steps_db.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/cli/test_steps_db.py`:

```python
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


async def test_step_admin_non_interactive_password_too_short(session: AsyncMock) -> None:
    session.execute = _execute_returning(None)
    with pytest.raises(RuntimeError, match=">= 8"):
        await step_admin(
            session=session,
            interactive=False,
            env_email="a@b.c",
            env_password="short",
        )


async def test_step_admin_interactive_loops_on_short_password(session: AsyncMock) -> None:
    session.execute = _execute_returning(None)
    # First password too short, second OK; first confirm matches second pw.
    prompts = iter(["a@b.c", "short", "longerpassword", "longerpassword"])
    with patch("src.cli.bootstrap.Prompt.ask", side_effect=lambda *a, **kw: next(prompts)):
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
    prompts = iter(["a@b.c", "longpassword", "mismatched-confirm", "longpassword", "longpassword"])
    with patch("src.cli.bootstrap.Prompt.ask", side_effect=lambda *a, **kw: next(prompts)):
        await step_admin(
            session=session,
            interactive=True,
            env_email=None,
            env_password=None,
        )
    added = session.add.call_args.args[0]
    assert added.email == "a@b.c"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_steps_db.py -v
```

Expected: ImportError on `step_admin` and `step_seed_models`.

- [ ] **Step 3: Implement `step_admin`**

Add to the top imports of `bootstrap.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import _hash_password
from src.models.user import User
```

Append:

```python
_MIN_ADMIN_PASSWORD_LEN = 8


async def step_admin(
    *,
    session: AsyncSession,
    interactive: bool,
    env_email: str | None,
    env_password: str | None,
    console: Console | None = None,
) -> None:
    """Step 7/8: ensure at least one admin user exists."""
    console = console or Console()
    console.print("[bold cyan][7/8][/] Admin user")
    existing = (
        await session.execute(
            select(User).where(User.is_admin.is_(True)).limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        console.print("      [dim]✓ admin already exists, skipping[/]")
        return
    if interactive:
        email = Prompt.ask("      ? Admin email")
        password = _prompt_admin_password(console)
    else:
        if not env_email:
            raise RuntimeError(
                "Non-interactive bootstrap requires BOOTSTRAP_ADMIN_EMAIL."
            )
        if not env_password or len(env_password) < _MIN_ADMIN_PASSWORD_LEN:
            raise RuntimeError(
                "Non-interactive bootstrap requires BOOTSTRAP_ADMIN_PASSWORD "
                f"(>= {_MIN_ADMIN_PASSWORD_LEN} chars)."
            )
        email = env_email
        password = env_password
    user = User(
        email=email,
        password_hash=_hash_password(password),
        name="Admin",
        is_admin=True,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    console.print(f"      [green]✓[/] Created admin {email}")


def _prompt_admin_password(console: Console) -> str:
    """Loop until the user enters a >=8-char password and confirms it correctly."""
    while True:
        pw = Prompt.ask(
            f"      ? Admin password (min {_MIN_ADMIN_PASSWORD_LEN} chars)",
            password=True,
        )
        if len(pw) < _MIN_ADMIN_PASSWORD_LEN:
            console.print(
                f"      [yellow]Password must be at least "
                f"{_MIN_ADMIN_PASSWORD_LEN} characters.[/]"
            )
            continue
        confirm = Prompt.ask("      ? Confirm password", password=True)
        if pw != confirm:
            console.print("      [yellow]Passwords do not match. Try again.[/]")
            continue
        return pw
```

- [ ] **Step 4: Run the admin tests to verify they pass**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_steps_db.py -v -k step_admin
```

Expected: 6 admin tests PASS. The seed-model tests still fail (next task).

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py backend/tests/cli/test_steps_db.py
git commit -m "feat(cli): admin user step

Skips if any admin exists. Interactive: prompts email + password with
confirm-loop and min-length enforcement. Non-interactive: reads
BOOTSTRAP_ADMIN_EMAIL / BOOTSTRAP_ADMIN_PASSWORD."
```

---

## Task 12: Seed models step (async DB)

**Files:**
- Modify: `backend/src/cli/bootstrap.py`
- Modify: `backend/tests/cli/test_steps_db.py`

- [ ] **Step 1: Extend the test file with seed-model tests**

Append to `backend/tests/cli/test_steps_db.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify the new ones fail**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_steps_db.py -v -k step_seed_models
```

Expected: ImportError on `step_seed_models`.

- [ ] **Step 3: Implement `step_seed_models`**

Add to the imports of `bootstrap.py`:

```python
from src.models.llm_model import LLMModel
```

Append:

```python
async def step_seed_models(
    *,
    session: AsyncSession,
    seeds_path: Path,
    providers: set[str],
    console: Console | None = None,
) -> None:
    """Step 8/8: insert LLM models filtered by ``providers``.

    Idempotent: entries already present (matched by ``model_id``) are
    skipped silently. At most one inserted entry has ``is_default=True``
    (guaranteed by :func:`filter_seeds_by_providers`).
    """
    console = console or Console()
    console.print("[bold cyan][8/8][/] Seed LLM models")
    catalogue = load_seed_catalogue(seeds_path)
    filtered = filter_seeds_by_providers(catalogue, providers)
    if not filtered:
        console.print(
            "      [yellow]No models match configured providers; skipping[/]"
        )
        return
    existing_rows = (
        await session.execute(select(LLMModel.model_id))
    ).all()
    existing = {row[0] for row in existing_rows}
    inserted = 0
    default_chosen: str | None = None
    for entry in filtered:
        if entry["model_id"] in existing:
            continue
        model = LLMModel(
            display_name=entry["display_name"],
            model_id=entry["model_id"],
            provider=entry["provider"],
            description=entry.get("description"),
            is_default=bool(entry.get("is_default")),
            is_active=True,
        )
        session.add(model)
        inserted += 1
        if model.is_default:
            default_chosen = model.model_id
    if inserted:
        await session.commit()
        suffix = f" · default: {default_chosen}" if default_chosen else ""
        console.print(f"      [green]✓[/] Inserted {inserted} models{suffix}")
    else:
        console.print("      [dim]✓ all models already seeded, skipping[/]")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_steps_db.py -v
```

Expected: all 10 DB-step tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py backend/tests/cli/test_steps_db.py
git commit -m "feat(cli): seed LLM models step

Inserts entries from seeds/models.yaml filtered by configured providers.
Idempotent (skips model_ids already present); ensures exactly one
default among inserted entries when applicable."
```

---

## Task 13: `main()` entry point + CLI

**Files:**
- Modify: `backend/src/cli/bootstrap.py`

- [ ] **Step 1: Implement `main()` and `__main__` block**

Append to `backend/src/cli/bootstrap.py`:

```python
import argparse
import asyncio
import os
import sys

from rich.panel import Panel
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Resolve paths relative to backend/ (this file lives in backend/src/cli/).
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ENV_PATH = _BACKEND_ROOT / ".env"
_ENV_EXAMPLE_PATH = _BACKEND_ROOT / ".env.example"
_SEEDS_PATH = _BACKEND_ROOT / "seeds" / "models.yaml"


def _print_welcome(console: Console) -> None:
    console.print(
        Panel.fit(
            "agents-project-template · Bootstrap\n"
            "This wizard sets up your project from zero to running.\n"
            "Safe to re-run: each step checks current state.",
            border_style="cyan",
        )
    )


def _print_complete(console: Console) -> None:
    console.print(
        Panel.fit(
            "[green]✓ Bootstrap complete[/]\n\n"
            "Next steps:\n"
            "  backend:   task run\n"
            "  frontend:  cd ../frontend && npm install && npm run dev\n\n"
            "Login at http://localhost:3000\n"
            "API docs at http://localhost:2026/docs",
            border_style="green",
        )
    )


async def _run_db_steps(
    *,
    db_url: str,
    interactive: bool,
    env_email: str | None,
    env_password: str | None,
    providers: set[str],
    console: Console,
) -> None:
    """Open an async session and execute steps 7 + 8."""
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            await step_admin(
                session=session,
                interactive=interactive,
                env_email=env_email,
                env_password=env_password,
                console=console,
            )
            await step_seed_models(
                session=session,
                seeds_path=_SEEDS_PATH,
                providers=providers,
                console=console,
            )
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="task bootstrap",
        description=(
            "Interactive wizard that takes a fresh clone to a running backend. "
            "Safe to re-run; each of the 8 steps skips when already configured."
        ),
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help=(
            "Skip prompts. Reads BOOTSTRAP_ADMIN_EMAIL, "
            "BOOTSTRAP_ADMIN_PASSWORD, POSTGRES_PASSWORD, and the LLM API "
            "key env vars. Aborts if required values are missing."
        ),
    )
    args = parser.parse_args(argv)
    interactive = not args.non_interactive

    console = Console()
    _print_welcome(console)

    try:
        # Steps 1-4: .env mutations (sync).
        step_env_file(
            env_path=_ENV_PATH,
            example_path=_ENV_EXAMPLE_PATH,
            console=console,
        )
        step_jwt_secret(env_path=_ENV_PATH, console=console)
        step_db_password(
            env_path=_ENV_PATH,
            interactive=interactive,
            env_value=os.environ.get("POSTGRES_PASSWORD"),
            console=console,
        )
        step_llm_keys(
            env_path=_ENV_PATH,
            interactive=interactive,
            env_values=dict(os.environ),
            console=console,
        )
        # Steps 5-6: infra.
        step_postgres(console=console)
        step_migrations(console=console)
        # Steps 7-8: DB.
        # Re-read .env so settings sees the values we just wrote.
        env = parse_env_file(_ENV_PATH)
        for key, value in env.items():
            os.environ.setdefault(key, value)
        # Import settings *after* env is hydrated so Settings() picks
        # up POSTGRES_PASSWORD, JWT_SECRET_KEY, etc.
        from src.core.settings import settings
        asyncio.run(
            _run_db_steps(
                db_url=settings.db_url,
                interactive=interactive,
                env_email=os.environ.get("BOOTSTRAP_ADMIN_EMAIL"),
                env_password=os.environ.get("BOOTSTRAP_ADMIN_PASSWORD"),
                providers=configured_providers(env),
                console=console,
            )
        )
    except RuntimeError as err:
        console.print(f"\n[red]Error:[/] {err}")
        return 1
    except FileNotFoundError as err:
        console.print(f"\n[red]Error:[/] {err}")
        return 1

    _print_complete(console)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Sanity-check that the module imports cleanly**

Run from `backend/`:
```bash
uv run python -c "from src.cli import bootstrap; print(bootstrap.main.__name__)"
```

Expected: prints `main`.

- [ ] **Step 3: Verify --help works**

Run from `backend/`:
```bash
uv run python -m src.cli.bootstrap --help
```

Expected: argparse help text mentioning `--non-interactive`.

- [ ] **Step 4: Run the lint + the existing CLI test suite**

Run from `backend/`:
```bash
uv run task lint
uv run pytest tests/cli/ -v
```

Expected: lint clean, all CLI tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py
git commit -m "feat(cli): main() entry point wiring the 8 steps

Steps 1-4 (.env mutations) and 5-6 (infra) are sync. Steps 7-8 open a
fresh async engine using the .env values just written, run admin +
seed in a single session, then dispose the engine. RuntimeError /
FileNotFoundError print a red error and exit 1."
```

---

## Task 14: Smoke E2E + idempotency

**Files:**
- Create: `backend/tests/cli/test_bootstrap_flow.py`

- [ ] **Step 1: Write the test**

Create `backend/tests/cli/test_bootstrap_flow.py`:

```python
"""End-to-end smoke + idempotency test for the bootstrap wizard.

External boundaries (Docker, Alembic, real DB) are mocked. The goal is
to prove the orchestration sequence and that a second run is a no-op.
"""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cli import bootstrap


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
    secret_line = next(ln for ln in text.splitlines() if ln.startswith("JWT_SECRET_KEY="))
    assert len(secret_line.split("=", 1)[1]) == 64
    # DB steps ran exactly once.
    assert len(db_calls) == 1
    assert db_calls[0]["providers"] == {"ollama", "anthropic"}

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
    monkeypatch.setattr("src.cli.bootstrap.subprocess.run", lambda *a, **kw: _ok("healthy\n"))

    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.delenv("BOOTSTRAP_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)

    code = bootstrap.main(["--non-interactive"])
    assert code == 1
```

- [ ] **Step 2: Run the test to verify it passes**

Run from `backend/`:
```bash
uv run pytest tests/cli/test_bootstrap_flow.py -v
```

Expected: both tests PASS.

- [ ] **Step 3: Run the full CLI suite + lint**

Run from `backend/`:
```bash
uv run task lint
uv run pytest tests/cli/ -v
```

Expected: lint clean, all tests across `tests/cli/` PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/cli/test_bootstrap_flow.py
git commit -m "test(cli): smoke E2E + idempotency for bootstrap wizard

Two cases:
- Full non-interactive run writes .env and invokes the DB step block;
  second run with identical state leaves .env byte-for-byte unchanged.
- Non-interactive abort when required BOOTSTRAP_* / POSTGRES_PASSWORD
  env vars are missing returns exit code 1."
```

---

## Task 15: README pointer to `task bootstrap`

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add the Quick start block above the existing setup**

Open `README.md`. After the `## Pré-requisitos` section and before `## Passo a passo: do clone ao primeiro agente`, insert (English — the full English rewrite happens in Phase 2):

```markdown
---

## Quick start (recommended)

After installing the prerequisites above:

```bash
cd backend
uv sync
task bootstrap
```

The interactive wizard generates secrets, starts PostgreSQL, runs migrations,
creates an admin account, and seeds the LLM catalogue. Safe to re-run.

Then start the servers:

```bash
# Terminal 1
task run                                  # backend on :2026

# Terminal 2
cd ../frontend && npm install && npm run dev   # frontend on :3000
```

Log in at <http://localhost:3000>.

The manual setup below remains documented for transparency.

---
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(readme): add Quick start pointer to task bootstrap

The full README rewrite (English-only, restructured) happens in Phase 2;
this minimal addition gives the wizard a discoverable entry point in
the meantime."
```

---

## Task 16: Final integration sanity check

**Files:**
- (No file changes — runs the full suite as a release gate.)

- [ ] **Step 1: Run the entire backend test suite**

Run from `backend/`:
```bash
uv run task test
```

Expected: all tests PASS (existing suite + new CLI suite); coverage report still ≥ 85 %.

- [ ] **Step 2: Run lint**

Run from `backend/`:
```bash
uv run task lint
```

Expected: ruff clean, mypy clean.

- [ ] **Step 3: Manual smoke (optional, if Docker is available locally)**

If you have Docker running and want to validate the wizard end-to-end against a real DB, temporarily move your existing `.env` aside and run:

```bash
mv backend/.env backend/.env.bak 2>/dev/null || true
docker compose -f backend/docker-compose.yml down -v
cd backend
task bootstrap
```

Walk through the prompts; verify the wizard exits 0, that `.env` contains the values you provided, and that `task run` boots without errors. Then restore your original env:

```bash
cd ..
docker compose -f backend/docker-compose.yml down -v
mv backend/.env.bak backend/.env 2>/dev/null || true
```

Skip this step if Docker isn't available — the automated tests already exercise the orchestration logic.

- [ ] **Step 4: Phase 1 done**

No commit for this task — it is a verification gate. Open the next plan (Phase 2: README + LICENSE + CI) when ready.

---

## Verification matrix

After all tasks complete, this matrix should be all green:

| Requirement (from spec) | Implemented in | Verified by |
|---|---|---|
| Front B.1: sanitise `.env.example` | Task 1 | `test_env_example_safety.py` |
| Front B.2: docker-compose fail-fast | Task 2 | manual `docker compose config` checks |
| Front B.3: regression test | Task 1 | `test_env_example_safety.py` |
| Front A.1: file layout | Tasks 5, 7, 8-13 | imports resolve, lint passes |
| Front A.2: rich + pyyaml deps | Task 3 | `uv sync`, lockfile |
| Front A.3: 8-step wizard flow | Tasks 8, 9, 10, 11, 12, 13 | individual `test_steps_*.py` |
| Front A.4: idempotency contract | Tasks 8-12 | each step has a "skip when present" test; Task 14 second-run check |
| Front A.5: non-interactive mode | Tasks 8, 9, 11, 13 | env-var tests in each + Task 14 abort test |
| Front A.6: error handling | Tasks 10, 13 | `test_steps_infra.py` (timeout, docker missing) + `main()` exit-1 paths |
| Front A.7: seeds/models.yaml | Task 4 | `test_seed_loader.py` covers loader, Task 12 covers insert |
| Front A.8: pyproject task | Task 3 | `task --list` smoke |
