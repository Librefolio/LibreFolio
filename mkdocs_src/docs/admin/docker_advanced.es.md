# 🐳 Guía Avanzada de Docker

Esta guía proporciona una mirada más profunda a la configuración de Docker para LibreFolio, destinada a usuarios que deseen personalizar su despliegue.

## ⚠️ Prerrequisitos

!!! warning "Grupo Docker (Linux)"

    En Linux, su usuario debe pertenecer al grupo `docker` para ejecutar comandos de Docker sin `sudo`:

    ```bash
    sudo usermod -aG docker $USER
    ```

    Luego **cierre la sesión y vuelva a iniciarla**, o ejecute `newgrp docker` para activar el grupo en la sesión actual. De lo contrario, todos los comandos `docker` y `docker compose` fallarán con un error de permisos.

!!! warning "Archivo `.env` requerido"

    LibreFolio requiere un archivo `.env` en la raíz del proyecto. Si falta, `./dev.py docker build` se negará a proceder.

    ```bash
    cp .env.example .env
    $EDITOR .env # revisar y personalizar parámetros
    ```

## 🏗️ Arquitectura

LibreFolio utiliza una **imagen de Docker solo de tiempo de ejecución (runtime-only)**. El frontend (SvelteKit) y la documentación (MkDocs) se compilan en el host y luego se copian en la imagen. El comando `./dev.py docker build` gestiona esto automáticamente.

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

- 🏗️ **`build: .`**: Compila desde el `Dockerfile` en la raíz del proyecto.
- 🔌 **`ports`**: Mapea el puerto del host (`${PORT:-8000}`) al puerto `8000` del contenedor, y `${TEST_PORT:-8001}` al `8001` para el modo de prueba.
- 📂 **`volumes`**: Un montaje de enlace (bind mount) `./LibreFolio-data` → `/app/backend/data/prod-docker` persiste la base de datos, las cargas de archivos, los informes del bróker y los logs **en el mismo directorio que `docker-compose.yml`**.
- 📝 **`env_file: .env`**: Carga toda la configuración desde el archivo `.env` (copiado de `.env.example`).
- 🌍 **`environment`**: Sobrescribe solo los valores específicos de Docker: `LIBREFOLIO_DATA_DIR` (ruta del contenedor) y `HOST=0.0.0.0`.
- 🩺 **`healthcheck`**: Consulta `GET /api/v1/system/health` cada 30 segundos.

### 💾 Directorio de Datos: `LibreFolio-data/`

Un directorio de **montaje de enlace** creado junto a `docker-compose.yml`. Contiene la base de datos SQLite, las cargas personalizadas, los informes del bróker y los archivos de log. Los datos sobreviven a la detención, reinicio o eliminación del contenedor. Puede realizar copias de seguridad directamente desde el sistema de archivos del host.

## 🛠️ Comandos CLI

Todas las operaciones de Docker están disponibles a través de `dev.py`:

```bash
./dev.py docker build # Compilar imagen (compila automáticamente el frontend y la documentación)
./dev.py docker build --no-cache # Recompilación completa sin caché de Docker
./dev.py docker rebuild # Build → stop → restart (despliegue en un paso)
./dev.py docker up # Iniciar contenedores
./dev.py docker down # Detener contenedores
./dev.py docker logs -f # Seguir logs del contenedor
./dev.py docker status # Mostrar estado del contenedor
./dev.py docker exec <cmd> # Ejecutar un comando de dev.py dentro del contenedor
```

!!! tip "Documentación con capturas de pantalla"

    Si está compilando la documentación y desea capturas de pantalla completas en la galería, ejecute:

    ```bash
    ./dev.py mkdocs --gallery
    ```

    Esto requiere un entorno completamente instalado (con `pipenv`) y un servidor en ejecución con datos de prueba cargados. Sea paciente: la generación de la galería tarda unos minutos.

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

| Puerto | Propósito | Base de Datos |
|------|---------|----------|
| `8000` | Servidor de producción (iniciado por el CMD del contenedor) | `prod-docker/sqlite/app.db` (volumen persistente) |
| `8001` | Servidor de prueba (iniciado manualmente vía `docker exec`) | `test/sqlite/app.db` (efímero) |

### Iniciando el Servidor de Prueba

1. **Inicie el contenedor** (el servidor de producción se inicia automáticamente en `:8000`):

 ```bash
 docker compose up -d
 ```

2. **Cargue la base de datos de prueba** con datos simulados:

 ```bash
 ./dev.py docker exec test db populate --force --with-static
 ```

3. **Inicie el servidor de prueba** en el puerto 8001:

 ```bash
 ./dev.py docker exec server --test
 ```

4. **Acceda** en **`http://localhost:8001`**

 Credenciales de prueba:

 | Usuario | Contraseña |
 |----------|----------|
 | `e2e_test_user` | `E2eTestPass123!` |
 | `e2e_test_admin` | `E2eAdminPass123!` |

!!! warning "Los datos de prueba son efímeros"

    La base de datos de prueba reside dentro de la **capa escribible** del contenedor, no en un montaje de enlace persistente. Esto significa que:

    - ✅ Los datos sobreviven a `docker compose stop` / `docker compose start` (el contenedor se pausa, no se elimina).
    - ❌ Los datos se **pierden** con `docker compose down` (el contenedor se elimina y se recrea).

    Si necesita datos de prueba persistentes, añada un montaje de enlace dedicado en `docker-compose.yml`:

    ```yaml
    volumes:
    - ./LibreFolio-data:/app/backend/data/prod-docker
    - ./LibreFolio-test-data:/app/backend/data/test # ← añada esto
    ```

## 🏭 Consideraciones de Producción

### 🎮 1. Personalización de `docker-compose.yml`

El repositorio incluye un archivo `docker-compose.yml` listo para usar. Aquí está el archivo completo con anotaciones que muestran qué puede personalizar:

```yaml
services:
 librefolio:
 image: librefolio:latest # Built by ./dev.py docker build
 build: .
 container_name: librefolio
 restart: unless-stopped
 ports:
 - "${PORT:-8000}:8000" # (1) Production port — change via PORT in .env
 - "${TEST_PORT:-8001}:8001" # (2) Test server port (optional)
 volumes:
 - ./LibreFolio-data:/app/backend/data/prod-docker # (3) Persistent data (bind mount)
 env_file: .env # (4) All config from .env file
 environment:
 - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker # Docker-specific override
 - HOST=0.0.0.0
 healthcheck:
 test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/system/health')"]
 interval: 30s
 timeout: 10s
 start_period: 15s
 retries: 3
```

**Personalizaciones comunes:**

| # | Qué | Cómo |
|---|------|-----|
| (1) | Cambiar puerto de producción | Establezca `PORT=3000` en `.env` |
| (2) | Deshabilitar puerto de prueba | Elimine la línea `TEST_PORT` de `ports:` |
| (3) | Ruta de datos personalizada | Cambie el montaje: `./my-data:/app/backend/data/prod-docker` |
| (4) | Toda la configuración | Edite el archivo `.env` (copiado de `.env.example`) |

!!! tip "Primer usuario"

    La primera vez que acceda a LibreFolio en el navegador, verá una página de registro. Cree su cuenta directamente; el primer usuario se convierte automáticamente en el administrador. No es necesario usar la CLI.

### 🔒 2. Proxy Inverso

Se recomienda encarecidamente ejecutar LibreFolio detrás de un proxy inverso como **Nginx** o **Traefik**. Esto le permite:

- 🔐 Gestionar fácilmente certificados SSL/TLS para HTTPS.
- 🖥️ Servir múltiples aplicaciones en el mismo servidor.
- 🛡️ Añadir cabeceras de seguridad y limitación de frecuencia (rate limiting).

### 💾 3. Copia de Seguridad de la Base de Datos

La base de datos se almacena en el directorio `LibreFolio-data/` junto a `docker-compose.yml`. Realice la copia de seguridad directamente desde el sistema de archivos del host:

```bash
#!/bin/bash
cp ./LibreFolio-data/sqlite/app.db /path/to/backups/app.db-$(date +%F)
```

No es necesario usar `docker cp`, ya que el directorio de datos es un montaje de enlace accesible desde el host.

### 🔑 4. Variables de Entorno

Toda la configuración se gestiona en el archivo `.env` (copiado de `.env.example`). Las sobrescrituras específicas de Docker en el bloque `environment:` no deben cambiarse:

| Variable | Predeterminado | Descripción | Ubicación |
|----------|---------|-------------|-------|
| `PORT` | `8000` | Puerto del host para el servidor de producción | `.env` |
| `TEST_PORT` | `8001` | Puerto del host para el servidor de prueba | `.env` |
| `LOG_LEVEL` | `INFO` | Verbosidad de los logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `.env` |
| `PORTFOLIO_BASE_CURRENCY` | `EUR` | Moneda base para los cálculos de la cartera | `.env` |
| `PREVIEW_CACHE_MAX_MB` | `50` | Caché máxima de previsualización de imágenes en memoria (MB) | `.env` |
| `LIBREFOLIO_DATA_DIR` | `/app/backend/data/prod-docker` | Ruta del contenedor para los datos (no cambiar) | `docker-compose.yml` |
| `HOST` | `0.0.0.0` | Dirección de enlace del contenedor (no cambiar) | `docker-compose.yml` |
