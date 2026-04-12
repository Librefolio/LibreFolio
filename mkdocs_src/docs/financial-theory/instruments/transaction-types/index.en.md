# 💸 Transaction Types

LibreFolio records every financial event as a transaction. Understanding these types is crucial for accurate portfolio tracking and tax reporting.

## 📋 Supported Transactions

<table>
  <thead>
    <tr>
      <th style="width: 60px; text-align: center;">Icon</th>
      <th style="white-space: nowrap;">Type</th>
      <th style="white-space: nowrap;">Code</th>
      <th>Description</th>
      <th style="text-align: center;">Cash</th>
      <th style="text-align: center;">Asset</th>
      <th style="white-space: nowrap;">Details</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/transactions/buy.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Buy / Sell</strong></td>
      <td style="white-space: nowrap;"><code>BUY</code> / <code>SELL</code></td>
      <td>Purchase or sale of an asset.</td>
      <td style="text-align: center;">⬇️⬆️</td>
      <td style="text-align: center;">⬆️⬇️</td>
      <td><a href="buy-sell/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/transactions/deposit.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Deposit / Withdrawal</strong></td>
      <td style="white-space: nowrap;"><code>DEPOSIT</code> / <code>WITHDRAWAL</code></td>
      <td>Adding or removing cash from a broker account.</td>
      <td style="text-align: center;">⬆️⬇️</td>
      <td style="text-align: center;">—</td>
      <td><a href="deposit-withdrawal/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/transactions/dividend.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Dividend</strong></td>
      <td style="white-space: nowrap;"><code>DIVIDEND</code></td>
      <td>Cash payment from a stock or ETF holding.</td>
      <td style="text-align: center;">⬆️</td>
      <td style="text-align: center;">—</td>
      <td><a href="dividend/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/transactions/fee.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Fee / Tax</strong></td>
      <td style="white-space: nowrap;"><code>FEE</code> / <code>TAX</code></td>
      <td>Costs associated with trades, account maintenance, or taxes.</td>
      <td style="text-align: center;">⬇️</td>
      <td style="text-align: center;">—</td>
      <td><a href="fee/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/transactions/interest.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Interest</strong></td>
      <td style="white-space: nowrap;"><code>INTEREST</code></td>
      <td>Interest received from cash, bonds, or P2P loans.</td>
      <td style="text-align: center;">⬆️</td>
      <td style="text-align: center;">—</td>
      <td><a href="interest/">📖</a></td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../../static/icons/transactions/transfer.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Transfer / FX</strong></td>
      <td style="white-space: nowrap;"><code>TRANSFER_IN/OUT</code> / <code>FX_CONVERSION</code></td>
      <td>Moving assets between portfolios or converting currencies.</td>
      <td style="text-align: center;">varies</td>
      <td style="text-align: center;">varies</td>
      <td><a href="transfer/">📖</a></td>
    </tr>
  </tbody>
</table>

---

## 🔗 Related

- 📊 **[Asset Types](../asset-types/index.md)** — The instruments these transactions act upon
- 📅 **[Asset Events](../asset-events/index.md)** — Global events vs personal transactions
- 💰 **[Taxation](../../fundamentals/taxation.md)** — Tax implications of transactions
