# <img src="https://www.coinbase.com/favicon.ico" alt=""> Coinbase

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

To export your transaction statement from Coinbase:

1. Log in to your [Coinbase account](https://www.coinbase.com).
2. Click on your profile picture in the top-right corner, then select **Taxes** or **Statements**.
3. Under the **Reports** section, locate **Transaction History**.
4. Click **Generate Report**, select **CSV** as the file type, and choose the desired date range.
5. Once the report is ready, download the CSV file to your computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Coinbase Taxes/Reports - Generate Transaction History CSV report] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Incorrect Report Type"

    Make sure you download the **Transaction History** report. Other reports (like Tax Statements, Balance Summaries, or specific Asset Ledger reports) are structured differently and will not be parsed correctly.

!!! warning "USD/EUR Conversions"

    The Coinbase parser processes crypto trades, buys, sells, and fees. Ensure your account display currency matches your main LibreFolio portfolio currency to avoid FX discrepancies.

## 📝 Notes

- Supports buys, sells, conversions, sends, receives, staking rewards, and fee assessments.
- **Staking income, rewards income and learning rewards** are imported as **Reward** transactions: the units you received,
  with no cash, at the value Coinbase gives them in the `Subtotal` column (the value of one unit is `Subtotal` ÷ quantity).
  That value is both their purchase cost and your income.
- A file you imported before this change had these rows as **Adjustment** transactions. Importing it again marks each
  reward as a likely duplicate of the old row, and leaves it unselected: nothing is counted twice.
- Supports major fiat base currencies (USD, EUR, GBP).

## 🔗 Developer Reference

→ [Coinbase Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
