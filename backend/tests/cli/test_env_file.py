"""Tests for parse_env_file (read-only) and update_env_file (in-place mutate)."""
from pathlib import Path

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


def test_update_env_file_no_duplicate_when_both_present(tmp_path: Path) -> None:
    f = tmp_path / ".env"
    f.write_text("# FOO=template\nFOO=existing\n")
    update_env_file(f, {"FOO": "new"})
    text = f.read_text()
    assert text.count("FOO=") == 1
    assert "FOO=new\n" in text
