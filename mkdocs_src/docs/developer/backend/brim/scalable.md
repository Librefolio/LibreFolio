# 🏦 Scalable Capital Importers

`broker_scalable` and `broker_scalable_deposit` import the two accounts of **Scalable Capital**,
each into a LibreFolio broker of its own: the **broker account** (*Scalable Capital broker*) and the
**overnight account** (*Scalable Capital overnight account*). They live in
`backend/app/services/brim_providers/broker_scalable/plugin.py` and `broker_scalable_deposit/plugin.py`
(`plugin_version` 1.1.0, `.csv` only, `detection_priority` 100), which hold only their properties
and calls to the shared reader, `_scalable.py`: recognition, refusals and parsing are written once,
for both accounts. The leading underscore keeps `_scalable.py` out of the registry's
auto-discovery.

This page covers what is specific to Scalable. The user's view is
[Scalable Capital](../../../user/transactions/import/scalable.md), where the `docs_url` of both
plugins points.

---

## 🗂️ Files and detection

Every file starts with the 14 columns of Scalable's own CSV export (`PRIME_COLUMNS`):

```text
date;time;status;reference;description;assetType;type;isin;shares;price;amount;fee;tax;currency
```

| File | Header | Read by |
|---|---|---|
| Scalable's own CSV — PRIME and PRIME+ plans, broker account only | the 14 columns | `broker_scalable` |
| The [LibreFolio exporter](https://github.com/Librefolio/librefolio-exporter)'s broker file | the 14 columns, then `lf_*`; `lf_account` is `broker` | `broker_scalable` |
| The exporter's overnight account file | the 14 columns, then `lf_*`; `lf_account` is `deposit` | `broker_scalable_deposit` |

- **Recognition** (`read_file`, behind `can_parse`): a `.csv` whose first line holds the 14
  columns, in any case and any order, split on the delimiter the base class detects. Without an
  `lf_account` column the file is Scalable's own CSV, always the broker account; with it, the
  `lf_account` values give the account — `broker`, `deposit`, both (`mixed`), or none for an
  export without rows, which both plugins accept. The file name is never read: the user may rename
  the file. A file that cannot be read is simply not a Scalable export: recognition never raises.
- **Refusals** (`refusal`): each plugin refuses the other account's file, and both refuse a mixed
  one, with a code and — except for the mixed file — the plugin that reads it. The codes are
  listed in
  [Saying why with a code](../../architecture/patterns/brim_plugin_guide.md#cannot-parse-detail).
  Any other file gets no refusal.
- **Values** are read by column name. The 14 columns use the decimal comma (`to_decimal_it`) and
  `date` is `YYYY-MM-DD`. Of the exporter's own columns, described in its
  [format](https://github.com/Librefolio/librefolio-exporter/blob/main/docs/formats/scalable.md),
  the reader uses `lf_account`, `lf_id`, `lf_subtype`, `lf_is_cancellation`, `lf_ordered_shares`
  and `lf_account_index`.

---

## 📝 What is imported

`_Reader` takes the data rows in file order. A reversal (`lf_is_cancellation` is `true`) and a row
whose `status` is not `Executed` or `Settled` are left out (see *Only executed rows* below for
what each status gets), and so is a row without a readable `date`, `amount` or `currency`. Then
`type`, compared lower-case, decides:

| In the file (`type`) | Imported as |
|:--|:--|
| `Buy`, `Savings plan` | `BUY` on the gross `amount` — the value of the shares, as Scalable's CSV and exporter 1.0.1 or later write it — with `fee` as a `FEE` and a positive `tax` as a `TAX` of the same asset. A negative `tax`, given back, becomes a `DEPOSIT` without asset |
| `Sell` | `SELL`, the same way |
| a type containing `Distribution` | `DIVIDEND`, gross — `amount` plus the tax withheld in `tax` — with that tax as a `TAX` of the same asset; net when `tax` is empty |
| `Interest` | `INTEREST`, gross, with the tax withheld as a `TAX`, both without asset; net when `tax` is empty |
| `Deposit`, `Withdrawal` — bank transfers, and transfers between the two accounts | `DEPOSIT`, `WITHDRAWAL` |
| `Fee` | `FEE`, without asset |
| `Taxes`, `Tax` | `TAX`, without asset; a positive amount, a refund, becomes a `DEPOSIT` |
| Any other row whose `assetType` is `Cash`, such as a bonus | `DEPOSIT` or `WITHDRAWAL`, by the sign of `amount` |
| `Security transfer`, `Corporate action` and any other type | Not imported: the `scalable_not_imported` notice lists them |

- **Signs**: a cash row whose sign contradicts its type — a negative `Deposit`, a positive
  `Withdrawal` or `Fee` — is booked by its sign, and so is a negative dividend or interest
  (`scalable_cash_by_sign`). A cash row, a dividend or an interest of zero is not imported
  (`scalable_not_imported`).
- **Trades without their details**: in an exporter file, an empty `fee` means the details were
  not read, and the trade is booked on `amount` as it is, without legs (`scalable_fees_unknown`).
- **Exporter 1.0.0** is not supported: its trades carry the fee and the tax inside `amount`
  (added on a purchase, taken away on a sale), so both would be counted twice; the user exports
  again with 1.0.1 or later.
- **Only executed rows** are imported (`status` `Executed` or `Settled`, compared lower-case). What
  the others get follows the rule *known rows quietly, unknown rows loudly*
  ([plugin guide](../../architecture/patterns/brim_plugin_guide.md#row-skips)), in `_Reader._not_executed`:
    - A `Pending` row with `lf_ordered_shares` and some `shares` already executed is an order filled
      in part (`scalable_open_partial`): it comes, executed, with a later export.
    - `pending`, `cancelled`, `canceled`, `expired` and `rejected` (`_NOT_EXECUTED`) are known, and
      not a movement: no notice, one log line at the end of the file with the count of each status. An
      order executed later comes with the next export.
    - Any other status goes to the shared notice `rows_not_recognized` (reason `status: <value>`); an
      empty one goes to `rows_unreadable` (reason `status`). The notice `scalable_not_executed` no
      longer exists.
- **Assets**: one fake asset id per ISIN — per `description` when the row has no ISIN — counting
  down from `FAKE_ASSET_ID_BASE` in order of first use, with `extracted_isin` and
  `extracted_name` (`description`) and no symbol; only the assets of written transactions are
  returned. The user matches them to LibreFolio's assets in the wizard's Review step. A trade or a
  dividend with neither ISIN nor description is unreadable.
- **Descriptions** (`_description`): an optional leg prefix — `Order fee`, `Tax`, `Tax refund` —
  then the row's `description` (its `type` when empty, `Scalable Capital` when both are) cut to
  350 characters, then `id <lf_id>` in exporter files and `ref <reference>` when the row has one,
  joined by ` · `. The id keeps two identical movements of one day apart and lets a new export
  recognise the rows already imported: the [deduplication](architecture.md#deduplication-logic)
  makes a match on the key fields `LIKELY`, unticked, only when the descriptions match too. Only
  the exporter's descriptions carry `id …`, so a row imported from one layout comes back from the
  other as a `POSSIBLE` duplicate, ticked.
- **Transfers between the two accounts** (`lf_subtype` `CASH_TRANSFER_IN` or
  `CASH_TRANSFER_OUT`) are imported as plain `DEPOSIT` and `WITHDRAWAL` and listed by
  `scalable_internal_transfers`: a `CASH_TRANSFER` links two brokers, so the user merges the two
  halves in the bulk editor ([Transfers](../../../user/transactions/import/scalable.md#transfers)).
  A merged half still matches when it is exported again
  ([Merged transfers and exchanges](architecture.md#dedup-merged-legs)).
- **Tags**: `import` and `scalable` (`_TAGS`), from both plugins, so the two halves of a merged
  transfer carry the same tags. Both plugins declare `history_tag` `scalable` to match:
  `broker_scalable` by default, `broker_scalable_deposit` by override, since its default would be
  `scalable_deposit`.
- **Amounts are copied** from the file, never recomputed or converted — a gross dividend or
  interest is the sum of `amount` and the tax withheld — and the currency comes from each row's
  `currency`: a value that is not an ISO 4217 code makes the row unreadable.

---

## 🔔 Notices

`_NOTICES` holds the ten notices of Scalable's own in display order, each with its severity, an English message
and the comment of its evidence table. A notice comes only when it has rows, with `context.count`
and one `BRIMEvidence`: those rows under the file's header, with their line numbers and an empty
`title`, so the wizard captions the table itself. The wizard words the message as
`importWizard.brimNotice.<code>` and the comment as `importWizard.brimEvidence.<code>`, keys
present in the four catalogues; the English texts are the fallback
([Talking to the import wizard](../../architecture/patterns/brim_plugin_guide.md#talking-to-the-import-wizard)).

| Code | Severity | Rows |
|---|---|---|
| `scalable_unreadable_rows` | warning, `report_issue` | A date, an amount, a currency, the shares or the security missing or unreadable: not imported |
| `scalable_fees_unknown` | warning | Exporter rows without their fee and tax details: imported on the amount shown, without legs |
| `scalable_open_partial` | warning | Orders filled in part and still open: not imported yet |
| `scalable_reversal` | warning | Reversals of a transaction already booked: not imported |
| `scalable_not_imported` | warning, `report_issue` | Security transfers, corporate actions, other types and zero amounts |
| `scalable_several_overnight_accounts` | warning | The first row of each overnight account (`lf_account_index`), when the file holds more than one: they all go into one broker |
| `scalable_internal_transfers` | info | Transfers between the two accounts: imported, to be merged |
| `scalable_dividends_net` | info | Dividends without `tax`: imported net |
| `scalable_tax_refund` | info | Tax refunds: imported as `DEPOSIT` |
| `scalable_cash_by_sign` | info | Cash rows of an unknown type, or with an unexpected sign: booked by the sign of `amount` |

The two warnings marked `report_issue` carry `context.report_issue = True`: the wizard shows the link
*open an issue on GitHub* under them, because a row the importer cannot read, or does not import, may
move shares or cash. Besides these ten, `_Reader.skips` (a `RowSkips`, built on the file's header)
collects the rows with an unknown or empty `status` into the two **shared** notices `rows_not_recognized`
and `rows_unreadable`, appended after the ten; their texts are written once for every plugin
([BRIM Architecture → Rows left out](architecture.md#brim-row-skips)).
---

## 🧪 Samples and tests

- `backend/app/services/brim_providers/sample_reports/` holds `scalable-prime-export.csv`
  (Scalable's own CSV), `scalable-broker-export.csv` and `scalable-deposit-export.csv` (exporter
  1.0.1, one file per account, whose internal transfers mirror each other): invented values on the
  real layout, described in the folder's `README.md`.
- `./dev.py test external brim-scalable` (`test_external/test_brim_scalable.py`) pins recognition,
  refusals, the three samples row by row, the rules on synthetic files and the catalogue keys;
  `./dev.py test api brim-scalable` (`test_api/test_brim_scalable_api.py`) imports both accounts
  end to end, merges the transfers and imports them again as duplicates.

## 🔗 Related

- [Scalable Capital — user guide](../../../user/transactions/import/scalable.md)
- [BRIM Providers List](providers_list.md)
- [BRIM Architecture → Deduplication Logic](architecture.md#deduplication-logic)
- [BRIM Plugin Guide → Saying why with a code](../../architecture/patterns/brim_plugin_guide.md#cannot-parse-detail)
- [LibreFolio exporter](https://github.com/Librefolio/librefolio-exporter), and its
  [CSV format](https://github.com/Librefolio/librefolio-exporter/blob/main/docs/formats/scalable.md)
