# 🔍 Posiciones y Análisis

*[⬅️ Volver a la Descripción General del Panel de Control](index.md)*

La pestaña **Posiciones** del panel de control te permite inspeccionar las posiciones activas, analizar el rendimiento y profundizar en los lotes fiscales coincidentes.

<div class="lf-screenshot-carousel" data-carousel="carousel-positions-views" data-carousel-interval="6000" data-show-titles="true" style="margin: 1.5rem 0 2.5rem 0;">
 <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="dashboard" data-name="positions-holdings-table" data-title="📋 Posiciones (Tabla)" alt="Vista de Tabla de Posiciones">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-holdings-map" data-title="🗺️ Posiciones (Mapa / Treemap)" alt="Vista de Mapa de Posiciones">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-table" data-title="📈 Rendimiento (Tabla)" alt="Vista de Tabla de Rendimiento">
 <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="dashboard" data-name="positions-performance-map" data-title="📊 Rendimiento (Mapa / Gráfico)" alt="Vista de Mapa de Rendimiento">
</div>

---

## 🔍 Pestaña de Posiciones

La pestaña **Posiciones** proporciona un desglose detallado de todos los instrumentos financieros que actualmente posees en tu cartera (Acciones, ETFs, Bonos, Criptomonedas, etc.).

La pestaña Posiciones le permite cambiar entre dos modos de métricas principales utilizando el interruptor de vista, cada uno centrado en un aspecto diferente de sus posiciones:

#### 📋 Vista de Posiciones (Holdings)

La vista de **Posiciones** (Holdings) se centra en la contabilidad, las cantidades y la valoración actual de los activos. Le ayuda a monitorear la exposición actual de su cartera y las métricas de referencia.

| Métrica | Descripción |
|:---|:---|
| **Cantidad** | Acciones, unidades o monedas actualmente mantenidas en tu cartera. |
| **Precio de Mercado** | Precio del activo en vivo obtenido del proveedor de datos conectado. |
| **Valor de Mercado** | Valor total a precios de mercado actuales (\(\text{Precio} \times \text{Cantidad}\)). |
| **Precio Medio (PMP)** | El Precio Medio Ponderado pagado para adquirir la posición abierta actual. |
| **Peso** | Participación proporcional de este asset en relación con el valor total de la cartera. |

#### 📈 Vista de Rendimiento

La vista de **Rendimiento** se centra en los rendimientos absolutos y relativos. Le ayuda a analizar la rentabilidad de sus posiciones abiertas, teniendo en cuenta las transacciones históricas y los ingresos distribuidos.

| Métrica | Descripción |
|:---|:---|
| **Valor Total** | Valor actual de las posiciones (coincide con el Valor de Mercado). |
| **PyG No Realizada** | Ganancia o pérdida latente calculada como \(\text{Valor de Mercado} - \text{Valor de Costo}\). |
| **% ROI** | Tasa de rendimiento en relación con el costo medio ponderado de la posición. |
| **PyG Total** | Rendimiento absoluto acumulado (incluye ventas cerradas pasadas y dividendos). |

#### 🗺️ Estilo Visual: Tabla vs Mapa

| Modo Visual | Características Principales | Caso de Uso Óptimo |
|:---|:---|:---|
| **📋 Vista de Tabla** | • Diseño de cuadrícula ordenable<br>• Valores numéricos precisos<br>• Ordenación rápida de columnas | Contabilidad estándar, búsqueda de cantidades específicas de activos, o comparación de valores de PMP. |
| **🗺️ Vista de Mapa** | • Visualización de Treemap<br>• El tamaño indica el peso del activo<br>• La intensidad del color indica el rendimiento (verde = ganancia, rojo = pérdida) | Diagnósticos visuales rápidos, detección de sobreponderación, o identificación de activos con bajo rendimiento. |

---

## 🔬 Análisis de Lotes FIFO {: #fifo-lots-analysis }

Cuando haces clic en una posición en la vista de Tabla o Mapa, se despliega un panel de **Análisis de Lotes FIFO** desde el lado derecho de la pantalla. Este panel proporciona un análisis profundo del historial fiscal y de coincidencia de lotes para ese activo específico.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="dashboard" data-name="fifo-lots-panel" alt="Panel de Análisis de Lotes FIFO">
</div>

### 1. Cronología de Burbujas

El gráfico de **Cronología de Burbujas** visualiza todas las compras y ventas durante el período seleccionado:

- 🟢 **Burbujas Verdes**: Representan transacciones de compra. El tamaño de la burbuja representa la cantidad comprada.
- 🔴 **Burbujas Rojas**: Representan transacciones de venta. El tamaño representa la cantidad vendida.
- 🔵 **Línea Azul**: Traza la progresión histórica de tu Precio Medio Ponderado (PMP/Valor contable por acción).
- 🔍 **Información emergente**: Al pasar el cursor sobre cualquier burbuja, se revela la fecha, el tipo de transacción, la cantidad y el precio de la transacción.

### 2. Gráfico de Precio del PMP

Este gráfico superpone la línea del **Precio Medio Ponderado (PMP)** sobre la línea histórica del **Precio de Mercado**. Esto te ayuda a visualizar cuándo compraste en relación con los movimientos del mercado y si tus posiciones actuales están en ganancia o pérdida.

🔗 **Teoría**: Consulta **[Precio Medio Ponderado (PMP)](../../financial-theory/technical-analysis/performance-metrics/weighted-average-cost.md)** para saber cómo se calcula la base de costo, y **[Cadena de Precios de Valoración](../../financial-theory/technical-analysis/performance-metrics/nav.md#valuation-price-chain)** para saber cómo los proveedores de datos resuelven los precios de mercado.

### 3. Tabla de Lotes Abiertos

Muestra los **Lotes Fiscales** activos que están actualmente abiertos (aún no coincididos con una venta). Muestra:

- 📅 **Fecha de Adquisición**: La fecha exacta en que se compraron las acciones.
- 💰 **Precio de Adquisición**: El precio de compra original.
- 📦 **Cantidad restante**: Las acciones de este lote que aún se mantienen.
- 📊 **Valor del Lote**: Valor de mercado actual de este lote específico.
- 📈 **PyG No Realizada**: Ganancia o pérdida específica de esta compra.

### 4. Tabla de Lotes Cerrados

Muestra el historial de **ventas realizadas** donde un lote de compra coincidió con un lote de venta. Ayuda a rastrear:

- 🤝 **Fecha de Coincidencia**: La fecha de venta.
- 📦 **Cantidad coincidente**: Las acciones cerradas.
- 💸 **PyG Realizada**: La ganancia o pérdida final reconocida al coincidir esta compra con la venta.

!!! info "Lógica de coincidencia FIFO"

    LibreFolio resuelve los lotes fiscales siguiendo estrictamente la metodología contable **Primero en Entrar, Primero en Salir (FIFO)**. Las acciones adquiridas más antiguas se emparejan primero con cualquier operación de venta entrante.

    Para una visión teórica detallada de cómo el emparejamiento FIFO se relaciona con el cálculo de plusvalías y los impuestos, consulta **[Teoría sobre Impuestos](../../financial-theory/fundamentals/taxation.md)** y el **[Modelo de Transacción de Compra/Venta](../../financial-theory/instruments/transaction-types/buy-sell.md#fifo-matching)**.

---

## 💸 Pestaña de Transacciones

La pestaña **Transacciones** en el Panel de Control muestra una lista completa y paginada de todas las operaciones registradas dentro del alcance de la cartera activa (órdenes de compra/venta, pagos de dividendos, depósitos en efectivo, transferencias, etc.).

Para una explicación detallada de la lista de transacciones, filtros y cómo leer los detalles de las transacciones de solo lectura, consulta la página dedicada **[Descripción General de Transacciones](../transactions/index.md)**.
