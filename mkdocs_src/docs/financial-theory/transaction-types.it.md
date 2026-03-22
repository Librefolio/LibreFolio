# 💸 Tipi di Transazione

LibreFolio registra ogni evento finanziario come una transazione. Comprendere questi tipi è fondamentale per una corretta tenuta del portafoglio e per la dichiarazione fiscale.

## 📋 Transazioni Supportate

<table>
 <thead>
 <tr>
 <th style="width: 60px; text-align: center;">Icona</th>
 <th style="white-space: nowrap;">Tipo</th>
 <th style="white-space: nowrap;">Codice</th>
 <th>Descrizione</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/buy.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Acquisto</strong></td>
 <td style="white-space: nowrap;"><code>BUY</code></td>
 <td>Acquisto di un asset. Aumenta le **posizioni**, diminuisce la liquidità.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/sell.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Vendita</strong></td>
 <td style="white-space: nowrap;"><code>SELL</code></td>
 <td>Vendita di un asset. Diminuisce le **posizioni**, aumenta la liquidità. Realizza plus/minusvalenze (P&L).</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/dividend.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Dividendo</strong></td>
 <td style="white-space: nowrap;"><code>DIVIDEND</code></td>
 <td>Pagamento in contanti da una posizione in azioni o ETF.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/interest.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Interesse</strong></td>
 <td style="white-space: nowrap;"><code>INTEREST</code></td>
 <td>Interessi ricevuti da liquidità, obbligazioni o prestiti P2P.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/deposit.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Deposito</strong></td>
 <td style="white-space: nowrap;"><code>DEPOSIT</code></td>
 <td>Aggiunta di liquidità a un portafoglio/conto broker.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/withdrawal.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Prelievo</strong></td>
 <td style="white-space: nowrap;"><code>WITHDRAWAL</code></td>
 <td>Rimozione di liquidità da un portafoglio/conto broker.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/fee.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Commissione</strong></td>
 <td style="white-space: nowrap;"><code>FEE</code></td>
 <td>Costo associato a un'operazione di trading o ai costi di gestione del conto.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/tax.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Imposta</strong></td>
 <td style="white-space: nowrap;"><code>TAX</code></td>
 <td>Imposte pagate su dividendi, interessi o plusvalenze.</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/fx-conversion.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Cambio Valuta</strong></td>
 <td style="white-space: nowrap;"><code>FX_CONVERSION</code></td>
 <td>Scambio di una valuta con un'altra (conversione FX).</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/transfer.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Trasferimento In</strong></td>
 <td style="white-space: nowrap;"><code>TRANSFER_IN</code></td>
 <td>Trasferimento di asset **in** questo portafoglio da un altro (senza una vendita).</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/transfer.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Trasferimento Out</strong></td>
 <td style="white-space: nowrap;"><code>TRANSFER_OUT</code></td>
 <td>Trasferimento di asset **da** questo portafoglio a un altro (senza una vendita).</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../static/icons/transactions/adjustment.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Rettifica</strong></td>
 <td style="white-space: nowrap;"><code>ADJUSTMENT</code></td>
 <td>Correzione manuale del saldo o delle **posizioni**.</td>
 </tr>
 </tbody>
</table>
