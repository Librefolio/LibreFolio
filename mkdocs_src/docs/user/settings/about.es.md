# ℹ️ Acerca de

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about" alt="Acerca de">
</div>

La pestaña **Acerca de** muestra:

- La **versión** actual de LibreFolio
- La **licencia** (AGPL-3.0)
- Enlaces al **repositorio de GitHub** y a la **documentación**
- Una tarjeta **Apoya a LibreFolio** con el enlace del café y los botones para compartir — consulta [Apoya a LibreFolio](#support-librefolio) más abajo
- Una tarjeta de **Aviso legal** — consulta [Aviso legal](#legal-notice) más abajo
- Una cuadrícula de **información del sistema** (versión de Python, sistema operativo, modo de despliegue — Docker o local —, navegador, ventana gráfica, tema e idioma) con un botón de **copiar para incidencia** que empaqueta estos detalles en un informe de error listo para pegar
- Los **plugins instalados**: listas plegables de los proveedores de precios de activos, proveedores de tipos de cambio (FX), plugins de importación de brókers e indicadores de señales detectados al iniciar, seguidas de **Diagnóstico de plugins**

---

## ❤️ Apoya a LibreFolio {: #support-librefolio }

La tarjeta **Apoya a LibreFolio** ofrece dos formas de ayudar al proyecto:

- **Buy Me a Coffee** abre la página de Buy Me a Coffee del proyecto en una nueva pestaña. El mismo enlace está en
  la cabecera de la página (el icono del café, con su etiqueta en pantallas más anchas), en el
  menú **Ayuda y soporte**, y en la parte superior de las páginas de inicio de sesión.
- Debajo de **O comparte**, un botón por red social: **X**, **Reddit**, **Facebook**,
  **Instagram** y **TikTok**.

Un botón para compartir abre un diálogo **Compartir en …** con un **Mensaje sugerido** redactado para esa
red, en el idioma de la interfaz. Sea cual sea el idioma, todos los mensajes terminan con los
mismos cinco hashtags: `#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance`.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="social-share-modal" alt="Diálogo Compartir en Reddit con el título sugerido, un mensaje que termina en los cinco hashtags y Copiar e ir">
</div>

**Copiar e ir** copia el mensaje, seguido del enlace al sitio web público del proyecto, y
abre la red social en una nueva pestaña: LibreFolio permanece abierto en su propia pestaña. Cada red acepta
una cantidad distinta de contenido preparado, y el diálogo explica qué esperar antes de que hagas clic:

| Red | Qué se abre |
|---|---|
| **X** | Una publicación nueva con el mensaje y el enlace del proyecto ya rellenados. |
| **Reddit** | Una publicación de texto nueva, con el **Título sugerido** como título y el mensaje como cuerpo. Si Reddit deja el cuerpo vacío, pega el texto que acabas de copiar. |
| **Facebook** | Una publicación solo con la vista previa del enlace: pega el texto copiado en el mensaje de la publicación. |
| **Instagram** | Instagram en sí, que no puede preparar una publicación a partir de un enlace: elige **Crear** (+), selecciona una foto o un vídeo y pega el pie de foto copiado. |
| **TikTok** | La página de subida de TikTok (inicia sesión si te lo pide): selecciona tu vídeo y pega el pie de foto copiado. |

Si el texto no se puede copiar, el diálogo lo indica y te pide que permitas el acceso al portapapeles. Si el
navegador bloquea la nueva pestaña, el diálogo indica que el texto se ha copiado pero que el sitio no se ha podido
abrir, y te pide que permitas las ventanas emergentes. LibreFolio nunca publica nada por ti: la publicación es
tuya para revisarla y publicarla en la red social.

### ☕ La ventana emergente de donación {: #donation-popup }

De vez en cuando, justo después de iniciar sesión, LibreFolio te recuerda que puedes apoyar el
proyecto, con el mismo enlace del café y los mismos botones para compartir.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="donation-popup" alt="Ventana emergente de donación tras iniciar sesión, con Buy Me a Coffee, los cinco botones para compartir y Quizá más tarde">
</div>

---

## ⚖️ Aviso legal {: #legal-notice }

La tarjeta de **Aviso legal** contiene un breve descargo de responsabilidad: LibreFolio te ayuda a seguir tus inversiones
y no constituye asesoramiento financiero. Si tu instancia los tiene, la tarjeta también enlaza sus
**Términos del servicio** y su **Política de privacidad**: cada uno se abre en una nueva pestaña.

Encontrarás el mismo aviso bajo la tarjeta de la página de Bienvenida. Una versión más corta, en una sola línea con los
mismos enlaces, aparece bajo la tarjeta de cada página de inicio de sesión y al pie de la barra lateral, debajo del
número de versión, mientras la barra lateral está expandida. Todo texto que copies con
[exportación IA](../ai-export/index.md) incluye también el aviso, cerca del final y sin los enlaces.

---

## 🧩 Diagnóstico de plugins

El panel plegable **Diagnóstico de plugins** informa del estado de los cuatro registros de plugins — **Activo**
(proveedores de precios), **FX** (proveedores de tipos de cambio), **BRIM** (importadores de brókers) y **Señales**
(indicadores) — y, debajo de ellos, de las **Herramientas**.

Cada registro está marcado como **Todo cargado** (verde) o enumera los **plugins que no se pudieron importar** (rojo), con el nombre del archivo y el error subyacente. Si falta en el resto de la aplicación un proveedor, importador o indicador que esperabas encontrar, este panel te dice por qué: un plugin que no se carga al iniciar simplemente no se registra.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-plugin-diagnostics" alt="Panel plegable de diagnóstico de plugins en la pestaña Acerca de">
</div>

### 🧰 Herramientas y diagnóstico de herramientas {: #tool-diagnostics }

Debajo de los registros, el panel **Herramientas** enumera el catálogo de [Herramientas](../tools/index.md). Es
de solo lectura —no se ejecuta ningún cálculo, sondeo ni reparación— y solo se carga cuando abres
**Diagnóstico de plugins**; **Recargar** vuelve a leerlo. Para cada herramienta ves su nombre y descripción,
un enlace de **Documentación**, su código y `Version: <contract_version>`, y si se incluye una interfaz
compatible en el frontend que estás ejecutando. La versión de implementación no se muestra
aquí, y el par de versiones `Backend/API · UI` aparece solo en las tarjetas de la página Herramientas y en la
cabecera de una herramienta abierta.

Abre **Diagnóstico de herramientas** para cargar una instantánea del proceso del servidor que respondió:

- el **Ámbito de la instantánea** y el **identificador del proceso de la API**;
- la **Instantánea del grupo de ejecución**: si el grupo está disponible, los trabajos activos, en cola, pendientes,
  completados y fallidos, y los carriles degradados;
- las **Herramientas cargadas en este proceso de la API**, cada una con su nombre, código y versión de contrato, y
  los posibles **Fallos de descubrimiento**;
- los **Límites efectivos de la plataforma**, en un panel plegable propio.

La instantánea describe un solo proceso del servidor, no toda la instancia, y no se actualiza por sí sola:
vuelve a cargarla para leerla de nuevo.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-tool-diagnostics" alt="Panel Herramientas en Diagnóstico de plugins, con el asignador PAC y Diagnóstico de herramientas abiertos">
</div>

---

## 📜 Ventana modal del registro de cambios {: #changelog-modal }

La **ventana modal del registro de cambios** integrada en la aplicación muestra el registro de cambios incluido con LibreFolio, en el idioma de tu interfaz. Puedes abrirla desde dos lugares:

- el **número de versión en la parte inferior de la barra lateral** (en cualquier página), y
- la **etiqueta de versión justo debajo del título de esta página Acerca de** (Configuración → Acerca de).

Cada versión se muestra en tu idioma cuando su traducción está disponible; una versión aún no traducida aparece en inglés, marcada con una pequeña etiqueta **Aún no traducida**.

- Un **panel plegable por versión** — solo la versión más reciente empieza abierta; las secciones y subsecciones también se pliegan.
- Un **índice de versiones** con chips en la parte superior: al hacer clic en una versión, esta se despliega y la vista se desplaza directamente hasta ella.
- Un **cuadro de búsqueda** que desciende por los pliegues: las secciones coincidentes se abren automáticamente y los chips de resultado en los que se puede hacer clic saltan al punto exacto.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal-search" alt="Búsqueda de la ventana modal del registro de cambios abriendo los pliegues coincidentes">
</div>

- Botones de **expandir todo / contraer todo**, y un enlace al archivo del registro de cambios en GitHub.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal" alt="Ventana modal del registro de cambios con versiones plegables y búsqueda">
</div>

### 🔄 Comprobar si hay actualizaciones

La cabecera de la ventana modal también tiene un botón **Buscar actualizaciones**. Pregunta al servidor qué versión se
está ejecutando, vuelve a leer la última versión **estable** de GitHub (en lugar de reutilizar el resultado
que la comprobación automática conserva durante una hora) y compara ambas. Una versión más reciente solo cuenta
una vez que su imagen de Docker está disponible en el registro, por lo que una versión cuya compilación aún está en curso
no se ofrece todavía; consulta [Notificaciones de actualización](../../admin/index.md#update-notifications).

Una comprobación iniciada aquí siempre te dice cómo ha ido:

- Si LibreFolio está **actualizado**, aparece un aviso de confirmación con la versión detectada en línea.
- Si GitHub no tiene **ninguna versión estable**, o la **imagen de Docker de una versión más reciente aún no está disponible**,
  un aviso de advertencia lo indica.
- Si la comprobación **falla** —por ejemplo, cuando no se puede acceder a GitHub o al registro—, un error
  te pide que lo intentes de nuevo. Una comprobación fallida nunca indica que estás actualizado.
- Si existe una versión más reciente y eres **administrador**, la ventana modal **Nueva versión disponible** se abre
  de inmediato, encima del registro de cambios: las versiones actual y más reciente una al lado de la otra, con **Cómo actualizar**
  (la [guía de actualización](../installation.md#updating)) y **Notas de la versión en GitHub**. Puedes
  cerrarla con **Recuérdamelo más tarde** (se te recordará en el siguiente inicio de sesión) o
  **Omitir esta versión** (la comprobación automática nunca vuelve a avisar para esa versión; una comprobación iniciada
  aquí todavía la muestra). A los administradores también se les consulta automáticamente al iniciar sesión; consulta
  [Notificaciones de actualización](../../admin/index.md#update-notifications) para el flujo del lado del administrador.
- Si existe una versión más reciente y **no eres administrador**, el diálogo **Actualización disponible — contacta con un administrador**
  enumera los **administradores** de la instancia —con direcciones de correo electrónico cuando están disponibles, cada una con un enlace mailto
  y un botón de copiar— para que sepas a quién pedirle la actualización. A los no administradores nunca se les consulta automáticamente.

### ✨ Novedades tras una actualización {: #whats-new }

Cuando LibreFolio se ha actualizado desde tu última visita, la próxima vez que lo abras, una
ventana **Novedades de LibreFolio** muestra qué ha cambiado: la parte del registro de cambios correspondiente a cada versión
publicada desde la última que viste. Si tu cuenta es más antigua que esta ventana, muestra la parte de
la versión que se está ejecutando ahora.

- Cada parte está en el idioma de tu interfaz cuando su traducción está lista; de lo contrario, está en inglés,
  marcada como **Aún no traducida**, como en el registro de cambios.
- **Registro de cambios completo** abre el registro de cambios completo en GitHub, en una nueva pestaña.
- **Entendido** cierra la ventana, y lo mismo hacen <kbd>Esc</kbd> y un clic fuera de ella. No vuelve a aparecer
  hasta la próxima actualización. Si LibreFolio no puede registrar que la has cerrado, por ejemplo, porque
  se perdió la conexión, la ventana vuelve a mostrarse la próxima vez que abras LibreFolio.
- Espera hasta que no haya ninguna guía ni otra ventana abierta, y aparece antes que la
  [ventana emergente de donación](#donation-popup) y el aviso de actualización.
- Una cuenta nueva nunca la ve: empieza con la versión con la que se creó.

---

## 🔗 Relacionado

- ⚙️ **[Resumen de configuración](index.md)** — Resumen de la configuración general
- 👤 **[Perfil](profile.md)** — Nombre de usuario, correo electrónico, avatar, contraseña
- 🎛️ **[Preferencias del usuario](preferences.md)** — Idioma, moneda base y tema
- 🛡️ **[Configuración global](../../admin/settings.md)** — Opciones del administrador y planificador
