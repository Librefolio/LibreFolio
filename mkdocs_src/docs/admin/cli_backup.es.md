# 💾 Herramientas de administración de CLI: Copias de seguridad

Esta página forma parte de la guía de las herramientas de línea de comandos. Cubre los comandos de **copia de seguridad**: crear, comprobar y restaurar un archivo, seguir una restauración y hacer copias de seguridad con Docker.

El resto de la guía comienza en [Herramientas de línea de comandos](cli_tools.md).

---

## 💾 Hacer una copia de seguridad de la instancia {: #backup }

`backup create` coloca toda la instancia en un único archivo zip, mientras el servidor sigue en ejecución: la base de datos, los archivos subidos, los informes del bróker y tus propios escenarios de estrés. Con `--encrypt`, crea un [archivo seguro](#backup-secure), cifrado con una contraseña que elijas, que `backup decrypt` vuelve a convertir en su zip. Con `--sealed` o `--recipient`, crea un [archivo sellado](#backup-sealed), cuya contraseña solo abre una clave privada tuya, para copias de seguridad que se ejecutan solas. `backup inspect` comprueba un archivo y muestra lo que contiene, `backup restore --dry-run` prueba una restauración del mismo sobre una copia, dejando la instancia como está, y `backup restore` lo restaura en el siguiente arranque del servidor. Para copiar el directorio de datos manualmente, consulta [Copia de seguridad](filesystem.md#backup).

### 📦 Crear un archivo

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

- 🟢 El servidor sigue funcionando, y escribiendo, durante la copia de seguridad: la base de datos se copia con `VACUUM INTO` de SQLite, una instantánea consistente, y después se ejecutan la comprobación de integridad y la comprobación de claves foráneas de SQLite sobre la copia.
- 🗃️ **Sin `--output`, el archivo se queda en el servidor**, en una carpeta propia dentro de `backups/`, como `backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip`: la carpeta recibe el nombre del momento, de dónde vino la copia de seguridad (`cli`) y un código corto. No se copia ni se mueve nada, y el comando imprime esa ruta y luego una línea `SHA-256: <64 hexadecimal digits>`, la suma de comprobación del archivo. La copia de seguridad aparece entonces en la lista de **Configuración › Administración › Copia de seguridad**, y en la limpieza automática: [Copias de seguridad conservadas en el servidor](backup_restore.md#kept-backups).
- 📋 **Con `--output`, el archivo se copia allí** y no queda nada en `backups/`: la misma línea `SHA-256:` sigue a la ruta de la copia. Compárala con la suma de comprobación del archivo una vez que esté en otro disco.
- 🏷️ El archivo recibe el nombre del momento en que empieza la copia de seguridad, en UTC: `librefolio-backup-20261015-121500.zip`, o `.lfbk` para un [archivo seguro](#backup-secure). En una carpeta indicada con `--output` que ya contiene un archivo con ese nombre, por ejemplo tras dos copias de seguridad en el mismo segundo, pasa a ser `librefolio-backup-20261015-121500-2.zip`, luego `-3`, y así sucesivamente: un archivo de copia de seguridad nunca reemplaza a otro archivo.
- 📁 `--output` (`-o`) se comprueba antes de que empiece la copia de seguridad, y el comando debe poder escribir allí. Una carpeta existente recibe el archivo con su nombre predeterminado. Cualquier otra ruta corresponde al archivo de la copia de seguridad, incluso una que termine en `/`: una carpeta que aún no existe pasa a ser el nombre del archivo. Ese archivo no debe existir todavía, y su nombre nunca cambia. Sus carpetas faltantes solo se crean cuando el archivo se mueve allí, así que una copia de seguridad fallida no deja ninguna carpeta vacía. Prefiere rutas absolutas: una relativa empieza en la raíz del proyecto, desde dondequiera que ejecutes el comando.
- 💽 Antes de escribir nada, el comando comprueba el espacio libre donde construye el archivo, en la carpeta `backups/` del directorio de datos, incluso con `-o`: aproximadamente el doble del tamaño de la base de datos, más los archivos, más un pequeño margen. Cuando es insuficiente, o cuando el disco o una cuota se llenan durante la copia de seguridad de todos modos, el comando se detiene con `❌ Backup failed (backup_no_space): not enough free space`. Cuando `-o` está en otro disco, el espacio allí se comprueba una vez construido el archivo y conocido su tamaño.
- 🛟 Si el archivo terminado no puede ir a `-o` (apareció mientras tanto un archivo con ese nombre, no se pueden crear sus carpetas, el otro disco no tiene espacio suficiente, un error de escritura), se coloca en `backups/` en su lugar, como archivo suelto: no está en la lista de copias de seguridad conservadas y la limpieza automática nunca lo elimina. El comando sale con `1`. Un movimiento que falla a mitad no deja ningún archivo parcial.
- 🚦 Se ejecuta una copia de seguridad a la vez: mientras otra está en ejecución, el comando se detiene y te pide que lo intentes de nuevo cuando termine.
- ✅ Termina con `✅ Backup written: <path>`, el tamaño y el tiempo empleado, `SHA-256: <checksum>`, las advertencias que haya y un recordatorio: `🔒 The archive holds every user's data: keep it private.`, o, para un archivo seguro, `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.` Sale con `0` cuando el archivo está donde pediste, advertencias incluidas, y con `1` en caso contrario.
- 🔒 Sin contraseña, el archivo no está cifrado: LibreFolio lo escribe, igual que uno seguro, para que solo su propietario pueda leerlo y escribirlo (`0600`). Mantenlo, junto con cada copia, tan privado como el directorio de datos.
- 🗑️ Las copias de seguridad conservadas en `backups/` permanecen allí hasta que las elimines desde **Configuración › Administración › Copia de seguridad** o desde la carpeta, o hasta que la [limpieza automática](backup_restore.md#backup-cleanup) que hayas configurado las elimine, excepto la más reciente. LibreFolio nunca toca los archivos sueltos `librefolio-backup-*.zip` que versiones anteriores dejaron en `backups/`. Esa carpeta está en el mismo disco que los datos, así que copia los archivos a otro disco, a un NAS o a una ubicación externa, o escríbelos allí directamente con `-o`.
- 🔗 Mantén `backups/` como una carpeta real, nunca un enlace a un NAS u otro disco: cada archivo se construye primero dentro de ella, incluso con `-o`. Un enlace, o un archivo, en su lugar detiene el comando con `❌ <data dir>/backups is not a plain folder (a link, or a file): …`.
- 🧪 `backup --test-db create` hace la copia de seguridad del directorio de datos de prueba en su lugar: una opción de desarrollo.

??? note "⚠️ Advertencias y errores — qué significan los mensajes"

    **Advertencias**: el archivo se escribe de todos modos.

    - `The database failed its integrity check` o `The database has foreign-key violations`: el archivo conserva la base de datos tal como está, y `backup inspect` muestra el resultado de la integridad.
    - `Left out (<n>): links, special files, files or folders that could not be read, or files removed during the backup`, seguido de las entradas, como máximo 50: no están en el archivo. Nunca se siguen los enlaces, incluso cuando toda una carpeta como `custom-uploads/` es un enlace a otro disco.
    - `The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`: un [archivo seguro](#backup-secure) sin la clave.

    **No donde pediste**: el archivo se escribe, y el comando sale con `1`.

    - `⚠️ <reason>: the archive was written to <path> instead`, seguido de las líneas habituales: `-o` no pudo recibir el archivo terminado, así que está en `backups/`, como un archivo suelto fuera de la lista de copias de seguridad conservadas. Muévelo donde quieras.
    - `❌ <reason>: the archive stays in <path>. Move it within the hour: the next backup after that removes it.`: `backups/` tampoco pudo recibirlo. Sigue estando en la carpeta de trabajo de la copia de seguridad, dentro de `backups/.jobs/`, que elimina la primera copia de seguridad iniciada después de esa hora, o el primer arranque de LibreFolio posterior: mueve el archivo fuera antes de entonces.

    **Errores**: no se escribe ningún archivo, y el comando sale con `1`.

    - `❌ No data directory at <path>` o `❌ No database at <path>: nothing to back up`: el comando hace la copia de seguridad del [directorio de datos](filesystem.md) con el que está configurado LibreFolio; comprueba `LIBREFOLIO_DATA_DIR`.
    - `❌ <path> already exists: choose another name or folder`, `❌ <path> is not a folder: choose another path` (hay un archivo donde la ruta necesita una carpeta) o `❌ cannot write into <folder>: choose another folder, or run the command as a user who can`: `-o` no puede recibir el archivo. La copia de seguridad no ha empezado, y no se ha creado nada.
    - `❌ <data dir>/backups is not a plain folder (a link, or a file): …`: vuelve a convertir `backups/` en una carpeta real. `❌ The backup could not run in <data dir>/backups: <reason>`: el comando no pudo preparar allí su carpeta de trabajo, por ejemplo porque no puede escribir en el directorio de datos.
    - `❌ Backup failed (backup_no_space): not enough free space`: el espacio libre era insuficiente al principio, o el disco o una cuota se llenaron durante la copia de seguridad, incluso en mitad de un archivo. Libera espacio en el disco del directorio de datos.
    - `❌ Backup failed (backup_failed): the cause is in the log above`: cualquier otro fallo. Uno de ellos es un archivo que falla mientras se copia al archivo, como un error de lectura en mitad del archivo: parte de un archivo no se puede sacar de nuevo de un zip, así que se detiene toda la copia de seguridad. Un archivo que falla antes de que empiece su copia se omite con la advertencia anterior.

### 🗃️ Dónde se guardan las copias de seguridad {: #backup-kept }

Tanto el comando como la aplicación dejan sus copias de seguridad terminadas en `backups/`, una carpeta cada una, con el nombre `librefolio-backup-<date>-<time>-<origin>-<id>`, donde el origen es `cli` aquí y `ui` para la aplicación. `backups/.jobs/` solo contiene una copia de seguridad en curso o una que falló. Qué hacer con ellas:

- 📋 Lístalas, descárgalas y elimínalas en **Configuración › Administración › Copia de seguridad**, o en **Archivos › Copias de seguridad** (solo administradores): [Copias de seguridad conservadas en el servidor](backup_restore.md#kept-backups).
- 🧹 Configura un tamaño total y una antigüedad máxima, ambos opcionales, para que las más antiguas se eliminen solas, nunca la más reciente: [Limpieza automática](backup_restore.md#backup-cleanup). El comando las aplica después de cada copia de seguridad, igual que la aplicación.
- 💽 Una copia en el disco de tus datos no es una copia de seguridad real: copia el archivo a otro disco, o usa `--output`.
- 🔎 Para comprobar o restaurar un archivo conservado desde la línea de comandos, pasa a `backup inspect` o `backup restore` la ruta que imprimió `backup create`.

### 🔐 Un archivo seguro {: #backup-secure }

```bash
# The password is asked twice at the terminal
pipenv run ./dev.py backup create --encrypt

# The password read from a file that holds it alone (with Docker, a secret: /run/secrets/…)
pipenv run ./dev.py backup create --password-file ~/.librefolio-backup-password

# The password read from the standard input, such as from a password manager
pass show librefolio/backup | pipenv run ./dev.py backup create --password-stdin
```

Un archivo seguro, `librefolio-backup-20261015-121500.lfbk`, es el zip que `backup create` escribe sin contraseña, cifrado con una contraseña que elijas: solo esa contraseña lo abre, y LibreFolio no puede recuperar una perdida. Qué protege y qué no: [Copias de seguridad seguras](backup_restore.md#secure).

- 🔑 **De dónde viene la contraseña**, nunca de la línea de comandos, que cualquier usuario del servidor puede leer (`ps`) y que el shell guarda en su historial: no existe la opción `--password`, y los comandos que aceptan una contraseña no aceptan ninguna opción abreviada.
    - `--encrypt` solo: se escribe en el terminal, dos veces.
    - `--password-file FILE`: el texto del archivo, sin la marca de orden de bytes al principio ni los saltos de línea al final, como en [Secretos en archivos](configuration_secrets.md#secret-files): un archivo que contiene solo la contraseña, como un secreto de Docker. Una ruta relativa empieza en la raíz del proyecto.
    - `--password-stdin`: una línea de la entrada estándar, sin su salto de línea, como la de una tubería. En un terminal, la contraseña se pide como sin la opción, sin mostrarse, dos veces para `create`: escrita allí como una línea, se mostraría.

    `--password-file` y `--password-stdin` se excluyen mutuamente, y cualquiera de las dos hace que el archivo sea seguro sin `--encrypt`.

- 📄 **Un archivo en el que el comando pueda confiar.** El archivo de `--password-file`, como el de `--instance-key-file` ([La clave de instancia de otra instalación](#backup-restore-instance-key)), debe ser un archivo regular: un FIFO, una carpeta o un dispositivo se rechazan de inmediato, sin esperar ni leer nunca, con `❌ password file: <path> is not a regular file (password_unreadable)`. Iniciado como root, como con `docker compose exec`, el comando también rechaza una ruta que pasa por un enlace dentro del directorio de datos, donde el usuario de LibreFolio podría haber colocado uno hacia un archivo que solo root puede leer: `❌ password file: <path> goes through a link inside the data directory: give the file itself, from outside it (password_unreadable)`. Un enlace en otro lugar se sigue, ya que Kubernetes monta así sus secretos; los secretos de Docker y Compose son archivos normales. Para `--instance-key-file`, las mismas líneas empiezan con `instance key file:` y terminan con `(instance_key_unreadable)`.

- 📏 **Las reglas** son las de la contraseña de una cuenta con al menos 12 caracteres: una letra mayúscula y una minúscula, un dígito y un símbolo, contando cada clase en Unicode como para las cuentas; como máximo 1024 caracteres. Se comprueban antes de que empiece la copia de seguridad: una contraseña que incumpla una regla no escribe nada.
- 🗝️ **La clave de instancia.** El archivo incluye `secrets/instance.key` cuando LibreFolio generó la clave y puede usarla; nunca una clave establecida con `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`. Una clave generada que no se puede usar, está dañada, no está accesible o supera los 4096 bytes, más de lo que una restauración vuelve a leer, se omite, con la advertencia `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`, y el archivo se escribe de todos modos.
- 🔐 **El cifrado** viene después de las fases habituales, como `… encrypting`. Escribe el `.lfbk` junto al zip en `backups/`, así que necesita de nuevo allí el tamaño del zip, más 64 MB: cuando es insuficiente, `❌ Backup failed (backup_no_space): not enough free space`. El zip se elimina una vez cifrado, o cuando falla la copia de seguridad. Una copia de seguridad interrumpida de golpe, por un corte de energía o `kill -9`, no puede eliminarlo: el siguiente arranque de LibreFolio da esa copia de seguridad por interrumpida y elimina lo que dejó en `backups/.jobs/`, incluidos el zip y la copia de la base de datos.
- ✅ Termina como se ha descrito, con el recordatorio `🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.`

??? note "❌ Errores de contraseña — qué significan los mensajes"

    No se escribe nada, y el comando sale con `1`.

    - `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`: `--encrypt` sin un terminal donde preguntar, como en cron. Una contraseña vacía escrita en el terminal termina con `❌ No password was typed (password_required)`; una línea vacía de una tubería con `--password-stdin`, con `❌ The standard input carried no password (password_required)`.
    - `❌ The two passwords differ (password_mismatch)`.
    - `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: <rules>)`: los códigos de las reglas que incumple, en este orden: `min_length`, `uppercase`, `lowercase`, `digit`, `special`.
    - `❌ The password is longer than 1024 characters (password_too_long)`.
    - `❌ password file: <path> does not exist (password_unreadable)`, o `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it` (véase «Un archivo en el que el comando pueda confiar» más arriba).

    Ambas opciones de contraseña a la vez, o una opción que no existe, como `--password`, detienen el comando antes de que empiece, con su línea de uso y el código de salida `2`.

### 🗂️ Qué contiene el archivo

El archivo tiene la estructura del directorio de datos y solo contiene:

| Entrada | Qué es |
| --- | --- |
| `manifest.json` | La descripción del archivo, véase más abajo |
| `sqlite/app.db` | La copia de la base de datos |
| `custom-uploads/` | Los archivos subidos en la aplicación |
| `broker_reports/` | Los informes del bróker |
| `scenario_catalog/` | Tus propios escenarios de estrés, si has añadido alguno |
| `secrets/instance.key` | Solo en un [archivo seguro](#backup-secure), cuando LibreFolio generó la clave de instancia: su texto, fuera de la lista de archivos del manifiesto. Una restauración la lee para volver a cifrar los secretos guardados, y nunca la extrae |

Todo lo demás queda fuera: `secrets/` (pero `secrets/instance.key` en un archivo seguro), `logs/`, `scheduler_state.json`, la propia carpeta `backups/`, el marcador `.librefolio-production-data` y los archivos de trabajo de SQLite junto a la base de datos: `app.db-wal`, `app.db-shm`, `app.db.post-migration.lock` y las copias `.bak` de las [correcciones posteriores a la migración](cli_tools.md#post-migration-fixes). La copia de la base de datos ya contiene lo que estaba esperando en `app.db-wal`. Nunca se siguen ni se archivan enlaces simbólicos ni archivos especiales.

!!! warning "🔑 La clave de instancia solo está en un archivo seguro"

    Un archivo sin cifrar deja fuera `secrets/`, que contiene la [clave de instancia](configuration_secrets.md#instance-key). Haz una copia de seguridad por separado, como explica [Estructura del sistema de archivos → Qué incluir en la copia de seguridad](filesystem.md#what-to-back-up), y mantén la copia tan privada como los archivos. Antes de iniciar LibreFolio con los datos de un archivo sin cifrar, vuelve a poner `secrets/` con ellos: sin su clave, lo que LibreFolio cifró ya no se puede leer. Un [archivo seguro](#backup-secure) incluye la clave que generó LibreFolio, nunca una establecida con `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`: guarda esa donde la estableciste. Con una copia de la clave, una restauración en otra instalación aún puede leer los secretos guardados de un archivo sin cifrar: [La clave de instancia de otra instalación](#backup-restore-instance-key).

??? info "📋 `manifest.json` — qué registra"

    - el formato, `librefolio-backup`, y su versión;
    - la versión de LibreFolio que creó el archivo, cómo (`cli` para este comando, `ui` para la interfaz web) y cuándo, en UTC;
    - la base de datos: su revisión de migración (Alembic), el resultado de la comprobación de integridad de SQLite, el número de violaciones de claves foráneas, las filas de cada tabla y los totales de control del libro mayor, el efectivo de cada bróker en cada moneda y la cantidad de cada posición (un archivo creado antes de que existieran no tiene ninguno);
    - cada entrada, primero la base de datos, con su ruta, su tamaño y su SHA-256;
    - si el archivo incluye la clave de instancia y el SHA-256 de esa entrada: solo lo hace un archivo seguro.

### 🔍 Comprobar un archivo

```bash
# Check every entry against the manifest, and show what the archive holds
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip

# Faster: compare the entry names with the manifest, without reading the entries
pipenv run ./dev.py backup inspect /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --no-verify
```

- 🟢 Funciona con cualquier archivo, con el servidor en ejecución o detenido, y no necesita un directorio de datos, salvo para un archivo seguro (más abajo). Como con `-o`, una ruta relativa empieza en la raíz del proyecto.
- 📋 Muestra quién creó el archivo y cuándo (`Made by LibreFolio <version> (cli) on <date> UTC`), la revisión de migración, el tamaño y la comprobación de integridad de la base de datos, sus filas y tablas, el número y el tamaño de los archivos, y si se incluye la clave de instancia.
- 🔎 Compara el tamaño y el SHA-256 de cada entrada con el manifiesto, y termina con `✅ Every entry matches the manifest`. `--no-verify` compara solo los nombres de las entradas, sin leer las entradas, y termina con `ℹ️ The entry names match the manifest; their contents were not read (--no-verify)`.
- 🔐 Un archivo seguro, reconocido por sus primeros bytes sea cual sea su nombre, pide su contraseña primero, una vez, desde las mismas fuentes que `create` ([Un archivo seguro](#backup-secure)). Luego se descifra (`🔓 Decrypting <path>`) en una carpeta privada `.decrypt-…` del `backups/` del directorio de datos, que se elimina al final, también cuando falla el comando: el comando necesita ese directorio de datos, y espacio en él para el archivo descifrado, aproximadamente el tamaño del `.lfbk`. Una carpeta que dejó atrás un `inspect` interrumpido de golpe (un corte de energía, `kill -9`) la elimina el siguiente `inspect`, o el siguiente arranque de LibreFolio, una vez que tiene una hora de antigüedad: una más reciente puede ser de otro `inspect` que sigue en ejecución. Su informe añade `Secure backup: decrypted with its password`. Una contraseña incorrecta termina con `❌ The password does not open this backup (wrong_password)`; consulta también `password_required`, `envelope_damaged` y `envelope_unsupported` en los rechazos de [Probar una restauración sobre una copia](#backup-restore-dry-run). Un `.zip` ignora las opciones de contraseña.
- ❌ Sale con `1` cuando faltan entradas, difieren del manifiesto o no están en él (nombra las cinco primeras de cada caso), y cuando el archivo no es uno que pueda leer: el mensaje termina entonces con un código, como `archive_unreadable` (no es un archivo zip, o está cortado), `manifest_missing`, `manifest_unknown_format` (no es una copia de seguridad de LibreFolio) o `manifest_newer_format` (creado por un LibreFolio más reciente: compruébalo con esa versión o una más reciente).

### 🔏 Un archivo sellado {: #backup-sealed }

Un archivo sellado es un `.tar` cuya contraseña genera el propio LibreFolio y cifra para una o dos claves públicas age: solo la clave privada correspondiente lo abre, y el servidor que lo creó no puede. Está pensado para copias de seguridad que se ejecutan solas, como cada noche desde cron. Qué contiene, cómo guardar la clave y cómo cambiarla: [Copias de seguridad selladas](backup_sealed.md#sealed).

```bash
# A key pair: the private key into a file of its own (0600, never over a file), the public key printed
pipenv run ./dev.py backup keygen --identity-file ~/librefolio-backup-key.txt

# A sealed archive for that public key (twice --recipient while a key is being changed)
pipenv run ./dev.py backup create --recipient age1…

# The same, for the keys of LIBREFOLIO_BACKUP_RECIPIENTS
pipenv run ./dev.py backup create --sealed

# Check, restore or decrypt it where the private key is
pipenv run ./dev.py backup inspect librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt
pipenv run ./dev.py backup restore librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt --dry-run
pipenv run ./dev.py backup decrypt librefolio-backup-<date>-<time>.tar --identity-file ~/librefolio-backup-key.txt -o backup.zip
```

- 🗝️ **`keygen`** escribe la clave privada en el formato de `age-keygen` (`# created:`, `# public key: age1…`, luego `AGE-SECRET-KEY-1…`), legible solo por su propietario, y nunca sobre un archivo que exista (`❌ <path> already exists: a key file is never written over`). Después imprime `🔑 Public key, for --recipient or LIBREFOLIO_BACKUP_RECIPIENTS:` y la línea `age1…`. Ejecútalo en un ordenador tuyo, no en el servidor: la clave privada debe estar fuera del servidor.
- 🔏 **`create --recipient age1…`** sella para la clave indicada, `--recipient` dos veces para dos claves; **`create --sealed`** sella para las claves de `LIBREFOLIO_BACKUP_RECIPIENTS` ([Variables de entorno](configuration.md)). El archivo es `librefolio-backup-20261015-121500.tar`, con las reglas habituales de `-o` y de nombres. Después de las fases de un archivo seguro, la copia de seguridad muestra `… sealing`, y termina con `🔏 Sealed for 1 key: only the matching private key opens its password, and this server cannot.`
- 🔑 **No hay contraseña que dar.** `--sealed` y `--recipient` van sin `--encrypt`, `--password-file` y `--password-stdin`, y `--sealed` sin `--recipient`: el comando se detiene antes de que se escriba nada. No necesita terminal, así que se ejecuta desde cron tal cual; con Docker, `docker compose exec -T librefolio python dev.py backup create --sealed`.
- 🗝️ **Nunca la clave de instancia**, ni siquiera una generada por LibreFolio: a diferencia de un [archivo seguro](#backup-secure), uno sellado deja fuera `secrets/instance.key`.
- 💽 **Espacio.** El sellado escribe el `.tar` junto al `.lfbk`, así que la carpeta de trabajo en `backups/` necesita de nuevo el tamaño del `.lfbk`, más 64 MB, o la copia de seguridad se detiene con `backup_no_space`.
- 🔓 **`--identity-file`** abre un archivo sellado para `inspect`, `restore` y `decrypt`. Lee un archivo de clave tal como lo escribe `age-keygen`, antes de cualquier cambio de usuario, como hace `--password-file`: un secreto de Docker funciona. El comando comprueba el `.tar` y su manifiesto, abre la contraseña con la clave, la comprueba contra `backup.lfbk`, imprime `🔏 Sealed backup <path>: its password opened with <key file>`, luego copia `backup.lfbk` en una carpeta privada de la carpeta temporal del sistema, eliminada al final, y continúa como para un archivo seguro con su contraseña.
- ❌ Un `.tar` sin `--identity-file` se detiene con `sealed_backup_needs_key`; `--identity-file` con cualquier otro archivo se detiene con `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one`.
- 🧾 **Los rechazos**, cada uno al final de su mensaje: `sealed_identity_invalid` (el archivo de clave no contiene ninguna clave age, o no se puede leer), `sealed_no_identity` (ninguna clave del archivo abre la contraseña), `sealed_tar_invalid` (no son los tres archivos de un archivo sellado, en orden, como archivos ustar simples), `sealed_manifest_invalid` (su `manifest.json` no lo describe), `sealed_password_invalid` (lo que abrió la clave no es una contraseña que LibreFolio escriba), y luego los de un archivo seguro: `wrong_password` (esa contraseña no abre `backup.lfbk`) y `envelope_damaged`. Cada mensaje, con qué hacer: [Crear o abrir una copia de seguridad sellada](backup_moving.md#sealed-problems).

### 🧪 Probar una restauración sobre una copia {: #backup-restore-dry-run }

```bash
# Check an archive for a restore, on a copy: the instance stays as it is
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --dry-run
```

`backup restore --dry-run` extrae el archivo en una copia, la pone al día y la comprueba, y después te dice qué haría una restauración. La copia se crea en el directorio de datos, en `.restore/stage/<id>/`, y se elimina al final: nunca se tocan la base de datos ni los archivos de la instancia, así que el servidor puede seguir en ejecución. Sin `--dry-run`, la misma comprobación es la primera mitad de una restauración: consulta [Restaurar un archivo](#backup-restore).

Un [archivo seguro](#backup-secure) pide su contraseña primero, como hace `inspect`, y se descifra en la carpeta de la copia, como `.restore/stage/<id>/archive.zip`, que se elimina una vez extraído. Una comprobación interrumpida de golpe deja ese archivo descifrado, o su parte `archive.zip.part`: el siguiente arranque de LibreFolio lo elimina. Después, la comprobación pasa por seis pasos y se detiene en el primero que rechace el archivo:

1. **Un archivo de LibreFolio.** Solo se acepta un archivo escrito por LibreFolio, con su `manifest.json`: un directorio de datos comprimido a mano no lo es. Cada entrada se comprueba antes de escribir un solo byte: el manifiesto la enumera (o la anuncia, para la clave de instancia de un archivo seguro), es un archivo normal (no una carpeta, un enlace ni una entrada cifrada), su nombre aparece solo una vez, incluso ignorando mayúsculas y minúsculas, su tamaño es el del manifiesto, y el conjunto cabe en el espacio libre.
2. **Extraído.** Cada entrada se escribe en un archivo nuevo de la copia, nunca a través de un enlace ni sobre otro archivo, y su SHA-256 se compara con el del manifiesto. Después, antes de que nada más abra la copia, se lee el esquema de su base de datos, y no se ejecuta nada de él: si contiene un disparador, una vista o una tabla virtual —que LibreFolio nunca crea y cuyo SQL se ejecutaría durante la comprobación y en el servidor tras una restauración—, cualquiera de ellos hace que se rechace el archivo (`database_foreign_objects`).
3. **La revisión decide.** La revisión de migración (Alembic) de la base de datos, dada por el manifiesto y confirmada por la propia base de datos:
    - la propia revisión de este LibreFolio: la base de datos se restaura tal como está;
    - una más antigua: la copia se actualiza a la revisión de este LibreFolio, en un proceso propio, que se detiene si dura más de una hora;
    - una que este LibreFolio no conoce, muy probablemente de una versión más reciente: se rechaza con `revision_unknown`. Actualiza LibreFolio primero: una base de datos nunca se degrada.

    Después se ejecutan en la copia las [correcciones posteriores a la migración](cli_tools.md#post-migration-fixes), como en cada arranque.

4. **Comprobada antes y después.** Antes de la actualización, la copia pasa la comprobación de integridad de SQLite, contiene exactamente las filas que contó el manifiesto y no contiene texto que no sea UTF-8: LibreFolio nunca escribe ese texto, y el servidor no podría leer sus filas tras una restauración. Después, la copia vuelve a pasar la comprobación de integridad, en la revisión de este LibreFolio. Una migración puede cambiar datos, así que las filas que cambiaron son una advertencia, no un rechazo, y también lo son las referencias rotas (claves foráneas), que se conservan tal como están.
5. **Administradores.** El informe nombra a los administradores activos de la copia de seguridad. Sin ninguno, la restauración se bloquea: nadie podría gestionar la instancia después.
6. **Secretos guardados.** La instancia conserva su propia [clave de instancia](configuration_secrets.md#instance-key). Cuando el archivo incluye la clave que cifró sus secretos de complementos guardados, como la clave de API de una fuente de datos, o cuando proporcionas esa clave con `--instance-key-file` ([La clave de instancia de otra instalación](#backup-restore-instance-key)), se vuelven a cifrar en la copia con la clave de esta instancia; los demás se cuentan, para introducirlos de nuevo después de la restauración. Una copia sin secretos ni siquiera lee la clave de esta instancia.

Muestra los pasos a medida que avanza (`… decrypting` para un archivo seguro, `… checking`, `… unpacking`, `… upgrading`, `… verifying`), y luego su informe:

- 📦 Quién creó el archivo y cuándo (`Made by LibreFolio <version> (<how>) on <date> UTC`), y qué hace una restauración con la base de datos: `this LibreFolio's own: restored as it is`, o `upgraded on the copy to <revision> (<n> migrations)`, seguido de cada migración con la primera línea de su descripción.
- 🩹 Las correcciones posteriores a la migración que cambiaron algo en la copia, si las hubo.
- 🔢 Las filas, las tablas y el tamaño de la base de datos, y luego las tablas cuyas filas cambió la actualización, como `<table> (<before> → <after>)`, con `—` para una tabla que no existía.
- 📁 El número y el tamaño de los archivos; `Secure backup: decrypted with its password` para un archivo seguro; `Instance key: included` o `Instance key: not included`, o `Instance key: not included; given with --instance-key-file` con esa opción; y las claves guardadas de los proveedores de datos: `Saved provider keys: <n> re-encrypted with this instance's key`, y `⚠️ <n> saved provider keys cannot be read with this instance's key: enter them again after the restore` para aquellas que la clave del archivo, o la clave proporcionada, no leyó, o cuando no hay clave.
- ⚖️ Los totales de control del libro mayor: el efectivo de cada bróker en cada moneda y la cantidad de cada posición, sumados solo a partir de las transacciones, sin precio, tipo de cambio, coste ni fecha. La copia de seguridad los registró en su manifiesto, y la comprobación vuelve a leerlos en la copia una vez que está al día. Una diferencia es una advertencia, nunca un rechazo: una migración puede corregir datos. El informe dice una de estas cosas:
    - `Ledger totals: the same as when the backup was made`;
    - `⚠️ Ledger totals differ from the backup's (<n> lines):`, luego las líneas que difieren, primero el efectivo, como máximo 20: `broker <id>, <currency> cash: <before> → <after>` o `broker <id>, asset <id> quantity: <before> → <after>`, el importe de la copia de seguridad antes de la flecha y el de la copia después, con `—` para cero. `… and <n> more` cuenta las líneas omitidas;
    - `Ledger totals: not recorded in this archive`: un archivo creado por un LibreFolio anterior, de antes de los totales, no registra ninguno, ni tampoco uno cuyos totales no se pudieron leer cuando se creó;
    - `Ledger totals: recorded by another version of the method, not compared`;
    - `⚠️ Ledger totals: could not be read on the copy`.
- 👑 Los administradores, y lo que una restauración significará para todos: `After a restore you sign in with one of them, with the password of then; every session open now ends.` y `Invitations and links sent before the restore will have expired: send them again if needed.`
- ⚠️ Las advertencias, que permiten que la restauración continúe: `The upgrade changed the rows of some tables (listed above)`, `The backup's database has broken references: they are kept as they are`, `The upgrade added broken references to the copy`, `The ledger's totals differ from those the backup recorded (listed above)`, `The ledger's totals could not be read on the copy` o `Some currency codes in the backup are not ISO 4217 codes, names or numbers an earlier version saved: an edit of their rows is refused until they are corrected (./dev.py db currencies lists them after the restore)`, que explica [Códigos de moneda que no son códigos ISO](cli_tools.md).
- 👥 Una copia de seguridad con más cuentas activas de las que permite `LIBREFOLIO_MAX_USERS` añade una línea, impresa una vez, que no nombra ninguna cuenta ni dirección: `⚠️ The backup holds <n> active accounts; this instance accepts <m> (LIBREFOLIO_MAX_USERS): at the first sign-in the administrator chooses who keeps access, the others are deactivated (not deleted)`. Solo informa: `backup restore --yes` confirma y `--dry-run` sale con `0`, como con cualquier copia de seguridad.
- ⛔ El bloqueo, que lo impide: `❌ The backup has no active administrator: after a restore nobody could manage the instance`.

Termina con `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` y sale con `0`. Sale con `1` cuando se rechaza el archivo o se bloquea la restauración. Un rechazo es una línea, el motivo seguido de un código entre paréntesis, como `❌ The file is not a LibreFolio backup (not_a_backup)`, y no queda nada de la copia.

- 💽 La copia necesita espacio libre en el disco del directorio de datos: todo lo que contiene el archivo una vez extraído, más el doble del tamaño de su base de datos para la actualización, más 64 MB. `backup inspect` muestra esos tamaños; el archivo en sí se lee donde está, nunca se copia. Un archivo seguro también necesita espacio para su archivo descifrado, aproximadamente su propio tamaño, hasta que se extrae. Cuando el espacio es insuficiente, la comprobación se detiene antes de extraer nada, con el número de bytes que necesita (`no_space`); un disco que se llena durante la comprobación también la detiene.
- 📦 Lo que el archivo extrae tiene un límite cuando `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` establece uno («Opciones principales» en [Variables de entorno](configuration.md)). Los tamaños que declara el manifiesto se suman antes de comprobar el espacio libre, y un archivo que supera el límite se rechaza con `unpacked_too_large`, antes de extraer nada. `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` delante del comando lo elimina para ese comando: `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 pipenv run ./dev.py backup restore <archive>`, o `docker compose exec -e LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0 librefolio python dev.py backup restore <archive>` con Docker. Un límite que no se puede leer detiene el comando antes de `🔎 Checking … on a copy`, con el código de salida `1`: `❌ LIBREFOLIO_BACKUP_MAX_RESTORE_MB: expected a whole number of megabytes, 0 for no limit (backup_restore_unavailable)`.
- 🚦 Se comprueba un archivo a la vez: mientras se ejecuta otra comprobación, el comando se detiene con `❌ Another archive is being checked (from the web interface or another command): try again when it ends`.
- 🆕 Nunca usa la base de datos de la instancia: cualquier instalación puede comprobar un archivo, incluida una nueva, siempre que exista su directorio de datos (de lo contrario, `❌ No data directory at <path>`). Como con `-o`, una ruta relativa empieza en la raíz del proyecto.
- 🔗 Mantén `.restore/` y `.restore/stage/` como carpetas reales: un enlace, o un archivo, en su lugar detiene el comando con `❌ <path> is not a plain folder (a link, or a file): the copy is made in a folder of the data directory`.

??? note "❌ Rechazos — qué significan los códigos"

    | Código | Por qué se rechaza el archivo |
    | --- | --- |
    | `not_a_backup` | No es un zip, o es un zip sin el manifiesto que escribe LibreFolio, como un directorio de datos comprimido a mano |
    | `password_required` | Un archivo seguro y ninguna contraseña: no hay terminal donde preguntar, y ni `--password-file` ni `--password-stdin` |
    | `wrong_password` | La contraseña no abre el archivo seguro: no es con la que se creó, o se cambió el inicio del archivo |
    | `envelope_damaged` | El archivo seguro está dañado, cortado o se cambió después de crearse |
    | `envelope_unsupported` | El archivo seguro viene de un LibreFolio más reciente, o pide una configuración que este no acepta: actualiza LibreFolio primero |
    | `instance_key_unreadable`, `instance_key_invalid` | El archivo proporcionado con `--instance-key-file` no puede dar la clave, o la clave tiene menos de 32 caracteres: consulta [La clave de instancia de otra instalación](#backup-restore-instance-key) |
    | `archive_unreadable`, `archive_damaged` | El archivo no se puede leer, o el zip está dañado |
    | `manifest_newer_format` | El formato del archivo es más reciente que el que lee este LibreFolio: actualiza LibreFolio primero |
    | `manifest_invalid`, `manifest_unreadable`, `manifest_too_large` | El manifiesto está dañado o no es válido |
    | `unexpected_entry`, `missing_entry` | El archivo contiene una entrada que su manifiesto no enumera, o le faltan entradas que el manifiesto enumera; para la clave de instancia, una entrada que el manifiesto no anuncia, o una que anuncia y al archivo le falta |
    | `duplicate_entry` | Una entrada aparece dos veces, incluso cuando solo cambia el uso de mayúsculas y minúsculas de su nombre, o está donde debe estar la carpeta de otra entrada |
    | `not_a_file`, `encrypted_entry`, `unsupported_entry` | Una entrada es una carpeta o un enlace, está cifrada, o usa una compresión que LibreFolio no escribe |
    | `too_many_entries` | El archivo contiene más de 500.000 entradas |
    | `checksum_mismatch` | El tamaño o el SHA-256 de una entrada difiere del manifiesto: el archivo está dañado o se cambió |
    | `unpacked_too_large` | Una vez extraído, el archivo sería mayor de lo que esta instalación acepta para una restauración, según los tamaños que declara su manifiesto: `LIBREFOLIO_BACKUP_MAX_RESTORE_MB`. No se extrae nada |
    | `no_space` | No hay suficiente espacio libre para la copia |
    | `stage_failed` | No se pudo escribir la copia: el error impreso justo arriba indica la causa |
    | `database_damaged` | La base de datos de la copia de seguridad no pasa la comprobación de integridad de SQLite, antes o después de la actualización, SQLite no puede leer su esquema, o contiene texto que no es UTF-8 (otro programa escribió en ella, o se cambió) |
    | `database_foreign_objects` | La base de datos de la copia de seguridad contiene un disparador, una vista o una tabla virtual, que LibreFolio nunca crea: no la creó LibreFolio, o se cambió. Usa otra copia de seguridad |
    | `manifest_mismatch` | La base de datos de la copia de seguridad no es la que describe su manifiesto |
    | `revision_missing` | La base de datos de la copia de seguridad no registra ninguna revisión de migración |
    | `revision_unknown` | La copia de seguridad viene de un LibreFolio más reciente, o no de este: actualiza LibreFolio y vuelve a comprobarla |
    | `upgrade_failed` | La actualización de la copia falló o duró más de una hora (el error impreso justo arriba indica la causa), o no alcanzó la revisión de este LibreFolio |
    | `post_migration_failed` | Una corrección posterior a la migración falló en la copia: el error impreso justo arriba indica la causa |
    | `head_unknown` | Este LibreFolio no puede leer sus propios scripts de migración |

### ♻️ Restaurar un archivo {: #backup-restore }

```bash
# Check the archive on a copy, then restore it at the next start of the server
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

Sin `--dry-run`, `backup restore` ejecuta la misma comprobación sobre una copia y muestra el mismo informe ([Probar una restauración sobre una copia](#backup-restore-dry-run)). Cuando el archivo se puede restaurar, te pide confirmación:

```text
   Type "restore" to restore this archive at the next start of the server:
```

- ⌨️ Escribe `restore`, en minúsculas; los espacios alrededor no cuentan. Cualquier otra cosa, incluidos `Restore` o una línea vacía, termina con `Nothing restored: the copy was removed.` y el código de salida `1`.
- 🤖 `--yes` (`-y`) confirma sin preguntar. Sin un terminal donde preguntar, por ejemplo en un script, es obligatorio: de lo contrario, el comando se detiene con `❌ No terminal to ask on: add --yes to confirm the restore. Nothing restored: the copy was removed.` y sale con `1`. Un [archivo seguro](#backup-secure) también necesita allí su contraseña: añade `--password-file` o `--password-stdin`.

Una vez confirmado, el comando sale con `0` y dice:

```text
✅ The restore waits for the next start of the server: restart LibreFolio to apply it.
   That start replaces the database and the files, and ends every session: sign in with an administrator of the backup.
   ./dev.py backup pending shows it; ./dev.py backup pending --cancel drops it.
```

Todavía no ha cambiado nada: el servidor sigue en ejecución con sus datos, y la copia comprobada espera en `.restore/stage/<id>/`, por mucho tiempo que tarde. Reinicia LibreFolio cuando te convenga: detén todo el servidor y vuelve a [iniciarlo](cli_tools.md#start-the-server); con Docker, `docker compose restart librefolio` ([Hacer copias de seguridad con Docker](#backup-docker)). Si el servidor está detenido, su siguiente arranque aplica la restauración.

Ese arranque la aplica antes de leer ningún dato:

1. 🛑 **Solo un arranque de todo el servidor.** Cada proceso del servidor LibreFolio mantiene un bloqueo sobre el directorio de datos desde el principio de su arranque, antes de leer ningún dato, hasta que termina. Un arranque que lo encuentra retenido por otro proceso, como un worker que uvicorn inicia de nuevo junto a sus procesos hermanos en ejecución con `--workers`, o un segundo servidor sobre el mismo directorio de datos, deja la restauración esperando (`server_running`). Reinicia todo el servidor, nunca un solo worker. Un arranque que encuentra la restauración aplicada por otro servidor que aún se ejecuta, o por otro arranque, se detiene en lugar de servir datos cuya restauración no se ha completado.
2. 🔀 **El intercambio.** `sqlite/`, `custom-uploads/`, `broker_reports/` y `scenario_catalog/` de la instancia se intercambian con los de la copia. Cada movimiento es un cambio de nombre dentro del directorio de datos: instantáneo, sea cual sea el tamaño. Las carpetas propias de la instancia se apartan en `.restore/previous/`.
3. 🔒 **Qué permanece.** No se tocan `secrets/`, `logs/`, `scheduler_state.json` ni `backups/`: la instancia conserva su [clave de instancia](configuration_secrets.md#instance-key), sus registros y sus archivos.
4. ✅ **El primer arranque debe completarse.** El arranque continúa, sobre los datos restaurados, que la comprobación ya puso en la revisión de este LibreFolio. Una vez que lo consigue, antes de responder a nadie, termina todas las sesiones, revoca los enlaces de un solo uso de la copia de seguridad y elimina los datos anteriores de la instancia y la copia: la restauración ha terminado.
5. ↩️ **De lo contrario, todo como antes.** Si ese primer arranque falla, por una migración que falla o un archivo dañado, el siguiente arranque vuelve a poner los datos como estaban antes por sí solo, y registra la restauración como revertida, con el motivo ([Seguir o cancelar una restauración](#backup-pending)). Con Docker, el contenedor se reinicia solo tras un arranque fallido, así que los datos vuelven sin que hagas nada; si no hay nada que reinicie el servidor, inícialo tú mismo.

Después de la restauración:

- 🔑 Todos vuelven a iniciar sesión, en cada dispositivo, con una cuenta de la copia de seguridad y la contraseña que tenía entonces. El informe de la comprobación nombra a los administradores de la copia de seguridad.
- 🔗 Ningún enlace enviado antes de la restauración funciona ya (invitaciones, restablecimientos de contraseña, verificaciones de correo electrónico), ni siquiera los que la copia de seguridad aún contenía: envía nuevos.
- 📧 Una cuenta que la copia de seguridad contenía y que aún esperaba su verificación de correo electrónico también pierde su enlace, y deja de esperar: la página de inicio de sesión ya no puede enviarle otro enlace, y responde que la cuenta está desactivada. Un administrador la activa en [Usuarios e invitaciones](users.md#actions), y su dirección permanece sin verificar; o la elimina ([Eliminar una cuenta](users.md#delete)), para que su propietario se registre de nuevo y reciba un enlace nuevo. Esa cuenta nunca inició sesión, así que no contiene datos.
- 🆘 Si nadie recuerda la contraseña de entonces de un administrador, quien ejecute el servidor crea un enlace de restablecimiento con [`user reset-link`](cli_tools.md), o establece una nueva contraseña con `user reset`. Una vez iniciada la sesión, un administrador envía enlaces de restablecimiento a los demás desde [Usuarios e invitaciones](users.md#reset-links).

Conviene saber:

- 🚦 Una restauración a la vez: mientras una espera o se está aplicando, `backup restore` se detiene antes de la comprobación con `❌ A restore already waits for the next start: ./dev.py backup pending --cancel drops it (restore_already_pending)` y sale con `1`. También se detiene si no puede leer el estado de la restauración, ya que no puede saber si hay una esperando: `❌ The state of the restore cannot be read: <reason> (restore_state_unreadable)`, código de salida `1`, nada comprobado. `--dry-run` sigue funcionando.
- ❌ Si se rechaza la propia confirmación, el comando imprime una línea que termina con un código, elimina la copia y sale con `1`: `restore_stage_outdated` cuando LibreFolio se actualizó entre la comprobación y la confirmación, `restore_stage_expired` cuando la pregunta esperó más de 24 horas, `restore_already_pending` cuando se confirmó otra restauración mientras tanto. Vuelve a ejecutar el comando; después de `restore_stage_outdated`, comprueba el archivo de nuevo.
- 📍 Ejecútalo donde se ejecuta el servidor, en el contenedor con Docker: la restauración se registra para la ruta del directorio de datos, y un servidor que encuentra su directorio de datos en otra ruta no la aplica.
- 🔗 Mantén las cuatro carpetas como carpetas reales del directorio de datos: una que sea un enlace, o que esté montada por separado, no se puede intercambiar. El arranque entonces deja los datos como están, y registra la restauración como revertida con `swap_failed`.
- 💽 El intercambio no necesita espacio propio: la copia que hizo la comprobación pasa a ser los datos de la instancia, y los datos anteriores se eliminan una vez que se completa el primer arranque.
- 🗝️ La restauración conserva la clave de instancia de esta instalación. Cuando el archivo incluye la clave de la instalación que lo creó (un [archivo seguro](#backup-secure), cuando LibreFolio generó esa clave), la comprobación ya volvió a cifrar sus secretos guardados con la clave de esta instalación. Desde cualquier otro archivo de otra instalación, proporciona la clave de esa instalación con `--instance-key-file`, y la comprobación también los vuelve a cifrar ([La clave de instancia de otra instalación](#backup-restore-instance-key)). De lo contrario, no se pueden leer aquí: el informe los cuenta, para introducirlos de nuevo después de la restauración, a menos que vuelvas a poner primero la clave de esa instalación ([Secretos guardados y la clave de instancia](configuration_secrets.md#plugin-secrets)). Véase «La clave de instancia solo está en un archivo seguro» más arriba.

### 🗝️ La clave de instancia de otra instalación {: #backup-restore-instance-key }

```bash
# A clear archive of another installation, with the instance key of that installation
pipenv run ./dev.py backup restore /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip --instance-key-file ~/old-instance.key
```

Un archivo sin cifrar deja fuera la clave de instancia, y también lo hace uno seguro cuya clave vino del entorno: los secretos de complementos guardados que contiene, como la clave de API de una fuente de datos, solo se abren con la clave de la instalación que lo creó. `--instance-key-file FILE` da esa clave a `backup restore`, con o sin `--dry-run`: la comprobación vuelve a cifrar esos secretos en la copia con la clave de esta instancia, que permanece como está.

- 📄 El archivo contiene la clave de instancia de la instalación antigua: una copia de su `secrets/instance.key`, el archivo de su `LIBREFOLIO_INSTANCE_KEY_FILE` tal cual, o el valor de su `LIBREFOLIO_INSTANCE_KEY` escrito en un archivo tal como se escribió en la variable, incluidos los espacios. Solo se descartan una marca de orden de bytes al principio y los saltos de línea al final, como para `--password-file`: una clave que funcionaba como variable funciona igual en el archivo.
- 🔑 El comando lo lee primero, como el usuario que lo inició, antes de cambiar al propietario del directorio de datos, igual que lee `--password-file`: con `docker compose exec`, funciona un secreto de Docker que solo root puede leer. El archivo sigue la misma regla que `--password-file`, «Un archivo en el que el comando pueda confiar» en [Un archivo seguro](#backup-secure): mantenlo fuera del directorio de datos.
- 🙈 La clave nunca se imprime. Solo la línea de comandos la acepta: la interfaz web nunca acepta una clave, y una restauración desde Configuración › Administración › Copia de seguridad cuenta esos secretos como ilegibles.
- 📁 El informe dice `Instance key: not included; given with --instance-key-file`, y luego `Saved provider keys: <n> re-encrypted with this instance's key`.
- ℹ️ Un archivo que incluye su propia clave se restaura con ella, independientemente de lo que contenga el archivo de clave indicado con `--instance-key-file`: el informe añade `ℹ️ The archive carries its own instance key: --instance-key-file is not used`.
- ⚠️ Una clave que no lee ninguno de los secretos guardados no es la clave de la instalación que creó la copia de seguridad: el informe añade `⚠️ The key given with --instance-key-file reads none of the saved provider keys: it is not the key of the instance this backup came from`, antes de la línea que los cuenta, para introducirlos de nuevo después de la restauración. Cuando la propia clave de esta instancia no se puede usar, o cuando aún no tiene clave y la comprobación no puede crear una, como cuando no se puede escribir en `secrets/`, no se vuelve a cifrar nada, sea cual sea la clave proporcionada, y la línea es `⚠️ This instance's own key cannot be used, so nothing was re-encrypted with the key given: <problem>` en su lugar: el problema del `The instance key cannot be used: …` del registro de arranque («Comprobaciones de arranque» en [Variables de entorno](configuration.md)), o, sin clave, `<path>: there is no instance key yet, and it could not be created`. Los secretos que ya están bajo la clave de esta instancia, como en un archivo de esta misma instancia, se dejan como están, sea cual sea la clave proporcionada.
- ❌ Sale con `1`, antes de comprobar nada, cuando el archivo no puede proporcionar la clave: `❌ instance key file: <path> does not exist (instance_key_unreadable)`, o `cannot be read (…)`, `is empty or blank`, `is not UTF-8 text`, `is larger than 65536 bytes, too large for a secret`, `is not a regular file`, `goes through a link inside the data directory: give the file itself, from outside it`. Una clave de menos de 32 caracteres lo detiene antes de crear la copia: `❌ The instance key given is too short: an instance key has at least 32 characters (instance_key_invalid)`.

### ⏳ Seguir o cancelar una restauración {: #backup-pending }

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

`backup pending` no cambia nada y sale con `0`, excepto cuando no puede leer el estado de la restauración: consulta [Un estado de restauración ilegible](#backup-pending-unreadable) más abajo. `--json` y `--recover` están pensados para scripts: consulta [Para scripts](#backup-pending-json). En caso contrario, muestra una de estas cosas:

| Lo que imprime | Lo que significa |
| --- | --- |
| `ℹ️ No restore waits for the next start` | No se confirmó ninguna restauración, o se descartó la última |
| `⏳ A restore waits for the next start of the server`, luego `backup made by LibreFolio <version> on <date> UTC; confirmed by <who> on <date> UTC` | Confirmada, aún no aplicada. `<who>` es `cli` para este comando; en caso contrario, el nombre de usuario del administrador que la confirmó |
| `⏳ A restore is being applied by the server` | Un arranque la aplicó y aún no ha terminado. Si ese arranque murió, el siguiente vuelve a poner los datos |
| `✅ The last restore was applied on <date> UTC: backup made by LibreFolio <version> on <date> UTC` | La restauración ha terminado |
| `⚠️ The last restore was rolled back on <date> UTC, the data is as it was before: <reason> (<code>)` | La restauración se deshizo, por el motivo indicado abajo |

Cuando un arranque encontró una restauración esperando y no la aplicó, una línea más dice por qué, y la restauración sigue esperando:

- `⚠️ At the last start a backup was running: the next start applies it (backup_running)`: había una copia de seguridad en ejecución cuando se inició el servidor, por ejemplo un `backup create` desde la línea de comandos.
- `⚠️ It was confirmed for another data directory (<path>): this one does not apply it (other_data_directory)`: el servidor encontró su directorio de datos en otra ruta distinta de donde se confirmó la restauración, como una copia del directorio de datos. Descártala con `--cancel` y luego ejecuta `backup restore` donde se ejecuta el servidor.
- `⚠️ At the last start another server process was serving the data directory: restart the whole server to apply it (server_running)`: se inició de nuevo un worker mientras los demás seguían sirviendo (`--workers`), o otro servidor usa el mismo directorio de datos. Reinicia todo el servidor.

| Código | `<reason>` | Qué hacer |
| --- | --- | --- |
| `first_start_failed` | `the first start after it did not complete` | El registro de ese arranque contiene la causa |
| `swap_interrupted` | `the start that applied it was interrupted` | Nada: un arranque se detuvo durante el intercambio, y el siguiente lo deshizo |
| `swap_failed` | `its folders could not be moved into place` | Convierte las cuatro carpetas en carpetas reales del directorio de datos, ni enlaces ni montajes separados |
| `stage_missing` | `its checked copy was gone` | La copia en `.restore/stage/` se eliminó o cambió: comprueba el archivo de nuevo |

Una reversión también elimina los datos restaurados y la copia: para intentarlo de nuevo, vuelve a ejecutar `backup restore`. Si incluso volver a poner los datos falla, por ejemplo por un error de disco o de permisos, LibreFolio no arranca: su registro contiene `The data directory is half restored: the restore could not be undone, and LibreFolio does not start on it`, y cada arranque lo intenta de nuevo.

#### 🧩 Un estado de restauración ilegible {: #backup-pending-unreadable }

El estado de la restauración, `.restore/restore.json`, puede volverse ilegible: cambió su propietario o sus permisos, un error de disco, un enlace o una carpeta en su lugar, o contenido que LibreFolio no escribió. Entonces una restauración puede haberse detenido a mitad, y LibreFolio no puede saber qué datos contiene. `backup pending` lo indica y sale con `1`:

```text
❌ The state of the restore cannot be read: <why>: a restore may have stopped half way. LibreFolio serves no data until you choose (restore_state_unreadable: <reason>)
   The data of before is kept in .restore/previous/: sqlite, user_files
   Checked copies kept: 1 (none is removed while the state cannot be read)
👉 Stop LibreFolio, then run ./dev.py backup pending --recover previous: it puts the data of before back.
```

`<reason>` es `io` (el sistema de archivos lo rechaza: devuelve `.restore/` y sus archivos al usuario que ejecuta LibreFolio y luego vuelve a ejecutar `backup pending`, lo que puede bastar), `not_a_file` o `invalid`. Mientras el estado no se pueda leer, no se elimina ninguna copia comprobada, ni por la limpieza del servidor ni por Configuración › Administración › Copia de seguridad, y no se puede confirmar ninguna restauración.

`backup pending --recover previous`, con LibreFolio detenido, vuelve a poner los datos de antes a partir de lo que indican las carpetas: cada carpeta conservada en `.restore/previous/` vuelve a su sitio, y la que reemplaza va a `.restore/failed/`. Una restauración que se completó no conservó datos de antes, así que sus datos permanecen. El estado ilegible se conserva como `.restore/restore.json.unreadable-<date>` para echar un vistazo, y nunca se vuelve a leer. Después, inicia LibreFolio con los datos de antes, o vuelve a restaurar una copia de seguridad con `backup restore`. Mientras LibreFolio se ejecuta, se detiene con `(restore_in_use)` y sale con `5`; con un estado que puede leer, o ninguno, se detiene con `(restore_nothing_to_recover)` y sale con `3`: los códigos de salida son la tabla de [Para scripts](#backup-pending-json). Ejecutado dos veces, la segunda ejecución no cambia nada.

`--cancel`, lo mismo que `--recover cancel` pero con los códigos de salida de abajo, descarta la restauración en espera, junto con su copia comprobada, quienquiera que la haya confirmado: `✅ The restore waiting for the next start was dropped, with its copy: the data stays as it is`, código de salida `0`. Si la copia no se puede eliminar, por ejemplo por un error de permisos o de disco, la restauración se descarta de todos modos, código de salida `0`, con dos líneas en su lugar: `✅ The restore waiting for the next start was dropped: the data stays as it is` y `⚠️ Its checked copy could not be removed: it goes when its check expires`. Cuando la eliminación falló con un error, el registro anterior contiene la advertencia `The copy of a cancelled restore could not be removed: it goes when its check expires`; una copia que queda sin error, como una que contiene una carpeta de solo lectura, no tiene ninguna. LibreFolio lo intenta de nuevo en su primer arranque cuando la comprobación tiene 24 horas. Si la propia restauración no se puede descartar, por un error del sistema de archivos antes de que lo haga (su bloqueo, o la eliminación de su estado): `❌ The restore could not be cancelled: <reason>. It still waits for the next start (restore_cancel_failed)`, código de salida `1`. Cuando el estado de la restauración no se puede leer: la línea `restore_state_unreadable` de `backup pending`, código de salida `1`. Cuando no espera ninguna restauración, o ya se está aplicando una: `❌ No restore waits for the next start: nothing to cancel (restore_not_pending)`, código de salida `1`.

#### 🤖 Para scripts: --json y --recover {: #backup-pending-json }

Un script, o una máquina que accede al servidor por `ssh`, lee el estado con `--json` y actúa con `--recover CHOICE`. Ambos están pensados para ejecutarse sin una persona: nunca se pregunta nada en el terminal, y los códigos de salida son fijos.

**La línea JSON.** Con `--json`, `backup pending` escribe exactamente una línea en stdout: un objeto JSON, luego un salto de línea, sin color. Todo lo que diría de otro modo, y las líneas de registro de LibreFolio, van a stderr. Sale con `0` siempre que se haya impreso la línea: un estado ilegible es un estado, no un fallo.

| Clave | Valor |
| --- | --- |
| `state` | `none`, `pending`, `in_progress`, `committed`, `rolled_back` o `unreadable` |
| `reason` | Por qué: el motivo de reversión de un estado `rolled_back` (`first_start_failed`, `swap_interrupted`, `swap_failed`, `stage_missing`), o `io`, `not_a_file`, `invalid` para uno `unreadable`; `null` en caso contrario |
| `waiting` | Por qué un arranque no aplicó una restauración que espera: `backup_running`, `other_data_directory`, `server_running`, o `null` |
| `backup_created_at` | Cuándo se creó la copia de seguridad de la restauración, como `2026-10-23T03:00:12Z` (UTC); `null` sin estado, o con uno ilegible |
| `safety_copy` | `{"present": true, "at": "<date>Z"}` cuando los datos anteriores a un intercambio se conservan en `.restore/previous/`; en caso contrario, `{"present": false, "at": null}` |
| `choices` | Las palabras que `--recover` acepta ahora, en la tabla de abajo |

Después de un `--recover`, la línea describe el estado **después** de él y añade `recover`, `{"choice": "<word>", "done": true}` o `false`, y, cuando el código de salida no es `0`, `error`, la palabra de la tabla de códigos de salida.

| `state` | Significa | `choices` |
| --- | --- | --- |
| `none` | No se confirmó ninguna restauración, o se descartó la última | ninguna |
| `pending` | Una restauración espera el siguiente arranque | `cancel` |
| `in_progress` | Un arranque la está aplicando, o la ha aplicado y aún no ha terminado | ninguna |
| `committed` | La última restauración está completada | ninguna |
| `rolled_back` | La última restauración se deshizo, con su `reason` | ninguna |
| `unreadable` | El estado de la restauración no se puede leer: [Un estado de restauración ilegible](#backup-pending-unreadable) | `previous` |

```json
{"state":"unreadable","reason":"invalid","waiting":null,"backup_created_at":null,"safety_copy":{"present":true,"at":"2026-10-23T03:00:12Z"},"choices":["previous"]}
{"state":"pending","reason":null,"waiting":"server_running","backup_created_at":"2026-10-22T21:30:05Z","safety_copy":{"present":false,"at":null},"choices":["cancel"]}
```

La línea nunca contiene un nombre de usuario, un correo electrónico, una ruta ni un identificador: quién confirmó la restauración, el directorio de datos y la copia comprobada no están en ella. `safety_copy.at` es el momento en que se aplicó la restauración o, con un estado ilegible, cuándo cambió por última vez `.restore/previous/`.

**Los códigos de salida.** `--recover previous` vuelve a poner los datos de antes cuando el estado no se puede leer, con LibreFolio detenido; `--recover cancel` descarta la restauración en espera, junto con su copia comprobada. Los códigos de salida son los mismos con o sin `--json`:

| Salida | Cuándo | `error` en la línea |
| --- | --- | --- |
| `0` | Hecho: los datos de antes están de vuelta, o se descartó la restauración en espera | ninguno |
| `2` | Un error de uso: `--recover` sin una elección, `--recover` con `--cancel`, o `--json` con `--cancel` (usa `--recover cancel`) | ninguno: la línea no se escribe |
| `3` | Nada que recuperar: no hay estado de restauración, o la elección ya se aplicó. | `nothing_to_recover` |
| `4` | La elección no es válida en este estado, como `previous` mientras el estado se puede leer, `cancel` mientras no se puede, o una palabra que no es una elección: nada cambia | `choice_not_valid` |
| `5` | Falló: LibreFolio se está ejecutando en este directorio de datos (`restore_in_use`), no se pudo mover una carpeta de vuelta (`restore_apply_failed`), no se pudo descartar la restauración (`failed`): no se declara nada como hecho. Con un directorio de datos que falta, también `5`, pero no se escribe ninguna línea: stdout queda vacío y stderr dice por qué | `restore_in_use`, `restore_apply_failed` o `failed` |

Ejecutada de nuevo, una elección no cambia nada: el segundo `--recover previous` no encuentra ningún estado ilegible, no mueve ninguna carpeta, no añade nada a `.restore/failed/` y sale con `3`; lo mismo hace un segundo `--recover cancel`. Por lo tanto, un script puede repetir `previous` o `cancel` hasta que lea `0` o `3`.

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

```bash
# The zip inside a secure archive, to use it by hand
pipenv run ./dev.py backup decrypt /mnt/nas/librefolio/librefolio-backup-20261015-121500.lfbk -o /mnt/nas/librefolio/librefolio-backup-20261015-121500.zip
```

`backup decrypt` escribe el zip que contiene un [archivo seguro](#backup-secure): el archivo que `backup create` escribe sin contraseña, con `secrets/instance.key` cuando el archivo seguro incluye la clave. `inspect` y `restore` aceptan ese zip como cualquier otro, y su clave sigue volviendo a cifrar los secretos guardados. Para restaurar un archivo seguro, no necesitas descifrarlo: `backup restore` acepta el `.lfbk` tal como está.

- 🔑 Pide la contraseña una vez, o la lee con `--password-file` o `--password-stdin` ([Un archivo seguro](#backup-secure)).
- 🆕 `-o` (`--output`) es obligatorio, y es el archivo del zip: no debe existir todavía. Uno que exista se rechaza antes de pedir la contraseña, `❌ <path> already exists: choose another name`, y no se escribe nada. Como con `create`, una ruta relativa empieza en la raíz del proyecto.
- 🔒 El zip contiene los datos de todos los usuarios en claro, y solo su propietario puede leerlo (`0600`): el usuario que ejecutó el comando, o el usuario del servidor cuando el comando cambió a él. Termina con `✅ Decrypted: <path> (<size>)` y `🔒 It holds every user's data in clear: keep it private, and remove it once used.` Cuando el archivo seguro incluye la clave de instancia, una última línea añade `🔑 It also holds the instance key: with it, every saved provider key can be read.`
- 🟢 No necesita un directorio de datos, y funciona con el servidor en ejecución o detenido. Cuando existe uno y lo ejecutas como root, como con `docker compose exec`, lee primero un `--password-file`, como root (funciona un secreto de Docker propiedad de root), y luego cambia al propietario del directorio de datos, como hacen los demás comandos: el zip pasa entonces a pertenecer al usuario del servidor, y `-o` debe ser un lugar donde ese usuario pueda escribir ([Hacer copias de seguridad con Docker](#backup-docker)). Si no puede cambiar, se detiene antes de leer el archivo o de pedir la contraseña, con el mensaje de los demás comandos: `❌ cannot switch to the owner of <path> (<uid>:<gid>): <reason>. Run the command as that user.`
- ❌ Sale con `1` cuando no puede leer el archivo, como un archivo que solo root puede leer una vez que el comando se ejecuta como el usuario del servidor (`❌ Cannot read <path>: <reason> (archive_unreadable)`, antes de pedir la contraseña), cuando no es un archivo seguro (`❌ <path> is not a secure backup: a plain .zip needs no decrypting (not_an_envelope)`), cuando la contraseña no lo abre (`wrong_password`), cuando está dañado (`envelope_damaged`: no queda nada en `-o`) o viene de un LibreFolio más reciente (`envelope_unsupported`), y cuando no puede escribir en `-o` (`❌ Cannot write <path>: <reason>`, una vez dada la contraseña: no queda nada allí).

### 🚚 Usar un archivo en otra instalación

[`backup restore`](#backup-restore) restaura un archivo en la instalación donde lo ejecutas, y conserva el `secrets/` de esa instalación. Para iniciar otra instalación con los datos de un archivo manualmente, con el `secrets/` de la instalación que lo creó, como cuando trasladas LibreFolio:

1. **Detén LibreFolio** en la instalación que recibe los datos.
2. **Descomprime el archivo en un [directorio de datos](filesystem.md) vacío** (`LibreFolio-data/` con Docker Compose): si contiene algo, muévelo aparte primero. Nada de los datos antiguos debe mezclarse con los del archivo, ni siquiera `app.db-wal` y `app.db-shm` de SQLite. Un archivo seguro se descifra primero en su zip ([Descifrar un archivo seguro](#backup-decrypt)).
3. **Vuelve a poner `secrets/`** en el directorio de datos, desde la copia que guardaste por separado. El zip de un archivo seguro que incluye la clave ya trae `secrets/instance.key`: da a la carpeta el modo `0700` y al archivo `0600` (`chmod`), o el registro de arranque tendrá una advertencia.
4. **Inicia LibreFolio**, la versión que creó el archivo o una más reciente: las migraciones pendientes se ejecutan solas al arrancar.

Conviene saber:

- 🧪 Antes del paso 1, comprueba el archivo en la instalación que lo recibe, con `backup restore <archive> --dry-run` ([Probar una restauración sobre una copia](#backup-restore-dry-run)): sin cambiar nada, te dice si ese LibreFolio puede aceptar el archivo, qué migraciones aplicará su arranque y con qué administradores iniciarás sesión.
- ⛔ LibreFolio nunca degrada una base de datos: un archivo creado por una versión más reciente necesita esa versión o una más reciente, y una más antigua no arranca con él. `backup inspect` muestra qué versión creó el archivo, y `backup restore --dry-run` rechaza ese archivo con `revision_unknown`.
- 🧹 El `manifest.json` que queda en la raíz del directorio de datos es inofensivo: puedes eliminarlo.
- 👤 Con Docker, el contenedor asigna el directorio de datos a su usuario en cada arranque, así que el propietario de los archivos descomprimidos no importa. En una instalación en el host, descomprime como el usuario que ejecuta LibreFolio, para que los archivos le pertenezcan.
- 🗝️ La clave de un archivo seguro solo funciona donde no estén establecidas ni `LIBREFOLIO_INSTANCE_KEY` ni `LIBREFOLIO_INSTANCE_KEY_FILE`: una clave establecida allí prevalece sobre `secrets/instance.key`. Nunca la pongas en lugar de una clave ya en uso: lo que se guardó bajo esa clave se volvería ilegible. Una instalación con su propia clave acepta el archivo con [`backup restore`](#backup-restore), que vuelve a cifrar los secretos guardados.

### 🐳 Hacer copias de seguridad con Docker {: #backup-docker }

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

- 👤 `docker compose exec` se ejecuta como root: el comando cambia al propietario del directorio de datos, incluido `backup decrypt`, así que todo lo que escribe pertenece al usuario del servidor. Si no puede cambiar, se detiene y te pide que lo ejecutes como ese usuario: `docker compose exec --user <uid>:<gid> librefolio python dev.py backup create`, con los números del mensaje.
- 📂 `-o` y los archivos de `inspect` y `restore` son rutas dentro del contenedor, donde el directorio de datos es `/app/backend/data/prod-docker`. El archivo que imprimió `backup create` está en una carpeta propia allí, como `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`. Para comprobar un archivo que está en el host, cópialo primero en `LibreFolio-data/`, por ejemplo en `LibreFolio-data/backups/`. Para escribir el archivo en otro lugar que no sea `LibreFolio-data/backups/`, usa una carpeta montada desde el host en la que el usuario del servidor pueda escribir: en cualquier otro lugar, permanece dentro del contenedor y se pierde cuando se recrea el contenedor.
- 🔑 `restore` y `decrypt` también leen el archivo como el usuario del servidor: un archivo que escribió `backup create` está bien, pero uno que hayas copiado tú mismo debe ser legible por ese usuario, o se detienen con `archive_unreadable`. Con la imagen oficial, `sudo chown 1000:1000 <archive>` en el host se lo asigna a ese usuario.
- ⌨️ `docker compose exec` da al comando un terminal donde preguntar. Sin uno, como con `docker compose exec -T` en un script, añade `--yes`.
- 🔐 Para un [archivo seguro](#backup-secure), `--encrypt` pide la contraseña en ese terminal. Con `-T`, por ejemplo desde cron, proporciónala con `--password-file` y un secreto de Docker, como `/run/secrets/backup_password`: [el ejemplo](backup_restore.md#command-line) de Copia de seguridad, restauración y traslado de la instancia muestra las líneas que hay que añadir a `docker-compose.yml`. `backup decrypt` también cambia al usuario del servidor, así que su zip pertenece a ese usuario: dale un `-o` en el que ese usuario pueda escribir, en `LibreFolio-data/backups/` o en una carpeta montada desde el host, como `docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip`.
- 🔏 Un [archivo sellado](#backup-sealed) no necesita terminal: `docker compose exec -T librefolio python dev.py backup create --sealed` lee `LIBREFOLIO_BACKUP_RECIPIENTS` del entorno del contenedor, que `env_file: .env` rellena; tras un cambio de `.env`, `docker compose up -d` recrea el contenedor con él. Para abrir uno en el contenedor, da a `--identity-file` una ruta dentro de él; mejor, ábrelo en tu ordenador, donde está la clave privada ([Abrir una copia de seguridad sellada](backup_sealed.md#sealed-open)).
- 🔁 Después de un primer arranque que falla con los datos restaurados, el contenedor se reinicia solo (`restart: unless-stopped`, en ambos archivos compose que distribuye LibreFolio), y ese arranque vuelve a poner los datos como estaban antes.
- 🔒 En el host, los archivos pertenecen al usuario del contenedor, y solo ese usuario puede leerlos: si tu usuario del host es otro, cópialos con `sudo cp -a`.
- 💻 Desde una copia del código fuente, `./dev.py docker exec backup create` hace lo mismo.

---

## 🔗 Relacionado

- 📄 **[Herramientas de línea de comandos](cli_tools.md)** — Iniciar el servidor, gestionar usuarios, mantener la base de datos, …
