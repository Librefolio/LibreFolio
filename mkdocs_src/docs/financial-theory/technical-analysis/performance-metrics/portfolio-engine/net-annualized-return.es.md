# 📈 Rendimiento Neto Anualizado

## 💡 Propósito

LibreFolio reporta el rendimiento anualizado solo cuando la ventana observada es suficientemente larga para que la capitalización compuesta sea significativa. La conversión compartida es:

$$
\boxed{r_{\mathrm{ann}} = (1+r_{\mathrm{cum}})^{365/d}-1}
$$

donde $d$ son días calendario. Es la inversa de:

$$
r_{\mathrm{cum}}=(1+r_{\mathrm{ann}})^{d/365}-1
$$

La implementación devuelve `None` cuando:

- $r_{\mathrm{cum}} \leq -1$
- $d < 30$
- el cálculo se desborda

!!! warning "Guardia de treinta días"

    Un rendimiento semanal anualizado a 365 días puede explotar en porcentajes sin sentido. Por lo tanto, LibreFolio suprime la anualización por debajo de 30 días y muestra un valor vacío en lugar de un CAGR matemáticamente correcto pero engañoso.

## 🧾 Vista de Posiciones

Para una posición abierta en "Tus posiciones" / resumen de la cartera:

$$
r_{\mathrm{net}} =
\frac{
\mathrm{ComponenteDeMercado}
+ \mathrm{Ingresos}
- \mathrm{ComisionesImpuestos}
}{
\mathrm{BaseDeCosto}
}
$$

donde:

$$
\mathrm{ComponenteDeMercado} =
\begin{cases}
\mathrm{ValorActual}-\mathrm{BaseDeCosto}, & \text{existe valor de mercado}\\
0, & \text{sin precio / valorado al costo}
\end{cases}
$$

Ventana de anualización:

$$
d = t_{\mathrm{reporte}} - t_{\mathrm{primer\ lote\ que\ afecta}}
$$

Los tipos de transacciones que afectan al lote son:

$$
\{\text{COMPRA},\ \text{VENTA},\ \text{AJUSTE},\ \text{TRANSFERENCIA}\}
$$

Esto incluye sucesiones en especie, transferencias de bróker y posiciones iniciadas por ajuste. La antigua detección solo de COMPRA/VENTA pasaría por alto esas posiciones.

## 🪟 Vista de Período

Para la contribución por activo en un período:

$$
\mathrm{PnL}_{periodo} =
\Delta \mathrm{PlusvalíaNoReal}
+ \mathrm{PlusvalíaRealizada}
+ \mathrm{Ingresos}
- \mathrm{ComisionesImpuestos}
$$

El porcentaje del período mostrado sigue siendo:

$$
r_{\mathrm{periodo}} = \frac{\mathrm{PnL}_{periodo}}{|\mathrm{StartValue}|}
$$

cuando `StartValue` es distinto de cero. La anualización puede recurrir al coste base final para activos abiertos a mitad del período:

$$
\mathrm{base\_anual}=
\begin{cases}
|\mathrm{StartValue}|, & |\mathrm{StartValue}|>0\\
\mathrm{BaseDeCosto}_{final}, & \text{de lo contrario}
\end{cases}
$$

El inicio de la ventana se limita al lote FIFO más antiguo aún abierto al final del período:

$$
t_{\mathrm{inicio}}=\max(t_{\mathrm{desde}},\ t_{\mathrm{lote\ abierto\ más\ antiguo}})
$$

Entonces:

$$
r_{\mathrm{ann}} =
\operatorname{anualizar}\left(\frac{\mathrm{PnL}_{periodo}}{\mathrm{base\_anual}},\ t_{\mathrm{final}}-t_{\mathrm{inicio}}\right)
$$

## 🧬 Lotes FIFO

El rendimiento anualizado del lote FIFO es neto de ingresos, comisiones e impuestos asignados:

$$
\mathrm{PnLTotalNeto}_i =
\mathrm{PnLMercado}_i
+ \mathrm{PnLRealizada}_i
+ \mathrm{Ingresos}_i
- \mathrm{Comisiones}_i
- \mathrm{Impuestos}_i
$$

$$
\mathrm{RetornoTotalNeto}_i =
\frac{\mathrm{PnLTotalNeto}_i}{\mathrm{ValorApertura}_i}
$$

El valor anualizado usa `net_total_return`, no el `total_return` bruto:

$$
r_{\mathrm{ann},i} =
\operatorname{anualizar}
\left(
\mathrm{RetornoTotalNeto}_i,\ 
t_{\mathrm{fin\ lote}}-t_{\mathrm{apertura}}
\right)
$$

donde $t_{\mathrm{fin\ lote}}$ es la fecha de cierre para lotes completamente cerrados; de lo contrario, la fecha de fin del análisis.

## 🔗 Relacionado

- 🧭 [Resolución de Precios](price-resolution.md) — fuente de valoraciones de mercado y de origen de operaciones
- 📉 [ROI Simple](roi.md) — contexto de rendimiento del titular y a nivel de posición
- 📊 [P&L del período](period-pnl.md) — descomposición del período
- 🔬 [Análisis de Lotes FIFO](../fifo-engine/fifo-lot-analysis.md) — métricas netas por lote
- ⚙️ [Portfolio Engine](index.md) — modelo matemático completo
