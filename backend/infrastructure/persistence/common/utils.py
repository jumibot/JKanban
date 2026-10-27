"""Shared persistence utilities — engine-agnostic.

No imports from sqlite3, psycopg2 or any specific driver.
"""
from datetime import datetime, timezone
from typing import Any


# ── Time helpers ──────────────────────────────────────────────────────────────

def utcnow() -> str:
    """Current UTC time as ISO-8601 string (no timezone suffix).

    Computed in Python, never delegated to a SQL DEFAULT expression like
    datetime('now') or NOW().  That keeps the timestamp format consistent
    across engines and independent of DB server clock drift.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# Legacy alias — lets existing callers keep `_now()` without a change.
_now = utcnow


def dt_str(val: datetime | None) -> str | None:
    """Serialise a datetime to the ISO-8601 string stored in the database.
    Returns None when val is None (NULL column).
    """
    return val.isoformat() if val else None


# ── Row helpers ───────────────────────────────────────────────────────────────

def row_opt(row: Any, col: str) -> Any | None:
    """Return row[col], or None if the column is absent or NULL.

    Works with sqlite3.Row (has .keys()) and dict-like rows from other
    drivers, as long as they support subscript access and .keys().
    """
    return row[col] if col in row.keys() and row[col] is not None else None


def to_datetime(v: Any) -> datetime | None:
    """Normalise a DB timestamp value to a naive UTC datetime (or None).

    Engines differ in what they return for a timestamp column:
      - SQLite stores TEXT → ISO-8601 string
      - PostgreSQL TIMESTAMP[TZ] → datetime (possibly timezone-aware)
    Domain entities use naive UTC datetimes, so aware values are converted.
    """
    if not v:
        return None
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    if v.tzinfo is not None:
        v = v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


def row_dt(row: Any, col: str) -> datetime | None:
    """Return row[col] as a naive UTC datetime, or None."""
    return to_datetime(row_opt(row, col))


# ── Placeholder helper ────────────────────────────────────────────────────────

def ph(n: int) -> str:
    """Return n comma-separated %s placeholders: '%s, %s, …'

    Use for IN (...) clauses:
        f"WHERE id IN ({ph(len(ids))})"

    The %s style is engine-neutral at the repository level.  The SQLite
    connection wrapper translates %s → ? before reaching sqlite3.
    """
    return ", ".join(["%s"] * n)
