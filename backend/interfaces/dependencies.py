from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from backend.application.group_use_cases import GroupUseCases
from backend.application.project_use_cases import ProjectUseCases
from backend.application.tag_use_cases import TagUseCases
from backend.application.task_use_cases import TaskUseCases
from backend.application.todo_use_cases import TodoUseCases
from backend.application.user_use_cases import UserUseCases
from backend.domain.entities import User
from backend.domain.exceptions import ProjectNotFound, UserNotInProject
from backend.infrastructure.jwt_handler import decode_access_token
from backend.infrastructure.repositories.group_repository import SqlGroupRepository
from backend.infrastructure.repositories.priority_repository import SqlPriorityRepository
from backend.infrastructure.repositories.project_repository import SqlProjectRepository
from backend.infrastructure.repositories.tag_repository import SqlTagRepository
from backend.infrastructure.repositories.task_repository import SqlTaskRepository
from backend.infrastructure.repositories.todo_repository import SqlTodoRepository
from backend.infrastructure.repositories.user_repository import SqlUserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    try:
        user_id = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = SqlUserRepository().get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# ── Project access helpers ────────────────────────────────────────────────────

def get_project_use_cases() -> ProjectUseCases:
    return ProjectUseCases(
        project_repo=SqlProjectRepository(),
        group_repo=SqlGroupRepository(),
        user_repo=SqlUserRepository(),
        priority_repo=SqlPriorityRepository(),
    )


_project_uc = get_project_use_cases


def require_admin(current_user: User) -> None:
    """Raises 403 if the user is not a platform admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador de plataforma",
        )


def require_project_access(project_id: int | None, user_id: int) -> None:
    """Raises 403 if user is not owner/leader/member. No-op for standalone (project_id=None)."""
    if project_id is None:
        return
    try:
        _project_uc().get_user_role(project_id, user_id)
    except (ProjectNotFound, UserNotInProject):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este proyecto",
        )


def require_project_leader(project_id: int, user_id: int) -> None:
    """Raises 403 if user is not owner or leader of the project."""
    try:
        role = _project_uc().get_user_role(project_id, user_id)
    except (ProjectNotFound, UserNotInProject):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este proyecto",
        )
    if role not in ("owner", "leader"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el propietario o líder puede gestionar las etiquetas del proyecto",
        )


def get_user_project_ids(user_id: int) -> set[int]:
    """Returns the set of project IDs the user can access."""
    pairs = _project_uc().get_projects_for_user(user_id)
    return {p.id for p, _ in pairs}


def get_user_use_cases() -> UserUseCases:
    return UserUseCases(user_repo=SqlUserRepository())


def get_task_use_cases() -> TaskUseCases:
    return TaskUseCases(
        task_repo=SqlTaskRepository(),
        group_repo=SqlGroupRepository(),
        user_repo=SqlUserRepository(),
        priority_repo=SqlPriorityRepository(),
    )


def get_group_use_cases() -> GroupUseCases:
    return GroupUseCases(
        group_repo=SqlGroupRepository(),
        task_repo=SqlTaskRepository(),
        project_repo=SqlProjectRepository(),
    )


def get_todo_use_cases() -> TodoUseCases:
    return TodoUseCases(
        todo_repo=SqlTodoRepository(),
        task_repo=SqlTaskRepository(),
    )


def get_priority_use_cases():
    from backend.application.priority_use_cases import PriorityUseCases
    return PriorityUseCases(priority_repo=SqlPriorityRepository())


def get_tag_use_cases() -> TagUseCases:
    return TagUseCases(
        tag_repo=SqlTagRepository(),
        task_repo=SqlTaskRepository(),
        group_repo=SqlGroupRepository(),
    )
