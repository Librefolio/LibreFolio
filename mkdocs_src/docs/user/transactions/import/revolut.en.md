# <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" alt=""> Revolut

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

To export your stock/crypto transaction history from Revolut:

1. Open your **Revolut mobile app** or log in via the web client.
2. Navigate to the **Invest** (or Stocks/Crypto) tab.
3. Tap **... (More)** next to your portfolio balance, then select **Statements**.
4. Select the desired account (e.g. Stocks account) and tap **Transaction Statement**.
5. Set the timeframe, choose **CSV** as the format, and export. Transfer the file to your computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Revolut App - Invest Statements selection and CSV export] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Trading Account vs Main Account"

    Ensure you export the statement from the **Invest/Trading** sub-account. The main Revolut debit card statement uses a completely different file format and cannot be parsed by this plugin.

## 📝 Notes

- Supports stock trades, crypto purchases, dividends paid, custody fees, and cash transfers.
- Handles multi-currency amounts in the same file automatically.
