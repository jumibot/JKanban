from fastapi import APIRouter, Depends, HTTPException
from backend.application.project_use_cases import ProjectUseCases
from backend.application.user_use_cases import UserUseCases
from backend.domain.entities import User
from backend.domain.exceptions import EmailAlreadyExists, UserNotFound, UserOwnsProjects
from backend.infrastructure.repositories.group_repository import SqlGroupRepository
from backend.infrastructure.repositories.priority_repository import SqlPriorityRepository
from backend.infrastructure.repositories.project_repository import SqlProjectRepository
from backend.infrastructure.repositories.user_repository import SqlUserRepository
from backend.interfaces.dependencies import get_current_user, get_user_use_cases, require_admin
from backend.interfaces.schemas import ProjectWithRoleResponse, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


def _project_use_cases() -> ProjectUseCases:
    return ProjectUseCases(
        project_repo=SqlProjectRepository(),
        group_repo=SqlGroupRepository(),
        user_repo=SqlUserRepository(),
        priority_repo=SqlPriorityRepository(),
    )


@router.get("/", response_model=list[UserResponse])
def list_users(
    current_user: User = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    return [UserResponse.from_entity(u) for u in use_cases.get_all()]


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    try:
        return UserResponse.from_entity(use_cases.get_by_id(user_id))
    except UserNotFound:
        raise HTTPException(status_code=404, detail="User not found")


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(body: UserCreate, use_cases: UserUseCases = Depends(get_user_use_cases)):
    """Public endpoint — no auth required (registration)."""
    try:
        user = use_cases.create(
            name=body.name, email=body.email,
            password=body.password, avatar_url=body.avatar_url,
        )
        return UserResponse.from_entity(user)
    except EmailAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    # Existence check first (404), then authorization (403)
    try:
        use_cases.get_by_id(user_id)
    except UserNotFound:
        raise HTTPException(status_code=404, detail="User not found")
    # Only admins can update other users or set the is_admin flag
    if current_user.id != user_id or "is_admin" in updates:
        require_admin(current_user)
    if current_user.id == user_id and updates.get("is_admin") is False:
        raise HTTPException(status_code=403, detail="An administrator cannot remove their own admin privileges")
    try:
        return UserResponse.from_entity(use_cases.update(user_id, updates))
    except EmailAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    # Existence check first (404), then authorization (403)
    try:
        use_cases.get_by_id(user_id)
    except UserNotFound:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You can only delete your own account")
    if current_user.is_admin and user_id == current_user.id:
        raise HTTPException(status_code=403, detail="An administrator cannot delete their own account")
    try:
        use_cases.delete(user_id)
    except UserOwnsProjects as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{user_id}/projects", response_model=list[ProjectWithRoleResponse])
def get_user_projects(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    try:
        pairs = _project_use_cases().get_projects_for_user(user_id)
        return [ProjectWithRoleResponse.from_entity_and_role(p, role) for p, role in pairs]
    except UserNotFound:
        raise HTTPException(status_code=404, detail="User not found")
