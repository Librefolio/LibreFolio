# 🚀 Primeros pasos

¡Bienvenido a LibreFolio! En unos pocos pasos crearás tu cuenta, harás un recorrido rápido e importarás tu primer extracto de bróker — y tu panel se llenará por sí solo.

---

## 📝 1. Registra tu cuenta

Abre la dirección de LibreFolio (por ejemplo, `http://localhost:6040`): aparecerá la página de inicio de sesión. Haz clic en **Regístrate aquí** para crear una cuenta.

Si la página de inicio de sesión no muestra **Regístrate aquí**, tu administrador solo permite el acceso con un enlace de invitación o ha cerrado el registro: pídele una invitación o una cuenta. Si tienes una invitación, sigue [Si has recibido un enlace de invitación](#invitation-link).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Formulario de registro" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Completa tus datos:

- 👤 **Nombre de usuario** — único, de 3 a 50 caracteres, sin `@`: con él inicias sesión. Los espacios, las letras acentuadas y los signos como `.`, `_`, `-` o `+` están permitidos. Al iniciar sesión, LibreFolio interpreta cualquier cosa con un `@` como una dirección de correo electrónico, por lo que el formulario rechaza uno: *El nombre de usuario no puede contener @: para iniciar sesión, siempre puedes usar tu dirección de correo electrónico.*
- 📧 **Correo electrónico** — una dirección válida; también sirve para iniciar sesión.
- 🔑 **Contraseña** y **Confirmar contraseña** — el indicador de seguridad te dice cuándo la contraseña es suficientemente segura.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registro con indicador de seguridad de la contraseña" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Primer usuario = Administrador"

    La primera cuenta que se registra se convierte en el **administrador**: gestiona la **[Configuración global](../admin/settings.md)** de toda la instancia y todas las funciones de administración.

### ✉️ Si has recibido un enlace de invitación {: #invitation-link }

Un administrador puede invitarte con un enlace propio, por mensaje o por correo electrónico: el correo es *Te han invitado a LibreFolio*, y su botón **Crea tu cuenta** abre el enlace.

1. Abre el enlace. LibreFolio lo comprueba y después muestra el formulario de registro con una nota de que te han invitado; una segunda nota te indica cuándo la invitación te convierte en administrador.
2. Si el administrador escribió tu dirección de correo electrónico en la invitación, ya está rellenada: puedes cambiarla.
3. Elige tu nombre de usuario y contraseña, y haz clic en **Registrarse**.
4. Volverás a la página de inicio de sesión, con una confirmación: inicia sesión con tu nueva cuenta.

- ⏱️ Un enlace de invitación funciona una sola vez, durante 7 días. Si la página indica que el enlace ha caducado, ya se ha usado, se ha retirado o no es válido, pide uno nuevo a tu administrador.
- 📬 Si la instancia te pide que confirmes tu dirección de correo electrónico, abre el enlace que te envía por correo antes de iniciar sesión: consulta [Si LibreFolio te pide que confirmes tu correo electrónico](#verify-email).
- 🔒 En cuanto se abre la página, la barra de direcciones pierde la parte secreta del enlace: conserva el mensaje que recibiste por si necesitas volver a abrir el enlace. Si la página indica que el enlace está incompleto, ábrelo de nuevo desde ese mensaje.
- 🚪 Si la página indica que el registro está deshabilitado, el administrador ha cerrado los registros por ahora: pregúntale.

### 📬 Si LibreFolio te pide que confirmes tu correo electrónico {: #verify-email }

Algunas instancias piden a cada cuenta nueva que confirme su dirección de correo electrónico antes del primer inicio de sesión. En ese caso, después de **Registrarse**:

1. La página de inicio de sesión dice: *Cuenta creada. Te estamos enviando un correo electrónico con un enlace para activarla: ábrelo en un plazo de 24 horas y luego inicia sesión. ¿No recibiste el correo tras unos minutos? Revisa la carpeta de spam y luego inicia sesión con tu nombre de usuario y contraseña: se te ofrecerá un nuevo enlace.* Todavía no puedes iniciar sesión.
2. Abre el correo *Confirma tu dirección de correo electrónico* y haz clic en **Confirma mi dirección de correo electrónico**. Si el botón no funciona, copia en tu navegador la dirección que aparece debajo.
3. El botón abre una página de LibreFolio que te pide confirmación. Haz clic allí en **Confirma mi dirección de correo electrónico**: LibreFolio confirmará tu dirección y te devolverá a la página de inicio de sesión, con una confirmación: inicia sesión con tu nombre de usuario y contraseña.

- 🖱️ ¿Por qué un clic más? Algunos servicios de correo abren los enlaces de un mensaje por su cuenta para comprobarlos: el clic garantiza que eres tú quien confirma.
- 🙋 Si no te registraste en esta instancia, simplemente cierra la página: no ocurrirá nada.
- ⏱️ El enlace funciona una sola vez, durante 24 horas.
- 📭 ¿No recibiste el correo? Revisa la carpeta de spam. Después, en la página de inicio de sesión, inicia sesión con tu nombre de usuario y contraseña: LibreFolio indicará que tu dirección aún no está verificada y ofrecerá **Enviar el enlace de nuevo** más abajo. Un nuevo enlace sustituye a los anteriores. Si lo solicitas con demasiada frecuencia, o tras demasiadas contraseñas incorrectas, la página te indicará cuántos minutos faltan para poder solicitarlo de nuevo.
- 🚦 Si la página de inicio de sesión indica, en cambio, que el correo de activación no ha podido salir ahora porque hubo demasiados registros desde tu red en la última hora (o la instancia ha enviado demasiados correos), no hay ningún correo en camino. Tu cuenta se ha creado igualmente: espera los minutos que indique la página, inicia sesión con tu nombre de usuario y contraseña, y se te ofrecerá **Enviar el enlace de nuevo**.
- ⌛ Si la página indica que el enlace ha caducado, inicia sesión de la misma manera: se te ofrecerá un nuevo enlace. Si mientras tanto la instancia se ha quedado sin plazas libres, pregunta a tu administrador.
- ✅ Si la página indica que el enlace ya se ha usado, es probable que tu cuenta ya esté activa: inicia sesión.
- 🔒 Al igual que con una invitación, la barra de direcciones pierde la parte secreta del enlace en cuanto se abre la página: conserva el correo hasta que tu cuenta esté activa.

---

## 🔐 2. Inicia sesión

Después de registrarte, volverás a la página de inicio de sesión. Inicia sesión con tu nombre de usuario (o correo electrónico) y tu contraseña. Escribe tu nombre de usuario exactamente como lo elegiste, incluidas las mayúsculas. Si tu nombre de usuario contiene una `@`, algo que pueden tener las cuentas creadas antes de la versión 1.3, inicia sesión con tu dirección de correo electrónico en su lugar. Si LibreFolio te pidió que confirmaras tu dirección de correo electrónico, abre primero el enlace que te envió por correo: consulta [Si LibreFolio te pide que confirmes tu correo electrónico](#verify-email).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Página de inicio de sesión" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Debajo de la tarjeta, como en todas las páginas de inicio de sesión, una línea contiene el [aviso legal](settings/about.md#legal-notice) de tu instancia.

!!! note "Demasiados intentos de inicio de sesión"

    Tras 10 contraseñas incorrectas en 15 minutos para el mismo nombre de usuario o dirección de correo electrónico, o 50 desde la misma dirección IP, la página de inicio de sesión dice *Demasiados intentos de inicio de sesión: espera unos minutos e inténtalo de nuevo.* Hasta que termine la espera, se rechaza incluso la contraseña correcta: espera hasta 15 minutos y luego inicia sesión. Tu administrador también puede permitirte entrar de inmediato reiniciando LibreFolio.

### 📧 Si has olvidado tu contraseña {: #forgot-password }

En la página de inicio de sesión, haz clic en **¿Olvidaste tu contraseña?**. Cuando tu instancia puede enviar correos electrónicos, la página tiene un formulario en la parte superior:

1. Escribe tu nombre de usuario o tu dirección de correo electrónico y haz clic en **Envíame un enlace de restablecimiento**.
2. La página responde *Correo enviado: revisa también la carpeta de spam.*, de la misma manera tanto si hay una cuenta coincidente como si no: revisa tu bandeja de entrada y la carpeta de spam.
3. Abre el correo *Restablece tu contraseña de LibreFolio* y haz clic en **Elige una nueva contraseña**. La página que se abre es la de un enlace enviado por un administrador: sigue [Si un administrador te ha enviado un enlace para restablecer la contraseña](#password-reset-link) a partir del paso 2.

- ⏱️ El enlace funciona una sola vez, durante 30 minutos.
- 📭 ¿No recibiste el correo tras unos minutos? Puede que la cuenta esté desactivada o registrada con otra dirección, o que las solicitudes se hayan hecho demasiado seguidas: inténtalo más tarde o pregunta a tu administrador.
- ⏳ Tras una solicitud, el botón muestra una cuenta atrás de 5 minutos antes de que puedas pedirlo de nuevo: el servidor envía como máximo un correo cada 5 minutos para la misma cuenta. Recargar la página mantiene la cuenta atrás.
- 💻 Cuando tu instancia no puede enviar correos, la página muestra en su lugar el comando que tu administrador ejecuta en el servidor para restablecer una contraseña: pregúntale.

### 🔑 Si un administrador te ha enviado un enlace para restablecer la contraseña {: #password-reset-link }

Tu administrador también puede enviarte un enlace para que elijas una nueva contraseña, por mensaje o por correo electrónico.

1. Abre el enlace: la página muestra la cuenta a la que pertenece.
2. Escribe la nueva contraseña dos veces: debe cumplir las reglas que se muestran debajo del campo.
3. Haz clic en **Establecer la nueva contraseña**. Volverás a la página de inicio de sesión, con una confirmación: inicia sesión con la nueva contraseña.

- ⏱️ El enlace funciona una sola vez, durante 30 minutos. Si la página indica que ha caducado, que ya se ha usado o que se ha retirado, pide uno nuevo: cada enlace nuevo retira los enviados antes.
- 🚪 Al establecer la nueva contraseña, se cierra la sesión de tu cuenta en todos los dispositivos: vuelve a iniciar sesión con la nueva contraseña en cada uno.

---

## 🎉 3. Configuración de bienvenida y recorrido rápido {: #welcome-setup }

La primera vez que inicias sesión, LibreFolio abre una página de **Bienvenida** antes del panel:

- 🌍 Comprueba **Idioma** y **Moneda predeterminada**: se inician con los valores predeterminados de tu administrador.
- 🖼️ Añade una **foto de perfil** si quieres; de lo contrario, se mostrarán tus iniciales.
- ✅ Haz clic en **Continuar** para guardar, o en **Omitir la configuración permanentemente** para mantener la configuración actual.
- 🚪 ¿Necesitas salir? **Cerrar sesión** está en la esquina superior derecha.
- ⚖️ Debajo de la tarjeta: el [aviso legal](settings/about.md#legal-notice) de tu instancia.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="welcome-setup" alt="La página de Bienvenida del primer inicio: el bloque de foto de perfil con el avatar de iniciales y Elegir foto, Idioma y Moneda predeterminada ya rellenados, la nota de que tu preferencia de tema se mantiene sin cambios, y Omitir la configuración permanentemente y Continuar" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

A continuación se muestra una breve animación de bienvenida y luego el **Recorrido rápido** comienza por sí solo: haz clic en **Iniciar recorrido** para empezar de inmediato, o en **✕** para omitirlo. El recorrido muestra dónde está cada cosa: el botón de menú y, después, **Panel**, **Transacciones**, **Brókers**, **FX**, **Activos**, **Herramientas** y **Configuración**. Solo señala: nunca abre un formulario ni crea datos.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="core-tour-step" alt="El Recorrido rápido en el Panel, en el paso 5 de 8, tipos de cambio: un marco y un cursor sobre la entrada Tipos de cambio de la barra lateral, y el panel de mensaje con Atrás y Siguiente" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

??? note "👋 ¿Ya usas LibreFolio? — cuentas anteriores a las guías"

    Si tu cuenta existía antes de que se añadieran las guías, LibreFolio no te hace pasar por ellas: la configuración de bienvenida cuenta como **Completada**, y el recorrido y todas las guías como **Omitidos**. Aun así, puedes repetir cualquiera de ellos desde **[Configuración → Preferencias → Introducción y guías](settings/preferences.md#onboarding-and-guides)**.

??? warning "⚠️ La configuración no se carga — qué hacer"

    Si no se pueden cargar tu configuración o el progreso de tus guías, una página **No pudimos cargar la introducción** ofrece **Reintentar** y **Cerrar sesión**. Si tu configuración de bienvenida ya está hecha, es posible que veas el Panel en su lugar, con un banner de **Reintentar** en la parte superior.

### 🧭 Guías contextuales

Más adelante, unas guías breves se inician la primera vez que llegas a un lugar donde ayudan:

| Área | Guías contextuales |
|---|---|
| **Transacciones** | Resumen de la página, formulario Añadir transacción, espacio de trabajo masivo y asistente de importación |
| **Brókers** | Página de brókers, formulario Añadir bróker y detalles del bróker |
| **FX** | Página de FX, formulario Añadir par y detalles del par |
| **Activos** | Página de activos, formulario Añadir activo y detalles del activo |

- Señalan controles reales y nunca hacen clic, suben archivos, editan ni guardan por ti.
- Un marco pulsante marca el área de la que habla un paso; un pequeño cursor marca un botón que puedes probar. Al hacer clic en él, realiza su función normal y avanza la guía.
- El panel de mensaje se atenúa un poco después de un momento, para que puedas ver la página que hay detrás; pasa el cursor por encima para que vuelva.
- Si abandonas una página en mitad de una guía, su guía se retoma en el mismo paso cuando vuelves; cerrar un formulario reinicia la guía de ese formulario.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="contextual-guide" alt="La guía de la página de FX, en el paso 2 de 4, sobre el filtrado de fechas, divisas y vistas: un marco alrededor de los filtros de divisas y el panel de mensaje con Atrás y Siguiente" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Puedes repetir cualquier guía desde **[Configuración → Preferencias → Introducción y guías](settings/preferences.md#onboarding-and-guides)**.

---

## 🏦 4. Importa tu primer extracto (crea brókers y activos sobre la marcha)

Tu panel sigue vacío, tanto si llegas directamente a él como si vienes de las pantallas de bienvenida anteriores.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Panel vacío" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La forma más rápida de llenarlo es importar tu historial de transacciones. No necesitas configurar brókers ni activos primero: el asistente de importación los crea sobre la marcha.

### 📋 Pasos

1. **Abre el asistente de importación**: en la página **[Transacciones](transactions/index.md)**, haz clic en **Importar** (:material-file-upload:). La página de detalles de un bróker tiene el mismo botón, con ese bróker ya seleccionado.

2. **Sube tu extracto**: arrastra el informe de tu bróker (`.csv`, `.xlsx` o `.xls`) al asistente y asígnalo a su bróker; elige **Crear nuevo** si el bróker aún no existe. Todos los informes que subes se conservan (los encuentras en **[Archivos y subidas](files/index.md#broker-reports)**): la próxima vez, omite este paso y marca el informe en el siguiente paso.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Paso de subida del asistente" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. **Selecciona archivos y analiza**: marca los informes que quieres importar. Cada uno recibe el analizador de su bróker; cámbialo por archivo si es necesario, **CSV genérico** para un formato desconocido. LibreFolio lee entonces cada fila y resume lo que ha encontrado: transacciones, valores, incidencias y posibles duplicados. Después, algunos archivos necesitan uno o dos pasos adicionales (consulta el panel de abajo).
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Paso de análisis del asistente" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Revisa e importa**: asocia cada valor con tu biblioteca de activos o créalo **sobre la marcha** con los detalles leídos del extracto. Los posibles duplicados llegan desmarcados, y las filas con fecha anterior a la fecha de apertura del bróker se omiten. Más información en **[Asignación de activos](transactions/import/index.md#asset-mapping)**.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Paso de revisión del asistente: resolución de activos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

5. **Guarda desde el editor masivo**: **Importar N transacciones** traslada las filas marcadas al editor masivo; todavía no se ha guardado nada. Dales un último vistazo y haz clic en **Guardar todo**.

??? note "🧩 Pasos adicionales — solo cuando tus archivos los necesitan"

    El asistente añade un paso solo cuando tus archivos lo requieren; un informe limpio de un solo archivo los omite todos:

    - **Unificar activos** — el mismo valor aparece con nombres o códigos diferentes.
    - **Correcciones** — algunas filas no se pudieron leer por completo.
    - **Duplicados** — el mismo movimiento está en dos archivos que importas juntos.
    - **Alinear con el banco** — después de **Revisión**, para un conjunto de informes como Danske Bank, cuando las cifras del banco difieren de las de LibreFolio.

    Consulta **[Pasos que solo aparecen cuando son necesarios](transactions/import/how-to.md#only-when-needed)**.

La primera vez que abres el asistente, una guía te acompaña por los pasos que necesitan tus archivos; nunca hace clic ni guarda por ti (consulta **[Primera importación guiada](transactions/import/how-to.md#guided-first-import)**). Para ver el recorrido completo, consulta **[Cómo importar transacciones](transactions/import/how-to.md)**; para conocer los brókers y formatos de archivo admitidos, consulta **[Importar desde el bróker](transactions/import/index.md)**.

---

## 📈 5. Vuelve al panel

Vuelve al **Panel**: el valor de tu cartera, tu asignación (por tipo, sector y geografía) y el historial de rendimiento ya están completados.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Vista principal del panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 6. ¿Qué viene después?

Ahora que tu cartera ya tiene datos, puedes:

- 🤝 **[Comparte tu bróker](brokers/sharing.md)** — Da acceso a familiares o asesores.
- 💱 **[Configura los tipos de cambio](fx/index.md)** — Configura la conversión de divisa para carteras multidivisa.
- ⚙️ **[Personaliza tus preferencias](settings/preferences.md)** — Ajusta tu idioma, moneda predeterminada y tema. Los administradores también gestionan la **[Configuración global](../admin/settings.md)** de todo el sistema.
- 🧭 **[Repite la configuración de bienvenida o los recorridos guiados](settings/preferences.md#onboarding-and-guides)** — Revisa la pantalla de bienvenida, el recorrido rápido o la guía de importación en cualquier momento desde Configuración → Preferencias.
- 📱 **[Instala LibreFolio como aplicación](pwa.md)** — Colócala en la pantalla de inicio de tu teléfono o en su propia ventana de escritorio.
