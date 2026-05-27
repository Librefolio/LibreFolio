# 🐳 Guía Avanzada de Docker

Esta guía proporciona una mirada más profunda a la configuración de Docker para LibreFolio, destinada a usuarios que deseen personalizar su despliegue.

## ⚠️ Prerrequisitos

!!! warning "Docker group (Linux)"

    En Linux, su usuario debe pertenecer al grupo `docker` para ejecutar comandos de Docker sin `sudo`:

    ```bash
    sudo usermod -aG docker $USER
    ```

    Luego **cierre la sesión y vuelva a iniciarla**, o ejecute `newgrp docker` para activar el grupo en la sesión actual. Sin esto, todos los comandos `docker` y `docker compose` fallarán con un error de permisos.

!!! warning "`.env` file required"

    LibreFolio requiere un archivo `.env` en la raíz del proyecto. Si no existe, `./dev.py docker build` se negará a proceder.

    ```bash
    cp .env.example .env
    $EDITOR .env # revise y personalice los parámetros
    ```

## 🏗️ Arquitectura

LibreFolio utiliza una **imagen de Docker exclusiva de tiempo de ejecución**. El frontend (SvelteKit) y la documentación (MkDocs) se compilan en el host y luego se copian en la imagen. El comando `./dev.py docker build` gestiona esto automáticamente.

```text
Host (build) Docker Image (runtime)
┌──────────────┐ ┌──────────────────────┐
│ frontend/src │──npm build──▶ │ frontend/build/ │
│ mkdocs_src/ │──mkdocs ───▶ │ mkdocs_src/site/ │
│ backend/ │──copy──────▶ │ backend/ │
│ Pipfile* │──pipenv ───▶ │ Python packages │
└──────────────┘ └──────────────────────┘
```

## 📄 `docker-compose.yml`

El archivo `docker-compose.yml` define el servicio y el directorio de datos persistentes.

### 🔧 Servicio: `librefolio`

- 🏗️ **`build: .`**: Compila a partir del `Dockerfile` en la raíz del proyecto.
- 🔌 **`ports`**: Mapea el puerto del host (`${PORT:-6040}`) al puerto `6040` del contenedor, y `${TEST_PORT:-6041}` al `6041` para el modo de prueba.
- 📂 **`volumes`**: Un montaje de enlace (bind mount) `./LibreFolio-data` → `/app/backend/data/prod-docker` persiste la base de datos, las cargas de archivos, los informes de brókers y los logs **en el mismo directorio que `docker-compose.yml`**.
- 📝 **`env_file: .env`**: Carga toda la configuración desde el archivo `.env` (copiado de `.env.example`).
- 🌍 **`environment`**: Sobrescribe solo los valores específicos de Docker: `LIBREFOLIO_DATA_DIR` (ruta del contenedor) y `HOST=0.0.0.0`.
- 🩺 **`healthcheck`**: Consulta `GET /api/v1/system/health` cada 30 segundos.

### 💾 Directorio de Datos: `LibreFolio-data/`

Un directorio de **montaje de enlace** creado junto a `docker-compose.yml`. Contiene la base de datos SQLite, las cargas personalizadas, los informes de brókers y los archivos de log. Los datos sobreviven al detener, reiniciar o eliminar el contenedor. Puede realizar copias de seguridad directamente desde el sistema de archivos del host.

### 👤 Usuario y Permisos

El contenedor de LibreFolio se ejecuta como un **usuario no root** por seguridad. El UID/GID por defecto es `1000:1000`. Los archivos creados por la aplicación en `LibreFolio-data/` pertenecerán a este UID/GID en el host.

#### Elección del UID y GID correctos

Configure `UID` y `GID` en su archivo `.env` para que coincidan con el **usuario del host** (o usuario dedicado) que debe poseer los archivos de datos:

```bash
UID=1000
GID=1000
```


!!! note "Cómo `ls -l` muestra la propiedad"

    En el **host**, `ls -l LibreFolio-data/` muestra el nombre de usuario/grupo elegido (resuelto desde el UID/GID vía `/etc/passwd`).

    **Dentro del contenedor**, los mismos archivos se muestran como `librefolio:librefolio` — es el mismo UID/GID numérico, solo que resuelto contra el `/etc/passwd` propio del contenedor.

??? tip "Linux cheatsheet: users, groups, and IDs"

    **Descubra su UID y GID actuales:**

    ```bash
    id -u # su ID de usuario (ej. 1000)
    id -g # su ID de grupo primario (ej. 1000)
    id # info completa: uid, gid, groups
    ```

    **Encuentre el UID/GID de cualquier usuario:**

    ```bash
    id -u username # UID de 'username'
    id -g username # GID primario de 'username'
    ```

    **Crear un nuevo grupo:**

    ```bash
    sudo groupadd librefolio # crear grupo (asigna GID automáticamente)
    sudo groupadd -g 1500 librefolio # crear grupo con GID específico
    ```

    **Crear un nuevo usuario:**

    ```bash
    # Usuario de sistema (sin home, sin login — ideal para servicios)
    sudo useradd --system --no-create-home --gid librefolio --shell /usr/sbin/nologin librefolio

    # Usuario regular con directorio home
    sudo useradd -m -g librefolio librefolio
    ```

    **Verificar los IDs asignados:**

    ```bash
    id librefolio
    # → uid=998(librefolio) gid=998(librefolio) groups=998(librefolio)
    ```

    **Añadir su usuario actual a un grupo:**

    ```bash
    sudo usermod -aG librefolio $USER
    newgrp librefolio # activar en la sesión actual (o cerrar/abrir sesión)
    ```

    **Verificar la membresía del grupo:**

    ```bash
    groups $USER # listar todos los grupos de su usuario
    ```

    **Establecer la propiedad del directorio de datos:**

    ```bash
    sudo chown -R librefolio:librefolio ./LibreFolio-data
    ```

    Luego establezca el UID/GID coincidente en `.env`.

## 🛠️ Comandos de la CLI

Todas las operaciones de Docker están disponibles a través de `dev.py`:

```bash
./dev.py docker build # Compilar imagen (compila automáticamente el frontend y la documentación)
./dev.py docker build --no-cache # Recompilación completa sin caché de Docker
./dev.py docker rebuild # Compilar → detener → reiniciar (despliegue en un paso)
./dev.py docker up # Iniciar contenedores
./dev.py docker down # Detener contenedores
./dev.py docker logs -f # Seguir los logs del contenedor
./dev.py docker status # Mostrar el estado del contenedor
./dev.py docker exec <cmd> # Ejecutar un comando de dev.py dentro del contenedor
```

!!! tip "Documentación con capturas de pantalla"

    Si está compilando la documentación y desea capturas de pantalla completas en la galería, ejecute:

    ```bash
    ./dev.py mkdocs --gallery
    ```

    Esto requiere un entorno completamente instalado (con `pipenv`) y un servidor en funcionamiento con datos de prueba poblados. Sea paciente; la generación de la galería tarda unos minutos.

### 📡 `docker exec` — Ejecución de comandos dentro del contenedor

El subcomando `docker exec` reenvía cualquier comando de `dev.py` al contenedor en ejecución:

```bash
./dev.py docker exec user create admin admin@example.com Pass123!
./dev.py docker exec user list
./dev.py docker exec db upgrade
./dev.py docker exec server --test
```

Esto es equivalente a ejecutar `docker compose exec librefolio python dev.py <cmd>`.

## 🧪 Modo de Prueba

La configuración de Docker Compose expone **dos puertos**:

| Puerto | Propósito | Base de datos |
|------|---------|----------|
| `6040` | Servidor de producción (iniciado por el CMD del contenedor) | `prod-docker/sqlite/app.db` (volumen persistente) |
| `6041` | Servidor de prueba (iniciado manualmente vía `docker exec`) | `test/sqlite/app.db` (efímera) |

### Iniciar el Servidor de Prueba

1. **Inicie el contenedor** (el servidor de producción se inicia automáticamente en `:6040`):

 ```bash
 docker compose up -d
 ```

2. **Pueble la base de datos de prueba** con datos simulados:

 ```bash
 ./dev.py docker exec test db populate --force --with-static
 ```

3. **Inicie el servidor de prueba** en el puerto 6041:

 ```bash
 ./dev.py docker exec server --test
 ```

4. **Acceda** a **`http://localhost:6041`**

 Credenciales de prueba:

 | Usuario | Contraseña |
 |----------|----------|
 | `e2e_test_user` | `E2eTestPass123!` |
 | `e2e_test_admin` | `E2eAdminPass123!` |

!!! warning "Los datos de prueba son efímeros"

    La base de datos de prueba reside dentro de la **capa escribible** del contenedor, no en un montaje de enlace persistente. Esto significa que:

    - ✅ Los datos sobreviven a `docker compose stop` / `docker compose start` (el contenedor se pausa, no se elimina).
    - ❌ Los datos se **pierden** con `docker compose down` (el contenedor se elimina y se vuelve a crear).

    Si necesita datos de prueba persistentes, añada un montaje de enlace dedicado en `docker-compose.yml`:

    ```yaml
    volumes:
    - ./LibreFolio-data:/app/backend/data/prod-docker
    - ./LibreFolio-test-data:/app/backend/data/test # ← añada esto
    ```

## 🏭 Consideraciones de Producción

### 🎮 1. Personalización de `docker-compose.yml`

El repositorio incluye un `docker-compose.yml` listo para usar. Aquí está el archivo completo con anotaciones que muestran qué puede personalizar:

```yaml
services:
 librefolio:
 image: librefolio:latest # Built by ./dev.py docker build
 build:
 context: .
 args:
 UID: ${UID:-1000} # (1) Match host user UID
 GID: ${GID:-1000} # (1) Match host user GID
 container_name: librefolio
 # No 'user:' directive — entrypoint starts as root, fixes permissions,
 # then drops to 'librefolio' user via gosu (same pattern as postgres/redis).
 restart: unless-stopped
 ports:
 - "${PORT:-6040}:6040" # (2) Production port — change via PORT in .env
 - "${TEST_PORT:-6041}:6041" # (3) Test server port (optional)
 volumes:
 - ./LibreFolio-data:/app/backend/data/prod-docker # (4) Persistent data (bind mount)
 env_file: .env # (5) All config from .env file
 environment:
 - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker # Docker-specific override
 - HOST=0.0.0.0
 healthcheck:
 test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:6040/api/v1/system/health')"]
 interval: 30s
 timeout: 10s
 start_period: 15s
 retries: 3
```

**Personalizaciones comunes:**

| # | Qué | Cómo |
|---|------|-----|
| (1) | Coincidir UID/GID del host | Establezca `UID=1001` y `GID=1001` en `.env`, luego vuelva a compilar |
| (2) | Cambiar puerto de producción | Establezca `PORT=3000` en `.env` |
| (3) | Desactivar puerto de prueba | Elimine la línea `TEST_PORT` de `ports:` |
| (4) | Ruta de datos personalizada | Cambie el bind mount: `./my-data:/app/backend/data/prod-docker` |
| (5) | Toda la configuración | Edite el archivo `.env` (copiado de `.env.example`) |

!!! tip "Primer usuario"

    La primera vez que acceda a LibreFolio en el navegador, verá una página de registro. Cree su cuenta directamente; el primer usuario se convierte automáticamente en el administrador. No se requiere la CLI.

### 🔒 2. Proxy Inverso

Se recomienda encarecidamente ejecutar LibreFolio detrás de un proxy inverso como **Nginx** o **Traefik**. Esto le permite:

- 🔐 Gestionar fácilmente certificados SSL/TLS para HTTPS.
- 🖥️ Servir múltiples aplicaciones en el mismo servidor.
- 🛡️ Añadir cabeceras de seguridad y limitación de tasa (rate limiting).

### 💾 3. Copia de Seguridad de la Base de Datos

La base de datos se almacena en el directorio `LibreFolio-data/` junto a `docker-compose.yml`. Realice la copia de seguridad directamente desde el sistema de archivos del host:

```bash
#!/bin/bash
cp ./LibreFolio-data/sqlite/app.db /path/to/backups/app.db-$(date +%F)
```

No es necesario usar `docker cp`; el directorio de datos es un montaje de enlace accesible desde el host.

### 🔑 4. Variables de Entorno

Toda la configuración se gestiona en el archivo `.env` (copiado de `.env.example`). Las sobrescrituras específicas de Docker en el bloque `environment:` no deben cambiarse:

| Variable | Por defecto | Descripción | Dónde |
|----------|---------|-------------|-------|
| `PORT` | `6040` | Puerto del host para el servidor de producción | `.env` |
| `TEST_PORT` | `6041` | Puerto del host para el servidor de prueba | `.env` |
| `UID` | `1000` | UID del usuario del contenedor (debe coincidir con el dueño del directorio de datos) | `.env` |
| `GID` | `1000` | GID del usuario del contenedor (debe coincidir con el dueño del directorio de datos) | `.env` |
| `LOG_LEVEL` | `INFO` | Nivel de detalle de los logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `.env` |
| `PORTFOLIO_BASE_CURRENCY` | `EUR` | Moneda base para los cálculos de la cartera | `.env` |
| `PREVIEW_CACHE_MAX_MB` | `50` | Caché máxima de vista previa de imágenes en memoria (MB) | `.env` |
| `LIBREFOLIO_DATA_DIR` | `/app/backend/data/prod-docker` | Ruta del contenedor para los datos (no cambiar) | `docker-compose.yml` |
| `HOST` | `0.0.0.0` | Dirección de enlace del contenedor (no cambiar) | `docker-compose.yml` |
