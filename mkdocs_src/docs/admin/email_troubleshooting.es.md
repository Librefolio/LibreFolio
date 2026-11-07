# 🛠️ Correo electrónico: cuando no funciona

Página de diagnóstico: los correos no salen.
Para cada error encuentras **qué ves**, **por qué** y **qué hacer**, con el lugar donde actúas.

Cómo configurar el correo electrónico y su correo de prueba: [Correo electrónico](email.md).
Los mensajes que envía LibreFolio: [Correo electrónico: enlaces y mensajes](email_flows.md).

---

## 🛠️ Cuando no funciona {: #troubleshooting }

Dos tipos de problema:

| Qué ves | Por qué | Dónde mirar |
| --- | --- | --- |
| Estado **No funciona** en cuanto abres la pestaña **Correo** | Una variable que LibreFolio no puede usar | [Problemas de configuración](#configuration-problems) |
| El error solo aparece al enviar un correo | El servidor SMTP rechaza el correo o no responde | [Errores de envío](#sending-errors) |

Una configuración que no se puede usar desactiva solo el correo electrónico: el servidor arranca como de costumbre y todo lo demás funciona.

Dónde actúas, en las tablas de esta página:

| Dónde | Qué | Después |
| --- | --- | --- |
| **`.env`** — el archivo `.env` de LibreFolio ([dónde está](email.md#where-it-lives)) | Las variables `LIBREFOLIO_SMTP_…` y `LIBREFOLIO_PUBLIC_URL` | Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`. |
| **Servidor SMTP** — el servidor o el proveedor | Inicio de sesión, remitentes permitidos, certificado, retransmisión | Prueba de nuevo el correo de prueba. |
| **Interfaz** — **Configuración › Administración › Correo**, [Perfil](../user/settings/profile.md), [Usuarios e invitaciones](users.md#actions) | Estado, correo de prueba, tu dirección, las cuentas | Sin reinicio. |
| **Registro** | La respuesta exacta del servidor y el código | [Qué dice el registro](#logs): dónde leerlo. |

### ⚙️ Problemas de configuración {: #configuration-problems }

**Dónde: el archivo `.env` de LibreFolio.** La pestaña **Correo** nombra la variable; el código está en el registro, justo después de `Starting LibreFolio`.
Después de cada corrección: reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.

| Qué ves (pestaña) | Código | Por qué | Qué hacer |
| --- | --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` no es un nombre de servidor válido… | `SMTP_HOST_INVALID` | No es solo un nombre o una dirección IP | `smtp.example.com`, no `smtp://smtp.example.com`, `smtp.example.com:587` ni `user@smtp.example.com`. El puerto va en `LIBREFOLIO_SMTP_PORT`; una dirección IPv6 sin corchetes. |
| `LIBREFOLIO_SMTP_TLS` debe ser starttls, tls o none. | `SMTP_TLS_INVALID` | Palabra no permitida | Una de las tres. Cifrado desde el primer byte, puerto 465: `tls`. |
| `LIBREFOLIO_SMTP_PORT` debe ser un número entero de 1 a 65535. | `SMTP_PORT_INVALID` | Fuera de rango o no numérico | Solo dígitos, o elimina la línea: se aplica el puerto del modo. |
| El archivo de la contraseña indicado por `LIBREFOLIO_SMTP_PASSWORD_FILE` no se puede leer. | `SMTP_PASSWORD_UNREADABLE` | El archivo no existe en esa ruta (con Docker, la ruta dentro del contenedor), el usuario que ejecuta LibreFolio no puede leerlo, está vacío o en blanco, no es UTF-8 o supera los 64 KiB | El registro dice cuál: sistema de archivos o ruta. |
| `LIBREFOLIO_SMTP_USER` está definida sola… (o `LIBREFOLIO_SMTP_PASSWORD`) | `SMTP_CREDENTIALS_INCOMPLETE` | Usuario sin contraseña o al revés. Una contraseña de `LIBREFOLIO_SMTP_PASSWORD_FILE` cuenta como `LIBREFOLIO_SMTP_PASSWORD` | Las dos, o ninguna. |
| Falta `LIBREFOLIO_SMTP_FROM`… | `SMTP_FROM_MISSING` | Obligatoria en cuanto defines un servidor | Añade el remitente. |
| `LIBREFOLIO_SMTP_FROM` debe ser una sola dirección… | `SMTP_FROM_INVALID` | Lista o salto de línea | Una dirección, con o sin nombre: `LibreFolio <noreply@example.com>`. |
| `LIBREFOLIO_SMTP_REPLY_TO` debe ser una sola dirección. | `SMTP_REPLY_TO_INVALID` | La misma regla que para el remitente | Una dirección, o elimina la línea. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` debe ser un número entero de al menos 1. | `SMTP_MAX_PER_HOUR_INVALID` | No es un número entero ≥ 1 | Solo dígitos, al menos `1`. Para dejar de enviar, elimina `LIBREFOLIO_SMTP_HOST` en su lugar. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` debe ser un número entero de al menos 1. | `SIGNUP_EMAILS_PER_ADDRESS_INVALID` | No es un número entero ≥ 1. Como las demás, desactiva el correo electrónico hasta que se corrija; el servidor arranca de todos modos | Solo dígitos, al menos `1`, o elimina la línea: valor predeterminado `20`. |

### 📤 Errores de envío {: #sending-errors }

El correo de prueba, en **Configuración › Administración › Correo**, dice por qué no salió.
La respuesta exacta del servidor está en el registro ([Qué dice el registro](#logs)).

| Qué ves (correo de prueba) | Código | Por qué | Qué hacer — dónde |
| --- | --- | --- | --- |
| LibreFolio no consigue conectar con el servidor SMTP… | `CONNECTION_FAILED` | Nombre del servidor, puerto o firewall. El nombre cuenta desde donde se ejecuta LibreFolio: en un contenedor, `localhost` es el propio contenedor | **`.env`**: `LIBREFOLIO_SMTP_HOST`, `LIBREFOLIO_SMTP_PORT`. **Red**: un firewall que rechaza la conexión. |
| La conexión segura ha fallado… | `TLS_FAILED` | El modo y el puerto no van juntos; con `starttls` el servidor no ofrece cifrado; certificado no válido o no emitido para el nombre de `LIBREFOLIO_SMTP_HOST` (uno autofirmado, o una IP en lugar del nombre, falla) | **`.env`**: `starttls` con 587, `tls` con 465; en `LIBREFOLIO_SMTP_HOST` el nombre del certificado. **Servidor SMTP**: un certificado válido. |
| El servidor SMTP ha rechazado el inicio de sesión… | `AUTH_FAILED` | Usuario o contraseña incorrectos. Un servidor sin inicio de sesión rechaza el inicio de sesión | **`.env`**: usuario y contraseña; con un proveedor, una contraseña de aplicación. Servidor sin inicio de sesión: elimina ambos. |
| El servidor SMTP ha rechazado la dirección del remitente… | `SENDER_REFUSED` | El servidor solo acepta las direcciones con las que tu cuenta puede enviar. Sin usuario, aun así puede exigir un inicio de sesión | **`.env`**: en `LIBREFOLIO_SMTP_FROM` una de esas direcciones, o añade el inicio de sesión. |
| El servidor SMTP ha rechazado tu dirección. | `RECIPIENT_REFUSED` | El correo electrónico de tu cuenta. Sin inicio de sesión, un servidor puede negarse a retransmitir a otros dominios: la respuesta en el registro lo indica | **Interfaz**: tu dirección en [Perfil](../user/settings/profile.md). **Servidor SMTP**: la retransmisión. |
| El servidor SMTP no ha respondido a tiempo. | `TIMEOUT` | Más allá de los 20 segundos que LibreFolio espera en cada paso: un firewall que descarta la conexión sin rechazarla, o `starttls` en el puerto 465 | **`.env`**: la pareja modo/puerto. **Red**: el firewall. |
| El servidor SMTP no ha aceptado el mensaje. | `SEND_FAILED` | El servidor rechazó el propio mensaje. Las letras fuera de ASCII antes de la `@`, como `zoë@example.com`, necesitan SMTPUTF8: sin él, el correo nunca sale de LibreFolio y el registro indica `SMTPNotSupportedError` | **Registro**: la respuesta del servidor dice por qué. **Servidor SMTP**: SMTPUTF8, o una dirección ASCII. |
| Se ha alcanzado el límite de … correos por hora… (estado), o Se ha alcanzado el límite de correos por hora: inténtalo de nuevo dentro de … min. (prueba) | `EMAIL_RATE_LIMITED` | Máximo de la hora alcanzado | Espera los minutos indicados. Para permitir más, **`.env`**: aumenta `LIBREFOLIO_SMTP_MAX_PER_HOUR` y reinicia. |
| El correo está desactivado o no funciona en esta instancia. | `EMAIL_UNAVAILABLE` | La configuración cambió desde que cargaste la pestaña, por ejemplo tras un reinicio | **Interfaz**: la pestaña muestra ahora el estado y su problema. |
| La dirección de tu cuenta no es una dirección de correo válida. | `EMAIL_RECIPIENT_INVALID` | El correo electrónico de tu cuenta | **Interfaz**: corrígelo en [Perfil](../user/settings/profile.md). |
| No se ha podido enviar el correo de prueba. | — | Ninguna respuesta conocida, por ejemplo un error de red | Recarga la página y mira el **registro**. |
| Correo de prueba enviado a tu dirección…, pero no llega nada | — | El servidor lo aceptó: a partir de ahí, la entrega es cosa suya. Un remitente de un dominio que no autoriza a ese servidor puede ser rechazado o acabar en el spam por el camino | Carpeta de spam, luego los **registros del servidor o del proveedor**. |

**No se ha podido leer el estado del correo.**: la pestaña no llegó al servidor. Recarga; si persiste, mira el registro.

**Enviar por correo**, en los diálogos de invitación y de restablecimiento, dice por qué no salió un enlace:

| Qué ves (diálogo) | Código | Por qué | Qué hacer — dónde |
| --- | --- | --- | --- |
| El correo está apagado o no funciona en esta instancia. | `EMAIL_UNAVAILABLE` | La configuración cambió desde que abriste el diálogo, por ejemplo tras un reinicio | **Interfaz**: [Configuración › Administración › Correo](email.md#email-tab). |
| Los correos no pueden llevar enlaces: LIBREFOLIO_PUBLIC_URL no está definida, o no puede iniciar un enlace. | `EMAIL_LINKS_UNAVAILABLE` | Falta el comienzo de los enlaces | **`.env`**: define `LIBREFOLIO_PUBLIC_URL` y reinicia ([Correos con un enlace](email_flows.md#public-url)). |
| Este enlace ya no funciona: crea uno nuevo. | `EMAIL_LINK_INVALID` | Enlace caducado, usado o revocado | **Interfaz**: crea un enlace nuevo y envía ese. |
| La cuenta no está activa: actívala antes de enviarle un enlace de restablecimiento. | `EMAIL_ACCOUNT_INACTIVE` | Cuenta desactivada | **Interfaz**: **Reactivar** en [Usuarios e invitaciones](users.md#actions); o **línea de comandos**: `user activate` ([CLI](cli_tools.md)). Luego vuelve a enviar el enlace. |
| Escribe la dirección a la que enviar la invitación. | `EMAIL_RECIPIENT_REQUIRED` | La invitación no tiene ninguna dirección | **Interfaz**: escribe una en **Enviar a**. |
| No es una sola dirección de correo válida. | `EMAIL_RECIPIENT_INVALID` | Dirección no válida. Para un restablecimiento, es la de la propia cuenta | **Interfaz**: corrige **Enviar a**. Para el restablecimiento, copia el enlace en su lugar. |
| Se alcanzó el límite de correos por hora: inténtalo de nuevo en … min. | `EMAIL_RATE_LIMITED` | Máximo de la hora alcanzado | Espera los minutos indicados. Para permitir más, **`.env`**: aumenta `LIBREFOLIO_SMTP_MAX_PER_HOUR` y reinicia. |
| El servidor SMTP ha rechazado la dirección del destinatario. | `RECIPIENT_REFUSED` | La dirección del enlace: **Enviar a** para una invitación, el correo electrónico de la cuenta para un restablecimiento. Sin inicio de sesión, un servidor puede negarse a retransmitir a otros dominios | **Interfaz**: la dirección. **Registro**: la respuesta del servidor. **Servidor SMTP**: la retransmisión. |
| Los demás mensajes del correo de prueba | `CONNECTION_FAILED`, `TLS_FAILED`, `AUTH_FAILED`, … | Como en la tabla anterior | Como en la tabla anterior. |
| No se pudo enviar el correo. | — | Ninguna respuesta conocida, por ejemplo un error de red | Recarga la página y mira el **registro**. |

`EMAIL_RECIPIENT_NOT_ALLOWED` (otra dirección para un enlace de restablecimiento) solo proviene de la API: el diálogo nunca lo devuelve.

### 📜 Qué dice el registro {: #logs }

**Dónde leerlo:**

| Instalación | Comando o archivo |
| --- | --- |
| Docker | `docker compose logs librefolio` |
| En el host | `logs/librefolio.log` en la carpeta de datos ([Estructura del sistema de archivos](filesystem.md)); el servidor también lo imprime en la consola |

En cada inicio, justo después de `Starting LibreFolio`, el servidor comprueba la configuración, incluido el correo electrónico ([Comprobaciones al arrancar](configuration_security.md#startup-checks)): una configuración que no se puede usar (las dos primeras líneas de abajo), `none` hacia un servidor fuera de tu red local (una línea), `LIBREFOLIO_PUBLIC_URL` ausente o no válida (una línea).
Ninguna de ellas impide el inicio.
Las mismas tres comprobaciones están en **Configuración › Administración › Seguridad**, se leen de nuevo cuando lo pides; un hallazgo enlaza con la [pestaña Correo](email.md#email-tab) (consulta «Seguridad» en [Configuración global](settings.md)).

**Inicio y envío**

| El registro dice | Nivel | Cuándo |
| --- | --- | --- |
| `Email configuration cannot be used: email stays off` | `error` | Una variable no se puede usar. Una vez por proceso del servidor, al inicio, con `variable`, `problem` (el código) y `reason`: la regla que incumple, o por qué no se puede leer el archivo de contraseña. |
| `LIBREFOLIO_SMTP_… cannot be used (SMTP_…): email stays off until it is fixed` | `error` | Al inicio, después de la línea anterior, con `check` establecido en `email.smtp`: las comprobaciones de inicio informan del mismo problema. |
| `LIBREFOLIO_SMTP_TLS=none with …: emails, their links and the SMTP password travel unencrypted; use starttls or tls` | `warning` | Al inicio, con `check` establecido en `email.smtp_encryption`: `none` hacia un servidor fuera de tu red local, que la línea nombra ([Notas de seguridad](#security)). |
| `LIBREFOLIO_PUBLIC_URL is not set: emails work, but none with a link (forgotten password, invitation, reset) can go out` | `info` | Al inicio, con `check` establecido en `email.links`: el correo electrónico funciona, pero `LIBREFOLIO_PUBLIC_URL` no está definida ([Correos con un enlace](email_flows.md#public-url)). |
| `LIBREFOLIO_PUBLIC_URL cannot start a link (it needs http:// or https:// and a host, with no user name, password, ? or #): no email with a link (forgotten password, invitation, reset) can go out` | `warning` | Al inicio, con `check` establecido en `email.links`: el correo electrónico funciona, pero la variable no puede iniciar un enlace ([Correos con un enlace](email_flows.md#public-url)). |
| `Email sent` | `info` | El servidor aceptó un correo; `kind` indica cuál: `test`, `invite`, `password_reset`, `email_verification`, `email_changed` o `email_change_confirmation`. |
| `Email not sent` | `warning` | El servidor rechazó el correo o no respondió: `code`, como en [Errores de envío](#sending-errors), y `detail`, la respuesta del propio servidor, la pista más precisa. |
| `Email not sent: the hourly limit of the instance is reached` | `warning` | El límite por hora detuvo un correo; `retry_after` está en segundos. |
| `Test email sent by an administrator` | `info` | Salió un correo de prueba, con `admin_id` y `language`. |
| `Link emailed by an administrator` | `info` | Un administrador envió un enlace por correo: `admin_id`, `purpose` (`invite` o `password_reset`), `token_id`, el `user_id` de la cuenta para un enlace de restablecimiento, y `language`. |

**Contraseñas olvidadas**

| El registro dice | Nivel | Cuándo |
| --- | --- | --- |
| `Forgotten password: reset link emailed` | `info` | Salió un enlace de restablecimiento: `user_id`, `token_id` y `language`. |
| `Forgotten password: no active account matches, nothing sent` | `info` | Ninguna cuenta activa tiene ese nombre de usuario o dirección de correo electrónico. Lo que se escribió nunca se registra. |
| `Forgotten password: the account had a reset link moments ago, nothing sent` | `info` | Los límites de la cuenta: un enlace de restablecimiento hace menos de 5 minutos, o 3 en la última hora; con `user_id`. |
| `Forgotten password: an administrator's reset link is still live, nothing sent` | `info` | Una solicitud nunca cancela un enlace dado por un administrador; con `user_id`. |
| `Forgotten password: the hourly limit of the instance is reached, nothing sent` | `warning` | Se alcanzó el límite por hora después de la respuesta; con `user_id`. |
| `Forgotten password: the mailbox had reset emails moments ago, nothing sent` | `info` | Ese buzón ya había tenido 3 correos de restablecimiento en la última hora, incluidos los que no salieron; con `user_id`. |
| `Forgotten password: another request won the race, nothing sent` | `info` | Dos solicitudes para la cuenta en el mismo momento: la otra envía el correo; con `user_id`. |
| `Forgotten password: no email sent` | `warning` | El correo electrónico o `LIBREFOLIO_PUBLIC_URL` dejaron de funcionar después de la respuesta, o se rechazó el correo: `reason` y `code` indican cuál. El enlace creado se revoca. |
| `Forgotten password: the request failed` | `error` | Un error inesperado, con su tipo en `error` y nada más: ningún detalle de la solicitud llega al registro. |

Cada enlace de restablecimiento también deja una línea `Password reset link created`, con `user_id`, `token_id` y, si lo creó un administrador, `created_by_user_id`.

**Verificación por correo electrónico**

| El registro dice | Nivel | Cuándo |
| --- | --- | --- |
| `Registration waits for email verification` | `info` | Una cuenta nueva espera su enlace; con `user_id`. La línea `User registered` del mismo registro tiene `waits_for_email` establecido en true. |
| `Verification email held: address limit or instance budget reached` | `info` | La dirección ya había recibido sus `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` correos (20 de forma predeterminada) en la hora, o el límite por hora de la instancia está agotado: la cuenta espera sin su correo, y la página de inicio de sesión se lo indica a su propietario; con `user_id`. |
| `Verification link emailed` | `info` | Salió un enlace de verificación: `user_id`, `token_id` y `language`. |
| `Verification email: not sent` | `warning` | El correo de un registro no salió: `reason` y `code` dicen por qué. La página había dicho que el correo iba en camino: solo esta línea indica que no salió. La cuenta sigue esperando; el propietario puede volver a pedir el enlace. |
| `Verification email: the account no longer waits, nothing sent` | `info` | Un administrador activó, desactivó o eliminó la cuenta antes de que saliera el correo; con `user_id`. |
| `Verification email: the request failed` | `error` | Un error inesperado, con su tipo en `error` y el `user_id`, nada más. |
| `Login refused: email not verified` | `info` | Una cuenta en espera inició sesión con la contraseña correcta; con `user_id`. |
| `Verification resend refused: wrong credentials` | `warning` | Solicitud de un nuevo enlace de verificación con una contraseña incorrecta, o para una cuenta que no existe. Ni lo que se escribió ni la dirección se registran. |
| `Email verified` | `info` | El propietario confirmó en la página del enlace: la cuenta está activa; `user_id` y `token_id`. |
| `Email verification refused: the link's email did not go out` | `info` | Confirmación con un enlace cuyo correo LibreFolio contó como no enviado: la cuenta sigue esperando, y **Enviar el enlace de nuevo** funciona. |
| `Email verification refused: the link was sent to another address` | `info` | La dirección de la cuenta cambió después de enviarse el enlace: ese enlace deja de funcionar. |

**Cambio de dirección de correo electrónico**

| El registro dice | Nivel | Cuándo |
| --- | --- | --- |
| `Email change notice sent to the previous address` | `info` | El aviso fue a la dirección anterior. La línea tiene `user_id` y `language`, ninguna de las dos direcciones. |
| `Email change notice: email is off, nothing sent` | `info` | El correo electrónico está desactivado: nada que enviar, nada va mal. |
| `Email change notice: past its limits, nothing sent` | `info` | La cuenta, o el buzón anterior, ya había recibido 3 avisos en la hora: el cambio se realizó, el aviso no. Con `user_id`. |
| `Email change notice: the account no longer exists, nothing sent` | `info` | La cuenta se eliminó antes de que saliera el correo. |
| `Email change notice: not sent` | `warning` | El correo electrónico está configurado pero no se puede usar ahora, se alcanzó el límite por hora, la dirección anterior no es una única dirección simple, o el envío falló: `reason` y `code` indican cuál. |
| `Email change notice: the request failed` | `error` | Un error inesperado, con su tipo en `error` y el `user_id`, nada más. |

Ninguna de estas líneas contiene la contraseña SMTP, el contenido de un correo, un enlace o su parte secreta, lo que alguien escribió para pedir un enlace de restablecimiento o de verificación, ni la dirección completa del destinatario: solo su dominio, en `recipient_domain`.
La respuesta del servidor también se enmascara, porque a menudo cita la dirección rechazada: `550 5.1.1 <***@example.com>: Recipient address rejected`.
El aviso de un cambio de correo electrónico no nombra ni la dirección anterior ni la nueva.

---

## 🔒 Notas de seguridad {: #security }

- **`starttls` nunca recurre a texto sin cifrar.** Un servidor que no ofrece cifrado no recibe ni la contraseña ni el mensaje: el correo de prueba falla con `TLS_FAILED`.
- **El certificado siempre se comprueba**, con `starttls` y con `tls`: ninguna opción lo omite.
- **`none` envía todo en claro**: mensajes, enlaces y la contraseña SMTP. Úsalo solo para una retransmisión en tu propia máquina o red. Hacia cualquier otro servidor, Configuración › Administración › Correo muestra una advertencia: *Los correos, sus enlaces y la contraseña SMTP viajan sin cifrar a un servidor fuera de la red local*; el registro de inicio también tiene una ([Qué dice el registro](#logs)).
- **Guarda la contraseña en un archivo secreto** (`LIBREFOLIO_SMTP_PASSWORD_FILE`) que solo pueda leer el usuario que ejecuta LibreFolio, fuera de `.env` y de la carpeta de datos. Usa una contraseña de aplicación, o una cuenta solo para LibreFolio, que puedas revocar por separado.
- **Los enlaces provienen solo de `LIBREFOLIO_PUBLIC_URL`**, nunca de una solicitud: nadie puede hacer que LibreFolio envíe a uno de tus usuarios un enlace a un sitio de terceros ([Correos con un enlace](email_flows.md#public-url)).
- **Un enlace de verificación va solo a la dirección de la propia cuenta**, y nadie lo ve, administrador incluido. **Enviar el enlace de nuevo** pide la contraseña de la cuenta, como el inicio de sesión, y un enlace nuevo desactiva los anteriores.
- **Los nombres se quedan en una sola línea.** El nombre de usuario, el nombre de quien invita y el nombre de la instancia entran en un correo en una sola línea: los caracteres de control y los saltos de línea se convierten en espacios, y los controles bidireccionales se eliminan. Un nombre de usuario manipulado no puede añadir líneas a un correo ni disfrazar su texto.
- **Ninguna palabra de un desconocido en un correo.** El restablecimiento de contraseña, la verificación del correo y el aviso de cambio de dirección pueden enviarse, por alguien que no es administrador, a una dirección de su elección. Estos correos empiezan con un simple «Hola:», sin el nombre de usuario, y el aviso no muestra ninguna parte de la nueva dirección: LibreFolio no resuelve dominios, así que incluso el final de una dirección se elige libremente. Un enlace de restablecimiento que envías por correo se escribe igual; el nombre de usuario aparece una vez abierto el enlace. Solo el correo de prueba y el enlace de configuración del administrador inicial saludan por el nombre: los envías tú, o quien gestiona el servidor.
- **Las contraseñas olvidadas no dicen a nadie qué cuentas existen**: la misma respuesta para todos, la búsqueda después de la respuesta, y límites por dirección, por nombre de usuario o dirección de correo, por buzón y por cuenta ([Contraseñas olvidadas](email_flows.md#forgot-password)).
- **Cambiar la dirección de correo de una cuenta requiere su contraseña actual.** Sin ella, un momento dentro de la sesión de alguien (una cookie de sesión robada, un ordenador sin bloquear) bastaría para poner una dirección propia en la cuenta y luego restablecer su contraseña: el restablecimiento por correo existe solo junto con esta regla. Cuando el correo funciona, la dirección anterior también recibe un aviso ([Cambios de dirección de correo electrónico](email_flows.md#email-change-notice)).
- **El límite por hora** limita lo que la instancia puede enviar, pase lo que pase: auméntalo solo hasta donde lo necesites.

??? info "🏠 Qué cuenta como tu red local — cuándo aparece la advertencia"

    LibreFolio juzga `LIBREFOLIO_SMTP_HOST` tal como está escrito, sin resolver el nombre. Local significa:

    - `localhost`, o un nombre sin punto, como un servicio de Docker Compose (`smtp-relay`) o una
      máquina de tu LAN;
    - un nombre que termina en `.local`, `.lan`, `.home.arpa`, `.internal` o `.localhost`;
    - una dirección de loopback, privada o de enlace local, como `127.0.0.1`, `192.168.1.10` o
      `fd00::25`, o una dirección de Tailscale (`100.64.0.0/10`, `fd7a:115c:a1e0::/48`).

    Cualquier otro servidor recibe la advertencia, incluso uno de tu red conocido por un nombre completo como
    `relay.example.com`. Un nombre de Tailscale como `relay.tailnet.ts.net` también la recibe, mientras que su
    dirección `100.x` no.

---

## 🔗 Relacionado

- 📄 **[Correo electrónico](email.md)** — Dónde se encuentra la configuración, Las variables, Ejemplos, …
- 📄 **[Correo electrónico: enlaces y mensajes](email_flows.md)** — Correos con un enlace, Enlaces enviados por un administrador, Contraseñas olvidadas, …
