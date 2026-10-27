# Servidor MCP (`jkanban_mcp`)

Servidor MCP que deja que los agentes del **proyecto SF** guarden y consulten en
JKanban los planes y actividades de cada proyecto. Habla con la **API REST** como
un usuario normal de JKanban: respeta permisos y reglas de negocio, y no toca la
base de datos directamente.

## Modelo

No añade entidades: reutiliza las de Kanban, así que todo se ve en el tablero web.

| SF | JKanban | En el tablero |
|----|---------|---------------|
| Proyecto | `Project` | proyecto |
| Plan | `Group` | columna |
| Actividad | `Task` | tarjeta |
| Paso | `TodoItem` | subtarea (checklist) |

Una actividad terminada es una tarea con `completed = true`. Las fechas son
`estimated_*` / `actual_*` de la tarea, en ISO 8601.

**Estados del método:** con [flujos](flows.md). Un flujo (p. ej. *Devslice*: Planificada
→ … → Terminada) se asocia a una etiqueta; al poner la etiqueta en un plan o actividad
entra en el estado inicial y solo avanza por las transiciones definidas. Planes y
actividades lo muestran en `states` (`{"Devslice": "En desarrollo"}`). La SF define
sus flujos y etiquetas como **globales** (sirven en todos los proyectos), con
`ensure_flow` y `create_tag` sin `project_id`; para eso su usuario es administrador.

## Estructura

```
jkanban_mcp/
├── client.py          # cliente HTTP: login JWT, reintento ante 401, JKanbanError
├── service.py         # SFService: operaciones en vocabulario SF (sin SDK de MCP)
├── server.py          # tools MCP (MCPServer, SDK 2.x) + main() por stdio
├── __main__.py        # python -m jkanban_mcp
├── requirements.txt   # mcp==2.3.0, httpx
└── tests/test_server.py  # capa MCP (se ejecuta en .venv-mcp)
tests/test_mcp_service.py  # SFService contra la API real (TestClient)
tests/test_mcp_flows.py    # flujos, etiquetas globales y estados (SFService)
tests/test_reorder.py      # endpoints de ordenar del backend
```

`server.py` convierte los `JKanbanError` en `ToolError`: el SDK solo enseña al
modelo el mensaje de un `ToolError`, y cualquier otra excepción llega como un
«Error executing tool» sin el motivo. Cada tool devuelve el estado guardado
después del cambio, para que el agente no dé por hecho lo que no se confirmó.

## Tools (44)

Solo usan funcionalidad que JKanban ya tiene. Lo que la SF pide y JKanban no
tiene (dependencias, bloqueos con motivo, enlaces a evidencias) queda fuera; ver
[Lo que falta](#lo-que-falta-en-jkanban).

**Vista general y consultas** (todos los proyectos, 3 llamadas a la API)

| Tool | Qué hace |
|------|----------|
| `overview(next_count?)` | Por proyecto: planes, actividades hechas/total, progreso, pasos, en curso, vencidas, última actividad, siguientes pendientes y `flow_states` (`{etiqueta: {estado: {plans, activities}}}`); más los totales. |
| `find_activities(project_id?, plan_id?, done?, tags?, priority?, text?, overdue?, in_progress?, modified_since?, limit?, states?)` | Actividades de todos los proyectos que cumplen todos los filtros, con su proyecto y plan, en orden de tablero → `{total, returned, activities}`. `states`: `{etiqueta: estado}`. |

*En curso* = con `actual_start` y sin terminar. *Vencida* = `estimated_end` pasado
y sin terminar (hora local del equipo donde corre el MCP).

**Proyectos y miembros**

| Tool | Qué hace |
|------|----------|
| `list_projects()` | Proyectos accesibles para el usuario del MCP. |
| `ensure_project(name, description?)` | Devuelve el proyecto con ese nombre (sin distinguir mayúsculas) o lo crea → `{project, created}`. Punto de entrada habitual. |
| `update_project(project_id, name?, description?)` | |
| `get_project(project_id, include_steps?)` | Estado completo: planes en orden → actividades con etiquetas, estados, prioridad y progreso. |
| `list_members` / `add_member` / `remove_member(project_id, email)` | Para que una persona vea en el tablero web los proyectos del MCP. |

**Planes, actividades y pasos**

| Tool | Qué hace |
|------|----------|
| `create_plan(project_id, name, description?, tags?)` | Nuevo plan al final del proyecto. |
| `update_plan(plan_id, name?, description?)` | |
| `reorder_plans(project_id, plan_ids)` | Lista completa de ids en el orden deseado. |
| `tag_plan(plan_id, add?, remove?)` | Etiquetas por nombre, entre las del proyecto y las globales; las que no existen se crean en el proyecto, sin flujo. Con flujo: entra en el estado inicial. |
| `delete_plan(plan_id, with_activities?)` | Falla (409) si tiene actividades, salvo con `with_activities=true`. |
| `create_activity(plan_id, title, description?, steps?, priority_id?, tags?, estimated_duration?, estimated_start?, estimated_end?)` | Al final del plan. Duración en horas. |
| `get_activity(activity_id)` | Detalle con pasos. |
| `update_activity(activity_id, title?, description?, done?, plan_id?, priority_id?, estimated_*?, actual_start?, actual_end?, clear?)` | Solo cambia lo indicado. `plan_id` la mueve; `clear` vacía `description`, `priority`, `estimated_*` o `actual_*`. |
| `reorder_activities(plan_id, activity_ids)` | Lista completa. |
| `tag_activity(activity_id, add?, remove?)` | Ídem para actividades. |
| `delete_activity(activity_id)` | |
| `add_steps(activity_id, steps)` | Al final. |
| `update_step(activity_id, step_id, done?, title?)` | |
| `reorder_steps(activity_id, step_ids)` | Lista completa. |
| `delete_step(activity_id, step_id)` | |

**Etiquetas** (sin `project_id`, globales: solo el administrador las crea o cambia)

| Tool | Qué hace |
|------|----------|
| `list_tags(project_id?)` | Globales; con proyecto, también las del proyecto. Cada una con `scope` y `flow`. |
| `create_tag(name, project_id?, color?, flow?)` | `flow` por nombre. Una global solo puede usar flujos globales. |
| `update_tag(tag_id, project_id?, name?, color?, flow?, remove_flow?)` | `project_id` si es de un proyecto. Cambiar o quitar el flujo falla (409) si está puesta en algún plan o actividad. |
| `delete_tag(tag_id, project_id?)` | La quita de planes y actividades, con su historial. |

**Flujos** (sin `project_id`, globales: solo el administrador)

| Tool | Qué hace |
|------|----------|
| `list_flows(project_id?)` | Globales; con proyecto, también los del proyecto. Estados y transiciones por nombre. |
| `create_flow(name, states, initial, transitions?, project_id?)` | `states`: nombres o `{name, color}`, en orden. `transitions`: `[{"from", "to"}]` por nombre. |
| `ensure_flow(...)` | Mismos argumentos. Crea el flujo o **añade** los estados y transiciones que falten; nunca borra ni cambia lo existente (ni el inicial ni los colores). → `{flow, created, added_states, added_transitions, extra_states, extra_transitions, initial_differs}`. Repetible: es la forma de que la SF deje sus flujos como los necesita. |
| `update_flow(flow_id, name)` / `delete_flow(flow_id)` | Borrar falla (409) si alguna etiqueta lo usa. |
| `add_flow_state(flow_id, name, color?, initial?)` | Al final. |
| `update_flow_state(flow_id, state, name?, color?, initial?, order?)` | `state` por id o nombre. `initial=true` lo hace el inicial (solo para asignaciones futuras). |
| `delete_flow_state(flow_id, state)` | Falla si hay planes o actividades en él (409, dice cuáles) o si es el inicial (422). |
| `add_flow_transition` / `remove_flow_transition(flow_id, from_state, to_state)` | Por id o nombre. |

**Estado de planes y actividades**

| Tool | Qué hace |
|------|----------|
| `set_flow_state(tag, to, plan_id? \| activity_id?, note?)` | Por nombres. Solo si existe la transición; si no, el error dice los destinos válidos. → `{tag, flow, state, next, plan\|activity}`. |
| `get_flow_history(tag, plan_id? \| activity_id?)` | `[{from, to, note, by, at}]`; entrar en el flujo tiene `from` nulo y quitar la etiqueta, `to` nulo. Se conserva al quitarla. |

Lo puede hacer cualquier miembro del proyecto, no solo el administrador.

**Prioridades** (por proyecto)

| Tool | Qué hace |
|------|----------|
| `list_priorities` / `create_priority` / `update_priority` / `delete_priority` | Se asignan a actividades con `priority_id`. |

### Validaciones propias del MCP

- **Ordenar:** el backend exige que los ids sean del proyecto o del grupo y no se
  repitan. El MCP exige además la lista **completa** de ids actuales (422 si no),
  para que no queden órdenes a medias.
- **Flujos:** `create_flow` y `ensure_flow` validan la definición antes de tocar nada,
  para que `ensure_flow` no deje un flujo a medias por una definición mal hecha.
### Limitaciones

- Los planes no tienen prioridad (en JKanban solo la tienen tareas y proyectos).
- La descripción de un plan no se puede vaciar (la API de grupos ignora `null`).
## Instalación

Requiere JKanban instalado y **arrancado** ([installation.md](installation.md)).

1. **Entorno propio.** El SDK de MCP 2.x necesita versiones de Starlette y Pydantic
   incompatibles con las que fija el backend, así que no se instala en `.venv`:

   ```powershell
   cd <JKANBAN>
   python -m venv .venv-mcp
   .\.venv-mcp\Scripts\python.exe -m pip install -r jkanban_mcp\requirements.txt
   ```

2. **Usuario de JKanban para el MCP.** Se recomienda uno dedicado (p. ej.
   `sf-bot@…`). Para la SF es **el administrador** de su JKanban, creado en la
   instalación con `python -m backend.create_admin` (JKanban arranca vacío y la SF
   lo configura todo). Para otros usos basta un usuario normal (desde la web o
   `POST /users/`). Solo ve los proyectos que posee o de los que es miembro: los
   que crea por `ensure_project` son suyos. Para que una persona los vea en el
   tablero, añádela como miembro.

3. **Registrar el MCP en el proyecto SF.** Desde la carpeta del proyecto SF:

   ```powershell
   claude mcp add jkanban --scope local `
     -e PYTHONPATH=<JKANBAN> `
     -e JKANBAN_URL=http://127.0.0.1:8000 `
     -e JKANBAN_EMAIL=sf-bot@example.com `
     -e JKANBAN_PASSWORD=<password> `
     -- <JKANBAN>\.venv-mcp\Scripts\python.exe -m jkanban_mcp
   ```

   `PYTHONPATH` hace falta porque Claude Code lanza el servidor desde la carpeta
   del proyecto SF, no desde la de JKanban. Usa `--scope local` (no se versiona)
   para no subir la contraseña al repo. Si prefieres `--scope project` (`.mcp.json`
   compartido), pon `"JKANBAN_PASSWORD": "${JKANBAN_PASSWORD}"` y define la
   variable en el entorno.

4. **Comprobar.** En Claude Code, dentro del proyecto SF: `/mcp` debe mostrar
   `jkanban` conectado con 44 tools.

| Variable | Defecto | |
|----------|---------|---|
| `JKANBAN_URL` | `http://127.0.0.1:8000` | URL de la API |
| `JKANBAN_EMAIL` | *(obligatoria)* | usuario del MCP |
| `JKANBAN_PASSWORD` | *(obligatoria)* | su contraseña |

## Tests

| Qué | Dónde | Cómo |
|-----|-------|------|
| `SFService` contra la API real (todas las operaciones, filtros y validaciones) | `tests/test_mcp_service.py` | `pytest` en `.venv` (con el resto de la suite) |
| Flujos, etiquetas globales, estados e historial en `SFService` | `tests/test_mcp_flows.py` | `pytest` en `.venv` |
| Endpoints de ordenar del backend | `tests/test_reorder.py` | `pytest` en `.venv` |
| Capa MCP: cada tool existe, pasa sus argumentos al servicio, valida la entrada y devuelve el motivo de los errores | `jkanban_mcp/tests/test_server.py` | `.venv-mcp\Scripts\python -m pytest jkanban_mcp/tests` (en `.venv` se salta) |

Para correr el test de la capa MCP, instalar pytest en `.venv-mcp`
(`pip install pytest==8.3.3`). El circuito completo por stdio (Claude Code ↔ MCP ↔
API) se ha probado a mano; no está automatizado.

## Lo que falta en JKanban

La [especificación de la SF](../../SoftwareFactory/docs/specs/funcional/software-factory.md)
y su metodología piden, además, cosas que JKanban no tiene y este MCP no puede dar:

- **Dependencias** entre planes o actividades.
- **Bloqueos** con motivo y acción necesaria (hoy, un estado «Bloqueada» en el flujo
  y la nota del cambio de estado).
- **Enlaces** a documentos e informes como campo propio (hoy, en la descripción).
- **Historial** de cambios de los demás campos (solo `modified_at`). El de estados sí
  existe (`get_flow_history`).

Los **estados del método y sus transiciones** ya no faltan: son los [flujos](flows.md).

Fallos del backend detectados al construir el MCP, **ya corregidos** (con tests en
`tests/test_reorder.py` y `tests/test_task_priority_scope.py`):

- Los endpoints de ordenar aceptaban ids de otros proyectos o grupos, así que con
  acceso a un proyecto se podía reordenar otro. Ahora responden 404 sin cambiar nada.
  Los ids repetidos responden 422.
- Una tarea aceptaba una prioridad de otro proyecto. Ahora responde 422
  (`PriorityNotInProject`).