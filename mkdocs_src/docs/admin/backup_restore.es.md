# 💾 Copia de seguridad, restauración y traslado de tu instancia

Una copia de seguridad es un archivo con todo tu LibreFolio dentro: la base de datos y los archivos de cada usuario, en un zip simple o, para una [copia de seguridad segura](#secure), cifrado con una contraseña que elijas. Esta página cuenta toda la historia: qué contiene el archivo, cómo hacer y comprobar uno, cómo protegerlo con una contraseña, cómo restaurarlo y cómo trasladar LibreFolio desde una instancia que alguien aloja para ti a tu propio servidor, o al revés. Cada opción y mensaje de los comandos está en «Hacer copia de seguridad de la instancia», en [Herramientas de administración de CLI](cli_tools.md).

!!! tip "🗓️ Haz una antes de cada actualización"

    LibreFolio nunca lleva una base de datos a una versión anterior. Una copia de seguridad hecha antes de una actualización es tu camino de vuelta a la versión que tenías: consulta [Actualizar LibreFolio](../user/installation.md#updating).

!!! info "📚 Esta guía está en varias páginas"

    Además de esta página: [Copias de seguridad: Copias selladas](backup_sealed.md), [Copias de seguridad: Traslado y solución de problemas](backup_moving.md).

---

## 📦 Qué contiene una copia de seguridad {: #contents }

El archivo es un zip con la estructura del [directorio de datos](filesystem.md): descomprimido en un directorio de datos vacío, vuelve a ser tu instancia. Una [copia de seguridad segura](#secure) es el mismo zip, cifrado con una contraseña en un archivo `.lfbk`, y una [copia de seguridad sellada](backup_sealed.md#sealed) es una copia de seguridad segura cuya contraseña solo puede abrir una clave privada tuya, en un `.tar`.

| En el archivo | Qué es |
| --- | --- |
| `sqlite/app.db` | La base de datos: usuarios, brókers, transacciones, activos, precios, tipos de cambio y configuración. Una copia consistente, hecha mientras LibreFolio sigue ejecutándose |
| `custom-uploads/` | Los archivos subidos en la aplicación |
| `broker_reports/` | Los informes del bróker |
| `scenario_catalog/` | Tus propios escenarios de estrés, si añadiste alguno |
| `secrets/instance.key` | Solo en una [copia de seguridad segura](#secure), y solo cuando LibreFolio generó la clave de instancia: la clave que cifró las claves guardadas de los proveedores de datos, para que viajen con los datos. Una restauración solo la lee: la instalación que recibe la copia de seguridad conserva su propia clave |
| `manifest.json` | La descripción del archivo: la versión de LibreFolio que lo hizo y cuándo, la revisión de migración de la base de datos, sus filas por tabla, los totales de control del libro mayor (el efectivo de cada bróker en cada moneda y la cantidad de cada posición), el tamaño y la suma de comprobación SHA-256 de cada archivo, y si el archivo contiene la clave de instancia |

Nunca en el archivo:

- 🔑 `secrets/`, que contiene la clave de instancia: una [copia de seguridad segura](#secure) solo contiene la clave que generó LibreFolio, `secrets/instance.key`, nunca una clave que hayas establecido tú con `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`. Consulta «La clave de la instancia» en [Variables de entorno](configuration.md);
- 📝 `logs/`, y `scheduler_state.json`, la última ejecución de las sincronizaciones programadas;
- 💾 `backups/`, donde LibreFolio [conserva las copias de seguridad que hace](#kept-backups), y `.restore/`, la carpeta de trabajo de una restauración;
- ⚙️ la configuración: `.env` y las variables de entorno, incluida la configuración de [correo electrónico](email.md), que LibreFolio solo guarda en el entorno.

### 🧭 Lo que sigue {: #what-follows }

- 🔒 **Mantenla privada.** Un archivo sin cifrar contiene los datos de todos los usuarios y no está cifrado: mantenlo, junto con cada copia, tan privado como el propio servidor. Una [segura](#secure) solo se abre con su contraseña: guarda la contraseña por separado.
- 🗝️ **Secretos guardados y la clave de instancia.** Lo que LibreFolio cifró con la clave de instancia, como la clave de API de una fuente de datos guardada en la aplicación, solo se puede leer con esa clave.
    - Una [copia de seguridad segura](#secure) contiene la clave que generó LibreFolio: su restauración vuelve a cifrar esos secretos con la clave de la instalación que la recibe, y no hay nada que hacer.
    - Una copia de seguridad sin cifrar omite la clave; también la omite siempre una [sellada](backup_sealed.md#sealed), y una segura cuya clave provino del entorno (`LIBREFOLIO_INSTANCE_KEY`, `LIBREFOLIO_INSTANCE_KEY_FILE`) o no se pudo usar. En una instalación con otra clave, LibreFolio conserva esos secretos, los informa como ilegibles y nunca usa un valor incorrecto: **Configuración › Complementos** dice bajo cada uno *Guardado, pero la clave de esta instancia no puede leerlo: vuelve a introducirlo.* Si aún tienes la clave antigua, vuelve a ponerla primero, antes de que nadie introduzca un secreto de nuevo: detén LibreFolio, pon tu copia de `secrets/instance.key` en lugar de la generada, o establece el valor antiguo de la variable, y vuelve a iniciarlo («La clave de la instancia» en [Variables de entorno](configuration.md)). Una instalación que conserva su propia clave, o una cuyos propios secretos ya están bajo su clave, toma la clave antigua en la restauración: restaura desde la línea de comandos con `--instance-key-file` y tu copia de la clave antigua, y la comprobación vuelve a cifrar esos secretos con la clave de esta instalación («La clave de instancia de otra instalación» en [Herramientas de administración de CLI](cli_tools.md)). Vuelve a introducir los secretos solo si la clave antigua se pierde: un secreto introducido bajo la nueva clave se volvería ilegible una vez que la antigua vuelva.
    - Para la configuración de toda la instancia, cada inicio también registra el error *Secretos de complementos almacenados que la clave de la instancia no puede leer: …* con su recuento, hasta que se vuelvan a introducir o vuelva la clave antigua. Ningún complemento distribuido con LibreFolio guarda hoy ninguno de esos secretos.
- ⚙️ **Lleva tu configuración.** Guarda una copia de tu `.env` junto con las copias de seguridad: en otra instalación, vuelve a establecer las opciones que necesites, incluidas las de correo electrónico ([Dónde vive la configuración](email.md#where-it-lives)).
- 🏠 **Cualquier instalación puede aceptarla**, si ejecuta la misma versión de LibreFolio o una más reciente, quienquiera que haya creado el archivo: Configuración o la línea de comandos.

---

## ⬇️ Hacer una copia de seguridad {: #create }

Tres formas producen el mismo archivo:

- **Configuración › Administración › Copia de seguridad**, en la aplicación: el archivo se descarga en tu ordenador. Para administradores.
- **La línea de comandos**, en el servidor: `backup create`.

Desde Configuración y desde la línea de comandos, la copia de seguridad también puede ser [segura](#secure): el mismo zip, cifrado con una contraseña que elijas. Desde la línea de comandos, también puede ser [sellada](backup_sealed.md#sealed): cifrada con una contraseña aleatoria que solo puede abrir una clave privada tuya, para copias de seguridad hechas sin nadie frente al teclado.

En todos los casos, LibreFolio sigue funcionando durante la copia de seguridad, y se ejecuta una copia a la vez, sea quien sea quien la haya iniciado.

### 🖱️ Desde Configuración › Administración › Copia de seguridad {: #settings-backup }

1. Abre **Configuración › Administración › Copia de seguridad**: solo los administradores tienen esta pestaña.
2. En **Hacer copia de seguridad de la instancia**, elige el tipo de copia de seguridad:
    - **Sin cifrar**, la opción con la que empieza la tarjeta: *Un .zip simple: quien tenga el archivo ve todos los datos, y en otra instancia deben introducirse de nuevo las claves de los proveedores de datos.*
    - **Segura**: *Un .lfbk cifrado con una contraseña que elijas: solo esa contraseña lo abre, y una contraseña perdida no se puede recuperar. También contiene las claves de los proveedores de datos.* Consulta [Copias de seguridad seguras](#secure).
3. Para una copia de seguridad segura, escribe su contraseña en **Contraseña de la copia de seguridad**, y luego otra vez en **La misma contraseña de nuevo**. La contraseña sigue las reglas que indica el servidor, las de la contraseña de una cuenta con al menos 12 caracteres: el medidor bajo el primer campo las enumera mientras escribes (*Al menos 12 caracteres*, *Una letra mayúscula*, *Una letra minúscula*, *Un número*, *Un carácter especial*) y muestra lo fuerte que es la contraseña. Mientras los dos campos difieran, *Las dos contraseñas difieren.* aparece bajo el segundo, y **Crear copia de seguridad** permanece deshabilitado hasta que ambos sean correctos.
4. Haz clic en **Crear copia de seguridad**. Los campos de contraseña se vacían de inmediato. La tarjeta sigue la copia de seguridad en el servidor, fase por fase; una copia de seguridad segura termina con *Cifrando con tu contraseña*.
5. Cuando muestre **Copia de seguridad lista**, haz clic en **Descargar**. Tu navegador guarda el archivo, con el nombre del momento en que comenzó la copia de seguridad, en UTC, como `librefolio-backup-20261015-121500.zip`, o `librefolio-backup-20261015-121500.lfbk` para una copia de seguridad segura, que la tarjeta marca *Cifrado con tu contraseña: guárdalo a salvo, LibreFolio no puede recuperarlo.* Una copia permanece en el servidor, en la lista de [Copias de seguridad conservadas en el servidor](#kept-backups): descárgala también desde allí más tarde.

Conviene saber:

- 🔑 **Guarda la contraseña de una copia de seguridad segura.** LibreFolio no guarda ninguna copia de ella, y sin ella nadie abre el archivo, tú incluido: guárdala en un gestor de contraseñas, aparte del archivo.
- 💾 El archivo permanece en el servidor hasta que lo elimines, o hasta que la [limpieza automática](#backup-cleanup) que configures lo elimine. Una copia en el mismo disco que tus datos no es una copia de seguridad real: descárgala y guárdala en otro lugar ([Mantén copias fuera del servidor](#keep-copies)). **Eliminar del servidor** lo elimina de inmediato, y **Crear una nueva copia de seguridad** inicia otra.
- ⚠️ **La copia de seguridad está completa, con advertencias** significa que la base de datos falló su comprobación de integridad o tiene referencias rotas, y se archivó tal cual, o que se omitieron algunos archivos, o, para una copia de seguridad segura, que la clave de la instancia no se pudo usar y se omitió ([Hacer una copia de seguridad segura](backup_moving.md#secure-problems)). El archivo se escribe de todos modos: lee las advertencias antes de confiar en él.
- 🚦 Mientras se ejecuta otra copia de seguridad, iniciada desde la aplicación o la línea de comandos, la tarjeta lo indica: inténtalo de nuevo cuando termine. Una iniciada desde esta pestaña, o desde otra pestaña de la aplicación, cuya respuesta nunca llegó (la conexión se cayó mientras se iniciaba) no se pierde: la siguiente **Crear copia de seguridad** la encuentra en ejecución, y la tarjeta la sigue y luego ofrece su descarga, como si acabara de iniciarla. Esto solo vale para una copia de seguridad sin cifrar: una segura nunca se sigue de esta manera, porque solo su propia contraseña abre su archivo, y una copia seguida que resulta ser segura no se ofrece, a menos que la tarjeta la haya iniciado ella misma; en ambos casos la tarjeta dice que se ejecuta otra copia de seguridad. Una tarjeta que ya ofrece un archivo sigue ofreciéndolo, y solo dice que se ejecuta otra copia de seguridad. Una iniciada desde la línea de comandos no se sigue: su archivo va a otro lugar. La tarjeta nunca dice qué copia de seguridad se ejecuta; la consola del navegador sí (su id y dónde se inició), por si necesitas encontrarla.

### ⌨️ Desde la línea de comandos {: #command-line }

```bash
# Docker: the archive appears in its own folder of ./LibreFolio-data/backups/ on the host
docker compose exec librefolio python dev.py backup create

# Host installation: the archive goes into its own folder of backups/ in the data directory
pipenv run ./dev.py backup create

# A secure backup (.lfbk): the password is asked twice
docker compose exec librefolio python dev.py backup create --encrypt
```

- 🗃️ Sin `--output`, el archivo permanece en el servidor, en su propia carpeta de `backups/` ([Copias de seguridad conservadas en el servidor](#kept-backups)), y el comando imprime su ruta y su `SHA-256:`.
- 📁 `--output` (`-o`) copia el archivo en otra carpeta que ya exista, o con un nombre propio, e imprime también su `SHA-256:`; entonces no se conserva nada en `backups/`. Con Docker, la ruta está dentro del contenedor: usa una carpeta montada desde el host.
- 🔒 Solo el propietario del archivo puede leerlo (`0600`): con Docker, ese es el usuario del contenedor.
- 🔐 `--encrypt` crea una [copia de seguridad segura](#secure), `librefolio-backup-<date>-<time>.lfbk`, y pide su contraseña dos veces en el terminal. En lugar de escribirla, dala con `--password-file FILE`, un archivo que contiene solo la contraseña (los saltos de línea al final no cuentan), como un secreto de Docker, o con `--password-stdin`, una línea de la entrada estándar, desde una tubería: en un terminal, el comando la pide en su lugar, sin mostrarla, como sin la opción. Cualquiera de las dos hace segura la copia de seguridad por sí sola, con o sin `--encrypt`; las dos no pueden ir juntas.
- 🙈 Una contraseña nunca es un argumento del comando: todos los usuarios del servidor pueden leer los comandos que se ejecutan (`ps`), y el shell los guarda en su historial. No existe la opción `--password`.
- 📏 La contraseña sigue las reglas de Configuración › Administración › Copia de seguridad: al menos 12 caracteres, con una letra mayúscula y una minúscula, un dígito y un símbolo. Una que incumpla algunas detiene el comando antes de que se escriba nada, con las reglas que incumple: `❌ The password of a backup needs at least 12 characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: min_length, digit)`.
- 🤖 Sin terminal, desde cron o un script, `--encrypt` por sí solo se detiene con `❌ A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal (password_required)`.
- 📖 Cada opción, advertencia y error: «Hacer copia de seguridad de la instancia» y «Hacer copia de seguridad con Docker» en [Herramientas de administración de CLI](cli_tools.md).

??? example "🐳 La contraseña de las copias de seguridad como secreto de Docker"

    1. Escribe la contraseña sola en un archivo junto a `docker-compose.yml`, como `backup_password.txt`, nunca en `LibreFolio-data/`: quien tuviera los datos tendría también su contraseña. Mantén el archivo privado, `chmod 600 backup_password.txt`, y una copia de la contraseña en otro lugar: una contraseña perdida no se puede recuperar.
    2. Añade las líneas marcadas a `docker-compose.yml`, y deja el resto del servicio como está:

        ```yaml
        services:
          librefolio:
            secrets:                              # added
              - backup_password                   # added
        secrets:                                  # added
          backup_password:                        # added
            file: ./backup_password.txt           # added
        ```

        Si el archivo ya tiene listas `secrets:`, como para `JWT_SECRET_FILE` («Secretos en archivos» en [Variables de entorno](configuration.md)), añade las líneas a ellas. Luego ejecuta `docker compose up -d`, que recrea el contenedor con el secreto.

    3. Haz la copia de seguridad con la ruta donde Docker pone el secreto en el contenedor:

        ```bash
        docker compose exec librefolio python dev.py backup create --password-file /run/secrets/backup_password
        ```

### 🗃️ Copias de seguridad conservadas en el servidor {: #kept-backups }

Una copia de seguridad hecha desde la aplicación o la línea de comandos ya no se elimina después de una hora: permanece en el servidor hasta que la elimines, o hasta que la [limpieza automática](#backup-cleanup) la elimine. Cada una tiene su propia carpeta en la carpeta `backups/` del directorio de datos, con el nombre del momento en que se hizo (en UTC), de dónde vino (`ui` para la aplicación, `cli` para la línea de comandos) y un código corto que distingue dos copias de seguridad del mismo segundo:

```text
backups/librefolio-backup-20261015-121500-ui-1a2b3c4d/librefolio-backup-20261015-121500.zip
```

El archivo interior conserva su nombre habitual, `.zip`, `.lfbk` o `.tar`. `backups/.jobs/` solo contiene una copia de seguridad en curso o una que falló, que se elimina después de una hora.

**Configuración › Administración › Copia de seguridad**, bajo *Copias de seguridad en este servidor*, enumera cada copia de seguridad conservada. **Archivos**, en su pestaña **Copias de seguridad**, muestra la misma lista; solo los administradores ven cualquiera de las dos. Para cada copia de seguridad ofrece:

- 📅 la fecha y hora en que se hizo, y de dónde vino: la aplicación o la línea de comandos;
- 🔐 su tipo: sin cifrar, con contraseña ([segura](#secure)) o [sellada](backup_sealed.md#sealed);
- 📏 su tamaño, y su SHA-256: haz clic para copiar la suma de comprobación completa, y compárala con la del archivo que descargues;
- ⬇️ **Descargar** y 🗑️ **Eliminar**, que elimina la copia de seguridad del servidor de inmediato.

!!! warning "💽 Descárgala y guárdala en otro lugar"

    Una copia de seguridad que permanece en el mismo disco que tus datos no es una copia de seguridad real: cuando se pierde el disco, los datos y sus copias de seguridad se van juntos. Descarga el archivo y guárdalo en otro disco, un NAS o fuera del sitio ([Mantén copias fuera del servidor](#keep-copies)).

La lista muestra solo las copias de seguridad hechas por esta versión de LibreFolio. Los archivos sueltos `librefolio-backup-*.zip` que versiones anteriores dejaron en `backups/` no se enumeran y LibreFolio nunca los elimina: elimínalos tú cuando ya no los necesites.

### 🧹 Limpieza automática {: #backup-cleanup }

Las copias de seguridad conservadas se acumulan, y viven en el disco de tus datos. En el panel cerrado **Limpieza automática** de la misma sección **Copias de seguridad en este servidor**, en **Configuración › Administración › Copia de seguridad** y en **Archivos › Copias de seguridad**, configuras dos límites, ambos opcionales:

| Límite | Qué hace | Desactivado |
| --- | --- | --- |
| Tamaño total, en MB | Cuando las copias de seguridad conservadas pesan más, se eliminan las más antiguas hasta que el resto quepa | `0` |
| Antigüedad máxima, en días | Una copia de seguridad más antigua que esto se elimina | `0` |

- 🛡️ **La última copia de seguridad siempre se conserva**, digan lo que digan los límites: una instancia nunca se queda sin ninguna.
- ⏰ La limpieza se ejecuta después de cada copia de seguridad y cuando LibreFolio se inicia, como mucho una vez por hora: un cambio guardado se aplica en una hora como máximo.
- 🏠 **Autoalojado:** ambos límites están desactivados hasta que los configures.
- 🔍 Solo se limpian las copias de seguridad de la lista. Los archivos sueltos más antiguos en `backups/`, una copia de seguridad en curso y una fallida nunca se tocan.
- ⌨️ La línea de comandos deja sus copias de seguridad en el mismo lugar y se aplican los mismos límites: consulta [Dónde se quedan las copias de seguridad](cli_backup.md#backup-kept).

### 📊 La barra de espacio {: #space-used }

**Archivos** muestra a los administradores una barra, **Espacio utilizado**, encima de sus pestañas, sea cual sea la pestaña abierta: cuánto espacio ocupa tu instancia. Se vuelve a leer cuando haces clic en **Actualizar** y siempre que cambie la lista de copias de seguridad conservadas, así que una copia de seguridad hecha o eliminada se muestra de inmediato. Su leyenda da el tamaño de cada parte:

| Parte | Qué cuenta |
| --- | --- |
| **Base de datos** | La base de datos y los archivos que guarda junto a ella |
| **Archivos subidos** | Los archivos subidos en la aplicación, como los de la página **Archivos** |
| **Informes del bróker** | Los extractos subidos para importar transacciones |
| **Copias de seguridad** | Todo en `backups/`: las [copias de seguridad conservadas en el servidor](#kept-backups), una copia de seguridad en curso y una fallida |
| **Otros archivos de LibreFolio** | El resto del directorio de datos: registros, la carpeta de trabajo de una restauración y similares |

La barra tiene tres aspectos, según si se ha establecido un límite y si se conoce el disco:

- 💽 **Sin límite** (el valor predeterminado en una instalación autoalojada): la barra es todo el disco de tus datos. Las partes de LibreFolio están coloreadas, **Otro en el disco** es gris, y el espacio **Libre** se deja vacío. La línea bajo la barra dice cuánto usa LibreFolio de un disco y de qué tamaño es este.
- 📏 **Con un límite**: la barra es el límite, y las partes de LibreFolio la llenan hasta donde llegan los datos. La línea bajo la barra dice *usado del límite*.
- 📁 **Sin límite y disco desconocido**: LibreFolio no puede consultar el disco, así que la barra es la propia carpeta de LibreFolio, dividida en sus partes, sin espacio libre.

**Establece el límite** en el panel cerrado **Avanzado** bajo la misma barra, en el campo **Espacio total de LibreFolio (MB)**: un número entero de megabytes, `0` para sin límite, luego **Guardar**; un aviso verde lo confirma. Es el espacio máximo que LibreFolio puede ocupar en total. También es la [configuración global](settings.md) *Límite de espacio*, que no se muestra en la pestaña Administración: este campo es el lugar para cambiarlo.

- 🚧 **Más allá del límite**, LibreFolio rechaza lo que añadiría datos: un archivo subido, un informe del bróker, una copia de seguridad iniciada a mano (tras probar la [limpieza automática](#backup-cleanup)) y una [restauración](#restore) cuyo resultado lo superaría. El mensaje dice que subas el espacio total a al menos un tamaño y, si al disco mismo le falta sitio, cuánto más necesita libre. Nunca se detienen: tus transacciones, precios y base de datos, las copias de un panel de alojamiento y de la línea de comandos (la limpieza las sigue) y una restauración ya confirmada. El límite no elimina nada por sí mismo.
- ⚠️ **Por encima del límite**, la barra advierte que se ha superado el límite y sugiere eliminar copias de seguridad o archivos, o subir el límite.
- 🔒 **Establecido en la configuración del servidor**: cuando `LIBREFOLIO_STORAGE_LIMIT_MB` está definido, su valor es el límite, el campo aparece en gris y una nota dice que lo establece quien aloja la instancia. Consulta [Variables de entorno](configuration.md). Un valor que LibreFolio no puede usar, uno que no sea un número entero, se ignora, y el campo funciona como se describe arriba.
- 🧹 **La limpieza y la barra trabajan juntas.** Las copias de seguridad suelen ser la parte que crece: la [limpieza automática](#backup-cleanup) las mantiene a raya, y cada copia de seguridad que elimines en **Configuración › Administración › Copia de seguridad** o en **Archivos › Copias de seguridad** acorta **Copias de seguridad** en la barra. Cuando estés cerca del límite, empieza por ahí.

### 🗄️ Mantén copias fuera del servidor {: #keep-copies }

`backups/` está en el directorio de datos, en el mismo disco que los datos: una copia de seguridad conservada allí no sobrevive a la pérdida de ese disco. Un archivo descargado desde Configuración ya está fuera del servidor. Desde la línea de comandos, escribe los archivos en otro disco, un NAS o fuera del sitio con `--output`, según una programación.

Una línea de `cron` para una instalación en host, cada noche a las 03:30 (`crontab -e`, como el usuario que ejecuta LibreFolio):

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /mnt/nas/librefolio/
```

Con Docker, añade `-T`, ya que cron no da terminal al comando. El archivo llega a su propia carpeta dentro de `LibreFolio-data/backups/`, donde la [limpieza automática](#backup-cleanup), una vez configurada, evita que el disco se llene: cópialo a otro lugar con tu herramienta habitual.

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create
```

Para archivos [seguros](#secure), añade `--password-file` con la ruta de un archivo que contenga la contraseña, ya que cron no tiene terminal donde preguntar; con Docker, el secreto del ejemplo anterior:

```text
30 3 * * * cd /path/to/librefolio && docker compose exec -T librefolio python dev.py backup create --password-file /run/secrets/backup_password
```

- 📁 La carpeta indicada a `--output` debe existir cuando se ejecuta el comando, así que monta el NAS primero: una ruta que no sea una carpeta existente se convierte en el nombre del propio archivo.
- 🔢 El comando imprime lo que hizo, y sale con `1` cuando el archivo no está donde pediste: conserva esa salida, o haz que cron te la envíe por correo.
- 🧭 cron ejecuta comandos con un `PATH` corto: si no encuentra `pipenv` o `docker`, escribe la ruta completa, que imprime `command -v pipenv`.
- 🗑️ LibreFolio no elimina ninguno de estos archivos: elimina tú los antiguos. Conserva varios, y el último hecho antes de cada actualización.
- 🔑 Guarda también una copia de `.env`, tan privada como los archivos de copia de seguridad: ningún archivo de copia de seguridad lo contiene. Guarda una de `secrets/` también, a menos que tus copias de seguridad sean seguras: una copia sin cifrar o [sellada](backup_sealed.md#sealed) omite la clave de la instancia; una segura contiene la clave que generó LibreFolio.
- 🔏 Para archivos nocturnos que el propio servidor no puede abrir, sin un archivo de contraseña en su disco, consulta [Cada noche con cron](backup_sealed.md#sealed-cron), en Copias de seguridad selladas.

### 🧰 Copias de seguridad con restic o Backrest {: #restic }

LibreFolio escribe el archivo; una herramienta de copia de seguridad puede luego enviarlo fuera del sitio y mantener un historial. [restic](https://restic.net/) envía una carpeta a un bucket de S3, Backblaze B2, un servidor por SFTP y otros lugares, cifrada, y olvida las copias antiguas según una regla que le des. [Backrest](https://github.com/garethgeorge/backrest) es una interfaz web para restic, con su propio planificador. LibreFolio no necesita ninguna: solo leen la carpeta donde se escriben sus archivos.

Una receta nocturna para una instalación en host, con las variables de restic en un archivo privado (`chmod 600`):

```bash
# /etc/librefolio-restic.env: where the copies go, and the file with restic's password
RESTIC_REPOSITORY=sftp:backup@nas.example:/srv/restic/librefolio
RESTIC_PASSWORD_FILE=/root/.restic-librefolio-password
```

```text
30 3 * * * cd /path/to/LibreFolio && pipenv run ./dev.py backup create --output /var/backups/librefolio/ && . /etc/librefolio-restic.env && restic backup /var/backups/librefolio/ && restic forget --keep-daily 7 --keep-weekly 4 --prune && find /var/backups/librefolio/ -name 'librefolio-backup-*' -mtime +2 -delete
```

La línea crea el archivo, envía la carpeta, conserva siete copias diarias y cuatro semanales en el repositorio, y elimina los archivos locales con más de dos días. Con Docker, crea el archivo con el comando de [Mantén copias fuera del servidor](#keep-copies) y da a restic la carpeta del host `LibreFolio-data/backups/`. Con Backrest, añade un plan sobre esa misma carpeta, con su programación y su retención, y deja `backup create` en cron.

- 🔐 **La contraseña de restic es una clave a todos tus datos.** restic cifra el repositorio con ella, pero cualquiera que la tenga lee todas las copias que contiene: guárdala tan privada como la contraseña de una [copia de seguridad segura](#secure), y una copia de ella en otro lugar. Si se pierde, el repositorio no se puede leer.
- 🔑 **Sin clave pública.** restic necesita su contraseña tanto para escribir como para leer, así que el servidor que envía las copias también puede leerlas. Si eso te importa, envía [copias de seguridad selladas](backup_sealed.md#sealed-cron) (`--sealed`): restic entonces almacena archivos que solo abre tu clave privada, y ni el servidor ni la contraseña de restic los leen. Las [copias de seguridad seguras](#secure) (`--password-file`) también funcionan, pero entonces su contraseña reside en un archivo en el mismo servidor.
- 📦 **Poco que deduplicar.** Cada archivo está comprimido, y uno seguro está cifrado: dos noches parecen diferentes a restic, que almacena cada archivo casi entero. Planifica el espacio del repositorio para las copias que conserves.
- 🧪 **Prueba una restauración antes de necesitarla.** `restic restore latest --target /tmp/librefolio-check`, luego comprueba el archivo con [`backup restore --dry-run`](#check).

---

## 🔐 Copias de seguridad seguras {: #secure }

Una copia de seguridad segura es el archivo de una copia de seguridad sin cifrar, cifrado con una contraseña que elijas, en un archivo propio de LibreFolio: `.lfbk`. Créala desde [Configuración › Administración › Copia de seguridad](#settings-backup) o con `backup create --encrypt` en la [línea de comandos](#command-line); toda comprobación y restauración de esta página la acepta, una vez dada su contraseña.

- 🛡️ **Qué protege: el archivo en reposo.** Un disco perdido, un portátil robado, una copia en una unidad en la nube o un NAS: sin la contraseña, no se puede leer nada de él, ni los datos ni los nombres de los archivos. Un archivo cambiado o truncado se detecta al abrirlo, y se rechaza.
- 👁️ **Qué no protege.** Quien conozca la contraseña lee todo: los datos de todos los usuarios, y las claves de los proveedores de datos. Dásela solo a quien pueda restaurar la copia de seguridad, y nunca la guardes con el archivo.
- 🗝️ **Qué contiene.** Además de los datos, la clave de la instancia, cuando LibreFolio la generó (`secrets/instance.key`): las claves guardadas de los proveedores de datos viajan con la copia de seguridad, y su restauración las vuelve a cifrar con la clave de la instalación que la recibe, que conserva la suya. Una clave que establezcas tú mismo, con `LIBREFOLIO_INSTANCE_KEY` o `LIBREFOLIO_INSTANCE_KEY_FILE`, nunca sale: quien la estableció la conserva.
- 🆘 **Una contraseña perdida no se puede recuperar.** LibreFolio no guarda ninguna copia de ella, y nada más abre el archivo.
- ⏳ **Lento de adivinar.** La clave del archivo proviene de la contraseña mediante scrypt, que consume 32 MiB de memoria y alrededor de una décima de segundo por intento: nada para una copia de seguridad, lo bastante ligero para un servidor pequeño, pero lento para quien pruebe contraseñas una tras otra. De ahí las reglas: al menos 12 caracteres, con una letra mayúscula y una minúscula, un dígito y un símbolo.
- 💽 **En el servidor, mientras se crea,** el archivo sin cifrar se escribe primero, en la carpeta de trabajo de la copia de seguridad dentro de `backups/`, que solo el usuario del servidor puede abrir; se elimina en cuanto se escribe el `.lfbk`, y cuando la copia de seguridad falla. Una comprobación descifra la copia de seguridad de la misma manera, en una carpeta privada del directorio de datos, y elimina el archivo descifrado una vez que lo ha usado. Una ejecución interrumpida abruptamente, por un corte de energía o `kill -9`, no puede limpiar: el siguiente inicio de LibreFolio elimina lo que dejó sin cifrar, y una copia de seguridad truncada de esa manera debe hacerse de nuevo. La carpeta de un `backup inspect` interrumpido así se elimina cuando tiene una hora de antigüedad.

El diseño, para desarrolladores: [Copias de seguridad seguras (`.lfbk`)](../developer/architecture/security.md#secure-backups).

---

## 🔎 Comprobar una copia de seguridad {: #check }

Dos comandos comprueban un archivo y no cambian nada. Con Docker, indica la ruta dentro del contenedor: un archivo en `LibreFolio-data/backups/` está en `/app/backend/data/prod-docker/backups/` allí. Una copia de seguridad que LibreFolio [conserva](#kept-backups) está en su propia carpeta, como `/app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/`.

```bash
# Is the archive whole, and what does it hold?
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# Can this installation restore it? A restore tried on a copy
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip --dry-run

# A secure backup: the same commands ask its password first
docker compose exec librefolio python dev.py backup inspect /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.lfbk
```

En una instalación en host, ejecuta `pipenv run ./dev.py backup …` con la ruta del archivo en el host.

| | `backup inspect` | `backup restore --dry-run` |
| --- | --- | --- |
| Qué responde | Si el archivo está íntegro: el tamaño y la suma de comprobación SHA-256 de cada entrada, comparados con el manifiesto | Si esta instalación puede restaurarlo: el archivo descomprimido en una copia, actualizado y comprobado |
| Qué muestra | Quién hizo el archivo y cuándo, la revisión de su base de datos, sus filas y tablas, sus archivos, y si se incluye la clave de la instancia | Lo mismo, más las migraciones que aplicaría una restauración, los totales de control del libro mayor de la copia comparados con los que registró el archivo, las claves guardadas de los proveedores de datos vueltas a cifrar con la clave de esta instalación o pendientes de volver a introducir, y los administradores con los que iniciarías sesión |
| Qué necesita | Cualquier LibreFolio, con su servidor en marcha o detenido: no necesita ningún directorio de datos, salvo para una copia de seguridad segura, que descifra allí | La instalación que recibiría el archivo, cuyo servidor puede seguir en marcha, y espacio libre en su directorio de datos: el archivo descomprimido, más el doble de su base de datos, más 64 MB |
| Con qué termina | `✅ Every entry matches the manifest` | `✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.` |

- 🔐 **Una copia de seguridad segura** (`.lfbk`): ambos comandos piden su contraseña primero, escrita en el terminal o dada con `--password-file FILE` o `--password-stdin`, como para `backup create`. La descifran en una carpeta privada del directorio de datos, que solo el usuario del servidor puede abrir, y la eliminan al final: el disco allí necesita espacio también para el archivo descifrado, aproximadamente el tamaño del `.lfbk`. Lo que un comando interrumpido abruptamente, por un corte de energía o `kill -9`, deja sin cifrar se elimina en el siguiente inicio de LibreFolio: el archivo descifrado de `--dry-run` de inmediato, la carpeta de `inspect` cuando tiene una hora de antigüedad, que el siguiente `inspect` también elimina. Su informe añade `Secure backup: decrypted with its password`. Una contraseña incorrecta los detiene con `❌ The password does not open this backup (wrong_password)`. Un `.zip` ignora las dos opciones de contraseña.
- 🗝️ `--dry-run` también dice qué ocurre con las claves guardadas de los proveedores de datos, para cualquier archivo: `Saved provider keys: 2 re-encrypted with this instance's key` cuando la copia de seguridad contiene la clave que las cifró, `⚠️ 1 saved provider key cannot be read with this instance's key: enter it again after the restore` para las que no puede leer ([Lo que sigue](#what-follows)).
- 🔁 Ejecuta `inspect` de vez en cuando sobre las copias que conserves, y `--dry-run` antes de un traslado, en la instalación que recibirá el archivo.
- 🖱️ **Restaurar un archivo**, en Configuración › Administración › Copia de seguridad, ejecuta la misma comprobación que `--dry-run` sobre un archivo de tu ordenador: lee su informe, luego **Descartar este archivo**, y nada cambia ([Restaurar desde Configuración › Administración › Copia de seguridad](#restore-settings)).
- ❌ Un rechazo termina con un código entre paréntesis: consulta [Cuando algo va mal](backup_moving.md#troubleshooting). Las listas completas están en «Comprobar un archivo» y «Probar una restauración sobre una copia», en [Herramientas de administración de CLI](cli_tools.md).

---

## ♻️ Restaurar en esta instalación {: #restore }

Una restauración reemplaza los datos de la instalación con los del archivo: la base de datos y los archivos, para todos los usuarios. Dos caminos llevan a ella: **Configuración › Administración › Copia de seguridad**, en la aplicación, para administradores, y `backup restore`, en la línea de comandos del servidor. Ambos comprueban el archivo sobre una copia primero y no cambian nada hasta que confirmes: el siguiente inicio de LibreFolio entonces la aplica. Desde Configuración › Administración › Copia de seguridad, LibreFolio se detiene en cuanto confirmas, para ese inicio; en la línea de comandos, lo reinicias cuando te convenga. En una instancia que alguien aloja para ti, la línea de comandos está en su servidor: como uno de sus administradores, usa Configuración › Administración › Copia de seguridad, o pídeselo.

### 🖱️ Restaurar desde Configuración › Administración › Copia de seguridad {: #restore-settings }

1. **Elige el archivo.** En **Configuración › Administración › Copia de seguridad**, bajo **Hacer copia de seguridad de la instancia**, la tarjeta **Restaurar un archivo** te recuerda que una restauración reemplaza los datos de todos los usuarios: si puede que quieras recuperar los datos actuales, [haz una copia de seguridad](#settings-backup) primero. Haz clic en **Elegir un archivo…** y selecciona un archivo de copia de seguridad hecho por LibreFolio aquí o en otra instalación: un `.zip`, o un `.lfbk` seguro. Un `.zip` se envía al servidor de inmediato, con una barra de progreso: **Detener el envío** lo detiene, y no se conserva nada.
2. **Escribe su contraseña**, para una copia de seguridad segura. La tarjeta la pide antes de enviar nada: *Una copia de seguridad segura: escribe la contraseña con la que se creó.* Escríbela en **Contraseña de la copia de seguridad** y haz clic en **Comprobar la copia de seguridad**: el archivo se envía, con la misma barra de progreso, y la contraseña va con la solicitud que inicia la comprobación, que la prueba de inmediato. Una contraseña incorrecta devuelve el formulario, con *Contraseña incorrecta, o el archivo cambió: escribe la contraseña de nuevo.* El archivo permanece en el servidor, y el siguiente intento no lo envía de nuevo. **Cancelar** olvida el archivo.
3. **Deja que se compruebe.** El servidor comprueba el archivo sobre una copia, como hace `backup restore --dry-run` ([Comprobar una copia de seguridad](#check)): *Descifrando la copia de seguridad*, solo para una copia de seguridad segura, *Comprobando el archivo*, *Descomprimiéndolo en una copia*, *Actualizando la base de datos de la copia*, *Verificando la copia*. Nada cambia hasta que confirmes. **Detener la comprobación** la descarta: una comprobación aún en ejecución se descarta en cuanto termina.
4. **Lee el informe.** Se abre en una ventana, **Qué haría esta restauración**; una vez cerrada, **Leer el informe** la abre de nuevo. Da:
    - quién hizo el archivo, con qué versión de LibreFolio, y cuándo;
    - su base de datos: en la versión de este LibreFolio, o llevada a ella en la copia, con las migraciones enumeradas, y las correcciones aplicadas a la copia;
    - los archivos y su tamaño, el tamaño de la base de datos, y las tablas cuyas filas cambió la actualización;
    - si la copia de seguridad contiene la clave de la instancia de la que proviene: en cualquier caso, este LibreFolio conserva la suya;
    - las claves guardadas de los proveedores de datos: cuántas se vuelven a cifrar con la clave de este LibreFolio, como *2 claves guardadas de proveedores de datos se vuelven a cifrar con la clave de esta instancia.*, y cuántas no puede leer, para volver a introducir tras la restauración, como *1 clave guardada de un proveedor de datos no se puede leer con la clave de esta instancia: vuelve a introducirla tras la restauración.* ([Lo que sigue](#what-follows));
    - los totales del libro mayor: los mismos que cuando se hizo la copia de seguridad, diferentes en las líneas enumeradas ([cómo leerlos](backup_moving.md#check-refused)), no registrados, registrados por otra versión del método, o ilegibles;
    - los administradores de la copia de seguridad, con *Después de la restauración inicias sesión con uno de ellos, con la contraseña de entonces; toda sesión abierta ahora termina.*
    - *Las invitaciones y enlaces enviados antes de la restauración habrán caducado: envíalos de nuevo si es necesario.*
    - las advertencias, que permiten continuar la restauración, y el bloqueo, que la prohíbe: una copia de seguridad sin un administrador activo;
    - hasta cuándo se conserva la copia comprobada: 24 horas después de la comprobación.

    **Descartar este archivo** descarta la comprobación y su copia: no se restaura nada.

5. **Escribe la palabra.** La ventana muestra una palabra elegida al azar, una palabra real de 6 a 10 letras en el idioma de la interfaz. Escríbela a mano en el campo de debajo: el campo rechaza el texto pegado y arrastrado. La palabra protege contra un clic apresurado, no contra un administrador: la API y la línea de comandos prescinden de ella. Para un archivo que no se puede restaurar, el campo y el botón permanecen deshabilitados.
6. **Restaurar y reiniciar.** Una vez escrita la palabra, **Restaurar y reiniciar** confirma la restauración y detiene LibreFolio de inmediato, para todos. Una ventana cubre la página, **LibreFolio se está reiniciando**: *Su inicio aplica la restauración. Esta página espera a que vuelva.* LibreFolio no se inicia de nuevo por sí solo: lo hace quien lo supervise ([Quién inicia LibreFolio de nuevo](#supervisors)), y ese inicio aplica la restauración ([Qué hace el siguiente inicio](#next-start)).

Una vez que LibreFolio responde de nuevo, la página muestra cómo fue:

- ✅ **Funcionó**: la página va a la página de inicio de sesión, sin mensaje, ya que toda sesión ha terminado. Inicia sesión con un administrador de la copia de seguridad, con la contraseña que la cuenta tenía cuando se hizo la copia de seguridad: la primera página habitual muestra los datos restaurados. Una restauración que funcionó no deja ninguna línea en la tarjeta.
- ↩️ **No se completó**: la ventana dice **La restauración no se completó**, con el motivo, y **Volver a Copia de seguridad** regresa a la tarjeta, tras la página de inicio de sesión si el reinicio terminó tu sesión, o a la página de bloqueo en una instancia bloqueada mientras tanto. *Los datos están como antes: …* significa que la restauración se revirtió: la tarjeta entonces dice cuándo, y por qué. *LibreFolio se reinició, pero la restauración no se aplicó.* significa que un inicio la dejó esperando, por el motivo que sigue. Qué hacer: [Qué dice Configuración › Administración › Copia de seguridad](backup_moving.md#restore-settings-problems).
- ⏳ **Tarda mucho**: tras un minuto sin el servidor, la ventana añade *LibreFolio aún no ha vuelto. Si nada lo inicia de nuevo por sí solo, inícialo tú mismo: la restauración se aplica en ese inicio.* Si LibreFolio no se detiene en absoluto, tras un minuto la ventana dice *LibreFolio no se ha detenido. Si no se reinicia por sí solo, reinícialo tú mismo: la restauración se aplica en ese inicio.*, y ofrece **Volver a Copia de seguridad**: consulta [Qué dice Configuración › Administración › Copia de seguridad](backup_moving.md#restore-settings-problems).

La página lee el resultado con un ticket de un solo uso que recibió su solicitud de reinicio, válido una hora y conservado solo en la memoria de la pestaña: no necesita sesión, así que la ventana informa del resultado sea cual sea tu configuración. Sin ese ticket, tras una recarga de la página, más de una hora de espera, o LibreFolio reiniciado desde la línea de comandos en lugar de desde esta página, la página se guía por su sesión: sin `JWT_SECRET`, que cierra la sesión de todos en cada inicio ([Mantener a los usuarios con sesión iniciada tras un reinicio](index.md#session-persistence)), entonces va a la página de inicio de sesión sea cual sea el resultado, y **Configuración › Administración › Copia de seguridad** dice, una vez que hayas iniciado sesión, si la restauración se completó.

Una restauración confirmada y aún no aplicada se muestra en la tarjeta en lugar de **Elegir un archivo…**: una confirmada desde la línea de comandos, o aquí cuando LibreFolio no se detuvo o un inicio la dejó esperando. La tarjeta dice **Una restauración espera el siguiente inicio de LibreFolio**, con la copia de seguridad, quién la confirmó (`cli` desde la línea de comandos) y cuándo, por qué un inicio la dejó esperando si lo hizo, y *Reiniciar detiene LibreFolio para todos; su siguiente inicio aplica la restauración y termina toda sesión.*

- **Reiniciar ahora y restaurar** detiene LibreFolio, como hace **Restaurar y reiniciar**, y la página lo espera de la misma manera.
- **Cancelar la restauración** la descarta con su copia comprobada, como hace `backup pending --cancel`: los datos quedan como están.

Mientras un inicio aplica la restauración, la tarjeta dice *Un inicio de LibreFolio está aplicando la restauración.*

Conviene saber:

- 👑 Solo los administradores tienen la pestaña, y se ejecuta una restauración a la vez: se comprueba un archivo a la vez, dondequiera que haya comenzado la comprobación, aquí, en otra pestaña o en la línea de comandos (*Se está comprobando otro archivo: inténtalo de nuevo cuando termine.*), y una restauración en espera ocupa el lugar de **Elegir un archivo…**.
- 📏 Cuando la instalación limita el tamaño de los archivos, la tarjeta lo dice, como *Archivos de hasta 500 MB.*, y rechaza un archivo mayor antes de enviar nada. El límite es `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`, en megabytes de 1024 × 1024 bytes: ninguno por defecto en tu propia instalación ([El límite de subida de una restauración](#restore-upload-limit)).
- 💽 El disco del directorio de datos necesita espacio para el archivo y, mientras se comprueba, para su copia; en el caso de una copia de seguridad segura, también para su archivo descifrado: [Comprobar una copia de seguridad](#check) dice cuánto.
- 🔑 La contraseña de una copia de seguridad segura va al servidor solo con la solicitud que inicia la comprobación, que la prueba de inmediato: nunca se almacena, se escribe en el registro ni se devuelve. El campo se vacía en cuanto la envías.
- 🔄 Una recarga de la página, en la misma pestaña, mantiene el seguimiento de la comprobación y de su informe. La copia comprobada se conserva 24 horas: después de eso, la confirmación responde *La comprobación es demasiado antigua: comprueba el archivo de nuevo.*
- 🚪 La restauración termina toda sesión, todos inician sesión de nuevo con una cuenta de la copia de seguridad, y los enlaces enviados antes dejan de funcionar: consulta [Qué hace el siguiente inicio](#next-start).
- ❌ Si se rechaza una subida, una comprobación o una confirmación, o si un servidor no responde, el motivo se muestra en la tarjeta. **Intentar de nuevo** vuelve a leer el estado de la restauración; para enviar un archivo de nuevo, elígelo otra vez con **Elegir un archivo…**. La comprobación rechaza los mismos archivos que la línea de comandos: consulta [La comprobación rechaza el archivo](backup_moving.md#check-refused).
- 🖥️ Sin nada que inicie LibreFolio de nuevo, como una instalación en host iniciada a mano, [inicia el servidor](cli_tools.md#start-the-server) tú mismo una vez que se haya detenido: la página lo espera.

### 📤 El límite de subida de una restauración {: #restore-upload-limit }

Para comprobar un archivo para una restauración, un administrador lo sube a la instancia desde Configuración › Administración › Copia de seguridad ([Restaurar desde Configuración › Administración › Copia de seguridad](backup_restore.md#restore-settings)), mediante `PUT /api/v1/backup/restore/upload`; la instancia entonces lo comprueba sobre una copia, como hace `backup restore --dry-run` en la [línea de comandos](cli_tools.md). `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` limita el tamaño de los archivos que un administrador puede subir.

| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | Archivo más grande aceptado |
| --- | --- |
| Sin establecer, o vacío | Sin límite |
| `0` | Sin límite |
| Un número entero, como `2048` | Esos megabytes, de 1024 × 1024 bytes cada uno |

```bash
LIBREFOLIO_BACKUP_MAX_UPLOAD_MB=2048
```

- Establécelo en el entorno del contenedor o en `.env`, luego reinicia LibreFolio.
- Para un archivo por encima del límite, el servidor responde `413`, con el código `backup_too_large` y el límite en `limit_mb`: antes de que se escriba nada cuando la solicitud anuncia su tamaño, de lo contrario en cuanto la subida supera el límite. No se conserva nada de él.
- Un proxy delante de LibreFolio debe dejar pasar al menos esa cantidad: Nginx con `client_max_body_size`, cuyo valor predeterminado es solo 1 MB (`client_max_body_size 2048m;` coincide con el ejemplo anterior), y tu CDN, si limita el tamaño de una solicitud. Un `413` sin el código `backup_too_large` proviene del proxy, no de LibreFolio.
- Un valor distinto de un número entero, como `500MB` o `-1`, no detiene el servidor: el registro de inicio ya tiene un error, `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: …` (`check` es `backup.upload_limit`), entonces cada subida responde `503` con el código `backup_upload_unavailable`, y el registro tiene un error que nombra la variable: `The upload limit of a restore cannot be read`.
- El disco del directorio de datos necesita espacio para el archivo y, mientras se comprueba, también para su copia descomprimida (cuánto: «Probar una restauración sobre una copia» en [Herramientas de administración de CLI](cli_tools.md)): si falta espacio, la subida responde `507` con el código `backup_no_space`, también cuando el disco se declara lleno solo al final del archivo, como puede hacer un sistema de archivos de red o una cuota. La comprobación responde con su propio código, `no_space`: un `507` cuando ni siquiera puede empezar, un rechazo del archivo una vez que se ejecuta. Una subida que no se puede escribir por otro motivo responde `500` con el código `backup_upload_failed`, y el registro tiene la causa.
- Un administrador lee el límite vigente en `upload_limit_mb` de `GET /api/v1/backup/restore/status`: `0` para sin límite, `null` cuando el valor no se puede leer. Configuración › Administración › Copia de seguridad lo muestra en su tarjeta de restauración, como *Archivos de hasta 500 MB.*, y rechaza un archivo mayor antes de enviarlo.

El límite de subida limita el archivo tal como se envía, comprimido: un zip puede descomprimirse a mucho más que su propio tamaño, y la comprobación lo descomprime en el disco del directorio de datos. `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` limita a qué se descomprime un archivo, a partir de los tamaños que declara su manifiesto, antes de que la comprobación descomprima nada.

| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | Tamaño mayor al que se descomprime un archivo |
| --- | --- |
| Sin establecer, o vacío | Sin límite |
| `0` | Sin límite |
| Un número entero, como `16384` | Esos megabytes, de 1024 × 1024 bytes cada uno |

- Un archivo por encima del límite se rechaza antes de que se descomprima nada: la comprobación falla con el código `unpacked_too_large`, y no queda nada de su copia. Un archivo seguro se descifra primero, lo que ocupa aproximadamente su propio tamaño, luego se mide de la misma manera.
- Un valor que establezcas siempre prevalece, `0` incluido. `backup restore` en la línea de comandos sigue el mismo límite; quien ejecuta el servidor lo levanta para un comando con `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` delante («Probar una restauración sobre una copia» en [Herramientas de administración de CLI](cli_tools.md)).
- Un valor distinto de un número entero no detiene el servidor: el registro de inicio ya tiene un error, `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: …` (`check` es `backup.restore_limit`), entonces cada comprobación, `POST /api/v1/backup/restore/stage`, responde `503` con el código `backup_restore_unavailable`, el archivo se conserva, y el registro tiene un error.

### ⌨️ Restaurar desde la línea de comandos {: #restore-command }

Ejecútalo donde se ejecuta el servidor, en el contenedor con Docker:

```bash
# 1. Check the archive on a copy, read the report, then type "restore" to confirm
docker compose exec librefolio python dev.py backup restore /app/backend/data/prod-docker/backups/librefolio-backup-20261015-121500-cli-1a2b3c4d/librefolio-backup-20261015-121500.zip

# 2. Restart LibreFolio: its next start applies the restore
docker compose restart librefolio

# 3. See how it went
docker compose exec librefolio python dev.py backup pending
```

- 🧪 El paso 1 ejecuta la misma comprobación que `--dry-run` y muestra el mismo informe, luego te pide escribir `restore`. Nada cambia todavía: LibreFolio sigue ejecutándose con sus datos, y la restauración espera al siguiente inicio.
- 🖥️ En una instalación en host, ejecuta `pipenv run ./dev.py backup restore <archive>`, luego detén todo el servidor y [inícialo](cli_tools.md#start-the-server) de nuevo: nunca reinicies un solo worker.
- ⏳ Una vez que LibreFolio vuelve a estar en marcha, `backup pending` dice `✅ The last restore was applied on …`. Antes del reinicio, `backup pending --cancel` descarta la restauración en espera, con su copia comprobada.
- 🤖 En un script, `--yes` confirma sin preguntar.
- 🔐 Para una copia de seguridad segura (`.lfbk`), `backup restore` pide su contraseña antes de la comprobación, o la lee con `--password-file` o `--password-stdin`, como hace `inspect` ([Comprobar una copia de seguridad](#check)): en un script, da una de ellas además de `--yes`.
- 📖 Más: «Restaurar un archivo» y «Seguir o cancelar una restauración» en [Herramientas de administración de CLI](cli_tools.md).

### 🔄 Qué hace el siguiente inicio {: #next-start }

- 🔀 **El intercambio.** La base de datos y las tres carpetas de archivos se intercambian con la copia comprobada: un renombrado por carpeta, instantáneo sea cual sea su tamaño. `secrets/`, `logs/`, `scheduler_state.json` y `backups/` permanecen como están, así que la instalación conserva su propia clave de instancia. La clave que contiene una copia de seguridad segura nunca se pone en su lugar: la comprobación ya volvió a cifrar las claves guardadas de los proveedores de datos en la copia, con la clave de esta instalación.
- 🚪 **Toda sesión termina.** Todos inician sesión de nuevo, en cada dispositivo, con una cuenta de la copia de seguridad y la contraseña que tenía entonces.
- 🔗 **Los enlaces de un solo uso se revocan.** Ningún enlace de invitación, restablecimiento de contraseña o verificación de correo electrónico enviado antes funciona ya, ni siquiera los que contenía la copia de seguridad: envía nuevos. Una cuenta que aún espera la verificación de su correo electrónico deja de esperar: cuando su propietario pide a la página de inicio de sesión un nuevo enlace, la página responde que la cuenta está deshabilitada. Un administrador la reactiva con **Reactivar** ([Qué hace cada acción](users.md#actions)), o la elimina ([Eliminar una cuenta](users.md#delete)) para que su propietario se registre de nuevo.
- ✅ **El primer inicio debe completarse.** Solo entonces se conserva la restauración y se eliminan los datos anteriores. Si ese inicio falla, por una migración que falla o un archivo dañado, el siguiente inicio restaura los datos anteriores por sí solo, y `backup pending`, como la tarjeta en Configuración › Administración › Copia de seguridad, dice que la restauración se revirtió, con el motivo.

### 🔌 Quién inicia LibreFolio de nuevo {: #supervisors }

Tú mismo inicias la restauración: con el reinicio de la línea de comandos, o con **Restaurar y reiniciar** en Configuración › Administración › Copia de seguridad, que detiene LibreFolio. Nada en LibreFolio inicia el servidor de nuevo: lo hace quien lo supervise, después de esa parada, y después de un primer inicio que falla, para que el siguiente inicio recupere los datos.

| Supervisor | Inicia LibreFolio de nuevo por sí solo |
| --- | --- |
| Docker Compose | Con `restart: unless-stopped`, en ambos archivos compose que incluye LibreFolio |
| systemd | Con `Restart=always` |
| Ninguno | No: inicia LibreFolio tú mismo, y la restauración, o la vuelta atrás, ocurre en ese inicio |

**Restaurar y reiniciar** detiene LibreFolio limpiamente: una política que solo lo inicia de nuevo tras un fallo, como `on-failure`, no lo inicia después de esa parada.

---

## 🔗 Relacionado

- 📄 **[Copias de seguridad: Copias selladas](backup_sealed.md)** — Copias de seguridad selladas: una clave en lugar de una contraseña
- 📄 **[Copias de seguridad: Traslado y solución de problemas](backup_moving.md)** — Lleva tu LibreFolio a casa, cuando algo va mal
- 🛠️ **[Herramientas de administración de CLI](cli_tools.md)** — «Hacer copia de seguridad de la instancia»: cada opción y mensaje de `backup create`, `inspect`, `restore`, `decrypt` y `pending`, y «Hacer copia de seguridad con Docker»
- 📂 **[Estructura del sistema de archivos](filesystem.md)** — El directorio de datos, `secrets/`, y una copia hecha a mano
- 🐳 **[Instalación con Docker](../user/installation.md)** — Instalar LibreFolio, y actualizarlo
- 👥 **[Usuarios e invitaciones](users.md)** — Reactivar o eliminar cuentas, y enviar nuevos enlaces
- 📧 **[Correo electrónico](email.md)** — Las variables de correo electrónico, que ningún archivo contiene
- 📝 **[Variables de entorno](configuration.md)** — «La clave de la instancia», y cada opción de `.env`
- 🧑‍💻 Para desarrolladores: **[Restaurar una copia de seguridad](../developer/architecture/security.md#backup-restore)** — El intercambio, el diario, la reversión y el reinicio
- 🧑‍💻 Para desarrolladores: **[Copias de seguridad seguras (`.lfbk`)](../developer/architecture/security.md#secure-backups)** — El sobre, la contraseña y la clave de instancia que contiene una copia de seguridad segura
- 🧑‍💻 Para desarrolladores: **[Copias de seguridad selladas (`.tar`)](../developer/architecture/security.md#sealed-backups)** — Los tres miembros, age mediante `pyrage`, y el lector estricto
