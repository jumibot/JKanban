"""Servidor MCP (stdio) con las tools de planes y actividades del proyecto SF.

Configuración por variables de entorno:
    JKANBAN_URL       URL de la API (defecto: http://127.0.0.1:8000)
    JKANBAN_EMAIL     usuario de JKanban con el que opera el MCP
    JKANBAN_PASSWORD  su contraseña
"""
from __future__ import annotations

import functools
import os
from typing import Annotated, Literal, NotRequired, TypedDict

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

from jkanban_mcp.client import JKanbanClient, JKanbanError
from jkanban_mcp.service import SFService

INSTRUCTIONS = """\
Persistencia de planes y actividades de los proyectos SF en JKanban.
Jerarquía: proyecto > plan > actividad > paso. En el tablero de JKanban cada plan
es una columna, cada actividad una tarjeta y cada paso una subtarea.
Para una visión general sin entrar en cada proyecto: overview(); para consultas
entre proyectos (pendientes, vencidas, en curso, por etiqueta o texto): find_activities.
Flujo habitual: ensure_project(nombre) para obtener el id del proyecto,
get_project(id) para ver el estado completo, y luego create_plan /
create_activity / update_activity (done=true al terminar) / update_step.
Orden: reorder_plans, reorder_activities y reorder_steps reciben la lista completa
de ids en el orden deseado. Etiquetas por nombre con tag_activity / tag_plan (las
que no existen se crean). Prioridades: list_priorities y priority_id en las actividades.
Para que una persona vea el proyecto en el tablero web, add_member(email).
Flujos: un flujo define estados (uno inicial) y las transiciones permitidas, y se
asocia a una etiqueta. Al poner esa etiqueta en un plan o actividad entra en el
estado inicial; set_flow_state(tag, to, ...) la mueve solo por una transición
existente, y get_flow_history muestra los cambios. ensure_flow deja un flujo como se
define sin borrar nada (repetible). Flujos y etiquetas son globales (sin project_id;
solo el administrador los gestiona) o de un proyecto. Planes y actividades muestran
su estado en `states` ({etiqueta: estado}); find_activities filtra por `states`.
Cada tool devuelve el estado guardado: un cambio solo está hecho si la tool lo confirma.
Las fechas van en ISO 8601 (p. ej. 2026-10-26 o 2026-10-26T09:30:00).
"""

ProjectId = Annotated[int, Field(description="id del proyecto (de ensure_project o list_projects)")]
PlanId = Annotated[int, Field(description="id del plan")]
ActivityId = Annotated[int, Field(description="id de la actividad")]
IsoDate = Annotated[str | None, Field(description="fecha ISO 8601")]
Hours = Annotated[float | None, Field(description="duración estimada en horas", ge=0)]
PriorityId = Annotated[int | None, Field(description="id de una prioridad del proyecto (list_priorities)")]
TagNames = Annotated[list[str] | None, Field(description="nombres de etiqueta; las que no existen se crean")]
HexColor = Annotated[str | None, Field(description="color #RRGGBB", pattern=r"^#[0-9A-Fa-f]{6}$")]
StateRef = Annotated[int | str, Field(description="id o nombre del estado")]
FlowName = Annotated[str | None, Field(description="nombre del flujo de la etiqueta")]
ScopeProject = Annotated[int | None, Field(
    description="id del proyecto; sin él, ámbito global (solo administrador para crear o cambiar)")]


class FlowStateDef(TypedDict):
    name: str
    color: NotRequired[str]


Transition = TypedDict("Transition", {"from": str, "to": str})
FlowStates = Annotated[list[str | FlowStateDef], Field(
    description="estados en orden: nombres o {name, color}", min_length=1)]
FlowTransitions = Annotated[list[Transition] | None, Field(
    description='transiciones permitidas por nombre: [{"from": "A", "to": "B"}]')]

Clearable = Literal["description", "priority", "estimated_duration", "estimated_start",
                    "estimated_end", "actual_start", "actual_end"]


class _ReportApiErrors:
    """Proxy del servicio: convierte JKanbanError en ToolError.

    El SDK solo enseña al modelo el mensaje de un ToolError; cualquier otra
    excepción llega como un «Error executing tool» genérico, sin el motivo.
    """

    def __init__(self, service: SFService):
        self._service = service

    def __getattr__(self, name: str):
        fn = getattr(self._service, name)

        @functools.wraps(fn)
        def call(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except JKanbanError as e:
                raise ToolError(str(e)) from e
        return call


def build_server(service: SFService) -> MCPServer:
    service = _ReportApiErrors(service)
    mcp = MCPServer(name="jkanban", instructions=INSTRUCTIONS)

    # ── Proyectos ─────────────────────────────────────────────────────────

    @mcp.tool()
    def list_projects() -> list[dict]:
        """Lista los proyectos accesibles para el usuario del MCP."""
        return service.list_projects()

    @mcp.tool()
    def ensure_project(name: str, description: str | None = None) -> dict:
        """Devuelve el proyecto con ese nombre (sin distinguir mayúsculas) o lo crea si no existe.
        Respuesta: {project, created}."""
        return service.ensure_project(name, description)

    @mcp.tool()
    def update_project(project_id: ProjectId, name: str | None = None,
                       description: str | None = None) -> dict:
        """Cambia el nombre o la descripción de un proyecto."""
        return service.update_project(project_id, name, description)

    @mcp.tool()
    def get_project(project_id: ProjectId, include_steps: bool = False) -> dict:
        """Estado completo de un proyecto: planes en orden con sus actividades, etiquetas,
        prioridad y progreso. include_steps=true añade el detalle de los pasos."""
        return service.get_project(project_id, include_steps)

    # ── Vista general y consultas ─────────────────────────────────────────

    @mcp.tool()
    def overview(next_count: Annotated[int, Field(
            description="cuántas actividades pendientes mostrar por proyecto", ge=0, le=20)] = 3) -> dict:
        """Vista general de TODOS los proyectos sin entrar en cada uno: planes, actividades
        hechas/total, progreso, pasos, en curso (con inicio real y sin terminar), vencidas
        (fin estimado pasado y sin terminar), última actividad, siguientes pendientes y
        flow_states (planes y actividades por etiqueta y estado)."""
        return service.overview(next_count)

    @mcp.tool()
    def find_activities(project_id: Annotated[int | None, Field(description="limitar a un proyecto")] = None,
                        plan_id: Annotated[int | None, Field(description="limitar a un plan")] = None,
                        done: Annotated[bool | None, Field(description="true hechas, false pendientes")] = None,
                        tags: Annotated[list[str] | None, Field(
                            description="deben tener TODAS estas etiquetas")] = None,
                        priority: Annotated[str | None, Field(description="nombre de la prioridad")] = None,
                        text: Annotated[str | None, Field(
                            description="texto en el título o la descripción")] = None,
                        overdue: Annotated[bool | None, Field(
                            description="fin estimado pasado y sin terminar")] = None,
                        in_progress: Annotated[bool | None, Field(
                            description="con inicio real y sin terminar")] = None,
                        modified_since: Annotated[str | None, Field(
                            description="modificadas (o creadas) desde esta fecha ISO 8601")] = None,
                        limit: Annotated[int, Field(ge=1, le=500)] = 50,
                        states: Annotated[dict[str, str] | None, Field(
                            description='estado de etiquetas con flujo, p. ej. {"Devslice": "En desarrollo"}')] = None,
                        ) -> dict:
        """Busca actividades en todos los proyectos combinando filtros (todos deben cumplirse).
        Cada resultado incluye proyecto y plan. Respuesta: {total, returned, activities}."""
        return service.find_activities(project_id, plan_id, done, tags, priority, text,
                                       overdue, in_progress, modified_since, limit, states)

    # ── Miembros ──────────────────────────────────────────────────────────

    @mcp.tool()
    def list_members(project_id: ProjectId) -> list[dict]:
        """Miembros del proyecto (además del propietario)."""
        return service.list_members(project_id)

    @mcp.tool()
    def add_member(project_id: ProjectId, email: str) -> dict:
        """Da acceso al proyecto a un usuario de JKanban existente, por su email."""
        return service.add_member(project_id, email)

    @mcp.tool()
    def remove_member(project_id: ProjectId, email: str) -> dict:
        """Quita el acceso de un miembro al proyecto."""
        return service.remove_member(project_id, email)

    # ── Planes ────────────────────────────────────────────────────────────

    @mcp.tool()
    def create_plan(project_id: ProjectId, name: str, description: str | None = None,
                    tags: TagNames = None) -> dict:
        """Crea un plan (columna del tablero) al final del proyecto."""
        return service.create_plan(project_id, name, description, tags)

    @mcp.tool()
    def update_plan(plan_id: PlanId, name: str | None = None,
                    description: str | None = None) -> dict:
        """Cambia el nombre o la descripción de un plan."""
        return service.update_plan(plan_id, name, description)

    @mcp.tool()
    def reorder_plans(project_id: ProjectId, plan_ids: Annotated[list[int], Field(
            description="todos los ids de planes del proyecto, en el orden deseado")]) -> list[dict]:
        """Reordena los planes (columnas) de un proyecto."""
        return service.reorder_plans(project_id, plan_ids)

    @mcp.tool()
    def tag_plan(plan_id: PlanId, add: TagNames = None, remove: TagNames = None) -> dict:
        """Añade o quita etiquetas de un plan, por nombre."""
        return service.tag_plan(plan_id, add, remove)

    @mcp.tool()
    def delete_plan(plan_id: PlanId, with_activities: bool = False) -> dict:
        """Borra un plan. Si tiene actividades falla, salvo con with_activities=true,
        que las borra también. Irreversible."""
        return service.delete_plan(plan_id, with_activities)

    # ── Actividades ───────────────────────────────────────────────────────

    @mcp.tool()
    def create_activity(plan_id: PlanId, title: str, description: str | None = None,
                        steps: Annotated[list[str] | None, Field(
                            description="títulos de los pasos, en orden")] = None,
                        priority_id: PriorityId = None,
                        tags: TagNames = None,
                        estimated_duration: Hours = None,
                        estimated_start: IsoDate = None,
                        estimated_end: IsoDate = None) -> dict:
        """Crea una actividad al final de un plan, opcionalmente con pasos, prioridad y etiquetas."""
        return service.create_activity(plan_id, title, description, steps, priority_id, tags,
                                       estimated_duration, estimated_start, estimated_end)

    @mcp.tool()
    def get_activity(activity_id: ActivityId) -> dict:
        """Detalle de una actividad con todos sus pasos."""
        return service.get_activity(activity_id)

    @mcp.tool()
    def update_activity(activity_id: ActivityId, title: str | None = None,
                        description: str | None = None,
                        done: Annotated[bool | None, Field(
                            description="true = actividad terminada")] = None,
                        plan_id: Annotated[int | None, Field(
                            description="mover la actividad a otro plan")] = None,
                        priority_id: PriorityId = None,
                        estimated_duration: Hours = None,
                        estimated_start: IsoDate = None,
                        estimated_end: IsoDate = None,
                        actual_start: IsoDate = None,
                        actual_end: IsoDate = None,
                        clear: Annotated[list[Clearable] | None, Field(
                            description="campos que se vacían")] = None) -> dict:
        """Actualiza una actividad. Solo cambian los campos indicados; `clear` vacía campos."""
        return service.update_activity(activity_id, title, description, done, plan_id,
                                       priority_id, estimated_duration, estimated_start,
                                       estimated_end, actual_start, actual_end, clear)

    @mcp.tool()
    def reorder_activities(plan_id: PlanId, activity_ids: Annotated[list[int], Field(
            description="todos los ids de actividades del plan, en el orden deseado")]) -> list[dict]:
        """Reordena las actividades de un plan."""
        return service.reorder_activities(plan_id, activity_ids)

    @mcp.tool()
    def tag_activity(activity_id: ActivityId, add: TagNames = None,
                     remove: TagNames = None) -> dict:
        """Añade o quita etiquetas de una actividad, por nombre."""
        return service.tag_activity(activity_id, add, remove)

    @mcp.tool()
    def delete_activity(activity_id: ActivityId) -> dict:
        """Borra una actividad y sus pasos. Irreversible."""
        return service.delete_activity(activity_id)

    # ── Pasos ─────────────────────────────────────────────────────────────

    @mcp.tool()
    def add_steps(activity_id: ActivityId, steps: list[str]) -> dict:
        """Añade pasos al final de una actividad."""
        return service.add_steps(activity_id, steps)

    @mcp.tool()
    def update_step(activity_id: ActivityId, step_id: int, done: bool | None = None,
                    title: str | None = None) -> dict:
        """Marca un paso como hecho o pendiente, o cambia su título."""
        return service.update_step(activity_id, step_id, done, title)

    @mcp.tool()
    def reorder_steps(activity_id: ActivityId, step_ids: Annotated[list[int], Field(
            description="todos los ids de pasos de la actividad, en el orden deseado")]) -> dict:
        """Reordena los pasos de una actividad."""
        return service.reorder_steps(activity_id, step_ids)

    @mcp.tool()
    def delete_step(activity_id: ActivityId, step_id: int) -> dict:
        """Borra un paso de una actividad."""
        return service.delete_step(activity_id, step_id)

    # ── Etiquetas ─────────────────────────────────────────────────────────

    @mcp.tool()
    def list_tags(project_id: Annotated[int | None, Field(
            description="id del proyecto; sin él, solo las globales")] = None) -> list[dict]:
        """Etiquetas globales y, con project_id, también las del proyecto."""
        return service.list_tags(project_id)

    @mcp.tool()
    def create_tag(name: str, project_id: ScopeProject = None, color: HexColor = None,
                   flow: FlowName = None) -> dict:
        """Crea una etiqueta global (sin project_id) o de un proyecto, opcionalmente con
        flujo (una global solo puede usar flujos globales)."""
        return service.create_tag(name, project_id, color, flow)

    @mcp.tool()
    def update_tag(tag_id: int, project_id: Annotated[int | None, Field(
                       description="id del proyecto si la etiqueta es de un proyecto")] = None,
                   name: str | None = None, color: HexColor = None, flow: FlowName = None,
                   remove_flow: bool = False) -> dict:
        """Renombra, recolorea o cambia el flujo de una etiqueta. Cambiar o quitar el flujo
        falla si la etiqueta está puesta en algún plan o actividad."""
        return service.update_tag(tag_id, project_id, name, color, flow, remove_flow)

    @mcp.tool()
    def delete_tag(tag_id: int, project_id: Annotated[int | None, Field(
            description="id del proyecto si la etiqueta es de un proyecto")] = None) -> dict:
        """Borra una etiqueta (y la quita de planes y actividades, con su historial)."""
        return service.delete_tag(tag_id, project_id)

    # ── Flujos ────────────────────────────────────────────────────────────

    @mcp.tool()
    def list_flows(project_id: Annotated[int | None, Field(
            description="id del proyecto; sin él, solo los globales")] = None) -> list[dict]:
        """Flujos globales y, con project_id, también los del proyecto."""
        return service.list_flows(project_id)

    @mcp.tool()
    def create_flow(name: str, states: FlowStates, initial: str,
                    transitions: FlowTransitions = None,
                    project_id: ScopeProject = None) -> dict:
        """Crea un flujo: estados en orden, el inicial y las transiciones permitidas."""
        return service.create_flow(name, states, initial, transitions, project_id)

    @mcp.tool()
    def ensure_flow(name: str, states: FlowStates, initial: str,
                    transitions: FlowTransitions = None,
                    project_id: ScopeProject = None) -> dict:
        """Deja el flujo como se define, de forma repetible: lo crea si no existe o le
        añade los estados y transiciones que falten. Nunca borra ni cambia nada (ni el
        inicial ni los colores). Respuesta: {flow, created, added_states,
        added_transitions, extra_states, extra_transitions, initial_differs}."""
        return service.ensure_flow(name, states, initial, transitions, project_id)

    @mcp.tool()
    def update_flow(flow_id: int, name: str) -> dict:
        """Renombra un flujo."""
        return service.update_flow(flow_id, name)

    @mcp.tool()
    def delete_flow(flow_id: int) -> dict:
        """Borra un flujo. Falla si alguna etiqueta lo usa."""
        return service.delete_flow(flow_id)

    @mcp.tool()
    def add_flow_state(flow_id: int, name: str, color: HexColor = None,
                       initial: bool = False) -> dict:
        """Añade un estado al final del flujo (initial=true lo hace el inicial)."""
        return service.add_flow_state(flow_id, name, color, initial)

    @mcp.tool()
    def update_flow_state(flow_id: int, state: StateRef, name: str | None = None,
                          color: HexColor = None,
                          initial: Annotated[bool | None, Field(
                              description="true = pasa a ser el estado inicial")] = None,
                          order: Annotated[int | None, Field(description="posición (sort_order)")] = None,
                          ) -> dict:
        """Renombra, recolorea o reordena un estado, o lo convierte en el inicial
        (solo afecta a las asignaciones futuras)."""
        return service.update_flow_state(flow_id, state, name, color, initial, order)

    @mcp.tool()
    def delete_flow_state(flow_id: int, state: StateRef) -> dict:
        """Borra un estado y sus transiciones. Falla si hay planes o actividades en él
        o si es el inicial."""
        return service.delete_flow_state(flow_id, state)

    @mcp.tool()
    def add_flow_transition(flow_id: int, from_state: StateRef, to_state: StateRef) -> dict:
        """Permite pasar de un estado a otro."""
        return service.add_flow_transition(flow_id, from_state, to_state)

    @mcp.tool()
    def remove_flow_transition(flow_id: int, from_state: StateRef, to_state: StateRef) -> dict:
        """Quita una transición (los elementos en ese estado pueden quedarse sin salida)."""
        return service.remove_flow_transition(flow_id, from_state, to_state)

    # ── Estado de planes y actividades ────────────────────────────────────

    @mcp.tool()
    def set_flow_state(tag: Annotated[str, Field(description="nombre de la etiqueta con flujo")],
                       to: Annotated[str, Field(description="nombre del estado destino")],
                       plan_id: Annotated[int | None, Field(description="el plan, o bien...")] = None,
                       activity_id: Annotated[int | None, Field(description="...la actividad")] = None,
                       note: Annotated[str | None, Field(
                           description="motivo; queda en el historial", max_length=1000)] = None) -> dict:
        """Cambia el estado de una etiqueta en un plan o actividad (uno de los dos). Solo se
        permite si el flujo tiene esa transición; si no, el error dice los destinos válidos.
        Respuesta: {tag, flow, state, next, plan|activity}."""
        return service.set_flow_state(tag, to, plan_id, activity_id, note)

    @mcp.tool()
    def get_flow_history(tag: Annotated[str, Field(description="nombre de la etiqueta")],
                         plan_id: Annotated[int | None, Field(description="el plan, o bien...")] = None,
                         activity_id: Annotated[int | None, Field(description="...la actividad")] = None,
                         ) -> list[dict]:
        """Historial de estados de una etiqueta en un plan o actividad: [{from, to, note,
        by, at}]. Entrar en el flujo tiene from nulo; salir (quitar la etiqueta), to nulo."""
        return service.get_flow_history(tag, plan_id, activity_id)

    # ── Prioridades ───────────────────────────────────────────────────────

    @mcp.tool()
    def list_priorities(project_id: ProjectId) -> list[dict]:
        """Prioridades definidas en el proyecto."""
        return service.list_priorities(project_id)

    @mcp.tool()
    def create_priority(project_id: ProjectId, name: str,
                        icon: Annotated[str | None, Field(
                            description="nombre de icono Material Symbols (defecto: flag)")] = None,
                        color: HexColor = None) -> dict:
        """Crea una prioridad en el proyecto."""
        return service.create_priority(project_id, name, icon, color)

    @mcp.tool()
    def update_priority(project_id: ProjectId, priority_id: int, name: str | None = None,
                        icon: str | None = None, color: HexColor = None) -> dict:
        """Cambia nombre, icono o color de una prioridad."""
        return service.update_priority(project_id, priority_id, name, icon, color)

    @mcp.tool()
    def delete_priority(project_id: ProjectId, priority_id: int) -> dict:
        """Borra una prioridad del proyecto."""
        return service.delete_priority(project_id, priority_id)

    return mcp


def main() -> None:
    email = os.environ.get("JKANBAN_EMAIL")
    password = os.environ.get("JKANBAN_PASSWORD")
    if not email or not password:
        raise SystemExit("Faltan JKANBAN_EMAIL y/o JKANBAN_PASSWORD")
    client = JKanbanClient(os.environ.get("JKANBAN_URL", "http://127.0.0.1:8000"), email, password)
    build_server(SFService(client)).run("stdio")
