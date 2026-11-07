# 📦 Instalación en el host (Pipenv)

Instala LibreFolio en tu máquina sin Docker, con Python, Node.js y Pipenv: práctico con pocos recursos y el primer paso hacia un entorno de desarrollo.

Para Docker, consulta la [Instalación del Manual de usuario](../user/installation.md) o la [Guía avanzada de Docker](docker_advanced.md).

---

## ✅ Requisitos previos

Instala primero estas tres herramientas.

??? info "🐍 Python 3.13"

    La versión establecida en el `Pipfile` del proyecto.

    * **macOS**, con Homebrew:
      ```bash
      brew install python@3.13
      ```
    * **Windows**: descarga el instalador desde [python.org](https://www.python.org/downloads/) y marca «Add Python to PATH».
    * **Linux (Ubuntu/Debian)**:
      ```bash
      sudo apt update
      sudo apt install python3.13 python3.13-venv python3.13-dev
      ```

??? info "📦 Node.js 24+"

    Compila la interfaz web.

    * **macOS**, con Homebrew:
      ```bash
      brew install node@24
      ```
    * **Windows/Linux**: con [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) o [nvm-windows](https://github.com/coreybutler/nvm-windows) (Windows), o descárgalo desde [nodejs.org](https://nodejs.org/).

??? info "📋 Pipenv"

    Gestiona el entorno virtual de Python y sus paquetes.

    * **Todas las plataformas**:
      ```bash
      pip install --user pipenv
      ```
      Añade la carpeta de binarios del usuario (`~/.local/bin` en Linux/macOS, `%APPDATA%\Python` en Windows) al `PATH` del shell.

---

## 📋 Instrucciones de configuración

!!! tip "Los comandos se ejecutan en el entorno de Pipenv"

    Los comandos de `dev.py` comienzan con `pipenv run`, que los ejecuta en el entorno virtual del proyecto.
    O entra en él una vez con `pipenv shell` y escribe `./dev.py …` sin el prefijo.

### 📥 1. Descargar el proyecto

**Dónde:** terminal, en la carpeta donde quieras el proyecto.

```bash
git clone https://github.com/Librefolio/LibreFolio.git
cd LibreFolio
```

Resultado: la carpeta `LibreFolio/`. O descarga y descomprime la última versión desde [Versiones de GitHub](https://github.com/Librefolio/LibreFolio/releases).

### 🐍 2. Crear el entorno de Python

**Dónde:** terminal, carpeta `LibreFolio/`.

```bash
pipenv install --dev
```

Resultado: el entorno virtual con los paquetes de Python. Hazlo antes de cualquier comando `dev.py`: sin él, se detiene con `ModuleNotFoundError`.

### 📦 3. Instalar las demás dependencias

**Dónde:** terminal, carpeta `LibreFolio/`.

```bash
pipenv run ./dev.py install
```

Resultado, en orden:

1. los paquetes de Python de nuevo (`pipenv install --dev`);
2. las herramientas del proyecto (`npm ci`);
3. las dependencias de la interfaz web (`npm ci` en `frontend/`);
4. el navegador Chromium de Playwright, para las pruebas de extremo a extremo y las capturas de pantalla de la documentación. Si solo falla esta descarga, la instalación se completa igualmente.

### ⚙️ 4. Configurar el entorno

**Dónde:** terminal, carpeta `LibreFolio/`; luego el archivo `.env` recién creado.

```bash
cp .env.example .env
```

Resultado: el archivo `.env` con valores predeterminados que funcionan tal cual. Las variables principales:

| Variable | Predeterminado | Descripción |
| --- | --- | --- |
| `PORT` | `6040` | Puerto de escucha del servidor. |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Directorio de la base de datos, los archivos subidos y los registros (consulta [Estructura del sistema de archivos](filesystem.md)). |
| `LOG_LEVEL` | `INFO` | Verbosidad del registro. |

Las demás variables: [Guía de variables de entorno](configuration.md).

### 🚀 5. Iniciar el servidor

**Dónde:** terminal, carpeta `LibreFolio/`.

```bash
pipenv run ./dev.py server
```

Resultado: LibreFolio responde en `http://localhost:6040`. El primer inicio compila la interfaz web y la documentación: unos minutos. Procesos worker, otro puerto y las demás opciones: [Herramientas de línea de comandos](cli_tools.md#start-the-server).

### 👤 6. Crear tu cuenta

**Dónde:** navegador, `http://localhost:6040`, enlace **Regístrate aquí** debajo del formulario de inicio de sesión.

Resultado: la primera cuenta registrada se convierte en administrador. Para gestionar usuarios desde la terminal, consulta [Herramientas de línea de comandos](cli_tools.md). Para que LibreFolio cree el administrador por sí mismo en su primer inicio, consulta [El administrador inicial](configuration_accounts.md#initial-admin).

---

## 🗃️ Inicialización y restablecimiento de la base de datos {: #database-reset }

No hay nada que inicializar: en cada inicio, el servidor crea la base de datos si falta y aplica las migraciones pendientes.

Para empezar de nuevo desde una **base de datos vacía**, usa una de las dos formas siguientes.

!!! warning "Se pierden todos los datos"

    Ambas formas eliminan la base de datos para siempre: usuarios, brókers, transacciones y configuración. Haz primero una copia de seguridad (consulta [Copia de seguridad](filesystem.md#backup)).

### 🧹 Con `dev.py`

**Dónde:** terminal, carpeta `LibreFolio/`, con el servidor detenido (el comando se niega a ejecutarse mientras el servidor está activo).

```bash
pipenv run ./dev.py db create-clean
```

Resultado: una base de datos nueva y vacía.

### 🗑️ A mano

**Dónde:** el directorio de datos, por defecto `backend/data/prod/`.

1. Detén el servidor si está en ejecución.
2. Elimina el archivo de la base de datos SQLite, por defecto `backend/data/prod/sqlite/app.db`.
3. Inicia el servidor: crea una nueva.

Ambas formas reemplazan solo la base de datos: los archivos subidos, los informes del bróker y los registros permanecen en el directorio de datos. Para empezar completamente desde cero, detén el servidor y elimina todo el directorio de datos: el siguiente inicio lo recrea.
