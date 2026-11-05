# 📈 Rentabilidad anualizada neta

## 💡 Propósito

LibreFolio informa de la rentabilidad anualizada solo cuando la ventana observada es lo bastante larga como para que la capitalización compuesta sea significativa. La conversión compartida es:

$$
\boxed{r_{\mathrm{ann}} = (1+r_{\mathrm{cum}})^{365/d}-1}
$$

donde $d$ son días naturales. Es la inversa de:

$$
r_{\mathrm{cum}}=(1+r_{\mathrm{ann}})^{d/365}-1
$$

La implementación devuelve `None` cuando:

- $r_{\mathrm{cum}} \leq -1$
- $d < 30$
- el cálculo se desborda

!!! warning "Protección de treinta días"

    Una rentabilidad de una semana anualizada a 365 días puede dispararse a porcentajes sin sentido. Por tanto, LibreFolio suprime la anualización por debajo de 30 días y muestra un valor vacío en lugar de un CAGR matemáticamente correcto pero engañoso.

## 🧾 Vista de posiciones

Para una posición abierta en «Tus posiciones» / resumen de cartera:

$$
r_{\mathrm{net}} =
\frac{
\mathrm{MarketComponent}
+ \mathrm{Income}
- \mathrm{FeesTaxes}
}{
\mathrm{CostBasis}
}
$$

donde:

$$
\mathrm{MarketComponent} =
\begin{cases}
\mathrm{CurrentValue}-\mathrm{CostBasis}, & \text{existe valor de mercado}\\
0, & \text{sin precio / valorado al coste}
\end{cases}
$$

Ventana de anualización:

$$
d = t_{\mathrm{report}} - t_{\mathrm{first\ lot\ affecting}}
$$

Los tipos de transacción que afectan a lotes son:

$$
\{\text{BUY},\ \text{SELL},\ \text{ADJUSTMENT},\ \text{TRANSFER}\}
$$

Esto incluye sucesiones en especie, traspasos entre brókeres y posiciones creadas mediante ajustes. La antigua detección basada únicamente en BUY/SELL omitiría esas posiciones.

## 🪟 Vista por periodo

Para la contribución por activo del periodo:

$$
\mathrm{PnL}_{period} =
\Delta \mathrm{UGL}
+ \mathrm{Realized}
+ \mathrm{Income}
- \mathrm{FeesTaxes}
$$

El porcentaje mostrado del periodo sigue siendo:

$$
r_{\mathrm{period}} = \frac{\mathrm{PnL}_{period}}{|\mathrm{StartValue}|}
$$

cuando `StartValue` no es cero. La anualización puede recurrir al coste base final para los activos abiertos a mitad del periodo:

$$
\mathrm{ann\_base}=
\begin{cases}
|\mathrm{StartValue}|, & |\mathrm{StartValue}|>0\\
\mathrm{CostBasis}_{end} + \sum_a \left(V_a - C_a\right), & \text{en caso contrario}
\end{cases}
$$

La suma abarca los traspasos desde otro bróker del ámbito que la posición recibió en el periodo, contabilizados como en
[Posiciones cerradas en el periodo](#closed-in-period): lo que sus unidades ganaron antes de llegar, el valor al llegar menos
el coste histórico movido (MF-A9). El resultado de la posición contabiliza esas unidades desde su valor al llegar, y su coste final
se contabiliza a su coste histórico, por lo que la base suma la misma cantidad. Solo se aplica mientras ninguna unidad haya salido de la posición en el
periodo, ni antes de la llegada ni después de esta: una vez que han salido unidades, un traspaso no conlleva cantidad alguna que indique qué parte de la suma salió con
ellas, y la suma se descarta; solo el coste final es la base, como para cualquier posición abierta a mitad del periodo que vendió parte de
lo que compró.

El inicio de la ventana se acota al lote FIFO más antiguo que siga abierto al final del periodo:

$$
t_{\mathrm{start}}=\max(t_{\mathrm{from}},\ t_{\mathrm{oldest\ open\ lot}})
$$

Los lotes se cuentan en cada bróker: un traspaso abre un lote con fecha de su llegada al bróker receptor. Un desdoblamiento de acciones reescala los lotes abiertos y conserva sus fechas, por lo que nunca acorta la ventana. Los lotes más antiguos que en conjunto contienen $10^{-5}$ unidades o menos —el residual que deja una venta— se apartan, ya que una posición cerrada cuenta ese residual como cerrado: un residual dejado hace años no hace retroceder el inicio de la ventana hasta su fecha, y una posición que no contiene más que ese residual no tiene ningún lote abierto (MF-A7). Las cantidades son las del motor, con la participación del propietario en el bróker: en un bróker con una participación del 50 %, un residual de $0{,}000012$ unidades es $0{,}000006$ para el propietario, polvo para la ventana y para la fila (MF-A10).

Entonces:

$$
r_{\mathrm{ann}} =
\operatorname{annualize}\left(\frac{\mathrm{PnL}_{period}}{\mathrm{ann\_base}},\ t_{\mathrm{end}}-t_{\mathrm{start}}\right)
$$

### 🔚 Posiciones cerradas en el periodo {: #closed-in-period }

Una posición está cerrada cuando su cantidad en $t_{\mathrm{end}}$, con la participación del propietario en el bróker, es igual o inferior al umbral de polvo de $10^{-5}$ unidades, de modo que un residual dejado por reembolsos por tramos cuenta como cerrado. No tiene coste final, y un valor inicial no dice nada sobre una posición vendida a las pocas semanas. Su rentabilidad anualizada usa el capital que desplegó y el tiempo que se mantuvo dentro del periodo:

$$
\mathrm{CostOut} = \sum_{s\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} C_s \;+\; \sum_{m\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} C_m \;+\; \sum_{a\,\in\,(t_{\mathrm{from}},\ t_{\mathrm{end}}]} \left(V_a - C_a\right)
$$

$$
t_{\mathrm{start}} = \max(t_{\mathrm{from}},\ t_{\mathrm{first\ opening}}), \qquad t_{\mathrm{close}} = \text{último día en que su cantidad cayó al umbral de polvo o por debajo}
$$

$$
r_{\mathrm{ann}} =
\operatorname{annualize}\left(\frac{\mathrm{PnL}_{period}}{\mathrm{CostOut}},\ t_{\mathrm{close}}-t_{\mathrm{start}}\right)
$$

- $C_s$ es el coste histórico, en $C^*$, de cada enajenación que cuenta el P&L realizado del periodo —una SELL, o un ADJUSTMENT saliente no vinculado a un desdoblamiento ([Motor de cartera — §8](index.md#8-realized-gain-loss)). Una enajenación excluida del P&L realizado no añade coste.
- $C_m$ es el coste histórico que movió fuera cada traspaso a otro bróker del ámbito, cuando la fila contabiliza el tramo de ese traspaso: salió después de $t_{\mathrm{from}}$, llegó a más tardar en $t_{\mathrm{end}}$, y se conocen tanto su valor al llegar como el coste movido ([P&L período](period-pnl.md), decisión del desarrollador P22). El resultado de la fila recoge lo que hicieron esas unidades hasta su llegada (el ajuste de tramo), por lo que su coste pertenece a la base.
- $V_a - C_a$ es, para cada uno de esos traspasos que la posición **recibió**, lo que sus unidades ganaron antes de llegar: su valor al llegar menos el coste histórico movido con ellas. El resultado de la fila hace que esas unidades partan de $V_a$ (el ajuste de tramo descuenta $V_a - C_a$), mientras que $C_s$ y $C_m$ llevan su coste histórico, de modo que la base suma la misma cantidad y también las cuenta por su valor al llegar (MF-A8). Así, $\mathrm{CostOut}$ no es solo coste histórico: para las unidades que recibió la posición, la base contiene su valor al llegar.
- $t_{\mathrm{first\ opening}}$ es la primera adquisición de la posición en ese bróker: un traspaso la abre a su llegada allí, un desdoblamiento nunca lo hace. Es la primera de todas, no la del último lote, por lo que los días a cero entre dos cierres dentro del periodo permanecen en la ventana.
- El numerador es el $\mathrm{PnL}_{period}$ completo de la fila: para una posición mantenida en $t_{\mathrm{from}}$, su $\Delta\mathrm{UGL}$ descuenta la ganancia/pérdida no realizada con la que empezó.
- El porcentaje mostrado del periodo mantiene $|\mathrm{StartValue}|$ como base: solo el valor anualizado cambia de base y de ventana.

Cuando esto no da valor, se dan dos casos:

- **Menos de 30 días mantenidos** en el periodo, $t_{\mathrm{close}} - t_{\mathrm{start}} < 30$: la fila no tiene rentabilidad anualizada (`—`), independientemente de cualquier otra cosa que hiciera inutilizable la base. La regla anterior anualizaría sobre $t_{\mathrm{from}} \to t_{\mathrm{end}}$, como si diez días de tenencia hubieran durado todo el periodo (MF-A3).
- **En caso contrario**, la fila mantiene la regla anterior. Eso ocurre cuando las unidades salieron de la posición de cualquier otra forma —un traspaso fuera del ámbito, o unidades aún en tránsito en $t_{\mathrm{end}}$, un traspaso o una enajenación cuyo valor o coste es desconocido—, ya que entonces el resultado de la fila contendría más de lo que cubre su base; y con una rentabilidad de $-100\%$ o peor. La regla anterior es: $|\mathrm{StartValue}|$ sobre $t_{\mathrm{from}} \to t_{\mathrm{end}}$, y ningún valor para una posición abierta en el periodo.

??? example "Ejemplo: una posición vendida a los 90 días de un periodo de un año"

    En $t_{\mathrm{from}}$, la posición vale 1.100 con un coste de 1.000. Se vende toda 90 días después por 1.250:

    $$
    \mathrm{PnL}_{period} = (0 - 100) + (1\,250 - 1\,000) = +150
    $$

    $$
    r_{\mathrm{ann}} = \operatorname{annualize}\left(\frac{150}{1\,000},\ 90\right) = 1{,}15^{365/90} - 1 \approx +76{,}3\%
    $$

    La ganancia no realizada de +100 con la que empezó se descuenta de $\Delta\mathrm{UGL}$, y el P&L realizado añade +250. El porcentaje del periodo se mantiene en $150 / 1\,100 = 13{,}64\%$; anualizado durante todo el año sobre el valor inicial, como se haría con una posición abierta, el mismo +150 también daría 13,64 %.

??? example "Ejemplo: la mitad vendida, la mitad traspasada a otro bróker"

    En $t_{\mathrm{from}}$, la posición tiene 10 unidades, valoradas en 1.100 con un coste de 1.000. Cinco se venden por 625; cinco se traspasan a otro bróker del ámbito y valen 600 cuando llegan:

    $$
    \mathrm{PnL}_{period} = \underbrace{(0 - 100)}_{\Delta\mathrm{UGL}} + \underbrace{(625 - 500)}_{\text{Realizado}} + \underbrace{(600 - 500)}_{\text{tramo}} = +125
    $$

    $$
    \mathrm{CostOut} = 500 + 500 = 1\,000, \qquad \frac{125}{1\,000} = 12{,}5\%
    $$

    El coste de las unidades vendidas por sí solo daría $125 / 500 = 25\%$: el resultado de las unidades traspasadas en el numerador, sin su coste en la base (MF-A5).

    El bróker que recibió las cinco unidades y después las vendió por 660 muestra la imagen especular: su resultado es $(660 - 500) - (600 - 500) = +60$, y su base $500 + (600 - 500) = 600$, así que $60 / 600 = 10\%$; las unidades cuentan desde su valor al llegar, tanto en el resultado como en la base (MF-A8).

## 🧬 Lotes FIFO

La rentabilidad anualizada del lote FIFO es neta de los ingresos, comisiones e impuestos asignados:

$$
\mathrm{NetTotalPnL}_i =
\mathrm{MarketPnL}_i
+ \mathrm{RealizedPnL}_i
+ \mathrm{Income}_i
- \mathrm{Fees}_i
- \mathrm{Taxes}_i
$$

$$
\mathrm{NetTotalReturn}_i =
\frac{\mathrm{NetTotalPnL}_i}{\mathrm{OpeningValue}_i}
$$

El valor anualizado usa `net_total_return`, no el `total_return` bruto:

$$
r_{\mathrm{ann},i} =
\operatorname{annualize}
\left(
\mathrm{NetTotalReturn}_i,\ 
t_{\mathrm{lot\ end}}-t_{\mathrm{opening}}
\right)
$$

donde $t_{\mathrm{lot\ end}}$ es la fecha de cierre para lotes totalmente cerrados; en caso contrario, la fecha de fin del análisis.

## 🔗 Relacionados

- 🧭 [Resolución de precios](price-resolution.md) — fuente de las valoraciones de mercado y de las originadas por operaciones
- 📉 [ROI simple](roi.md) — contexto de rentabilidad principal y a nivel de posición
- 📊 [P&L período](period-pnl.md) — descomposición del periodo
- 🔬 [Análisis de lotes FIFO](../fifo-engine/fifo-lot-analysis.md) — métricas netas por lote
- ⚙️ [Motor de cartera](index.md) — modelo matemático completo
