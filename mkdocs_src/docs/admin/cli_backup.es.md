# 💾 Herramientas de administración de CLI: Copias de seguridad

Esta página de la guía de comandos cubre `dev.py backup`: crear, comprobar y restaurar un archivo, seguir una restauración y trabajar con Docker.

El resto de la guía comienza en [Herramientas de línea de comandos](cli_tools.md).

---

## 💾 Hacer una copia de seguridad de la instancia {: #backup }

`backup create` coloca toda la instancia en un único zip, con el servidor en ejecución: base de datos, archivos subidos, informes del bróker, escenarios de estrés. Para copiar el directorio de datos manualmente, consulta [Copia de seguridad](filesystem.md#backup).

| Tarea | Comando |
| --- | --- |
| Crear un archivo | `backup create`; con `--encrypt`, un [archivo seguro](#backup-secure); con `--sealed` o `--recipient`, un [archivo sellado](#backup-sealed) para las copias de seguridad que se ejecutan solas |
| Comprobar un archivo y ver lo que contiene | `backup inspect` |
| Probar una restauración sobre una copia, sin tocar la instancia | `backup restore --dry-run` |
| Restaurar en el siguiente arranque del servidor | `backup restore` |
| Seguir o cancelar una restauración | `backup pending` |
| Volver a convertir un archivo seguro en su zip | `backup decrypt` |
| Generar la clave de un archivo sellado | `backup keygen` |

**Dónde se ejecutan los comandos:**

| Instalación | Dónde | Comando |
| --- | --- | --- |
| Host | Terminal del servidor, carpeta de LibreFolio | `pipenv run ./dev.py backup …` |
| Docker | Terminal del servidor, carpeta de `docker-compose.yml`: el comando se ejecuta dentro del contenedor | `docker compose exec librefolio python dev.py backup …`, con las rutas del contenedor: [Copias de seguridad con Docker](#backup-docker) |
| Un ordenador tuyo | `backup keygen`, y abrir un archivo sellado donde está la clave privada | [Un archivo sellado](#backup-sealed) |

Una ruta relativa (`-o`, archivos, archivos de contraseña) empieza en la raíz del proyecto, desde dondequiera que ejecutes el comando: prefiere rutas absolutas. `backup --test-db create` hace la copia de seguridad del directorio de datos de prueba: una opción de desarrollo.

### 📦 Crear un archivo

**Dónde: terminal del servidor, carpeta de LibreFolio** (Docker: [dentro del contenedor](#backup-docker)).

```bash
# Keep an archive in its own folder of <data dir>/backups/, and print its SHA-256
pipenv run ./dev.py backup create

# Copy it into another folder instead, which must already exist
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/

# Or give the archive a name of your own
pipenv run ./dev.py backup create -o /mnt/nas/librefolio/before-update.zip

# A secure archive (.lfbk): the password is asked twice
pipenv run ./dev.py backup create --encrypt -o /mnt/nas/librefolio/
```

Resultado: el archivo zip, en el lugar elegido con las opciones de abajo, y su suma de comprobación impresa.

| Opción | Efecto |
| --- | --- |
| ninguna | **El archivo se queda en el servidor**, en una carpeta propia de `backups/`: `backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip` (momento, origen `cli`, código corto). No se copia ni se mueve nada. Aparece en **Configuración › Administración › Copia de seguridad** y en la limpieza automática: [Copias de seguridad conservadas en el servidor](backup_restore.md#kept-backups) |
| `-o`, `--output PATH` | **El archivo se copia allí**, y no queda nada en `backups/`. Una carpeta existente: el archivo con su nombre predeterminado dentro. Cualquier otra ruta, incluso con una `/` final: el archivo de la copia, que no debe existir y nunca cambia de nombre; las carpetas que faltan se crean solo al mover, así que una copia de seguridad fallida no deja ninguna carpeta vacía. Se comprueba antes de que empiece la copia de seguridad: el comando debe poder escribir allí |
| `--encrypt` | [Archivo seguro](#backup-secure) `.lfbk`, contraseña pedida dos veces |
| `--password-file FILE`, `--password-stdin` | Archivo seguro con la contraseña tomada de un archivo o de la entrada estándar, sin `--encrypt` |
| `--recipient age1…`, `--sealed` | [Archivo sellado](#backup-sealed) `.tar`, sin contraseña |

Conviene saber:

- ✅ Termina con `✅ Backup written: <path>`, el tamaño y el tiempo empleado, `SHA-256: <checksum>`, las advertencias que haya y el recordatorio `🔒 The archive holds every user's data: keep it private.` (archivo seguro: `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.`). Sale con `0` cuando el archivo está donde pediste, advertencias incluidas; con `1` en caso contrario.
- 🟢 El servidor sigue funcionando, y escribiendo: la base de datos se copia con `VACUUM INTO` de SQLite, una instantánea consistente, y después la copia supera la comprobación de integridad y la comprobación de claves foráneas.
- 🏷️ El nombre procede del momento en que empieza la copia de seguridad, en UTC: `librefolio-backup-20261015-121500.zip`, `.lfbk` para un archivo seguro. En una carpeta de `--output` que ya contiene ese nombre, por ejemplo tras dos copias de seguridad en el mismo segundo: `librefolio-backup-20261015-121500-2.zip`, luego `-3`, y así sucesivamente. Un archivo nunca reemplaza a otro.
- 🧾 Tras la ruta, el comando imprime `SHA-256: <64 hexadecimal digits>`, la suma de comprobación del archivo: compárala con la del archivo una vez que esté en otro disco.
- 💽 **Espacio**: se comprueba antes de escribir, en `backups/` del directorio de datos, incluso con `-o`: aproximadamente el doble de la base de datos, más los archivos, más un pequeño margen. Insuficiente, o un disco o una cuota que se llenan durante la copia de seguridad → `❌ Backup failed (backup_no_space): not enough free space`. Con `-o` en otro disco, el espacio allí se comprueba una vez construido el archivo y conocido su tamaño.
- 🛟 Si el archivo terminado no puede ir a `-o` (apareció mientras tanto un archivo con ese nombre, carpetas que no se pueden crear, el otro disco lleno, un error de escritura) → se queda en `backups/` como archivo suelto: fuera de la lista de copias de seguridad conservadas, y la limpieza automática nunca lo elimina. El comando sale con `1`. Un movimiento que falla a mitad no deja ningún archivo parcial.
- 🚦 Una copia de seguridad a la vez: con otra en ejecución, el comando se detiene y te pide que lo intentes de nuevo cuando la otra haya terminado.
- 🔒 Sin contraseña, el archivo no está cifrado: se escribe con `0600`, legible y escribible solo por su propietario. Mantenlo, junto con cada copia, tan privado como el directorio de datos.
- 🗑️ Las copias de seguridad de `backups/` permanecen allí hasta que las elimines desde **Configuración › Administración › Copia de seguridad** o desde la carpeta, o hasta que la [limpieza automática](backup_restore.md#backup-cleanup) las elimine, excepto la más reciente. Los archivos sueltos `librefolio-backup-*.zip` de versiones anteriores nunca se tocan. `backups/` está en el disco de los datos: copia los archivos a otro disco, a un NAS o a una ubicación externa, o escríbelos allí directamente con `-o`.
- 🔗 Mantén `backups/` como una carpeta real, nunca un enlace a un NAS u otro disco: cada archivo se construye allí, incluso con `-o`. Un enlace, o un archivo, en su lugar → `❌ <data dir>/backups is not a plain folder (a link, or a file): …`.

??? note "⚠️ Advertencias y errores — qué significan los mensajes"

    **Advertencias**: el archivo se escribe de todos modos.

    - `The database failed its integrity check` o `The database has foreign-key violations`: la base de datos está en el archivo tal como está; `backup inspect` muestra el resultado de la comprobación.
    - `Left out (<n>): links, special files, files or folders that could not be read, or files removed during the backup`, seguido de las entradas, como máximo 50: no están en el archivo. Nunca se siguen los enlaces, incluso cuando toda una carpeta como `custom-uploads/` es un enlace a otro disco.
    - `The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`: un [archivo seguro](#backup-secure) sin la clave.

    **No donde pediste**: el archivo se escribe, código de salida `1`.

    - `⚠️ <reason>: the archive was written to <path> instead`, seguido de las líneas habituales: `-o` no pudo recibir el archivo, que está en `backups/` como archivo suelto, fuera de la lista de copias de seguridad conservadas. Muévelo donde quieras.
    - `❌ <reason>: the archive stays in <path>. Move it within the hour: the next backup after that removes it.`: `backups/` tampoco pudo recibirlo. Está en la carpeta de trabajo, dentro de `backups/.jobs/`, que elimina la primera copia de seguridad o el primer arranque de LibreFolio posterior a esa hora: sácalo de allí antes.

    **Errores**: no se escribe ningún archivo, código de salida `1`.

    - `❌ No data directory at <path>` o `❌ No database at <path>: nothing to back up`: el comando usa el [directorio de datos](filesystem.md) con el que está configurado LibreFolio; comprueba `LIBREFOLIO_DATA_DIR`.
    - `❌ <path> already exists: choose another name or folder`, `❌ <path> is not a folder: choose another path` (hay un archivo donde la ruta necesita una carpeta) o `❌ cannot write into <folder>: choose another folder, or run the command as a user who can`: `-o` no puede recibir el archivo. La copia de seguridad no ha empezado.
    - `❌ <data dir>/backups is not a plain folder (a link, or a file): …`: vuelve a convertir `backups/` en una carpeta real. `❌ The backup could not run in <data dir>/backups: <reason>`: no se puede preparar allí la carpeta de trabajo, por ejemplo porque el directorio de datos no es escribible.
    - `❌ Backup failed (backup_no_space): not enough free space`: espacio insuficiente al empezar, o un disco o una cuota que se llenaron durante la copia de seguridad, incluso en mitad de un archivo. Libera espacio en el disco del directorio de datos.
    - `❌ Backup failed (backup_failed): the cause is in the log above`: cualquier otro error, por ejemplo un archivo que falla mientras se copia al archivo (un error de lectura a mitad): parte de un archivo no se puede sacar de un zip, así que se detiene toda la copia de seguridad. Un archivo que falla antes de la copia se omite, en cambio, con la advertencia anterior.

### 🗃️ Dónde se guardan las copias de seguridad {: #backup-kept }

Tanto el comando como la aplicación dejan las copias de seguridad terminadas en `backups/`, una carpeta cada una: `librefolio-backup-<date>-<time>-<origin>-<id>`, origen `cli` para el comando y `ui` para la aplicación. `backups/.jobs/` solo contiene una copia de seguridad en curso o una que falló.

| Qué hacer con ellas | Dónde |
| --- | --- |
| Listarlas, descargarlas, eliminarlas | **Configuración › Administración › Copia de seguridad**, o **Archivos › Copias de seguridad** (solo administradores): [Copias de seguridad conservadas en el servidor](backup_restore.md#kept-backups) |
| Eliminar las más antiguas por sí solas, nunca la más reciente: tamaño total y antigüedad máxima, ambos opcionales | [Limpieza automática](backup_restore.md#backup-cleanup). El comando las aplica después de cada copia de seguridad, igual que la aplicación |
| Comprobar o restaurar un archivo conservado desde la línea de comandos | `backup inspect` o `backup restore`, con la ruta que imprimió `backup create` |

💽 Una copia en el disco de tus datos no es una copia de seguridad real: copia el archivo a otro disco, o usa `--output`.

### 🔐 Un archivo seguro {: #backup-secure }

**Dónde: terminal del servidor, carpeta de LibreFolio** (Docker, desde cron: `-T` y un secreto, [más abajo](#backup-docker)).

```bash
# The password is asked twice at the terminal
pipenv run ./dev.py backup create --encrypt

# The password read from a file that holds it alone (with Docker, a secret: /run/secrets/…)
pipenv run ./dev.py backup create --password-file ~/.librefolio-backup-password

# The password read from the standard input, such as from a password manager
pass show librefolio/backup | pipenv run ./dev.py backup create --password-stdin
```

Resultado: `librefolio-backup-20261015-121500.lfbk`, el zip que `backup create` escribe sin contraseña, cifrado con la tuya.

Solo esa contraseña lo abre, y LibreFolio no recupera una contraseña perdida: el comando termina como una copia de seguridad normal, con el recordatorio `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.` Qué protege y qué no: [Copias de seguridad seguras](backup_restore.md#secure).

**De dónde viene la contraseña**: nunca de la línea de comandos, que cualquier usuario del servidor puede leer (`ps`) y que el shell guarda en su historial. No existe `--password`, y las opciones de contraseña no tienen forma abreviada.

| Opción | La contraseña |
| --- | --- |
| `--encrypt` solo | Escrita en el terminal, dos veces |
| `--password-file FILE` | El texto del archivo, sin la marca de orden de bytes al principio ni los saltos de línea al final, como en [Secretos en archivos](configuration_secrets.md#secret-files): un archivo que contiene solo la contraseña, como un secreto de Docker. Una ruta relativa empieza en la raíz del proyecto |
| `--password-stdin` | Una línea de la entrada estándar, sin su salto de línea, como la de una tubería. En un terminal se pide como sin la opción, sin mostrarse, dos veces para `create`: escrita allí como una línea, se mostraría |

`--password-file` y `--password-stdin` se excluyen mutuamente, y cualquiera de las dos hace que el archivo sea seguro sin `--encrypt`.

- 📄 **Un archivo en el que el comando pueda confiar.** El archivo de `--password-file`, como el de `--instance-key-file` ([La clave de instancia de otra instalación](#backup-restore-instance-key)), debe ser un archivo regular. Un FIFO, una carpeta o un dispositivo se rechazan de inmediato, sin leerlos: `❌ password file: <path> is not a regular file (password_unreadable)`. Como root, por ejemplo con `docker compose exec`, también se rechaza una ruta que pasa por un enlace dentro del directorio de datos (el usuario de LibreFolio podría haberlo apuntado a un archivo que solo root lee): `❌ password file: <path> goes through a link inside the data directory: give the file itself, from outside it (password_unreadable)`. Un enlace en otro lugar se sigue, como los secretos de Kubernetes; los secretos de Docker y Compose son archivos normales. Para `--instance-key-file`, las mismas líneas empiezan con `instance key file:` y terminan con `(instance_key_unreadable)`.
- 📏 **Las reglas**: como para la contraseña de una cuenta, al menos 12 caracteres con una letra mayúscula, una minúscula, un dígito y un símbolo (clases contadas en Unicode, como para las cuentas), como máximo 1024. Se comprueban antes de que empiece la copia de seguridad: una contraseña que incumpla una regla no escribe nada.
- 🗝️ **La clave de instancia**: `secrets/instance.key` está en el archivo cuando LibreFolio generó la clave y puede usarla; nunca una clave de `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`. Una clave generada que no se puede usar (dañada, fuera de alcance, de más de 4096 bytes, más de lo que una restauración vuelve a leer) se omite con `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`; el archivo se escribe de todos modos.
- 💽 **Espacio**: el cifrado (`… encrypting`, tras las fases habituales) escribe el `.lfbk` junto al zip en `backups/`: allí se necesita de nuevo el tamaño del zip, más 64 MB, de lo contrario `❌ Backup failed (backup_no_space): not enough free space`. El zip se elimina una vez cifrado, o si la copia de seguridad falla. Tras una interrupción brusca (corte de energía, `kill -9`), el siguiente arranque de LibreFolio da esa copia de seguridad por interrumpida y elimina lo que queda en `backups/.jobs/`, incluidos el zip y la copia de la base de datos.

??? note "❌ Errores de contraseña — qué significan los mensajes"

    No se escribe nada, código de salida `1`.

    - `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`: `--encrypt` sin un terminal donde preguntar, por ejemplo en cron. Contraseña vacía escrita en el terminal: `❌ No password was typed (password_required)`; línea vacía por una tubería con `--password-stdin`: `❌ The standard input carried no password (password_required)`.
    - `❌ The two passwords differ (password_mismatch)`.
    - `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: <rules>)`: los códigos de las reglas incumplidas, en este orden: `min_length`, `uppercase`, `lowercase`, `digit`, `special`.
    - `❌ The password is longer than 1024 characters (password_too_long)`.
    - `❌ password file: <path> does not exist (password_unreadable)`, o `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it` («Un archivo en el que el comando pueda confiar» más arriba).

    Ambas opciones de contraseña a la vez, o una opción que no existe como `--password`, detienen el comando antes de que empiece, con la línea de uso y el código de salida `2`.

### 🗂️ Qué contiene el archivo

El archivo tiene la estructura del directorio de datos y solo contiene:

| Entrada | Qué es |
| --- | --- |
| `manifest.json` | La descripción del archivo, más abajo |
| `sqlite/app.db` | La copia de la base de datos |
| `custom-uploads/` | Los archivos subidos en la aplicación |
| `broker_reports/` | Los informes del bróker |
| `scenario_catalog/` | Tus propios escenarios de estrés, si añadiste alguno |
| `secrets/instance.key` | Solo en un [archivo seguro](#backup-secure), cuando LibreFolio generó la clave de instancia: su texto, fuera de la lista de archivos del manifiesto. Una restauración lo lee para volver a cifrar los secretos guardados, y nunca lo descomprime |

Todo lo demás queda fuera: `secrets/` (pero `secrets/instance.key` en un archivo seguro), `logs/`, `scheduler_state.json`, la carpeta `backups/`, el marcador `.librefolio-production-data` y los archivos de trabajo de SQLite junto a la base de datos: `app.db-wal`, `app.db-shm`, `app.db.post-migration.lock` y las copias `.bak` de las [reparaciones posteriores a las migraciones](cli_tools.md#post-migration-fixes). La copia de la base de datos ya contiene lo que esperaba en `app.db-wal`. Los enlaces simbólicos y los archivos especiales nunca se siguen ni se archivan.

!!! warning "🔑 La clave de instancia está solo en un archivo seguro"

    Un archivo en claro deja fuera `secrets/`, con la [clave de instancia](configuration_secrets.md#instance-key). Haz una copia de seguridad de ella por separado ([Estructura del sistema de archivos → Qué hay que respaldar](filesystem.md#what-to-back-up)) y mantén la copia tan privada como los archivos. Antes de iniciar LibreFolio con los datos de un archivo en claro, vuelve a poner `secrets/` junto a ellos: sin su clave, lo que LibreFolio cifró ya no se puede leer. Un [archivo seguro](#backup-secure) contiene la clave que generó LibreFolio, nunca una de `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`: guarda esa donde la estableciste. Con una copia de la clave, una restauración en otra instalación sigue leyendo los secretos guardados de un archivo en claro: [La clave de instancia de otra instalación](#backup-restore-instance-key).

??? info "📋 `manifest.json` — qué registra"

    - el formato, `librefolio-backup`, y su versión;
    - la versión de LibreFolio que creó el archivo, cómo (`cli` para este comando, `ui` para la interfaz web) y cuándo, en UTC;
    - la base de datos: la revisión de migración (Alembic), el resultado de la comprobación de integridad de SQLite, el número de violaciones de claves foráneas, las filas de cada tabla y los totales de control del libro mayor, el efectivo de cada bróker en cada moneda y la cantidad de cada posición (un archivo creado antes de que existieran no tiene ninguno);
    - cada entrada, la base de datos primero, con ruta, tamaño y SHA-256;
    - si el archivo contiene la clave de instancia, y el SHA-256 de esa entrada: solo un archivo seguro la contiene.

### 🔍 Comprobar un archivo

**Dónde: cualquier instalación**, con el servidor en ejecución o detenido; no necesita directorio de datos, excepto para un archivo seguro (más abajo). Docker: [dentro del contenedor](#backup-docker), con la ruta del contenedor.

```bash
# Check every entry against the manifest, and show what the archive holds
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip

# Faster: compare the entry names with the manifest, without reading the entries
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --no-verify
```

Resultado: el informe del archivo, y `✅ Every entry matches the manifest` una vez comparados con el manifiesto el tamaño y el SHA-256 de cada entrada.

| Opción | Efecto |
| --- | --- |
| `--no-verify` | Compara solo los nombres de las entradas, sin leerlas: `ℹ️ The entry names match the manifest; their contents were not read (--no-verify)` |
| `--password-file FILE`, `--password-stdin` | La contraseña de un archivo seguro, de las mismas fuentes que `create` ([Un archivo seguro](#backup-secure)); un `.zip` las ignora |
| `--identity-file FILE` | La clave privada de un [archivo sellado](#backup-sealed) |

- 📋 El informe: quién creó el archivo y cuándo (`Made by LibreFolio <version> (cli) on <date> UTC`), la revisión de migración de la base de datos, su tamaño y su comprobación de integridad, filas y tablas, número y tamaño de los archivos, si se incluye la clave de instancia.
- 🔐 Un archivo seguro, reconocido por sus primeros bytes sea cual sea su nombre, pide primero la contraseña, una sola vez. Se descifra (`🔓 Decrypting <path>`) en una carpeta privada `.decrypt-…` dentro de `backups/` del directorio de datos, que se elimina al final aunque el comando falle: hace falta ese directorio, y espacio para el archivo descifrado, aproximadamente el tamaño del `.lfbk`. Una carpeta que deja un `inspect` interrumpido bruscamente (corte de energía, `kill -9`) la elimina el siguiente `inspect`, o el siguiente arranque de LibreFolio, cuando tiene una hora: una más reciente puede ser de otro `inspect` que sigue en ejecución. El informe añade `Secure backup: decrypted with its password`. Contraseña incorrecta: `❌ The password does not open this backup (wrong_password)`; `password_required`, `envelope_damaged` y `envelope_unsupported` figuran entre los rechazos de [Probar una restauración sobre una copia](#backup-restore-dry-run).
- ❌ Sale con `1` cuando faltan entradas, difieren del manifiesto o no figuran en él (las cinco primeras de cada tipo), y cuando el archivo no es un archivo legible: el mensaje termina con un código, como `archive_unreadable` (no es un zip, o está cortado), `manifest_missing`, `manifest_unknown_format` (no es una copia de seguridad de LibreFolio) o `manifest_newer_format` (creado por un LibreFolio más reciente: compruébalo con esa versión o una posterior).

### 🔏 Un archivo sellado {: #backup-sealed }

Un archivo sellado es un `.tar` cuya contraseña genera LibreFolio y cifra para una o dos claves públicas age: solo la clave privada correspondiente lo abre, y el servidor que lo creó no puede. Está pensado para las copias de seguridad que se ejecutan solas, por ejemplo cada noche desde cron. Qué contiene, cómo guardar y cambiar la clave: [Copias de seguridad selladas](backup_sealed.md#sealed).

1. **En un ordenador tuyo, no en el servidor**: la clave privada no debe quedarse en el servidor.

    ```bash
    # A key pair: the private key into a file of its own (0600, never over a file), the public key printed
    pipenv run ./dev.py backup keygen --identity-file ~/librefolio-backup-key.txt
    ```

    Resultado: la clave privada en el formato de `age-keygen` (`# created:`, `# public key: age1…`, luego `AGE-SECRET-KEY-1…`), legible solo por su propietario, nunca sobre un archivo existente (`❌ <path> already exists: a key file is never written over`); después `🔑 Public key, for --recipient or LIBREFOLIO_BACKUP_RECIPIENTS:` y la línea `age1…`.

2. **Terminal del servidor, carpeta de LibreFolio** (Docker: `docker compose exec -T librefolio python dev.py backup create --sealed`).

    ```bash
    # A sealed archive for that public key (twice --recipient while a key is being changed)
    pipenv run ./dev.py backup create --recipient age1…

    # The same, for the keys of LIBREFOLIO_BACKUP_RECIPIENTS
    pipenv run ./dev.py backup create --sealed
    ```

    Resultado: `librefolio-backup-20261015-121500.tar`, con las reglas habituales de `-o` y de los nombres; tras las fases de un archivo seguro, `… sealing`, y después `🔏 Sealed for 1 key: only the matching private key opens its password, and this server cannot.`

3. **Donde está la clave privada**: compruébalo, restáuralo o descífralo con `--identity-file`.

    ```bash
    # Check, restore or decrypt it where the private key is
    pipenv run ./dev.py backup inspect librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt
    pipenv run ./dev.py backup restore librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt --dry-run
    pipenv run ./dev.py backup decrypt librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt -o backup.zip
    ```

    Resultado: `🔏 Sealed backup <path>: its password opened with <key file>`, y después el comando continúa como con un archivo seguro y su contraseña.

| Opción | Efecto |
| --- | --- |
| `--recipient age1…` | Sella para esa clave; dos veces para dos claves, mientras se cambia una clave |
| `--sealed` | Sella para las claves de `LIBREFOLIO_BACKUP_RECIPIENTS` ([Variables de entorno](configuration.md)); sin `--recipient` |
| `--identity-file FILE` | Abre un `.tar` para `inspect`, `restore` y `decrypt`: un archivo de clave como lo escribe `age-keygen`, leído antes de cualquier cambio de usuario, como `--password-file`: funciona un secreto de Docker |

Conviene saber:

- 🔑 **Sin contraseña que dar**: `--sealed` y `--recipient` van sin `--encrypt`, `--password-file` y `--password-stdin`; de lo contrario el comando se detiene antes de escribir nada. No necesita terminal: se ejecuta desde cron tal cual.
- 🗝️ **Nunca la clave de instancia**, ni siquiera una que generó LibreFolio: a diferencia de un [archivo seguro](#backup-secure), un archivo sellado deja fuera `secrets/instance.key`.
- 💽 **Espacio**: sellar escribe el `.tar` junto al `.lfbk`, así que la carpeta de trabajo de `backups/` necesita de nuevo el tamaño del `.lfbk`, más 64 MB, de lo contrario `backup_no_space`.
- 🔓 **Cómo se abre**: el comando comprueba el `.tar` y su manifiesto, abre la contraseña con la clave, la comprueba con `backup.lfbk`, y después copia `backup.lfbk` en una carpeta privada de la carpeta temporal del sistema, que se elimina al final.
- ❌ Un `.tar` sin `--identity-file` se detiene con `sealed_backup_needs_key`; `--identity-file` con cualquier otro archivo, con `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one`.
- 🧾 **Los rechazos**, al final del mensaje: `sealed_identity_invalid` (el archivo no contiene ninguna clave age, o no se puede leer), `sealed_no_identity` (ninguna clave del archivo abre la contraseña), `sealed_tar_invalid` (no contiene los tres archivos de un archivo sellado, en orden, como archivos ustar normales), `sealed_manifest_invalid` (su `manifest.json` no lo describe), `sealed_password_invalid` (lo que abrió la clave no es una contraseña escrita por LibreFolio), y después los de un archivo seguro: `wrong_password` (no abre `backup.lfbk`) y `envelope_damaged`. Cada mensaje, con lo que hay que hacer: [Crear o abrir una copia de seguridad sellada](backup_moving.md#sealed-problems).

### 🧪 Probar una restauración sobre una copia {: #backup-restore-dry-run }

**Dónde: terminal del servidor, carpeta de LibreFolio** (Docker: [dentro del contenedor](#backup-docker)). Funciona en cualquier instalación con directorio de datos, incluida una nueva: nunca usa la base de datos de la instancia, y el servidor puede seguir en ejecución.

```bash
# Check an archive for a restore, on a copy: the instance stays as it is
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --dry-run
```

Resultado: el archivo se descomprime en una copia, `.restore/stage/<id>/` en el directorio de datos, se actualiza y se comprueba; después el informe dice lo que haría una restauración y la copia se elimina.

- ✅ Termina con `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.`, código de salida `0`; `1` cuando se rechaza el archivo o se bloquea la restauración: una línea con un código entre paréntesis, como `❌ The file is not a LibreFolio backup (not_a_backup)`, y no queda nada de la copia.
- ♻️ Sin `--dry-run`, la misma comprobación es la primera mitad de una restauración: [Restaurar un archivo](#backup-restore).
- 🔐 Un [archivo seguro](#backup-secure) pide primero la contraseña, como hace `inspect`, y se descifra en la copia como `.restore/stage/<id>/archive.zip`, que se elimina una vez descomprimido. Una comprobación interrumpida bruscamente deja ese archivo, o su parte `archive.zip.part`: el siguiente arranque de LibreFolio lo elimina.

**Qué comprueba**, en seis pasos, deteniéndose en el primero que rechaza el archivo (`… decrypting` para un archivo seguro, `… checking`, `… unpacking`, `… upgrading`, `… verifying`):

1. **Un archivo de LibreFolio**, con su `manifest.json`: un directorio de datos comprimido a mano no lo es. Cada entrada, antes de escribir un solo byte: listada por el manifiesto (o anunciada, para la clave de instancia), un archivo normal (no una carpeta, un enlace ni una entrada cifrada), nombre único incluso sin distinguir mayúsculas de minúsculas, el tamaño del manifiesto; el conjunto cabe en el espacio libre.
2. **Descomprimido**: cada entrada en un archivo nuevo de la copia, nunca a través de un enlace ni sobre otro archivo, SHA-256 comparado con el manifiesto. El esquema de la base de datos se lee sin ejecutar nada de él: un disparador, una vista o una tabla virtual, que LibreFolio nunca crea, hacen que se rechace el archivo (`database_foreign_objects`).
3. **La revisión decide**: la revisión de migración (Alembic), del manifiesto y confirmada por la base de datos.
    - la misma que la de este LibreFolio: se restaura tal cual;
    - más antigua: la copia se actualiza a la revisión de este LibreFolio, en un proceso aparte, detenido al cabo de una hora;
    - desconocida, lo más probable es que más reciente: `revision_unknown`. Actualiza primero LibreFolio: una base de datos nunca se degrada.

    Después las [reparaciones posteriores a las migraciones](cli_tools.md#post-migration-fixes) se ejecutan sobre la copia, como en cada arranque.

4. **Comprobada antes y después**: antes de la actualización la copia supera la comprobación de integridad de SQLite, contiene exactamente las filas que contó el manifiesto y ningún texto que no sea UTF-8 (LibreFolio no escribe ninguno, y el servidor no podría leerlo); después, supera de nuevo la comprobación de integridad. Las filas modificadas por una migración y las referencias rotas (claves foráneas), conservadas tal cual, son advertencias, no rechazos.
5. **Administradores**: sin un administrador activo en la copia de seguridad, la restauración se bloquea: nadie podría gestionar la instancia después.
6. **Secretos guardados**: la instancia conserva su propia [clave de instancia](configuration_secrets.md#instance-key). Los secretos de plugins guardados (como la clave de API de una fuente de datos) se vuelven a cifrar en la copia con ella cuando el archivo contiene la clave que los cifró, o la das con `--instance-key-file` ([La clave de instancia de otra instalación](#backup-restore-instance-key)); los demás se cuentan, para volver a introducirlos tras la restauración. Una copia sin secretos ni siquiera lee la clave de esta instancia.

**El informe**:

- 📦 Quién creó el archivo y cuándo (`Made by LibreFolio <version> (<how>) on <date> UTC`), y lo que hace una restauración con la base de datos: `this LibreFolio's own: restored as it is`, o `upgraded on the copy to <revision> (<n> migrations)`, y después cada migración con la primera línea de su descripción.
- 🩹 Las reparaciones posteriores a las migraciones que cambiaron algo en la copia, si las hay.
- 🔢 Filas, tablas y tamaño de la base de datos, y después las tablas cuyas filas cambiaron con la actualización, como `<table> (<before> → <after>)`, con `—` para una tabla que no existía.
- 📁 Número y tamaño de los archivos; `Secure backup: decrypted with its password` para un archivo seguro; `Instance key: included` o `Instance key: not included`, o `Instance key: not included; given with --instance-key-file` con esa opción; las claves guardadas de los proveedores de datos: `Saved provider keys: <n> re-encrypted with this instance's key`, y `⚠️ <n> saved provider keys cannot be read with this instance's key: enter them again after the restore` para las que la clave del archivo, o la clave dada, no leyó, o cuando no hay clave.
- ⚖️ Los totales de control del libro mayor: el efectivo de cada bróker en cada moneda y la cantidad de cada posición, solo a partir de las transacciones, sin precio, tipo de cambio, coste ni fecha. Registrados en el manifiesto al crear el archivo, y leídos de nuevo en la copia una vez actualizada. Una diferencia es una advertencia, nunca un rechazo: una migración puede corregir datos. Una de estas líneas:
    - `Ledger totals: the same as when the backup was made`;
    - `⚠️ Ledger totals differ from the backup's (<n> lines):`, y después las líneas que difieren, primero el efectivo, como máximo 20: `broker <id>, <currency> cash: <before> → <after>` o `broker <id>, asset <id> quantity: <before> → <after>`, con el importe de la copia de seguridad antes de la flecha y el de la copia después, `—` para cero. `… and <n> more` cuenta las líneas omitidas;
    - `Ledger totals: not recorded in this archive`: un archivo de un LibreFolio anterior a los totales, o cuyos totales no se pudieron leer al crearlo;
    - `Ledger totals: recorded by another version of the method, not compared`;
    - `⚠️ Ledger totals: could not be read on the copy`.
- 👑 Los administradores, y lo que significará una restauración para todos: `After a restore you sign in with one of them, with the password of then; every session open now ends.` y `Invitations and links sent before the restore will have expired: send them again if needed.`
- ⚠️ Las advertencias, que permiten que la restauración continúe: `The upgrade changed the rows of some tables (listed above)`, `The backup's database has broken references: they are kept as they are`, `The upgrade added broken references to the copy`, `The ledger's totals differ from those the backup recorded (listed above)`, `The ledger's totals could not be read on the copy` o `Some currency codes in the backup are not ISO 4217 codes, names or numbers an earlier version saved: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them after the restore)`, como explica [Códigos de moneda que no son códigos ISO](cli_tools.md).
- 👥 Una copia de seguridad con más cuentas activas de las que permite `LIBREFOLIO_MAX_USERS` añade una línea, una sola vez, sin nombres ni direcciones: `⚠️ The backup holds <n> active accounts; this instance accepts <m> (LIBREFOLIO_MAX_USERS): at the first sign-in the administrator chooses who keeps access, the others are deactivated (not deleted)`. Solo informa: `backup restore --yes` confirma y `--dry-run` sale con `0`, como con cualquier copia de seguridad.
- ⛔ El bloqueo: `❌ The backup has no active administrator: after a restore nobody could manage the instance`.

Conviene saber:

- 💽 La copia necesita espacio libre en el disco del directorio de datos: el contenido descomprimido del archivo, más el doble de su base de datos para la actualización, más 64 MB (`backup inspect` muestra esos tamaños); el archivo se lee donde está, nunca se copia. Un archivo seguro necesita además espacio para el archivo descifrado, aproximadamente su propio tamaño, hasta que se descomprime. Espacio insuficiente → la comprobación se detiene antes de descomprimir, con los bytes necesarios (`no_space`); un disco que se llena durante la comprobación también la detiene.
- 📦 `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` («Opciones principales» en [Variables de entorno](configuration.md)) limita el tamaño descomprimido: los tamaños del manifiesto se suman antes de la comprobación de espacio, y un archivo que supera el límite se rechaza con `unpacked_too_large`, sin descomprimir nada. Para levantar el límite en un comando, pon `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` delante de él:

    ```bash
    # Host
    LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 pipenv run ./dev.py backup restore <archive>

    # Docker
    docker compose exec -e LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 librefolio python dev.py backup restore <archive>
    ```

    Un límite ilegible detiene el comando antes de `🔎 Checking … on a copy`, código de salida `1`: `❌ LIBREFOLIO_BACKUP_MAX_RESTORE_MB: expected a whole number of megabytes, 0 for no limit (backup_restore_unavailable)`.

- 🚦 Un archivo a la vez: con otra comprobación en ejecución, `❌ Another archive is being checked (from the web interface or another command): try again when it ends`.
- 🆕 Solo hace falta el directorio de datos, de lo contrario `❌ No data directory at <path>`. Como con `-o`, una ruta relativa empieza en la raíz del proyecto.
- 🔗 Mantén `.restore/` y `.restore/stage/` como carpetas reales: un enlace, o un archivo, en su lugar → `❌ <path> is not a plain folder (a link, or a file): the copy is made in a folder of the data directory`.

??? note "❌ Rechazos — qué significan los códigos"

    | Código | Por qué se rechaza el archivo |
    | --- | --- |
    | `not_a_backup` | No es un zip, o es un zip sin el manifiesto que escribe LibreFolio, como un directorio de datos comprimido a mano |
    | `password_required` | Un archivo seguro, y ninguna contraseña: no hay terminal donde preguntar, ni `--password-file` ni `--password-stdin` |
    | `wrong_password` | La contraseña no abre el archivo seguro: no es con la que se creó, o se cambió el principio del archivo |
    | `envelope_damaged` | El archivo seguro está dañado, cortado, o se cambió después de crearlo |
    | `envelope_unsupported` | El archivo seguro viene de un LibreFolio más reciente, o pide ajustes que este no acepta: actualiza primero LibreFolio |
    | `instance_key_unreadable`, `instance_key_invalid` | El archivo dado con `--instance-key-file` no puede dar la clave, o la clave tiene menos de 32 caracteres: [La clave de instancia de otra instalación](#backup-restore-instance-key) |
    | `archive_unreadable`, `archive_damaged` | No se puede leer el archivo, o el zip está dañado |
    | `manifest_newer_format` | El formato del archivo es más reciente de lo que lee este LibreFolio: actualiza primero LibreFolio |
    | `manifest_invalid`, `manifest_unreadable`, `manifest_too_large` | El manifiesto está dañado o no es válido |
    | `unexpected_entry`, `missing_entry` | El archivo contiene una entrada que el manifiesto no lista, o le faltan entradas que lista; para la clave de instancia, una entrada que el manifiesto no anuncia, o una que anuncia y falta en el archivo |
    | `duplicate_entry` | Una entrada aparece dos veces, incluso cuando solo cambian las mayúsculas de su nombre, o está donde debe estar la carpeta de otra entrada |
    | `not_a_file`, `encrypted_entry`, `unsupported_entry` | Una entrada es una carpeta o un enlace, está cifrada, o usa una compresión que LibreFolio no escribe |
    | `too_many_entries` | El archivo contiene más de 500 000 entradas |
    | `checksum_mismatch` | El tamaño o el SHA-256 de una entrada difiere del manifiesto: el archivo está dañado o se cambió |
    | `unpacked_too_large` | Descomprimido, el archivo superaría lo que esta instalación acepta para una restauración, según los tamaños del manifiesto: `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`. No se descomprime nada |
    | `no_space` | No hay espacio libre suficiente para la copia |
    | `stage_failed` | No se pudo escribir la copia: el error impreso justo encima da la causa |
    | `database_damaged` | La base de datos de la copia de seguridad no supera la comprobación de integridad de SQLite, antes o después de la actualización, SQLite no puede leer su esquema, o contiene texto que no es UTF-8 (otro programa escribió en ella, o se cambió) |
    | `database_foreign_objects` | La base de datos de la copia de seguridad contiene un disparador, una vista o una tabla virtual, que LibreFolio nunca crea: no la hizo LibreFolio, o se cambió. Usa otra copia de seguridad |
    | `manifest_mismatch` | La base de datos de la copia de seguridad no es la que describe su manifiesto |
    | `revision_missing` | La base de datos de la copia de seguridad no registra ninguna revisión de migración |
    | `revision_unknown` | La copia de seguridad viene de un LibreFolio más reciente, o no de este: actualiza LibreFolio y vuelve a comprobarla |
    | `upgrade_failed` | La actualización de la copia falló o duró más de una hora (el error impreso justo encima da la causa), o no llegó a la revisión de este LibreFolio |
    | `post_migration_failed` | Una reparación posterior a la migración falló en la copia: el error impreso justo encima da la causa |
    | `head_unknown` | Este LibreFolio no puede leer sus propios scripts de migración |

### ♻️ Restaurar un archivo {: #backup-restore }

**Dónde: donde se ejecuta el servidor** — terminal del servidor, carpeta de LibreFolio; con Docker [dentro del contenedor](#backup-docker). La restauración queda registrada para la ruta del directorio de datos: un servidor que encuentra su directorio de datos bajo otra ruta no la aplica.

1. **Ejecuta el comando.**

    ```bash
    # Check the archive on a copy, then restore it at the next start of the server
    pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
    ```

    Resultado: la misma comprobación sobre una copia y el mismo informe que [Probar una restauración sobre una copia](#backup-restore-dry-run); si el archivo se puede restaurar, la pregunta:

    ```text
       Type "restore" to restore this archive at the next start of the server:
    ```

2. **Escribe `restore`**, en minúsculas; los espacios alrededor no cuentan. Cualquier otra cosa, `Restore` o una línea vacía incluidas, termina con `Nothing restored: the copy was removed.` y código de salida `1`.

    Resultado, código de salida `0`:

    ```text
    ✅ The restore waits for the next start of the server: restart LibreFolio to apply it.
       That start replaces the database and the files, and ends every session: sign in with an administrator of the backup.
       ./dev.py backup pending shows it; ./dev.py backup pending --cancel drops it.
    ```

    Todavía no ha cambiado nada: el servidor sigue funcionando con sus datos, y la copia comprobada espera en `.restore/stage/<id>/`, tanto tiempo como haga falta.

3. **Reinicia LibreFolio** cuando te convenga: detén todo el servidor y [vuelve a iniciarlo](cli_tools.md#start-the-server); con Docker, `docker compose restart librefolio` ([Copias de seguridad con Docker](#backup-docker)). Si el servidor está detenido, su siguiente arranque aplica la restauración.

    Resultado: ese arranque aplica la restauración antes de leer ningún dato (más abajo).

| Opción | Efecto |
| --- | --- |
| `--dry-run` | Solo la comprobación: [Probar una restauración sobre una copia](#backup-restore-dry-run) |
| `--yes`, `-y` | Confirma sin preguntar. Sin terminal, por ejemplo en un script, es obligatorio: de lo contrario `❌ No terminal to ask on: add --yes to confirm the restore. Nothing restored: the copy was removed.`, código de salida `1` |
| `--password-file FILE`, `--password-stdin` | La contraseña de un [archivo seguro](#backup-secure), obligatoria sin terminal |
| `--instance-key-file FILE` | La clave de instancia de otra instalación: [más abajo](#backup-restore-instance-key) |
| `--identity-file FILE` | La clave privada de un [archivo sellado](#backup-sealed) |

**Qué hace ese arranque:**

1. 🛑 **Solo un arranque de todo el servidor.** Cada proceso del servidor mantiene un bloqueo sobre el directorio de datos desde el principio de su arranque hasta que termina. Un arranque que lo encuentra en manos de otro proceso (un worker que uvicorn vuelve a iniciar junto a sus hermanos, con `--workers`; un segundo servidor en el mismo directorio) deja la restauración en espera (`server_running`). Reinicia todo el servidor, nunca un solo worker. Un arranque que encuentra la restauración aplicada por otro servidor que sigue en ejecución, o por otro arranque, se detiene en lugar de servir datos cuya restauración no está completada.
2. 🔀 **El intercambio.** `sqlite/`, `custom-uploads/`, `broker_reports/` y `scenario_catalog/` de la instancia intercambian su lugar con los de la copia: renombrados dentro del directorio de datos, instantáneos sea cual sea el tamaño. Las carpetas de la instancia pasan a `.restore/previous/`.
3. 🔒 **Lo que se queda.** `secrets/`, `logs/`, `scheduler_state.json` y `backups/` no se tocan: la instancia conserva su [clave de instancia](configuration_secrets.md#instance-key), sus registros y sus archivos.
4. ✅ **El primer arranque debe completarse.** Continúa, con los datos restaurados, ya en la revisión de este LibreFolio. Una vez superado, antes de responder a nadie, cierra todas las sesiones, revoca los enlaces de un solo uso de la copia de seguridad y elimina los datos anteriores y la copia: la restauración está completada.
5. ↩️ **De lo contrario, vuelta a como estaba.** Si ese primer arranque falla (una migración, un archivo dañado), el siguiente arranque devuelve los datos a como estaban por sí solo y registra la reversión con el motivo ([Seguir o cancelar una restauración](#backup-pending)). Con Docker el contenedor se reinicia solo; si nada reinicia el servidor, inícialo tú.

**Después de la restauración:**

- 🔑 Todos vuelven a iniciar sesión, en todos los dispositivos, con una cuenta de la copia de seguridad y la contraseña de entonces. El informe de la comprobación nombra los administradores de la copia de seguridad.
- 🔗 Ningún enlace enviado antes de la restauración funciona ya (invitaciones, restablecimientos de contraseña, verificaciones de correo), ni siquiera los que aún están en la copia de seguridad: envía otros nuevos.
- 📧 Una cuenta que la copia de seguridad tenía esperando la verificación de su correo pierde su enlace y deja de esperar: la página de inicio de sesión no le envía otro y responde que la cuenta está desactivada. Un administrador la activa en [Usuarios e invitaciones](users.md#actions), con la dirección sin verificar, o la elimina ([Eliminar una cuenta](users.md#delete)), para que su propietario se registre de nuevo y reciba un enlace nuevo. Una cuenta así nunca inició sesión: no contiene datos.
- 🆘 Si nadie recuerda la contraseña de entonces de un administrador, quien gestiona el servidor crea un enlace de restablecimiento con [`user reset-link`](cli_tools.md), o establece una contraseña nueva con `user reset`. Una vez dentro, un administrador envía enlaces de restablecimiento a los demás desde [Usuarios e invitaciones](users.md#reset-links).

Conviene saber:

- 🚦 Una restauración a la vez: mientras una espera o se está aplicando, `backup restore` se detiene antes de la comprobación con `❌ A restore already waits for the next start: ./dev.py backup pending --cancel drops it (restore_already_pending)`, código de salida `1`. También se detiene ahí cuando no puede leer el estado de la restauración, porque no puede saber si hay una en espera: `❌ The state of the restore cannot be read: <reason> (restore_state_unreadable)`, código de salida `1`, nada comprobado. `--dry-run` sigue funcionando.
- ❌ Si se rechaza la confirmación, el comando imprime una línea con un código, elimina la copia y sale con `1`: `restore_stage_outdated` (LibreFolio se actualizó entre la comprobación y la confirmación), `restore_stage_expired` (pregunta en espera más de 24 horas), `restore_already_pending` (otra restauración confirmada mientras tanto). Ejecuta de nuevo el comando; tras `restore_stage_outdated`, comprueba de nuevo el archivo.
- 🔗 Mantén las cuatro carpetas como carpetas reales del directorio de datos: una que sea un enlace, o esté montada por separado, no se puede intercambiar. El arranque deja los datos como están y registra la reversión con `swap_failed`.
- 💽 El intercambio no necesita espacio propio: la copia de la comprobación pasa a ser los datos de la instancia, y los datos anteriores se eliminan cuando se completa el primer arranque.
- 🗝️ La restauración conserva la clave de instancia de esta instalación. Los secretos guardados de un archivo de otra instalación los vuelve a cifrar con ella la comprobación si el archivo contiene la clave que los cifró (un [archivo seguro](#backup-secure), con una clave que generó LibreFolio) o si la das con `--instance-key-file` ([La clave de instancia de otra instalación](#backup-restore-instance-key)). De lo contrario no se pueden leer aquí: el informe los cuenta, para volver a introducirlos tras la restauración, a menos que antes vuelvas a poner la clave de esa instalación ([Secretos guardados y la clave de instancia](configuration_secrets.md#plugin-secrets)). Consulta «La clave de instancia está solo en un archivo seguro» más arriba.

### 🗝️ La clave de instancia de otra instalación {: #backup-restore-instance-key }

**Dónde: terminal del servidor, carpeta de LibreFolio**, con el archivo de clave fuera del directorio de datos (Docker: un secreto que solo lee root, [más abajo](#backup-docker)).

```bash
# A clear archive of another installation, with the instance key of that installation
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --instance-key-file ~/old-instance.key
```

Resultado: la comprobación vuelve a cifrar en la copia los secretos de plugins guardados (como la clave de API de una fuente de datos) con la clave de esta instancia, que se queda como está.

Hace falta porque un archivo en claro deja fuera la clave de instancia, y también un archivo seguro cuya clave venía del entorno: sus secretos guardados solo se abren con la clave de la instalación que lo creó. Funciona con o sin `--dry-run`.

- 📁 El informe dice `Instance key: not included; given with --instance-key-file`, y después `Saved provider keys: <n> re-encrypted with this instance's key`.
- 📄 **El archivo**: una copia del `secrets/instance.key` de la instalación antigua, el archivo de su `LIBREFOLIO_INSTANCE_KEY_FILE` tal cual, o el valor de su `LIBREFOLIO_INSTANCE_KEY` escrito en un archivo tal como estaba en la variable, espacios incluidos. Solo se descartan una marca de orden de bytes al principio y los saltos de línea al final, como con `--password-file`: una clave que funcionaba como variable funciona igual en el archivo.
- 🔑 Se lee primero, como el usuario que inició el comando, antes del cambio al propietario del directorio de datos, como `--password-file`: con `docker compose exec` funciona un secreto de Docker que solo lee root. Misma regla que `--password-file`, «Un archivo en el que el comando pueda confiar» en [Un archivo seguro](#backup-secure): mantenlo fuera del directorio de datos.
- 🙈 La clave nunca se imprime. Solo la línea de comandos la acepta: la interfaz web no, y una restauración desde Configuración › Administración › Copia de seguridad cuenta esos secretos como ilegibles.
- ℹ️ Un archivo con su propia clave se restaura con esa, sea cual sea el contenido del archivo: `ℹ️ The archive carries its own instance key: --instance-key-file is not used`.
- ⚠️ Una clave que no lee ningún secreto guardado no es la clave de la instalación que creó la copia de seguridad: `⚠️ The key given with --instance-key-file reads none of the saved provider keys: it is not the key of the instance this backup came from`, antes de la línea que los cuenta. Si la clave de esta instancia no se puede usar, o no hay ninguna y la comprobación no puede crearla (`secrets/` no escribible), no se vuelve a cifrar nada, sea cual sea la clave dada: `⚠️ This instance's own key cannot be used, so nothing was re-encrypted with the key given: <problem>`, con el problema del `The instance key cannot be used: …` del registro de arranque («Comprobaciones al arrancar» en [Variables de entorno](configuration.md)) o, sin clave, `<path>: there is no instance key yet, and it could not be created`. Los secretos que ya están bajo la clave de esta instancia, como en un archivo de esta misma instancia, se quedan como están.
- ❌ Sale con `1`, antes de comprobar nada, cuando el archivo no da la clave: `❌ instance key file: <path> does not exist (instance_key_unreadable)`, o `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it`. Una clave de menos de 32 caracteres lo detiene antes de hacer la copia: `❌ The instance key given is too short: an instance key has at least 32 characters (instance_key_invalid)`.

### ⏳ Seguir o cancelar una restauración {: #backup-pending }

**Dónde: terminal del servidor, carpeta de LibreFolio** (Docker: [dentro del contenedor](#backup-docker)); `--recover previous` solo con LibreFolio detenido.

```bash
# The restore waiting for the next start, or the last one
pipenv run ./dev.py backup pending

# Drop the restore waiting, and its checked copy (the same as --recover cancel)
pipenv run ./dev.py backup pending --cancel

# When the state of the restore cannot be read: put the data of before back (LibreFolio stopped)
pipenv run ./dev.py backup pending --recover previous

# For a script: the state as one JSON line, and the same actions with fixed exit codes
pipenv run ./dev.py backup pending --json
pipenv run ./dev.py backup pending --recover cancel --json
```

Resultado: `backup pending` no cambia nada y sale con `0`, excepto cuando no puede leer el estado de la restauración ([Un estado de restauración ilegible](#backup-pending-unreadable)). Muestra una de estas líneas:

| Imprime | Qué significa |
| --- | --- |
| `ℹ️ No restore waits for the next start` | Ninguna restauración confirmada, o la última se descartó |
| `⏳ A restore waits for the next start of the server`, y después `backup made by LibreFolio <version> on <date> UTC; confirmed by <who> on <date> UTC` | Confirmada, aún no aplicada. `<who>` es `cli` para este comando; en otro caso, el nombre de usuario del administrador que la confirmó |
| `⏳ A restore is being applied by the server` | Un arranque la aplicó y aún no se ha completado. Si ese proceso terminó de forma anómala, el siguiente devuelve los datos a como estaban |
| `✅ The last restore was applied on <date> UTC: backup made by LibreFolio <version> on <date> UTC` | Completada |
| `⚠️ The last restore was rolled back on <date> UTC, the data is as it was before: <reason> (<code>)` | Deshecha, por el motivo de la tabla de abajo |

| Opción | Efecto |
| --- | --- |
| `--cancel` | Descarta la restauración en espera, con su copia: [más abajo](#backup-pending-unreadable) |
| `--json` | El estado como una línea JSON, para scripts: [Para scripts](#backup-pending-json) |
| `--recover CHOICE` | `previous` o `cancel`, con códigos de salida fijos: [Para scripts](#backup-pending-json) |

Cuando un arranque encontró una restauración en espera sin aplicarla, una línea más dice por qué, y la restauración sigue esperando:

- `⚠️ At the last start a backup was running: the next start applies it (backup_running)`: había una copia de seguridad en ejecución en el arranque, por ejemplo un `backup create` desde la línea de comandos.
- `⚠️ It was confirmed for another data directory (<path>): this one does not apply it (other_data_directory)`: el servidor encontró su directorio de datos bajo una ruta distinta de la de la confirmación, por ejemplo una copia del directorio de datos. Descártala con `--cancel` y ejecuta `backup restore` donde se ejecuta el servidor.
- `⚠️ At the last start another server process was serving the data directory: restart the whole server to apply it (server_running)`: un worker se reinició mientras los demás servían (`--workers`), u otro servidor en el mismo directorio de datos. Reinicia todo el servidor.

| Código | `<reason>` | Qué hacer |
| --- | --- | --- |
| `first_start_failed` | `the first start after it did not complete` | El registro de ese arranque da la causa |
| `swap_interrupted` | `the start that applied it was interrupted` | Nada: un arranque se detuvo durante el intercambio, y el siguiente lo deshizo |
| `swap_failed` | `its folders could not be moved into place` | Haz que las cuatro carpetas sean carpetas reales del directorio de datos, ni enlaces ni montajes separados |
| `stage_missing` | `its checked copy was gone` | La copia de `.restore/stage/` se eliminó o se cambió: comprueba de nuevo el archivo |

Una reversión también elimina los datos restaurados y la copia: para intentarlo de nuevo, ejecuta `backup restore` otra vez. Si ni siquiera falla volver a los datos anteriores (disco, permisos), LibreFolio no arranca: el registro contiene `The data directory is half restored: the restore could not be undone, and LibreFolio does not start on it`, y cada arranque lo intenta de nuevo.

#### 🧩 Un estado de restauración ilegible {: #backup-pending-unreadable }

El estado de la restauración, `.restore/restore.json`, puede volverse ilegible: cambio de propietario o de permisos, un error de disco, un enlace o una carpeta en su lugar, contenido que LibreFolio no escribió. Puede que una restauración se haya detenido a mitad, y LibreFolio no sabe qué datos contiene. `backup pending` lo dice y sale con `1`:

```text
❌ The state of the restore cannot be read: <why>: a restore may have stopped half way. LibreFolio serves no data until you choose (restore_state_unreadable: <reason>)
   The data of before is kept in .restore/previous/: sqlite, user_files
   Checked copies kept: 1 (none is removed while the state cannot be read)
👉 Stop LibreFolio, then run ./dev.py backup pending --recover previous: it puts the data of before back.
```

`<reason>` es `io` (el sistema de archivos lo rechaza: devuelve `.restore/` y sus archivos al usuario que ejecuta LibreFolio, y vuelve a ejecutar `backup pending`, lo que puede bastar), `not_a_file` o `invalid`. Mientras no se pueda leer el estado, no se elimina ninguna copia comprobada, ni por la limpieza del servidor ni por Configuración › Administración › Copia de seguridad, y no se puede confirmar ninguna restauración.

**`--recover previous`**, con LibreFolio detenido, devuelve los datos de antes desde las carpetas: cada carpeta conservada en `.restore/previous/` vuelve a su lugar, y la que reemplaza pasa a `.restore/failed/`. Una restauración completada no conservó datos anteriores: sus datos se quedan. El estado ilegible se conserva como `.restore/restore.json.unreadable-<date>` para que lo mires, y nunca se vuelve a leer. Después inicia LibreFolio con los datos de antes, o restaura una copia de seguridad de nuevo con `backup restore`. Con LibreFolio en ejecución se detiene con `(restore_in_use)`, código de salida `5`; con un estado legible, o ninguno, con `(restore_nothing_to_recover)`, código de salida `3` ([Para scripts](#backup-pending-json)). Ejecutado dos veces, la segunda no cambia nada.

**`--cancel`**, igual que `--recover cancel` pero con los códigos de salida de abajo, descarta la restauración en espera con su copia comprobada, sea quien sea quien la confirmó:

| Resultado | Imprime | Salida |
| --- | --- | --- |
| Descartada | `✅ The restore waiting for the next start was dropped, with its copy: the data stays as it is` | `0` |
| Descartada, copia no eliminada (permisos, disco) | `✅ The restore waiting for the next start was dropped: the data stays as it is` y `⚠️ Its checked copy could not be removed: it goes when its check expires`. Con un error, el registro de arriba contiene `The copy of a cancelled restore could not be removed: it goes when its check expires`; una copia que queda sin error, como una con una carpeta de solo lectura, no tiene ninguno. LibreFolio lo intenta de nuevo en su primer arranque una vez que la comprobación tiene 24 horas | `0` |
| No se puede descartar, por un error del sistema de archivos antes (el bloqueo, o al eliminar el estado) | `❌ The restore could not be cancelled: <reason>. It still waits for the next start (restore_cancel_failed)` | `1` |
| Estado ilegible | La línea `restore_state_unreadable` de `backup pending` | `1` |
| Ninguna restauración en espera, o una ya aplicándose | `❌ No restore waits for the next start: nothing to cancel (restore_not_pending)` | `1` |

#### 🤖 Para scripts: --json y --recover {: #backup-pending-json }

Un script, o una máquina que llega al servidor por `ssh`, lee el estado con `--json` y actúa con `--recover CHOICE`: no se pregunta nada en el terminal, y los códigos de salida son fijos.

**La línea JSON.** Con `--json`, `backup pending` escribe exactamente una línea en stdout: un objeto JSON, luego un salto de línea, sin color. Todo lo demás, incluidas las líneas de registro de LibreFolio, va a stderr. Sale con `0` siempre que se imprime la línea: un estado ilegible es un estado, no un error.

| Clave | Valor |
| --- | --- |
| `state` | `none`, `pending`, `in_progress`, `committed`, `rolled_back` o `unreadable` |
| `reason` | El motivo de reversión de un estado `rolled_back` (`first_start_failed`, `swap_interrupted`, `swap_failed`, `stage_missing`), o `io`, `not_a_file`, `invalid` para uno `unreadable`; `null` en otro caso |
| `waiting` | Por qué un arranque no aplicó una restauración que espera: `backup_running`, `other_data_directory`, `server_running`, o `null` |
| `backup_created_at` | Cuándo se creó la copia de seguridad de la restauración, como `2026-10-23T03:00:12Z` (UTC); `null` sin estado, o con uno ilegible |
| `safety_copy` | `{"present": true, "at": "<date>Z"}` cuando los datos de antes de un intercambio están en `.restore/previous/`, en otro caso `{"present": false, "at": null}` |
| `choices` | Las palabras que `--recover` acepta ahora, en la tabla de abajo |

Tras un `--recover`, la línea describe el estado **después** de él y añade `recover`, `{"choice": "<word>", "done": true}` o `false`, y, con un código de salida distinto de `0`, `error`, la palabra de la tabla de códigos de salida.

| `state` | Significa | `choices` |
| --- | --- | --- |
| `none` | Ninguna restauración confirmada, o la última se descartó | ninguna |
| `pending` | Una restauración espera al siguiente arranque | `cancel` |
| `in_progress` | Un arranque la está aplicando, o la ha aplicado y aún no se ha completado | ninguna |
| `committed` | La última restauración está completada | ninguna |
| `rolled_back` | La última restauración se deshizo, con su `reason` | ninguna |
| `unreadable` | No se puede leer el estado: [Un estado de restauración ilegible](#backup-pending-unreadable) | `previous` |

```json
{"state":"unreadable","reason":"invalid","waiting":null,"backup_created_at":null,"safety_copy":{"present":true,"at":"2026-10-23T03:00:12Z"},"choices":["previous"]}
{"state":"pending","reason":null,"waiting":"server_running","backup_created_at":"2026-10-22T21:30:05Z","safety_copy":{"present":false,"at":null},"choices":["cancel"]}
```

La línea nunca contiene un nombre de usuario, un correo, una ruta ni un identificador: quién confirmó, el directorio de datos y la copia comprobada no están en ella. `safety_copy.at` es el momento en que se aplicó la restauración o, con un estado ilegible, el último cambio de `.restore/previous/`.

**Los códigos de salida.** `--recover previous` devuelve los datos de antes cuando no se puede leer el estado, con LibreFolio detenido; `--recover cancel` descarta la restauración en espera, con su copia comprobada. Igual con o sin `--json`:

| Salida | Cuándo | `error` en la línea |
| --- | --- | --- |
| `0` | Hecho: los datos de antes han vuelto, o se descartó la restauración en espera | ninguno |
| `2` | Un error de uso: `--recover` sin una opción, `--recover` con `--cancel`, o `--json` con `--cancel` (usa `--recover cancel`) | ninguno: la línea no se escribe |
| `3` | Nada que recuperar: no hay estado de restauración, o la opción ya estaba hecha | `nothing_to_recover` |
| `4` | La opción no es válida en este estado, como `previous` mientras se puede leer el estado, `cancel` mientras no se puede, o una palabra que no es una opción: no cambia nada | `choice_not_valid` |
| `5` | Falló: LibreFolio está en ejecución sobre este directorio de datos (`restore_in_use`), una carpeta no se puede devolver a su sitio (`restore_apply_failed`), no se puede descartar la restauración (`failed`): no se da nada por hecho. Con un directorio de datos inexistente, también `5`, pero sin línea: stdout vacío, stderr dice por qué | `restore_in_use`, `restore_apply_failed` o `failed` |

Si se repite, una opción no cambia nada: el segundo `--recover previous` no encuentra ningún estado ilegible, no mueve ninguna carpeta, no añade nada a `.restore/failed/` y sale con `3`; lo mismo para un segundo `--recover cancel`. Un script puede repetir `previous` o `cancel` hasta leer `0` o `3`.

Un script que lee el estado y recupera, en un servidor donde LibreFolio está detenido:

```bash
state=$(pipenv run ./dev.py backup pending --json 2>/dev/null)

if [ "$(echo "$state" | jq -r '.choices | index("previous") != null')" = "true" ]; then
    pipenv run ./dev.py backup pending --recover previous --json 2>/dev/null
    case $? in
        0|3) echo "data of before is back" ;;
        5)   echo "failed: stop LibreFolio, read the log" >&2; exit 1 ;;
    esac
fi
```

### 🔓 Descifrar un archivo seguro {: #backup-decrypt }

**Dónde: cualquier instalación**, servidor en ejecución o detenido; no necesita directorio de datos. Docker: [dentro del contenedor](#backup-docker), con `-o` donde pueda escribir el usuario del servidor.

```bash
# The zip inside a secure archive, to use it by hand
pipenv run ./dev.py backup decrypt /mnt/nas/librefolio/librefolio-backup-20261015-121500.lfbk -o /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

Resultado: el zip contenido en el [archivo seguro](#backup-secure), el que `backup create` escribe sin contraseña, con `secrets/instance.key` si el archivo seguro contiene la clave.

| Opción | Efecto |
| --- | --- |
| `-o`, `--output FILE` | Obligatorio: el archivo del zip, que todavía no debe existir. Uno existente se rechaza antes de la contraseña, `❌ <path> already exists: choose another name`, sin escribir nada. Ruta relativa desde la raíz del proyecto, como con `create` |
| `--password-file FILE`, `--password-stdin` | La contraseña; de lo contrario se pide una vez en el terminal ([Un archivo seguro](#backup-secure)) |
| `--identity-file FILE` | La clave privada de un [archivo sellado](#backup-sealed) |

- ✅ Termina con `✅ Decrypted: <path> (<size>)` y `🔒 It holds every user's data in clear: keep it private, and remove it once used.`; con la clave de instancia, una última línea: `🔑 It also holds the instance key: with it, every saved provider key can be read.`
- ♻️ `inspect` y `restore` toman ese zip como cualquier otro, y su clave sigue volviendo a cifrar los secretos guardados. Para restaurar un archivo seguro no hace falta: `backup restore` toma el `.lfbk` tal cual.
- 🔒 El zip contiene los datos de todos los usuarios en claro, y solo su propietario lo lee (`0600`): el usuario que ejecutó el comando, o el usuario del servidor cuando el comando cambió a él.
- 👤 Donde hay un directorio de datos y lo ejecutas como root, por ejemplo con `docker compose exec`, lee primero `--password-file` como root (funciona un secreto de Docker de root), y después cambia al propietario del directorio de datos, como hacen los demás comandos: el zip pertenece al usuario del servidor, y `-o` debe ser escribible por ese usuario ([Copias de seguridad con Docker](#backup-docker)). Si no puede cambiar, se detiene antes de leer el archivo o de pedir la contraseña: `❌ cannot switch to the owner of <path> (<uid>:<gid>): <reason>. Run the command as that user.`
- ❌ Sale con `1` cuando no puede leer el archivo, como uno que solo lee root una vez cambiado al usuario del servidor (`❌ Cannot read <path>: <reason> (archive_unreadable)`, antes de la contraseña), cuando el archivo no es un archivo seguro (`❌ <path> is not a secure backup: a plain .zip needs no decrypting (not_an_envelope)`), cuando la contraseña no lo abre (`wrong_password`), cuando está dañado (`envelope_damaged`: no queda nada en `-o`) o es de un LibreFolio más reciente (`envelope_unsupported`), y cuando no puede escribir en `-o` (`❌ Cannot write <path>: <reason>`, una vez dada la contraseña: no queda nada allí).

### 🚚 Usar un archivo en otra instalación

[`backup restore`](#backup-restore) restaura un archivo en la instalación donde lo ejecutas, con el `secrets/` de esa instalación. Para, en cambio, iniciar otra instalación a mano con los datos de un archivo, con el `secrets/` de la instalación que lo creó, por ejemplo cuando trasladas LibreFolio:

1. **Instalación que recibe los datos, terminal**: primero, comprueba el archivo con `backup restore <archive> --dry-run` ([Probar una restauración sobre una copia](#backup-restore-dry-run)): sin cambiar nada, te dice si ese LibreFolio acepta el archivo, qué migraciones aplicará y con qué administradores iniciarás sesión. Después **detén LibreFolio**.
2. **Directorio de datos vacío** (`LibreFolio-data/` con Docker Compose): si contiene algo, apártalo primero: nada de los datos antiguos puede mezclarse con los del archivo, ni siquiera `app.db-wal` y `app.db-shm` de SQLite. **Descomprime el archivo** allí; un archivo seguro se descifra primero en su zip ([Descifrar un archivo seguro](#backup-decrypt)).
3. **`secrets/` en el directorio de datos**: vuelve a ponerlo desde la copia guardada por separado. El zip de un archivo seguro con la clave ya trae `secrets/instance.key`: da a la carpeta el modo `0700` y al archivo `0600` (`chmod`), de lo contrario el registro de arranque muestra una advertencia.
4. **Inicia LibreFolio**, la versión que creó el archivo o una más reciente: las migraciones pendientes se ejecutan solas al arrancar.

Conviene saber:

- ⛔ LibreFolio nunca degrada una base de datos: un archivo de una versión más reciente necesita esa versión o una posterior, y una más antigua no arranca con él. `backup inspect` muestra la versión que creó el archivo; `backup restore --dry-run` lo rechaza con `revision_unknown`.
- 🧹 El `manifest.json` que queda en la raíz del directorio de datos es inofensivo: puedes borrarlo.
- 👤 Con Docker, el contenedor entrega el directorio de datos a su usuario en cada arranque: el propietario de los archivos descomprimidos no importa. En una instalación en el host, descomprime como el usuario que ejecuta LibreFolio.
- 🗝️ La clave de un archivo seguro funciona solo donde no están establecidas ni `LIBREFOLIO_INSTANCE_KEY` ni `LIBREFOLIO_INSTANCE_KEY_FILE`: una clave establecida allí prevalece sobre `secrets/instance.key`. Nunca la pongas en lugar de una clave que ya está en uso: lo que se guardó con esa clave dejaría de poder leerse. Una instalación con su propia clave toma el archivo con [`backup restore`](#backup-restore), que vuelve a cifrar los secretos guardados.

### 🐳 Copias de seguridad con Docker {: #backup-docker }

**Dónde: terminal del servidor, carpeta de `docker-compose.yml`.** El comando se ejecuta dentro del contenedor, donde el directorio de datos es `/app/backend/data/prod-docker`.

```bash
# Write an archive: on the host, it appears in its own folder of ./LibreFolio-data/backups/
docker compose exec librefolio python dev.py backup create

# Check it, with its path inside the container
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Try a restore of it on a copy: the instance stays as it is
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# Restore it: the same check, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Restart the container: its start applies the restore
docker compose restart librefolio

# Then see how it went
docker compose exec librefolio python dev.py backup pending
```

Resultado: como en el host; el archivo de `backup create` está en una carpeta propia, como `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`, que es `./LibreFolio-data/backups/` en el host.

- 👤 `docker compose exec` se ejecuta como root: el comando cambia al propietario del directorio de datos, `backup decrypt` incluido, y lo que escribe pertenece al usuario del servidor. Si no puede cambiar, se detiene y te pide que lo ejecutes como ese usuario: `docker compose exec --user <uid>:<gid> librefolio python dev.py backup create`, con los números del mensaje.
- 📂 `-o` y los archivos de `inspect` y `restore` son rutas dentro del contenedor. Un archivo que está en el host: cópialo primero en `LibreFolio-data/`, por ejemplo en `LibreFolio-data/backups/`. Un archivo que se escribe fuera de `LibreFolio-data/backups/`: una carpeta montada desde el host, escribible por el usuario del servidor; en cualquier otro sitio se queda dentro del contenedor y se pierde cuando el contenedor se vuelve a crear.
- 🔑 `restore` y `decrypt` leen el archivo como el usuario del servidor: uno escrito por `backup create` está bien, uno que hayas copiado debe ser legible por ese usuario, de lo contrario `archive_unreadable`. Con la imagen oficial, `sudo chown 1000:1000 <archive>` en el host.
- ⌨️ `docker compose exec` da al comando un terminal donde preguntar. Sin él, por ejemplo `docker compose exec -T` en un script, añade `--yes`.
- 🔐 [Archivo seguro](#backup-secure): `--encrypt` pide la contraseña en ese terminal. Con `-T`, por ejemplo desde cron, usa `--password-file` y un secreto de Docker, como `/run/secrets/backup_password`: [el ejemplo](backup_restore.md#command-line) de Copia de seguridad, restauración y traslado de tu instancia muestra las líneas que hay que añadir a `docker-compose.yml`. El zip de `backup decrypt` pertenece al usuario del servidor: dale un `-o` en el que ese usuario pueda escribir, en `LibreFolio-data/backups/` o en una carpeta montada desde el host: `docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip`.
- 🔏 [Archivo sellado](#backup-sealed), sin terminal: `docker compose exec -T librefolio python dev.py backup create --sealed` lee `LIBREFOLIO_BACKUP_RECIPIENTS` del entorno del contenedor, que rellena `env_file: .env`; tras un cambio de `.env`, `docker compose up -d` vuelve a crear el contenedor. Para abrir uno en el contenedor, da a `--identity-file` una ruta dentro de él; mejor, ábrelo en tu ordenador, donde está la clave privada ([Abrir una copia sellada](backup_sealed.md#sealed-open)).
- 🔁 Tras un primer arranque que falla con los datos restaurados, el contenedor se reinicia solo (`restart: unless-stopped`, en los dos archivos compose que incluye LibreFolio), y ese arranque devuelve los datos a como estaban.
- 🔒 En el host, los archivos pertenecen al usuario del contenedor, y solo ese usuario los lee: con otro usuario del host, cópialos con `sudo cp -a`.
- 💻 Desde una copia del código fuente, `./dev.py docker exec backup create` hace lo mismo.

---

## 🔗 Relacionado

- 📄 **[Herramientas de línea de comandos](cli_tools.md)** — Iniciar el servidor, gestionar usuarios, mantener la base de datos, …
