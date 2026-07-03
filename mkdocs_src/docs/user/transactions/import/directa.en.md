# <img src="https://www.directa.it/favicon.ico" alt=""> Directa SIM

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

LibreFolio supports the **CSV** format exported from Directa SIM. The screenshots below are from desktop, but the steps are similar on mobile.

### Step 1 — Open the transaction list

Log in to [Directa](https://www.directatrading.com) and click the **CONTO** tab (❶). Then click the transactions filter icon on the left (❷) and select the time period you want — e.g. **6M** (❸).

![Directa SIM — CONTO tab, transaction list, time period selector](../../../static/broker-guides/Directa_1.png){ style="border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### Step 2 — Export as CSV

Click the export icon (the spreadsheet icon with the green **X**) at the top of the table. In the dialog that opens, select **File separato da virgole (csv)** and click **ESTRAI**.

![Directa SIM — Export dialog, CSV option selected](../../../static/broker-guides/Directa_2.png){ style="border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

Save the file without opening or modifying it in Excel, then import it into LibreFolio.

## 📝 Notes

- Supports stock, bond, and ETF trades, dividends, taxes (*ritenute fiscali*), and transaction fees.
- Only the **CSV** format is supported — not xlsx or ods.
- Account operations are denominated in EUR.
- The export covers up to 3,000 rows per file. For longer histories, export multiple periods and import them in sequence.


