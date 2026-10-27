# Reglas de negocio y excepciones de dominio

## Índice

- [Excepciones de dominio](#excepciones-de-dominio-appdomainexceptionspy)
- [Reglas de negocio clave](#reglas-de-negocio-clave)
  - [Proyectos](#proyectos)
  - [Usuarios](#usuarios)
  - [Tags y Prioridades](#tags-y-prioridades)
  - [Flujos](#flujos)
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
| `TagNameAlreadyExists` | 409 | Nombre de etiqueta en uso en su ámbito (global o proyecto) |
| `TagNotInProject` | 422 | Etiqueta de otro proyecto asignada a una tarea o grupo (las globales valen en todos) |
| `TagNotAssigned` | 404 | Cambiar el estado de una etiqueta que el elemento no tiene |
| `TagHasNoFlow` | 422 | Cambiar el estado de una etiqueta sin flujo |
| `FlowNotFound` | 404 | Flujo no existe |
| `FlowStateNotFound` | 404 | Estado no existe o es de otro flujo |
| `FlowTransitionNotFound` | 404 | Borrar una transición que no existe |
| `InvalidFlowDefinition` | 422 | Flujo mal definido: sin estados, sin inicial válido, estado o transición repetidos, transición a sí mismo; quitar o borrar el estado inicial |
| `FlowNameAlreadyExists` | 409 | Nombre de flujo en uso en su ámbito |
| `FlowNotInScope` | 422 | Etiqueta global con flujo de proyecto, o de proyecto con flujo de otro proyecto |
| `FlowInUse` | 409 | Borrar un flujo que usa alguna etiqueta, o cambiar el flujo de una etiqueta asignada |
| `FlowStateInUse` | 409 | Borrar un estado en el que hay elementos (dice cuáles) |
| `InvalidFlowTransition` | 409 | No hay transición desde el estado actual (dice los destinos válidos) |
| `PriorityNotFound` | 404 | Prioridad no existe |
| `PriorityNameAlreadyExists` | 409 | Nombre de prioridad duplicado en el mismo proyecto |
| `PriorityNotInProject` | 422 | La prioridad asignada a una tarea es de otro proyecto (las prioridades globales, sin proyecto, se aceptan) |

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

- **Prioridades:** siempre de un proyecto; nombre único en el proyecto.
- **Etiquetas:** globales (`project_id` nulo, las gestiona solo el administrador) o de
  un proyecto (propietario o líder). Nombres sin distinguir mayúsculas: una global no
  repite ningún otro nombre; una de proyecto no repite una global ni otra de su proyecto.
- Al asignar una etiqueta de proyecto a una tarea o grupo, debe ser de su proyecto; una
  global vale en cualquier proyecto al que el usuario tenga acceso.

### Flujos

Especificación completa en [flows.md](flows.md).

- Un flujo tiene al menos un estado, **exactamente uno inicial** y transiciones entre
  estados distintos del mismo flujo. Global (admin) o de proyecto (propietario o líder).
- Una etiqueta puede usar un flujo (global: solo globales). Al asignarla, el elemento
  entra en el estado inicial; después solo cambia por una transición existente.
  Desasignar siempre está permitido. Cada entrada, cambio y salida se registra.
- En uso se puede renombrar, recolorear, reordenar y añadir estados, cambiar el
  inicial (solo afecta a asignaciones futuras) y añadir o quitar transiciones. No se
  puede borrar un estado ocupado, el estado inicial, un flujo que usa una etiqueta, ni
  cambiar el flujo de una etiqueta asignada.
- JKanban no marca estados finales ni pone condiciones a las transiciones.

### Grupos y Tareas

- Un grupo no puede eliminarse si contiene tareas (`GroupHasTasks` → 409). Hay que vaciar el grupo primero o eliminar las tareas manualmente.
- Las tareas heredan el acceso del grupo → proyecto. Un usuario sin acceso al proyecto no puede ver ni operar sus tareas.
- El orden de grupos y tareas se gestiona con el campo `sort_order` y los endpoints de reorder (`PATCH .../reorder`), que reciben una lista ordenada de IDs. Todos deben ser grupos del proyecto (o tareas del grupo) y no repetirse; si no, no se cambia nada (404 / 422).

---

## Eliminaciones en cascada (resumen)

```
Borrar Proyecto (cascade)
  → elimina: Grupos → Tareas → TodoItems, task_tags
  → elimina: Tags, Flows, Priorities (del proyecto)
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
