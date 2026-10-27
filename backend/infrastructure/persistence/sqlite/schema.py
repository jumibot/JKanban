"""SQLite schema — CREATE TABLE statements.

This module is intentionally SQLite-specific.  It uses:
  - INTEGER PRIMARY KEY AUTOINCREMENT  (vs SERIAL / GENERATED ALWAYS AS IDENTITY in PG)
  - datetime('now') DEFAULT            (vs NOW() / CURRENT_TIMESTAMP in PG)
  - SUBSTR(...)                        (vs SUBSTRING(...) in PG)
  - TEXT for booleans and timestamps   (vs BOOLEAN / TIMESTAMPTZ in PG)

⚠ Circular FK between projects and priorities:
  projects.priority_id → priorities.id
  priorities.project_id → projects.id
  SQLite creates these without validation.  PostgreSQL would require either:
    (a) creating projects first without priority_id, then ALTER TABLE to add it, or
    (b) DEFERRABLE INITIALLY DEFERRED constraints.
  This must be resolved before adding a PostgreSQL adapter.
"""


def create_schema(conn) -> None:
    """Create all tables if they don't exist yet.

    Receives an open connection (SQLiteConnection wrapper).
    The caller is responsible for committing.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            avatar_url    TEXT,
            is_admin      INTEGER NOT NULL DEFAULT 0 CHECK(is_admin IN (0,1)),
            created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
            modified_at   TEXT,
            created_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
            modified_by   INTEGER REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS priorities (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            icon        TEXT NOT NULL DEFAULT 'flag',
            color       TEXT NOT NULL DEFAULT '#6B7280' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            modified_at TEXT,
            created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            UNIQUE(name, project_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            description TEXT,
            icon        TEXT    NOT NULL DEFAULT 'folder',
            color       TEXT    NOT NULL DEFAULT '#3B82F6' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
            owner_id    INTEGER NOT NULL REFERENCES users(id),
            leader_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            priority_id INTEGER REFERENCES priorities(id) ON DELETE SET NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            modified_at TEXT,
            created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_members (
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            user_id    INTEGER NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            PRIMARY KEY (project_id, user_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            description TEXT,
            color       TEXT    NOT NULL DEFAULT '#3B82F6' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            sort_order  INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            modified_at TEXT,
            created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id           INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
            user_id            INTEGER REFERENCES users(id) ON DELETE SET NULL,
            priority_id        INTEGER REFERENCES priorities(id) ON DELETE SET NULL,
            title              TEXT    NOT NULL,
            description        TEXT,
            completed          INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
            estimated_duration REAL,
            estimated_start    TEXT,
            estimated_end      TEXT,
            actual_start       TEXT,
            actual_end         TEXT,
            sort_order         INTEGER NOT NULL DEFAULT 0,
            created_at         TEXT    NOT NULL DEFAULT (datetime('now')),
            modified_at        TEXT,
            created_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
            modified_by        INTEGER REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS todo_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            title       TEXT    NOT NULL,
            completed   INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
            sort_order  INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            modified_at TEXT,
            created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flows (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            modified_at TEXT,
            created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flow_states (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            flow_id     INTEGER NOT NULL REFERENCES flows(id) ON DELETE CASCADE,
            name        TEXT NOT NULL,
            color       TEXT NOT NULL DEFAULT '#6B7280' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
            sort_order  INTEGER NOT NULL DEFAULT 0,
            is_initial  BOOLEAN NOT NULL DEFAULT 0,
            UNIQUE(flow_id, name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flow_transitions (
            flow_id       INTEGER NOT NULL REFERENCES flows(id) ON DELETE CASCADE,
            from_state_id INTEGER NOT NULL REFERENCES flow_states(id) ON DELETE CASCADE,
            to_state_id   INTEGER NOT NULL REFERENCES flow_states(id) ON DELETE CASCADE,
            PRIMARY KEY (from_state_id, to_state_id),
            CHECK (from_state_id <> to_state_id)
        )
    """)
    # project_id NULL = global tag. Name uniqueness across scopes is checked
    # in TagUseCases (UNIQUE does not treat NULLs as equal).
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
            color       TEXT NOT NULL DEFAULT '#6B7280' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
            flow_id     INTEGER REFERENCES flows(id) ON DELETE SET NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            modified_at TEXT,
            created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
            modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            UNIQUE(name, project_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_tags (
            task_id    INTEGER NOT NULL REFERENCES tasks(id)  ON DELETE CASCADE,
            tag_id     INTEGER NOT NULL REFERENCES tags(id)   ON DELETE CASCADE,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            state_id   INTEGER REFERENCES flow_states(id) ON DELETE SET NULL,
            PRIMARY KEY (task_id, tag_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS group_tags (
            group_id   INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
            tag_id     INTEGER NOT NULL REFERENCES tags(id)   ON DELETE CASCADE,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            state_id   INTEGER REFERENCES flow_states(id) ON DELETE SET NULL,
            PRIMARY KEY (group_id, tag_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS flow_state_changes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id    INTEGER REFERENCES tasks(id)  ON DELETE CASCADE,
            group_id   INTEGER REFERENCES groups(id) ON DELETE CASCADE,
            tag_id     INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            from_state TEXT,
            to_state   TEXT,
            note       TEXT,
            changed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            changed_at TEXT NOT NULL DEFAULT (datetime('now')),
            CHECK ((task_id IS NULL) <> (group_id IS NULL))
        )
    """)
