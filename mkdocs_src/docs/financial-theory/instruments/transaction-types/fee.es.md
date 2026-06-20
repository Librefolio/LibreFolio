# ![](../../../static/icons/transactions/fee.png){: width="32" style="vertical-align: middle;" } Comisiones e Impuestos ![](../../../static/icons/transactions/tax.png){: width="32" style="vertical-align: middle;" }

Las **comisiones** y los **impuestos** representan costes que reducen el valor de su cartera. Son tipos de transacciones separados para distinguir entre los costes cobrados por el bróker y las obligaciones impuestas por el gobierno.

---

## 🔑 Propiedades Clave

| Propiedad | Comisión | Impuesto |
|----------|-----|-----|
| **Código** | `FEE` | `TAX` |
| **Efecto en efectivo** | ⬇️ Disminuye el saldo | ⬇️ Disminuye el saldo |
| **Efecto en activos** | — | — |
| **Ejemplos** | Comisión, comisión de custodia, spread | Impuesto sobre las plusvalías, retención fiscal, impuesto de timbre |

---

## 📊 Tipos de Comisiones

| Tipo de Comisión | Descripción | Frecuencia |
|----------|-------------|-----------|
| **Comisión de trading** | Coste por operación cobrado por el bróker | Por transacción |
| **Comisión de custodia** | Cargo por mantenimiento de la cuenta | Mensual/Trimestral |
| **Spread** | Diferencia entre el precio de demanda (bid) y de oferta (ask) | Implícita por operación |
| **Comisión de conversión de divisa** | Coste del cambio de moneda | Por conversión |
| **Comisión de gestión (TER)** | Gasto anual de ETF/Fondo | Deducido del NAV |

---

## 💰 Tipos de Impuestos

| Tipo de Impuesto | Descripción | Cuándo se cobra |
|----------|-------------|-------------|
| **Impuesto sobre las plusvalías** | Impuesto sobre el beneficio realizado por la venta | Al vender |
| **Retención fiscal** | Impuesto deducido en la fuente (dividendos, intereses) | Al pago |
| **Impuesto de timbre** | Impuesto sobre la transacción (ej. stamp duty del Reino Unido) | Al comprar |
| **Impuesto sobre transacciones financieras** | Impuesto sobre operaciones (ej. tasa Tobin en Italia) | Al operar |

---

## 📐 Impacto en los Rendimientos

Las comisiones y los impuestos reducen directamente su rendimiento neto. La relación entre el rendimiento bruto y el neto es:

$$
R_{net} = R_{gross} - \frac{\text{Fees} + \text{Taxes}}{V_{start}}
$$

Donde:

- $R_{gross}$ = rendimiento antes de costes (la rentabilidad del mercado)
- $R_{net}$ = rendimiento después de costes (lo que usted conserva realmente)
- $V_{start}$ = valor de la cartera al inicio del periodo

### 📉 Efecto Compuesto de las Comisiones

En periodos de tenencia prolongados, incluso las comisiones recurrentes pequeñas erosionan los rendimientos significativamente debido al **lastre del interés compuesto**:

$$
V_{final} = V_0 \times (1 + r - f)^n
$$

Donde:

- $V_0$ = inversión inicial
- $r$ = tasa de rendimiento bruto anual (ej., 0.07 para 7%)
- $f$ = tasa de comisión anual (ej., 0.01 para 1%)
- $n$ = número de años

!!! example "El lastre del 1% durante 30 años"

    Con $10,000 invertidos a un rendimiento bruto del 7%:

    - **Sin comisiones**: $10,000 × $(1.07)^{30}$ = **$76,123**
    - **Con comisión del 1%**: $10,000 × $(1.06)^{30}$ = **$57,435**

    La comisión anual del 1% le cuesta **$18,688**, una reducción del 26% en el valor final.

---

## 🔗 Relacionado

- 📈 **[Rendimientos y Tasas de Crecimiento](../../fundamentals/returns.md)** — Cómo se miden los rendimientos (brutos vs netos)
- 💰 **[Tributación](../../fundamentals/taxation.md)** — Teoría fiscal exhaustiva y eficiencia fiscal
- 🛒 **[Compra y Venta](buy-sell.md)** — Comisiones de trading asociadas a las transacciones
- 💱 **[Conversión de divisa](fx-conversion.md)** — Spreads de FX ocultos como comisiones implícitas
