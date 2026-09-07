# 📥 <img src="https://www.intesasanpaolo.com/favicon.ico" alt=""> Intesa Sanpaolo

!!! info "Beta"

    This plugin is in **Beta** — tested with sample files but edge cases may exist.

## 📥 How to Export

LibreFolio reads Intesa Sanpaolo exports in **CSV** *or* **XLSX** — you do not need to
convert the file, just import it as downloaded. Two different reports are supported and
they cover two different situations:

- The **movements list** (*lista movimenti*) — the account activity for a period.
- The **portfolio snapshot** (*patrimonio*) — the current holdings with their fiscal
  cost basis and the cash balance.

From your Intesa Sanpaolo online banking, download the movements list for the period you
want and, if you also need to seed historical positions, the portfolio snapshot of your
*Deposito Amministrato*.

## 🧭 Which files should I import?

=== "Brand-new account"

    If the account was **opened recently** and every purchase is inside the exported
    period, importing only the **movements list** is enough — there is no back-history to
    reconstruct.

=== "Account with history (recommended)"

    Intesa only exports about **one year** of movements and does **not** include the
    original purchase transactions. To represent positions bought earlier, first import
    the **portfolio snapshot**: it seeds the account with

    - one **cash deposit** for the reported liquidity (when the snapshot contains a non-zero cash balance), and
    - one **cost-basis adjustment per holding** (quantity from the snapshot, with the
      fiscal cost stored as a **per-unit** cost-basis override),

    all dated at the snapshot date. Then import the **movements list** to add the recent
    coupons and fees.

## 📝 Notes

- **Movements list** — the parser maps operation labels by keyword: *Cedole* → interest,
  *Dividend...* → dividend, *Commission...* → fee, and *Ritenut...* / *Imposta...* /
  *Bollo...* → tax. Everyday current-account operations that may appear in the same export
  (transfers, card payments, salary, etc.) are **not recognised as securities activity and
  are skipped**, with a warning — the import never fails because of them.
- **No ISIN in the movements list** — the security is taken from the free-text *Dettagli*
  field, so assets are matched **by name**. The portfolio snapshot *does* carry the ISIN.
  Because the two reports identify the same security differently (name vs ISIN), LibreFolio
  will not merge them automatically — confirm the asset in **Step 4** of the wizard.
- **Snapshot seed** — each adjustment stores `cost_basis_override` as the **per-unit** fiscal cost. Intesa reports *Controvalore di carico fiscale €* as a total position value, so LibreFolio divides it by the holding quantity before storing it. The engine later multiplies the per-unit value by quantity to reconstruct the total cost basis. The snapshot date is the latest quote date in the report.
- **Maturity notices** — if parsed Intesa rows contain maturity/redemption cues, the asset-create dialog may show an amber advisory notice warning that the security may be matured or delisted.
- **Amounts are imported verbatim** in EUR, exactly as they appear in the report. No
  currency conversion is performed.

## ⛔ Before the broker's opening date

When your broker has an **opening date** set, movements dated **strictly before** that date are flagged in the wizard as **"Before opening"** and cannot be imported (their checkbox is disabled). The opening day itself is valid: the shipped check is `txDate < info.openedAt`, not `<=`. This prevents duplicating positions that are already represented by the snapshot seed. If a row is flagged incorrectly, use the inline **Edit broker date** action, then re-check/refresh so the wizard evaluates the updated broker date.

## 🔗 Developer Reference

→ [BRIM Providers — Implementation Details](../../../developer/backend/brim/providers_list.md)
