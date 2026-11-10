# 🏠 Copias de seguridad: traslado y solución de problemas

Esta página de la guía de copias de seguridad trata del **traslado** de LibreFolio de una instalación a otra (de un alojamiento a un servidor propio, o al revés) y de qué hacer **cuando algo va mal** con una copia de seguridad o una restauración.

El resto de la guía comienza en [Copia de seguridad, restauración y traslado de tu instancia](backup_restore.md).

---

## 🏠 Lleva tu LibreFolio a casa {: #bring-home }

Un archivo traslada tu LibreFolio de una instalación a otra. Hay dos vías:

| Vía | Cuándo | Dónde |
| --- | --- | --- |
| **Restauración** | La restauración comprueba el archivo sobre una copia antes de que cambie nada; con Docker toma tal cual una copia de seguridad segura (`.lfbk`), y es la vía más sencilla | Configuración › Administración › Copia de seguridad, o `backup restore` ([Restaurar en esta instalación](backup_restore.md#restore)) |
| **A mano** | La carpeta de datos del destino está vacía, o aún no existe: descomprime allí el zip antes del primer inicio | Terminal del servidor de destino, [más abajo](#by-hand) |

En ambos casos, el destino ejecuta la misma versión de LibreFolio o una más reciente ([Nunca hacia atrás](#never-backwards)).

### ✋ A mano: descomprime antes del primer inicio {: #by-hand }

Ten esto presente antes de empezar:

- 🔎 **Nada comprueba el archivo de antemano.** Un archivo dañado, o uno de un LibreFolio más reciente, se manifiesta cuando falla el inicio, y algunos daños solo más tarde, cuando una página lee los datos que toca. Una restauración lo comprueba sobre una copia antes de que cambie nada. Para comprobar un archivo antes de descomprimirlo a mano, usa una instalación de LibreFolio que **ya esté en ejecución**: `backup inspect <archive>` compara cada fichero con el manifiesto y, para un zip, no escribe nada; `backup restore <archive> --dry-run` hace toda la comprobación de una restauración, sobre una copia («Comprobar un archivo» y «Probar una restauración sobre una copia» en [Herramientas de administración de CLI](cli_tools.md)). El ensayo en seco funciona en la carpeta de datos de esa instalación: nunca lo apuntes a la carpeta vacía que estás a punto de llenar.
- 📖 Los pasos para cualquier instalación, incluida la del host: «Usar un archivo en otra instalación» en [Herramientas de administración de CLI](cli_tools.md).

Los pasos, con Docker Compose:

1. **Servidor de origen — Configuración › Administración › Copia de seguridad, o terminal.** Haz una copia de seguridad y llévala al servidor de destino ([Hacer una copia de seguridad](backup_restore.md#create)). Si es una copia sin cifrar, lleva también la carpeta `secrets/` de su carpeta de datos: el archivo no la contiene.

    Resultado: el archivo (`.zip` o `.lfbk`) está en el servidor de destino.

2. **Servidor de destino — terminal, carpeta de `docker-compose.yml`.** La carpeta de datos `LibreFolio-data` debe estar vacía, o no existir todavía. Si LibreFolio ya se ha iniciado sobre ella, deténlo (`docker compose down`) y mueve `LibreFolio-data` a otro sitio primero.

    Resultado: ningún otro dato se mezcla con los del archivo.

3. **Solo para una copia de seguridad segura (`.lfbk`) — terminal de una instalación donde esté disponible la línea de comandos de LibreFolio.** Un `.lfbk` no es un zip: conviértelo en su zip con `backup decrypt`.

    ```bash
    # Host installation
    pipenv run ./dev.py backup decrypt librefolio-backup-20261015-121500.lfbk -o librefolio-backup-20261015-121500.zip

    # Docker, in a running LibreFolio container: the paths inside it, and the zip where the container's user can write
    docker compose exec librefolio python dev.py backup decrypt /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.lfbk -o /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500.zip
    ```

    Resultado: el zip que descomprimirás en el paso 4. Ten esto presente:

    - 🔓 La contraseña se pide en el terminal, o se lee con `--password-file` o `--password-stdin`.
    - 🚫 Se rechaza un `-o` que ya exista, y no se escribe nada: el comando nunca reemplaza un fichero.
    - 🔒 Solo el propietario puede leer el zip (`0600`): el usuario que ejecutó el comando o, con Docker, el usuario del contenedor.
    - 🗑️ El zip contiene los datos de todos los usuarios en claro: bórralo una vez descomprimido.
    - 🔑 Si la copia de seguridad contiene la clave de la instancia, el comando añade `🔑 It also holds the instance key: with it, every saved provider key can be read.`: quien tenga ese zip también puede leer las claves guardadas de los proveedores de datos.

4. **Servidor de destino — terminal, carpeta de `docker-compose.yml`.** Descomprime el zip en la carpeta de datos.

    ```bash
    # In the folder of docker-compose.yml, before the first start
    unzip librefolio-backup-20261015-121500.zip -d LibreFolio-data
    ```

    Resultado: `LibreFolio-data/` contiene los datos del archivo. El `manifest.json` que queda allí es inofensivo: puedes eliminarlo.

5. **Servidor de destino — carpeta `LibreFolio-data/secrets/`.** Antes del primer inicio:

    - 🗝️ **Copia de seguridad sin cifrar**: vuelve a poner el `secrets/` del servidor de origen en `LibreFolio-data/`, y los secretos guardados seguirán siendo legibles. Sin él, LibreFolio crea una nueva clave de instancia la primera vez que necesita una.
    - 🔐 **Copia de seguridad segura que lleva la clave**: el zip ya contiene `secrets/instance.key`, y las claves guardadas de los proveedores de datos siguen siendo legibles. Haz privadas la carpeta y el fichero, o el registro de inicio tendrá una advertencia («Comprobaciones de inicio» en [Variables de entorno](configuration.md)):

    ```bash
    chmod 700 LibreFolio-data/secrets
    chmod 600 LibreFolio-data/secrets/instance.key
    ```

    Resultado: la clave de la instancia está en su sitio, y nada en el registro de inicio habla de ella.

    !!! warning "⛔ La clave de una copia de seguridad, solo en una carpeta de datos vacía"

        Usa la clave de una copia de seguridad solo así: en una carpeta de datos vacía, en una instalación que no establezca ni `LIBREFOLIO_INSTANCE_KEY` ni `LIBREFOLIO_INSTANCE_KEY_FILE`. Una clave establecida allí prevalece sobre `secrets/instance.key`, y las claves guardadas de los proveedores de datos quedarían ilegibles.
        Nunca la pongas en lugar de una clave ya en uso: lo que se guardó con esa clave quedaría ilegible. Para llevar una copia de seguridad segura a una instalación que tiene su propia clave, restáurala: la restauración vuelve a cifrar las claves guardadas con la clave de esa instalación.

6. **Servidor de destino — terminal, carpeta de `docker-compose.yml`.** Primer inicio, con la misma imagen que el origen o una más reciente.

    ```bash
    docker compose up -d
    ```

    Resultado: el inicio aplica por sí mismo las migraciones pendientes.

### ⛔ Nunca hacia atrás {: #never-backwards }

LibreFolio nunca hace retroceder una base de datos a una versión anterior: usa la versión que creó el archivo, o una más reciente. Un LibreFolio más antiguo rechaza un archivo cuya base de datos contiene una migración que no conoce.

- 🏷️ `backup inspect` muestra qué versión creó el archivo (`Made by LibreFolio <version>`); **Configuración › Acerca de** muestra la versión de una instancia.
- ❌ `backup restore` rechaza tal archivo con `revision_unknown`, antes de que cambie nada.
- 🛑 A mano, un LibreFolio más antiguo no se inicia sobre tales datos: el registro contiene `Failed to apply database migrations`, y Docker no deja de reiniciar el contenedor. Deténlo con `docker compose down`.

Actualiza primero el LibreFolio receptor ([Actualizar LibreFolio](../user/installation.md#updating)), y después restaura. Con Docker, la imagen `latest` es la versión más reciente.

---

## 🧯 Cuando algo va mal {: #troubleshooting }

### 🔐 Crear una copia de seguridad segura {: #secure-problems }

| Qué ves | Por qué | Qué hacer |
| --- | --- | --- |
| `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)` | `backup create --encrypt` sin un terminal donde preguntar, como en cron | Da la contraseña con `--password-file` o `--password-stdin` ([Desde la línea de comandos](backup_restore.md#command-line)) |
| `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: …)`, o en Configuración › Administración › Copia de seguridad *La contraseña no cumple las reglas de la contraseña de una copia.* | Las reglas se enumeran después de `password_too_weak:`. En Configuración, **Crear copia de seguridad** sigue desactivado hasta que se cumpla cada regla; si las reglas de una copia de seguridad no vinieron del servidor (`GET /api/v1/backup/instance/options`), el medidor aplica las de la contraseña de una cuenta (8 caracteres), y el servidor sigue rechazando una de menos de 12 | Elige una contraseña más larga que cumpla todas las reglas. No se escribió nada |
| `❌ The two passwords differ (password_mismatch)` | La segunda contraseña escrita en el terminal no es la primera | Ejecuta el comando de nuevo |
| `❌ password file: <path> does not exist (password_unreadable)`, o `cannot be read`, `is empty or blank`, `is not UTF-8 text` | `--password-file` no puede proporcionar la contraseña | Corrige el fichero: solo la contraseña, en UTF-8. Con Docker, la ruta dentro del contenedor, como `/run/secrets/backup_password` |
| `⚠️ The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore`, o en Configuración › Administración › Copia de seguridad *La clave de la instancia no se puede usar: la copia se hizo sin ella, así que tras una restauración habrá que volver a introducir las claves de los proveedores de datos.* | `secrets/instance.key` está ahí, pero dañada o fuera de alcance, o tiene más de los 4096 bytes que una restauración puede volver a leer (la clave que genera LibreFolio tiene 43 caracteres). La copia de seguridad está completa, sin la clave | Si el registro de inicio dice qué le pasa a la clave, corrígelo («Comprobaciones de inicio» en [Variables de entorno](configuration.md)) y luego haz una nueva copia de seguridad segura. Si no dice nada, la clave es demasiado larga para viajar: guarda una copia de `secrets/` con la copia de seguridad, como para una copia sin cifrar |

### 🧾 La comprobación rechaza el archivo {: #check-refused }

`backup restore`, con o sin `--dry-run`, termina con un rechazo y su código entre paréntesis, sin cambiar nada. Configuración › Administración › Copia de seguridad rechaza los mismos archivos y lo explica en la tarjeta, sin el código: *El archivo está dañado.* para `archive_damaged`, por ejemplo.

| Código | Por qué | Qué hacer |
| --- | --- | --- |
| `revision_unknown` | El archivo viene de un LibreFolio más reciente | Actualiza esta instalación ([Nunca hacia atrás](#never-backwards)) y luego ejecuta el comando de nuevo |
| `manifest_newer_format` | El formato del archivo es más reciente que el que lee este LibreFolio | Actualiza LibreFolio primero |
| `checksum_mismatch`, `archive_damaged`, `missing_entry` | El archivo está dañado, cortado o se modificó | `backup inspect` nombra las entradas que difieren. Copia de nuevo el archivo desde donde lo guardes, o usa otro |
| `database_damaged` | La base de datos no pasa la comprobación de integridad de SQLite, SQLite no puede leer su esquema, o contiene texto que no es UTF-8. Configuración › Administración › Copia de seguridad: *La base de datos de la copia de seguridad está dañada: no se puede restaurar.* | Copia de nuevo el archivo desde donde lo guardes, o usa otro. Texto que no es UTF-8 significa que otro programa escribió en la base de datos (LibreFolio nunca la escribe), o que se modificó el archivo |
| `database_foreign_objects` | La base de datos contiene un disparador, una vista o una tabla virtual, que LibreFolio nunca crea. Configuración › Administración › Copia de seguridad: *La base de datos de la copia de seguridad contiene disparadores, vistas u otros objetos que LibreFolio nunca crea: no procede de LibreFolio, o ha sido modificada, y no se puede restaurar.* | El archivo no lo creó LibreFolio, o se modificó después: usa otra copia de seguridad |
| `not_a_backup` | No es un archivo que haya escrito LibreFolio, como una carpeta de datos comprimida a mano | Vuelve a poner tal copia [a mano](#by-hand), en una carpeta de datos vacía |
| `sealed_backup_needs_key` | Una copia de seguridad nocturna sellada (`.tar`): su contraseña está dentro, cifrada para una clave que la comprobación no tiene. Configuración › Administración › Copia de seguridad: *Esta es una copia de seguridad sellada de un panel de alojamiento: su contraseña está cifrada para la clave del proveedor. Extrae backup.lfbk, abre password.age con age y luego restaura backup.lfbk con esa contraseña.* | Restáurala donde esté su clave privada: `backup restore <archive>.tar --identity-file <key file>` ([Copias de seguridad selladas](backup_sealed.md#sealed)) |
| `sealed_no_identity`, `sealed_identity_invalid`, `sealed_tar_invalid`, `sealed_manifest_invalid`, `sealed_password_invalid` | Una [copia de seguridad sellada](backup_sealed.md#sealed) dada con `--identity-file` que no se abre | Consulta [Crear o abrir una copia de seguridad sellada](#sealed-problems) |
| `no_space` | La copia necesita más espacio libre del que tiene el disco de la carpeta de datos | Libera espacio: el archivo descomprimido, más el doble de su base de datos, más 64 MB, y para una copia de seguridad segura también el tamaño de su `.lfbk` |
| `archive_unreadable` | El archivo no se puede abrir, casi siempre porque el usuario del servidor no puede leerlo | Con Docker y la imagen oficial, `sudo chown 1000:1000 <archive>` en el host se lo entrega a ese usuario |
| `restore_already_pending` | Otra restauración espera al siguiente inicio | Reinicia LibreFolio para aplicarla, o cancélala con `backup pending --cancel` o **Cancelar la restauración** en Configuración › Administración › Copia de seguridad |
| `wrong_password` | La contraseña no abre la copia de seguridad segura: no es la que se usó para crearla, o se modificó el inicio del fichero. Configuración › Administración › Copia de seguridad la vuelve a pedir: *Contraseña incorrecta, o el archivo fue modificado: vuelve a escribir la contraseña.* | Escríbela de nuevo tal como se eligió, mayúsculas y minúsculas incluidas. Si es correcta, copia el fichero de nuevo desde donde lo guardes |
| `password_required` | Una copia de seguridad segura, y ninguna contraseña: el comando no tenía terminal donde preguntar, ni `--password-file` ni `--password-stdin` | Ejecuta el comando en un terminal, o da la contraseña con una de las dos opciones |
| `envelope_damaged` | La copia de seguridad segura está dañada, cortada o se modificó después de crearse | Cópiala de nuevo desde donde la guardes, o usa otra: LibreFolio no lee ninguna parte de un `.lfbk` dañado |
| `envelope_unsupported` | La copia de seguridad segura viene de un LibreFolio más reciente, o pide ajustes que este no acepta | Actualiza esta instalación primero ([Nunca hacia atrás](#never-backwards)) y luego ejecuta el comando de nuevo |

Dos mensajes más:

- `❌ No file at <path>`: con Docker, da la ruta dentro del contenedor, `/app/backend/data/prod-docker/…`.
- `❌ The backup has no active administrator: after a restore nobody could manage the instance`, o lo mismo en el informe de Configuración › Administración › Copia de seguridad, cuya confirmación permanece desactivada: en la instalación de la que viene la copia de seguridad, haz administrador a una cuenta activa y luego haz una nueva copia de seguridad.

Todos los códigos: «Rechazos — qué significan los códigos» en [Herramientas de administración de CLI](cli_tools.md).

Dos avisos dejan que la restauración continúe, pero léelos antes de confirmar:

- 🔑 *Tu cuenta no está entre los administradores de esta copia de seguridad: después del reinicio no podrás iniciar sesión con ella.* Solo en el informe de Configuración › Administración › Copia de seguridad, en rojo. Después de la restauración, inicias sesión con una cuenta de la copia de seguridad, con la contraseña que tenía entonces: la cuenta que usas ahora no está en ella. Antes de confirmar, asegúrate de que conoces la contraseña de uno de los administradores que nombra el informe; si no la conoces, usa otra copia de seguridad.
- `⚠️ Ledger totals differ from the backup's (<n> lines):`, o *Los totales del registro difieren de los de la copia de seguridad en 2 líneas:* en el informe de Configuración › Administración › Copia de seguridad: el efectivo de un bróker o la cantidad de una posición en la copia, una vez puesta al día, no es la que registró la copia de seguridad, porque se perdieron, añadieron o cambiaron transacciones entre las dos (por una migración que corrige datos, por ejemplo). Cada línea que sigue da el número de un bróker, luego una divisa o el número de un activo, con el importe de la copia de seguridad antes de la flecha y el de la copia después: los números son los de las direcciones `/brokers/<id>` y `/assets/<id>` de la aplicación. Compara estas líneas con la instancia de la que viene la copia de seguridad. El aviso nunca bloquea la restauración: que confirmes o no depende de ti.

### 🔏 Crear o abrir una copia de seguridad sellada {: #sealed-problems }

Para crear una, con `backup create --sealed` o `--recipient`: no se escribe nada, y el comando termina con `1`.

| Qué ves | Por qué | Qué hacer |
| --- | --- | --- |
| `❌ LIBREFOLIO_BACKUP_RECIPIENTS is not set: give the recipients there, or with --recipient age1…` | `--sealed` no encontró la variable: no está en `.env`, o el contenedor no se recreó después de añadirla | Establécela ([Sellar cada copia de seguridad](backup_sealed.md#sealed-recipients)) y luego `docker compose up -d`, o ejecuta el comando desde la carpeta del proyecto con `pipenv run`, que lee `.env` |
| `❌ LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: expected age1… as age-keygen prints it (BACKUP_RECIPIENTS_INVALID)`, o `expected at most 2 recipients, comma-separated (BACKUP_RECIPIENTS_TOO_MANY)`, o `item 2 repeats an earlier recipient (BACKUP_RECIPIENTS_DUPLICATE)` | La variable contiene algo distinto de una o dos claves `age1…` diferentes: una clave privada, una clave SSH, una coma de más | Escribe solo las claves públicas, tal como las imprimen `keygen` o `age-keygen -y`. La pestaña **Seguridad** dice lo mismo (`backup.recipients`) |
| `❌ A --recipient is not an age recipient: expected age1…, as keygen or age-keygen prints it`, `❌ The same recipient is given twice`, `❌ At most 2 recipients: --recipient twice, while a key is being changed` | Las mismas reglas, para `--recipient` | Da una o dos claves públicas diferentes |
| `❌ A sealed backup draws a password of its own: --sealed and --recipient go without --encrypt, --password-file or --password-stdin` | Una copia de seguridad sellada no tiene contraseña que dar | Quita las opciones de contraseña |
| `❌ --sealed reads the recipients from LIBREFOLIO_BACKUP_RECIPIENTS: give them there or with --recipient, not both` | `--sealed` y `--recipient` juntos | Quédate con uno de los dos |
| `❌ <path> already exists: a key file is never written over` | `backup keygen` nunca reemplaza una clave: la antigua aún puede abrir copias de seguridad | Elige otro nombre de fichero, o aparta primero el fichero antiguo si estás seguro de que ninguna copia de seguridad lo necesita |

Para abrir una, con `--identity-file`: el comando no cambia nada y termina con `1`. Lee primero el fichero de clave, luego el `.tar`.

| Qué ves | Por qué | Qué hacer |
| --- | --- | --- |
| `(sealed_backup_needs_key)` | Un `.tar` dado sin `--identity-file`, en la línea de comandos o en Configuración › Administración › Copia de seguridad | Da el fichero de clave, o [ábrela a mano](backup_sealed.md#sealed-by-hand) y restaura `backup.lfbk` con su contraseña |
| `❌ --identity-file opens a sealed backup (.tar) only: <path> is not one` | Un `.zip` o un `.lfbk` dado con `--identity-file` | Quita `--identity-file`: esos archivos se abren como de costumbre |
| `❌ The key file cannot be read (sealed_identity_invalid)`, `Line 3 of the key file is not an age key`, `The key file holds no age key` | El fichero no es una clave privada: solo la clave pública, una clave copiada con un carácter de menos, o un fichero que el comando no puede leer | Da el fichero escrito por `keygen` o `age-keygen`, con su línea `AGE-SECRET-KEY-1…`. Los comentarios (`#`) y las líneas en blanco pueden quedarse |
| `❌ None of the keys given opens the password of this backup (sealed_no_identity)` | La copia de seguridad se selló para otra clave: una más antigua, antes de un [cambio de clave](backup_sealed.md#sealed-rotation) | Compara sus `recipients` (`tar xOf <archive>.tar manifest.json`) con la línea `# public key:` de tus ficheros de clave, y da la que coincida |
| `(sealed_tar_invalid)`, como `The archive is cut short` o `The archive does not hold manifest.json, password.age and backup.lfbk, in this order` | No es el `.tar` que escribió LibreFolio: cortado por una copia, reconstruido a mano con `tar cf`, o no es una copia de seguridad sellada | Copia de nuevo el original desde donde lo guardes, o usa la copia de seguridad de otra noche |
| `(sealed_manifest_invalid)`, como `The manifest does not describe backup.lfbk: its size or SHA-256 differs` | Se modificó `manifest.json` o `backup.lfbk` | La copia está dañada: usa otra |
| `(sealed_password_invalid)` | La clave abrió `password.age`, pero lo que contiene no es una contraseña que haya escrito LibreFolio | No es una copia de seguridad de LibreFolio, o se modificó: usa otra copia |
| `❌ The password does not open this backup (wrong_password)` | La clave abrió la contraseña, pero esa contraseña no abre `backup.lfbk`: los dos ficheros vienen de copias de seguridad distintas, o se modificó uno | Usa otra copia, conservada entera tal como la escribió LibreFolio |
| `(envelope_damaged)`, durante la comprobación o la restauración | Se modificó un byte de `backup.lfbk` después de hacer la copia de seguridad: la contraseña era correcta | Usa otra copia: LibreFolio no lee ninguna parte de un `.lfbk` dañado |

### 🔁 La restauración no llega a completarse {: #restart-problems }

| Qué ves | Por qué | Qué hacer |
| --- | --- | --- |
| `backup pending` dice `The state of the restore cannot be read`, `(restore_state_unreadable: <reason>)` | `.restore/restore.json` no se puede usar: permisos (`io`), un enlace o una carpeta en su lugar (`not_a_file`), o contenido que LibreFolio no escribió (`invalid`). Puede que una restauración se haya detenido a medias. Mientras tanto no se elimina ninguna copia comprobada | Para `io`, devuelve `.restore/` al usuario que ejecuta LibreFolio y vuelve a comprobar. Si no, detén LibreFolio y ejecuta `backup pending --recover previous`: los datos de antes vuelven desde `.restore/previous/`. Luego inícialo, o restaura una copia de seguridad de nuevo («Un estado de restauración ilegible» en [Herramientas de administración de CLI](cli_tools.md)) |
| `backup pending` termina con `(server_running)` | En el último inicio, otro proceso de servidor servía la carpeta de datos: un worker se reinició por su cuenta, o había un segundo servidor | Reinicia todo el servidor, nunca un solo worker, y ejecuta un servidor por carpeta de datos |
| `backup pending` termina con `(other_data_directory)` | El servidor encontró su carpeta de datos bajo una ruta distinta de aquella para la que se confirmó la restauración, como una copia de la carpeta de datos | `backup pending --cancel`, o **Cancelar la restauración** en Configuración › Administración › Copia de seguridad, y luego restaura el archivo de nuevo: con `backup restore`, donde se ejecuta el servidor |
| `backup pending` termina con `(backup_running)` | Había una copia de seguridad en curso en el último inicio | Nada: el siguiente inicio aplica la restauración |
| `backup pending` dice que la restauración se deshizo, `(first_start_failed)` | El primer inicio sobre los datos restaurados no se completó | Los datos están como estaban. El registro de ese inicio tiene la causa: corrígela y luego restaura el archivo de nuevo |
| … se deshizo, `(swap_interrupted)` | El inicio que aplicó la restauración se interrumpió, y el siguiente la deshizo | Restaura el archivo de nuevo |
| … se deshizo, `(swap_failed)` | No se pudieron colocar las carpetas en su sitio | Haz que `sqlite/`, `custom-uploads/`, `broker_reports/` y `scenario_catalog/` sean carpetas reales de la carpeta de datos, ni enlaces ni montajes separados, y luego restaura el archivo de nuevo |
| … se deshizo, `(stage_missing)` | La copia comprobada desapareció o cambió | Restaura el archivo de nuevo |
| Un inicio se detiene, y su registro dice que otro servidor aplicó la restauración o sirve la carpeta de datos | Dos servidores de LibreFolio usan la misma carpeta de datos | Detén el otro y luego inicia LibreFolio de nuevo: `backup pending` dirá si se conservó la restauración |
| LibreFolio no se inicia, y su registro contiene `The data directory is half restored` | Volver a poner los datos anteriores también falló, por un error de disco o de permisos, por ejemplo | Corrige la causa que indica el registro: cada inicio lo intenta de nuevo |
| `Failed to apply database migrations` tras descomprimir a mano | Un archivo de un LibreFolio más reciente, o una migración que falla: el registro contiene el error | Para un archivo más reciente, `docker compose down` y luego usa la versión que lo creó o una más reciente ([Nunca hacia atrás](#never-backwards)) |

### 🖱️ Qué dice Configuración › Administración › Copia de seguridad {: #restore-settings-problems }

La ventana del reinicio da con palabras el motivo que `backup pending` da como código: la tabla dice cuál, y la fila de ese código en [La restauración no llega a completarse](#restart-problems) dice qué hacer. En la tarjeta, **Reintentar** vuelve a leer el estado de la restauración; para enviar de nuevo un archivo, vuelve a elegirlo.

| Qué ves | Por qué | Qué hacer |
| --- | --- | --- |
| Después de **Restaurar y reiniciar**, la página de inicio de sesión, sin ningún mensaje | La restauración funcionó y cerró todas las sesiones. Solo en el caso de la siguiente fila aparece la página de inicio de sesión aunque la restauración no se completó | Inicia sesión con un administrador de la copia de seguridad, con la contraseña que tenía la cuenta cuando se hizo la copia. Si nadie la recuerda: [Después de una restauración](#after-restore) |
| Apareció la página de inicio de sesión, pero una vez iniciada la sesión los datos están como antes | La página no leyó el resultado con su ticket (una recarga de la página, más de una hora de espera, o LibreFolio reiniciado desde la línea de comandos en vez de desde la página), y LibreFolio se ejecuta sin `JWT_SECRET` ([Mantener a los usuarios con la sesión iniciada tras un reinicio](index.md#session-persistence)): cada inicio cierra la sesión de todos, aunque la restauración no se haya completado. Las cuentas y contraseñas de antes siguen funcionando | Abre **Configuración › Administración › Copia de seguridad**: la tarjeta dice *La última restauración se deshizo el …*, o muestra la restauración en espera, con el motivo; luego consulta más abajo la fila de ese motivo |
| *LibreFolio aún no ha vuelto. Si nada lo reinicia por sí solo, inícialo tú: la restauración se aplica en ese inicio.* | LibreFolio no ha respondido durante un minuto: nada lo reinició (sin supervisor, o con uno que solo lo inicia tras un fallo, [Quién inicia LibreFolio de nuevo](backup_restore.md#supervisors)), o su inicio es lento | Si está detenido, inícialo: `docker compose up -d` con Docker, o [inicia el servidor](cli_tools.md#start-the-server) en una instalación en el host. La página continúa por sí sola cuando LibreFolio responde |
| *LibreFolio no se ha detenido. Si no se reinicia por sí solo, reinícialo tú: la restauración se aplica en ese inicio.*, un minuto después de **Restaurar y reiniciar**, con **Volver a la copia de seguridad** | La solicitud no detuvo el servidor: la restauración sigue esperando al siguiente inicio, y `backup pending` la muestra en espera | Reinicia LibreFolio tú mismo: `docker compose restart librefolio` con Docker, o detén todo el servidor e [inícialo](cli_tools.md#start-the-server) de nuevo. Su inicio aplica la restauración, y la página continúa por sí sola. O **Volver a la copia de seguridad**: la tarjeta muestra la restauración en espera, para reiniciar (**Reiniciar ahora y restaurar**) o cancelar (**Cancelar la restauración**) |
| **La restauración no se completó**, con *Los datos están como antes: …* | La restauración se deshizo: *el primer inicio posterior no se completó* (`first_start_failed`), *el inicio que la aplicaba se interrumpió* (`swap_interrupted`), *sus carpetas no se pudieron colocar en su sitio* (`swap_failed`) o *su copia comprobada ya no estaba* (`stage_missing`) | Lo que dice la fila de ese código. **Volver a la copia de seguridad** vuelve a la tarjeta, que dice cuándo se deshizo la última restauración y por qué |
| **La restauración no se completó**, con *LibreFolio se reinició, pero la restauración no se aplicó.* y el motivo | Un inicio dejó la restauración en espera: *En el último inicio había una copia de seguridad en curso…* (`backup_running`), *Se confirmó para otra carpeta de datos…* (`other_data_directory`) o *En el último inicio otro proceso de LibreFolio estaba sirviendo los datos…* (`server_running`) | Lo que dice la fila de ese código. **Volver a la copia de seguridad** muestra la restauración en espera, con **Reiniciar ahora y restaurar** y **Cancelar la restauración** |
| *El archivo es más grande de lo que acepta este LibreFolio (500 MB).* | La instalación limita los archivos subidos para una restauración con `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` (`backup_too_large`) | No hay límite a menos que alguien haya puesto uno: auméntalo, o ponlo en `0`, y luego reinicia ([El límite de subida de una restauración](backup_restore.md#restore-upload-limit)). O restaura desde la línea de comandos, que no tiene límite de subida |
| *Descomprimido, el archivo es más grande de lo que este LibreFolio acepta para una restauración.* | Los tamaños que declara el manifiesto, sumados, superan `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` (`unpacked_too_large`). La comprobación rechazó el archivo antes de descomprimir nada | No hay límite a menos que alguien haya puesto uno: auméntalo, ponlo en `0` o elimínalo, y luego reinicia ([El límite de subida de una restauración](backup_restore.md#restore-upload-limit)). O restaura desde la línea de comandos con `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` delante de `backup restore` |
| *LibreFolio no puede leer ahora su límite de restauración: inténtalo más tarde.* | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` no es un número entero de megabytes (`backup_restore_unavailable`): no se inicia ninguna comprobación, y el archivo se queda en el servidor. El registro tiene un error, ya desde el inicio | Escribe un número entero de megabytes, `0` para ningún límite, o elimina la variable, y luego reinicia; la pestaña **Seguridad** de Configuración › Administración la nombra (`backup.restore_limit`). Después vuelve a elegir el archivo |
| El envío se detiene con *Un proxy delante de LibreFolio rechazó un archivo tan grande: pide a quien lo gestiona que acepte subidas más grandes, o restaura desde la línea de comandos.*, o con *El servidor no responde: comprueba la conexión e inténtalo de nuevo.* o *El servidor respondió con un error: el registro del servidor tiene la causa.*, y el registro de LibreFolio no dice nada al respecto | Un proxy delante de LibreFolio rechazó el archivo: Nginx solo acepta 1 MB por defecto. El primer mensaje: el proxy responde *demasiado grande* (HTTP 413); los demás: corta la conexión o responde de otro modo | Deja que el proxy acepte archivos tan grandes como el tuyo, con `client_max_body_size` en Nginx ([El límite de subida de una restauración](backup_restore.md#restore-upload-limit)), o restaura desde la línea de comandos |
| *No hay espacio libre suficiente en el servidor para este archivo.* | El disco de la carpeta de datos, o una cuota, está lleno (`backup_no_space`): mientras se envía, y entonces no se conserva nada del archivo (un sistema de archivos de red o una cuota pueden informarlo solo al final del fichero), o en la confirmación con **Restaurar y reiniciar**, y entonces no se confirma nada y la copia comprobada se queda; el registro contiene `A restore could not be confirmed: not enough free space` | Libera espacio en el disco de la carpeta de datos y luego vuelve a elegir el archivo. Después de una confirmación, **Reintentar**: el informe vuelve, y **Restaurar y reiniciar** confirma de nuevo |
| *No hay espacio libre suficiente en el servidor para comprobar el archivo.* | El disco de la carpeta de datos, o una cuota, está lleno cuando empieza la comprobación, y entonces el archivo se queda en el servidor, o mientras la comprobación hace su copia (`no_space`) | Libera espacio, tanto como dice la fila `no_space` de [La comprobación rechaza el archivo](#check-refused), y luego vuelve a elegir el archivo |
| *La copia no se pudo escribir: el registro del servidor tiene la causa.* | La comprobación no empezó, o no escribió su copia, por una razón distinta del espacio (`stage_failed`): el propietario o los permisos de una carpeta de `.restore/`, un disco de solo lectura, un error de disco. El registro contiene `A check of a backup archive could not start`, con el error y la razón del sistema | Corrige lo que nombra la línea del registro, por ejemplo devolviendo `.restore/` al usuario que ejecuta LibreFolio, y luego vuelve a elegir el archivo |
| *No hay espacio libre suficiente en el servidor para la copia de seguridad.*, en la tarjeta **Copia de seguridad de la instancia** | El disco de la carpeta de datos, o una cuota, está lleno (`backup_no_space`), al empezar la copia de seguridad o mientras se ejecuta: la copia de seguridad se hace en `backups/`, en ese disco | Libera espacio en ese disco y luego **Reintentar**. Cuánto espacio necesita una copia de seguridad: «Crear un archivo» en [Herramientas de administración de CLI](cli_tools.md) |
| *La restauración no se pudo confirmar: el registro del servidor tiene la causa. No ha cambiado nada.*, después de **Restaurar y reiniciar** | No se escribió la confirmación, por una razón distinta del espacio (`restore_confirm_failed`): el propietario o los permisos de `.restore/`, un disco de solo lectura, un error de disco. El registro contiene `A restore could not be confirmed`, con el error y la razón del sistema. No se confirma nada, y la copia comprobada se queda | Corrige lo que nombra la línea del registro, por ejemplo devolviendo `.restore/` al usuario que ejecuta LibreFolio, y luego **Reintentar**: el informe vuelve, y **Restaurar y reiniciar** confirma de nuevo |
| *La restauración no se pudo cancelar: el registro del servidor tiene la causa. Sigue esperando el próximo inicio.*, después de **Cancelar la restauración**: la tarjeta sigue mostrando la restauración en espera, con **Reiniciar ahora y restaurar** y **Cancelar la restauración** | Su estado en `.restore/` no se pudo bloquear ni eliminar (`restore_cancel_failed`): propietario o permisos, un disco de solo lectura, un error de disco. El registro contiene `A pending restore could not be cancelled`, con el error y la razón del sistema. Una copia que no se puede eliminar tras la cancelación no es tal fallo: la restauración está cancelada, y el registro tiene la advertencia `The copy of a cancelled restore could not be removed: it goes when its check expires` | Corrige lo que nombra la línea del registro y luego **Cancelar la restauración** de nuevo, en la misma tarjeta: hasta que se cancele, el siguiente inicio de LibreFolio aplica la restauración. Una copia que quede se elimina en el primer inicio de LibreFolio una vez que su comprobación tenga 24 horas |
| *LibreFolio no se pudo reiniciar: el registro del servidor tiene la causa. La restauración sigue esperando el próximo inicio.*, después de **Restaurar y reiniciar** o **Reiniciar ahora y restaurar** | LibreFolio no se detuvo: no se escribió el ticket con el que la página lee el resultado (`restore_restart_failed`), por un disco lleno o por el propietario o los permisos de `.restore/`. El registro contiene `The ticket of the restore's outcome could not be written: no restart`. La restauración está confirmada, y espera | Corrige lo que nombra la línea del registro y luego **Reiniciar ahora y restaurar**, que la tarjeta muestra con la restauración en espera. O reinicia LibreFolio tú mismo, `docker compose restart librefolio` con Docker: su inicio aplica la restauración |
| *No se puede leer el estado de la restauración: el registro del servidor tiene la causa. Puede que una restauración siga esperando el próximo inicio.* | No se puede leer el estado de la restauración en `.restore/` (`restore_state_unreadable`): propietario o permisos, como ficheros escritos por `root`, o un error de disco. No se sabe si hay una restauración en espera: confirmar otra se rechaza, y un inicio que no lee el estado lo deja como está y no aplica nada | Devuelve `.restore/` y sus ficheros al usuario que ejecuta LibreFolio, legibles por él, y luego **Reintentar**. Con Docker, cada inicio del contenedor devuelve la carpeta de datos a ese usuario antes de que LibreFolio lea el estado, así que una restauración en espera se aplica en ese inicio; los permisos cambiados con `chmod` se quedan como están. `backup pending` dice lo mismo, con la razón del sistema |
| La tarjeta rechaza el archivo, por ejemplo *Este archivo no es una copia de seguridad de LibreFolio.*, *El archivo está dañado.* o *La copia segura está dañada o fue modificada: no se puede abrir.* | La comprobación lo rechazó, como hace `backup restore` | Consulta su código en [La comprobación rechaza el archivo](#check-refused) |
| La tarjeta vuelve a pedir la contraseña de una copia de seguridad segura: *Contraseña incorrecta, o el archivo fue modificado: vuelve a escribir la contraseña.* | La contraseña no abre la copia de seguridad (`wrong_password`) | Escríbela de nuevo: el archivo se queda en el servidor y no se envía otra vez. Si la contraseña es correcta, el fichero se modificó: **Cancelar**, y luego elige una copia buena con **Elegir un archivo…** |

### 🔑 Después de una restauración {: #after-restore }

| Qué ocurre | Qué hacer |
| --- | --- |
| Nadie recuerda la contraseña que tenía un administrador en la copia de seguridad | Quien ejecuta el servidor establece una nueva con `user reset`, o crea un enlace de restablecimiento con `user reset-link` ([Restablecer una contraseña o bloquear una cuenta](cli_tools.md#reset-a-password-or-lock-an-account)) |
| La página de inicio de sesión responde que una cuenta está desactivada: estaba esperando la verificación de su correo electrónico | Un administrador hace clic en **Reactivar** en su fila ([Qué hace cada acción](users.md#actions)), o la elimina para que su propietario se registre de nuevo ([Eliminar una cuenta](users.md#delete)) |
| Un enlace enviado antes de la restauración ya no funciona | Envía una nueva invitación o un nuevo enlace de restablecimiento de contraseña ([Usuarios e invitaciones](users.md)) |
| Un ajuste secreto de un plugin se informa como establecido pero ilegible, como anunció el informe de la comprobación (*… no se pueden leer con la clave de esta instancia: vuelve a introducirlas tras la restauración.*) | La copia de seguridad no tenía ninguna clave capaz de leerlo: una copia sin cifrar, o una segura cuya instancia tenía una clave establecida en su entorno, o no podía usar la suya. Si aún tienes la clave antigua, vuelve a ponerla en su sitio antes de que nadie introduzca un secreto de nuevo; solo si no, vuelve a introducir el ajuste en **Configuración › Plugins**, donde cada usuario introduce el suyo ([Lo que sigue](backup_restore.md#what-follows)). Si el registro de inicio dice que la clave de esta instalación no se puede usar, corrige eso primero («Comprobaciones de inicio» en [Variables de entorno](configuration.md)) |
| Tras un traslado, no sale ningún correo electrónico | Establece las variables de correo electrónico en esta instalación y luego reinicia ([Correo electrónico](email.md)) |

---

## 🔗 Relacionado

- 📄 **[Copia de seguridad, restauración y traslado de tu instancia](backup_restore.md)** — Qué contiene una copia de seguridad, Hacer una copia de seguridad, Copias de seguridad seguras, …
- 📄 **[Copias de seguridad: copias selladas](backup_sealed.md)** — Copias de seguridad selladas: una clave en lugar de una contraseña
