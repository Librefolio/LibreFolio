# 📝 Configuración

Las opciones de arranque están en un archivo `.env`: puertos, la carpeta de datos, el registro, las sesiones de inicio de sesión, las altas, los secretos y algunas funciones opcionales. Se encuentra en la raíz del proyecto o junto a `docker-compose.yml` con Docker. Las opciones que cambias desde dentro de la aplicación son, en cambio, [Configuración global](settings.md).

Esta página es el inicio de la guía de configuración: cómo crear el archivo `.env`, las **opciones principales** con sus valores predeterminados y qué valor prevalece cuando la misma opción se establece en varios lugares.

!!! info "📚 Esta guía se reparte en varias páginas"

    El resto de la guía entra en más detalle, una vez que los conceptos básicos de esta página están claros:

    - [Configuración: Secretos y configuración de plugins](configuration_secrets.md): las opciones que son secretas, cómo leerlas desde archivos, la clave de instancia y la configuración de los plugins.
    - [Configuración: Comprobaciones y protecciones](configuration_security.md): lo que LibreFolio comprueba al arrancar, las protecciones del navegador (Content-Security-Policy, protección de marcos) y cómo se detiene.
    - [Configuración: Cuentas y búsqueda de activos](configuration_accounts.md): quién puede registrarse, el límite de inicios de sesión fallidos, el administrador inicial, el orden de los proveedores de precios en la búsqueda y la búsqueda web.

---

## 🔧 Crear el archivo `.env`

En la carpeta del proyecto, copia el archivo de ejemplo y luego edita los valores que necesites:

```bash
cp .env.example .env
```

Con la imagen de Docker precompilada, la guía de [instalación con Docker](../user/installation.md) descarga la misma muestra como `.env`.

- La muestra agrupa las opciones según lo que hacen. Una opción comentada, como `# SESSION_COOKIE_SECURE=auto`, muestra su valor predeterminado: elimina el `#` solo para cambiar el valor.
- LibreFolio lee `.env` al arrancar: reinicia LibreFolio después de un cambio. Con Docker Compose, ejecuta `docker compose up -d`, porque `docker compose restart` conserva los valores antiguos.
- Los nombres distinguen entre mayúsculas y minúsculas. En las opciones principales y las opciones de configuración de riesgo que aparecen más abajo, un valor del tipo incorrecto o fuera de rango detiene el servidor al arrancar con un error.

---

## ✏️ Opciones principales {: #main-options }

| Variable | Valor predeterminado | Qué hace |
| --- | --- | --- |
| `PORT` | `6040` | Puerto del servidor web. Con Docker Compose, el puerto que se abre en el host (el contenedor siempre escucha en `6040`). |
| `TEST_PORT` | `6041` | Puerto del servidor de pruebas (`./dev.py server --test`). |
| `LIBREFOLIO_DATA_DIR` | `./backend/data/prod` | Carpeta de la base de datos, las subidas, los informes de brókeres y los registros; una ruta relativa parte de la carpeta del proyecto. Docker la fija en `/app/backend/data/prod-docker`: para mover los datos en el host, cambia el lado izquierdo del volumen `./LibreFolio-data` en `docker-compose.yml`. |
| `LOG_LEVEL` | `INFO` | Cuánto registra el servidor: `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR` o `CRITICAL`. En `DEBUG` o `TRACE`, la aplicación web también escribe en la consola del navegador cada llamada fallida al servidor, incluidas las rechazadas (una respuesta `4xx`); en los demás niveles, solo los errores del servidor, las llamadas que no obtuvieron respuesta y las respuestas que no puede leer. |
| `JWT_SECRET` | _sin establecer_ | Clave que firma las sesiones de inicio de sesión. Sin establecer, vacía o solo con espacios: se genera una clave nueva en cada arranque, así que todos vuelven a iniciar sesión tras un reinicio. `JWT_SECRET_FILE` la lee desde un archivo en su lugar: consulta [Secretos](configuration_secrets.md#secrets). Consulta [Mantener a los usuarios con la sesión iniciada](index.md#session-persistence). |
| `SESSION_COOKIE_SECURE` | `auto` | Cuándo se envía la cookie de la sesión de inicio de sesión solo por HTTPS: `auto` (si el navegador usa HTTPS), `always` o `never`. Consulta [HTTPS y proxies inversos](#session-cookie-secure). |
| `LIBREFOLIO_CLIENT_IP_HEADER` | _sin establecer_ | Detrás de un proxy inverso, el encabezado en el que transmite la dirección del visitante, como `Fly-Client-IP` en Fly.io: establécelo solo si todas las solicitudes atraviesan ese proxy. Consulta [La dirección del visitante](connection_proxy.md#client-address). |
| `PREVIEW_CACHE_MAX_MB` | `50` | Memoria, en MB, de la caché de vistas previas de imágenes en cada proceso del servidor. |
| `LIBREFOLIO_FRAME_PROTECTION` | `false` | Déjala sin establecer en una instalación autoalojada: los paneles en otra dirección, como los paneles de Home Assistant, pueden entonces mostrar LibreFolio en un marco. `true` permite que solo las páginas propias de LibreFolio lo muestren en un marco, con `X-Frame-Options: SAMEORIGIN` y `Content-Security-Policy: frame-ancestors 'self'`, en cada respuesta. Las tres reglas `object-src 'none'; base-uri 'self'; form-action 'self'` no dependen de ella: las páginas de LibreFolio siempre las incluyen ([La Content-Security-Policy](configuration_security.md#csp)). `true` o `false`; `1`/`0`, `yes`/`no` y `on`/`off` también funcionan, sin distinguir mayúsculas de minúsculas; cualquier otro valor detiene el servidor al arrancar. Consulta [Protección de marcos](configuration_security.md#frame-protection). |
| `LIBREFOLIO_CSP_REPORT_ONLY` | `false` | Déjala sin establecer en una instalación autoalojada. `true` añade una segunda Content-Security-Policy, más amplia, a las páginas de la aplicación web, no a la documentación ni a la API, en modo de solo informe: no bloquea nada, y el navegador enumera en su consola de desarrollador lo que esa política más amplia bloquearía, sin enviar ningún informe a ninguna parte. La [Content-Security-Policy](configuration_security.md#csp) aplicada siempre está activa, con o sin ella. Los mismos valores que `LIBREFOLIO_FRAME_PROTECTION`. Consulta [La política de solo informe](configuration_security.md#csp-report-only). |
| `LIBREFOLIO_API_DOCS` | `false` | Déjala sin establecer. `true` sirve las páginas de documentación propias de la API, Swagger UI en `/api/v1/docs` y ReDoc en `/api/v1/redoc`, con el esquema de la API en `/api/v1/openapi.json`. Desactivada la opción, esas páginas responden `404`, en todos los perfiles y también con Docker: una instancia en uso no publica ningún mapa de su API. Un navegador que abre una de estas direcciones, o cualquier otra dirección bajo `/api/`, o una página de documentación que no existe bajo `/mkdocs/`, se redirige a la aplicación (`/`); un programa que llama a la API sigue recibiendo `404` con `{"detail": "Not Found"}`. En la aplicación web, una página que no existe te devuelve a la página de la que venías, o al Panel. Es una herramienta para desarrolladores, así que `./dev.py server --debug` la activa, y las propias ejecuciones de prueba de LibreFolio la tienen activada. `true` o `false`; `1` y `0` también funcionan. La política propia de las páginas está en [La Content-Security-Policy](configuration_security.md#csp). |
| `LIBREFOLIO_SUPPORT_URL` | _sin establecer_ | Dónde piden ayuda los usuarios de la instancia, por ejemplo, con un activo que la búsqueda no encuentra ([Avísanos](../user/assets/create-edit.md#let-us-know), bajo los resultados de la búsqueda): una página con `http://` o `https://`, o una dirección de correo como `mailto:help@example.org`. Con una dirección de correo, la aplicación de correo del usuario abre un mensaje con los detalles de la búsqueda; con una página, la página se abre en una pestaña nueva y recibe el informe en su dirección, como los parámetros de consulta `title` y `body`, igual que una incidencia de GitHub prerrellenada, de modo que un formulario de soporte pueda rellenarse solo, y los detalles también se copian, para pegarlos allí. Sin establecer: en una instalación autoalojada (el perfil `selfhosted`), se abre una nueva incidencia pública en GitHub de LibreFolio con los detalles, para que el usuario la revise antes de enviarla. Cualquier otro valor se ignora, como si no estuviera establecido, y el servidor lo registra una vez. Una página cuya dirección contenga un nombre de usuario o una contraseña también cuenta como no establecida. La dirección es pública: cualquiera que pueda acceder al servidor puede leerla en `/api/v1/system/instance`. |
| `LIBREFOLIO_TOS_URL` | _sin establecer_ | Los términos de servicio de la instancia: una página con `http://` o `https://`. El aviso legal que ve cada usuario, en Configuración › Acerca de, en la página de bienvenida, bajo la tarjeta de cada página de inicio de sesión y al pie de la barra lateral, lo enlaza como **Términos de servicio**, abierto en una pestaña nueva. Sin establecer: sin enlace, solo el aviso. A diferencia de `LIBREFOLIO_SUPPORT_URL`, no se admite `mailto:`. Un valor que LibreFolio no pueda usar, incluida una dirección con un nombre de usuario o una contraseña, no detiene el servidor: el enlace permanece oculto y el registro contiene un error (consulta más abajo). La dirección es pública: cualquiera que pueda acceder al servidor puede leerla en `/api/v1/system/instance`. |
| `LIBREFOLIO_PRIVACY_URL` | _sin establecer_ | La política de privacidad de la instancia, enlazada como **Política de privacidad** junto a los términos de servicio: las mismas reglas que `LIBREFOLIO_TOS_URL`. |
| `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` | _sin establecer_ | Déjala sin establecer. El mayor archivo que un administrador puede subir para comprobarlo con vistas a una restauración, en megabytes; `0` significa sin límite. Sin establecer: sin límite. Un valor que no sea un número entero no detiene el servidor: las solicitudes de subida responden `503`, y el registro contiene un error, ya desde el inicio ([Comprobaciones de arranque](configuration_security.md#startup-checks)) y luego cada vez que se lee el límite. Se lee solo del entorno. Consulta [El límite de subida de una restauración](backup_restore.md#restore-upload-limit). |
| `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` | _sin establecer_ | Déjala sin establecer. El mayor tamaño al que un archivo puede descomprimirse mientras se comprueba para una restauración, en megabytes, según los tamaños que declara su manifiesto; `0` significa sin límite. Sin establecer: sin límite. Un valor que establezcas siempre prevalece, `0` incluido, y `backup restore` en la línea de comandos también lo respeta. Un archivo que supere el límite se rechaza antes de descomprimir nada (`unpacked_too_large`). Un valor que no sea un número entero no detiene el servidor: las comprobaciones de una restauración responden `503` (`backup_restore_unavailable`), el registro contiene un error, ya desde el inicio ([Comprobaciones de arranque](configuration_security.md#startup-checks)) y luego en cada comprobación, y la pestaña **Seguridad** de Configuración › Administración lo notifica (`backup.restore_limit`). Se lee solo del entorno. Consulta [El límite de subida de una restauración](backup_restore.md#restore-upload-limit). |
| `LIBREFOLIO_BACKUP_RECIPIENTS` | _sin establecer_ | Una o dos claves públicas de age (`age1…`, tal como las imprimen `backup keygen` o `age-keygen`), separadas por comas: dos solo mientras se cambia una clave. No es un secreto. Si se establece, `backup create --sealed` crea una copia de seguridad [sellada](backup_sealed.md#sealed): un `.tar` cuya contraseña solo pueden abrir las claves privadas correspondientes, nunca con la clave de instancia. Un valor que LibreFolio no pueda usar (una clave que no sea `age1…`, más de dos, la misma dos veces) no detiene el servidor: el registro contiene un error, y la pestaña **Seguridad** de Configuración › Administración lo notifica (`backup.recipients`). Se lee solo del entorno. |
| `LIBREFOLIO_STORAGE_LIMIT_MB` | _sin establecer_ | Déjala sin establecer en una instalación autoalojada: tú estableces el límite en la barra de espacio de la página **Archivos**. El espacio que puede ocupar la instancia, en megabytes; `0` significa sin límite. Si se establece, prevalece sobre la opción de configuración **Límite de espacio (MB)**, sea cual sea el valor que un administrador haya guardado antes, y lo bloquea: el campo de la barra de espacio aparece atenuado y se rechaza el guardado. Sin establecer: la configuración decide, `0` hasta que un administrador guarde otro valor. Un valor que no sea un número entero se ignora, y la configuración decide. Más allá, LibreFolio rechaza un archivo subido, un informe del bróker, una copia de seguridad iniciada a mano y una restauración que llevaría los datos más allá, y no elimina nada; como el administrador no puede subirlo aquí, el mensaje pide hacerlo a quien aloja la instancia. Se lee solo del entorno. Consulta [La barra de espacio](backup_restore.md#space-used). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | La primera pausa de un proveedor de precios que responde «demasiadas solicitudes» (HTTP 429): ninguna solicitud llega a él hasta que termina la pausa, y cada rechazo consecutivo duplica la siguiente pausa. Un número entero de segundos de `0` a `86400`; `0` desactiva las pausas, como antes de la versión 1.3. Activada de forma predeterminada, por decisión del desarrollador 34: una excepción a la regla de que una opción nueva deja una instalación como estaba. Un valor que no se pueda usar tampoco detiene el servidor: el registro contiene un error, y se aplican ambos valores predeterminados. Consulta [Pausas de proveedores](settings.md#provider-pauses). |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | La pausa más larga que alcanza la duplicación: un número entero de segundos de `1` a `86400`, no inferior a la primera pausa mientras las pausas estén activadas. El `Retry-After` de un proveedor aún puede pedir más, hasta un día. Un valor que no se pueda usar tampoco detiene el servidor: el registro contiene un error, y se aplican ambos valores predeterminados. Consulta [Pausas de proveedores](settings.md#provider-pauses). |
| `LIBREFOLIO_PROBE_RATE_LIMIT` | `30` | Cuántas veces por minuto puede un usuario probar la configuración de un proveedor de precios (**Probar configuración** en el formulario de activo; **Preguntar al proveedor** también cuenta), lo que puede implicar una llamada al proveedor; superado ese límite, el formulario indica al usuario cuándo volver a intentarlo. Un número entero de `0` a `10000`; `0` desactiva el límite, solo para una instancia de pruebas (lo hace `./dev.py server --test`), y el registro contiene una advertencia en cada arranque. Se lee en cada prueba: un cambio se aplica sin reiniciar. Un valor que no se pueda usar no detiene el servidor: el registro contiene un error, y se aplica `30`. |
| `LIBREFOLIO_BRIM_PREWARM` | `false` (`true` en modo de prueba) | Opcional. `true` hace que los workers de importación de brókeres estén listos al arrancar, con los plugins de importación cargados: la primera importación de bróker tras un arranque es entonces unos 4 segundos más rápida, a cambio de unos 80 MB de memoria retenidos desde el inicio y unos 1,4 segundos de CPU en cada arranque. Desactivada de forma predeterminada, por decisión N56: en una máquina pequeña en la nube, esa memoria y esa CPU cuestan más que los segundos que ahorran. `true` o `false`; `1`/`0`, `yes`/`no` y `on`/`off` también funcionan, sin distinguir mayúsculas de minúsculas. Cualquier otro valor no detiene el servidor, a diferencia de las opciones principales: el registro contiene una advertencia al arrancar, y permanece desactivada. Consulta [Arquitectura de BRIM → Precarga y calentamiento](../developer/backend/brim/architecture.md#parse-pool-warm-up). |
| `LIBREFOLIO_SMTP_HOST` | _sin establecer_: correo desactivado | Opcional. El servidor SMTP que envía los correos de LibreFolio, como `smtp.example.com`. Consulta [Correo electrónico](email.md#variables). |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | Cómo se cifra la conexión con el servidor SMTP: `starttls`, `tls` o `none`. Consulta [Modos de cifrado](email.md#encryption-modes). |
| `LIBREFOLIO_SMTP_PORT` | `587` con `starttls`, `465` con `tls`, `25` con `none` | El puerto del servidor SMTP, solo cuando no es el habitual de su modo de cifrado. Consulta [Correo electrónico](email.md#variables). |
| `LIBREFOLIO_SMTP_USER` | _sin establecer_: sin inicio de sesión | El inicio de sesión en el servidor SMTP, establecido junto con `LIBREFOLIO_SMTP_PASSWORD` ([Secretos](configuration_secrets.md#secrets)). Consulta [Correo electrónico](email.md#variables). |
| `LIBREFOLIO_SMTP_FROM` | _sin establecer_ | El remitente de los correos, obligatorio en cuanto se establece un servidor. Consulta [Correo electrónico](email.md#variables). |
| `LIBREFOLIO_SMTP_REPLY_TO` | _sin establecer_: las respuestas van al remitente | Adónde van las respuestas a los correos de LibreFolio. Consulta [Correo electrónico](email.md#variables). |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | `50` | Cuántos correos puede enviar la instancia en una hora, por proceso del servidor. Consulta [Correo electrónico](email.md#variables). |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | `20` | Cuántos correos de registro puede activar una dirección de cliente en una hora, por proceso del servidor: un número entero, como mínimo 1. Un mismo recuento para los registros, **Enviar el enlace de nuevo** y **¿Olvidaste tu contraseña?**. Superado ese límite, se crea una cuenta nueva y queda en espera, y su correo se retiene. Consulta [Límites de los correos de activación y restablecimiento de contraseña](email_flows.md#activation-limits). |

Un valor que LibreFolio no pueda usar en `LIBREFOLIO_TOS_URL` o `LIBREFOLIO_PRIVACY_URL` nunca detiene el servidor: ese enlace permanece oculto y el aviso legal se muestra sin él. La primera vez que cada proceso del servidor responde a `/api/v1/system/instance`, que la aplicación lee en cuanto se abre, el registro contiene un error, `Invalid instance link`, con la variable y su valor en `problem` (un valor que contenga una `@` no se muestra: puede llevar un nombre de usuario o una contraseña), y en `consequence` lo que cuesta hasta que lo corrijas, por ejemplo `the terms of service link stays hidden until it is fixed: the legal notice shows without it`. Corrige el valor y reinicia. Un `LIBREFOLIO_SUPPORT_URL` que no se pueda usar registra el mismo error, con su propio `consequence`.

Los archivos `.env` más antiguos pueden seguir conteniendo `PORTFOLIO_BASE_CURRENCY`: LibreFolio lo ignora, y los usuarios nuevos parten de la **Divisa predeterminada** en [Configuración global](settings.md).

??? info "🔒 HTTPS y proxies inversos — la cookie de sesión"

    `SESSION_COOKIE_SECURE` decide cuándo la cookie que mantiene a los usuarios con la sesión iniciada es `Secure`: el navegador la envía entonces solo por HTTPS, de modo que la sesión nunca viaja por una conexión sin cifrar. No importan las mayúsculas ni los espacios alrededor del valor; cualquier otro valor detiene el servidor al arrancar con un error.
    {: #session-cookie-secure }

    - **`auto`** (predeterminado): `Secure` cuando el navegador llegó a LibreFolio por HTTPS. LibreFolio sirve HTTP sin cifrar, así que HTTPS proviene de un proxy inverso delante de él, que lo indica con el encabezado `X-Forwarded-Proto: https`; solo cuenta su primer valor. No hay ninguna lista de proxies de confianza que configurar: el encabezado solo puede activar `Secure`, nunca desactivarlo. Por HTTP sin cifrar, como `http://localhost:6040`, una IP de LAN o la IP de Tailscale de los niveles 1 y 2 en [Exponer de forma segura](service_exposure.md), la cookie no es `Secure`, así que el inicio de sesión sigue funcionando.
    - **`always`**: siempre `Secure`, para una instalación a la que se accede solo por HTTPS. Por HTTP sin cifrar, el navegador descarta la cookie, así que el inicio de sesión no persiste: la siguiente página devuelve al usuario a la página de inicio de sesión.
    - **`never`**: nunca `Secure`. Es la salida cuando un proxy envía `X-Forwarded-Proto: https` a un navegador que en realidad usa HTTP sin cifrar, como Nginx con un `proxy_set_header X-Forwarded-Proto https;` codificado de forma fija en un bloque `server` de HTTP sin cifrar: con `auto`, ese navegador sería devuelto a la página de inicio de sesión después de cada inicio de sesión. Es mejor corregir el proxy (`$scheme` en lugar de `https`); `never` es el fallback.

    Detrás de un proxy inverso HTTPS, `auto` se basa en su encabezado `X-Forwarded-Proto`:

    - **Tailscale Serve y Funnel** (niveles 3 y 4 en [Exponer de forma segura](service_exposure.md)), **Caddy** y **Traefik** lo envían por su cuenta: no hay nada que configurar.
    - **Nginx** no lo hace: añade `proxy_set_header X-Forwarded-Proto $scheme;` al `location` que hace de proxy de LibreFolio.
    - **Cualquier otro proxy**: haz que envíe el encabezado o, si solo se puede acceder a LibreFolio a través de él, establece `SESSION_COOKIE_SECURE=always`.

    Para comprobar en tu navegador si la cookie de sesión está marcada como `Secure`, consulta [Comprobar la seguridad de la conexión](connection_checks.md#session-cookie).

??? info "🧮 Workers del motor de riesgo — configuración avanzada"

    Las simulaciones de riesgo y las optimizaciones de cartera se ejecutan en procesos worker separados, que se inician en el primer uso. Los valores predeterminados son adecuados para la mayoría de las instalaciones: añade una variable a `.env` solo para cambiarlos.

    | Variable | Valor predeterminado | Qué hace |
    | --- | --- | --- |
    | `RISK_SIMULATION_WORKERS`, `RISK_OPTIMIZATION_WORKERS` | `1` (1–8) | Procesos worker por tipo de tarea: cuantos más, más tareas se ejecutan a la vez. |
    | `RISK_SIMULATION_QUEUE_CAPACITY`, `RISK_OPTIMIZATION_QUEUE_CAPACITY` | `2` (0–64) | Tareas que pueden esperar a un worker; más allá de eso, las nuevas solicitudes se rechazan. |
    | `RISK_SIMULATION_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_TIMEOUT_SECONDS` | `120` / `60` | Límite de tiempo de una tarea, en segundos. |
    | `RISK_SIMULATION_IDLE_TIMEOUT_SECONDS`, `RISK_OPTIMIZATION_IDLE_TIMEOUT_SECONDS` | `600` | Los workers inactivos se detienen tras este número de segundos y se reinician con la siguiente tarea; `0` los mantiene en ejecución. |

---

## 💻 Parámetros establecidos por las herramientas

`./dev.py` y Docker Compose los establecen por ti: cámbialos solo si sabes por qué.

| Variable | Valor predeterminado | Qué hace |
| --- | --- | --- |
| `HOST` | `0.0.0.0` | Dirección en la que escucha `./dev.py server`; `127.0.0.1` acepta solo conexiones locales. Docker Compose siempre usa `0.0.0.0`. |
| `LIBREFOLIO_LOG_LEVEL` | — | Sustituye a `LOG_LEVEL` cuando se establece; `./dev.py server --debug` y `./dev.py server --test` lo establecen en `DEBUG`. |
| `LIBREFOLIO_API_DOCS` | — | Establecida en `1` por `./dev.py server --debug`, que activa las páginas de documentación de la API (la variable del mismo nombre, más arriba). |
| `LIBREFOLIO_NO_SCHEDULER` | — | Cualquier valor no vacío, incluido `0`, desactiva las sincronizaciones programadas de precios y de FX. La establece `./dev.py server --no-scheduler`. |
| `LIBREFOLIO_TEST_MODE` | — | `1`, `true` o `yes`, sin distinguir mayúsculas de minúsculas, cambia a la carpeta de datos de prueba. Solo para las propias ejecuciones de prueba de LibreFolio: `./dev.py server --test` y los ejecutores de pruebas la establecen, y `./dev.py server` la desactiva. Un servidor iniciado sin `./dev.py`, como con `uvicorn` directamente o desde una unidad de servicio, la toma de su entorno. En una instancia en uso, fuera del ejecutor de pruebas, las [comprobaciones de arranque](configuration_security.md#startup-checks) la señalan como un error. |
| `LIBREFOLIO_TEST_DATA_DIR` | `./backend/data/test` | Carpeta de los datos de prueba; no puede solaparse con la de producción. |

---

## 🔝 Qué valor prevalece

De mayor a menor prioridad:

1. Las opciones `--host`, `--port` y `--data-dir` de `./dev.py server`.
2. Las variables establecidas en el shell.
3. El archivo `.env`.
4. Los valores predeterminados que se indican en esta página.

Con Docker Compose, el bloque `environment:` de `docker-compose.yml` prevalece sobre `.env`: fija `HOST`, `LIBREFOLIO_DATA_DIR` y, dentro del contenedor, `PORT=6040` (tu `PORT` sigue estableciendo el puerto del host). Consulta [Docker avanzado](docker_advanced.md#resolution-priority).

Para una [configuración de plugin](configuration_secrets.md#plugin-settings), de mayor a menor prioridad: su variable (`LIBREFOLIO_PLUGIN_…` antes que el nombre anterior del plugin para ella, cada una antes que su forma `_FILE`), el valor guardado dentro de LibreFolio y, después, el valor predeterminado del plugin. Una variable con un valor incorrecto sigue prevaleciendo y deja el plugin sin configurar. Una configuración personal no tiene variable: el valor guardado por el usuario y, después, el predeterminado.

---

## 📂 Dónde van los datos

- **Producción**: `backend/data/prod/`, o `LIBREFOLIO_DATA_DIR`. Contiene la base de datos (`sqlite/app.db`), `custom-uploads/`, `broker_reports/`, `logs/` y, una vez que LibreFolio ha creado la [clave de instancia](configuration_secrets.md#instance-key), `secrets/`.
- **Pruebas**: `backend/data/test/`, o `LIBREFOLIO_TEST_DATA_DIR`. La misma estructura, mantenida separada.

[Estructura del sistema de archivos](filesystem.md) detalla cada carpeta y cómo hacer una copia de seguridad de ella.

---

## 🔗 Relacionado

- 📄 **[Configuración: Secretos y configuración de plugins](configuration_secrets.md)** — Secretos, configuración de plugins
- 📄 **[Configuración: Comprobaciones y protecciones](configuration_security.md)** — Comprobaciones de arranque, protecciones del navegador, detención del servidor
- 📄 **[Configuración: Cuentas y búsqueda de activos](configuration_accounts.md)** — Cuentas y altas, el orden de los proveedores de precios en la búsqueda, opcional: búsqueda web de nuevos activos
- ⚙️ **[Configuración global](settings.md)** — Opciones que se cambian desde dentro de la aplicación
- 🐳 **[Docker avanzado](docker_advanced.md)** — Archivo Compose, volúmenes, ID de usuario y de grupo
- 🧑‍💻 Para desarrolladores: **[Sistema de configuración](../developer/architecture/settings.md)** — Cómo se cargan estos valores
- 🔒 Para desarrolladores: **[Arquitectura de seguridad](../developer/architecture/security.md)** — Secretos, la clave de instancia, las comprobaciones de arranque y el límite de inicios de sesión fallidos
- 🧩 Para desarrolladores: **[Configuración de plugins](../developer/architecture/patterns/plugin_settings.md)** — Cómo declaran los plugins su configuración y cómo se protegen los secretos
