# 📦 Instalación en el host (Pipenv)

Esta guía instala LibreFolio directamente en tu máquina con Python, Node.js y Pipenv, sin Docker: útil en máquinas con pocos recursos y el primer paso hacia un entorno de desarrollo.

Para Docker, consulta la [Instalación en el Manual de usuario](../user/installation.md) o la [Guía Avanzada de Docker](docker_advanced.md).

---

## ✅ Requisitos previos

Instala primero estas tres herramientas.

??? info "🐍 Python 3.13"

    El backend necesita Python 3.13, la versión establecida en el `Pipfile` del proyecto.

    * **macOS**: Instala usando Homebrew:
      ```bash
      brew install python@3.13
      ```
    * **Windows**: Descarga el instalador desde [python.org](https://www.python.org/downloads/) (asegúrate de marcar "Add Python to PATH").
    * **Linux (Ubuntu/Debian)**:
      ```bash
      sudo apt update
      sudo apt install python3.13 python3.13-venv python3.13-dev
      ```

??? info "📦 Node.js 24+"

    Node.js compila la interfaz web.

    * **macOS**: Instala mediante Homebrew:
      ```bash
      brew install node@24
      ```
    * **Windows/Linux**: Instala usando [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) o [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), o descárgalo directamente desde [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Pipenv gestiona el entorno virtual de Python y sus paquetes.

    * **Todas las plataformas**:
      ```bash
      pip install --user pipenv
      ```
      *Nota: asegúrate de que las rutas de los binarios del directorio base del usuario (p. ej., `~/.local/bin` en Linux/macOS o `%APPDATA%\Python` en Windows) estén añadidas a la variable `PATH` de tu shell.*

---

## 📋 Instrucciones de configuración

!!! tip "Los comandos se ejecutan en el entorno de Pipenv"

    Los comandos de `dev.py` comienzan con `pipenv run`, que los ejecuta en el entorno virtual del proyecto. También puedes entrar en él una vez con `pipenv shell` y luego escribir `./dev.py …` sin el prefijo.

### 📥 1. Descargar el proyecto

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

O descarga el paquete de la última versión desde [Versiones de GitHub](https://github.com/Librefolio/LibreFolio/releases) y descomprímelo.

### 🐍 2. Crear el entorno de Python

```bash
pipenv install --dev
```

Haz esto antes de cualquier comando `dev.py`: `dev.py` necesita estos paquetes de Python y, sin ellos, se detiene con un `ModuleNotFoundError`.

### 📦 3. Instalar las demás dependencias

```bash
pipenv run ./dev.py install
```

En orden, instala:

1. los paquetes de Python de nuevo, con `pipenv install --dev`;
2. las herramientas del proyecto, con `npm install`;
3. las dependencias de la interfaz web, con `npm ci` en `frontend/`;
4. el navegador Chromium de Playwright, usado por las pruebas de extremo a extremo y las capturas de pantalla de la documentación. Si solo falla esta descarga, la instalación se completa igualmente.

### ⚙️ 4. Configurar el entorno

```bash
cp .env.example .env
```

Los valores predeterminados funcionan tal cual. Las variables principales:

| Variable | Predeterminado | Descripción |
| --- | --- | --- |
| `PORT` | `6040` | Puerto de escucha del servidor. |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Directorio donde se almacenan la base de datos, los archivos subidos y los registros (consulta [Estructura del sistema de archivos](filesystem.md)). |
| `LOG_LEVEL` | `INFO` | Verbosidad del registro. |

Las demás variables se describen en la [Guía de variables de entorno](configuration.md).

### 🚀 5. Iniciar el servidor

```bash
pipenv run ./dev.py server
```

El primer inicio compila la interfaz web y la documentación, por lo que tarda unos minutos. Luego abre `http://localhost:6040`. Para los procesos worker, otro puerto y las demás opciones, consulta [Herramientas de línea de comandos](cli_tools.md#start-the-server).

### 👤 6. Crear tu cuenta

Abre LibreFolio en tu navegador y elige **Regístrate aquí** debajo del formulario de inicio de sesión: la primera cuenta registrada se convierte en administrador. Para gestionar usuarios desde la terminal, consulta [Herramientas de línea de comandos](cli_tools.md).

---

## 🗃️ Inicialización y restablecimiento de la base de datos {: #database-reset }

No hay nada que inicializar a mano: en cada inicio, el servidor crea la base de datos si falta y aplica cualquier migración pendiente.

Para empezar de nuevo desde una **base de datos vacía**, usa una de las dos formas siguientes.

!!! warning "Se pierden todos los datos"

    Ambas formas eliminan la base de datos para siempre: usuarios, brókers, transacciones y configuración. Haz una copia de seguridad primero (consulta [Copia de seguridad](filesystem.md#backup)).

### 🧹 Con `dev.py`

Detén el servidor (el comando se niega a ejecutarse mientras está activo), luego:

```bash
pipenv run ./dev.py db create-clean
```

### 🗑️ A mano

1. Detén el servidor si está en ejecución.
2. Elimina el archivo de base de datos SQLite (por defecto `backend/data/prod/sqlite/app.db`).
3. Inicia el servidor: crea una base de datos nueva.

Ambas formas reemplazan solo la base de datos: los archivos subidos, los informes del bróker y los registros permanecen en el directorio de datos. Para un inicio completamente desde cero, detén el servidor y elimina todo el directorio de datos en su lugar (por defecto `backend/data/prod/`): el siguiente inicio lo recrea.
