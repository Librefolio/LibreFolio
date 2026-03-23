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
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/buy.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Buy</strong></td>
      <td style="white-space: nowrap;"><code>BUY</code></td>
      <td>Purchase of an asset. Increases holdings, decreases cash.</td>
      <td style="text-align: center;">⬇️</td>
      <td style="text-align: center;">⬆️</td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/sell.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Sell</strong></td>
      <td style="white-space: nowrap;"><code>SELL</code></td>
      <td>Sale of an asset. Decreases holdings, increases cash. Realizes P&amp;L.</td>
      <td style="text-align: center;">⬆️</td>
      <td style="text-align: center;">⬇️</td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/dividend.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Dividend</strong></td>
      <td style="white-space: nowrap;"><code>DIVIDEND</code></td>
      <td>Cash payment from a stock or ETF holding.</td>
      <td style="text-align: center;">⬆️</td>
      <td style="text-align: center;">—</td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/interest.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Interest</strong></td>
      <td style="white-space: nowrap;"><code>INTEREST</code></td>
      <td>Interest received from cash, bonds, or P2P loans.</td>
      <td style="text-align: center;">⬆️</td>
      <td style="text-align: center;">—</td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/deposit.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Deposit</strong></td>
      <td style="white-space: nowrap;"><code>DEPOSIT</code></td>
      <td>Adding cash to a portfolio/broker account.</td>
      <td style="text-align: center;">⬆️</td>
      <td style="text-align: center;">—</td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/withdrawal.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Withdrawal</strong></td>
      <td style="white-space: nowrap;"><code>WITHDRAWAL</code></td>
      <td>Removing cash from a portfolio/broker account.</td>
      <td style="text-align: center;">⬇️</td>
      <td style="text-align: center;">—</td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/fee.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Fee</strong></td>
      <td style="white-space: nowrap;"><code>FEE</code></td>
      <td>Cost associated with a trade or account maintenance.</td>
      <td style="text-align: center;">⬇️</td>
      <td style="text-align: center;">—</td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/tax.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Tax</strong></td>
      <td style="white-space: nowrap;"><code>TAX</code></td>
      <td>Taxes paid on dividends, interest, or capital gains.</td>
      <td style="text-align: center;">⬇️</td>
      <td style="text-align: center;">—</td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/fx-conversion.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>FX Conversion</strong></td>
      <td style="white-space: nowrap;"><code>FX_CONVERSION</code></td>
      <td>Exchanging one currency for another.</td>
      <td style="text-align: center;">⬆️⬇️</td>
      <td style="text-align: center;">—</td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/transfer.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Transfer In</strong></td>
      <td style="white-space: nowrap;"><code>TRANSFER_IN</code></td>
      <td>Moving assets <em>into</em> this portfolio from another (without a sale).</td>
      <td style="text-align: center;">—</td>
      <td style="text-align: center;">⬆️</td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/transfer.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Transfer Out</strong></td>
      <td style="white-space: nowrap;"><code>TRANSFER_OUT</code></td>
      <td>Moving assets <em>out of</em> this portfolio to another (without a sale).</td>
      <td style="text-align: center;">—</td>
      <td style="text-align: center;">⬇️</td>
    </tr>
    <tr>
      <td style="text-align: center;"><img src="../../static/icons/transactions/adjustment.png" width="32" /></td>
      <td style="white-space: nowrap;"><strong>Adjustment</strong></td>
      <td style="white-space: nowrap;"><code>ADJUSTMENT</code></td>
      <td>Manual correction of balance or holdings.</td>
      <td style="text-align: center;">⬆️⬇️</td>
      <td style="text-align: center;">⬆️⬇️</td>
    </tr>
  </tbody>
</table>
