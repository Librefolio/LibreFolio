---
name: brim-plugin
description: "Use this skill when creating, extending, or reviewing a BRIM broker-import plugin (backend/app/services/brim_providers/). Explains the high-level spirit of a BRIM plugin — what it must do and the mandatory import rules — and points to the developer guide for up-to-date technical details."
---

# 📦 BRIM Plugin Skill

> High-level guide to what a **Broker Report Import Manager (BRIM)** plugin must do
> and the spirit it must follow. For exact, up-to-date technical details, read the
> developer guide (see [Where to find the technical details](#where-to-find-the-technical-details)).

## 🎯 What a BRIM plugin is

A BRIM plugin teaches LibreFolio to read **one specific broker's export file** and turn
its rows into standard transactions the user can review and import. It lives in
`backend/app/services/brim_providers/` (one file per broker), extends `BRIMProvider`, and
is auto-discovered via `@register_provider(BRIMProviderRegistry)`.

Think of it as a **faithful transcriber**: it copies what the broker reported into
LibreFolio's transaction shape. It is **not** a calculator, a pricing engine, or an FX
converter.

## 🧭 The spirit — mandatory rules

1. **Verbatim / copy-paste import.** Import the numbers exactly as they appear in the
   report. Never recompute totals, prices, or amounts — transcribe them.
2. **No forex, ever.** Never call the FX subsystem and never convert amounts using the
   report's own exchange-rate column. If the export has a rate column, **ignore it**.
3. **Currency from the source.** Take each transaction's currency from the broker's own
   currency column (per row) and tag every monetary figure in that row with it. One file
   may contain multiple currencies — keep them as reported.
4. **Detect the delimiter.** Always resolve the separator with the base-class
   `detect_csv_delimiter` helper — never hardcode `,` or `;`.
5. **Handle multiple layouts.** When a broker ships more than one report layout (e.g. with
   and without commission columns), detect the variant **dynamically**: locate the header
   row and branch on the real column set, not a fixed line offset.
6. **Correct sign conventions.** Set signs per transaction type (BUY: qty > 0 / cash < 0;
   SELL: qty < 0 / cash > 0; DIVIDEND & INTEREST: qty = 0 / cash > 0; FEE & TAX: qty = 0 /
   cash < 0; ADJUSTMENT: qty ≠ 0 / no cash), but take magnitudes verbatim from the report.
7. **Fake asset IDs.** Emit negative fake asset IDs (keyed by ISIN/ticker) plus the
   extracted asset info, so the core can drive the asset-matching UI.

## 🛠️ Rough shape of the work

1. Create `backend/app/services/brim_providers/broker_<name>.py`, extend `BRIMProvider`,
   decorate with `@register_provider(BRIMProviderRegistry)`.
2. Implement `can_parse` (quick header/extension sniff) and `parse` (full parsing →
   `BRIMParseOutput`). Use the base-class helpers instead of re-implementing them.
3. Map the broker's operation labels to `TransactionType`, applying the sign rules above.
4. Add a sample export under `sample_reports/`, set `test_file_pattern`, and add a
   user-facing docs page under `mkdocs_src/docs/user/transactions/import/`.

## 📚 Where to find the technical details

This skill is intentionally **high-level and durable**. For the precise, current contract
— abstract methods, exact signatures, return types (`BRIMParseOutput`,
`BRIMExtractedAssetInfo`, `BRIMValidationIssue`), base-class helpers, favicon handling, and
worked examples — **always read the developer guide**, which is the source of truth:

- **BRIM Plugin Guide** — `mkdocs_src/docs/developer/architecture/patterns/brim_plugin_guide.md`
- **Generic CSV reference** — `mkdocs_src/docs/developer/backend/brim/generic_csv.md`
- **Providers list** — `mkdocs_src/docs/developer/backend/brim/providers_list.md`
- **Reference implementations** — `broker_directa.py` (Italian broker) and
  `broker_generic_csv.py` in `backend/app/services/brim_providers/`.

Do not rely on this page for method signatures or exact conventions — they can change;
the developer guide is kept up to date.
