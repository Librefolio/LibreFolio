# 💼 Valor Liquidativo (NAV) / Patrimonio Neto

*[⬅️ Volver a la Descripción General de Métricas de Rendimiento](index.md)*

## 💡 ¿Qué es el NAV?

**Valor Liquidativo (NAV)** es la valoración total de mercado de tu cartera en un momento $t$. Responde a: *"¿Cuánto vale la cartera ahora mismo?"*

---

## 🧮 Fórmula

$$
\boxed{\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)}
$$

Donde $\mathrm{MV}(t) = \sum_{(a,b) \in S} q(a,b,t) \cdot p(a,t) \cdot \mathrm{fx}(\mathrm{ccy}_p, C^*, t)$

🔗 Consulta **[Portfolio Engine — §5 Aggregation](portfolio-engine.md#5-portfolio-aggregation)** para la derivación completa.

---

## 🔗 Cadena de Precios de Valoración {: #valuation-price-chain }

El precio $p(a,t)$ sigue una jerarquía estricta:

1. **Precio de mercado** — PriceHistory con relleno hacia atrás (último $\leq t$)
2. **Último precio de compra** — precio unitario de COMPRA más reciente de $V(u)$ (todos los brókers visibles)
3. **Falta** — posición excluida del NAV

El **PMP** *nunca* se usa para valoración. Consulta **[Portfolio Engine — §2](portfolio-engine.md#2-valuation-price)**.

---

## 📝 Ejemplo

| Componente | Cantidad |
|------------|----------|
| Valor de Mercado de Activos | €32,759 |
| Saldo de Efectivo | €631 |
| En Tránsito | €0 |

$$
\mathrm{NAV} = 32\,759 + 631 + 0 = 33\,390 \text{ EUR}
$$

---

## ⚖️ Distinciones Clave

- **NAV vs [Valor Contable](book-value.md)**: NAV = valor de mercado; valor contable = costo de adquisición. Diferencia = ganancias no realizadas.
- **NAV vs [PnL del Período](period-pnl.md)**: NAV = instantánea; PnL del Período = cambio ajustado por flujo a lo largo del tiempo.

---

## ⚠️ Calidad de Datos

| Fuente de Valoración | Confianza |
|----------------------|-----------|
| `MARKET_PRICE` | Completa — PriceHistory disponible |
| `LAST_BUY_PRICE` | Parcial — usando precio de transacción |
| `MISSING` | Ninguna — excluida del NAV |
