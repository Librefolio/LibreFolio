# 📂 Estructura del sistema de archivos

LibreFolio guarda todo lo que almacena en un **directorio de datos**: la base de datos, los archivos subidos, los informes del bróker y los registros. Su estructura es todo lo que necesitas saber para las copias de seguridad y el mantenimiento.

| Instalación | Directorio de datos |
| --- | --- |
| Host (Pipenv) | `backend/data/prod/` en la carpeta del proyecto, o la ruta en `LIBREFOLIO_DATA_DIR` |
| Docker Compose | `LibreFolio-data/` junto a `docker-compose.yml` (`/app/backend/data/prod-docker` dentro del contenedor) |

---

## 🗂️ Estructura de directorios

```text
backend/data/
├── 📂 prod/                          # Production data (default)
│   ├── 🗃️ sqlite/
│   │   └── 📄 app.db                 # Main SQLite database (WAL mode)
│   ├── 🖼️ custom-uploads/            # Files uploaded in the app
│   ├── 📊 broker_reports/
│   │   ├── 📥 uploaded/              # Reports waiting to be read
│   │   ├── ✅ parsed/                # Reports read successfully
│   │   └── ❌ failed/                # Reports that could not be read
│   ├── 📝 logs/                      # Application log files
│   ├── 🎭 scenario_catalog/          # Optional: your own stress scenarios
│   └── 📋 scheduler_state.json       # Last run of the scheduled syncs
│
└── 🧪 test/                          # Test data (completely isolated)
    ├── 🗃️ sqlite/app.db
    ├── 🖼️ custom-uploads/
    ├── 📊 broker_reports/
    └── 📝 logs/
```

---

## 📖 Qué hay en cada directorio

### 🗃️ `sqlite/`

- 📄 `app.db` contiene todos los datos estructurados: usuarios, brókers, transacciones, activos, precios, tipos de cambio y configuración.
- 📎 `app.db-wal` y `app.db-shm` son los archivos de trabajo de SQLite (modo WAL), esperados mientras el servidor está en ejecución: nunca copies `app.db` por sí solo mientras el servidor está activo.
- 🔒 `app.db.post-migration.lock` es un archivo vacío que se usa al inicio: déjalo en su sitio. Un archivo llamado `app.db.pre-<fix>-<UTC time>.bak` es una copia que se conserva tras una [corrección posterior a la migración](cli_tools.md#post-migration-fixes) fallida: elimínalo cuando ya no lo necesites.

### 🖼️ `custom-uploads/`

Archivos subidos en la aplicación, como los de la página **Archivos**, y los avatares predeterminados. Cada archivo tiene un nombre aleatorio y un archivo `.json` junto a él que lo describe: mantén juntos los pares.

### 📊 `broker_reports/`

Los informes del bróker subidos para importar, en una carpeta `broker_<id>/` por bróker:

- **📥 `uploaded/`** — esperando a ser leídos
- **✅ `parsed/`** — leídos correctamente
- **❌ `failed/`** — no se pudieron leer, se conservan para que puedas comprobar por qué

Un informe pasa de `uploaded/` a `parsed/` o `failed/`, así que su archivo original siempre está en una de las tres.

### 📝 `logs/`

- 📄 `librefolio.log` contiene un registro JSON por línea; el servidor también imprime el log en su consola.
- 🗓️ Cada lunes (UTC) el archivo se archiva y comprime (`.gz`); se conservan los últimos 52 archivos, un año.
- 🎚️ `LOG_LEVEL` en `.env` establece cuánto se escribe (por defecto `INFO`).

??? info "📶 Niveles de registro — qué registra cada uno"

    Cada nivel también registra todos los más graves.

    | Nivel | Qué captura |
    |-------|-----------------|
    | 🔬 `TRACE` | Datos granulares de alta frecuencia: tipos de cambio individuales analizados, puntos de precio por activo |
    | 🐛 `DEBUG` | Detalles internos operativos: qué proveedor se usó, resultados intermedios, decisiones algorítmicas |
    | ℹ️ `INFO` *(por defecto)* | Operaciones significativas del usuario: sincronización completada, importación, inicio de sesión, recurso creado/eliminado |
    | ⚠️ `WARNING` | Anomalías recuperables: fallback activado, datos opcionales faltantes, modo degradado |
    | ❌ `ERROR` | Errores gestionados: operaciones fallidas, corrupción de datos, proveedor inaccesible |
    | 💀 `CRITICAL` | Errores fatales que detienen el proceso |

    - **Producción**: `LOG_LEVEL=INFO` — señal limpia, sin ruido
    - **Solución de problemas**: `LOG_LEVEL=DEBUG` — ver qué está decidiendo el sistema
    - **Depuración profunda de FX/precios**: `LOG_LEVEL=TRACE` — ver cada punto de datos individual

🔗 Para desarrolladores: [Directorio de datos en disco](../developer/architecture/database/index.md#data-directory) — cada archivo, su formato y el código que lo escribe, `scenario_catalog/` incluido.

---

## 🌍 Variables de entorno

- `LIBREFOLIO_DATA_DIR` mueve el directorio de datos de producción, y `LIBREFOLIO_TEST_DATA_DIR` el de pruebas. Una ruta relativa parte de la carpeta del proyecto.
- Con Docker Compose la ruta dentro del contenedor es fija: para guardar los datos en otro lugar del host, cambia el lado izquierdo del volumen `./LibreFolio-data:/app/backend/data/prod-docker` en `docker-compose.yml`.

Las demás variables, y el archivo `.env`, se describen en [Configuración](configuration.md).

---

## 💾 Copia de seguridad {: #backup }

### 📦 Copia de seguridad simple

La forma más sencilla de hacer una copia de seguridad de LibreFolio es copiar todo el directorio de datos:

```bash
# Stop the server first (to ensure database consistency)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

### 🐳 Copia de seguridad con Docker

Con Docker Compose, el directorio de datos es la carpeta `LibreFolio-data/` en el host, así que no se necesita ningún comando de copia de Docker. Detén el contenedor para obtener una copia consistente:

```bash
docker compose stop librefolio
cp -r ./LibreFolio-data/ /path/to/backup/librefolio-$(date +%Y%m%d)/
docker compose start librefolio
```

??? tip "🔄 Copia de seguridad de la base de datos sin detener el servidor"

    La copia de seguridad en línea de SQLite hace una copia consistente mientras el servidor está en ejecución. Necesita la herramienta `sqlite3`:

    ```bash
    sqlite3 backend/data/prod/sqlite/app.db ".backup '/path/to/backup/app.db'"
    ```

    Con Docker, la base de datos es `./LibreFolio-data/sqlite/app.db`. Esto copia solo la base de datos: copia las carpetas de abajo como de costumbre.

### ✅ Qué incluir en la copia de seguridad

Como mínimo, haz copia de seguridad de:

1. **`sqlite/app.db`** — Todos tus datos (usuarios, transacciones, configuración, tipos de cambio)
2. **`custom-uploads/`** — Archivos subidos por el usuario (avatares, documentos)
3. **`broker_reports/`** — Los informes del bróker originales, por si necesitas importarlos de nuevo
4. **`scenario_catalog/`** — Tus propios escenarios de estrés, si has añadido alguno

Si el almacenamiento es limitado, `sqlite/app.db` por sí solo conserva todos los datos estructurados: los archivos y los informes se pueden volver a subir si aún los tienes.
