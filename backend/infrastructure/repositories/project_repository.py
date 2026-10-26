from backend.domain.entities import Priority, Project, ProjectContentCounts, User
from backend.domain.repositories import ProjectRepository
from backend.infrastructure.persistence.common.utils import ph, row_dt, row_opt, utcnow
from backend.infrastructure.persistence.factory import (
    get_connection,
    idempotent_insert,
    insert_returning_id,
)


class SqlProjectRepository(ProjectRepository):

    def get_all(self) -> list[Project]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM projects ORDER BY id").fetchall()
            projects = [self._to_entity(r) for r in rows]
            self._load_relations(conn, projects)
        return projects

    def get_by_id(self, project_id: int) -> Project | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = %s", (project_id,)).fetchone()
            if row is None:
                return None
            project = self._to_entity(row)
            self._load_relations(conn, [project])
        return project

    def get_owned_by(self, owner_id: int) -> list[Project]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM projects WHERE owner_id = %s ORDER BY id", (owner_id,)
            ).fetchall()
            projects = [self._to_entity(r) for r in rows]
            self._load_relations(conn, projects)
        return projects

    def count_contents(self, project_id: int) -> ProjectContentCounts:
        with get_connection() as conn:
            def count(sql: str) -> int:
                return conn.execute(sql, (project_id,)).fetchone()["n"]

            return ProjectContentCounts(
                groups=count("SELECT COUNT(*) AS n FROM groups WHERE project_id = %s"),
                tasks=count(
                    """SELECT COUNT(*) AS n FROM tasks t
                       JOIN groups g ON t.group_id = g.id
                       WHERE g.project_id = %s"""
                ),
                tags=count("SELECT COUNT(*) AS n FROM tags WHERE project_id = %s"),
                priorities=count("SELECT COUNT(*) AS n FROM priorities WHERE project_id = %s"),
                members=count("SELECT COUNT(*) AS n FROM project_members WHERE project_id = %s"),
            )

    def create(self, project: Project) -> Project:
        with get_connection() as conn:
            new_id = insert_returning_id(
                conn,
                """INSERT INTO projects
                       (name, description, icon, color, owner_id, leader_id, priority_id)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (project.name, project.description, project.icon, project.color,
                 project.owner_id, project.leader_id, project.priority_id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM projects WHERE id = %s", (new_id,)).fetchone()
            result = self._to_entity(row)
            self._load_relations(conn, [result])
        return result

    def update(self, project: Project) -> Project:
        with get_connection() as conn:
            conn.execute(
                """UPDATE projects
                   SET name=%s, description=%s, icon=%s, color=%s,
                       owner_id=%s, leader_id=%s, priority_id=%s, modified_at=%s
                   WHERE id=%s""",
                (project.name, project.description, project.icon, project.color,
                 project.owner_id, project.leader_id, project.priority_id,
                 utcnow(), project.id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM projects WHERE id = %s", (project.id,)).fetchone()
            result = self._to_entity(row)
            self._load_relations(conn, [result])
        return result

    def delete(self, project_id: int) -> None:
        # FKs with ON DELETE CASCADE remove groups, tasks, tags, priorities, members…
        with get_connection() as conn:
            conn.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            conn.commit()

    # ── Members ──────────────────────────────────────────────────────────────

    def get_members(self, project_id: int) -> list[User]:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT u.* FROM users u
                   JOIN project_members pm ON pm.user_id = u.id
                   WHERE pm.project_id = %s ORDER BY u.id""",
                (project_id,),
            ).fetchall()
        return [_user_from_row(r) for r in rows]

    def add_member(self, project_id: int, user_id: int) -> None:
        with get_connection() as conn:
            idempotent_insert(
                conn,
                "INSERT INTO project_members (project_id, user_id) VALUES (%s,%s)",
                (project_id, user_id),
            )
            conn.commit()

    def remove_member(self, project_id: int, user_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM project_members WHERE project_id=%s AND user_id=%s",
                (project_id, user_id),
            )
            conn.commit()

    def is_member(self, project_id: int, user_id: int) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM project_members WHERE project_id=%s AND user_id=%s",
                (project_id, user_id),
            ).fetchone()
        return row is not None

    def get_projects_for_user(self, user_id: int) -> list[Project]:
        with get_connection() as conn:
            rows = conn.execute(
                """SELECT DISTINCT p.*
                   FROM projects p
                   LEFT JOIN project_members pm ON pm.project_id = p.id
                   WHERE p.owner_id = %s OR p.leader_id = %s OR pm.user_id = %s
                   ORDER BY p.id""",
                (user_id, user_id, user_id),
            ).fetchall()
            projects = [self._to_entity(r) for r in rows]
            self._load_relations(conn, projects)
        return projects

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_entity(row) -> Project:
        return Project(
            id=row["id"],
            name=row["name"],
            description=row_opt(row, "description"),
            icon=row["icon"],
            color=row["color"],
            owner_id=row["owner_id"],
            leader_id=row_opt(row, "leader_id"),
            priority_id=row_opt(row, "priority_id"),
            created_at=row_dt(row, "created_at"),
            modified_at=row_dt(row, "modified_at"),
            created_by=row_opt(row, "created_by"),
            modified_by=row_opt(row, "modified_by"),
        )

    @staticmethod
    def _load_relations(conn, projects: list[Project]) -> None:
        if not projects:
            return

        # Owners and leaders
        user_ids = list({uid for p in projects for uid in (p.owner_id, p.leader_id) if uid})
        users_by_id: dict[int, User] = {}
        if user_ids:
            rows = conn.execute(
                f"SELECT * FROM users WHERE id IN ({ph(len(user_ids))})", user_ids
            ).fetchall()
            users_by_id = {r["id"]: _user_from_row(r) for r in rows}
        for p in projects:
            p.owner = users_by_id.get(p.owner_id)
            p.leader = users_by_id.get(p.leader_id)

        # Priorities
        priority_ids = list({p.priority_id for p in projects if p.priority_id is not None})
        if priority_ids:
            rows = conn.execute(
                f"SELECT * FROM priorities WHERE id IN ({ph(len(priority_ids))})", priority_ids
            ).fetchall()
            prio_by_id = {r["id"]: Priority(id=r["id"], name=r["name"], icon=r["icon"], color=r["color"])
                          for r in rows}
            for p in projects:
                p.priority = prio_by_id.get(p.priority_id)

        # Members
        pids = [p.id for p in projects]
        rows = conn.execute(
            f"""SELECT pm.project_id, u.*
                FROM project_members pm JOIN users u ON u.id = pm.user_id
                WHERE pm.project_id IN ({ph(len(pids))}) ORDER BY u.id""",
            pids,
        ).fetchall()
        members_by_proj: dict[int, list[User]] = {p.id: [] for p in projects}
        for r in rows:
            members_by_proj[r["project_id"]].append(_user_from_row(r))
        for p in projects:
            p.members = members_by_proj.get(p.id, [])


def _user_from_row(row) -> User:
    return User(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        password_hash=row["password_hash"] if "password_hash" in row.keys() else "",
        avatar_url=row_opt(row, "avatar_url"),
        created_at=row_dt(row, "created_at"),
        modified_at=row_dt(row, "modified_at"),
        created_by=row_opt(row, "created_by"),
        modified_by=row_opt(row, "modified_by"),
    )
