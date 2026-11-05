# 📧 Correo electrónico

LibreFolio puede enviar correo electrónico a través de un servidor SMTP que indiques en unas pocas variables de entorno.
El correo electrónico es **opcional**: sin él nada cambia, no se envía nada y los enlaces de invitación y
de restablecimiento de contraseña se copian a mano.

Qué envía LibreFolio:

- **Un correo de prueba**, que un administrador envía a su propia dirección desde
  **Configuración › Administración › Correo electrónico**, para comprobar que todo funciona.
- **Los enlaces de invitación y de restablecimiento de contraseña que crea un administrador**, con **Enviar por correo electrónico** en
  sus diálogos, en lugar de copiarlos a mano: [Enlaces enviados por un administrador](email_flows.md#admin-links).
- **Un enlace de restablecimiento para una contraseña olvidada**, a quien solicite uno para su cuenta desde la
  página de inicio de sesión: [Contraseñas olvidadas](email_flows.md#forgot-password).
- **El enlace de configuración del administrador inicial**, una sola vez, cuando LibreFolio crea ese administrador
  a partir de `LIBREFOLIO_ADMIN_EMAIL` y genera el enlace por sí mismo: consulta
  [El administrador inicial](configuration_accounts.md#initial-admin).
- **Un enlace para confirmar la dirección de correo electrónico de una cuenta nueva**, cuando **Requerir verificación de correo electrónico** está
  activado: consulta [Verificación de correo electrónico](email_flows.md#verification).
- **Un aviso a la dirección anterior** cuando alguien cambia la dirección de correo electrónico de su cuenta:
  [Cambios de dirección de correo electrónico](email_flows.md#email-change-notice).

Los correos electrónicos con enlace también necesitan `LIBREFOLIO_PUBLIC_URL`: consulta [Correos con enlace](email_flows.md#public-url).

Para configurarlo:

1. Escribe las variables `LIBREFOLIO_SMTP_*` en `.env`: al menos el servidor y el remitente, y el usuario de tu cuenta cuando el servidor lo pida. Los [ejemplos](#examples) cubren los casos habituales.
2. Para los correos electrónicos con enlace, define también `LIBREFOLIO_PUBLIC_URL` ([Correos con enlace](email_flows.md#public-url)).
3. Reinicia LibreFolio.
4. Abre **Configuración › Administración › Correo electrónico**: el estado indica **Listo**. Envíate un correo de prueba.

!!! info "📚 Esta guía se divide en varias páginas"

    Esta página explica cómo configurar el correo electrónico: las variables, ejemplos para los servidores habituales, la pestaña **Correo electrónico** de Configuración y su correo de prueba. El resto de la guía:

    - [Correo electrónico: enlaces y mensajes](email_flows.md): los correos con enlace, las contraseñas olvidadas, sus límites, la verificación de correo electrónico y el aviso de cambio de dirección.
    - [Correo electrónico: cuando no funciona](email_troubleshooting.md): los errores, lo que dice el registro y las notas de seguridad de la configuración SMTP.

---

## 🔐 Dónde se encuentra la configuración {: #where-it-lives }

La configuración SMTP proviene **únicamente** de variables de entorno, y la contraseña también de un
archivo de secretos.

- **Nunca se almacena.** LibreFolio no la escribe en ningún sitio: no está en la base de datos, y una copia de seguridad de
  los datos de LibreFolio no la contiene. Conserva tu propia copia de `.env` y del archivo de contraseña.
- **Nunca se muestra.** Ninguna página de la interfaz muestra el servidor, el puerto, el usuario, el remitente ni la
  contraseña: [Configuración › Administración › Correo electrónico](#email-tab) indica si el correo electrónico funciona y, cuando
  no lo hace, qué variable hay que corregir; de los valores `LIBREFOLIO_SMTP_*`, solo muestra el límite por hora.
- **Público: solo si el correo electrónico está listo.** `/api/v1/system/instance`, que cualquiera que pueda acceder al
  servidor puede leer, indica si esta instancia puede enviar correo electrónico: `"available": true` cuando el estado es
  **Listo**, y `"links": true` cuando, además,
  los correos pueden llevar un enlace ([Correos con enlace](email_flows.md#public-url)). No hay nada más sobre el correo electrónico.
- **Se lee del entorno.** `./dev.py` y Docker Compose (`env_file: .env`) ponen allí los valores de
  `.env`, así que estas variables van en `.env` como las demás [opciones](configuration.md).
- **Reinicia después de un cambio.** Con Docker Compose, ejecuta `docker compose up -d`:
  `docker compose restart` conserva los valores antiguos.

Para desactivar el correo electrónico, elimina `LIBREFOLIO_SMTP_HOST` o déjala vacía y, después, reinicia. Las demás
variables pueden quedarse: sin un servidor, LibreFolio las ignora.

---

## 📋 Las variables {: #variables }

La sección «Email» de `.env.example` las enumera, comentadas: copia en tu `.env` las líneas que necesites.

| Variable | Valor predeterminado | Valores aceptados |
| --- | --- | --- |
| `LIBREFOLIO_SMTP_HOST` | _sin definir_: correo electrónico desactivado | El servidor SMTP: un nombre de host, como `smtp.example.com`, o una dirección IP, y nada más: ni `smtp://`, ni `user@`, ni `:587`, ni una ruta. Una dirección IPv6 se escribe sin corchetes, como `fd00::25`. |
| `LIBREFOLIO_SMTP_TLS` | `starttls` | `starttls`, `tls` o `none`, en mayúsculas o no: consulta [Modos de cifrado](#encryption-modes). |
| `LIBREFOLIO_SMTP_PORT` | `587` con `starttls`, `465` con `tls`, `25` con `none` | Un número entero de 1 a 65535. Defínelo solo cuando tu servidor use un puerto distinto del de su modo. |
| `LIBREFOLIO_SMTP_USER` | _sin definir_: sin inicio de sesión | El usuario de tu cuenta en el servidor SMTP. |
| `LIBREFOLIO_SMTP_PASSWORD` | _sin definir_ | La contraseña de ese usuario, usada exactamente tal como se escribe, incluidos los espacios. O `LIBREFOLIO_SMTP_PASSWORD_FILE`: la ruta de un archivo que la contiene. |
| `LIBREFOLIO_SMTP_FROM` | _obligatorio_ con un servidor | El remitente: una dirección, con un nombre o sin él, como `LibreFolio <noreply@example.com>` o `noreply@example.com`. |
| `LIBREFOLIO_SMTP_REPLY_TO` | _sin definir_: las respuestas van al remitente | Una dirección a la que van las respuestas. |
| `LIBREFOLIO_SMTP_MAX_PER_HOUR` | `50` | Cuántos correos electrónicos puede enviar LibreFolio en una hora, por proceso del servidor: un número entero, como mínimo 1. |
| `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS` | `20` | Cuántos correos de registro puede desencadenar una dirección de cliente en una hora, por proceso del servidor: un número entero, como mínimo 1. Superado ese límite, las siguientes cuentas nuevas se crean y esperan, pero sus correos quedan retenidos: consulta [Límites de los correos de verificación](email_flows.md#verification-limits). No es una variable SMTP, por lo que su nombre no empieza por `LIBREFOLIO_SMTP_`; se comprueba junto con ellas y solo se lee mientras hay un servidor definido. |

- **Vacío es lo mismo que sin definir**: un valor vacío, o que solo contiene espacios, cuenta como no definido.
- **El usuario y la contraseña van juntos**: define `LIBREFOLIO_SMTP_USER` junto con una contraseña, o ninguno de
  los dos para un servidor que acepta correo sin inicio de sesión.
- **La contraseña en un archivo**: `LIBREFOLIO_SMTP_PASSWORD_FILE` sigue las reglas de
  [Secretos en archivos](configuration_secrets.md#secret-files). La contraseña es el texto del archivo tal cual,
  sean cuales sean los caracteres que contenga, sin los saltos de línea del final. Define una de las dos: cuando ambas
  están definidas, gana `LIBREFOLIO_SMTP_PASSWORD`, el archivo se ignora y el registro de inicio muestra una advertencia.
  A diferencia de `JWT_SECRET_FILE`, un archivo de contraseña que no se puede leer nunca detiene el servidor: el correo electrónico permanece
  desactivado hasta que se corrija.
- **Los límites por hora se cuentan por proceso del servidor**, durante los últimos 60 minutos, en memoria:
  tanto `LIBREFOLIO_SMTP_MAX_PER_HOUR` como `LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS`. Un reinicio
  vuelve a empezar el recuento desde cero. `./dev.py server --workers 4` ejecuta cuatro procesos, cada uno con su
  propio recuento, así que la instancia puede enviar hasta cuatro veces el límite
  ([Iniciar el servidor](cli_tools.md#start-the-server)). La imagen de Docker ejecuta un único proceso.

### 🔑 Modos de cifrado {: #encryption-modes }

| `LIBREFOLIO_SMTP_TLS` | Qué hace | Puerto habitual |
| --- | --- | --- |
| `starttls` (predeterminado) | Se conecta y luego cambia a cifrado antes de enviar nada. Se rechaza un servidor que no lo ofrezca: nada sale en claro. | 587 |
| `tls` | Cifrado desde el primer byte, también llamado SSL/TLS o SMTPS. | 465 |
| `none` | Sin cifrado: los mensajes, sus enlaces y la contraseña viajan en claro. Solo para un relé en la misma máquina o en tu red local. | 25 |

- Con `starttls` y `tls`, LibreFolio comprueba el certificado del servidor: debe ser válido y
  estar emitido para el nombre de `LIBREFOLIO_SMTP_HOST`. Escribe el nombre para el que se emitió el certificado,
  normalmente no la dirección IP del servidor.
- El puerto sigue al modo, no al contrario: `LIBREFOLIO_SMTP_PORT=465` por sí solo mantiene
  `starttls`, que un servidor en el puerto 465 no espera. Para el puerto 465, define
  `LIBREFOLIO_SMTP_TLS=tls`.

---

## 💡 Ejemplos {: #examples }

Sustituye `smtp.example.com`, las direcciones y la contraseña por los tuyos y, después, reinicia LibreFolio.

=== "Docker Compose + archivo de secretos"

    La contraseña queda fuera de `.env` y fuera del entorno del contenedor, en un secreto de Docker.

    1. Guarda la contraseña en un archivo junto a `docker-compose.yml`, como `smtp_password.txt`. Un salto
       de línea al final no cuenta; los espacios sí.
    2. El contenedor ve el archivo con el propietario y los permisos que tiene en el host, así que haz que el usuario
       que ejecuta LibreFolio en el contenedor pueda leerlo, `1000:1000` con la imagen oficial:

        ```bash
        sudo chown 1000:1000 smtp_password.txt
        sudo chmod 600 smtp_password.txt
        ```

        Una imagen que hayas creado tú mismo puede usar otros id: pon esos en el comando `chown` en su lugar
        (consulta [Docker avanzado](docker_advanced.md)).

    3. Añade las líneas marcadas a `docker-compose.yml` y deja el resto del servicio tal como está. Si
       el archivo ya tiene listas `secrets:`, como el ejemplo de `JWT_SECRET_FILE` de
       [Secretos](configuration_secrets.md#secrets), añade las nuevas líneas a ellas:

        ```yaml
        services:
          librefolio:
            secrets:                         # added
              - smtp_password                # added
        secrets:                             # added
          smtp_password:                     # added
            file: ./smtp_password.txt        # added
        ```

    4. Añade las variables a `.env`. Si da un valor a `LIBREFOLIO_SMTP_PASSWORD`, elimina esa
       línea: ganaría al archivo.

        ```env
        LIBREFOLIO_SMTP_HOST=smtp.example.com
        LIBREFOLIO_SMTP_USER=noreply@example.com
        LIBREFOLIO_SMTP_PASSWORD_FILE=/run/secrets/smtp_password
        LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
        ```

        Sin `LIBREFOLIO_SMTP_TLS` y sin puerto: `starttls` en el puerto 587 es lo predeterminado.

    5. Ejecuta `docker compose up -d`.

=== "Proveedor de correo"

    Tu propia cuenta en el servidor SMTP de un proveedor de correo:

    ```env
    LIBREFOLIO_SMTP_HOST=smtp.example.com
    LIBREFOLIO_SMTP_USER=you@example.com
    LIBREFOLIO_SMTP_PASSWORD=your-app-password
    LIBREFOLIO_SMTP_FROM=LibreFolio <you@example.com>
    ```

    - Eso es `starttls` en el puerto 587, los valores predeterminados. Si tu proveedor indica el puerto 465 en su lugar, añade
      `LIBREFOLIO_SMTP_TLS=tls`: el puerto se ajusta en consecuencia.
    - Usa una **contraseña de aplicación**, no la contraseña con la que inicias sesión: una contraseña aparte que tu
      proveedor crea para una aplicación y que puedes revocar sin tocar tu cuenta.
    - Las páginas de ayuda de tu proveedor indican el nombre del servidor, el puerto y el cifrado, y dicen qué
      direcciones de remitente puede usar tu cuenta.
    - Mejor aún, guarda la contraseña en un archivo, como en la pestaña de Docker Compose.

=== "Gmail"

    Tu cuenta de Gmail, o una de Google Workspace, a través del servidor SMTP de Gmail. LibreFolio inicia sesión
    solo con un usuario y una contraseña, no con «Iniciar sesión con Google», así que Gmail necesita una
    **contraseña de aplicación**, no la contraseña de tu Cuenta de Google.

    1. Activa la **Verificación en dos pasos** para tu Cuenta de Google, si aún no está activada: las contraseñas de aplicación
       solo existen con ella.
    2. Abre [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) y
       crea una contraseña de aplicación, con un nombre como `LibreFolio`. Google la muestra como un código de 16
       caracteres, en cuatro grupos de cuatro: cópiala. Si esa página no ofrece ninguna forma de crear una,
       [la página de ayuda de Google](https://support.google.com/accounts/answer/185833) explica por qué. Una cuenta de trabajo o
       del centro educativo puede necesitar a su administrador.
    3. Añade las variables a `.env`:

        ```env
        LIBREFOLIO_SMTP_HOST=smtp.gmail.com
        LIBREFOLIO_SMTP_USER=you@gmail.com
        LIBREFOLIO_SMTP_PASSWORD=abcdefghijklmnop
        LIBREFOLIO_SMTP_FROM=LibreFolio <you@gmail.com>
        ```

        - `you@gmail.com` representa tu dirección completa de Gmail, o tu dirección completa de trabajo con
          Google Workspace.
        - `abcdefghijklmnop` representa tu contraseña de aplicación: sus 16 caracteres, escritos
          **sin los espacios**, ya que LibreFolio usa la contraseña exactamente tal como se escribe, incluidos los espacios.
          Mejor aún, guárdala en un archivo de contraseña, como en la pestaña de Docker Compose, también
          sin los espacios.
        - El remitente es la misma dirección, con un nombre delante o sin él. Gmail solo envía como tu
          propia dirección, o como una que hayas añadido y confirmado en **Enviar correo como** en la configuración de Gmail.
        - Sin `LIBREFOLIO_SMTP_TLS` y sin puerto: `starttls` en el puerto 587 es lo predeterminado, y una de
          las dos formas que ofrece Gmail. Para la otra, el puerto 465, añade `LIBREFOLIO_SMTP_TLS=tls`: el
          puerto se ajusta en consecuencia.

    4. Reinicia LibreFolio. Con Docker Compose, ejecuta `docker compose up -d`:
       `docker compose restart` conserva los valores antiguos.
    5. Abre **Configuración › Administración › Correo electrónico**, donde el estado indica **Listo**, y haz clic en
       **Enviar un correo de prueba**. Se envía a la dirección de tu cuenta: consulta
       [El correo de prueba](#test-email).

    Para que siga funcionando:

    - Una cuenta personal de Gmail puede enviar unos 500 correos al día: superado ese límite, Gmail se niega a enviar
      durante un período de 1 a 24 horas. Una cuenta de Google Workspace tiene 2.000 al día a través de `smtp.gmail.com`. Estos
      son los [límites de Google](https://support.google.com/mail/answer/22839), y Google puede cambiarlos.
      Cuando Gmail se niega, el correo de prueba y el registro informan del rechazo
      ([Errores de envío](email_troubleshooting.md#sending-errors)).
    - El límite propio de LibreFolio es de 50 correos por hora de forma predeterminada, lo que podría llegar a 1.200 al día. Para
      mantenerte por debajo del límite personal, añade `LIBREFOLIO_SMTP_MAX_PER_HOUR=20` a `.env`, es decir, 480 al
      día, y reinicia. El recuento es por proceso del servidor: consulta [Las variables](#variables).
    - Google revoca las contraseñas de aplicación cuando cambia la contraseña de tu Cuenta de Google: en ese caso, crea una
      nueva, escríbela en lugar de la anterior y reinicia. Eliminar la contraseña de aplicación, en la página
      donde la creaste, también impide que LibreFolio envíe.

=== "Relé local"

    Un relé como Postfix, en la misma máquina o en tu red, acepta correo sin inicio de sesión y
    lo entrega para LibreFolio.

    LibreFolio en el host, el relé en la misma máquina:

    ```env
    LIBREFOLIO_SMTP_HOST=localhost
    LIBREFOLIO_SMTP_TLS=none
    LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
    ```

    LibreFolio en Docker, el relé en otro contenedor de la misma red de Docker, aquí un servicio de Compose
    llamado `smtp-relay`:

    ```env
    LIBREFOLIO_SMTP_HOST=smtp-relay
    LIBREFOLIO_SMTP_TLS=none
    LIBREFOLIO_SMTP_FROM=LibreFolio <noreply@example.com>
    ```

    LibreFolio en Docker, el relé en el propio host: dentro de un contenedor, `localhost` es el
    contenedor, no el host. Añade las líneas marcadas a `docker-compose.yml`, define
    `LIBREFOLIO_SMTP_HOST=host.docker.internal` y deja que el relé acepte correo de la red de Docker
    (en Postfix: `inet_interfaces` y `mynetworks`):

    ```yaml
    services:
      librefolio:
        extra_hosts:                                # added
          - "host.docker.internal:host-gateway"     # added
    ```

    - El puerto 25 es el predeterminado con `none`: define `LIBREFOLIO_SMTP_PORT` solo si el relé escucha en
      otro.
    - Sin usuario y sin contraseña: un relé sin inicio de sesión no necesita ninguno de los dos.
    - El relé entrega el correo: se le debe permitir enviar para el dominio de
      `LIBREFOLIO_SMTP_FROM`.
    - `none` envía en claro: úsalo solo hacia tu propia máquina o red. Hacia cualquier otro
      servidor, Configuración › Administración › Correo electrónico y el registro de inicio muestran una [advertencia](email_troubleshooting.md#security).

---

## 🖥️ Configuración › Administración › Correo electrónico {: #email-tab }

Abre **Configuración** (icono de engranaje en la barra lateral), luego **Administración** y su pestaña **Correo electrónico**, después de
**Copia de seguridad** (en un teléfono, el icono de escudo y luego el icono de sobre). Solo los administradores pueden ver esta pestaña. El
icono de libro de su parte superior abre esta página.

### 🚦 El estado {: #state }

| Estado | Qué significa | Qué muestra la pestaña |
| --- | --- | --- |
| **Desactivado** | `LIBREFOLIO_SMTP_HOST` no está definida: no se envía nada. Este es el valor predeterminado. | Una explicación breve y una referencia a esta guía. |
| **Listo** | Todas las variables se pueden usar. | Los correos restantes de esta hora, los avisos que correspondan, la dirección con la que empiezan los enlaces enviados por correo y [su comprobación](#links-check), y **Enviar un correo de prueba**. |
| **No funciona** | Una variable no se puede usar: el correo electrónico permanece desactivado hasta que se corrija. | El problema, indicando la variable responsable, y un recordatorio para reiniciar después de la corrección. |

!!! note "✅ Listo no significa que ya se haya entregado un correo"

    **Listo** significa que todas las variables se pueden usar. LibreFolio no contacta con el servidor hasta que
    envía un correo electrónico: solo un correo de prueba demuestra que el servidor acepta tu correo.

- **No funciona** indica un problema a la vez, el primero que encuentra: corrígelo, reinicia y vuelve a mirar.
  [Problemas de configuración](email_troubleshooting.md#configuration-problems) indica qué comprobar para cada uno.
- Con **Listo**, la pestaña cuenta los correos restantes, como **48 de 50 correos restantes en esta hora**: los
  últimos 60 minutos, no la hora del reloj. Cuando no queda ninguno, indica en cuántos minutos puede salir el siguiente.
  Con varios procesos del servidor, cada uno cuenta los suyos, y la pestaña muestra el recuento del
  proceso que respondió.
- La advertencia de cifrado aparece cuando `LIBREFOLIO_SMTP_TLS=none` apunta a un servidor fuera de tu
  red local: consulta [Notas de seguridad](email_troubleshooting.md#security).
- Aparece un aviso sobre `LIBREFOLIO_PUBLIC_URL` cuando no está definida (información: los correos funcionan, pero
  ninguno con enlace puede salir) o no puede ser el inicio de un enlace (advertencia): consulta [Correos con enlace](email_flows.md#public-url).

### 🧭 La dirección de los enlaces enviados por correo {: #links-check }

Con el estado **Listo** y un `LIBREFOLIO_PUBLIC_URL` utilizable, la pestaña muestra *Los enlaces de los correos empiezan
por …*, seguido de esa dirección, y comprueba desde este navegador que **esta** instancia responde
ahí. Es la misma comprobación firmada que la de los diálogos de invitación y restablecimiento
([La dirección del servidor de un enlace](users.md#server-address)).

| Mensaje | Qué significa |
| --- | --- |
| *Comprobando desde este dispositivo que esta instancia responde ahí…* | La comprobación está en curso. |
| *Esta instancia responde ahí, desde este dispositivo.* | Bien: los enlaces llegan a este LibreFolio, al menos desde aquí. |
| *Desde este dispositivo, otro servidor responde en esa dirección, no esta instancia.* … | Algo responde ahí, pero no este LibreFolio. |
| *Este dispositivo no puede acceder a esta instancia en esa dirección.* … | Nada respondió que este navegador pudiera leer: una dirección incorrecta o cerrada, un nombre que este dispositivo no puede resolver, ninguna respuesta en 8 segundos, un navegador que bloquea que una página pública acceda a una dirección local o que primero te pide permiso, o una versión anterior de LibreFolio que no puede responder a la comprobación. |
| *Esta página usa https:// mientras que LIBREFOLIO_PUBLIC_URL empieza por http://* … | Este navegador no puede comprobar una dirección `http://` desde una página `https://`, y los enlaces de los correos viajarían sin cifrar: define la variable con la dirección `https://`. |
| *Este navegador no puede leer LIBREFOLIO_PUBLIC_URL como una dirección* … | El navegador interpreta las direcciones con algo más de rigor que el servidor: puede que los enlaces no se abran. Comprueba el valor. |

!!! warning "📱 Solo este dispositivo"

    La comprobación se ejecuta desde el navegador que estás usando, así que indica lo que ve este dispositivo. Una VPN, una
    dirección IP directa, su DNS o su red pueden ser distintos de los de tus usuarios: después de una advertencia, comprueba
    desde otro dispositivo antes de cambiar la variable. **Comprobar de nuevo** ejecuta la comprobación una vez más,
    por ejemplo después de cambiar de red.

- La comprobación se ejecuta una vez al abrir la pestaña, no después de cada correo de prueba. **Comprobar de nuevo** aparece con una
  advertencia.
- No se comprueba nada mientras el correo electrónico está **Desactivado** o **No funciona**, ni cuando `LIBREFOLIO_PUBLIC_URL` no está
  definida o no se puede usar, lo que indica el aviso anterior.

### ✉️ El correo de prueba {: #test-email }

Con el estado **Listo**, **Enviar un correo de prueba** te envía un correo electrónico a ti mismo:

- **A tu propia dirección**: el correo electrónico de tu cuenta, como en [Perfil](../user/settings/profile.md). No hay ningún campo para escribir otra.
- **En tu idioma**: el de tus [Preferencias](../user/settings/preferences.md) o, en su defecto, el **Idioma predeterminado** de la instancia ([Configuración global](settings.md)) o, en último caso, el inglés.
- **Qué dice**: su asunto es **LibreFolio test email** en inglés. El mensaje nombra tu instancia por la dirección con la que tu navegador llegó a ella, no por `LIBREFOLIO_PUBLIC_URL`, y dice que, si puedes leerlo, LibreFolio puede enviar correos electrónicos. Llega como texto sin formato con una versión HTML.
- **Se cuenta dentro del límite por hora**, incluso cuando el servidor lo rechaza.

El resultado aparece debajo del botón. **Correo de prueba enviado a tu dirección** significa que el servidor SMTP
aceptó el mensaje: mira en tu bandeja de entrada y en la carpeta de spam. En caso contrario, la pestaña indica qué salió
mal: consulta [Errores de envío](email_troubleshooting.md#sending-errors). Mientras LibreFolio habla con el servidor, el botón indica
**Enviando…**: LibreFolio espera hasta 20 segundos por cada paso, así que un servidor que no responde
tarda un poco en fallar.

---

## 🔗 Relacionados

- 📄 **[Correo electrónico: enlaces y mensajes](email_flows.md)** — Correos con enlace, enlaces enviados por un administrador, contraseñas olvidadas, …
- 📄 **[Correo electrónico: cuando no funciona](email_troubleshooting.md)** — Cuando no funciona, notas de seguridad
- 📝 **[Configuración](configuration.md)** — El archivo `.env` y sus opciones principales, y
  `LIBREFOLIO_PUBLIC_URL`
- 🔐 **[Configuración: secretos y ajustes de complementos](configuration_secrets.md)** — Secretos en archivos,
  como la contraseña SMTP
- 🩺 **[Configuración: comprobaciones y protecciones](configuration_security.md)** — Las comprobaciones de inicio
- ⚙️ **[Configuración global](settings.md)** — El interruptor **Requerir verificación de correo electrónico**
- 👥 **[Usuarios e invitaciones](users.md)** — Cuentas en espera y cómo permitir el acceso a una
- 🛠️ **[Herramientas de línea de comandos](cli_tools.md)** — Enlaces de invitación y de restablecimiento de contraseña desde la línea
  de comandos
- 🐳 **[Docker avanzado](docker_advanced.md)** — El archivo de Compose y el usuario que ejecuta LibreFolio
  en el contenedor
- 📂 **[Estructura del sistema de archivos](filesystem.md)** — Dónde se guarda el registro
- 👤 **[Perfil](../user/settings/profile.md)** — La dirección de correo electrónico de tu cuenta
- 🧑‍💻 Para desarrolladores: **[Servicio de correo electrónico (SMTP)](../developer/backend/email.md)** — Cómo funciona el servicio
  por dentro
