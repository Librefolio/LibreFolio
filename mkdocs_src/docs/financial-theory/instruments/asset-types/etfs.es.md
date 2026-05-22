# ![](../../../static/icons/asset-types/etf.png){: width="32" style="vertical-align: middle;" } ETFs (Fondos Cotizados en Bolsa)

Un **ETF** es una cesta de valores (acciones, bonos, materias primas o una combinación) que cotiza en una bolsa como una sola acción. Los ETFs combinan la diversificación de los fondos mutuos con la flexibilidad de negociación en tiempo real de las acciones.

---

## 🔑 Características Clave

| Propiedad | Detalle |
|----------|--------|
| **Código en LibreFolio** | `ETF` |
| **Cotización** | Precios de bolsa en tiempo real, como las acciones |
| **Moneda** | Denominada en la moneda de la bolsa donde cotiza |
| **Dividendos** | Pueden distribuir (Dist) o reinvertir internamente (Acc) |
| **TER** | Ratio de Gastos Totales — comisión anual de gestión deducida del NAV |
| **Proveedores típicos** | Yahoo Finance, justETF, CSS Scraper |

---

## 📊 Acumulativos vs Distributivos

| Característica | Acumulativo (Acc) | Distributivo (Dist) |
|---------|-------------------|-------------------|
| **Dividendos** | Reinvertidos internamente | Pagados a los tenedores |
| **Evento fiscal** | Solo en la venta | En cada distribución |
| **Capitalización compuesta** | Crecimiento compuesto total | Reducido por el efecto fiscal |
| **Mejor para** | Crecimiento a largo plazo | Necesidades de ingresos |

La [ventaja de diferimiento fiscal](../../fundamentals/taxation.md#tax-deferral-advantage) de los ETFs acumulativos puede ser significativa en horizontes largos.

---

## 📈 NAV vs Precio de Mercado

- **NAV** (Valor Liquidativo): El valor real de las participaciones subyacentes ÷ acciones en circulación. Calculado diariamente.
- **Precio de Mercado**: El precio real al que se negocia el ETF en la bolsa. Puede desviarse ligeramente del NAV.
- **Prima/Descuento**: Cuando el precio de mercado > NAV, el ETF cotiza con prima; cuando < NAV, con descuento.

---

## 🔍 Seguimiento del Índice

La mayoría de los ETFs siguen un benchmark (p. ej., S&P 500, MSCI World). El **error de seguimiento** mide cuánto se desvía el rendimiento del ETF del índice:

$$
TE = \sigma(R_{ETF} - R_{index})
$$

Un error de seguimiento más bajo = mejor replicación del benchmark.

---

## 🔗 Relacionados

- 💰 **[Eventos de Dividendos](../asset-events/dividend.md)** — Distribuciones de las participaciones del ETF
- 📈 **[Índice y Benchmark](index-benchmark.md)** — Cómo funcionan los benchmarks
- 💰 **[Fiscalidad](../../fundamentals/taxation.md)** — Implicaciones fiscales de Acc vs Dist
