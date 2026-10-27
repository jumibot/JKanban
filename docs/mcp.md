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
tests/test_reorder.py      # endpoints de ordenar del backend
```

`server.py` convierte los `JKanbanError` en `ToolError`: el SDK solo enseña al
modelo el mensaje de un `ToolError`, y cualquier otra excepción llega como un
«Error executing tool» sin el motivo. Cada tool devuelve el estado guardado
después del cambio, para que el agente no dé por hecho lo que no se confirmó.

## Tools (32)

Solo usan funcionalidad que JKanban ya tiene. Lo que la SF pide y JKanban no
tiene (estados del método, dependencias, bloqueos con motivo, enlaces a
evidencias, historial) queda fuera; ver [Lo que falta](#lo-que-falta-en-jkanban).

**Vista general y consultas** (todos los proyectos, 3 llamadas a la API)

| Tool | Qué hace |
|------|----------|
| `overview(next_count?)` | Por proyecto: planes, actividades hechas/total, progreso, pasos, en curso, vencidas, última actividad y siguientes pendientes; más los totales. |
| `find_activities(project_id?, plan_id?, done?, tags?, priority?, text?, overdue?, in_progress?, modified_since?, limit?)` | Actividades de todos los proyectos que cumplen todos los filtros, con su proyecto y plan, en orden de tablero → `{total, returned, activities}`. |

*En curso* = con `actual_start` y sin terminar. *Vencida* = `estimated_end` pasado
y sin terminar (hora local del equipo donde corre el MCP).

**Proyectos y miembros**

| Tool | Qué hace |
|------|----------|
| `list_projects()` | Proyectos accesibles para el usuario del MCP. |
| `ensure_project(name, description?)` | Devuelve el proyecto con ese nombre (sin distinguir mayúsculas) o lo crea → `{project, created}`. Punto de entrada habitual. |
| `update_project(project_id, name?, description?)` | |
| `get_project(project_id, include_steps?)` | Estado completo: planes en orden → actividades con etiquetas, prioridad y progreso. |
| `list_members` / `add_member` / `remove_member(project_id, email)` | Para que una persona vea en el tablero web los proyectos del MCP. |

**Planes, actividades y pasos**

| Tool | Qué hace |
|------|----------|
| `create_plan(project_id, name, description?, tags?)` | Nuevo plan al final del proyecto. |
| `update_plan(plan_id, name?, description?)` | |
| `reorder_plans(project_id, plan_ids)` | Lista completa de ids en el orden deseado. |
| `tag_plan(plan_id, add?, remove?)` | Etiquetas por nombre. |
| `delete_plan(plan_id, with_activities?)` | Falla (409) si tiene actividades, salvo con `with_activities=true`. |
| `create_activity(plan_id, title, description?, steps?, priority_id?, tags?, estimated_duration?, estimated_start?, estimated_end?)` | Al final del plan. Duración en horas. |
| `get_activity(activity_id)` | Detalle con pasos. |
| `update_activity(activity_id, title?, description?, done?, plan_id?, priority_id?, estimated_*?, actual_start?, actual_end?, clear?)` | Solo cambia lo indicado. `plan_id` la mueve; `clear` vacía `description`, `priority`, `estimated_*` o `actual_*`. |
| `reorder_activities(plan_id, activity_ids)` | Lista completa. |
| `tag_activity(activity_id, add?, remove?)` | Etiquetas por nombre. |
| `delete_activity(activity_id)` | |
| `add_steps(activity_id, steps)` | Al final. |
| `update_step(activity_id, step_id, done?, title?)` | |
| `reorder_steps(activity_id, step_ids)` | Lista completa. |
| `delete_step(activity_id, step_id)` | |

**Etiquetas y prioridades** (por proyecto)

| Tool | Qué hace |
|------|----------|
| `list_tags` / `create_tag` / `update_tag` / `delete_tag` | Las etiquetas que se añaden por nombre y no existen se crean solas. |
| `list_priorities` / `create_priority` / `update_priority` / `delete_priority` | Se asignan a actividades con `priority_id`. |

### Validaciones propias del MCP

- **Ordenar:** el backend exige que los ids sean del proyecto o del grupo y no se
  repitan. El MCP exige además la lista **completa** de ids actuales (422 si no),
  para que no queden órdenes a medias.
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
   `jkanban` conectado con 32 tools.

| Variable | Defecto | |
|----------|---------|---|
| `JKANBAN_URL` | `http://127.0.0.1:8000` | URL de la API |
| `JKANBAN_EMAIL` | *(obligatoria)* | usuario del MCP |
| `JKANBAN_PASSWORD` | *(obligatoria)* | su contraseña |

## Tests

| Qué | Dónde | Cómo |
|-----|-------|------|
| `SFService` contra la API real (todas las operaciones, filtros y validaciones) | `tests/test_mcp_service.py` | `pytest` en `.venv` (con el resto de la suite) |
| Endpoints de ordenar del backend | `tests/test_reorder.py` | `pytest` en `.venv` |
| Capa MCP: cada tool existe, pasa sus argumentos al servicio, valida la entrada y devuelve el motivo de los errores | `jkanban_mcp/tests/test_server.py` | `.venv-mcp\Scripts\python -m pytest jkanban_mcp/tests` (en `.venv` se salta) |

Para correr el test de la capa MCP, instalar pytest en `.venv-mcp`
(`pip install pytest==8.3.3`). El circuito completo por stdio (Claude Code ↔ MCP ↔
API) se ha probado a mano; no está automatizado.

## Lo que falta en JKanban

La [especificación de la SF](../../SoftwareFactory/docs/specs/funcional/software-factory.md)
y su metodología piden, además, cosas que JKanban no tiene y este MCP no puede dar:

- **Estados** del método (Planificada → … → Terminada) y sus transiciones. Hoy solo
  hay `done`. Se pueden imitar con etiquetas, sin validar transiciones.
- **Dependencias** entre planes o actividades.
- **Bloqueos** con motivo y acción necesaria (hoy, como mucho, una etiqueta y texto).
- **Enlaces** a documentos e informes como campo propio (hoy, en la descripción).
- **Historial** de cambios (solo `modified_at`).

Fallos del backend detectados al construir el MCP, **ya corregidos** (con tests en
`tests/test_reorder.py` y `tests/test_task_priority_scope.py`):

- Los endpoints de ordenar aceptaban ids de otros proyectos o grupos, así que con
  acceso a un proyecto se podía reordenar otro. Ahora responden 404 sin cambiar nada.
  Los ids repetidos responden 422.
- Una tarea aceptaba una prioridad de otro proyecto. Ahora responde 422
  (`PriorityNotInProject`).