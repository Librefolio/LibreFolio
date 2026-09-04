# 📥 <img src="https://www.credit-agricole.it/favicon.ico" alt=""> Crédit Agricole

Crédit Agricole functions as both **bank and broker**: the same account holds both your **cash** (salary or pension, wire transfers, utility bills, taxes) and your **securities**. For this reason, the primary import to run is the **Account Activity List**: it is the full bank statement and brings **real cash** into LibreFolio — wire transfers, utility bills, pension, **taxes**, **fees**, and actually credited **coupons and dividends**. Download the file, import it as-is, and the plugin automatically recognizes the format.

The account statement covers the **last 2 years**. If your securities account is **older** and you want to recover its **history**, expand the collapsible section below **before** proceeding.

??? note "📦 Securities account older than 2 years? Recover history (optional)"

    The bank account statement stops at **2 years**. If the securities account is older, add a second export — the **Securities Account Activity List** — which goes much further back and recovers at least the **securities history** (quantities, prices, coupons, maturities) **prior** to that window. It is **securities-only**: it does **not** contain checking account cash flows (wire transfers, utilities, taxes…), which remain in the Account Activity List. The cash for this export is **auto-balanced** to avoid distorting cash balances.

    **How to combine them without duplicates.** First export the **Account Activity List** and note its start date (**"Date from"**). Then export the **Securities Account Activity List** **truncated** so that it ends the day **before** the start of the account activity: the two files **do not overlap** and the same operation is not counted twice.

    #### 📂 Step 1 — Open the securities dossier

    From online banking, navigate to the **Securities Account** section and go to the activity list.

    ![Crédit Agricole — home, selecting the Securities Account section](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/01_CA_HOME_selezionePagina.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 🗓️ Step 2 — Select the time period

    Go as far back as possible, then truncate at the beginning of the checking account activity (see the tip above).

    ![Crédit Agricole — securities activity list with period selector](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/02_CA_ListaMobimentiPeriodo.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 💾 Step 3 — Export

    Export and import the file into LibreFolio without opening or modifying it.

    ![Crédit Agricole — securities activity export area](../../../static/broker-guides/CreditAgricole/MovimentiSoloTitoli/03_CA_ExportZone.jpeg){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    #### 💰 Step 4 — Starting balance (manual deposit)

    Required to have **correct total cash balances**: neither export records the starting cash balance as a transaction, so without this step absolute cash starts at zero at the beginning of the exported window and remains offset.

    **How to get it.** The **Starting Balance** can be read in two equivalent places (it is the same value): at the top of the **Excel file** of the *Account Activity List* and also **at the beginning of the webpage export** — the same page from which you export account activity. It is the value (e.g., `2984.99 EUR`) at the date **"Date from"** (e.g., `01/07/2024`).

    The plugin does **not** create it automatically: at import time **manually create a cash deposit transaction** equal to that **Starting Balance**, with a **date** equal to the **"Date from"**. This keeps absolute cash accurate even if the export covers only a time window.

    ![Crédit Agricole — "Starting Balance" and "Date from" row at the top of export](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/04C_CA_SaldoInizialeExportMovimenti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

    **How securities operations are mapped.** The report only includes the security **name** (`Nome`), not the ISIN: assets are matched by name — confirm the asset in **Step 4** of the wizard if it is not recognized.

    | Transaction Type | Imported as |
    |:-----------------|:------------|
    | `CEDOLA` | Bond **Coupon** → interest (nominal value in quantity column is ignored) |
    | `ACQ.CONT.SU MERC.`, `SICAV: SOTTOSCR` | **Buy** with an automatic **deposit** of equal amount |
    | `FONDI: RIMBORSO` | **Sell** (fund redemption) with an automatic **withdrawal** of equal amount |
    | `TITOLI SCADUTI` | Bond **Maturity**: **sell at par (100)** + an **interest** leg for any amount above par |
    | `GIRO ALTRO DOSSIER`, `VERS.TITOLI` | **Inbound transfer** from inheritance → **adjustment** without cash using cost price per unit |

    Amounts are imported **verbatim** in the report currency: no conversion, the *Exchange Rate* column is ignored. The date used is *Transaction Date*.

    **Cash model (securities).** Being a securities-only export, LibreFolio maintains a **neutral** cash balance via automatic offset transactions (tag `auto_cash`): every **buy** receives a **deposit** of equal amount, every **sell**/**coupon**/**maturity interest** receives a **withdrawal** of equal amount. Thus the securities export **does not accumulate ghost cash** — true cash comes from the Account Activity List.

## 💳 How to Import — Account Activity List

This is the **main import**: the statement with **real cash** (wire transfers, utilities, pension, taxes, fees, credited coupons and dividends). Covers the **last 2 years**.

### 📄 Step 1 — Open account activity

From online banking, navigate to the **checking account** section and go to the activity list.

![Crédit Agricole — home, checking account activity section](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/01C_CA_HomeContiMovimenti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 🗓️ Step 2 — Select the time period

Click on **Advanced Search** to open the date filters, then set the widest allowed window (account export is limited to **2 years**).

![Crédit Agricole — account activity list](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/02C_CA_ListaMovimentiConti.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 💾 Step 3 — Export

Download the list and import it into LibreFolio without modifying it.

![Crédit Agricole — account activity export with period warning](../../../static/broker-guides/CreditAgricole/MovimentiContiTotali/03C_CA_ExportMovimentiContiConWarning.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

!!! warning "If the maximum period warning appears"

    Crédit Agricole limits how many rows/months you can export at once. If the warning appears, **split the export into multiple sub-blocks** until all missing months are covered:

    1. Export the block as currently shown.
    2. Look at the **last** (oldest) transaction of the freshly downloaded block and note its date.
    3. Return to the date selector and set the **end date ("to")** to the date of that last transaction.
    4. Export the new block and **repeat** from step 2 until you reach the desired period.
    5. Import **all** exported files into LibreFolio.

### 📝 How account transactions are mapped

Account **transaction types** are categorized as follows:

| Transaction Type | Imported as |
|:-----------------|:------------|
| Credited coupons / dividends | **Interest** (coupon) or **Dividend** if description identifies a security with **ISIN**; otherwise **interest** |
| Interest / credit fees | **Interest** (positive amount) |
| Account fee, commissions, management fees, coupon detachment fees | **Fee** (cash outflow) |
| Capital gains tax, stamp duty, withholding tax, D.Lgs 461 | **Tax** (cash outflow) |
| Securities/funds trading | **Buy/Sell** when description and sign agree and the quantity is recoverable; otherwise **deposit/withdrawal** with a **blocking flag** to complete in the correction step |
| Matured or drawn securities | **Sale at par** closing the position |
| Incoming transfer that redeems a fund | **Deposit** + **blocking flag**: the fund states the countervalue, not the units, so you choose the fund and enter the quantity |
| Pension/salaries, POS, utilities, withdrawals, other transfers | **Deposit** (amount > 0) / **Withdrawal** (amount < 0) by sign |

## 🔗 Developer Reference

→ [BRIM Providers — Implementation details](../../../developer/backend/brim/providers_list.md)
