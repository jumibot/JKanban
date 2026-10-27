# Frontend — Arquitectura SPA

## Índice

- [Estructura general](#estructura-general)
- [Estado global](#estado-global-jsstatejs)
- [Capa API](#capa-api-jsapijs)
- [Router](#router-jsrouterjs)
- [Pipeline de render](#pipeline-de-render-jsrenderjs)
- [Sistema de modales](#sistema-de-modales-jsmodalsbasejs)
- [Módulos de vistas y modales](#módulos-de-vistas-y-modales)
- [Flujos y estados](#flujos-y-estados-jsflowsjs)
- [Seguridad frontend](#seguridad-frontend)
- [Drag & Drop](#drag--drop-jsdndjs)

---

## Estructura general

SPA (Single-Page Application) en Vanilla JS con routing por hash. Sin bundler ni framework. Los módulos JS se cargan como `<script src>` en orden de dependencias dentro de `index.html`.

**Orden de carga de scripts:**
```
state.js → utils.js → api.js → auth.js → router.js → render.js
→ views/* → modals/* → dnd.js → delete.js → flows.js → [init IIFE]
```

---

## Estado global (`js/state.js`)

Un único objeto `S` mutado directamente. Cada operación que cambia datos llama a `render()` al final.

```javascript
S = {
  projects:    [],        // ProjectResponse[] — todos los proyectos accesibles
  groups:      [],        // GroupResponse[]   — todos los grupos
  tasks:       [],        // TaskResponse[]    — todas las tareas
  users:       [],        // UserResponse[]    — todos los usuarios
  tags:        [],        // TagResponse[]     — etiquetas usables en el proyecto actual (globales + propias)
  priorities:  [],        // PriorityResponse[]— prioridades del proyecto actual
  flows:       [],        // FlowResponse[]    — flujos usables en el proyecto actual (globales + propios)
  gtags:       [],        // TagResponse[]     — etiquetas globales (solo en la vista globals)
  gflows:      [],        // FlowResponse[]    — flujos globales (solo en la vista globals)
  members:     [],        // UserResponse[]    — miembros del proyecto actual
  view:        'dashboard', // 'dashboard' | 'board' | 'team' | 'globals'
  pid:         null,      // int | null — project_id activo
  subview:     'kanban',  // 'kanban' | 'tags' | 'priorities' | 'team'
  currentUser: null,      // UserResponse | null
}
```

`tags`, `priorities`, `flows` y `members` son project-scoped: se recargan cuando cambia `S.pid`.

---

## Capa API (`js/api.js`)

```javascript
req(method, path, body)   // fetch con token JWT; 401 → clearAuth+showAuthWall
GET(path)                 // shorthand
POST(path, body)
PATCH(path, body)
DEL(path)

loadAll()         // carga projects+groups+tasks+users en paralelo
                  // si S.pid: también loadProjectMeta(); si S.view==='globals': loadGlobals()
loadProjectMeta() // tags, priorities y flows del proyecto actual
loadGlobals()     // gtags y gflows (panel de administración)
loadMembers()  // carga S.members para el proyecto actual
```

Los errores de negocio (4xx) se propagan como `Error(body.detail)` y los modales los capturan con `toast(err.message, 'err')`.

---

## Router (`js/router.js`)

Hash-based. Se ejecuta en `hashchange` y al arrancar.

| Hash | Vista | Requiere |
|------|-------|---------|
| `#/` | Dashboard | — |
| `#/board/{pid}` | Kanban (default) | acceso al proyecto |
| `#/board/{pid}/kanban` | Kanban | acceso al proyecto |
| `#/board/{pid}/tags` | Gestión etiquetas | acceso al proyecto |
| `#/board/{pid}/priorities` | Gestión prioridades | acceso al proyecto |
| `#/board/{pid}/team` | Equipo del proyecto | acceso al proyecto |
| `#/team` | Panel admin usuarios | `is_admin` |
| `#/admin/flows` | Flujos y etiquetas globales | `is_admin` |

Al cambiar de proyecto (`newPid !== S.pid`) recarga tags y priorities. IDs no numéricos redirigen a `#/`.

---

## Pipeline de render (`js/render.js`)

```
render()
 ├── renderSidebar()    → nav items, botones de acción, avatar usuario
 ├── renderHeader()     → breadcrumb, título, botones contextuales
 └── renderContent()    → llama a la función de vista correspondiente:
      dashboard  → vDashboard()
      board/kanban → vBoard()
      board/tags  → vProjectTags()
      board/priorities → vProjectPriorities()
      board/team  → vProjectTeam()
      team        → vTeam()
      globals     → vGlobals()
```

Todas las funciones de vista retornan HTML como string y se insertan con `innerHTML`. El render es completo en cada ciclo (no virtual DOM).

---

## Sistema de modales (`js/modals/base.js`)

```javascript
showModal(html)   // inserta html en .modal-box y muestra #modal-bg
closeM()          // oculta el modal
bgClose(e)        // cierra si se hace click en el fondo
mhdr(title, sub)  // helper: cabecera estilizada del modal
mfoot(label, showDanger, dangerFn)  // helper: footer con botón guardar y optionalmente eliminar
swatches(sel, nm) // picker de 10 colores predefinidos
iconGrid(sel, nm) // picker de 25 iconos Material Symbols
```

Los modales de creación/edición siempre terminan con: `closeM() → await loadAll() → render() → toast(...)`.

---

## Módulos de vistas y modales

| Archivo | Funciones principales |
|---------|-----------------------|
| `views/dashboard.js` | `vDashboard()`, `projCard(p, taskStats, groupCounts)` |
| `views/board.js` | `vBoard()`, `kanbanCol(g)`, `taskCard(t)` |
| `views/team.js` | `vProjectTeam()`, `vTeam()` |
| `views/tags.js` | `vProjectTags()`: etiquetas y flujos del proyecto (editables) y globales (solo lectura) |
| `views/priorities.js` | `vProjectPriorities()` |
| `modals/project.js` | `mProject(id?)`, `mProjectTeam()`, `mProjectMenu(id)` |
| `modals/group.js` | `mGroup(id?)`, `mColMenu(id)` |
| `modals/task.js` | `mTask(taskId?, groupId?)`, `saveTask()`, `renderTTagSection()`, `renderPrioritySection()` |
| `modals/tag.js` | `mTag(id?, scope='project'\|'global')`, `saveTag()`; selector de flujo |
| `modals/priority.js` | `mProjectPriorities(pid)`, `mPriority(id?)` |
| `modals/user.js` | `mUser()`, `mEditProfile()`, `mAdminEditUser(id)`, `confirmDelUser(id)` |
| `modals/subtask.js` | `loadTodos(taskId)`, `addTodo(taskId)`, `toggleTodo(taskId, todoId)` |
| `delete.js` | `confirmDel(type, id)`, `execDel(type, id)`; tipos `gtag` y `flow` incluidos |
| `flows.js` | Flujos y estados: `tagChip()`, `mFlowState()` (cambio de estado con nota e historial), `mFlowNew()`, `mFlowEdit()` (editor de estados y matriz de transiciones), `vGlobals()`, `tagCards()`, `flowCards()`; permisos `canManageProject()`, `canManageScope()` |
| `dnd.js` | Drag & drop de tarjetas entre columnas y reordenación de columnas |

---

## Flujos y estados (`js/flows.js`)

Ver la especificación en [flows.md](flows.md).

- **Chips de estado:** en tarjetas y en la cabecera de las columnas, una etiqueta
  con flujo se pinta como `Etiqueta: Estado` (`tagChip(tg, kind, itemId)`). Al
  pulsarlo se abre `mFlowState`, que solo ofrece los destinos permitidos por las
  transiciones, admite una nota y muestra el historial del elemento.
- **Vista de etiquetas del proyecto** (`#/board/{pid}/tags`): etiquetas y flujos
  propios, editables por owner/leader/admin; los globales, en solo lectura.
- **Panel global** (`#/admin/flows`, solo admin): etiquetas y flujos globales.
- **Editor de flujo:** nombre, estados (color, nombre, inicial, borrar), alta de
  estados y matriz de transiciones desde × hacia. Cada cambio se envía al momento
  y el editor se vuelve a pintar con la respuesta (`flowOp` → `refreshFlowEditor`).
  Borrar un estado pide un segundo clic en 3 s (`armThen`); si está en uso, el
  backend responde 409 y se muestra en un toast.
- **Grupos:** el modal de grupo tiene casillas de etiquetas; al guardar asigna y
  desasigna por diferencia.

---

## Seguridad frontend

- **`esc(s)`** (`utils.js`): escapa HTML (`&`, `<`, `>`, `"`, `'`) — se usa siempre que se inserta user content en `innerHTML`.
- **`jsq(s)`** (`utils.js`): escapa para literales de string JS dentro de atributos `onclick` (escapa `\`, `'`, `"`, saltos de línea). Necesario para valores de texto en handlers inline.
- **`confirmDel(type, id)`**: recibe solo el ID numérico (seguro), busca el nombre en `S` internamente — evita inyección de strings en atributos onclick.
- Los IDs numéricos se interpolan directamente en `onclick` sin riesgo de inyección.

---

## Drag & Drop (`js/dnd.js`)

Implementación manual con eventos de ratón (`mousedown`, `mousemove`, `mouseup`):
- **Tarjetas:** arrastrar entre columnas → `PATCH /groups/{id}/tasks/reorder`
- **Columnas:** reordenar el tablero → `PATCH /groups/reorder`
- Indicadores visuales: clases CSS `drop-before` / `drop-after` en tarjetas, `col-reorder-before` / `col-reorder-after` en columnas.
