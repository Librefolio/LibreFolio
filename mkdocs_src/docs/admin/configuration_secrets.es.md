# 🔐 Configuración: secretos y configuración de plugins

Lo que debe permanecer privado en una instalación de LibreFolio: las opciones que son **secretos** (claves, contraseñas y tokens), que también pueden leerse desde archivos como los secretos de Docker; la **clave de instancia**, que protege lo que LibreFolio almacena; y la **configuración de los plugins**, incluidas las claves API.

¿Es la primera vez que usas el archivo `.env`? Cómo crearlo, las opciones principales y qué valor prevalece: [Configuración](configuration.md).

---

## 🔐 Secretos {: #secrets }

**Dónde**: en el `.env` de LibreFolio, o en el entorno del contenedor (bloque `environment:` de `docker-compose.yml`). Cada secreto también puede leerse desde un archivo, con su variable `_FILE` ([Secretos en archivos](#secret-files)). Trátalos con la misma privacidad que la base de datos.

| Secreto | Desde un archivo | Qué es |
| --- | --- | --- |
| `JWT_SECRET` | `JWT_SECRET_FILE` | La clave que firma las sesiones de inicio de sesión, en las [opciones principales](configuration.md). |
| `LIBREFOLIO_INSTANCE_KEY` | `LIBREFOLIO_INSTANCE_KEY_FILE` | La [clave de instancia](#instance-key). Si no se establece, LibreFolio crea una en el directorio de datos. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | La clave de un servicio de búsqueda de pago, para el motor `apikey` de la [búsqueda web](configuration_accounts.md#optional-web-search-for-new-assets). |
| `LIBREFOLIO_SMTP_PASSWORD` | `LIBREFOLIO_SMTP_PASSWORD_FILE` | La contraseña del servidor SMTP que envía los correos electrónicos de LibreFolio: [Correo electrónico](email.md). |

Un plugin puede tener sus propios secretos, como la clave API de una fuente de datos de pago: [Configuración de plugins](#plugin-settings).

### 📄 Secretos en archivos {: #secret-files }

Añade `_FILE` al nombre del secreto y proporciona la ruta de un archivo que lo contenga, por ejemplo `/run/secrets/jwt_secret`. Así entregan sus secretos Docker y Kubernetes: el secreto queda fuera de `.env` y fuera del entorno del contenedor.

Reglas del archivo:

- El secreto es el texto del archivo, sin los saltos de línea al final y sin la marca de orden de bytes que algunos editores de Windows colocan al principio. Cualquier otro espacio cuenta, también al principio y al final.
- Una ruta relativa parte de la carpeta del proyecto.
- Un secreto o su variable `_FILE` que esté vacío o contenga solo espacios se considera no establecido: nunca se usa un espacio suelto como clave.
- Establece una de las dos. Si están establecidas ambas, prevalece la variable en sí, se ignora el archivo y el registro de inicio contiene una [advertencia](configuration_security.md#startup-checks).
- `.env` funciona tanto con `./dev.py` como con Docker Compose (`env_file: .env`): ambos colocan sus valores en el entorno, donde LibreFolio los lee.

Si el archivo no proporciona el secreto:

| Variable | Cuándo se lee | Si el archivo no proporciona el secreto |
| --- | --- | --- |
| `JWT_SECRET_FILE`, `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` | al inicio | **El servidor se detiene al inicio.** El error indica la variable y la ruta, nunca el secreto. Esto incluye un archivo que falta, que no se puede leer, que está vacío o en blanco (solo espacios y saltos de línea), que no es texto UTF-8 o que supera los 64 KiB. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` | solo cuando una búsqueda usa el motor `apikey` | El servidor no se detiene: la búsqueda continúa sin la búsqueda web, con una advertencia en el registro (`web_link_finder: …; disabling`); la búsqueda propia de los proveedores sigue funcionando. |
| `LIBREFOLIO_SMTP_PASSWORD_FILE` | solo cuando `LIBREFOLIO_SMTP_HOST` está establecido | El servidor no se detiene: el correo electrónico permanece desactivado, con un error en el registro (`Email configuration cannot be used: email stays off`). |

??? example "🐳 Un secreto de Docker con Docker Compose"

    1. **Desde un terminal, en la carpeta de `docker-compose.yml`**, guarda una clave nueva en un archivo:

        ```bash
        python3 -c "import secrets; print(secrets.token_urlsafe(64))" > jwt_secret.txt
        ```

        Obtienes `jwt_secret.txt` junto a `docker-compose.yml`.

    2. **Desde un terminal**, haz que el archivo sea legible por el usuario de la imagen, `1000:1000` para la oficial ([Docker avanzado](docker_advanced.md)):

        ```bash
        sudo chown 1000:1000 jwt_secret.txt
        sudo chmod 600 jwt_secret.txt
        ```

        Compose monta el archivo en el contenedor tal como está en el host, con su propietario y sus permisos: si el usuario de la imagen no puede leerlo, el servidor se detiene al inicio con `cannot be read` para el archivo.

    3. **En `docker-compose.yml`**, añade las líneas marcadas y deja el resto del servicio tal como está:

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

    4. **En `.env`**, si una línea asigna un valor a `JWT_SECRET`, elimínala: prevalecería sobre el archivo. Una línea `JWT_SECRET=` vacía no causa ningún problema.

    5. Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.

    Los archivos de `LIBREFOLIO_INSTANCE_KEY_FILE`, `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` y `LIBREFOLIO_SMTP_PASSWORD_FILE` se montan de la misma manera; lo que hace cada variable cuando el archivo no proporciona el secreto: la tabla de [Secretos en archivos](#secret-files).

### 🗝️ La clave de instancia {: #instance-key }

Un secreto por instalación: LibreFolio deriva de él sus propias claves de cifrado. No hay nada que configurar. LibreFolio usa la primera clave que encuentra:

1. `LIBREFOLIO_INSTANCE_KEY`, la clave en sí;
2. `LIBREFOLIO_INSTANCE_KEY_FILE`, un archivo que la contiene, como un secreto de Docker;
3. `secrets/instance.key` en el directorio de datos, que LibreFolio crea la primera vez que la necesita: 43 caracteres aleatorios, en una carpeta y un archivo que solo puede abrir el usuario que ejecuta LibreFolio (`0700` y `0600`).

**Para proporcionar una clave propia**, por ejemplo en la nube, desde el entorno o desde un secreto de Docker en lugar del directorio de datos. Cada instancia tiene su propia clave: nunca compartas una misma clave entre varias instancias.

1. **Desde un terminal**, genera la clave:

    ```bash
    python3 -c "import secrets; print(secrets.token_urlsafe(32))"
    ```

    Obtienes una clave aleatoria de al menos 32 caracteres, el mínimo. No uses nunca una frase de contraseña: las claves que LibreFolio deriva de ella son tan fuertes como la frase. Si LibreFolio ya ha creado `secrets/instance.key`, no generes nada: usa su contenido como valor, porque establecer `LIBREFOLIO_INSTANCE_KEY` donde `secrets/instance.key` ya existe cambia la clave.

2. **En `.env` o en el entorno del contenedor**, establece la clave, o guárdala en un archivo y proporciona la ruta, como en el [ejemplo de Docker](#secret-files):

    ```env
    LIBREFOLIO_INSTANCE_KEY=<key>
    # or
    LIBREFOLIO_INSTANCE_KEY_FILE=/run/secrets/instance_key
    ```

3. Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.

!!! warning "🔑 No cambies ni borres nunca la clave una vez en uso"

    Solo la misma clave puede volver a leer lo que se cifró con ella.

    - Haz una copia de seguridad de `secrets/` junto con el resto del directorio de datos y mantén las copias tan privadas como la base de datos: [Copia de seguridad](filesystem.md#backup).
    - Una vez que existe la clave, LibreFolio no puede distinguir un `instance.key` perdido de un primer uso: crea una clave nueva, y lo que cifró la anterior ya no se puede leer. Cuando restaures los datos, vuelve a poner `secrets/` con ellos antes de iniciar LibreFolio de nuevo. No inicies nunca LibreFolio sobre datos restaurados sin su `secrets/`.
    - Si LibreFolio ya ha creado una clave nueva: deténlo, pon tu copia de `instance.key` en lugar de la nueva y vuelve a iniciarlo, antes de que nadie vuelva a introducir un [secreto de plugin](#plugin-secrets): un secreto introducido con la clave nueva dejaría de poder leerse en cuanto vuelva la anterior.
    - `instance.key` presente pero dañado o inaccesible: LibreFolio registra un error y nunca lo reemplaza. Qué hacer: [Comprobaciones de inicio](configuration_security.md#startup-checks).

### 🔏 La comprobación de la clave {: #instance-key-check }

Junto a la clave, LibreFolio guarda un **valor de comprobación**: `secrets/instance.key.check` en el directorio de datos (carpeta `0700`, archivo `0600`), una huella corta de la clave a partir de la cual no se puede deducir la clave. En cada inicio compara la huella de la clave que tiene ahora con la almacenada: difieren cuando arranca con **una clave distinta de aquella con la que se escribieron los datos** (una máquina que recibió la clave equivocada, un archivo de clave sustituido por uno nuevo).

- **El primer inicio** escribe el archivo. No lo escribe si ya existen secretos de plugin guardados y la clave actual no lee ninguno: tomaría la clave equivocada por la correcta. La comprobación indica entonces que la clave no coincide hasta que vuelvas a poner la correcta.
- **Con una clave que no coincide**: un error en el registro al iniciar, y la pestaña **Seguridad** de Configuración › Administración lo indica (la comprobación es `platform.instance_key_check`). **La instancia sigue funcionando**: tus datos no dependen de esta clave, solo los secretos de plugin guardados.

**La solución es la clave correcta.**

1. **En `.env` o en el entorno del contenedor** (`LIBREFOLIO_INSTANCE_KEY` o su `_FILE`), o **en el directorio de datos** (`secrets/instance.key`), vuelve a poner la clave con la que se escribieron los datos.
2. Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`. La siguiente respuesta es `ok`, sin nada más que hacer.

**Para cambiar de verdad la clave**, por ejemplo cuando decides que los secretos antiguos están perdidos y los secretos de plugin se introducen de nuevo:

1. **En `.env` o en el entorno del contenedor**, añade, para **un solo inicio**:

    ```env
    LIBREFOLIO_INSTANCE_KEY_ACCEPT=1
    ```

    Valores: `1` o `0`, `true` o `false`, `yes` o `no`, `on` u `off`; cualquier otro valor detiene el inicio, indicando la variable.

2. Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`. Ese inicio sustituye el valor de comprobación almacenado por el de la clave que tiene, y registra una advertencia.

3. **Elimina la variable y reinicia otra vez.** Mientras esté establecida, cada inicio acepta la clave que tenga y la protección no hace nada; la advertencia se registra en cada inicio, como recordatorio.

!!! note "📏 Lo que la comprobación no puede ver"

    - Sin un valor de comprobación almacenado y sin ningún secreto de plugin guardado no hay nada que comparar: la respuesta es `ok`. No se puede detectar el primer inicio de una instancia cuya clave ya era incorrecta; a partir de ahí, el valor almacenado la protege.
    - Si los datos vuelven sin su carpeta `secrets/`, el valor se escribe de nuevo en el siguiente inicio; mientras falte, deciden los secretos de plugin.
    - Un valor de comprobación que no se puede leer (un permiso, un archivo dañado) nunca detiene una copia de seguridad: la respuesta es `ok` y el registro tiene una advertencia, una sola vez.

---

## 🧩 Configuración de plugins {: #plugin-settings }

Un plugin puede pedir ajustes propios: la clave API de una fuente de datos de pago, una región, una preferencia. De los plugins incluidos con LibreFolio, dos piden uno, una preferencia personal de búsqueda cada uno: justETF y Borsa Italiana. Ninguno pide un ajuste para toda la instancia; un plugin que añadas puede hacerlo. Dos tipos:

| Tipo | Quién lo guarda | Quién lo lee | Desde una variable de entorno |
| --- | --- | --- | --- |
| **Para toda la instancia** | solo un administrador | todos los usuarios leen un valor simple; de uno secreto, como una clave API, solo saben si está establecido | sí: [Las variables](#plugin-variables) |
| **Personal** | solo ese usuario | solo ese usuario; los administradores nunca lo ven | no |

**Dónde cambiarlos**: en **Configuración › Plugins**, una pestaña que tiene todo usuario: los personales cada uno los suyos, los de toda la instancia solo los administradores (los demás usuarios los ven en solo lectura). En el diálogo del activo, **Configurar**, junto al proveedor de precios elegido, abre el mismo formulario solo para ese proveedor. Lo que muestra la pestaña, ajuste por ajuste: [Configuración de plugins](../user/settings/plugins.md) en el manual de usuario.

Los plugins que tienen ajustes, con las claves de sus ajustes, los lista `GET /api/v1/settings/plugins` para cualquier usuario con sesión iniciada.

### 🏷️ Las variables {: #plugin-variables }

**Dónde**: en `.env` o en el entorno del contenedor, como las demás opciones; solo para ajustes de toda la instancia. El nombre de la variable:

```text
LIBREFOLIO_PLUGIN_<KIND>_<PLUGIN CODE>_<SETTING KEY>
```

- `<KIND>` es `ASSET` para un proveedor de precios y `FX` para un proveedor de tipos de cambio.
- Todo en mayúsculas; cada carácter que no sea una letra o un dígito se convierte en `_`. El ajuste `api_key` del proveedor de precios `my_provider`:

    ```env
    LIBREFOLIO_PLUGIN_ASSET_MY_PROVIDER_API_KEY=<value>
    ```

- Cada variable también tiene una forma `_FILE`: la ruta de un archivo que contiene el valor, como un secreto de Docker, que se lee como en [Secretos en archivos](#secret-files). Un archivo que no se puede leer nunca detiene el servidor: consulta [más abajo](#plugin-variable-lock).
- Para un ajuste secreto, un plugin también puede aceptar la variable que leía antes de tener ajustes, de modo que una instalación existente siga funcionando. Si están establecidas ambas, prevalece el nombre de arriba.

Luego reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.

### 🔒 Una variable bloquea el ajuste {: #plugin-variable-lock }

Mientras su variable esté establecida, un ajuste toma su valor de allí y nadie puede cambiarlo desde dentro de LibreFolio: se rechaza un guardado (`LOCKED_BY_ENV`), y un valor guardado antes se ignora hasta que elimines la variable y reinicies. **Configuración › Plugins** muestra el ajuste en solo lectura, uno secreto solo como *Establecido*: *Definido por la variable del servidor* y el nombre de la variable para los administradores, *Definido por el servidor* para los demás usuarios.

**Un valor incorrecto**, uno que el ajuste no acepta, o un `_FILE` que no se puede leer, bloquea igualmente el ajuste, y el plugin queda entonces sin configurar: LibreFolio rechaza toda petición hacia él, incluso cuando el ajuste es opcional, hasta que corrijas la variable. Nunca recurre al valor guardado ni al predeterminado del plugin.

- En el registro, una advertencia una vez por proceso del servidor: `Plugin setting variable invalid: the plugin is not configured until it is fixed`, con la variable y el motivo, nunca el valor.
- En **Configuración › Plugins**, la insignia del plugin dice **Por configurar** y el ajuste indica que su variable no es válida.

Corrige el valor **en `.env` o en el entorno del contenedor** y reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.

### 🔐 Secretos guardados y la clave de instancia {: #plugin-secrets }

Un ajuste guardado dentro de LibreFolio se conserva en la base de datos. Uno secreto se cifra primero (AES-256-GCM) con una clave derivada de la [clave de instancia](#instance-key), y no se vuelve a mostrar nunca, ni siquiera a quien lo guardó: **Configuración › Plugins** solo indica si está establecido, *Establecido el* y la fecha en que se guardó. Un valor dado por una variable, secreto o no, nunca se guarda en la base de datos.

**Si cambia la clave de instancia**, los secretos guardados ya no se pueden leer. LibreFolio los conserva, los marca como ilegibles y nunca usa un valor incorrecto. La pestaña lo indica bajo cada uno: *Guardado, pero la clave de esta instancia no puede leerlo. Si un administrador puede volver a poner la clave anterior, eso va primero; si no, vuelve a introducirlo.* Desde el primer inicio tras el cambio, y en cada inicio hasta que se vuelvan a introducir o vuelva la clave anterior, el registro tiene un error que cuenta los de toda la instancia, si los hay: [Comprobaciones de inicio](configuration_security.md#startup-checks).

| Situación | Qué hacer |
| --- | --- |
| Todavía tienes la clave anterior | Vuelve a ponerla, antes de que nadie vuelva a introducir los secretos ([La clave de instancia](#instance-key) explica por qué). |
| Ya no la tienes | Vuelve a introducir cada secreto en **Configuración › Plugins**. |
| Quieres llevarlos a otra instalación, que conserva su propia clave | **Desde un terminal, en esa instalación**, restaura una copia de seguridad con la clave anterior: `backup restore` con `--instance-key-file` los vuelve a cifrar con la clave de esa instalación ([La clave de instancia de otra instalación](cli_tools.md)). |

**Si `secrets/instance.key` está dañado o inaccesible**, LibreFolio arranca igualmente, con un error de las [comprobaciones de inicio](configuration_security.md#startup-checks); una clave que estableces tú mismo y que no se puede usar detiene el inicio. Hasta que lo corrijas:

- todo secreto guardado se marca como ilegible, y los plugins funcionan sin ellos: un plugin que necesita uno responde que no está configurado;
- los secretos dados por variables siguen funcionando;
- no se puede guardar un secreto nuevo: la pestaña responde *Los secretos no se pueden guardar: la clave de esta instancia no se puede usar (consulta las comprobaciones de la configuración).*, y no se escribe nada de ese guardado;
- el registro tiene un error más, la primera vez que cada proceso del servidor necesita un secreto guardado: `Plugin secrets unreadable: the instance key cannot be used (see the configuration checks)`.

Corrige el archivo **en el directorio de datos**, o restáuralo desde una copia de seguridad: los secretos guardados vuelven. Una clave nueva no los devuelve: habría que volver a introducirlos.

!!! warning "🗄️ La base de datos y la clave en la misma carpeta"

    La base de datos (`sqlite/app.db`) y la clave de instancia que genera LibreFolio (`secrets/instance.key`) están en el mismo [directorio de datos](filesystem.md): quien consiga ambas, la propia carpeta o una copia de ella, puede leer todos los secretos guardados.

    - Mantén privado el directorio de datos y cada copia suya.
    - Mejor aún, proporciona la clave de instancia desde un almacén de secretos, con `LIBREFOLIO_INSTANCE_KEY_FILE` (un secreto de Docker) o `LIBREFOLIO_INSTANCE_KEY`: LibreFolio entonces nunca la escribe en el directorio de datos. Si `secrets/instance.key` ya existe, usa su contenido como valor ([La clave de instancia](#instance-key)): otra clave dejaría ilegibles los secretos guardados.

---

## 🔗 Relacionado

- 📄 **[Configuración](configuration.md)** — Crear el archivo `.env`, opciones principales, parámetros establecidos por las herramientas, …
- 📄 **[Configuración: comprobaciones y protecciones](configuration_security.md)** — Comprobaciones de inicio, protecciones del navegador, detener el servidor
- 📄 **[Configuración: cuentas y búsqueda de activos](configuration_accounts.md)** — Cuentas y registros, el orden de los proveedores de precios en la búsqueda, opcional: búsqueda web para nuevos activos
