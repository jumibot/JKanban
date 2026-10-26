from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.application.user_use_cases import verify_password
from backend.domain.entities import User
from backend.infrastructure.persistence.factory import get_connection
from backend.infrastructure.repositories.user_repository import SQLiteUserRepository
from backend.interfaces.dependencies import get_current_user, require_admin
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
    user = SQLiteUserRepository().get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


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

    with get_connection() as conn:
        projects_raw = conn.execute(
            "SELECT id, name FROM projects WHERE owner_id = %s ORDER BY id",
            (user_id,),
        ).fetchall()

        projects = []
        for p in projects_raw:
            pid = p["id"]
            groups_count = conn.execute(
                "SELECT COUNT(*) FROM groups WHERE project_id = %s", (pid,)
            ).fetchone()[0]
            tasks_count = conn.execute(
                """SELECT COUNT(*) FROM tasks t
                   JOIN groups g ON t.group_id = g.id
                   WHERE g.project_id = %s""",
                (pid,),
            ).fetchone()[0]
            tags_count = conn.execute(
                "SELECT COUNT(*) FROM tags WHERE project_id = %s", (pid,)
            ).fetchone()[0]
            priorities_count = conn.execute(
                "SELECT COUNT(*) FROM priorities WHERE project_id = %s", (pid,)
            ).fetchone()[0]
            members_count = conn.execute(
                "SELECT COUNT(*) FROM project_members WHERE project_id = %s", (pid,)
            ).fetchone()[0]
            projects.append(ProjectSummary(
                id=pid, name=p["name"],
                groups_count=groups_count, tasks_count=tasks_count,
                tags_count=tags_count, priorities_count=priorities_count,
                members_count=members_count,
            ))

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

    with get_connection() as conn:
        # Deleting projects cascades: groups → tasks → todo_items, task_tags,
        # group_tags, project_members, tags, priorities
        conn.execute("DELETE FROM projects WHERE owner_id = %s", (user_id,))
        # Deleting user cascades: project_members (as member), sets user_id=NULL
        # on tasks, sets leader_id=NULL on projects
        conn.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
