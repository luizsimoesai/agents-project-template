"""Interactive bootstrap wizard for the agents-project-template.

Run via `uv run task bootstrap`. Idempotent: re-runs skip already-configured
steps. See `docs/superpowers/specs/2026-05-23-onboarding-and-template-launch-design.md`
for the full design.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models.llm_model import LLMModel
from src.models.user import User

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
            # Suppress uncommented assignment lines for keys already handled
            # (avoids duplicates when both a commented and uncommented version
            # of the same key appear in the file).
            if "=" in body and not body.startswith("#"):
                line_key = body.split("=", 1)[0].strip()
                if line_key in handled:
                    continue
            new_lines.append(raw)

    for key, value in updates.items():
        if key not in handled:
            new_lines.append(f"{key}={value}\n")

    path.write_text("".join(new_lines))


def load_seed_catalogue(path: Path) -> list[dict[str, object]]:
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
    seeds: list[dict[str, object]],
    providers: set[str],
) -> list[dict[str, object]]:
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


def step_env_file(
    *, env_path: Path, example_path: Path, console: Console | None = None
) -> None:
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
    if len(current) >= 32 and not is_placeholder(current):  # noqa: PLR2004
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
    # Imported lazily (not at module top) so loading this module does not
    # eagerly instantiate Settings() via src.core.security -> src.core.settings
    # before steps 1-4 have created .env. See the matching settings import in main().
    from src.core.security import _hash_password  # noqa: PLC0415

    user = User(  # type: ignore[call-arg]
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
    """Loop until the user enters a valid password and confirms it correctly."""
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


async def step_seed_models(  # noqa: PLR0913
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
            "  backend:   uv run task run\n"
            "  frontend:  cd ../frontend && npm install && npm run dev\n\n"
            "Login at http://localhost:3000\n"
            "API docs at http://localhost:2026/docs",
            border_style="green",
        )
    )


async def _run_db_steps(  # noqa: PLR0913
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
        prog="uv run task bootstrap",
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
        from src.core.settings import settings  # noqa: PLC0415
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
