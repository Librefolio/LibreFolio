# 👥 Usuarios e invitaciones

La pestaña **Usuarios** de **Configuración › Administración** es donde un administrador gestiona las
cuentas de la instancia: quién puede iniciar sesión, quién es administrador y quién está invitado a unirse. Funciona
igual en cualquier instalación.

---

## 🧭 Abrir la pestaña {: #open-the-tab }

Abre **Configuración** (icono de engranaje en la barra lateral), luego **Administración** y su pestaña **Usuarios**, junto a
**Configuración global**. Solo los administradores tienen esta pestaña: el resto no la ve.

La pestaña tiene tres partes: las plazas ocupadas, arriba; las **Cuentas**; las **Invitaciones abiertas**.
Después de cada cambio, la pestaña recarga sus listas, así que siempre muestra lo que tiene el servidor.

!!! tip "💻 En un servidor sin navegador"

    La [línea de comandos](cli_tools.md) también hace la mayor parte de esto: `user invite`, `user reset-link`,
    `user deactivate` y `user activate`, `user promote` y `user demote`, `user reset-onboarding`.
    También puede superar el límite de usuarios. No puede eliminar una cuenta ni revocar una invitación.

---

## 📏 Plazas {: #places }

El encabezado cuenta las plazas ocupadas: **3 / 10 cuentas** cuando la instancia tiene un límite de usuarios,
**3 cuentas** cuando no lo tiene. Las cuentas activas y las invitaciones abiertas ocupan una plaza, y también una
cuenta [pendiente de su correo electrónico](#waiting) mientras su enlace está vigente, y también un
administrador inicial que aún está [pendiente de su enlace de configuración](#pending-setup); las cuentas desactivadas
no. El límite se establece en el servidor con `LIBREFOLIO_MAX_USERS`: consulta «Cuando la instancia está llena» en
[Variables de entorno](configuration_accounts.md#user-limit).

- 🚫 Cuando la instancia está llena, un aviso dice *La instancia está llena: no se puede crear ninguna invitación nueva hasta que
  desactives o elimines una cuenta, o revoques una invitación.* **Invitar** está desactivado, y una cuenta desactivada no se puede reactivar hasta que
  haya una plaza libre, a menos que esté [pendiente de su correo electrónico](#waiting) con un enlace vigente.
- 🔒 **Invitar** también está desactivado mientras el registro está cerrado. Si la configuración global **Registro** está
  en **Cerrado**, la pestaña te indica que la cambies allí ([Configuración global](settings.md), «Quién puede registrarse»). Si el servidor lo cierra con `LIBREFOLIO_REGISTRATION`, la pestaña indica el nombre de la variable: solo la
  configuración del servidor puede volver a abrirlo.

### 🚪 Quién puede registrarse {: #registration }

**Quién puede registrarse**, junto a **Invitar**, es la configuración global **Registro**, aquí y también en
[Configuración global](settings.md) («Quién puede registrarse»): **Abierto**, **Por invitación** o **Cerrado**. La elección se
guarda al instante, sin botón **Guardar**, y la pestaña vuelve a leer la configuración. Solo **Abierto** te pide
confirmación primero, porque deja entrar a cualquiera que llegue a la página de inicio de sesión; si cancelas, el modo se queda como estaba.
Si el servidor establece el modo con `LIBREFOLIO_REGISTRATION`, el selector está desactivado y la pestaña indica el nombre de la
variable.

---

## 👤 Cuentas {: #accounts }

Una fila por cuenta, empezando por la más antigua: el avatar de la cuenta, el nombre de usuario con sus insignias, luego el
correo electrónico y la fecha de creación. El avatar es la imagen elegida para la cuenta por su usuario (consulta
[Perfil](../user/settings/profile.md)); una cuenta sin avatar muestra la primera letra de su
nombre de usuario en un círculo simple.

| Insignia | Significado |
|---|---|
| **Tú** | Tu propia cuenta |
| **Admin** | Un administrador: gestiona la instancia, su configuración, sus usuarios y sus invitaciones |
| **Desactivada** | La cuenta no puede iniciar sesión y no ocupa plaza. Una cuenta [pendiente de su correo electrónico](#waiting) tiene una insignia propia, más abajo |
| **Pendiente de configuración** | El [administrador inicial](configuration_accounts.md#initial-admin), aún no activo: nadie ha usado su enlace de configuración ni ha configurado la cuenta de otra forma. Se muestra en lugar de **Desactivada**: consulta [Pendiente de su enlace de configuración](#pending-setup) |
| **Pendiente de verificación** | Una cuenta que aún no ha abierto el enlace de verificación que LibreFolio envió a su dirección, incluso una vez que ese enlace ha caducado. No puede iniciar sesión y ocupa una plaza mientras su enlace está vigente. Se muestra en lugar de **Desactivada**: consulta [Cuentas pendientes de su correo electrónico](#waiting) |

Haz clic en una fila para abrir sus acciones, y otra vez para cerrarlas. Tu propia fila no tiene ninguna: dice *Esta es
tu cuenta. Gestiónala desde:* con un enlace a **Perfil**, la pestaña donde cambias tus datos o
[eliminas tu cuenta](../user/settings/profile.md).

### ⚙️ Qué hace cada acción {: #actions }

| Acción | Qué hace | Pide confirmación |
|---|---|---|
| **Desactivar** | La cuenta ya no puede iniciar sesión y se cierra la sesión en todos los dispositivos. Sus brókeres y transacciones se conservan, y su plaza queda libre. Se muestra para una cuenta activa | ✅ |
| **Reactivar** | La cuenta puede volver a iniciar sesión, con sus datos tal como estaban; sus sesiones antiguas no vuelven. Vuelve a ocupar una plaza, así que necesita una libre, a menos que la cuenta esté [pendiente de su correo electrónico](#waiting) con un enlace vigente: su plaza ya está contada. Se muestra para una cuenta desactivada, incluida una pendiente de su correo electrónico, pero no para el administrador inicial [pendiente de su enlace de configuración](#pending-setup) | — |
| **Cancelar enlace de configuración** | El enlace de configuración del administrador inicial [pendiente de su configuración](#pending-setup) deja de funcionar, incluido el que ya se había entregado; la cuenta sigue esperando un enlace nuevo. Se muestra solo para esa cuenta, en lugar de **Reactivar**: consulta [Cancelar su enlace de configuración](#cancel-setup) | ✅ |
| **Hacer administrador** | La cuenta también gestiona la instancia: configuración, usuarios e invitaciones | ✅ |
| **Quitar administrador** | La cuenta permanece, como usuario normal, y se cierra la sesión en todos los dispositivos | ✅ |
| **Enlace de restablecimiento de contraseña** | Un enlace para elegir una nueva contraseña: consulta [Enlaces de restablecimiento de contraseña](#reset-links) | Su propio diálogo |
| **Cerrar sesión en todos los dispositivos** | Se cierra la sesión de la cuenta en todos los dispositivos: su usuario vuelve a iniciar sesión en cada uno. La cuenta permanece activa | ✅ |
| **Reiniciar las guías** | La próxima vez que su usuario abra LibreFolio, la [Configuración de bienvenida](../user/getting-started.md#welcome-setup) y todas las guías empiezan de nuevo, como para una cuenta nueva. Sus datos y preferencias se conservan | ✅ |
| **Eliminar** | Elimina la cuenta definitivamente: consulta [Eliminar una cuenta](#delete) | Su propio diálogo |

### 🔒 Cuándo una acción está desactivada {: #action-off }

LibreFolio desactiva las acciones que sabe que el servidor rechazaría, e indica por qué debajo de los botones:

| El panel dice | Desactivada | Qué puedes hacer |
|---|---|---|
| *Es el único administrador activo: no se puede desactivar ni degradar.* | **Desactivar**, **Quitar administrador** | Haz primero administradora a otra cuenta |
| *La instancia está llena: libera una plaza para reactivarla.* | **Reactivar** | Desactiva o elimina otra cuenta, o revoca una invitación; `user activate` de la línea de comandos supera el límite |
| *Hay que degradar a un administrador antes de poder eliminarlo.* | **Eliminar** | **Quitar administrador** primero y luego **Eliminar** |
| *Está pendiente de su configuración: conserva su rol hasta entonces.* | **Quitar administrador**, para el administrador inicial [pendiente de su enlace de configuración](#pending-setup) | [Cancela su enlace de configuración](#cancel-setup), o **Elimínala**: no necesita **Quitar administrador** primero |
| *Esta cuenta de administrador se activa mediante su enlace de configuración. Si el enlace se pierde, ejecuta `dev.py user setup-link` en el servidor.* | No hay **Reactivar**: **Cancelar enlace de configuración** en su lugar | Haz que se use su enlace de configuración, o dale uno nuevo: consulta [Pendiente de su enlace de configuración](#pending-setup) |

- 👑 La instancia siempre conserva un administrador activo. Tu propia fila no tiene acciones, así que para dejar el cargo:
  haz administradora a otra cuenta y luego pídele que te quite los permisos.

### ⏳ Cuentas pendientes de su correo electrónico {: #waiting }

Con **Requerir verificación de correo electrónico** activado ([Configuración global](settings.md)), una cuenta nueva espera hasta que
su propietario confirme la dirección con el enlace que LibreFolio le envía por correo. Hasta entonces:

- su fila muestra **Pendiente de verificación** en lugar de **Desactivada**, incluso una vez que su enlace ha
  caducado. Pasa el cursor sobre la insignia para ver la información emergente, o abre la fila, donde se lee debajo de los botones: *Su
  propietario aún no ha abierto el enlace de verificación: al iniciar sesión se ofrece enviar uno nuevo. Reactivar
  permite entrar a la cuenta de inmediato, sin el correo electrónico.* Una cuenta desactivada mientras espera (consulta el
  último punto) deja de esperar, y su fila vuelve a mostrar **Desactivada**;
- ocupa una plaza mientras su enlace está vigente, es decir, durante 24 horas después del último enlace enviado;
- **Reactivar** le permite entrar de inmediato: puede iniciar sesión, y los enlaces ya enviados dejan de funcionar. Mientras
  su enlace está vigente, esto no ocupa una plaza adicional, ya que su plaza ya está contada: **Reactivar**
  funciona incluso en una instancia llena, y también `user activate` en la
  [línea de comandos](cli_tools.md), sin advertencia de límite. Una vez que el enlace ha caducado, reactivarla
  requiere una plaza libre, como para cualquier cuenta desactivada;
- **Eliminar** la elimina, como cualquier cuenta. Esta pestaña no ofrece **Desactivar** para una cuenta que
  no está activa; `user deactivate` en la línea de comandos, o la API de administración
  (`PATCH /api/v1/users/{id}` con `is_active: false`), la conserva pero termina la espera: sus enlaces dejan
  de funcionar, su plaza queda libre, y solo puede iniciar sesión una vez reactivada.

Cómo funciona la verificación y sus límites: [Verificación por correo electrónico](email_flows.md#verification).

### 👑 Pendiente de su enlace de configuración {: #pending-setup }

Cuando LibreFolio crea el administrador de `LIBREFOLIO_ADMIN_EMAIL` en su primer arranque, la
cuenta espera, aún sin estar activa, hasta que alguien abra su enlace de configuración y elija la contraseña, o la configure
de otra forma (más abajo): consulta
[El administrador inicial](configuration_accounts.md#initial-admin). Hasta entonces:

- su fila muestra **Pendiente de configuración** en lugar de **Desactivada**, incluso una vez que su enlace ha caducado o
  se ha [cancelado](#cancel-setup);
- ocupa una plaza, como una cuenta activa;
- su panel no tiene **Reactivar**: nadie conoce su contraseña, y activarla también haría que su
  enlace de configuración dejara de funcionar. **Cancelar enlace de configuración** ocupa su lugar ([más abajo](#cancel-setup)). Debajo
  de los botones, el panel dice: *Esta cuenta de administrador se activa mediante su enlace de configuración. Si
  el enlace se pierde, ejecuta `dev.py user setup-link` en el servidor.*;
- **Quitar administrador** está desactivado, con el motivo *Está pendiente de su configuración: conserva su rol hasta
  entonces.* Para anular el enlace ya entregado, cancélalo; para eliminar la cuenta por completo, elimínala;
- **Eliminar** no necesita **Quitar administrador** primero, a diferencia de cualquier otro administrador;
- las demás acciones son las de cualquier cuenta desactivada.

El servidor se niega a activarla, o a quitarle sus derechos de administrador: `PATCH /api/v1/users/{id}`
con `is_active: true`, o con `is_superuser: false`, responde `409`, con el código `PENDING_SETUP`,
y no cambia nada. Si tal cambio llega al servidor de todos modos, por ejemplo desde una lista cargada
antes, la pestaña explica por qué en lugar de mostrar un error genérico: *Este administrador está pendiente de su configuración: aquí no se puede
reactivar ni degradar.* `GET /api/v1/users` marca la cuenta con
`pending_setup: true`.

Esta versión no tiene un botón para generar un nuevo enlace de configuración: en el servidor, `user setup-link` imprime uno (consulta
«Un nuevo enlace de configuración para el administrador inicial» en [Herramientas de línea de comandos](cli_tools.md))). Una vez que se usa el enlace, la cuenta está
activa, como cualquier otra.

La cuenta también deja de esperar cuando se configura de otra forma, sin su enlace:

- **activada en el servidor** con `user activate`: la línea de comandos no lo rechaza, a diferencia de
  esta pestaña, y no imprime ninguna advertencia de límite, ya que la cuenta ya ocupa su plaza. Su contraseña
  sigue siendo la que nadie conoce, hasta que `user reset` o un enlace de restablecimiento le asigne
  una;
- **con una contraseña asignada**, con `user reset` en el servidor, o con un
  [enlace de restablecimiento de contraseña](#reset-links) una vez que se usa: uno que crees con
  **Enlace de restablecimiento de contraseña** en su panel, o uno que imprima `user reset-link`. La cuenta permanece inactiva
  hasta que se active.

A partir de entonces, todos los enlaces de configuración que tenía dejan de funcionar: la página de configuración dice *Este enlace ha sido
retirado.*, y `user setup-link` no encuentra ningún administrador pendiente. La pestaña la muestra como cualquier otra
cuenta: **Desactivada** mientras no está activa, con **Reactivar**, y `GET /api/v1/users` la marca
con `pending_setup: false`. Como cualquier cuenta desactivada, entonces no ocupa plaza, así que **Reactivar**
necesita una libre. Un enlace de restablecimiento que nadie usa la deja esperando, y también lo hace
[cancelar su enlace de configuración](#cancel-setup).

### 🚫 Cancelar su enlace de configuración {: #cancel-setup }

Cancela el enlace de configuración del administrador inicial cuando llegó a la persona equivocada, o cuando alguien
más pudo haberlo visto, por ejemplo en un correo reenviado o en el registro del servidor:

1. Abre la fila de la cuenta **Pendiente de configuración** y haz clic en **Cancelar enlace de configuración**.
2. El diálogo pregunta *¿Cancelar el enlace de configuración de {username}?* y explica: *El enlace ya
   entregado deja de funcionar. La cuenta sigue esperando su configuración: un nuevo enlace se obtiene con «dev.py user
   setup-link» en el servidor.*
3. Haz clic en **Cancelar el enlace**. Un mensaje confirma: *El enlace de configuración de {username} ya no funciona.*

Qué ocurre:

- 🔗 todos los enlaces de configuración de la cuenta dejan de funcionar, incluido el ya entregado: quien lo abra
  recibe *Este enlace ha sido retirado.*, y no puede configurar la cuenta;
- ⏳ la cuenta sigue esperando: su fila aún muestra **Pendiente de configuración**, conserva su plaza y
  todavía no se puede reactivar aquí;
- 🔁 para permitir la entrada al administrador, dale un enlace nuevo: en el servidor, `user setup-link` imprime uno (consulta
  «Un nuevo enlace de configuración para el administrador inicial» en [Herramientas de línea de comandos](cli_tools.md))). Reiniciar el servidor con el mismo
  `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` no genera un enlace nuevo, ya que la instancia ya ha visto ese
  token: cada arranque registra una advertencia de que el enlace de configuración fue retirado, y pide ejecutar
  `dev.py user setup-link`, o establecer un token nuevo.

En el servidor, `user deactivate` sobre esta cuenta cancela su enlace de la misma forma.

Si el administrador completó su configuración después de que se cargara tu lista, no queda nada que
cancelar: LibreFolio no cambia nada y dice *Este administrador completó su configuración mientras
tanto: no se cambió nada.* La pestaña se recarga, y la fila ahora muestra un administrador activo,
con **Desactivar** en lugar de **Cancelar enlace de configuración**. La cuenta permanece activa y su propietario
sigue con la sesión iniciada.

Para eliminar la cuenta, en cambio, haz clic en **Eliminar** ([Eliminar una cuenta](#delete)), sin
**Quitar administrador** primero. La cuenta se va con sus enlaces de configuración, su plaza queda libre y
nadie espera ya una configuración: `user setup-link` no encuentra a nadie, y las variables `LIBREFOLIO_ADMIN_*`
no crean nada en los siguientes arranques, ya que la instancia tiene cuentas. Si, mientras tanto, la configuración también se completó
allí, no se elimina nada: el diálogo dice *Hay que degradar a un administrador antes de poder eliminarlo.*,
ya que la cuenta ahora es un administrador activo.

### 🔤 Nombres de usuario con una @ {: #usernames-with-at }

A partir de la versión 1.3, un nombre de usuario nuevo no puede contener `@`: al iniciar sesión, LibreFolio interpreta cualquier cosa con una
`@` como una dirección de correo electrónico. El registro, un cambio de nombre de usuario en el Perfil y `user create` en la
[línea de comandos](cli_tools.md) lo rechazan, y un `LIBREFOLIO_ADMIN_USERNAME` con una `@` detiene el
servidor al arrancar («El administrador inicial» en [Variables de entorno](configuration_accounts.md#initial-admin)).
Los espacios, las letras acentuadas y signos como `.`, `_`, `-` o `+` siguen permitidos.

Una cuenta creada antes de la versión 1.3 puede tener uno, como `anna@example.com` como nombre de usuario:

- 🏷️ el nombre de usuario se queda como está: nada lo renombra. Su usuario puede cambiarlo en su
  [Perfil](../user/settings/profile.md), por un nombre sin `@`;
- 🔑 la cuenta inicia sesión con su dirección de correo electrónico, ya que todas las cuentas tienen una. El nombre de usuario en sí
  funciona solo mientras ninguna cuenta lo tenga como su dirección de correo electrónico: al escribirse al iniciar sesión, una dirección identifica la
  cuenta que la tiene;
- 📧 ninguna otra cuenta puede tomar ese nombre de usuario como su dirección de correo electrónico, con cualquier combinación de mayúsculas y minúsculas: el registro,
  el Perfil, `user create` y `user set-email` lo rechazan con *Correo electrónico ya registrado*. La
  propia cuenta puede usarlo como su propia dirección.

---

## ✉️ Invitaciones {: #invitations }

Para invitar a alguien:

1. Haz clic en **Invitar**.
2. Opcionalmente, escribe su dirección en **Correo electrónico (opcional)**. Solo sirve para anotar a quién va dirigida
   la invitación: el enlace funciona para quien lo abra. La lista de invitaciones la muestra, y
   el formulario de registro empieza con ella, donde la persona puede cambiarla.
3. Marca **Administrador** si la nueva cuenta debe gestionar la instancia.
4. Haz clic en **Crear el enlace**: *Comparte este enlace: funciona una vez, durante 7 días.* Comprueba la
   [dirección del servidor](#server-address), haz clic en **Copiar** y envía tú mismo el enlace, por mensaje o
   correo electrónico, o deja que LibreFolio lo envíe: [Enviar por correo electrónico](#send-by-email).
5. Haz clic en **Listo**: la invitación pasa a **Invitaciones abiertas**.

La persona abre el enlace y crea su cuenta con el nombre de usuario, correo electrónico y contraseña que
elija: [Primeros pasos](../user/getting-started.md) muestra lo que ve.

- 🔗 El enlace se muestra solo una vez, cuando lo creas. Si se pierde, revoca la invitación y
  crea una nueva.
- 📏 Una invitación ocupa una plaza desde el momento en que la creas hasta que se usa, se revoca o
  caduca; la cuenta que crea ocupa entonces esa plaza.
- 🔤 Una dirección de correo electrónico pertenece a una sola cuenta, sin importar sus mayúsculas (`Anna@example.com` es
  `anna@example.com`), pero solo las letras de la A a la Z se comparan así: `Émile@example.com` y
  `émile@example.com` son dos direcciones diferentes.

### 📋 Invitaciones abiertas {: #open-invitations }

Las invitaciones que nadie ha usado aún, empezando por la más antigua: el correo electrónico (o *Sin correo electrónico*), una insignia **Admin**
cuando la invitación otorga derechos de administrador, y cuándo se creó y cuándo caduca. Una invitación
sale de la lista una vez que se usa, se revoca o caduca.

**Revocar** retira una invitación en cualquier momento, tras una confirmación: el enlace deja de funcionar
de inmediato y su plaza queda libre.

---

## 🔑 Enlaces de restablecimiento de contraseña {: #reset-links }

Cuando alguien olvide su contraseña, envíale un enlace para que elija una nueva por sí mismo. Con correo electrónico,
también puede pedir uno desde la página de inicio de sesión: consulta [Contraseñas olvidadas](email_flows.md#forgot-password).

1. Abre su fila y haz clic en **Enlace de restablecimiento de contraseña**.
2. El diálogo explica: *Un enlace de un solo uso para establecer una nueva contraseña, válido durante 30 minutos. Los enlaces
   creados antes para esta cuenta dejan de funcionar.* Haz clic en **Crear el enlace**.
3. Comprueba la [dirección del servidor](#server-address), haz clic en **Copiar** y envía el enlace, o haz clic en
   **Enviar por correo electrónico** ([Enviar por correo electrónico](#send-by-email)); luego haz clic en **Listo**.

- ⏱️ El enlace funciona una vez, durante 30 minutos, y solo funciona el enlace más reciente de una cuenta.
- 🔒 También deja de funcionar en cuanto la persona cambia su contraseña o su dirección de correo electrónico, o cuando
  ejecutas `user reset` o `user set-email` en la [línea de comandos](cli_tools.md).
- 🚪 Crear el enlace no cierra la sesión de nadie. Una vez que la persona establece la nueva contraseña, se cierra la sesión de su cuenta
  en todos los dispositivos.
- 🔗 El enlace se muestra solo una vez: si se pierde, crea uno nuevo.

Lo que ve la persona está en [Primeros pasos](../user/getting-started.md).

---

## 🌐 La dirección del servidor de un enlace {: #server-address }

Los enlaces de invitación y de restablecimiento de contraseña se muestran en el mismo panel:

- **Dirección del servidor**: dónde empieza el enlace. Se rellena con `LIBREFOLIO_PUBLIC_URL` cuando el
  servidor la establece; de lo contrario, con la dirección que tu navegador está usando ahora. *Cámbiala si tus usuarios
  llegan a LibreFolio en otra dirección*: por ejemplo, tú estás en `http://192.168.1.10:6040` en
  casa, mientras que tus usuarios pasan por `https://librefolio.example.com`.
- **Enlace**: la dirección del servidor seguida de la ruta propia del enlace. **Copiar** lo pone en el portapapeles;
  si el navegador se niega, se selecciona el enlace para que puedas copiarlo a mano. *Válido hasta …*
  indica su caducidad.

Cuando cambias la dirección, tu navegador comprueba, medio segundo después de que dejes de escribir, que
**esta** instancia responde allí, y no un servidor cualquiera: carga una imagen diminuta desde
`<address>/api/v1/auth/address-probe.png?nonce=…`, que es de 1×1 cuando responde esta instancia y de 2×1
cuando responde otra. La propia dirección rellenada no se
comprueba.

| Mensaje | Qué significa |
|---|---|
| *Comprobando que este LibreFolio responde en esta dirección…* | La comprobación está en curso |
| *Esta instancia responde en esta dirección.* | El enlace llega a este LibreFolio |
| *Algo responde en esta dirección, pero no esta instancia: compruébalo antes de compartir.* | Allí responde otro LibreFolio: probablemente no es la dirección que querías |
| *No se pudo comprobar esta dirección desde este navegador: aún puedes compartir el enlace.* | El navegador no pudo cargar la imagen. Allí no responde nada (una dirección incorrecta o cerrada, o ninguna respuesta en 8 segundos); una página abierta con `https://` comprueba una dirección `http://`, que el navegador bloquea; una página en una dirección pública comprueba una local, que algunos navegadores bloquean o permiten solo tras pedirte permiso; una instancia que está bloqueada no sirve la imagen; o responde un LibreFolio más antiguo, que no se puede comprobar |
| *Introduce una dirección que empiece por http:// o https://, sin ? ni #.* | No es una dirección: **Copiar** permanece desactivado hasta que la corrijas |

Sea cual sea el resultado, salvo que la dirección no sea válida, puedes copiar el enlace: la comprobación solo
aconseja. De vuelta en la dirección rellenada, el mensaje desaparece. Cómo funciona la comprobación:
[Sonda de dirección](../developer/architecture/security.md#address-probe), para desarrolladores.

!!! tip "🌐 Configura la dirección una vez"

    Establece `LIBREFOLIO_PUBLIC_URL` en la dirección que abren tus usuarios, y el panel parte de ella: consulta
    «Cuentas y registros» en [Variables de entorno](configuration_accounts.md#accounts). La
    [línea de comandos](cli_tools.md) también la pone delante de los enlaces que imprime.

---

## 📧 Enviar por correo electrónico {: #send-by-email }

Mientras la instancia pueda enviar correos electrónicos con un enlace —correo **Listo** y `LIBREFOLIO_PUBLIC_URL` establecida en
una dirección que LibreFolio pueda usar ([Correos electrónicos con un enlace](email_flows.md#public-url))—, ambos diálogos de enlace tienen
**Enviar por correo electrónico** debajo del enlace:

- **Una invitación**: **Enviar a** empieza con la dirección escrita en la invitación, y puedes
  cambiarla. Si se deja vacía, el correo va a la dirección escrita en la invitación; si no hay ninguna, el
  diálogo pide una dirección.
- **Un enlace de restablecimiento de contraseña** no tiene campo: el correo va a la dirección de la cuenta, y solo
  mientras la cuenta está activa.
- **El enlace del correo empieza por `LIBREFOLIO_PUBLIC_URL`**, independientemente de lo que muestre la **Dirección del servidor**
  arriba: el diálogo lo indica.
- **El idioma**: una invitación va en el idioma elegido en **Idioma del correo electrónico**, el
  **Idioma predeterminado** de la instancia a menos que elijas otro; un enlace de restablecimiento va en el de la cuenta.
- **El resultado** se muestra en el diálogo: *Enviado a …* con la dirección y el idioma en que se
  escribió el correo, o por qué no se envió el correo ([Errores de envío](email_troubleshooting.md#sending-errors)).

Sin correo electrónico, el botón no está: copia el enlace como antes. Las reglas y los límites:
[Enlaces enviados por un administrador](email_flows.md#admin-links).

---

## 🗑️ Eliminar una cuenta {: #delete }

Abre la fila de la cuenta y haz clic en **Eliminar**; para un administrador, haz clic en **Quitar administrador**
primero, a menos que sea el administrador inicial [pendiente de su enlace de configuración](#cancel-setup), al que
eliminas directamente. La eliminación sigue la misma regla que eliminar la propia cuenta
([Perfil](../user/settings/profile.md)):

1. Para una cuenta activa, el diálogo primero ofrece **Desactivar** en su lugar: conserva todos los brókeres y
   transacciones y se puede deshacer; la cuenta simplemente ya no puede iniciar sesión.
2. Luego muestra lo que conllevaría la eliminación:
    - **Se eliminan, con todas sus transacciones y archivos**: los brókeres de los que la cuenta es el único propietario,
      cada uno con su número de transacciones. También se eliminan para los usuarios con los que los compartía.
      Si no hay ninguno, el diálogo dice *No se elimina ningún bróker*;
    - **Brókeres compartidos que se conservan (solo se elimina el acceso)**: los demás brókeres que la cuenta puede abrir,
      con su rol en cada uno;
    - una advertencia cuando las transacciones en otros brókeres son mitades de transferencias con los brókeres que
      se eliminan: se conservan, sin su otra mitad. Una transferencia recibida se convierte en un ajuste por su
      coste, y una transferencia enviada a uno de esos brókeres, en un ajuste que saca los activos del
      bróker que los envió, sin un valor: su coste cuenta como una pérdida realizada allí (consulta
      [Editar o eliminar un bróker](../user/brokers/index.md)).
3. Escribe el nombre de usuario de la cuenta y luego haz clic en **Eliminar permanentemente**.

!!! danger "Eliminar una cuenta no se puede deshacer"

    La cuenta, su configuración y los brókeres indicados como eliminados se eliminan de inmediato, y a quien tenga la sesión
    iniciada en ella se le cerrará la sesión en su siguiente solicitud. Si la eliminación falla por un motivo técnico,
    no se elimina nada. Si el diálogo no puede cargar lo que conllevaría la eliminación, no te permite
    eliminar: ciérralo e inténtalo de nuevo.

Cómo funciona la regla: [Eliminar una cuenta](../developer/architecture/access_control.md#admin-account-deletion),
para desarrolladores.

---

## 🔗 Relacionado

- 📝 **[Variables de entorno](configuration_accounts.md#accounts)** — «Cuentas y registros»: `LIBREFOLIO_MAX_USERS`,
  `LIBREFOLIO_REGISTRATION` y `LIBREFOLIO_PUBLIC_URL`
- ⚙️ **[Configuración global](settings.md)** — «Quién puede registrarse»: la configuración **Registro**
- 🛠️ **[Herramientas de línea de comandos](cli_tools.md)** — «Gestionar usuarios»: la mayoría de estas tareas, sin navegador
- 👤 **[Perfil](../user/settings/profile.md)** — Tu propia cuenta y cómo eliminarla
- 🧑‍💻 Para desarrolladores: **[API de administrador](../developer/architecture/access_control.md#admin-user-api)**
  y **[Componentes de configuración](../developer/frontend/components/features/settings.md#userstab)**
