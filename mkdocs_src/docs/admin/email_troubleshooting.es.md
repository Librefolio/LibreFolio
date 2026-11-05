# 🛠️ Correo electrónico: cuando no funciona

Esta página es para cuando los correos electrónicos no salen: los errores que muestran el correo de prueba y los diálogos,
lo que dice el registro y las notas de seguridad de la configuración de SMTP.

Cómo configurar el correo electrónico, con la pestaña **Correo electrónico** de Configuración y su correo de prueba, está en
[Correo electrónico](email.md); los mensajes que envía LibreFolio están en [Correo electrónico: enlaces y mensajes](email_flows.md).

---

## 🛠️ Cuando no funciona {: #troubleshooting }

Los problemas son de dos tipos:

- una variable que LibreFolio no puede usar: el estado es **No funciona** en cuanto abres la pestaña
  ([Problemas de configuración](#configuration-problems));
- un servidor que rechaza el correo o no responde: solo se muestra cuando se envía un correo
  ([Errores de envío](#sending-errors)).

Una configuración que no se puede usar desactiva el correo electrónico, y nada más: el servidor arranca como de costumbre y
todo lo demás funciona. El registro de inicio ya nombra la variable culpable, justo después de
`Starting LibreFolio`, y la pestaña también lo hace ([Qué dice el registro](#logs)).

### ⚙️ Problemas de configuración {: #configuration-problems }

La pestaña nombra la variable culpable; el código está en el registro.

| La pestaña dice | Código | Qué comprobar |
| --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` no es un nombre de servidor válido… | `SMTP_HOST_INVALID` | Solo el nombre o la dirección IP: `smtp.example.com`, no `smtp://smtp.example.com`, `smtp.example.com:587` ni `user@smtp.example.com`. El puerto va en `LIBREFOLIO_SMTP_PORT`; una dirección IPv6 va sin corchetes. |
| `LIBREFOLIO_SMTP_TLS` debe ser starttls, tls o none. | `SMTP_TLS_INVALID` | Una de las tres palabras. Para cifrado desde el primer byte, en el puerto 465, la palabra es `tls`. |
| `LIBREFOLIO_SMTP_PORT` debe ser un número entero de 1 a 65535. | `SMTP_PORT_INVALID` | Solo dígitos, o ninguna línea para usar el puerto del modo. |
| No se puede leer el archivo de contraseña indicado por `LIBREFOLIO_SMTP_PASSWORD_FILE`. | `SMTP_PASSWORD_UNREADABLE` | El registro dice por qué: el archivo no existe en esa ruta (con Docker, la ruta dentro del contenedor), el usuario que ejecuta LibreFolio no puede leerlo, o está vacío o en blanco, no es texto UTF-8 o supera los 64 KiB. |
| `LIBREFOLIO_SMTP_USER` está definido solo… (o `LIBREFOLIO_SMTP_PASSWORD`) | `SMTP_CREDENTIALS_INCOMPLETE` | Define tanto el usuario como la contraseña, o ninguno. Una contraseña proporcionada por `LIBREFOLIO_SMTP_PASSWORD_FILE` se notifica como `LIBREFOLIO_SMTP_PASSWORD`. |
| Falta `LIBREFOLIO_SMTP_FROM`… | `SMTP_FROM_MISSING` | Añade el remitente: es obligatorio en cuanto se define un servidor. |
| `LIBREFOLIO_SMTP_FROM` debe ser una dirección… | `SMTP_FROM_INVALID` | Una dirección, con o sin nombre, como `LibreFolio <noreply@example.com>`: sin lista y sin salto de línea. |
| `LIBREFOLIO_SMTP_REPLY_TO` debe ser una dirección. | `SMTP_REPLY_TO_INVALID` | La misma regla que para el remitente, o elimina la línea. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` debe ser un número entero de al menos 1. | `SMTP_MAX_PER_HOUR_INVALID` | Solo dígitos, al menos `1`. Para dejar de enviar, elimina `LIBREFOLIO_SMTP_HOST` en su lugar. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` debe ser un número entero de al menos 1. | `SIGNUP_EMAILS_PER_ADDRESS_INVALID` | Solo dígitos, al menos `1`, o ninguna línea para el valor predeterminado de `20`. Como las demás, desactiva el correo electrónico hasta que se corrija; el servidor arranca de todos modos. |

### 📤 Errores de envío {: #sending-errors }

El correo de prueba dice por qué no salió. Para ver la respuesta del propio servidor, consulta el registro.

| La pestaña dice | Código | Qué comprobar |
| --- | --- | --- |
| LibreFolio no puede llegar al servidor SMTP… | `CONNECTION_FAILED` | El nombre del servidor, tal como se ve desde donde se ejecuta LibreFolio (en un contenedor, `localhost` es el propio contenedor), el puerto y un firewall que rechaza la conexión. |
| La conexión segura falló… | `TLS_FAILED` | El modo y el puerto van juntos: `starttls` con 587, `tls` con 465. Con `starttls`, el servidor debe ofrecer cifrado. Su certificado debe ser válido y estar emitido para el nombre de `LIBREFOLIO_SMTP_HOST`: un certificado autofirmado, o una dirección IP en lugar del nombre, no supera la comprobación. |
| El servidor SMTP rechazó el inicio de sesión… | `AUTH_FAILED` | El usuario y la contraseña: con un proveedor, una contraseña de aplicación. Un servidor que acepta correo sin inicio de sesión rechaza uno: elimina el usuario y la contraseña. |
| El servidor SMTP rechazó la dirección del remitente… | `SENDER_REFUSED` | El servidor solo acepta las direcciones con las que tu cuenta puede enviar: usa una de ellas en `LIBREFOLIO_SMTP_FROM`. Sin un usuario, es posible que el servidor también requiera un inicio de sesión. |
| El servidor SMTP rechazó tu dirección. | `RECIPIENT_REFUSED` | El correo electrónico de tu cuenta, en [Perfil](../user/settings/profile.md). Sin inicio de sesión, un servidor puede rechazar el reenvío de correo a otros dominios: su respuesta en el registro lo indica. |
| El servidor SMTP no respondió a tiempo. | `TIMEOUT` | LibreFolio espera hasta 20 segundos por cada paso. Un firewall que descarta la conexión sin rechazarla termina aquí, y `starttls` en el puerto 465 también puede hacerlo. |
| El servidor SMTP no aceptó el mensaje. | `SEND_FAILED` | El servidor rechazó el propio mensaje: su respuesta en el registro dice por qué. Una dirección con letras fuera de ASCII antes de la `@`, como `zoë@example.com`, necesita un servidor que admita SMTPUTF8: sin ello, el correo nunca sale de LibreFolio y el registro indica `SMTPNotSupportedError`. |
| Se ha alcanzado el límite por hora de … correos… (estado), o Se ha alcanzado el límite de correos por hora: vuelve a intentarlo en … min. (prueba) | `EMAIL_RATE_LIMITED` | Espera los minutos indicados. Para permitir más, aumenta `LIBREFOLIO_SMTP_MAX_PER_HOUR` y reinicia. |
| El correo electrónico está desactivado o no funciona en esta instancia. | `EMAIL_UNAVAILABLE` | La configuración cambió desde que se cargó la pestaña, por ejemplo tras un reinicio: ahora la pestaña muestra el estado y su problema. |
| La dirección de tu cuenta no es una dirección de correo electrónico válida. | `EMAIL_RECIPIENT_INVALID` | Corrige el correo electrónico de tu cuenta en [Perfil](../user/settings/profile.md). |
| No se pudo enviar el correo de prueba. | — | No llegó ninguna respuesta conocida, como tras un error de red: recarga la página y consulta el registro. |
| Correo de prueba enviado a tu dirección…, pero no llega nada | — | El servidor aceptó el mensaje: a partir de ahí, la entrega es cosa suya. Revisa la carpeta de spam y luego los registros del servidor o de tu proveedor. Un remitente de un dominio que no permite que ese servidor envíe en su nombre puede ser rechazado, o clasificado como spam, durante el trayecto. |

**No se pudo leer el estado del correo electrónico.** significa que la pestaña no pudo llegar al servidor: recarga
la página y, si persiste, consulta el registro.

**Enviar por correo electrónico**, en los diálogos de invitación y restablecimiento, dice por qué no salió un enlace:

| El diálogo dice | Código | Qué hacer |
| --- | --- | --- |
| El correo electrónico está desactivado o no funciona en esta instancia. | `EMAIL_UNAVAILABLE` | La configuración cambió desde que se abrió el diálogo, por ejemplo tras un reinicio: consulta [Configuración › Administración › Correo electrónico](email.md#email-tab). |
| Los correos electrónicos no pueden llevar enlaces: LIBREFOLIO_PUBLIC_URL no está definida o no puede iniciar un enlace. | `EMAIL_LINKS_UNAVAILABLE` | Defínela y reinicia: consulta [Correos electrónicos con enlace](email_flows.md#public-url). |
| Este enlace ya no funciona: crea uno nuevo. | `EMAIL_LINK_INVALID` | El enlace ha caducado, se ha usado o se ha revocado: crea un enlace nuevo y envía ese. |
| La cuenta no está activa: actívala antes de enviarle un enlace de restablecimiento. | `EMAIL_ACCOUNT_INACTIVE` | **Reactiva** la cuenta en [Usuarios e invitaciones](users.md#actions), o ejecuta `user activate` en la [línea de comandos](cli_tools.md), y luego vuelve a enviar el enlace. |
| Introduce la dirección a la que enviar la invitación. | `EMAIL_RECIPIENT_REQUIRED` | La invitación no tiene ninguna dirección escrita: escribe una en **Enviar a**. |
| Esta no es una dirección de correo electrónico válida. | `EMAIL_RECIPIENT_INVALID` | Corrige la dirección en **Enviar a**. Para un enlace de restablecimiento, la dirección de la propia cuenta no es válida: copia el enlace en su lugar. |
| Se ha alcanzado el límite de correos por hora: vuelve a intentarlo en … min. | `EMAIL_RATE_LIMITED` | Espera los minutos indicados. Para permitir más, aumenta `LIBREFOLIO_SMTP_MAX_PER_HOUR` y reinicia. |
| El servidor SMTP rechazó la dirección del destinatario. | `RECIPIENT_REFUSED` | La dirección a la que fue el enlace: la de **Enviar a** para una invitación, el correo electrónico de la cuenta para un enlace de restablecimiento. Sin inicio de sesión, un servidor puede rechazar el reenvío de correo a otros dominios: su respuesta en el registro lo indica. |
| Los demás mensajes del correo de prueba | `CONNECTION_FAILED`, `TLS_FAILED`, `AUTH_FAILED`, … | Como en la tabla anterior. |
| No se pudo enviar el correo electrónico. | — | No llegó ninguna respuesta conocida, como tras un error de red: recarga la página y consulta el registro. |

`EMAIL_RECIPIENT_NOT_ALLOWED`, otra dirección para un enlace de restablecimiento, solo proviene de la API: el
diálogo no envía ese código.

### 📜 Qué dice el registro {: #logs }

El registro es `logs/librefolio.log` en la carpeta de datos, y el servidor también lo imprime en su consola:
`docker compose logs librefolio` con Docker ([Estructura del sistema de archivos](filesystem.md)).

En cada inicio, justo después de `Starting LibreFolio`, el servidor comprueba su configuración, incluido el correo
electrónico ([Comprobaciones de inicio](configuration_security.md#startup-checks)). Una configuración que no se puede
usar aparece allí en dos líneas, las dos primeras de la tabla siguiente; `none` hacia un servidor fuera de tu red local, y una `LIBREFOLIO_PUBLIC_URL` ausente o no válida, en una línea cada caso. Ninguna de ellas impide
el inicio. Las mismas tres comprobaciones están en la pestaña **Seguridad** de **Configuración › Administración**,
se leen de nuevo cuando lo solicitas, y allí un hallazgo enlaza con la [pestaña Correo electrónico](email.md#email-tab) (véase «Seguridad» en
[Configuración global](settings.md)).

| El registro dice | Nivel | Cuándo |
| --- | --- | --- |
| `Email configuration cannot be used: email stays off` | `error` | Una variable no se puede usar. Cada proceso del servidor lo registra una vez, al inicio, con `variable`, `problem` (el código) y `reason`: la regla que incumple, o por qué no se puede leer el archivo de contraseña. |
| `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` | `error` | Al inicio, después de la línea anterior, con `check` establecido en `email.smtp`: las comprobaciones de inicio informan del mismo problema. |
| `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `warning` | Al inicio, con `check` establecido en `email.smtp_encryption`: `none` hacia un servidor fuera de tu red local, que la línea nombra ([Notas de seguridad](#security)). |
| `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` | `info` | Al inicio, con `check` establecido en `email.links`: el correo electrónico funciona, pero `LIBREFOLIO_PUBLIC_URL` no está definida ([Correos electrónicos con enlace](email_flows.md#public-url)). |
| `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` | `warning` | Al inicio, con `check` establecido en `email.links`: el correo electrónico funciona, pero la variable no puede iniciar un enlace ([Correos electrónicos con enlace](email_flows.md#public-url)). |
| `Email sent` | `info` | El servidor aceptó un correo electrónico; `kind` indica cuál: `test`, `invite`, `password_reset`, `email_verification`, `email_changed` o `email_change_confirmation`. |
| `Email not sent` | `warning` | El servidor rechazó el correo electrónico o no respondió: `code`, como en [Errores de envío](#sending-errors), y `detail`, la respuesta del propio servidor, la pista más precisa. |
| `Email not sent: the hourly limit of the instance is reached` | `warning` | El límite por hora detuvo un correo electrónico; `retry_after` está en segundos. |
| `Test email sent by an administrator` | `info` | Salió un correo de prueba, con `admin_id` y `language`. |
| `Link emailed by an administrator` | `info` | Un administrador envió un enlace por correo electrónico: `admin_id`, `purpose` (`invite` o `password_reset`), `token_id`, el `user_id` de la cuenta para un enlace de restablecimiento, y `language`. |
| `Forgotten password: reset link emailed` | `info` | Salió un enlace de restablecimiento para una contraseña olvidada: `user_id`, `token_id` y `language`. |
| `Forgotten password: no active account matches, nothing sent` | `info` | Ninguna cuenta activa tiene ese nombre de usuario o dirección de correo electrónico. Lo que se escribió nunca se registra. |
| `Forgotten password: the account had a reset link moments ago, nothing sent` | `info` | Los límites de la propia cuenta: un enlace de restablecimiento hace menos de 5 minutos, o 3 en la última hora; con `user_id`. |
| `Forgotten password: an administrator's reset link is still live, nothing sent` | `info` | Una solicitud nunca cancela un enlace que un administrador dio a la cuenta; con `user_id`. |
| `Forgotten password: the hourly limit of the instance is reached, nothing sent` | `warning` | Se alcanzó el límite por hora después de la respuesta; con `user_id`. |
| `Forgotten password: the mailbox had reset emails moments ago, nothing sent` | `info` | Ese buzón ya había tenido 3 correos de restablecimiento en la última hora, incluidos los que no salieron; con `user_id`. |
| `Forgotten password: another request won the race, nothing sent` | `info` | Dos solicitudes para la cuenta en el mismo momento: la otra envía el correo electrónico; con `user_id`. |
| `Forgotten password: no email sent` | `warning` | El correo electrónico o `LIBREFOLIO_PUBLIC_URL` dejaron de funcionar después de la respuesta, o se rechazó el correo: `reason` y `code` indican cuál. Un enlace creado para ello se revoca. |
| `Forgotten password: the request failed` | `error` | Un error inesperado, con su tipo en `error` y nada más: ningún detalle de la solicitud llega al registro. |
| `Registration waits for email verification` | `info` | Una cuenta nueva espera su enlace; con `user_id`. La línea `User registered` del mismo registro tiene `waits_for_email` establecido en true. |
| `Verification email held: address limit or instance budget reached` | `info` | La dirección del registro ya había tenido sus `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` correos (20 de forma predeterminada) en la hora, o el límite por hora de la instancia está agotado: la cuenta espera sin su correo electrónico, y la página de inicio de sesión se lo indica a su propietario; con `user_id`. |
| `Verification link emailed` | `info` | Salió un enlace de verificación: `user_id`, `token_id` y `language`. |
| `Verification email: not sent` | `warning` | El correo electrónico de un registro no salió: `reason` y `code` dicen por qué. La página había dicho que el correo iba en camino, así que solo esta línea indica que no se envió. La cuenta sigue esperando, y su propietario puede volver a pedir el enlace. |
| `Verification email: the account no longer waits, nothing sent` | `info` | Un administrador activó, desactivó o eliminó la cuenta antes de que saliera su correo electrónico; con `user_id`. |
| `Verification email: the request failed` | `error` | Un error inesperado, con su tipo en `error` y el `user_id`, nada más. |
| `Login refused: email not verified` | `info` | Una cuenta en espera inició sesión con la contraseña correcta; con `user_id`. |
| `Verification resend refused: wrong credentials` | `warning` | Alguien pidió un nuevo enlace de verificación con una contraseña incorrecta, o para una cuenta que no existe. Ni lo que se escribió ni la dirección se registran. |
| `Email verified` | `info` | El propietario confirmó en la página del enlace: la cuenta está activa; `user_id` y `token_id`. |
| `Email verification refused: the link's email did not go out` | `info` | Alguien confirmó con un enlace cuyo correo electrónico LibreFolio contó como no enviado: la cuenta sigue esperando, y **Enviar el enlace de nuevo** funciona. |
| `Email verification refused: the link was sent to another address` | `info` | La dirección de la cuenta cambió después de enviarse el enlace: ese enlace deja de funcionar. |
| `Email change notice sent to the previous address` | `info` | El aviso se envió a la dirección anterior. La línea tiene `user_id` y `language`, y ninguna de las dos direcciones. |
| `Email change notice: email is off, nothing sent` | `info` | El correo electrónico está desactivado: no hay nada que enviar y nada va mal. |
| `Email change notice: past its limits, nothing sent` | `info` | La cuenta, o el buzón anterior, ya había tenido 3 avisos en la hora: el cambio se realizó, el aviso no. Con `user_id`. |
| `Email change notice: the account no longer exists, nothing sent` | `info` | La cuenta se eliminó antes de que saliera el correo electrónico. |
| `Email change notice: not sent` | `warning` | El correo electrónico está configurado pero no se puede usar ahora, se alcanzó el límite por hora, la dirección anterior no es una única dirección simple, o el envío falló: `reason` y `code` indican cuál. |
| `Email change notice: the request failed` | `error` | Un error inesperado, con su tipo en `error` y el `user_id`, nada más. |

Cada enlace de restablecimiento también deja una línea `Password reset link created`, con `user_id`, `token_id` y,
cuando lo creó un administrador, `created_by_user_id`.

Ninguna de estas líneas contiene la contraseña SMTP, el contenido de un correo electrónico, un enlace o su parte secreta,
lo que alguien escribió para pedir un enlace de restablecimiento o un nuevo enlace de verificación, ni la dirección completa
del destinatario: solo su dominio, en `recipient_domain`. Los servidores suelen citar la dirección que rechazan, así que
su respuesta también se enmascara, por ejemplo `550 5.1.1 <***@example.com>: Recipient address rejected`. El
aviso de un cambio de correo electrónico no nombra ni la dirección anterior ni la nueva.

---

## 🔒 Notas de seguridad {: #security }

- **`starttls` nunca recurre a texto sin cifrar.** Un servidor que no ofrece cifrado no recibe ni la contraseña ni el mensaje: el correo de prueba falla con `TLS_FAILED`.
- **El certificado siempre se comprueba**, con `starttls` y con `tls`: no hay ninguna opción para omitir la comprobación.
- **`none` envía todo en claro**: los mensajes, sus enlaces y la contraseña SMTP. Resérvalo para un servidor de retransmisión en tu propia máquina o red. Hacia cualquier otro servidor,
  Configuración › Administración › Correo electrónico muestra una advertencia: *Los correos electrónicos, sus enlaces y la contraseña SMTP viajan sin cifrar a un servidor fuera de la red local*; el registro de inicio también tiene una
  ([Qué dice el registro](#logs)).
- **Guarda la contraseña en un archivo secreto** (`LIBREFOLIO_SMTP_PASSWORD_FILE`) que solo pueda leer el usuario
  que ejecuta LibreFolio, fuera de `.env` y de la carpeta de datos. Usa una contraseña de aplicación, o una
  cuenta solo para LibreFolio, que puedas revocar por sí sola.
- **Los enlaces provienen solo de `LIBREFOLIO_PUBLIC_URL`**, nunca de una solicitud: nadie puede hacer que
  LibreFolio envíe por correo a uno de tus usuarios un enlace a un sitio de un tercero ([Correos electrónicos con enlace](email_flows.md#public-url)).
- **Un enlace de verificación solo va a la dirección de la propia cuenta**, y nadie lo ve, incluido un
  administrador. **Enviar el enlace de nuevo** pide la contraseña de la cuenta, igual que el inicio de sesión,
  y un enlace nuevo detiene los anteriores.
- **Los nombres permanecen en una sola línea.** Un nombre de usuario, el nombre de quien invita o el nombre de la instancia
  se escriben en un correo electrónico en una sola línea: los caracteres de control y los saltos de línea se convierten en espacios, y los
  caracteres que reordenan el texto (controles bidireccionales) se eliminan. Un nombre de usuario manipulado no puede
  añadir líneas propias a un correo electrónico ni disimular su texto.
- **Sin palabras de desconocidos en un correo electrónico.** Un restablecimiento de contraseña, una verificación de correo electrónico y el aviso de un
  cambio de correo electrónico pueden enviarse, por alguien que no es administrador, a una dirección de su elección.
  Estos correos comienzan con un «Hola,» simple, sin el nombre de usuario, y el aviso no muestra ninguna parte de la
  nueva dirección: LibreFolio no resuelve nombres de dominio, así que incluso el final de un dominio puede elegirse libremente. Un enlace
  de restablecimiento que envíes por correo electrónico se redacta de la misma manera. El nombre de usuario sigue apareciendo una vez que se abre el enlace.
  Solo el correo de prueba y el enlace de configuración del administrador inicial saludan por su nombre: los envías
  tú, o quien ejecute el servidor.
- **El restablecimiento de contraseñas olvidadas no revela a nadie qué cuentas existen**: la misma respuesta para todos, la
  búsqueda después de la respuesta, y límites por dirección, por nombre de usuario o dirección de correo electrónico, por buzón y
  por cuenta ([Contraseñas olvidadas](email_flows.md#forgot-password)).
- **Cambiar la dirección de correo electrónico de una cuenta pide su contraseña actual.** Sin ella, bastaría un momento
  dentro de la sesión de alguien (una cookie de sesión robada, un ordenador que se dejó desbloqueado) para
  poner una dirección propia en la cuenta y luego restablecer su contraseña desde ahí: el restablecimiento por correo electrónico solo se
  habilitó junto con esta regla. Cuando el correo electrónico funciona, la dirección anterior también recibe un aviso
  ([Cambios de dirección de correo electrónico](email_flows.md#email-change-notice)).
- **El límite por hora** limita lo que la instancia puede enviar, pase lo que pase: auméntalo solo hasta donde lo necesites.

??? info "🏠 Qué se considera tu red local — cuándo aparece la advertencia"

    LibreFolio evalúa `LIBREFOLIO_SMTP_HOST` tal como está escrito, sin resolver el nombre. Por local se entiende:

    - `localhost`, o un nombre sin punto, como un servicio de Docker Compose (`smtp-relay`) o una
      máquina de tu LAN;
    - un nombre que termina en `.local`, `.lan`, `.home.arpa`, `.internal` o `.localhost`;
    - una dirección de loopback, privada o link-local, como `127.0.0.1`, `192.168.1.10` o
      `fd00::25`, o una dirección de Tailscale (`100.64.0.0/10`, `fd7a:115c:a1e0::/48`).

    Cualquier otro servidor recibe la advertencia, incluso uno de tu red conocido por un nombre completo como
    `relay.example.com`. Un nombre de Tailscale como `relay.tailnet.ts.net` también la recibe, mientras que su
    dirección `100.x` no.

---

## 🔗 Relacionado

- 📄 **[Correo electrónico](email.md)** — Dónde está la configuración, las variables, ejemplos, …
- 📄 **[Correo electrónico: enlaces y mensajes](email_flows.md)** — Correos electrónicos con enlace, enlaces enviados por un administrador, contraseñas olvidadas, …
