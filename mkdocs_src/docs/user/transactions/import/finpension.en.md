# <img src="https://www.finpension.ch/favicon.ico" alt=""> Finpension

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

To export your transactions from Finpension:

1. Log in to your [Finpension account](https://app.finpension.ch).
2. Go to your active portfolio/account dashboard.
3. Click on the **Transactions** (Transazioni / Transaktionen) tab.
4. Click on the **Export** or download button and select **CSV**.
5. Save the file to your computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Finpension Portal - Transactions page and Export button] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Do Not Modify Delimiters"

    Finpension exports use a semicolon `;` as the column separator and German/Swiss formats. The BRIM parser detects these locales automatically. Avoid opening the file in spreadsheet editors (such as Excel) and saving it back, as this may change the CSV's raw structure.

## 📝 Notes

- Swiss pension platform.
- Supports cash deposits, buys, sells, tax withholdings, and management fees.
- Denominated in CHF.
