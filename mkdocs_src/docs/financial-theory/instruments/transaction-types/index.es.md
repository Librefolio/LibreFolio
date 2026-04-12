# 💸 Tipos de Transacciones

LibreFolio registra cada evento financiero como una transacción. Comprender estos tipos es fundamental para un seguimiento preciso de la cartera y los informes fiscales.

## 📋 Transacciones admitidas

<table>
 <thead>
 <tr>
 <th style="width: 60px; text-align: center;">Icono</th>
 <th style="white-space: nowrap;">Tipo</th>
 <th style="white-space: nowrap;">Código</th>
 <th>Descripción</th>
 <th style="text-align: center;">Efectivo</th>
 <th style="text-align: center;">Activo</th>
 <th style="white-space: nowrap;">Detalles</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/buy.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Compra / Venta</strong></td>
 <td style="white-space: nowrap;"><code>BUY</code> / <code>SELL</code></td>
 <td>Compra o venta de un activo.</td>
 <td style="text-align: center;">⬇️⬆️</td>
 <td style="text-align: center;">⬆️⬇️</td>
 <td><a href="buy-sell/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/deposit.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Depósito / Retiro</strong></td>
 <td style="white-space: nowrap;"><code>DEPOSIT</code> / <code>WITHDRAWAL</code></td>
 <td>Añadir o retirar efectivo de una cuenta de bróker.</td>
 <td style="text-align: center;">⬆️⬇️</td>
 <td style="text-align: center;">—</td>
 <td><a href="deposit-withdrawal/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/dividend.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Dividendo</strong></td>
 <td style="white-space: nowrap;"><code>DIVIDEND</code></td>
 <td>Pago en efectivo generado por una posición de acciones o ETF.</td>
 <td style="text-align: center;">⬆️</td>
 <td style="text-align: center;">—</td>
 <td><a href="dividend/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/fee.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Comisión / Impuesto</strong></td>
 <td style="white-space: nowrap;"><code>FEE</code> / <code>TAX</code></td>
 <td>Costos asociados con operaciones, mantenimiento de cuenta o impuestos.</td>
 <td style="text-align: center;">⬇️</td>
 <td style="text-align: center;">—</td>
 <td><a href="fee/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/interest.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Interés</strong></td>
 <td style="white-space: nowrap;"><code>INTEREST</code></td>
 <td>Intereses recibidos de efectivo, bonos o préstamos P2P.</td>
 <td style="text-align: center;">⬆️</td>
 <td style="text-align: center;">—</td>
 <td><a href="interest/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/transfer.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Transferencia / FX</strong></td>
 <td style="white-space: nowrap;"><code>TRANSFER_IN/OUT</code> / <code>FX_CONVERSION</code></td>
 <td>Movimiento de activos entre carteras o conversión de divisas.</td>
 <td style="text-align: center;">varía</td>
 <td style="text-align: center;">varía</td>
 <td><a href="transfer/">📖</a></td>
 </tr>
 </tbody>
</table>

---

## 🔗 Relacionado

- 📊 **[Tipos de Activos](../asset-types/index.md)** — Los instrumentos sobre los que actúan estas transacciones
- 📅 **[Eventos de Activos](../asset-events/index.md)** — Eventos globales frente a transacciones personales
- 💰 **[Tributación](../../fundamentals/taxation.md)** — Implicaciones fiscales de las transacciones
