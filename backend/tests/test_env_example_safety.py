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
