from backend.domain.entities import TodoItem
from backend.domain.repositories import TodoRepository
from backend.infrastructure.persistence.common.utils import row_dt, row_opt, utcnow
from backend.infrastructure.persistence.factory import get_connection, insert_returning_id


class SqlTodoRepository(TodoRepository):

    def get_by_task(self, task_id: int) -> list[TodoItem]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM todo_items WHERE task_id=%s ORDER BY sort_order, id",
                (task_id,),
            ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, todo_id: int) -> TodoItem | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM todo_items WHERE id=%s", (todo_id,)).fetchone()
        return self._to_entity(row) if row else None

    def create(self, todo: TodoItem) -> TodoItem:
        with get_connection() as conn:
            new_id = insert_returning_id(
                conn,
                "INSERT INTO todo_items (task_id, title, completed, sort_order) VALUES (%s,%s,%s,%s)",
                (todo.task_id, todo.title, bool(todo.completed), todo.order),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM todo_items WHERE id=%s", (new_id,)).fetchone()
        return self._to_entity(row)

    def update(self, todo: TodoItem) -> TodoItem:
        with get_connection() as conn:
            conn.execute(
                "UPDATE todo_items SET title=%s, completed=%s, sort_order=%s, modified_at=%s WHERE id=%s",
                (todo.title, bool(todo.completed), todo.order, utcnow(), todo.id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM todo_items WHERE id=%s", (todo.id,)).fetchone()
        return self._to_entity(row)

    def delete(self, todo_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM todo_items WHERE id=%s", (todo_id,))
            conn.commit()

    @staticmethod
    def _to_entity(row) -> TodoItem:
        return TodoItem(
            id=row["id"],
            task_id=row["task_id"],
            title=row["title"],
            completed=bool(row["completed"]),
            order=row["sort_order"],
            created_at=row_dt(row, "created_at"),
            modified_at=row_dt(row, "modified_at"),
            created_by=row_opt(row, "created_by"),
            modified_by=row_opt(row, "modified_by"),
        )
