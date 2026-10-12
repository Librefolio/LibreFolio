# 📖 Valor contable

## 💡 ¿Qué es el Valor contable?

**El Valor contable** representa el coste contable histórico de tu cartera: coste base abierto más reservas de efectivo y valor contable en tránsito. No fluctúa con los precios de mercado — solo el efectivo mantenido en otra divisa sigue su tipo de cambio, en el Valor contable como en el NAV — y es distinto de [Resolución de precios](price-resolution.md).

---

## 🧮 Fórmula

$$
\boxed{\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)}
$$

Donde el coste base abierto:

$$
\mathrm{OCB}(t) = \sum_{\substack{(a,b) \in S \\ q > 0}} q(a,b,t) \cdot w^{C^*}(a,b,t)
$$

Aquí $w^{C^*}(a,b,t)$ es el [PMC](../weighted-average-cost.md) mantenido directamente en la divisa solicitada $C^*$: cada adquisición entró en él al tipo de cambio de su propia fecha $d_i$, como $P_i \cdot \mathrm{fx}(\mathrm{ccy}(P_i), C^*, d_i)$ para un importe $P_i$ realmente pagado. Por tanto, OCB **no utiliza ningún tipo de cambio en la fecha de valoración** $t$: es la suma de costes históricos — lo que se pagó — y no se mueve cuando se mueven los tipos de cambio.

El efectivo, en cambio, es el de cada bróker, mantenido en las divisas en que se registró y valorado al tipo de cambio de $t$:

$$
\mathrm{Cash}(t) = \sum_{b \in S} \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t)
$$

Aquí $N_{b,c}(t)$ es el saldo que el bróker $b$ mantiene en la divisa $c$ en la fecha $t$ — sus movimientos en $c$ con fecha igual o anterior a $t$, en proporción a la [cuota de propiedad](../../../../user/brokers/sharing.md) del bróker — y $\mathrm{fx}(c, C^*, t)$ es el último tipo de cambio en la fecha $t$ o anterior, con $\mathrm{fx}(C^*, C^*, t) = 1$. A diferencia de OCB, Cash se mueve con los tipos de cambio: 1.000 USD valen €900 a 0,90 EUR por USD y €950 a 0,95. Cada movimiento sigue registrado al tipo de cambio de su propia fecha, y los flujos de capital entre ellos entraron en la [base de capital](deposited-capital.md) a ese tipo; solo el saldo mantenido después sigue el tipo de cambio.

En el término en tránsito, el efectivo en tránsito también se convierte en la fecha $t$, como el efectivo en reposo, mientras que los activos en tránsito conservan su coste congelado convertido en su fecha de llegada.

!!! note "Coste incompleto"

    Cuando parte del coste de una posición es desconocido — no hay tipo de cambio en o antes de una fecha de adquisición, o una transferencia o ajuste sin coste base —, OCB incluye solo la parte conocida, y la propia posición queda marcada: su coste medio y su P&L no realizado no se muestran.

🔗 Consulte **[Motor de cartera — §3 Estado de la posición](index.md#3-position-state)** para la derivación completa.

---

## ⚖️ P&L no realizado

$$
\mathrm{Unrealized}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

Dado que NAV valora los activos al precio de mercado del día **y** al tipo de cambio, mientras que el Valor contable mantiene los costes históricos, el P&L no realizado de un activo valorado en otra divisa incluye el efecto del tipo de cambio. Por ejemplo, 10 unidades compradas por €400 cuando valían 500 USD mantienen un OCB de €400; si valen 550 USD en un día en que 1 USD = 0,75 €, su valor de mercado es €412,50 y el P&L no realizado es €12,50 — la ganancia propia de las unidades (+€37,50) menos la caída del dólar (−€25,00). [P&L período](period-pnl.md#unrealized-change-by-currency) muestra cómo el Panel desglosa ambos.

El efectivo mantenido en otra divisa es distinto: $\mathrm{Cash}(t)$ es el mismo término en el NAV y en el Valor contable, valorado al tipo de cambio de $t$ en ambos lados, por lo que su efecto cambiario se anula en la diferencia y el P&L no realizado lo excluye. Aun así, es un resultado: el motor lo registra como [resultado de cambio sobre el efectivo](index.md#exchange-result-on-foreign-cash), forma parte del [P&L total](deposited-capital.md) y, en un período, es la parte [Efecto del tipo de cambio sobre el efectivo](period-pnl.md#fx-on-cash) de Other. Por ejemplo, 1.000 USD depositados a 0,90 EUR por USD y mantenidos mientras el tipo sube a 0,95 cuentan €950 tanto en el NAV como en el Valor contable: el P&L no realizado no se mueve, mientras que el P&L total gana €50 sobre los €900 de capital.

---

## 📝 Ejemplo

| Componente | Importe |
|-----------|--------|
| Coste base abierto | €27.000 |
| Efectivo | €600 |
| Valor contable en tránsito | €0 |

$$
\mathrm{Book} = 27\,000 + 600 = 27\,600 \text{ EUR}
$$

Con NAV = €33.000:

$$
\mathrm{Unrealized} = 33\,000 - 27\,600 = +5\,400 \text{ EUR}
$$

---

## 🔗 Relacionado

- 📊 [PMC](../weighted-average-cost.md) — método de coste unitario para OCB
- 💼 [NAV](nav.md) — contrapartida de valor de mercado
- 🧭 [Resolución de precios](price-resolution.md) — marcas de mercado/negociación usadas por NAV, no por el valor contable
- 📈 [P&L período](period-pnl.md) — P&L realizado + P&L no realizado combinados
- 📈 [Resumen de métricas de rendimiento](../index.md) — todas las métricas de rendimiento de un vistazo
