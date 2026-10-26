from datetime import datetime
from backend.domain.entities import Task
from backend.domain.exceptions import (
    GroupNotFound, PriorityNotFound, PriorityNotInProject, TaskNotFound, UserNotFound,
)
from backend.domain.repositories import GroupRepository, PriorityRepository, TaskRepository, UserRepository


class TaskUseCases:
    def __init__(
        self,
        task_repo: TaskRepository,
        group_repo: GroupRepository,
        user_repo: UserRepository,
        priority_repo: PriorityRepository,
    ):
        self._tasks = task_repo
        self._groups = group_repo
        self._users = user_repo
        self._priorities = priority_repo

    def get_all(self) -> list[Task]:
        return self._tasks.get_all()

    def get_by_id(self, task_id: int) -> Task:
        task = self._tasks.get_by_id(task_id)
        if task is None:
            raise TaskNotFound(task_id)
        return task

    def create(
        self,
        group_id: int,
        title: str,
        description: str | None,
        completed: bool,
        user_id: int | None,
        priority_id: int | None,
        estimated_duration: float | None,
        estimated_start: datetime | None,
        estimated_end: datetime | None,
        actual_start: datetime | None,
        actual_end: datetime | None,
        sort_order: int | None = None,
    ) -> Task:
        group = self._groups.get_by_id(group_id)
        if group is None:
            raise GroupNotFound(group_id)
        if user_id is not None and self._users.get_by_id(user_id) is None:
            raise UserNotFound(user_id)
        if priority_id is not None:
            self._check_priority(priority_id, group.project_id)
        if sort_order is None:
            sort_order = self._tasks.count_by_group(group_id)
        task = Task(
            group_id=group_id, title=title, description=description,
            completed=completed, user_id=user_id, priority_id=priority_id,
            estimated_duration=estimated_duration,
            estimated_start=estimated_start, estimated_end=estimated_end,
            actual_start=actual_start, actual_end=actual_end,
            sort_order=sort_order,
        )
        return self._tasks.create(task)

    def update(self, task_id: int, updates: dict) -> Task:
        task = self.get_by_id(task_id)
        group_id = updates["group_id"] if updates.get("group_id") is not None else task.group_id
        group = self._groups.get_by_id(group_id)
        if group is None:
            raise GroupNotFound(group_id)
        if "user_id" in updates and updates["user_id"] is not None:
            if self._users.get_by_id(updates["user_id"]) is None:
                raise UserNotFound(updates["user_id"])
        if "priority_id" in updates and updates["priority_id"] is not None:
            self._check_priority(updates["priority_id"], group.project_id)
        for key, value in updates.items():
            setattr(task, key, value)
        return self._tasks.update(task)

    def delete(self, task_id: int) -> None:
        self.get_by_id(task_id)
        self._tasks.delete(task_id)

    def reorder_in_group(self, group_id: int, task_ids: list[int]) -> None:
        # Solo tareas de este grupo: un id ajeno se trata como inexistente.
        for task_id in task_ids:
            task = self._tasks.get_by_id(task_id)
            if task is None or task.group_id != group_id:
                raise TaskNotFound(task_id)
        self._tasks.reorder(task_ids)

    def _check_priority(self, priority_id: int, project_id: int | None) -> None:
        """La prioridad debe existir y ser del proyecto de la tarea (o global, sin proyecto)."""
        priority = self._priorities.get_by_id(priority_id)
        if priority is None:
            raise PriorityNotFound(priority_id)
        if priority.project_id is not None and priority.project_id != project_id:
            raise PriorityNotInProject(priority_id, project_id)
