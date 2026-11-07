# 👥 Usuarios e invitaciones

Un administrador cuida de las cuentas de la instancia — quién puede iniciar sesión, quién es administrador, quién está invitado — en una sola pestaña.

**Dónde:** **Configuración › Administración › Usuarios**. Igual en cualquier instalación.

---

## 🧭 Abrir la pestaña {: #open-the-tab }

1. Abre **Configuración** (icono de engranaje en la barra lateral), luego **Administración**, luego la pestaña **Usuarios**, junto a **Configuración Global**.

    Solo los administradores ven esta pestaña.

La pestaña tiene tres partes: las **plazas** ocupadas, arriba; las **Cuentas**; las **Invitaciones abiertas**. Después de cada cambio recarga sus listas: siempre muestra lo que tiene el servidor.

!!! tip "💻 En un servidor sin navegador"

    La [línea de comandos](cli_tools.md) hace la mayor parte de esto, en el servidor, en la carpeta de LibreFolio:

    ```bash
    pipenv run ./dev.py user invite
    pipenv run ./dev.py user reset-link <username>
    pipenv run ./dev.py user deactivate <username>
    pipenv run ./dev.py user activate <username>
    pipenv run ./dev.py user promote <username>
    pipenv run ./dev.py user demote <username>
    pipenv run ./dev.py user reset-onboarding <username>
    ```

    Con Docker, el comando va en el contenedor: «Dónde ejecutar los comandos» en [Herramientas de línea de comandos](cli_tools.md).
    La línea de comandos también supera el límite de usuarios. No puede eliminar una cuenta ni revocar una invitación.

---

## 📏 Plazas {: #places }

El encabezado cuenta las plazas ocupadas: **3 / 10 cuentas** con un límite de usuarios, **3 cuentas** sin él.

| Ocupa una plaza | |
|---|---|
| Cuenta activa | ✅ |
| Invitación abierta | ✅ |
| Cuenta [en espera de su correo electrónico](#waiting) | ✅ mientras su enlace está vigente |
| Administrador inicial [en espera de su enlace de configuración](#pending-setup) | ✅ |
| Cuenta desactivada | ❌ |

**Dónde se establece el límite:** en el `.env` de LibreFolio, con `LIBREFOLIO_MAX_USERS`: «Cuando la instancia está llena» en [Variables de entorno](configuration_accounts.md#user-limit).

Cuando **Invitar** está desactivado:

| Por qué | Qué dice la pestaña | Qué puedes hacer |
|---|---|---|
| 🚫 La instancia está llena | Un aviso: *La instancia está llena: no hay nuevas invitaciones hasta que desactives o elimines una cuenta, o revoques una invitación.* Ni siquiera se puede reactivar una cuenta desactivada, salvo que esté [en espera de su correo electrónico](#waiting) con un enlace vigente | Desactivar o eliminar una cuenta, o revocar una invitación |
| 🔒 El ajuste global **Registro** está en **Cerrado** | Te indica que lo cambies en la [Configuración global](settings.md), «Quién puede registrarse» | Cambiarlo allí, o en [Quién puede registrarse](#registration) más abajo |
| 🔒 El servidor cierra el registro con `LIBREFOLIO_REGISTRATION` | Nombra la variable | Solo la configuración del servidor puede volver a abrirlo |

### 🚪 Quién puede registrarse {: #registration }

**Dónde:** el selector **Quién puede registrarse**, junto a **Invitar**. Es el ajuste global **Registro**, el mismo que en la [Configuración global](settings.md) («Quién puede registrarse»).

1. Elige **Abierto**, **Por invitación** o **Cerrado**.

    La elección se guarda al instante, sin botón **Guardar**, y la pestaña vuelve a leer el ajuste.

- ⚠️ Solo **Abierto** te pide confirmar primero: deja entrar a cualquiera que llegue a la página de inicio de sesión. Si cancelas, el modo se queda como estaba.
- 🔒 Si el servidor establece el modo con `LIBREFOLIO_REGISTRATION`, el selector está desactivado y la pestaña nombra la variable.

---

## 👤 Cuentas {: #accounts }

Una fila por cuenta, empezando por la más antigua: avatar, nombre de usuario con sus insignias, correo electrónico, fecha de creación. El avatar es la imagen que el usuario eligió en su [Perfil](../user/settings/profile.md); sin avatar, la primera letra del nombre de usuario en un círculo.

| Insignia | Significado |
|---|---|
| **Tú** | Tu propia cuenta |
| **Admin** | Un administrador: gestiona la instancia, su configuración, sus usuarios y sus invitaciones |
| **Desactivada** | La cuenta no puede iniciar sesión y no ocupa plaza |
| **Pendiente de configuración** | El [administrador inicial](configuration_accounts.md#initial-admin), aún no activo: nadie ha usado su enlace de configuración, ni lo ha configurado de otra manera. En lugar de **Desactivada**: consulta [En espera de su enlace de configuración](#pending-setup) |
| **Pendiente de verificación** | Una cuenta que todavía no ha abierto el enlace de verificación enviado a su dirección, incluso después de que el enlace haya caducado. No puede iniciar sesión y ocupa una plaza mientras el enlace está vigente. En lugar de **Desactivada**: consulta [Cuentas en espera de su correo electrónico](#waiting) |

**Dónde están las acciones:** haz clic en una fila para abrirlas, de nuevo para cerrarlas. Tu propia fila no tiene ninguna: dice *Esta es tu cuenta. Gestiónala desde:* con un enlace a **Perfil**, donde cambias tus datos o [eliminas tu cuenta](../user/settings/profile.md).

### ⚙️ Qué hace cada acción {: #actions }

| Acción | Qué hace | Pide confirmación |
|---|---|---|
| **Desactivar** | La cuenta ya no puede iniciar sesión y se cierra su sesión en todos los dispositivos. Los brókers y las transacciones se mantienen; su plaza se libera. Solo para una cuenta activa | ✅ |
| **Reactivar** | La cuenta vuelve a iniciar sesión, con sus datos; las sesiones antiguas no vuelven. Vuelve a ocupar una plaza, así que necesita una libre, salvo que esté [en espera de su correo electrónico](#waiting) con un enlace vigente (la plaza ya está contada). Para una cuenta desactivada, incluida una en espera de su correo electrónico, pero no para el administrador inicial [en espera de su enlace de configuración](#pending-setup) | — |
| **Cancelar el enlace de configuración** | El enlace de configuración del administrador inicial [en espera de su configuración](#pending-setup) deja de funcionar, incluido el ya entregado; la cuenta sigue esperando un enlace nuevo. Solo para esa cuenta, en lugar de **Reactivar**: consulta [Cancelar su enlace de configuración](#cancel-setup) | ✅ |
| **Hacer administrador** | La cuenta gestiona también la instancia: configuración, usuarios e invitaciones | ✅ |
| **Quitar administrador** | La cuenta se mantiene, como usuario normal, y se cierra su sesión en todos los dispositivos | ✅ |
| **Enlace de restablecimiento** | Un enlace para elegir una nueva contraseña: consulta [Enlaces de restablecimiento de contraseña](#reset-links) | Su propio diálogo |
| **Cerrar sesión en todas partes** | Se cierra la sesión de la cuenta en todos los dispositivos y vuelve a iniciar sesión en cada uno. Sigue activa | ✅ |
| **Reiniciar las guías** | La próxima vez que se abra LibreFolio, la [Configuración de bienvenida](../user/getting-started.md#welcome-setup) y todas las guías empiezan de nuevo, como en una cuenta nueva. Los datos y las preferencias se mantienen | ✅ |
| **Eliminar** | Elimina la cuenta para siempre: consulta [Eliminar una cuenta](#delete) | Su propio diálogo |

### 🔒 Cuando una acción está desactivada {: #action-off }

LibreFolio desactiva las acciones que el servidor rechazaría y explica por qué bajo los botones:

| Qué dice el panel | Desactivadas | Qué puedes hacer |
|---|---|---|
| *Es el único administrador activo: no se puede desactivar ni degradar.* | **Desactivar**, **Quitar administrador** | Haz administrador antes a otra cuenta |
| *La instancia está llena: libera una plaza para reactivarla.* | **Reactivar** | Desactiva o elimina otra cuenta, o revoca una invitación; el `user activate` de la línea de comandos supera el límite |
| *Un administrador debe ser degradado antes de poder eliminarlo.* | **Eliminar** | Primero **Quitar administrador**, luego **Eliminar** |
| *Espera su configuración: mantiene su rol hasta entonces.* | **Quitar administrador**, para el administrador inicial [en espera de su enlace de configuración](#pending-setup) | [Cancelar su enlace de configuración](#cancel-setup), o **Eliminar** la cuenta, sin **Quitar administrador** antes |
| *Esta cuenta de administrador se activa con su enlace de configuración. Si el enlace se ha perdido, ejecuta `dev.py user setup-link` en el servidor.* | Sin **Reactivar**: **Cancelar el enlace de configuración** en su lugar | Haz que se use su enlace de configuración, o entrega uno nuevo: consulta [En espera de su enlace de configuración](#pending-setup) |

- 👑 La instancia siempre conserva un administrador activo. Tu propia fila no tiene acciones: para dejar de serlo, haz administrador a otra cuenta y pídele que te quite los derechos.

### ⏳ Cuentas en espera de su correo electrónico {: #waiting }

Con **Verificación Email Requerida** activada ([Configuración global](settings.md)), una cuenta nueva espera hasta que su titular confirma la dirección con el enlace que LibreFolio le envía por correo. Hasta entonces:

- 🏷️ la fila muestra **Pendiente de verificación** en lugar de **Desactivada**, incluso después de que el enlace haya caducado. Pasa el cursor sobre la insignia para ver la pista, o abre la fila: bajo los botones dice *Su titular aún no ha abierto el enlace de verificación: al iniciar sesión puede pedir uno nuevo. Reactivar le deja entrar de inmediato, sin el correo.*;
- 📏 ocupa una plaza mientras su enlace está vigente: 24 horas después de enviarse el último enlace;
- ✅ **Reactivar** la deja entrar de inmediato: puede iniciar sesión, y los enlaces ya enviados dejan de funcionar. Con el enlace aún vigente, no hace falta una plaza libre (la suya ya está contada): funciona incluso en una instancia llena, como `user activate` en la [línea de comandos](cli_tools.md), sin advertencia de límite. Con el enlace caducado, hace falta una plaza libre, como para cualquier cuenta desactivada;
- 🗑️ **Eliminar** la elimina, como a cualquier cuenta;
- ⛔ la pestaña no ofrece **Desactivar** para una cuenta que no está activa. En el servidor, `user deactivate`, o la API de administrador (`PATCH /api/v1/users/{id}` con `is_active: false`), la mantiene pero termina la espera: sus enlaces dejan de funcionar, su plaza queda libre, la fila vuelve a mostrar **Desactivada**, y solo puede iniciar sesión una vez reactivada.

Cómo funciona la verificación y sus límites: [Verificación por correo electrónico](email_flows.md#verification).

### 👑 En espera de su enlace de configuración {: #pending-setup }

Cuando LibreFolio crea el administrador de `LIBREFOLIO_ADMIN_EMAIL` en el primer inicio, la cuenta espera, no activa, hasta que alguien abre su enlace de configuración y elige la contraseña, o la configura de otra manera (más abajo): [El administrador inicial](configuration_accounts.md#initial-admin). Hasta entonces:

- 🏷️ la fila muestra **Pendiente de configuración** en lugar de **Desactivada**, incluso después de que el enlace haya caducado o se haya [cancelado](#cancel-setup);
- 📏 ocupa una plaza, como una cuenta activa;
- ⛔ el panel no tiene **Reactivar**: nadie conoce su contraseña, y activarla también haría que el enlace de configuración dejara de funcionar. En su lugar hay **Cancelar el enlace de configuración** ([más abajo](#cancel-setup)), con el motivo de la [tabla de arriba](#action-off);
- 🔒 **Quitar administrador** está desactivado, con su motivo ([tabla de arriba](#action-off)). Para detener el enlace ya entregado, cancélalo; para detener la cuenta por completo, elimínala;
- 🗑️ **Eliminar** no necesita **Quitar administrador** antes, a diferencia de cualquier otro administrador;
- las demás acciones son las de cualquier cuenta desactivada.

El servidor se niega a activarla o a degradarla: `PATCH /api/v1/users/{id}` con `is_active: true`, o con `is_superuser: false`, responde `409`, código `PENDING_SETUP`, y no cambia nada. Si un cambio así llega al servidor de todos modos, por ejemplo desde una lista cargada antes, la pestaña dice *Este administrador espera su configuración: no se puede reactivar ni degradar desde aquí.* `GET /api/v1/users` la marca con `pending_setup: true`.

**Un nuevo enlace de configuración.** Esta versión no tiene un botón para crearlo.

**Dónde:** en el servidor, en la carpeta de LibreFolio:

```bash
pipenv run ./dev.py user setup-link
```

El comando imprime el enlace: «Un nuevo enlace de configuración para el administrador inicial» en [Herramientas de línea de comandos](cli_tools.md). Una vez usado, la cuenta está activa como cualquier otra.

**Configurarla de otra manera, sin su enlace.** La cuenta deja de esperar también así:

| Dónde | Cómo | Resultado |
|---|---|---|
| En el servidor | `user activate` | La línea de comandos no la rechaza, a diferencia de la pestaña, y no imprime advertencia de límite: la cuenta ya ocupa su plaza. Su contraseña sigue siendo la que nadie conoce, hasta que `user reset` o un enlace de restablecimiento le dé una |
| En el servidor | `user reset` | Se asigna una contraseña. La cuenta sigue inactiva hasta que se activa |
| En su panel, o en el servidor | Un [enlace de restablecimiento de contraseña](#reset-links) usado: desde **Enlace de restablecimiento**, o impreso por `user reset-link` | Como arriba: inactiva hasta que se activa |

A partir de entonces todos los enlaces de configuración dejan de funcionar: la página de configuración dice *Este enlace ha sido revocado.*, y `user setup-link` no encuentra ningún administrador en espera. La pestaña la muestra como a cualquier otra cuenta: **Desactivada** hasta que está activa, con **Reactivar**, y `GET /api/v1/users` la marca con `pending_setup: false`. Ya no ocupa plaza, así que **Reactivar** necesita una libre. Un enlace de restablecimiento que nadie usa la deja en espera, como lo hace [cancelar su enlace de configuración](#cancel-setup).

### 🚫 Cancelar su enlace de configuración {: #cancel-setup }

Cuando el enlace fue a la persona equivocada, o alguien más puede haberlo visto (un correo reenviado, el registro del servidor).

**Dónde:** la fila de la cuenta **Pendiente de configuración**, botón **Cancelar el enlace de configuración**. En el servidor, `user deactivate` sobre esta cuenta cancela el enlace de la misma manera.

1. Abre la fila y haz clic en **Cancelar el enlace de configuración**.

    El diálogo pregunta *¿Cancelar el enlace de configuración de {username}?* y explica: *El enlace ya entregado deja de funcionar. La cuenta sigue esperando su configuración: un enlace nuevo se obtiene con «dev.py user setup-link» en el servidor.*

2. Haz clic en **Cancelar el enlace**.

    Un mensaje lo confirma: *El enlace de configuración de {username} ya no funciona.*

Qué ocurre:

- 🔗 todos los enlaces de configuración de la cuenta dejan de funcionar, incluido el entregado: quien lo abra leerá *Este enlace ha sido revocado.* y no podrá configurar la cuenta;
- ⏳ la cuenta sigue esperando: la fila sigue mostrando **Pendiente de configuración**, conserva su plaza y no se puede reactivar aquí;
- 🔁 para dejar entrar al administrador, entrega un enlace nuevo con `user setup-link` en el servidor (arriba). Reiniciar el servidor con el mismo `LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN` no da un enlace nuevo: la instancia ya ha visto ese token. Cada inicio registra una advertencia de que el enlace de configuración se revocó, y pide ejecutar `dev.py user setup-link` o establecer un token nuevo.

Casos especiales:

| Caso | Qué ocurre |
|---|---|
| El administrador completó la configuración después de cargarse tu lista | No hay nada que cancelar: LibreFolio no cambia nada y dice *Este administrador completó su configuración mientras tanto: no se ha cambiado nada.* La pestaña se recarga: la fila muestra un administrador activo, con **Desactivar** en lugar de **Cancelar el enlace de configuración**; su titular ha iniciado sesión |
| Quieres eliminar la cuenta | **Eliminar** ([Eliminar una cuenta](#delete)), sin **Quitar administrador** antes. La cuenta se elimina con sus enlaces de configuración, la plaza queda libre y nadie espera ya una configuración: `user setup-link` no encuentra a nadie, y las variables `LIBREFOLIO_ADMIN_*` no crean nada en los siguientes inicios, ya que la instancia tiene cuentas |
| Quieres eliminarla, pero la configuración se completó mientras tanto | No se elimina nada: el diálogo dice *Un administrador debe ser degradado antes de poder eliminarlo.*, ya que ahora es un administrador activo |

### 🔤 Nombres de usuario con una @ {: #usernames-with-at }

Desde la versión 1.3 un nombre de usuario nuevo no puede contener `@`: al iniciar sesión, LibreFolio lee cualquier cosa con una `@` como una dirección de correo electrónico. El registro, un cambio de nombre de usuario en el Perfil y `user create` en la [línea de comandos](cli_tools.md) lo rechazan; un `LIBREFOLIO_ADMIN_USERNAME` con una `@` detiene el servidor al iniciar («El administrador inicial» en [Variables de entorno](configuration_accounts.md#initial-admin)). Los espacios, las letras con tilde y signos como `.`, `_`, `-` o `+` están permitidos.

Una cuenta creada antes de la versión 1.3 puede tener uno, por ejemplo `anna@example.com`:

- 🏷️ el nombre de usuario se queda como está: nada lo renombra. El usuario puede cambiarlo en su propio [Perfil](../user/settings/profile.md), por un nombre sin `@`;
- 🔑 la cuenta inicia sesión con su propia dirección de correo electrónico. El nombre de usuario funciona al iniciar sesión solo mientras ninguna cuenta lo tenga como su dirección de correo electrónico: una dirección escrita nombra a la cuenta que es su titular;
- 📧 ninguna otra cuenta puede tomar ese nombre de usuario como su dirección de correo electrónico, con cualquier combinación de mayúsculas: el registro, el Perfil, `user create` y `user set-email` lo rechazan con *Correo electrónico ya registrado*. La propia cuenta puede tomarlo como su dirección.

---

## ✉️ Invitaciones {: #invitations }

**Dónde:** **Usuarios**, botón **Invitar**. En el servidor: `pipenv run ./dev.py user invite` ([línea de comandos](cli_tools.md)).

1. Haz clic en **Invitar**.

2. Opcional: escribe su dirección en **Correo (opcional)**.

    Es solo una nota de a quién va dirigida la invitación: el enlace funciona para quien lo abra. La lista de invitaciones la muestra, y el formulario de registro parte de ella, editable.

3. Marca **Administrador** si la cuenta nueva debe gestionar la instancia.

4. Haz clic en **Crear el enlace**.

    *Comparte este enlace: funciona una sola vez, durante 7 días.* Comprueba la [dirección del servidor](#server-address), haz clic en **Copiar** y envía el enlace tú mismo (mensaje o correo), o deja que lo envíe LibreFolio: [Enviar por correo electrónico](#send-by-email).

5. Haz clic en **Hecho**.

    La invitación aparece en **Invitaciones abiertas**. La persona abre el enlace y crea la cuenta con el nombre de usuario, el correo electrónico y la contraseña que elija: [Primeros pasos](../user/getting-started.md) muestra lo que ve.

- 🔗 El enlace se muestra una sola vez, cuando lo creas. Si se pierde, revoca la invitación y crea una nueva.
- 📏 Una invitación ocupa una plaza desde que la creas hasta que se usa, se revoca o caduca; la cuenta que crea ocupa entonces esa plaza.
- 🔤 Una dirección de correo electrónico pertenece a una sola cuenta, con cualquier combinación de mayúsculas (`Anna@example.com` es `anna@example.com`), pero solo las letras de la A a la Z se comparan así: `Émile@example.com` y `émile@example.com` son dos direcciones distintas.

### 📋 Invitaciones abiertas {: #open-invitations }

Las invitaciones que nadie ha usado todavía, empezando por la más antigua: el correo electrónico (o *Sin correo*), una insignia **Admin** cuando la invitación crea un administrador, fecha de creación y de caducidad. Una invitación sale de la lista cuando se usa, se revoca o caduca.

**Revocar** retira una invitación en cualquier momento, tras una confirmación: el enlace deja de funcionar de inmediato y su plaza queda libre.

---

## 🔑 Enlaces de restablecimiento de contraseña {: #reset-links }

Cuando alguien ha olvidado su contraseña, envíale un enlace para que elija una nueva por sí mismo. Con correo electrónico, también puede pedir uno desde la página de inicio de sesión: [Contraseñas olvidadas](email_flows.md#forgot-password).

**Dónde:** la fila de la cuenta, botón **Enlace de restablecimiento**. En el servidor: `pipenv run ./dev.py user reset-link <username>` ([línea de comandos](cli_tools.md)).

1. Abre la fila y haz clic en **Enlace de restablecimiento**.

    El diálogo explica: *Un enlace de un solo uso para establecer una nueva contraseña, válido 30 minutos. Los enlaces creados antes para esta cuenta dejan de funcionar.*

2. Haz clic en **Crear el enlace**.

3. Comprueba la [dirección del servidor](#server-address), haz clic en **Copiar** y envía el enlace, o haz clic en **Enviar por correo** ([Enviar por correo electrónico](#send-by-email)). Luego **Hecho**.

    La persona abre el enlace y elige la contraseña: [Primeros pasos](../user/getting-started.md).

- ⏱️ El enlace funciona una sola vez, durante 30 minutos; solo el enlace más reciente de una cuenta es válido.
- 🔒 También deja de funcionar en cuanto la persona cambia su contraseña o su dirección de correo electrónico, o cuando ejecutas `user reset` o `user set-email` en la [línea de comandos](cli_tools.md).
- 🚪 Crear el enlace no cierra la sesión de nadie. Cuando la persona establece la nueva contraseña, se cierra la sesión de la cuenta en todos los dispositivos.
- 🔗 El enlace se muestra una sola vez: si se pierde, crea uno nuevo.

---

## 🌐 La dirección del servidor de un enlace {: #server-address }

Los enlaces de invitación y de restablecimiento de contraseña se muestran en el mismo panel:

- **Dirección del servidor**: dónde empieza el enlace. Se rellena con `LIBREFOLIO_PUBLIC_URL` cuando el servidor la establece, y si no con la dirección que usa ahora tu navegador. *Cámbiala si tus usuarios acceden a LibreFolio desde otra dirección*: por ejemplo, estás en `http://192.168.1.10:6040` en casa, y tus usuarios entran por `https://librefolio.example.com`.
- **Enlace**: la dirección del servidor seguida de la ruta del enlace. **Copiar** lo pone en el portapapeles; si el navegador lo rechaza, el enlace queda seleccionado para que puedas copiarlo a mano. *Válido hasta el …* indica su caducidad.

Cuando cambias la dirección, medio segundo después de que dejes de escribir el navegador comprueba que **esta** instancia responde allí, y no un servidor cualquiera: carga `<address>/api/v1/auth/address-probe.png?nonce=…`. La propia dirección rellenada no se comprueba.

| Mensaje | Qué significa |
|---|---|
| *Comprobando que este LibreFolio responde en esta dirección…* | La comprobación está en marcha |
| *Esta instancia responde en esta dirección.* | El enlace llega a este LibreFolio |
| *Algo responde en esta dirección, pero no esta instancia: compruébala antes de compartir.* | Otro LibreFolio responde allí: probablemente no es la dirección que querías |
| *No se ha podido comprobar esta dirección desde este navegador: aun así puedes compartir el enlace.* | El navegador no cargó la imagen. No responde nada allí (una dirección equivocada o cerrada, o ninguna respuesta en 8 segundos); una página `https://` comprueba una dirección `http://`, que el navegador bloquea; una página en una dirección pública comprueba una dirección local, que algunos navegadores bloquean o permiten solo después de pedirte permiso; una instancia bloqueada no sirve la imagen; o responde un LibreFolio más antiguo, que no se puede comprobar |
| *Introduce una dirección que empiece por http:// o https://, sin ? ni #.* | No es una dirección: **Copiar** sigue desactivado hasta que lo corrijas |

Sea cual sea el resultado, salvo una dirección que no lo sea, puedes copiar el enlace: la comprobación es solo un consejo. De vuelta a la dirección rellenada, el mensaje desaparece. Cómo funciona: [Sonda de dirección](../developer/architecture/security.md#address-probe), para desarrolladores.

!!! tip "🌐 Establece la dirección una vez"

    **Dónde:** en el `.env` de LibreFolio, la dirección que abren tus usuarios:

    ```bash
    LIBREFOLIO_PUBLIC_URL=https://librefolio.example.com
    ```

    El panel parte de ahí: «Cuentas y registros» en [Variables de entorno](configuration_accounts.md#accounts). La [línea de comandos](cli_tools.md) la pone también delante de los enlaces que imprime.

---

## 📧 Enviar por correo electrónico {: #send-by-email }

Condición: correo electrónico **Listo** y `LIBREFOLIO_PUBLIC_URL` establecida en una dirección que LibreFolio pueda usar ([Correos con un enlace](email_flows.md#public-url)). Entonces los dos diálogos de enlace tienen **Enviar por correo** bajo el enlace. Sin correo electrónico el botón no está: copia el enlace como antes.

| | Invitación | Enlace de restablecimiento de contraseña |
|---|---|---|
| **Destinatario** | **Enviar a** parte de la dirección escrita en la invitación; puedes cambiarla. Si está vacío, el correo va a la dirección de la invitación; si no hay ninguna, el diálogo pide una dirección | Sin campo: va a la dirección de la cuenta, y solo mientras la cuenta está activa |
| **Idioma** | **Idioma del correo**: el **Idioma Predeterminado** de la instancia, salvo que elijas otro | El idioma de la cuenta |

- 🌐 **El enlace del correo empieza con `LIBREFOLIO_PUBLIC_URL`**, sea lo que sea lo que muestre la **Dirección del servidor** de arriba: el diálogo lo dice.
- 📨 **El resultado** está en el diálogo: *Enviado a …* con la dirección y el idioma del correo, o por qué el correo no salió ([Errores de envío](email_troubleshooting.md#sending-errors)).

Reglas y límites: [Enlaces enviados por un administrador](email_flows.md#admin-links).

---

## 🗑️ Eliminar una cuenta {: #delete }

**Dónde:** la fila de la cuenta, botón **Eliminar**. Para un administrador, primero **Quitar administrador**; no para el administrador inicial [en espera de su enlace de configuración](#cancel-setup), que eliminas directamente. La línea de comandos no elimina cuentas.

La eliminación sigue la misma regla que eliminar la propia cuenta ([Perfil](../user/settings/profile.md)):

1. Para una cuenta activa, el diálogo ofrece primero **Desactivar** como alternativa.

    Conserva todos los brókers y transacciones y se puede deshacer; la cuenta simplemente deja de iniciar sesión.

2. El diálogo muestra lo que se llevaría la eliminación:

    - **Eliminados, con todas sus transacciones y archivos**: los brókers de los que la cuenta es la única propietaria, cada uno con su número de transacciones. Se eliminan también para los usuarios con los que los compartía. Si no hay ninguno: *No se elimina ningún bróker*;
    - **Brókers compartidos que se mantienen (solo desaparece el acceso)**: los demás brókers que la cuenta puede abrir, con su rol en cada uno;
    - una advertencia cuando transacciones de otros brókers son mitades de transferencias con los brókers eliminados: se mantienen, sin la otra mitad. Una transferencia recibida pasa a ser un ajuste a su coste; una transferencia enviada a uno de esos brókers, un ajuste que saca los activos del bróker que los envió, sin un valor: su coste cuenta como una pérdida realizada en ese bróker ([Editar o eliminar un bróker](../user/brokers/index.md)).

3. Escribe el nombre de usuario de la cuenta y luego haz clic en **Eliminar Permanentemente**.

    La cuenta, su configuración y los brókers listados se eliminan al instante.

!!! danger "Eliminar una cuenta no se puede deshacer"

    Quien tenga la sesión iniciada con esa cuenta se desconecta en la siguiente petición. Si la eliminación falla por una razón técnica, no se elimina nada. Si el diálogo no puede cargar lo que se llevaría la eliminación, no te deja eliminar: ciérralo e inténtalo de nuevo.

Cómo funciona la regla: [Eliminar una cuenta](../developer/architecture/access_control.md#admin-account-deletion), para desarrolladores.

---

## 🔗 Relacionado

- 📝 **[Variables de entorno](configuration_accounts.md#accounts)** — «Cuentas y registros»: `LIBREFOLIO_MAX_USERS`, `LIBREFOLIO_REGISTRATION` y `LIBREFOLIO_PUBLIC_URL`
- ⚙️ **[Configuración global](settings.md)** — «Quién puede registrarse»: el ajuste **Registro**
- 🛠️ **[Herramientas de línea de comandos](cli_tools.md)** — «Gestionar usuarios»: la mayor parte de estas tareas, sin navegador
- 👤 **[Perfil](../user/settings/profile.md)** — Tu propia cuenta y cómo eliminarla
- 🧑‍💻 Para desarrolladores: **[API de administrador](../developer/architecture/access_control.md#admin-user-api)** y **[Componentes de configuración](../developer/frontend/components/features/settings.md#userstab)**
