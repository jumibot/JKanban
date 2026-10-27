# JKanban

JKanban es una aplicación web de gestión de tareas estilo Kanban diseñada para equipos que trabajan con múltiples proyectos en paralelo. Permite organizar el trabajo en tableros visuales con grupos de tareas personalizables, asignar responsables, establecer fechas y duraciones estimadas, y clasificar las tareas mediante etiquetas y prioridades propias de cada proyecto.

La aplicación incluye gestión de equipos por proyecto —con roles de owner, líder y miembro—, subtareas con seguimiento de progreso, drag & drop para reordenar tareas y columnas, y un panel de administración de plataforma para gestionar usuarios y sus datos de forma centralizada.

El backend expone una API REST construida con FastAPI y persiste los datos en SQLite. El frontend es una SPA en Vanilla JS servida directamente por el propio backend, sin dependencias de frameworks ni proceso de build.

## Documentación técnica

La documentación técnica detallada del proyecto está en [`docs/`](docs/overview.md) — arquitectura, modelo de datos, API, permisos, frontend, reglas de negocio y tests.

---

## Índice

- [Funcionalidades](#funcionalidades)
  - [Proyectos](#proyectos)
  - [Tablero Kanban](#tablero-kanban)
  - [Tareas](#tareas)
  - [Etiquetas y Prioridades](#etiquetas-y-prioridades)
  - [Equipo](#equipo)
  - [Autenticación](#autenticación)
  - [Administración de plataforma](#administración-de-plataforma)
- [Tecnologías](#tecnologías)
- [Estructura del repositorio](#estructura-del-repositorio)
  - [Nivel raíz](#nivel-raíz)
  - [Backend](#backend--backend)
  - [Frontend](#frontend--frontend)
- [API — Endpoints](#api--endpoints)
- [Arranque en desarrollo](#arranque-en-desarrollo)
- [Tests](#tests)

---

## Funcionalidades

### Proyectos
- Crear y gestionar múltiples proyectos con nombre, icono, color y descripción
- Asignar un **Team Leader** y una **prioridad** a cada proyecto
- Vista de progreso por proyecto (tareas completadas / total)

### Tablero Kanban
- Grupos de tareas (columnas) con color propio y ordenación por drag & drop
- Reordenación de columnas arrastrando la cabecera
- Reordenación de tareas dentro de una columna y movimiento entre columnas

### Tareas
- Crear, editar y eliminar tareas
- Campos: título, descripción, responsable, duración estimada, fecha de inicio y fin
- **Etiquetas** multiselección con colores personalizados por proyecto
- **Prioridad** por tarea con icono y color
- **Subtareas** (checklist) con progreso visual
- Marcar tareas como completadas

### Etiquetas y Prioridades
- Gestionadas por proyecto (owner o team leader)
- Paleta de colores y selector de iconos para prioridades

### Equipo
- Asignar y eliminar miembros por proyecto
- Vista de roles: Owner, Líder, Miembros
- Panel de administración de usuarios (solo admins)

### Autenticación
- Registro e inicio de sesión con JWT
- Sesión persistida en `localStorage`
- Roles: usuario estándar y administrador

### Administración de plataforma
Funciones exclusivas para usuarios con rol **admin**:
- Crear usuarios directamente desde el panel (sin pasar por el registro público)
- Editar cualquier usuario: nombre, email, contraseña, avatar
- Promover o revocar el rol de administrador en cualquier cuenta (no en la propia)
- Eliminación en cascada de usuarios con previsualización del impacto: muestra los proyectos que serán borrados junto con el recuento de grupos, tareas, etiquetas, prioridades y miembros afectados
- La eliminación requiere confirmación con la contraseña del admin como segunda verificación
- Un admin no puede eliminarse ni revocar sus propios privilegios

---

## Tecnologías

### Backend
| Tecnología | Uso |
|---|---|
| **Python 3.13** | Lenguaje principal |
| **FastAPI** | Framework REST API |
| **SQLite** | Base de datos por defecto (fichero `tasks.db`); capa de persistencia preparada para otros motores vía `DB_ENGINE` |
| **PyJWT** | Autenticación con tokens JWT |
| **Uvicorn** | Servidor ASGI |
| **pytest + httpx** | Suite de tests (334 tests) |

### Frontend
| Tecnología | Uso |
|---|---|
| **HTML5 / Vanilla JS** | SPA sin framework ni bundler |
| **Tailwind CSS** (CDN) | Utilidades de estilo |
| **Material Symbols** | Iconografía |
| **Drag & Drop API** | Reordenación de tareas y columnas |

El frontend se sirve directamente desde el backend a través de `StaticFiles` de FastAPI.

---

## Estructura del repositorio

### Nivel raíz

| Directorio / Archivo | Contenido |
|---|---|
| `backend/` | API REST — lógica de negocio, base de datos y rutas HTTP |
| `frontend/` | SPA — HTML, estilos y módulos JavaScript |
| `tests/` | Suite de 334 tests (pytest): integración por recurso + guardas de arquitectura |
| `scripts/` | Scripts de utilidad para desarrollo |
| `docs/` | Documentación técnica (entrada: [`docs/overview.md`](docs/overview.md)) y referencias visuales de diseño |

---

### Backend — `backend/`

El backend sigue una **arquitectura por capas** (domain → application → infrastructure → interfaces).

| Capa | Directorio | Responsabilidad |
|---|---|---|
| Entrada | `main.py` | Punto de entrada: registra routers y sirve el frontend estático |
| Dominio | `domain/` | Entidades, interfaces de repositorio y excepciones de negocio |
| Aplicación | `application/` | Casos de uso: orquesta dominio e infraestructura |
| Infraestructura | `infrastructure/` | Persistencia (SQLite por defecto), JWT y repositorios concretos |
| Interfaces | `interfaces/` | Schemas Pydantic, dependencias FastAPI y routers HTTP |

**`domain/`**

| Archivo | Contenido |
|---|---|
| `entities.py` | Dataclasses: `Project`, `Group`, `Task`, `Tag`, `Priority`, `User`, `TodoItem`, `ProjectContentCounts` |
| `repositories.py` | Interfaces abstractas de repositorio |
| `exceptions.py` | Excepciones de negocio |

**`application/`** — un módulo de casos de uso por entidad

| Archivo | Entidad |
|---|---|
| `project_use_cases.py` | Proyectos |
| `group_use_cases.py` | Grupos de tareas |
| `task_use_cases.py` | Tareas |
| `tag_use_cases.py` | Etiquetas |
| `priority_use_cases.py` | Prioridades |
| `user_use_cases.py` | Usuarios |
| `todo_use_cases.py` | Subtareas |

**`infrastructure/`**

| Archivo | Contenido |
|---|---|
| `persistence/factory.py` | Elige el motor según `DB_ENGINE` y expone conexión y helpers de dialecto |
| `persistence/sqlite/` | Conexión, esquema, migraciones y datos demo de SQLite |
| `persistence/common/` | Utilidades independientes del motor (fechas, placeholders) |
| `jwt_handler.py` | Generación y validación de tokens JWT |
| `repositories/` | `Sql*Repository`: implementación SQL portable de cada repositorio del dominio |

**`interfaces/routers/`** — un router por entidad

| Archivo | Endpoints |
|---|---|
| `auth.py` | Login |
| `projects.py` | CRUD proyectos, miembros, previsualización de borrado |
| `groups.py` | CRUD grupos, reordenación |
| `tasks.py` | CRUD tareas, etiquetas de tarea, reordenación |
| `tags.py` | CRUD etiquetas por proyecto |
| `priorities.py` | CRUD prioridades por proyecto |
| `users.py` | CRUD usuarios, perfil |
| `todos.py` | CRUD subtareas |
| `admin.py` | Previsualización y borrado en cascada de usuarios |

---

### Frontend — `frontend/`

SPA de página única sin framework ni bundler. `index.html` carga los módulos JS en orden mediante `<script src>`.

**Raíz `js/`** — foundation

| Archivo | Responsabilidad |
|---|---|
| `state.js` | Objeto global `S` con el estado de la aplicación |
| `utils.js` | Helpers: `esc`, `avatar`, `toast`, `hashCol`, `emptyState` |
| `api.js` | Capa HTTP: `req`, `GET/POST/PATCH/DEL`, `loadAll`, `loadMembers` |
| `auth.js` | Login, registro, logout, auth wall |
| `router.js` | `go`, `route`, listener `hashchange` |
| `render.js` | `renderSidebar`, `renderHeader`, `renderContent` |
| `dnd.js` | Drag & drop de tareas y reordenación de columnas |
| `delete.js` | `confirmDel`, `confirmCascadeDelProject`, `execDel` |

**`js/views/`** — vistas principales

| Archivo | Vista |
|---|---|
| `dashboard.js` | Grid de proyectos con progreso |
| `board.js` | Tablero Kanban con columnas y tarjetas |
| `tags.js` | Gestión de etiquetas del proyecto |
| `priorities.js` | Gestión de prioridades del proyecto |
| `team.js` | Equipo del proyecto y panel de administración de usuarios |

**`js/modals/`** — formularios y diálogos

| Archivo | Modales |
|---|---|
| `base.js` | `showModal`, `closeM`, `mhdr`, `mfoot`, selectores de color e icono |
| `project.js` | Crear/editar proyecto, gestión de equipo, menú contextual |
| `group.js` | Crear/editar grupo de tareas, menú contextual |
| `task.js` | Crear/editar tarea con etiquetas y prioridad inline |
| `subtask.js` | Añadir, completar y eliminar subtareas |
| `tag.js` | Crear/editar etiqueta |
| `priority.js` | Crear/editar prioridad |
| `user.js` | Crear usuario, editar perfil, edición admin, borrado en cascada |

---

## API — Endpoints

La API completa está disponible en modo interactivo en `http://127.0.0.1:8000/docs` (Swagger UI) una vez arrancado el servidor.

### Autenticación

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/auth/login` | Obtener token JWT |

### Usuarios

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/users/` | Registrar nuevo usuario | No |
| `GET` | `/users/` | Listar todos los usuarios | Sí |
| `GET` | `/users/{id}` | Obtener usuario por ID | Sí |
| `PATCH` | `/users/{id}` | Actualizar usuario (self o admin) | Sí |
| `DELETE` | `/users/{id}` | Eliminar usuario (self o admin) | Sí |
| `GET` | `/users/{id}/projects` | Proyectos del usuario con su rol | Sí |

### Proyectos

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/projects/` | Crear proyecto | Sí |
| `GET` | `/projects/` | Listar proyectos | Sí |
| `GET` | `/projects/{id}` | Obtener proyecto por ID | Sí |
| `PATCH` | `/projects/{id}` | Actualizar proyecto | Sí |
| `DELETE` | `/projects/{id}` | Eliminar proyecto | Sí |
| `GET` | `/projects/{id}/groups` | Grupos del proyecto | Sí |
| `GET` | `/projects/{id}/members` | Miembros del proyecto | Sí |
| `POST` | `/projects/{id}/members/{uid}` | Añadir miembro | Sí |
| `DELETE` | `/projects/{id}/members/{uid}` | Eliminar miembro | Sí |
| `GET` | `/projects/{id}/role/{uid}` | Rol de un usuario en el proyecto | Sí |
| `GET` | `/projects/{id}/deletion-preview` | Previsualizar impacto del borrado | Sí |
| `DELETE` | `/projects/{id}/cascade` | Eliminar proyecto y todo su contenido | Sí |

### Grupos de tareas

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/groups/` | Crear grupo | Sí |
| `GET` | `/groups/` | Listar grupos | Sí |
| `GET` | `/groups/{id}` | Obtener grupo por ID | Sí |
| `PATCH` | `/groups/{id}` | Actualizar grupo | Sí |
| `DELETE` | `/groups/{id}` | Eliminar grupo | Sí |
| `GET` | `/groups/{id}/tasks` | Tareas del grupo | Sí |
| `PATCH` | `/groups/reorder` | Reordenar columnas del tablero | Sí |
| `PATCH` | `/groups/{id}/tasks/reorder` | Reordenar tareas dentro del grupo | Sí |

### Tareas

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/tasks/` | Crear tarea | Sí |
| `GET` | `/tasks/` | Listar tareas | Sí |
| `GET` | `/tasks/{id}` | Obtener tarea por ID | Sí |
| `PATCH` | `/tasks/{id}` | Actualizar tarea | Sí |
| `DELETE` | `/tasks/{id}` | Eliminar tarea | Sí |
| `GET` | `/tasks/{id}/todos` | Listar subtareas | Sí |
| `POST` | `/tasks/{id}/todos` | Crear subtarea | Sí |
| `PATCH` | `/tasks/{id}/todos/{tid}` | Actualizar subtarea | Sí |
| `DELETE` | `/tasks/{id}/todos/{tid}` | Eliminar subtarea | Sí |

### Etiquetas

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/projects/{id}/tags/` | Crear etiqueta | Sí |
| `GET` | `/projects/{id}/tags/` | Listar etiquetas del proyecto | Sí |
| `GET` | `/projects/{id}/tags/{tid}` | Obtener etiqueta | Sí |
| `PATCH` | `/projects/{id}/tags/{tid}` | Actualizar etiqueta | Sí |
| `DELETE` | `/projects/{id}/tags/{tid}` | Eliminar etiqueta | Sí |

### Prioridades

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `POST` | `/projects/{id}/priorities/` | Crear prioridad | Sí |
| `GET` | `/projects/{id}/priorities/` | Listar prioridades del proyecto | Sí |
| `GET` | `/projects/{id}/priorities/{pid}` | Obtener prioridad | Sí |
| `PATCH` | `/projects/{id}/priorities/{pid}` | Actualizar prioridad | Sí |
| `DELETE` | `/projects/{id}/priorities/{pid}` | Eliminar prioridad | Sí |

### Administración

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| `GET` | `/admin/users/{id}/deletion-preview` | Previsualizar borrado de usuario en cascada | Admin |
| `DELETE` | `/admin/users/{id}/cascade` | Eliminar usuario y todos sus proyectos | Admin |

---

## Arranque en desarrollo

> Para una instalación nueva desde cero, incluida la contraseña del administrador, sigue [`docs/guias/instalacion.md`](docs/guias/instalacion.md). Para pasar a una versión nueva, [`docs/guias/actualizacion.md`](docs/guias/actualizacion.md).

```powershell
# Instalar dependencias
pip install -r backend/requirements.txt

# Arrancar el servidor (puerto por defecto: 8000)
.\scripts\start-dev.ps1

# O directamente con uvicorn
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

La aplicación queda disponible en `http://127.0.0.1:8000`.

## Tests

```bash
pytest tests/
```
