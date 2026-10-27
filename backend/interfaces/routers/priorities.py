from fastapi import APIRouter, Depends, HTTPException, status
from backend.application.priority_use_cases import PriorityUseCases
from backend.domain.entities import User
from backend.domain.exceptions import PriorityNameAlreadyExists, PriorityNotFound
from backend.interfaces.dependencies import (
    get_current_user, get_priority_use_cases,
    require_project_access, require_project_leader,
)
from backend.interfaces.schemas import PriorityCreate, PriorityResponse, PriorityUpdate

router = APIRouter(prefix="/projects/{project_id}/priorities", tags=["priorities"])


@router.get("/", response_model=list[PriorityResponse])
def list_priorities(
    project_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: PriorityUseCases = Depends(get_priority_use_cases),
):
    require_project_access(project_id, current_user.id)
    return [PriorityResponse.from_entity(p) for p in use_cases.get_by_project(project_id)]


@router.get("/{priority_id}", response_model=PriorityResponse)
def get_priority(
    project_id: int,
    priority_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: PriorityUseCases = Depends(get_priority_use_cases),
):
    require_project_access(project_id, current_user.id)
    try:
        p = use_cases.get_by_id(priority_id)
    except PriorityNotFound:
        raise HTTPException(status_code=404, detail="Priority not found")
    if p.project_id != project_id:
        raise HTTPException(status_code=404, detail="Priority not found")
    return PriorityResponse.from_entity(p)


@router.post("/", response_model=PriorityResponse, status_code=status.HTTP_201_CREATED)
def create_priority(
    project_id: int,
    body: PriorityCreate,
    current_user: User = Depends(get_current_user),
    use_cases: PriorityUseCases = Depends(get_priority_use_cases),
):
    require_project_leader(project_id, current_user.id)
    try:
        return PriorityResponse.from_entity(
            use_cases.create(name=body.name, icon=body.icon, color=body.color, project_id=project_id)
        )
    except PriorityNameAlreadyExists as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/{priority_id}", response_model=PriorityResponse)
def update_priority(
    project_id: int,
    priority_id: int,
    body: PriorityUpdate,
    current_user: User = Depends(get_current_user),
    use_cases: PriorityUseCases = Depends(get_priority_use_cases),
):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    require_project_leader(project_id, current_user.id)
    try:
        p = use_cases.get_by_id(priority_id)
    except PriorityNotFound:
        raise HTTPException(status_code=404, detail="Priority not found")
    if p.project_id != project_id:
        raise HTTPException(status_code=404, detail="Priority not found")
    try:
        return PriorityResponse.from_entity(use_cases.update(priority_id, updates))
    except PriorityNotFound:
        raise HTTPException(status_code=404, detail="Priority not found")
    except PriorityNameAlreadyExists as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.delete("/{priority_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_priority(
    project_id: int,
    priority_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: PriorityUseCases = Depends(get_priority_use_cases),
):
    require_project_leader(project_id, current_user.id)
    try:
        p = use_cases.get_by_id(priority_id)
    except PriorityNotFound:
        raise HTTPException(status_code=404, detail="Priority not found")
    if p.project_id != project_id:
        raise HTTPException(status_code=404, detail="Priority not found")
    use_cases.delete(priority_id)
