# Reglas de negocio y excepciones de dominio

## Índice

- [Excepciones de dominio](#excepciones-de-dominio-appdomainexceptionspy)
- [Reglas de negocio clave](#reglas-de-negocio-clave)
  - [Proyectos](#proyectos)
  - [Usuarios](#usuarios)
  - [Tags y Prioridades](#tags-y-prioridades)
  - [Grupos y Tareas](#grupos-y-tareas)
- [Eliminaciones en cascada](#eliminaciones-en-cascada-resumen)
- [Comportamiento SET NULL vs CASCADE](#comportamiento-set-null-vs-cascade)

---

## Excepciones de dominio (`backend/domain/exceptions.py`)

Cada excepción de dominio se mapea a un código HTTP en los routers de la capa de interfaces.

| Excepción | HTTP | Descripción |
|-----------|------|-------------|
| `InvalidCredentials` | 401 | Email o contraseña incorrectos |
| `UserNotFound` | 404 | Usuario no existe |
| `EmailAlreadyExists` | 409 | El email ya está registrado |
| `UserOwnsProjects` | 409 | No se puede eliminar un usuario que tiene proyectos propios |
| `AdminCannotDeleteSelf` | 403 | Un admin no puede eliminarse a sí mismo |
| `ProjectNotFound` | 404 | Proyecto no existe |
| `ProjectHasGroups` | 409 | No se puede eliminar un proyecto que tiene grupos (usar cascade) |
| `ProjectLeaderRequired` | 422 | Todo proyecto debe tener un leader asignado |
| `UserNotInProject` | 403 | El usuario no tiene acceso al proyecto |
| `MemberAlreadyInProject` | 409 | El usuario ya es miembro del proyecto |
| `MemberNotInProject` | 404 | El usuario no es miembro del proyecto |
| `GroupNotFound` | 404 | Grupo no existe |
| `GroupHasTasks` | 409 | No se puede eliminar un grupo que contiene tareas |
| `TaskNotFound` | 404 | Tarea no existe |
| `TodoNotFound` | 404 | Subtarea no existe |
| `TagNotFound` | 404 | Etiqueta no existe |
| `TagNameAlreadyExists` | 409 | Nombre de etiqueta duplicado en el mismo proyecto |
| `TagNotInProject` | 400 | La etiqueta no pertenece al proyecto de la tarea |
| `PriorityNotFound` | 404 | Prioridad no existe |
| `PriorityNameAlreadyExists` | 409 | Nombre de prioridad duplicado en el mismo proyecto |
| `PriorityNotInProject` | 400 | La prioridad no pertenece al proyecto |

---

## Reglas de negocio clave

### Proyectos

- **Leader obligatorio:** un proyecto siempre debe tener `leader_id`. Intentar setearlo a `null` devuelve 422 (`ProjectLeaderRequired`).
- **Eliminación simple vs. cascade:** `DELETE /projects/{id}` falla con 409 si el proyecto tiene grupos. Para eliminar con datos usar `DELETE /projects/{id}/cascade` — requiere contraseña del owner para confirmar.
- **Solo el owner puede eliminar** el proyecto (simple o cascade). El leader no puede.
- **El owner no puede ser removido** de los miembros del proyecto.

### Usuarios

- Un usuario con proyectos propios no puede ser eliminado directamente — hay que usar el cascade-delete de admin (`DELETE /admin/users/{id}/cascade`), que borra todos sus proyectos y su contenido en cascada.
- Un admin no puede eliminar su propia cuenta (`AdminCannotDeleteSelf`).
- Un admin no puede quitarse el flag `is_admin` a sí mismo (403 en backend; el checkbox está deshabilitado en el frontend).
- El primer usuario de la BD se promueve automáticamente a admin al arrancar si no hay ningún admin.

### Tags y Prioridades

- Los nombres son únicos **por proyecto** (no globalmente).
- Tags y prioridades están siempre scoped a un proyecto — no se comparten entre proyectos.
- Al asignar una tag a una tarea, se valida que la tag pertenezca al mismo proyecto que la tarea.

### Grupos y Tareas

- Un grupo no puede eliminarse si contiene tareas (`GroupHasTasks` → 409). Hay que vaciar el grupo primero o eliminar las tareas manualmente.
- Las tareas heredan el acceso del grupo → proyecto. Un usuario sin acceso al proyecto no puede ver ni operar sus tareas.
- El orden de grupos y tareas se gestiona con el campo `sort_order` y los endpoints de reorder (`PATCH .../reorder`), que reciben una lista ordenada de IDs.

---

## Eliminaciones en cascada (resumen)

```
Borrar Proyecto (cascade)
  → elimina: Grupos → Tareas → TodoItems, task_tags
  → elimina: Tags, Priorities (del proyecto)
  → elimina: project_members
  Requiere: owner_password

Borrar Usuario (cascade, solo admin)
  → elimina todos sus Proyectos (con su cascada completa)
  → limpia: project_members donde aparezca como miembro
  → SET NULL: tasks.user_id, projects.leader_id
  Requiere: admin_password
```

---

## Comportamiento SET NULL vs CASCADE

| FK | Al borrar referenciado |
|----|----------------------|
| `tasks.user_id` → users | SET NULL (tarea queda sin responsable) |
| `tasks.priority_id` → priorities | SET NULL (tarea queda sin prioridad) |
| `projects.leader_id` → users | SET NULL (requiere reasignación manual) |
| `projects.priority_id` → priorities | SET NULL |
| `groups.project_id` → projects | CASCADE |
| `tasks.group_id` → groups | CASCADE |
| `todo_items.task_id` → tasks | CASCADE |
| `tags.project_id` → projects | CASCADE |
| `priorities.project_id` → projects | CASCADE |
| `project_members.*` → projects/users | CASCADE (ambos lados) |
| `task_tags.*` → tasks/tags | CASCADE (ambos lados) |
