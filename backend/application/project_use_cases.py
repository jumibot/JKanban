from backend.domain.entities import Project, ProjectContentCounts, User
from backend.domain.exceptions import (
    MemberAlreadyInProject, MemberNotInProject,
    PriorityNotFound, ProjectHasGroups, ProjectLeaderRequired, ProjectNotFound, UserNotFound, UserNotInProject,
)
from backend.domain.repositories import GroupRepository, PriorityRepository, ProjectRepository, UserRepository


class ProjectUseCases:
    def __init__(
        self,
        project_repo: ProjectRepository,
        group_repo: GroupRepository,
        user_repo: UserRepository,
        priority_repo: PriorityRepository,
    ):
        self._projects = project_repo
        self._groups = group_repo
        self._users = user_repo
        self._priorities = priority_repo

    def get_all(self) -> list[Project]:
        return self._projects.get_all()

    def get_by_id(self, project_id: int) -> Project:
        project = self._projects.get_by_id(project_id)
        if project is None:
            raise ProjectNotFound(project_id)
        return project

    def get_groups(self, project_id: int):
        self.get_by_id(project_id)
        return [g for g in self._groups.get_all() if g.project_id == project_id]

    def create(
        self,
        name: str,
        description: str | None,
        icon: str,
        color: str,
        owner_id: int,
        leader_id: int | None,
        priority_id: int | None,
    ) -> Project:
        if self._users.get_by_id(owner_id) is None:
            raise UserNotFound(owner_id)
        if leader_id is None:
            leader_id = owner_id
        if self._users.get_by_id(leader_id) is None:
            raise UserNotFound(leader_id)
        if priority_id is not None and self._priorities.get_by_id(priority_id) is None:
            raise PriorityNotFound(priority_id)
        project = Project(
            name=name, description=description, icon=icon, color=color,
            owner_id=owner_id, leader_id=leader_id, priority_id=priority_id,
        )
        return self._projects.create(project)

    def update(self, project_id: int, updates: dict) -> Project:
        project = self.get_by_id(project_id)
        if "owner_id" in updates and updates["owner_id"] is not None:
            if self._users.get_by_id(updates["owner_id"]) is None:
                raise UserNotFound(updates["owner_id"])
        if "leader_id" in updates:
            if updates["leader_id"] is None:
                raise ProjectLeaderRequired()
            if self._users.get_by_id(updates["leader_id"]) is None:
                raise UserNotFound(updates["leader_id"])
        if "priority_id" in updates and updates["priority_id"] is not None:
            if self._priorities.get_by_id(updates["priority_id"]) is None:
                raise PriorityNotFound(updates["priority_id"])
        for key, value in updates.items():
            setattr(project, key, value)
        return self._projects.update(project)

    def delete(self, project_id: int) -> None:
        self.get_by_id(project_id)
        groups_in_project = [g for g in self._groups.get_all() if g.project_id == project_id]
        if groups_in_project:
            raise ProjectHasGroups(project_id, len(groups_in_project))
        self._projects.delete(project_id)

    # ── Cascade delete ───────────────────────────────────────────────────────

    def get_deletion_preview(self, project_id: int) -> tuple[Project, ProjectContentCounts]:
        """What a cascade delete of this project would remove."""
        project = self.get_by_id(project_id)
        return project, self._projects.count_contents(project_id)

    def get_owned_with_contents(self, owner_id: int) -> list[tuple[Project, ProjectContentCounts]]:
        """Projects owned by a user, each with its dependent-data counts."""
        return [(p, self._projects.count_contents(p.id)) for p in self._projects.get_owned_by(owner_id)]

    def delete_cascade(self, project_id: int) -> None:
        """Delete the project and all its data, even if it still has groups."""
        self.get_by_id(project_id)
        self._projects.delete(project_id)

    # ── Members ──────────────────────────────────────────────────────────────

    def get_members(self, project_id: int) -> list[User]:
        self.get_by_id(project_id)
        return self._projects.get_members(project_id)

    def add_member(self, project_id: int, user_id: int) -> None:
        self.get_by_id(project_id)
        if self._users.get_by_id(user_id) is None:
            raise UserNotFound(user_id)
        if self._projects.is_member(project_id, user_id):
            raise MemberAlreadyInProject(user_id, project_id)
        self._projects.add_member(project_id, user_id)

    def remove_member(self, project_id: int, user_id: int) -> None:
        self.get_by_id(project_id)
        if not self._projects.is_member(project_id, user_id):
            raise MemberNotInProject(user_id, project_id)
        self._projects.remove_member(project_id, user_id)

    # ── Access & roles ───────────────────────────────────────────────────────

    def get_projects_for_user(self, user_id: int) -> list[tuple[Project, str]]:
        """Devuelve [(project, role)] para todos los proyectos a los que tiene acceso el usuario."""
        if self._users.get_by_id(user_id) is None:
            raise UserNotFound(user_id)
        projects = self._projects.get_projects_for_user(user_id)
        result = []
        for p in projects:
            if p.owner_id == user_id:
                role = "owner"
            elif p.leader_id == user_id:
                role = "leader"
            else:
                role = "member"
            result.append((p, role))
        return result

    def get_user_role(self, project_id: int, user_id: int) -> str:
        """Devuelve el rol del usuario en el proyecto o lanza UserNotInProject."""
        project = self.get_by_id(project_id)
        if project.owner_id == user_id:
            return "owner"
        if project.leader_id == user_id:
            return "leader"
        if self._projects.is_member(project_id, user_id):
            return "member"
        raise UserNotInProject(user_id, project_id)
