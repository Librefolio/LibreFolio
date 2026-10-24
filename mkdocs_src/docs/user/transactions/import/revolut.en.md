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
- Transfers between your own accounts are left out quietly, since they change nothing.

## 🔀 Stock Splits

In an **Invest** file, a **STOCK SPLIT** row with a positive **Quantity** is imported as an incoming **Adjustment** of the shares added (the **Quantity** of the row is the number of new shares, not the total after the split), at no cost. The Bulk editor will mark it as *may be a stock split*, so you can create the **Split** event and link it, or link an existing one: see [Asset Events](../../assets/detail/events.md).

!!! warning "Link the split to a Split event"

    Until the row is linked to a **Split** event, the new shares enter without cost and dilute the average cost of the asset. Linking it makes the cost follow the old shares, which is right for a split. The file does not say whether the shares come from a split, a gift or a spin-off, so the choice stays with you.

## 🚧 Known limitations

- **Reverse splits are not imported.** A **STOCK SPLIT** row with a negative, zero or missing **Quantity** (or without a ticker) is listed in an amber warning, with a link to open an issue on GitHub: add it by hand.
- **Invest files only.** Stock splits are read in Invest statements, not in Crypto ones.
- **Something is off?** Please [open an issue](https://github.com/Librefolio/LibreFolio/issues) with an anonymised example file.

## 🔗 Developer Reference

→ [Revolut Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
