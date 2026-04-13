# 💸 Types de transactions

LibreFolio enregistre chaque événement financier sous forme de transaction. La compréhension de ces types est cruciale pour un suivi précis du portefeuille et la déclaration fiscale.

## 📋 Transactions supportées

| | Type | Code | Description | Cash | Asset | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/buy.png){: width="32" } | **Achat / Vente** | `BUY` / `SELL` | Achat ou vente d'un actif. | ⬇️⬆️ | ⬆️⬇️ | [📖](buy-sell.md) |
| ![](../../../static/icons/transactions/deposit.png){: width="32" } | **Dépôt / Retrait** | `DEPOSIT` / `WITHDRAWAL` | Ajout ou retrait de liquidités d'un compte courtier. | ⬆️⬇️ | — | [📖](deposit-withdrawal.md) |
| ![](../../../static/icons/transactions/dividend.png){: width="32" } | **Dividende** | `DIVIDEND` | Paiement en espèces provenant d'une position en actions ou ETF. | ⬆️ | — | [📖](dividend.md) |
| ![](../../../static/icons/transactions/fee.png){: width="32" } | **Frais / Taxe** | `FEE` / `TAX` | Coûts associés aux transactions, à la maintenance du compte ou de taxes. | ⬇️ | — | [📖](fee.md) |
| ![](../../../static/icons/transactions/interest.png){: width="32" } | **Intérêts** | `INTEREST` | Intérêts reçus sur les liquidités, des obligations ou des prêts P2P. | ⬆️ | — | [📖](interest.md) |
| ![](../../../static/icons/transactions/transfer.png){: width="32" } | **Transfert / FX** | `TRANSFER_IN/OUT` / `FX_CONVERSION` | Déplacement d'actifs entre portefeuilles ou conversion de devises. | variable | variable | [📖](transfer.md) |

---

## 🔗 Liens connexes

- 📊 **[Types d'actifs](../asset-types/index.md)** — Les instruments sur lesquels portent ces transactions
- 📅 **[Événements d'actifs](../asset-events/index.md)** — Événements globaux vs transactions personnelles
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Implications fiscales des transactions
