# ℹ️ Acerca de

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="about" alt="Acerca de">
</div>

La pestaña **Acerca de** muestra:

- La **versión** actual de LibreFolio
- La **licencia** (AGPL-3.0)
- Enlaces al **repositorio de GitHub** y a la **documentación**
- Una cuadrícula de **información del sistema** (versión de Python, sistema operativo, modo de despliegue — Docker o local — navegador, viewport, tema e idioma) con un botón **copiar para incidencia** que empaqueta estos detalles en un informe de error listo para pegar
- Los **plugins instalados**: listas plegables de los proveedores de precios de activos, proveedores de tipos de cambio (FX), plugins de importación de brókeres e indicadores de señales detectados al inicio

---

## 🧩 Diagnóstico de plugins

El panel plegable **Diagnóstico de plugins** informa del estado de los cuatro registros de plugins: **proveedores de activos**, **proveedores de FX**, **importadores de brókeres** e **indicadores de señales**.

Cada registro se marca como **todos cargados** (en verde) o enumera los **plugins que no se pudieron importar** (en rojo), con el nombre del archivo y el error subyacente. Si falta un proveedor, importador o indicador que esperabas en el resto de la aplicación, este panel te explica por qué: un plugin que no se carga al inicio simplemente no se registra.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="about-plugin-diagnostics" alt="Panel plegable de diagnóstico de plugins en la pestaña Acerca de">
</div>

---

## 📜 Modal de registro de cambios {: #changelog-modal }

El **modal de registro de cambios** de la aplicación renderiza el `CHANGELOG.md` incluido. Puedes acceder a él desde dos lugares:

- el **número de versión en la parte inferior de la barra lateral** (en cualquier página), y
- la **etiqueta de versión justo debajo del título de esta página Acerca de** (Configuración → Acerca de).

- Un **panel plegable por versión**: solo la versión más reciente comienza abierta; las secciones y subsecciones también se pliegan.
- Un **índice de versiones** con chips en la parte superior: al hacer clic en una versión, se despliega y se desplaza directamente hasta ella.
- Un **cuadro de búsqueda** que desciende entre los pliegues: las secciones coincidentes se abren automáticamente y los chips de resultados clicables saltan al lugar exacto.
<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="changelog-modal-search" alt="Búsqueda en el modal de registro de cambios que abre los pliegues coincidentes">
</div>

- Botones de **expandir todo / contraer todo** y un enlace al archivo de registro de cambios en GitHub.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="changelog-modal" alt="Modal de registro de cambios con versiones plegables y búsqueda">
</div>

### 🔄 Comprobación de actualizaciones

El encabezado del modal también tiene un botón **comprobar actualizaciones**, que consulta en GitHub la última versión estable disponible. Lo que ocurre a continuación depende de tu rol:

- Si LibreFolio está **actualizado**, aparece una notificación de confirmación.
- Si existe una versión más reciente y eres **administrador**, se abre el **modal de actualización disponible**: las versiones actual y más reciente, una al lado de la otra, con enlaces a la [guía de actualización](../installation.md#updating) y a la página de lanzamiento en GitHub. Puedes descartarlo con **Más tarde** (se te recordará en el próximo inicio de sesión) o con **Omitir esta versión** (no se te volverá a preguntar por esa versión). A los administradores también se les realiza la comprobación automáticamente al iniciar sesión — consulta [Notificaciones de actualización](../../admin/index.md#update-notifications) para ver el flujo del lado del administrador.
- Si existe una versión más reciente y **no eres administrador**, un cuadro de diálogo enumera los **administradores** de la instancia — con direcciones de correo electrónico cuando estén disponibles, cada uno de ellos con un enlace mailto y un botón de copia — para que sepas a quién pedir la actualización. A los no administradores nunca se les realiza la comprobación automáticamente.

---

## 🔗 Relacionados

- ⚙️ **[Descripción general de configuración](index.md)** — Resumen de la configuración general
- 👤 **[Perfil](profile.md)** — Nombre de usuario, correo electrónico, avatar, contraseña
- 🎛️ **[Preferencias de usuario](preferences.md)** — Idioma, moneda base y tema
- 🛡️ **[Configuración global](../../admin/settings.md)** — Opciones de administrador y planificador
