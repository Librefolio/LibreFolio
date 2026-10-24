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

Trading212 writes a split as two rows, **Stock split close** (the old shares leave) and **Stock split open** (the new shares arrive), for the same ISIN at the same instant. When the shares after the split are **more** than before, LibreFolio imports the pair as one incoming **Adjustment** of the difference, at no cost. The Bulk editor will mark it as *may be a stock split*, so you can create the **Split** event and link it, or link an existing one: see [Asset Events](../../assets/detail/events.md).

!!! warning "Link the split to a Split event"

    Until the row is linked to a **Split** event, the new shares enter without cost and dilute the average cost of the asset. Linking it makes the cost follow the old shares, which is right for a split. The file does not say whether the shares come from a split, a gift or a spin-off, so the choice stays with you.

## 🚧 Known limitations

- **Splits that are not imported.** A reverse split (fewer shares after than before), a split with the same number of shares, and a split row without its pair are listed in an amber warning, with a link to open an issue on GitHub: add them by hand.
- **Share distributions and currency conversions are not imported.** The **Stock distribution** and **Currency conversion** rows are listed in the same warning: add them by hand.
- **Something is off?** Please [open an issue](https://github.com/Librefolio/LibreFolio/issues) with an anonymised example file.

## 🔗 Developer Reference

→ [Trading212 Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
