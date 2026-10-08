# <img src="https://www.degiro.com/favicon.ico" alt=""> Degiro

## 📥 How to Export

LibreFolio imports DEGIRO's **Account Statement**, the CSV export that records every movement of your account (usually saved as `Account.csv`). To export it:

1. Log in to the [Degiro Client Portal](https://www.degiro.eu).
2. Go to **Inbox** (or Account) in the left sidebar, then click on **Account Statement**.
3. Select the desired **Start Date** and **End Date** to cover your transaction history.
4. Click on the **Export** button and select **CSV** format.
5. Save the file to your computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Degiro Portal - Inbox and Account Statement page] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Separate Reports"

    Degiro has different menu exports. Make sure to download the **Account Statement**, which records every cash movement — trades, fees, dividends, deposits, withdrawals and currency conversions — rather than the **Transactions** list, which holds only your orders. If you upload the Transactions export, LibreFolio recognises it, imports nothing and shows a warning asking you to export the Account Statement instead.

!!! warning "Language Formats"

    The Account Statement is read by **column position**, not by column name, so an export in any DEGIRO language works. Upload the file as DEGIRO exports it: LibreFolio needs its twelve columns in their original order and its `DD-MM-YYYY` dates, so do not add, remove or move columns.

    Import warnings follow the language of the file's header row — English, Dutch, German, French or Spanish — whatever language LibreFolio itself uses; a file in any other language gets them in English.

## 📝 Notes

### 🔄 What Gets Imported

| In the statement | Imported as |
|:-----------------|:------------|
| Buys and sells, such as `Buy 5 APPLE INC@180,25 USD`, in any language | **Buy** or **Sell**: the sign of the amount gives the direction, the description gives the quantity |
| Order fees (`DEGIRO Transaction and/or third party fees`) and exchange connection fees | **Fee** |
| Stamp duty and financial transaction taxes on an order | **Tax** |
| Dividends and their withholding tax (`Dividend`, `Dividend Tax`) | **Dividend** and **Tax**, each in its own currency |
| Deposits and withdrawals | **Deposit** and **Withdrawal** |
| Interest (`Flatex Interest Income`) | **Interest**; interest charged to you becomes a **Fee** |
| Promotional and courtesy credits (`DEGIRO courtesy`) | **Interest**, keeping DEGIRO's description |
| Currency conversions (`FX Debit` and `FX Credit`) | One linked pair of **FX conversions** (see below) |

Amounts are imported as DEGIRO reports them, each in the currency of its own row.

### 💱 Currency Conversions

DEGIRO records a currency conversion as two rows: the amount that leaves one currency and the amount that arrives in the other. LibreFolio imports them as one linked pair. In the review step of the [import wizard](how-to.md) the pair is a single row showing **From**, **To** and the exchange rate the two amounts imply, and selecting or deselecting it always moves both legs together. The counters and the **Import** button count transactions, so a pair counts as two: a statement of 17 transactions with two conversions shows 15 rows, and with every row selected the button reads **Import 17 transactions**. DEGIRO's AutoFX cost is already part of the amount the conversion debits, so LibreFolio adds no separate fee for it.

### 🚫 What Is Not Imported

These rows are not imported. Each kind is listed in a warning during the import, together with the original rows, so you can check them:

- **Corporate actions** (product or ISIN changes, splits, mergers, stock dividends and their cash settlements), **money market fund** rows and **capital returns**: LibreFolio does not import them automatically — check the positions they affect.
- **flatex withdrawal rows** (`flatex Withdrawal`): LibreFolio cannot yet tell whether money really left your account. If it did, add the withdrawal by hand.
- **Currency conversion rows without a partner**: the other leg is missing from the file or cannot be identified.
- **Rows with an unexpected sign** for their type, such as a negative dividend.
- **Trades whose quantity cannot be read** from the description.
- **Unrecognised rows**: anything else LibreFolio could not classify.

Skipped without a warning: information lines without an amount, DEGIRO's internal bookings (cash sweeps, transfers to or from flatexDEGIRO Bank, reservations) and interest of zero.
