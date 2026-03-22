# 🛠️ Herramientas de Línea de Comandos

LibreFolio proporciona el script `dev.py` para tareas de administración. Esta página cubre los comandos más relevantes para **administradores del sistema**.

!!! info "👩‍💻 Para Desarrolladores"
 Para comandos específicos de desarrollo (compilación frontend, ejecutor de pruebas, sincronización de API, auditoría i18n), consulta la [Guía de Instalación para Desarrolladores](../developer/dev-installation.md).

---

## 🚀 Instalación

Instala todas las dependencias del proyecto (Python y Node.js):

```bash
./dev.py install
```

---

## 🖥️ Servidor (Producción)

### ▶️ Iniciar el servidor

```bash
# Inicio estándar
./dev.py server

# Con workers calculados automáticamente (2 × (CPU-1))
./dev.py server --workers N

# Terminar proceso existente en el puerto antes de iniciar
./dev.py server --force
```

!!! tip "Multi-worker"
 Para producción, usa `--workers` para ejecutar múltiples workers de Uvicorn. Esto mejora el rendimiento y se recomienda para cualquier despliegue con más de un núcleo de CPU.

---

## 👤 Gestión de Usuarios

La gestión de usuarios se realiza mediante subcomandos `./dev.py user`:

```bash
# Crear un usuario (el primer usuario se convierte automáticamente en admin)
./dev.py user create <nombredeusuario> <email> <contraseña>

# Listar todos los usuarios
./dev.py user list

# Restablecer la contraseña de un usuario
./dev.py user reset <nombredeusuario> <nueva_contraseña>

# Promover un usuario a admin
./dev.py user promote <nombredeusuario>

# Degradar un admin a usuario regular
./dev.py user demote <nombredeusuario>
```

---

## ⚙️ Gestión del sistema

### 🔧 Inicializar configuración global

```bash
./dev.py user init-settings
```

Puebla la base de datos con [Configuración Global](settings.md) predeterminada si aún no existen.

### 🗄️ Migraciones de base de datos

```bash
# Aplicar migraciones pendientes
./dev.py db upgrade
```

!!! warning "🗄️ Restablecimiento de base de datos"
 `./dev.py db create-clean` recrea la base de datos desde cero — **se pierden todos los datos**. Úsalo solo si necesitas reiniciar desde cero.

---

## 📚 Documentación

```bash
# Compilar y desplegar documentación de MkDocs en GitHub Pages
./dev.py mkdocs deploy

# Generar capturas de pantalla de la galería (requiere servidor en ejecución + datos de prueba)
./dev.py mkdocs gallery
```

---

## 📋 Árbol completo de comandos

Para una lista completa de todos los comandos disponibles:

```bash
./dev.py --help
```

!!! info "👩‍💻 Comandos de Desarrollador"
 Comandos adicionales para flujos de trabajo de desarrollo:

 - **Frontend**: `./dev.py front build`, `front dev`, `front check` — ver [Desarrollo Frontend](../developer/frontend/index.md)
 - **Pruebas**: `./dev.py test all` — ver [Recorrido de Pruebas](../developer/test-walkthrough/index.md)
 - **Cliente API**: `./dev.py api sync` — ver [Visión General de la API](../developer/api/overview.md)
 - **i18n**: `./dev.py i18n audit` — ver [Internacionalización](../developer/frontend/i18n.md)
