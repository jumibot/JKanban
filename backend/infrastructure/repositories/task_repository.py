from backend.domain.entities import Priority, Tag, Task, User
from backend.domain.repositories import TaskRepository
from backend.infrastructure.persistence.common.utils import dt_str, ph, row_dt, row_opt, utcnow
from backend.infrastructure.persistence.factory import get_connection, insert_returning_id


class SqlTaskRepository(TaskRepository):

    def get_all(self) -> list[Task]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY sort_order, id").fetchall()
            tasks = [self._to_entity(r) for r in rows]
            self._load_related(conn, tasks)
        return tasks

    def get_by_id(self, task_id: int) -> Task | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task_id,)).fetchone()
            if row is None:
                return None
            task = self._to_entity(row)
            self._load_related(conn, [task])
        return task

    def get_by_group(self, group_id: int) -> list[Task]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE group_id = %s ORDER BY sort_order, id", (group_id,)
            ).fetchall()
            tasks = [self._to_entity(r) for r in rows]
            self._load_related(conn, tasks)
        return tasks

    def count_by_group(self, group_id: int) -> int:
        with get_connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) AS n FROM tasks WHERE group_id = %s", (group_id,)
            ).fetchone()["n"]

    def create(self, task: Task) -> Task:
        with get_connection() as conn:
            new_id = insert_returning_id(
                conn,
                """INSERT INTO tasks
                       (group_id, user_id, priority_id, title, description, completed,
                        estimated_duration, estimated_start, estimated_end,
                        actual_start, actual_end, sort_order)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    task.group_id, task.user_id, task.priority_id,
                    task.title, task.description, bool(task.completed),
                    task.estimated_duration,
                    dt_str(task.estimated_start), dt_str(task.estimated_end),
                    dt_str(task.actual_start), dt_str(task.actual_end),
                    task.sort_order,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM tasks WHERE id = %s", (new_id,)).fetchone()
            result = self._to_entity(row)
            self._load_related(conn, [result])
        return result

    def update(self, task: Task) -> Task:
        with get_connection() as conn:
            conn.execute(
                """UPDATE tasks SET
                       group_id=%s, user_id=%s, priority_id=%s, title=%s, description=%s,
                       completed=%s, estimated_duration=%s, estimated_start=%s, estimated_end=%s,
                       actual_start=%s, actual_end=%s, sort_order=%s, modified_at=%s
                   WHERE id=%s""",
                (
                    task.group_id, task.user_id, task.priority_id,
                    task.title, task.description, bool(task.completed),
                    task.estimated_duration,
                    dt_str(task.estimated_start), dt_str(task.estimated_end),
                    dt_str(task.actual_start), dt_str(task.actual_end),
                    task.sort_order, utcnow(), task.id,
                ),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM tasks WHERE id = %s", (task.id,)).fetchone()
            result = self._to_entity(row)
            self._load_related(conn, [result])
        return result

    def delete(self, task_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            conn.commit()

    def reorder(self, task_ids: list[int]) -> None:
        with get_connection() as conn:
            for order, task_id in enumerate(task_ids):
                conn.execute("UPDATE tasks SET sort_order=%s WHERE id=%s", (order, task_id))
            conn.commit()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_entity(row) -> Task:
        return Task(
            id=row["id"],
            group_id=row["group_id"],
            user_id=row_opt(row, "user_id"),
            priority_id=row_opt(row, "priority_id"),
            title=row["title"],
            description=row_opt(row, "description"),
            completed=bool(row["completed"]),
            estimated_duration=row_opt(row, "estimated_duration"),
            estimated_start=row_dt(row, "estimated_start"),
            estimated_end=row_dt(row, "estimated_end"),
            actual_start=row_dt(row, "actual_start"),
            actual_end=row_dt(row, "actual_end"),
            sort_order=row["sort_order"] if "sort_order" in row.keys() else 0,
            created_at=row_dt(row, "created_at"),
            modified_at=row_dt(row, "modified_at"),
            created_by=row_opt(row, "created_by"),
            modified_by=row_opt(row, "modified_by"),
        )

    @classmethod
    def _load_related(cls, conn, tasks: list[Task]) -> None:
        cls._load_user(conn, tasks)
        cls._load_priority(conn, tasks)
        cls._load_tags(conn, tasks)
        cls._load_todo_counts(conn, tasks)

    @staticmethod
    def _load_user(conn, tasks: list[Task]) -> None:
        ids = list({t.user_id for t in tasks if t.user_id is not None})
        if not ids:
            return
        rows = conn.execute(f"SELECT * FROM users WHERE id IN ({ph(len(ids))})", ids).fetchall()
        by_id = {
            r["id"]: User(
                id=r["id"], name=r["name"], email=r["email"],
                password_hash=r["password_hash"],
                avatar_url=row_opt(r, "avatar_url"),
                created_at=row_dt(r, "created_at"),
            )
            for r in rows
        }
        for task in tasks:
            task.user = by_id.get(task.user_id)

    @staticmethod
    def _load_tags(conn, tasks: list[Task]) -> None:
        if not tasks:
            return
        ids = [t.id for t in tasks]
        rows = conn.execute(
            f"""SELECT tt.task_id, t.id, t.name, t.color
                FROM task_tags tt JOIN tags t ON t.id = tt.tag_id
                WHERE tt.task_id IN ({ph(len(ids))}) ORDER BY tt.task_id, t.id""",
            ids,
        ).fetchall()
        by_task: dict[int, list[Tag]] = {t.id: [] for t in tasks}
        for r in rows:
            by_task[r["task_id"]].append(Tag(id=r["id"], name=r["name"], color=r["color"]))
        for task in tasks:
            task.tags = by_task.get(task.id, [])

    @staticmethod
    def _load_priority(conn, tasks: list[Task]) -> None:
        ids = list({t.priority_id for t in tasks if t.priority_id is not None})
        if not ids:
            return
        rows = conn.execute(f"SELECT * FROM priorities WHERE id IN ({ph(len(ids))})", ids).fetchall()
        by_id = {r["id"]: Priority(id=r["id"], name=r["name"], icon=r["icon"], color=r["color"])
                 for r in rows}
        for task in tasks:
            task.priority = by_id.get(task.priority_id)

    @staticmethod
    def _load_todo_counts(conn, tasks: list[Task]) -> None:
        if not tasks:
            return
        ids = [t.id for t in tasks]
        # CASE (not a plain SUM over the column) works for INTEGER 0/1 (SQLite) and BOOLEAN (PostgreSQL)
        rows = conn.execute(
            f"""SELECT task_id,
                       COUNT(*) AS total,
                       SUM(CASE WHEN completed THEN 1 ELSE 0 END) AS done
                FROM todo_items WHERE task_id IN ({ph(len(ids))}) GROUP BY task_id""",
            ids,
        ).fetchall()
        counts = {r["task_id"]: (r["total"], r["done"] or 0) for r in rows}
        for task in tasks:
            total, done = counts.get(task.id, (0, 0))
            task.todos_total = total
            task.todos_completed = done
