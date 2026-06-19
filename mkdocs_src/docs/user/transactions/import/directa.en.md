# <img src="https://www.directa.it/favicon.ico" alt=""> Directa SIM

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

To export your transactions from Directa SIM:

1. Log in to your [Directa Portal](https://www.directatrading.com) (using the dLite or Classic interface).
2. Go to **INFO** or **Operazioni** in the main menu, then select **Movimenti** (Cash Movements) or **Tabella Ordini** (Order History).
3. Select the date range you want to export.
4. Click on the **CSV** download icon or the export button at the top-right of the table.
5. Save the file directly without opening or modifying it in Excel.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Directa SIM Portal - Movimenti Cash / Transazioni CSV export page] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Header Rows"

    Directa SIM files contain a metadata header block (usually 9 lines) before the actual data table. The parser is built to skip this block automatically. **Do not delete these header lines manually**, otherwise the parser will fail to find the correct data columns.

!!! warning "Delimiter Warnings"

    Directa exports use the semicolon `;` as a delimiter and standard Italian number formatting (comma `,` for decimals). The parser parses these settings automatically. Avoid saving the CSV via software that converts these delimiters (like opening and saving in Microsoft Excel without raw-text settings).

## 📝 Notes

- Supports stock, bond, and ETF trades, dividends, taxes (ritenute fiscali), and transaction fees.
- Account operations are denominated in EUR.

## 🔗 Developer Reference

→ [Directa SIM Provider — Implementation Details](../../../developer/backend/brim/providers_list.md)
