# 📖 Valor Contable (Book Value)

*[⬅️ Volver a la descripción general de métricas de rendimiento](../index.md)*

## 💡 ¿Qué es el valor contable?

El **valor contable (Book Value)** representa el coste contable histórico de su cartera: cuánto capital ha desplegado a coste, más las reservas de efectivo. No fluctúa con los precios del mercado e distinto de la [Resolución de Precios](price-resolution.md).

---

## 🧮 Fórmula

$$
\boxed{\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)}
$$

Donde la Base de coste abierta (Open Cost Basis):

$$
\mathrm{OCB}(t) = \sum_{\substack{(a,b) \in S \\ q > 0}} q(a,b,t) \cdot w(a,b,t) \cdot \mathrm{fx}(\mathrm{ccy}_w, C^*, t)
$$

Donde $w(a,b,t)$ es el PMC en su moneda de coste. El propio coste de adquisición está fijado al tipo de cambio de la fecha de transacción dentro del PMC; el valor contable abierto se informa entonces en la moneda solicitada para la fecha de valorización.


🔗 Consulte **[Portfolio Engine — §3 Estado de la Posición](index.md#3-position-state)** para la derivación completa.

---

## ⚖️ Ganancia/Pérdida No Realizada

$$
\mathrm{Unrealized}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

---

## 📝 Ejemplo

| Componente | Importe |
|-----------|--------|
| Base de coste abierta (Open Cost Basis) | €27,000 |
| Efectivo (Cash) | €600 |
| Valor contable en tránsito (In-Transit Book) | €0 |

$$
\mathrm{Book} = 27\,000 + 600 = 27\,600 \text{ EUR}
$$

Con NAV = €33,000:

$$
\mathrm{Unrealized} = 33\,000 - 27\,600 = +5\,400 \text{ EUR}
$$

---

## 🔗 Relacionado

- 📊 [PMP](../weighted-average-cost.md) — método de coste unitario para OCB
- 💼 [NAV](nav.md) — equivalente de valor de mercado
- 🧭 [Resolución de Precios](price-resolution.md) — marcas de mercado/trade usadas por el NAV, no por el valor contable
- 📈 [Period PnL](period-pnl.md) — combinación de ganancias/pérdidas realizadas y no realizadas
