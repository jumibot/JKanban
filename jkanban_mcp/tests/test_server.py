"""Capa MCP: registro de tools, paso de argumentos al servicio y errores.

Necesita el SDK de MCP, que no está en el .venv del backend. Se ejecuta con:
    .venv-mcp\\Scripts\\python -m pytest jkanban_mcp/tests
Con el pytest del backend se salta solo (importorskip).
"""
import asyncio
import inspect

import pytest

pytest.importorskip("mcp")

from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from jkanban_mcp.client import JKanbanError  # noqa: E402
from jkanban_mcp.server import build_server  # noqa: E402
from jkanban_mcp.service import SFService  # noqa: E402

# Una llamada de ejemplo por tool, con todos sus argumentos con nombre.
CALLS = {
    "list_projects": {},
    "ensure_project": {"name": "P", "description": "d"},
    "update_project": {"project_id": 1, "name": "N", "description": "d"},
    "get_project": {"project_id": 1, "include_steps": True},
    "overview": {"next_count": 5},
    "find_activities": {"project_id": 1, "plan_id": 2, "done": False, "tags": ["x"],
                        "priority": "Alta", "text": "api", "overdue": True,
                        "in_progress": False, "modified_since": "2026-10-01", "limit": 10},
    "list_members": {"project_id": 1},
    "add_member": {"project_id": 1, "email": "a@b.c"},
    "remove_member": {"project_id": 1, "email": "a@b.c"},
    "create_plan": {"project_id": 1, "name": "Plan", "description": "d", "tags": ["x"]},
    "update_plan": {"plan_id": 2, "name": "N", "description": "d"},
    "reorder_plans": {"project_id": 1, "plan_ids": [3, 2]},
    "tag_plan": {"plan_id": 2, "add": ["x"], "remove": ["y"]},
    "delete_plan": {"plan_id": 2, "with_activities": True},
    "create_activity": {"plan_id": 2, "title": "T", "description": "d", "steps": ["s"],
                        "priority_id": 5, "tags": ["x"], "estimated_duration": 1.5,
                        "estimated_start": "2026-11-02", "estimated_end": "2026-11-03"},
    "get_activity": {"activity_id": 4},
    "update_activity": {"activity_id": 4, "title": "T", "description": "d", "done": True,
                        "plan_id": 3, "priority_id": 5, "estimated_duration": 2.0,
                        "estimated_start": "2026-11-02", "estimated_end": "2026-11-03",
                        "actual_start": "2026-11-04", "actual_end": "2026-11-05",
                        "clear": ["actual_end"]},
    "reorder_activities": {"plan_id": 2, "activity_ids": [5, 4]},
    "tag_activity": {"activity_id": 4, "add": ["x"], "remove": ["y"]},
    "delete_activity": {"activity_id": 4},
    "add_steps": {"activity_id": 4, "steps": ["a", "b"]},
    "update_step": {"activity_id": 4, "step_id": 7, "done": True, "title": "t"},
    "reorder_steps": {"activity_id": 4, "step_ids": [8, 7]},
    "delete_step": {"activity_id": 4, "step_id": 7},
    "list_tags": {"project_id": 1},
    "create_tag": {"project_id": 1, "name": "x", "color": "#112233"},
    "update_tag": {"project_id": 1, "tag_id": 9, "name": "y", "color": "#112233"},
    "delete_tag": {"project_id": 1, "tag_id": 9},
    "list_priorities": {"project_id": 1},
    "create_priority": {"project_id": 1, "name": "Alta", "icon": "bolt", "color": "#112233"},
    "update_priority": {"project_id": 1, "priority_id": 5, "name": "A", "icon": "flag",
                        "color": "#112233"},
    "delete_priority": {"project_id": 1, "priority_id": 5},
}


class RecordingService:
    """Sustituto de SFService que anota con qué argumentos se le llama."""

    def __init__(self, fail_with: JKanbanError | None = None):
        self.calls: list[tuple[str, dict]] = []
        self._fail = fail_with

    def __getattr__(self, name):
        real = getattr(SFService, name)

        def method(*args, **kwargs):
            bound = inspect.signature(real).bind(None, *args, **kwargs)
            bound.apply_defaults()
            args_by_name = dict(bound.arguments)
            args_by_name.pop("self")
            self.calls.append((name, args_by_name))
            if self._fail:
                raise self._fail
            returns_list = str(inspect.signature(real).return_annotation).startswith("list")
            return [{"ok": name}] if returns_list else {"ok": name}
        return method


def run(coro):
    return asyncio.run(coro)


def test_every_service_operation_has_a_tool():
    tools = {t.name for t in run(build_server(RecordingService()).list_tools())}
    public = {n for n, _ in inspect.getmembers(SFService, inspect.isfunction) if not n.startswith("_")}
    assert tools == public  # cada tool se llama igual que su operación del servicio
    assert tools == set(CALLS)


@pytest.mark.parametrize("tool", sorted(CALLS))
def test_tool_passes_arguments_to_service(tool):
    service = RecordingService()
    result = run(build_server(service).call_tool(tool, CALLS[tool]))
    assert not result.is_error, result.content
    assert service.calls == [(tool, CALLS[tool])]


def test_optional_arguments_default_to_none():
    service = RecordingService()
    run(build_server(service).call_tool("update_activity", {"activity_id": 4, "done": True}))
    (_, args), = service.calls
    assert args["done"] is True
    assert all(v is None for k, v in args.items() if k not in ("activity_id", "done"))


def test_api_error_reaches_the_model_with_its_reason():
    service = RecordingService(fail_with=JKanbanError(409, "el plan 2 tiene 1 actividades"))
    with pytest.raises(ToolError) as e:
        run(build_server(service).call_tool("delete_plan", {"plan_id": 2}))
    # ToolError (no UnexpectedToolError): el SDK envía su texto al modelo
    assert type(e.value) is ToolError
    assert "HTTP 409" in str(e.value) and "el plan 2 tiene 1 actividades" in str(e.value)


@pytest.mark.parametrize("tool,args", [
    ("create_tag", {"project_id": 1, "name": "x", "color": "rojo"}),
    ("update_activity", {"activity_id": 4, "clear": ["title"]}),
    ("create_activity", {"plan_id": 2, "title": "T", "estimated_duration": -1}),
    ("reorder_plans", {"project_id": 1}),
])
def test_invalid_arguments_are_rejected_before_the_service(tool, args):
    service = RecordingService()
    with pytest.raises(ToolError) as e:
        run(build_server(service).call_tool(tool, args))
    assert type(e.value) is ToolError
    assert service.calls == []


def test_server_publishes_instructions():
    server = build_server(RecordingService())
    assert "ensure_project" in server.instructions
