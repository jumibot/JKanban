from backend.domain.entities import TodoItem
from backend.domain.exceptions import TaskNotFound, TodoNotFound
from backend.domain.repositories import TaskRepository, TodoRepository


class TodoUseCases:
    def __init__(self, todo_repo: TodoRepository, task_repo: TaskRepository):
        self._todos = todo_repo
        self._tasks = task_repo

    def _require_task(self, task_id: int) -> None:
        if self._tasks.get_by_id(task_id) is None:
            raise TaskNotFound(task_id)

    def _require_todo(self, task_id: int, todo_id: int) -> TodoItem:
        todo = self._todos.get_by_id(todo_id)
        if todo is None or todo.task_id != task_id:
            raise TodoNotFound(todo_id)
        return todo

    def get_todos(self, task_id: int) -> list[TodoItem]:
        self._require_task(task_id)
        return self._todos.get_by_task(task_id)

    def create(self, task_id: int, title: str, completed: bool, order: int | None) -> TodoItem:
        self._require_task(task_id)
        if order is None:
            existing = self._todos.get_by_task(task_id)
            order = len(existing)
        return self._todos.create(TodoItem(task_id=task_id, title=title, completed=completed, order=order))

    def update(self, task_id: int, todo_id: int, updates: dict) -> TodoItem:
        self._require_task(task_id)
        todo = self._require_todo(task_id, todo_id)
        for key, value in updates.items():
            setattr(todo, key, value)
        return self._todos.update(todo)

    def delete(self, task_id: int, todo_id: int) -> None:
        self._require_task(task_id)
        self._require_todo(task_id, todo_id)
        self._todos.delete(todo_id)
