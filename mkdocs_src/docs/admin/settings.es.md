# ⚙️ Configuración global

La configuración global se aplica a toda la instancia y a cada usuario. Se guarda en la base de datos, y
solo los administradores tienen su pestaña para verla y cambiarla. No es secreta, sin embargo: la aplicación
la lee para cada usuario con sesión iniciada, para aplicarla (el límite de subida, los valores predeterminados de las
[Preferencias](../user/settings/preferences.md)…), y cualquier usuario con sesión iniciada puede leerla a través de la
API.

---

## 🗂️ Configuración › Administración {: #administration }

**Configuración global** es la primera pestaña de **Administración**, el grupo de pestañas que se encargan de la
instancia, en el extremo derecho de la barra de pestañas de **Configuración** en una pantalla ancha. Solo los administradores tienen
el grupo. Haz clic en **Administración**: se abre **Configuración global** y una segunda fila de pestañas debajo de la
primera, con las pestañas del grupo.

| Pestaña | Quién la tiene | Para qué sirve |
|---|---|---|
| ⚙️ **Configuración global** | Administradores | La configuración de esta página |
| 👥 **Usuarios** | Administradores | Las cuentas, invitaciones y enlaces de restablecimiento de contraseña: [Usuarios e invitaciones](users.md) |
| 💾 **Copia de seguridad** | Administradores | Toda la instancia en un solo archivo, y su restauración: [Copia de seguridad, restauración y traslado](backup_restore.md) |
| ✉️ **Correo electrónico** | Administradores | Si LibreFolio puede enviar correos, y un correo de prueba: [Correo electrónico](email.md) |
| 🛡️ **Seguridad** | Administradores | Cómo está configurada la instancia, y qué necesita tu atención: [Seguridad](#security-tab), más abajo |

- 👤 Un usuario que no es administrador no tiene el grupo **Administración**, ni ninguna de sus pestañas: su
  **Configuración** termina en **Acerca de**, y un enlace a una de las pestañas del grupo abre su **Perfil**
  en su lugar.
- 🔁 Hacer clic en **Administración** mientras una de sus pestañas está abierta mantiene esa pestaña abierta.
- 🔢 Un número en **Seguridad**, repetido en **Administración**, cuenta los errores y advertencias de las
  [comprobaciones de seguridad](#security-tab).
- 📱 En un teléfono, las pestañas muestran solo sus iconos, y el título de la página nombra la pestaña abierta.

---

## ✏️ Cambiar una configuración

### 🔓 1. Desbloquear la pestaña

Abre **Configuración** (icono de engranaje en la barra lateral), luego **Administración**, que se abre en
**Configuración global**: su panel agrupa la configuración por categoría. Haz clic en el **icono de candado** (🔒) en la
cabecera para desbloquearla. Solo los administradores (superusuarios) tienen esta pestaña.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Configuración global" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💾 2. Editar y guardar

- No se escribe nada hasta que hagas clic en **Guardar** junto a una configuración, o en **Guardar todo** en la cabecera.
  **Deshacer** y **Deshacer todo** recuperan los valores guardados.
- **Restablecer al valor predeterminado** y **Restablecer todo a los valores predeterminados** rellenan los valores
  predeterminados, listos para guardar.
- Los valores guardados se aplican de inmediato, sin reiniciar.

??? note "🔒 Bloquear con cambios sin guardar — cuando un diálogo pregunta primero"

    Hacer clic en el candado con cambios sin guardar pregunta si se descartan. **Cancelar** mantiene tus
    ediciones; **Descartar** devuelve los valores guardados y bloquea la pestaña.

??? tip "💻 Configuraciones faltantes — recrearlas desde la línea de comandos"

    Cada inicio del servidor vuelve a crear cualquier configuración faltante con su valor predeterminado. Para hacerlo sin
    reiniciar, ejecuta la [herramienta de línea de comandos](cli_tools.md):

    ```bash
    pipenv run ./dev.py user init-settings
    ```

    Se conservan los valores que cambiaste.

---

## 📋 Qué hace cada configuración

| Categoría | Configuración | Predeterminado | Qué hace — cuándo cambiarla |
|---|---|---|---|
| ⏳ Sesión | **Duración de la sesión** | 24 horas | Cuánto tiempo permanecen los usuarios con la sesión iniciada. Redúcela en dispositivos compartidos; un nuevo valor se aplica desde el siguiente inicio de sesión de cada usuario. |
| 🛡️ Seguridad | **Registro** | Por invitación | Quién puede crear una cuenta: **Abierto**, **Por invitación** o **Cerrado** (consulta [Quién puede registrarse](#registration)). Una instancia actualizada desde una versión anterior conserva el modo que tenía. **Abierto** deja entrar a cualquiera que llegue a la página de inicio de sesión: evítalo si se puede acceder a la instancia desde internet. Los administradores que abren la aplicación en una dirección fuera de la red local reciben una [advertencia](#open-registration-warning) mientras está **Abierto**. |
| 🛡️ Seguridad | **Requerir verificación de correo electrónico** | Desactivado | Las cuentas nuevas deben abrir un enlace enviado por correo a su dirección antes de poder iniciar sesión; la primera cuenta nunca espera, y las cuentas existentes no se ven afectadas. Solo se activa mientras el correo funciona y se puede usar `LIBREFOLIO_PUBLIC_URL`: hasta entonces el interruptor está atenuado. Consulta *Verificación de correo electrónico* en [Correo electrónico](email.md). |
| 🔄 Tarea de actualización | **Planificador habilitado** | Activado | Activa o desactiva las actualizaciones automáticas de precios y tipos de cambio: consulta [Planificador de datos de mercado](#market-data-scheduler). |
| 🧠 Memoria | **Tamaño máximo de archivo subido** | 10 MB | El archivo más grande que los usuarios pueden subir, informes del bróker incluidos. Auméntalo si se rechaza una exportación grande. |
| — (no se muestra en esta pestaña) | **Límite de espacio (MB)** | `0`, sin límite | La cantidad máxima de megabytes que la instancia puede ocupar, que se muestra como la línea contra la que se dibuja la barra de espacio de **Archivos**. `0` es sin límite: la barra entonces muestra el disco. La editas en esa barra, que solo ven los administradores, no en esta pestaña. `LIBREFOLIO_STORAGE_LIMIT_MB`, cuando está definida, prevalece y la bloquea ([Variables de entorno](configuration.md)). Consulta [La barra de espacio](backup_restore.md#space-used). |
| 🌍 Valores predeterminados | **Divisa predeterminada** | `EUR` | La divisa en la que informan los usuarios nuevos. Hasta que la guardas por primera vez, `LIBREFOLIO_DEFAULT_CURRENCY` en el archivo `.env`, si está definida, decide; desde tu primer guardado, prevalece tu valor, incluso cuando vuelve a ser `EUR` ([Variables de entorno](configuration_accounts.md#accounts)). |
| 🌍 Valores predeterminados | **Idioma predeterminado** | `en` | 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr` o 🇪🇸 `es`. También es el idioma de los correos enviados a personas que aún no tienen cuenta. Hasta que lo guardas por primera vez, `LIBREFOLIO_DEFAULT_LANGUAGE` en el archivo `.env`, si está definido, decide; desde tu primer guardado, prevalece tu valor, incluso cuando vuelve a ser inglés ([Variables de entorno](configuration_accounts.md#accounts)). |
| 🌍 Valores predeterminados | **Tema predeterminado** | `auto` | ☀️ `light`, 🌙 `dark`, o 🖥️ `auto`, que sigue al dispositivo. |

Los usuarios nuevos parten de los tres valores predeterminados: la [Configuración de bienvenida](../user/getting-started.md#welcome-setup)
muestra su idioma y divisa ya rellenados. Cambiar un valor predeterminado más tarde deja intactas las
[Preferencias](../user/settings/preferences.md) de los usuarios existentes.

---

## 🚪 Quién puede registrarse {: #registration }

La configuración **Registro** decide quién puede crear una cuenta:

| Modo | Quién puede crear una cuenta |
|---|---|
| 🌐 **Abierto** | Cualquiera que llegue a la página de inicio de sesión, con **Regístrate aquí**. |
| ✉️ **Por invitación** (predeterminado) | Solo las personas con un enlace de invitación. Creas un enlace por persona desde la pestaña [Usuarios](users.md#invitations), o desde la [línea de comandos](cli_tools.md#invite), y se lo envías. La página de inicio de sesión no muestra **Regístrate aquí**. |
| 🔒 **Cerrado** | Nadie, ni siquiera con un enlace de invitación. La página de inicio de sesión no muestra **Regístrate aquí**. |

- 👑 La primera cuenta de una instancia nueva siempre se puede crear, sea cual sea el modo: hasta que
  exista, la página de inicio de sesión muestra **Regístrate aquí**, y la cuenta que se crea se convierte en
  administrador. Con `LIBREFOLIO_ADMIN_EMAIL`, LibreFolio crea ese administrador por sí mismo en su
  primer inicio, y nadie puede registrarse en su lugar: consulta
  [El administrador inicial](configuration_accounts.md#initial-admin).
- 🆕 Una instancia nueva empieza en **Por invitación**. Una instancia actualizada desde una versión anterior conserva
  el modo que tenía: una que estaba **Abierta**, el valor predeterminado anterior, sigue **Abierta** hasta que lo cambies
  (**Restablecer al valor predeterminado** propone **Por invitación**). Una vez que todos tienen una cuenta, elige
  **Por invitación** o **Cerrado**.
- ✉️ Un enlace de invitación funciona una vez, durante 7 días, y puede hacer que la nueva cuenta sea administrador. Con
  **Abierto**, nadie necesita uno, pero un enlace sigue otorgando su rol.
- 👥 La misma configuración está en la pestaña [Usuarios](users.md#registration), junto a **Invitar**: eliges
  el modo allí y se guarda de inmediato, y solo pide confirmación al elegir **Abierto**. Si
  `LIBREFOLIO_REGISTRATION` establece el modo, ambos lugares lo muestran y ninguno puede cambiarlo.
- 💻 Sea cual sea el modo, la [línea de comandos](cli_tools.md) sigue pudiendo crear cuentas con
  `user create`.
- 📏 Con un límite de usuarios, nadie puede registrarse sin una invitación una vez que la instancia está llena: consulta
  [Cuando la instancia está llena](configuration_accounts.md#user-limit).
- 🔒 Si la configuración del servidor establece `LIBREFOLIO_REGISTRATION`, ese valor decide: el campo
  lo muestra, no se puede cambiar y dice *Establecido en el servidor por LIBREFOLIO_REGISTRATION: cámbialo
  allí*. **Restablecer todo a los valores predeterminados** no lo toca. Consulta [Cuentas y registros](configuration_accounts.md#accounts).
- ⬆️ Esta configuración reemplaza el interruptor **Habilitar registro** de versiones anteriores, y la actualización
  conserva tu elección: un interruptor que estaba activado se convierte en **Abierto**, un interruptor que estaba desactivado se convierte en **Cerrado**.

!!! warning "🆕 Una instancia nueva: crea tu cuenta primero"

    Hasta que exista la primera cuenta, cualquiera que llegue a la página de inicio de sesión puede crearla con
    **Regístrate aquí**, sea cual sea el modo, `LIBREFOLIO_REGISTRATION` incluido, y esa cuenta
    se convierte en el administrador. Regístrate en cuanto el servidor esté en marcha, antes de hacerlo accesible
    desde internet. A partir de la segunda cuenta, se aplica el modo: con **Por invitación**, el
    valor predeterminado, la página de inicio de sesión ya no muestra **Regístrate aquí**.

    También puedes crear el primer administrador desde la [línea de comandos](cli_tools.md), sin el
    navegador:

    ```bash
    pipenv run ./dev.py user create <username> <email> <password>
    ```

    Con Docker: `docker compose exec librefolio python dev.py user create <username> <email> <password>`.

    O asigna a LibreFolio `LIBREFOLIO_ADMIN_EMAIL` antes de su primer inicio: entonces crea el
    administrador por sí mismo, con un enlace de configuración para ti, y nadie puede registrarse en su lugar
    ([El administrador inicial](configuration_accounts.md#initial-admin)).

### 📢 La advertencia de registro abierto {: #open-registration-warning }

Mientras **Registro** está **Abierto**, un administrador que abre LibreFolio en una dirección fuera de la
red local recibe una advertencia sobre las páginas de la aplicación:

*El registro está abierto y esta instancia es accesible desde fuera de tu red local: cualquiera que
la encuentre puede crear una cuenta.*

Su enlace, **Cambiar quién puede registrarse**, abre **Configuración › Administración › Configuración global**, donde
está esta configuración. Cuando `LIBREFOLIO_REGISTRATION` establece el modo en el servidor, la advertencia nombra esa
variable en su lugar y no tiene enlace: solo la configuración del servidor puede cambiar el modo
([Cuentas y registros](configuration_accounts.md#accounts)).

- 👑 Solo los administradores la ven.
- 🌐 Tu navegador decide, a partir del nombre o la dirección IP de su barra de direcciones (el puerto no
  importa). No se envía nada al servidor y nada comprueba si realmente se puede acceder a la instancia desde internet. Estas direcciones cuentan como locales y no reciben advertencia:
    - `localhost`, y todos los nombres que terminan en `.localhost`;
    - un nombre sin punto, como `nas`, y todos los nombres que terminan en `.local`, `.lan`, `.home.arpa`
      o `.internal`;
    - las direcciones IPv4 de `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` y
      `100.64.0.0/10` (NAT de nivel de operador, el rango donde Tailscale numera sus dispositivos);
    - la dirección IPv6 `::1`, y las de `fc00::/7` y `fe80::/10`; una dirección IPv4 escrita como
      IPv6, como `::ffff:192.168.1.10`, cuenta como la dirección IPv4 que contiene.

    Las mayúsculas y un punto final no cambian nada. Cualquier otra dirección cuenta como exterior, incluidos los nombres de Tailscale
    que terminan en `.ts.net`: Tailscale Funnel puede publicarlos en internet.
- ✖️ Su botón de cierre la oculta hasta que la página se vuelve a cargar.
- 🔄 Desaparece en cuanto el modo deja de ser **Abierto**: guardar **Registro** aquí la actualiza
  de inmediato.
- 🛡️ La pestaña [Seguridad](#security-tab) enumera la misma advertencia entre sus hallazgos, mientras
  se mantenga, incluso después de cerrarla sobre las páginas.

Cómo decide, para desarrolladores:
[La advertencia de registro abierto](../developer/architecture/security.md#open-registration-warning).

---

## 🕐 Planificador de datos de mercado {: #market-data-scheduler }

El planificador mantiene los precios y los tipos de cambio actualizados por sí solo, incluso cuando nadie tiene la sesión iniciada:

- 💰 **Actualización del precio actual** — cada pocos minutos, el último precio de cada activo activo que tiene
  un proveedor de precios.
- 📊 **Sincronización del historial** — en los días y horas que elijas, los precios diarios de esos activos y los
  tipos de cada par FX con un proveedor, durante al menos el **Horizonte de retroceso**, para rellenar cualquier hueco.
  Para un activo o un par FX cuyo último precio o tipo guardado sea más antiguo, retrocede hasta ese día, hasta un
  año; un activo que aún no tiene ningún precio guardado recibe solo el horizonte, ya que el planificador nunca descarga un
  historial completo. Los pares FX que solo tienen tipos manuales se omiten.

Si el servidor está apagado o suspendido a la hora de una sincronización, la sincronización del historial que se perdió se ejecuta en cuanto el servidor
vuelve, en lugar de esperar a la siguiente hora de sincronización: un servidor apagado durante semanas rellena todo su hueco.

### ⚙️ Configurar la programación

Desbloquea la pestaña, abre **Tarea de actualización** y haz clic en **Configurar…** en la fila **Configuración de la programación**.
El diálogo tiene su propio botón **Guardar**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modal de configuración del planificador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Campo | Predeterminado | Qué establece |
|---|---|---|
| **Zona horaria** | `UTC` | La zona horaria de las horas y días siguientes; el reloj UTC del servidor se muestra junto a ella. Hasta que guardas la programación por primera vez, `LIBREFOLIO_DEFAULT_TIMEZONE` en el archivo `.env`, si está definido, decide; desde tu primer guardado, prevalece tu valor, incluso cuando vuelve a ser `UTC` ([Variables de entorno](configuration_accounts.md#accounts)). |
| **Actualizar cada** | 10 minutos | Con qué frecuencia se actualizan los precios actuales, de 1 a 1440 minutos. |
| **Horas de sincronización** | `06:00`, `23:00` | Cuándo se ejecuta la sincronización del historial; **Añadir hora** añade una franja. |
| **Días de sincronización** | Lun a Sáb | Los días de la sincronización del historial. |
| **Horizonte de retroceso** | 14 días | Cuántos días pasados comprueba como mínimo cada sincronización del historial, de 1 a 365. Retrocede más, hasta un año, cuando el último precio o tipo guardado de un activo o un par FX es más antiguo. |

Mantén al menos una hora y un día. Consejo: una sincronización del historial después del cierre de los mercados (por ejemplo,
`22:00`) obtiene los datos más completos.

??? warning "🌍 Cambiar la zona horaria — las tareas se desplazan en el tiempo"

    Las horas y los días conservan sus valores pero cuentan en la nueva zona horaria, así que las tareas se ejecutan en otro
    momento. También siguen su horario de verano: `06:00` en `Europe/Rome` se ejecuta a las 05:00 UTC
    en invierno y a las 04:00 UTC en verano.

### 📜 Leer el registro del planificador

La fila **Estado del planificador** muestra la última actualización del precio actual, con un punto para su resultado.
Mientras hay un reintento pendiente, una línea adicional indica su hora: **Fallido: próximo intento a las …** tras una
actualización que no pudo terminar; si no, **Elementos pausados reintentados a las …** para los precios diferidos
porque su proveedor se había pausado.
Haz clic en la fila (o en **Detalles…**) para abrir el **Registro de ejecución del planificador**. Solo los administradores pueden
leer el estado y el registro.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modal del registro del planificador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- Cada entrada es una ejecución: tarea, hora, duración y cuántos elementos tuvieron éxito. 🟢 **OK**: todos
  ellos, o nada que hacer; 🟡 **Parcial**: algunos fallaron, o se difirieron porque su proveedor se pausó tras demasiadas
  peticiones; 🔴 **Error**: ninguno tuvo éxito y ninguno se difirió.
- Haz clic en una entrada para ver cada activo o par FX, su proveedor y los precios cambiados (**Delta**).
  Pasa el cursor sobre un error para leerlo completo; haz doble clic en él (pulsación larga en un teléfono) para copiarlo.
- Un elemento diferido muestra un icono de pausa y **Diferido: proveedor pausado**: pasa el cursor sobre la etiqueta para leer el
  mensaje del proveedor. La entrada cuenta los elementos diferidos con ⏸, junto a ✓ y ✗ (por ejemplo,
  `3/5 ✓ · 1 ⏸ · 1 ✗`), y **Reintentar a las** en su cabecera indica la hora fijada para reintentarlos.
- Filtra por tarea, estado o periodo, desde la última hora hasta los últimos 30 días. Solo se conservan las
  ejecuciones más recientes.

---

## ⏸️ Pausas de proveedores {: #provider-pauses }

LibreFolio pide precios y tipos de cambio a servicios externos: sus proveedores de precios, como Yahoo
Finance o el Banco Central Europeo. Cuando uno de ellos responde «demasiadas peticiones» (HTTP 429),
LibreFolio lo pausa: hasta que termina la pausa, ninguna petición llega a ese proveedor, ya sea que la solicite el
[planificador de datos de mercado](settings.md#market-data-scheduler) o un usuario. Una pausa se mantiene para cada
usuario y cada tarea del servidor.

Las pausas están activadas por defecto: una excepción a la regla de que una nueva opción deja una instalación como
estaba, por la decisión de desarrollo n.º 34 (15 de octubre de 2026). `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0`
las desactiva, como antes de la versión 1.3.

| Variable | Predeterminado | Qué hace |
| --- | --- | --- |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | La primera pausa, en segundos, duplicada en cada rechazo seguido: un número entero de `0` a `86400` (un día). `0` desactiva las pausas. |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | La pausa más larga que alcanza la duplicación, en segundos: un número entero de `1` a `86400`, y no inferior a la primera pausa mientras las pausas están activadas. Un `Retry-After` del proveedor aún puede pedir más, hasta un día. |

Defínelas en `.env` o en el entorno del contenedor, luego reinicia LibreFolio: con Docker Compose,
`docker compose up -d`. Un valor que LibreFolio no puede usar no detiene el servidor: el registro tiene un
error ([En el registro](#provider-pauses-log)), y se aplican ambos valores predeterminados, 60 y 3600, así que las pausas siguen
activadas. Con las pausas desactivadas, cada petición vuelve a ir al proveedor; el planificador sigue contando una petición rechazada como diferida ([más abajo](#provider-pauses-effects)).

### ⏱️ Cuánto dura una pausa {: #provider-pauses-length }

- **El primer rechazo** pausa el proveedor durante `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS`, 60
  segundos por defecto.
- **Cada rechazo seguido** duplica la pausa, hasta `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS`.
  Con los valores predeterminados: 2 minutos, luego 4, 8, 16 y 32, luego una hora en cada rechazo posterior.
  Las peticiones rechazadas juntas cuentan como un solo rechazo.
- **Un `Retry-After`**, cuando el proveedor lo envía, es la pausa más corta que toma LibreFolio: se
  respeta más allá de la pausa más larga, hasta un día.
- **Un extra aleatorio** de hasta el 10 % se añade a cada pausa, nunca más allá de un día.
- **Cuando termina una pausa**, una petición pasa para probar el proveedor, y las demás siguen contando
  como pausadas hasta que tenga un resultado, un minuto como máximo. Una respuesta termina la serie: el siguiente rechazo
  empieza de nuevo desde la primera pausa, y lo mismo ocurre si un rechazo llega más tiempo que la pausa más larga
  después de que terminara la pausa anterior.
- **Una pausa se mantiene para todo el proveedor**, excepto con el CSS Scraper: un sitio que rechaza pausa
  solo las páginas de ese sitio, y los demás sitios se siguen leyendo.

### 👀 Quién espera, y qué ves {: #provider-pauses-effects }

| Dónde | Durante una pausa |
| --- | --- |
| 🕐 [Planificador de datos de mercado](settings.md#market-data-scheduler) | Los activos y pares FX de un proveedor pausado están **diferidos**: no se cuentan ni como actualizados ni como fallidos, y su tarea es **Parcial**. La tarea se ejecuta de nuevo cuando termina la primera de esas pausas, o a su hora habitual si llega antes. En **Configuración global**, la fila **Estado del planificador** dice **Elementos pausados reintentados a las …** para la actualización del precio actual; el **Registro de ejecución del planificador** cuenta los elementos diferidos con ⏸, marca cada uno con un icono de pausa y **Diferido: proveedor pausado**, y muestra **Reintentar a las …** en la cabecera de la entrada: consulta «Leer el registro del planificador» en esa página. |
| 💰 Precios en vivo, en la lista de Activos y en la página de un activo | Se mantiene el último precio almacenado, sin ningún mensaje nuevo. Cuando todos los activos sobre los que pregunta la página tienen su proveedor pausado, la página vuelve a preguntar por sí misma solo cuando ha terminado la primera de esas pausas; mientras un proveedor siga respondiendo, la actualización continúa, y LibreFolio no llama a los pausados. Tras una actualización que falla, la siguiente espera el doble, y así hasta diez minutos, hasta que una actualización vuelve a funcionar. |
| 🔌 **Probar configuración**, en el diálogo del activo | ⚠️ *Pausado por demasiadas peticiones hasta …*, con la hora a la que termina la pausa; la prueba sigue pasando. Consulta [Conectar un proveedor de precios](../user/assets/create-edit.md). |
| 🔎 Búsqueda de activos | Un proveedor pausado no da resultados hasta que termina su pausa; los demás proveedores responden como de costumbre. |
| 💱 Tipos de cambio | Un proveedor pausado cuenta como una ruta que falló: un par FX con otra ruta obtiene su tipo allí, como cuando un banco central no responde ([Configuración de proveedores](../user/fx/detail/provider.md)). Si no, el planificador difiere el par, como hace con un activo. |

### 💤 En memoria {: #provider-pauses-memory }

- **Cada proceso del servidor mantiene sus pausas en memoria.** Un reinicio las olvida, incluido un despliegue.
  Con varios procesos del servidor (`--workers N`), cada uno conoce solo las pausas de sus propios rechazos;
  la imagen de Docker ejecuta uno.

### 📋 En el registro {: #provider-pauses-log }

| Nivel | El registro dice | Cuándo |
| --- | --- | --- |
| ⚠️ `warning` | `Provider refused for too many requests: paused`, con `domain` (`asset` o `fx`), `provider`, `scope` (el sitio, con el CSS Scraper), `wait_s`, los segundos de pausa por delante, y `retry_after`, la espera que pidió el proveedor, si la hay | Un proveedor rechazó una petición |
| ℹ️ `info` | `Provider answering again after a pause`, con `refusals`, los rechazos seguidos antes de ella | La primera respuesta tras una pausa |
| ❌ `error` | `Provider pause settings cannot be used: the defaults apply`, con `variable`, `code` (`PROVIDER_COOLDOWN_BASE_INVALID` o `PROVIDER_COOLDOWN_MAX_INVALID`) y `reason` | Una de las dos variables tiene un valor que no se puede usar: una vez por proceso del servidor, la primera vez que LibreFolio está a punto de llamar a un proveedor |

En nivel `DEBUG`, `Provider call skipped: paused after too many requests`, con `wait_s`, marca cada
petición que una pausa impidió enviar al proveedor. Las líneas propias del planificador, `Scheduler: current-price refresh`
y `Scheduler: history sync`, dan los elementos diferidos en `deferred`, con `retry_at`.

---

## 🗄️ Cachés del servidor {: #server-caches }

Para mantenerse rápido, LibreFolio mantiene en memoria las respuestas recientes de los proveedores y los resultados calculados. El
panel **Estado de la caché**, al final de la categoría **Memoria**, enumera cada caché con su
**Tamaño / Máx.** y su **TTL** (cuánto se conserva una entrada). Haz clic en una cabecera de columna para ordenar;
**Actualizar** actualiza los números.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Panel de cachés del servidor en Configuración global (categoría Memoria)">
</div>

El panel muestra sus cifras tanto si la pestaña está bloqueada como si no. Con la pestaña desbloqueada, puedes vaciar
una caché con **Vaciar** o todas con **Vaciar todo**, para forzar datos nuevos sin reiniciar.
Un reinicio también vacía todas las cachés.

!!! warning "Vaciar una caché ralentiza la siguiente obtención"

    Ambas acciones piden confirmación primero. Tras un vaciado, la siguiente petición de esos datos vuelve
    a los proveedores, así que espera una ralentización similar a la de un reinicio del servidor mientras las cachés se
    vuelven a llenar.

??? note "🧵 Varios workers — cuando el servidor se ejecuta con `--workers`"

    Cada proceso worker tiene sus propias cachés. El panel muestra, y vacía, las del worker que
    respondió; reinicia el servidor para vaciarlas todas.

---

## 🛡️ Seguridad {: #security-tab }

**Configuración › Administración › Seguridad** comprueba cómo está configurada esta instancia y enumera primero
lo que necesita tu atención. Solo los administradores tienen esta pestaña. No es la categoría 🛡️ **Seguridad**
de Configuración global, que contiene **Registro** y **Requerir verificación de correo electrónico**.

### 🚦 Qué enumera {: #security-findings }

Cada hallazgo indica qué está mal, con su icono y su color: ❌ un **error**, ⚠️ una **advertencia** o
ℹ️ una **información**. Los errores van primero, luego las advertencias y luego la información; dentro de cada gravedad, los
hallazgos mantienen el orden de esta tabla.

| Comprobación | Un hallazgo cuando | Su enlace |
|---|---|---|
| Clave de firma de sesión | ℹ️ La clave es aleatoria: cada reinicio desconecta a todos; define `JWT_SECRET` para seguir conectado. ⚠️ La clave tiene menos de 32 caracteres. ❌ No se puede leer su `JWT_SECRET_FILE` | — |
| Secretos definidos dos veces | ⚠️ Un secreto está definido tanto directamente como a través de su variable `_FILE`: prevalece el valor directo | — |
| Clave de instancia | ❌ No se puede usar. ⚠️ Su carpeta o su archivo está abierto a otros usuarios | — |
| Cookie de sesión | ⚠️ `SESSION_COOKIE_SECURE=never`: la cookie también viaja por HTTP simple | — |
| Dirección del visitante | ⚠️ Desde el inicio, las peticiones llegaron a través de un proxy inverso en el que LibreFolio no confía: los límites por dirección de visitante no se les aplican. ℹ️ Desde el inicio, se ignoraron las cabeceras de reenvío de una dirección pública. Qué hacer: [La dirección del visitante](connection_proxy.md#client-address) | — |
| Nivel de registro | ℹ️ `DEBUG` o `TRACE` | — |
| Modo de prueba | ❌ `LIBREFOLIO_TEST_MODE` está activado fuera de las propias ejecuciones de prueba de LibreFolio: se sirven proveedores de datos que existen solo para las pruebas, y los datos se guardan en la carpeta de datos de prueba | — |
| Límite de subida de una restauración | ❌ No se puede usar `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` (un número entero de megabytes, `0` para sin límite): las subidas de restauración se rechazan hasta que se corrija. Se supera con un límite, como *Una restauración acepta archivos de hasta 500 MB.*, o sin ninguno | — |
| Tamaño descomprimido de una restauración | ❌ No se puede usar `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` (un número entero de megabytes, `0` para sin límite): las comprobaciones de restauración se rechazan hasta que se corrija. Se supera con un límite, como *Una comprobación de restauración acepta archivos que se descomprimen hasta 4000 MB.*, o sin ninguno | — |
| Inicios de sesión fallidos | ⚠️ El límite está desactivado: `LIBREFOLIO_LOGIN_LIMIT=off` | — |
| Servidor de correo | ❌ No se puede usar un valor `LIBREFOLIO_SMTP_*`: el correo sigue desactivado hasta que se corrija | **Abrir la pestaña Correo electrónico** |
| Cifrado del correo | ⚠️ Los correos, sus enlaces y la contraseña SMTP viajan sin cifrar a un servidor fuera de tu red local | **Abrir la pestaña Correo electrónico** |
| Enlaces en los correos | ℹ️ El correo funciona, pero `LIBREFOLIO_PUBLIC_URL` no está definida. ⚠️ `LIBREFOLIO_PUBLIC_URL` no puede iniciar un enlace | **Abrir la pestaña Correo electrónico** |
| Secretos de plugins | ❌ Los secretos de plugins de toda la instancia no se pueden leer con la clave de instancia | **Abrir la configuración de plugins**, en **Configuración › Plugins** |
| Registro abierto, comprobado por tu navegador | ⚠️ **Registro** está **Abierto**, y llegaste a LibreFolio en una dirección fuera de tu red local, como en [la advertencia sobre las páginas](#open-registration-warning) | **Cambiar quién puede registrarse**, en **Configuración global**. Ninguno cuando `LIBREFOLIO_REGISTRATION` establece el modo: el hallazgo nombra esa variable en su lugar |
| Un script bloqueado, comprobado por tu navegador | ⚠️ Un script que LibreFolio no envió, añadido por un proxy, un CDN o una extensión del navegador, se bloqueó en esta pestaña del navegador: el hallazgo nombra sus fuentes. Desaparece cuando cierras la pestaña. No se corrige en el servidor, sino en el proxy, el CDN o la extensión: [Un script que no enviaste](configuration_security.md#csp-blocked-script) | — |

Cada fila tiene un botón de ayuda, y cuál es depende de quién pueda resolver la comprobación:

- 📖 **Guía**: puedes resolverla por tu cuenta, en el servidor. El botón, que también se muestra en las comprobaciones superadas, abre
  la página de esta guía que explica esa comprobación, en una pestaña nueva y en tu idioma cuando está
  traducida.

Una comprobación que no tiene página propia ni soporte no tiene botón.

Los hallazgos sin enlace se corrigen en el servidor, en su configuración, y necesitan un reinicio: qué
hacer para cada uno está en la tabla de «Comprobaciones de inicio» en [Configuración](configuration.md), donde
el registro del servidor expresa las mismas comprobaciones.

### 🔢 El número en la pestaña {: #security-badge }

**Seguridad** muestra cuántos errores y advertencias enumera, y **Administración** muestra el mismo
número, para que lo veas desde cada pestaña de Configuración. La información se enumera pero nunca se cuenta: con
solo información, no hay número, y la pestaña tampoco dice *Nada necesita tu atención.*

Fuera de Configuración, el mismo recuento te acompaña en cada página, como un punto en la línea de conexión en la
parte inferior de la barra lateral: rojo con al menos un error, ámbar solo con advertencias, ninguno solo con información.
Haz clic en la línea: tras su motivo, sus detalles enlazan a esta pestaña con el recuento, como
**2 advertencias de seguridad**, errores incluidos. En un teléfono, el botón de menú también lleva el punto. Qué
aspecto tiene: [Advertencias de seguridad para administradores](../user/connection-security.md#security-warnings).

### 🔄 Cuándo comprueba {: #security-refresh }

LibreFolio lee las comprobaciones una vez, en cuanto se abre en tu navegador, sea cual sea la página: la
línea de conexión de la barra lateral las solicita, así que su punto, y el número en la pestaña, ya están ahí
cuando abres **Configuración**. Si esa lectura falla, abrir **Configuración** lo intenta de nuevo. LibreFolio conserva
las comprobaciones mientras usas la aplicación: después de cambiar la configuración del servidor y reiniciarlo, haz clic en
**Comprobar de nuevo**, en la parte superior de la pestaña, o recarga la página. El hallazgo de registro abierto sigue
a **Registro** de inmediato: guardarlo en Configuración global actualiza la lista, el número y el punto.

- ⏳ Hasta la primera respuesta, la pestaña muestra filas de marcador de posición.
- ⚠️ Cuando no se pueden leer las comprobaciones, la pestaña dice *No se pudieron cargar las comprobaciones de seguridad.*, con
  **Intentar de nuevo**. Si **Comprobar de nuevo** falla, los últimos resultados siguen enumerados debajo.

### ✅ Comprobaciones superadas {: #security-passed }

Sin ningún hallazgo, la pestaña dice *Nada necesita tu atención.* Debajo de los hallazgos, una sección plegada,
**N comprobaciones superadas**, enumera las comprobaciones que se superaron, cada una con su propia frase (como *Las sesiones
se firman con una clave establecida por el administrador.*): haz clic en ella para desplegarla. El correo que está desactivado, o que se envía
sin cifrar a un servidor de tu propia red, cuenta como superado, y así lo dice allí.

---

## 🔗 Relacionado

- 📝 **[Variables de entorno](configuration.md)** — La configuración que reside en `.env` en su lugar
- 👥 **[Usuarios e invitaciones](users.md)** — Las cuentas de la instancia, invitaciones y enlaces de restablecimiento de contraseña
- 👤 **[Preferencias del usuario](../user/settings/preferences.md)** — Lo que cada usuario puede cambiar por sí mismo
- 🧑‍💻 Para desarrolladores: **[Sistema de configuración](../developer/architecture/settings.md)**,
  **[Registro de cachés](../developer/architecture/settings_cache.md)**,
  **[Planificador de datos de mercado](../developer/backend/scheduler.md)** y
  **[Comprobaciones de configuración](../developer/architecture/security.md#configuration-checks)**
