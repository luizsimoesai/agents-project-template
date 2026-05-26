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
