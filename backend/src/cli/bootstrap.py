"""Interactive bootstrap wizard for the agents-project-template.

Run via `task bootstrap`. Idempotent: re-runs skip already-configured
steps. See `docs/superpowers/specs/2026-05-23-onboarding-and-template-launch-design.md`
for the full design.
"""
from __future__ import annotations

import secrets
from pathlib import Path

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
            new_lines.append(raw)

    for key, value in updates.items():
        if key not in handled:
            new_lines.append(f"{key}={value}\n")

    path.write_text("".join(new_lines))
