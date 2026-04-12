# 💸 Tipi di Transazione

LibreFolio registra ogni evento finanziario come una transazione. Comprendere questi tipi è fondamentale per un monitoraggio accurato del portafoglio e per la rendicontazione fiscale.

## 📋 Transazioni Supportate

<table>
 <thead>
 <tr>
 <th style="width: 60px; text-align: center;">Icona</th>
 <th style="white-space: nowrap;">Tipo</th>
 <th style="white-space: nowrap;">Codice</th>
 <th>Descrizione</th>
 <th style="text-align: center;">Liquidità</th>
 <th style="text-align: center;">Asset</th>
 <th style="white-space: nowrap;">Dettagli</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/buy.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Acquisto / Vendita</strong></td>
 <td style="white-space: nowrap;"><code>BUY</code> / <code>SELL</code></td>
 <td>Acquisto o vendita di un asset.</td>
 <td style="text-align: center;">⬇️⬆️</td>
 <td style="text-align: center;">⬆️⬇️</td>
 <td><a href="buy-sell/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/deposit.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Deposito / Prelievo</strong></td>
 <td style="white-space: nowrap;"><code>DEPOSIT</code> / <code>WITHDRAWAL</code></td>
 <td>Aggiunta o rimozione di liquidità da un conto broker.</td>
 <td style="text-align: center;">⬆️⬇️</td>
 <td style="text-align: center;">—</td>
 <td><a href="deposit-withdrawal/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/dividend.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Dividendo</strong></td>
 <td style="white-space: nowrap;"><code>DIVIDEND</code></td>
 <td>Pagamento in liquidità da una posizione in azioni o ETF.</td>
 <td style="text-align: center;">⬆️</td>
 <td style="text-align: center;">—</td>
 <td><a href="dividend/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/fee.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Commissione / Tassa</strong></td>
 <td style="white-space: nowrap;"><code>FEE</code> / <code>TAX</code></td>
 <td>Costi associati a operazioni, gestione del conto o tasse.</td>
 <td style="text-align: center;">⬇️</td>
 <td style="text-align: center;">—</td>
 <td><a href="fee/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/interest.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Interesse</strong></td>
 <td style="white-space: nowrap;"><code>INTEREST</code></td>
 <td>Interessi ricevuti da liquidità, obbligazioni o prestiti P2P.</td>
 <td style="text-align: center;">⬆️</td>
 <td style="text-align: center;">—</td>
 <td><a href="interest/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/transfer.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Trasferimento / FX</strong></td>
 <td style="white-space: nowrap;"><code>TRANSFER_IN/OUT</code> / <code>FX_CONVERSION</code></td>
 <td>Spostamento di asset tra portafogli o conversione di valute.</td>
 <td style="text-align: center;">variabile</td>
 <td style="text-align: center;">variabile</td>
 <td><a href="transfer/">📖</a></td>
 </tr>
 </tbody>
</table>

---

## 🔗 Correlati

- 📊 **[Tipi di Asset](../asset-types/index.md)** — Gli strumenti su cui agiscono queste transazioni
- 📅 **[Eventi Asset](../asset-events/index.md)** — Eventi globali vs transazioni personali
- 💰 **[Tassazione](../../fundamentals/taxation.md)** — Implicazioni fiscali delle transazioni
