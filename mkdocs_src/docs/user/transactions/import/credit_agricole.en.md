# 📥 <img src="https://www.credit-agricole.it/favicon.ico" alt=""> Crédit Agricole Italia

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

LibreFolio reads Crédit Agricole Italia exports in **CSV** *or* **XLSX** — you do not need
to convert the file, just import it as downloaded. The supported report is the
**"Lista Movimenti Deposito Titoli"** (securities dossier movements) of your account.

From your Crédit Agricole Italia online banking, open the securities dossier, select the
period you want, and export the movements list.

## 📝 Notes

- **No ISIN** — the report only carries the security **name** (`Nome`), so assets are matched by name. Confirm the asset in **Step 4** of the wizard if it is not recognised.
- **Operations** (*causali*) are mapped as follows:

    | Causale | Imported as |
    |:--------|:------------|
    | `CEDOLA` | Bond **coupon** → interest (the nominal in the quantity column is ignored) |
    | `ACQ.CONT.SU MERC.`, `SICAV: SOTTOSCR` | **Buy** with an automatic matching **deposit** |
    | `FONDI: RIMBORSO` | **Sell** (fund redemption) with an automatic matching **withdrawal** |
    | `TITOLI SCADUTI` | Bond **maturity**: **sell at par (100)** + an **interest** leg for anything credited above par (see below) |
    | `GIRO ALTRO DOSSIER`, `VERS.TITOLI` | Succession **transfer-in** → cashless **adjustment** carrying the per-unit book price (see succession note) |

- **`TITOLI SCADUTI` (bond maturity)** — a matured security is **assumed to be a bond
  redeemed at par (100)**. LibreFolio closes the held nominal with a **sell at par** and books
  any amount **credited above par** (a *premio fedeltà* or *FOI* inflation revaluation) as a
  separate **interest** leg — the same nature as a coupon. This keeps the realised gain based
  on price-vs-cost only and lets the position close cleanly to zero. The nominal is taken from
  the positions already present in the file (buy / succession rows). If those legs are **not in
  the file** (e.g. you exported only the last few months), the nominal is **derived** from
  countervalue ÷ price and the row is **flagged for review** — verify it matches the holding
  you are closing. *Assumption:* today every `TITOLI SCADUTI` row is treated as a par-100 bond
  (anything above par → interest); this will be generalised if a non-bond maturity ever
  appears in a real export.
- **Amounts are imported verbatim** in the currency reported by Crédit Agricole. No currency conversion is performed and the *Cambio* (exchange rate) column is ignored. The code uses *Data operazione* as the transaction date.

## ⚠️ Maturity notices

If a row such as `TITOLI SCADUTI` or `FONDI: RIMBORSO` suggests a security may be matured or redeemed, LibreFolio attaches an asset notice. When you create or map the asset in the wizard, that notice appears as an amber advisory banner; it is informational only and does not change the import.

## 💶 Cash model

The Crédit Agricole "Lista Movimenti Deposito Titoli" export is **securities-only**: it
does not include the ordinary bank-account cash movements that fund purchases or receive
sale proceeds. To keep the imported broker cash balance neutral, LibreFolio adds automatic
cash counter-entries:

- each **buy** gets a same-day **deposit** immediately before it;
- each **sell** gets a same-day **withdrawal** immediately after it (for a maturity, the
  withdrawal neutralises the par principal, so only the interest surplus adds cash);
- **coupons** (`CEDOLA`) and **maturity interest** stay as reported and do not receive
  counter-entries.

## 👵 Succession transfers

When a securities dossier is transferred following a **succession**, Crédit Agricole may
record the incoming holdings with the causali `GIRO ALTRO DOSSIER` and `VERS.TITOLI`
(price present, countervalue 0). These rows are the **receiving leg** of a transfer whose
paying leg lives on **another account that LibreFolio does not track** — no money is spent
here.

LibreFolio therefore imports each succession row as a **cashless adjustment** (not a buy):
it seeds the position with the reported quantity and carries the **per-unit book price** as
a cost-basis override, using the report's price convention (bond prices per 100 of nominal;
funds per unit). **No deposit is created**, so your paid-in capital is not inflated by money
you never spent. The **origin causale stays in the description**, for example
`[GIRO ALTRO DOSSIER — successione / transfer-in] ...`, so the provenance of each position
remains traceable.

!!! info "Faithful multi-leg import"

    Crédit Agricole may list the same security in multiple succession legs at different
    prices or quantities. LibreFolio keeps those rows separate (each adjustment keeps its
    own price) instead of aggregating them, mirroring the bank report.

## ⛔ Before the broker's opening date

When your broker has an **opening date** set, movements dated **strictly before** that date are flagged in the wizard as **"Before opening"** and cannot be imported (their checkbox is disabled). The opening day itself is valid: the shipped check is `txDate < info.openedAt`, not `<=`. If a row is flagged incorrectly, use the inline **Edit broker date** action, then re-check/refresh so the wizard evaluates the updated broker date.

## 🔗 Developer Reference

→ [BRIM Providers — Implementation Details](../../../developer/backend/brim/providers_list.md)
