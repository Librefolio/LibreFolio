# <img src="https://cdn.prod.website-files.com/66289cd2c30bc8d40bd60733/66f526a076ad61485c78771c_favicon.png" alt=""> Freetrade

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

To export your transaction statement from Freetrade:

1. Open the **Freetrade app** on your mobile device (or access the web portal if available).
2. Tap on your **Account** icon in the top corner.
3. Scroll down and select **Activity**.
4. Tap the **Export** button (usually represented by a download or share icon in the top corner).
5. Select **CSV** as the format, pick your date range, and export the file. Send it to your computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Freetrade App - Account Activity Export CSV view] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Export Format"

    Make sure you request the raw **CSV** export. PDFs or screen-scrapes of transactions will not pass validation.

## 📝 Notes

- UK-based broker.
- Supports equity and ETF trades, dividends, cash deposits, and withdrawals.
- A **free share** (`FREESHARE_ORDER`) is imported as a **Reward** transaction: the share you received, with no cash, at
  the `Price per Share in Account Currency` of the file. That value is both its purchase cost and your income. Before this
  change it was a purchase that took cash from the account, cash that never left it.
- Full multi-currency support for GBP, EUR, and USD assets.
