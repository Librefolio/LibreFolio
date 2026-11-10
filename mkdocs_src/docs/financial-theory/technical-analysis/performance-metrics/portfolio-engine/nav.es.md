# 💼 Valor neto (NAV) / Patrimonio neto

## 💡 ¿Qué es el NAV?

**El valor neto (NAV)** es la valoración de mercado total de tu cartera en un momento dado $t$. Responde a la pregunta: *"¿Cuánto vale la cartera ahora mismo?"*

---

## 🧮 Fórmula

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Donde:

$$
\mathrm{MV}(t)=
\sum_{(a,b)\in S}
\frac{q(a,b,t)}{qbq(a)}
\cdot \operatorname{mark}(a,t)
\cdot \mathrm{fx}(\mathrm{ccy}_{mark}, C^*, t)
$$

y el efectivo de cada bróker, mantenido en las monedas en que se registró y valorado al tipo de cambio de $t$:

$$
\mathrm{Cash}(t) = \sum_{b \in S} \sum_{c} N_{b,c}(t) \cdot \mathrm{fx}(c, C^*, t)
$$

siendo $N_{b,c}(t)$ el saldo que el bróker $b$ mantiene en la moneda $c$ en $t$, multiplicado por la [participación de titularidad](../../../../user/brokers/sharing.md) del bróker, y $\mathrm{fx}(c, C^*, t)$ el último tipo de cambio en $t$ o antes ($1$ para $c = C^*$). Por tanto, el efectivo mantenido en otra moneda modifica el NAV cuando cambia su tipo de cambio.

Una posición cuyo activo aún no tiene precio de valoración —sin cotización, sin BUY ni SELL y sin [estimación del coste de transferencia](price-resolution.md#transfer-cost-estimate) en $t$ o antes— se incluye en $\mathrm{MV}(t)$ por su coste base $\mathrm{CB}(a,b,t)$, en lugar de por su precio de valoración, cuando ese coste está completo, y se excluye del NAV en caso contrario.

🔗 Consulta **[Motor de cartera — §3 Estado de la posición](index.md#3-position-state)** y **[§5 Agregación](index.md#5-portfolio-aggregation)** para ver la derivación completa.

---

## 🔗 Resolvedor unificado de precios {: #valuation-price-chain }

El precio de valoración $\operatorname{mark}(a,t)$ procede del resolvedor unificado:

1. **MARKET** — cotización del sistema de activos del mismo día.
2. **TRADE_AVG** — promedio de observaciones de BUY/SELL del mismo día, o el coste de una transferencia entrante para un activo que aún no tiene nada más ([estimación](price-resolution.md#transfer-cost-estimate)).
3. **CARRIED** — última observación anterior a $t$, arrastrada (LOCF).
4. **MISSING** — ninguna observación en $t$ o antes.

Un ADJUSTMENT nunca es una observación, con o sin un coste base: registra un coste, no un precio. El coste de una transferencia entrante solo cuenta como estimación, y solo mientras el activo no tenga cotización ni ninguna otra operación en ese día o antes.

Los precios de valoración permanecen en moneda nativa hasta la valoración, y los saldos de efectivo también, cada uno en la moneda en que se registró; la conversión FX se produce en $t$. El PMC **nunca** es un precio: solo una posición sin ningún precio de valoración se cuenta por su coste base, una estimación declarada (`ESTIMATED_AT_COST`) que conserva los tipos de cambio de sus fechas de adquisición. Consulta [Resolución de precios](price-resolution.md).

---

## 📝 Ejemplo

| Componente | Importe |
|-----------|--------|
| Valor de mercado de los activos | €32,759 |
| Saldo de efectivo | €631 |
| En tránsito | €0 |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinciones clave

- **NAV frente a [valor contable](book-value.md)**: NAV = valor de mercado; valor contable = coste de adquisición. La diferencia = plusvalías no realizadas.
- **NAV frente a [P&L período](period-pnl.md)**: NAV = instantánea; P&L período = cambio ajustado por flujos a lo largo del tiempo.

---

## ⚠️ Calidad de datos

| Fuente de valoración | Confianza |
|-----------------|------------|
| `MARKET_PRICE` | Completa — cotización real, exacta o arrastrada |
| `LAST_TRADE_PRICE` | Parcial — valoración del resolvedor originada por una operación |
| `ESTIMATED_AT_COST` | Estimación — sin precio en absoluto: el coste base, sin plusvalía ni minusvalía no realizadas |
| `MISSING` | Ninguna — sin precio y con un coste incompleto: excluida del NAV |

`estimated=True` solo se aplica a los precios de valoración originados por operaciones. Una cotización MARKET arrastrada y obsoleta está obsoleta, pero no se considera estimada.

Para un activo con proveedor de precios, el panel advierte, en la fecha de valoración, lo siguiente: una valoración originada por operaciones, una vez que el activo ha estado sin cotización de mercado durante más del periodo de gracia de 14 días —contado desde la llegada de la transferencia para un activo nunca cotizado, comprado ni vendido y valorado al coste de una transferencia—, genera la advertencia “valorado a su último precio de transacción”; y una valoración a coste, más de 14 días después de la primera adquisición del activo, genera la advertencia “valorado a coste”. Un activo sin proveedor no genera ninguna de las dos: sus operaciones, o su coste, son su valor previsto.
