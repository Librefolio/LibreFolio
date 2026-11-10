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

In an **Invest** file, a **STOCK SPLIT** row with a positive **Quantity** is imported as an incoming **Adjustment** of the shares added (the **Quantity** of the row is the number of new shares, not the total after the split), at no cost.

The importer cannot tell a split from a gift or a spin-off, so it flags the row. The end of the import wizard (the **Review** step) tells you how many rows look like splits, and the Bulk editor shows a banner, *N rows may be stock splits*. For each row it lists the ticker, the shares added and the date. When the rows above it in the file show how many shares you held before the split, it also shows the **ratio** that results (for example 3 for a 3-for-1 split) and the shares held.

Two buttons let you settle it:

- **Create the SPLIT event and link** opens the small event form with the type already set to **Split** and the ratio filled in with the suggested one. You can change it: type `3` for a 3-for-1 split, `0.25` for a 1-for-4 reverse split.
- **Link to an existing event** lets you pick one of the asset's events, if you already created the split.

Once the row is linked, the banner entry goes away. If the row's asset is not chosen yet, the banner asks you to choose it first. For more on events, see [Asset Events](../../assets/detail/events.md).

!!! note "🔢 When the broker rounds the quantity"

    Brokers sometimes round the shares they write (for example 0.1643 instead of 0.16431924). If the quantity of the row differs from your holding times the ratio minus one, the banner says so and gives the difference in shares. The **Lots** view follows the ratio of the event, while the **Dashboard** and the average cost follow the quantity of the row. The gap is small, but after selling the whole position a tiny lot that cannot be sold may be left over.

!!! warning "Link the split to a Split event"

    Until the row is linked to a **Split** event, the new shares enter without cost and dilute the average cost of the asset. The **Lots** view shows a lot with a cost of 0. If you sell part of the position, LibreFolio first sells the old, expensive lots at the price after the split, so you see a loss, and later a gain when the zero-cost lot is used up. An asset without quotations also stays overvalued: the new shares count at full value, even though the price has not been divided. Linking the event makes the cost follow the old shares, which is right for a split. The file does not say whether the shares come from a split, a gift or a spin-off, so the choice stays with you.

## 🚧 Known limitations

- **Reverse splits are not imported.** A **STOCK SPLIT** row with a negative, zero or missing **Quantity** (or without a ticker) is listed in an amber warning, with a link to open an issue on GitHub: add it by hand.
- **Invest files only.** Stock splits are read in Invest statements, not in Crypto ones.
- **Something is off?** Please [open an issue](https://github.com/Librefolio/LibreFolio/issues) with an anonymised example file.

## 🔗 Developer Reference

→ [Revolut Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
