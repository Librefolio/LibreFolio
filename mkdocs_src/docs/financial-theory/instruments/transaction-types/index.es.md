# 💸 Tipos de Transacciones

LibreFolio registra cada evento financiero como una transacción. Comprender estos tipos es crucial para un seguimiento preciso de la cartera y la declaración de impuestos.

## 📋 Transacciones Simples

Estas operan de forma independiente en una sola cuenta de bróker.

| | Tipo | Código | Descripción | Efectivo | Activo | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/buy.png){: width="32" } | **Compra / Venta** | `BUY` / `SELL` | Compra o venta de un activo. | ⬇️⬆️ | ⬆️⬇️ | [📖](buy-sell.md) |
| ![](../../../static/icons/transactions/deposit.png){: width="32" } | **Depósito / Retiro** | `DEPOSIT` / `WITHDRAWAL` | Aportación o retiro de efectivo de una cuenta de bróker. | ⬆️⬇️ | — | [📖](deposit-withdrawal.md) |
| ![](../../../static/icons/transactions/dividend.png){: width="32" } | **Dividendo** | `DIVIDEND` | Pago en efectivo de una posición de acción o ETF. | ⬆️ | — | [📖](dividend.md) |
| ![](../../../static/icons/transactions/fee.png){: width="32" } | **Comisión / Impuesto** | `FEE` / `TAX` | Costos asociados con operaciones, mantenimiento de cuenta o impuestos. | ⬇️ | — | [📖](fee.md) |
| ![](../../../static/icons/transactions/interest.png){: width="32" } | **Interés** | `INTEREST` | Intereses recibidos de efectivo, bonos o préstamos P2P. | ⬆️ | — | [📖](interest.md) |
| ![](../../../static/icons/transactions/adjustment.png){: width="32" } | **Ajuste** | `ADJUSTMENT` | Corrección manual de saldos. | ± | ± | [📖](adjustment.md) |

## 🔀 Transacciones Compuestas

Estas representan movimientos **entre** cuentas o divisas. Generan dos entradas vinculadas que se equilibran entre sí.

| | Tipo | Código | Descripción | Efectivo | Activo | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/transfer.png){: width="32" } | **Transferencia de Activos** | `TRANSFER` | Movimiento de valores entre brókers. | — | ⬆️⬇️ | [📖](transfer.md) |
| ![](../../../static/icons/transactions/cash-transfer.png){: width="32" } | **Transferencia de Efectivo** | `CASH_TRANSFER` | Transferencia bancaria entre brókers. | ⬆️⬇️ | — | [📖](cash-transfer.md) |
| ![](../../../static/icons/transactions/fx-conversion.png){: width="32" } | **Conversión de divisa** | `FX_CONVERSION` | Cambio de moneda dentro de un bróker. | ⬆️⬇️ | — | [📖](fx-conversion.md) |

---

## 🔗 Relacionado

- 📊 **[Tipos de Activos](../asset-types/index.md)** — Los instrumentos sobre los que actúan estas transacciones
- 📅 **[Eventos de Activos](../asset-events/index.md)** — Eventos globales frente a transacciones personales
- 💰 **[Tributación](../../fundamentals/taxation.md)** — Implicaciones fiscales de las transacciones
