# <img src="https://www.schwab.com/favicon.ico" alt=""> Charles Schwab

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

To export your transaction history from Charles Schwab:

1. Log in to your [Charles Schwab Client Portal](https://www.schwab.com).
2. Go to the **Accounts** tab and select **History**.
3. Select the account you want to export (if you have multiple accounts).
4. Select the desired date range.
5. Click the **Export** link (usually located in the top-right corner of the transaction table) and select **CSV**.
6. Save the file to your computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Charles Schwab Portal - History tab and Export link] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Do Not Modify Headers"

    Schwab CSV files have a specific layout with metadata lines at the bottom (usually starting with "Transactions Total"). The BRIM parser automatically detects and skips these metadata lines. Do not manually trim the bottom lines of the CSV.

## 📝 Notes

- Supports US-formatted CSV parameters (MM/DD/YYYY date structures and USD currency listings).
- Parses buy/sell transactions, dividend payments, reinvestments, and transaction charges.

## 🔗 Developer Reference

→ [Charles Schwab Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
