# <img src="../../../static/icons/transactions/fee.png" width="32" style="vertical-align: middle;" /> Comisiones e Impuestos

Las **comisiones** y los **impuestos** representan costes que reducen el valor de su cartera. Son tipos de transacciones independientes para distinguir entre los costes cobrados por el bróker y las obligaciones impuestas por el gobierno.

---

## 🔑 Propiedades Clave

| Propiedad | Comisión | Impuesto |
|----------|-----|-----|
| **Código** | `FEE` | `TAX` |
| **Efecto en efectivo** | ⬇️ Disminuye el saldo | ⬇️ Disminuye el saldo |
| **Efecto en activos** | — | — |
| **Ejemplos** | Comisión, tasa de custodia, spread | Impuesto sobre plusvalías, retención fiscal, impuesto de sellos |

---

## 📊 Tipos de Comisiones

| Tipo de Comisión | Descripción | Frecuencia |
|----------|-------------|-----------|
| **Comisión de trading** | Coste por operación cobrado por el bróker | Por transacción |
| **Tasa de custodia** | Cargo por mantenimiento de cuenta | Mensual/Trimestral |
| **Spread** | Diferencia entre el precio de compra (bid) y el de venta (ask) | Implícito por operación |
| **Comisión de conversión FX** | Coste del cambio de moneda | Por conversión |
| **Comisión de gestión (TER)** | Gasto anual de ETF/Fondo | Deducido del NAV |

---

## 💰 Tipos de Impuestos

| Tipo de Impuesto | Descripción | Cuándo se cobra |
|----------|-------------|-------------|
| **Impuesto sobre plusvalías** | Impuesto sobre el beneficio realizado por la venta | En la venta |
| **Retención fiscal** | Impuesto deducido en la fuente (dividendos, intereses) | En el pago |
| **Impuesto de sellos** | Impuesto sobre la transacción (ej. stamp duty del Reino Unido) | En la compra |
| **Impuesto sobre transacciones financieras** | Impuesto sobre operaciones (ej. tasa Tobin italiana) | En la operación |

---

## 📐 Impacto en los Rendimientos

Las comisiones y los impuestos reducen directamente su rendimiento neto:

$$
R_{net} = R_{gross} - \frac{\text{Comisiones} + \text{Impuestos}}{V_{start}}
$$

A largo plazo, incluso las comisiones recurrentes pequeñas tienen un efecto compuesto significativo:

$$
V_{final} = V_0 \times (1 + r - f)^n
$$

donde $f$ es la tasa de comisión anual. Una comisión anual del 1% sobre un rendimiento del 7% durante 30 años reduce el valor final en un **26%**.

---

## 🔗 Relacionado

- 💰 **[Tributación](../../fundamentals/taxation.md)** — Teoría fiscal exhaustiva
- 🛒 **[Compra y Venta](buy-sell.md)** — Comisiones cobradas en las transacciones
