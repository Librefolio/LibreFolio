# ⚙️ Configuración global

La configuración global se aplica a toda la instancia y a todos los usuarios. Vive en la base de datos.
Solo los administradores tienen la pestaña para verla y cambiarla. No es secreta: la aplicación la lee para cada usuario con sesión iniciada (el límite de subida, los valores predeterminados de las [Preferencias](../user/settings/preferences.md)…) y cualquier usuario con sesión iniciada puede leerla a través de la API.

Algunas tienen una variable en el archivo `.env` que las fija o que tiene prioridad: la columna **Dónde** de cada tabla lo indica.

---

## 🗂️ Configuración › Administración {: #administration }

**Dónde:** **Configuración** (icono de engranaje en la barra lateral) › **Administración**, en el extremo derecho de la barra de pestañas en una pantalla ancha. Solo los administradores tienen el grupo.
Haz clic en **Administración**: se abre **Configuración Global** y una segunda fila de pestañas debajo de la primera.

| Pestaña | Para qué sirve |
|---|---|
| ⚙️ **Configuración Global** | Los ajustes de esta página |
| 👥 **Usuarios** | Las cuentas, las invitaciones y los enlaces de restablecimiento de contraseña: [Usuarios e invitaciones](users.md) |
| 💾 **Copia de seguridad** | Toda la instancia en un solo archivo, y su restauración: [Copia de seguridad, restauración y traslado](backup_restore.md) |
| ✉️ **Correo** | Si LibreFolio puede enviar correos, y un correo de prueba: [Correo electrónico](email.md) |
| 🛡️ **Seguridad** | Cómo está configurada la instancia y qué necesita tu atención: [Seguridad](#security-tab), más abajo |

- 👤 Un usuario que no es administrador no tiene ni el grupo ni sus pestañas: su **Configuración** termina en **Acerca de**, y un enlace a una pestaña del grupo abre su **Perfil**.
- 🔁 Haz clic en **Administración** mientras una de sus pestañas está abierta: esa pestaña se queda abierta.
- 🔗 Cada pestaña tiene su propia dirección, para un marcador o un enlace: `/settings/admin/global`, `/settings/admin/users`, `/settings/admin/backup`, `/settings/admin/email`, `/settings/admin/security`; `/settings/admin` abre la primera pestaña del grupo. La dirección sigue la pestaña abierta, y **Atrás** vuelve a la de antes.
- 🔢 Un número en **Seguridad**, repetido en **Administración**, cuenta los errores y las advertencias de las [comprobaciones de seguridad](#security-tab).
- 📱 En un teléfono, las pestañas muestran solo sus iconos; el título de la página nombra la pestaña abierta.

---

## ✏️ Cambiar un ajuste

### 🔓 1. Desbloquear la pestaña

**Dónde:** **Configuración › Administración › Configuración Global**. El panel agrupa los ajustes por categoría.
Haz clic en el **icono de candado** (🔒) de la cabecera.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Configuración Global" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 💾 2. Editar y guardar

- No se escribe nada hasta que haces clic en **Guardar**, junto a un ajuste, o en **Guardar Todo**, en la cabecera. **Deshacer** y **Deshacer Todo** recuperan los valores guardados.
- **Restablecer** y **Restablecer Todo** rellenan los valores predeterminados, listos para guardar.
- Los valores guardados se aplican de inmediato, sin reiniciar.

??? note "🔒 Bloquear con cambios sin guardar — cuando un diálogo pregunta primero"

    Haz clic en el candado con cambios sin guardar: pregunta si quieres descartarlos. **Cancelar** conserva tus ediciones; **Descartar** recupera los valores guardados y bloquea la pestaña.

??? tip "💻 Ajustes que faltan — volver a crearlos desde la línea de comandos"

    Cada arranque del servidor vuelve a crear los ajustes que faltan con su valor predeterminado. Para hacerlo sin reiniciar, **en el terminal del servidor**, con la [herramienta de línea de comandos](cli_tools.md):

    ```bash
    pipenv run ./dev.py user init-settings
    ```

    Los valores que cambiaste se conservan.

---

## 📋 Qué hace cada ajuste

**Dónde:** la categoría indicada de la pestaña **Configuración Global**.

| Dónde | Ajuste | Predeterminado | Qué hace — cuándo cambiarlo |
|---|---|---|---|
| ⏳ Sesión | **Duración de Sesión** | 24 horas | Cuánto tiempo permanecen los usuarios con la sesión iniciada. Redúcela en dispositivos compartidos. Un valor nuevo se aplica desde el siguiente inicio de sesión de cada usuario. |
| 🛡️ Seguridad | **Registro** | Por invitación | Quién puede crear una cuenta: **Abierto**, **Por invitación** o **Cerrado**. **Abierto** deja entrar a cualquiera que llegue a la página de inicio de sesión: evítalo si se puede acceder a la instancia desde internet. Modos, advertencia y `LIBREFOLIO_REGISTRATION`: [Quién puede registrarse](#registration). |
| 🛡️ Seguridad | **Verificación Email Requerida** | Desactivada | Las cuentas nuevas deben abrir un enlace enviado a su dirección antes de poder iniciar sesión; la primera cuenta nunca espera y las cuentas existentes no se ven afectadas. Solo se puede activar mientras el correo funciona y se puede usar `LIBREFOLIO_PUBLIC_URL`: hasta entonces el interruptor está desactivado. Consulta *Verificación de correo electrónico* en [Correo electrónico](email.md). |
| 🔄 Tarea de actualización | **Planificador Activado** | Activado | Activa o desactiva las actualizaciones automáticas de precios y tipos de cambio: [Planificador de datos de mercado](#market-data-scheduler). |
| 🧠 Memoria | **Tamaño Máx. Subida** | 10 MB | El archivo más grande que pueden subir los usuarios, informes de brókeres incluidos. Auméntalo si se rechaza una exportación grande. |
| 🧠 Memoria | **Espacio total de LibreFolio (MB)** | `0`, sin límite | Los megabytes máximos que puede ocupar la instancia: es la línea contra la que se dibuja la barra de espacio de **Archivos**. `0` significa sin límite: la barra entonces muestra el disco. El mismo campo está bajo esa barra, en **Avanzado**. `LIBREFOLIO_STORAGE_LIMIT_MB`, cuando está definida, prevalece y lo bloquea: el campo es de solo lectura y dice que lo fija quien aloja la instancia ([Variables de entorno](configuration.md)). **Abrir la configuración**, ante un rechazo del límite, abre esta pestaña con la fila resaltada; la pestaña sigue bloqueada. Consulta [La barra de espacio](backup_restore.md#space-used). |
| 🌍 Valores Predeterminados | **Divisa predeterminada** | `EUR` | La divisa en la que informan los usuarios nuevos. Antes del primer guardado, decide `LIBREFOLIO_DEFAULT_CURRENCY` (más abajo). |
| 🌍 Valores Predeterminados | **Idioma Predeterminado** | `en` | 🇬🇧 `en`, 🇮🇹 `it`, 🇫🇷 `fr` o 🇪🇸 `es`. También es el idioma de los correos enviados a personas que aún no tienen cuenta. Antes del primer guardado, decide `LIBREFOLIO_DEFAULT_LANGUAGE` (más abajo). |
| 🌍 Valores Predeterminados | **Tema Predeterminado** | `auto` | ☀️ `light`, 🌙 `dark` o 🖥️ `auto`, que sigue al dispositivo. |

**En el archivo `.env`**, dos variables deciden, si están definidas, solo hasta que guardas el ajuste por primera vez: desde el primer guardado prevalece tu valor, incluso cuando vuelve a ser el predeterminado (`EUR`, `en`). Consulta [Variables de entorno](configuration_accounts.md#accounts).

```env
LIBREFOLIO_DEFAULT_CURRENCY=EUR
LIBREFOLIO_DEFAULT_LANGUAGE=en
```

Los usuarios nuevos parten de los tres valores predeterminados: la [Configuración de bienvenida](../user/getting-started.md#welcome-setup) muestra el idioma y la divisa ya rellenados. Cambiar un valor predeterminado más tarde no toca las [Preferencias](../user/settings/preferences.md) de los usuarios existentes.

---

## 🚪 Quién puede registrarse {: #registration }

**Dónde:** **Configuración Global › Seguridad › Registro**, o la pestaña [Usuarios](users.md#registration), junto a **Invitar**: allí el modo se guarda al instante, y solo pide confirmación para **Abierto**.

| Modo | Quién puede crear una cuenta |
|---|---|
| 🌐 **Abierto** | Cualquiera que llegue a la página de inicio de sesión, con **Regístrate aquí**. |
| ✉️ **Por invitación** (predeterminado) | Solo las personas con un enlace de invitación. Crea un enlace por persona desde la pestaña [Usuarios](users.md#invitations) o desde la [línea de comandos](cli_tools.md#invite), y envíaselo. La página de inicio de sesión no muestra **Regístrate aquí**. |
| 🔒 **Cerrado** | Nadie, ni siquiera con un enlace de invitación. La página de inicio de sesión no muestra **Regístrate aquí**. |

- 👑 La primera cuenta de una instancia nueva siempre se puede crear, sea cual sea el modo: consulta la advertencia de más abajo.
- 🆕 Una instancia nueva empieza en **Por invitación**. Una instancia actualizada desde una versión anterior conserva el modo que tenía: una que estaba **Abierto**, el valor predeterminado anterior, sigue **Abierto** hasta que lo cambies (**Restablecer** propone **Por invitación**). Cuando todos tengan una cuenta, elige **Por invitación** o **Cerrado**.
- ✉️ Un enlace de invitación funciona una vez, durante 7 días, y puede hacer que la cuenta nueva sea administradora. Con **Abierto**, nadie necesita uno, pero un enlace sigue dando su rol.
- 💻 Sea cual sea el modo, la [línea de comandos](cli_tools.md) puede crear cuentas con `user create`.
- 📏 Con un límite de usuarios, nadie puede registrarse sin una invitación cuando la instancia está llena: [Cuando la instancia está llena](configuration_accounts.md#user-limit).
- 🔒 **En el archivo `.env`**, `LIBREFOLIO_REGISTRATION` fija el modo: el campo lo muestra en ambos sitios, no se puede cambiar y dice *Lo define `LIBREFOLIO_REGISTRATION` en el servidor: cámbialo allí.* **Restablecer Todo** no lo toca. Consulta [Cuentas y registros](configuration_accounts.md#accounts).
- ⬆️ Este ajuste reemplaza el interruptor **Habilitar registro** de versiones anteriores; la actualización conserva tu elección: un interruptor activado pasa a **Abierto**, uno desactivado a **Cerrado**.

!!! warning "🆕 Una instancia nueva: crea primero tu cuenta"

    Hasta que exista la primera cuenta, cualquiera que llegue a la página de inicio de sesión puede crearla con **Regístrate aquí**, sea cual sea el modo, `LIBREFOLIO_REGISTRATION` incluido, y esa cuenta se convierte en la administradora. Regístrate en cuanto el servidor esté en marcha, antes de hacerlo accesible desde internet. A partir de la segunda cuenta se aplica el modo: con **Por invitación**, el predeterminado, la página de inicio de sesión ya no muestra **Regístrate aquí**.

    O crea el primer administrador **en el terminal del servidor**, sin navegador ([línea de comandos](cli_tools.md)):

    ```bash
    pipenv run ./dev.py user create <username> <email> <password>
    ```

    Con Docker: `docker compose exec librefolio python dev.py user create <username> <email> <password>`.

    O define `LIBREFOLIO_ADMIN_EMAIL` **en el archivo `.env`** antes del primer arranque: LibreFolio crea el administrador por sí mismo, con un enlace de configuración para ti, y nadie puede registrarse en su lugar ([El administrador inicial](configuration_accounts.md#initial-admin)).

### 📢 La advertencia de registro abierto {: #open-registration-warning }

Mientras **Registro** está **Abierto**, un administrador que abre LibreFolio en una dirección fuera de la red local lee, sobre las páginas de la aplicación:

*El registro está abierto y esta instancia es accesible desde fuera de tu red local: cualquiera que la encuentre puede crear una cuenta.*

Su enlace, **Cambiar quién puede registrarse**, abre **Configuración › Administración › Configuración Global**. Cuando `LIBREFOLIO_REGISTRATION` fija el modo, la advertencia nombra esa variable en su lugar y no tiene enlace: solo la configuración del servidor (archivo `.env`) puede cambiarlo ([Cuentas y registros](configuration_accounts.md#accounts)).

- 👑 Solo los administradores la ven.
- 🌐 Lo decide tu navegador, a partir del nombre o de la dirección IP de la barra de direcciones (el puerto no importa). No se envía nada al servidor y nada comprueba si la instancia es realmente accesible desde internet. Estas direcciones cuentan como locales, sin advertencia:
    - `localhost` y todos los nombres que terminan en `.localhost`;
    - un nombre sin punto, como `nas`, y todos los nombres que terminan en `.local`, `.lan`, `.home.arpa` o `.internal`;
    - las direcciones IPv4 de `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` y `100.64.0.0/10` (NAT de nivel de operador, el rango donde Tailscale numera sus dispositivos);
    - la dirección IPv6 `::1` y las de `fc00::/7` y `fe80::/10`; una dirección IPv4 escrita como IPv6, como `::ffff:192.168.1.10`, cuenta como la dirección IPv4 que contiene.

    Las mayúsculas y un punto final no cambian nada. Cualquier otra dirección cuenta como exterior, incluidos los nombres de Tailscale que terminan en `.ts.net`: Tailscale Funnel puede publicarlos en internet.
- ✖️ El botón de cierre la oculta hasta que la página se vuelve a cargar.
- 🔄 Desaparece en cuanto el modo deja de ser **Abierto**: guardar **Registro** la actualiza al instante.
- 🛡️ La pestaña [Seguridad](#security-tab) enumera la misma advertencia entre sus hallazgos mientras se cumpla, incluso después de que la hayas cerrado.

Cómo lo decide, para desarrolladores: [La advertencia de registro abierto](../developer/architecture/security.md#open-registration-warning).

---

## 🕐 Planificador de datos de mercado {: #market-data-scheduler }

El planificador actualiza precios y tipos de cambio por sí solo, incluso cuando nadie tiene la sesión iniciada:

- 💰 **Actualización del precio actual** — cada pocos minutos, el último precio de cada activo activo con un proveedor de precios.
- 📊 **Sincronización del historial** — en los días y a las horas que elijas, los precios diarios de esos activos y los tipos de cada par FX con un proveedor, durante al menos el **Horizonte de recuperación**, para rellenar los huecos. Si el último precio o tipo guardado es más antiguo, retrocede hasta ese día, hasta un año como máximo; un activo sin ningún precio guardado recibe solo el horizonte: el planificador nunca descarga un historial completo. Los pares con tipos manuales únicamente se omiten.

Servidor apagado o suspendido a la hora de la sincronización: la sincronización perdida se ejecuta en cuanto el servidor vuelve, sin esperar a la siguiente hora. Un servidor apagado durante semanas rellena todo su hueco.

### ⚙️ Configurar el horario

**Dónde:** **Configuración Global › Tarea de actualización › Configuración del Horario › Configurar…**, con la pestaña desbloqueada. El diálogo tiene su propio botón **Guardar**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Diálogo de configuración del planificador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

| Campo | Predeterminado | Qué fija |
|---|---|---|
| **Zona horaria** | `UTC` | La zona horaria de las horas y los días de abajo; a su lado, el reloj UTC del servidor. Antes del primer guardado del horario, decide `LIBREFOLIO_DEFAULT_TIMEZONE` **en el archivo `.env`**, si está definida; desde el primer guardado prevalece tu valor, incluso cuando vuelve a ser `UTC` ([Variables de entorno](configuration_accounts.md#accounts)). |
| **Actualizar cada** | 10 minutos | Cada cuánto se actualizan los precios actuales, de 1 a 1440 minutos. |
| **Horarios de sincronización** | `06:00`, `23:00` | Cuándo se ejecuta la sincronización del historial; **Agregar horario** añade una franja. |
| **Días de sincronización** | De lun a sáb | Los días de la sincronización del historial. |
| **Horizonte de recuperación** | 14 días | Cuántos días pasados comprueba cada sincronización como mínimo, de 1 a 365. Retrocede más, hasta un año, cuando el último precio o tipo guardado es más antiguo. |

Conserva al menos una hora y un día. Una sincronización después del cierre de los mercados (por ejemplo `22:00`) obtiene los datos más completos.

??? warning "🌍 Cambiar la zona horaria — las tareas se mueven en el tiempo"

    Las horas y los días conservan sus valores, pero se cuentan en la nueva zona horaria: las tareas se ejecutan en otro momento. También siguen el horario de verano de la zona horaria: las `06:00` de `Europe/Rome` se ejecutan a las 05:00 UTC en invierno y a las 04:00 UTC en verano.

### 📜 Leer el registro del planificador

**Dónde:** **Configuración Global › Tarea de actualización › Estado del Planificador**. Solo los administradores leen el estado y el registro.

La fila muestra la última actualización del precio actual, con un punto para su resultado. Mientras hay un reintento pendiente, una línea extra da su hora: **Fallido: nuevo intento a las …** después de una actualización que no pudo terminar; en otro caso, **Elementos en pausa reintentados a las …** para los precios aplazados porque su proveedor estaba en pausa.
Haz clic en la fila (o en **Detalles…**): se abre el **Registro de Ejecución del Planificador**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Diálogo del registro del planificador" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

- Cada entrada es una ejecución: tarea, hora, duración y cuántos elementos tuvieron éxito. 🟢 **OK**: todos, o nada que hacer; 🟡 **Parcial**: algunos fallaron, o se aplazaron porque su proveedor se puso en pausa tras demasiadas peticiones; 🔴 **Error**: ninguno tuvo éxito y ninguno se aplazó.
- Haz clic en una entrada: cada activo o par FX, su proveedor y los precios cambiados (**Delta**). Pasa el ratón sobre un error para leerlo completo; haz doble clic (pulsación larga en un teléfono) para copiarlo.
- Un elemento aplazado muestra un icono de pausa y **Aplazado: proveedor en pausa**: pasa el ratón sobre la etiqueta para leer el mensaje del proveedor. La entrada cuenta los elementos aplazados con ⏸, junto a ✓ y ✗ (por ejemplo `3/5 ✓ · 1 ⏸ · 1 ✗`), y **Reintento a las …** en la cabecera da la hora del reintento.
- Filtra por tarea, estado o periodo, desde la última hora hasta los últimos 30 días. Solo se conservan las ejecuciones más recientes.

---

## ⏸️ Pausas de proveedor {: #provider-pauses }

Cuando un proveedor de precios o de tipos de cambio (Yahoo Finance, el Banco Central Europeo…) responde «demasiadas peticiones» (HTTP 429), LibreFolio lo pone en pausa: hasta que la pausa termina, ninguna petición le llega, ni del [planificador de datos de mercado](settings.md#market-data-scheduler) ni de un usuario. Una pausa vale para todos los usuarios y todas las tareas del servidor.

Las pausas están activadas por defecto. `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=0` las desactiva, como antes de la versión 1.3.

**Dónde:** **en el archivo `.env`** (o en el entorno del contenedor). Estos son los valores predeterminados:

```env
LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS=60
LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS=3600
```

| Variable | Predeterminado | Qué hace |
| --- | --- | --- |
| `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS` | `60` | La primera pausa, en segundos, que se duplica en cada rechazo seguido: un número entero de `0` a `86400` (un día). `0` desactiva las pausas. |
| `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS` | `3600` | La pausa más larga que alcanza la duplicación, en segundos: un número entero de `1` a `86400`, no inferior a la primera pausa mientras las pausas estén activadas. Un `Retry-After` del proveedor aún puede pedir más, hasta un día. |

Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`.

- Un valor que LibreFolio no puede usar no detiene el servidor: el registro tiene un error ([En el registro](#provider-pauses-log)) y se aplican los dos valores predeterminados, 60 y 3600: las pausas siguen activadas.
- Con las pausas desactivadas, cada petición vuelve a llegar al proveedor; el planificador sigue contando una petición rechazada como aplazada ([más abajo](#provider-pauses-effects)).

### ⏱️ Cuánto dura una pausa {: #provider-pauses-length }

- **El primer rechazo** pone al proveedor en pausa durante `LIBREFOLIO_PROVIDER_COOLDOWN_BASE_SECONDS`, 60 segundos por defecto.
- **Cada rechazo seguido** duplica la pausa, hasta `LIBREFOLIO_PROVIDER_COOLDOWN_MAX_SECONDS`. Con los valores predeterminados: 2 minutos, luego 4, 8, 16 y 32, y después una hora en cada rechazo siguiente. Las peticiones rechazadas a la vez cuentan como un solo rechazo.
- **Un `Retry-After`**, cuando el proveedor envía uno, es la pausa más corta que toma LibreFolio: se respeta incluso por encima de la pausa más larga, hasta un día.
- **Un extra aleatorio** de hasta el 10 % se suma a cada pausa, sin pasar nunca de un día.
- **Cuando una pausa termina**, pasa una petición para probar el proveedor; las demás siguen contando como en pausa hasta que tenga un resultado, un minuto como máximo. Una respuesta cierra la serie: el siguiente rechazo vuelve a empezar desde la primera pausa. Lo mismo vale para un rechazo que llega, desde el final de la pausa anterior, tras un intervalo más largo que la pausa más larga.
- **Una pausa vale para todo el proveedor**, salvo con el CSS Scraper: un sitio que rechaza pausa solo las páginas de ese sitio; los demás sitios se siguen leyendo.

### 👀 Quién espera y qué ves {: #provider-pauses-effects }

| Dónde | Durante una pausa |
| --- | --- |
| 🕐 [Planificador de datos de mercado](settings.md#market-data-scheduler) | Los activos y los pares FX de un proveedor en pausa quedan **aplazados**: ni actualizados ni fallidos, y su tarea es **Parcial**. La tarea se ejecuta de nuevo cuando termina la primera de esas pausas, o a su hora habitual si esta llega antes. Cómo lo muestran **Estado del Planificador** y el **Registro de Ejecución del Planificador**: «Leer el registro del planificador», arriba. |
| 💰 Precios en vivo, en la lista de Activos y en la página de un activo | Se queda el último precio guardado, sin ningún mensaje nuevo. Cuando todos los activos por los que pregunta la página tienen su proveedor en pausa, la página vuelve a preguntar por sí sola solo cuando termina la primera de esas pausas; mientras un proveedor siga respondiendo, la actualización continúa y LibreFolio no llama a los que están en pausa. Tras una actualización que falla, la siguiente espera el doble, y así hasta diez minutos, hasta que una funcione de nuevo. |
| 🔌 **Probar Configuración**, en el diálogo del activo | ⚠️ *Pausa por exceso de peticiones hasta las …*, con la hora en que termina la pausa; la prueba aun así se supera. Consulta [Conectar un proveedor de precios](../user/assets/create-edit.md). |
| 🔎 Búsqueda de activos | Un proveedor en pausa no devuelve resultados hasta que su pausa termina; los demás responden como de costumbre. |
| 💱 Tipos de cambio | Un proveedor en pausa cuenta como una ruta que falló: un par con otra ruta obtiene su tipo allí, como cuando un banco central no responde ([Configuración de Proveedores](../user/fx/detail/provider.md)). En otro caso, el planificador aplaza el par, como hace con un activo. |

### 💤 En memoria {: #provider-pauses-memory }

- **Cada proceso del servidor guarda sus propias pausas en memoria.** Un reinicio las olvida, un despliegue incluido. Con varios procesos del servidor (`--workers N`), cada uno aprende una pausa a partir de un rechazo propio; la imagen de Docker ejecuta uno.

### 📋 En el registro {: #provider-pauses-log }

| Nivel | El registro dice | Cuándo |
| --- | --- | --- |
| ⚠️ `warning` | `Provider refused for too many requests: paused`, con `domain` (`asset` o `fx`), `provider`, `scope` (el sitio, con el CSS Scraper), `wait_s`, los segundos de pausa que quedan, y `retry_after`, la espera que pidió el proveedor, si la hubo | Un proveedor rechazó una petición |
| ℹ️ `info` | `Provider answering again after a pause`, con `refusals`, los rechazos seguidos antes de ella | La primera respuesta tras una pausa |
| ❌ `error` | `Provider pause settings cannot be used: the defaults apply`, con `variable`, `code` (`PROVIDER_COOLDOWN_BASE_INVALID` o `PROVIDER_COOLDOWN_MAX_INVALID`) y `reason` | Una de las dos variables tiene un valor que no se puede usar: una vez por proceso del servidor, la primera vez que LibreFolio está a punto de llamar a un proveedor |

En nivel `DEBUG`, `Provider call skipped: paused after too many requests`, con `wait_s`, marca cada petición que una pausa impidió enviar. Las líneas del planificador, `Scheduler: current-price refresh` y `Scheduler: history sync`, dan los elementos aplazados en `deferred`, con `retry_at`.

---

## 🗄️ Cachés del servidor {: #server-caches }

LibreFolio guarda en memoria las respuestas recientes de los proveedores y los resultados calculados.

**Dónde:** **Configuración Global › Memoria › Estado de la caché**, al final de la categoría. El panel lista cada caché con **Tam. / Máx** y **TTL** (cuánto tiempo se conserva una entrada). Haz clic en la cabecera de una columna para ordenar; **Actualizar** refresca los números.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="cache-panel" alt="Panel de cachés del servidor en Configuración Global (categoría Memoria)">
</div>

El panel muestra sus números incluso con la pestaña bloqueada. Con la pestaña desbloqueada, **Vaciar** vacía una caché y **Vaciar todo** todas, para forzar datos nuevos sin reiniciar. Un reinicio también vacía todas las cachés.

!!! warning "Vaciar una caché ralentiza la siguiente recuperación"

    Ambas acciones piden confirmación antes. Tras vaciar, la siguiente petición de esos datos vuelve a los proveedores: espera una ralentización parecida a la de un reinicio del servidor hasta que las cachés se vuelvan a llenar.

??? note "🧵 Varios workers — cuando el servidor se ejecuta con `--workers`"

    Cada proceso worker tiene sus propias cachés. El panel muestra y vacía las del worker que respondió; reinicia el servidor para vaciarlas todas.

---

## 🛡️ Seguridad {: #security-tab }

**Dónde:** **Configuración › Administración › Seguridad**. Solo los administradores tienen la pestaña. Comprueba cómo está configurada la instancia y lista primero lo que necesita tu atención.
No es la categoría 🛡️ **Seguridad** de Configuración Global, que contiene **Registro** y **Verificación Email Requerida**.

### 🚦 Qué lista {: #security-findings }

Cada hallazgo dice qué va mal, con un icono y un color: ❌ un **error**, ⚠️ una **advertencia** o ℹ️ una **información**. Primero los errores, luego las advertencias, luego la información; a igual gravedad, el orden de esta tabla.

| Comprobación | Hay un hallazgo cuando | Su enlace |
|---|---|---|
| Clave de firma de sesión | ℹ️ La clave es aleatoria: cada reinicio cierra la sesión de todos; define `JWT_SECRET` para seguir con la sesión iniciada. ⚠️ La clave tiene menos de 32 caracteres. ❌ Su `JWT_SECRET_FILE` no se puede leer | — |
| Secretos definidos dos veces | ⚠️ Un secreto está definido a la vez directamente y mediante su variable `_FILE`: gana el valor directo | — |
| Clave de la instancia | ❌ No se puede usar. ⚠️ Su carpeta o su archivo está abierto a otros usuarios | — |
| Cookie de sesión | ⚠️ `SESSION_COOKIE_SECURE=never`: la cookie también viaja por HTTP sin cifrar | — |
| Dirección del visitante | ⚠️ Desde el arranque, llegaron peticiones a través de un proxy inverso en el que LibreFolio no confía: los límites por dirección del visitante no se les aplican. ℹ️ Desde el arranque, se ignoraron cabeceras de reenvío procedentes de una dirección pública. Qué hacer: [La dirección del visitante](connection_proxy.md#client-address) | — |
| Nivel del registro | ℹ️ `DEBUG` o `TRACE` | — |
| Modo de prueba | ❌ `LIBREFOLIO_TEST_MODE` está activado fuera de las ejecuciones de prueba de LibreFolio: se sirven proveedores de datos que existen solo para las pruebas y los datos se guardan en la carpeta de datos de prueba | — |
| Límite de subida de una restauración | ❌ `LIBREFOLIO_BACKUP_MAX_UPLOAD_MB` no se puede usar (un número entero de megabytes, `0` para sin límite): se rechazan las subidas de restauración hasta que se corrija. Superada con un límite, como *Una restauración acepta archivos de hasta 500 MB.*, o sin ninguno | — |
| Tamaño descomprimido de una restauración | ❌ `LIBREFOLIO_BACKUP_MAX_RESTORE_MB` no se puede usar (un número entero de megabytes, `0` para sin límite): se rechazan las verificaciones de restauración hasta que se corrija. Superada con un límite, como *Una verificación para una restauración acepta archivos que, descomprimidos, ocupan hasta 4000 MB.*, o sin ninguno | — |
| Inicios de sesión fallidos | ⚠️ El límite está desactivado: `LIBREFOLIO_LOGIN_LIMIT=off` | — |
| Servidor de correo | ❌ Un valor `LIBREFOLIO_SMTP_*` no se puede usar: el correo sigue desactivado hasta que se corrija | **Abrir la pestaña Correo** |
| Cifrado del correo | ⚠️ Los correos, sus enlaces y la contraseña SMTP viajan sin cifrar a un servidor fuera de tu red local | **Abrir la pestaña Correo** |
| Enlaces en los correos | ℹ️ El correo funciona, pero `LIBREFOLIO_PUBLIC_URL` no está definida. ⚠️ `LIBREFOLIO_PUBLIC_URL` no se puede usar al principio de un enlace | **Abrir la pestaña Correo** |
| Secretos de plugins | ❌ Los secretos de plugins de toda la instancia no se pueden leer con la clave de la instancia | **Abrir los ajustes de los plugins**, en **Configuración › Plugins** |
| Registro abierto, comprobado por tu navegador | ⚠️ **Registro** está **Abierto** y llegaste a LibreFolio en una dirección fuera de tu red local, como en [la advertencia sobre las páginas](#open-registration-warning) | **Cambiar quién puede registrarse**, en **Configuración Global**. Ninguno cuando `LIBREFOLIO_REGISTRATION` fija el modo: el hallazgo nombra esa variable en su lugar |
| Un script bloqueado, comprobado por tu navegador | ⚠️ Un script que LibreFolio no envió, añadido por un proxy, una CDN o una extensión del navegador, se bloqueó en esta pestaña del navegador: el hallazgo nombra sus orígenes. Desaparece al cerrar la pestaña. No se corrige en el servidor, sino en el proxy, la CDN o la extensión: [Un script que no enviaste](configuration_security.md#csp-blocked-script) | — |

Cada fila tiene un botón de ayuda, elegido según quién puede resolver la comprobación:

- 📖 **Guía**: puedes resolverla tú solo, en el servidor. El botón, que se muestra también en las comprobaciones superadas, abre la página de esta guía que explica esa comprobación, en una pestaña nueva y en tu idioma cuando está traducida.

Una comprobación sin página propia y sin soporte no tiene botón.

Los hallazgos sin enlace se corrigen en la configuración del servidor (**archivo `.env`**) y necesitan un reinicio: qué hacer con cada uno está en la tabla de «Comprobaciones al arrancar» de [Configuración](configuration.md), donde el registro del servidor informa de las mismas comprobaciones.

### 🔢 El número en la pestaña {: #security-badge }

**Seguridad** muestra cuántos errores y advertencias lista; **Administración** muestra el mismo número, visible desde todas las pestañas de Configuración. La información se lista pero nunca se cuenta: con solo información no hay número, y la pestaña tampoco dice *Nada requiere tu atención.*

Fuera de Configuración, la misma cuenta te sigue en todas las páginas, como un punto en la línea de conexión al pie de la barra lateral: rojo con al menos un error, ámbar con solo advertencias, ninguno con solo información. Haz clic en la línea: tras su motivo, los detalles enlazan con esta pestaña con la cuenta, por ejemplo **2 avisos de seguridad**, errores incluidos. En un teléfono, el botón del menú lleva también el punto. Cómo se ve: [Advertencias de seguridad para administradores](../user/connection-security.md#security-warnings).

### 🔄 Cuándo comprueba {: #security-refresh }

LibreFolio lee las comprobaciones una vez, en cuanto se abre en tu navegador, sea cual sea la página: la línea de conexión de la barra lateral las pide, así que el punto y el número de la pestaña ya están ahí cuando abres **Configuración**. Si esa lectura falla, abrir **Configuración** lo intenta de nuevo. Las comprobaciones se mantienen mientras usas la aplicación: tras cambiar la configuración del servidor (archivo `.env`) y reiniciar, haz clic en **Comprobar de nuevo**, arriba en la pestaña, o recarga la página. El hallazgo de registro abierto sigue a **Registro** al instante: guardarlo en Configuración Global actualiza la lista, el número y el punto.

- ⏳ Hasta la primera respuesta, la pestaña muestra filas de relleno.
- ⚠️ Cuando las comprobaciones no se pueden leer, la pestaña dice *No se han podido cargar las comprobaciones de seguridad.*, con **Reintentar**. Tras un **Comprobar de nuevo** que falla, los últimos resultados siguen listados debajo.

### ✅ Comprobaciones superadas {: #security-passed }

Sin ningún hallazgo, la pestaña dice *Nada requiere tu atención.* Debajo de los hallazgos, una sección plegada, **N comprobaciones superadas**, lista las comprobaciones superadas, cada una con su propia frase (por ejemplo *Las sesiones se firman con una clave definida por el administrador.*): haz clic en ella para desplegarla. El correo desactivado, o enviado sin cifrar a un servidor de tu propia red, cuenta como superado y lo dice ahí.

---

## 🔗 Relacionado

- 📝 **[Variables de entorno](configuration.md)** — Los ajustes que viven en el archivo `.env`
- 👥 **[Usuarios e invitaciones](users.md)** — Las cuentas de la instancia, las invitaciones y los enlaces de restablecimiento de contraseña
- 👤 **[Preferencias de usuario](../user/settings/preferences.md)** — Lo que cada usuario puede cambiar por sí mismo
- 🧑‍💻 Para desarrolladores: **[Sistema de configuración](../developer/architecture/settings.md)**,
  **[Registro de cachés](../developer/architecture/settings_cache.md)**,
  **[Planificador de datos de mercado](../developer/backend/scheduler.md)** y
  **[Comprobaciones de configuración](../developer/architecture/security.md#configuration-checks)**
