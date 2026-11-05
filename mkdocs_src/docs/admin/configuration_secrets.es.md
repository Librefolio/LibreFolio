# 🔐 Configuración: secretos y configuración de plugins

Esta página cubre lo que debe permanecer privado en una instalación de LibreFolio: las opciones que son **secretos**
(claves, contraseñas y tokens), que también pueden leerse desde archivos como los secretos de Docker, la
**clave de instancia** que protege lo que LibreFolio almacena, y la **configuración de los plugins**, incluidas las claves API.

¿Es la primera vez que usas el archivo `.env`? Cómo crearlo, las opciones principales y qué valor prevalece se explican en
[Configuración](configuration.md); esta página profundiza en los secretos.

---

## 🔐 Secretos {: #secrets }

Estas opciones son secretos: mantenlas tan privadas como la base de datos. Cada una puede escribirse en `.env` o
leerse desde un archivo.

| Secreto | Desde un archivo | Qué es |
| --- | --- | --- |
| `JWT_SECRET` | `JWT_SECRET_FILE` | La clave que firma las sesiones de inicio de sesión, en las [opciones principales](configuration.md). |
| `LIBREFOLIO_INSTANCE_KEY` | `LIBREFOLIO_INSTANCE_KEY_FILE` | La [clave de instancia](#instance-key). Si no se establece, LibreFolio crea una en el directorio de datos. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | La clave de un servicio de búsqueda de pago, para el motor `apikey` de la [búsqueda web](configuration_accounts.md#optional-web-search-for-new-assets). A diferencia de las dos primeras, un archivo que no pueda proporcionarla no detiene el servidor: solo desactiva la búsqueda web. |
| `LIBREFOLIO_SMTP_PASSWORD` | `LIBREFOLIO_SMTP_PASSWORD_FILE` | La contraseña del servidor SMTP que envía los correos electrónicos de LibreFolio: consulta [Correo electrónico](email.md). Al igual que la clave de búsqueda web, un archivo que no pueda proporcionarla no detiene el servidor: solo desactiva el correo electrónico. |

Un plugin puede tener sus propios secretos, como la clave API de una fuente de datos de pago: consulta
[Configuración de plugins](#plugin-settings).

### 📄 Secretos en archivos {: #secret-files }

Añade `_FILE` al nombre de un secreto y proporciona la ruta de un archivo que lo contenga. Así entregan sus secretos Docker y
Kubernetes, por ejemplo `/run/secrets/jwt_secret`: el secreto queda fuera de `.env`
y fuera del entorno del contenedor.

- El secreto es el texto del archivo, sin los saltos de línea al final y sin la marca de orden de bytes que algunos editores de Windows colocan al principio. Cualquier otro espacio cuenta, también al principio y al final.
- Una ruta relativa parte de la carpeta del proyecto.
- Si un secreto o su variable `_FILE` están vacíos o contienen solo espacios, se consideran no establecidos: nunca se usa un espacio suelto como clave.
- Establece una de las dos. Cuando ambas están establecidas, prevalece la variable en sí, se ignora el archivo y el registro de inicio contiene una [advertencia](configuration_security.md#startup-checks).
- Para `JWT_SECRET_FILE`, `LIBREFOLIO_INSTANCE_KEY_FILE` y `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE`, un archivo que falte, que no se pueda leer, que esté vacío o en blanco (solo espacios y saltos de línea), que no sea texto UTF-8 o que supere los 64 KiB detiene el servidor al inicio. El error indica el nombre de la variable y la ruta, nunca el secreto.
- `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` solo se lee cuando una búsqueda usa el motor `apikey`. Un archivo que no pueda proporcionar la clave no detiene el servidor: la búsqueda continúa sin la búsqueda web, con una advertencia en el registro (`web_link_finder: …; disabling`), y la búsqueda propia de los proveedores sigue funcionando.
- `LIBREFOLIO_SMTP_PASSWORD_FILE` solo se lee cuando `LIBREFOLIO_SMTP_HOST` está establecido. Al igual que el archivo de la clave de búsqueda web, un archivo que no pueda proporcionar la contraseña no detiene el servidor: el correo electrónico permanece desactivado, con un error en el registro (`Email configuration cannot be used: email stays off`).
- LibreFolio lee estas variables de su entorno: `./dev.py` y Docker Compose (`env_file: .env`) colocan ahí los valores de `.env`, de modo que `.env` funciona con ambos.

??? example "🐳 Un secreto de Docker con Docker Compose"

    1. Guarda una clave nueva en un archivo junto a `docker-compose.yml`:

        ```bash
        python3 -c "import secrets; print(secrets.token_urlsafe(64))" > jwt_secret.txt
        ```

    2. Añade las líneas marcadas a `docker-compose.yml` y deja el resto del servicio tal como está:

        ```yaml
        services:
          librefolio:
            environment:
              - LIBREFOLIO_DATA_DIR=/app/backend/data/prod-docker
              - HOST=0.0.0.0
              - JWT_SECRET_FILE=/run/secrets/jwt_secret  # added
            secrets:                                     # added
              - jwt_secret                               # added
        secrets:                                         # added
          jwt_secret:                                    # added
            file: ./jwt_secret.txt                       # added
        ```

    3. Si `.env` asigna un valor a `JWT_SECRET`, elimina esa línea: prevalecería sobre el archivo. Una línea
       `JWT_SECRET=` vacía no causa ningún problema. Luego ejecuta `docker compose up -d`.

    Compose monta el archivo en el contenedor tal como está en el host, con su propietario y sus permisos.
    LibreFolio se ejecuta allí como el usuario de la imagen, `1000:1000` para la oficial (consulta
    [Docker avanzado](docker_advanced.md)), y ese usuario debe poder leer el archivo. Con la
    imagen oficial, por ejemplo: `sudo chown 1000:1000 jwt_secret.txt`, luego
    `sudo chmod 600 jwt_secret.txt`. De lo contrario, el servidor se detiene al inicio y el error indica que el
    archivo `cannot be read`.

    `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` y
    `LIBREFOLIO_SMTP_PASSWORD_FILE` se montan de la misma manera; lo que hace cada una cuando su archivo
    no puede proporcionar el secreto se explica en [Secretos en archivos](#secret-files).

### 🗝️ La clave de instancia {: #instance-key }

La clave de instancia es un secreto por instalación: LibreFolio deriva de ella sus claves de cifrado.
No hay nada que configurar. LibreFolio usa la primera clave que encuentra:

1. `LIBREFOLIO_INSTANCE_KEY`, la clave en sí;
2. `LIBREFOLIO_INSTANCE_KEY_FILE`, un archivo que la contiene, como un secreto de Docker;
3. `secrets/instance.key` en el directorio de datos, que LibreFolio crea la primera vez que necesita la
   clave: 43 caracteres aleatorios, en una carpeta y un archivo que solo el usuario que ejecuta LibreFolio puede abrir
   (`0700` y `0600`).

Una clave propia debe ser aleatoria y tener al menos 32 caracteres, como la salida de
`python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. Nunca uses una frase de contraseña: las claves
que LibreFolio deriva de ella solo son tan seguras como ella.

En un despliegue en la nube, la clave puede provenir del entorno o de un secreto de Docker en lugar del
directorio de datos. Asigna a cada instancia su propia clave: nunca compartas una clave entre varias instancias.

!!! warning "🔑 Nunca cambies ni elimines la clave una vez en uso"

    Solo la misma clave puede volver a leer lo que se cifró con ella.

    - Haz una copia de seguridad de `secrets/` junto con el resto del directorio de datos y mantén las copias tan privadas como la
      base de datos: consulta [Copia de seguridad](filesystem.md#backup).
    - Una vez que existe la clave, LibreFolio no puede distinguir una `instance.key` perdida de un primer uso: crea una
      clave nueva y lo que cifró la antigua ya no se puede leer. Cuando restaures los datos, vuelve a colocar
      `secrets/` junto con ellos antes de iniciar LibreFolio de nuevo. Nunca inicies LibreFolio con datos restaurados
      sin su `secrets/`. Si LibreFolio ya ha creado una clave nueva, detenlo, coloca tu
      copia de `instance.key` en lugar de la nueva y vuelve a iniciarlo, antes de que alguien introduzca de nuevo un
      [secreto de plugin](#plugin-secrets): un secreto introducido con la clave nueva quedaría
      ilegible una vez que vuelva la clave antigua.
    - Si `instance.key` está presente pero dañada o inaccesible, LibreFolio registra un error y nunca
      la reemplaza: consulta qué hacer en [Comprobaciones de inicio](configuration_security.md#startup-checks).
    - Establecer `LIBREFOLIO_INSTANCE_KEY` donde ya existe `secrets/instance.key` cambia la clave. Para
      mover la clave al entorno o a un secreto de Docker, usa el contenido de `secrets/instance.key`
      como valor.

### 🔏 La comprobación de la clave {: #instance-key-check }

LibreFolio guarda, junto a la clave, un **valor de comprobación**: una huella corta de la clave en el archivo
`secrets/instance.key.check` del directorio de datos (carpeta `0700`, archivo `0600`). No es la clave y la clave
no se puede deducir a partir de él. En cada inicio, LibreFolio compara la huella de
la clave que tiene ahora con la que almacenó. Difieren cuando LibreFolio se inicia con **una clave distinta de aquella con la que se
escribieron los datos**: una máquina que recibió la clave equivocada, un archivo de clave reemplazado por uno nuevo.

- **El primer inicio** escribe el archivo. Si ya existen secretos de plugins guardados y la clave actual no puede leer
  ninguno, LibreFolio no lo escribe: tomaría la clave equivocada por la correcta. Entonces la comprobación
  indica que la clave no coincide hasta que vuelvas a poner la correcta.
- **Con una clave que no coincide**, el registro contiene un error al inicio, la
  pestaña Seguridad de Configuración › Administración lo indica (la comprobación es `platform.instance_key_check`). **La instancia sigue sirviendo**: tus datos no dependen de esta
  clave, solo los secretos de plugins guardados.
- **La solución es la clave correcta.** Vuelve a colocarla, con `LIBREFOLIO_INSTANCE_KEY`, su `_FILE` o el
  `secrets/instance.key` de los datos, e inicia LibreFolio de nuevo: la siguiente respuesta es `ok`, sin nada más que hacer.
- **Para cambiar realmente la clave**, por ejemplo cuando decides que los secretos antiguos están perdidos y que los secretos de plugins
  se introducirán de nuevo, establece `LIBREFOLIO_INSTANCE_KEY_ACCEPT=1` durante **un inicio**. Ese inicio reemplaza el valor de comprobación
  almacenado por el de la clave que tiene y registra una advertencia. **Luego elimina la variable y vuelve a iniciar**: mientras esté
  establecida, cada inicio acepta la clave que tenga y la protección no hace nada (la advertencia se registra en cada inicio, como recordatorio).
  Los valores son `1` o `0`, `true` o `false`, `yes` o `no`, `on` o `off`; cualquier otro valor detiene el inicio e indica el nombre de la variable.

!!! note "📏 Lo que la comprobación no puede ver"

    Sin un valor de comprobación almacenado y sin ningún secreto de plugin guardado, no hay nada que comparar, así que
    la respuesta es `ok`: el primer inicio de una instancia cuya clave ya era incorrecta no se puede detectar. A partir
    de entonces, el valor almacenado la protege. Si los datos vuelven sin su carpeta `secrets/`, el valor
    se escribe de nuevo en el siguiente inicio, y los secretos de plugins deciden mientras falta. Un valor de comprobación que no se puede leer
    (un permiso, un archivo dañado) nunca impide una copia de seguridad: la respuesta es `ok` y el registro contiene una advertencia, una vez.

---

## 🧩 Configuración de plugins {: #plugin-settings }

Un plugin puede solicitar su propia configuración: la clave API de una fuente de datos de pago, una región, una
preferencia. De los plugins incluidos con LibreFolio, dos solicitan una, cada uno una preferencia de búsqueda personal:
justETF y Borsa Italiana. Ninguno solicita un ajuste para toda la instancia; un plugin que añadas podría hacerlo. Un
ajuste puede ser de dos tipos:

- **Para toda la instancia**: un valor para toda la instancia, que solo un administrador puede guardar. Todos los
  usuarios pueden leer un valor no secreto y, de uno secreto, como una clave API, solo pueden saber si está establecido.
- **Personal**: el valor propio de cada usuario, que solo ese usuario puede guardar y leer. Los administradores nunca
  lo ven.

La configuración personal y la de toda la instancia se cambian en **Configuración › Plugins**, una pestaña que todos los usuarios tienen:
allí cada usuario cambia su configuración personal, y los administradores también la de toda la instancia, que los demás usuarios ven en solo lectura. En el diálogo de activos, **Configurar**, junto al proveedor de precios elegido, abre el mismo formulario solo para ese proveedor. Lo que muestra la pestaña, ajuste por ajuste:
[Configuración de plugins](../user/settings/plugins.md) en el manual de usuario.

Un ajuste para toda la instancia también puede darse mediante una variable de entorno, en `.env` o en el
entorno del contenedor como las demás opciones; uno personal no. Los plugins que tienen configuración, con las claves de su configuración, se enumeran mediante `GET /api/v1/settings/plugins` a cualquier
usuario que haya iniciado sesión.

### 🏷️ Las variables {: #plugin-variables }

LibreFolio construye el nombre de la variable a partir del tipo de plugin, el código del plugin y la
clave del ajuste:

```text
LIBREFOLIO_PLUGIN_<KIND>_<PLUGIN CODE>_<SETTING KEY>
```

- `<KIND>` es `ASSET` para un proveedor de precios y `FX` para un proveedor de tipos de cambio.
- El nombre completo está en mayúsculas y cada carácter que no sea una letra o un dígito se convierte en `_`:
  el ajuste `api_key` del proveedor de precios `my_provider` es
  `LIBREFOLIO_PLUGIN_ASSET_MY_PROVIDER_API_KEY`.
- Para un ajuste secreto, un plugin también puede aceptar la variable que leía antes de tener configuración, para
  que una instalación existente siga funcionando. Cuando ambas están establecidas, prevalece el nombre indicado arriba.
- Cada variable también tiene una forma `_FILE`, la ruta de un archivo que contiene el valor, como un secreto
  de Docker. El archivo se lee como en [Secretos en archivos](#secret-files), pero uno que no se pueda leer nunca
  detiene el servidor: consulta más abajo.

### 🔒 Una variable bloquea el ajuste {: #plugin-variable-lock }

Mientras su variable esté establecida, un ajuste toma su valor de allí y nadie puede cambiarlo desde
dentro de LibreFolio: se rechaza el guardado (`LOCKED_BY_ENV`) y se ignora un valor guardado anteriormente hasta
que elimines la variable y reinicies. **Configuración › Plugins** muestra el ajuste en solo lectura; si es secreto, solo como *Establecido*: *Establecido por la variable del servidor* y el nombre de la variable para los administradores, *Establecido por el servidor* para los demás usuarios.

- Un valor incorrecto, uno que el ajuste no acepta o un `_FILE` que no se puede leer, sigue bloqueando el
  ajuste, y entonces el plugin queda sin configurar: LibreFolio rechaza todas las solicitudes que se le hagan, incluso cuando
  el ajuste es opcional, hasta que corrijas la variable. Nunca recurre al valor guardado ni al
  valor predeterminado del plugin. El registro explica por qué, con una advertencia una vez por proceso del servidor:
  `Plugin setting variable invalid: the plugin is not configured until it is fixed`, con la
  variable y el motivo, nunca el valor. En **Configuración › Plugins**, la insignia del plugin muestra
  **Por configurar**, y el ajuste indica que su variable no es válida. Corrige el valor y luego reinicia.

### 🔐 Secretos guardados y la clave de instancia {: #plugin-secrets }

Un ajuste guardado dentro de LibreFolio se conserva en la base de datos. Si es secreto, se cifra primero
(AES-256-GCM) con una clave derivada de la [clave de instancia](#instance-key), y nunca se vuelve a mostrar,
ni siquiera a quien lo guardó: LibreFolio solo indica si está establecido (en **Configuración › Plugins**,
*Establecido* y la fecha en que se guardó). Un valor dado por una variable, sea secreto o no, nunca se guarda en
la base de datos.

Si la clave de instancia cambia, los secretos guardados ya no se pueden leer. LibreFolio los conserva y
los notifica como ilegibles, y nunca usa un valor incorrecto. La pestaña lo indica bajo cada
uno: *Guardado, pero la clave de esta instancia no puede leerlo. Si un administrador puede volver a poner la clave antigua,
eso es lo primero; de lo contrario, introdúcelo de nuevo.* Si todavía tienes la clave antigua, vuelve a ponerla antes de que alguien los introduzca de nuevo: un secreto introducido con la clave nueva quedaría
ilegible una vez que vuelva la antigua. Para llevarlos a otra instalación, que mantiene su propia
clave, restaura allí una copia de seguridad con la clave antigua: `backup restore` con `--instance-key-file`
los vuelve a cifrar con la clave de esa instalación ([La clave de instancia de otra
instalación](cli_tools.md)). Desde el primer inicio después del cambio, y en cada inicio
hasta que se introduzcan de nuevo o vuelva la clave antigua, el registro contiene un error que cuenta los
secretos de toda la instancia, si los hay: consulta [Comprobaciones de inicio](configuration_security.md#startup-checks).

Si `secrets/instance.key` está dañada o es inaccesible, LibreFolio se inicia de todos modos, con un error de
las [comprobaciones de inicio](configuration_security.md#startup-checks); en cambio, una clave que hayas establecido tú y que no se pueda usar detiene el inicio.
Hasta que lo corrijas:

- todos los secretos guardados se notifican como ilegibles y los plugins se ejecutan sin ellos: un plugin que necesita
  uno responde que no está configurado;
- los secretos proporcionados por variables siguen funcionando;
- un secreto nuevo no se puede guardar: la pestaña responde *Los secretos no se pueden guardar: la clave de esta instancia no se puede usar (consulta las comprobaciones de configuración).*, y no se escribe nada de ese guardado;
- el registro contiene un error más, la primera vez que cada proceso del servidor necesita un secreto guardado:
  `Plugin secrets unreadable: the instance key cannot be used (see the configuration checks)`.

Corrige el archivo, o restáuralo desde una copia de seguridad, y los secretos guardados vuelven. Una clave nueva no los recupera: tendrían que introducirse de nuevo.

!!! warning "🗄️ La base de datos y la clave en una misma carpeta"

    La base de datos (`sqlite/app.db`) y la clave de instancia que genera LibreFolio
    (`secrets/instance.key`) están en el mismo [directorio de datos](filesystem.md): quien obtenga ambas cosas, la
    carpeta en sí o una copia de ella, puede leer todos los secretos guardados.

    - Mantén privado el directorio de datos y todas sus copias.
    - Mejor aún, proporciona la clave de instancia desde un almacén de secretos, con `LIBREFOLIO_INSTANCE_KEY_FILE` (un
      secreto de Docker) o `LIBREFOLIO_INSTANCE_KEY`: así LibreFolio nunca la escribe en el directorio de datos. Si LibreFolio ya ha creado `secrets/instance.key`, usa su contenido como
      valor, tal como explica [La clave de instancia](#instance-key): otra clave haría ilegibles los secretos guardados.

---

## 🔗 Relacionados

- 📄 **[Configuración](configuration.md)** — Crear el archivo `.env`, opciones principales, parámetros establecidos por las herramientas, …
- 📄 **[Configuración: comprobaciones y protecciones](configuration_security.md)** — Comprobaciones de inicio, protecciones del navegador, detener el servidor
- 📄 **[Configuración: cuentas y búsqueda de activos](configuration_accounts.md)** — Cuentas y registros, el orden de los proveedores de precios en la búsqueda, opcional: búsqueda web para nuevos activos
