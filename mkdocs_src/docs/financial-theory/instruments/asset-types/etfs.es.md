# ![](../../../static/icons/asset-types/etf.png){: width="32" style="vertical-align: middle;" } ETFs (Exchange Traded Funds)

Un **ETF** es una cesta de valores (acciones, bonos, materias primas o una mezcla) que cotiza en bolsa como si fuera una sola acción. Los ETFs combinan la diversificación de los fondos de inversión con la flexibilidad de negociación en tiempo real de las acciones.

---

## 🔑 Características Clave

| Propiedad | Detalle |
|----------|--------|
| **Código en LibreFolio** | `ETF` |
| **Precio** | Precios de bolsa en tiempo real, como las acciones |
| **Moneda** | Denominado en la moneda de la bolsa de cotización |
| **Dividendos** | Pueden distribuir (Dist) o reinvertir internamente (Acc) |
| **TER** | Total Expense Ratio — comisión de gestión anual deducida del NAV |
| **Proveedores típicos** | Yahoo Finance, justETF, CSS Scraper |

---

## 📊 Acumulación vs Distribución

| Característica | Acumulación (Acc) | Distribución (Dist) |
|---------|-------------------|-------------------|
| **Dividendos** | Reinvertidos internamente | Pagados a los tenedores |
| **Evento fiscal** | Solo al vender | En cada distribución |
| **Interés compuesto** | Crecimiento compuesto total | Reducido por la carga fiscal |
| **Ideal para** | Crecimiento a largo plazo | Necesidades de ingresos |

La [ventaja del diferimiento fiscal](../../fundamentals/taxation.md#tax-deferral-advantage) de los ETFs de acumulación puede ser significativa en horizontes temporales largos.

---

## 📈 NAV vs Precio de Mercado

- **NAV** (Net Asset Value): El valor real de las posiciones subyacentes ÷ participaciones en circulación. Se calcula diariamente.
- **Precio de Mercado**: El precio al que el ETF cotiza realmente en la bolsa. Puede desviarse ligeramente del NAV.
- **Prima/Descuento**: Cuando el precio de mercado > NAV, el ETF cotiza con prima; cuando < NAV, con descuento.

---

## 🔍 Seguimiento de Índices

La mayoría de los ETFs siguen un índice benchmark (por ejemplo, S&P 500, MSCI World). El **error de seguimiento** (tracking error) mide cuánto se desvía el rendimiento del ETF respecto al benchmark:

$$
TE = \sigma(R_{ETF} - R_{index})
$$

Menor error de seguimiento = mejor replicación del índice.

---

## 🔗 Relacionado

- 💰 **[Eventos de Dividendos](../asset-events/dividend.md)** — Distribuciones de las posiciones del ETF
- 📈 **[Índice y Benchmark](index-benchmark.md)** — Cómo funcionan los benchmarks
- 💰 **[Fiscalidad](../../fundamentals/taxation.md)** — Implicaciones fiscales de Acc vs Dist
