# 💸 Types de transactions

LibreFolio enregistre chaque événement financier en tant que transaction. La compréhension de ces types est cruciale pour un suivi précis du portefeuille et pour les rapports fiscaux.

## 📋 Transactions simples

Celles-ci s'effectuent indépendamment sur un seul compte de courtage.

| | Type | Code | Description | Liquidités | Actif | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/buy.png){: width="32" } | **Achat / Vente** | `BUY` / `SELL` | Achat ou vente d'un actif. | ⬇️⬆️ | ⬆️⬇️ | [📖](buy-sell.md) |
| ![](../../../static/icons/transactions/deposit.png){: width="32" } | **Dépôt / Retrait** | `DEPOSIT` / `WITHDRAWAL` | Ajout ou retrait de liquidités d'un compte de courtage. | ⬆️⬇️ | — | [📖](deposit-withdrawal.md) |
| ![](../../../static/icons/transactions/dividend.png){: width="32" } | **Dividende** | `DIVIDEND` | Paiement en espèces provenant d'une position d'actions ou d'ETF. | ⬆️ | — | [📖](dividend.md) |
| ![](../../../static/icons/transactions/fee.png){: width="32" } | **Frais / Taxe** | `FEE` / `TAX` | Coûts associés aux transactions, à la maintenance du compte ou aux taxes. | ⬇️ | — | [📖](fee.md) |
| ![](../../../static/icons/transactions/interest.png){: width="32" } | **Intérêt** | `INTEREST` | Intérêts reçus sur les liquidités, les obligations ou les prêts P2P. | ⬆️ | — | [📖](interest.md) |
| ![](../../../static/icons/transactions/adjustment.png){: width="32" } | **Ajustement** | `ADJUSTMENT` | Correction manuelle des soldes. | ± | ± | [📖](adjustment.md) |

## 🔀 Transactions composites

Celles-ci représentent des mouvements **entre** des comptes ou des devises. Elles produisent deux écritures liées qui s'équilibrent.

| | Type | Code | Description | Liquidités | Actif | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/transfer.png){: width="32" } | **Transfert d'actifs** | `TRANSFER` | Déplacement de titres entre courtiers. | — | ⬆️⬇️ | [📖](transfer.md) |
| ![](../../../static/icons/transactions/cash-transfer.png){: width="32" } | **Transfert de fonds** | `CASH_TRANSFER` | Virement bancaire entre courtiers. | ⬆️⬇️ | — | [📖](cash-transfer.md) |
| ![](../../../static/icons/transactions/fx-conversion.png){: width="32" } | **Conversion de devise** | `FX_CONVERSION` | Change de devises au sein d'un courtier. | ⬆️⬇️ | — | [📖](fx-conversion.md) |

---

## 🔗 Liens connexes

- 📊 **[Types d'actifs](../asset-types/index.md)** — Les instruments sur lesquels s'appliquent ces transactions
- 📅 **[Événements d'actifs](../asset-events/index.md)** — Événements globaux vs transactions personnelles
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Implications fiscales des transactions
