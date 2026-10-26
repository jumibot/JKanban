"""Guards for the persistence layer.

1. Repositories stay engine-agnostic: no SQLite-only SQL, driver imports,
   positional row access or int-encoded booleans.
2. Routers, use cases and domain never touch persistence directly.
3. get_connection() closes the connection when the `with` block ends.
4. The factory rejects unknown engines.
5. Timestamps are normalised whatever type the driver returns.
"""
import ast
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.infrastructure.persistence import factory
from backend.infrastructure.persistence.common.utils import to_datetime

_BACKEND = Path(__file__).parent.parent / "backend"
_REPOS = sorted((_BACKEND / "infrastructure" / "repositories").glob("*.py"))
_UPPER_LAYERS = sorted(
    p for d in ("domain", "application", "interfaces")
    for p in (_BACKEND / d).rglob("*.py")
)
_SQL_RE = re.compile(
    r"\bSELECT\b.+\bFROM\b|\bINSERT\s+INTO\b|\bUPDATE\s+\w+\s+SET\b|\bDELETE\s+FROM\b",
    re.IGNORECASE | re.DOTALL,
)

# (regex over source text, how to fix it)
_FORBIDDEN_IN_REPOS = [
    (re.compile(r"\blastrowid\b"), "usa insert_returning_id() del factory"),
    (re.compile(r"INSERT\s+OR\s+(IGNORE|REPLACE)", re.IGNORECASE), "usa idempotent_insert() del factory"),
    (re.compile(r"^\s*(import sqlite3|from sqlite3\b)", re.MULTILINE), "sqlite3 solo dentro de persistence/sqlite/"),
    (re.compile(r"persistence\.sqlite\b"), "importa desde persistence.factory, no desde un engine concreto"),
    (re.compile(r"fetch(one|all)\(\)\s*\[\s*\d+\s*\]"), "accede por nombre: SELECT COUNT(*) AS n … row['n']"),
    (re.compile(r"\bint\(\s*\w+\.(completed|is_admin)\s*\)"), "pasa bool(...): BOOLEAN no acepta enteros en PostgreSQL"),
    (re.compile(r"SUM\(\s*\w*\.?completed\s*\)", re.IGNORECASE), "usa SUM(CASE WHEN completed THEN 1 ELSE 0 END)"),
    (re.compile(r"datetime\.fromisoformat"), "usa row_dt()/to_datetime(): el driver puede devolver datetime"),
]

_FORBIDDEN_IN_UPPER_LAYERS = [
    (re.compile(r"\bpersistence\b"), "el acceso a BD va en repositorios; usa un caso de uso"),
    (re.compile(r"\bget_connection\b"), "el acceso a BD va en repositorios; usa un caso de uso"),
    (re.compile(r"^\s*(import sqlite3|from sqlite3\b)", re.MULTILINE), "sqlite3 solo dentro de persistence/sqlite/"),
]


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


def _problems(path: Path, rules) -> list[str]:
    source = path.read_text(encoding="utf-8")
    return [
        f"{path.name}: '{m.group(0).strip()}' → {fix}"
        for regex, fix in rules
        for m in regex.finditer(source)
    ]


@pytest.mark.parametrize("path", _REPOS, ids=lambda p: p.name)
def test_repository_is_engine_agnostic(path: Path):
    problems = _problems(path, _FORBIDDEN_IN_REPOS)
    problems += [
        f"{path.name}:{line}: placeholder '?' en SQL → usa %s"
        for line, text in _sql_strings(ast.parse(path.read_text(encoding="utf-8")))
        if "?" in text
    ]
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize(
    "path", _UPPER_LAYERS, ids=lambda p: str(p.relative_to(_BACKEND)).replace("\\", "/")
)
def test_upper_layers_do_not_touch_persistence(path: Path):
    problems = _problems(path, _FORBIDDEN_IN_UPPER_LAYERS)
    if path.parent.name == "routers":
        problems += [
            f"{path.name}:{line}: SQL en un router → muévelo a un repositorio"
            for line, _ in _sql_strings(ast.parse(path.read_text(encoding="utf-8")))
        ]
    assert not problems, "\n".join(problems)


# ── Connection lifecycle ──────────────────────────────────────────────────────

def test_connection_is_closed_after_with_block():
    with factory.get_connection() as conn:
        assert conn.execute("SELECT 1 AS n").fetchone()["n"] == 1
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


# ── Timestamp normalisation ───────────────────────────────────────────────────

@pytest.mark.parametrize("value, expected", [
    (None, None),
    ("", None),
    ("2026-10-26T08:30:00", datetime(2026, 10, 26, 8, 30)),                 # SQLite TEXT
    (datetime(2026, 10, 26, 8, 30), datetime(2026, 10, 26, 8, 30)),         # TIMESTAMP
    (datetime(2026, 10, 26, 10, 30, tzinfo=timezone(timedelta(hours=2))),   # TIMESTAMPTZ
     datetime(2026, 10, 26, 8, 30)),
])
def test_to_datetime_normalises_driver_values(value, expected):
    assert to_datetime(value) == expected
