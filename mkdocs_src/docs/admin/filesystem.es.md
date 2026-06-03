# 📂 Estructura del Sistema de Archivos

LibreFolio almacena todos los datos persistentes en un directorio estructurado bajo `backend/data/`. Comprender esta estructura es importante para realizar copias de seguridad, depuración y mantenimiento.

---

## 🗂️ Diseño del Directorio

```
backend/data/
├── 📂 prod/ # Datos de producción (predeterminado)
│ ├── 🗃️ sqlite/
│ │ └── 📄 app.db # Base de datos SQLite principal (modo WAL)
│ ├── 🖼️ custom-uploads/ # Archivos subidos por el usuario
│ │ ├── 📄 {uuid}.{ext} # Archivo binario (imagen, documento, etc.)
│ │ └── 📋 {uuid}.json # Archivo de metadatos complementario (quien subió, fecha, tipo MIME)
│ ├── 📊 broker_reports/
│ │ ├── 📥 uploaded/ # Reportes esperando ser procesados
│ │ ├── ✅ parsed/ # Reportes procesados exitosamente
│ │ └── ❌ failed/ # Reportes que fallaron en el procesamiento
│ └── 📝 logs/ # Archivos de registro (logs) de la aplicación
│
└── 🧪 test/ # Datos de prueba (completamente aislados)
    ├── 🗃️ sqlite/app.db
    ├── 🖼️ custom-uploads/
    ├── 📊 broker_reports/
    └── 📝 logs/
```

---

## 📖 Qué hay en cada Directorio

### 🗃️ `sqlite/app.db`

La base de datos SQLite principal. Contiene todos los datos de la aplicación: usuarios, brókers, transacciones, tipos de cambio FX, configuración, etc.

- 📝 Utiliza el modo de diario **WAL (Write-Ahead Logging)** para un mejor acceso concurrente
- 📎 Los archivos `.db-wal` y `.db-shm` son archivos WAL temporales; son normales y gestionados por SQLite

:material-arrow-right: **Inmersión para desarrolladores**: [Esquema de la Base de Datos](../developer/architecture/database/index.md)

### 🖼️ `custom-uploads/`

Archivos subidos por los usuarios a través de la página de Archivos. Cada subida crea dos archivos:

- 📄 `{uuid}.{ext}` — El archivo binario real (ej. `a1b2c3d4.png`)
- 📋 `{uuid}.json` — Metadatos que incluyen: nombre de archivo original, tipo MIME, tamaño del archivo, fecha de subida, ID del usuario que subió el archivo

:material-arrow-right: **Inmersión para desarrolladores**: [Componente de Subida de Archivos](../developer/frontend/components/file-upload.md)

### 📊 `broker_reports/`

Archivos de reportes de brókers para el sistema BRIM (Broker Report Import Manager):

- **📥 `uploaded/`** — Archivos en bruto tal como fueron subidos por los usuarios (CSV, Excel)
- **✅ `parsed/`** — Archivos que han sido procesados exitosamente (transacciones extraídas)
- **❌ `failed/`** — Archivos que fallaron en el procesamiento (se conservan para depuración; consulte los logs para más detalles)

:material-arrow-right: **Inmersión para desarrolladores**: [Arquitectura de BRIM](../developer/backend/brim/architecture.md)

### 📝 `logs/`

Registros de la aplicación en formato JSON estructurado (vía `structlog`). Los archivos de registro se rotan semanalmente y se conservan durante 1 año (comprimidos con gzip).

La verbosidad está controlada por la variable de entorno `LOG_LEVEL`.

**Qué captura cada nivel** — cada fila muestra qué niveles de log son visibles:

| LOG_LEVEL | 🔬 TRACE (5) | 🐛 DEBUG (10) | ℹ️ INFO (20) | ⚠️ WARNING (30) | ❌ ERROR (40) | 💀 CRITICAL (50) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 🔬`TRACE` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 🐛`DEBUG` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ℹ️ **`INFO`** *(predeterminado)* | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| ⚠️ `WARNING` | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| ❌`ERROR` | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| 💀`CRITICAL` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

**Qué significa cada nivel:**

| Nivel | Qué captura |
|-------|-----------------|
| 🔬`TRACE` | Datos granulares de alta frecuencia: tipos de cambio FX individuales procesados, puntos de precio por activo |
| 🐛`DEBUG` | Internos operativos: qué proveedor se utilizó, resultados intermedios, decisiones algorítmicas |
| ℹ️`INFO` | Operaciones de usuario significativas: sincronización completada, importación, inicio de sesión, recurso creado/eliminado |
| ⚠️`WARNING` | Anomalías recuperables: fallback activado, datos opcionales faltantes, modo degradado |
| ❌`ERROR` | Errores manejados: operaciones fallidas, corrupción de datos, proveedor inalcanzable |
| 💀`CRITICAL` | Errores fatales que detienen el proceso |

!!! tip "Configuraciones recomendadas"

    - **Producción**: `LOG_LEVEL=INFO` — señal limpia, sin ruido
    - **Resolución de problemas**: `LOG_LEVEL=DEBUG` — permite ver qué está decidiendo el sistema
    - **Depuración profunda de FX/precios**: `LOG_LEVEL=TRACE` — permite ver cada punto de dato individual

---

## 🌍 Variables de Entorno

| Variable | Predeterminado | Descripción |
|----------|---------|-------------|
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Sobrescribe la ruta del directorio de datos de producción |
| `LIBREFOLIO_TEST_MODE` | `0` | Establecer en `1` para usar `backend/data/test/` en lugar de `prod/` |
| `PORT` | `6040` | Puerto del servidor de producción |
| `TEST_PORT` | `6041` | Puerto del servidor de prueba (usado cuando `LIBREFOLIO_TEST_MODE=1`) |

---

## 💾 Copia de Seguridad (Backup)

### 📦 Copia de Seguridad Simple

La forma más sencilla de respaldar LibreFolio es copiar todo el directorio de datos:

```bash
# Detenga el servidor primero (para asegurar la consistencia de la base de datos)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Copia de Seguridad con Docker

Si se ejecuta vía Docker, el directorio de datos normalmente está montado como un volumen:

```bash
# Buscar el volumen
docker volume inspect librefolio_data

# Extraer los datos
docker cp librefolio-container:/app/backend/data/prod/ ./backup/
```

### ✅ Qué respaldar

Como mínimo, respalde:

1. **`sqlite/app.db`** — Todos sus datos (usuarios, transacciones, configuración, tipos de cambio FX)
2. **`custom-uploads/`** — Archivos subidos por los usuarios (avatares, documentos)
3. **`broker_reports/uploaded/`** — Reportes originales de brókers (en caso de que necesite procesarlos nuevamente)

!!! tip "Respaldo solo de la base de datos"

    Si el almacenamiento es limitado, respaldar solo `sqlite/app.db` preserva todos los datos estructurados. Los archivos siempre pueden volver a subirse.

---

## 🔧 Mantenimiento desde la Terminal del Host

### 🐳 Docker exec

```bash
# Acceder al shell del contenedor
docker exec -it librefolio-container /bin/bash

# Ejecutar comandos de dev.py dentro del contenedor
./dev.py user list
./dev.py user reset admin newpassword
./dev.py db upgrade
```

### 💻 Acceso directo (sin Docker)

```bash
# Desde la raíz del proyecto
./dev.py user list # Listar todos los usuarios
./dev.py user reset <user> <pw> # Restablecer la contraseña de un usuario
./dev.py user promote <user> # Otorgar privilegios de superusuario
./dev.py user demote <user> # Eliminar privilegios de superusuario
./dev.py db upgrade # Aplicar migraciones pendientes
./dev.py db create-clean # Restablecer base de datos (ADVERTENCIA: elimina todos los datos)
```

Para una lista completa de comandos CLI, consulte [Herramientas CLI](cli_tools.md).
