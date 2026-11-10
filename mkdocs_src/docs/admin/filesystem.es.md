# 📂 Estructura del sistema de archivos

LibreFolio guarda todo lo que almacena en un único **directorio de datos**: la base de datos, los archivos subidos, los informes de los brókers, los registros y la clave de instancia.
Conocerlo es todo lo que necesitas para las copias de seguridad y el mantenimiento.

**Dónde está.** En el resto de la página, `<data>` es esta carpeta:

| Instalación | `<data>` en el host | `<data>` dentro del contenedor |
| --- | --- | --- |
| Host (Pipenv) | `backend/data/prod/` en la carpeta del proyecto, o la ruta indicada en `LIBREFOLIO_DATA_DIR` | — |
| Docker Compose | `LibreFolio-data/` junto a `docker-compose.yml` | `/app/backend/data/prod-docker` |

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

| Carpeta | Qué contiene | Quién la escribe o la lee |
| --- | --- | --- |
| 🗃️ `sqlite/` | `app.db`: usuarios, brókers, transacciones, activos, precios, tipos de cambio, configuración | El servidor |
| 🖼️ `custom-uploads/` | Archivos subidos en la aplicación (como los de la página **Archivos**) y avatares predeterminados | La aplicación |
| 📊 `broker_reports/` | Los informes de los brókers subidos, una carpeta `broker_<id>/` por cada bróker | La importación |
| 📝 `logs/` | `librefolio.log` y sus archivos semanales | El servidor escribe, tú lees |
| 💾 `backups/` | Las copias de seguridad guardadas en el servidor, una carpeta cada una | Copia de seguridad y restauración |
| 🎭 `scenario_catalog/` | Tus propios escenarios de estrés, si has añadido alguno | Tú |
| 🗄️ `cache/` | Copias que se pueden volver a descargar (`pdf-fonts/`) | La vista previa de PDF |
| 🔐 `secrets/` | `instance.key`, la clave de instancia | LibreFolio, la primera vez que necesita la clave |
| 📋 `scheduler_state.json` | Última ejecución y reintento pendiente de las sincronizaciones programadas | Las sincronizaciones programadas |

---

## 📖 Qué hay en cada directorio

### 🗃️ `sqlite/`

- 📎 `app.db-wal` y `app.db-shm`: archivos de trabajo de SQLite (modo WAL), presentes mientras el servidor está en ejecución. Nunca copies `app.db` solo con el servidor en marcha.
- 🔒 `app.db.post-migration.lock`: archivo vacío que se usa al iniciar, déjalo en su sitio.
- 🗑️ `app.db.pre-<fix>-<UTC time>.bak`: copia que se conserva después de que falle una [corrección posterior a la migración](cli_tools.md#post-migration-fixes). Elimínala cuando ya no la necesites.

### 🖼️ `custom-uploads/`

Cada archivo tiene un nombre aleatorio y un `.json` junto a él que lo describe: mantén juntas las parejas.

### 📊 `broker_reports/`

Dentro de `broker_<id>/`, un informe pasa de `uploaded/` a `parsed/` o `failed/`: el original siempre está en una de las tres.

- **📥 `uploaded/`** — pendientes de lectura
- **✅ `parsed/`** — leídos correctamente
- **❌ `failed/`** — no se pudieron leer; se conservan para que puedas comprobar por qué

### 📝 `logs/`

- 📄 `librefolio.log`: un registro JSON por línea; el servidor también imprime el registro en la consola.
- 🗓️ Cada lunes (UTC), el archivo se archiva y se comprime (`.gz`); se conservan los últimos 52 archivos, un año.

**Cuánto se escribe.** En el **`.env`** de LibreFolio (valor predeterminado `INFO`):

```env
LOG_LEVEL=INFO
```

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

**Lectura del registro.** Cada línea es un objeto JSON: el mensaje está en `event`, el nivel en `level`, la hora (UTC) en `timestamp` y la traza de un error en `exception`.
Una línea escrita durante una solicitud lleva su `request_id`; cuando algo falla, ese mismo id llega al navegador: encabezado `X-Request-Id` de la respuesta, cuerpo del error del servidor, línea `[API]` en la consola del navegador (herramientas de desarrollo, **Consola**).

1. **Pide el id** a la persona que informa del error.
2. **En la carpeta `<data>/logs/`**, lee sus líneas con [jq](https://jqlang.org/):

    ```bash
    # Every line of one request
    jq -cR 'fromjson? | select(.request_id == "3f2a9c0d41b7e865")' librefolio.log

    # The errors, each followed by its traceback
    jq -rR 'fromjson? | select(.level == "ERROR" or .level == "CRITICAL") | "\(.timestamp) \(.request_id // "-") \(.event)", (.exception // empty)' librefolio.log
    ```

    Una línea de una solicitud fallida indica el método y la ruta, nunca la cadena de consulta, los encabezados ni el cuerpo.

- `fromjson?` omite las líneas que no son JSON, como las de las bibliotecas que usa LibreFolio.
- Semana archivada: `gzip -dc librefolio.log.2026-10-12.gz | jq -cR …`.

### 🗄️ `cache/`

`pdf-fonts/`: las fuentes chinas, japonesas y coreanas que la vista previa de PDF descarga en el primer uso cuando el PDF las utiliza, consulta [La Content-Security-Policy](configuration_security.md#csp).
Borrarla no supone perder nada; no forma parte de una [copia de seguridad](backup_restore.md).

### 🔐 `secrets/`

- 🔑 `instance.key` es la [clave de instancia](configuration_secrets.md#instance-key), a partir de la cual LibreFolio deriva sus claves de cifrado. Si falta, LibreFolio lo interpreta como un primer uso: crea una clave nueva y lo que se cifró con la anterior ya no se puede leer.
- 🔒 Carpeta `0700`, archivo `0600`, con el usuario que ejecuta LibreFolio como propietario. De lo contrario, el [registro de inicio](configuration_security.md#startup-checks) muestra una advertencia, o un error si el propio LibreFolio no puede abrirlos.
- ⛔ Nunca edites, reemplaces ni elimines el `instance.key` en uso. Si está dañado, o si LibreFolio ya ha sustituido una clave perdida por una nueva: detén LibreFolio y restaura tu copia antes de que alguien vuelva a introducir un secreto de plugin, consulta [La clave de instancia](configuration_secrets.md#instance-key).
- ♻️ Cuando restaures el directorio de datos, vuelve a colocar `secrets/` con él antes de iniciar LibreFolio. Nunca inicies LibreFolio con datos restaurados sin su `secrets/`.
- ⚙️ Con la clave en `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`, LibreFolio no usa esta carpeta.

🔗 Para desarrolladores: [El directorio de datos en disco](../developer/architecture/database/index.md#data-directory) — cada archivo, su formato y el código que lo escribe, incluido `scenario_catalog/`.

---

## 🌍 Variables de entorno

**Host, en el `.env` de LibreFolio**. Una ruta relativa parte de la carpeta del proyecto:

```env
LIBREFOLIO_DATA_DIR=/path/to/data        # production data directory
LIBREFOLIO_TEST_DATA_DIR=/path/to/test   # test data directory
```

**Docker Compose, en `docker-compose.yml`.** La ruta dentro del contenedor es fija: para guardar los datos en otro lugar del host, cambia el lado izquierdo del volumen.

```yaml
- ./LibreFolio-data:/app/backend/data/prod-docker
```

Las demás variables y el archivo `.env`: [Configuración](configuration.md).

---

## 💾 Copia de seguridad {: #backup }

La forma recomendada es un archivo de copia de seguridad, creado mientras LibreFolio sigue en ejecución: [Copia de seguridad, restauración y traslado de tu instancia](backup_restore.md).

- **Desde la línea de comandos**, `./dev.py backup create`: un único zip con la base de datos, los archivos subidos, los informes de los brókers y los escenarios de estrés, de forma predeterminada en una carpeta propia dentro de `<data>/backups/`. Consulta [Copia de seguridad de la instancia](cli_backup.md#backup) y, para el comando en el contenedor, [Copia de seguridad con Docker](cli_backup.md#backup-docker).
- El archivo **deja fuera `secrets/`**, que debes respaldar aparte ([Qué hay que respaldar](#what-to-back-up)), a menos que lo haga [seguro](backup_restore.md#secure) con `--encrypt`: un archivo seguro incluye la clave de instancia que generó LibreFolio.
- La alternativa es copiar el directorio de datos a mano, como se muestra a continuación.

### 📦 Copia de seguridad sencilla

1. **Detén el servidor**, para que la base de datos sea coherente.
2. **Desde la carpeta del proyecto**, copia todo el directorio de datos:

    ```bash
    # Stop the server first (to ensure database consistency)
    cp -r backend/data/prod/ /path/to/backup/librefolio-$(date +%Y%m%d)/
    ```

    Resultado: una copia completa y fechada de `<data>`.

Esta copia, al igual que la de Docker que aparece más abajo, también incluye `backups/`, con todas las copias de seguridad que LibreFolio guarda allí ([Copias de seguridad conservadas en el servidor](backup_restore.md#kept-backups)): elimina antes las que ya no necesites, configura la [limpieza automática](backup_restore.md#backup-cleanup) o deja fuera esa carpeta.

### 🐳 Copia de seguridad con Docker

El directorio de datos es la carpeta `LibreFolio-data/` del host: no hace falta ningún comando de Docker para copiar.

1. **Desde la carpeta de `docker-compose.yml`**, detén el contenedor, copia y reinicia:

    ```bash
    docker compose stop librefolio
    cp -r ./LibreFolio-data/ /path/to/backup/librefolio-$(date +%Y%m%d)/
    docker compose start librefolio
    ```

    Resultado: una copia coherente; el servidor permanece detenido solo mientras dura la copia.

??? tip "🔄 Copia de seguridad de la base de datos sin detener el servidor"

    La copia de seguridad en línea de SQLite crea una copia coherente mientras el servidor se ejecuta. Necesita la herramienta `sqlite3`:

    ```bash
    sqlite3 backend/data/prod/sqlite/app.db ".backup '/path/to/backup/app.db'"
    ```

    Con Docker, la base de datos es `./LibreFolio-data/sqlite/app.db`. Este comando copia solo la base de datos: copia las carpetas que se indican a continuación como de costumbre.

### ✅ Qué hay que respaldar {: #what-to-back-up }

Como mínimo, incluye en la copia de seguridad:

1. **`sqlite/app.db`** — Todos tus datos (usuarios, transacciones, configuración, tipos de cambio)
2. **`custom-uploads/`** — Archivos subidos por el usuario (avatares, documentos)
3. **`broker_reports/`** — Los informes originales de los brókers, por si necesitas importarlos de nuevo
4. **`scenario_catalog/`** — Tus propios escenarios de estrés, si has añadido alguno
5. **`secrets/`** — La clave de instancia, si LibreFolio la ha creado

!!! warning "🔑 Mantén `secrets/` junto con los datos y mantenla privada"

    Incluye `secrets/` en la copia de seguridad junto con la base de datos y mantén las copias tan privadas como la propia base de datos. Nunca cambies ni elimines la clave de instancia en uso: lo que se cifró con ella ya no se podría leer. Al restaurar, vuelve a colocar `secrets/` con los datos antes de iniciar LibreFolio.

    Solo el usuario que ejecuta LibreFolio puede abrir `secrets/`. Lo mismo ocurre con `backups/`, creada en la primera copia de seguridad, y `.restore/`, creada la primera vez que se comprueba un archivo para una restauración: LibreFolio crea ambas con permisos `0700` y los archivos de `backups/` con `0600`. Si `cp` muestra `Permission denied` en una de ellas, por ejemplo con Docker cuando tu usuario del host no es el del contenedor, copia como root y conserva los permisos: `sudo cp -a`. Eliminar un archivo antiguo de `backups/` falla de la misma manera: usa `sudo rm`.

Si el almacenamiento es limitado, conserva al menos `sqlite/app.db`, que contiene todos los datos estructurados, y la pequeña carpeta `secrets/`: los archivos y los informes se pueden volver a subir si aún los tienes.
