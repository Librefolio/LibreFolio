# 📐 Medidas

La herramienta Medida responde a *¿cuánto cambió entre estos dos días?* Elige dos puntos en el gráfico y lee el cambio del activo, y de las líneas dibujadas con él, entre ellos.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="assets" data-name="detail-measures" alt="Panel de medidas del activo" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Tomar una medida

1. Haz clic en **📏 Añadir medición** en la parte superior derecha del gráfico: el panel **Medidas** se abre debajo de él.
2. Haz clic en el punto **inicio** del gráfico, luego en el punto **fin**.
3. La nueva medida se abre con su tabla, y el gráfico la dibuja con su propio color.

**+ Añadir medición** en el encabezado del panel, en cambio, mide todo el gráfico, desde su primer hasta su último punto: práctico en el móvil. El encabezado de cada medida contiene su color y 🗑️ para eliminarla; despliega la medida para cambiar sus fechas.

Las medidas no se guardan: recargar la página vacía el panel. **Precios** y **Rentabilidad móvil** mantienen medidas separadas.

---

## 💵 En modo Precios

La tabla tiene una fila para el activo (una segunda en su propia moneda cuando el gráfico se convierte) y una para cada línea dibujada en el eje de precios, como un activo de comparación o una media móvil. Junto a los valores de **Inicio** y **Fin**:

- **Δ Abs** — la diferencia $V_{end} - V_{start}$, en la unidad de la línea.
- **Δ %** — el cambio $\frac{V_{end} - V_{start}}{V_{start}}$ → [Rentabilidades y tasas de crecimiento](../../../financial-theory/fundamentals/returns.md)
- **Δ%/yr** — el mismo cambio como tasa anual a lo largo de los $d$ días naturales entre los puntos, $(1 + \Delta\%)^{365/d} - 1$ → [Rentabilidades y tasas de crecimiento](../../../financial-theory/fundamentals/returns.md)

La línea de resumen de la medida añade el número de días.

---

## 📈 En modo Rentabilidad móvil

Los valores ya son rentabilidades, así que la tabla los compara:

- **Inicio**, **Fin** — la rentabilidad móvil en cada una de las dos fechas.
- **Δ pp** — Fin menos Inicio, en puntos porcentuales → [Rentabilidad móvil a lo largo de los días naturales](../../../financial-theory/fundamentals/returns.md#rolling-return-calendar)
- **Días** — los días naturales entre los dos puntos.

---

## 🔗 Relacionado

- 📈 **[Gráfico interactivo](chart.md)** — Controles del gráfico y filtrado por rango de fechas
- 📊 **[Señales](signals.md)** — Superposiciones de indicadores técnicos
