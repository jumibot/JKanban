# Modelo de datos

## Índice

- [Entidades principales](#entidades-principales)
  - [User](#user)
  - [Project](#project)
  - [Group](#group-columna-kanban)
  - [Task](#task)
  - [Priority](#priority-scoped-a-proyecto)
  - [Tag](#tag-global-o-de-proyecto)
  - [Flow, FlowState y transiciones](#flow-flowstate-y-transiciones)
  - [FlowStateChange](#flowstatechange-registro-de-estados)
  - [TodoItem](#todoitem-subtarea)
- [Tablas de unión](#tablas-de-unión)
- [Relaciones y cascadas](#relaciones-y-cascadas)
- [Restricciones de integridad notables](#restricciones-de-integridad-notables)

---

## Entidades principales

### User
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | autoincrement |
| name | str (1-100) | |
| email | str único | lowercase, validado |
| password_hash | str | `pbkdf2$<salt_hex>$<hash_hex>` |
| avatar_url | str? | URL libre |
| is_admin | bool | false por defecto |
| created_at / modified_at | datetime? | |
| created_by / modified_by | int? | FK a users.id |

### Project
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| name | str (1-100) | |
| description | str? | |
| icon | str | nombre icono Material Symbols, default `folder` |
| color | str | hex #RRGGBB, default `#3B82F6` |
| owner_id | int FK | → users, NOT NULL |
| leader_id | int FK? | → users, ON DELETE SET NULL; default = owner al crear |
| priority_id | int FK? | → priorities, ON DELETE SET NULL |
| members | list[User] | via tabla `project_members` |

### Group (columna Kanban)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| name | str (1-100) | |
| description | str? | |
| color | str | hex #RRGGBB |
| project_id | int FK | → projects, ON DELETE CASCADE |
| sort_order | int | orden de la columna (0-indexed) |

### Task
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| group_id | int FK | → groups, ON DELETE CASCADE |
| title | str (1-200) | |
| description | str? | |
| completed | bool | false por defecto |
| user_id | int FK? | → users, ON DELETE SET NULL (responsable) |
| priority_id | int FK? | → priorities, ON DELETE SET NULL |
| estimated_duration | float? | horas |
| estimated_start / estimated_end | datetime? | |
| actual_start / actual_end | datetime? | |
| sort_order | int | orden dentro del grupo |
| tags | list[Tag] | via tabla `task_tags` |
| todos_total / todos_completed | int | computed al leer |

### Priority *(scoped a proyecto)*
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| name | str (1-50) | único por proyecto |
| icon | str | nombre icono Material Symbols, default `flag` |
| color | str | hex #RRGGBB |
| project_id | int FK | → projects, ON DELETE CASCADE |

### Tag *(global o de proyecto)*
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| name | str (1-50) | único en su ámbito, sin distinguir mayúsculas (lo comprueba `TagUseCases`) |
| color | str | hex #RRGGBB |
| project_id | int FK nulo | → projects, ON DELETE CASCADE. **Nulo = global** |
| flow_id | int FK nulo | → flows, ON DELETE SET NULL. Global: solo flujos globales |

### Flow, FlowState y transiciones
Ver [flows.md](flows.md).

| Tabla | Campos | Notas |
|-------|--------|-------|
| `flows` | id, name, project_id (FK nulo, CASCADE; **nulo = global**), auditoría | nombre único en su ámbito (caso de uso) |
| `flow_states` | id, flow_id (CASCADE), name, color, sort_order, is_initial (bool) | `UNIQUE(flow_id, name)`; exactamente un inicial (caso de uso) |
| `flow_transitions` | flow_id (CASCADE), from_state_id, to_state_id (CASCADE) | PK (from, to); `CHECK from <> to` |

### FlowStateChange *(registro de estados)*
Tabla `flow_state_changes`: id, task_id **o** group_id (CASCADE; `CHECK` exactamente
uno), tag_id (CASCADE), from_state, to_state (**nombres**, nulos al entrar/salir del
flujo), note, changed_by (SET NULL), changed_at. Se conserva al desasignar la
etiqueta; se borra con la tarea, el grupo o la etiqueta.

### TodoItem (subtarea)
| Campo | Tipo | Notas |
|-------|------|-------|
| id | int PK | |
| task_id | int FK | → tasks, ON DELETE CASCADE |
| title | str (1-200) | |
| completed | bool | |
| order | int | orden dentro de la tarea |

---

## Tablas de unión

| Tabla | Columnas | Propósito |
|-------|----------|-----------|
| `project_members` | (project_id, user_id) PK | membresía al proyecto |
| `task_tags` | (task_id, tag_id) PK, state_id | etiquetas de una tarea; `state_id` (→ flow_states, SET NULL) = estado actual si la etiqueta tiene flujo |
| `group_tags` | (group_id, tag_id) PK, state_id | ídem para grupos |

---

## Relaciones y cascadas

```
User
 └─< Project (owner_id)          → SET NULL al borrar user
 └─< Project (leader_id)         → SET NULL al borrar user
 └─< project_members             → CASCADE al borrar user/project

Project
 └─< Priority                    → CASCADE
 └─< Tag                         → CASCADE (las globales no tienen proyecto)
 └─< Flow                        → CASCADE (ídem)
      └─< FlowState, transiciones → CASCADE
 └─< Group
      └─< Task
           └─< TodoItem          → CASCADE
           └─< task_tags         → CASCADE
```

Borrar un **Proyecto** elimina en cascada: grupos, tareas, todos, tags y flujos del proyecto, prioridades, membresías.  
Borrar un **Usuario** (operación admin) requiere primero borrar o transferir sus proyectos; existe el endpoint de cascade-delete con confirmación de contraseña.

---

## Restricciones de integridad notables

- `priorities.name` + `priorities.project_id` → UNIQUE
- `tags.name` + `tags.project_id` → UNIQUE (no cubre las globales: los nulos no se comparan; la regla completa está en el caso de uso)
- `flow_states.flow_id` + `name` → UNIQUE; `flow_transitions` sin `from = to`
- `users.email` → UNIQUE
- Colores validados como hex `#RRGGBB` en Pydantic (schemas) y con CHECK en SQLite
- `is_admin` → CHECK (0 o 1)
