# Autenticación y permisos

## Índice

- [Autenticación JWT](#autenticación-jwt)
- [Hashing de contraseñas](#hashing-de-contraseñas)
- [Roles en proyecto](#roles-en-proyecto)
- [Permisos por operación](#permisos-por-operación)
- [Flag `is_admin` (admin de plataforma)](#flag-is_admin-admin-de-plataforma)
- [Flujo de login](#flujo-de-login-frontend)
- [Flujo de logout](#flujo-de-logout-frontend)

---

## Autenticación JWT

- **Algoritmo:** HS256
- **Expiración:** 7 días
- **Payload:** `{sub: <user_id:int>, exp: <timestamp>}`
- **Secret:** variable de entorno `JWT_SECRET`
- **Header HTTP:** `Authorization: Bearer <token>`
- **Almacenamiento frontend:** `localStorage` bajo las claves `jk_token` y `jk_user`

Cuando el servidor devuelve 401 (token inválido o expirado), el frontend borra el token de localStorage y muestra el formulario de login.

---

## Hashing de contraseñas

Formato almacenado: `pbkdf2$<salt_16bytes_hex>$<hash_hex>`

- Función: PBKDF2-SHA256
- Iteraciones: 100 000
- Verificación: `hmac.compare_digest` (tiempo constante, anti-timing-attack)

---

## Roles en proyecto

Cada usuario puede tener uno de estos roles respecto a un proyecto:

| Rol | Descripción | Cómo se asigna |
|-----|------------|----------------|
| **owner** | Creador del proyecto | Automático al crear el proyecto |
| **leader** | Responsable técnico | Asignado por el owner; por defecto = owner al crear |
| **member** | Colaborador | Añadido por owner o leader vía `POST /projects/{id}/members/{uid}` |
| *(sin rol)* | Sin acceso | 403 en cualquier endpoint del proyecto |

Un usuario puede ser owner de un proyecto y member de otro simultáneamente.

---

## Permisos por operación

| Operación | Owner | Leader | Member | Admin plataforma |
|-----------|:-----:|:------:|:------:|:----------------:|
| Ver proyecto / grupos / tareas | ✓ | ✓ | ✓ | — |
| Crear/editar tareas y grupos | ✓ | ✓ | ✓ | — |
| Editar proyecto (nombre, color, etc.) | ✓ | ✓ | — | — |
| Gestionar miembros (add/remove) | ✓ | ✓ | — | — |
| Crear/editar etiquetas, flujos y prioridades del proyecto | ✓ | ✓ | — | — |
| Asignar etiquetas, cambiar su estado, ver el registro | ✓ | ✓ | ✓ | — |
| Crear/editar etiquetas y flujos **globales** | — | — | — | ✓ |
| Ver etiquetas y flujos globales (cualquier usuario autenticado) | ✓ | ✓ | ✓ | ✓ |
| Eliminar proyecto (simple) | ✓ | — | — | — |
| Eliminar proyecto en cascada | ✓ | — | — | — |
| Ver todos los usuarios | — | — | — | ✓ |
| Crear usuarios | — | — | — | ✓ |
| Editar cualquier usuario | — | — | — | ✓ |
| Eliminar usuario en cascada | — | — | — | ✓ |
| Acceder a `/admin/*` | — | — | — | ✓ |
| Cambiar propio perfil | propio | propio | propio | propio |

---

## Flag `is_admin` (admin de plataforma)

- Gestiona usuarios a nivel global (crear, editar, eliminar con cascada).
- Puede acceder a la vista `/team` en el frontend.
- **No puede** eliminarse a sí mismo (`AdminCannotDeleteSelf`).
- **No puede** quitarse su propio `is_admin` — el backend lo rechaza con 403, y el frontend deshabilita el checkbox en el modal de edición.
- El primer usuario de la BD se promueve automáticamente a admin al arrancar si no existe ningún admin.

---

## Flujo de login (frontend)

```
Usuario envía form
  → POST /auth/login {email, password}
  ← {access_token, user}
  → saveAuth(token, user)       localStorage + S.currentUser
  → showApp()                   oculta auth-wall, muestra app
  → loadAll()                   carga datos globales
  → route()                     navega al hash actual
```

## Flujo de logout (frontend)

```
doLogout()
  → clearAuth()                 borra localStorage
  → showAuthWall()              muestra auth-wall
  → resetea S completo          projects, groups, tasks, users, tags, priorities, members = []
  → location.hash = '#/'
```
