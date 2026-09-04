# 💼 Valor Liquidativo Neto (NAV) / Patrimonio Neto

*[⬅️ Volver a la Descripción General de Métricas de Rendimiento](../index.md)*

## 💡 ¿Qué es el NAV?

El **Valor Liquidativo Neto (NAV)** es la valoración total de mercado de su cartera en un punto en el tiempo $t$. Responde a: *"¿Cuánto vale la cartera en este momento?"*

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

🔗 Ver **[Portfolio Engine — §5 Aggregation](index.md#5-portfolio-aggregation)** para la derivación completa.

---

## 🔗 Cadena de Precios de Valoración {: #valuation-price-chain }

La marca $\operatorname{mark}(a,t)$ proviene del resolver unificado:

1. **MARKET** — cotización de cierre de mercado del mismo día.
2. **TRADE_AVG** — observación promedio COMPRA/VENTA/AJUSTE del mismo día.
3. **CARRIED** — última observación anterior a $t$, proyectada hacia adelante (LOCF).
4. **MISSING** — sin observación en o antes de la fecha $t$.

Las marcas permanecen en moneda nativa hasta la valoración; la conversión FX ocurre en $t$. El PMC **nunca** se utiliza para la valoración. Ver [Resolución de Precios](price-resolution.md).

---

## 📝 Ejemplo

| Componente | Monto |
|------------|-------|
| Valor de Mercado de Activos | €32,759 |
| Saldo de Efectivo | €631 |
| En Tránsito | €0 |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinciones Clave

- **NAV vs [Book Value](book-value.md)**: NAV = valor de mercado; Book = coste de adquisición. Diferencia = ganancias no realizadas.
- **NAV vs [Period PnL](period-pnl.md)**: NAV = instantánea; Period PnL = cambio ajustado por flujos en el tiempo.

---

## ⚠️ Calidad de Datos

| Fuente de Valoración | Confianza |
|----------------------|-----------|
| `MARKET_PRICE` | Completa — cotización real, exacta o proyectada |
| `LAST_TRADE_PRICE` | Parcial — marca del resolver de origen transacción |
| `MISSING` | Ninguna — excluido del NAV |

`estimated=True` solo se aplica a marcas de origen TRADE. Una cotización MARKET obsoleta es stale pero no estimated.

Las valoraciones de origen transacción de más de 14 días activan la advertencia "activos valorados al coste / sin precio de mercado durante más de dos semanas" en la fecha de valoración.
