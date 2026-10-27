# Guía de actualización de JKanban

> Procedimiento para pasar una instalación existente de JKanban a una versión nueva,
> pensado para que **Claude Code** lo ejecute cuando se le pida «actualiza JKanban en
> `<carpeta>` a la versión X». También sirve para una persona: cada paso trae el
> comando y cómo comprobar que ha ido bien.
>
> Para instalar en un equipo o una carpeta nuevos, usar la
> [guía de instalación desde cero](instalacion.md).

**Versión:** JKanban 1.0.0, 27 de octubre de 2026.

---

## 0. Datos de entrada

| Dato | Valor por defecto | Notas |
|------|-------------------|-------|
| `DEST` — carpeta de la instalación | *(obligatorio)* | Ruta absoluta. Si no se indica, **preguntar**. |
| Versión destino | la última etiquetada | Ver [`CHANGELOG.md`](../../CHANGELOG.md). Nunca `develop`. |
| Base de datos | `DEST/tasks.db` | O la que indique `SQLITE_PATH` en esa instalación. |

## 1. Leer qué cambia

En [`CHANGELOG.md`](../../CHANGELOG.md), leer todas las entradas entre la versión
instalada y la de destino, y las [notas por versión](#notas-por-versión) de esta guía.

- Si sube el **primer número** (por ejemplo, de 1.x a 2.0), algo deja de ser compatible
  (API REST, herramientas del MCP o datos). Contar al usuario qué cambia y **pedir
  confirmación** antes de seguir.
- Si sube el segundo o el tercero, la actualización es compatible.

## 2. Comprobar la instalación actual

Desde `DEST`:

```bash
git describe --tags      # versión instalada, por ejemplo v1.0.0
git status --short       # debe salir vacío
```

✅ Se conoce la versión instalada y no hay cambios locales.

Si `git status` muestra cambios, **no seguir**: preguntar al usuario qué hacer con
ellos. Una actualización no debe perder trabajo.

## 3. Parar JKanban

Detener el servidor (la consola de `start-dev.ps1` o de uvicorn). Si el MCP está
registrado en algún proyecto, cerrar las sesiones de Claude Code que lo usan: cada una
lanza su propio proceso del MCP.

✅ `GET http://127.0.0.1:8000/health` ya no responde.

## 4. Copia de seguridad de la base de datos

```powershell
# Windows (PowerShell), desde DEST
Copy-Item tasks.db "tasks.db.antes-de-vX.Y.Z.bak"
```

```bash
# Linux / macOS
cp tasks.db "tasks.db.antes-de-vX.Y.Z.bak"
```

Con `SQLITE_PATH`, copiar ese archivo. Sustituir `vX.Y.Z` por la versión destino.

✅ La copia existe y tiene el mismo tamaño que el original.

## 5. Cambiar a la versión nueva

```bash
git fetch --tags
git checkout vX.Y.Z
```

Git avisa de *detached HEAD*: es lo normal en una versión etiquetada.

✅ `git describe --tags` devuelve `vX.Y.Z`.

## 6. Dependencias

```powershell
# Windows (PowerShell)
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
# Solo si el MCP está instalado:
.\.venv-mcp\Scripts\python.exe -m pip install -r jkanban_mcp\requirements.txt
```

```bash
# Linux / macOS
.venv/bin/python -m pip install -r backend/requirements.txt
.venv-mcp/bin/python -m pip install -r jkanban_mcp/requirements.txt   # solo con MCP
```

✅ `pip` termina sin errores.

## 7. Arrancar y verificar

La base de datos se migra sola al arrancar: las migraciones de SQLite ponen al día el
esquema sin perder datos.

```powershell
.\scripts\start-dev.ps1              # Windows
```

```bash
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Verificación, con el servidor en marcha:

1. `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`.
2. `GET http://127.0.0.1:8000/openapi.json` → `info.version` es la versión destino, sin la `v`.
3. `POST http://127.0.0.1:8000/auth/login` con el admin → devuelve `access_token`.
4. `GET http://127.0.0.1:8000/projects/` con ese token → están los proyectos de antes.

✅ Si las cuatro funcionan, la actualización está completa.

**Con MCP:** volver a abrir Claude Code en el proyecto que lo usa. `/mcp` debe mostrar
`jkanban` conectado, con el número de herramientas que indique el `CHANGELOG.md`.

## 8. Vuelta atrás, si algo falla

1. Parar JKanban.
2. Volver a la versión anterior: `git checkout v<anterior>`.
3. Restaurar la copia del paso 4 sobre `tasks.db`. Hace falta aunque los datos parezcan
   bien: las migraciones pueden haber cambiado el esquema, y la versión anterior no lo
   entiende.
4. Repetir el paso 6 para reinstalar las dependencias anteriores.
5. Arrancar y verificar como en el paso 7.

## 9. Informe final al usuario

- Versión anterior y nueva, y commit (`git log --oneline -1`).
- Dónde quedó la copia de la base de datos.
- Resultado de las comprobaciones del paso 7, también del MCP si lo hay.
- Cambios de la versión que afecten al usuario (del `CHANGELOG.md`).
- Cualquier paso saltado o que fallara.

## Notas por versión

Lo que una versión pide además de los pasos anteriores. Cada versión nueva añade aquí
su entrada, si la necesita.

**A 1.0.0, desde 0.0.0.** Cambia la estructura del código (`app/` pasa a `backend/` y
`frontend/`), el archivo de dependencias (`backend/requirements.txt`) y la orden de
arranque (`backend.main:app`). En lugar de actualizar la carpeta antigua:

1. Instalar la 1.0.0 en otra carpeta con la [guía de instalación](instalacion.md),
   pasos 1-3.
2. Copiar el `tasks.db` antiguo a la carpeta nueva antes del paso 4.
3. Seguir desde el paso 4. Si ya hay un usuario administrador con contraseña conocida,
   el paso 4 no hace falta; si no, el comando convierte en administrador el usuario de
   ese email.
4. Al arrancar, las migraciones ponen al día el esquema.
