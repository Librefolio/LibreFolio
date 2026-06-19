# <img src="https://www.interactivebrokers.com/favicon.ico" alt=""> Interactive Brokers (IBKR)

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

To export your transactions from Interactive Brokers, follow these steps:

1. Log in to the [Interactive Brokers Client Portal](https://www.interactivebrokers.com).
2. Navigate to **Reports** in the top menu, then select **Statements**.
3. Under the **Activity** section, click the **Activity Statement** card.
4. Select the desired **Date Range** (e.g., Year to Date, Custom) and choose **CSV** as the format.
5. Click **Run** or download the generated CSV report to your computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Interactive Brokers Portal - Statements & Reports menu] -->
</div>

### ⚙️ Using Flex Queries (Recommended)

For more advanced portfolios, you can configure a **Flex Query** to export specific data:

1. Under **Reports**, go to **Flex Queries** and click the **+ (Create)** button.
2. Select **Activity Flex Query**.
3. Add **Trades**, **Cash Transactions** (for dividends and fees), and **Corporate Actions** to the query.
4. Set the format to **CSV** and save the query. You can run this custom query at any time.

## ⚠️ Common Pitfalls

!!! warning "File Format"

    Make sure you export as a **CSV** file. PDF statements are not supported by the parser and will fail to upload.

!!! warning "Language Settings"

    The parser is designed for English CSV headers. Ensure your IBKR Client Portal language is set to English before running the export.

## 📝 Notes

- Supports standard IBKR activity reports (trades, dividends, tax withholdings, fees, deposits, withdrawals).
- Multi-currency accounts are supported.
- Corporate actions (splits, mergers) may require manual adjustments inside the staging grid.

## 🔗 Developer Reference

→ [IBKR Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
