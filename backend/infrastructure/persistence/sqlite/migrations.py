"""SQLite schema migrations.

Ad-hoc, introspection-based migrations that bring old databases up to the
current schema without data loss.

⚠ SQLite-specific throughout:
  - sqlite_master    — used to enumerate tables and read DDL strings
  - PRAGMA table_info, foreign_key_list — column/FK introspection
  - PRAGMA foreign_keys = OFF/ON — required to rebuild tables
  - Table-rebuild pattern (CREATE new + INSERT SELECT + DROP old + RENAME)
    because SQLite cannot drop columns or modify constraints in-place.

When adding a PostgreSQL adapter, implement proper versioned migrations
(e.g. with Alembic or numbered SQL files) instead of this introspection
pattern, which is specific to SQLite's limited ALTER TABLE support.
"""


def _fk_off(conn) -> None:
    """Disable FK enforcement before rebuilding a table.

    PRAGMA foreign_keys is a no-op inside an open transaction, and any earlier
    DML in migrate() opens one. Without the commit, DROP TABLE would
    cascade-delete the rows of every child table.
    """
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")


def _fk_on(conn) -> None:
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def migrate(conn) -> None:
    """Apply all pending schema migrations to an open connection.

    The caller is responsible for committing after this returns.
    """
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    # ── resources → users ────────────────────────────────────────────────────
    if "resources" in tables and "users" not in tables:
        conn.execute("ALTER TABLE resources RENAME TO users")
        tables.add("users")
        tables.discard("resources")

    if "resources" in tables:
        conn.execute("DROP TABLE IF EXISTS resources")
        tables.discard("resources")

    if "users" in tables:
        ucols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
        for col, typedef in [
            ("password_hash", "TEXT NOT NULL DEFAULT 'changeme'"),
            ("is_admin",      "INTEGER NOT NULL DEFAULT 0"),
            ("modified_at",   "TEXT"),
            ("created_by",    "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by",   "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in ucols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")
        if conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=1").fetchone()[0] == 0:
            conn.execute(
                "UPDATE users SET is_admin=1 WHERE id=(SELECT MIN(id) FROM users)"
            )
        _u_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone() or [""])[0]
        if "CHECK(is_admin IN (0,1))" not in _u_sql:
            _fk_off(conn)
            conn.execute("DROP TABLE IF EXISTS users_new")
            conn.execute("""
                CREATE TABLE users_new (
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
                INSERT INTO users_new
                    (id, name, email, password_hash, avatar_url, is_admin,
                     created_at, modified_at, created_by, modified_by)
                SELECT id, name, email, password_hash, avatar_url, is_admin,
                       created_at, modified_at, created_by, modified_by
                FROM users
            """)
            conn.execute("DROP TABLE users")
            conn.execute("ALTER TABLE users_new RENAME TO users")
            _fk_on(conn)

    # ── projects: fix stale FK leader_id → resources ──────────────────────────
    if "projects" in tables:
        proj_fk_tables = {r["table"] for r in conn.execute("PRAGMA foreign_key_list(projects)")}
        if "resources" in proj_fk_tables:
            _fk_off(conn)
            conn.execute("DROP TABLE IF EXISTS projects_new")
            conn.execute("""
                CREATE TABLE projects_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL,
                    description TEXT,
                    icon        TEXT    NOT NULL DEFAULT 'folder',
                    color       TEXT    NOT NULL DEFAULT '#3B82F6',
                    owner_id    INTEGER REFERENCES users(id),
                    leader_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    priority_id INTEGER REFERENCES priorities(id) ON DELETE SET NULL,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO projects_new
                    (id, name, description, icon, color, owner_id, leader_id, priority_id,
                     created_at, modified_at, created_by, modified_by)
                SELECT id, name, description, icon, color, owner_id, leader_id, priority_id,
                       created_at, modified_at, created_by, modified_by
                FROM projects
            """)
            conn.execute("DROP TABLE projects")
            conn.execute("ALTER TABLE projects_new RENAME TO projects")
            _fk_on(conn)
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    # ── projects: owner_id + audit ────────────────────────────────────────────
    if "projects" in tables:
        pcols = {r[1] for r in conn.execute("PRAGMA table_info(projects)")}
        if "owner_id" not in pcols:
            conn.execute(
                "ALTER TABLE projects ADD COLUMN owner_id INTEGER REFERENCES users(id)"
            )
            conn.execute("""
                UPDATE projects
                SET owner_id = COALESCE(
                    leader_id,
                    (SELECT id FROM users ORDER BY id LIMIT 1)
                )
            """)
        for col, typedef in [
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in pcols:
                conn.execute(f"ALTER TABLE projects ADD COLUMN {col} {typedef}")

    # ── groups: project_id CASCADE + audit ───────────────────────────────────
    if "groups" in tables:
        gcols = {r[1] for r in conn.execute("PRAGMA table_info(groups)")}
        if "color" not in gcols:
            conn.execute("ALTER TABLE groups ADD COLUMN color TEXT NOT NULL DEFAULT '#3B82F6'")
        if "project_id" not in gcols:
            conn.execute(
                "ALTER TABLE groups ADD COLUMN project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE"
            )
        for col, typedef in [
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in gcols:
                conn.execute(f"ALTER TABLE groups ADD COLUMN {col} {typedef}")
        _g_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='groups'"
        ).fetchone() or [""])[0]
        group_notnull = {r["name"]: r["notnull"] for r in conn.execute("PRAGMA table_info(groups)")}
        group_fk_actions = {
            r["from"]: r["on_delete"]
            for r in conn.execute("PRAGMA foreign_key_list(groups)")
        }
        if (group_fk_actions.get("project_id") != "CASCADE"
                or not group_notnull.get("project_id", 0)
                or "CHECK(LENGTH(color)" not in _g_sql):
            _fk_off(conn)
            conn.execute("DROP TABLE IF EXISTS groups_new")
            conn.execute("""
                CREATE TABLE groups_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL,
                    description TEXT,
                    color       TEXT    NOT NULL DEFAULT '#3B82F6' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
                    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO groups_new
                    (id, name, description, color, project_id,
                     created_at, modified_at, created_by, modified_by)
                SELECT id, name, description, color, project_id,
                       created_at, modified_at, created_by, modified_by
                FROM groups
            """)
            conn.execute("DROP TABLE groups")
            conn.execute("ALTER TABLE groups_new RENAME TO groups")
            _fk_on(conn)

        gcols = {r[1] for r in conn.execute("PRAGMA table_info(groups)")}
        if "sort_order" not in gcols:
            conn.execute("ALTER TABLE groups ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
            conn.execute("""
                UPDATE groups SET sort_order = (
                    SELECT COUNT(*) FROM groups g2
                    WHERE g2.project_id = groups.project_id AND g2.id < groups.id
                )
            """)

    # ── tasks: user_id + audit ────────────────────────────────────────────────
    if "tasks" in tables:
        tcols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
        for col, typedef in [
            ("estimated_duration", "REAL"),
            ("estimated_start",    "TEXT"),
            ("estimated_end",      "TEXT"),
            ("actual_start",       "TEXT"),
            ("actual_end",         "TEXT"),
        ]:
            if col not in tcols:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {typedef}")

        if "user_id" not in tcols:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL"
            )

        if "priority_id" not in tcols:
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN priority_id INTEGER REFERENCES priorities(id) ON DELETE SET NULL"
            )

        for col, typedef in [
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in tcols:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {col} {typedef}")

        tcols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
        if "resource_id" in tcols:
            conn.execute("DROP TABLE IF EXISTS tasks_new")
            conn.execute("""
                CREATE TABLE tasks_new (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id           INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                    user_id            INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    priority_id        INTEGER REFERENCES priorities(id) ON DELETE SET NULL,
                    title              TEXT    NOT NULL,
                    description        TEXT,
                    completed          INTEGER NOT NULL DEFAULT 0,
                    estimated_duration REAL,
                    estimated_start    TEXT,
                    estimated_end      TEXT,
                    actual_start       TEXT,
                    actual_end         TEXT,
                    created_at         TEXT    NOT NULL DEFAULT (datetime('now')),
                    modified_at        TEXT,
                    created_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by        INTEGER REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO tasks_new
                    (id, group_id, user_id, priority_id, title, description,
                     completed, estimated_duration, estimated_start, estimated_end,
                     actual_start, actual_end, created_at, modified_at, created_by, modified_by)
                SELECT id, group_id, user_id, priority_id, title, description,
                       completed, estimated_duration, estimated_start, estimated_end,
                       actual_start, actual_end, created_at, modified_at, created_by, modified_by
                FROM tasks
            """)
            conn.execute("DROP TABLE tasks")
            conn.execute("ALTER TABLE tasks_new RENAME TO tasks")

        _t_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks'"
        ).fetchone() or [""])[0]
        if "CHECK(completed IN (0,1))" not in _t_sql:
            _fk_off(conn)
            conn.execute("DROP TABLE IF EXISTS tasks_new")
            conn.execute("""
                CREATE TABLE tasks_new (
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
                    created_at         TEXT    NOT NULL DEFAULT (datetime('now')),
                    modified_at        TEXT,
                    created_by         INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by        INTEGER REFERENCES users(id) ON DELETE SET NULL
                )
            """)
            conn.execute("""
                INSERT INTO tasks_new
                    (id, group_id, user_id, priority_id, title, description,
                     completed, estimated_duration, estimated_start, estimated_end,
                     actual_start, actual_end, created_at, modified_at, created_by, modified_by)
                SELECT id, group_id, user_id, priority_id, title, description,
                       completed, estimated_duration, estimated_start, estimated_end,
                       actual_start, actual_end, created_at, modified_at, created_by, modified_by
                FROM tasks
            """)
            conn.execute("DROP TABLE tasks")
            conn.execute("ALTER TABLE tasks_new RENAME TO tasks")
            _fk_on(conn)

        tcols = {r[1] for r in conn.execute("PRAGMA table_info(tasks)")}
        if "sort_order" not in tcols:
            conn.execute("ALTER TABLE tasks ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
            conn.execute("""
                UPDATE tasks SET sort_order = (
                    SELECT COUNT(*) FROM tasks t2
                    WHERE t2.group_id = tasks.group_id AND t2.id < tasks.id
                )
            """)

    # ── todo_items: audit ─────────────────────────────────────────────────────
    if "todo_items" in tables:
        tdicols = {r[1] for r in conn.execute("PRAGMA table_info(todo_items)")}
        for col, typedef in [
            ("created_at",  "TEXT"),
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in tdicols:
                conn.execute(f"ALTER TABLE todo_items ADD COLUMN {col} {typedef}")
        _tdi_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='todo_items'"
        ).fetchone() or [""])[0]
        if "CHECK(completed IN (0,1))" not in _tdi_sql:
            _fk_off(conn)
            conn.execute("DROP TABLE IF EXISTS todo_items_new")
            conn.execute("""
                CREATE TABLE todo_items_new (
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
                INSERT INTO todo_items_new
                    (id, task_id, title, completed, sort_order,
                     created_at, modified_at, created_by, modified_by)
                SELECT id, task_id, title, completed, sort_order,
                       COALESCE(created_at, datetime('now')),
                       modified_at, created_by, modified_by
                FROM todo_items
            """)
            conn.execute("DROP TABLE todo_items")
            conn.execute("ALTER TABLE todo_items_new RENAME TO todo_items")
            _fk_on(conn)

    # ── tags: project_id + audit ──────────────────────────────────────────────
    if "tags" in tables:
        tagcols = {r[1] for r in conn.execute("PRAGMA table_info(tags)")}
        if "project_id" not in tagcols:
            conn.execute("DROP TABLE IF EXISTS tags_new")
            conn.execute("""
                CREATE TABLE tags_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                    color       TEXT NOT NULL DEFAULT '#6B7280',
                    created_at  TEXT,
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    UNIQUE(name, project_id)
                )
            """)
            conn.execute("""
                INSERT INTO tags_new (id, name, color, created_at, modified_at, created_by, modified_by)
                SELECT id, name, color, created_at, modified_at, created_by, modified_by FROM tags
            """)
            conn.execute("DROP TABLE tags")
            conn.execute("ALTER TABLE tags_new RENAME TO tags")
            tagcols = {r[1] for r in conn.execute("PRAGMA table_info(tags)")}
        for col, typedef in [
            ("created_at",  "TEXT"),
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in tagcols:
                conn.execute(f"ALTER TABLE tags ADD COLUMN {col} {typedef}")
        # Target: project_id nullable (NULL = global tag, since flows), flow_id,
        # color CHECK. Before flows a NULL project_id meant an orphan tag: drop those.
        _tag_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='tags'"
        ).fetchone() or [""])[0]
        _tag_notnull = {r["name"]: r["notnull"] for r in conn.execute("PRAGMA table_info(tags)")}
        tagcols = {r[1] for r in conn.execute("PRAGMA table_info(tags)")}
        if ("flow_id" not in tagcols or _tag_notnull.get("project_id", 0)
                or "CHECK(LENGTH(color)" not in _tag_sql):
            if "flow_id" not in tagcols:
                conn.execute("DELETE FROM tags WHERE project_id IS NULL")
            flow_expr = "flow_id" if "flow_id" in tagcols else "NULL"
            _fk_off(conn)
            conn.execute("DROP TABLE IF EXISTS tags_new")
            conn.execute("""
                CREATE TABLE tags_new (
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
            conn.execute(f"""
                INSERT INTO tags_new
                    (id, name, project_id, color, flow_id, created_at, modified_at, created_by, modified_by)
                SELECT id, name, project_id, color, {flow_expr},
                       COALESCE(created_at, datetime('now')),
                       modified_at, created_by, modified_by
                FROM tags
            """)
            conn.execute("DROP TABLE tags")
            conn.execute("ALTER TABLE tags_new RENAME TO tags")
            _fk_on(conn)

    # ── priorities: project_id + audit ───────────────────────────────────────
    if "priorities" in tables:
        pricols = {r[1] for r in conn.execute("PRAGMA table_info(priorities)")}
        if "project_id" not in pricols:
            conn.execute("DROP TABLE IF EXISTS priorities_new")
            conn.execute("""
                CREATE TABLE priorities_new (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL,
                    project_id  INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                    icon        TEXT NOT NULL DEFAULT 'flag',
                    color       TEXT NOT NULL DEFAULT '#6B7280',
                    created_at  TEXT,
                    modified_at TEXT,
                    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    UNIQUE(name, project_id)
                )
            """)
            conn.execute("""
                INSERT INTO priorities_new (id, name, icon, color, created_at, modified_at, created_by, modified_by)
                SELECT id, name, icon, color, created_at, modified_at, created_by, modified_by FROM priorities
            """)
            conn.execute("DROP TABLE priorities")
            conn.execute("ALTER TABLE priorities_new RENAME TO priorities")
            pricols = {r[1] for r in conn.execute("PRAGMA table_info(priorities)")}
        for col, typedef in [
            ("created_at",  "TEXT"),
            ("modified_at", "TEXT"),
            ("created_by",  "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("modified_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ]:
            if col not in pricols:
                conn.execute(f"ALTER TABLE priorities ADD COLUMN {col} {typedef}")
        _pri_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='priorities'"
        ).fetchone() or [""])[0]
        _pri_notnull = {r["name"]: r["notnull"] for r in conn.execute("PRAGMA table_info(priorities)")}
        if not _pri_notnull.get("project_id", 0) or "CHECK(LENGTH(color)" not in _pri_sql:
            conn.execute("DELETE FROM priorities WHERE project_id IS NULL")
            _fk_off(conn)
            conn.execute("DROP TABLE IF EXISTS priorities_new")
            conn.execute("""
                CREATE TABLE priorities_new (
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
                INSERT INTO priorities_new
                    (id, name, project_id, icon, color, created_at, modified_at, created_by, modified_by)
                SELECT id, name, project_id, icon, color,
                       COALESCE(created_at, datetime('now')),
                       modified_at, created_by, modified_by
                FROM priorities
            """)
            conn.execute("DROP TABLE priorities")
            conn.execute("ALTER TABLE priorities_new RENAME TO priorities")
            _fk_on(conn)

    # ── task_tags / group_tags: audit columns ────────────────────────────────
    if "task_tags" in tables:
        ttcols = {r[1] for r in conn.execute("PRAGMA table_info(task_tags)")}
        for col, typedef in [
            ("created_at", "TEXT"),
            ("created_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("state_id",   "INTEGER REFERENCES flow_states(id) ON DELETE SET NULL"),
        ]:
            if col not in ttcols:
                conn.execute(f"ALTER TABLE task_tags ADD COLUMN {col} {typedef}")

    if "group_tags" in tables:
        gtcols = {r[1] for r in conn.execute("PRAGMA table_info(group_tags)")}
        for col, typedef in [
            ("created_at", "TEXT"),
            ("created_by", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
            ("state_id",   "INTEGER REFERENCES flow_states(id) ON DELETE SET NULL"),
        ]:
            if col not in gtcols:
                conn.execute(f"ALTER TABLE group_tags ADD COLUMN {col} {typedef}")

    # ── data cleanup ─────────────────────────────────────────────────────────
    conn.execute("DELETE FROM groups WHERE project_id IS NULL")
    conn.execute("""
        UPDATE projects SET owner_id = (SELECT MIN(id) FROM users)
        WHERE owner_id IS NULL AND (SELECT COUNT(*) FROM users) > 0
    """)
    conn.execute("""
        DELETE FROM priorities
        WHERE project_id IS NULL
          AND id NOT IN (SELECT DISTINCT priority_id FROM tasks WHERE priority_id IS NOT NULL)
          AND id NOT IN (SELECT DISTINCT priority_id FROM projects WHERE priority_id IS NOT NULL)
    """)

    # ── projects: owner_id NOT NULL + color CHECK ─────────────────────────────
    if "projects" in tables:
        _proj_sql = (conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='projects'"
        ).fetchone() or [""])[0]
        _proj_notnull = {r["name"]: r["notnull"] for r in conn.execute("PRAGMA table_info(projects)")}
        if not _proj_notnull.get("owner_id", 0) or "CHECK(LENGTH(color)" not in _proj_sql:
            _fk_off(conn)
            conn.execute("DROP TABLE IF EXISTS projects_new")
            conn.execute("""
                CREATE TABLE projects_new (
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
                INSERT INTO projects_new
                    (id, name, description, icon, color, owner_id, leader_id, priority_id,
                     created_at, modified_at, created_by, modified_by)
                SELECT id, name, description, icon, color, owner_id, leader_id, priority_id,
                       created_at, modified_at, created_by, modified_by
                FROM projects
            """)
            conn.execute("DROP TABLE projects")
            conn.execute("ALTER TABLE projects_new RENAME TO projects")
            _fk_on(conn)

    # ── legacy tables ─────────────────────────────────────────────────────────
    for legacy_table in ("task_resources",):
        if legacy_table in tables:
            conn.execute(f"DROP TABLE {legacy_table}")
