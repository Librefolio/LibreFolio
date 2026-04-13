# 💸 Transaction Types

LibreFolio records every financial event as a transaction. Understanding these types is crucial for accurate portfolio tracking and tax reporting.

## 📋 Supported Transactions

| | Type | Code | Description | Cash | Asset | |
|:---:|:---|:---|---|:---:|:---:|:---:|
| ![](../../../static/icons/transactions/buy.png){: width="32" } | **Buy / Sell** | `BUY` / `SELL` | Purchase or sale of an asset. | ⬇️⬆️ | ⬆️⬇️ | [📖](buy-sell.md) |
| ![](../../../static/icons/transactions/deposit.png){: width="32" } | **Deposit / Withdrawal** | `DEPOSIT` / `WITHDRAWAL` | Adding or removing cash from a broker account. | ⬆️⬇️ | — | [📖](deposit-withdrawal.md) |
| ![](../../../static/icons/transactions/dividend.png){: width="32" } | **Dividend** | `DIVIDEND` | Cash payment from a stock or ETF holding. | ⬆️ | — | [📖](dividend.md) |
| ![](../../../static/icons/transactions/fee.png){: width="32" } | **Fee / Tax** | `FEE` / `TAX` | Costs associated with trades, account maintenance, or taxes. | ⬇️ | — | [📖](fee.md) |
| ![](../../../static/icons/transactions/interest.png){: width="32" } | **Interest** | `INTEREST` | Interest received from cash, bonds, or P2P loans. | ⬆️ | — | [📖](interest.md) |
| ![](../../../static/icons/transactions/transfer.png){: width="32" } | **Transfer / FX** | `TRANSFER_IN/OUT` / `FX_CONVERSION` | Moving assets between portfolios or converting currencies. | varies | varies | [📖](transfer.md) |

---

## 🔗 Related

- 📊 **[Asset Types](../asset-types/index.md)** — The instruments these transactions act upon
- 📅 **[Asset Events](../asset-events/index.md)** — Global events vs personal transactions
- 💰 **[Taxation](../../fundamentals/taxation.md)** — Tax implications of transactions
