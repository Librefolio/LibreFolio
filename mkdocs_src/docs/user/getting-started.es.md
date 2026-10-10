# 🚀 Primeros pasos

¡Bienvenido a LibreFolio! En unos pocos pasos creas tu cuenta, haces un recorrido rápido e importas tu primer extracto de bróker — y tu panel se llena por sí solo.

---

## 📝 1. Registra tu cuenta

Abre la dirección de tu LibreFolio (por ejemplo `http://localhost:6040`): aparece la página de inicio de sesión. Haz clic en **Regístrate aquí** para crear una cuenta.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="02-register-empty" alt="Formulario de registro" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Rellena tus datos:

- 👤 **Nombre de usuario** — único: inicias sesión con él.
- 📧 **Correo electrónico** — una dirección válida; también sirve para iniciar sesión.
- 🔑 **Contraseña** y **Confirmar contraseña** — el indicador de fortaleza te dice cuándo la contraseña es suficientemente segura.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="03-register-filled" alt="Registro con indicador de fortaleza de contraseña" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

!!! info "Primer usuario = Administrador"

    La primera cuenta que se registra se convierte en el **administrador**: gestiona la **[Configuración global](../admin/settings.md)** de toda la instancia y todas las funciones de administrador.

---

## 🔐 2. Inicia sesión

Después de registrarte, vuelves a la página de inicio de sesión. Inicia sesión con tu nombre de usuario (o correo electrónico) y tu contraseña.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="auth" data-name="01-login" alt="Página de inicio de sesión" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎉 3. Configuración de bienvenida y recorrido rápido {: #welcome-setup }

La primera vez que inicias sesión, LibreFolio abre una página de **Bienvenida** antes del panel:

- 🌍 Revisa **Idioma** y **Moneda predeterminada**: comienzan con los valores predeterminados de tu administrador.
- 🖼️ Añade una **foto de perfil** si quieres — de lo contrario, se muestran tus iniciales.
- ✅ Haz clic en **Continuar** para guardar, o en **Omitir configuración permanentemente** para mantener la configuración actual.
- 🚪 ¿Necesitas salir? **Cerrar sesión** está en la esquina superior derecha.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="welcome-setup" alt="La página de Bienvenida de la primera ejecución: el bloque de foto de perfil con el avatar de iniciales y Elegir imagen, Idioma y Moneda predeterminada prellenados, la nota de que tu preferencia de tema se mantiene sin cambios, y Omitir configuración permanentemente y Continuar" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Después sigue una breve animación de bienvenida y, luego, el **Recorrido rápido** comienza por sí solo — haz clic en **Iniciar recorrido** para empezar de inmediato, o en **✕** para omitirlo. El recorrido muestra dónde está cada cosa: el botón de menú y, después, **Panel**, **Transacciones**, **Brókers**, **FX**, **Activos**, **Herramientas** y **Configuración**. Solo señala: nunca abre un formulario ni crea datos.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="core-tour-step" alt="El Recorrido rápido en el Panel en el paso 5 de 8, tipos de cambio: un marco y un cursor sobre la entrada Tipos de cambio de la barra lateral, y el panel de mensajes con Atrás y Siguiente" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

??? note "👋 ¿Ya usas LibreFolio? — cuentas anteriores a las guías"

    Si tu cuenta existía antes de que se añadieran las guías, LibreFolio no te las muestra:
    la configuración de bienvenida cuenta como **Completada**, y el recorrido y todas las guías como **Omitidos**. Aun así, puedes repetir cualquiera de ellas desde
    **[Configuración → Preferencias → Introducción y guías](settings/preferences.md#onboarding-and-guides)**.

??? warning "⚠️ La configuración no se carga — qué hacer"

    Si tu configuración o el progreso de tus guías no se pueden cargar, aparece una página **No pudimos cargar la introducción** que ofrece **Reintentar** y **Cerrar sesión**. Si tu configuración de bienvenida ya está hecha, puede que veas el Panel en su lugar, con un banner de **Reintentar** en la parte superior.

### 🧭 Guías contextuales

Más adelante, aparecen breves guías la primera vez que llegas a un lugar donde resultan útiles:

| Área | Guías contextuales |
|---|---|
| **Transacciones** | Resumen de la página, formulario Añadir transacción, espacio de trabajo masivo y Asistente de importación |
| **Brókers** | Página de Brókers, formulario Añadir bróker y detalles del bróker |
| **FX** | Página de FX, formulario Añadir par FX y detalles del par FX |
| **Activos** | Página de Activos, formulario Añadir activo y detalles del activo |

- Señalan controles reales y nunca hacen clic, suben, editan ni guardan por ti.
- Un marco pulsante marca el área de la que habla un paso; un pequeño cursor marca un botón que puedes probar. Al hacer clic en él, realiza su función normal y avanza la guía.
- El panel de mensajes se atenúa un poco tras un momento, para que puedas ver la página que hay detrás; pasa el cursor por encima para volver a mostrarlo.
- Si abandonas una página en mitad de una guía, esta se retoma en el mismo paso cuando vuelves; cerrar un formulario reinicia la guía de ese formulario.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="onboarding" data-name="contextual-guide" alt="La guía de la página FX en el paso 2 de 4, sobre el filtrado de fechas, monedas y vistas: un marco alrededor de los filtros de moneda, y el panel de mensajes con Atrás y Siguiente" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Puedes repetir cualquier guía desde **[Configuración → Preferencias → Introducción y guías](settings/preferences.md#onboarding-and-guides)**.

---

## 🏦 4. Importa tu primer extracto (crea bróker y activos sobre la marcha)

Tu panel sigue vacío — ya sea que llegues allí directamente o después de las pantallas de bienvenida anteriores.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="empty-state" alt="Panel vacío" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La forma más rápida de llenarlo es importar tu historial de transacciones. No necesitas configurar brókers ni activos primero: el Asistente de importación los crea sobre la marcha.

### 📋 Pasos

1. **Abre el Asistente de importación**: en la página **[Transacciones](transactions/index.md)**, haz clic en **Importar** (:material-file-upload:). La página de detalles de un bróker tiene el mismo botón, con ese bróker ya seleccionado.

2. **Sube tu extracto**: arrastra el informe de tu bróker (`.csv`, `.xlsx` o `.xls`) al asistente y asígnalo a su bróker — elige **Crear nuevo** si el bróker aún no existe. Cada informe que subes se conserva (lo encuentras en **[Archivos y subidas](files/index.md#broker-reports)**): la próxima vez, omite este paso y marca el informe en el siguiente.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step1" alt="Paso de subida del asistente" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

3. **Selecciona archivos y analiza**: marca los informes para importar. Cada uno recibe el analizador de su bróker — cámbialo por archivo si es necesario, **CSV genérico** para un formato desconocido. LibreFolio lee entonces cada fila y resume lo que encontró: transacciones, valores, incidencias y posibles duplicados. Algunos archivos necesitan después uno o dos pasos extra (consulta el panel de abajo).
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step3" alt="Paso de análisis del asistente" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

4. **Revisa e importa**: asigna cada valor a tu biblioteca de activos, o créalo **sobre la marcha** con los detalles leídos del extracto. Los posibles duplicados llegan desmarcados, y las filas con fecha anterior a la fecha de apertura del bróker se omiten. Más información en **[Asignación de activos](transactions/import/index.md#asset-mapping)**.
    <div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
        <img class="gallery-img" data-category="brokers" data-name="import-wizard-step4-resolution" alt="Paso de revisión del asistente: resolución de activos" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
    </div>

5. **Guarda desde el editor masivo**: **Importar N transacciones** mueve las filas marcadas al editor masivo — aún no se ha guardado nada. Dales un último vistazo y luego haz clic en **Guardar todo**.

??? note "🧩 Pasos extra — solo cuando tus archivos los necesitan"

    El asistente añade un paso solo cuando tus archivos lo requieren; un informe limpio de un solo archivo los omite todos:

    - **Unificar activos** — el mismo valor aparece con nombres o códigos diferentes.
    - **Correcciones** — algunas filas no se pudieron leer por completo.
    - **Duplicados** — el mismo movimiento está en dos archivos que importas juntos.
    - **Alinear con el banco** — después de **Revisar**, para un conjunto de informes como Danske Bank, cuando las cifras del banco difieren de las de LibreFolio.

    Ver **[Pasos que aparecen solo cuando se necesitan](transactions/import/how-to.md#only-when-needed)**.

La primera vez que abres el asistente, una guía te acompaña por los pasos que necesitan tus archivos; nunca hace clic ni guarda por ti (consulta **[Primera importación guiada](transactions/import/how-to.md#guided-first-import)**). Para el recorrido completo, consulta **[Cómo importar transacciones](transactions/import/how-to.md)**; para los brókers y formatos de archivo compatibles, consulta **[Importar desde bróker](transactions/import/index.md)**.

---

## 📈 5. Vuelve al panel

Vuelve al **Panel**: el valor de tu cartera, tu asignación (por tipo, sector y geografía) y tu historial de rendimiento ahora están completados.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="main" alt="Vista principal del panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔮 6. ¿Qué sigue?

Ahora que tu cartera está poblada, puedes:

- 🤝 **[Comparte tu bróker](brokers/sharing.md)** — Da acceso a familiares o asesores.
- 💱 **[Configura los tipos de cambio](fx/index.md)** — Configura la conversión de divisa para carteras multidivisa.
- ⚙️ **[Personaliza tus preferencias](settings/preferences.md)** — Ajusta tu idioma, moneda predeterminada y tema. Los administradores también gestionan la **[Configuración global](../admin/settings.md)** de todo el sistema.
- 🧭 **[Repite la configuración de bienvenida o los recorridos guiados](settings/preferences.md#onboarding-and-guides)** — Revisa la pantalla de bienvenida, el recorrido rápido o la guía de importación en cualquier momento desde Configuración → Preferencias.
- 📱 **[Instala LibreFolio como aplicación](pwa.md)** — Ponlo en la pantalla de inicio de tu teléfono o en su propia ventana de escritorio.
