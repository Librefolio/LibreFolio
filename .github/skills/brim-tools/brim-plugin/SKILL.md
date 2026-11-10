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
9. **The operation date, and only settled rows.** Record every transaction on its **operation
   date**, the day the operation was made (the trade date), never on the settlement or value
   date (the developer's principle, 19/10/2026): the movement is recorded when it happens, not when the systems process it: in between the money is already gone and cannot be used, so hiding it would be wrong (the developer, 28/10/2026). No exception for a subscription during a placement or an IPO: the order of 17/02 is dated 17/02 even when the issue and the cash debit come on 25/02; LibreFolio shows the position at cost and the cash already gone in between, which is what happened. Then decide from the columns the
   report has
   whether the row is stable and booked:
   - a **status** column, when there is one, decides; what it says follows rule 10 (reserved,
     cancelled or pending are known; a word the plugin does not know is unknown);
   - otherwise a **value or settlement date** after the server's today (`server_today()`,
     `backend/app/utils/datetime_utils.py`, never the browser's date) marks a provisional row. It
     is left out **whole**, with every transaction it would have produced (its fee, its
     premium), and arrives with the next import. Say so with one `severity="info"` note per
     reason (a `code`, `context.count`, the rows as evidence), never a warning: nothing is
     wrong, the rows are simply not final yet (Fineco);
   - a report that covers a known period compares with its end instead (Danske Bank's cash
     file: a trade valued after its last day waits for the next import);
   - with neither, the operation date itself must not be after today.

   A report set that compares balances with the bank's, as Danske Bank does, compares them in
   operation-date terms: a truth on a day adds the cash and the quantities still in flight
   (operation date ≤ day < value date; `_Analysis.in_flight`), and its opening is the eve of the
   oldest operation date of the export, even when the cash statement starts later (the
   statement's first balance then stands for it). **The one exception is the
   Generic CSV**: its files are the user's own, so the date column the user maps is the
   transaction date, whatever it means.
10. **Known rows quietly, unknown rows loudly.** Leave a row out only for a reason the plugin can
    name (the developer's principle, 19/10/2026).
    - **Known and safe to leave out** — a blank, header or total row, a reservation (Danske
      Bank's «Varaus»), a row the broker marks as cancelled, a duplicate of another row: no
      notice, at most one backend log line per reason (`logger.info(…, reason=…, count=…)`). In a
      report set the row keeps its place in the set's accounting: an `excluded` outcome with its
      reason, labelled by `importWizard.reportSet.reason.<reason>`.
    - **Unknown or unreadable** — a type, status or description the plugin does not recognise;
      a date, amount or required field it cannot read: leave it out, and say so with one
      `severity="warning"` notice per reason (a `code`, `context.count`, the rows as evidence)
      that carries `context.report_issue = True`. The wizard then shows the link «open an issue
      on GitHub» under the warning, on every instance, self-hosted or hosted: the users become
      the canaries of a broker whose export changes. Example: Danske Bank's `excluded_status`.
      **Use the shared helper** `_brim_io.RowSkips` (W-B86): `skips = io.RowSkips(header_row)`,
      `skips.unknown(line, row, reason)` for a type or status the plugin does not recognise (or does
      not import yet), `skips.unreadable(line, row, reason)` for a date, amount or required field it
      cannot read (a `csv.DictReader` row works too: `skips.set_headers(reader.fieldnames)` first),
      then `warnings=[*warnings, *skips.notices()]`. It yields the two shared warnings
      `rows_not_recognized` and `rows_unreadable` (`context = {count, report_issue: True}`, the rows
      and a «Reason» column as evidence), already worded in the four languages
      (`importWizard.brimNotice.<code>`, `importWizard.brimEvidence.<code>`). A plugin with its own
      notice codes (DEGIRO, Crédit Agricole, Scalable, Danske) just adds `report_issue: True` to the
      context of the ones that mean «unknown» or «unreadable». A plain `warnings.append("Row 5: …")`
      cannot carry the link. `test_brim_row_skips.py` classifies every registered plugin: a new one
      must be listed there, with how to build an unknown and an unreadable row.
    - **Never silently** leave out a row that may carry an economic effect (a split, a fee, a
      tax, a currency conversion) unless the plugin knows that is safe: a row it cannot import
      is unknown.
    - Rule 9's rows not settled yet are neither: they keep their info note.
    - **Beta plugins.** While a plugin is in beta it may still write one plain string per skipped
      row (a `legacy` warning, no link): with no reliable reports there is no way yet to tell the
      safe rows from the unknown ones (decision of 19/10/2026, confirmed 22/10). That is a
      **rule, not a lot**: **leaving the beta means adopting `RowSkips`** (or your own codes with
      `report_issue`), in the same change that removes the Beta label. In
      `test_brim_row_skips.py` take the plugin out of `ROW_SKIPS_PENDING` and list it in
      `ROW_SKIPS_BY_PLUGIN` with an unknown and an unreadable row, and bump its
      `plugin_version`. Fineco did it when it left the beta (W-B92, 1.5.0).

## ⚙️ Settings (prepared, not used yet)

The plugin settings of the foundation (`services/plugin_settings/`) have a family `brim`, with the same rules as the price
sources: personal and instance-wide values, and secrets encrypted with the instance key. **No real plugin declares a field
today** (W-BS): a plugin that does not declare `settings_fields` is untouched. The day one needs a value (a date format, a
key), declare `settings_fields` on the class, as the asset and FX plugins do (skill `asset-plugin`); the card appears in the
Plugins tab by itself and a secret never comes back in clear. Read `self.settings.get("key")` and `self.settings.secret("key")`
**inside `parse`**, never in `__init__`: the parse runs in a worker process that re-creates the plugin, and the values are
bound to it just before it parses. **Only the parse delivers settings**: detection, report sets and the gap fix create the plugin
without values (defaults, no secret), so nothing they use may depend on a setting. Never log a secret nor put one in a notice.

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
