# 📦 Instalación en Host (Pipenv)

Esta guía cubre la configuración de LibreFolio directamente en una máquina host usando Python, Node.js y Pipenv. Este método de instalación manual es adecuado para usuarios que desean ejecutar LibreFolio sin Docker (por ejemplo, en máquinas con pocos recursos) y también es el primer paso para los desarrolladores que preparan un entorno de desarrollo local.

Para el despliegue en contenedores, consulte la [Guía de Instalación del Manual de Usuario](../user/installation.md) o la [Guía de Docker Avanzado](docker_advanced.md).

---

## ✅ Requisitos Previos

Antes de continuar, asegúrese de tener instalados los siguientes requisitos en su sistema:

??? info "🐍 Python 3.13+"

    Se requiere Python 3.13 para el backend de FastAPI.
    
    * **macOS**: Instalar usando Homebrew:
      ```bash
      brew install python@3.13
      ```
    * **Windows**: Descargue el instalador desde [python.org](https://www.python.org/downloads/) (asegúrese de marcar "Add Python to PATH").
    * **Linux (Ubuntu/Debian)**:
      ```bash
      sudo apt update
      sudo apt install python3.13 python3.13-venv python3.13-dev
      ```

??? info "📦 Node.js 24+"

    Se requiere Node.js para compilar el frontend de SvelteKit.
    
    * **macOS**: Instalar a través de Homebrew:
      ```bash
      brew install node@24
      ```
    * **Windows/Linux**: Instalar usando [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) o [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), o descárguelo directamente desde [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Pipenv gestiona los entornos virtuales y las dependencias de Python.
    
    * **Todas las plataformas**:
      ```bash
      pip install --user pipenv
      ```
      *Nota: Asegúrese de que las rutas de binarios de usuario (por ejemplo, `~/.local/bin` en Linux/macOS o `%APPDATA%\Python` en Windows) estén añadidas a la variable `PATH` de su shell.*

---

## 📋 Instrucciones de Configuración

LibreFolio incluye un script de orquestación principal, `dev.py`, para automatizar las tareas de gestión comunes.

!!! important "Prerrequisito para el Entorno de Python"

    Dado que `dev.py` importa módulos del código de la aplicación del backend, ejecutarlo directamente antes de instalar las dependencias dará como resultado excepciones de tipo `ImportError`. 
    
    Por lo tanto, la primera vez que configure el proyecto en su host, debe inicializar el entorno virtual ejecutando:
    ```bash
    pipenv install --dev
    ```
    Una vez configurado este entorno inicial, puede usar `dev.py` de forma segura para todos los pasos posteriores.

!!! tip "Ejecución de `dev.py` (Contexto de Pipenv)"

    Dado que todas las dependencias del backend se instalan dentro del entorno virtual gestionado por `pipenv`, cualquier ejecución de comandos en el host debe ejecutarse en ese contexto:
    
    * **Comandos únicos**: Prefije su comando con `pipenv run` (por ejemplo, `pipenv run ./dev.py server`).
    * **Shell interactiva**: Ejecute primero `pipenv shell` para entrar al entorno virtual, después de lo cual podrá ejecutar directamente `./dev.py` sin prefijos.
    
    *Nota: Si está ejecutando comandos dentro de un contenedor Docker en ejecución (por ejemplo, a través de `docker exec`), **no** es necesario utilizar `pipenv run` o `pipenv shell`. La imagen de producción de Docker preinstala todas las dependencias de Python de forma global en el entorno del sistema del contenedor.*

### 📥 1. Descargar el Proyecto

Clone el repositorio:

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

O descargue el último paquete de lanzamiento desde [GitHub Releases](https://github.com/Librefolio/LibreFolio/releases) y descomprímalo.

### 📦 2. Instalar Dependencias

Una vez inicializado su entorno virtual, instale todas las dependencias restantes de Python, Node.js y del navegador:

```bash
pipenv run ./dev.py install
```

Bajo el capó, este comando:

1. Inicializará el entorno virtual de Python e instalará los paquetes a través de `pipenv`.
2. Instalará las dependencias de frontend de SvelteKit a través de `npm`.
3. Instalará los binarios del navegador Playwright (utilizados para la generación de informes PDF y las pruebas E2E).

### ⚙️ 3. Configurar el Entorno

Copie el archivo de entorno de ejemplo para crear su configuración `.env` activa:

```bash
cp .env.example .env
```

Los ajustes predeterminados funcionan de inmediato. A continuación se presentan las variables clave:

* **`PORT`**: Puerto de escucha del servidor (por defecto: `6040`).
* **`LIBREFOLIO_DATA_DIR`**: Ruta del directorio donde se almacenan la base de datos, las subidas y los logs (por defecto: `./backend/data/prod`).
* **`LOG_LEVEL`**: Nivel de detalle de los logs (por defecto: `INFO`).

Para una descripción completa de todas las variables de entorno soportadas, consulte la [Guía de Variables de Entorno](configuration.md).

### 🚀 4. Iniciar el Servidor

Para iniciar el servidor FastAPI en el host:

```bash
pipenv run ./dev.py server
```

El servidor estará disponible en `http://localhost:6040`.

#### Opciones del Comando del Servidor

| Bandera | Descripción |
|------|-------------|
| `--host HOST` | Dirección de escucha (por defecto: var de entorno `HOST` o `0.0.0.0`) |
| `--port PORT` / `-p PORT` | Puerto de escucha (por defecto: var de entorno `PORT` o `6040`) |
| `--workers N` / `-w N` | Número de procesos trabajadores de uvicorn (por defecto: 1, deshabilita la recarga automática) |
| `--no-scheduler` | Deshabilita las tareas en segundo plano para sincronizar datos de mercado |

### 👤 5. Acceder a la Aplicación y Crear Usuarios

La primera vez que acceda a LibreFolio en su navegador, verá una **página de registro** donde podrá crear su primera cuenta. El primer usuario registrado se convierte automáticamente en el administrador del sistema.

Para gestionar usuarios o promoverlos a administrador a través de la línea de comandos, consulte la [Guía de Herramientas CLI para Usuarios](cli_tools.md).

---

## 🗃️ Inicialización y Restablecimiento de la Base de Datos

Al ejecutar la aplicación por primera vez, la base de datos se inicializa automáticamente. Si necesita restablecer la base de datos a un estado limpio, puede hacerlo de dos maneras:

### 1. Comando de Terminal
Puede ejecutar el comando de limpieza desde la CLI de la base de datos:
```bash
pipenv run ./dev.py db create-clean
```
> [!WARNING]
> Este comando eliminará por completo la base de datos SQLite existente y recreará el esquema desde cero. **Todos los datos se perderán de forma permanente.**

### 2. Restablecimiento Manual
1. Detenga el servidor si está en ejecución.
2. Elimine el archivo de base de datos SQLite (ubicado por defecto en `backend/data/prod/sqlite/app.db`).
3. Reinicie el servidor; inicializará automáticamente un nuevo archivo de base de datos SQLite.
