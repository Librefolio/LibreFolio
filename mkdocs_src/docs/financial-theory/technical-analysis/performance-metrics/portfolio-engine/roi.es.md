# 📉 ROI Simple (Retorno sobre la Inversión)

## 💡 ¿Qué es?

El ROI simple mide el valor generado en relación con el capital invertido. En el motor de cartera actual, el denominador del capital invertido es la **línea base de capital** proveniente de `cumulative_external_cash_flow`, no solo depósitos en efectivo.

## 🧮 Fórmula

$$
\mathrm{ROI}(t)=
\frac{\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)}
{\mathrm{CapitalBaseline}(t)}
$$

La misma línea base impulsa la cifra principal de `total_gain_loss`:

$$
\mathrm{TotalGainLoss}(t)=\mathrm{NAV}(t)-\mathrm{CapitalBaseline}(t)
$$

`CapitalBaseline` incluye flujos de efectivo externos ordinarios y capital valorado en especie por AJUSTE/TRANSFERENCIA. Esto evita que carteras heredadas o sembradas muestren un ROI absurdo porque un activo ingresó sin un depósito en efectivo.

## 🎯 Cuándo usarlo

- Para leer la ganancia/pérdida principal de la cartera en relación con el capital económico aportado.
- Para comparar el NAV actual con la línea base de capital actual.
- Para verificar el rendimiento ajustado por flujo de efectivo antes de analizar TWRR/MWRR.

## 📈 Rendimiento Neto Anualizado de la Posición

Las posiciones abiertas también exponen un CAGR neto:

$$
r_{\mathrm{net}}=
\frac{\mathrm{MarketComponent}+\mathrm{Income}-\mathrm{FeesTaxes}}
{\mathrm{CostBasis}}
$$

La anualización utiliza:

$$
r_{\mathrm{ann}}=(1+r_{\mathrm{net}})^{365/d}-1
$$

La ventana comienza en la primera transacción que afecta al lote: COMPRA, VENTA, AJUSTE o TRANSFERENCIA. Los valores menores a 30 días se suprimen. Las definiciones completas están en [Rendimiento Neto Anualizado](net-annualized-return.md).

## ⚠️ La Limitación: Dilución por Flujo de Efectivo

El ROI simple sigue siendo sensible a la cantidad y el momento del capital agregado. Si se agrega una contribución grande después de que ya ocurrieron ganancias, el ratio puede caer aunque el valor de mercado no lo haya hecho. Utilice [PyG del Período](period-pnl.md), [TWRR](twrr.md) y [MWRR](mwrr.md) para separar la ganancia absoluta, el rendimiento de la estrategia y el rendimiento del inversor ponderado por dinero.
