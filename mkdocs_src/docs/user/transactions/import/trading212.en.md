# <img src="https://www.trading212.com/favicon-32x32.png" alt=""> Trading212

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

- Supports stock/ETF buys and sells, dividends, interest on cash, deposits and withdrawals.
- Multi-currency accounts are supported.
- Transfers between your own accounts are left out quietly, since they change nothing.

## 🔀 Stock Splits

Trading212 writes a split as two rows, **Stock split close** (the old shares leave) and **Stock split open** (the new shares arrive), for the same ISIN at the same instant. When the shares after the split are **more** than before, LibreFolio imports the pair as one incoming **Adjustment** of the difference, at no cost.

The importer cannot tell a split from a gift or a spin-off, so it flags the row. The end of the import wizard (the **Review** step) tells you how many rows look like splits, and the Bulk editor shows a banner, *N rows may be stock splits*. For each row it lists the ticker, the shares added and the date. Since the **Stock split close** row holds the shares you had before, it also shows the **ratio** that results (for example 3 for a 3-for-1 split) and the shares held.

Two buttons let you settle it:

- **Create the SPLIT event and link** opens the small event form with the type already set to **Split** and the ratio filled in with the suggested one. You can change it: type `3` for a 3-for-1 split, `0.25` for a 1-for-4 reverse split.
- **Link to an existing event** lets you pick one of the asset's events, if you already created the split.

Once the row is linked, the banner entry goes away. If the row's asset is not chosen yet, the banner asks you to choose it first. For more on events, see [Asset Events](../../assets/detail/events.md).

!!! note "🔢 When the broker rounds the quantity"

    Brokers sometimes round the shares they write (for example 0.1643 instead of 0.16431924). If the quantity of the row differs from your holding times the ratio minus one, the banner says so and gives the difference in shares. The **Lots** view follows the ratio of the event, while the **Dashboard** and the average cost follow the quantity of the row. The gap is small, but after selling the whole position a tiny lot that cannot be sold may be left over.

!!! warning "Link the split to a Split event"

    Until the row is linked to a **Split** event, the new shares enter without cost and dilute the average cost of the asset. The **Lots** view shows a lot with a cost of 0. If you sell part of the position, LibreFolio first sells the old, expensive lots at the price after the split, so you see a loss, and later a gain when the zero-cost lot is used up. An asset without quotations also stays overvalued: the new shares count at full value, even though the price has not been divided. Linking the event makes the cost follow the old shares, which is right for a split. The file does not say whether the shares come from a split, a gift or a spin-off, so the choice stays with you.

## 🚧 Known limitations

- **Splits that are not imported.** A reverse split (fewer shares after than before), a split with the same number of shares, and a split row without its pair are listed in an amber warning, with a link to open an issue on GitHub: add them by hand.
- **Share distributions and currency conversions are not imported.** The **Stock distribution** and **Currency conversion** rows are listed in the same warning: add them by hand.
- **Something is off?** Please [open an issue](https://github.com/Librefolio/LibreFolio/issues) with an anonymised example file.

## 🔗 Developer Reference

→ [Trading212 Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
