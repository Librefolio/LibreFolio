# 💸 Tipos de Transacciones

LibreFolio registra cada evento financiero como una transacción. Comprender estos tipos es crucial para el seguimiento preciso del portafolio y la declaración de impuestos.

## 📋 Transacciones Soportadas

<table>
 <thead>
 <tr>
 <th style="width: 60px; text-align: center;">Icono</th>
 <th style="white-space: nowrap;">Tipo</th>
 <th style="white-space: nowrap;">Código</th>
 <th>Descripción</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/buy.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Compra</strong></td>
 <td style="white-space: nowrap;"><code>BUY</code></td>
 <td>Compra de un activo. Aumenta las tenencias, disminuye el efectivo.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/sell.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Venta</strong></td>
 <td style="white-space: nowrap;"><code>SELL</code></td>
 <td>Venta de un activo. Disminuye las tenencias, aumenta el efectivo. Realiza ganancias y pérdidas (PyG).</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/dividend.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Dividendo</strong></td>
 <td style="white-space: nowrap;"><code>DIVIDEND</code></td>
 <td>Pago en efectivo de una tenencia de acciones o ETFs.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/interest.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Interés</strong></td>
 <td style="white-space: nowrap;"><code>INTEREST</code></td>
 <td>Interés recibido de efectivo, bonos o préstamos P2P.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/deposit.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Depósito</strong></td>
 <td style="white-space: nowrap;"><code>DEPOSIT</code></td>
 <td>Agregar efectivo a un portafolio/cuenta de broker.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/withdrawal.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Retiro</strong></td>
 <td style="white-space: nowrap;"><code>WITHDRAWAL</code></td>
 <td>Retirar efectivo de un portafolio/cuenta de broker.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/fee.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Comisión</strong></td>
 <td style="white-space: nowrap;"><code>FEE</code></td>
 <td>Costo asociado a una operación o mantenimiento de cuenta.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/tax.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Impuesto</strong></td>
 <td style="white-space: nowrap;"><code>TAX</code></td>
 <td>Impuestos pagados sobre dividendos, intereses o ganancias de capital.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/fx-conversion.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Conversión de Divisas</strong></td>
 <td style="white-space: nowrap;"><code>FX_CONVERSION</code></td>
 <td>Intercambio de una moneda por otra.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/transfer.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Transferencia Entrante</strong></td>
 <td style="white-space: nowrap;"><code>TRANSFER_IN</code></td>
 <td>Transfiere activos *hacia* este portafolio desde otro (sin que haya una venta).</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/transfer.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Transferencia Saliente</strong></td>
 <td style="white-space: nowrap;"><code>TRANSFER_OUT</code></td>
 <td>Transfiere activos *fuera de* este portafolio hacia otro (sin que haya una venta).</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/adjustment.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Ajuste</strong></td>
 <td style="white-space: nowrap;"><code>ADJUSTMENT</code></td>
 <td>Corrección manual del saldo o tenencias.</td>
 </tr>
 </tbody>
</table>
