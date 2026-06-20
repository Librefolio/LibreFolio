# 🛠️ Herramientas de Línea de Comandos

LibreFolio proporciona el script `dev.py` para tareas de administración. Esta página cubre los comandos más relevantes para los **administradores del sistema**.

!!! info "👩‍💻 Para Desarrolladores"

    Para comandos específicos de desarrollo (construcción del frontend, ejecutor de pruebas, sincronización de API, auditoría de i18n), consulte la [Guía de Workflow para Desarrolladores](../developer/dev_workflow.md).

---
## 🖥️ Servidor (Producción)

### ▶️ Iniciar el Servidor

```bash
# Standard start
./dev.py server

# With auto-calculated workers (2 × (CPU-1))
./dev.py server --workers N

# Kill existing process on port before starting
./dev.py server --force
```

!!! tip "Multi-worker"

    Para producción, use `--workers` para ejecutar múltiples workers de Uvicorn. Esto mejora la capacidad de procesamiento y se recomienda para cualquier despliegue con más de 1 núcleo de CPU.

---

## 👤 Gestión de Usuarios

La gestión de usuarios se realiza a través de los subcomandos `./dev.py user`:

```bash
# Create a user (first user becomes admin automatically)
./dev.py user create <username> <email> <password>

# List all users
./dev.py user list

# Reset a user's password
./dev.py user reset <username> <new_password>

# Promote a user to admin
./dev.py user promote <username>

# Demote an admin to regular user
./dev.py user demote <username>
```

---

## ⚙️ Gestión del Sistema

### 🔧 Inicializar Configuración Global

```bash
./dev.py user init-settings
```

Puebla la base de datos con la [Configuración Global](settings.md) predeterminada si esta aún no existe.

### 🗄️ Migraciones de Base de Datos

```bash
# Apply pending migrations
./dev.py db upgrade
```

!!! warning "🗄️ Reinicio de base de datos"

    `./dev.py db create-clean` recrea la base de datos desde cero — **se pierden todos los datos**. Úselo solo si necesita empezar desde cero.

---

## 📚 Documentación

```bash
# Build and deploy MkDocs documentation to GitHub Pages
./dev.py mkdocs deploy

# Generate gallery screenshots (requires running server + test data)
./dev.py mkdocs gallery
```

---

## 📋 Árbol Completo de Comandos

Para obtener una lista completa de todos los comandos disponibles:

```bash
./dev.py --help
```

!!! info "👩‍💻 Comandos de Desarrollador"

    Comandos adicionales para flujos de trabajo de desarrollo:

    - **Frontend**: `./dev.py front build`, `front dev`, `front check` — consulte [Desarrollo del Frontend](../developer/frontend/index.md)
    - **Pruebas**: `./dev.py test all` — consulte [Recorrido de Pruebas](../developer/test-walkthrough/index.md)
    - **Cliente API**: `./dev.py api sync` — consulte [Descripción General de la API](../developer/api/overview.md)
    - **i18n**: `./dev.py i18n audit` — consulte [Internacionalización](../developer/frontend/i18n.md)
