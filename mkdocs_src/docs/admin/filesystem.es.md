# 📂 Estructura del sistema de archivos

LibreFolio guarda todo lo que almacena en un único **directorio de datos**: la base de datos, los archivos subidos, los informes del bróker, los registros y la clave de instancia. Su estructura es todo lo que necesita saber para las copias de seguridad y el mantenimiento.

| Instalación | Directorio de datos |
| --- | --- |
| Host (Pipenv) | `backend/data/prod/` en la carpeta del proyecto, o la ruta indicada en `LIBREFOLIO_DATA_DIR` |
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
│   ├── 💾 backups/                   # Backups kept by LibreFolio, one folder each
│   ├── 🎭 scenario_catalog/          # Optional: your own stress scenarios
│   ├── 🗄️ cache/                     # Safe to delete: PDF preview fonts, fetched again
│   ├── 🔐 secrets/                   # Created when LibreFolio first needs the key
│   │   └── 🔑 instance.key           # The instance key: back it up, never change it
│   └── 📋 scheduler_state.json       # Scheduled syncs: last run, pending retry
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
- 📎 `app.db-wal` y `app.db-shm` son archivos de trabajo de SQLite (modo WAL), normales mientras el servidor está en ejecución: nunca copie `app.db` solo con el servidor en marcha.
- 🔒 `app.db.post-migration.lock` es un archivo vacío que se usa al iniciar: déjelo en su sitio. Un archivo llamado `app.db.pre-<fix>-<UTC time>.bak` es una copia que se conserva después de que falle una [corrección posterior a la migración](cli_tools.md#post-migration-fixes): elimínelo cuando ya no lo necesite.

### 🖼️ `custom-uploads/`

Archivos subidos en la aplicación, como los de la página **Archivos**, y los avatares predeterminados. Cada archivo tiene un nombre aleatorio y un archivo `.json` junto a él que lo describe: mantenga juntos ambos archivos.

### 📊 `broker_reports/`

Los informes del bróker subidos para su importación, en una carpeta `broker_<id>/` por cada bróker:

- **📥 `uploaded/`** — pendientes de lectura
- **✅ `parsed/`** — leídos correctamente
- **❌ `failed/`** — no se pudieron leer; se conservan para que pueda comprobar por qué

Un informe pasa de `uploaded/` a `parsed/` o `failed/`, así que su archivo original siempre está en una de las tres.

### 📝 `logs/`

- 📄 `librefolio.log` contiene un registro JSON por línea; el servidor también imprime el registro en su consola.
- 🗓️ Cada lunes (UTC), el archivo se archiva y se comprime (`.gz`); se conservan los últimos 52 archivos, un año.
- 🎚️ `LOG_LEVEL` en `.env` determina cuánto se escribe (valor predeterminado: `INFO`).

??? info "📶 Niveles de registro — qué registra cada uno"

    Cada nivel registra también todos los niveles más graves.

    | Nivel | Qué registra |
    |-------|-----------------|
    | 🔬 `TRACE` | Datos granulares de alta frecuencia: tipos de cambio individuales procesados, puntos de precio por activo |
    | 🐛 `DEBUG` | Detalles internos de funcionamiento: qué proveedor se usó, resultados intermedios, decisiones algorítmicas |
    | ℹ️ `INFO` *(predeterminado)* | Operaciones significativas del usuario: sincronización completada, importación, inicio de sesión, recurso creado/eliminado |
    | ⚠️ `WARNING` | Anomalías recuperables: activación de fallback, faltan datos opcionales, modo degradado |
    | ❌ `ERROR` | Errores gestionados: operaciones fallidas, corrupción de datos, proveedor inaccesible |
    | 💀 `CRITICAL` | Errores fatales que detienen el proceso |

    - **Producción**: `LOG_LEVEL=INFO` — señal limpia, sin ruido
    - **Solución de problemas**: `LOG_LEVEL=DEBUG` — ver qué está decidiendo el sistema
    - **Depuración profunda de FX/precios**: `LOG_LEVEL=TRACE` — ver cada punto de datos individual

**Lectura del registro.** Cada línea que escribe LibreFolio es un objeto JSON: el mensaje está en `event`, el nivel en `level`, la hora (UTC) en `timestamp` y la traza de un error en `exception`. Cada línea escrita mientras el servidor atiende una solicitud lleva el `request_id` de esa solicitud. Cuando algo falla, ese mismo id llega al navegador: en el encabezado `X-Request-Id` de la respuesta, en el cuerpo de un error del servidor y en la línea `[API]` que la aplicación web escribe en la consola del navegador (herramientas de desarrollo, **Consola**). Pida ese id a la persona que informe del error y, después, lea sus líneas con [jq](https://jqlang.org/) desde la carpeta `logs/`:

```bash
# Every line of one request
jq -cR 'fromjson? | select(.request_id == "3f2a9c0d41b7e865")' librefolio.log

# The errors, each followed by its traceback
jq -rR 'fromjson? | select(.level == "ERROR" or .level == "CRITICAL") | "\(.timestamp) \(.request_id // "-") \(.event)", (.exception // empty)' librefolio.log
```

`fromjson?` omite las pocas líneas que no son JSON, como las de las bibliotecas que usa LibreFolio. Para una semana archivada, descomprímala sobre la marcha: `gzip -dc librefolio.log.2026-10-12.gz | jq -cR …`. Una línea sobre una solicitud fallida indica su método y su ruta, nunca su cadena de consulta, sus encabezados ni su cuerpo.

### 🗄️ `cache/`

Copias que LibreFolio puede volver a obtener. Actualmente contiene `pdf-fonts/`, las fuentes chinas, japonesas y coreanas que la vista previa de PDF necesita para un PDF que las utilice y que se conservan tras la primera descarga: consulte [La Content-Security-Policy](configuration_security.md#csp). Borrarla no supone perder nada y no forma parte de una [copia de seguridad](backup_restore.md).

### 🔐 `secrets/`

- 🔑 `instance.key` contiene la [clave de instancia](configuration_secrets.md#instance-key), el secreto a partir del cual LibreFolio deriva sus claves de cifrado. LibreFolio la crea la primera vez que necesita la clave. A partir de entonces, la ausencia de `instance.key` se interpreta igual que un primer uso: LibreFolio crea una clave nueva y lo que cifraba la anterior ya no se puede leer.
- 🔒 Solo el usuario que ejecuta LibreFolio puede abrir la carpeta y el archivo: la carpeta tiene permisos `0700` y el archivo, `0600`. Manténgalos así y con ese usuario como propietario: de lo contrario, el [registro de inicio](configuration_security.md#startup-checks) mostrará una advertencia, o un error cuando LibreFolio no pueda abrirlos.
- ⛔ Nunca edite, reemplace ni elimine el `instance.key` en uso: lo que se cifró con él ya no se podría leer. Si está dañado, o si LibreFolio ya ha sustituido una clave perdida por una nueva, detenga LibreFolio y restaure su copia antes de que alguien vuelva a introducir un secreto de plugin: consulte [La clave de instancia](configuration_secrets.md#instance-key).
- ♻️ Cuando restaure el directorio de datos, vuelva a colocar `secrets/` con él antes de iniciar LibreFolio de nuevo. Nunca inicie LibreFolio con datos restaurados sin su `secrets/`.
- ⚙️ Cuando la clave proviene de `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`, LibreFolio no usa esta carpeta.

🔗 Para desarrolladores: [El directorio de datos en disco](../developer/architecture/database/index.md#data-directory) — cada archivo, su formato y el código que lo escribe, incluido `scenario_catalog/`.

---

## 🌍 Variables de entorno

- `LIBREFOLIO_DATA_DIR` cambia la ubicación del directorio de datos de producción, y `LIBREFOLIO_TEST_DATA_DIR`, la del de pruebas. Una ruta relativa parte de la carpeta del proyecto.
- Con Docker Compose, la ruta dentro del contenedor es fija: para guardar los datos en otro lugar del host, cambie el lado izquierdo del volumen `./LibreFolio-data:/app/backend/data/prod-docker` en `docker-compose.yml`.

Las demás variables, y el archivo `.env`, se describen en [Configuración](configuration.md).

---

## 💾 Copia de seguridad {: #backup }

La forma recomendada es un archivo de copia de seguridad, creado mientras LibreFolio sigue en ejecución: consulte [Copia de seguridad, restauración y traslado de su instancia](backup_restore.md). Desde la línea de comandos, `./dev.py backup create` escribe un único archivo zip de la base de datos, los archivos subidos, los informes del bróker y sus propios escenarios de estrés; de forma predeterminada, en una carpeta propia dentro de la carpeta `backups/` del directorio de datos: consulte [Copia de seguridad de la instancia](cli_backup.md#backup) y [Copia de seguridad con Docker](cli_backup.md#backup-docker) para ver el comando en el contenedor. Omite `secrets/`, que debe respaldar aparte como se explica en [Qué hay que respaldar](#what-to-back-up), a menos que la haga [segura](backup_restore.md#secure) (`--encrypt`): un archivo seguro incluye la clave de instancia que generó LibreFolio. Copiar el directorio de datos a mano, como se muestra a continuación, es la alternativa.

### 📦 Copia de seguridad sencilla

La forma más sencilla de hacer una copia de seguridad de LibreFolio es copiar todo el directorio de datos:

```bash
# Stop the server first (to ensure database consistency)
cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
```

Esta copia, al igual que la de Docker que aparece más abajo, también incluye `backups/`, con todas las copias de seguridad que LibreFolio guarda allí ([Copias de seguridad conservadas en el servidor](backup_restore.md#kept-backups)): elimine antes las que ya no necesite, configure la [limpieza automática](backup_restore.md#backup-cleanup) o deje fuera esa carpeta.

### 🐳 Copia de seguridad con Docker

Con Docker Compose, el directorio de datos es la carpeta `LibreFolio-data/` del host, así que no hace falta ningún comando de Docker para copiar. Detenga el contenedor para obtener una copia coherente:

```bash
docker compose stop librefolio
cp -r ./LibreFolio-data/ /path/to/backup/librefolio-$(date +%Y%m%d)/
docker compose start librefolio
```

??? tip "🔄 Copia de seguridad de la base de datos sin detener el servidor"

    La copia de seguridad en línea de SQLite crea una copia coherente mientras el servidor se ejecuta. Necesita la herramienta `sqlite3`:

    ```bash
    sqlite3 backend/data/prod/sqlite/app.db ".backup '/path/to/backup/app.db'"
    ```

    Con Docker, la base de datos es `./LibreFolio-data/sqlite/app.db`. Esto copia solo la base de datos: copie las carpetas que se indican a continuación como de costumbre.

### ✅ Qué hay que respaldar {: #what-to-back-up }

Como mínimo, incluya en la copia de seguridad:

1. **`sqlite/app.db`** — Todos sus datos (usuarios, transacciones, configuración, tipos de cambio)
2. **`custom-uploads/`** — Archivos subidos por el usuario (avatares, documentos)
3. **`broker_reports/`** — Los informes del bróker originales, por si necesita importarlos de nuevo
4. **`scenario_catalog/`** — Sus propios escenarios de estrés, si ha añadido alguno
5. **`secrets/`** — La clave de instancia, si LibreFolio la ha creado

!!! warning "🔑 Mantenga `secrets/` junto con los datos y manténgala privada"

    Incluya `secrets/` en la copia de seguridad junto con la base de datos y mantenga las copias tan privadas como la propia base de datos. Nunca cambie ni elimine la clave de instancia una vez en uso: lo que se cifró con ella ya no se podría leer. Al restaurar, vuelva a colocar `secrets/` con los datos antes de iniciar LibreFolio.

    Solo el usuario que ejecuta LibreFolio puede abrir `secrets/`. Lo mismo ocurre con `backups/`, creada en la primera copia de seguridad, y `.restore/`, creada la primera vez que se comprueba un archivo para una restauración: LibreFolio crea ambas con permisos `0700` y los archivos de `backups/` con `0600`. Si `cp` muestra `Permission denied` en una de ellas, por ejemplo con Docker cuando su usuario del host no es el del contenedor, copie como root y conserve los permisos: `sudo cp -a`. Eliminar un archivo antiguo de `backups/` falla de la misma manera: use `sudo rm`.

Si el almacenamiento es limitado, conserve al menos `sqlite/app.db`, que contiene todos los datos estructurados, y la pequeña carpeta `secrets/`: los archivos y los informes se pueden volver a subir si aún los tiene.
