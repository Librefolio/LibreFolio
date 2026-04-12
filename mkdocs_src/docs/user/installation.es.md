# 🐳 Instalación (Usuario)

Esta guía explica cómo desplegar LibreFolio para uso regular utilizando Docker. Este es el método recomendado para los usuarios que no tengan la intención de modificar el código fuente.

## ✅ Prerrequisitos

- 🐍 **Python 3.13+**: [Instalar Python](https://www.python.org/downloads/)
- 📦 **Node.js 20.19+**: [Instalar Node.js](https://nodejs.org/) (incluye npm)
- 📋 **Pipenv**: `pip install pipenv`
- 🐋 **Docker**: [Instalar Docker](https://docs.docker.com/get-docker/) (incluye Docker Compose)

!!! warning "Grupo Docker (Linux)"

    En Linux, su usuario debe estar en el grupo `docker` para ejecutar comandos de Docker sin `sudo`:

    ```bash
    sudo usermod -aG docker $USER
    ```

    Luego **cierre sesión y vuelva a iniciar sesión**, o ejecute `newgrp docker` para activar el grupo en la sesión actual.

!!! note "¿Por qué Python y Node.js?"

    LibreFolio utiliza una **imagen de Docker solo de tiempo de ejecución (runtime-only)** — el frontend y la documentación se compilan en el host antes de empaquetarse en la imagen de Docker. Se planean imágenes precompiladas en un registro de contenedores para futuras versiones.

## 📥 1. Descargar el Proyecto

Clone el repositorio:

```bash
git clone https://github.com/Alfystar/LibreFolio.git
cd LibreFolio
```

O descargue la última versión desde [GitHub Releases](https://github.com/Alfystar/LibreFolio/releases) y descomprímala.

## ⚙️ 2. Configurar el Entorno

1. **Copie el archivo de ejemplo** (obligatorio — la compilación no se iniciará sin el archivo `.env`):

 ```bash
 cp .env.example .env
 ```

2. **Edite `.env`** para personalizar:

 - 🔌 `PORT`: Cambie el puerto si el `8000` ya está en uso.
 - 💰 `PORTFOLIO_BASE_CURRENCY`: La moneda base de la cartera (por defecto: `EUR`).
 - 📊 `LOG_LEVEL`: Verbosidad del registro (por defecto: `INFO`).

## 📦 3. Instalar Dependencias

```bash
./dev.py install
```

Esto instala las dependencias de Python (backend) y Node.js (frontend).

## 🏗️ 4. Compilar la Imagen de Docker

```bash
./dev.py docker build
```

Este comando automáticamente:

1. Compila el frontend (compilación de producción de SvelteKit)
2. Compila el sitio de documentación (MkDocs)
3. Empaqueta todo en una única imagen de Docker etiquetada como `librefolio:latest`

## 🚀 5. Iniciar con Docker Compose

```bash
docker compose up -d
```

- 🔄 `-d` ejecuta la aplicación en modo desvinculado (en segundo plano).

## 🌐 6. Acceder a LibreFolio

Abra su navegador y vaya a:

**`http://localhost:8000`**

(O utilice el puerto que configuró en `.env`).

La primera vez que acceda a LibreFolio, aparecerá una **página de registro** — cree su cuenta directamente desde el navegador. El primer usuario registrado se convierte automáticamente en el administrador.

Endpoints disponibles:

- 🏠 **Frontend**: `http://localhost:8000/`
- 📚 **Documentación de Usuario**: `http://localhost:8000/mkdocs/`

!!! tip "Gestión de usuarios por CLI"

    También puede gestionar los usuarios desde la línea de comandos. Consulte el [Manual del Administrador — Herramientas CLI](../admin/cli_tools.md) para comandos como la creación, promoción y listado de usuarios.

## 🔄 Actualizar LibreFolio

Para actualizar a una nueva versión:

1. **Obtenga el código más reciente**:

 ```bash
 git pull
 ```

2. **Recompile la imagen de Docker** (recompila automáticamente el frontend y la documentación si han cambiado):

 ```bash
 ./dev.py docker rebuild
 ```

 Este comando compila una nueva imagen, detiene los contenedores en ejecución y reinicia con la nueva versión.

3. Las **migraciones de la base de datos** se aplican automáticamente al iniciar.

## 🧪 Probar con Datos de Prueba (Opcional)

Puede iniciar un servidor de prueba con datos simulados pre-cargados para explorar la aplicación antes de introducir datos reales:

```bash
./dev.py docker exec test db populate --force --with-static
./dev.py docker exec server --test
```

Acceda en **`http://localhost:8001`** con el usuario `e2e_test_user` / `E2eTestPass123!`.

El servidor de prueba se ejecuta junto al de producción, utilizando una base de datos separada. Consulte la [Guía Avanzada de Docker](../admin/docker_advanced.md#test-mode) para más detalles.

---

!!! tip "Temas avanzados"

    Para la configuración de proxy inverso, copias de seguridad de la base de datos, rutas de datos personalizadas y consideraciones de producción, consulte la [🐳 Guía Avanzada de Docker](../admin/docker_advanced.md).
