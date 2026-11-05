# 📬 Correo electrónico: enlaces y mensajes

Esta página cubre los mensajes que LibreFolio envía una vez que el correo electrónico funciona: los **enlaces** para invitaciones y restablecimientos de contraseña, **contraseñas olvidadas**, los **límites** de esos correos, la **verificación** de nuevas direcciones y el aviso de un **cambio de dirección**.

El correo electrónico debe funcionar primero: las variables SMTP, la pestaña **Correo electrónico** y el correo de prueba están en [Correo electrónico](email.md), y qué comprobar cuando un mensaje no sale está en [Correo electrónico: cuando no funciona](email_troubleshooting.md).

---

## 🌐 Correos con un enlace {: #public-url }

Un enlace de invitación o de restablecimiento de contraseña enviado por correo electrónico se construye solo a partir de `LIBREFOLIO_PUBLIC_URL`: esa dirección, y luego la página que recibe el enlace, como `https://librefolio.example.com/reset-password#token=…`. Nunca a partir de la dirección que usó tu navegador, ni de cualquier otra cosa de una solicitud.

- **Por qué.** Cualquiera puede enviar a LibreFolio una solicitud que indique otra dirección. Si un enlace se construyera a partir de la solicitud, un desconocido podría hacer que LibreFolio envíe por correo a uno de tus usuarios un enlace real a un sitio suyo, y capturar su parte secreta cuando el usuario lo abra.
- **Qué configurar.** La dirección en la que tus usuarios abren LibreFolio, con `http://` o `https://` y un nombre de host, como `https://librefolio.example.com`: sin nombre de usuario ni contraseña, sin `?` ni `#`, sin espacios. Es la misma variable que la línea de comandos antepone a los enlaces que imprime: consulta [Cuentas y altas](configuration_accounts.md#accounts).
- **Sin ella**, o con una dirección que incumpla estas reglas, no sale ningún correo con un enlace: dicho correo se rechaza con `EMAIL_LINKS_UNAVAILABLE`, mientras que el correo de prueba sigue funcionando, y **Requerir verificación por correo electrónico** no se puede activar ([Verificación por correo electrónico](#verification)). Los enlaces que copias, por ejemplo desde la [línea de comandos](cli_tools.md), permanecen como están.
- **Qué dice el correo electrónico**: nombra tu instancia por el host de `LIBREFOLIO_PUBLIC_URL`, e indica cuánto tiempo sigue funcionando el enlace: 7 días para una nueva invitación, 30 minutos para un enlace de restablecimiento, 24 horas para un enlace de verificación, 72 horas para el enlace de configuración del administrador inicial. Un enlace funciona una sola vez.
- **La parte secreta** del enlace va después de `#`: los navegadores nunca la envían al servidor, así que queda fuera de los registros del servidor y del proxy.
- **Para comprobarlo**: con el correo electrónico **Listo**, Configuración › Administración › Correo electrónico muestra un aviso cuando `LIBREFOLIO_PUBLIC_URL` no está definida o no se puede usar, y el registro de inicio tiene una línea ([Qué dice el registro](email_troubleshooting.md#logs)). Una vez que se puede usar, la pestaña muestra la dirección y comprueba, desde tu navegador, que esta instancia responde allí: consulta [La dirección en los enlaces enviados por correo](email.md#links-check). Desde cualquier lugar, `/api/v1/system/instance` muestra `"links": true` cuando tanto el correo electrónico como la dirección están bien.

---

## 📨 Enlaces enviados por un administrador {: #admin-links }

Un enlace de invitación o de restablecimiento de contraseña que crea un administrador puede salir por correo electrónico, en lugar de copiarse a mano. Mientras el correo electrónico está **Listo** y `LIBREFOLIO_PUBLIC_URL` se puede usar ([Correos con un enlace](#public-url)), los diálogos de invitación y restablecimiento de [Usuarios e invitaciones](users.md#send-by-email) muestran **Enviar por correo electrónico** bajo el enlace:

1. Crea el enlace como de costumbre: **Invitar**, o **Enlace de restablecimiento de contraseña** en la fila de la persona.
2. Para una invitación, comprueba la dirección en **Enviar a**: empieza por la escrita en la invitación y puedes cambiarla. Un enlace de restablecimiento no tiene campo: va a la dirección de su cuenta.
3. Para una invitación, elige el **Idioma del correo electrónico**: **El idioma de la instancia** lo escribe en el **Idioma predeterminado** de la instancia ([Configuración global](settings.md)); elige English, Italiano, Français o Español para alguien que lea otro. Un enlace de restablecimiento va en el idioma de su cuenta. Para establecer el **Idioma predeterminado** antes de que ningún administrador lo haya guardado, pon `LIBREFOLIO_DEFAULT_LANGUAGE` en el archivo `.env` (`en`, `it`, `fr` o `es`): consulta [Variables de entorno](configuration_accounts.md#accounts).
4. Haz clic en **Enviar por correo electrónico**. El diálogo dice *Enviado a …* con la dirección y el idioma en que se escribió el correo electrónico, o por qué no salió el correo ([Errores de envío](email_troubleshooting.md#sending-errors)).

Las reglas:

- **El enlace del correo electrónico empieza por `LIBREFOLIO_PUBLIC_URL`**, sea cual sea la **Dirección del servidor** que muestre el diálogo: solo la parte secreta del enlace viaja desde el diálogo. El diálogo lo indica encima del botón.
- **Una invitación** va a la dirección de **Enviar a**, o si no, a la escrita en la invitación, en el idioma elegido en **Idioma del correo electrónico**, el **Idioma predeterminado** de la instancia salvo que hayas elegido otro. Es solo el idioma del correo electrónico: no se convierte en el idioma de la cuenta que crea la invitación. Te identifica como la persona que invita, y lo indica cuando la nueva cuenta vaya a ser administradora.
- **Un enlace de restablecimiento de contraseña** va solo a la dirección de su cuenta, en el idioma de la cuenta, y solo mientras la cuenta está activa.
- **Solo sale un enlace vigente**: uno que haya caducado, se haya usado o se haya revocado se rechaza, y se debe crear uno nuevo.
- Cada correo electrónico cuenta para el límite por hora.

---

## 🗝️ Contraseñas olvidadas {: #forgot-password }

Alguien que olvidó su contraseña puede solicitar un enlace de restablecimiento por correo electrónico, con su nombre de usuario o su dirección de correo, sin iniciar sesión. En la página de inicio de sesión, **¿Olvidaste tu contraseña?** abre un formulario para ello mientras puedan salir correos electrónicos con un enlace: correo electrónico **Listo** y un `LIBREFOLIO_PUBLIC_URL` utilizable. Debajo del formulario, un panel cerrado hasta que se hace clic conserva el comando que un administrador puede ejecutar en el servidor. De lo contrario, la página muestra ese comando, abierto, bajo la advertencia *La recuperación por correo electrónico no está disponible en esta instancia. Restablece tu contraseña desde la terminal del servidor o pide a tu administrador un enlace de restablecimiento de contraseña.* Cuando la página no puede leer la configuración de la instancia desde el servidor, muestra solo el consejo *Pide a tu administrador un enlace de restablecimiento de contraseña: puede crear uno para tu cuenta.* Un administrador crea ese enlace en **Configuración › Administración › Usuarios**, incluso sin correo electrónico ([Enlaces de restablecimiento de contraseña](users.md#reset-links)).

Es seguro porque cambiar la dirección de correo electrónico de una cuenta pide su contraseña actual ([Perfil](../user/settings/profile.md)): consulta [Notas de seguridad](email_troubleshooting.md#security).

Funciona así:

- **La misma respuesta para todos**: *Si coincide una cuenta activa, su propietario recibe un correo electrónico con un enlace para elegir una nueva contraseña*, coincida o no una cuenta. La búsqueda de la cuenta y el correo electrónico se producen después de la respuesta, así que nadie puede usarla para averiguar qué cuentas existen.
- **La cuenta** se encuentra como la encuentra el inicio de sesión, por nombre de usuario o dirección de correo electrónico. Solo una cuenta activa recibe el correo electrónico, en su propia dirección y en su idioma.
- **El enlace** funciona una vez, durante 30 minutos, y sustituye los enlaces de restablecimiento que solicitudes anteriores enviaron a la cuenta. Mientras sigue vigente un enlace de restablecimiento creado por un administrador, no se envía nada: una solicitud nunca lo cancela.
- **Cuando el correo electrónico o `LIBREFOLIO_PUBLIC_URL` no están listos**, la solicitud se rechaza con un mensaje breve, el mismo para todos.

Los límites:

| Límite | Al superarlo |
| --- | --- |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` solicitudes por hora (20 de forma predeterminada) desde la misma dirección, un recuento compartido con las altas y **Enviar el enlace de nuevo** ([Límites de los correos de activación y restablecimiento de contraseña](#activation-limits)); una dirección IPv6 cuenta por su /64, el bloque que suele tener un abonado | La solicitud se rechaza hasta que se libere un lugar en ese recuento, o en el límite por hora de la instancia si este tarda más; la respuesta indica cuánto tiempo. |
| 3 solicitudes por hora para el mismo nombre de usuario o dirección de correo electrónico, coincida o no una cuenta | La solicitud se rechaza hasta que la más antigua de ellas tenga una hora. |
| El límite por hora de la instancia, `LIBREFOLIO_SMTP_MAX_PER_HOUR` | La solicitud se rechaza hasta que vuelva a caber un correo electrónico. |
| 3 correos electrónicos por hora al mismo buzón, para cualquier cuenta y sin importar cómo se escriba su dirección | No se envía nada y la respuesta sigue siendo la misma. |
| 1 correo electrónico cada 5 minutos, y 3 por hora, para la misma cuenta, incluidos los enlaces de restablecimiento creados por un administrador | No se envía nada y la respuesta sigue siendo la misma. Dos solicitudes en el mismo momento no pueden enviarse ambas. |

El límite por cuenta se basa en los enlaces de restablecimiento de la cuenta guardados en la base de datos. Los demás se guardan en la memoria de cada proceso del servidor: con varios procesos, cada uno mantiene su propio recuento, y un reinicio los olvida. Un correo de restablecimiento que no salió sigue contando, para la cuenta y para el buzón.

**Un mismo buzón, se escriba como se escriba su dirección.** El límite por buzón cuenta los alias de una dirección como un solo buzón: no cuentan las mayúsculas, ni una etiqueta `+tag` en cualquier dominio (`name+news@example.com` es `name@example.com`), ni los puntos de una dirección de Gmail, donde `googlemail.com` es `gmail.com` (`first.last@googlemail.com` es `firstlast@gmail.com`). Los límites de los [correos de verificación](#verification-limits) y de los [avisos de un cambio de correo electrónico](#email-change-notice) cuentan de la misma manera. Cada correo electrónico sigue yendo a la dirección exactamente como la tiene la cuenta. Un buzón que acepta correo con cualquier nombre, como un dominio comodín o `anything@user.fastmail.com` de Fastmail, cuenta cada nombre por separado: solo el límite por hora de la instancia los frena.

**Detrás de un proxy inverso**, la dirección que cuenta es la del visitante, tal como la lee LibreFolio (consulta [La dirección del visitante](connection_proxy.md#client-address)):

- Cuando `LIBREFOLIO_CLIENT_IP_HEADER` nombra el encabezado que tu proxy establece con la dirección del visitante (`Fly-Client-IP` en Fly.io, `X-Real-IP` de Nginx), LibreFolio lo lee allí. Establécelo solo si todas las solicitudes pasan por ese proxy: un visitante que llegue directamente a LibreFolio podría escribir el encabezado.
- De lo contrario, es la dirección que ve el servidor (uvicorn), que toma la dirección del visitante del encabezado `X-Forwarded-For` del proxy solo cuando la dirección del proxy está listada en `FORWARDED_ALLOW_IPS` (`127.0.0.1` cuando no se establece). Lista allí las direcciones o redes de tu proxy, como `172.18.0.0/16`, nunca `*`: con `*`, uvicorn toma la primera dirección del encabezado, que el visitante puede escribir.
- **Un proxy en el que LibreFolio no confía, en una dirección local** (una red de Docker, tu propia red o tu VPN), como un contenedor de proxy delante de la imagen de Docker, la configuración habitual: estos límites por dirección dejan fuera las solicitudes que pasan por él, para que las solicitudes de un visitante no puedan agotar el recuento de **¿Olvidaste tu contraseña?**, **Enviar el enlace de nuevo** y las altas para todos. Los límites por nombre de usuario o dirección de correo electrónico, por cuenta y por buzón, y el límite por hora de la instancia, sí las cuentan. El registro advierte una vez por proceso del servidor, y las comprobaciones de seguridad lo notifican como una advertencia de `platform.client_address` (consulta [La dirección del visitante](connection_proxy.md#client-address)).
- **Un proxy en el que LibreFolio no confía, en una dirección pública**, como una CDN: todos los visitantes comparten la dirección del proxy y su recuento, así que las primeras `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` solicitudes de cualquiera agotan el recuento de esas solicitudes a través del proxy para todos, durante hasta una hora. Informa a LibreFolio sobre el proxy.

---

## 🚦 Límites de los correos de activación y restablecimiento de contraseña {: #activation-limits }

Los correos electrónicos que activan una cuenta y los que restablecen una contraseña están limitados por **dos contadores**, los mismos para todas las formas de solicitarlos. Cada uno cuenta durante los últimos 60 minutos, en la memoria de cada proceso del servidor.

| Contador | Variable | Valor predeterminado | Qué cuenta |
| --- | --- | --- | --- |
| **Por dirección** | `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | 20 por hora | Los correos electrónicos que salen para una dirección de cliente (una dirección IPv6 por su /64), en un solo recuento: las altas, cada **Enviar el enlace de nuevo** con la contraseña correcta y cada **¿Olvidaste tu contraseña?** para una cuenta que existe. Los intentos no se cuentan: una contraseña incorrecta, una solicitud para un nombre que ninguna cuenta tiene, o una rechazada por otro límite no le cuestan nada |
| **Por instancia** | `LIBREFOLIO_SMTP_MAX_PER_HOUR` | 50 por hora | Cada correo electrónico que envía la instancia: activaciones, restablecimientos, invitaciones, avisos |

Tres límites más permanecen como están. No son contadores de correos de activación, y rara vez importan para una cuenta cuyo correo electrónico fue retenido, ya que todavía no ha llegado nada a su buzón:

- el límite de inicio de sesión sobre **contraseñas incorrectas** ([Inicios de sesión fallidos](configuration_accounts.md#login-limit)), que **Enviar el enlace de nuevo** comparte con la página de inicio de sesión;
- **3 correos electrónicos por hora al mismo buzón**, para que LibreFolio no pueda usarse para inundar la dirección de otra persona;
- **1 correo electrónico cada 5 minutos, y 3 por hora, para la misma cuenta**, para **Enviar el enlace de nuevo**.

El contador por dirección cuenta **correos electrónicos que salen**, no intentos. Se consulta primero, así que una solicitud se rechaza de inmediato, antes de comprobar la contraseña, cuando el recuento está lleno; se consume en el último momento, cuando el correo electrónico está a punto de salir, y no por ninguna otra cosa: las contraseñas incorrectas tienen su propio límite, una solicitud para un nombre que ninguna cuenta tiene no cuesta nada (y, para **¿Olvidaste tu contraseña?**, la respuesta es la misma tanto si coincide una cuenta como si no), y un **Enviar el enlace de nuevo** rechazado por el límite por cuenta o por buzón no consume nada. Un correo electrónico que luego rechaza el servidor SMTP sigue contado: se intentó.

Cuando un contador frena una solicitud, la respuesta indica cuántos segundos esperar, y ese tiempo es real: es la **mayor** de las esperas de los contadores que la frenaron, así que la misma solicitud hecha entonces se acepta, a menos que otros de la misma red hayan usado el lugar mientras tanto (la respuesta entonces indica el nuevo tiempo).

**Un ejemplo.** Una oficina con una dirección de internet y un límite de 20. Veinte compañeros se registran entre las 9:00 y las 9:40, y sus veinte correos electrónicos salen. A las 9:45 se registra el 21.º, Mario: su cuenta se crea, pero su correo electrónico queda retenido, y la página le dice que lo intente de nuevo en unos 15 minutos, el tiempo hasta que el correo de las 9:00 salga del recuento a las 10:00. A las 9:46 inicia sesión y solicita el enlace de nuevo: el mismo contador lo rechaza, durante 14 minutos. A las 10:00 vuelve a solicitarlo con su nombre de usuario y contraseña, y el enlace sale.

El contador por dirección se comparte a propósito, con una consecuencia que conviene conocer: cuando una red ha agotado su recuento con altas, **¿Olvidaste tu contraseña?** desde esa red también espera, hasta que se libere un lugar. Aumenta `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` para una red donde muchas personas se dan de alta juntas, como una escuela o una oficina, y reinicia.

---

## ✅ Verificación por correo electrónico {: #verification }

Con **Requerir verificación por correo electrónico** activado, una cuenta nueva no puede iniciar sesión hasta que su propietario confirme la dirección con un enlace que LibreFolio envía por correo electrónico a la cuenta. El interruptor está en **Configuración › Administración › Configuración global**, en la categoría **Seguridad** ([Configuración global](settings.md)), y está desactivado de forma predeterminada.

- **Quién espera**: cada cuenta creada desde la página de alta mientras el interruptor está activado, incluidas las abiertas con una invitación. La primera cuenta de una nueva instancia, su administrador, nunca espera, ni tampoco el administrador que LibreFolio crea a partir de `LIBREFOLIO_ADMIN_EMAIL`, al que activa su enlace de configuración; tampoco las cuentas creadas con `user create` en la [línea de comandos](cli_tools.md), ni las cuentas que ya existen.
- **Justo después del alta**, la página de inicio de sesión dice: *Cuenta creada. Te estamos enviando un correo electrónico con un enlace para activarla: ábrelo en un plazo de 24 horas y luego inicia sesión. ¿No llega ningún correo tras unos minutos? Revisa la carpeta de spam y luego inicia sesión con tu nombre de usuario y contraseña: se te ofrecerá un nuevo enlace.* Cuando desde la dirección del cliente ya se han agotado los correos correspondientes a `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` altas (20 de forma predeterminada) en la última hora, o se ha agotado el límite por hora de la instancia, no sale ningún correo, y la página lo indica en su lugar, con cuánto tiempo esperar: *Cuenta creada, pero el correo de activación no ha podido salir ahora. Inténtalo de nuevo en unos N minutos: inicia sesión con tu nombre de usuario y contraseña, y se te ofrecerá un nuevo enlace.* N es real: es el tiempo hasta que ambos contadores admitan un nuevo correo electrónico ([Límites de los correos de activación y restablecimiento de contraseña](#activation-limits)). Detrás de un proxy inverso en el que LibreFolio no confía, en una dirección local (la configuración habitual de Docker), no se cuenta nada por dirección, así que este segundo texto nunca aparece ([Contraseñas olvidadas](#forgot-password)). En cualquier caso, la cuenta se crea y espera.
- **El correo electrónico**, *Confirma tu dirección de correo electrónico*, sale justo después de esa respuesta, a menos que un límite lo retenga ([Límites de los correos de verificación](#verification-limits)), en el **Idioma predeterminado** de la instancia: una cuenta nueva aún no tiene idioma propio. Su botón, **Confirmar mi dirección de correo electrónico**, abre un enlace que empieza por `LIBREFOLIO_PUBLIC_URL` ([Correos con un enlace](#public-url)) y funciona una vez, durante 24 horas.
- **Hasta que se confirme la dirección**, la cuenta no puede iniciar sesión. Iniciar sesión con la contraseña correcta indica que la dirección aún no está verificada y ofrece **Enviar el enlace de nuevo**: un nuevo enlace, que detiene los anteriores. Con una contraseña incorrecta, el inicio de sesión da su rechazo habitual, así que nadie averigua más que con cualquier otro intento.
- **Una vez que el propietario confirma**, la cuenta está activa, y su propietario vuelve a la página de inicio de sesión con una confirmación. Lo que ve la persona, paso a paso: *Si LibreFolio te pide que confirmes tu correo electrónico* en [Primeros pasos](../user/getting-started.md).
- **Abrir el enlace no confirma nada**: muestra una página de LibreFolio con un botón, **Confirmar mi dirección de correo electrónico**, y solo el clic en él consume el enlace. El motivo son los filtros de correo que analizan enlaces, como Microsoft Defender Safe Links: abren los enlaces de un mensaje en un navegador que ejecuta scripts, y si bastara con abrirlo, el filtro activaría la cuenta en lugar de su propietario. Esa apertura no consume nada; el enlace sigue siendo válido para su propietario. Quien abre un enlace sin haberse dado de alta solo tiene que cerrar la página.

### 🔀 Activarlo y desactivarlo {: #verification-switch }

- **Solo se activa mientras puedan salir correos electrónicos con un enlace**: correo electrónico **Listo** ([Configuración › Administración › Correo electrónico](email.md#email-tab)) y un `LIBREFOLIO_PUBLIC_URL` utilizable ([Correos con un enlace](#public-url)). Hasta entonces, mientras está desactivado, el interruptor aparece atenuado, con la indicación *Necesita que salga un correo electrónico con un enlace: configura primero SMTP y LIBREFOLIO_PUBLIC_URL (Configuración › Administración › Correo electrónico).* Si eso cambia entre el momento en que abres la pestaña y tu guardado, el guardado se rechaza — *La verificación por correo electrónico necesita que salga un correo electrónico con un enlace, y ahora no puede salir ninguno: comprueba Configuración › Administración › Correo electrónico.* — y no se almacena nada de ello.
- **Desactivarlo siempre funciona.** Las cuentas que ya están esperando siguen esperando: sus enlaces siguen funcionando, y también **Enviar el enlace de nuevo**. Para dejar entrar una de inmediato, actívala ([Cuentas en espera](#verification-waiting)).
- **Mientras está activado, guardar el resto de la configuración siempre funciona**, incluso cuando el correo electrónico ha dejado de funcionar desde entonces.
- **Si el correo electrónico deja de funcionar mientras está activado** —el servidor o una variable falla—, nadie puede darse de alta ya, ni siquiera con una invitación, que sigue siendo válida: la página de alta dice *El alta no es posible en este momento: esta instancia no puede enviar el correo de verificación. Inténtalo más tarde o pregunta a su administrador.*, y no se crea ninguna cuenta. Solo se deja pasar la primera cuenta de una nueva instancia. **Enviar el enlace de nuevo** falla de la misma manera. Arregla el correo electrónico ([Cuando no funciona](email_troubleshooting.md#troubleshooting)) o desactiva el interruptor.

### ⏳ Cuentas en espera {: #verification-waiting }

En **Configuración › Administración › Usuarios**, una cuenta en espera muestra la insignia **Esperando verificación**, no **Desactivada**, incluso una vez que su enlace ha caducado. Pasa el cursor sobre la insignia, o abre la fila, para ver la indicación: su propietario aún no ha abierto el enlace, iniciar sesión ofrece uno nuevo, y **Reactivar** deja entrar la cuenta de inmediato.

- **Ocupa un lugar** del límite de usuarios (`LIBREFOLIO_MAX_USERS`) mientras su enlace está vigente, como una invitación abierta. Cuando caduca el último enlace enviado, 24 horas después, el lugar vuelve a quedar libre, y **Enviar el enlace de nuevo** entonces necesita un lugar libre: en una instancia llena, a su propietario se le dice que te lo pida.
- **Para dejarla entrar sin el correo electrónico**, haz clic en **Reactivar** en su fila ([Cuentas en espera de su correo electrónico](users.md#waiting)) o ejecuta `user activate` en la [línea de comandos](cli_tools.md): puede iniciar sesión de inmediato y los enlaces ya enviados dejan de funcionar. Mientras su enlace está vigente, esto no ocupa un lugar adicional, ya que su lugar ya está contado: **Reactivar** funciona incluso en una instancia llena, y `user activate` no imprime ninguna advertencia de límite. Una vez que el enlace ha caducado, reactivarla necesita un lugar libre, como cualquier cuenta desactivada.
- **Para rechazarla**, elimínala ([Eliminar una cuenta](users.md#delete)) o desactívala: con `user deactivate` en la línea de comandos, o con la API de administración (`PATCH /api/v1/users/{id}` con `is_active: false`). Desactivada, deja de esperar: sus enlaces dejan de funcionar, su lugar queda libre, su fila muestra **Desactivada** a partir de entonces, y al iniciar sesión se le dice a su propietario que la cuenta está deshabilitada. La pestaña Usuarios no ofrece **Desactivar** para una cuenta que no está activa: allí, **Eliminar** es la forma.

### 📏 Límites de los correos de verificación {: #verification-limits }

| Límite | Al superarlo |
| --- | --- |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` correos electrónicos por hora (20 de forma predeterminada) desde la misma dirección, contando los correos que salen: las altas, **Enviar el enlace de nuevo** con la contraseña correcta y **¿Olvidaste tu contraseña?** para una cuenta que existe; una dirección IPv6 cuenta por su /64 | Las siguientes cuentas nuevas se siguen creando y esperan, pero sus correos electrónicos no salen: la página de inicio de sesión lo indica justo después del alta, con cuánto tiempo esperar, y sus propietarios piden el enlace de nuevo desde la página de inicio de sesión una vez transcurrido ese tiempo. **Enviar el enlace de nuevo** se rechaza durante el mismo tiempo. |
| El límite propio del inicio de sesión sobre contraseñas incorrectas, compartido con la página de inicio de sesión: 10 cada 15 minutos para el mismo nombre de usuario o dirección de correo electrónico, 50 desde la misma dirección (consulta [Inicios de sesión fallidos](configuration_accounts.md#login-limit)) | La solicitud se rechaza antes de comprobar la contraseña: la página indica en cuántos minutos volver a intentarlo. La contraseña correcta borra los fallos de lo que se escribió. |
| 1 correo electrónico cada 5 minutos, y 3 por hora, para la misma cuenta, incluido el correo del alta | La solicitud se rechaza: la página indica en cuántos minutos volver a intentarlo. |
| 3 correos electrónicos por hora al mismo buzón, para cualquier cuenta y sin importar cómo se escriba su dirección ([Contraseñas olvidadas](#forgot-password)): tanto el correo de un alta como los enlaces enviados de nuevo, y solo los correos que salieron | **Enviar el enlace de nuevo** se rechaza: la página indica en cuántos minutos volver a intentarlo. Tras un alta, la cuenta se crea y espera, pero no sale ningún correo, y nada se le dice a su propietario: la página muestra su texto habitual, que ya indica qué hacer (mirar en la carpeta de spam y luego iniciar sesión para que se ofrezca un nuevo enlace). |
| El límite por hora de la instancia, `LIBREFOLIO_SMTP_MAX_PER_HOUR` | La solicitud se rechaza hasta que vuelva a caber un correo electrónico. Un alta hecha mientras está agotado queda retenida como una que supera el límite de su dirección. |
| Un lugar libre, una vez que ha caducado el enlace de la cuenta | La solicitud se rechaza: a su propietario se le dice que te lo pida. |

**Lo que permanece invisible.** Tras un alta, *Te estamos enviando un correo electrónico* significa que el correo está en cola, no que se haya entregado: sale después de la respuesta, y aún puede no salir. El límite del buzón de 3 correos de verificación por hora, el límite por hora de la instancia, un fallo de SMTP, el correo electrónico o `LIBREFOLIO_PUBLIC_URL` que dejaron de funcionar mientras tanto, un reinicio: nada de eso llega a la página. Solo lo dice el registro, con `Verification email: not sent` o `Verification email: the request failed` ([Qué dice el registro](email_troubleshooting.md#logs)), y un reinicio antes de que saliera el correo no deja ninguna línea. La cuenta espera con su retención, y **Enviar el enlace de nuevo** la recupera; por eso el texto de la página le dice a la persona qué hacer cuando no llega nada. Deliberadamente, el límite del buzón no se comprueba antes de la respuesta: un alta que respondiera de forma diferente cuando el buzón acabara de recibir correos les diría a quienes se dan de alta con la dirección de otra persona si ese buzón los está recibiendo.

Un enlace cuyo correo electrónico no salió no cuenta ni para la cuenta ni para el buzón. Si la cuenta deja de esperar mientras tanto —se confirma su dirección, o un administrador la activa o desactiva—, no se envía ningún enlace nuevo. Los límites por dirección y por buzón se guardan en la memoria de cada proceso del servidor: con varios procesos, cada uno mantiene su propio recuento, y un reinicio los olvida. Detrás de un proxy inverso, la dirección que cuenta sigue las reglas dadas en [Contraseñas olvidadas](#forgot-password).

---

## 🔔 Cambios de dirección de correo electrónico {: #email-change-notice }

Cuando alguien cambia la dirección de correo electrónico de su cuenta, en [Perfil](../user/settings/profile.md), LibreFolio escribe a la dirección que la cuenta tenía **antes**:

- **Solo a la dirección anterior**: la nueva no recibe nada.
- **Nada de la nueva dirección, ni el nombre de usuario**: el correo electrónico solo dice que la dirección cambió, sin ninguna parte de la nueva, ni siquiera su dominio, y comienza con un simple «Hola,» ([Notas de seguridad](email_troubleshooting.md#security)).
- **Sin enlace.** Le dice al propietario que, si no hizo el cambio, puede que alguien esté usando su cuenta: cambie la contraseña de inmediato si todavía puede, y te lo comunique.
- **En el idioma de la cuenta.** Nombra tu instancia por el host de `LIBREFOLIO_PUBLIC_URL`, con su puerto si lo tiene, o «LibreFolio» cuando la variable no está definida o no se puede usar: al no haber ningún enlace dentro, el aviso no la necesita.
- **Después del cambio**: el correo electrónico sale después de la respuesta, y el cambio nunca espera a que salga. Con el correo electrónico desactivado, no se envía nada, y el registro lo dice en una línea informativa, no en una advertencia. El aviso cuenta para el límite por hora como cualquier correo electrónico.
- **Como máximo 3 por hora para una cuenta, y 3 por hora al mismo buzón**, sin importar cómo se escriba su dirección ([Contraseñas olvidadas](#forgot-password)). Si se supera cualquiera de los dos, el cambio sigue adelante y el aviso se omite. Sin estos límites, una cuenta podría apuntar su correo electrónico a cualquier dirección y cambiarlo de nuevo, para hacer que tu instancia escriba allí.
- **No por mayúsculas solas.** Cambiar solo las mayúsculas de las letras A a Z, como `Anna@example.com` por `anna@example.com`, no es un cambio de dirección, así que no sale ningún aviso. Las letras acentuadas cuentan como diferentes: `Émile@example.com` por `émile@example.com` es un cambio, con su aviso.

---

## 🔗 Relacionado

- 📄 **[Correo electrónico](email.md)** — Dónde está la configuración, las variables, ejemplos, …
- 📄 **[Correo electrónico: cuando no funciona](email_troubleshooting.md)** — Cuando no funciona, notas de seguridad
