# 📂 Estructura del Sistema de Archivos

LibreFolio almacena todos los datos persistentes en un directorio estructurado bajo `backend/data/`. Comprender esta estructura es importante para realizar copias de seguridad, depuración y mantenimiento.

---

## 🗂️ Diseño del Directorio

```
backend/data/
├── 📂 prod/                          # Production data (default)
│   ├── 🗃️ sqlite/
│   │   └── 📄 app.db                 # Main SQLite database (WAL mode)
│   ├── 🖼️ custom-uploads/            # User-uploaded files
│   │   ├── 📄 {uuid}.{ext}          # Binary file (image, document, etc.)
│   │   └── 📋 {uuid}.json           # Metadata sidecar (uploader, date, MIME type)
│   ├── 📊 broker_reports/
│   │   ├── 📥 uploaded/              # Reports waiting to be parsed
│   │   ├── ✅ parsed/               # Successfully parsed reports
│   │   └── ❌ failed/               # Reports that failed parsing
│   └── 📝 logs/                      # Application log files
│
└── 🧪 test/                          # Test data (completely isolated)
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

:material-arrow-right: **Inmersión para desarrolladores**: [Componente de Subida de Archivos](../developer/frontend/components/core-ui/file-upload.md)

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

Las rutas de almacenamiento y los comportamientos en tiempo de ejecución del sistema de archivos están controlados por variables de entorno (como `LIBREFOLIO_DATA_DIR` y `LIBREFOLIO_TEST_MODE`). Para obtener una lista completa de todas las variables de entorno admitidas y cómo configurarlas mediante el archivo `.env`, consulte la página de [Configuración](configuration.md).

---

## 💾 Copia de Seguridad (Backup)

### 📦 Copia de Seguridad Simple

La forma más sencilla de respaldar LibreFolio es copiar todo el directorio de datos:

```bash
# Stop the server first (to ensure database consistency)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Copia de Seguridad con Docker

Si ejecuta LibreFolio a través de Docker Compose (el método de despliegue estándar), el directorio de datos de producción está montado directamente (bind-mount) en el directorio `./LibreFolio-data` de su máquina host (y mapeado a `/app/backend/data/prod-docker` dentro del contenedor).

Por lo tanto, no necesita ningún comando especial de copia de Docker; simplemente realizar una copia de seguridad de la carpeta `./LibreFolio-data` en su máquina host es suficiente para asegurar sus datos.

### ✅ Qué respaldar

Como mínimo, respalde:

1. **`sqlite/app.db`** — Todos sus datos (usuarios, transacciones, configuración, tipos de cambio FX)
2. **`custom-uploads/`** — Archivos subidos por los usuarios (avatares, documentos)
3. **`broker_reports/uploaded/`** — Reportes originales de brókers (en caso de que necesite procesarlos nuevamente)

!!! tip "Respaldo solo de la base de datos"

    Si el almacenamiento es limitado, respaldar solo `sqlite/app.db` preserva todos los datos estructurados. Los archivos siempre pueden volver a subirse.
