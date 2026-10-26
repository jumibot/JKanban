from backend.domain.entities import Group
from backend.domain.exceptions import GroupNotFound, ProjectNotFound
from backend.domain.repositories import GroupRepository, ProjectRepository, TaskRepository


class GroupUseCases:
    def __init__(self, group_repo: GroupRepository, task_repo: TaskRepository, project_repo: ProjectRepository):
        self._groups = group_repo
        self._tasks = task_repo
        self._projects = project_repo

    def get_all(self) -> list[Group]:
        return self._groups.get_all()

    def get_by_id(self, group_id: int) -> Group:
        group = self._groups.get_by_id(group_id)
        if group is None:
            raise GroupNotFound(group_id)
        return group

    def get_tasks(self, group_id: int):
        self.get_by_id(group_id)  # raises GroupNotFound
        return self._tasks.get_by_group(group_id)

    def create(self, name: str, description: str | None, color: str, project_id: int | None, sort_order: int | None = None) -> Group:
        if project_id is not None and self._projects.get_by_id(project_id) is None:
            raise ProjectNotFound(project_id)
        if sort_order is None:
            sort_order = self._groups.count_by_project(project_id) if project_id is not None else 0
        return self._groups.create(Group(name=name, description=description, color=color, project_id=project_id, sort_order=sort_order))

    def update(self, group_id: int, updates: dict) -> Group:
        group = self.get_by_id(group_id)  # raises GroupNotFound
        for key, value in updates.items():
            setattr(group, key, value)
        return self._groups.update(group)

    def delete(self, group_id: int) -> None:
        self.get_by_id(group_id)  # raises GroupNotFound
        self._groups.delete(group_id)  # tasks cascade via FK

    def reorder_in_project(self, project_id: int, group_ids: list[int]) -> None:
        # Solo grupos de este proyecto: un id ajeno se trata como inexistente.
        for group_id in group_ids:
            group = self._groups.get_by_id(group_id)
            if group is None or group.project_id != project_id:
                raise GroupNotFound(group_id)
        self._groups.reorder(group_ids)
