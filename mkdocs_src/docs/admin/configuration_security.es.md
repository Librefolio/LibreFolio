# 🛡️ Configuración: comprobaciones y protecciones

Esta página cubre lo que LibreFolio comprueba en su configuración al arrancar, qué significa cada hallazgo
y qué hacer al respecto, las protecciones que pide al navegador (la **Content-Security-Policy** y
la protección de marcos), y cómo se detiene.

Las opciones que examinan estas comprobaciones se explican en [Configuración](configuration.md), la
primera página de la guía, y los secretos que mencionan en
[Configuración: secretos y configuración de plugins](configuration_secrets.md).

---

## 🩺 Comprobaciones al arrancar {: #startup-checks }

Justo después de su línea `Starting LibreFolio`, el servidor comprueba su configuración. No cambia nada:
cada hallazgo es una línea del registro, en su nivel, con el nombre de la comprobación en `check`, como
`platform.jwt_secret`.

Las mismas comprobaciones, bajo demanda, están en la pestaña **Seguridad** de **Configuración › Administración**, para
administradores: redactadas en el idioma de la aplicación, con errores y advertencias contabilizados mediante un número en la
pestaña, y se vuelven a consultar con **Comprobar de nuevo** una vez que hayas corregido la configuración y
reiniciado (véase «Seguridad» en [Configuración global](settings.md)).

| Nivel | El registro dice | Qué hacer |
| --- | --- | --- |
| ℹ️ `info` | `The session key is random: every restart signs everyone out. To stay signed in, set JWT_SECRET.` | Nada, si desconectar a todos en cada reinicio te parece bien. En caso contrario, véase [Mantener a los usuarios conectados](index.md#session-persistence). |
| ⚠️ `warning` | `The session signing key from JWT_SECRET is … characters long: use at least 32 random characters` (o `from JWT_SECRET_FILE (<path>)`) | Genera una clave más larga, como se explica en [Mantener a los usuarios conectados](index.md#session-persistence), y colócala donde indica la línea. |
| ⚠️ `warning` | `Set both directly and through a *_FILE variable: …` | Para cada secreto listado, conserva solo una de las dos: la variable en sí prevalece, el archivo se ignora. |
| ❌ `error` | `The instance key cannot be used: …`, terminando con `cannot be reached (Permission denied)` o `cannot be read (…)` | La carpeta `secrets/` o `instance.key` pertenece a otro usuario, o sus permisos dejan a LibreFolio fuera. Devuelve ambos al usuario que ejecuta LibreFolio (`chown`), luego `chmod 700` en la carpeta y `chmod 600` en el archivo. Nunca sustituyas la clave por una nueva. El servidor arranca de todos modos. |
| ❌ `error` | `The instance key cannot be used: …`, terminando con otro motivo, como `is empty or blank` | `instance.key` está dañada: restáurala desde una copia de seguridad, nunca la sustituyas por una clave nueva. El servidor arranca de todos modos. |
| ⚠️ `warning` | `… is open to other users (…): the folder should be 0700 and the file 0600` | Restringe sus permisos: `chmod 700` en la carpeta `secrets/`, `chmod 600` en `instance.key`. |
| ⚠️ `warning` | `SESSION_COOKIE_SECURE=never: the session cookie is sent over plain HTTP too; prefer auto` | Vuelve a `auto` salvo que realmente necesites `never`: véase [HTTPS y proxies inversos](configuration.md). |
| ℹ️ `info` | `The log level is DEBUG: the log records operational detail; …` (o `TRACE`) | Vuelve a `INFO` cuando termines de diagnosticar. |
| ❌ `error` | `LIBREFOLIO_TEST_MODE is on outside a test lane: test-only providers are served, the data are kept in the test data directory <path> and .env is not read; unset it on a production instance` (`check` es `platform.test_mode`) | El modo de prueba es para las propias ejecuciones de prueba de LibreFolio (`./dev.py test`, `./dev.py server --test`), que lo activan y desactivan por sí mismas: elimina `LIBREFOLIO_TEST_MODE` del entorno del servidor, o establécela en `0`, y luego reinicia: busca de dónde viene el entorno del servidor, como una unidad de servicio. Hasta entonces el servidor trabaja en la carpeta que indica la línea en lugar de tu [directorio de datos](filesystem.md): lo que se introduce mientras tanto se guarda allí, no con tus datos. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore uploads answer 503 until it is fixed` (`check` es `backup.upload_limit`) | Escribe un número entero de megabytes, `0` para indicar que no hay límite, o elimina la variable, y luego reinicia ([El límite de subida de una restauración](backup_restore.md#restore-upload-limit)). Hasta entonces Configuración › Administración › Copia de seguridad no puede subir un archivo para restaurarlo; la línea de comandos sigue restaurando uno. El servidor arranca de todos modos. |
| ❌ `error` | `LIBREFOLIO_BACKUP_MAX_RESTORE_MB cannot be used: expected a whole number of megabytes, 0 for no limit; restore checks answer 503 until it is fixed` (`check` es `backup.restore_limit`) | Escribe un número entero de megabytes, `0` para indicar que no hay límite, en la variable que indica la línea, o elimínala, y luego reinicia ([El límite de subida de una restauración](backup_restore.md#restore-upload-limit)). Hasta entonces toda comprobación de una restauración se rechaza con `backup_restore_unavailable`, desde Configuración › Administración › Copia de seguridad y desde la línea de comandos, donde `LIBREFOLIO_BACKUP_MAX_RESTORE_MB=0` delante de `backup restore` levanta el límite para ese comando. El servidor arranca de todos modos. |
| ❌ `error` | `LIBREFOLIO_BACKUP_RECIPIENTS: item 2 is not an age recipient: …; the hosting panel's backups answer 503 until it is fixed` (o `expected at most 2 recipients`, `repeats an earlier recipient`) (`check` es `backup.recipients`) | Escribe una o dos claves públicas `age1…`, separadas por comas, tal como las da `backup keygen`, y luego reinicia ([Copias de seguridad selladas](backup_sealed.md#sealed)). El servidor arranca de todos modos. |
| ⚠️ `warning` | `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance` (`check` es `accounts.login_limit`) | Nada, en una instancia dedicada a pruebas. En caso contrario, elimina la variable, o establécelaa en `on`, y luego reinicia: véase [Inicios de sesión fallidos](configuration_accounts.md#login-limit). |
| ❌ `error` | `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` (`check` es `email.smtp`) | El correo está desactivado, nada más lo está: corrige la variable que indica la línea y luego reinicia. Qué significa cada código: [Problemas de configuración](email_troubleshooting.md#configuration-problems). El servidor arranca de todos modos. |
| ⚠️ `warning` | `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | Configura `LIBREFOLIO_SMTP_TLS` como `starttls` o `tls`, o envía a través de un relay en tu propia red: véase [Notas de seguridad](email_troubleshooting.md#security). |
| ℹ️ `info` | `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` (`check` es `email.links`) | Nada, si ningún enlace tiene que salir por correo electrónico. En caso contrario, establece `LIBREFOLIO_PUBLIC_URL` en la dirección en la que tus usuarios abren LibreFolio ([Cuentas y registros](configuration_accounts.md#accounts)), y luego reinicia: véase [Correo electrónico](email.md). |
| ⚠️ `warning` | `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` (`check` es `email.links`) | Escribe la dirección con `http://` o `https://` y un nombre de host, sin nombre de usuario, contraseña, `?` ni `#`, como `https://librefolio.example.com`, y luego reinicia: véase [Correo electrónico](email.md). |
| ❌ `error` | `Stored plugin secrets that the instance key cannot read: <N>. Enter them again in the plugin settings, or restore the instance key they were saved with` (`check` es `platform.plugin_secrets`; esta llega más tarde en el arranque, una vez que la base de datos está lista) | La clave de instancia cambió después de que se guardaran estos [secretos de plugins](configuration_secrets.md#plugin-secrets) de toda la instancia: un `secrets/instance.key` perdido que LibreFolio sustituyó por uno nuevo, datos restaurados sin su `secrets/`, u otro `LIBREFOLIO_INSTANCE_KEY`. Si todavía tienes la clave antigua (tu copia de `secrets/instance.key`, respaldada con el directorio de datos como dice [La clave de instancia](configuration_secrets.md#instance-key), ya que un archivo claro de **Copia de seguridad de la instancia** deja fuera la clave, mientras que uno [seguro](backup_restore.md#secure) lleva la clave que generó LibreFolio y su restauración vuelve a cifrar estos secretos; o el valor antiguo de la variable), detén LibreFolio, colócala en lugar de la nueva y vuelve a arrancar. Hazlo antes de que nadie introduzca un secreto de nuevo: un secreto introducido de nuevo se guarda bajo la clave nueva, y se vuelve ilegible una vez que vuelve la antigua. Solo si la clave antigua se ha perdido, introduce los secretos de nuevo en **Configuración › Plugins**: a partir de entonces, la clave nueva es la que hay que respaldar. Si el registro también dice `The instance key cannot be used: …`, corrige eso primero: véase arriba. Los secretos personales no se cuentan: cada usuario ve los suyos en su propia pestaña. El servidor arranca de todos modos. |

Algunos de los secretos que hayas configurado detienen el arranque, en cambio, cuando no se pueden usar: un `JWT_SECRET_FILE` o un
`LIBREFOLIO_INSTANCE_KEY_FILE` que no puede dar su secreto (véase [Secretos en archivos](configuration_secrets.md#secret-files)),
o una clave de instancia propia de menos de 32 caracteres. El error está en la salida de consola del servidor
(`docker compose logs librefolio` con Docker): nombra la variable, y el archivo cuando existe, nunca el secreto. Corrígelo y vuelve a arrancar.

Lo mismo ocurre con un `LIBREFOLIO_LOGIN_LIMIT` distinto de `on` o `off`
([Inicios de sesión fallidos](configuration_accounts.md#login-limit)).

---

## 🛡️ Protecciones del navegador {: #browser-protections }

Todas las respuestas de LibreFolio llevan cabeceras que indican al navegador cómo proteger sus páginas. Tres
están siempre presentes, sin nada que configurar:

- `X-Content-Type-Options: nosniff`: el navegador usa el tipo que envía LibreFolio y nunca adivina
  otro, de modo que un archivo subido nunca se ejecuta como script ni se muestra como página.
- `Referrer-Policy: strict-origin-when-cross-origin`: otro sitio aprende como mucho la dirección de
  LibreFolio, como `https://librefolio.example.com`, nunca la página de la que vino una petición.
- Una `Content-Security-Policy` en cada página, en cada perfil, sin interruptor para desactivarla: véase
  [La Content-Security-Policy](#csp).

Otras dos son interruptores, cada uno configurado por separado, desactivados en una instalación propia:
[Protección de marcos](#frame-protection) y
[La política de solo informe](#csp-report-only). LibreFolio lee ambos al arrancar: reinícialo después de un cambio. Para
desarrolladores: [Cabeceras de respuesta](../developer/architecture/security.md#response-headers).

### 🛡️ La Content-Security-Policy {: #csp }

Una Content-Security-Policy indica al navegador qué puede ejecutar una página y a dónde puede conectarse.
LibreFolio **siempre aplica** una, en cada perfil: no hay ninguna opción de configuración para desactivarla. Se mantiene
lo más estrecha posible mientras LibreFolio funciona como siempre lo hizo, y se amplía solo donde LibreFolio
realmente lo necesita. No te pide nada en el caso habitual: solo importa cuando algo entre
LibreFolio y el navegador añade un script a la página ([Un script que no enviaste](#csp-blocked-script)).

| Qué | Política | Por qué |
|---|---|---|
| Cada página de LibreFolio: la aplicación web, la documentación (`/mkdocs`) y, donde están activas, las páginas propias de la API en `/api/v1/docs` y `/api/v1/redoc` | `object-src 'none'; base-uri 'self'; form-action 'self'` | Ningún contenido de plugin (`<object>`, `<embed>`); ningún elemento `<base>` que envíe los enlaces de la página a otro sitio; ningún formulario que envíe sus datos a otro sitio. LibreFolio no usa ninguno de ellos. Un PDF no es una página: no lleva nada de esto |
| Las páginas de la aplicación web | `script-src`: solo los scripts propios de LibreFolio. Sus scripts en línea se permiten por su hash, que LibreFolio calcula a partir de los archivos de la aplicación web, de modo que un script escrito en la página por cualquier otra persona no se ejecuta | Un script que LibreFolio no envió es la forma en que se secuestra una página |
| Las páginas de la aplicación web | `worker-src 'self' blob:` | Los workers del lector de PDF |
| Las páginas propias de la API en `/api/v1/docs` y `/api/v1/redoc`, solo donde `LIBREFOLIO_API_DOCS` está activo | `script-src 'self' https://cdn.jsdelivr.net`, `worker-src 'self' blob:`, `connect-src 'self'` | Las dos páginas son propias de LibreFolio, no de FastAPI: cargan Swagger UI y ReDoc desde `cdn.jsdelivr.net` en una versión exacta, y el navegador rechaza un archivo cuyo checksum (Subresource Integrity) no sea el que LibreFolio espera. Sus scripts de inicio vienen de tu instancia, así que las páginas no contienen script en línea, y no usan Google Fonts. El worker es la búsqueda de ReDoc. Donde las páginas están desactivadas, nada de esto existe |
| Los scripts de la compilación de la aplicación web, los archivos bajo `/_app/` | `script-src 'self'`, el mismo `connect-src` que las páginas, `worker-src 'self' blob:`, `object-src 'none'`, `base-uri 'self'` | Una política para el caso en que un navegador ejecute uno de estos archivos como **worker**: puede cargar los scripts propios de LibreFolio y nada más, y conectarse solo a donde pueden las páginas. Un navegador la ignora en cualquier script que no sea un worker. Hoy el único worker iniciado desde un archivo es el que procesa precios; el worker del lector de PDF se inicia desde un `blob:` y conserva la política de la página |
| Las páginas de la aplicación web | `connect-src 'self'`, el origen de [`LIBREFOLIO_PUBLIC_URL`](configuration_accounts.md#accounts) cuando está configurado, y `https://api.github.com` solo en una instalación autoalojada | A dónde puede enviar peticiones la página. La dirección pública es la que indicas a los usuarios de LibreFolio para acceder a él; GitHub es la comprobación de una versión más reciente, que tu navegador hace cuando un administrador inicia sesión (el perfil `managed` nunca la hace) |
| Cada respuesta, con [Protección de marcos](#frame-protection) activada | `frame-ancestors 'self'` | Solo las páginas propias de LibreFolio pueden mostrarlo en un marco |

**La vista previa de PDF no pide nada a terceros.** El motor del lector es una copia propia de LibreFolio, y `connect-src` se mantiene en la dirección propia de LibreFolio. Si no se puede acceder a esa copia, la vista previa muestra en su lugar el lector de PDF propio de tu navegador. El texto en chino, japonés y coreano es lo único que el lector descarga, y lo descarga de tu instancia, no de un tercero: cuando un PDF necesita una fuente así, la página se la pide a LibreFolio (`/api/v1/files/pdf-fonts/…`, solo para usuarios con sesión iniciada). La primera vez, **el servidor** descarga el archivo desde `cdn.jsdelivr.net` (una dirección fija, en una versión fija), lo conserva solo si su checksum (sha256) coincide con la lista que se distribuye con LibreFolio, y lo guarda en `cache/pdf-fonts/` dentro del [directorio de datos](filesystem.md). Es seguro eliminar esa carpeta: las fuentes se descargan de nuevo cuando un PDF las necesita, y no forma parte de una copia de seguridad. Una instancia que no puede acceder a `cdn.jsdelivr.net` muestra ese PDF sin esos caracteres; un archivo que no coincide con la lista se descarta, y el registro tiene una advertencia que lo nombra.

Lo que la política **no** impone: `default-src`, `style-src`, `img-src`, `font-src` y
`frame-src`. Las imágenes (los iconos de activos y brókers se establecen mediante un enlace a cualquier dirección), los estilos,
las fuentes y los marcos quedan libres; si otra página puede mostrar LibreFolio en un marco lo decide solo
`LIBREFOLIO_FRAME_PROTECTION`, ya que mostrar LibreFolio dentro de un panel es un uso legítimo
de una instalación propia.

Nada cambia para lo que hace LibreFolio por sí mismo. Cuando recompilas la aplicación web desde las fuentes
mientras LibreFolio se ejecuta, los hashes siguen la nueva compilación: no necesitas reiniciarlo.

#### 🕵️ Un script que no enviaste {: #csp-blocked-script }

Un proxy, una CDN o una extensión del navegador que **añada un script** a las páginas de LibreFolio se bloquea, como
cualquier otra cosa que LibreFolio no envió. Casos típicos:

- el **Rocket Loader** de Cloudflare, su **Email Address Obfuscation** y la configuración automática de sus
  **Web Analytics**, que reescriben la página o le añaden un script a su paso;
- un `sub_filter` de Nginx que escribe un `<script>` en las páginas;
- una extensión del navegador que añade un script propio a cada página.

Lo que ves:

- la página funciona, pero puede perder la pieza que aportaba ese script: un contador, una dirección ofuscada, un
  widget de la extensión;
- la consola del navegador muestra, una vez por carga de página, `LibreFolio blocked a script it did not send
  (<source>): a proxy, a CDN or a browser extension adds it. Guide:
  https://<your address>/mkdocs/admin/configuration_security/#csp`, donde `<source>` es la dirección de la que vino el script,
  o `inline` para un script escrito en la página;
- en la pestaña [Seguridad](settings.md) de **Configuración › Administración**, el navegador
  en el que se encontró muestra una advertencia, *se bloqueó un script*, que nombra las fuentes. La advertencia pertenece a esa
  pestaña del navegador, y desaparece cuando se cierra la pestaña.

Nada se envía a tu servidor: ni informe, ni petición. La consola y la pestaña son los únicos
lugares donde el navegador lo dice.

Qué hacer: **desactiva la adición para la dirección de LibreFolio**. La política no se amplía mediante una
opción de configuración, porque un script añadido por el camino es exactamente lo que esta política pretende detener.

- **Cloudflare**: para el nombre de host de LibreFolio, desactiva Rocket Loader (*Speed › Optimization*), Email
  Address Obfuscation (*Scrape Shield*) y la configuración automática de Web Analytics (*Analytics & Logs ›
  Web Analytics*). Una *Configuration Rule* puede hacerlo solo para ese host y dejar tus otros sitios como
  están. Los nombres de los menús cambian de vez en cuando.
- **Nginx**: elimina el `sub_filter` que añade el script en el bloque `server` o `location` que
  hace de proxy de LibreFolio.
- **Una extensión del navegador**: desactívala para la dirección de LibreFolio, o prueba la página en una ventana privada,
  que normalmente se ejecuta sin extensiones.

Luego recarga la página: la línea ha desaparecido de la consola. La advertencia de la pestaña Seguridad permanece hasta
que cierres esa pestaña del navegador.

#### 🔗 Una dirección pública que no se puede usar {: #csp-public-url }

`LIBREFOLIO_PUBLIC_URL` añade su origen (`scheme://host`, con el puerto solo cuando no es el
predeterminado) a `connect-src`. Un valor que no se puede usar, como uno sin `http://` o
`https://`, o con un nombre de usuario o una contraseña, no añade nada: el servidor arranca y sirve como de costumbre,
y el registro tiene una advertencia, *LIBREFOLIO_PUBLIC_URL cannot be used*. Corrige el valor y luego reinicia: véase
[Cuentas y registros](configuration_accounts.md#accounts).

#### 📡 La comprobación de dirección de un enlace para compartir {: #csp-address-check }

La comprobación de la **Dirección del servidor** en los diálogos de invitación y restablecimiento de contraseña de la
pestaña [Usuarios](users.md#server-address) ya no pide datos a la dirección: la política se lo impediría a la
página. Carga una imagen diminuta y transparente desde la dirección que escribiste,
`/api/v1/auth/address-probe.png`, que la política permite, y lee su tamaño: un tamaño dice que
**esta** instancia responde ahí, otro dice que responde otra cosa. Lo que dicen los mensajes es
lo mismo que antes.

### 🖼️ Protección de marcos {: #frame-protection }

`LIBREFOLIO_FRAME_PROTECTION` decide si una página en otra dirección puede mostrar LibreFolio en un
marco. Otra dirección es otro nombre de host, o el mismo en otro puerto: un panel de Home Assistant
en `http://homeassistant.local:8123` que muestra LibreFolio desde
`http://homeassistant.local:6040` es una página en otra dirección.

- **Desactivada** (`false`), el valor predeterminado en una instalación propia: cualquier página puede mostrar LibreFolio en un marco.
- **Activada** (`true`): solo las páginas propias de LibreFolio pueden mostrarlo en
  un marco. En cualquier otro sitio, el navegador se niega a mostrarlo.

Con el interruptor activado:

- cada respuesta lleva `X-Frame-Options: SAMEORIGIN` y
  `Content-Security-Policy: frame-ancestors 'self'`, la misma regla en la cabecera antigua y en la
  nueva;
- el mismo campo `Content-Security-Policy` también lleva las tres reglas que
  [LibreFolio aplica en sus páginas](#csp) en todos los perfiles: `object-src 'none'`,
  `base-uri 'self'` y `form-action 'self'`. No dependen de este interruptor. Un PDF conserva
  solo `frame-ancestors 'self'`, de modo que el navegador aún puede mostrarlo;
- una respuesta `304 Not Modified` solo recibe `X-Frame-Options`, para que el navegador conserve la política de
  la copia que ya tiene.

Cuándo cambiarlo:

- **En una instalación propia**, déjalo desactivado si alguna página tuya muestra LibreFolio en un marco, como
  un panel de Home Assistant: con el interruptor activado, el navegador se negaría a mostrar LibreFolio
  ahí. Si ninguna página tuya lo hace, puedes activarlo, para que ningún otro sitio pueda mostrar LibreFolio
  dentro de sus propias páginas.

Es la comprobación `platform.frame_protection` de las [comprobaciones al arrancar](#startup-checks), también en la
pestaña [Seguridad](settings.md) de **Configuración › Administración**:

- La comprobación pasa, y el registro no dice nada al respecto. La pestaña la incluye entre las
  [comprobaciones superadas](settings.md): *Solo las páginas propias de LibreFolio pueden mostrarlo en un
  marco.* con el interruptor activado, *Las páginas en otra dirección, como tus paneles, pueden mostrar
  LibreFolio en un marco: el valor predeterminado de una instalación propia.* con el interruptor desactivado en una instalación
  propia.

### 📋 La política de solo informe {: #csp-report-only }

La [Content-Security-Policy](#csp) que aplica LibreFolio es estrecha a propósito: deja libres las imágenes,
los estilos, las fuentes y los marcos. `LIBREFOLIO_CSP_REPORT_ONLY` añade una segunda política, **más amplia**, a las
páginas de la aplicación web: la política completa a la que aspira LibreFolio, que también dice de dónde puede cargar una página
sus imágenes, estilos, fuentes y marcos. Es de solo informe: el navegador la comprueba y no bloquea
nada. Enumera lo que queda fuera de ella en su consola de desarrollador, y en ningún otro lugar, ya que la política
no nombra ninguna dirección a la que enviar un informe. La política aplicada está activa independientemente de lo que diga este interruptor.

- **Desactivada** (`false`), el valor predeterminado en una instalación propia.
- **Activada** (`true`).

Con el interruptor activado:

- las páginas de la aplicación web llevan una cabecera `Content-Security-Policy-Report-Only`. La documentación
  (`/mkdocs`), todo lo que hay bajo `/api/`, incluidas las páginas de documentación de la API, y los archivos que
  cargan las páginas no la llevan, ni tampoco una respuesta `304 Not Modified`;
- la política permite lo que viene de la dirección propia de LibreFolio, y unas pocas excepciones que la aplicación necesita,
  como imágenes de cualquier dirección `https://` (los iconos de activos y brókers se establecen mediante un enlace),
  estilos en línea y el WebAssembly del lector de PDF. Para desarrolladores, la política completa, directiva
  por directiva:
  [La Content-Security-Policy y la protección de marcos](../developer/architecture/security.md#managed-headers);
- los scripts en línea propios de la aplicación web se permiten por sus hashes, igual que en la política aplicada,
  que siguen los archivos de la aplicación web: después de recompilar la aplicación web desde las fuentes, no necesitas
  reiniciar LibreFolio;
- cada línea que esta política añade a la consola dice lo que habría bloqueado: no bloqueó nada. Un script
  que bloquea la política aplicada es otra cosa, y tiene su propia línea: véase
  [Un script que no enviaste](#csp-blocked-script).

Cuándo cambiarlo:

- **En una instalación propia**, no hay necesidad de activarlo: tus usuarios no ven ninguna diferencia
  en ninguno de los dos casos. Actívalo si quieres ver, en la consola de desarrollador del navegador, qué bloquearía una política así
  en tu instancia.

Es la comprobación `platform.csp_report_only` de las [comprobaciones al arrancar](#startup-checks), también en la
pestaña [Seguridad](settings.md) de **Configuración › Administración**:

- La comprobación pasa, y el registro no dice nada al respecto. La pestaña la incluye entre las
  [comprobaciones superadas](settings.md): una línea que dice que las páginas de la aplicación web llevan una
  política de solo informe, con el interruptor activado, *Sin Content-Security-Policy de solo informe: el valor predeterminado
  de una instalación propia.* con el interruptor desactivado en una instalación propia.

---

## ⏹️ Detener el servidor {: #shutdown }

Cuando se pide al servidor que se detenga, debe hacerlo dentro de un límite de tiempo, el **presupuesto de apagado**:
8 segundos salvo que lo cambies, contados desde la señal (SIGTERM de `docker stop`,
`docker compose down` o un reinicio; SIGINT de Ctrl+C). La mayoría de las veces los usuarios no notan nada,
salvo reinicios más rápidos y limpios.

| Variable | Predeterminado | Qué hace |
| --- | --- | --- |
| `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS` | `8` | El presupuesto de apagado, en segundos: un número entero de `2` a `600`, o `0` para indicar que no hay límite, como antes de la versión 1.3. Un valor que no se puede usar no detiene el servidor, a diferencia de las [opciones principales](configuration.md): el registro dice `Shutdown budget setting cannot be used: the default applies`, y el presupuesto se queda en 8 segundos. |
| `UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN` | 3/8 del presupuesto | Cuántos segundos espera uvicorn, el servidor web, a las peticiones en curso: `3` con el presupuesto predeterminado. La imagen de Docker y `./dev.py server` lo calculan a partir del presupuesto. Un valor que establezcas tú mismo prevalece: mantenlo por debajo del presupuesto, que sigue contando para la detención completa. |

El presupuesto se gasta en este orden:

1. **Peticiones en curso**: el servidor web no acepta nuevas y da a las que ya se están ejecutando 3/8 del
   presupuesto, 3 segundos por defecto. Luego cancela las que siguen ejecutándose, como una importación larga de bróker:
   lo que no habían guardado aún se revierte, así que simplemente se pueden repetir una vez que
   LibreFolio vuelva.
2. **El trabajo propio del servidor**: las sincronizaciones programadas, los procesos worker, las cachés… se detienen uno tras
   otro, cada uno dentro del tiempo restante. El último paso termina los procesos hijos que aún se ejecutan
   (importaciones de bróker, simulaciones de riesgo, Herramientas), de modo que ninguno sobrevive al servidor.
3. **Cuando se agota el presupuesto**: si algo todavía retiene el servidor, termina de todos modos, con estado de salida
   1, y su registro dice qué seguía ejecutándose: `Shutdown budget exhausted: ending the process`.

!!! warning "🐳 Da al contenedor más tiempo que el presupuesto"

    Docker da a un contenedor 10 segundos para detenerse por defecto, y luego lo mata: el presupuesto predeterminado de
    8 segundos encaja. Si aumentas `LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`, da al contenedor al menos
    2 segundos más: establece `stop_grace_period` en el servicio `librefolio` de `docker-compose.yml`, deja
    el resto del servicio como está, y luego ejecuta `docker compose up -d`.

    ```yaml
    services:
      librefolio:
        stop_grace_period: 32s  # for LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=30
    ```

    De lo contrario, Docker mata el servidor después de 10 segundos, sea cual sea su presupuesto.

`./dev.py server` mantiene ese margen por sí mismo: después de un Ctrl+C espera hasta el presupuesto más 2 segundos
para esta detención, y luego termina el servidor ([Iniciar el servidor](cli_tools.md#start-the-server)).

---

## 🔗 Relacionado

- 📄 **[Configuración](configuration.md)** — Crear el archivo `.env`, opciones principales, parámetros establecidos por las herramientas, …
- 📄 **[Configuración: secretos y configuración de plugins](configuration_secrets.md)** — Secretos, configuración de plugins
- 📄 **[Configuración: cuentas y búsqueda de activos](configuration_accounts.md)** — Cuentas y registros, el orden de los proveedores de precios en la búsqueda, opcional: búsqueda web de nuevos activos
