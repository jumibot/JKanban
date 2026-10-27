# API REST — Referencia completa

## Índice

- [Schemas compartidos](#schemas-compartidos)
- [Auth](#auth) — `POST /auth/login`
- [Users](#users) — `GET|POST|PATCH|DELETE /users/`
- [Projects](#projects) — `GET|POST|PATCH|DELETE /projects/`
  - [Miembros](#post-projectsproject_idmembersuser_id----owner-o-leader)
  - [Deletion preview & cascade](#get-projectsproject_iddeletion-preview----solo-owner)
- [Groups](#groups) — `GET|POST|PATCH|DELETE /groups/` · reorder
- [Tasks](#tasks) — `GET|POST|PATCH|DELETE /tasks/` · tag assignment
- [Todos](#todos-subtareas) — `/tasks/{id}/todos`
- [Tags](#tags) — `/tags/` (globales) · `/projects/{id}/tags/` · asignación, estado e historial
- [Flows](#flows) — `/flows/` (globales) · `/projects/{id}/flows/` · estados y transiciones
- [Priorities](#priorities-project-scoped) — `/projects/{id}/priorities/`
- [Admin](#admin) — deletion preview · cascade delete usuario

---

**Base URL:** `http://host:8000`  
**Auth:** `Authorization: Bearer <jwt_token>` en todas las rutas salvo las marcadas como públicas.  
**Content-Type:** `application/json`  
**Errores:** body `{"detail": "<mensaje>"}` en todos los 4xx.

---

## Schemas compartidos

### UserResponse
```json
{
  "id": 1,
  "name": "Alice",
  "email": "alice@empresa.com",
  "avatar_url": "https://..." | null,
  "is_admin": false,
  "created_at": "2024-01-15T10:30:00",
  "modified_at": "2024-01-16T08:00:00" | null
}
```

### TagResponse
```json
{ "id": 3, "name": "Devslice", "color": "#3B82F6", "project_id": null,
  "flow": { "id": 1, "name": "Devslice" },
  "state": { "id": 4, "name": "En desarrollo" } }
```
`project_id` nulo = etiqueta global. `flow` es nulo si la etiqueta no tiene flujo.
`state` solo viene relleno en las etiquetas de una tarea o grupo (`TaskResponse.tags`,
`GroupResponse.tags`) cuya etiqueta tiene flujo; en el resto es nulo.

### FlowResponse
```json
{ "id": 1, "name": "Devslice", "project_id": null, "initial_state_id": 1,
  "states": [ { "id": 1, "name": "Planificada", "color": "#6B7280", "sort_order": 0, "is_initial": true } ],
  "transitions": [ { "from_state_id": 1, "to_state_id": 2 } ],
  "created_at": "…", "modified_at": null }
```
`project_id` nulo = flujo global. Estados en `sort_order`.

### PriorityResponse
```json
{ "id": 2, "name": "Crítico", "icon": "flag", "color": "#EF4444", "project_id": 7 }
```

### ProjectResponse
```json
{
  "id": 7, "name": "Mi Proyecto", "description": "...",
  "icon": "folder", "color": "#3B82F6",
  "created_at": "...", "modified_at": "...",
  "owner":    { ...UserResponse },
  "leader":   { ...UserResponse } | null,
  "priority": { ...PriorityResponse } | null,
  "members":  [ ...UserResponse ]
}
```

### GroupResponse
```json
{
  "id": 5, "name": "En Progreso", "description": null,
  "color": "#3B82F6", "project_id": 7, "sort_order": 1,
  "created_at": "...", "modified_at": null,
  "tags": [ ...TagResponse ]
}
```

### TaskResponse
```json
{
  "id": 12, "group_id": 5, "title": "Diseñar login",
  "description": "...", "completed": false, "sort_order": 0,
  "user":     { ...UserResponse } | null,
  "priority": { ...PriorityResponse } | null,
  "estimated_duration": 3.5 | null,
  "estimated_start": "2024-02-01T09:00:00" | null,
  "estimated_end":   "2024-02-01T12:30:00" | null,
  "actual_start": null, "actual_end": null,
  "created_at": "...", "modified_at": null,
  "tags": [ ...TagResponse ],
  "todos_total": 4, "todos_completed": 1
}
```

### TodoResponse
```json
{
  "id": 8, "task_id": 12, "title": "Revisar diseño",
  "completed": false, "order": 0,
  "created_at": "...", "modified_at": null
}
```

---

## Auth

### `POST /auth/login` — público
Devuelve un JWT + datos del usuario autenticado.

**Request body:**
| Campo | Tipo | Req | Notas |
|-------|------|-----|-------|
| `email` | string | ✓ | normalizado a minúsculas |
| `password` | string | ✓ | |

**Response 200:**
```json
{ "access_token": "<jwt>", "token_type": "bearer", "user": { ...UserResponse } }
```

**Errores:**
| Código | Condición |
|--------|-----------|
| 401 | Credenciales incorrectas |

---

## Users

### `POST /users/` — público (registro)

**Request body:**
| Campo | Tipo | Req | Notas |
|-------|------|-----|-------|
| `name` | string | ✓ | 1–100 chars |
| `email` | string | ✓ | max 200, debe contener `@`, normalizado a minúsculas |
| `password` | string | ✓ | 6–128 chars |
| `avatar_url` | string\|null | — | URL libre |

**Response 201:** `UserResponse`

**Errores:**
| Código | Condición |
|--------|-----------|
| 409 | Email ya registrado |
| 422 | Validación Pydantic |

---

### `GET /users/` — autenticado
Devuelve todos los usuarios de la plataforma.

**Response 200:** `list[UserResponse]`

---

### `GET /users/{user_id}` — autenticado

**Response 200:** `UserResponse`

**Errores:** 404 si no existe.

---

### `PATCH /users/{user_id}` — propio usuario o admin

**Request body** (todos opcionales):
| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | string\|null | 1–100 chars |
| `email` | string\|null | max 200 |
| `password` | string\|null | 6–128 chars; hash se regenera |
| `avatar_url` | string\|null | null borra el avatar |
| `is_admin` | bool\|null | solo admin puede modificarlo |

**Response 200:** `UserResponse`

**Errores:**
| Código | Condición |
|--------|-----------|
| 403 | Intentar editar otro usuario sin ser admin |
| 403 | Admin intentando quitarse su propio `is_admin` |
| 404 | Usuario no encontrado |
| 409 | El nuevo email ya está en uso |
| 422 | Sin campos para actualizar |

---

### `DELETE /users/{user_id}` — propio usuario o admin
Elimina un usuario sin proyectos propios. Si tiene proyectos, usar el cascade-delete de admin.

**Response 204**

**Errores:**
| Código | Condición |
|--------|-----------|
| 403 | Intentar borrar otro usuario sin ser admin |
| 403 | Admin intentando borrarse a sí mismo |
| 404 | Usuario no encontrado |
| 409 | El usuario tiene proyectos propios (usar cascade) |

---

### `GET /users/{user_id}/projects` — autenticado

**Response 200:** `list[ProjectWithRoleResponse]`
> Igual que `ProjectResponse` con campo adicional `"role": "owner" | "leader" | "member"`.

---

## Projects

### `GET /projects/` — autenticado
Solo devuelve proyectos a los que el usuario tiene acceso (owner/leader/member).

**Response 200:** `list[ProjectResponse]`

---

### `GET /projects/{project_id}` — member+

**Response 200:** `ProjectResponse`

**Errores:** 404 si no existe.

---

### `POST /projects/` — autenticado
El usuario autenticado se convierte en owner. Si no se especifica `leader_id`, el owner también es leader.

**Request body:**
| Campo | Tipo | Req | Notas |
|-------|------|-----|-------|
| `name` | string | ✓ | 1–100 chars |
| `description` | string\|null | — | |
| `icon` | string | — | nombre icono Material Symbols; default `"folder"` |
| `color` | string | — | hex `#RRGGBB`; default `"#3B82F6"` |
| `leader_id` | int\|null | — | ID de usuario; default = owner |
| `priority_id` | int\|null | — | debe pertenecer al proyecto |

**Response 201:** `ProjectResponse`

**Errores:**
| Código | Condición |
|--------|-----------|
| 404 | `leader_id` o `priority_id` no encontrados |
| 422 | Color inválido (`#RRGGBB` requerido) |

---

### `PATCH /projects/{project_id}` — owner o leader

**Request body** (todos opcionales):
| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | string\|null | 1–100 |
| `description` | string\|null | |
| `icon` | string\|null | |
| `color` | string\|null | hex `#RRGGBB` |
| `owner_id` | int\|null | transferir propiedad |
| `leader_id` | int\|null | no puede ser null (regla de negocio) |
| `priority_id` | int\|null | null desvincula la prioridad |

**Response 200:** `ProjectResponse`

**Errores:**
| Código | Condición |
|--------|-----------|
| 403 | No es owner ni leader |
| 404 | Proyecto / usuario / prioridad no encontrados |
| 422 | Intentar dejar `leader_id` en null |

---

### `DELETE /projects/{project_id}` — solo owner
Falla si el proyecto tiene grupos. Para eliminar con datos, usar cascade.

**Response 204**

**Errores:**
| Código | Condición |
|--------|-----------|
| 403 | No es owner |
| 404 | Proyecto no encontrado |
| 409 | El proyecto tiene grupos |

---

### `GET /projects/{project_id}/deletion-preview` — solo owner
Vista previa de lo que eliminará un cascade-delete.

**Response 200:**
```json
{
  "project": { ...ProjectResponse },
  "groups_count": 3,
  "tasks_count": 17,
  "tags_count": 5,
  "priorities_count": 2,
  "members_count": 4
}
```

---

### `DELETE /projects/{project_id}/cascade` — solo owner
Elimina el proyecto y todo su contenido. Requiere contraseña del owner como confirmación.

**Request body:**
| Campo | Tipo | Req |
|-------|------|-----|
| `owner_password` | string | ✓ |

**Response 204**

**Errores:**
| Código | Condición |
|--------|-----------|
| 403 | No es owner |
| 403 | Contraseña incorrecta |
| 404 | Proyecto no encontrado |

---

### `GET /projects/{project_id}/members` — member+

**Response 200:** `list[UserResponse]`

---

### `GET /projects/{project_id}/role/{user_id}` — member+

**Response 200:** `{ "role": "owner" | "leader" | "member" }`

**Errores:** 404 si proyecto o usuario sin rol no encontrados.

---

### `POST /projects/{project_id}/members/{user_id}` — owner o leader

**Response 204**

**Errores:**
| Código | Condición |
|--------|-----------|
| 403 | No es owner ni leader |
| 404 | Usuario no encontrado |
| 409 | El usuario ya es miembro |

---

### `DELETE /projects/{project_id}/members/{user_id}` — owner o leader

**Response 204**

**Errores:**
| Código | Condición |
|--------|-----------|
| 403 | No es owner ni leader |
| 404 | El usuario no es miembro |

---

## Groups

### `GET /groups/` — autenticado
Solo grupos de proyectos accesibles al usuario.

**Response 200:** `list[GroupResponse]`

---

### `GET /groups/{group_id}` — member+

**Response 200:** `GroupResponse`

**Errores:** 404 si no existe.

---

### `POST /groups/` — member+

**Request body:**
| Campo | Tipo | Req | Notas |
|-------|------|-----|-------|
| `name` | string | ✓ | 1–100 |
| `project_id` | int | ✓ | |
| `description` | string\|null | — | |
| `color` | string | — | hex `#RRGGBB`; default `"#3B82F6"` |
| `sort_order` | int\|null | — | se asigna al final si omitido |

**Response 201:** `GroupResponse`

**Errores:** 404 si proyecto no encontrado.

---

### `PATCH /groups/{group_id}` — member+

**Request body** (todos opcionales):
| Campo | Tipo | Notas |
|-------|------|-------|
| `name` | string\|null | 1–100 |
| `description` | string\|null | |
| `color` | string\|null | hex |
| `project_id` | int\|null | mover a otro proyecto |
| `sort_order` | int\|null | |

**Response 200:** `GroupResponse`

**Errores:** 404 si no existe, 422 si sin campos.

---

### `DELETE /groups/{group_id}` — member+
Falla si el grupo tiene tareas.

**Response 204**

**Errores:** 404 si no existe.
> Nota: `GroupHasTasks` (grupo con tareas) no está mapeado explícitamente en el router actual — la FK de SQLite puede generar un error 500. Vaciar el grupo antes de eliminarlo.

---

### `PATCH /groups/reorder` — member+
Reordena todas las columnas de un proyecto.

**Request body:**
| Campo | Tipo | Req |
|-------|------|-----|
| `project_id` | int | ✓ |
| `group_ids` | list[int] | ✓ — lista completa en el nuevo orden |

**Response 204**

**Errores:**
| Código | Condición |
|--------|-----------|
| 404 | Algún id no existe o no es un grupo de `project_id` (no se cambia nada) |
| 422 | Ids repetidos |

---

### `GET /groups/{group_id}/tasks` — member+

**Response 200:** `list[TaskResponse]`

---

### `PATCH /groups/{group_id}/tasks/reorder` — member+
Reordena las tareas dentro de un grupo.

**Request body:**
| Campo | Tipo | Req |
|-------|------|-----|
| `task_ids` | list[int] | ✓ — lista completa en el nuevo orden |

**Response 204**

**Errores:**
| Código | Condición |
|--------|-----------|
| 404 | El grupo no existe, o algún id no es una tarea de ese grupo (no se cambia nada) |
| 422 | Ids repetidos |

---

## Tasks

### `GET /tasks/` — autenticado
Solo tareas de proyectos accesibles.

**Response 200:** `list[TaskResponse]`

---

### `GET /tasks/{task_id}` — member+

**Response 200:** `TaskResponse`

**Errores:** 404 si no existe.

---

### `POST /tasks/` — member+

**Request body:**
| Campo | Tipo | Req | Notas |
|-------|------|-----|-------|
| `group_id` | int | ✓ | |
| `title` | string | ✓ | 1–200 |
| `description` | string\|null | — | |
| `completed` | bool | — | default `false` |
| `user_id` | int\|null | — | responsable |
| `priority_id` | int\|null | — | debe pertenecer al mismo proyecto |
| `estimated_duration` | float\|null | — | horas, ≥ 0 |
| `estimated_start` | datetime\|null | — | ISO 8601 |
| `estimated_end` | datetime\|null | — | ISO 8601 |
| `actual_start` | datetime\|null | — | |
| `actual_end` | datetime\|null | — | |
| `sort_order` | int\|null | — | se añade al final si omitido |

**Response 201:** `TaskResponse`

**Errores:**
| Código | Condición |
|--------|-----------|
| 404 | `group_id`, `user_id` o `priority_id` no encontrados |
| 422 | `priority_id` de otro proyecto (`PriorityNotInProject`) |

---

### `PATCH /tasks/{task_id}` — member+
Todos los campos del cuerpo son opcionales. Para mover una tarea entre columnas incluir `group_id`.

**Request body:** mismos campos que `POST /tasks/` pero todos opcionales. Adicionalmente:
- `group_id` — mover a otra columna (debe ser del mismo proyecto)

**Response 200:** `TaskResponse`

**Errores:**
| Código | Condición |
|--------|-----------|
| 400 | Intentar mover la tarea a un grupo de otro proyecto |
| 404 | Tarea / grupo / usuario / prioridad no encontrados |
| 422 | Sin campos para actualizar, o `priority_id` de otro proyecto (`PriorityNotInProject`) |

---

### `DELETE /tasks/{task_id}` — member+

**Response 204**

**Errores:** 404 si no existe.

---

### `POST|DELETE /tasks/{task_id}/tags/{tag_id}` · `PATCH .../state` · `GET .../history`
Asignar y desasignar etiquetas, cambiar su estado y ver el registro: ver
[Asignación, estado e historial](#asignación-estado-e-historial).

---

## Todos (subtareas)

### `GET /tasks/{task_id}/todos` — member+

**Response 200:** `list[TodoResponse]`

**Errores:** 404 si tarea no existe.

---

### `POST /tasks/{task_id}/todos` — member+

**Request body:**
| Campo | Tipo | Req | Notas |
|-------|------|-----|-------|
| `title` | string | ✓ | 1–200 |
| `completed` | bool | — | default `false` |
| `order` | int\|null | — | posición en la lista |

**Response 201:** `TodoResponse`

**Errores:** 404 si tarea no existe.

---

### `PATCH /tasks/{task_id}/todos/{todo_id}` — member+

**Request body** (todos opcionales):
| Campo | Tipo |
|-------|------|
| `title` | string\|null (1–200) |
| `completed` | bool\|null |
| `order` | int\|null |

**Response 200:** `TodoResponse`

**Errores:** 404 si tarea o subtarea no existen; 422 si sin campos.

---

### `DELETE /tasks/{task_id}/todos/{todo_id}` — member+

**Response 204**

**Errores:** 404 si tarea o subtarea no existen.

---

## Tags

Una etiqueta es **global** (`project_id` nulo; la gestiona solo el administrador)
o **de un proyecto** (la gestionan su propietario o líder). Puede usar un
[flujo](#flows): una global, solo flujos globales; una de proyecto, globales o de
su proyecto.

**Nombres** (sin distinguir mayúsculas): una global no puede repetir el nombre de
ninguna otra etiqueta; una de proyecto, ni el de una global ni el de otra de su
proyecto (409).

### `GET /projects/{project_id}/tags/` — member+

**Response 200:** `list[TagResponse]` — primero las globales y después las del proyecto.

---

### `GET /projects/{project_id}/tags/{tag_id}` — member+

**Response 200:** `TagResponse` (del proyecto o global).

**Errores:** 404 si no existe o es de otro proyecto.

---

### `POST /projects/{project_id}/tags/` — owner o leader

**Request body:**
| Campo | Tipo | Req | Notas |
|-------|------|-----|-------|
| `name` | string | ✓ | 1–50; ver reglas de nombres |
| `color` | string | — | hex `#RRGGBB`; default `"#6B7280"` |
| `flow_id` | int | — | flujo global o del proyecto |

**Response 201:** `TagResponse`

**Errores:**
| Código | Condición |
|--------|-----------|
| 403 | No es owner ni leader |
| 404 | `flow_id` no existe |
| 409 | Nombre ya en uso |
| 422 | Flujo de otro proyecto (`FlowNotInScope`) |

---

### `PATCH /projects/{project_id}/tags/{tag_id}` — owner o leader

**Request body** (todos opcionales): `name`, `color`, `flow_id` (`null` quita el flujo).

**Response 200:** `TagResponse`

**Errores:** 403; 404 (no existe, es de otro proyecto o es global); 409 (nombre
duplicado, o cambiar/quitar el flujo de una etiqueta asignada: `FlowInUse`); 422
(sin campos, o flujo fuera de ámbito).

---

### `DELETE /projects/{project_id}/tags/{tag_id}` — owner o leader

**Response 204.** Se quita de tareas y grupos y se borra su registro de estados.

**Errores:** 403; 404 (no existe, es de otro proyecto o es global).

---

### `GET /tags/` · `GET /tags/{tag_id}` — autenticado

Etiquetas globales. **Errores:** 404 si no existe o es de un proyecto.

### `POST /tags/` · `PATCH /tags/{tag_id}` · `DELETE /tags/{tag_id}` — admin

Mismo cuerpo, respuestas y errores que las rutas de proyecto, para etiquetas
globales (solo flujos globales). 403 si no es administrador.

---

### Asignación, estado e historial

Las mismas rutas para tareas (`/tasks/{task_id}/…`) y grupos (`/groups/{group_id}/…`).
Permiso: acceso al proyecto del elemento (member+). Una etiqueta de proyecto solo
se asigna en su proyecto; una global, en cualquiera.

| Ruta | Qué hace |
|------|----------|
| `POST /tasks/{id}/tags/{tag_id}` | Asigna (idempotente). Con flujo: el elemento entra en el **estado inicial** y se registra. **204** |
| `DELETE /tasks/{id}/tags/{tag_id}` | Desasigna (siempre permitido, idempotente). Con flujo: se registra la salida (`to_state` nulo). **204** |
| `PATCH /tasks/{id}/tags/{tag_id}/state` | Body `{"state_id": n, "note": "…"}` (nota opcional, ≤1000). Solo a un destino con transición desde el estado actual. **200** `TagResponse` con el nuevo `state` |
| `GET /tasks/{id}/tags/{tag_id}/history` | **200** `list[FlowStateChangeResponse]` en orden; se conserva tras desasignar |

```json
{ "id": 2, "tag_id": 3, "task_id": 10, "group_id": null,
  "from_state": "Planificada", "to_state": "En desarrollo", "note": "arranco",
  "changed_by": 5, "changed_at": "2026-10-27T10:00:00" }
```
Los estados se guardan **por nombre**: el registro sigue siendo legible aunque luego
se renombren o borren.

**Errores:**
| Código | Condición |
|--------|-----------|
| 403 | Sin acceso al proyecto del elemento |
| 404 | Tarea, grupo o etiqueta no existen; etiqueta no asignada (en `state`); estado de otro flujo |
| 409 | `InvalidFlowTransition`: no hay transición (el mensaje lista los destinos válidos); también al pedir el estado actual |
| 422 | Etiqueta de otro proyecto (al asignar); etiqueta sin flujo (`TagHasNoFlow`, en `state`) |

---

## Flows

Un flujo tiene estados (exactamente uno **inicial**) y transiciones permitidas.
Es **global** (`/flows/`: lo gestiona el administrador y lo ve cualquier usuario
autenticado) o **de un proyecto** (`/projects/{id}/flows/`: lo gestionan su
propietario o líder y lo ven sus miembros). Las rutas `/flows/{id}/…` valen para
los dos ámbitos, con esos mismos permisos. Nombres de flujo: misma regla que las
etiquetas. Nombres de estado: únicos en el flujo, sin distinguir mayúsculas.

### `GET /flows/` · `GET /projects/{project_id}/flows/`

**Response 200:** `list[FlowResponse]`. La de proyecto incluye primero los globales.

### `POST /flows/` (admin) · `POST /projects/{project_id}/flows/` (owner o leader)

```json
{ "name": "Devslice",
  "states": [{"name": "Planificada", "color": "#94A3B8"}, {"name": "En desarrollo"}, {"name": "Terminada"}],
  "initial": "Planificada",
  "transitions": [{"from": "Planificada", "to": "En desarrollo"},
                  {"from": "En desarrollo", "to": "Terminada"}] }
```
Estados en el orden dado; `initial` y transiciones por nombre (sin distinguir
mayúsculas); `transitions` es opcional.

**Response 201:** `FlowResponse`

**Errores:** 403; 409 (nombre en uso); 422 (`InvalidFlowDefinition`: sin estados,
inicial que no es un estado, estado repetido, transición con un estado desconocido,
a sí mismo o repetida).

### `GET /flows/{flow_id}` · `PATCH /flows/{flow_id}` · `DELETE /flows/{flow_id}`

- `PATCH` con body `{"name": "…"}` → `FlowResponse`. 409 si el nombre está en uso.
- `DELETE` → 204. **409** (`FlowInUse`) si alguna etiqueta lo usa.

### Estados

| Ruta | Body | Notas |
|------|------|-------|
| `POST /flows/{id}/states` | `name`, `color?`, `is_initial?` | Al final. **201** `FlowResponse` |
| `PATCH /flows/{id}/states/{sid}` | `name?`, `color?`, `sort_order?`, `is_initial?` | **200** `FlowResponse`. `is_initial: true` lo hace el único inicial (solo afecta a asignaciones futuras); `false` sobre el inicial → 422 |
| `DELETE /flows/{id}/states/{sid}` | — | **204**; borra también sus transiciones. **409** (`FlowStateInUse`) si algún elemento está en él (indica cuáles); **422** si es el inicial |

### Transiciones

| Ruta | Notas |
|------|-------|
| `POST /flows/{id}/transitions` | Body `{"from_state_id", "to_state_id"}`. **201** `FlowResponse`. 404 si un estado no es del flujo; 422 si es a sí mismo o ya existe |
| `DELETE /flows/{id}/transitions/{from_sid}/{to_sid}` | **204**; 404 si no existe |

Añadir o quitar estados y transiciones está permitido aunque el flujo esté en uso;
un elemento puede quedarse sin salidas.

---

## Priorities *(project-scoped)*

### `GET /projects/{project_id}/priorities/` — member+

**Response 200:** `list[PriorityResponse]`

---

### `GET /projects/{project_id}/priorities/{priority_id}` — member+

**Response 200:** `PriorityResponse`

**Errores:** 404 si no existe o no pertenece al proyecto.

---

### `POST /projects/{project_id}/priorities/` — owner o leader

**Request body:**
| Campo | Tipo | Req | Notas |
|-------|------|-----|-------|
| `name` | string | ✓ | 1–50, único en el proyecto |
| `icon` | string | — | nombre icono Material Symbols; default `"flag"` |
| `color` | string | — | hex `#RRGGBB`; default `"#6B7280"` |

**Response 201:** `PriorityResponse`

**Errores:** 403, 409 (nombre duplicado).

---

### `PATCH /projects/{project_id}/priorities/{priority_id}` — owner o leader

**Request body** (todos opcionales): `name`, `icon`, `color`

**Response 200:** `PriorityResponse`

**Errores:** 403, 404, 409, 422 (sin campos).

---

### `DELETE /projects/{project_id}/priorities/{priority_id}` — owner o leader

**Response 204**

**Errores:** 403, 404.

---

## Admin

### `GET /admin/users/{user_id}/deletion-preview` — admin
Vista previa de todo lo que se eliminará al hacer cascade-delete de un usuario.

**Response 200:**
```json
{
  "user": { ...UserResponse },
  "projects": [
    {
      "id": 7, "name": "Mi Proyecto",
      "groups_count": 3, "tasks_count": 17,
      "tags_count": 5, "priorities_count": 2, "members_count": 4
    }
  ],
  "totals": {
    "projects": 1, "groups": 3, "tasks": 17, "tags": 5, "priorities": 2
  }
}
```

**Errores:**
| Código | Condición |
|--------|-----------|
| 403 | No es admin de plataforma |
| 404 | Usuario no encontrado |

---

### `DELETE /admin/users/{user_id}/cascade` — admin
Elimina el usuario y todos sus proyectos propios en cascada. Requiere contraseña del admin como confirmación.

**Request body:**
| Campo | Tipo | Req |
|-------|------|-----|
| `admin_password` | string | ✓ |

**Response 204**

**Errores:**
| Código | Condición |
|--------|-----------|
| 400 | Intentar eliminarse a sí mismo |
| 403 | No es admin |
| 403 | Contraseña incorrecta |
| 404 | Usuario no encontrado |
