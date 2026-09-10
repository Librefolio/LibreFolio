# <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

To export your transaction history from eToro:

1. Log in to your [eToro account](https://www.etoro.com).
2. Click on **Portfolio** in the left sidebar, then click on the clock icon to open **History**.
3. Click the settings gear icon in the top right and select **Account Statement**.
4. Choose the start and end date for your statement, then click **Create**.
5. Select the **CSV** export option. Save the file to your computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: eToro Portfolio History - Account Statement creation and export] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Do Not Use PDF Statements"

    eToro allows downloading statements as PDFs or Excel files. Only **CSV** files can be processed by the BRIM importer. Make sure you select the CSV format.

!!! warning "Review Withdrawal Conversion Fees"

    In the eToro CSV sample observed in this repository, a `Withdrawal Conversion Fee` row with a non-zero `Amount` is imported as a separate `FEE` cash debit. Rows labelled `Withdraw Fee`, `Withdrawal Conversion Fee`, or `Conversion Fee` with a zero `Amount` are ignored. The original `Withdraw Request` remains unchanged, so the imported transactions can show both the withdrawal and the separate fee.

    This behavior reflects the observed sample format; it does not establish universal eToro semantics or proven settlement behavior. If eToro uses different wording or formatting in your statement, compare the imported amounts with the statement before saving them.

!!! warning "CFD vs Real Assets"

    eToro supports both CFD (contracts for difference) and real assets. The parser will import CFD transactions, but because CFDs do not represent underlying shares, cost basis and WAC logic might require manual validation in the transaction grid.

## 📝 Notes

- Supports stock, ETF, crypto, and CFD trades, dividends paid, deposits, withdrawals, and fee adjustments.
- All values in the exported eToro files are denominated in USD.

## 🔗 Developer Reference

→ [eToro Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
