# Flujos y etiquetas globales — especificación

> Estado: **pendiente de implementar**. Acordada con el propietario el 2026-10-27.
> Origen: la Software Factory (SF) necesita estados con transiciones para su
> trabajo (metodología, sección 4). En lugar de fijar en JKanban los estados del
> método, JKanban ofrece flujos genéricos que cada cual define.

## 1. Idea

- Un **flujo** es una definición reutilizable: una lista de **estados** (uno
  marcado como **inicial**) y las **transiciones** permitidas entre ellos.
- Una **etiqueta** puede usar un flujo. Al poner esa etiqueta en un plan (grupo) o
  en una actividad (tarea), el elemento entra en el estado inicial. A partir de
  ahí solo puede pasar a los estados que permitan las transiciones.
- El estado es **de cada elemento**: la misma etiqueta puede estar en estados
  distintos en elementos distintos.
- Flujos y etiquetas pueden ser **globales** (sirven en todos los proyectos) o
  **de un proyecto**. La SF usará solo globales.
- JKanban no conoce el significado de los estados: no hay estados «finales» ni
  condiciones de negocio. El nombre del estado lo dice todo, y las reglas propias
  de cada método las aplica quien lo usa (la SF, vía MCP).

## 2. Decisiones

| Tema | Decisión |
|------|----------|
| Flujos | Entidad propia, separada de las etiquetas. Varias etiquetas pueden usar el mismo flujo. |
| Ámbito | Flujos y etiquetas globales o de proyecto. La SF, todo global. |
| Estado inicial | Obligatorio: exactamente uno por flujo. |
| Desasignar | Siempre permitido; el elemento pierde su estado. Sin protección por ahora. |
| Modificar un flujo en uso | Permitido, con comprobación fina por estado (sección 4.3). |
| Estados finales | No se marcan. |
| Condiciones de transición | Ninguna en JKanban; solo se valida que la transición exista. |
| Registro de cambios | Sí: cada cambio de estado se registra. |
| Datos actuales | Son de prueba: la migración no tiene que conservar etiquetas. |
| Gestión de lo global | Solo el **administrador**. El usuario del MCP de la SF es administrador. |
| Flujo de una etiqueta | Una etiqueta **global** solo usa flujos **globales**; una de **proyecto**, globales o de su proyecto. |
| `ensure_flow` (MCP) | Crea el flujo o **añade** lo que falte; nunca borra ni cambia lo existente, e informa de las diferencias (sección 6). |
| Arranque en vacío | JKanban puede arrancar sin datos de demostración y con un administrador creado por comando (sección 2b). La SF lo configura todo por el MCP. |
| Lo que define la SF | Nadie más puede modificarlo; otros pueden usarlo y añadir lo suyo. Se consigue con los roles: la SF es el **único administrador** de su JKanban (sección 4.5). |

## 2b. Requisito previo: arrancar JKanban vacío

La SF instala JKanban, lo arranca **sin datos** y lo configura entero por el MCP.
Hoy no es posible: con una base de datos nueva se cargan datos de demostración, y
el único administrador es el de esos datos, con una contraseña ficticia.

- **Variable `JKANBAN_DEMO_DATA`.** Con `0`, no se cargan los datos de
  demostración. Por defecto `1`, para no cambiar el comportamiento actual. La
  instalación de la SF la pone a `0`.
- **Comando para crear un administrador**, a través de los casos de uso (sin SQL):
  ```
  python -m backend.create_admin --email <email> --name <nombre> --password <contraseña>
  ```
  - Si el email no existe, crea el usuario como administrador.
  - Si existe, lo convierte en administrador; con `--password`, además fija la
    contraseña.
  - Respeta `SQLITE_PATH` y crea la base de datos si no existe.
- **Guía de instalación** (`docs/installation.md`): usa este comando en lugar de
  fijar la contraseña del administrador de demostración, y documenta
  `JKANBAN_DEMO_DATA`.
- Se descarta «el primer usuario registrado es administrador»: si la instancia es
  accesible, cualquiera podría registrarse antes.

## 3. Modelo de datos

| Tabla | Columnas | Notas |
|-------|----------|-------|
| `flows` (nueva) | `id`, `name`, `project_id` (nulo = global), auditoría (`created_by`…) | Nombre único en su ámbito. |
| `flow_states` (nueva) | `id`, `flow_id`, `name`, `color`, `sort_order`, `is_initial` | Nombre único dentro del flujo; un único inicial. |
| `flow_transitions` (nueva) | `flow_id`, `from_state_id`, `to_state_id` | Única; `from ≠ to`. |
| `tags` | `project_id` pasa a **admitir nulo** (= global); nueva `flow_id` (nula) | Requiere reconstruir la tabla en SQLite. |
| `task_tags`, `group_tags` | nueva `state_id` (nula) | Estado actual; solo si la etiqueta tiene flujo. |
| `flow_state_changes` (nueva) | `id`, `task_id` o `group_id` (uno de los dos), `tag_id`, `from_state`, `to_state`, `note`, `changed_by`, `changed_at` | Guarda los **nombres** de los estados, para que el registro siga siendo legible aunque luego se renombren o borren. |

Unicidad de nombres (en el caso de uso, porque `UNIQUE` no trata los nulos como
iguales):
- Una etiqueta global no puede llamarse igual que otra global, ni que una de
  proyecto. Una de proyecto no puede llamarse igual que una global ni que otra de
  su proyecto. Lo mismo para los flujos.

## 4. Reglas

### 4.1. Definir un flujo
- Al menos un estado; exactamente uno inicial; nombres de estado sin repetir.
- Las transiciones unen estados del mismo flujo, sin repetirse y sin `from = to`.
- Se crea en una sola operación (estados y transiciones por nombre). Después se
  puede editar (4.3).

### 4.2. Usar un flujo
- **Asignar** una etiqueta con flujo a un plan o actividad → estado inicial, y se
  registra el cambio (`from_state` nulo).
- **Cambiar de estado** → solo a un destino con transición desde el estado actual.
  Si no la hay: `InvalidFlowTransition` (409), con la lista de destinos válidos. Se
  registra el cambio con la nota opcional.
- **Desasignar** → siempre permitido; se registra la salida (`to_state` nulo).
- Cambiar de estado una etiqueta sin flujo → `TagHasNoFlow` (422).
- Una etiqueta de proyecto solo se asigna en su proyecto (como hoy). Una global, en
  cualquier proyecto al que el usuario tenga acceso.

### 4.3. Modificar un flujo en uso (comprobación fina por estado)
- Renombrar, recolorear, reordenar y **añadir** estados: siempre.
- **Borrar un estado**: rechazado con `FlowStateInUse` (409) si algún elemento está
  ahora en él, indicando cuántos y cuáles. Si no, se borra con sus transiciones.
- **Cambiar el estado inicial**: siempre (afecta solo a asignaciones futuras).
  El inicial no se puede borrar sin elegir antes otro.
- **Añadir o quitar transiciones**: siempre. Un elemento puede quedarse sin salidas.
- **Borrar un flujo**: rechazado con `FlowInUse` (409) si alguna etiqueta lo usa.
- **Cambiar el flujo de una etiqueta** (o quitárselo): rechazado con `FlowInUse`
  (409) si la etiqueta está asignada a algún elemento.

### 4.4. Permisos

| Acción | Global | De proyecto |
|--------|--------|-------------|
| Ver flujos y etiquetas | cualquier usuario autenticado | miembros del proyecto |
| Crear, editar, borrar flujos y etiquetas | administrador | propietario o líder (como las etiquetas hoy) |
| Asignar, desasignar, cambiar de estado, ver el registro | miembros del proyecto del elemento | miembros del proyecto del elemento |



### 4.5. Lo que define la SF

Lo que define la SF no lo puede cambiar nadie más; los demás pueden usarlo y
añadir lo suyo. No hace falta un mecanismo propio: basta con los roles.

- En el JKanban de la SF, **la SF es el único administrador** (su usuario del MCP,
  creado con `create_admin`). Como lo global solo lo gestiona el administrador,
  solo la SF puede cambiar sus flujos y etiquetas globales.
- Las personas entran como **usuarios normales**, miembros de los proyectos
  (`add_member`). Pueden usar las etiquetas de la SF, cambiar estados y añadir
  etiquetas propias en los proyectos donde sean propietario o líder.
- **Límite conocido:** si se diera rol de administrador a otra persona, podría
  modificar lo de la SF. Si llega a hacer falta, la solución prevista es una marca
  «protegido» que restrinja la edición al autor (`created_by`).
## 5. API

**Flujos**
- `GET|POST /flows/` — globales. `GET|POST /projects/{pid}/flows/` — del proyecto
  (el `GET` incluye también los globales, con su ámbito).
- `GET|PATCH|DELETE /flows/{id}` — un flujo, sea del ámbito que sea.
- `POST /flows/{id}/states`, `PATCH|DELETE /flows/{id}/states/{sid}`.
- `POST /flows/{id}/transitions`, `DELETE /flows/{id}/transitions/{from_sid}/{to_sid}`.

Crear un flujo:
```json
{ "name": "Devslice",
  "states": [{"name": "Planificada"}, {"name": "En preparación"}, {"name": "Preparada"},
             {"name": "En desarrollo"}, {"name": "En verificación"}, {"name": "Terminada"}],
  "initial": "Planificada",
  "transitions": [{"from": "Planificada", "to": "En preparación"},
                  {"from": "En verificación", "to": "En desarrollo"}] }
```

**Etiquetas**
- `GET|POST /tags/` y `PATCH|DELETE /tags/{id}` — globales.
- `/projects/{pid}/tags/` — como hoy; el `GET` incluye también las globales.
- `TagResponse` añade `project_id` (nulo = global) y `flow` (`{id, name}` o nulo).
  Al crear o editar se acepta `flow_id`.

**Estado de un elemento**
- `POST|DELETE /tasks/{id}/tags/{tag_id}` y `/groups/{id}/tags/{tag_id}` — como hoy
  (con flujo: estado inicial / salida del flujo).
- `PATCH /tasks/{id}/tags/{tag_id}/state` y `/groups/{id}/tags/{tag_id}/state` —
  cuerpo `{"state_id": n, "note": "…"}`.
- `GET /tasks/{id}/tags/{tag_id}/history` y `/groups/{id}/tags/{tag_id}/history`.
- Las etiquetas que devuelven tareas y grupos incluyen `state` (`{id, name}` o nulo).

**Excepciones nuevas del dominio**

| Excepción | HTTP |
|-----------|------|
| `FlowNotFound`, `FlowStateNotFound` | 404 |
| `InvalidFlowDefinition` | 422 |
| `InvalidFlowTransition` | 409 |
| `FlowStateInUse`, `FlowInUse` | 409 |
| `FlowNameAlreadyExists` | 409 |
| `TagHasNoFlow` | 422 |

`TagNameAlreadyExists` y `TagNotInProject` se mantienen, adaptadas a los ámbitos.

## 6. MCP

- **Flujos:** `list_flows(project_id?)`, `create_flow(name, states, initial,
  transitions, project_id?)`, `ensure_flow(...)`, `update_flow`, `add_flow_state`,
  `update_flow_state`, `delete_flow_state`, `add_flow_transition`,
  `remove_flow_transition`, `delete_flow`. Sin `project_id`, globales.
- **`ensure_flow(name, states, initial, transitions, project_id?)`** — deja el
  flujo como lo necesita la SF, de forma repetible. Nombres comparados sin
  distinguir mayúsculas.

  | Situación | Acción |
  |---|---|
  | El flujo no existe | Lo crea tal cual. |
  | Existe e idéntico | Nada. |
  | Faltan estados | Los añade al final, en el orden de la definición. |
  | Faltan transiciones | Las añade. |
  | Sobran estados o transiciones | No los borra; los indica como sobrantes. |
  | Estado inicial distinto | No lo cambia; lo indica. |
  | Color distinto en un estado existente | No lo cambia (el color solo se aplica al crear). |

  Devuelve `{flow, created, added_states, added_transitions, extra_states,
  extra_transitions, initial_differs}`. Un renombre de estado no se detecta
  (aparece como un estado nuevo y uno sobrante); se hace con `update_flow_state`.
- **Etiquetas:** `create_tag` y similares aceptan `project_id` opcional (sin él,
  global) y `flow`. `tag_plan` y `tag_activity` resuelven el nombre entre las
  etiquetas del proyecto y las globales; las que no existen se crean en el
  proyecto, sin flujo.
- **Estado:** `set_flow_state(plan_id | activity_id, tag, to, note?)` por nombres;
  `get_flow_history(plan_id | activity_id, tag)`.
- **Consultas:** `get_project` muestra el estado de cada etiqueta con flujo;
  `find_activities` filtra por `tag` + `state`; `overview()` cuenta, por proyecto,
  planes y actividades por etiqueta y estado.

## 7. Web

- **Panel de administración:** gestión de flujos y etiquetas globales.
- **Vista de etiquetas del proyecto:** las del proyecto (editables) y las globales
  (solo lectura), y los flujos del proyecto.
- **Editor de flujo:** lista de estados (con el inicial marcado) y una matriz de
  transiciones desde × hacia con casillas.
- **Tarjetas y columnas:** una etiqueta con flujo se muestra como
  `Devslice: En desarrollo`, con un desplegable que solo ofrece los destinos
  permitidos. El registro, en un desplegable o modal del elemento.

## 8. Migración

Los datos actuales son de prueba, pero la migración sigue la regla del proyecto
(no destructiva, en `migrations.py`): reconstruir `tags` con `project_id` nulable
y `flow_id`; añadir `state_id` a `task_tags` y `group_tags`; crear las tablas
nuevas. `conftest.py` añade las tablas nuevas a `_TABLES`. SQL portable según
`CLAUDE.md`.

## 9. Pruebas

- Definición: cada regla de 4.1 (estados, inicial, transiciones, nombres).
- Uso: asignar (inicial), transición válida e inválida, desasignar, registro de
  cada cambio con nombres y nota.
- Modificación en uso: cada regla de 4.3.
- Ámbitos: unicidad de nombres global/proyecto, etiqueta global con flujo de
  proyecto (rechazo), global en varios proyectos.
- Permisos: tabla 4.4.
- Migración sobre una base de datos con el esquema anterior.
- MCP: servicio contra la API real y capa MCP.

## 10. Fuera de alcance

Proteger la desasignación, condiciones de transición, estados finales, prioridades
globales, dependencias, bloqueos y enlaces a evidencias.

## 11. Plan

0. Arranque en vacío: `JKANBAN_DEMO_DATA`, `create_admin`, tests y guía de instalación.
1. Backend de flujos: dominio, persistencia, casos de uso, API y tests.
2. MCP: tools, tests y `docs/mcp.md`.
3. Web: panel de administración, editor de flujos, desplegable de estado.

Unas tres sesiones; el paso 0 es pequeño.
