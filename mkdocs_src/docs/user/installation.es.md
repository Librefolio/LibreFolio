# 🐳 Instalación (Usuario)

Esta guía explica cómo desplegar LibreFolio para uso regular utilizando Docker. Este es el método recomendado para usuarios que no tengan la intención de modificar el código fuente.

## ✅ Requisitos previos

- 🐍 **Python 3.13+**: [Instalar Python](https://www.python.org/downloads/)
- 📦 **Node.js 20.19+**: [Instalar Node.js](https://nodejs.org/) (incluye npm)
- 📋 **Pipenv**: `pip install pipenv`
- 🐋 **Docker**: [Instalar Docker](https://docs.docker.com/get-docker/) (incluye Docker Compose)

!!! warning "Grupo de Docker (Linux)"

    En Linux, su usuario debe pertenecer al grupo `docker` para ejecutar comandos de Docker sin `sudo`:

    ```bash
    sudo usermod -aG docker $USER
    ```

    Luego, **cierre la sesión y vuelva a entrar**, o ejecute `newgrp docker` para activar el grupo en la sesión actual.

!!! note "¿Por qué Python y Node.js?"

    LibreFolio utiliza una **imagen de Docker solo de tiempo de ejecución (runtime-only)**; el frontend y la documentación se construyen en el host antes de empaquetarse en la imagen de Docker. Se planea incluir imágenes preconstruidas en un registro de contenedores en futuras versiones.

## 📥 1. Descargar el proyecto

Clone el repositorio:

```bash
git clone https://github.com/Alfystar/LibreFolio.git
cd LibreFolio
```

O descargue la última versión desde [GitHub Releases](https://github.com/Alfystar/LibreFolio/releases) y descomprímala.

## ⚙️ 2. Configurar el entorno

1. **Copie el archivo de ejemplo** (obligatorio: el proceso de construcción se detendrá si no existe el archivo `.env`):

    ```bash
    cp .env.example .env
    ```

2. **Edite `.env`** para personalizar:

    - 🔌 `PORT`: Cambie el puerto si el `6040` ya está en uso.
    - 💰 `PORTFOLIO_BASE_CURRENCY`: Su moneda base (por defecto: `EUR`).
    - 📊 `LOG_LEVEL`: Nivel de detalle del registro (por defecto: `INFO`).

## 📦 3. Instalar dependencias

```bash
./dev.py install
```

Esto instala las dependencias de Python (backend) y Node.js (frontend).

## 🏗️ 4. Construir la imagen de Docker

```bash
./dev.py docker build
```

Este comando realiza automáticamente lo siguiente:

1. Construye el frontend (build de producción de SvelteKit)
2. Construye el sitio de documentación (MkDocs)
3. Empaqueta todo en una única imagen de Docker etiquetada como `librefolio:latest`

## 🚀 5. Iniciar con Docker Compose

```bash
docker compose up -d
```

- 🔄 `-d` ejecuta la aplicación en modo desconectado (en segundo plano).

## 🌐 6. Acceder a LibreFolio

Abra su navegador y diríjase a:

**`http://localhost:6040`**

(O utilice el puerto que configuró en `.env`).

La primera vez que acceda a LibreFolio, se le presentará una **página de registro**; cree su cuenta directamente desde el navegador. El primer usuario registrado se convierte automáticamente en el administrador.

Endpoints disponibles:

- 🏠 **Frontend**: `http://localhost:6040/`
- 📚 **Documentación de usuario**: `http://localhost:6040/mkdocs/`

!!! tip "Gestión de usuarios por CLI"

    También puede gestionar los usuarios desde la línea de comandos. Consulte el [Manual de Administración — Herramientas CLI](../admin/cli_tools.md) para comandos como la creación, promoción y listado de usuarios.

## 🔄 Actualizar LibreFolio

Para actualizar a una nueva versión:

1. **Obtenga el código más reciente**:

    ```bash
    git pull
    ```

2. **Reconstruya la imagen de Docker** (reconstruye automáticamente el frontend y la documentación si han cambiado):

    ```bash
    ./dev.py docker rebuild
    ```

    Este comando construye una nueva imagen, detiene los contenedores en ejecución y los reinicia con la nueva versión.

3. Las **migraciones de la base de datos** se aplican automáticamente al iniciar.

## 🧪 Probar con datos de prueba (Opcional)

Puede iniciar un servidor de prueba con datos simulados pre-cargados para explorar la aplicación antes de introducir datos reales:

```bash
./dev.py docker exec test db populate --force --with-static
./dev.py docker exec server --test
```

Acceda en **`http://localhost:6041`** con el usuario `e2e_test_user` / `E2eTestPass123!`.

El servidor de prueba se ejecuta junto al de producción, utilizando una base de datos separada. Consulte la [Guía Avanzada de Docker](../admin/docker_advanced.md#test-mode) para más detalles.

---

!!! tip "Temas avanzados"

    Para la configuración de proxy inverso, copias de seguridad de la base de datos, rutas de datos personalizadas y consideraciones de producción, consulte la [🐳 Guía Avanzada de Docker](../admin/docker_advanced.md).
