# 📂 Estructura del Sistema de Archivos

LibreFolio almacena todos los datos persistentes en un directorio estructurado bajo `backend/data/`. Comprender esta estructura es importante para las copias de seguridad, la depuración y el mantenimiento.

---

## 🗂️ Diseño de Directorios

```
backend/data/
├── 📂 prod/ # Datos de producción (por defecto)
│ ├── 🗃️ sqlite/
│ │ └── 📄 app.db # Base de datos SQLite principal (modo WAL)
│ ├── 🖼️ custom-uploads/ # Archivos subidos por usuarios
│ │ ├── 📄 {uuid}.{ext} # Archivo binario (imagen, documento, etc.)
│ │ └── 📋 {uuid}.json # Archivo de metadatos asociado (subidor, fecha, tipo MIME)
│ ├── 📊 broker_reports/
│ │ ├── 📥 uploaded/ # Informes esperando ser procesados
│ │ ├── ✅ parsed/ # Informes procesados exitosamente
│ │ └── ❌ failed/ # Informes que fallaron al procesarse
│ └── 📝 logs/ # Archivos de registro de la aplicación
│
└── 🧪 test/ # Datos de prueba (completamente aislados)
 ├── 🗃️ sqlite/app.db
 ├── 🖼️ custom-uploads/
 ├── 📊 broker_reports/
 └── 📝 logs/
```

---

## 📖 Contenido de Cada Directorio

### 🗃️ `sqlite/app.db`

La base de datos SQLite principal. Contiene todos los datos de la aplicación: usuarios, brokers, transacciones, tasas de cambio, configuración, etc.

- 📝 Utiliza el **modo WAL (Write-Ahead Logging)** para un mejor acceso concurrente
- 📎 Los archivos `.db-wal` y `.db-shm` son archivos temporales generados y gestionados automáticamente por SQLite

:material-arrow-right: **Análisis en profundidad para desarrolladores**: [Esquema de la Base de Datos](../developer/architecture/database/index.md)

### 🖼️ `custom-uploads/`

Archivos subidos por usuarios a través de la página de Archivos. Cada subida crea dos archivos:

- 📄 `{uuid}.{ext}` — El archivo binario real (ej., `a1b2c3d4.png`)
- 📋 `{uuid}.json` — Archivo de metadatos asociado que incluye: nombre de archivo original, tipo MIME, tamaño, fecha de subida, ID del usuario que subió

:material-arrow-right: **Análisis en profundidad para desarrolladores**: [Componente de Subida de Archivos](../developer/frontend/components/file-upload.md)

### 📊 `broker_reports/`

Archivos de informes de broker para el sistema BRIM (Broker Report Import Manager):

- **📥 `uploaded/`** — Archivos sin procesar subidos por usuarios (CSV, Excel)
- **✅ `parsed/`** — Archivos que se han procesado con éxito (transacciones extraídas)
- **❌ `failed/`** — Archivos que fallaron al procesarse (se guardan para depuración — revisar los registros para detalles)

:material-arrow-right: **Análisis en profundidad para desarrolladores**: [Arquitectura de BRIM](../developer/backend/brim/architecture.md)

### 📝 `logs/`

Registros de la aplicación en formato JSON estructurado (vía `structlog`).

---

## 🌍 Variables de Entorno

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Sobrescribir la ruta del directorio de datos de producción |
| `LIBREFOLIO_TEST_MODE` | `0` | Establecer a `1` para usar `backend/data/test/` en lugar de `prod/` |
| `PORT` | `8000` | Puerto del servidor de producción |
| `TEST_PORT` | `8001` | Puerto del servidor de pruebas (usado cuando `LIBREFOLIO_TEST_MODE=1`) |

---

## 💾 Copia de Seguridad

### 📦 Copia de Seguridad Simple

La forma más fácil de hacer una copia de seguridad de LibreFolio es copiar todo el directorio de datos:

```bash
# Detener el servidor primero (para garantizar la consistencia de la base de datos)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Copia de Seguridad con Docker

Si se ejecuta con Docker, el directorio de datos suele estar montado como un volumen:

```bash
# Encontrar el volumen
docker volume inspect librefolio_data

# Copiar los datos afuera
docker cp librefolio-container:/app/backend/data/prod/ ./backup/
```

### ✅ Qué Copiar

Como mínimo, haz copia de seguridad de:

1. **`sqlite/app.db`** — Todos tus datos (usuarios, transacciones, configuración, tasas de cambio)
2. **`custom-uploads/`** — Archivos subidos por usuarios (avatars, documentos)
3. **`broker_reports/uploaded/`** — Informes originales de broker (por si necesitas volver a procesarlos)

!!! tip "Copia de seguridad solo de la base de datos"
 Si el almacenamiento es limitado, hacer copia de seguridad solo de `sqlite/app.db` preserva todos los datos estructurados. Los archivos siempre se pueden volver a subir.

---

## 🔧 Mantenimiento desde el Terminal del Host

### 🐳 Docker exec

```bash
# Acceder al shell del contenedor
docker exec -it librefolio-container /bin/bash

# Ejecutar comandos de dev.py dentro del contenedor
./dev.py user list
./dev.py user reset admin newpassword
./dev.py db upgrade
```

### 💻 Ejecución directa (sin Docker)

```bash
# Desde la raíz del proyecto
./dev.py user list # Listar todos los usuarios
./dev.py user reset <user> <pw> # Restablecer la contraseña de un usuario
./dev.py user promote <user> # Otorgar privilegios de superusuario
./dev.py user demote <user> # Eliminar privilegios de superusuario
./dev.py db upgrade # Aplicar migraciones pendientes
./dev.py db create-clean # Reiniciar la base de datos (ADVERTENCIA: elimina todos los datos)
```

Para una lista completa de comandos de CLI, ver [Herramientas CLI](cli_tools.md).

---
