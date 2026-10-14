# 🔍 Página de detalle del activo

Haz clic en un activo en la [página de Activos](../index.md) para abrir su propia página: su historial de precios, las herramientas para analizarlo y los datos que hay detrás.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Página de detalle del activo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

La página tiene dos pestañas: **Resumen**, descrito a continuación, y **Riesgo y escenarios**.

!!! info "Beta"

    La pestaña **Riesgo y escenarios** todavía está en beta: se abre con el aviso *El análisis de riesgos está en beta.* y aún no está cubierta por esta documentación.

---

## 🧭 Qué muestra el Resumen

De arriba a abajo:

### 📊 [Señales](signals.md)

Dibuja cualquiera de los **22 indicadores técnicos**, otro activo o par de divisas, o una curva de referencia sobre el gráfico.

### 📈 [Gráfico interactivo](chart.md)

El historial de precios, o el **[Rendimiento móvil](chart.md#rolling-return)** en una ventana que elijas (1 sem., 1 mes, 3 meses, 1 año o una duración personalizada). Haz zoom, desplázate y conviértelo a otra divisa.

### ✏️ [Editor de datos](data-editor.md)

Añade, corrige o elimina precios y eventos, uno a uno o desde un archivo CSV.

### 📐 [Medidas](measures.md)

Haz clic en dos puntos del gráfico para leer la variación entre ellos.

### 🗂️ [Clasificación](classification.md)

El desglose por sector y país, en el panel **Metadatos y clasificación**.

### 📅 [Eventos](events.md)

Dividendos, desdoblamientos, interés y otros eventos del activo, dibujados como marcadores en el gráfico.

---

## 🔧 Encabezado y barra de herramientas

- **←** vuelve a la lista, o a la página desde la que viniste, en un solo paso, incluso después de navegar con las flechas.
- **El activo** — un punto (verde activo, rojo archivado), su nombre, tipo y divisa, un enlace **Transacciones (N)** cuando tiene alguna transacción, su proveedor (o **✏️ Manual**), y un enlace a su página web: la que definiste en el activo o, si no, la del proveedor.
- **‹ n/N ›** — el activo anterior o siguiente, manteniendo las mismas fechas (consulta el panel de abajo).
- **Rango de fechas** y **Convertir a** — el periodo y la divisa del [gráfico](chart.md).
- **Exportación IA** — copia los datos del activo para un asistente de IA ([Exportación IA de un activo](../../ai-export/asset.md)).
- **Editar** (✏️) — abre el formulario del activo ([Crear y editar](../create-edit.md)).
- **Sincronizar** (🔄) — descarga los últimos precios, junto con los de los activos comparados y los tipos de cambio que necesita el gráfico; se muestra como **Recalcular** para una inversión programada. No está disponible para un activo sin proveedor ni para uno archivado.
- **Recargar** (↻) — recarga los datos de la página a partir de lo que LibreFolio tiene almacenado.

??? info "🧭 Qué orden siguen las flechas ‹ ›"

    - **Abierto desde la página de Activos**: la lista tal como la dejaste — su búsqueda, sus filtros, la vista de cuadrícula o de tabla y, en la tabla, su ordenación y sus filtros de columna.
    - **Abierto de cualquier otra forma** (un enlace o marcador, una recarga, el panel, Transacciones…), o para un activo que esa lista no muestra: todos los activos en el orden predeterminado de la página de Activos, y los archivados solo cuando el activo que abriste está archivado.
    - El contador (por ejemplo, 3/12) muestra dónde estás. Las flechas se detienen en ambos extremos y desaparecen cuando solo hay un activo que explorar.

---

## 🔗 Relacionado

- ➕ **[Crear y editar](../create-edit.md)** — Crear y configurar activos
- 📋 **[Resumen de activos](../index.md)** — Volver a la lista de activos
