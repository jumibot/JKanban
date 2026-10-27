from fastapi import APIRouter, Depends, HTTPException
from backend.application.todo_use_cases import TodoUseCases
from backend.domain.entities import User
from backend.domain.exceptions import TaskNotFound, TodoNotFound
from backend.interfaces.dependencies import (
    get_current_user, get_todo_use_cases, get_task_use_cases,
    require_project_access,
)
from backend.interfaces.schemas import TodoCreate, TodoResponse, TodoUpdate

router = APIRouter(prefix="/tasks", tags=["todos"])


def _task_project_id(task_id: int, task_uc) -> int | None:
    """Returns the project_id of a task's group, or None if standalone/not found."""
    from backend.interfaces.routers.tasks import _group_project_id
    try:
        task = task_uc.get_by_id(task_id)
        return _group_project_id(task.group_id)
    except TaskNotFound:
        return None


@router.get("/{task_id}/todos", response_model=list[TodoResponse])
def list_todos(
    task_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    task_uc=Depends(get_task_use_cases),
):
    require_project_access(_task_project_id(task_id, task_uc), current_user.id)
    try:
        return [TodoResponse.from_entity(t) for t in use_cases.get_todos(task_id)]
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/todos", response_model=TodoResponse, status_code=201)
def create_todo(
    task_id: int,
    body: TodoCreate,
    current_user: User = Depends(get_current_user),
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    task_uc=Depends(get_task_use_cases),
):
    require_project_access(_task_project_id(task_id, task_uc), current_user.id)
    try:
        todo = use_cases.create(
            task_id=task_id, title=body.title, completed=body.completed, order=body.order
        )
        return TodoResponse.from_entity(todo)
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")


@router.patch("/{task_id}/todos/{todo_id}", response_model=TodoResponse)
def update_todo(
    task_id: int,
    todo_id: int,
    body: TodoUpdate,
    current_user: User = Depends(get_current_user),
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    task_uc=Depends(get_task_use_cases),
):
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    require_project_access(_task_project_id(task_id, task_uc), current_user.id)
    try:
        return TodoResponse.from_entity(use_cases.update(task_id, todo_id, updates))
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")
    except TodoNotFound:
        raise HTTPException(status_code=404, detail="TodoItem not found")


@router.delete("/{task_id}/todos/{todo_id}", status_code=204)
def delete_todo(
    task_id: int,
    todo_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TodoUseCases = Depends(get_todo_use_cases),
    task_uc=Depends(get_task_use_cases),
):
    require_project_access(_task_project_id(task_id, task_uc), current_user.id)
    try:
        use_cases.delete(task_id, todo_id)
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")
    except TodoNotFound:
        raise HTTPException(status_code=404, detail="TodoItem not found")
