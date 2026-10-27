# Instalación de JKanban

> Procedimiento pensado para que **Claude Code** lo ejecute cuando se le pida
> «instala JKanban en `<carpeta>`». También sirve para una persona: cada paso
> trae el comando y cómo comprobar que ha ido bien.

---

## 0. Datos de entrada

| Dato | Valor por defecto | Notas |
|------|-------------------|-------|
| `DEST` — carpeta destino | *(obligatorio)* | Ruta absoluta. Si no se indica, **preguntar**. |
| Rama | `develop` | `main` usa otra estructura (`app/`), ver [Ramas](#ramas). |
| Puerto | `8000` | Cambiarlo si está ocupado. |
| Modo | **vacío** | `vacío`: sin datos, para uso real (es el de la SF). `demo`: con 3 usuarios y proyectos de ejemplo. |
| Email, nombre y contraseña del admin | *(preguntar)* | Contraseña de al menos 6 caracteres. No inventarla sin decirlo. En modo demo, el email por defecto es `alice@example.com`. |

Repositorio: `https://github.com/jumibot/JKanban.git`

## 1. Comprobaciones previas

| Requisito | Comprobación | Si falla |
|-----------|--------------|----------|
| Git | `git --version` | Pedir al usuario que lo instale. |
| Python **3.13** (mínimo 3.10) | `python --version` (Windows: también `py -3 --version`) | Pedir al usuario que lo instale. No instalar Python por tu cuenta. |
| `DEST` no existe o está vacía | `Test-Path DEST` / `ls -A DEST` | **No sobrescribir.** Si ya contiene un clon de JKanban, ofrecer actualizarlo (`git pull`) en vez de reinstalar. |
| Puerto libre | `Get-NetTCPConnection -LocalPort 8000` / `lsof -i :8000` | Elegir otro puerto. |

## 2. Clonar

```bash
git clone --branch develop https://github.com/jumibot/JKanban.git "DEST"
```

✅ Existen `DEST/backend/main.py` y `DEST/frontend/index.html`.

## 3. Entorno virtual y dependencias

Desde `DEST`:

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

```bash
# Linux / macOS
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
```

✅ `.venv/…/python -c "import fastapi, uvicorn, jwt"` termina sin error.

> El `.venv` guarda rutas absolutas: si después se mueve o renombra la carpeta,
> hay que borrarlo y repetir este paso.

## 4. Base de datos y administrador

La base de datos SQLite (`DEST/tasks.db`, o `SQLITE_PATH`) se crea sola la primera
vez. Si está vacía y `JKANBAN_DEMO_DATA` no es `0`, se llena con datos de
demostración. El registro público solo crea usuarios normales, así que **el
administrador se crea con un comando**, que pasa por los casos de uso (sin SQL).

Ejecutar **desde `DEST`** y **antes del primer arranque**: así la base de datos se
crea ya con el modo elegido. Sustituir `<EMAIL>`, `<NOMBRE>` y `<PASSWORD>`.

**Modo vacío** (recomendado; el de la SF):

```powershell
# Windows (PowerShell)
$env:JKANBAN_DEMO_DATA = "0"
.\.venv\Scripts\python.exe -m backend.create_admin --email "<EMAIL>" --name "<NOMBRE>" --password "<PASSWORD>"
```

```bash
# Linux / macOS
JKANBAN_DEMO_DATA=0 .venv/bin/python -m backend.create_admin --email "<EMAIL>" --name "<NOMBRE>" --password "<PASSWORD>"
```

✅ Imprime `Administrador creado: <email> (id 1)`.

**Modo demo:** el administrador de los datos de demostración
(`alice@example.com`) trae una contraseña ficticia; el comando le pone una real:

```bash
.venv/bin/python -m backend.create_admin --email alice@example.com --password "<PASSWORD>"
```

✅ Imprime `Usuario existente convertido en administrador y contraseña actualizada: alice@example.com (id 1)`.
Desde la web, el admin puede poner contraseña a Bob y a Carol.

Notas:
- La contraseña también se puede pasar con la variable `JKANBAN_ADMIN_PASSWORD`
  (no queda en el historial de la consola).
- Repetir el comando es inocuo. Con un email existente, convierte ese usuario en
  administrador (y, con contraseña, la cambia).
- Una vez hay usuarios, los datos de demostración no se cargan nunca, sea cual sea
  `JKANBAN_DEMO_DATA`.
## 5. Configuración opcional (variables de entorno)

| Variable | Defecto | Cuándo cambiarla |
|----------|---------|------------------|
| `JWT_SECRET` | clave de desarrollo fija | **Siempre** si la app será accesible por otras personas. Generar con `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `SQLITE_PATH` | `DEST/tasks.db` | Para guardar la BD en otro sitio. Usar la misma variable en el paso 4 y al arrancar. |
| `JKANBAN_DEMO_DATA` | `1` | `0` para que una BD nueva arranque vacía (paso 4). Solo influye mientras no hay usuarios. |
| `JKANBAN_ADMIN_PASSWORD` | — | Contraseña para `create_admin`, en lugar de `--password`. |
| `DB_ENGINE` | `sqlite` | Único motor implementado hoy. No tocar. |

## 6. Arrancar y verificar

```powershell
# Windows
.\scripts\start-dev.ps1              # puerto 8000, con --reload
.\scripts\start-dev.ps1 -Port 8080   # otro puerto
```

```bash
# Cualquier sistema
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Verificación (con el servidor en marcha):

1. `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`
2. `POST http://127.0.0.1:8000/auth/login` con JSON
   `{"email":"<EMAIL>","password":"<PASSWORD>"}` → devuelve `access_token` y `"is_admin": true`.
3. `GET http://127.0.0.1:8000/projects/` con `Authorization: Bearer <token>` → lista
   proyectos.

✅ Si las tres funcionan, la instalación está completa. Si solo has arrancado el
servidor para verificar, **detenlo** al acabar, salvo que el usuario quiera dejarlo en marcha.

Ejecutar los tests es opcional (unos 80 s): `.venv/…/python -m pytest -q`. Usan una BD
temporal y no tocan `tasks.db`.

## 7. Informe final al usuario

Resumir en pocas líneas:

- Carpeta, rama y commit instalado (`git log --oneline -1`).
- URL de la app (`http://127.0.0.1:<puerto>`) y de Swagger (`/docs`).
- Modo (vacío o demo) y email del admin. La contraseña solo si la generaste tú.
- Cómo arrancarla de nuevo (comando del paso 6).
- Cualquier paso saltado o que fallara.

## 8. Opcional: servidor MCP

Solo si se pide (por ejemplo, para conectar el proyecto SF): seguir
[mcp.md](mcp.md#instalación). Usa un entorno aparte (`.venv-mcp`) y necesita un
usuario de JKanban dedicado.

---

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---------|-------|----------|
| `ModuleNotFoundError: No module named 'backend'` | Script lanzado fuera de `DEST` | Ejecutar con `DEST` como directorio actual. |
| Login → `Invalid email or password` con el admin | No se hizo el paso 4, o se hizo contra otra BD (`SQLITE_PATH` distinto) | Repetir el paso 4 con la misma configuración. |
| Aparecen datos de ejemplo en modo vacío | Se arrancó el servidor antes del paso 4 sin `JKANBAN_DEMO_DATA=0` | Parar, borrar el fichero de la BD (solo si es nueva) y repetir el paso 4. |
| `create_admin` → `falta la contraseña` | Ni `--password` ni `JKANBAN_ADMIN_PASSWORD` | Pasar una de las dos. |
| Login → `422` | Cuerpo enviado como formulario | Enviar JSON (`Content-Type: application/json`). |
| `.venv` falla tras mover la carpeta | Rutas absolutas en `.venv` | Borrar `.venv` y repetir el paso 3. |
| `start-dev.ps1` bloqueado por la política de ejecución | Política de PowerShell | `powershell -ExecutionPolicy Bypass -File scripts\start-dev.ps1`, o usar uvicorn directamente. |

## Ramas

| Rama | Backend | Frontend | Notas |
|------|---------|----------|-------|
| `develop` | `backend/` | `frontend/` | **Recomendada.** Este documento está escrito para ella. |
| `main`, `release/*` | `app/` | `app/interfaces/static/` | Estructura antigua: el módulo es `app.main:app` y no existe `create_admin`. |
