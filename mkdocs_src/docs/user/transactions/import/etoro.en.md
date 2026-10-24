# 📥 <img src="https://www.etoro.com/favicon.ico" alt=""> eToro

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

LibreFolio reads the **Account Activity** sheet of eToro's account statement, saved as CSV.

## 📥 How to Export

1. Log in to your [eToro account](https://www.etoro.com).
2. Open **Portfolio**, then **History** (the clock icon).
3. Click the settings icon at the top right and choose **Account Statement**.
4. Choose the start and end dates, then click **Create**.
5. Download the statement with the **XLS** icon.
6. Open the file in a spreadsheet, go to the **Account Activity** sheet and save it as **CSV**,
   keeping the column names on the first line. LibreFolio does not read PDF or Excel files.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: eToro Portfolio History - Account Statement creation and export] -->
</div>

## 🔄 What Gets Imported

| In Account Activity (**Type**) | Imported as |
|:-------------------------------|:------------|
| Open Position | **Buy** |
| Position closed | **Sell** |
| Dividend | **Dividend** |
| Interest Payment | **Interest** |
| Deposit | **Deposit** |
| Withdraw Request | **Withdrawal** |
| Withdraw Fee, Withdrawal Conversion Fee, Conversion Fee | **Fee**, when the amount is not zero |
| Overnight fee (CFD financing) | **Fee**, when the amount is not zero: a cost of money, with no asset |
| Overnight refund (CFD financing given back) | **Interest**: money given back (positive amount), with no asset and the description *Overnight refund* |
| SDRT (UK stamp duty) | **Tax**, on the instrument of the row |

The instrument comes from **Details** (for example `NKE/USD`) and the quantity from **Units**.

Any other type is skipped with a warning.

## ⚠️ Common Pitfalls

!!! warning "Check the currency of instruments not quoted in USD"

    LibreFolio records each row in the currency after the slash in **Details** (`KER/EUR` in euro),
    and every other row in US dollars. eToro states its amounts in your account currency (usually
    USD): check the rows of instruments quoted in another currency before saving them.

- **Keep eToro's dates**: day/month/year, with or without the time. A row whose date cannot be read
  is skipped with a warning.
- **Withdrawal conversion fees.** A non-zero fee becomes a separate **Fee**, next to the full
  **Withdraw Request**. Compare both with your statement: if the fee was already taken out of the
  withdrawn money, untick it in [Review](how-to.md#review).
- **CFDs** become ordinary buys and sells of the instrument, like real shares. Their **overnight
  fees** are imported as separate **Fee** transactions, with no asset: check those positions and
  their costs against your statement.
- **Overnight fees and refunds.** Fees are imported as **Fee** and refunds as **Interest**: the
  overnight cost you really paid, net of refunds, is the fees minus the refunds. A refund shows up
  as income, so a report of your income includes it.

## 🚧 Known limitations {: #known-limitations }

- **Amounts in your account currency.** See the warning above: check the currency of instruments not
  quoted in USD before saving.
- **Something is off?** Please [open an issue](https://github.com/Librefolio/LibreFolio/issues) with
  an anonymised example file.

## 🔗 Developer Reference

→ [BRIM Architecture — eToro notes](../../../developer/backend/brim/architecture.md#plugin-etoro)
