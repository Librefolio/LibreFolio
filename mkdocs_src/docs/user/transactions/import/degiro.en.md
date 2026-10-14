# 📥 <img src="https://www.degiro.com/favicon.ico" alt=""> Degiro

LibreFolio imports DEGIRO's **Account Statement**: the CSV that records every movement of your account — trades, fees, dividends, interest, deposits, withdrawals and currency conversions — in any language DEGIRO offers.

## 📥 How to Export

1. Log in to the [Degiro Client Portal](https://www.degiro.eu).
2. Open **Inbox** in the left sidebar, then **Account Statement**.
3. Choose the **Start Date** and **End Date**: from your first deposit to today for the full history.
4. Click **Export**, choose **CSV** and save the file (usually `Account.csv`).

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <!-- [Screenshot Placeholder: Degiro Portal - Inbox and Account Statement page] -->
</div>

## ⚠️ Common Pitfalls

!!! warning "Account Statement, not Transactions"

    DEGIRO's **Transactions** export lists only your orders: no dividends, deposits, withdrawals or currency conversions. If you upload it, LibreFolio recognises it, imports nothing and asks you for the Account Statement.

- **Keep the file as exported.** Any language works, as long as you do not add, remove or reorder columns, or change DEGIRO's day-month-year dates.
- **Warnings in the file's language.** Import warnings are in the language of the statement, whatever language LibreFolio uses: English, Dutch, German, French or Spanish, and English for any other.

## 🔄 What Gets Imported

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

DEGIRO books a conversion as two rows: the money leaving one currency and the money arriving in the other. LibreFolio imports them as one linked pair: in the wizard's [Review](how-to.md#review) it is a single row showing **From**, **To** and the rate the two amounts imply, selected and imported whole. It counts as two transactions in **Import N transactions**. DEGIRO's AutoFX cost is already inside the debited amount, so no separate fee is added.

## 🚫 What Is Not Imported

Each kind below is listed in a warning during the import, with its original rows, so you can check them:

- **Corporate actions** (product or ISIN changes, splits, mergers, stock dividends and their cash settlements), **money market fund** rows and **capital returns**: LibreFolio does not import them automatically — check the positions they affect.
- **flatex withdrawal rows** (`flatex Withdrawal`): LibreFolio cannot tell whether money really left your account. If it did, add the withdrawal by hand.
- **Currency conversion rows without a partner**: the other leg is missing from the file or cannot be identified.
- **Rows with an unexpected sign** for their type, such as a negative dividend.
- **Trades whose quantity cannot be read** from the description.
- **Unrecognised rows**: anything else LibreFolio could not classify.

Skipped without a warning: information lines without an amount, DEGIRO's internal bookings (cash sweeps, transfers to or from flatexDEGIRO Bank, reservations) and zero-amount lines that name no product, such as an interest of zero.

## 🔗 Developer Reference

→ [BRIM Architecture — DEGIRO notes](../../../developer/backend/brim/architecture.md#plugin-degiro)
