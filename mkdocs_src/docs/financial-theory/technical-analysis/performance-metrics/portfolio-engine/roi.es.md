# 📉 ROI simple (retorno de la inversión)

## 💡 ¿Qué es?

El ROI simple mide el valor generado en relación con el capital invertido. En el motor de cartera actual, el denominador del capital invertido es la **línea base de capital** de `cumulative_external_cash_flow`, no solo los depósitos en efectivo.

## 🧮 Fórmula

$$
\mathrm{ROI}(t)=
\frac{\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)}
{\mathrm{CapitalBaseline}(t)}
$$

La misma línea base determina el `total_gain_loss` principal:

$$
\mathrm{TotalGainLoss}(t)=\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)
$$

`CapitalBaseline` incluye los flujos de efectivo externos ordinarios y el capital en especie valorado procedente de ajuste/transferencia. Eso evita que las carteras heredadas o inicializadas muestren un ROI absurdo porque un activo se incorporó sin un depósito en efectivo.

## 🪟 El ROI de un período {: #dashboard-period-roi }

El ROI de la tarjeta de rentabilidad del panel y su línea en el gráfico `%` miden el período seleccionado, no todo el historial. Su capital es el valor con el que comienza el período, más los depósitos y menos los retiros realizados después:

$$
\mathrm{ROI}_{\mathrm{period}}(t)=
\frac{\mathrm{NAV}(t)-\mathrm{NetInvested}(t)}{\mathrm{NetInvested}(t)},
\qquad
\mathrm{NetInvested}(t)=\max\!\left(0,\ \mathrm{NAV}(t_0)+\sum_{t_0<s\le t}\mathrm{CF}_s\right)
$$

donde $t_0$ es el último día del historial que sea igual o anterior al inicio del período, y $\mathrm{CF}_s$ cuenta los flujos externos —los depósitos como positivos, los retiros como negativos y el capital en especie incluido como en la línea base de capital anterior—. La tarjeta es el último punto de la línea; cuando $\mathrm{NetInvested}(t)$ es cero, el ROI es $0$, nunca un valor ausente.

Cuando el período comienza **antes del primer día de la cartera**, no hay un valor con el que abrir el período, y los flujos de ese primer día —el primer depósito— quedarían fuera de la suma. Entonces el período abarca todo el historial, por lo que su capital es cada flujo, incluido el primer depósito: el ROI es el mismo que sin ninguna fecha de inicio, en la tarjeta y en cada punto de la línea.

## 🎯 Cuándo usarlo

- Para leer la ganancia/pérdida principal de la cartera frente al capital económico aportado.
- Para comparar el NAV actual con la línea base de capital actual.
- Para verificar rápidamente el rendimiento ajustado por flujos de efectivo antes de consultar TWRR/MWRR.

## 📈 Rentabilidad anualizada neta de la posición

Las posiciones abiertas también muestran un CAGR neto:

$$
r_{\mathrm{net}}=
\frac{\mathrm{MarketComponent}+\mathrm{Income}-\mathrm{FeesTaxes}}
{\mathrm{CostBasis}}
$$

La anualización utiliza:

$$
r_{\mathrm{ann}}=(1+r_{\mathrm{net}})^{365/d}-1
$$

La ventana comienza en la primera transacción que afecta al lote: compra, venta, ajuste o transferencia. Se suprimen los valores correspondientes a períodos inferiores a 30 días. Las definiciones completas están en [Rentabilidad anualizada neta](net-annualized-return.md).

## ⚠️ El defecto: dilución por flujos de efectivo

El ROI simple sigue siendo sensible al importe y al momento en que se añade capital. Si añades una aportación elevada después de que ya se hayan producido ganancias, el ratio puede caer aunque el valor de mercado no lo haya hecho. Usa [P&L período](period-pnl.md), [TWRR](twrr.md) y [MWRR](mwrr.md) para separar el beneficio absoluto, la rentabilidad de la estrategia y la rentabilidad del inversor ponderada por el dinero.
