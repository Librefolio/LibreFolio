# 💸 Tipos de Transacciones

LibreFolio registra cada evento financiero como una transacción. Comprender estos tipos es fundamental para un seguimiento preciso de la cartera y los informes fiscales.

## 📋 Transacciones admitidas

| | Type | Code | Description | Cash | Asset | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/buy.png){: width="32" } | **Compra / Venta** | `BUY` / `SELL` | Compra o venta de un activo. | ⬇️⬆️ | ⬆️⬇️ | [📖](buy-sell.md) |
| ![](../../../static/icons/transactions/deposit.png){: width="32" } | **Depósito / Retiro** | `DEPOSIT` / `WITHDRAWAL` | Añadir o retirar efectivo de una cuenta de bróker. | ⬆️⬇️ | — | [📖](deposit-withdrawal.md) |
| ![](../../../static/icons/transactions/dividend.png){: width="32" } | **Dividendo** | `DIVIDEND` | Pago en efectivo generado por una posición de acciones o ETF. | ⬆️ | — | [📖](dividend.md) |
| ![](../../../static/icons/transactions/fee.png){: width="32" } | **Comisión / Impuesto** | `FEE` / `TAX` | Costos asociados con operaciones, mantenimiento de cuenta o impuestos. | ⬇️ | — | [📖](fee.md) |
| ![](../../../static/icons/transactions/interest.png){: width="32" } | **Interés** | `INTEREST` | Intereses recibidos de efectivo, bonos o préstamos P2P. | ⬆️ | — | [📖](interest.md) |
| ![](../../../static/icons/transactions/transfer.png){: width="32" } | **Transferencia / FX** | `TRANSFER_IN/OUT` / `FX_CONVERSION` | Movimiento de activos entre carteras o conversión de divisas. | varía | varía | [📖](transfer.md) |

---

## 🔗 Relacionado

- 📊 **[Tipos de Activos](../asset-types/index.md)** — Los instrumentos sobre los que actúan estas transacciones
- 📅 **[Eventos de Activos](../asset-events/index.md)** — Eventos globales frente a transacciones personales
- 💰 **[Tributación](../../fundamentals/taxation.md)** — Implicaciones fiscales de las transacciones
