"""Guards for the persistence layer.

1. Code outside persistence/ must stay engine-agnostic: no SQLite-only SQL
   or driver imports in repositories and routers.
2. get_connection() must close the connection when the `with` block ends.
3. The factory must reject unknown engines.
"""
import ast
import re
from pathlib import Path

import pytest

from backend.infrastructure.persistence import factory

_BACKEND = Path(__file__).parent.parent / "backend"
_CHECKED_DIRS = [
    _BACKEND / "infrastructure" / "repositories",
    _BACKEND / "interfaces" / "routers",
]
_SQL_RE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)

# (regex over source text, reason shown when it matches)
_FORBIDDEN = [
    (re.compile(r"\blastrowid\b"), "usa insert_returning_id() del factory"),
    (re.compile(r"INSERT\s+OR\s+(IGNORE|REPLACE)", re.IGNORECASE), "usa idempotent_insert() del factory"),
    (re.compile(r"^\s*(import sqlite3|from sqlite3\b)", re.MULTILINE), "sqlite3 solo dentro de persistence/sqlite/"),
    (re.compile(r"persistence\.sqlite\b"), "importa desde persistence.factory, no desde un engine concreto"),
]


def _checked_files() -> list[Path]:
    return [p for d in _CHECKED_DIRS for p in sorted(d.glob("*.py"))]


def _sql_strings(tree: ast.AST):
    """Yield (lineno, text) for every string literal / f-string that looks like SQL."""
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            text = "".join(
                v.value for v in node.values
                if isinstance(v, ast.Constant) and isinstance(v.value, str)
            )
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value
        else:
            continue
        if _SQL_RE.search(text):
            yield node.lineno, text


@pytest.mark.parametrize("path", _checked_files(), ids=lambda p: p.name)
def test_no_sqlite_specific_code(path: Path):
    source = path.read_text(encoding="utf-8")
    problems = [
        f"{path.name}: '{m.group(0).strip()}' → {reason}"
        for regex, reason in _FORBIDDEN
        for m in regex.finditer(source)
    ]
    problems += [
        f"{path.name}:{line}: placeholder '?' en SQL → usa %s"
        for line, text in _sql_strings(ast.parse(source))
        if "?" in text
    ]
    assert not problems, "\n".join(problems)


def test_connection_is_closed_after_with_block():
    with factory.get_connection() as conn:
        assert conn.execute("SELECT 1").fetchone()[0] == 1
    with pytest.raises(Exception):
        conn.execute("SELECT 1")


def test_connection_is_closed_after_error_in_with_block():
    with pytest.raises(ZeroDivisionError):
        with factory.get_connection() as conn:
            1 / 0
    with pytest.raises(Exception):
        conn.execute("SELECT 1")


def test_unsupported_engine_is_rejected(monkeypatch):
    monkeypatch.setenv("DB_ENGINE", "oracle")
    with pytest.raises(ValueError, match="Unsupported DB engine"):
        factory.get_connection()
    with pytest.raises(ValueError, match="Unsupported DB engine"):
        factory.insert_returning_id(None, "INSERT INTO x VALUES (%s)", (1,))
