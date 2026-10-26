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
- [Tags](#tags-project-scoped) — `/projects/{id}/tags/` · group/task assignment
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
{ "id": 3, "name": "Backend", "color": "#3B82F6", "project_id": 7 }
```

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

### `POST /tasks/{task_id}/tags/{tag_id}` — member+
Asigna una etiqueta a una tarea. La etiqueta debe pertenecer al mismo proyecto que la tarea.

**Response 204**

**Errores:**
| Código | Condición |
|--------|-----------|
| 404 | Tarea o etiqueta no encontradas |
| 422 | La etiqueta no pertenece al proyecto de la tarea |

---

### `DELETE /tasks/{task_id}/tags/{tag_id}` — member+

**Response 204**

**Errores:** 404 si tarea no encontrada.

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

## Tags *(project-scoped)*

### `GET /projects/{project_id}/tags/` — member+

**Response 200:** `list[TagResponse]`

---

### `GET /projects/{project_id}/tags/{tag_id}` — member+

**Response 200:** `TagResponse`

**Errores:** 404 si no existe o no pertenece al proyecto.

---

### `POST /projects/{project_id}/tags/` — owner o leader

**Request body:**
| Campo | Tipo | Req | Notas |
|-------|------|-----|-------|
| `name` | string | ✓ | 1–50, único en el proyecto |
| `color` | string | — | hex `#RRGGBB`; default `"#6B7280"` |

**Response 201:** `TagResponse`

**Errores:**
| Código | Condición |
|--------|-----------|
| 403 | No es owner ni leader |
| 409 | Nombre ya en uso en el proyecto |

---

### `PATCH /projects/{project_id}/tags/{tag_id}` — owner o leader

**Request body** (todos opcionales): `name`, `color`

**Response 200:** `TagResponse`

**Errores:** 403, 404, 409 (nombre duplicado), 422 (sin campos).

---

### `DELETE /projects/{project_id}/tags/{tag_id}` — owner o leader

**Response 204**

**Errores:** 403, 404.

---

### `POST /groups/{group_id}/tags/{tag_id}` — member+
Asigna etiqueta a un grupo.

**Response 204**

**Errores:**
| Código | Condición |
|--------|-----------|
| 404 | Grupo o etiqueta no encontrados |
| 422 | La etiqueta no pertenece al mismo proyecto |

---

### `DELETE /groups/{group_id}/tags/{tag_id}` — member+

**Response 204**

**Errores:** 404 si grupo no encontrado.

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
