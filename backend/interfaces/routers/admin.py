from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.application.user_use_cases import verify_password
from backend.domain.entities import User
from backend.domain.exceptions import UserNotFound
from backend.interfaces.dependencies import (
    get_current_user,
    get_project_use_cases,
    get_user_use_cases,
    require_admin,
)
from backend.interfaces.schemas import UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ProjectSummary(BaseModel):
    id: int
    name: str
    groups_count: int
    tasks_count: int
    tags_count: int
    priorities_count: int
    members_count: int


class DeletionTotals(BaseModel):
    projects: int
    groups: int
    tasks: int
    tags: int
    priorities: int


class UserDeletionPreview(BaseModel):
    user: UserResponse
    projects: list[ProjectSummary]
    totals: DeletionTotals


class CascadeDeleteRequest(BaseModel):
    admin_password: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user_or_404(user_id: int) -> User:
    try:
        return get_user_use_cases().get_by_id(user_id)
    except UserNotFound:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/users/{user_id}/deletion-preview", response_model=UserDeletionPreview)
def deletion_preview(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    """Returns a full summary of what will be deleted when a user is cascade-deleted.
    Requires platform admin privileges."""
    require_admin(current_user)
    target = _get_user_or_404(user_id)

    projects = [
        ProjectSummary(
            id=project.id, name=project.name,
            groups_count=counts.groups, tasks_count=counts.tasks,
            tags_count=counts.tags, priorities_count=counts.priorities,
            members_count=counts.members,
        )
        for project, counts in get_project_use_cases().get_owned_with_contents(user_id)
    ]
    totals = DeletionTotals(
        projects=len(projects),
        groups=sum(p.groups_count for p in projects),
        tasks=sum(p.tasks_count for p in projects),
        tags=sum(p.tags_count for p in projects),
        priorities=sum(p.priorities_count for p in projects),
    )
    return UserDeletionPreview(
        user=UserResponse.from_entity(target),
        projects=projects,
        totals=totals,
    )


@router.delete("/users/{user_id}/cascade", status_code=204)
def cascade_delete_user(
    user_id: int,
    body: CascadeDeleteRequest,
    current_user: User = Depends(get_current_user),
):
    """Deletes a user and all their owned projects (with all dependent data) in cascade.
    Requires platform admin privileges and admin password confirmation."""
    require_admin(current_user)

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")

    _get_user_or_404(user_id)

    if not verify_password(body.admin_password, current_user.password_hash):
        raise HTTPException(status_code=403, detail="Contraseña incorrecta")

    get_user_use_cases().delete_cascade(user_id)
