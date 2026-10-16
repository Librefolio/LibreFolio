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
`backend/app/services/brim_providers/broker_<name>/` (one folder per broker: `plugin.py` holds
the code, `i18n/` its name and description), extends `BRIMProvider`, and is auto-discovered via
`@register_provider(BRIMProviderRegistry)`. Both come from the BRIM runtime, `backend/app/services/brim/`:
the contract from `brim_provider.py`, the registry from `registry.py`.

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
4. **Detect the delimiter, never assume the encoding.** Always resolve the separator with
   the base-class `detect_csv_delimiter` helper — never hardcode `,` or `;` — and read the
   file with `self._open_text(file_path)` (or `_brim_io.read_rows`), never with
   `open(..., encoding=...)`: bank exports are often Windows-1252 or Latin-1.
5. **Handle multiple layouts.** When a broker ships more than one report layout (e.g. with
   and without commission columns), detect the variant **dynamically**: locate the header
   row and branch on the real column set, not a fixed line offset.
6. **Correct sign conventions.** Set signs per transaction type (BUY: qty > 0 / cash < 0;
   SELL: qty < 0 / cash > 0; DIVIDEND & INTEREST: qty = 0 / cash > 0; FEE & TAX: qty = 0 /
   cash < 0; ADJUSTMENT: qty ≠ 0 / no cash), but take magnitudes verbatim from the report.
7. **`cost_basis_override` is PER-UNIT.** If you freeze an inherited cost basis (WAC) on a
   `TRANSFER`/`ADJUSTMENT` seed (opening snapshot, TRANSFER_IN), store the cost **per single
   unit**, never the total — the engine multiplies it by `quantity`. If the source reports a
   total countervalue, divide by quantity first, and round that quotient with
   `round_computed_value(value, Transaction, "cost_basis_override")` (`backend/app/db/precision.py`):
   a figure you compute is rounded explicitly, never one you read (C-97, decision D6). Set
   `cost_basis_currency` alongside it.
   Limits: a quantity keeps 10 decimal places, an amount 6, a price or per-unit cost 12,
   any of them 15 significant digits. A number read from the report beyond them is imported
   as read and refused at **Save All** with the maximum (decision D2): never round it.
8. **Fake asset IDs.** Emit high positive placeholder asset IDs — start at
   `FAKE_ASSET_ID_BASE` (`2**31 - 1`, in `backend/app/schemas/brim.py`) and count down, one
   per ISIN/ticker — plus the extracted asset info, so the core can drive the
   asset-matching UI. They are never negative and never persisted.

## 🛠️ Rough shape of the work

1. Create the folder `backend/app/services/brim_providers/broker_<name>/`: `__init__.py`
   (docstring only, no re-export) and `plugin.py`, which extends `BRIMProvider` and is decorated
   with `@register_provider(BRIMProviderRegistry)`. Import and patch from `….broker_<name>.plugin`.
2. Implement `can_parse` (quick header/extension sniff) and `parse` (full parsing →
   `BRIMParseOutput`). Use the base-class helpers instead of re-implementing them.
3. Map the broker's operation labels to `TransactionType`, applying the sign rules above.
4. Add a sample export under `sample_reports/`, set `test_file_pattern`, and add a
   user-facing docs page under `mkdocs_src/docs/user/transactions/import/`.
5. Give the plugin its name and description in EN/IT/FR/ES, in its own `i18n/`:
   `./dev.py i18n add brimPlugins.broker_<name>.name --en … --it … --fr … --es …
   --into brim_providers/broker_<name>` (and `.description`). The gate
   `utils gate-plugin-i18n-ownership` checks they live there.

## 📚 Where to find the technical details

This skill is intentionally **high-level and durable**. For the precise, current contract
— abstract methods, exact signatures, return types (`BRIMParseOutput`,
`BRIMExtractedAssetInfo`, `BRIMValidationIssue`), base-class helpers, favicon handling, and
worked examples — **always read the developer guide**, which is the source of truth:

- **BRIM Plugin Guide** — `mkdocs_src/docs/developer/architecture/patterns/brim_plugin_guide.md`
- **Generic CSV reference** — `mkdocs_src/docs/developer/backend/brim/generic_csv.md`
- **Providers list** — `mkdocs_src/docs/developer/backend/brim/providers_list.md`
- **Reference implementations** — `broker_directa/plugin.py` (Italian broker) and
  `broker_generic_csv/plugin.py` in `backend/app/services/brim_providers/`, each with its `i18n/`.

Do not rely on this page for method signatures or exact conventions — they can change;
the developer guide is kept up to date.
