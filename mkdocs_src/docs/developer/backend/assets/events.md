# 📅 Asset Events

Asset events represent significant occurrences that affect an asset's price or generate distributions. They live in the **asset domain**, not the portfolio/transaction domain.

## 📋 Event Types

| &nbsp; | Event Type                    | Effect on Price                    | Who Generates                                        | Description                                    |
|:------:|:------------------------------|:-----------------------------------|:-----------------------------------------------------|:-----------------------------------------------|
| 💰     | **DIVIDEND**                  | Price drops by event value (ex-date) | Provider (yfinance, justetf) or manual              | Cash distribution from equity/ETF              |
| 📈     | **INTEREST**                  | Price drops by event value         | Scheduled Investment (`generate_interest`) or manual | Interest payment from debt/loan. Resets accrued interest |
| 📊     | **PRICE_ADJUSTMENT**          | Algebraic change (+/−)             | Manual, or listed in a Scheduled Investment schedule | Non-cash value change (write-down, haircut)    |
| ✂️     | **SPLIT**                     | Changes quantity, not total value  | Provider (yfinance) or manual                        | Stock/unit split                               |
| 🏁     | **MATURITY_SETTLEMENT**       | Final capital return               | Scheduled Investment (`generate_interest`) or manual | Asset reaches maturity — no further calculations |

The type is always one of these five values (`AssetEventType`). `FAAssetEventPoint`
(`schemas/assets/events.py`), the event point of the API, of the provider output and of the
Scheduled Investment `asset_events`, trims and upper-cases it (`normalize_type()`: `dividend`
becomes `DIVIDEND`) and refuses anything else: `POST /api/v1/assets/events` answers 422. Until 1.3
a type was stored as it came (a hand-written CSV could store `dividend`), and one the enum does not
know broke every later read of the asset's events (`LookupError`, a 500). The post-migration fix
`event_types` repairs the rows stored that way, once, at the first start after the upgrade
(decision 23 of release 1.3; see
[Post-migration fixes](../../architecture/database/index.md#post-migration-fixes)).

---

## 🗃️ Database Model

```mermaid
erDiagram
    ASSET ||--o{ ASSET_EVENT : "has events"
    ASSET_PROVIDER_ASSIGNMENT ||--o{ ASSET_EVENT : "generates"

    ASSET_EVENT {
        int id PK
        int asset_id FK "→ assets.id"
        date date "Event date"
        enum type "DIVIDEND, INTEREST, PRICE_ADJUSTMENT, SPLIT, MATURITY_SETTLEMENT"
        decimal value "Monetary value"
        string currency "ISO 4217"
        int provider_assignment_id FK "nullable — NULL = manual"
        text notes "nullable"
    }
```

**No UniqueConstraint** on `(asset_id, date, type)` — auto-generated and manual events can coexist on the same date and type. Nothing forbids two rows of the **same** source on one key either: the upsert below collapses such legacy duplicates when a batch brings fewer events for that key.

**Indexes**: `(asset_id, date)`, `(asset_id, type, date)`, `(provider_assignment_id)`.

---

## 🔄 Dedup Strategy

`_write_asset_events()` (`assets/event_store.py`) writes both kinds of events **in place**,
one source per call: a sync passes the assignment's id through `_upsert_asset_events()`, which
returns their count; the manual upsert passes `None` and gets back the id of the row each event
wrote. It groups the incoming events by `(date, type)` and matches each key against the stored rows
of the **same** source only (same `asset_id` and `provider_assignment_id`, `IS NULL` for manual
events):

```python
# Simplified logic of _write_asset_events() and _write_event_group(), for each (date, type) key
stored = rows on the key with this asset_id and provider_assignment_id, ORDER BY id
for row, evt in zip(stored, incoming):  # paired lowest id first: updated, id kept
    row.value, row.currency = evt.value.amount, evt.value.code or default_currency
    row.notes, row.updated_at = evt.notes, now
session.add_all(incoming[len(stored):])  # extra incoming events are inserted
surplus = stored[len(incoming):]  # legacy same-key duplicates of this source
# UPDATE transactions SET asset_event_id = stored[0].id WHERE asset_event_id IN surplus
# DELETE FROM asset_events WHERE id IN surplus
```

A key thus ends with as many rows as the batch brings, the lowest ids kept, and the transactions of
a collapsed duplicate move to the row that stays. Rows of another source on that key are never
touched, and a stored key the batch does not mention is kept. Keys are written in slices of
`PRICE_UPSERT_CHUNK_SIZE` (1,000), each one flushed: a sync commits every slice (`commit=True`,
the default of `_upsert_asset_events()`), while the manual upsert (`commit=False`) leaves the
commit to `bulk_upsert_events()`, which commits once for the whole request.

The upsert used to DELETE the stored rows of each key and INSERT the new ones. But
`transactions.asset_event_id` is `ON DELETE RESTRICT`, so that failed as soon as a transaction
realised the event: a provider refresh of such an event reported *Event upsert failed*, and editing
a linked manual event answered HTTP 500. A row updated in place keeps its id, so the transactions
linked to it stay linked.

### 🤖 Auto-Generated Events (`provider_assignment_id IS NOT NULL`)

A sync passes the assignment's id. This ensures:

- An event the provider returns again updates the stored one of the same date and type, which keeps its id: a transaction linked to it stays linked
- Events from **different** providers for the same asset are independent, and manual events are never touched
- A stored event the provider no longer returns is kept: the upsert only touches the date and type pairs of its batch

A parametric provider (Scheduled Investment) derives its whole series from its parameters. When they
change, or when the asset leaves it for another provider, `provider_management.py` deletes the
asset's prices and that assignment's events, first unlinking the transactions that pointed to them
(`asset_event_id = NULL`); manual events stay.

The data editor shows these events read-only: the events of `POST /assets/prices/query` carry
`is_auto` (`provider_assignment_id IS NOT NULL`). An edit would be overwritten by the next sync.
The editor can still delete one, through `delete_ids` like a manual event (below), but the
deletion lasts only until the provider returns the event again.

### ✋ Manual Events (`provider_assignment_id IS NULL`)

`POST /api/v1/assets/events` (`bulk_upsert_events()`) takes a list of `FAEventUpsert` items,
`{asset_id, mode, events, delete_ids}`, whose points are `FAEventUpsertPoint`: an
`FAAssetEventPoint` with an optional `id` (`schemas/assets/events.py`).

The request is **all or nothing** (decision 22 of release 1.3). Its items run in order in one
transaction: `_write_manual_item()` checks an item, then writes and flushes it, so a later item
sees what the earlier ones wrote, and a single commit closes the request. Any refusal rolls the
whole request back, the items before it included: nothing of it is stored.

An item's `mode` (decision 20) is `"upsert"` by default; the data editor and its CSV import send
none:

- An event **with `id`** edits that manual row in place, every field included (`date`, `type`,
  value and currency, `notes`), and the row keeps its id. The data editor sends the id of every
  saved row, so changing the Type of a saved event no longer adds a second event.
- Events **without `id`** go through `_write_asset_events(provider_assignment_id=None)`: matched
  on `(date, type)` among the manual rows and updated in place, so a manual event still replaces
  the manual event of the same date and type, keeping its id.

With `mode: "create"`, an item only adds events, and none of them may carry an `id`. An event on a
`(date, type)` the asset already has, manual **or** from a provider, is refused with
`EVENT_EXISTS` (`_reject_existing_events()`): a new event never overwrites another one. The
transaction form's **+ New event** (`EventCreateMiniModal`) sends this mode. On `EVENT_EXISTS` it
shows `params.existing` (`EventExistsPanel`): **Use this** links the stored event and writes
nothing; **Edit this**, for a manual event only, loads it into the form, which then saves it by
`id` in an `upsert` item.

`delete_ids` (`upsert` items only) lists events of the item's asset to delete, manual or from a
provider: a provider's event comes back at the provider's next sync.
`_delete_item_events()` runs first in `_write_manual_item()`, right after the asset lookup and
before every other check, and flushes: an edit of the item may then take the `(date, type)` of an
event the item deletes. Every id must be an event of the item's asset (`EVENT_NOT_DELETABLE`), and
none may be linked to a transaction (`EVENT_IN_USE`). An item may only delete, with no `events`.
The data editor saves its Events tab this way, in one request: the rows marked deleted in
`delete_ids`, the edited and new rows in `events`.

In both modes, an event in a currency other than the asset's is refused
(`EVENT_CURRENCY_MISMATCH`), and so is a value with more than 12 digits before the decimal
point, 6 decimal places or 15 significant digits, or one that is not finite, which is never
rounded (`EVENT_TOO_MANY_DIGITS`, C-97; the digits before the point since W-B58). So is a
`SPLIT` whose ratio, its value, is not a number above 0 (`EVENT_INVALID_SPLIT_RATIO`, X-R47),
however it is written: added, matched on its date and type, or edited by `id`, including an edit
that turns another type into a `SPLIT`. Until X-R47 such a split was stored, and as soon as a
transaction linked it the portfolio engine raised (`financial_math/portfolio/engine.py`): the
Dashboard report answered 500. Since lot MF-D4 a split stored that way counts as missing. Only
its ratio is dropped: the linked `ADJUSTMENT` rows stay the split's rescale, with their cost
kept. No trade price before the split is restated by that ratio, the FIFO lots skip it, and the
Dashboard names the asset in an `INVALID_SPLIT_RATIO` warning (see
[DataQualityBanner](../../frontend/data-quality-banner.md)). The user fixes the ratio here.

Each result carries `event_ids`: the id of the event each point of
the item wrote, in request order. An edit keeps its id, an event matched on its date and type gets
the id of the row it updated, and an added event the id of its new row. `deleted_ids` lists the
ids of `delete_ids`, all deleted, in request order; `success_count` also counts an item that only
deletes.

A provider's event never meets these refusals: `_upsert_asset_events()`, which a sync calls,
first drops every event whose value `asset_events.value` cannot hold — not finite, or past 12
digits before the decimal point (`_storable_events()`, `integer_digits_issue()`) — and, among the
others, every `SPLIT` whose ratio is not above 0 (`is_valid_split_ratio()`, X-R47), then writes
the rest (W-B58: a value past a double's range, stored as a REAL inf, broke every response of
the asset's events, for every user). A raw event the event schema itself refuses — a value that
is no number, or whose exponent is past ±100 (`check_decimal_exponent()`, R13-SEC7-3) — is
dropped the same way, one event at a time: parsed in one go, it made the sync lose every event
it fetched. A dropped event is only logged, as a warning: the sync
result does not report it, and its `events_fetched` still counts it. A call logs at most one
warning per reason, *Events skipped: no event value can keep them* for the values and *Splits
skipped: a split's ratio must be a number above 0* for the splits, each with `asset_id`, `count`
and the first five dropped (`events`); an event the schema refused is listed by its date and
type only, as *(refused by the schema)*, never with its value, which can be of any length.

Every refusal below stops the whole request:

| Refused | Answer |
|---|---|
| A `type` that, trimmed and upper-cased, is not one of the five [event types](#event-types) | HTTP 422, from `FAAssetEventPoint.normalize_type()` |
| The same `id` twice in one item | HTTP 422 *Duplicate event id in one upsert item*, from the `FAEventUpsert` validator |
| An `id` in a `create` item | HTTP 422 *A create item cannot name an event id*, from the `FAEventUpsert` validator |
| `delete_ids` in a `create` item | HTTP 422 *A create item cannot delete events*, from the `FAEventUpsert` validator |
| The same id twice in `delete_ids` | HTTP 422 *Duplicate id in delete_ids*, from the `FAEventUpsert` validator |
| An id both in `delete_ids` and on an event of the same item | HTTP 422 *An event cannot be deleted and edited in one item*, from the `FAEventUpsert` validator |
| An item with neither `events` nor `delete_ids` | HTTP 422 *An upsert item needs at least one event or one id to delete*, from the `FAEventUpsert` validator |
| An item whose asset does not exist | HTTP 400 `EVENT_ASSET_NOT_FOUND` (until 1.3, a 200 whose result had `count` 0) |
| An id of `delete_ids` that is not an event of the item's asset: unknown, already gone, or another asset's | HTTP 400 `EVENT_NOT_DELETABLE`; `params.ids`: those ids |
| An id of `delete_ids` whose event a transaction is linked to | HTTP 409 `EVENT_IN_USE`; `params.events`: one `{id, date, type, linked_transactions}` per such event, ordered by date, type and id. Counts only, no transaction id: the transactions may belong to other users |
| An event in a currency other than the asset's | HTTP 400 `EVENT_CURRENCY_MISMATCH`; `params`: `expected` (the asset's currency) and `events`, one `{event_index, date, type, currency}` per such event of the item |
| An event whose value has more than 12 digits before the decimal point, more than 6 decimal places or more than 15 significant digits, trailing zeros not counted, or is not finite (`_reject_too_many_digits()`, the limits of `asset_events.value`) | HTTP 400 `EVENT_TOO_MANY_DIGITS`; `params`: `max_integer_digits` (12), `max_decimal_places` (6), `max_significant_digits` (15) and `events`, one `{event_index, date, type}` per such event of the item |
| A `SPLIT` whose ratio, its value, is not a number above 0: new, matched on its date and type, or edited by `id`, another type the edit turns into a `SPLIT` included (`_reject_invalid_split_ratios()`; the rule is `is_valid_split_ratio()` of `financial_math/splits.py`, the portfolio engine's own) | HTTP 400 `EVENT_INVALID_SPLIT_RATIO`; `params.events`: one `{event_index, date, type, ratio}` per such split of the item, in request order, `type` always `SPLIT` and `ratio` the value sent, as a string. A value that is not finite or has too many digits is refused first, with `EVENT_TOO_MANY_DIGITS` |
| An `id` that is unknown, belongs to another asset, or names a provider event | HTTP 400 `EVENT_NOT_EDITABLE`; `params.ids`: those ids |
| An edit that changes its date or type (a *mover*) landing on a key another edit of the item ends on, or on a key held by a manual row the item does not edit | HTTP 400 `EVENT_KEY_CONFLICT`; `params`: the `date` and `type` of the key |
| An event without `id` on a key an edit of the item ends on | HTTP 400 `EVENT_KEY_CONFLICT`; `params`: `date` and `type` |
| In a `create` item, an event on a `(date, type)` the asset already has, manual or from a provider | HTTP 409 `EVENT_EXISTS`; `params.existing`: the stored events on every such key of the item, ordered by date, type and id, each `{id, date, type, value: {code, amount}, notes, is_auto, linked_transactions}`, the last one the number of transactions linked to the event |

A 400 or a 409 answers `detail = {error_code, message, params}` (`_REFUSAL_STATUS` in
`api/v1/assets/events.py`): `message` is the English text, which starts with the code, and
`params` always holds `item_index` (the item's position in the request, from 0) and `asset_id`,
plus the fields above. Any other `AssetSourceError` stays a 500 with a string `detail`. A 422 is
FastAPI's validation error: nothing has run, and its `loc` points at the item, or at the event for
a type. `_split_manual_events()` also raises `EVENT_KEY_CONFLICT`, with `params.ids`, for an id
repeated in one item: over HTTP the 422 comes first, so only a caller that skips the schema meets
it.

Allowed: two edits swapping their keys, edits that keep a shared key (legacy duplicates stay
editable), an event without `id` on a key a mover vacates, and an edit landing on the key of an
event the item deletes: that deletion is flushed before the checks run. These checks only cover
keys an edit ends on: in an `upsert` item, an event without `id` on the key of a manual row the
item does not edit updates that row, and two events without `id` on one key are both stored.

A type change is allowed even when a transaction is linked to the event: the link stays, and the
transaction is then read according to the new type. `compute_wac_iterative()`
(`portfolio_service.py`) counts an `ADJUSTMENT` as split-linked only while its event is a `SPLIT`:
the type is joined live, and the split-linked set is part of the WAC cache fingerprint. Once the
event is retyped to `PRICE_ADJUSTMENT`, a +qty adjustment becomes an acquisition of unknown cost
(the pool cost turns incomplete, the numbers shown do not change) and a −qty one a plain reduction
that takes its share of the cost away (in the test, the total cost halves from 1,500 to 750). Both
cases are pinned by the `test_*_split_relabelled_as_price_adjustment_*` tests in
`test_scripts/test_api/test_portfolio_wac.py`.

Manual events are **never deleted** by the sync process. They survive provider re-syncs, provider
changes, and bulk refreshes. Only an explicit user deletion removes them, or the market-data wipe
of a currency change (`POST /api/v1/assets/{asset_id}/market-data/wipe`), which deletes every event
of the asset. A user deletes events in two ways:

- **`delete_ids` of `POST /api/v1/assets/events`**, the data editor's save: all or nothing, so an
  event a transaction uses stops the whole request (`EVENT_IN_USE`). Until 1.3 the editor sent the
  deletions apart, through the `DELETE` below, after the upsert: the rest of the save was stored,
  the used event was skipped with a warning, and an edit could not take the key of an event deleted
  in the same save.
- **`DELETE /api/v1/assets/events?asset_id=…&ids=…`**, which the frontend no longer calls: per id,
  `deleted`, `not_found` or `in_use` (an event a transaction uses is reported, not deleted), and
  the deletable ones are committed even when others are blocked.

Both are scoped to one asset (decision 21 of release 1.3). The `DELETE` requires `asset_id`, so a
request with `ids` alone, the form API clients sent before, is now a 422, and an id of another
asset answers `not_found` and leaves its event alone; in `delete_ids`, such an id is
`EVENT_NOT_DELETABLE`.

---

## 🔧 Auto-Generated Events

### 📈 Yahoo Finance: Dividends & Splits

During sync, the Yahoo Finance provider generates:

- **`DIVIDEND` events** from `ticker.dividends` — ex-dividend dates with the per-share payout value and currency.
- **`SPLIT` events** from `ticker.splits` — split dates with the split ratio as the event value (e.g., `4.0` for a 4:1 split).

Both are written by the standard `_upsert_asset_events()` pipeline, scoped by `provider_assignment_id`.

### 🔍 JustETF: Dividends from Chart Data

During sync, the JustETF provider parses dividend data from `load_chart()` response. Distribution dates and amounts are extracted and stored as **`DIVIDEND` events**.

### 📊 Scheduled Investment: `generate_interest`

When a schedule period has `generate_interest = True`, the Scheduled Investment provider auto-generates:

1. **`INTEREST` events** at each maturation date within the period
2. After each INTEREST event, accrued interest resets: `total_interest = 0`, `event_adjustment = 0` → value returns to `initial_value`

The maturation frequency is controlled by `maturation_frequency` on each interest rate period (DAILY, WEEKLY, MONTHLY, QUARTERLY, SEMIANNUAL, ANNUAL).

The events entered in the schedule itself (`asset_events` in the provider parameters, **Add Event**
in the asset form) travel the same way: `get_history_value()` returns them with the generated ones,
so the sync stores them under the assignment and the data editor shows them read-only.

### 🏁 `MATURITY_SETTLEMENT`

Auto-generated when:

- The schedule ends **and** `generate_interest = True` on the last period
- **Or** late interest is configured with `generate_interest = True`

After settlement, the engine is "off" — `get_current_value()` returns the settlement value for all future dates.

---

## 📐 Event Impact on Pricing

The Scheduled Investment engine's pricing formula incorporates events:

```
price(d) = initial_value + accrued_interest - Σ(INTEREST events) + Σ(PRICE_ADJUSTMENT events)
```

- Interest is always calculated on `initial_value` (not running value)
- INTEREST events **subtract** from the running price (coupon paid out)
- PRICE_ADJUSTMENT events are **algebraic** (can add or subtract)
- After `MATURITY_SETTLEMENT`, no further calculations occur

---

## 🔗 Related Documentation

- 📊 [Assets & Pricing ER Diagram](../../architecture/database/assets_pricing.md) — Database schema
- 💰 [Asset Architecture](architecture.md) — Sync pipeline and price queries
- 📅 [Scheduled Investment Provider](provider_scheduled_investment.md) — Interest schedule and auto-events
- 📐 [Day Count Conventions](../../../financial-theory/fundamentals/day-count.md) — ACT/365, ACT/360, 30/360
