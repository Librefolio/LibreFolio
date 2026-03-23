# 💸 Types de Transactions

LibreFolio enregistre chaque événement financier sous forme de transaction. Comprendre ces types est essentiel pour un suivi de portefeuille précis et une déclaration fiscale correcte.

## 📋 Transactions Prises en Charge

<table>
 <thead>
 <tr>
 <th style="width: 60px; text-align: center;">Icône</th>
 <th style="white-space: nowrap;">Type</th>
 <th style="white-space: nowrap;">Code</th>
 <th>Description</th>
 <th style="text-align: center;">Trésorerie</th>
 <th style="text-align: center;">Actif</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/buy.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Achat</strong></td>
 <td style="white-space: nowrap;"><code>BUY</code></td>
 <td>Achat d'un actif. Augmente les positions, réduit la trésorerie.</td>
 <td style="text-align: center;">⬇️</td>
 <td style="text-align: center;">⬆️</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/sell.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Vente</strong></td>
 <td style="white-space: nowrap;"><code>SELL</code></td>
 <td>Vente d'un actif. Réduit les positions, augmente la trésorerie. Entraîne la réalisation de gains ou de pertes (P&L).</td>
 <td style="text-align: center;">⬆️</td>
 <td style="text-align: center;">⬇️</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/dividend.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Dividende</strong></td>
 <td style="white-space: nowrap;"><code>DIVIDEND</code></td>
 <td>Paiement en espèces d'une action ou d'un ETF.</td>
 <td style="text-align: center;">⬆️</td>
 <td style="text-align: center;">—</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/interest.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Intérêts</strong></td>
 <td style="white-space: nowrap;"><code>INTEREST</code></td>
 <td>Intérêts reçus d'une trésorerie, d'obligations ou de prêts P2P.</td>
 <td style="text-align: center;">⬆️</td>
 <td style="text-align: center;">—</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/deposit.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Dépôt</strong></td>
 <td style="white-space: nowrap;"><code>DEPOSIT</code></td>
 <td>Ajout de trésorerie à un portefeuille/compte courtier.</td>
 <td style="text-align: center;">⬆️</td>
 <td style="text-align: center;">—</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/withdrawal.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Retrait</strong></td>
 <td style="white-space: nowrap;"><code>WITHDRAWAL</code></td>
 <td>Retrait de trésorerie d'un portefeuille/compte courtier.</td>
 <td style="text-align: center;">⬇️</td>
 <td style="text-align: center;">—</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/fee.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Frais</strong></td>
 <td style="white-space: nowrap;"><code>FEE</code></td>
 <td>Coût associé à une transaction ou à la maintenance du compte.</td>
 <td style="text-align: center;">⬇️</td>
 <td style="text-align: center;">—</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/tax.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Taxe</strong></td>
 <td style="white-space: nowrap;"><code>TAX</code></td>
 <td>Prélèvements fiscaux sur les dividendes, intérêts ou gains en capital.</td>
 <td style="text-align: center;">⬇️</td>
 <td style="text-align: center;">—</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/fx-conversion.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Conversion de devises</strong></td>
 <td style="white-space: nowrap;"><code>FX_CONVERSION</code></td>
 <td>Échange d'une devise contre une autre.</td>
 <td style="text-align: center;">⬆️⬇️</td>
 <td style="text-align: center;">—</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/transfer.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Transfert Entrant</strong></td>
 <td style="white-space: nowrap;"><code>TRANSFER_IN</code></td>
 <td>Déplacement d'actifs <em>vers</em> ce portefeuille depuis un autre (sans opération de vente).</td>
 <td style="text-align: center;">—</td>
 <td style="text-align: center;">⬆️</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/transfer.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Transfert Sortant</strong></td>
 <td style="white-space: nowrap;"><code>TRANSFER_OUT</code></td>
 <td>Déplacement d'actifs <em>hors de</em> ce portefeuille vers un autre (sans opération de vente).</td>
 <td style="text-align: center;">—</td>
 <td style="text-align: center;">⬇️</td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/adjustment.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Rectification</strong></td>
 <td style="white-space: nowrap;"><code>ADJUSTMENT</code></td>
 <td>Correction manuelle du solde ou des positions.</td>
 <td style="text-align: center;">⬆️⬇️</td>
 <td style="text-align: center;">⬆️⬇️</td>
 </tr>
 </tbody>
</table>
