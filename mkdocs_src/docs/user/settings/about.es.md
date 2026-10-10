# ℹ️ Acerca de

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about" alt="About">
</div>

La pestaña **Acerca de** muestra:

- La **versión** actual de LibreFolio
- La **licencia** (AGPL-3.0)
- Enlaces al **repositorio de GitHub** y a la **documentación**
- Una tarjeta **Apoya a LibreFolio** con el enlace del café y los botones para compartir — consulta [Apoya a LibreFolio](#support-librefolio) más abajo
- Una cuadrícula de **información del sistema** (versión de Python, sistema operativo, modo de despliegue — Docker o local — navegador, viewport, tema e idioma) con un botón de **copiar para incidencia** que empaqueta estos detalles en un informe de error listo para pegar
- Los **plugins instalados**: listas plegables de los proveedores de precios de activos, proveedores de tipos de cambio (FX), plugins de importación de brókers e indicadores de señales detectados al iniciar, seguidas de los **Diagnóstico de plugins**

---

## ❤️ Apoya a LibreFolio {: #support-librefolio }

La tarjeta **Apoya a LibreFolio** ofrece dos formas de ayudar al proyecto:

- **Buy Me a Coffee** abre la página de Buy Me a Coffee del proyecto en una nueva pestaña. El mismo enlace está en
  el encabezado de la página (el icono del café, con su etiqueta en pantallas más anchas) y en el
  menú **Ayuda y soporte**.
- Bajo **O comparte**, un botón por red social: **X**, **Reddit**, **Facebook**,
  **Instagram** y **TikTok**.

Un botón para compartir abre un diálogo **Compartir en …** con un **Mensaje sugerido** redactado para esa
red, en el idioma de la interfaz. Sea cual sea el idioma, todos los mensajes terminan con los
mismos cinco hashtags: `#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance`.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="social-share-modal" alt="Diálogo Compartir en Reddit con el título sugerido, un mensaje que termina con los cinco hashtags, y Copiar y abrir">
</div>

**Copiar y abrir** copia el mensaje, seguido del enlace al sitio web público del proyecto, y
abre la red social en una nueva pestaña: LibreFolio permanece abierto en su propia pestaña. Cada red acepta
una cantidad distinta de contenido preparado, y el diálogo explica qué esperar antes de que hagas clic:

| Red | Qué se abre |
|---|---|
| **X** | Una nueva publicación con el mensaje y el enlace del proyecto ya rellenados. |
| **Reddit** | Una nueva publicación de texto, con el **Título sugerido** como título y el mensaje como cuerpo. Si Reddit deja el cuerpo vacío, pega el texto que acabas de copiar. |
| **Facebook** | Una publicación solo con la vista previa del enlace: pega el texto copiado en el mensaje de la publicación. |
| **Instagram** | Instagram en sí, que no puede preparar una publicación a partir de un enlace: elige **Crear** (+), selecciona una foto o un vídeo y luego pega el pie de foto copiado. |
| **TikTok** | La página de subida de TikTok (inicia sesión si te lo pide): selecciona tu vídeo y luego pega el pie de foto copiado. |

Si el texto no se puede copiar, el diálogo lo indica y te pide que permitas el acceso al portapapeles. Si el
navegador bloquea la nueva pestaña, el diálogo indica que el texto se ha copiado pero que el sitio no se ha podido
abrir, y te pide que permitas las ventanas emergentes. LibreFolio nunca publica nada por ti: la publicación es
tuya para revisarla y publicarla en la red social.

### ☕ La ventana emergente de donación {: #donation-popup }

De vez en cuando, justo después de iniciar sesión, LibreFolio te recuerda que puedes apoyar al
proyecto, con el mismo enlace del café y los botones para compartir.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="support" data-name="donation-popup" alt="Ventana emergente de donación tras iniciar sesión, con Buy Me a Coffee, los cinco botones para compartir y Más tarde">
</div>

---

## 🧩 Diagnóstico de plugins

El desplegable **Diagnóstico de plugins** informa del estado de los cuatro registros de plugins — **Asset**
(proveedores de precios), **FX** (proveedores de tipos), **BRIM** (importadores de brókers) y **Signals**
(indicadores) — y, debajo de ellos, del de las **Herramientas**.

Cada registro o bien está marcado como **Todo cargado** (verde), o bien enumera los **plugins que no se pudieron importar** (rojo), con el nombre del archivo y el error subyacente. Si falta un proveedor, importador o indicador que esperabas en el resto de la aplicación, este panel te dice por qué: un plugin que no se carga al iniciar simplemente no se registra.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-plugin-diagnostics" alt="Desplegable Diagnóstico de plugins en la pestaña Acerca de">
</div>

### 🧰 Herramientas y diagnósticos de herramientas {: #tool-diagnostics }

Debajo de los registros, el panel **Herramientas** enumera el catálogo de [Herramientas](../tools/index.md). Es
de solo lectura — no se ejecuta ningún cálculo, sondeo ni reparación — y solo se carga cuando abres
**Diagnóstico de plugins**; **Recargar** lo vuelve a leer. Para cada herramienta ves su nombre y descripción,
un enlace a su **Documentación**, su código y `Version: <contract_version>`, y si se incluye una interfaz
compatible en el frontend que estás ejecutando. La versión de implementación no se muestra
aquí, y el par de versiones `Backend/API · UI` solo aparece en las tarjetas de la página de Herramientas y en la
cabecera de una herramienta abierta.

Abre **Diagnósticos de herramientas** para cargar una instantánea del proceso del servidor que respondió:

- el **Alcance de la instantánea** y el **identificador del proceso de la API**;
- la **Instantánea del grupo de ejecución**: si el grupo está disponible, los trabajos activos, en cola, pendientes,
  completados y fallidos, y los carriles degradados;
- las **Herramientas cargadas en este proceso de la API**, cada una con su nombre, código y versión del contrato, y
  los posibles **Fallos de descubrimiento**;
- los **Límites efectivos de la plataforma**, en su propio desplegable.

La instantánea describe un único proceso del servidor, no toda la instancia, y no se actualiza por sí sola:
recárgala para volver a leerla.

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="about-tool-diagnostics" alt="Panel Herramientas en Diagnóstico de plugins, con el Asignador PAC y Diagnósticos de herramientas abiertos">
</div>

---

## 📜 Modal del registro de cambios {: #changelog-modal }

El **modal del registro de cambios** integrado en la aplicación renderiza el archivo `CHANGELOG.md` incluido. Puedes acceder a él desde dos lugares:

- el **número de versión en la parte inferior de la barra lateral** (en cualquier página), y
- la **etiqueta de versión justo debajo del título de esta página Acerca de** (Configuración → Acerca de).

- Un **panel plegable por versión** — solo la versión más reciente se abre de inicio; las secciones y subsecciones también se pliegan.
- Un **índice de versiones** con chips en la parte superior: al hacer clic en una versión se despliega y se desplaza directamente hasta ella.
- Un **cuadro de búsqueda** que desciende por los pliegues: las secciones coincidentes se abren automáticamente, y los chips de resultados en los que se puede hacer clic saltan al punto exacto.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal-search" alt="Búsqueda en el modal Registro de cambios, que abre las secciones correspondientes">
</div>

- Botones de **Expandir todo / Contraer todo**, y un enlace al archivo del registro de cambios en GitHub.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="changelog-modal" alt="Modal Registro de cambios con versiones plegables y búsqueda">
</div>

### 🔄 Buscar actualizaciones

La cabecera del modal también tiene un botón **Buscar actualizaciones**. Pregunta al servidor qué versión se
está ejecutando, vuelve a leer la última versión **estable** desde GitHub (en lugar de reutilizar el resultado
que la comprobación automática conserva durante una hora) y compara las dos. Una versión más reciente solo cuenta
cuando su imagen de Docker está disponible en el registro, así que una versión cuya compilación aún está en curso
todavía no se ofrece — consulta [Notificaciones de actualización](../../admin/index.md#update-notifications).

Una comprobación iniciada aquí siempre te dice cómo ha ido:

- Si LibreFolio está **actualizado**, aparece un aviso de confirmación, con la versión detectada en línea.
- Si GitHub no tiene **ninguna versión estable**, o la **imagen de Docker de una versión más reciente aún no está disponible**,
  un aviso lo indica.
- Si la comprobación **falla** — por ejemplo, cuando no se puede acceder a GitHub o al registro — un error
  te pide que lo intentes de nuevo. Una comprobación fallida nunca informa de que estás actualizado.
- Si existe una versión más reciente y eres **administrador**, el modal **Nueva versión disponible** se abre
  de inmediato, por encima del registro de cambios: las versiones actual y más reciente una al lado de la otra, con **Cómo actualizar**
  (la [guía de actualización](../installation.md#updating)) y **Notas de la versión en GitHub**. Puedes
  descartarla con **Recordármelo más tarde** (se te recordará en el siguiente inicio de sesión) o
  **Omitir esta versión** (la comprobación automática nunca vuelve a avisar de esa versión; una comprobación iniciada
  aquí todavía la muestra). Los administradores también reciben una comprobación automática al iniciar sesión — consulta
  [Notificaciones de actualización](../../admin/index.md#update-notifications) para el flujo del lado del administrador.
- Si existe una versión más reciente y **no eres administrador**, el diálogo **Actualización disponible — contacta con un administrador** enumera los **administradores** de la instancia — con direcciones de correo electrónico cuando están disponibles, cada una con un enlace mailto y un botón de copiar — para que sepas a quién pedirle la actualización. Los no administradores nunca reciben una comprobación automática.

---

## 🔗 Relacionado

- ⚙️ **[Resumen de configuración](index.md)** — Resumen de la configuración general
- 👤 **[Perfil](profile.md)** — Nombre de usuario, correo electrónico, avatar, contraseña
- 🎛️ **[Preferencias del usuario](preferences.md)** — Idioma, moneda base y tema
- 🛡️ **[Configuración global](../../admin/settings.md)** — Opciones de administrador y planificador
