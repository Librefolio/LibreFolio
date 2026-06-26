# <img src="https://www.degiro.com/favicon.ico" alt=""> Degiro

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

To export your transactions from Degiro:

1. Log in to the [Degiro Client Portal](https://www.degiro.eu).
2. Go to **Inbox** (or Account) in the left sidebar, then click on **Account Statement**.
3. Select the desired **Start Date** and **End Date** to cover your transaction history.
4. Click on the **Export** button and select **CSV** format.
5. Save the file to your computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Degiro Portal - Inbox and Account Statement page] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Separate Reports"

    Degiro has different menu exports. Make sure to download the **Account Statement** (which records all cash movements, buys, sells, and dividends) rather than just the "Transactions" list, which might omit cash events.

!!! warning "Language Formats"

    The parser supports multiple local Degiro templates (English, Dutch, Italian, German, etc.). However, ensure you do not modify the column headers or CSV delimiters manually after exporting.

## 📝 Notes

- Supports buy/sell trades, dividends, transaction fees, deposits, and withdrawals.
- Currency conversions performed by Degiro are automatically processed.
