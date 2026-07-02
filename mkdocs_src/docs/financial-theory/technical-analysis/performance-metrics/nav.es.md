# 💼 Valor Liquidativo (NAV) / Patrimonio Neto

*[⬅️ Volver a la descripción general de métricas de rendimiento](index.md)*

## 💡 ¿Qué es el NAV?

**Net Asset Value (NAV)** es la valoración total de mercado de su cartera en un momento dado $t$. Responde a: *"¿Cuánto vale la cartera en este momento?"*

---

## 🧮 Fórmula

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Donde $\mathrm{MV}(t) = \sum_{(a,b) \in S} q(a,b,t) \cdot p(a,t) \cdot \mathrm{fx}(\mathrm{ccy}_p, C^*, t)$

🔗 Consulte **[Portfolio Engine — §5 Agregación de Cartera](portfolio-engine.md#5-portfolio-aggregation)** para ver la derivación completa.

---

## 🔗 Cadena de Precios de Valoración

El precio $p(a,t)$ sigue una prioridad estricta:

1. **Precio de mercado** — Relleno hacia atrás (backward-fill) de PriceHistory (el más reciente $\leq t$)
2. **Último precio de compra** — precio unitario de la compra (COMPRA) más reciente de $V(u)$ (todos los brókers visibles)
3. **Ausente** — la posición se excluye del NAV

El PMP **nunca** se utiliza para la valoración. Consulte **[Portfolio Engine — §2](portfolio-engine.md#2-valuation-price)**.

---

## 📝 Ejemplo

| Componente | Cantidad |
|-----------|--------|
| Valor de Mercado de Activos | €32,759 |
| Saldo de Efectivo | €631 |
| En Tránsito | €0 |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinciones Clave

- **NAV vs [Book Value](book-value.md)**: NAV = valor de mercado; Book = coste de adquisición. Diferencia = plusvalías no realizadas.
- **NAV vs [Period PnL](period-pnl.md)**: NAV = instantánea; Period PnL = cambio ajustado por flujos a lo largo del tiempo.

---

## ⚠️ Calidad de los Datos

| Fuente de Valoración | Confianza |
|-----------------|------------|
| `MARKET_PRICE` | Completa — PriceHistory disponible |
| `LAST_BUY_PRICE` | Parcial — utilizando precio de transacción |
| `MISSING` | Nula — excluido del NAV |
