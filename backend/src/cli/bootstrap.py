"""Interactive bootstrap wizard for the agents-project-template.

Run via `task bootstrap`. Idempotent: re-runs skip already-configured
steps. See `docs/superpowers/specs/2026-05-23-onboarding-and-template-launch-design.md`
for the full design.
"""
from __future__ import annotations

import secrets
from pathlib import Path

import yaml
from rich.console import Console
from rich.prompt import Prompt

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
    seeds: list[dict],
    providers: set[str],
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
