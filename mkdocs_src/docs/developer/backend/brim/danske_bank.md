# 🏦 Danske Bank Importer

`broker_danske_bank` imports the **equity savings account** (*osakesäästötili*) of Danske Bank
Finland from two exports that only make sense together: the custody transactions (XLSX) and the
cash statement (CSV). It lives in `backend/app/services/brim_providers/broker_danske_bank/plugin.py`
(`plugin_version` 1.1.0, 🔬 Alpha — built from the exports of one account, shared in
[issue #26](https://github.com/Librefolio/LibreFolio/issues/26)) and is LibreFolio's reference
**report-set plugin**.

This page covers what is specific to Danske Bank. The generic machinery — membership by upload
batch, `/sets/preview` and `/sets/combine`, the history start (H0), `/gap-fix` — is described in
[BRIM Architecture → Report sets](architecture.md#report-sets) and
[BRIM Plugin Guide → Multi-report plugins](../../architecture/patterns/brim_plugin_guide.md#report-sets),
the wizard side in
[Import Wizard → Report sets](../../frontend/components/features/import-wizard.md#report-sets).
The user's view is [Danske Bank](../../../user/transactions/import/danske-bank.md): the plugin's
`docs_url` points there, and so do the set card's *How to export it* links.

```mermaid
flowchart LR
    K["custody XLSX"] --> A["_Analysis<br/>read · rule M · classes<br/>pairs · zones · proofs"]
    C["cash CSV"] --> A
    A --> T["_TableBuilder<br/>combined CSV"]
    T --> P["_CombinedParser<br/>transactions · todos<br/>notices · truth points"]
    P --> H["apply_history<br/>H0"]
    H --> G["wizard review,<br/>then /gap-fix"]
```

`describe_set` and `combine` both build an `_Analysis` of the members; `combine` writes it out
through `_TableBuilder`, and `parse` reads back only the combined file (`_CombinedParser`). A
custody or cash file parsed alone raises `BRIMSetRequiredError`, naming the other role.

---

## 🗂️ Exports, roles and detection

| Role | Export (wizard name) | Extension | `max_history` | Coverage axis | `must_cover` |
|---|---|---|---|---|---|
| `custody` | *Securities transactions* — eBanking **Sijoitukset → Tapahtumat** | `.xlsx` | `P1Y` | trade date (`Kauppapäivä`) | — |
| `cash` | *Cash statement* — the account transactions of the account's cash account | `.csv` | `P5Y` | value date (`Pvm`) | `custody` |

Both roles are `required` and `multiple`. The plugin sets `settlement_lag_business_days` to 5 and
`pre_checkpoint_policy` to `summarize`, and keeps the default history tag, `danske_bank`.

**Detection.** `_file_kind()`, behind `can_parse` and `detect_role`, answers `custody`, `cash`,
`combined` or `None`:

- `.xlsx` (and `.xlsm`) — the first worksheet with data, read with `openpyxl` (values only), is
  `custody` when one of its first 20 rows (`_HEADER_SCAN_ROWS`) names every required custody column.
- `.csv` — decoded with the shared `TEXT_ENCODINGS` fallback (UTF-8 with or without BOM,
  Windows-1252, Latin-1) and split on `;`. A first row holding `lf_row_kind`, `lf_source`,
  `custody:Toimeksiantotyyppi` and `cash:Saaja/Maksaja` is `combined`; otherwise a header among the
  first 20 rows naming every required cash column makes it `cash`.
- Headers match case- and space-insensitively, a literal `<br/>` counting as a space (`_norm`). Any
  read error means «not ours».

`can_parse` accepts the three kinds, `detect_role` only the first two (`detection_priority` 100). A
downloaded combined file uploaded again is therefore an original without a role: the preview
reports it as `unknown_role`. No other plugin's `can_parse` accepts the sample exports, so the
wizard never offers *Read alone with ‹plugin›* for them.

| Export | Required columns | Also read |
|---|---|---|
| custody | `Kauppapäivä`, `Arvopäivä`, `Sijoituskohde`, `Määrä`, `Kurssi`, `Summa`, `Tila`, `Toimeksiantotyyppi` | `Palkkio sis. Alv`; the currency of `Summa` — `Valuutta`, or the unnamed column right after `Summa` (default EUR); `Säilytystili`, the custody account, read for the account check only and never copied |
| cash | `Pvm`, `Saaja/Maksaja`, `Määrä`, `Saldo`, `Tila` | `Tarkastus`. There is no currency column: the account is in euro |

Dates are `d.m.yyyy`. Numbers may use a space, NBSP or narrow NBSP as thousands separator, a comma
or a dot as decimal separator, and a Unicode minus (`_to_decimal`).

`describe_member()` reports rows and coverage. A custody file also gets an `account_fingerprint`,
the SHA-256 of its sorted `Säilytystili` values: custody files of different accounts make the
preview's `mixed_accounts`, and the set cannot be combined. Several accounts inside one custody
file only raise `mixed_accounts_in_file`.

---

## 🏷️ Row classes

### 📈 Custody rows

`_classify_custody()`: a `Tila` other than `Toteutettu` is `status`; a row without trade date,
value date, name or a non-zero quantity, or valued before its trade date, is `invalid`. Then the
order type decides:

| `Toimeksiantotyyppi` | Signs | Class |
|---|---|---|
| `Rajakurssi`, `Päivän kurssi`, `Pikakauppa` | `Määrä` > 0 and `Summa` < 0, or `Määrä` < 0 and `Summa` > 0; a `Kurssi` is required | `buy`, `sell` |
| `Tuotto` | `Määrä` > 0 and `Summa` > 0 | `income` |
| `Jakautuminen, vanha` | `Määrä` < 0, no `Summa` | `demerger_old` |
| `Jakautuminen, uusi` | `Määrä` > 0, no `Summa` | `demerger_new` |
| anything else | — | `unknown_type` |

A known order type with other signs is `invalid`.

### 💳 Cash rows

`_classify_cash()`: the label (`Saaja/Maksaja`) `Varaus` is checked first, before `Tila`: it makes
the row `reservation`, whatever its `Tila`. A reservation is a hold the bank replaces with the
booked movement: a known row, left out without a notice ([Finnish notices](#finnish-notices)). Then
a `Tila` other than `Toteutunut` is `status`; a row without a date, or with a zero or missing
amount, is `invalid`. Then the label and the sign decide (`_cash_label_class`):

| Label | Sign | Class | Becomes |
|---|---|---|---|
| `Osto <name>` | − | `buy` | half of a pair |
| `Myynti <name>` | + | `sell` | half of a pair |
| `<name> <10-digit reference>` | + | `income` | half of a pair |
| first word `Nosto` | − | `withdrawal` | `WITHDRAWAL` |
| first word `Vero` | − | `tax` | `TAX` |
| first word starting with `Palvelumaksu` | − | `fee` | `FEE` |
| first word `Korko` or `Hyvityskorko` | + | `interest` | `INTEREST` |
| any other credit | + | `deposit` | `DEPOSIT`, listed by the `deposit_assumed` notice: only the holder can pay into an equity savings account |
| any other debit, or a known word with the wrong sign | | `unknown_type` | excluded |

### 🧾 What the parse writes

| Combined line | Transaction | Date | Quantity | Cash |
|---|---|---|---|---|
| `pair` of a trade | `BUY` or `SELL` | custody `Kauppapäivä` | custody `Määrä` | cash `Määrä` |
| `pair` of a `Tuotto` | `DIVIDEND` | custody `Kauppapäivä` | 0 | cash `Määrä` |
| `standalone` cash row | `DEPOSIT`, `WITHDRAWAL`, `TAX`, `FEE` or `INTEREST` | `Pvm` | — | `Määrä` |
| `standalone` demerger line | `ADJUSTMENT` | custody `Kauppapäivä` | custody `Määrä` | — |

**The operation date** (1.1.0, lot B-52): every transaction is dated with the day the operation
was made, the plugin guide's rule *The operation date, and only settled rows* under
[Import philosophy](../../architecture/patterns/brim_plugin_guide.md#import-philosophy-currency-rules).
What comes from the custody export takes its trade date, `Kauppapäivä` — a purchase made on the
27th is a `BUY` of the 27th, whenever the bank moves its cash; for a `Tuotto` and a demerger line
the two custody dates are equal in the bank's exports. A cash-only row has no other date than its
`Pvm`. Before 1.1.0, pairs took the cash `Pvm` and demerger lines `Arvopäivä`, the value date.
Pairing, zones, `not_yet_settled` and `deferred_rows` still read the **value date**, because the
bank moves the cash on that day; the truth points bridge the two dates ([In flight](#in-flight)).

Cash is always EUR, taken as written. Every transaction is tagged `import` and `danske_bank`,
demerger lines also `demerger`. Each security gets one fake asset id per normalised name, with the
name as its only identifier (`extracted_name`): the exports carry no ISIN and no ticker.

`summarized`, `deferred` and `excluded` lines write no transaction (the last two feed the notices).
On a first import, the `standalone` rows of the `before` zone are written but dated before H0, so
the review hides them
([Import Wizard → Rows before H0](../../frontend/components/features/import-wizard.md#rows-before-history)).

**Sets imported before 1.1.0.** The wizard's duplicate check compares exact dates
([BRIM Architecture → Deduplication Logic](architecture.md#deduplication-logic)): a set imported
with 1.0.x and imported again brings its trades back on their trade date, a few days earlier than
the value date they were saved with, so the check does not recognise them. No code bridges the
two (the developer, 19/10/2026: the next imports carry the new date, so after the switch
everything settles). The transition, once: delete the Danske transactions those files created —
the `gap_fix` corrections included, so that the new import is a first import again — and import
the whole set again, or import only from the day after the last imported day. The user page says
the same.

---

## 🔗 Pairing trades with their cash

`_pair_rows()` pairs `buy`, `sell` and `income` rows only, on a key of **value date, amount to the
cent, currency and class** — `Arvopäivä`, `Summa` and the custody currency against `Pvm`, `Määrä`
and EUR. The class carries the direction.

- One custody row and one cash row on a key pair.
- More than 8 candidates on either side (`MAX_MATCH_CANDIDATES`) are all `ambiguous`.
- Interchangeable candidates — the same name, quantity, price, trade date and order type on the
  custody side, one label on the cash side — pair in file order, so identical partial fills stay
  two trades.
- Otherwise `_best_assignment()` keeps the assignment with the most compatible names, but only when
  every best assignment imports the same trades; if not, every candidate of the key is `ambiguous`.
  The plugin never guesses.

Two names are compatible when one normalised name is a prefix of the other, because the cash
statement truncates its labels. The name is a check, not a key: a pair whose names differ still
pairs, and the parse lists it in the `name_mismatch` notice.

**Several files of one role** (rule M, `_RoleMerge`): each day belongs to the file with the latest
coverage covering it — custody files by trade date, cash files by value date. The other files' rows
of that day count once when identical, and become `excluded` (`superseded`) when they differ;
`describe_set` then warns `overlap_mismatch`.

---

## 🗺️ Segments, zones and outcomes

- **Segments** — the custody files' trade-date spans, merged when they overlap or touch
  (`_raw_segments`). Two spans with a hole between them stay apart only when the cash statement
  proves trades in the hole: an unmatched cash trade valued after the first span and no later than
  5 business days after the eve of the second (`_proven_segments`). Otherwise they merge, hole
  included. Each hole left between two segments is a **gap** (`gaps()`, the preview's `gap`
  warning).
- **Checkpoint** — the eve of each segment, the day before its oldest trade date (`_timeline`),
  the first one included: also when the cash statement starts later
  ([A13](#a13-opening)). Before 1.1.0 the first one moved to the eve of the first booked cash day.
- **Window** — from the day after the checkpoint to the segment's last day plus 5 business days
  (`LAG_BUSINESS_DAYS`), capped at the next checkpoint. Its **border** is the first 5 business days
  after the checkpoint. Business days skip weekends only: holidays are not known.
- **Zones** of a value date (`_zone`): `before` (up to the first checkpoint), `window`, `gap` (after
  a window, up to the next checkpoint) and `after` (beyond the last window).

Every row gets exactly one outcome (`_Analysis._settle`):

| Row | Outcome |
|---|---|
| Custody row and cash row on one key | `pair` |
| Deposit, withdrawal, tax, fee or interest | `standalone`, imported with its own date |
| Demerger line | `standalone` |
| Cash trade or income without counterpart | `summarized` in the zone's checkpoint in `before` and `gap`, and in its own segment's checkpoint inside the border; valued after the segment's last day, `summarized` in the next segment's checkpoint, or `deferred` when there is none; `deferred` in `after`; elsewhere `excluded` (`no_counterpart`) |
| Custody trade or income without counterpart | `excluded`: `not_yet_settled` (valued after the cash statement's last day), `outside_cash_coverage` (outside the statement's spans), else `no_counterpart` |
| Ambiguous; superseded; `status`, `reservation`, `unknown_type`, `invalid` | `excluded` with that reason |

The cash rows of the `before` zone — standalone, `ambiguous` or `unknown_type` — are also absorbed
by the first checkpoint. The full matrix, zone by zone, is in the plugin guide, under *Zones and
outcomes*. When the cash statement starts after the custody export, the opening's border starts on
the custody export's eve, which leaves some cash trades `no_counterpart`
([A13](#a13-opening)).

The wizard's **Matching securities ↔ cash** reads the combined summary: the outcomes as chips
(*pairs*, *standalone rows*, *summarised in a checkpoint*, *with the next import*, *excluded*) and
one row per reason
([Import Wizard → Step analyze](../../frontend/components/features/import-wizard.md#set-analysis)):

| `lf_reason` | Wizard label | For Danske |
|---|---|---|
| `no_counterpart` | no counterpart | a trade or income in one file only, inside a window |
| `ambiguous` | ambiguous | candidates that cannot be told apart |
| `not_yet_settled` | not settled yet | a custody trade valued after the cash statement's last day |
| `outside_cash_coverage` | settled before the cash statement starts | a custody trade valued outside the cash statement's spans; valued before its first day, it belongs to the opening ([A13](#a13-opening)) |
| `status` | not executed or not booked | a custody `Tila` other than `Toteutettu`, or a cash `Tila` other than `Toteutunut` on a row that is no `Varaus`: the `excluded_status` warning, with the link to open an issue |
| `reservation` | reserved, not booked | a cash row labelled `Varaus`: no notice, one log line |
| `unknown_type` | unknown type | an order type or a label the plugin does not know |
| `invalid` | invalid | missing or inconsistent values |
| `superseded` | replaced by a newer file | rule M |

---

## 📄 The combined file

`_TableBuilder` writes one line per source row — a pair is one line — plus the truth rows
(`truth_cash`, `truth_position`, `verification`), sorted by day, the data lines before the truth
rows of the same day. The columns are the nine `lf_*` columns, then the verbatim `custody:<column>`
and `cash:<column>` values; the custody account (`Säilytystili`) is never copied.

The core writes the file (`write_combined_csv`: UTF-8 with BOM, `;`) under a generated name,
`Danske Bank — combined <first day>…<last day>.csv`, because the cash statement's own file name may
carry an account number. What each `lf_*` column holds is in the plugin guide, under *`combine` is
pure*.

`summary`, kept in the sidecar as `combine_summary`, holds `rows` per role, `outcomes`, `zones`,
`reasons`, `segments`, `gaps`, `checkpoints`, `verifications`, `balance_chain` (`ok` or `broken`)
and `overlap_mismatch_days`. `combine` refuses custody files without a dated row
(`BRIMParseError`, so a 422 `combine_failed`).

`plugin_version` covers `combine` and `parse` alike: bump it whenever either output changes for the
same files. The existing combined files then show **To re-combine**, and the next analysis rebuilds
them.

---

## 📍 Truth points

### 🏁 Starting point and «After the gap»

One checkpoint per segment, on its eve: the first is `opening`, the others `gap`. The wizard titles
them *Starting point · ‹date›* and *After the gap · ‹date›*. On a later import, `apply_history()`
drops the checkpoints before the eve of H0, turns the ones from H0 on into `gap` checkpoints and
removes what H0 already represents
([The history start (H0)](../../architecture/patterns/brim_plugin_guide.md#report-set-history)).

- **Cash** — the cash statement's running balance at the end of the checkpoint day, plus the cash
  of the border rows summarised in it: trades made before the custody export and settled after the
  checkpoint (`border_cash`); plus the cash in flight that day ([In flight](#in-flight)). For an
  opening that precedes the statement, the balance is the statement's first balance
  ([A13](#a13-opening)). Any other day the statement does not cover gets no cash (`not_covered`).
- **Absorbed rows** — every cash row the checkpoint summarises (`lf_checkpoint`), with date, amount
  and label. For the opening checkpoint, `opening_cash` is the checkpoint's cash minus their total:
  the balance before them. The gap-fix explanation reads both.

**Positions** come from proofs inside the segment's window, each brought back to the checkpoint by
removing the movements imported in between (by value date), then adding the quantity of the
security in flight that day — at most one per security:

- **E1** — a `Tuotto` states the shares that earned it: exact. Discarded when another movement of
  the security falls in the 30 days up to its trade date (`recent_trades`), when those 30 days start
  before both the segment and the cash statement (`window_not_covered`), or when an excluded row of
  the security lies between the checkpoint and the proof (`excluded_rows`).
- **E2** — the old line of a demerger states the whole holding: exact. Discarded on a same-day
  movement of the security (`same_day_movement`) or on excluded rows.
- **E3** — when no exact proof holds, selling more than was bought since the checkpoint proves
  **at least** the largest shortfall (`at_least`). Discarded on excluded rows.
- Exact proofs that disagree, or that give a negative quantity, are all discarded (`conflict`), and
  E3 is tried instead.

An excluded row never discards a proof when it belongs to the opening: a custody trade settled
before the cash statement starts (`_absorbed_by_opening`, [A13](#a13-opening)). A discarded proof
is written `discarded:<rule>:<reason>` in `lf_proof` and listed by the `proof_discarded` notice.
Danske never states a `unit_cost`.

### ✅ End-of-period check

One `verification`, on the last day of the last segment — or on the cash statement's last day when
it ends first — provided the running balance covers that day. Its cash is the running balance plus
the cash in flight that day ([In flight](#in-flight)), and the wizard titles it
*End-of-period check · ‹date›*. It is never a checkpoint: the next
import brings the `not_yet_settled` and `deferred` trades one by one, and a correction there would
count them twice (the safety rule of the plugin guide).

The running balance (`_chain`) takes the booked rows (every class but `status`, `reservation` and
`invalid`: `_UNBOOKED_CLASSES`) by value date — within a day in reverse file
order, since the statement lists the newest rows first — and checks each day against `Saldo`, row
by row or at least as a day total. A day that does not add up is a break: the chain goes on from
that day's last `Saldo`, and the cash of every checkpoint becomes a verification instead
(`balance_chain_broken`, warned by both `describe_set` and the parse).

### ✈️ In flight {: #in-flight }

A pair is recorded on its trade date, while the bank moves its cash on its value date, a few
business days later. In between, the trade is **in flight**: LibreFolio already holds it, the
bank's balance does not yet. So every truth at a day D adds what is in flight at D
(`_Analysis.in_flight(day)`, 1.1.0): the paired purchases and sales with trade date ≤ D < value
date — their cash, a purchase negative and a sale positive, and their quantity per security. It
applies to:

- the cash of every checkpoint, and the verification a broken chain gives in its place;
- the positions of every checkpoint, each for its own security;
- the end-of-period verification.

The gap-fix then compares LibreFolio, in operation-date terms, with the bank, whose balances are in
value-date terms, without false corrections. Only the imported purchases and sales count: a trade
left out (`not_yet_settled`, `outside_cash_coverage`…) or summarised is never in flight, nor is a
`Tuotto`, whose two dates are equal. The opening never has anything in flight, since every trade of
the set comes after it; a gap checkpoint or the end-of-period check may.

### 🕰️ A cash statement that starts later (A13) {: #a13-opening }

When the cash statement starts after the custody export — case A13 of the design
(`design-phase00BrimReportSets.md`) — the set still opens on the eve of the custody export's
oldest trade date, like any set (`_timeline`): a trade is recorded on its trade date, so the
opening must come before every one of them (the developer, 20/10/2026). Until 1.0.2 it opened on
the eve of the statement's first booked day.

- **The opening's cash** is the statement's first balance, in value-date terms: the balance before
  its first booked row, on the eve of its first booked day (`_checkpoint_lines`), plus the border
  rows as for any checkpoint. Nothing is in flight then.
- **A trade made before the statement starts and settled inside it** pairs as usual: it is imported
  as a `BUY` or `SELL` on its trade date, after the opening, with its true cost. The opening's
  positions subtract it, like any movement between the opening and a proof.
- **A trade settled between the opening and the statement's first day** has no cash row. It stays
  `excluded` (`outside_cash_coverage`, with the same `excluded_outside_cash_coverage` warning as
  before), but its cash is inside the statement's first balance: it lands in the opening, a few
  days before the day it was made — at most as many days as the statement starts after the custody
  export. The developer accepted this explicitly (20/10/2026). Its units
  belong to the opening too: the row no longer discards a proof of its security
  (`_absorbed_by_opening`), so a later proof — a `Tuotto`, a demerger's old line, a sale of more
  than was bought — brings them into the opening's position. A security with no proof gets no
  opening position, as anywhere else.
- **A sale straddling the statement's start, for a security with no exact proof** — the «at
  least» proof E3 gives the opening at least the shares sold, so the position never goes negative
  (an unchanged rule). Only another excluded row of the security between the opening and the sale
  — a row of unknown status, an invalid or ambiguous one — discards E3: the security then has no
  opening position (`proof_discarded`), and saving refuses the sale's day with
  `balanceAssetNegative` unless the broker allows shorting. In such a set that interval now starts
  on the custody export's eve, no longer on the statement's.
- **A side effect, rare.** The opening's border — the 5 business days after the checkpoint — now
  starts on the custody export's eve too. A cash trade row with no custody counterpart, valued
  after that border and no later than the segment's last day, is `excluded` (`no_counterpart`, a
  warning) instead of being summarised into the opening: the custody export covers its day, and
  its row is missing there.

---

## 🧮 The `gap_fix` corrections

`compute_gap_fix()` (`backend/app/services/brim/brim_gap_fix.py`) is generic
([Plugin Guide → report sets](../../architecture/patterns/brim_plugin_guide.md#report-sets),
[Import Wizard → Step gapFix](../../frontend/components/features/import-wizard.md#gapfix-step));
with this plugin's truth points it gives:

- For each checkpoint in date order, LibreFolio's state at the end of the day: the broker's saved
  transactions (without pending deletions) plus the editor's unsaved rows, the wizard's selection
  and the corrections proposed at the earlier checkpoints. Transactions entered by hand count like
  imported ones.
- **Cash** — a difference above 0.01 € becomes a **Deposit** (`DEPOSIT`, the bank holds more) or
  a **Withdrawal** (`WITHDRAWAL`, it holds less), dated on the checkpoint, that brings the cash to
  the checkpoint's: the cash statement's balance, with what is [in flight](#in-flight).
- **Positions** — an `exact` position gets an `ADJUSTMENT` of the difference, positive or negative;
  an `at_least` one only the missing part. With no `unit_cost` from Danske, every positive
  adjustment carries the blocker todo `gap_fix_cost` on `cost_basis_override`: the wizard tags it
  *cost to enter*, and the bulk editor waits for the cost. A negative adjustment carries no cost. A
  position whose security is still unresolved is left out (`unresolved_asset`).
- Tags `import`, `danske_bank` and `gap_fix`; description
  `Gap-fix <date> — Danske Bank: <what> at the end of the day, as stated by the bank`.
- The end-of-period verification is compared (`ok` within 0.01 €), never corrected.

Once saved, a correction counts in H0 from the day after its date. A later set whose segment covers
its date gets the preview warning `covers_gap_fix` (delete the correction after the import, or the
cash counts twice); a segment that ends before H0 gets `before_history_segment` and is not
imported.

---

## 💶 The commission estimate

The exports give one total per trade: the fee column (`Palkkio sis. Alv`) is always 0, and the
commission is inside `Summa`. Every paired purchase and sale therefore gets the `warning` todo
`danske_trade_charges_included` on `cash` (`_charges_todo`); dividends get none.

- **Context** — `split_hint: "trade_charges"`, so the **Corrections** step owns the row
  (`isCashSplitWarning`) and every trade needs a decision; `compare_nominal: false`; `cash` (the
  absolute amount), `currency`, `row`, `split_suggestions`, and `charges` when the estimate is
  plausible.
- **Estimate** — gross = absolute quantity × `Kurssi`, rounded to the cent; charges = absolute
  amount − gross for a purchase, gross − absolute amount for a sale. It is plausible when
  0 ≤ charges ≤ max(15 €, gross ÷ 100): the first suggestion then gives both figures, valid if the
  price is in euro. Otherwise it says the price may be quoted in another currency, so the
  commission cannot be computed from the file.
- The second suggestion always points to the trade confirmation in eBanking.

---

## ✂️ Demergers

`Jakautuminen, vanha` and `Jakautuminen, uusi` lines are never paired: booked, with the right
signs, they become cashless `ADJUSTMENT`s in any zone, dated on `Kauppapäivä` (equal to
`Arvopäivä` in the bank's exports; `Arvopäivä` before 1.1.0) and tagged `demerger`.

- **New line** — blocker todo `demerger` on `cost_basis_override`: the file gives no acquisition
  cost. A demerger is tax-neutral in Finland, and the old cost is split among the new shares in the
  ratio the Tax Administration publishes. The bulk editor's **Save All** waits for it.
- **Old line** — warning todo `demerger_old_leg` on `quantity`: it removes the whole holding without
  moving its cost to the new lines, so invested capital does not drop by itself.

Neither todo enters the **Corrections** step: a cost-basis blocker belongs to the bulk editor, and
the old-line warning has no `split_hint`. The old line is also proof E2 of the holding.

---

## 🇫🇮 Finnish notices

The parse speaks the language of the files: notice messages, todo messages and evidence comments
are in Finnish. Evidence tables are titled `Arvopaperitapahtumat` (custody columns) and
`Tilitapahtumat` (cash columns), with the line numbers of the combined file.

| Notice | Severity | Says |
|---|---|---|
| `excluded_<reason>` | warning | One per exclusion reason, with its rows: they are not imported. Every reason but `not_yet_settled` (an info note), `status` (its own row) and `reservation` (no notice). No `report_issue` |
| `excluded_status` | warning | The rows whose `Tila` the plugin does not know (`status`): not imported. `context.report_issue` is `true`, so the wizard shows the link *open an issue on GitHub* under the message, which asks the user to open one if the rows are real movements, so that the plugin learns the case (the plugin guide's rule *Known rows quietly, unknown rows loudly*, under [Import philosophy](../../architecture/patterns/brim_plugin_guide.md#import-philosophy-currency-rules)) |
| `excluded_not_yet_settled` | info | Custody trades valued after the cash statement's last day: not imported this time, they come with the next import. A note since N74, no longer a warning: nothing is wrong (the plugin guide's rule *The operation date, and only settled rows*, under [Import philosophy](../../architecture/patterns/brim_plugin_guide.md#import-philosophy-currency-rules)) |
| `deferred_rows` | info | Cash trades after the last custody day come with the next import |
| `name_mismatch` | warning | Paired trades whose names differ: check them |
| `proof_discarded` | info | Holdings the files could not prove reliably (`context.proofs`) |
| `balance_chain_broken` | warning | The statement's balances are only compared, never used for corrections |
| `deposit_assumed` | info | Credits read as deposits: check them |

A reservation (`reservation`, in `_SILENT_EXCLUSIONS`) gives no notice: the parse writes one
backend log line, `logger.info` with its `reason` and `count`, and the rows keep their place in the
set's accounting: `excluded` lines of the combined file, counted in the summary's `reasons` and
labelled *reserved, not booked* (`importWizard.reportSet.reason.reservation`). `status` is the one
reason in `_REPORTED_EXCLUSIONS`, the only `excluded_<reason>` notice with `report_issue`.

The todo codes — `danske_trade_charges_included`, `demerger`, `demerger_old_leg` — are in the
contract suite's `KNOWN_REASON_CODES`. The set warnings of `describe_set` (`empty_member`,
`mixed_accounts_in_file`, `overlap_mismatch`, `gap`, `balance_chain_broken`) and the gap-fix todo
`gap_fix_cost` are written in English and localised by the wizard
(`importWizard.reportSet.warning.<code>`, `importWizard.reportSet.gapFix.todo.<code>`).

---

## 🚦 Set statuses

| Where | Status | For a Danske set |
|---|---|---|
| `/sets/preview`, per role | `present`, `missing`, `excess` | `excess` never occurs: both roles are `multiple` |
| `/sets/preview`, `complete` | every required role present, no excess, no mixed accounts | mixed accounts can only come from custody files |
| `/sets/preview`, `missing` | the period a missing export must cover | a missing cash statement: from the eve of the first custody trade date to the last one; a missing custody export: no period |
| Step `upload` | after an upload, **Next** stays once on `upload` while a set of the session is incomplete | names the missing export, its extension and its period |
| Set card (`data-set-status`) | `loading` *Checking…*, `complete` *Complete*, `incomplete` *A file is missing* or *Cannot be combined*, `error` *Check failed* | *Cannot be combined* means mixed accounts; *Already analysed* is added when a parsed combined file of exactly these members exists |
| Files table | **Set of ‹date›**, **Incomplete**, **Combined**, **Used in a combined file**, **To re-combine** | [Import Wizard → Badges](../../frontend/components/features/import-wizard.md#report-set-badges) |

The cash role's coverage warnings (`must_cover: custody`) — `coverage_starts_late` when the
statement starts after the eve of the first custody trade date (the set still opens on that eve:
[A13](#a13-opening)), `coverage_ends_early` when it ends
before the last one — never block the set. How the user changes a set (*Read as*, *Remove from the
set*) is generic:
[Import Wizard → How a set is read](../../frontend/components/features/import-wizard.md#set-read-as).

---

## 🧪 Samples and tests

- `backend/app/services/brim_providers/sample_reports/` holds the **main** set
  (`danske_bank-custody.xlsx`, `danske_bank-cash.csv`) and the **gap** set
  (`danske_bank-gap-custody-1.xlsx`, `danske_bank-gap-custody-2.xlsx`, `danske_bank-gap-cash.csv`):
  synthetic values on the real column layout, declared in `test_sample_sets` and described in the
  folder's `README.md`.
- `./dev.py test external brim-danske-bank` (`test_external/test_brim_danske_bank.py`) pins the
  plugin's own rules — `TestOperationDateTruths` the operation date, the truths in flight and the
  A13 opening, end to end through the gap-fix of a first import; the generic suites are listed in
  [Testing a report-set plugin](../../architecture/patterns/brim_plugin_guide.md#report-set-tests).

## 🔗 Related

- [Danske Bank — user guide](../../../user/transactions/import/danske-bank.md)
- [BRIM Architecture → Report sets](architecture.md#report-sets)
- [BRIM Plugin Guide → Multi-report plugins (report sets)](../../architecture/patterns/brim_plugin_guide.md#report-sets)
- [Import Wizard → Report sets](../../frontend/components/features/import-wizard.md#report-sets)
- [BRIM Providers List](providers_list.md)
