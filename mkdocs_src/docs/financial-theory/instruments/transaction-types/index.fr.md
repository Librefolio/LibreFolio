# 💸 Types de Transactions

LibreFolio enregistre chaque événement financier sous forme de transaction. La compréhension de ces types est cruciale pour un suivi précis du portefeuille et le reporting fiscal.

## 📋 Transactions Simples

Celles-ci opèrent indépendamment sur un seul compte de courtier.

| | Type | Code | Description | Liquidités | Actif | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/buy.png){: width="32" } ![](../../../static/icons/transactions/sell.png){: width="32" } | **Achat / Vente** | `BUY` / `SELL` | Achat ou vente d'un actif. | ⬇️⬆️ | ⬆️⬇️ | [📖](buy-sell.md) |
| ![](../../../static/icons/transactions/deposit.png){: width="32" } ![](../../../static/icons/transactions/withdrawal.png){: width="32" } | **Dépôt / Retrait** | `DEPOSIT` / `WITHDRAWAL` | Ajout ou retrait de liquidités d'un compte de courtier. | ⬆️⬇️ | — | [📖](deposit-withdrawal.md) |
| ![](../../../static/icons/transactions/dividend.png){: width="32" } ![](../../../static/icons/transactions/interest.png){: width="32" } | **Dividende / Intérêt** | `DIVIDEND` / `INTEREST` | Rendement reçu d'actifs en actions ou à revenu fixe. | ⬆️ | — | [📖](dividend-interest.md) |
| ![](../../../static/icons/transactions/fee.png){: width="32" } ![](../../../static/icons/transactions/tax.png){: width="32" } | **Frais / Taxe** | `FEE` / `TAX` | Coûts associés aux transactions, à la maintenance du compte ou aux taxes. | ⬇️ | — | [📖](fee.md) |
| ![](../../../static/icons/transactions/adjustment.png){: width="32" } | **Ajustement** | `ADJUSTMENT` | Correction manuelle des soldes. | ± | ± | [📖](adjustment.md) |

## 🔀 Transactions Composites

Celles-ci représentent des mouvements **entre** des comptes ou des devises. Elles produisent deux entrées liées qui s'équilibrent mutuellement.

| | Type | Code | Description | Liquidités | Actif | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/transfer.png){: width="32" } | **Transfert d'Actifs** | `TRANSFER` | Déplacement de titres entre courtiers. | — | ⬆️⬇️ | [📖](transfer.md) |
| ![](../../../static/icons/transactions/cash-transfer.png){: width="32" } | **Transfert de liquidités** | `CASH_TRANSFER` | Virement bancaire entre courtiers. | ⬆️⬇️ | — | [📖](cash-transfer.md) |
| ![](../../../static/icons/transactions/fx-conversion.png){: width="32" } | **Conversion de devise** | `FX_CONVERSION` | Change de devise au sein d'un courtier. | ⬆️⬇️ | — | [📖](fx-conversion.md) |

---

## 🔗 Articles connexes

- 📊 **[Types d'Actifs](../asset-types/index.md)** — Les instruments sur lesquels ces transactions agissent
- 📅 **[Événements d'Actifs](../asset-events/index.md)** — Événements globaux vs transactions personnelles
- 💰 **[Fiscalité](../../fundamentals/taxation.md)** — Implications fiscales des transactions
