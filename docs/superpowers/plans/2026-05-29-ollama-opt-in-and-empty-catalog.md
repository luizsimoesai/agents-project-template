# Ollama Opt-In & Empty Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Ollama an explicit opt-in in `task bootstrap` (free-text model name instead of forcing `ollama:llama3.2`), stop auto-defaulting a model the user didn't choose, treat an empty catalog as a valid state, and guard the chat input when no models are configured.

**Architecture:** Backend change is confined to `backend/src/cli/bootstrap.py` and `backend/seeds/models.yaml`. Ollama becomes a `.env` step (records `OLLAMA_MODEL`/`OLLAMA_BASE_URL`); the actual catalog row is seeded in the DB phase by `step_seed_models`, which also elects a single default. Frontend change is confined to `frontend/components/chat/ChatInput.tsx` (disable send + show a notice when the active-model list is empty).

**Tech Stack:** Python 3.12, pytest (async), Rich (CLI), SQLAlchemy async; Next.js 16 / React 19, Vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-05-29-ollama-opt-in-and-empty-catalog-design.md`

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `backend/seeds/models.yaml` | Curated cloud catalogue | Remove the Ollama entry |
| `backend/src/cli/bootstrap.py` | Wizard steps + orchestration | `configured_providers`, new `step_ollama`, extend `step_seed_models`, `_run_db_steps` return, `_print_complete` warning, `main()` wiring, step renumbering, argparse help |
| `backend/.env.example` | Documented env vars | Add commented `OLLAMA_MODEL` / `OLLAMA_BASE_URL` |
| `backend/tests/cli/test_helpers.py` | `configured_providers` tests | Update for no-forced-ollama |
| `backend/tests/cli/test_steps_db.py` | seed-step tests | Add Ollama + default-election tests |
| `backend/tests/cli/test_steps_env.py` | env-step tests | Add `step_ollama` tests |
| `backend/tests/cli/test_bootstrap_flow.py` | E2E orchestration | Update providers assertion + step count |
| `frontend/components/chat/ChatInput.tsx` | Chat composer | Empty-catalog guard |
| `frontend/components/chat/ChatInput.test.tsx` | Guard test | Create |

---

## Task 1: Remove Ollama from the curated catalogue

**Files:**
- Modify: `backend/seeds/models.yaml`

- [ ] **Step 1: Remove the Ollama entry**

Delete the last entry so the file ends after the GPT-4o mini entry. The full file becomes:

```yaml
# Curated LLM catalogue used by `task bootstrap`.
#
# Wizard inserts only entries whose `provider` matches a configured API key.
# Ollama is NOT listed here — it is opt-in via the wizard's Ollama step
# (free-text model name) and seeded separately.
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
```

- [ ] **Step 2: Verify the catalogue still loads (no Ollama)**

Run: `cd backend && uv run pytest tests/cli/test_seed_loader.py -q`
Expected: PASS (these tests build their own YAML and don't depend on the shipped file).

- [ ] **Step 3: Commit**

```bash
git add backend/seeds/models.yaml
git commit -m "feat(cli): make catalogue cloud-only (drop forced Ollama seed)"
```

---

## Task 2: `configured_providers` no longer auto-includes Ollama

**Files:**
- Modify: `backend/src/cli/bootstrap.py` (`configured_providers`, lines ~53-63)
- Test: `backend/tests/cli/test_helpers.py` (lines ~46-65)

- [ ] **Step 1: Update the failing tests**

Replace the three `configured_providers` tests in `tests/cli/test_helpers.py` with:

```python
def test_configured_providers_empty_when_no_keys() -> None:
    assert configured_providers({}) == set()


def test_configured_providers_detects_real_keys() -> None:
    env = {
        "ANTHROPIC_API_KEY": "real-anthropic",
        "OPENAI_API_KEY": "real-openai",
        "OPENROUTER_API_KEY": "real-openrouter",
    }
    assert configured_providers(env) == {"anthropic", "openai", "openrouter"}


def test_configured_providers_ignores_placeholders() -> None:
    env = {
        "ANTHROPIC_API_KEY": "",
        "OPENAI_API_KEY": "sk-...",
        "OPENROUTER_API_KEY": "your-key-here",
    }
    assert configured_providers(env) == set()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/cli/test_helpers.py -q`
Expected: FAIL (current code returns `{"ollama"}` for empty/placeholder env).

- [ ] **Step 3: Update `configured_providers`**

Replace the function in `src/cli/bootstrap.py`:

```python
def configured_providers(env: dict[str, str]) -> set[str]:
    """Return the set of cloud LLM providers whose API key is non-placeholder.

    Ollama is intentionally NOT included here. It needs no API key and is opt-in
    via :func:`step_ollama` (free-text model name), then seeded separately in
    :func:`step_seed_models` — it is not driven by catalogue/provider filtering.
    """
    providers: set[str] = set()
    for provider, var in _PROVIDER_KEY_ENV.items():
        if not is_placeholder(env.get(var, "")):
            providers.add(provider)
    return providers
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/cli/test_helpers.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py backend/tests/cli/test_helpers.py
git commit -m "feat(cli): configured_providers no longer forces ollama"
```

---

## Task 3: New `step_ollama` (.env step)

**Files:**
- Modify: `backend/src/cli/bootstrap.py` (add `_OLLAMA_DEFAULT_BASE_URL` constant + `step_ollama`, after `step_llm_keys` / `_PROVIDER_DISPLAY`)
- Test: `backend/tests/cli/test_steps_env.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/cli/test_steps_env.py` (add `step_ollama` to the import from `src.cli.bootstrap`):

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/cli/test_steps_env.py -q`
Expected: FAIL with `ImportError: cannot import name 'step_ollama'`.

- [ ] **Step 3: Implement `step_ollama`**

In `src/cli/bootstrap.py`, add the constant and function immediately after the `step_llm_keys` function (after the block ending `update_env_file(env_path, updates)`):

```python
_OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"


def step_ollama(
    *,
    env_path: Path,
    interactive: bool,
    env_value: str | None,
    console: Console | None = None,
) -> None:
    """Step 5/9: optionally record a local Ollama model in .env.

    Unlike cloud providers (which need an API key), Ollama needs only a model
    name. This step writes ``OLLAMA_MODEL`` (and a default ``OLLAMA_BASE_URL``)
    to ``.env``; the catalog row itself is seeded later by
    :func:`step_seed_models`. This step never touches the DB.

    Interactive: ask Yes/No, then prompt for the model name. Non-interactive:
    use ``env_value`` (typically ``os.environ["OLLAMA_MODEL"]``); skip if absent.
    Skips entirely when ``.env`` already has a non-placeholder ``OLLAMA_MODEL``.
    """
    console = console or Console()
    console.print("[bold cyan][5/9][/] Ollama model (optional)")
    parsed = parse_env_file(env_path)
    if not is_placeholder(parsed.get("OLLAMA_MODEL", "")):
        console.print("      [dim]✓ already configured, skipping[/]")
        return
    if interactive:
        if not Confirm.ask("      ? Use a local Ollama model?", default=False):
            console.print("      [dim]Skipped Ollama[/]")
            return
        name = Prompt.ask("      ? Ollama model name (e.g. llama3.2)")
    else:
        name = env_value or ""
    if is_placeholder(name):
        return
    updates = {"OLLAMA_MODEL": name}
    if is_placeholder(parsed.get("OLLAMA_BASE_URL", "")):
        updates["OLLAMA_BASE_URL"] = _OLLAMA_DEFAULT_BASE_URL
    update_env_file(env_path, updates)
    console.print(f"      [green]✓[/] Saved OLLAMA_MODEL={name} to .env")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/cli/test_steps_env.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py backend/tests/cli/test_steps_env.py
git commit -m "feat(cli): add opt-in step_ollama .env step"
```

---

## Task 4: Extend `step_seed_models` with Ollama seeding + default election

**Files:**
- Modify: `backend/src/cli/bootstrap.py` (`step_seed_models`, lines ~456-504)
- Test: `backend/tests/cli/test_steps_db.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/cli/test_steps_db.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/cli/test_steps_db.py -q`
Expected: FAIL with `TypeError: step_seed_models() got an unexpected keyword argument 'ollama_model'`.

- [ ] **Step 3: Replace `step_seed_models`**

Replace the whole `step_seed_models` function in `src/cli/bootstrap.py` with:

```python
async def step_seed_models(
    *,
    session: AsyncSession,
    seeds_path: Path,
    providers: set[str],
    ollama_model: str | None = None,
    ollama_base_url: str | None = None,
    console: Console | None = None,
) -> None:
    """Step 9/9: insert cloud catalogue models (filtered by ``providers``) plus
    an optional Ollama model.

    Idempotent: entries already present (matched by ``model_id``) are skipped.
    Exactly one inserted entry is ``is_default=True`` — the cloud catalogue's
    default when a cloud provider is configured, otherwise the Ollama model,
    otherwise none (empty catalog).
    """
    console = console or Console()
    console.print("[bold cyan][9/9][/] Seed LLM models")
    catalogue = load_seed_catalogue(seeds_path)
    filtered = filter_seeds_by_providers(catalogue, providers)
    # Ollama is a code-built entry (not in the catalogue). It becomes the default
    # only when no cloud model was configured.
    if not is_placeholder(ollama_model or ""):
        filtered = [
            *filtered,
            {
                "display_name": f"{ollama_model} (local)",
                "model_id": f"ollama:{ollama_model}",
                "provider": "ollama",
                "description": "Local model via Ollama",
                "base_url": ollama_base_url or _OLLAMA_DEFAULT_BASE_URL,
                "is_default": len(filtered) == 0,
            },
        ]
    if not filtered:
        console.print("      [yellow]No models configured; catalog is empty[/]")
        return
    existing_rows = (await session.execute(select(LLMModel.model_id))).all()
    existing = {row[0] for row in existing_rows}
    inserted = 0
    default_chosen: str | None = None
    for entry in filtered:
        if entry["model_id"] in existing:
            continue
        model = LLMModel(  # type: ignore[call-arg]
            display_name=entry["display_name"],
            model_id=entry["model_id"],
            provider=entry["provider"],
            description=entry.get("description"),
            base_url=entry.get("base_url"),
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/cli/test_steps_db.py -q`
Expected: PASS (new tests + the existing `test_step_seed_models_*` tests, which call without the Ollama kwargs).

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py backend/tests/cli/test_steps_db.py
git commit -m "feat(cli): seed opt-in Ollama model and elect single default"
```

---

## Task 5: Renumber steps + wire `step_ollama` and Ollama seeding into `main()`

**Files:**
- Modify: `backend/src/cli/bootstrap.py` (`step_postgres`, `step_migrations`, `step_admin`, `step_env_file`, `step_jwt_secret`, `step_db_password`, `step_llm_keys` labels; `_run_db_steps`; `main`)

- [ ] **Step 1: Renumber the wizard step labels**

Apply these exact `console.print` label replacements in `src/cli/bootstrap.py`:

| Function | From | To |
|---|---|---|
| `step_env_file` | `[1/8]` | `[1/9]` |
| `step_jwt_secret` | `[2/8]` | `[2/9]` |
| `step_db_password` | `[3/8]` | `[3/9]` |
| `step_llm_keys` | `[4/8]` | `[4/9]` |
| `step_postgres` | `[5/8]` | `[6/9]` |
| `step_migrations` | `[6/8]` | `[7/9]` |
| `step_admin` | `[7/8]` | `[8/9]` |

(`step_ollama` is `[5/9]` and `step_seed_models` is `[9/9]` — already set in Tasks 3 and 4.)

- [ ] **Step 2: Update `_run_db_steps` to pass Ollama args and return catalog-empty**

Replace `_run_db_steps` with (adds `ollama_model`/`ollama_base_url` params, returns `bool`):

```python
async def _run_db_steps(  # noqa: PLR0913
    *,
    db_url: str,
    interactive: bool,
    env_email: str | None,
    env_password: str | None,
    providers: set[str],
    ollama_model: str | None,
    ollama_base_url: str | None,
    console: Console,
) -> bool:
    """Open an async session and execute steps 8 + 9.

    Returns True when the catalog ended up empty (no models at all), so the
    caller can warn the user to add one in /admin.
    """
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
                ollama_model=ollama_model,
                ollama_base_url=ollama_base_url,
                console=console,
            )
            result = await session.execute(select(LLMModel.id).limit(1))
            return result.first() is None
    finally:
        await engine.dispose()
```

- [ ] **Step 3: Call `step_ollama` in `main()` and capture the catalog-empty flag**

In `main()`, after the `step_llm_keys(...)` call, insert:

```python
        step_ollama(
            env_path=_ENV_PATH,
            interactive=interactive,
            env_value=os.environ.get("OLLAMA_MODEL"),
            console=console,
        )
```

Then replace the `asyncio.run(_run_db_steps(...))` call so it passes the Ollama values (read from the re-hydrated `env`). Do **not** capture the return yet — that happens in Task 6 (capturing it now would leave an unused variable until then):

```python
        asyncio.run(
            _run_db_steps(
                db_url=settings.db_url,
                interactive=interactive,
                env_email=os.environ.get("BOOTSTRAP_ADMIN_EMAIL"),
                env_password=os.environ.get("BOOTSTRAP_ADMIN_PASSWORD"),
                providers=configured_providers(env),
                ollama_model=env.get("OLLAMA_MODEL"),
                ollama_base_url=env.get("OLLAMA_BASE_URL"),
                console=console,
            )
        )
```

- [ ] **Step 4: Run the full CLI suite**

Run: `cd backend && uv run pytest tests/cli/ -q`
Expected: PASS except `test_bootstrap_flow.py` (fixed in Task 7) — note any failures there but do not fix yet.

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py
git commit -m "feat(cli): wire step_ollama into main and renumber to /9"
```

---

## Task 6: Empty-catalog warning in the completion panel

**Files:**
- Modify: `backend/src/cli/bootstrap.py` (`_print_complete`, lines ~525-536; the call in `main()`)
- Test: `backend/tests/cli/test_bootstrap_flow.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/cli/test_bootstrap_flow.py` (add `import io` and `from rich.console import Console` at the top alongside the existing imports):

```python
def test_print_complete_warns_when_catalog_empty() -> None:
    buf = io.StringIO()
    bootstrap._print_complete(Console(file=buf, width=100), catalog_empty=True)
    assert "No LLM model configured" in buf.getvalue()


def test_print_complete_no_warning_when_catalog_has_model() -> None:
    buf = io.StringIO()
    bootstrap._print_complete(Console(file=buf, width=100), catalog_empty=False)
    assert "No LLM model configured" not in buf.getvalue()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/cli/test_bootstrap_flow.py -k print_complete -q`
Expected: FAIL with `TypeError: _print_complete() got an unexpected keyword argument 'catalog_empty'`.

- [ ] **Step 3: Update `_print_complete` and its call site**

Replace `_print_complete` in `src/cli/bootstrap.py`:

```python
def _print_complete(console: Console, *, catalog_empty: bool = False) -> None:
    warning = (
        "\n\n[yellow]⚠ No LLM model configured. Add one at "
        "http://localhost:3000/admin before chatting.[/]"
        if catalog_empty
        else ""
    )
    console.print(
        Panel.fit(
            "[green]✓ Bootstrap complete[/]\n\n"
            "Next steps:\n"
            "  backend:   uv run task run\n"
            "  frontend:  cd ../frontend && npm install && npm run dev\n\n"
            "Login at http://localhost:3000\n"
            "API docs at http://localhost:2026/docs" + warning,
            border_style="green",
        )
    )
```

In `main()`, capture the `_run_db_steps` return and pass it to `_print_complete`.

First, add the assignment to the `asyncio.run(_run_db_steps(...))` call (from Task 5):

```python
        catalog_empty = asyncio.run(
            _run_db_steps(
```

(only the first line changes — the `_run_db_steps(...)` arguments stay as wired in Task 5.)

Then replace the final `_print_complete(console)` call with:

```python
    _print_complete(console, catalog_empty=bool(catalog_empty))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/cli/test_bootstrap_flow.py -k print_complete -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/cli/bootstrap.py backend/tests/cli/test_bootstrap_flow.py
git commit -m "feat(cli): warn in completion panel when catalog is empty"
```

---

## Task 7: Update E2E flow test, `.env.example`, and argparse help

**Files:**
- Modify: `backend/tests/cli/test_bootstrap_flow.py` (lines ~80-139)
- Modify: `backend/.env.example` (LLM block, after the `MODEL_BASE_URL` comment)
- Modify: `backend/src/cli/bootstrap.py` (argparse `--non-interactive` help text, lines ~578-586)

- [ ] **Step 1: Fix the providers assertion and add Ollama-kwarg checks**

In `test_bootstrap_flow.py`, in `test_bootstrap_full_run_then_idempotent_rerun`, the stub `fake_db_steps` already uses `**kwargs`. Change the post-run assertions block:

Replace:
```python
    # DB steps ran exactly once.
    assert len(db_calls) == 1
    assert db_calls[0]["providers"] == {"ollama", "anthropic"}
```
with:
```python
    # DB steps ran exactly once.
    assert len(db_calls) == 1
    assert db_calls[0]["providers"] == {"anthropic"}
    # No Ollama configured in this non-interactive run.
    assert db_calls[0]["ollama_model"] is None
```

- [ ] **Step 2: Make the stub return a catalog-empty flag**

In the same test, change the stub so `main()` receives a bool (not `None`):

Replace:
```python
    async def fake_db_steps(**kwargs):
        db_calls.append(kwargs)
```
with:
```python
    async def fake_db_steps(**kwargs):
        db_calls.append(kwargs)
        return False  # catalog not empty
```

- [ ] **Step 3: Run the flow test to verify it passes**

Run: `cd backend && uv run pytest tests/cli/test_bootstrap_flow.py -q`
Expected: PASS (all tests in the file, including the fresh-clone import regression and the idempotent rerun).

- [ ] **Step 4: Document the new env vars in `.env.example`**

In `backend/.env.example`, immediately after the line:
```
# MODEL_BASE_URL=https://litellm.example.com/v1  # optional: Ollama or proxy base URL
```
add:
```
# OLLAMA_MODEL=llama3.2                   # optional: local Ollama model name (no API key)
# OLLAMA_BASE_URL=http://localhost:11434  # optional: Ollama server URL (default shown)
```

- [ ] **Step 5: Mention `OLLAMA_MODEL` in the `--non-interactive` help**

In `src/cli/bootstrap.py`, in the `--non-interactive` argument's `help=`, replace:
```python
            "Skip prompts. Reads BOOTSTRAP_ADMIN_EMAIL, "
            "BOOTSTRAP_ADMIN_PASSWORD, POSTGRES_PASSWORD, and the LLM API "
            "key env vars. Aborts if required values are missing."
```
with:
```python
            "Skip prompts. Reads BOOTSTRAP_ADMIN_EMAIL, "
            "BOOTSTRAP_ADMIN_PASSWORD, POSTGRES_PASSWORD, OLLAMA_MODEL, and the "
            "LLM API key env vars. Aborts if required values are missing."
```

- [ ] **Step 6: Run lint, type-check, and the full backend suite**

Run: `cd backend && uv run task lint && uv run pytest tests/ -q`
Expected: PASS (ruff + mypy clean; all tests green).

- [ ] **Step 7: Commit**

```bash
git add backend/tests/cli/test_bootstrap_flow.py backend/.env.example backend/src/cli/bootstrap.py
git commit -m "test(cli): update flow test for opt-in Ollama; document env vars"
```

---

## Task 8: Frontend empty-catalog guard in `ChatInput`

**Files:**
- Modify: `frontend/components/chat/ChatInput.tsx`
- Test: `frontend/components/chat/ChatInput.test.tsx` (create)

- [ ] **Step 1: Write the failing test**

Create `frontend/components/chat/ChatInput.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ChatInput } from "./ChatInput"
import type { ModelRead } from "@/lib/types"

const models: ModelRead[] = [
  {
    id: "1", display_name: "Claude", model_id: "anthropic:claude-sonnet-4-6",
    provider: "anthropic", description: null, base_url: null,
    is_active: true, is_default: true,
    created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
  },
]

describe("ChatInput", () => {
  it("shows a notice and keeps send disabled when no models exist", async () => {
    render(
      <ChatInput
        onSubmit={vi.fn()} onStop={vi.fn()} isStreaming={false}
        models={[]} selectedModelId="" onModelChange={vi.fn()}
      />,
    )
    expect(screen.getByText(/no model configured/i)).toBeInTheDocument()
    await userEvent.type(screen.getByPlaceholderText(/message/i), "hello")
    // Only the send button is present (no model-picker combobox).
    expect(screen.getByRole("button")).toBeDisabled()
  })

  it("enables send after typing when models exist", async () => {
    render(
      <ChatInput
        onSubmit={vi.fn()} onStop={vi.fn()} isStreaming={false}
        models={models} selectedModelId="anthropic:claude-sonnet-4-6"
        onModelChange={vi.fn()}
      />,
    )
    expect(screen.queryByText(/no model configured/i)).not.toBeInTheDocument()
    await userEvent.type(screen.getByPlaceholderText(/message/i), "hello")
    expect(screen.getByRole("button")).not.toBeDisabled()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test:run -- ChatInput`
Expected: FAIL (no "no model configured" notice rendered; send button enabled).

- [ ] **Step 3: Implement the guard**

In `frontend/components/chat/ChatInput.tsx`:

Replace the `handleSend` early-return and the `showPicker` derivation. First, change `handleSend`:

```tsx
  function handleSend() {
    const msg = value.trim()
    if (!msg || isStreaming || noModels) return
    onSubmit(msg)
    setValue("")
    ref.current?.focus()
  }
```

Replace:
```tsx
  const showPicker = !!models && models.length > 0 && !!onModelChange
```
with:
```tsx
  const hasPicker = !!onModelChange && Array.isArray(models)
  const noModels = hasPicker && models!.length === 0
  const showPicker = hasPicker && models!.length > 0
```

Add the notice block right after the `{showPicker && ( ... )}` block (before `<div className="relative flex items-end ...">`):

```tsx
        {noModels && (
          <div className="flex items-center px-3 py-2 border-b border-border/40 bg-muted/20">
            <p className="font-mono text-xs text-muted-foreground">
              No model configured — ask an admin to add one in /admin.
            </p>
          </div>
        )}
```

Change the send button's `disabled` to also account for `noModels`:

```tsx
              disabled={!value.trim() || disabled || noModels}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test:run -- ChatInput`
Expected: PASS

- [ ] **Step 5: Run the full frontend suite**

Run: `cd frontend && npm run test:run`
Expected: PASS (no regressions in `ModelPicker`/`ChatView` tests).

- [ ] **Step 6: Commit**

```bash
git add frontend/components/chat/ChatInput.tsx frontend/components/chat/ChatInput.test.tsx
git commit -m "feat(chat): disable send and show notice when no models configured"
```

---

## Final verification

- [ ] **Backend:** `cd backend && uv run task lint && uv run pytest tests/ -q` → all green.
- [ ] **Frontend:** `cd frontend && npm run test:run` → all green.
- [ ] **Manual smoke (optional, needs Docker + Ollama):** fresh `.env`-less dir → `uv run task bootstrap`, decline all keys, decline Ollama → completion panel shows the empty-catalog warning; the admin `/admin` page lists zero models; chat input shows the "no model configured" notice with send disabled.
