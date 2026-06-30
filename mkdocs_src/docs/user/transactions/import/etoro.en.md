# <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

To export your transaction history from eToro:

1. Log in to your [eToro account](https://www.etoro.com).
2. Click on **Portfolio** in the left sidebar, then click on the clock icon to open **History**.
3. Click the settings gear icon in the top right and select **Account Statement**.
4. Choose the start and end date for your statement, then click **Create**.
5. Select the **Excel** or **CSV** export option. Save the file to your computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: eToro Portfolio History - Account Statement creation and export] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Do Not Use PDF Statements"

    eToro allows downloading statements as PDFs. PDF files cannot be processed by the BRIM importer. Make sure you select the spreadsheet format (XLSX or CSV).

!!! warning "CFD vs Real Assets"

    eToro supports both CFD (contracts for difference) and real assets. The parser will import CFD transactions, but because CFDs do not represent underlying shares, cost basis and WAC logic might require manual validation in the transaction grid.

## 📝 Notes

- Supports stock, ETF, crypto, and CFD trades, dividends paid, deposits, withdrawals, and fee adjustments.
- All values in the exported eToro files are denominated in USD.

## 🔗 Developer Reference

→ [eToro Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
