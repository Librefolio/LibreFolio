# 👥 Configuración: Cuentas y búsqueda de activos

Esta página cubre quién puede **registrarse** en tu LibreFolio y cuántas cuentas puede alojar, el límite de inicios de sesión fallidos y el **administrador inicial**, y luego dos opciones de la búsqueda de activos: el orden de los proveedores de precios en sus resultados y la búsqueda web opcional.

El archivo `.env` y sus otras opciones se explican en [Configuración](configuration.md), la primera página de la guía.

---

## 👥 Cuentas y registros {: #accounts }

Quién puede crear una cuenta, cuántas cuentas puede alojar la instancia y el límite de inicios de sesión fallidos. Sin estas variables, el ajuste **Registro** de la [Configuración global](settings.md) decide quién puede registrarse, no hay límite en el número de cuentas, el idioma de las cuentas nuevas es el que eligió un administrador ([Configuración global](settings.md)), y los inicios de sesión fallidos están limitados ([Inicios de sesión fallidos](#login-limit)). Las ocho son opcionales: descomenta una línea de la sección **Cuentas** de `.env.example` para establecer una. Otras tres, para instalaciones por script y Docker Compose, crean el [administrador inicial](#initial-admin) de una instancia nueva.

| Variable | Predeterminado | Qué hace |
| --- | --- | --- |
| `LIBREFOLIO_REGISTRATION` | _sin establecer_ | Quién puede crear una cuenta: `open` (cualquiera), `invite` (solo con un enlace de invitación) o `disabled` (nadie). Sin establecer: decide el ajuste global **Registro**, **Por invitación** en una instancia nueva salvo que un administrador lo haya cambiado (una instancia actualizada desde una versión anterior conserva el modo que tenía). Establecido: este valor prevalece y el ajuste global no se puede cambiar desde la aplicación. No importan las mayúsculas ni las minúsculas, ni los espacios alrededor del valor. Sea cual sea el valor, la primera cuenta de una instancia nueva se puede crear desde la página de inicio de sesión, con **Regístrate aquí**, y se convierte en el administrador: consulta [Quién puede registrarse](settings.md). Con `LIBREFOLIO_ADMIN_EMAIL`, LibreFolio crea ese administrador por sí mismo en su lugar: consulta [El administrador inicial](#initial-admin). Establecido en `open`, también muestra a los administradores que abren la aplicación en una dirección fuera de la red local una advertencia que nombra esta variable: consulta [La advertencia de registro abierto](settings.md). |
| `LIBREFOLIO_MAX_USERS` | _sin establecer_ (sin límite) | El máximo de cuentas que puede alojar la instancia: un número entero, como mínimo `1`; cualquier otra cosa (`0`, `abc`, `-3`, `1.5`) detiene el servidor al iniciar. Cuentan las cuentas activas, y también cada invitación hasta que se usa, se revoca o caduca, cada cuenta que espera la verificación de su correo electrónico mientras su enlace está activo, y el [administrador inicial](#initial-admin) mientras espera su configuración; las cuentas desactivadas no cuentan. Consulta [Cuando la instancia está llena](#user-limit). |
| `LIBREFOLIO_DEFAULT_LANGUAGE` | _sin establecer_ | El idioma de las cuentas que no han elegido uno, y de los correos enviados a personas que aún no tienen cuenta: `en`, `it`, `fr` o `es`, sin distinguir mayúsculas y minúsculas. Representa el **Idioma predeterminado** de la [Configuración global](settings.md) hasta que un administrador guarda ese ajuste por primera vez; desde ese primer guardado prevalece el valor del administrador, incluso cuando vuelve a ser inglés. Sin establecer: decide el ajuste, inglés en una instancia nueva. Cualquier otro valor detiene el servidor al iniciar. |
| `LIBREFOLIO_DEFAULT_CURRENCY` | _sin establecer_ | La moneda con la que empiezan las cuentas nuevas: un código ISO 4217 que LibreFolio conozca, como `EUR`, `USD` o `CHF`, sin distinguir mayúsculas y minúsculas. Representa la **Moneda predeterminada** de la [Configuración global](settings.md) hasta que un administrador guarda ese ajuste por primera vez; desde ese primer guardado prevalece el valor del administrador, incluso cuando vuelve a ser `EUR`. Sin establecer: decide el ajuste, `EUR` en una instancia nueva. Cualquier otro valor detiene el servidor al iniciar. |
| `LIBREFOLIO_DEFAULT_TIMEZONE` | _sin establecer_ | La zona horaria de la aplicación, en la que se leen las horas del [planificador de datos de mercado](settings.md#market-data-scheduler): un nombre IANA como `Europe/Rome` o `America/New_York` (el servidor en sí siempre trabaja en UTC). Representa la **Zona horaria** de la configuración del planificador hasta que un administrador guarda ese ajuste por primera vez; desde ese primer guardado prevalece el valor del administrador, incluso cuando vuelve a ser `UTC`. Sin establecer: decide el ajuste, `UTC` en una instancia nueva. Cualquier otro valor detiene el servidor al iniciar. |
| `LIBREFOLIO_PUBLIC_URL` | _sin establecer_ | La dirección en la que tus usuarios abren LibreFolio, con `http://` o `https://`, como `https://librefolio.example.com`. En la pestaña [Usuarios](users.md) de Configuración › Administración, los diálogos de invitación y de restablecimiento de contraseña rellenan su **Dirección del servidor** con ella; sin ella, con la dirección que usa el navegador del administrador. El administrador puede cambiar esa dirección, y el navegador comprueba entonces que este LibreFolio responde allí. La [línea de comandos](cli_tools.md) la pone delante de los enlaces de invitación y de restablecimiento de contraseña que imprime; sin ella, imprime solo la ruta (`/invite#token=…`) y tú añades la dirección. Los correos con un enlace también la necesitan, sin fallback a la dirección del navegador: sin ella, no sale ningún correo de invitación, de enlace de restablecimiento de contraseña o de contraseña olvidada ([Correo electrónico](email.md)). Se rechaza una dirección que contenga un nombre de usuario o una contraseña, y LibreFolio entonces funciona como lo hace sin ella. |
| `LIBREFOLIO_LOGIN_LIMIT` | `on` | El límite de inicios de sesión fallidos: `on` u `off`, sin distinguir mayúsculas y minúsculas; los espacios alrededor del valor no importan. `off` es solo para una instancia de prueba: entonces cualquiera puede probar contraseñas sin pausa, y cada inicio registra una [advertencia](configuration_security.md#startup-checks). A diferencia de `LIBREFOLIO_REGISTRATION` y `LIBREFOLIO_PUBLIC_URL`, cualquier otro valor, incluidos `true`, `1` y `yes`, detiene el servidor al iniciar. Consulta [Inicios de sesión fallidos](#login-limit). |

Un valor vacío cuenta como no establecido. Un valor incorrecto de `LIBREFOLIO_REGISTRATION` o `LIBREFOLIO_PUBLIC_URL` no detiene el servidor, a diferencia de las [opciones principales](configuration.md): LibreFolio se mantiene del lado seguro y escribe un error en su registro la primera vez que cada proceso del servidor necesita el valor: `Invalid account configuration`, con la variable y su valor en `problem` (no se muestra una dirección que contenga una `@`: puede llevar un nombre de usuario o una contraseña), y en `consequence` lo que cuesta hasta que lo corrijas. Corrige el valor y reinicia:

| Valor incorrecto | Qué hace LibreFolio | `consequence` en el registro |
| --- | --- | --- |
| `LIBREFOLIO_REGISTRATION` distinto de los tres modos | El registro está cerrado y el ajuste global permanece bloqueado | `registration stays closed until it is fixed` |
| `LIBREFOLIO_PUBLIC_URL` sin `http://` o `https://`, o con un nombre de usuario o una contraseña | Se ignora, como si no estuviera establecida: la [línea de comandos](cli_tools.md) imprime solo la ruta y explica por qué bajo cada enlace, y los diálogos de la pestaña [Usuarios](users.md) parten de la dirección del navegador. No sale ningún correo con un enlace y, mientras el correo funciona, el registro de inicio también tiene una [advertencia](configuration_security.md#startup-checks) ([Correo electrónico](email.md)) | `links show the bare path until it is fixed` |

`LIBREFOLIO_LOGIN_LIMIT`, `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_DEFAULT_LANGUAGE`, `LIBREFOLIO_DEFAULT_CURRENCY` y `LIBREFOLIO_DEFAULT_TIMEZONE` son las excepciones: un valor que LibreFolio no puede usar **detiene el servidor al iniciar**, como lo hace un valor inutilizable del [administrador inicial](#initial-admin). Para `LIBREFOLIO_LOGIN_LIMIT`, eso es cualquier cosa que no sea `on` u `off`; para `LIBREFOLIO_MAX_USERS`, cualquier cosa que no sea un número entero de al menos `1` (`0`, `abc`, `-3` y `1.5` lo detienen); para `LIBREFOLIO_DEFAULT_LANGUAGE`, cualquier cosa que no sea `en`, `it`, `fr` o `es`; para `LIBREFOLIO_DEFAULT_CURRENCY`, cualquier cosa que no sea un código de moneda que LibreFolio conozca; para `LIBREFOLIO_DEFAULT_TIMEZONE`, cualquier cosa que no sea un nombre de zona horaria IANA. El error está en la salida de consola del servidor (`docker compose logs librefolio` con Docker) y nombra la variable y el valor, como `LIBREFOLIO_LOGIN_LIMIT='yes': expected on or off` o `LIBREFOLIO_MAX_USERS='abc': expected a whole number of at least 1`. Corrígelo y vuelve a iniciar.

### 📏 Cuando la instancia está llena {: #user-limit }

Cuando las cuentas activas, las invitaciones pendientes, las cuentas que esperan la verificación de su correo y un [administrador inicial](#initial-admin) que espera su configuración alcanzan `LIBREFOLIO_MAX_USERS`:

- nadie puede registrarse sin una invitación, sea cual sea el modo de [Registro](settings.md);
- un enlace de invitación ya enviado sigue funcionando: su plaza se contó cuando se creó;
- los administradores no pueden crear invitaciones ni reactivar cuentas, excepto desde la [línea de comandos](cli_tools.md): `user create`, `user invite` y `user activate` imprimen una advertencia y luego continúan. `user activate` no imprime ninguna para una cuenta que ya ocupa su plaza: una que espera la verificación de su correo mientras su enlace está activo, o el administrador inicial que espera su configuración.

Se libera una plaza cuando se desactiva o elimina una cuenta, cuando se revoca o caduca una invitación, o cuando caduca el enlace de una cuenta que espera la verificación de su correo (consulta *Verificación de correo electrónico* en [Correo electrónico](email.md)). La primera cuenta de una instancia nueva siempre se puede crear.

### 📉 Cuando el plan se reduce {: #user-limit-over }

Si las cuentas **activas** superan en número a `LIBREFOLIO_MAX_USERS` — bajaste el límite y reiniciaste, o restauraste una copia de seguridad que contiene más usuarios de los que permite el límite —, la instancia está *por encima del límite*. LibreFolio no elimina a nadie; pide a un administrador que elija.

- **A quién afecta**: solo `active > limit`. Con exactamente tantas cuentas activas como el límite, no ocurre nada. Las invitaciones y las cuentas que esperan su verificación ocupan plazas, pero nunca inician este estado.
- **Qué ve un administrador**: en el primer inicio de sesión, antes que cualquier otra página, la lista de las cuentas activas. El administrador que elige está marcado y no se puede desmarcar. Cada fila indica cuántos brókers posee la cuenta **en solitario**: esos brókers permanecen, pero nadie más puede acceder a ellos hasta que se reactive la cuenta. Un contador muestra cuántas cuentas están elegidas frente a cuántas permite el límite.
- **Primero la copia de seguridad completa**: la misma página la ofrece, para que los datos se puedan llevar antes de desactivar a nadie.
- **Qué ocurre con «Desactivar las demás y continuar»**: las cuentas no elegidas se **desactivan**, no se eliminan: se cierra su sesión, no pueden iniciar sesión y conservan todos sus datos. Puedes reactivar una más adelante cuando haya una plaza libre ([Cuando la instancia está llena](#user-limit)). Las invitaciones pendientes se cancelan, de la más reciente a la más antigua, solo en la medida en que las cuentas elegidas necesiten sus plazas; la página indica cuántas antes de que confirmes.
- **Qué ve todo el mundo** hasta que se hace la elección: un mensaje de que un administrador tiene que elegir quién conserva el acceso. Nadie más que un administrador entra, y los administradores no ven nada más que esta elección.
- **Un límite que LibreFolio no puede leer** (`LIBREFOLIO_MAX_USERS=abc`, `0`) nunca inicia este estado: el servidor no arranca hasta que corrijas el valor, así que una errata no puede dejar a todo el mundo fuera.

No se necesita ningún paso especial después de una restauración: las cuentas restauradas se cuentan de la misma manera.

### 🚦 Inicios de sesión fallidos {: #login-limit }

LibreFolio deja de comprobar contraseñas durante un tiempo cuando los inicios de sesión siguen fallando, para que nadie pueda probar contraseña tras contraseña hasta que una funcione. El límite está activado a menos que lo desactives.

| Límite | Al superarlo |
| --- | --- |
| 10 inicios de sesión fallidos cada 15 minutos con el mismo nombre de usuario o dirección de correo electrónico, exista o no una cuenta con ese dato | Se rechaza todo inicio de sesión con ese dato, incluida la contraseña correcta, hasta que el fallo más antiguo tenga 15 minutos. |
| 50 inicios de sesión fallidos cada 15 minutos desde la misma dirección, sea cual sea el nombre de usuario o la dirección de correo electrónico que usen; una dirección IPv6 cuenta por su /64, el bloque que suele tener un abonado. No se cuentan los inicios de sesión que llegan a través de un proxy en el que LibreFolio no confía, en una dirección local: consulta *Detrás de un proxy inverso* más abajo | Se rechaza todo inicio de sesión desde esa dirección, para cualquier cuenta, hasta que el fallo más antiguo tenga 15 minutos. |

- **Qué ve el usuario**: la página de inicio de sesión dice *Demasiados intentos de inicio de sesión: espera unos minutos e inténtalo de nuevo.* La espera es de 15 minutos como máximo. La respuesta es la misma tanto si existe una cuenta como si no, así que el límite no revela a nadie qué cuentas existen.
- **Qué cuenta como fallo**: una contraseña incorrecta, o un nombre de usuario o una dirección de correo electrónico que ninguna cuenta tiene. En el inicio de sesión, la contraseña correcta de una cuenta desactivada, o de una que aún espera la verificación de su correo, no cuenta ni como fallo ni como éxito.
- **Volver a intentarlo no alarga la espera**: un inicio de sesión que el límite rechaza no se cuenta, y su contraseña ni siquiera se comprueba.
- **Un inicio de sesión correcto** borra los fallos del nombre de usuario o de la dirección de correo electrónico que usó, no los de la dirección desde la que llegó.
- **El nombre de usuario y la dirección de correo electrónico cuentan por separado**, incluso para una misma cuenta: quien adivine su contraseña tiene 10 intentos con el nombre de usuario y 10 con la dirección de correo electrónico cada 15 minutos, siempre dentro de los 50 de su dirección. Las mayúsculas de la A a la Z no importan: `Alice` y `alice` comparten un mismo recuento.
- **La contraseña actual también cuenta.** Una contraseña actual incorrecta en **Cambiar contraseña**, o cuando un usuario cambia su dirección de correo electrónico en la pestaña Perfil ([Perfil](../user/settings/profile.md)), cuenta como un inicio de sesión fallido con el nombre de usuario de la cuenta, desde la misma dirección. Así, 10 contraseñas actuales incorrectas también bloquean el inicio de sesión con ese nombre de usuario, y los inicios de sesión fallidos con el nombre de usuario bloquean esas dos comprobaciones: **Cambiar contraseña** y la pestaña Perfil entonces dicen *Demasiadas contraseñas incorrectas: espera unos minutos e inténtalo de nuevo.* Eliminar la propia cuenta no pide contraseña: no hay nada que limitar ahí.
- **Enviar el enlace de nuevo también cuenta.** En la página de inicio de sesión, una cuenta que espera la verificación de su correo recibe **Enviar el enlace de nuevo**, que comprueba el nombre de usuario o la dirección de correo electrónico y la contraseña como lo hace un inicio de sesión ([Verificación de correo electrónico](email_flows.md#verification)). Una contraseña incorrecta ahí cuenta como un inicio de sesión fallido con lo que se escribió, desde la misma dirección; superado el límite, se rechaza antes de comprobar la contraseña, y la página indica en cuántos minutos volver a intentarlo. La contraseña correcta borra los fallos de lo que se escribió, como lo hace un inicio de sesión correcto. Sus propios límites siguen aplicándose ([Límites de los correos de verificación](email_flows.md#verification-limits)).
- **No limitados**: los enlaces de invitaciones y de restablecimiento de contraseñas. Sus tokens son valores aleatorios largos que nadie puede adivinar, y un límite por dirección podría rechazarlos a todos los usuarios detrás del mismo router. **¿Olvidaste tu contraseña?** no pide contraseña y tiene sus propios límites: consulta [Contraseñas olvidadas](email_flows.md#forgot-password).
- **Se guardan en memoria**, por cada proceso del servidor: un reinicio olvida todos los recuentos, lo que también permite que un usuario que no puede esperar vuelva a entrar de inmediato. Con varios procesos del servidor (`./dev.py server --workers N`), cada uno mantiene sus propios recuentos, así que los límites se multiplican por N; la imagen de Docker ejecuta uno.
- **Detrás de un proxy inverso**, la dirección que cuenta es la del visitante, tal como la lee LibreFolio. Indica a LibreFolio cuál es tu proxy, incluyéndolo en `FORWARDED_ALLOW_IPS` o nombrando la cabecera que establece en `LIBREFOLIO_CLIENT_IP_HEADER`, como explica [La dirección del visitante](connection_proxy.md#client-address). Hasta entonces, LibreFolio ve a cada visitante con la dirección del proxy, y lo que ocurre depende de dónde esté el proxy.
- **Un proxy en el que LibreFolio no confía, en una dirección local** (una red de Docker, tu propia red o tu VPN), como un contenedor de proxy delante de la imagen de Docker, la configuración habitual: LibreFolio deja los inicios de sesión a través de él fuera del límite por dirección, para que 50 inicios de sesión fallidos de cualquiera no puedan rechazar a todos. El límite por nombre de usuario o dirección de correo electrónico sigue contándolos. El registro tiene una advertencia por proceso del servidor, la primera vez que una petición a través de dicho proxy alcanza un límite por dirección: `Requests come through a reverse proxy that LibreFolio does not trust: the limits per client address skip them. List the proxy in FORWARDED_ALLOW_IPS, or name the header it sets in LIBREFOLIO_CLIENT_IP_HEADER`.
- **Un proxy en el que LibreFolio no confía, en una dirección pública**, como una CDN: todos los visitantes comparten la dirección del proxy y su recuento, así que 50 inicios de sesión fallidos de cualquiera rechazan todos los inicios de sesión a través del proxy, incluidas las contraseñas correctas, durante hasta 15 minutos.

**Desactivarlo.** `LIBREFOLIO_LOGIN_LIMIT=off`, sin distinguir mayúsculas y minúsculas, está pensado para una instancia de prueba, cuyas pruebas automatizadas inician sesión mal a propósito: no se cuenta nada y no se rechaza nada. Cada inicio registra entonces una advertencia, con `accounts.login_limit` en `check`: `LIBREFOLIO_LOGIN_LIMIT=off: failed sign-ins are not limited; turn it back on unless this is a test instance`. La misma comprobación, a petición, está en la pestaña **Seguridad** de **Configuración › Administración**: una advertencia, contada en el número de la pestaña, hasta que el límite vuelva a estar activado (consulta «Seguridad» en [Configuración global](settings.md)). Elimina la variable, o establece su valor en `on`, para volver a activar el límite en el siguiente inicio. Cualquier otro valor detiene el servidor al iniciar: consulta [Cuentas y registros](#accounts).

### 👑 El administrador inicial {: #initial-admin }

LibreFolio puede crear el administrador de una instancia nueva por sí mismo, en su primer inicio, para la dirección que le indiques: nadie puede registrarse antes y ocupar su lugar. Está pensado para instalaciones hechas con un script o Docker Compose. Sin estas variables no cambia nada, y la primera cuenta registrada se convierte en el administrador ([Quién puede registrarse](settings.md)).

| Variable | Predeterminado | Qué hace |
| --- | --- | --- |
| `LIBREFOLIO_ADMIN_EMAIL` | _sin establecer_ | La dirección de correo electrónico del administrador. Establecerla activa el administrador inicial. |
| `LIBREFOLIO_ADMIN_USERNAME` | `admin` | El nombre de usuario del administrador: de 3 a 50 caracteres, sin `@`, como en el registro. |
| `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` | _sin establecer_ | Opcional: el token del enlace de configuración, para un script que entrega el enlace por sí mismo. De 32 a 200 caracteres, solo letras, dígitos y `-` `.` `_` `~`, ya que viaja en un enlace: la salida de `openssl rand -hex 32`, por ejemplo. `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` lo lee de un archivo en su lugar: consulta [Secretos](configuration_secrets.md#secrets). Sin establecer: LibreFolio genera el token. |

Un valor vacío cuenta como no establecido. Los espacios alrededor del correo electrónico y del nombre de usuario no importan; el token se usa exactamente como está escrito, así que un espacio en él, incluso al final, lo hace inutilizable.

En el primer inicio de una instancia **sin ninguna cuenta**, LibreFolio:

1. crea el administrador, todavía no activo, con una contraseña aleatoria que nadie conoce: nadie puede iniciar sesión con ella todavía;
2. establece el [ajuste global](settings.md) **Registro** en **Por invitación**; `LIBREFOLIO_REGISTRATION`, cuando está establecido, sigue decidiendo;
3. emite un **enlace de configuración**, `/setup#token=…`, que funciona una vez, durante 72 horas. Abre la página de configuración de la instancia, donde el administrador elige la contraseña y se inicia sesión.

Mientras el administrador espera, nadie puede registrarse como la primera cuenta, y el administrador ocupa una plaza de `LIBREFOLIO_MAX_USERS`. Quién entrega el enlace depende del token:

- **Con `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`**, quien lo haya elegido: el enlace es la dirección de la instancia seguida de `/setup#token=` y el token. LibreFolio ni lo registra ni lo envía por correo.
- **Sin él**, LibreFolio genera el token y entrega el enlace por sí mismo:
    - escribe el enlace **una vez** en su registro, como advertencia: `Setup link of the initial administrator, single use: open it to choose the password`, con el enlace en `link` (con Docker: `docker compose logs librefolio`). El enlace es la dirección completa cuando `LIBREFOLIO_PUBLIC_URL` está establecida; de lo contrario, es la ruta, y `note` te pide que pongas delante la dirección de tu servidor;
    - envía el enlace por correo a `LIBREFOLIO_ADMIN_EMAIL` cuando el correo funciona, es decir, con un servidor SMTP configurado ([Correo electrónico](email.md)) y `LIBREFOLIO_PUBLIC_URL` establecida. El correo está en el idioma predeterminado de la instancia y sale una vez que el servidor está en marcha, así que un servidor de correo lento nunca retrasa el inicio. Si no puede salir, el registro tiene `Setup link of the initial administrator not emailed`, con el motivo, y el enlace del registro sigue funcionando.

Un reinicio mientras el administrador espera no emite nada nuevo y no vuelve a escribir el enlace en el registro. Una vez que ningún enlace funciona, cada inicio registra una advertencia:
`The initial administrator's setup link has expired: run ./dev.py user setup-link…` cuando el enlace caducó, o
`The initial administrator's setup link was withdrawn (cancelled, or its address changed): run ./dev.py user setup-link…`
cuando se [canceló](users.md#cancel-setup) o cambió la dirección del administrador. Ese comando imprime un enlace nuevo ([Un nuevo enlace de configuración](cli_tools.md)). Un nuevo valor de `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` también da un enlace nuevo, en el siguiente inicio.

En una instancia que ya tiene cuentas, y ningún administrador esperando, las variables no crean nada: cada inicio registra `LIBREFOLIO_ADMIN_* ignored: this instance already has accounts`. Lo mismo ocurre una vez completada la configuración.

Un valor que LibreFolio no puede usar **detiene el servidor al iniciar**, en cualquier instancia, incluida una que ya tenga cuentas:

- `LIBREFOLIO_ADMIN_USERNAME` o `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` establecidos sin `LIBREFOLIO_ADMIN_EMAIL`;
- un correo electrónico que no es una dirección;
- un nombre de usuario de menos de 3 o más de 50 caracteres, o con una `@`: el inicio de sesión lee un nombre con `@` como una dirección de correo electrónico, y el administrador inicia sesión con la dirección de `LIBREFOLIO_ADMIN_EMAIL` de todos modos;
- un token de menos de 32 o más de 200 caracteres, o con un carácter distinto de letras, dígitos y `-` `.` `_` `~`, incluido un espacio;
- un `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN_FILE` que no puede dar el token ([Secretos en archivos](configuration_secrets.md#secret-files)).

El error está en la salida de consola del servidor (`docker compose logs librefolio` con Docker): nombra la variable, nunca el token. Corrige el valor y vuelve a iniciar.

---

## 🥇 El orden de los proveedores de precios en la búsqueda {: #provider-order }

Cuando creas un activo, la búsqueda pregunta a todos los proveedores de precios a la vez y enumera los resultados proveedor por proveedor. Cada proveedor declara en qué lugar se sitúa: su nivel, **premium** para una fuente que una instancia avala, como datos con licencia, o **community**, el predeterminado; y su prioridad dentro del nivel. Cuando hay al menos un proveedor premium disponible, sus resultados van primero. Ninguno de los proveedores incluidos con LibreFolio es premium, así que sin uno la búsqueda mantiene su orden.

| Variable | Predeterminado | Qué hace |
| --- | --- | --- |
| `LIBREFOLIO_ASSET_PROVIDERS_PREMIUM` | _sin establecer_ | Los proveedores que se cuentan como premium, por código, separados por comas, como `yfinance,justetf`: exactamente estos, independientemente de lo que declaren. Sin establecer: lo que declara cada proveedor. |
| `LIBREFOLIO_ASSET_PROVIDERS_ORDER` | _sin establecer_ | Los proveedores que se listan primero, en este orden, por código, separados por comas; los demás siguen en su orden declarado. Los proveedores premium siguen yendo antes que los demás. Sin establecer: lo que declara cada proveedor. |

- Los códigos de los proveedores incluidos con LibreFolio son `yfinance`, `justetf`, `borsa_italiana`, `css_scraper` y `scheduled_investment`; un proveedor que añadas tiene el suyo. No importan las mayúsculas ni las minúsculas, ni los espacios alrededor de ellos.
- Un código que ningún proveedor tiene se ignora, y el servidor lo registra una vez.
- Los valores de configuración se aplican en la siguiente búsqueda, sin reiniciar: LibreFolio los lee en cada búsqueda.

---

## 🔎 Opcional: búsqueda web de nuevos activos {: #optional-web-search-for-new-assets }

Cuando creas un activo, también desde el asistente de importación de brókers, y la búsqueda propia de un proveedor no encuentra nada, LibreFolio puede encontrar la página del activo con una búsqueda web mediante la biblioteca [`ddgs`](https://pypi.org/project/ddgs/). Está activada de forma predeterminada y nunca se usa para actualizaciones de precios. Todas estas variables son opcionales: descomenta una línea de `.env.example` para cambiar una.

| Variable | Predeterminado | Qué hace |
| --- | --- | --- |
| `LIBREFOLIO_WEB_LINK_FINDER_ENABLED` | `1` | `0` desactiva la búsqueda web; la búsqueda propia de los proveedores sigue funcionando. |
| `LIBREFOLIO_WEB_LINK_FINDER_ENGINE` | `ddgs` | `ddgs` no necesita configuración. `apikey` está reservado para un servicio de búsqueda de pago y todavía no devuelve resultados. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_REGION` | `wt-wt` | Región de búsqueda. `wt-wt` (mundial) evita que los sitios nacionales como Borsa Italiana se vean relegados. Ejemplos: `it-it`, `us-en`. |
| `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND` | `auto` | Motores que consulta `ddgs`: `auto` los alterna para obtener la mayor cobertura; una lista como `google,bing,duckduckgo` da resultados más estables. |
| `LIBREFOLIO_WEB_LINK_FINDER_TIMEOUT` | `6` | Límite de tiempo de una búsqueda, en segundos: como mínimo `1`. Cualquier otro valor hace que se use el valor predeterminado. |
| `LIBREFOLIO_WEB_LINK_FINDER_MAX` | `5` | Máximo de enlaces devueltos por una búsqueda: un número entero, como mínimo `1`. Cualquier otro valor hace que se use el valor predeterminado. |
| `LIBREFOLIO_WEB_LINK_FINDER_API_KEY` | _vacío_ | Clave para el motor `apikey`. `LIBREFOLIO_WEB_LINK_FINDER_API_KEY_FILE` la lee de un archivo en su lugar: consulta [Secretos](configuration_secrets.md#secrets). |

??? tip "🔁 Los resultados cambian entre intentos — cuando un activo conocido a veces no se encuentra"

    Con `auto`, cada búsqueda puede llegar a motores diferentes, así que la misma consulta puede ir mejor o peor de un intento a otro. Reinténtalo una vez, o establece
    `LIBREFOLIO_WEB_LINK_FINDER_DDGS_BACKEND=google,bing,duckduckgo`.

---

## 🔗 Relacionado

- 📄 **[Configuración](configuration.md)** — Crear el archivo `.env`, opciones principales, parámetros establecidos por las herramientas, …
- 📄 **[Configuración: secretos y configuración de plugins](configuration_secrets.md)** — Secretos, configuración de plugins
- 📄 **[Configuración: comprobaciones y protecciones](configuration_security.md)** — Comprobaciones de inicio, protecciones del navegador, detención del servidor
