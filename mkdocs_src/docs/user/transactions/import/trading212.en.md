# <img src="https://www.trading212.com/favicon.ico" alt=""> Trading212

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

To export your transaction statement from Trading212:

1. Log in to the [Trading212 Client Portal](https://www.trading212.com) (or open the app on your mobile device).
2. Go to the menu/profile section and click on **History**.
3. Click the **Export** button (usually represented by an export or document icon at the top of the history tab).
4. Select the desired columns (ensure all fields like ticker, date, quantity, price, and currency are selected).
5. Choose **CSV** as the format and click **Export**. Save the file to your computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Trading212 Portal - History and CSV Export modal] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Pie Transactions"

    Trading212 supports "Pies" (baskets of automatically managed assets). If you trade inside a Pie, the export reports these trades as separate underlying asset transactions. The BRIM parser processes these individual trades automatically, but make sure your Pie balances are fully synced in the staging grid before committing.

## 📝 Notes

- Supports stock/ETF buys and sells, dividends, interest on cash, deposits, withdrawals, and FX conversion fees.
- Multi-currency accounts are supported.
