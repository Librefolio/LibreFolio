# 💾 Copia de seguridad, restauración y traslado de tu instancia

Una copia de seguridad es un archivo con todo tu LibreFolio dentro: la base de datos y los archivos de cada usuario. Es un zip simple o, para una [copia de seguridad segura](#secure), un `.lfbk` cifrado con una contraseña que elijas.

Aquí encuentras:

- [qué contiene el archivo](#contents) y [lo que sigue](#what-follows);
- cómo [hacer una](#create), desde la aplicación o desde la línea de comandos, y cómo [guardar copias fuera del servidor](#keep-copies);
- cómo [comprobarla](#check) y cómo [restaurarla](#restore), desde la aplicación o desde la línea de comandos.

Cada opción y mensaje de los comandos: «Hacer copia de seguridad de la instancia», en [Herramientas de administración de CLI](cli_tools.md).

!!! tip "🗓️ Haz una antes de cada actualización"

    LibreFolio nunca lleva una base de datos a una versión anterior. Una copia de seguridad hecha antes de una actualización es tu camino de vuelta a la versión que tenías: consulta [Actualizar LibreFolio](../user/installation.md#updating).

!!! info "📚 Esta guía está en varias páginas"

    Además de esta página: [Copias de seguridad: Copias selladas](backup_sealed.md), [Copias de seguridad: Traslado y solución de problemas](backup_moving.md).

---

## 📦 Qué contiene una copia de seguridad {: #contents }

El archivo es un zip con la estructura del [directorio de datos](filesystem.md): descomprimido en un directorio de datos vacío, vuelve a ser tu instancia. Una [copia de seguridad segura](#secure) es el mismo zip, cifrado con una contraseña, en un archivo `.lfbk`. Una [copia de seguridad sellada](backup_sealed.md#sealed) es una copia de seguridad segura cuya contraseña solo se abre con una clave privada tuya, en un `.tar`.

| En el archivo | Qué es |
| --- | --- |
| `sqlite/app.db` | La base de datos: usuarios, brókeres, transacciones, activos, precios, tipos de cambio y ajustes. Una copia consistente, hecha mientras LibreFolio sigue en marcha |
| `custom-uploads/` | Los archivos subidos en la aplicación |
| `broker_reports/` | Los informes del bróker |
| `scenario_catalog/` | Tus escenarios de estrés, si añadiste alguno |
| `secrets/instance.key` | Solo en una [copia de seguridad segura](#secure), y solo si LibreFolio generó la clave de instancia: la clave que cifra las claves guardadas de los proveedores de datos. Una restauración solo la lee: la instalación que recibe la copia de seguridad conserva la suya |
| `manifest.json` | La descripción del archivo: versión de LibreFolio y fecha de creación, revisión de migración de la base de datos, filas por tabla, totales de control del libro mayor (el efectivo de cada bróker por moneda y la cantidad de cada posición), tamaño y suma de comprobación SHA-256 de cada archivo, y si el archivo lleva la clave de instancia |

Nunca en el archivo:

- 🔑 `secrets/`: una [copia de seguridad segura](#secure) solo lleva la clave que generó LibreFolio, `secrets/instance.key`, nunca una clave que hayas establecido tú con `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE` («La clave de la instancia» en [Variables de entorno](configuration.md));
- 📝 `logs/` y `scheduler_state.json` (la última ejecución de las sincronizaciones programadas);
- 💾 `backups/`, donde LibreFolio [conserva las copias de seguridad que hace](#kept-backups), y `.restore/`, la carpeta de trabajo de una restauración;
- ⚙️ la configuración: `.env` y las variables de entorno, incluidos los ajustes de [correo electrónico](email.md), que viven solo en el entorno.

### 🧭 Lo que sigue {: #what-follows }

- 🔒 **Mantenla privada.** Un archivo sin cifrar contiene los datos de todos los usuarios, sin cifrar: guárdalo, con cada copia, tan privado como el propio servidor. Una [segura](#secure) solo se abre con su contraseña: guarda la contraseña aparte del archivo.
- ⚙️ **Lleva tu configuración contigo.** Guarda una copia de tu `.env` junto con los archivos: en otra instalación, vuelve a establecer las opciones que necesites, incluidas las de correo electrónico ([Dónde vive la configuración](email.md#where-it-lives)).
- 🏠 **Cualquier instalación puede aceptarla**, desde Configuración o desde la línea de comandos, si ejecuta la misma versión de LibreFolio o una más reciente, quienquiera que haya hecho el archivo.
- 🗝️ **Secretos guardados y la clave de instancia.** Lo que LibreFolio cifró con la clave de instancia, como la clave de API de una fuente de datos guardada en la aplicación, solo se puede leer con esa clave:

| Copia de seguridad | La clave de instancia | Restaurada en una instalación con otra clave |
| --- | --- | --- |
| [Segura](#secure), clave generada por LibreFolio | Viaja con los datos | Los secretos se vuelven a cifrar con la clave de la instalación que la recibe: nada que hacer |
| Sin cifrar; [sellada](backup_sealed.md#sealed); segura con una clave del entorno (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) o que no se pueda usar | Se queda fuera | Los secretos siguen guardados pero ilegibles; LibreFolio nunca usa un valor incorrecto. **Configuración › Plugins** dice bajo cada uno *Guardado, pero la clave de esta instancia no puede leerlo: vuelve a introducirlo.* |

Si aún tienes la clave antigua, vuelve a ponerla **antes** de que nadie introduzca un secreto de nuevo: un secreto introducido bajo la nueva clave se volvería ilegible una vez que vuelva la antigua. Vuelve a introducir los secretos solo si la clave antigua se ha perdido.

1. Detén LibreFolio.
2. **En el servidor, en `secrets/` del directorio de datos**: pon tu copia de `secrets/instance.key` en lugar de la generada. O, **en `.env`**, establece de nuevo el valor antiguo de la variable («La clave de la instancia» en [Variables de entorno](configuration.md)).
3. Inicia LibreFolio de nuevo.

Si la instalación conserva su propia clave, o sus secretos ya están cifrados con su clave, toma la clave antigua en la restauración: **desde la línea de comandos**, restaura con `--instance-key-file` y tu copia de la clave antigua; la comprobación vuelve a cifrar esos secretos con la clave de esta instalación («La clave de instancia de otra instalación» en [Herramientas de administración de CLI](cli_tools.md)).

Para los ajustes de toda la instancia, cada inicio registra el error *Stored plugin secrets that the instance key cannot read: …*, con su recuento, hasta que se vuelvan a introducir o vuelva la clave antigua. Hoy ningún plugin distribuido con LibreFolio guarda ninguno.

---

## ⬇️ Hacer una copia de seguridad {: #create }

Dos caminos dan el mismo archivo:

| Dónde | Qué obtienes |
| --- | --- |
| **Configuración › Administración › Copia de seguridad**, en la aplicación (administradores) | El archivo descargado en tu ordenador, y una copia [conservada en el servidor](#kept-backups) |
| **Terminal en el servidor**: `backup create` | El archivo en el servidor, o donde indiques con `--output` |

Desde ambos, la copia de seguridad puede ser [segura](#secure): el mismo zip, cifrado con una contraseña que elijas. Solo desde la línea de comandos puede ser [sellada](backup_sealed.md#sealed): cifrada con una contraseña aleatoria que solo abre una clave privada tuya, para copias de seguridad hechas sin nadie frente al teclado.

LibreFolio sigue funcionando durante la copia de seguridad. Se ejecuta una copia a la vez, sea quien sea quien la haya iniciado.

### 🖱️ Desde Configuración › Administración › Copia de seguridad {: #settings-backup }

1. Abre **Configuración › Administración › Copia de seguridad** (solo los administradores tienen la pestaña), sección **Copia de seguridad de la instancia**.
2. Elige el tipo:
    - **Sin cifrar** (predeterminado): *Un .zip normal: quien tenga el archivo ve todos los datos, y en otra instancia hay que volver a introducir las claves de los proveedores de datos.*
    - **Segura**: *Un .lfbk cifrado con una contraseña que eliges tú: solo esa contraseña lo abre, y una contraseña perdida no se puede recuperar. También lleva las claves de los proveedores de datos.* Consulta [Copias de seguridad seguras](#secure).
3. Para una copia de seguridad segura, escribe la contraseña en **Contraseña de la copia** y otra vez en **Repite la contraseña**. Se aplican las reglas de la contraseña de una cuenta, dadas por el servidor: el medidor bajo el primer campo las enumera mientras escribes (*Al menos 12 caracteres*, *Una letra mayúscula*, *Una letra minúscula*, *Un número*, *Un carácter especial*) y muestra lo fuerte que es. Mientras los dos campos difieran, aparece *Las dos contraseñas no coinciden.* y **Crear copia de seguridad** sigue deshabilitado.
4. Haz clic en **Crear copia de seguridad**. Los campos de contraseña se vacían de inmediato; la tarjeta sigue la copia de seguridad fase por fase (una copia de seguridad segura termina con *Cifrando con tu contraseña*).
5. En **Copia de seguridad lista**, haz clic en **Descargar**. El navegador guarda `librefolio-backup-20261015-121500.zip` (fecha y hora de inicio, en UTC), o `.lfbk` para una copia de seguridad segura, que la tarjeta marca *Cifrada con tu contraseña: guárdala bien, LibreFolio no puede recuperarla.*

Conviene saber:

- 🔑 **Guarda la contraseña de una copia de seguridad segura** en un gestor de contraseñas, aparte del archivo: LibreFolio no guarda ninguna copia de ella, y sin ella nadie abre el archivo, tú incluido.
- 💾 Una copia permanece en el servidor, en la lista de [Copias de seguridad conservadas en el servidor](#kept-backups), hasta que la elimines o la [limpieza automática](#backup-cleanup) la elimine: descárgala también desde allí más tarde. Una copia en el mismo disco que los datos no es una copia de seguridad real: guárdala en otro lugar ([Mantén copias fuera del servidor](#keep-copies)). **Eliminar del servidor** la elimina de inmediato; **Crear una nueva copia** inicia otra.
- ⚠️ **Copia completada, con avisos**: la base de datos falló su comprobación de integridad o tiene referencias rotas y se archivó tal cual; o se omitieron algunos archivos; o, para una copia de seguridad segura, la clave de la instancia no se pudo usar y se omitió ([Hacer una copia de seguridad segura](backup_moving.md#secure-problems)). El archivo se escribe de todos modos: lee los avisos antes de confiar en él.
- 🚦 **Ya hay otra copia de seguridad en curso** (desde la aplicación o la línea de comandos): la tarjeta lo indica, inténtalo de nuevo cuando termine.

Qué hace la tarjeta con una copia de seguridad ya en curso:

| Copia de seguridad en curso | La tarjeta |
| --- | --- |
| Sin cifrar, iniciada desde esta pestaña o desde otra de la aplicación, cuya respuesta nunca llegó (la conexión se cayó al empezar) | No se pierde: el siguiente **Crear copia de seguridad** la encuentra, la sigue y ofrece su descarga |
| Segura, no iniciada desde esta pestaña | Nunca se sigue: solo su contraseña abre el archivo. La tarjeta dice que se ejecuta otra copia de seguridad |
| Cualquiera, mientras la tarjeta ya ofrece un archivo | Sigue ofreciendo el suyo y solo dice que se ejecuta otra copia de seguridad |
| Iniciada desde la línea de comandos | No se sigue: su archivo va a otro lugar |

La tarjeta nunca dice qué copia de seguridad se ejecuta: la consola del navegador sí (id y origen).

### ⌨️ Desde la línea de comandos {: #command-line }

**En el terminal del servidor**, desde la carpeta con `docker-compose.yml` (Docker) o desde la carpeta de LibreFolio (instalación en host):

```bash
# Docker: the archive appears in its own folder of ./LibreFolio-data/backups/ on the host
docker compose exec librefolio python dev.py backup create

# Host installation: the archive goes into its own folder of backups/ in the data directory
pipenv run ./dev.py backup create

# A secure backup (.lfbk): the password is asked twice
docker compose exec librefolio python dev.py backup create --encrypt
```

El comando imprime la ruta del archivo y su `SHA-256:`.

- 🗃️ Sin `--output`, el archivo permanece en el servidor, en una carpeta propia dentro de `backups/` ([Copias de seguridad conservadas en el servidor](#kept-backups)).
- 📁 `--output` (`-o`) copia el archivo en otra carpeta que ya exista, o con un nombre propio; no queda nada en `backups/`. Con Docker, la ruta está dentro del contenedor: usa una carpeta montada desde el host.
- 🔒 Solo el propietario del archivo puede leerlo (`0600`): con Docker, el usuario del contenedor.
- 🔐 `--encrypt` crea una [copia de seguridad segura](#secure), `librefolio-backup-<date>-<time>.lfbk`, y pide la contraseña dos veces en el terminal. En su lugar: `--password-file FILE`, un archivo que contiene solo la contraseña (los saltos de línea al final no cuentan), como un secreto de Docker; o `--password-stdin`, una línea de la entrada estándar desde una tubería (en un terminal, el comando la pide sin mostrarla). Cualquiera de las dos hace segura la copia de seguridad por sí sola, con o sin `--encrypt`; no se usan juntas.
- 🙈 No existe `--password`: todos los usuarios del servidor pueden leer los comandos que se ejecutan (`ps`), y el shell los guarda en su historial.
- 📏 Reglas de la contraseña, como en Configuración › Administración › Copia de seguridad: al menos 12 caracteres, una letra mayúscula, una letra minúscula, un dígito y un símbolo. De lo contrario, el comando se detiene antes de escribir nada: `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: min_length, digit)`.
- 🤖 Sin terminal (cron, script), `--encrypt` por sí solo se detiene: `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`.
- 📖 Cada opción, advertencia y error: «Hacer copia de seguridad de la instancia» y «Hacer copia de seguridad con Docker» en [Herramientas de administración de CLI](cli_tools.md).

??? example "🐳 La contraseña de las copias de seguridad como secreto de Docker"

    1. **Junto a `docker-compose.yml`**, escribe la contraseña sola en un archivo, como `backup_password.txt`, nunca en `LibreFolio-data/` (quien tuviera los datos tendría también la contraseña). Luego `chmod 600 backup_password.txt`, y guarda una copia de la contraseña en otro lugar: una contraseña perdida no se puede recuperar.
    2. **En `docker-compose.yml`**, añade las líneas marcadas y deja el resto del servicio como está. Si el archivo ya tiene listas `secrets:`, como para `JWT_SECRET_FILE` («Secretos en archivos» en [Variables de entorno](configuration.md)), añade las líneas a ellas.

        ```yaml
        services:
          librefolio:
            secrets:                              # added
              - backup_password                   # added
        secrets:                                  # added
          backup_password:                        # added
            file: ./backup_password.txt           # added
        ```

        Ejecuta `docker compose up -d`: el contenedor se recrea con el secreto.

    3. **En el terminal del servidor**, haz la copia de seguridad con la ruta del secreto en el contenedor:

        ```bash
        docker compose exec librefolio python dev.py backup create --password-file /run/secrets/backup_password
        ```

### 🗃️ Copias de seguridad conservadas en el servidor {: #kept-backups }

Una copia de seguridad hecha desde la aplicación o la línea de comandos ya no se elimina después de una hora: permanece en el servidor hasta que la elimines o hasta que la [limpieza automática](#backup-cleanup) la elimine. Cada una tiene su propia carpeta en `backups/` del directorio de datos: momento de creación (UTC), origen (`ui` aplicación, `cli` línea de comandos) y un código corto que distingue dos copias del mismo segundo. El archivo interior conserva su nombre habitual, `.zip`, `.lfbk` o `.tar`:

```text
backups/librefolio-backup-20261015-121500-ui-1a2b3c4d/librefolio-backup-20261015-121500.zip
```

`backups/.jobs/` solo contiene una copia de seguridad en curso o una que falló, que se elimina después de una hora.

**Dónde las ves**: **Configuración › Administración › Copia de seguridad**, bajo *Copias de seguridad en este servidor*, o **Archivos › Copias**, la misma lista; solo administradores. **Actualizar**, al principio de la lista, la lee de nuevo: una copia de seguridad hecha desde la línea de comandos aparece solo entonces. Para cada copia de seguridad:

- 📅 fecha y hora de creación, y origen: aplicación o línea de comandos;
- 🔐 tipo: simple, con contraseña ([segura](#secure)) o [sellada](backup_sealed.md#sealed);
- 📏 tamaño y SHA-256: haz clic para copiar la suma de comprobación completa y compararla con la del archivo descargado;
- 📦 **Una vez restaurada**: el espacio que ocupan sus contenidos una vez restaurados, sin comprimir, es decir, lo que tomará una restauración; pasa el puntero por encima para ver sus partes: la base de datos, los archivos subidos, los informes de los brókeres y los demás archivos. Una copia hecha antes de que LibreFolio lo registrara muestra «—»;
- ⬇️ **Descargar** y 🗑️ **Eliminar**, que elimina la copia de seguridad del servidor de inmediato.

!!! warning "💽 Descárgala y guárdala en otro lugar"

    Una copia de seguridad que permanece en el mismo disco que tus datos no es una copia de seguridad real: cuando se pierde el disco, los datos y sus copias de seguridad se van juntos. Descarga el archivo y guárdalo en otro disco, un NAS o fuera del sitio ([Mantén copias fuera del servidor](#keep-copies)).

La lista muestra solo las copias de seguridad hechas por esta versión de LibreFolio. Los archivos sueltos `librefolio-backup-*.zip` de versiones anteriores en `backups/` no se enumeran y LibreFolio nunca los elimina: elimínalos tú cuando ya no los necesites.

### 🧹 Limpieza automática {: #backup-cleanup }

**En el panel cerrado Limpieza automática**, en la sección **Copias de seguridad en este servidor** de **Configuración › Administración › Copia de seguridad** o de **Archivos › Copias**, estableces dos límites, ambos opcionales:

| Límite | Qué hace | Desactivado |
| --- | --- | --- |
| Tamaño total, en MB | Cuando las copias de seguridad conservadas pesan más, se eliminan las más antiguas hasta que el resto quepa | `0` |
| Antigüedad máxima, en días | Una copia de seguridad más antigua se elimina | `0` |

- 🛡️ **La última copia de seguridad siempre se conserva**, digan lo que digan los límites.
- ⏰ La limpieza se ejecuta después de cada copia de seguridad y cuando LibreFolio se inicia, como mucho una vez por hora: un cambio guardado se aplica en una hora.
- 🏠 **Autoalojado:** ambos límites están desactivados hasta que los establezcas.
- 🔍 Solo se limpian las copias de seguridad de la lista: nunca los archivos sueltos más antiguos en `backups/`, una copia de seguridad en curso ni una fallida.
- ⌨️ Las copias de seguridad de la línea de comandos permanecen en el mismo lugar y siguen los mismos límites: [Dónde se quedan las copias de seguridad](cli_backup.md#backup-kept).

### 📊 La barra de espacio {: #space-used }

**En Archivos**, encima de las pestañas, los administradores ven la barra **Espacio ocupado**: cuánto espacio ocupa tu instancia. Se actualiza con **Actualizar** y siempre que cambia la lista de copias de seguridad conservadas. La leyenda da el tamaño de cada parte:

| Parte | Qué cuenta |
| --- | --- |
| **Base de datos** | La base de datos y los archivos que guarda junto a ella |
| **Archivos subidos** | Los archivos subidos en la aplicación, como los de la página **Archivos** |
| **Informes de brókeres** | Los extractos subidos para importar transacciones |
| **Copias de seguridad** | Todo en `backups/`: las [copias de seguridad conservadas en el servidor](#kept-backups), una copia de seguridad en curso y una fallida |
| **Restauración pendiente** | Una [restauración](#restore) aún sin terminar o sin descartar: el archivo subido y su versión descomprimida |
| **Otros archivos de LibreFolio** | El resto del directorio de datos: registros, estado y similares |

Tres aspectos de la barra:

| Situación | La barra | La línea bajo ella |
| --- | --- | --- |
| 💽 **Sin límite** (valor predeterminado en autoalojado) | Todo el disco de los datos: las partes de LibreFolio coloreadas, **Otros en el disco** en gris, **Libre** vacío | Cuánto usa LibreFolio del disco |
| 📏 **Con un límite** | El límite, lleno hasta donde llegan los datos | *usado del límite* |
| 📁 **Sin límite y disco desconocido** (LibreFolio no puede consultarlo) | Solo la carpeta de LibreFolio, dividida en sus partes, sin espacio libre | — |

**Establece el límite** en **Archivos › Avanzado** (panel cerrado bajo la barra), campo **Espacio total de LibreFolio (MB)**: un número entero de megabytes, `0` para sin límite, luego **Guardar**; un aviso verde lo confirma. Es el espacio máximo que LibreFolio puede ocupar en total. El mismo campo está en **Configuración › Administración › [Configuración Global](settings.md)**, categoría **Memoria**: cualquiera de los dos sitios lo cambia.

- 🚧 **Más allá del límite**, LibreFolio rechaza lo que añadiría datos: un archivo subido, un informe del bróker, una copia de seguridad iniciada a mano (tras probar la [limpieza automática](#backup-cleanup)) y una [restauración](#restore) cuyo resultado lo superaría. El mensaje dice a qué subir el espacio total y, si al disco le falta sitio, cuánto más necesita libre. Nunca se detienen: transacciones, precios y base de datos, las copias de seguridad de un panel de alojamiento y de la línea de comandos (la limpieza las sigue) y una restauración ya confirmada. El límite no elimina nada por sí mismo.
- ⚠️ La barra avisa de que se ha superado el límite y sugiere eliminar copias de seguridad o archivos, o subir el límite. Entonces pasa a ser tus datos, para que ninguna parte quede fuera: una marca *Límite 20 MB* muestra dónde cae el límite, las líneas rojas tras ella cuánto lo superas.
- 💬 **Un rechazo se comunica donde estás**: en la ventana de subida o de importación, o en la tarjeta de copia de seguridad. Un administrador encuentra **Abrir la configuración**, que abre **Configuración › Administración › Configuración Global** con la fila **Espacio total de LibreFolio (MB)** a la vista y resaltada: desbloquea la pestaña para cambiarla; un usuario lee cuánto espacio liberar, o que se lo pida a un administrador. Con un límite establecido por quien aloja la instancia, el mensaje dice que se lo pidas a esa persona.
- 🔒 **Establecido en la configuración del servidor**: con `LIBREFOLIO_STORAGE_LIMIT_MB` en el entorno, su valor es el límite, el campo es de solo lectura, aquí y en Configuración Global, y una nota dice que lo establece quien aloja la instancia ([Variables de entorno](configuration.md)). Un valor que no sea un número entero se ignora y el campo funciona como se describe arriba.
- 🧹 **La limpieza y la barra trabajan juntas.** Normalmente las copias de seguridad son las que crecen: la [limpieza automática](#backup-cleanup) las mantiene a raya, y cada copia de seguridad eliminada en **Configuración › Administración › Copia de seguridad** o en **Archivos › Copias** acorta **Copias de seguridad** en la barra. Cerca del límite, empieza por ahí.

### 🗄️ Mantén copias fuera del servidor {: #keep-copies }

`backups/` está en el directorio de datos, en el mismo disco: una copia de seguridad allí no sobrevive a la pérdida del disco. Un archivo descargado desde Configuración ya está fuera del servidor. Desde la línea de comandos, escribe los archivos en otro disco, un NAS o fuera del sitio con `--output`, según una programación.

**En el `crontab` del usuario que ejecuta LibreFolio** (`crontab -e`), instalación en host, cada noche a las 03:30:

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /mnt/nas/librefolio/
```

**Con Docker**, añade `-T` (cron no da terminal al comando). El archivo llega a una carpeta propia dentro de `LibreFolio-data/backups/`, donde la [limpieza automática](#backup-cleanup), una vez establecida, evita que el disco se llene: cópialo a otro lugar con tu herramienta habitual.

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create
```

**Archivos [seguros](#secure)**: añade `--password-file` con un archivo que contenga la contraseña (cron no tiene terminal donde preguntar). Con Docker, el secreto del ejemplo anterior:

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create --password-file /run/secrets/backup_password
```

- 📁 La carpeta de `--output` debe existir cuando se ejecuta el comando: monta primero el NAS. Una ruta que no sea una carpeta existente se convierte en el nombre del archivo.
- 🔢 El comando imprime lo que hizo y sale con `1` cuando el archivo no está donde pediste: conserva la salida, o haz que cron te la envíe por correo.
- 🧭 cron tiene un `PATH` corto: si no encuentra `pipenv` o `docker`, escribe la ruta completa (`command -v pipenv` la imprime).
- 🗑️ LibreFolio no elimina ninguno de estos archivos: elimina tú los antiguos. Conserva varios, y el último hecho antes de cada actualización.
- 🔑 Guarda también una copia de `.env`, tan privada como los archivos: ningún archivo lo contiene. Y una copia de `secrets/`, a menos que tus archivos sean seguros: uno sin cifrar o [sellado](backup_sealed.md#sealed) deja fuera la clave de la instancia ([Lo que sigue](#what-follows)).
- 🔏 Archivos nocturnos que el propio servidor no puede abrir, sin un archivo de contraseña en su disco: [Cada noche con cron](backup_sealed.md#sealed-cron), en Copias de seguridad selladas.

### 🧰 Copias de seguridad con restic o Backrest {: #restic }

LibreFolio escribe el archivo; una herramienta de copia de seguridad lo lleva fuera del sitio y guarda un historial. [restic](https://restic.net/) copia una carpeta, cifrada, a S3, Backblaze B2, SFTP y más, y olvida las copias antiguas según una regla tuya. [Backrest](https://github.com/garethgeorge/backrest) es una interfaz web para restic, con su propio planificador. LibreFolio no necesita ninguna: solo leen la carpeta de sus archivos.

Receta nocturna, instalación en host. **En un archivo privado** (`chmod 600`), las variables de restic:

```bash
# /etc/librefolio-restic.env: where the copies go, and the file with restic's password
RESTIC_REPOSITORY=sftp:backup@nas.example:/srv/restic/librefolio
RESTIC_PASSWORD_FILE=/root/.restic-librefolio-password
```

**En el `crontab`**:

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /var/backups/librefolio/ && . /etc/librefolio-restic.env && restic backup /var/backups/librefolio/ && restic forget --keep-daily 7 --keep-weekly 4 --prune && find /var/backups/librefolio/ -name 'librefolio-backup-*' -mtime +2 -delete
```

La línea crea el archivo, envía la carpeta, conserva siete copias diarias y cuatro semanales en el repositorio y elimina los archivos locales con más de dos días. Con Docker, crea el archivo con el comando de [Mantén copias fuera del servidor](#keep-copies) y da a restic la carpeta del host `LibreFolio-data/backups/`. Con Backrest, añade un plan sobre esa carpeta, con su programación y su retención, y deja `backup create` en cron.

- 🔐 **La contraseña de restic es una clave a todos tus datos**: quien la tenga lee todas las copias. Tan privada como la contraseña de una [copia de seguridad segura](#secure), con una copia en otro lugar: si se pierde, el repositorio ya no se puede leer.
- 🔑 **Sin clave pública.** restic usa su contraseña tanto para escribir como para leer: el servidor que envía las copias también puede leerlas. Si eso es un problema, envía [copias de seguridad selladas](backup_sealed.md#sealed-cron) (`--sealed`): solo tu clave privada las abre, ni el servidor ni la contraseña de restic. Las [copias de seguridad seguras](#secure) (`--password-file`) también funcionan, pero su contraseña reside en un archivo en el mismo servidor.
- 📦 **Poco que deduplicar.** Cada archivo está comprimido y uno seguro está cifrado: restic almacena cada archivo casi entero. Planifica el espacio del repositorio para las copias que conserves.
- 🧪 **Prueba una restauración antes de necesitarla.** `restic restore latest --target /tmp/librefolio-check`, luego comprueba el archivo con [`backup restore --dry-run`](#check).

---

## 🔐 Copias de seguridad seguras {: #secure }

Una copia de seguridad segura es el archivo de una copia de seguridad sin cifrar, cifrado con una contraseña que elijas, en un archivo propio de LibreFolio: `.lfbk`. La haces desde [Configuración › Administración › Copia de seguridad](#settings-backup) o con `backup create --encrypt` en la [línea de comandos](#command-line); toda comprobación y restauración de esta página la acepta, dada su contraseña.

- 🛡️ **Protege el archivo en reposo.** Disco perdido, portátil robado, copia en una nube o en un NAS: sin la contraseña no se puede leer nada, ni los datos ni los nombres de los archivos. Un archivo cambiado o truncado se detecta al abrirlo y se rechaza.
- 👁️ **No protege de quien conozca la contraseña**: lee todo, los datos de todos los usuarios y las claves de los proveedores de datos. Dásela solo a quien pueda restaurar la copia de seguridad, nunca junto con el archivo.
- 🗝️ **Lleva la clave de instancia**, si LibreFolio la generó (`secrets/instance.key`): las claves guardadas de los proveedores de datos viajan con la copia de seguridad, y la restauración las vuelve a cifrar con la clave de la instalación que la recibe, que conserva la suya. Una clave que establezcas tú (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) nunca sale.
- 🆘 **Una contraseña perdida no se puede recuperar.** LibreFolio no guarda ninguna copia de ella, y nada más abre el archivo.
- ⏳ **Lento de adivinar.** La clave del archivo sale de la contraseña mediante scrypt: 32 MiB de memoria y alrededor de una décima de segundo por intento, nada para una copia de seguridad, lento para quien prueba contraseñas una tras otra. De ahí las reglas: al menos 12 caracteres, una letra mayúscula, una letra minúscula, un dígito y un símbolo.
- 💽 **En el servidor, mientras se crea,** el archivo sin cifrar se escribe primero, en la carpeta de trabajo de la copia de seguridad dentro de `backups/`, que solo el usuario del servidor puede abrir; se elimina en cuanto se escribe el `.lfbk`, y cuando la copia de seguridad falla. Tras una interrupción abrupta (corte de energía, `kill -9`), el siguiente inicio de LibreFolio elimina lo que quedó sin cifrar, y la copia de seguridad debe hacerse de nuevo. Una comprobación descifra la copia de seguridad de la misma manera: [Comprobar una copia de seguridad](#check).

El diseño, para desarrolladores: [Copias de seguridad seguras (`.lfbk`)](../developer/architecture/security.md#secure-backups).

---

## 🔎 Comprobar una copia de seguridad {: #check }

Dos comandos comprueban un archivo sin cambiar nada. **En el terminal del servidor**, dentro del contenedor con Docker: un archivo en `LibreFolio-data/backups/` está allí en `/app/backend/data/prod-docker/backups/`, y una copia de seguridad [conservada](#kept-backups) está en su propia carpeta, como `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`.

```bash
# Is the archive whole, and what does it hold?
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Can this installation restore it? A restore tried on a copy
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# A secure backup: the same commands ask its password first
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk
```

Instalación en host: `pipenv run ./dev.py backup …` con la ruta del archivo en el host.

| | `backup inspect` | `backup restore --dry-run` |
| --- | --- | --- |
| Responde | Si el archivo está íntegro: tamaño y SHA-256 de cada entrada, comparados con el manifiesto | Si esta instalación puede restaurarlo: archivo descomprimido en una copia, actualizado y comprobado |
| Muestra | Quién hizo el archivo y cuándo, revisión de la base de datos, filas y tablas, archivos, si la clave de instancia está incluida | Lo mismo, más: las migraciones que aplicaría una restauración, los totales del libro mayor de la copia comparados con los del archivo, las claves de proveedores vueltas a cifrar con la clave de esta instalación o por introducir de nuevo, los administradores con los que iniciarías sesión |
| Necesita | Cualquier LibreFolio, con el servidor en marcha o detenido; sin directorio de datos, salvo para una copia de seguridad segura, que descifra allí | La instalación que recibiría el archivo (el servidor puede seguir en marcha) y espacio libre en su directorio de datos: archivo descomprimido + el doble de su base de datos + 64 MB |
| Termina con | `✅ Every entry matches the manifest` | `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` |

- 🔐 **Copia de seguridad segura** (`.lfbk`): ambos piden primero la contraseña, en el terminal o con `--password-file FILE` / `--password-stdin`, como `backup create`. La descifran en una carpeta privada del directorio de datos, que solo el usuario del servidor puede abrir, y eliminan el archivo descifrado al final: también hace falta espacio para eso, aproximadamente el tamaño del `.lfbk`. Tras una interrupción abrupta (corte de energía, `kill -9`), el siguiente inicio de LibreFolio elimina lo que quedó sin cifrar: el archivo de `--dry-run` de inmediato, la carpeta de `inspect` después de una hora, que el siguiente `inspect` también elimina. El informe añade `Secure backup: decrypted with its password`. Contraseña incorrecta: `❌ The password does not open this backup (wrong_password)`. Un `.zip` ignora las dos opciones.
- 🗝️ `--dry-run` dice qué ocurre con las claves guardadas de los proveedores de datos, para cualquier archivo: `Saved provider keys: 2 re-encrypted with this instance's key` si la copia de seguridad lleva la clave que las cifró, `⚠️ 1 saved provider key cannot be read with this instance's key: enter it again after the restore` para las que no puede leer ([Lo que sigue](#what-follows)).
- 🔁 Ejecuta `inspect` de vez en cuando sobre las copias que conserves, y `--dry-run` antes de un traslado, en la instalación que recibirá el archivo.
- 🖱️ **Restaurar un archivo**, en Configuración › Administración › Copia de seguridad, ejecuta la misma comprobación que `--dry-run` sobre un archivo de tu ordenador: lee el informe, luego **Descartar este archivo**, y nada cambia ([Restaurar desde Configuración › Administración › Copia de seguridad](#restore-settings)).
- ❌ Un rechazo termina con un código entre paréntesis: [Cuando algo va mal](backup_moving.md#troubleshooting). Listas completas en «Comprobar un archivo» y «Probar una restauración sobre una copia», en [Herramientas de administración de CLI](cli_tools.md).

---

## ♻️ Restaurar en esta instalación {: #restore }

Una restauración reemplaza los datos de la instalación con los del archivo: base de datos y archivos, para todos los usuarios. Dos caminos, que comprueban primero el archivo sobre una copia y no cambian nada hasta que confirmes; el siguiente inicio de LibreFolio aplica la restauración:

| Dónde | Quién | Tras confirmar |
| --- | --- | --- |
| **Configuración › Administración › Copia de seguridad**, en la aplicación | Administradores | LibreFolio se detiene de inmediato, para ese inicio |
| **Terminal en el servidor**: `backup restore` | Quien tenga acceso al servidor | Lo reinicias cuando te convenga |

En una instancia que alguien aloja para ti, la línea de comandos está en su servidor: usa Configuración › Administración › Copia de seguridad, o pídeselo.

### 🖱️ Restaurar desde Configuración › Administración › Copia de seguridad {: #restore-settings }

1. **Elige el archivo.** En **Configuración › Administración › Copia de seguridad**, bajo **Copia de seguridad de la instancia**, la tarjeta **Restaurar un archivo** te recuerda que una restauración reemplaza los datos de todos los usuarios: si puede que quieras recuperarlos, [haz una copia de seguridad primero](#settings-backup). **Elegir un archivo…** → un `.zip` o un `.lfbk` seguro hecho por LibreFolio, aquí o en otro lugar. Se abre la ventana **Restaurar un archivo**, y los pasos siguientes continúan en ella: un `.zip` se envía al servidor de inmediato, con una barra de progreso: **Detener el envío** lo detiene, y no se conserva nada.

    **O toma una copia de seguridad que el servidor conserva**: **Restaurar** en su fila de la lista de [copias de seguridad conservadas en el servidor](#kept-backups), aquí o en **Archivos › Copias**, abre la ventana **Restaurar una copia de seguridad**, sin más confirmación: el servidor toma esa copia de seguridad como archivo, sin descarga ni subida, y los pasos siguientes, informe incluido, ocurren en esa ventana. Ciérrala, o elige **Lo decido después** en el informe: la comprobación espera en la tarjeta **Restaurar un archivo**, con **Retomar** y **Descartar**. Una copia de seguridad sellada de un panel de alojamiento solo se abre con la clave privada de sus destinatarios: no se restaura aquí.

2. **Escribe la contraseña**, para una copia de seguridad segura: la ventana la pide antes de enviar nada (*Una copia segura: escribe la contraseña con la que se hizo.*). Rellena **Contraseña de la copia** y haz clic en **Comprobar la copia**: el archivo se envía, y la contraseña va con la solicitud que inicia la comprobación, que la prueba de inmediato. Contraseña incorrecta → *Contraseña incorrecta, o el archivo fue modificado: vuelve a escribir la contraseña.*; el archivo permanece en el servidor y el siguiente intento no lo envía de nuevo. **Cancelar** olvida el archivo.
3. **Deja que se compruebe.** El servidor comprueba el archivo sobre una copia, como hace `backup restore --dry-run` ([Comprobar una copia de seguridad](#check)): *Descifrando la copia* (solo segura), *Comprobando el archivo*, *Extrayéndolo en una copia*, *Actualizando la base de datos de la copia*, *Verificando la copia*. Nada cambia hasta que confirmes. **Detener la comprobación** la descarta (una comprobación aún en ejecución se descarta en cuanto termina).
4. **Lee el informe**, en la ventana **Lo que haría esta restauración**: cerrarla guarda la comprobación para después, como hace **Lo decido después**. Cerrar la ventana durante la comprobación también la guarda: la comprobación sigue, y **Retomar** vuelve a seguirla. Lo que dice: más abajo.
5. **Escribe la palabra.** La ventana muestra una palabra real, elegida al azar, de 6 a 10 letras en el idioma de la interfaz. Escríbela a mano en el campo de debajo: el campo rechaza el texto pegado y arrastrado. La palabra protege contra un clic apresurado, no contra un administrador: la API y la línea de comandos prescinden de ella. Para un archivo que no se puede restaurar, no aparecen ni la palabra ni **Restaurar y reiniciar**: solo el botón que lo descarta.
6. **Restaurar y reiniciar.** Confirma la restauración y detiene LibreFolio de inmediato, para todos. Una ventana cubre la página, **LibreFolio se está reiniciando**: *Su inicio aplica la restauración. Esta página espera a que vuelva.* LibreFolio no se reinicia por sí solo: lo hace lo que lo supervise ([Quién inicia LibreFolio de nuevo](#supervisors)), y ese inicio aplica la restauración ([Qué hace el siguiente inicio](#next-start)).

#### 📋 Lo que dice el informe

- quién hizo el archivo, con qué versión de LibreFolio y cuándo;
- la base de datos: en la versión de este LibreFolio, o llevada a ella en la copia, con las migraciones enumeradas y las correcciones aplicadas a la copia;
- los archivos y su tamaño, el tamaño de la base de datos y las tablas cuyas filas cambió la actualización; y una barra de lo que contiene la copia de seguridad: la base de datos, los archivos subidos, los informes del bróker y los demás archivos;
- si la copia de seguridad lleva la clave de la instancia de la que viene: en cualquier caso, este LibreFolio conserva la suya;
- las claves guardadas de los proveedores de datos: cuántas se vuelven a cifrar con la clave de este LibreFolio (*2 claves guardadas de proveedores de datos se vuelven a cifrar con la clave de esta instancia.*) y cuántas son ilegibles, para introducir de nuevo tras la restauración (*1 clave guardada de un proveedor de datos no se puede leer con la clave de esta instancia: vuelve a introducirla tras la restauración.*) ([Lo que sigue](#what-follows));
- los totales del libro mayor: los mismos que cuando se hizo la copia de seguridad, diferentes en las líneas enumeradas ([cómo leerlos](backup_moving.md#check-refused)), no registrados, registrados por otra versión del método o ilegibles;
- los administradores de la copia de seguridad, con *Después de la restauración se inicia sesión con uno de ellos, con la contraseña de entonces; todas las sesiones abiertas ahora se cierran.*
- *Las invitaciones y los enlaces enviados antes de la restauración habrán caducado: vuelve a enviarlos si hace falta.*
- cada administrador con la imagen de su cuenta en la copia de seguridad, y **Verificar una contraseña antes de restaurar**: elige uno, escribe su contraseña y haz clic en **Verificar**. Respuesta: *Iniciarás sesión con esta contraseña tras la restauración.*, o *Esa no es su contraseña.* La contraseña se compara solo con la copia de seguridad: nunca se almacena, se escribe en el registro ni se devuelve;
- las advertencias, que permiten continuar, y los bloqueos, que prohíben la restauración: una copia de seguridad sin un administrador activo, y una restauración que superaría el [límite de espacio](#space-used), con el tamaño al que subirlo; una comprobación así devuelve su espacio de inmediato, y el informe permanece en pantalla hasta que lo cierres;
- hasta cuándo se conserva el archivo subido: 24 horas después de la comprobación.

Bajo el informe: **Descartar este archivo** descarta la comprobación y su copia, no se restaura nada. **Lo decido después** cierra la ventana y conserva la comprobación: la tarjeta **Restaurar un archivo** muestra *Una restauración espera tu decisión hasta …*, con **Retomar**, que abre de nuevo el mismo informe, y **Descartar**, desde cualquier pestaña o dispositivo de un administrador.

#### 🏁 Cómo fue

Cuando LibreFolio responde de nuevo, la página muestra el resultado:

| Resultado | Lo que ves | Qué hacer |
| --- | --- | --- |
| ✅ **Funcionó** | La página de inicio de sesión, sin mensaje: toda sesión ha terminado. Una restauración que funcionó no deja ninguna línea en la tarjeta | Inicia sesión con un administrador de la copia de seguridad, con la contraseña que tenía cuando se hizo la copia de seguridad: la primera página muestra los datos restaurados |
| ↩️ **No se completó** | **La restauración no se completó**, con el motivo. *Los datos están como antes: …* = revertida, la tarjeta dice cuándo y por qué. *LibreFolio se reinició, pero la restauración no se aplicó.* = un inicio la dejó esperando, por el motivo que sigue | **Volver a la copia de seguridad** regresa a la tarjeta (tras la página de inicio de sesión si el reinicio terminó tu sesión, o a la página de bloqueo en una instancia bloqueada entretanto). Luego [Qué dice Configuración › Administración › Copia de seguridad](backup_moving.md#restore-settings-problems) |
| ⏳ **Tarda mucho** | Tras un minuto sin el servidor: *LibreFolio aún no ha vuelto. Si nada lo reinicia por sí solo, inícialo tú: la restauración se aplica en ese inicio.* Si LibreFolio no se detiene en absoluto, tras un minuto: *LibreFolio no se ha detenido. Si no se reinicia por sí solo, reinícialo tú: la restauración se aplica en ese inicio.*, con **Volver a la copia de seguridad** | [Qué dice Configuración › Administración › Copia de seguridad](backup_moving.md#restore-settings-problems) |

La página lee el resultado con un ticket de un solo uso recibido de la solicitud de reinicio, válido una hora y conservado solo en la memoria de la pestaña: no necesita sesión. Sin el ticket (página recargada, más de una hora de espera, reinicio desde la línea de comandos en lugar de desde aquí) la página se guía por su sesión: sin `JWT_SECRET`, que cierra la sesión de todos en cada inicio ([Mantener a los usuarios con sesión iniciada tras un reinicio](index.md#session-persistence)), va a la página de inicio de sesión sea cual sea el resultado, y **Configuración › Administración › Copia de seguridad** dice, una vez dentro, si la restauración se completó.

#### ⏳ Una restauración en espera

Una restauración confirmada y aún no aplicada ocupa el lugar de **Elegir un archivo…**: una confirmada desde la línea de comandos, o aquí cuando LibreFolio no se detuvo o un inicio la dejó esperando. La tarjeta dice **Una restauración espera el próximo inicio de LibreFolio**, con la copia de seguridad, quién la confirmó (`cli` desde la línea de comandos) y cuándo, el motivo si un inicio la dejó esperando, y *Reiniciar detiene LibreFolio para todos; su próximo inicio aplica la restauración y cierra todas las sesiones.*

| Botón | Qué hace |
| --- | --- |
| **Reiniciar ahora y restaurar** | Detiene LibreFolio, como hace **Restaurar y reiniciar**; la página lo espera de la misma manera |
| **Cancelar la restauración** | La descarta con su copia comprobada, como hace `backup pending --cancel`: los datos quedan como están |

Mientras un inicio aplica la restauración, la tarjeta dice *Un inicio de LibreFolio está aplicando la restauración.*

Conviene saber:

- 👑 Solo los administradores tienen la pestaña. Una restauración a la vez: se comprueba un archivo a la vez, dondequiera que haya comenzado la comprobación, aquí, en otra pestaña o en la línea de comandos (*Se está comprobando otro archivo: inténtalo cuando termine.*).
- 📏 Si la instalación limita el tamaño de los archivos (`LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, ninguno por defecto), la tarjeta lo dice (*Archivos de hasta 500 MB.*) y rechaza un archivo mayor antes de enviar nada: [El límite de subida de una restauración](#restore-upload-limit).
- 💽 El disco del directorio de datos necesita espacio para el archivo, para su copia durante la comprobación y, para una copia de seguridad segura, para el archivo descifrado: cuánto, en [Comprobar una copia de seguridad](#check).
- 📦 Durante la comprobación, el archivo ocupa su tamaño en el servidor, que la tarjeta dice mientras se sube, más su versión descomprimida; ambos cuentan para el límite de espacio hasta que la restauración termina o se descarta.
- 🔑 La contraseña de una copia de seguridad segura va al servidor solo con la solicitud que inicia la comprobación, que la prueba de inmediato: nunca se almacena, se escribe en el registro ni se devuelve. El campo se vacía en cuanto la envías.
- 🔄 Una recarga de la página sigue la comprobación y el informe, y cualquier otra pestaña o dispositivo de un administrador lo retoma desde la pestaña Copia de seguridad. El archivo subido se conserva 24 horas: después, la confirmación responde *La comprobación es demasiado antigua: vuelve a comprobar el archivo.*
- 🚪 La restauración termina toda sesión, todos inician sesión de nuevo con una cuenta de la copia de seguridad, y los enlaces enviados antes dejan de funcionar: [Qué hace el siguiente inicio](#next-start).
- ❌ Una subida, comprobación o confirmación rechazada, o un servidor que no responde, se muestra en la tarjeta con el motivo. **Reintentar** vuelve a leer el estado de la restauración; para enviar un archivo de nuevo, **Elegir un archivo…**. La comprobación rechaza los mismos archivos que la línea de comandos: [La comprobación rechaza el archivo](backup_moving.md#check-refused).
- 🖥️ Si nada reinicia LibreFolio, como una instalación en host iniciada a mano, [inicia el servidor](cli_tools.md#start-the-server) tú mismo una vez que se haya detenido: la página lo espera.

### 📤 El límite de subida de una restauración {: #restore-upload-limit }

Un administrador sube el archivo desde Configuración › Administración › Copia de seguridad ([Restaurar desde Configuración › Administración › Copia de seguridad](backup_restore.md#restore-settings)), mediante `PUT /api/v1/backup/restore/upload`, y la instancia lo comprueba sobre una copia, como hace `backup restore --dry-run` en la [línea de comandos](cli_tools.md). Dos variables limitan su tamaño.

**`LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`** limita el archivo tal como se envía, comprimido:

| Valor | Archivo más grande aceptado |
| --- | --- |
| Sin establecer, o vacío | Sin límite |
| `0` | Sin límite |
| Un número entero, como `2048` | Esos megabytes, de 1024 × 1024 bytes cada uno |

1. **En `.env`**, o en el entorno del contenedor:

    ```bash
    LIBREFOLIO_BACKUP_MAX_UPLOAD_MB=2048
    ```

2. Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.
3. **En la configuración del proxy** delante de LibreFolio, deja pasar al menos tanto: Nginx con `client_max_body_size`, cuyo valor predeterminado es solo 1 MB (`client_max_body_size 2048m;` coincide con el ejemplo), y tu CDN, si limita el tamaño de una solicitud.

El límite vigente se lee en `upload_limit_mb` de `GET /api/v1/backup/restore/status`: `0` sin límite, `null` valor ilegible. Configuración › Administración › Copia de seguridad lo muestra en la tarjeta de restauración (*Archivos de hasta 500 MB.*) y rechaza un archivo mayor antes de enviarlo.

| La subida responde | Código | Cuándo |
| --- | --- | --- |
| `413` | `backup_too_large`, con el límite en `limit_mb` | Archivo por encima del límite: antes de escribir nada si la solicitud anuncia su tamaño, de lo contrario en cuanto la subida supera el límite. No se conserva nada |
| `413` sin `backup_too_large` | — | Viene del proxy, no de LibreFolio |
| `503` | `backup_upload_unavailable` | Valor que no es un número entero (`500MB`, `-1`): el servidor no se detiene, pero el registro de inicio ya tiene `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: …` (`check` es `backup.upload_limit`) y cada subida añade al registro un error que nombra la variable: `The upload limit of a restore cannot be read` |
| `507` | `backup_no_space` | El disco del directorio de datos no tiene espacio para el archivo y, durante la comprobación, para su copia descomprimida (cuánto: «Probar una restauración sobre una copia» en [Herramientas de administración de CLI](cli_tools.md)); también cuando el disco se declara lleno solo al final del archivo, como puede hacer un sistema de archivos de red o una cuota. La comprobación tiene un código propio, `no_space`: `507` si ni siquiera puede empezar, rechazo del archivo una vez que se ejecuta |
| `500` | `backup_upload_failed` | La subida no se puede escribir por otro motivo; el registro tiene la causa |

**`LIBREFOLIO_BACKUP_MAX_RESTORE_MB`** limita el tamaño descomprimido, a partir de los tamaños que declara el manifiesto, antes de que la comprobación descomprima nada: un zip puede descomprimirse a mucho más que su tamaño, en el disco del directorio de datos.

| Valor | Mayor tamaño descomprimido de un archivo |
| --- | --- |
| Sin establecer, o vacío | Sin límite |
| `0` | Sin límite |
| Un número entero, como `16384` | Esos megabytes, de 1024 × 1024 bytes cada uno |

- Un archivo por encima del límite se rechaza antes de descomprimir nada: la comprobación falla con el código `unpacked_too_large`, no queda nada de la copia. Un archivo seguro se descifra primero (aproximadamente su tamaño), luego se mide de la misma manera.
- Un valor que establezcas siempre prevalece, `0` incluido. `backup restore` en la línea de comandos sigue el mismo límite; quien ejecuta el servidor lo levanta para un comando con `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` delante («Probar una restauración sobre una copia» en [Herramientas de administración de CLI](cli_tools.md)).
- Un valor que no sea un número entero no detiene el servidor: el registro de inicio ya tiene `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: …` (`check` es `backup.restore_limit`), luego cada comprobación, `POST /api/v1/backup/restore/stage`, responde `503` con el código `backup_restore_unavailable`, el archivo se conserva y el registro tiene un error.

### ⌨️ Restaurar desde la línea de comandos {: #restore-command }

**En el terminal del servidor**, donde se ejecuta LibreFolio: en el contenedor con Docker.

```bash
# 1. Check the archive on a copy, read the report, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# 2. Restart LibreFolio: its next start applies the restore
docker compose restart librefolio

# 3. See how it went
docker compose exec librefolio python dev.py backup pending
```

- 🧪 El paso 1 ejecuta la misma comprobación que `--dry-run`, muestra el mismo informe, luego te pide escribir `restore`. Nada cambia todavía: LibreFolio sigue en marcha con sus datos, la restauración espera al siguiente inicio.
- 🖥️ Instalación en host: `pipenv run ./dev.py backup restore <archive>`, luego detén todo el servidor y [inícialo](cli_tools.md#start-the-server) de nuevo: nunca un solo worker.
- ⏳ Con LibreFolio en marcha de nuevo, `backup pending` dice `✅ The last restore was applied on …`. Antes del reinicio, `backup pending --cancel` descarta la restauración en espera, con su copia comprobada.
- 🤖 En un script, `--yes` confirma sin preguntar.
- 🔐 Copia de seguridad segura (`.lfbk`): `backup restore` pide la contraseña antes de la comprobación, o la lee con `--password-file` o `--password-stdin`, como hace `inspect` ([Comprobar una copia de seguridad](#check)): en un script, una de las dos junto con `--yes`.
- 📖 Más: «Restaurar un archivo» y «Seguir o cancelar una restauración» en [Herramientas de administración de CLI](cli_tools.md).

### 🔄 Qué hace el siguiente inicio {: #next-start }

- 🔀 **El intercambio.** La base de datos y las tres carpetas de archivos cambian de lugar con la copia comprobada, en un instante sea cual sea el tamaño. `secrets/`, `logs/`, `scheduler_state.json` y `backups/` permanecen como están: la instalación conserva su propia clave de instancia. La clave que lleva una copia de seguridad segura nunca se pone en su lugar: la comprobación ya volvió a cifrar las claves de los proveedores de datos en la copia, con la clave de esta instalación.
- 🚪 **Toda sesión termina.** Todos inician sesión de nuevo, en cada dispositivo, con una cuenta de la copia de seguridad y la contraseña que tenía entonces.
- 🔗 **Los enlaces de un solo uso se revocan.** Ningún enlace de invitación, de restablecimiento de contraseña ni de verificación de correo electrónico enviado antes funciona ya, ni siquiera los que contenía la copia de seguridad: envía nuevos. Una cuenta que aún espera la verificación de su correo electrónico deja de esperar: cuando su propietario pide a la página de inicio de sesión un nuevo enlace, la página responde que la cuenta está deshabilitada. Un administrador la reactiva con **Reactivar** ([Qué hace cada acción](users.md#actions)) o la elimina ([Eliminar una cuenta](users.md#delete)) para que su propietario se registre de nuevo.
- ✅ **El primer inicio debe completarse.** Solo entonces se conserva la restauración y se eliminan los datos anteriores. Si falla (migración fallida, archivo dañado), el siguiente inicio vuelve a poner los datos anteriores por sí solo, y `backup pending`, como la tarjeta en Configuración › Administración › Copia de seguridad, dice que se hizo la reversión, con el motivo.

### 🔌 Quién inicia LibreFolio de nuevo {: #supervisors }

Tú inicias la restauración: con el reinicio de la línea de comandos, o con **Restaurar y reiniciar** en Configuración › Administración › Copia de seguridad, que detiene LibreFolio. Nada en LibreFolio reinicia el servidor: lo hace lo que lo supervise, después de esa parada y después de un primer inicio que falla, para que el siguiente inicio recupere los datos.

| Supervisor | Reinicia LibreFolio por sí solo |
| --- | --- |
| Docker Compose | Con `restart: unless-stopped`, en ambos archivos compose que incluye LibreFolio |
| systemd | Con `Restart=always` |
| Ninguno | No: inicia LibreFolio tú mismo, y la restauración, o la vuelta atrás, ocurre en ese inicio |

**Restaurar y reiniciar** detiene LibreFolio limpiamente: una política que solo reinicia tras un fallo, como `on-failure`, no lo inicia después de esa parada.

---

## 🔗 Relacionado

- 📄 **[Copias de seguridad: Copias selladas](backup_sealed.md)** — Copias de seguridad selladas: una clave en lugar de una contraseña
- 📄 **[Copias de seguridad: Traslado y solución de problemas](backup_moving.md)** — Lleva tu LibreFolio a casa, cuando algo va mal
- 🛠️ **[Herramientas de administración de CLI](cli_tools.md)** — «Hacer copia de seguridad de la instancia»: cada opción y mensaje de `backup create`, `inspect`, `restore`, `decrypt` y `pending`, y «Hacer copia de seguridad con Docker»
- 📂 **[Estructura del sistema de archivos](filesystem.md)** — El directorio de datos, `secrets/` y una copia hecha a mano
- 🐳 **[Instalación con Docker](../user/installation.md)** — Instalar LibreFolio y actualizarlo
- 👥 **[Usuarios e invitaciones](users.md)** — Reactivar o eliminar cuentas y enviar nuevos enlaces
- 📧 **[Correo electrónico](email.md)** — Las variables de correo electrónico, que ningún archivo contiene
- 📝 **[Variables de entorno](configuration.md)** — «La clave de la instancia» y cada opción de `.env`
- 🧑‍💻 Para desarrolladores: **[Restaurar una copia de seguridad](../developer/architecture/security.md#backup-restore)** — El intercambio, el diario, la reversión y el reinicio
- 🧑‍💻 Para desarrolladores: **[Copias de seguridad seguras (`.lfbk`)](../developer/architecture/security.md#secure-backups)** — El sobre, la contraseña y la clave de instancia que lleva una copia de seguridad segura
- 🧑‍💻 Para desarrolladores: **[Copias de seguridad selladas (`.tar`)](../developer/architecture/security.md#sealed-backups)** — Los tres miembros, age mediante `pyrage` y el lector estricto
