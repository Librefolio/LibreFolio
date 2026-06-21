# 🛠️ Herramientas de Línea de Comandos

LibreFolio proporciona el script `dev.py` para tareas de administración. Esta página cubre los comandos más relevantes para los **administradores del sistema**.

!!! tip "Contexto del Entorno Virtual de Python"

    Si ejecuta LibreFolio directamente en la **máquina host**, todas las operaciones de línea de comandos deben ejecutarse dentro del entorno virtual de Python. Puede anteponer `pipenv run` a cada comando (por ejemplo, `pipenv run ./dev.py server`) o ingresar al entorno virtual una vez ejecutando `pipenv shell`.

    Si se encuentra dentro de la **terminal de un contenedor Docker** (por ejemplo, accediendo a través de `docker exec`), **no** es necesario usar `pipenv run` ni `pipenv shell`, ya que las dependencias están preinstaladas de forma global dentro de la imagen del contenedor. Puede ejecutar los comandos `./dev.py` directamente.

!!! info "👩‍💻 Para Desarrolladores"

    Para comandos específicos de desarrollo (construcción del frontend, ejecutor de pruebas, sincronización de API, auditoría de i18n), consulte la [Guía de Workflow para Desarrolladores](../developer/dev_workflow.md).

---
## 🖥️ Servidor (Producción)

### ▶️ Iniciar el Servidor

```bash
# Standard start
pipenv run ./dev.py server

# With auto-calculated workers (2 × (CPU-1))
pipenv run ./dev.py server --workers N

# Kill existing process on port before starting
pipenv run ./dev.py server --force
```

!!! tip "Multi-worker"

    Para producción, use `--workers` para ejecutar múltiples workers de Uvicorn. Esto mejora la capacidad de procesamiento y se recomienda para cualquier despliegue con más de 1 núcleo de CPU.

---

## 👤 Gestión de Usuarios

La gestión de usuarios se realiza a través de los subcomandos `./dev.py user`:

```bash
# Create a user (first user becomes admin automatically)
pipenv run ./dev.py user create <username> <email> <password>

# List all users
pipenv run ./dev.py user list

# Reset a user's password
pipenv run ./dev.py user reset <username> <new_password>

# Promote a user to admin
pipenv run ./dev.py user promote <username>

# Demote an admin to regular user
pipenv run ./dev.py user demote <username>
```

---

## ⚙️ Gestión del Sistema

### 🔧 Inicializar Configuración Global

```bash
pipenv run ./dev.py user init-settings
```

Puebla la base de datos con la [Configuración Global](settings.md) predeterminada si esta aún no existe.

### 🗄️ Migraciones de Base de Datos

```bash
# Apply pending migrations
pipenv run ./dev.py db upgrade
```

!!! warning "🗄️ Reinicio de base de datos"

    `pipenv run ./dev.py db create-clean` recrea la base de datos desde cero — **se pierden todos los datos**. Úselo solo si necesita empezar desde cero.

---

## 📚 Documentación

```bash
# Build and deploy MkDocs documentation to GitHub Pages
pipenv run ./dev.py mkdocs deploy

# Generate gallery screenshots (requires running server + test data)
pipenv run ./dev.py mkdocs gallery
```

---

## 📋 Árbol Completo de Comandos

Para obtener una lista completa de todos los comandos personalizados disponibles:

```bash
pipenv run ./dev.py --help
```

!!! info "👩‍💻 Comandos de Desarrollador"

    Comandos adicionales para flujos de trabajo de desarrollo:

    - **Frontend**: `pipenv run ./dev.py front build`, `front dev`, `front check` — consulte [Desarrollo del Frontend](../developer/frontend/index.md)
    - **Pruebas**: `pipenv run ./dev.py test all` — consulte [Recorrido de Pruebas](../developer/test-walkthrough/index.md)
    - **Cliente API**: `pipenv run ./dev.py api sync` — consulte [Descripción General de la API](../developer/api/overview.md)
    - **i18n**: `pipenv run ./dev.py i18n audit` — consulte [Internacionalización](../developer/frontend/i18n.md)
