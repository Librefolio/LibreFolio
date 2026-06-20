# 💸 Tipos de Transacción

LibreFolio registra cada evento financiero como una transacción. Comprender estos tipos es fundamental para un seguimiento preciso de la cartera y la declaración de impuestos.

## 📋 Transacciones Únicas

Estas operan de manera independiente en una sola cuenta de bróker.

| | Tipo | Código | Descripción | Efectivo | Activo | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/buy.png){: width="32" } ![](../../../static/icons/transactions/sell.png){: width="32" } | **Compra / Venta** | `BUY` / `SELL` | Compra o venta de un activo. | ⬇️⬆️ | ⬆️⬇️ | [📖](buy-sell.md) |
| ![](../../../static/icons/transactions/deposit.png){: width="32" } ![](../../../static/icons/transactions/withdrawal.png){: width="32" } | **Depósito / Retirada** | `DEPOSIT` / `WITHDRAWAL` | Ingreso o retiro de efectivo de una cuenta de bróker. | ⬆️⬇️ | — | [📖](deposit-withdrawal.md) |
| ![](../../../static/icons/transactions/dividend.png){: width="32" } ![](../../../static/icons/transactions/interest.png){: width="32" } | **Dividendo / Interés** | `DIVIDEND` / `INTEREST` | Rendimiento recibido de activos de renta variable o renta fija. | ⬆️ | — | [📖](dividend-interest.md) |
| ![](../../../static/icons/transactions/fee.png){: width="32" } ![](../../../static/icons/transactions/tax.png){: width="32" } | **Comisión / Impuesto** | `FEE` / `TAX` | Costos asociados con operaciones, mantenimiento de cuenta o impuestos. | ⬇️ | — | [📖](fee.md) |
| ![](../../../static/icons/transactions/adjustment.png){: width="32" } | **Ajuste** | `ADJUSTMENT` | Corrección manual de los saldos. | ± | ± | [📖](adjustment.md) |

## 🔀 Transacciones Compuestas

Estas representan movimientos **entre** cuentas o divisas. Generan dos asientos vinculados que se compensan entre sí.

| | Tipo | Código | Descripción | Efectivo | Activo | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/transfer.png){: width="32" } | **Transferencia de Activos** | `TRANSFER` | Traslado de valores entre brókeres. | — | ⬆️⬇️ | [📖](transfer.md) |
| ![](../../../static/icons/transactions/cash-transfer.png){: width="32" } | **Transferencia de Efectivo** | `CASH_TRANSFER` | Transferencia bancaria entre brókeres. | ⬆️⬇️ | — | [📖](cash-transfer.md) |
| ![](../../../static/icons/transactions/fx-conversion.png){: width="32" } | **Conversión de divisas** | `FX_CONVERSION` | Cambio de moneda dentro de un bróker. | ⬆️⬇️ | — | [📖](fx-conversion.md) |

---

## 🔗 Relacionado

- 📊 **[Tipos de Activos](../asset-types/index.md)** — Los instrumentos sobre los que actúan estas transacciones
- 📅 **[Eventos de Activos](../asset-events/index.md)** — Eventos globales frente a transacciones personales
- 💰 **[Impuestos](../../fundamentals/taxation.md)** — Implicaciones fiscales de las transacciones
