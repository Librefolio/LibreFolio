# 💸 Types de transactions

LibreFolio enregistre chaque événement financier sous forme de transaction. La compréhension de ces types est cruciale pour un suivi précis du portefeuille et la déclaration fiscale.

## 📋 Transactions supportées

<table>
 <thead>
 <tr>
 <th style="width: 60px; text-align: center;">Icône</th>
 <th style="white-space: nowrap;">Type</th>
 <th style="white-space: nowrap;">Code</th>
 <th>Description</th>
 <th style="text-align: center;">Liquidités</th>
 <th style="text-align: center;">Actif</th>
 <th style="white-space: nowrap;">Détails</th>
 </tr>
 </thead>
 <tbody>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/buy.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Achat / Vente</strong></td>
 <td style="white-space: nowrap;"><code>BUY</code> / <code>SELL</code></td>
 <td>Achat ou vente d'un actif.</td>
 <td style="text-align: center;">⬇️⬆️</td>
 <td style="text-align: center;">⬆️⬇️</td>
 <td><a href="buy-sell/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/deposit.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Dépôt / Retrait</strong></td>
 <td style="white-space: nowrap;"><code>DEPOSIT</code> / <code>WITHDRAWAL</code></td>
 <td>Ajout ou retrait de liquidités d'un compte courtier.</td>
 <td style="text-align: center;">⬆️⬇️</td>
 <td style="text-align: center;">—</td>
 <td><a href="deposit-withdrawal/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/dividend.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Dividende</strong></td>
 <td style="white-space: nowrap;"><code>DIVIDEND</code></td>
 <td>Paiement en espèces provenant d'une position en actions ou ETF.</td>
 <td style="text-align: center;">⬆️</td>
 <td style="text-align: center;">—</td>
 <td><a href="dividend/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/fee.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Frais / Taxe</strong></td>
 <td style="white-space: nowrap;"><code>FEE</code> / <code>TAX</code></td>
 <td>Coûts associés aux transactions, à la maintenance du compte ou de taxes.</td>
 <td style="text-align: center;">⬇️</td>
 <td style="text-align: center;">—</td>
 <td><a href="fee/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/interest.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Intérêts</strong></td>
 <td style="white-space: nowrap;"><code>INTEREST</code></td>
 <td>Intérêts reçus sur les liquidités, des obligations ou des prêts P2P.</td>
 <td style="text-align: center;">⬆️</td>
 <td style="text-align: center;">—</td>
 <td><a href="interest/">📖</a></td>
 </tr>
 <tr>
 <td style="text-align: center;"><img src="../../../static/icons/transactions/transfer.png" width="32" /></td>
 <td style="white-space: nowrap;"><strong>Transfert / FX</strong></td>
 <td style="white-space: nowrap;"><code>TRANSFER_IN/OUT</code> / <code>FX_CONVERSION</code></td>
 <td>Déplacement d'actifs entre portefeuilles ou conversion de devises.</td>
 <td style="text-align: center;">variable</td>
 <td style="text-align: center;">variable</td>
 <td><a href="transfer/">📖</a></td>
 </tr>
 </tbody>
</table>

---

## 🔗 Liens connexes

- 📊 **[Types d'actifs](../asset-types/index.md)** — Les instruments sur lesquels portent ces transactions
- 📅 **[Événements d'actifs](../asset-events/index.md)** — Événements globaux vs transactions personnelles
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Implications fiscales des transactions
