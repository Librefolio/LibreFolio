# 📈 Gráfico Interactivo

El gráfico de precios es la pieza central de la página de detalles del activo, que proporciona un historial visual del precio del activo a lo largo del tiempo.

<div class="screenshot-container" style="max-width: 800px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="detail-chart" alt="Gráfico de Precios del Activo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎛️ Barra de Filtros

La barra de filtros situada sobre el gráfico proporciona controles para personalizar la vista:

### 📅 Rango de Fechas

Seleccione una ventana de tiempo para los datos del gráfico:

- **Preajustes**: 1W, 1M, 3M, 6M, 1Y, 2Y, YTD, MAX — cuando la barra tiene espacio libre, aparecen **preajustes de relleno** adicionales para ocuparlo (3Y, 5Y, 10Y y WTD, MTD, QTD)
- **Personalizado**: elija una fecha de inicio y fin utilizando el selector de calendario

### 💱 Selector de Divisa

Visualice los precios en:

- La **divisa nativa** del activo (por ejemplo, USD para Apple)
- La **divisa base de su cartera** (por ejemplo, EUR) — convertida automáticamente mediante tipos de cambio

### 📊 Interruptor Absoluto / Porcentaje

- **Absoluto**: muestra los valores reales del precio
- **Porcentaje** (%): muestra el cambio porcentual desde el primer punto de datos en el rango seleccionado

### 📅 Marcadores de Eventos

Los dividendos, splits, pagos de intereses y otros [eventos de activos](events.md) aparecen como marcadores de colores en el gráfico:

- 💰 **Dividendo** — distribución de efectivo
- 💵 **Interés** — pago de intereses
- 📊 **Split** — división de acciones
- 📝 **Ajuste de Precio** — reducción de valor o recalificación
- 🏁 **Liquidación al Vencimiento** — el activo alcanzó su vencimiento

Pase el cursor sobre un marcador para ver los detalles del evento (fecha, tipo, valor).

---

## 🎨 Estética

Haga clic en el botón de **Configuración** (⚙️) para mostrar/ocultar el panel de estética en línea (relleno de área, colores de la línea base, líneas de cuadrícula, degradado stale, escala del eje Y). Los mismos ajustes — más las señales de superposición — también pueden editarse para todos los gráficos de activos a la vez desde el modal **Configuración del Gráfico** en la [página de la lista de Activos](../index.md), que muestra una vista previa en vivo mientras edita; consulte [Configuración del Gráfico](../../fx/chart-settings.md) para ver cómo funcionan el modal y su vista previa (el ámbito de Activos es independiente de FX).

---

## 🔗 Relacionado

- 📊 **[Señales](signals.md)** — Superponer indicadores técnicos
- 📐 **[Medidas](measures.md)** — Medir diferencias de precio
- 📅 **[Eventos](events.md)** — Comprender los marcadores de eventos
