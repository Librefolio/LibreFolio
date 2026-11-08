# 🛡️ Configuración: comprobaciones y protecciones

Esta página cubre:

- las **comprobaciones al arrancar**: qué significa cada hallazgo, dónde corregirlo y con qué valor;
- las **protecciones del navegador**: la Content-Security-Policy y la protección de marcos;
- **detener el servidor**.

Las opciones que examinan estas comprobaciones se explican en [Configuración](configuration.md); los secretos, en
[Configuración: secretos y configuración de plugins](configuration_secrets.md).

---

## 🩺 Comprobaciones al arrancar {: #startup-checks }

Justo después de la línea `Starting LibreFolio`, el servidor comprueba su propia configuración sin cambiar nada.

**Dónde las lees:**

| Dónde | Cómo |
| --- | --- |
| El registro del servidor | Una línea por hallazgo, en su nivel, con el nombre de la comprobación en `check` (p. ej. `platform.jwt_secret`). |
| **Configuración › Administración › Seguridad** (solo administradores) | Las mismas comprobaciones, en el idioma de la aplicación; un número en la pestaña cuenta los errores y las advertencias. Cuando hayas corregido y reiniciado, haz clic en **Comprobar de nuevo** ([Seguridad](settings.md#security-tab)). |

**Dónde las corriges:** salvo que la tabla diga otra cosa, en el **archivo `.env`** de LibreFolio.
Luego reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.

| Nivel | El registro dice (`check`) | Dónde | Qué hacer |
| --- | --- | --- | --- |
| ℹ️ `info` | `The session key is random: every restart signs everyone out. To stay signed in, set JWT_SECRET.` | `.env` | Nada, si te parece bien desconectar a todos en cada reinicio. En caso contrario, establece `JWT_SECRET`: [Mantener a los usuarios conectados](index.md#session-persistence). |
| ⚠️ `warning` | `The session signing key from JWT_SECRET is … characters long: use at least 32 random characters` (o `from JWT_SECRET_FILE (<path>)`) | `.env`, o el archivo que nombra la línea | Genera una clave de al menos 32 caracteres aleatorios, como en [Mantener a los usuarios conectados](index.md#session-persistence), y colócala donde indica la línea. |
| ⚠️ `warning` | `Set both directly and through a *_FILE variable: …` | `.env` | Para cada secreto listado, conserva solo una de las dos: la variable en sí prevalece, el archivo se ignora. |
| ❌ `error` | `The instance key cannot be used: …`, terminando con `cannot be reached (Permission denied)` o `cannot be read (…)` | Línea de comandos, en el servidor: la carpeta `secrets/` y `instance.key` | Pertenecen a otro usuario, o sus permisos dejan a LibreFolio fuera. Devuelve ambos al usuario que ejecuta LibreFolio (`chown`), luego `chmod 700` en la carpeta y `chmod 600` en el archivo. Nunca sustituyas la clave por una nueva. El servidor arranca de todos modos. |
| ❌ `error` | `The instance key cannot be used: …`, con otro motivo, como `is empty or blank` | El archivo `secrets/instance.key` | Está dañado: restáuralo desde una copia de seguridad, nunca lo sustituyas por una clave nueva. El servidor arranca de todos modos. |
| ⚠️ `warning` | `… is open to other users (…): the folder should be 0700 and the file 0600` | Línea de comandos, en el servidor | `chmod 700` en la carpeta `secrets/`, `chmod 600` en `instance.key`. |
| ⚠️ `warning` | `SESSION_COOKIE_SECURE=never: the session cookie is sent over plain HTTP too; prefer auto` | `.env` | Vuelve a `auto`, salvo que realmente necesites `never`: [`SESSION_COOKIE_SECURE`](configuration.md#session-cookie-secure). |
| ℹ️ `info` | `The log level is DEBUG: the log records operational detail; …` (o `TRACE`) | `.env` | Vuelve a `INFO` cuando termines de diagnosticar. |
| ❌ `error` | `LIBREFOLIO_TEST_MODE is on outside a test lane: test-only providers are served, the data are kept in the test data directory <path> and .env is not read; unset it on a production instance` (`platform.test_mode`) | El entorno del servidor, no `.env`: busca de dónde viene, por ejemplo una unidad de servicio | Elimina `LIBREFOLIO_TEST_MODE`, o establécela en `0`, y luego reinicia. El modo de prueba es para las propias pruebas de LibreFolio (`./dev.py test`, `./dev.py server --test`), que lo activan y desactivan por sí mismas. Hasta entonces el servidor trabaja en la carpeta que nombra la línea, no en tu [directorio de datos](filesystem.md): lo que introduzcas mientras tanto se guarda allí. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore uploads answer 503 until it is fixed` (`backup.upload_limit`) | `.env` | Un número entero de megabytes, `0` para indicar que no hay límite, o elimina la variable ([El límite de subida de una restauración](backup_restore.md#restore-upload-limit)). Hasta entonces Configuración › Administración › Copia de seguridad no puede subir un archivo para restaurarlo; la línea de comandos sigue restaurando uno. El servidor arranca de todos modos. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore checks answer 503 until it is fixed` (`backup.restore_limit`) | `.env` | Como arriba, en la variable que nombra la línea. Hasta entonces toda comprobación de una restauración se rechaza con `backup_restore_unavailable`, desde Configuración › Administración › Copia de seguridad y desde la línea de comandos, donde `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` delante de `backup restore` levanta el límite para ese comando. El servidor arranca de todos modos. |
| ❌ `error` | `LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: …; the hosting panel's backups answer 503 until it is fixed` (o `expected at most 2 recipients`, `repeats an earlier recipient`) (`backup.recipients`) | `.env` | Una o dos claves públicas `age1…`, separadas por comas, tal como las da `backup keygen` ([Copias de seguridad selladas](backup_sealed.md#sealed)). El servidor arranca de todos modos. |
| ⚠️ `warning` | `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance` (`accounts.login_limit`) | `.env` | Nada, en una instancia dedicada a pruebas. En caso contrario, elimina la variable o establécela en `on`: [Inicios de sesión fallidos](configuration_accounts.md#login-limit). |
| ❌ `error` | `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` (`email.smtp`) | `.env`, la variable que nombra la línea | Solo el correo está desactivado, nada más. Qué significa cada código: [Problemas de configuración](email_troubleshooting.md#configuration-problems). El servidor arranca de todos modos. |
| ⚠️ `warning` | `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `.env` | `LIBREFOLIO_SMTP_TLS=starttls` o `tls`, o envía a través de un relay en tu propia red: [Notas de seguridad](email_troubleshooting.md#security). |
| ℹ️ `info` | `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` (`email.links`) | `.env` | Nada, si ningún enlace tiene que salir por correo electrónico. En caso contrario, establece `LIBREFOLIO_PUBLIC_URL` en la dirección en la que tus usuarios abren LibreFolio ([Cuentas y registros](configuration_accounts.md#accounts), [Correo electrónico](email.md)). |
| ⚠️ `warning` | `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` (`email.links`) | `.env` | Escribe la dirección con `http://` o `https://` y un nombre de host, sin nombre de usuario, contraseña, `?` ni `#`, como `https://librefolio.example.com` ([Correo electrónico](email.md)). |
| ❌ `error` | `Stored plugin secrets that the instance key cannot read: <N>. Enter them again in the plugin settings, or restore the instance key they were saved with` (`platform.plugin_secrets`; esta llega más tarde, una vez que la base de datos está lista) | `secrets/instance.key` o `LIBREFOLIO_INSTANCE_KEY`; solo como último recurso **Configuración › Plugins** | La clave de instancia cambió después de que se guardaran estos [secretos de plugins](configuration_secrets.md#plugin-secrets): procedimiento más abajo. El servidor arranca de todos modos. |

??? note "🔑 Secretos de plugins ilegibles: vuelve a poner la clave antigua"

    Causas: un `secrets/instance.key` perdido que LibreFolio sustituyó por uno nuevo, datos restaurados sin su
    `secrets/`, u otro `LIBREFOLIO_INSTANCE_KEY`.

    Si el registro también dice `The instance key cannot be used: …`, corrige eso primero (tabla de arriba).

    1. **¿Todavía tienes la clave antigua?** Tu copia de `secrets/instance.key`, respaldada junto con el directorio
       de datos como dice [La clave de instancia](configuration_secrets.md#instance-key), o el valor antiguo de la
       variable. Un archivo claro hecho con **Copia de seguridad de la instancia** deja fuera la clave; uno
       [seguro](backup_restore.md#secure) lleva la clave que generó LibreFolio, y su restauración vuelve a cifrar
       estos secretos.
    2. **Detén LibreFolio**, coloca la clave antigua en lugar de la nueva y vuelve a arrancar.
       Los secretos vuelven a ser legibles.

    !!! warning "⚠️ Antes de que nadie introduzca un secreto de nuevo"

        Un secreto introducido de nuevo se guarda bajo la clave nueva, y se vuelve ilegible una vez que vuelve la
        antigua.

    Solo si la clave antigua se ha perdido: introduce los secretos de nuevo en **Configuración › Plugins**. A partir de
    entonces, la clave que hay que respaldar es la nueva.

    Los secretos personales no se cuentan: cada usuario ve los suyos en su propia pestaña.

**Errores que impiden el arranque.** El servidor no arranca, y el error está en la salida de la consola (con Docker,
`docker compose logs librefolio`): nombra la variable y, cuando existe, el archivo, nunca el secreto. Corrígelo y
vuelve a arrancar.

| Causa | Dónde |
| --- | --- |
| Un `JWT_SECRET_FILE` o un `LIBREFOLIO_INSTANCE_KEY_FILE` que no puede dar su secreto | El archivo al que apunta la variable ([Secretos en archivos](configuration_secrets.md#secret-files)) |
| Una clave de instancia propia de menos de 32 caracteres | `.env`, `LIBREFOLIO_INSTANCE_KEY` |
| Un `LIBREFOLIO_LOGIN_LIMIT` distinto de `on` o `off` | `.env` ([Inicios de sesión fallidos](configuration_accounts.md#login-limit)) |

---

## 🛡️ Protecciones del navegador {: #browser-protections }

Todas las respuestas de LibreFolio llevan cabeceras que indican al navegador cómo proteger sus páginas.

| Cabecera | ¿Hay que configurarla? | Qué hace |
| --- | --- | --- |
| `X-Content-Type-Options: nosniff` | No, siempre presente | El navegador usa el tipo que envía LibreFolio: un archivo subido nunca se ejecuta como script ni se muestra como página. |
| `Referrer-Policy: strict-origin-when-cross-origin` | No, siempre presente | Otro sitio aprende como mucho la dirección de LibreFolio (`https://librefolio.example.com`), nunca la página de la que vino una petición. |
| `Content-Security-Policy` | No, en cada página de cada perfil, sin interruptor | [La Content-Security-Policy](#csp). |
| `X-Frame-Options` + `frame-ancestors` | `LIBREFOLIO_FRAME_PROTECTION` en `.env`, desactivada en una instalación propia | [Protección de marcos](#frame-protection). |
| `Content-Security-Policy-Report-Only` | `LIBREFOLIO_CSP_REPORT_ONLY` en `.env`, desactivada en una instalación propia | [La política de solo informe](#csp-report-only). |

Los dos interruptores se leen al arrancar: después de un cambio, reinicia LibreFolio. Con Docker Compose, ejecuta
`docker compose up -d`. Para desarrolladores: [Cabeceras de respuesta](../developer/architecture/security.md#response-headers).

### 🛡️ La Content-Security-Policy {: #csp }

Indica al navegador qué puede ejecutar una página y a dónde puede conectarse. LibreFolio **siempre aplica** una, en
cada perfil, sin ninguna opción para desactivarla. En el caso habitual no te pide nada: solo importa cuando algo entre
LibreFolio y el navegador añade un script a la página ([Un script que no enviaste](#csp-blocked-script)).

| Qué | Política | Efecto |
|---|---|---|
| Cada página de LibreFolio: la aplicación web, la documentación (`/mkdocs`) y, donde están activas, las páginas propias de la API en `/api/v1/docs` y `/api/v1/redoc` | `object-src 'none'; base-uri 'self'; form-action 'self'` | Ningún contenido de plugin (`<object>`, `<embed>`), ningún `<base>` y ningún formulario hacia otro sitio: LibreFolio no usa ninguno. Un PDF no es una página: no lleva nada de esto. |
| Las páginas de la aplicación web | `script-src`: solo los scripts propios de LibreFolio; sus scripts en línea se permiten por su hash, calculado a partir de los archivos de la aplicación web | Un script escrito en la página por cualquier otra persona no se ejecuta. |
| Las páginas de la aplicación web | `worker-src 'self' blob:` | Los workers del lector de PDF. |
| Las páginas propias de la API en `/api/v1/docs` y `/api/v1/redoc`, solo donde `LIBREFOLIO_API_DOCS` está activo | `script-src 'self' https://cdn.jsdelivr.net`, `worker-src 'self' blob:`, `connect-src 'self'` | Páginas propias de LibreFolio, no de FastAPI: Swagger UI y ReDoc desde `cdn.jsdelivr.net` en una versión fija, con un checksum que el navegador verifica (Subresource Integrity). Sus scripts de inicio vienen de tu instancia: ningún script en línea, ningún Google Fonts. El worker es la búsqueda de ReDoc. Con las páginas desactivadas, nada de esto existe. |
| Los scripts de la compilación de la aplicación web, los archivos bajo `/_app/` | `script-src 'self'`, el mismo `connect-src` que las páginas, `worker-src 'self' blob:`, `object-src 'none'`, `base-uri 'self'` | Se aplica solo si un navegador ejecuta uno de estos archivos como **worker**: carga los scripts propios de LibreFolio y nada más, y se conecta solo a donde pueden las páginas. Hoy el único worker iniciado desde un archivo es el que procesa precios; el worker del lector de PDF se inicia desde un `blob:` y conserva la política de la página. |
| Las páginas de la aplicación web | `connect-src 'self'`, el origen de [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) cuando está configurado, y `https://api.github.com` solo en una instalación autoalojada | A dónde puede enviar peticiones la página. GitHub sirve para la comprobación de una versión más reciente, que tu navegador hace cuando un administrador inicia sesión (nunca en el perfil `managed`). |
| Cada respuesta, con [Protección de marcos](#frame-protection) activada | `frame-ancestors 'self'` | Solo las páginas propias de LibreFolio pueden mostrarlo en un marco. |

**No** aplica `default-src`, `style-src`, `img-src`, `font-src` ni `frame-src`: las imágenes (los iconos de activos y
brókers son un enlace a cualquier dirección), los estilos, las fuentes y los marcos quedan libres. Si otra página puede
mostrar LibreFolio en un marco lo decide solo [`LIBREFOLIO_FRAME_PROTECTION`](#frame-protection).

Cuando recompilas la aplicación web desde las fuentes mientras LibreFolio se ejecuta, los hashes siguen la nueva
compilación: no necesitas reiniciarlo.

??? note "📄 La vista previa de PDF no pide nada a terceros"

    El motor del lector es una copia propia de LibreFolio, y `connect-src` se mantiene limitado a la dirección propia
    de LibreFolio. Si no se puede acceder a esa copia, la vista previa muestra el lector de PDF propio de tu
    navegador.

    Lo único que el lector descarga es texto en chino, japonés y coreano, y se lo pide a tu instancia
    (`/api/v1/files/pdf-fonts/…`, solo para usuarios con sesión iniciada). La primera vez, **el servidor** descarga la
    fuente desde `cdn.jsdelivr.net` (dirección y versión fijas), la conserva solo si su checksum (sha256) coincide con
    la lista que se distribuye con LibreFolio, y la guarda en `cache/pdf-fonts/` dentro del
    [directorio de datos](filesystem.md).

    - Puedes eliminar esa carpeta: las fuentes se descargan de nuevo cuando un PDF las necesita. No forma parte de
      una copia de seguridad.
    - Una instancia que no puede acceder a `cdn.jsdelivr.net` muestra ese PDF sin esos caracteres.
    - Un archivo que no coincide con la lista se descarta, y el registro tiene una advertencia que lo nombra.

#### 🕵️ Un script que no enviaste {: #csp-blocked-script }

Un proxy, una CDN o una extensión del navegador que **añada un script** a las páginas de LibreFolio se bloquea, como
cualquier otra cosa que LibreFolio no envió.

**Lo que ves:**

- la página funciona, pero puede perder la pieza que aportaba ese script: un contador, una dirección ofuscada, un
  widget de la extensión;
- la consola del navegador muestra, una vez por carga de página:

    ```text
    LibreFolio blocked a script it did not send (<source>): a proxy, a CDN or a browser extension adds it. Guide: https://<your address>/mkdocs/admin/configuration_security/#csp
    ```

    `<source>` es la dirección de la que vino el script, o `inline` para un script escrito en la página;

- en **Configuración › Administración › Seguridad** ([Seguridad](settings.md#security-tab)), el navegador que lo
  encontró muestra la advertencia *se bloqueó un script*, con las fuentes. La advertencia pertenece a esa pestaña
  del navegador y desaparece cuando la cierras.

Nada se envía a tu servidor: ni informe, ni petición. La consola y la pestaña son los únicos lugares donde el
navegador lo dice.

**Qué hacer:** desactiva la adición para la dirección de LibreFolio. Ninguna opción amplía la política.

| Quién añade el script | Dónde corregirlo | Qué hacer |
| --- | --- | --- |
| **Cloudflare**: Rocket Loader, Email Address Obfuscation, la configuración automática de Web Analytics | El panel de Cloudflare, para el nombre de host de LibreFolio | Desactiva Rocket Loader (*Speed › Optimization*), Email Address Obfuscation (*Scrape Shield*) y la configuración automática de Web Analytics (*Analytics & Logs › Web Analytics*). Una *Configuration Rule* lo hace solo para ese host y deja tus otros sitios como están. Los nombres de los menús cambian de vez en cuando. |
| **Nginx**: un `sub_filter` que escribe un `<script>` en las páginas | La configuración de Nginx, en el `server` o el `location` que hace de proxy de LibreFolio | Elimina ese `sub_filter`. |
| **Una extensión del navegador** que añade un script propio a cada página | El navegador | Desactívala para la dirección de LibreFolio, o prueba la página en una ventana privada, que normalmente se ejecuta sin extensiones. |

Luego recarga la página: la línea ha desaparecido de la consola. La advertencia de la pestaña Seguridad permanece
hasta que cierres esa pestaña del navegador.

#### 🔗 Una dirección pública que no se puede usar {: #csp-public-url }

`LIBREFOLIO_PUBLIC_URL` añade su origen (`scheme://host`, con el puerto solo cuando no es el predeterminado) a
`connect-src`. Un valor que no se puede usar (sin `http://` o `https://`, o con un nombre de usuario o una
contraseña) no añade nada: el servidor arranca y sirve como de costumbre, y el registro tiene la advertencia
*LIBREFOLIO_PUBLIC_URL cannot be used*.

Corrige el valor en el **`.env`** ([Cuentas y registros](configuration_accounts.md#accounts)).
Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.

#### 📡 La comprobación de dirección de un enlace para compartir {: #csp-address-check }

El campo **Dirección del servidor** de los diálogos de invitación y de restablecimiento de contraseña de la pestaña
[Usuarios](users.md#server-address) no pide datos a la dirección: la política lo impediría. Carga una imagen
diminuta y transparente desde la dirección que escribiste, `/api/v1/auth/address-probe.png`, que la política permite, y
lee su tamaño: un tamaño dice que **esta** instancia responde ahí, otro dice que responde otra cosa. Los mensajes
dicen lo mismo que antes.

### 🖼️ Protección de marcos {: #frame-protection }

Decide si una página en **otra dirección** puede mostrar LibreFolio en un marco. Otra dirección es otro nombre de
host, o el mismo en otro puerto: un panel de Home Assistant en `http://homeassistant.local:8123` que muestra
LibreFolio desde `http://homeassistant.local:6040`.

| `LIBREFOLIO_FRAME_PROTECTION` | Efecto |
| --- | --- |
| `false`, el valor predeterminado en una instalación propia | Cualquier página puede mostrar LibreFolio en un marco. |
| `true` | Solo las páginas propias de LibreFolio pueden mostrarlo en un marco; en cualquier otro sitio, el navegador se niega a mostrarlo. |

**Cuándo activarla:** en una instalación propia, déjala desactivada si alguna página tuya muestra LibreFolio en un
marco, como un panel de Home Assistant: con el interruptor activado, el navegador se negaría a mostrarlo ahí. Si
ninguna página tuya lo hace, actívala: ningún otro sitio podrá mostrar LibreFolio dentro de sus propias páginas.

1. **En el archivo `.env`**, añade:

    ```env
    LIBREFOLIO_FRAME_PROTECTION=true
    ```

2. Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.
   Cada respuesta lleva ahora `X-Frame-Options: SAMEORIGIN` y `Content-Security-Policy: frame-ancestors 'self'`, la
   misma regla en la cabecera antigua y en la nueva.

Con el interruptor activado:

- el mismo `Content-Security-Policy` también lleva las tres reglas que [LibreFolio aplica en sus páginas](#csp) en
  todos los perfiles (`object-src 'none'`, `base-uri 'self'`, `form-action 'self'`): no dependen de este interruptor.
  Un PDF conserva solo `frame-ancestors 'self'`, de modo que el navegador aún puede mostrarlo;
- una respuesta `304 Not Modified` recibe solo `X-Frame-Options`, para que el navegador conserve la política de la
  copia que ya tiene.

Es la comprobación `platform.frame_protection` de las [comprobaciones al arrancar](#startup-checks). Siempre pasa, y
el registro no dice nada al respecto; **Configuración › Administración › Seguridad** la incluye entre las
[comprobaciones superadas](settings.md#security-passed):

| Interruptor | La pestaña dice |
| --- | --- |
| Activado | *Solo las páginas propias de LibreFolio pueden mostrarlo en un marco.* |
| Desactivado, en una instalación propia | *Las páginas en otra dirección, como tus paneles, pueden mostrar LibreFolio en un marco: el valor predeterminado de una instalación propia.* |

### 📋 La política de solo informe {: #csp-report-only }

`LIBREFOLIO_CSP_REPORT_ONLY` añade a las páginas de la aplicación web una segunda política, **más amplia** que la
[Content-Security-Policy](#csp) aplicada: también dice de dónde puede cargar una página imágenes, estilos, fuentes y
marcos. Es de solo informe: el navegador no bloquea nada y enumera lo que queda fuera de ella en su consola de
desarrollador, y en ningún otro lugar. La política aplicada sigue activa sea cual sea el valor.

| `LIBREFOLIO_CSP_REPORT_ONLY` | Efecto |
| --- | --- |
| `false`, el valor predeterminado en una instalación propia | Ninguna política de solo informe. |
| `true` | Las páginas de la aplicación web llevan `Content-Security-Policy-Report-Only`. |

**Cuándo activarla:** en una instalación propia no hace falta: tus usuarios no ven ninguna diferencia. Actívala para
ver, en la consola de desarrollador del navegador, qué bloquearía una política de este tipo en tu instancia.

1. **En el archivo `.env`**, añade:

    ```env
    LIBREFOLIO_CSP_REPORT_ONLY=true
    ```

2. Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.
   Las páginas de la aplicación web llevan ahora la cabecera `Content-Security-Policy-Report-Only`.

Con el interruptor activado:

- la documentación (`/mkdocs`), todo lo que hay bajo `/api/`, incluidas las páginas de documentación de la API, los
  archivos que cargan las páginas y una respuesta `304 Not Modified` no la llevan;
- la política permite lo que viene de la dirección propia de LibreFolio y unas pocas excepciones que la aplicación
  necesita: imágenes de cualquier dirección `https://` (los iconos de activos y brókers son un enlace), estilos en
  línea y el WebAssembly del lector de PDF. Para desarrolladores, directiva por directiva:
  [La Content-Security-Policy y la protección de marcos](../developer/architecture/security.md#managed-headers);
- los scripts en línea de la aplicación web se permiten por sus hashes, como en la política aplicada: después de
  recompilar la aplicación web desde las fuentes, no necesitas reiniciar LibreFolio;
- cada línea que esta política añade a la consola dice lo que **habría** bloqueado: no se bloqueó nada. Un script que
  bloquea la política aplicada tiene su propia línea: [Un script que no enviaste](#csp-blocked-script).

Es la comprobación `platform.csp_report_only` de las [comprobaciones al arrancar](#startup-checks). Siempre pasa, y
el registro no dice nada al respecto; **Configuración › Administración › Seguridad** la incluye entre las
[comprobaciones superadas](settings.md#security-passed):

| Interruptor | La pestaña dice |
| --- | --- |
| Activado | Una línea que dice que las páginas de la aplicación web llevan una política de solo informe. |
| Desactivado, en una instalación propia | *Sin Content-Security-Policy de solo informe: el valor predeterminado de una instalación propia.* |

---

## ⏹️ Detener el servidor {: #shutdown }

Cuando se le pide que se detenga, el servidor debe hacerlo dentro del **presupuesto de apagado**: 8 segundos salvo
que lo cambies, contados desde la señal (SIGTERM de `docker stop`, `docker compose down` o un reinicio; SIGINT de
Ctrl+C).

**Dónde:** en el **archivo `.env`**.

| Variable | Predeterminado | Qué hace |
| --- | --- | --- |
| `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` | `8` | El presupuesto de apagado, en segundos: un número entero de `2` a `600`, o `0` para indicar que no hay límite, como antes de la versión 1.3. Un valor que no se puede usar no detiene el servidor, a diferencia de las [opciones principales](configuration.md#main-options): el registro dice `Shutdown budget setting cannot be used: the default applies`, y el presupuesto se queda en 8 segundos. |
| `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` | 3/8 del presupuesto | Cuántos segundos espera uvicorn, el servidor web, a las peticiones en curso: `3` con el presupuesto predeterminado. La imagen de Docker y `./dev.py server` lo calculan a partir del presupuesto. Un valor propio prevalece: mantenlo por debajo del presupuesto, que sigue contando para la detención completa. |

El presupuesto se gasta en este orden:

1. **Peticiones en curso**: el servidor web no acepta nuevas y da a las que ya se están ejecutando 3/8 del
   presupuesto, 3 segundos por defecto. Luego cancela las que siguen ejecutándose, como una importación larga de
   bróker: lo que no habían guardado aún vuelve al estado anterior (rollback), y se repiten cuando LibreFolio
   vuelve.
2. **El trabajo propio del servidor**: las sincronizaciones programadas, los procesos worker, las cachés… se detienen
   uno tras otro, cada uno dentro del tiempo restante. El último paso termina los procesos hijos que aún se ejecutan
   (importaciones de bróker, simulaciones de riesgo, Herramientas): ninguno sobrevive al servidor.
3. **Presupuesto agotado**: si algo todavía retiene el servidor, termina de todos modos con estado de salida 1, y el
   registro dice qué seguía ejecutándose: `Shutdown budget exhausted: ending the process`.

!!! warning "🐳 Da al contenedor más tiempo que el presupuesto"

    Docker da a un contenedor 10 segundos para detenerse, y luego lo mata: el presupuesto predeterminado de 8
    segundos encaja. Si aumentas `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`, da al contenedor al menos 2 segundos más; de
    lo contrario, Docker mata el servidor a los 10 segundos, sea cual sea su presupuesto.

    **En `docker-compose.yml`**, en el servicio `librefolio`, deja el resto como está y añade:

    ```yaml
    services:
      librefolio:
        stop_grace_period: 32s  # for LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=30
    ```

    Luego ejecuta `docker compose up -d`.

`./dev.py server` mantiene ese margen por sí mismo: después de un Ctrl+C espera hasta el presupuesto más 2 segundos y
luego termina el servidor ([Iniciar el servidor](cli_tools.md#start-the-server)).

---

## 🔗 Relacionado

- 📄 **[Configuración](configuration.md)** — Crear el archivo `.env`, opciones principales, parámetros establecidos por las herramientas, …
- 📄 **[Configuración: secretos y configuración de plugins](configuration_secrets.md)** — Secretos, configuración de plugins
- 📄 **[Configuración: cuentas y búsqueda de activos](configuration_accounts.md)** — Cuentas y registros, el orden de los proveedores de precios en la búsqueda, opcional: búsqueda web de nuevos activos
- 📄 **[Configuración global](settings.md#security-tab)** — La pestaña Seguridad
