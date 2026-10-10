# 🎛️ Preferencias de usuario

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="Preferencias de usuario">
</div>

La pestaña **Preferencias** controla **cómo se ve y se comporta la aplicación para ti** — los cambios se aplican solo a tu cuenta. Tu identidad (nombre de usuario, correo electrónico, avatar, contraseña) se encuentran, en cambio, en la pestaña **[Perfil](profile.md)**.

| Ajuste | Categoría | Descripción |
|---------|----------|-------------|
| **Idioma** | 🌍 Visualización | Idioma de la interfaz — 🇬🇧 English, 🇮🇹 Italiano, 🇫🇷 Français, 🇪🇸 Español. Se aplica en cuanto lo guardas |
| **Divisa predeterminada** | 💰 Divisa | Tu propia divisa base. El Panel, la página de Brókers y la página de cada bróker, y la pestaña **Correlación** de la página de Activos se abren en ella, y la Exportación IA de un par de divisas también la usa; una divisa que elijas en el Panel se mantiene durante la sesión. También se propone cuando creas algo nuevo — un activo, el primer saldo de efectivo de un bróker nuevo, un plan PAC. Este menú enumera todas las divisas |
| **Tema** | 🎨 Apariencia | ☀️ Claro / 🌙 Oscuro / 🖥️ Auto (sigue tu sistema operativo) |

<style>
/* Keep the first two columns on one line (long setting names would wrap otherwise) */
article table:first-of-type th:nth-child(-n + 2),
article table:first-of-type td:nth-child(-n + 2) {
    white-space: nowrap;
    min-width: 11rem;
}
</style>

Elige una categoría en la barra lateral — en un teléfono, en el menú **Categoría** — para mostrar solo su configuración;
**Toda la configuración** muestra todo.

!!! tip "Menús de divisas en el Panel y en las páginas de activos"

    Los menús de divisas del **Panel** y de una página de activo son más cortos que **Divisa predeterminada**: ofrecen solo las divisas de tus pares FX, y **Crear forex…** al final de la lista añade un par que falte. Consulta **[Panel](../dashboard/index.md)**.

## 💾 Guardar, deshacer, restablecer

Cada campo conserva su propio estado:

- Cambia un campo y aparecen **Guardar** y **Deshacer**; el encabezado ofrece **Guardar todo** y **Deshacer todo**
  para cada campo modificado.
- Cuando un valor guardado difiere del **valor predeterminado de la instancia** (establecido por tu administrador en
  [Configuración global](../../admin/settings.md)), aparece un botón naranja **Restablecer al valor predeterminado**: devuelve
  el valor predeterminado al campo, listo para guardar. **Restablecer todo a los valores predeterminados** lo hace para cada
  campo.

---

## 🧭 Introducción y guías {: #onboarding-and-guides }

La categoría **Introducción** enumera todas las guías, agrupadas según dónde aparecen. Cada una muestra su
estado — **Pendiente**, **Completada** u **Omitida** — y la versión que has visto.
**Nueva versión para ver** significa que hay contenido actualizado en espera: la guía se inicia de nuevo la próxima vez que
llegues a ella.

| Grupo | Guías |
|---|---|
| **Configuración** | Configuración de bienvenida |
| **Recorrido principal** | Recorrido rápido |
| **Transacciones** | Resumen de transacciones, Guía para añadir transacciones, Resumen del espacio de trabajo masivo, Guía de importación |
| **Brókers** | Resumen de brókers, Guía de brókers, Guía de detalles del bróker |
| **FX** | Resumen de FX, Guía de FX, Guía de detalles del par FX |
| **Activos** | Resumen de activos, Guía de activos, Guía de detalles del activo |

### 🔁 Repetir una guía

- **Configuración de bienvenida** y **Recorrido rápido** — **Repetir** las inicia de inmediato.
- Cualquier otra guía — **Repetir en el próximo desencadenante** la deja lista: se inicia la próxima vez que abras su
  página, formulario, asistente o espacio de trabajo. **Cancelar activación** lo revierte.
- **Repetir todo** deja lista cada guía y abre primero la página de Bienvenida.

Una repetición nunca cambia el estado guardado, y las guías nunca hacen clic ni guardan por ti. Una excepción: en
una repetición de Bienvenida, **Continuar** guarda el idioma, la divisa y la imagen que elegiste (**Salir del recorrido**
sale sin guardar).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="settings" data-name="onboarding-replay" alt="La categoría Introducción de Preferencias: Introducción y guías con Repetir todo; Configuración y Recorrido principal abiertos, cada guía con su insignia Completada, Vista v1 · actual v1 y Repetir; las demás áreas plegadas con sus recuentos">
</div>

??? info "🧩 Guía de importación y Resumen del espacio de trabajo masivo — guías con pasos"

    Expande la fila de cualquiera de las dos guías para ver cada paso con su propio estado. Un paso de importación opcional
    (**Unificar activos**, **Correcciones**, **Duplicados**, **Alinear con el banco**) permanece **Pendiente**
    hasta que una importación lo necesite por primera vez.

    En estas dos guías, **✕** omite solo el paso actual: el siguiente se inicia cuando el asistente o
    el espacio de trabajo llega a él. En una repetición, **✕** elimina el paso de la repetición sin cambiar
    su estado guardado.

??? note "💾 Dónde se guarda una repetición — solo en este navegador"

    Una repetición se guarda en este navegador, para tu cuenta: una a medias sobrevive a una recarga,
    al cierre del navegador o a cerrar sesión y volver a iniciarla. No se comparte con otras cuentas,
    navegadores o dispositivos. Termina cuando la finalizas o sales de ella, la cancelas aquí, o una actualización trae una
    versión más reciente de la guía — y entonces también se cierra en tus otras pestañas abiertas.

Si la lista de guías no se puede cargar, esta sección muestra su propio botón **Reintentar**.

---

## 🙈 Modo privacidad {: #privacy-mode }

El modo privacidad oculta cuánto posees mientras otra persona puede ver tu pantalla — un compañero que pasa
por detrás, una pantalla compartida, un proyector. No es un campo de esta pestaña: es el **botón del ojo** en el
encabezado de la página, arriba a la derecha, junto a los botones de tema e idioma.

- :material-eye-outline: **Ocultar importes** — los importes son visibles; haz clic para ocultarlos.
- :material-eye-off-outline: **Mostrar importes** — el modo privacidad está activado; haz clic para mostrar de nuevo los importes.

El cambio se aplica de inmediato a la página en la que estás, sin recargarla, y el modo privacidad permanece activado mientras
te mueves entre páginas y después de una recarga, hasta que lo desactives. No debe confundirse con el icono del ojo
de la **barra de herramientas de una tabla**, que muestra u oculta columnas de la tabla.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="dashboard" data-name="privacy-masked" alt="El Panel con el modo privacidad activado: el botón del ojo tachado en el encabezado, los importes de las tarjetas KPI y de los Saldos de efectivo mostrados como ••• con su signo y divisa, los porcentajes aún legibles, y el eje de Crecimiento de la cartera enmascarado">
</div>

### 🔒 Qué se oculta

El modo privacidad sustituye el **número** de un importe por `•••`. La divisa siempre permanece, y también
el signo, de modo que una ganancia sigue leyéndose como ganancia y una pérdida como pérdida:

| Normalmente | Con el modo privacidad |
|---|---|
| `1,234.56 € 🇪🇺 EUR` | `••• € 🇪🇺 EUR` |
| `-1,234.56 € 🇪🇺 EUR` | `-••• € 🇪🇺 EUR` |
| `€1,234.56` o `1.234,56 €` | `€•••` o `••• €` |
| `—` (sin valor) | `—` |

`•••` son siempre los mismos tres puntos — incluso la **K** o la **M** de una cifra abreviada desaparece — de modo que
nunca revela el orden de magnitud. Cubre:

- **Panel**, **Brókers** y los **paneles de riesgo** — sus importes: las tarjetas KPI, los Saldos de efectivo,
  la información emergente de Asignación, las tarjetas de bróker y la página de detalles del bróker.
- **[Posiciones](../dashboard/positions.md)** y
  **[Análisis de lotes FIFO](../dashboard/positions.md#fifo-lots-analysis)** — cada importe excepto los
  precios por unidad, en las tablas, el modal de Detalle del lote y los gráficos, y las cantidades que posees
  (la columna **Cant.** de Posiciones, las cantidades de los lotes). Un lote parcialmente cerrado muestra su parte abierta, por
  ejemplo `••• (60%)`.
- **Transacciones** — el importe en efectivo de cada transacción.
- **[Asignador PAC](../tools/pac-allocator/index.md#reading-the-result)** — cada importe y
  cantidad del resultado, y los límites de compra de una ruta.

### 👀 Qué permanece visible

Los números que no indican **cuánto posees** siguen siendo legibles, para que puedas seguir trabajando:

- la **divisa** de cada importe oculto, los **porcentajes** (rentabilidades, ponderaciones, cuotas de asignación,
  rendimiento sobre coste) y los **tipos de cambio**;
- los **precios por unidad** — precios de mercado, las columnas **Precio** y **Coste medio** de Posiciones, los
  precios de los lotes y las líneas de precio del gráfico PMC / Precio de mercado;
- los **recuentos, fechas y nombres**, y los **eventos de activos** como un dividendo o un desdoblamiento, que describen
  el activo más que tu cartera;
- las **cantidades en la lista de Transacciones** — una elección deliberada, aunque una cantidad multiplicada
  por el precio público insinúe el tamaño de una operación;
- los números dentro de los **campos de edición**, por ejemplo mientras añades o editas una transacción: un campo que
  no puedes leer es un campo que no puedes editar.

### 🌐 Dónde se guarda el ajuste

El modo privacidad pertenece a **este navegador**, no a tu cuenta: tiene que ver con la pantalla que alguien
puede estar mirando.

- Está desactivado hasta que lo activas. Cerrar sesión o cambiar de cuenta lo deja tal como está, y no
  te sigue a otro navegador o dispositivo.
- Otras pestañas de LibreFolio ya abiertas en este navegador recogen el cambio cuando las recargas.
- Si el navegador bloquea el almacenamiento del sitio, el modo privacidad sigue funcionando en esta pestaña, pero puede estar desactivado de nuevo
  tras una recarga.

!!! warning "Qué no cubre el modo privacidad"

    - La **[Exportación IA](../ai-export/index.md)** copia las cifras reales al portapapeles incluso con
      el modo privacidad activado. Revisa el texto antes de compartirlo.
    - Las **descargas y los archivos exportados** contienen las cifras reales.
    - Oculta lo que se **dibuja en la pantalla**. Las cifras siguen llegando a tu navegador, así que no es
      una protección contra alguien que pueda usar tu dispositivo o sus herramientas de desarrollo.
    - Algunas cifras aún pueden **deducirse**: el signo distingue una ganancia de una pérdida, y cuando posees
      una sola unidad de un activo, su precio visible es su valor.

---

## 🔗 Relacionado

- 👤 **[Perfil](profile.md)** — Nombre de usuario, correo electrónico, avatar, contraseña, eliminar cuenta
- ⚙️ **[Resumen de configuración](index.md)** — Resumen de la configuración general
- ℹ️ **[Acerca de](about.md)** — Información de versión, plugins y registro de cambios
- 🛡️ **[Configuración global](../../admin/settings.md)** — Opciones de administrador y planificador
- 🛠️ **[Componentes de configuración](../../developer/frontend/components/features/settings.md)** — Cómo se construyen esta pestaña y su lista de Introducción (para desarrolladores)
