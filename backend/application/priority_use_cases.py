from backend.domain.entities import Priority
from backend.domain.exceptions import PriorityNameAlreadyExists, PriorityNotFound
from backend.domain.repositories import PriorityRepository


class PriorityUseCases:
    def __init__(self, priority_repo: PriorityRepository):
        self._priorities = priority_repo

    def get_all(self) -> list[Priority]:
        return self._priorities.get_all()

    def get_by_project(self, project_id: int) -> list[Priority]:
        return self._priorities.get_by_project(project_id)

    def get_by_id(self, priority_id: int) -> Priority:
        priority = self._priorities.get_by_id(priority_id)
        if priority is None:
            raise PriorityNotFound(priority_id)
        return priority

    def create(self, name: str, icon: str, color: str, project_id: int) -> Priority:
        existing = self._priorities.get_by_project(project_id)
        if any(p.name.lower() == name.lower() for p in existing):
            raise PriorityNameAlreadyExists(name)
        return self._priorities.create(Priority(name=name, icon=icon, color=color, project_id=project_id))

    def update(self, priority_id: int, updates: dict) -> Priority:
        priority = self.get_by_id(priority_id)
        if "name" in updates:
            existing = self._priorities.get_by_project(priority.project_id)
            if any(p.name.lower() == updates["name"].lower() and p.id != priority_id for p in existing):
                raise PriorityNameAlreadyExists(updates["name"])
        for key, value in updates.items():
            setattr(priority, key, value)
        return self._priorities.update(priority)

    def delete(self, priority_id: int) -> None:
        self.get_by_id(priority_id)
        self._priorities.delete(priority_id)
