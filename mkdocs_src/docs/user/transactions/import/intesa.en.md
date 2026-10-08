# 📥 <img src="https://www.intesasanpaolo.com/favicon.ico" alt=""> Intesa Sanpaolo

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

LibreFolio reads two Intesa Sanpaolo exports, in **CSV** or **Excel (XLSX)**, just as you download them:

- the **movements list** — the coupons, dividends, fees and taxes of a period;
- the **portfolio snapshot** (*patrimonio*) — your holdings at their fiscal cost, and your cash balance.

## 🧭 Which files should I import?

=== "Brand-new account"

    Import the **movements list**: it brings the coupons, dividends, fees and taxes. LibreFolio
    takes no buys or sells from it, so add your purchases by hand with the
    [transaction form](../form.md), or with a [Generic CSV](generic-csv.md) file.

=== "Account with history (recommended)"

    Intesa exports about **one year** of movements, and LibreFolio takes no buys or sells from
    them. Start from the portfolio snapshot instead:

    1. Import the **portfolio snapshot**. It adds one **Deposit** for your cash balance and one
       **Adjustment** per holding, at its fiscal cost, all dated the snapshot date: the latest
       quote date in the report.
    2. Set the broker's **Account Opened** date to that day. Older movements are already counted
       in the snapshot: the wizard marks them **Before opening** and leaves them out
       ([how it works](how-to.md#opening-date)).
    3. From then on, import the **movements list** for the new coupons, dividends, fees and taxes.

## 📥 How to Export

### 🔍 Step 1 — Open the advanced search

On the home page of your online banking, click **RICERCA AVANZATA**, next to **Ultime Operazioni**.

![Intesa Sanpaolo — home page, RICERCA AVANZATA next to Ultime Operazioni](../../../static/broker-guides/IntesaSanPaolo/01_ISP_RicercaAvanzata.jpg){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 🗓️ Step 2 — Filter and download the movements

Set **Tipologia Operazione** to **Operazioni titoli**, choose the period in **Da** and **A**, click **APPLICA**, then **SCARICA EXCEL**.

![Intesa Sanpaolo — Tipologia Operazione set to Operazioni titoli, period, APPLICA and SCARICA EXCEL](../../../static/broker-guides/IntesaSanPaolo/02_ISP_FiltraExport.png){ style="max-height: 460px; width: auto; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);" }

### 📊 Step 3 — Download the portfolio snapshot

For an account with history, open **Patrimonio** from the home page and download the holdings of
your *Deposito Amministrato*.

## 🔄 What Gets Imported

| In the movements list (**Operazione**) | Imported as |
|:---------------------------------------|:------------|
| *Cedole* (coupons) | **Interest**, linked to the security named in **Dettagli** |
| *Dividend…* | **Dividend**, linked the same way |
| *Commission…* | **Fee** |
| *Ritenut…*, *Imposta…*, *Bollo…* | **Tax** |

Any other operation — buys, sells and everyday banking rows such as card payments or transfers
included — is skipped with a warning: the import never fails because of it.

From the **portfolio snapshot**: one **Adjustment** per holding (its quantity, at its fiscal cost)
and one **Deposit** for the cash balance when it is not zero, all on the snapshot date.

## ⚠️ Good to know

- **Filter on Operazioni titoli.** Without that filter, every card payment or transfer of the
  period shows up in the warnings as a skipped row.
- **The same security, two names.** The movements list names a security only in free text, while
  the snapshot gives its ISIN. Match both to the same asset in the **Resolve Assets** panel of
  [Review](how-to.md#review).
- **Amounts as written.** Movements keep the currency of their **Valuta** column, and the snapshot
  is in euro: nothing is converted.
- **Messages in Italian.** The import warnings are in Italian, like the report.

## 🔗 Developer Reference

→ [BRIM Architecture — Intesa Sanpaolo notes](../../../developer/backend/brim/architecture.md#plugin-intesa)
