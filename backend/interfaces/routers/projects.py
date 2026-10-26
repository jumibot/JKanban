from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from backend.application.project_use_cases import ProjectUseCases
from backend.application.user_use_cases import verify_password
from backend.domain.entities import Project, User
from backend.domain.exceptions import (
    MemberAlreadyInProject, MemberNotInProject,
    PriorityNotFound, ProjectHasGroups, ProjectLeaderRequired, ProjectNotFound, UserNotFound, UserNotInProject,
)
from backend.infrastructure.repositories.group_repository import SqlGroupRepository
from backend.infrastructure.repositories.priority_repository import SqlPriorityRepository
from backend.infrastructure.repositories.project_repository import SqlProjectRepository
from backend.infrastructure.repositories.user_repository import SqlUserRepository
from backend.interfaces.dependencies import get_current_user
from backend.interfaces.schemas import (
    GroupResponse, ProjectCreate, ProjectResponse, ProjectRoleResponse,
    ProjectUpdate, UserResponse,
)


class CascadeDeleteProjectRequest(BaseModel):
    owner_password: str

router = APIRouter(prefix="/projects", tags=["projects"])


def _use_cases() -> ProjectUseCases:
    return ProjectUseCases(
        project_repo=SqlProjectRepository(),
        group_repo=SqlGroupRepository(),
        user_repo=SqlUserRepository(),
        priority_repo=SqlPriorityRepository(),
    )


def _require_owner_or_leader(project: Project, user_id: int) -> None:
    if project.owner_id != user_id and project.leader_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner or leader can perform this action",
        )


def _require_owner(project: Project, user_id: int) -> None:
    if project.owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can perform this action",
        )


@router.get("/", response_model=list[ProjectResponse])
def list_projects(current_user: User = Depends(get_current_user)):
    pairs = _use_cases().get_projects_for_user(current_user.id)
    return [ProjectResponse.from_entity(p) for p, _ in pairs]


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, current_user: User = Depends(get_current_user)):
    try:
        return ProjectResponse.from_entity(_use_cases().get_by_id(project_id))
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{project_id}/groups", response_model=list[GroupResponse])
def get_project_groups(project_id: int, current_user: User = Depends(get_current_user)):
    try:
        return [GroupResponse.from_entity(g) for g in _use_cases().get_groups(project_id)]
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{project_id}/members", response_model=list[UserResponse])
def get_project_members(project_id: int, current_user: User = Depends(get_current_user)):
    try:
        return [UserResponse.from_entity(u) for u in _use_cases().get_members(project_id)]
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, current_user: User = Depends(get_current_user)):
    try:
        return ProjectResponse.from_entity(
            _use_cases().create(
                name=body.name, description=body.description, icon=body.icon,
                color=body.color, owner_id=current_user.id,
                leader_id=body.leader_id, priority_id=body.priority_id,
            )
        )
    except UserNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PriorityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int, body: ProjectUpdate,
    current_user: User = Depends(get_current_user),
):
    uc = _use_cases()
    try:
        project = uc.get_by_id(project_id)
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    _require_owner_or_leader(project, current_user.id)
    try:
        updates = body.model_dump(exclude_unset=True)
        return ProjectResponse.from_entity(uc.update(project_id, updates))
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProjectLeaderRequired as e:
        raise HTTPException(status_code=422, detail=str(e))
    except UserNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PriorityNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, current_user: User = Depends(get_current_user)):
    uc = _use_cases()
    try:
        project = uc.get_by_id(project_id)
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    _require_owner(project, current_user.id)
    try:
        uc.delete(project_id)
    except ProjectHasGroups as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{project_id}/deletion-preview")
def project_deletion_preview(
    project_id: int,
    current_user: User = Depends(get_current_user),
):
    """Returns counts of everything that will be removed by a cascade delete.
    Only the project owner can call this."""
    try:
        project, counts = _use_cases().get_deletion_preview(project_id)
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    _require_owner(project, current_user.id)
    return {
        "project": ProjectResponse.from_entity(project),
        "groups_count": counts.groups,
        "tasks_count": counts.tasks,
        "tags_count": counts.tags,
        "priorities_count": counts.priorities,
        "members_count": counts.members,
    }


@router.delete("/{project_id}/cascade", status_code=status.HTTP_204_NO_CONTENT)
def cascade_delete_project(
    project_id: int,
    body: CascadeDeleteProjectRequest,
    current_user: User = Depends(get_current_user),
):
    """Deletes a project and all its data (groups, tasks, tags, priorities…) in cascade.
    Only the project owner can call this. Requires password confirmation."""
    uc = _use_cases()
    try:
        project = uc.get_by_id(project_id)
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    _require_owner(project, current_user.id)
    if not verify_password(body.owner_password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="Contraseña incorrecta")
    uc.delete_cascade(project_id)


# ── Members ──────────────────────────────────────────────────────────────────

@router.post("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_member(project_id: int, user_id: int, current_user: User = Depends(get_current_user)):
    uc = _use_cases()
    try:
        project = uc.get_by_id(project_id)
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    _require_owner_or_leader(project, current_user.id)
    try:
        uc.add_member(project_id, user_id)
    except UserNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MemberAlreadyInProject as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(project_id: int, user_id: int, current_user: User = Depends(get_current_user)):
    uc = _use_cases()
    try:
        project = uc.get_by_id(project_id)
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    _require_owner_or_leader(project, current_user.id)
    try:
        uc.remove_member(project_id, user_id)
    except MemberNotInProject as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Roles ─────────────────────────────────────────────────────────────────────

@router.get("/{project_id}/role/{user_id}", response_model=ProjectRoleResponse)
def get_user_role(project_id: int, user_id: int, current_user: User = Depends(get_current_user)):
    try:
        role = _use_cases().get_user_role(project_id, user_id)
        return ProjectRoleResponse(role=role)
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UserNotInProject as e:
        raise HTTPException(status_code=404, detail=str(e))
