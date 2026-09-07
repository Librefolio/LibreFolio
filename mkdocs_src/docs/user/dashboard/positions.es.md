# 🔍 Posiciones y Análisis

La pestaña **Posiciones** del panel de control le permite inspeccionar las posiciones abiertas, analizar el rendimiento y profundizar en los lotes fiscales coincidentes.

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Posiciones (Tabla)" alt="Vista de Tabla de Posiciones">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Posiciones (Mapa / Treemap)" alt="Vista de Mapa de Posiciones">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Rendimiento (Tabla)" alt="Vista de Tabla de Rendimiento">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Rendimiento (Mapa / Gráfico)" alt="Vista de Mapa de Rendimiento">
</div>

---

## 🔍 Pestaña de Posiciones

La pestaña **Posiciones** tiene dos modos semánticos: **Posiciones** y **Rendimiento**.

Usa el conmutador de vista para alternar entre ambos, y el de tabla/mapa para cambiar la presentación visual.

#### 📋 Vista de Posiciones

La vista **Posiciones** muestra la instantánea de las posiciones abiertas. La tabla tiene 13 columnas:

| Columna | Descripción |
|:---|:---|
| **Activo** | Nombre del activo con el icono del tipo — haz clic para abrir la página de detalle del activo. |
| **Δ1** | Variación del P&L no realizado respecto a ayer, manteniendo constante la cantidad de hoy. |
| **Δ1%** | La misma variación diaria como porcentaje del valor de mercado de la posición de ayer. |
| **P&L no realizado** | Ganancia/pérdida abierta: valor actual menos el coste residual. |
| **P&L %** | P&L no realizado como porcentaje del coste residual. |
| **Anualizado** | Rendimiento neto anualizado (CAGR) de los lotes aún abiertos, desde la primera transacción hasta hoy — para comparar posiciones mantenidas durante periodos distintos. |
| **Valor** | Valor total a precios de mercado actuales (\(\text{Precio} \times \text{Cantidad}\)). |
| **Peso** | Cuota proporcional de esta posición respecto al valor total de la cartera. |
| **Cant.** | Acciones, unidades o monedas actualmente mantenidas. |
| **Brókers** | Cuenta(s) de bróker que mantienen la posición. |
| **Precio** *(oculta por defecto)* | Precio actual del activo del proveedor conectado. |
| **Coste Medio** *(oculta por defecto)* | Coste medio por unidad de la posición actualmente abierta (Precio Medio de Compra). |
| **Lote abierto más antiguo** *(oculta por defecto)* | Fecha de apertura del lote FIFO más antiguo aún abierto para esta posición. |

Usa el **icono de ojo** en la barra de herramientas de la tabla para mostrar u ocultar columnas — tus elecciones se recuerdan entre sesiones.

#### 📈 Vista de Rendimiento

La vista **Rendimiento** se carga bajo demanda y muestra juntas las posiciones abiertas y cerradas. En la tabla/mapa, el **Estado** es filtrable dentro del componente, no como conmutador de primer nivel.

#### 🗺️ Estilo Visual: Tabla vs. Mapa

| Modo Visual | Características Principales | Caso de Uso Óptimo |
|:---|:---|:---|
| **📋 Vista de Tabla** | • Cuadrícula ordenable<br>• Valores numéricos precisos<br>• Ordenación rápida de columnas | Contabilidad estándar, búsqueda de cantidades específicas de activos o comparación de valores PMP. |
| **🗺️ Vista de Mapa** | • Visualización de Treemap<br>• El tamaño indica el peso del activo<br>• La intensidad del color indica el rendimiento (verde = ganancia, rojo = pérdida) | Diagnóstico visual rápido, detección de sobre-asignación o identificación de activos de bajo rendimiento. |

---

## 🔬 Análisis de Lotes FIFO {: #fifo-lots-analysis }

Cuando hace clic en una posición, ya sea en la vista de Tabla o de Mapa, LibreFolio expande un panel de **Análisis de Lotes FIFO** en línea directamente **debajo** de la vista de Posiciones. Utiliza una transición de deslizamiento vertical y se desplaza automáticamente a la vista — **no** es un deslizamiento lateral derecho. Si es necesario, primero aparece un banner de calidad de datos, luego los bloques de análisis permanecen en este orden: PMP / Precio de Mercado, Vida del Lote y Custodia, tabla de lotes unificada, comparación de Valor / Rendimiento y el modal de detalle del lote. Por defecto, sin una selección explícita, significa que **todos los lotes actualmente visibles** están incluidos en los gráficos vinculados.

<div class="lf-screenshot-carousel" data-carousel="carousel-fifo-lots-analysis" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="fifo-lots-panel" data-title="🔍 Descripción General" alt="Descripción General del Análisis de Lotes FIFO">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-wac-chart" data-title="📈 PMP / Precio de Mercado" alt="Gráfico de PMP y Precio de Mercado">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-gantt-chart" data-title="🕒 Vida del Lote y Custodia" alt="Gráfico Gantt de Vida del Lote y Custodia">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-table" data-title="📋 Tabla de Lotes Unificada" alt="Tabla de Lotes Unificada">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart" data-title="💰 Comparación de Valor" alt="Gráfico de Comparación de Valor">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-comparison-chart-return" data-title="📊 Comparación de Rendimiento" alt="Gráfico de Comparación de Rendimiento">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="fifo-lots-custody-modal" data-title="🧾 Modal de Detalle del Lote" alt="Modal de Detalle del Lote">
</div>

### 1. PMP / Precio de Mercado

Este primer gráfico compara el **Precio de Mercado** del activo con las líneas de **PMP** por bróker y la línea de PMP combinada para la posición seleccionada.

- Alterne **ABS / %** para cambiar entre precios absolutos y la evolución porcentual desde el inicio del rango.
- En modo **ABS**, alterne **Auto / Desde 0** para elegir si el eje Y se ajusta estrechamente o se fuerza a comenzar en cero.
- Los marcadores de eventos y las burbujas de rendimiento de lotes le ayudan a conectar compras, ventas, transferencias, divisiones y eventos de ingresos con el historial de la base de costo.
- Al hacer clic en las burbujas de lote, se actualiza la selección de lote compartida utilizada por los otros bloques.
- **El color de la burbuja** coincide con el **bróker de apertura** del lote — los mismos colores utilizados por las barras de custodia en el bloque 2 a continuación.
- **El tamaño de la burbuja** refleja el **valor de apertura** del lote (su base de costo original): las burbujas más grandes comenzaron como inversiones más grandes.
- Un **borde de burbuja discontinuo** marca un lote que actualmente se muestra **al costo** porque aún no tiene un precio de mercado en vivo disponible.

🔗 **Teoría**: Consulte **[Precio Medio Ponderado (PMP)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** para conocer las reglas de la base de costo, y **[Cadena de Precios de Valoración](../../financial-theory/technical-analysis/performance-metrics/portfolio-engine/nav.md#valuation-price-chain)** para entender cómo se resuelven los precios de mercado.

### 2. Vida del Lote y Custodia

El bloque **Vida del lote y custodia** es una línea de tiempo de estilo Gantt que muestra cuándo estuvo abierto cada lote y dónde se mantuvo a lo largo del tiempo.

- Use el filtro **Abierto / Cerrado** para mostrar solo lotes abiertos, solo lotes cerrados o ambos.
- Cada barra representa la vida de un lote; las transferencias crean carriles de custodia adicionales para que pueda ver los movimientos entre brókeres y los períodos en tránsito.
- **El color de la barra** identifica el **bróker de custodia** que actualmente posee ese segmento del lote — las insignias de bróker coincidentes se enumeran en la leyenda debajo del gráfico. Un segmento violeta discontinuo marca un período **en tránsito** entre brókeres (transferencia iniciada pero aún no recibida).
- **El grosor de la barra** es proporcional a la **cantidad mantenida** durante ese segmento exacto — un lote que se vendió o dividió parcialmente muestra barras más delgadas después.
- Al hacer clic en una barra, se selecciona ese lote en el análisis compartido; al hacer doble clic, puede saltar a la fila correspondiente en la tabla.

🔗 **Teoría**: Consulte **[Motor FIFO — Ciclo de Vida del Lote y Modelo de Coincidencia](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/index.md)** para conocer cómo se definen los estados de los lotes, las divisiones y las transferencias entre brókeres.

### 3. Tabla de Lotes Unificada

v3 reemplaza las antiguas tablas separadas de **Lotes Abiertos** y **Lotes Cerrados** con una **tabla unificada**.

- La tabla muestra el conjunto de lotes actual con columnas como fecha de apertura, rendimiento total, valor actual, custodia y **Estado**.
- El filtrado compartido significa que la tabla siempre refleja el mismo conjunto de lotes visibles que los gráficos anteriores.
- El menú **Acciones** de cada fila incluye:
 - **Ver detalle del lote**
 - **Ir al lote en el Gantt**
 - **Ir a la transacción de apertura**
 - **Copiar identificador del lote**

### 4. Comparación de Valor / Rendimiento

Este gráfico de comparación se centra en los lotes actualmente seleccionados en el panel. Si no ha seleccionado lotes específicos, utiliza **todos los lotes visibles**.

- Cambie entre **Valor** y **Rendimiento** usando el selector de modo en la parte superior derecha.
- El modo **Valor** compara los lotes seleccionados en términos monetarios absolutos y también ofrece la alternancia del eje Y **Auto / Desde 0**.
- El modo **Rendimiento** compara el porcentaje de rendimiento desde la fecha de apertura de cada lote en el mismo conjunto de lotes seleccionados.

### 5. Modal de Detalle del Lote

Elija **Ver detalle del lote** en las acciones de la fila de la tabla para abrir el modal **Detalle del Lote FIFO** para un lote específico.

- El resumen incluye **PyG Total**, **Rendimiento total**, **Ingresos del activo**, **Rendimiento en efectivo**, PyG FIFO, valor de apertura/actual y otras métricas a nivel de lote.
- **Custodia Actual** muestra cómo se distribuye actualmente el lote entre los brókeres o en porciones en tránsito.
- **Historial** enumera la cronología completa de custodia y ciclo de vida, incluidas transferencias y otros eventos del lote, con una acción directa **Ir a la transacción** para la transacción relevante.

!!! info "Lógica de coincidencia FIFO"

    LibreFolio resuelve los cierres de lotes estrictamente con la coincidencia de **Primero en Entrar, Primero en Salir (FIFO)**: las cantidades de venta siempre consumen primero el **lote abierto elegible más antiguo** antes de tocar los lotes más nuevos.

    Para una teoría y fórmulas más profundas, consulte:

    - **[Teoría de Impuestos](../../financial-theory/fundamentals/taxation.md)**
    - **[Modelo de Transacción de Compra/Venta](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching)**
    - **[Análisis de Lotes FIFO](../../financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md)**

---

## 💸 Pestaña de Transacciones

La pestaña **Transacciones** en el Panel de Control muestra una lista completa y paginada de todas las operaciones registradas en el ámbito de la cartera activa (órdenes de compra/venta, pagos de dividendos, depósitos en efectivo, transferencias, etc.).

Para una explicación detallada de la lista de transacciones, los filtros y cómo leer los detalles de la transacción de solo lectura, consulte la página dedicada **[Descripción General de Transacciones](../transactions/index.md)**.

---

*[⬅️ Volver a la Descripción General del Panel de Control](index.md)*
