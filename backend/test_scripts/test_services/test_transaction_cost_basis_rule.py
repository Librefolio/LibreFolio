"""
N2 — which rows need a cost basis, and when a batch holds them to it (workstream W, release 1.3).

The rule. A TRANSFER's receiving leg (quantity > 0) and an ADJUSTMENT adding quantity need a cost basis: a
``cost_basis_override``, or ``cost_basis_mode`` ``auto``/``auto-detail`` (the batch then writes the average itself).
``TX_TYPE_METADATA`` says so — TRANSFER ``cost_basis_pair = ["forbidden", "required_qty_pos"]``, ADJUSTMENT
``cost_basis_mode = "required_qty_pos"`` — and every batch path enforces it in ``validate_cost_basis``
(``batch_costs.py``): the issue ``costBasisRequired`` on ``cost_basis_override``, and the batch does not commit.

What N2 changes:

1. The rule is READ from ``TX_TYPE_METADATA`` — pair types ``cost_basis_pair[1 if quantity > 0 else 0]``, the
   others ``cost_basis_mode``; ``required_qty_pos`` with quantity > 0 means required — instead of being written by
   hand in ``TransactionValidationMixin._requires_cost_basis`` (``validation.py``).
2. An update is held to the rule only when it changes, compared with the stored row, the type, the quantity (its
   sign included), the cost (``cost_basis_override``, its currency, ``cost_basis_mode``) or the asset event link
   (``asset_event_id``: an ADJUSTMENT linked to a SPLIT takes its cost from the split's ratio, so the link stands
   for its cost). The comparison is on values, not on which keys the payload carries, so the app's diff payloads
   and a client sending the whole row are judged alike. Editing the notes (``description``, "Transaction notes") or
   the tags of a row an older version stored without a cost stays possible, and the row stays as it was: no repair.

Reds — fail before N2, pass after it:

- ``TestEditsOfARowStoredWithoutCost``: a notes-only or tags-only edit of a TRANSFER receiving leg (sent with its
  giving leg) or of an ADJUSTMENT +qty stored without a cost commits; today ``_check_update_cost_basis`` refuses any
  update of such a row. Plus a date-only edit, DERIVED from the same decision (a date is none of the changes the
  rule reads): it is what tells a cure that lists the changes that matter from one that lists the edits that are
  harmless.
- ``TestTheRuleReadsTheMetadata``: with an entry of ``TX_TYPE_METADATA`` patched in place, ``_requires_cost_basis``
  and a create follow the patch; today the hand-written rule ignores it.
- ``TestSplitLinkedAdjustment``: an update that only unlinks an ADJUSTMENT +qty linked to a SPLIT (stored without a
  cost by design), or re-links it to a PRICE_ADJUSTMENT, is refused. Not red before N2, which refused every update
  of that row, but red with the first N2 cure, whose ``cost_fields`` left the link out.

Guards — green before N2, and the cure must keep them green:

- ``TestCreatesNeedACost``: a create without a cost is refused, on its own row (index, field, params);
- ``TestUpdatesThatChangeWhatTheRuleReads``: a quantity change (a sign flip −5 → +5, or more units on a stored row
  without a cost), a type change into ADJUSTMENT, or ``cost_basis_mode: "manual"`` with no cost, is refused;
- ``TestEditsOfARowWithCost``: a notes-only or tags-only edit of a row that has its cost commits, cost untouched;
- ``TestAutoCost``: an Auto create with an average available commits, with that average written;
- ``TestPromoteOfARowStoredWithoutCost``: a promote that makes a stored ADJUSTMENT +5 without a cost the receiving
  leg of a TRANSFER stays refused when the same batch also edits that row's notes — today the update check refuses
  it, and ``_check_promoted_saved_cost_basis`` skips updated rows on the strength of that check;
- ``TestSplitLinkedAdjustment``: a notes-only or tags-only edit of the split-linked ADJUSTMENT commits, link and
  missing cost untouched; the same link changes made WITH a cost commit;
- ``TestTheRuleAgreesWithTheMetadata``: for every type and quantity sign, ``_requires_cost_basis`` says what the
  metadata says.

Not covered, on purpose:

- an update that REMOVES a cost, in N2: ``cost_basis_override: null`` is read as "unchanged" (``_apply_update_values``,
  ``batch_edits.py``), exactly like an absent key, until decision P5's cure makes it a removal where the type and side
  take a cost — ``TestDecisionP5AnExplicitNullEmptiesTheCost``, below;
- Auto with no average (P-1, ``auto_cost.py``) and SPLIT-linked ADJUSTMENTs: outside N2, unchanged.

Decision 47 as N78-1 changed it (the developer's decision, 21/10/2026) — the giving leg of a TRANSFER,
``TestDecision47TheGivingLegOfATransfer``, RED until the N78-1 cure but for the promote. An ADJUSTMENT with a negative
quantity has no value: the engines ignore any cost it stores, and the API refuses one (``costBasisNotAllowed``). So
where a batch takes a TRANSFER's giving leg out of its pair, the leg leaves WITHOUT a value:

- a split of a TRANSFER pair makes its giving leg an ADJUSTMENT −4 without ``cost_basis_override`` nor
  ``cost_basis_currency`` — whatever its broker's pool holds, a purchase of the same batch included —, the receiving
  leg keeping its own cost. Before N78-1 the leg left at its OWN broker's Auto cost (``_handover_cost``: 100 EUR, or 200
  with the purchase), computed in the batch's WAC stage;
- an update of the same batch that gives the giving leg a cost is refused with ``costBasisNotAllowed`` (before N78-1:
  the coordinator's decision 4, 16/10, kept it);
- a split whose giving leg's broker paid in a currency no rate converts commits all the same: no cost is computed, so
  no conversion is missing (before N78-1: ``WAC_FX_UNAVAILABLE`` on the split's index, refused);
- a promote of an ADJUSTMENT −4 carrying a cost (as an old row may hold it) and an ADJUSTMENT +4 into a TRANSFER takes
  the cost (and its currency) off the side whose new type takes none (``cost_basis_allowed``: the giving side); the
  receiving side keeps its own. Unchanged by N78-1.

Why here: these are rules about where a batch writes or removes a cost basis — this file's subject, its ``World``
(``source`` holding 10 units at 100 EUR, the Auto cost), its stored pair (``_store``) and its vocabulary. The broker
deletion's side of decision 47 is pinned in ``test_broker_service.py`` (BR-U-073, 076, 078, 086–088), the lone legs a
1.2 deletion left in ``test_lone_transfer_legs.py``.

W-B69 (release 1.3; it blocks the release) — an Auto cost computed while skipping an unreadable row, the ``TestWB69…``
classes: W's half of it, RED until its cure but for the guards. A regression of W-B58: ``RealDecimal``
(``db/real_decimal.py``) reads a stored value that is no number — a text such as 'n/a', a REAL ±inf — as None instead of
raising. ``compute_wac_iterative`` (``portfolio_service.py``) still selects such a row — in SQLite 'n/a' is not NULL and
differs from 0 —, and ``cost_movement_from_transaction`` (``financial_math/average_cost.py``) skips it when its quantity
reads None, or takes a BUY whose amount reads None as a free acquisition: the Auto cost is computed without the row, or
lower, and saved for good. The cure (approved design): ``_auto_cost`` (``auto_cost.py``) raises
``UnreadablePoolError(count)`` when a row of its pool — the facade's filters, minus the rows left out — reads None in its
quantity, its amount, or a cost basis it stores (``cost_basis_override`` not NULL in SQL: the contract's addition of
17/10; a BUY's NULL cost basis is legitimate), ``count`` the number of such rows — a row unreadable in two columns counts
once —; and each caller refuses. That core — the guard in ``_auto_cost``, ``UnreadablePoolError``, the broker deletion
(``delete_by_broker``) and the lone legs — is the MF workstream's (the coordinator's assignment, 17/10), pinned in MF's own
``test_auto_cost_unreadable_pool.py``. W's half, the batch's, is pinned here:

- a batch's Auto row (a create or an update in ``auto`` or ``auto-detail``), on /commit and on /validate: one issue
  ``autoCostUnreadable`` on its operation and index, ``field`` ``cost_basis_override``, ``params`` ``{"count": N}``, and no
  transaction id anywhere in it (the pool may be another user's broker); nothing committed, nothing saved, nothing raised;
- the split of a TRANSFER pair whose giving leg's broker pool holds such a row: since N78-1 the split computes no cost
  for the giving leg, so no ``autoCostUnreadable`` on it — only W-B74's ``ledgerUnreadable``, the split replaying that
  broker (before N78-1: one ``autoCostUnreadable`` on the split's index, ``ref_id`` the giving leg);
- ``TXValidationCode.AUTO_COST_UNREADABLE`` exists and ``GET /transactions/types`` lists it; a gate, green today, holds
  every code to its ``transactions.errors.<code>`` message in EN, IT, FR and ES.

The pool is ``source``'s: the ``world``'s BUY (10 units for 1 000 EUR) and the row ``_plant`` adds a week later — a BUY of
10 units for 3 000 EUR, or an incoming row that takes a cost basis, an ADJUSTMENT +10 or a receiving TRANSFER +10 (its
giving leg on a third broker of the test's), stored at 300 EUR a unit —, its quantity, its amount or its cost basis then
overwritten with 'n/a' by raw SQL. Readable, either averages (1 000 + 3 000) / 20 = 200 EUR; today, with the quantity
unreadable the average is 1 000 / 10 = 100, with the BUY's amount or the stored cost basis unreadable 1 000 / 20 = 50 (a
free acquisition, or one of unknown cost entering at zero). The planted row lies before the move, so today a batch's
balance replay reads it among the balances before its first day, which skip a None, and never in its day-by-day loop,
where a None raises (an uncoded "Balance validation error").

W-B74 (approved design, its cure pending; its own reds in test_transaction_service.py) makes the replay refuse a broker
whose rows hold a quantity or an amount that reads None, at every date: ``ledgerUnreadable`` ``{"brokerId": id, "count":
N}`` at index -1. So a W-B69 batch that replays ``source`` while it holds such a row — creating or updating the pair,
splitting it — gets that issue beside ``autoCostUnreadable``: exactly two, contract updates RED until W-B74's cure. A
stored cost basis is read by no balance: those reds keep exactly one issue. The guards that recompute the receiving leg
alone replay ``dest`` only, and refuse nothing; the row of another asset on ``source``, under a batch that creates the
pair, is refused by the replay alone (``test_unreadable_row_of_another_asset_is_refused_by_the_replay_alone``).

N78 (W-B72; the night decision N78, refined by the coordinator's (a) of 17/10) — a cost basis on a type and side that
take none, the ``TestN78…`` classes: RED until its cure but for the guards. ``cost_basis_allowed`` (``TX_TYPE_METADATA``)
lets a cost basis in only on a TRANSFER or an ADJUSTMENT with a quantity above 0; rule 12 of
``validate_transaction_business_rules`` reads only ``cost_basis_mode``, so a ``cost_basis_override`` sent without a mode is
stored on any type, by a create (``batch_creates.apply_creates``) or an update (``batch_edits._apply_update_values``). Only
an API client sends one: the form gates on ``cbAllowed``, the BRIM plugins set one only on an incoming ADJUSTMENT. The
contract:

- rule 12b, ``validate_transaction_business_rules(..., cost_basis_set=False)``: a request that SETS a non-null
  ``cost_basis_override`` without a ``cost_basis_mode`` where ``cost_basis_allowed`` refuses one gets
  ``costBasisNotAllowed`` ``{"type": <type>, "qty": str(quantity)}`` — EXCEPT on an ADJUSTMENT with a quantity below 0,
  whose stored cost is decision 47's handover cost, which decision 4 lets an update of the same batch set. With a mode,
  rule 12's ``costBasisModeIncompatible`` speaks alone, no double issue;
- a create is refused at the batch's parse: its issue on ``operation`` "create" and its index, ``params`` ``{type, qty}``,
  and no result; an update that sets one on a stored row whose final type and side take none, on its index and
  ``ref_id`` (``_validate_updated_final_state``). The promote's side is ``test_transaction_decimal_places.py``'s;
- a LONE business-rule error keeps its params (the coordinator's approval, 17/10): ``_parse_lenient`` keeps the context of
  a lone model-level error (``loc`` empty, plain values) as ``params``, as it already does for the errors
  ``multipleBusinessRuleErrors`` packs; a field-level pydantic error and a ``value_error`` keep None. Today a lone one
  gets None, so every refusal of a create here, rule 12's or rule 12b's, pins its params: ``{type, qty}``, the quantity
  compared as a number. The contract's own tests are ``test_transaction_service.py``'s (``TestParseLenientParams…``);
- rows already stored with a stray cost basis are kept: an update that does not set the cost basis passes, and an
  explicit null (clearing) is never refused — what it does to the cost is decision P5's;
- ``transactions.errors.costBasisNotAllowed`` and ``transactions.errors.costBasisModeIncompatible`` — today the only
  business-rule code without a message — in EN, IT, FR and ES; and a gate holds every business-rule code of
  ``schemas/transactions/transactions.py`` (its ``PydanticCustomError`` literals but the wrapper
  ``multipleBusinessRuleErrors``) to its message in the four languages.

Reds: a BUY +5 and the USD leg of an FX_CONVERSION pair created with a cost basis and no mode (today committed with it
stored); an update setting one on a stored BUY +3 (today committed); a cost basis sent WITH a mode on a BUY, whose lone
``costBasisModeIncompatible`` must carry ``{type: BUY, qty: 5}`` (today params None: RED until the lone-params cure, the
rest of it a guard); the two messages and the gate. Guards: an ADJUSTMENT +5 with a manual cost basis, a received
TRANSFER with one, an Auto row sending the form's currency hint commit; the giving side of an ADJUSTMENT — one created at
−5 with a cost basis and no mode, an update setting one on a stored ADJUSTMENT −4 — commits and holds it (the exception);
a notes-only edit of a BUY or an ADJUSTMENT −4 stored with a stray cost basis commits and keeps it; a create sending an
explicit null commits.

The conflict this file first flagged — decision 4's guard ``test_split_keeps_the_cost_an_update_of_the_same_batch_gives_the_giving_leg``
gives the giving leg a split leaves, an ADJUSTMENT −4, a cost of its own through an update without a mode, which the first
N78 refused — is resolved by the coordinator's (a), 17/10: decisions 4 and 47 are the developer's and win, so rule 12b
leaves an ADJUSTMENT below 0 alone, and that guard stays as it is.

W-B67 (release 1.3) — an Auto cost written on the wrong row of a batch, the ``TestWB67…`` classes: RED until its cure but
for the guards. ``_compute_wac_for_auto_items`` (``auto_cost.py``) finds the row of an Auto create (``cost_basis_mode``
``auto``/``auto-detail``) through ``_find_created_tx_for_wac``: by its ``link_uuid`` and index when it has one — a TRANSFER
pair's legs are found —, otherwise as the NEWEST row with the same broker, asset, date and type. Two creates on that key are
one row to it: the Auto cost lands on the later one, a Manual row's cost overwritten with an average; the Auto row commits
without one — the batch's cost check skips Auto creates (``batch_costs.py``) — and enters every later pool as an
acquisition of unknown cost, at zero (``ADD_UNKNOWN_COST``, ``financial_math/average_cost.py``); and ``wac_results``
answers on the Auto row's index the value computed for the other row.

The contract, night decision N84 (D-W67-1 = P1, 17/10): each Auto row gets the cost that saving the rows one at a time in
date order gives it. (a) Each create costs its own row; (b) the batch's Auto rows are costed in the order of their pool
date — the ``as_of`` of ``_auto_cost_source``: the row's date, its partner's for a receiving TRANSFER leg —, then by
index; (c) the Auto rows not yet costed, but the split-linked ones, stay out of each other's pools. Each ``wac_results``
item, on its own index, carries the cost its row stores, and ``wac_results`` keeps its order: the creates by index, then
the updates.

Reds — on ``source`` and the ``world``'s 10 units at 100 EUR; each batch is valid and commits, as ``POST
/transactions/commit`` runs it, and its rows are read back by id; an average is the quotient rounded as
``compute_wac_iterative`` rounds it (``round_computed_value``):

- an ADJUSTMENT +5 in ``auto`` (create 0), then one at a manual 50 EUR, no mode (create 1), on one key: the Manual row keeps
  50, the Auto row holds (1 000 + 5 × 50) / 15, and ``wac_results`` is that one item, on index 0. Today the Manual row
  holds 1 000 / 15, the Auto row none, and index 0 answers 1 000 / 15;
- two ADJUSTMENTs +5 in ``auto`` on one key: both hold 100 — the first costed without the second, (c), the second with the
  first at 100 — and index 0 and index 1 answer 100. Today the first holds none, the second 1 000 / 15, costed twice;
- an ADJUSTMENT +10 in ``auto`` linked to a 2:1 SPLIT of the asset (create 0) and a plain one +5 in ``auto`` (create 1), on
  one key: the split row holds no cost and index 0 answers none; the plain row holds the post-split 1 000 / 20 = 50,
  answered on index 1. Today index 0 answers the plain row's 50;
- Auto rows sent against date order, a purchase between them: an ADJUSTMENT +5 on D+2 (create 0), one on D (create 1), a
  BUY +5 on D+1 paying 2 000 EUR (create 2): the D row holds 100, the D+2 row (1 000 + 5 × 100 + 2 000) / 20 = 175, the D
  row in its pool at its own cost, (b); ``wac_results`` answers each on its index, in index order. Today the D+2 row holds
  150, the D row in its pool at zero; 200 would be (c) without (b).

Guards, green today and after the cure, where today's search finds the row: a lone ADJUSTMENT +5 in ``auto`` holds 100,
answered on index 0; a Manual row (create 0, 50 EUR) then an Auto one (create 1) on one key — the Auto row is the newest —
hold 50 and (1 000 + 250) / 15; and (c)'s exception: the Auto receiving leg of a TRANSFER pair source → dest (create 1),
costed before the ADJUSTMENT +10 in ``auto`` that realizes a 2:1 SPLIT on ``source`` the same day (create 2), holds the
post-split 50 EUR, the split row still to be costed staying in its pool. The third red costs its split row first, so a cure
without the exception fails it only if it leaves out the Auto rows without a cost, not if it leaves out those still to be
handled; the guard costs the split row last, and such a cure fails it either way. A TRANSFER pair's Auto receiving leg,
which its ``link_uuid`` finds, is guarded already: ``TestAutoCost`` (100, stored) and
``TestWB69GuardsReadablePoolsAndRowsOutsideThePool::test_auto_row_over_a_readable_pool_takes_its_average`` (its
``wac_results`` item on index 1, and its stored cost).

N88 (J-57; the coordinator's night decision N88, 17/10, approved) — an Auto cost with nothing to average, the
``TestN88…`` class: RED until its cure but for the controls. The pool of an Auto row (``_auto_cost_source``: an ADJUSTMENT
its own broker up to its date without itself, a receiving TRANSFER leg its partner's broker up to the partner's date)
that holds no units on its date — the broker never held the asset, or sold it all before — averages to 0 in
``compute_wac_iterative``, not to None; ``_write_auto_cost`` writes that 0, a ``Currency`` of 0 being truthy, and the
batch's cost check skips Auto rows (``batch_costs.py``): the row is saved as a free acquisition, in silence. A pool whose
units all entered at an unknown cost — an acquisition without a cost basis enters at zero, ``ADD_UNKNOWN_COST``, the
pool's cost incomplete (``report_complete`` False) — averages to the same silent 0. The contract: the batch refuses such a
row, ``autoCostEmptyPool`` when its pool holds no units on its date, ``autoCostUnknownPool`` when it holds units but none
at a known cost (the average 0, the pool's cost incomplete); an issue on the row's operation and index, ``field``
``cost_basis_override``, no params, ``ref_id`` None, as W-B69's ``autoCostUnreadable``; the refused row gets no
``wac_results`` item, and nothing is committed. A pool of free units — held, every one at a known cost of 0
(``ADD_ZERO_COST``) — keeps its average of 0, written; a Manual cost of 0 stays accepted. A pool only PART of whose units
have an unknown cost averages the known cost over all of them, understated and not refused: that is J-58, the developer's
to decide, pinned at today's value by a control.

Reds, each an ADJUSTMENT in ``auto`` on ``MOVE_DAY``: +5 on ``dest``, which never held the asset (on /commit and /validate,
in ``auto`` and ``auto-detail``); +5 on ``source`` after a SELL of the ``world``'s 10 units; +5 and +3 on ``dest`` in one
batch — N84 keeps the first, refused, out of the second's pool, so both are refused (a cure that wrote the first at 0 would
hand the second 5 free units, one that let it in without a cost 5 units of unknown cost); an update switching a stored
ADJUSTMENT +5 at 42 EUR on ``dest`` to Auto, which must keep its 42; and +3 on ``dest`` over an ADJUSTMENT +5 planted
without a cost basis (``autoCostUnknownPool``). Today each is saved, or answered, at 0. Controls: over the ``world``'s BUY,
100 EUR; over 10 units planted at a cost of 0, 0 EUR, written; a Manual 0 on ``dest``, committed; over the BUY's 10 units
for 1 000 EUR beside 10 planted without a cost, 1 000 / 20 = 50 EUR (J-58). The API side — the receiving leg of a TRANSFER
from an empty pool, at /validate — is ``test_wac_inline.py``'s ``test_wacp27_empty_pool_is_refused``.

J-60 (the coordinator's decision of 19/10, the developer's texts approved; N92 (i) refuses negative prices too) — a manual
cost basis below 0, the ``TestJ60…`` classes: RED until its cure but for the guards. Nothing reads the sign of a cost basis
today: −1 EUR written by a create, an update or a promote is saved, and the lots take it as a negative cost. The contract: a
stage ``check_cost_basis_sign``, beside ``check_decimal_limits`` and ``check_dates``, reads the costs the digit limits read
— a create's or an update's ``cost_basis_override`` sent without ``cost_basis_mode`` ``auto``/``auto-detail``, and the
one a promote resolves — and below 0 gives the row one ``costBasisNegative`` (``TXValidationCode.COST_BASIS_NEGATIVE``,
message ``transactions.errors.costBasisNegative``) on ``cost_basis_override``, its operation and index, ``ref_id`` the row
of an update, no params: not committed, nothing written, and the batch runs on, so the row's other refusals come in the
same answer. Reds, at −1 EUR on /commit and /validate: an ADJUSTMENT +5, a TRANSFER's receiving leg, an ADJUSTMENT −5's
handover cost, an update, a promote, each beside nothing else; the same row beside a refusal found before the check and
one found by the last stage; the code, its listing, its message; DERIVED, on /commit, an update re-sending unchanged the
−1 a row stores. Guards: a Manual 0, ``-0`` included; an Auto row, whatever its payload carries or (DERIVED) its pool
averages; a notes-only or tags-only edit of a row stored at −1, which keeps it.

Ownership. Every test builds its own asset and brokers under a unique marker, in a session rolled back at the end:
``execute_batch`` never commits (its caller does), so nothing reaches the lane's database. The two scaffolds that
change module state — an entry of ``TX_TYPE_METADATA``, ``SWAP_GROUPS`` — go through ``monkeypatch``, which puts
them back. W-B69's plants are raw SQL in the same session, rolled back with it, and N88's are ORM rows flushed in it.

Run: ``./dev.py test services transaction-cost-basis-rule`` (the action ``services_transaction_cost_basis_rule``); W-B69's
cases alone: ``./dev.py test services transaction-cost-basis-rule WB69``; N78's: ``… transaction-cost-basis-rule N78``;
W-B67's: ``… transaction-cost-basis-rule WB67``; N88's: ``… transaction-cost-basis-rule N88``; J-60's: ``…
transaction-cost-basis-rule J60``.
"""

import ast
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Before any app module that reads DATABASE_URL: this lane's test database.
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import and_, bindparam, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

import backend.app.schemas.transactions.transactions as transaction_schemas
import backend.app.schemas.transactions.type_metadata as type_metadata
from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, Broker, FxConversionRoute, FxRate, Transaction, TransactionType
from backend.app.db.precision import decimal_limit_issue, integer_digits_issue, round_computed_value
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.batch import TXBatchResponse, TXValidationCode, TXValidationIssue
from backend.app.schemas.transactions.type_metadata import EVENT_TYPE_METADATA, TX_TYPE_METADATA, TXTypesResponse, cost_basis_allowed
from backend.app.services.portfolio_service import compute_wac_iterative
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import utcnow
from scripts.i18n_catalog import flatten, load_catalog

EUR = "EUR"
BUY_DAY = date(2025, 1, 6)
MOVE_DAY = date(2025, 2, 3)
BUY_QUANTITY = Decimal("10")
# The BUY pays 1 000 EUR for 10 units: 100 EUR is the source broker's average, the cost an Auto row receives.
UNIT_COST = Decimal("100")
TRANSFER_QUANTITY = Decimal("4")
ADJUSTMENT_QUANTITY = Decimal("5")
# A cost basis a row was saved with, distinct from the average so that "unchanged" cannot be confused with "recomputed".
STORED_COST = Currency(code=EUR, amount=Decimal("42"))
STORED_TAGS = "n2-stored"
EDITED_TAGS = ["n2-edited"]
COST_BASIS_REQUIRED = TXValidationCode.COST_BASIS_REQUIRED.value

SHAPES = ("transfer_in", "adjustment_in")
SHAPE_LABELS = {
    "transfer_in": "TRANSFER receiving leg (quantity > 0, edited together with its giving leg)",
    "adjustment_in": "ADJUSTMENT adding quantity",
}
EDITS = ("notes", "tags")

SPLIT_RATIO = Decimal("2")
# A 2:1 split doubles the 10 units the BUY gave the source broker: the ADJUSTMENT that realizes it adds 10 more.
SPLIT_QUANTITY = BUY_QUANTITY * (SPLIT_RATIO - 1)
LINK_CHANGES = ("unlink", "relink-price-adjustment")

# Decision 47 — the giving leg of a TRANSFER (TestDecision47TheGivingLegOfATransfer).
WAC_FX_UNAVAILABLE = TXValidationCode.WAC_FX_UNAVAILABLE.value
PYG = "PYG"  # a currency no rate and no route reaches, proven before use
# 10 units bought in PYG a week before the EUR BUY: the EUR BUY stays the last acquisition, so the average is in EUR
# and PYG/EUR is the conversion it misses.
PYG_DAY = BUY_DAY - timedelta(days=7)
PYG_PAID = Decimal("-50000")
# 10 more units at 300 EUR that a split's own batch buys before the move: with the BUY's 1 000 for 10, the pool of
# the giving leg averages (1 000 + 3 000) / 20 = 200 EUR.
LATER_BUY_DAY = BUY_DAY + timedelta(days=7)
LATER_BUY_PAID = Decimal("-3000")


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def engine():
    """The app's async engine, on this lane's test database."""
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    """One session per test, rolled back at the end: ``execute_batch`` never commits, its caller does."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@dataclass
class World:
    """One test's own data: an asset, the broker that holds it, the broker that receives it."""

    session: AsyncSession
    marker: str
    asset: Asset
    source: Broker
    dest: Broker


@pytest_asyncio.fixture
async def world(session) -> World:
    """An asset and two brokers of this test alone, and the BUY that gives ``source`` 10 units at 100 EUR.

    The BUY is what lets ``source`` give units away without going short — the balance replay of every batch re-reads
    those days — and what an Auto cost averages. Both brokers allow a cash overdraft (the BUY spends cash no DEPOSIT
    brought) and refuse shorting, as a broker does by default.
    """
    marker = f"N2-cost-rule {uuid.uuid4().hex}"
    now = utcnow()
    asset = Asset(display_name=f"{marker} asset", asset_type=AssetType.STOCK, currency=EUR, created_at=now, updated_at=now)
    source = Broker(name=f"{marker} source", description="N2 cost basis rule: the broker units leave", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    dest = Broker(name=f"{marker} dest", description="N2 cost basis rule: the broker units reach", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    session.add_all([asset, source, dest])
    await session.flush()
    session.add(
        Transaction(
            broker_id=source.id,
            asset_id=asset.id,
            type=TransactionType.BUY,
            date=BUY_DAY,
            quantity=BUY_QUANTITY,
            amount=-(BUY_QUANTITY * UNIT_COST),
            currency=EUR,
            description=f"{marker} buy",
            created_at=now,
            updated_at=now,
        )
    )
    await session.flush()
    return World(session=session, marker=marker, asset=asset, source=source, dest=dest)


# ============================================================================
# HELPERS
# ============================================================================


def _stored_row(
    world: World,
    *,
    broker: Broker,
    tx_type: TransactionType,
    quantity: Decimal,
    cost: Currency | None = None,
    amount: Decimal = Decimal("0"),
    currency: str | None = None,
) -> Transaction:
    """A row as the database holds it, written without the batch and its checks.

    Without ``cost`` it is the shape ``test_db/legacy_cost_rows.py`` writes for data an older version left behind:
    amount 0, no currency, no cost basis, no asset event. Every row of a test carries the same description and tags,
    as both legs of a pair must.
    """
    now = utcnow()
    return Transaction(
        broker_id=broker.id,
        asset_id=world.asset.id,
        type=tx_type,
        date=MOVE_DAY,
        quantity=quantity,
        amount=amount,
        currency=currency,
        cost_basis_override=cost.amount if cost is not None else None,
        cost_basis_currency=cost.code if cost is not None else None,
        asset_event_id=None,
        description=f"{world.marker} stored",
        tags=STORED_TAGS,
        created_at=now,
        updated_at=now,
    )


@dataclass
class Stored:
    """A stored row that needs a cost basis, and the rows an edit of it sends.

    The receiving leg of a TRANSFER goes with its giving leg — a pair keeps one description and one set of tags, so
    the app edits both — and an ADJUSTMENT goes alone. ``subject_index`` is the subject's index in the edit.
    """

    subject: Transaction
    rows: list[Transaction]

    @property
    def subject_index(self) -> int:
        return next(index for index, row in enumerate(self.rows) if row is self.subject)


async def _store(world: World, shape: str, *, cost: Currency | None) -> Stored:
    """Store the row ``shape`` names — ``transfer_in`` (a linked pair source → dest) or ``adjustment_in`` (on dest)."""
    session = world.session
    if shape == "transfer_in":
        giving = _stored_row(world, broker=world.source, tx_type=TransactionType.TRANSFER, quantity=-TRANSFER_QUANTITY)
        receiving = _stored_row(world, broker=world.dest, tx_type=TransactionType.TRANSFER, quantity=TRANSFER_QUANTITY, cost=cost)
        session.add_all([giving, receiving])
        await session.flush()
        # A pair points both ways, and the ids exist only after the first flush (as legacy_cost_rows.py does it).
        giving.related_transaction_id = receiving.id
        receiving.related_transaction_id = giving.id
        await session.flush()
        return Stored(subject=receiving, rows=[giving, receiving])
    if shape == "adjustment_in":
        added = _stored_row(world, broker=world.dest, tx_type=TransactionType.ADJUSTMENT, quantity=ADJUSTMENT_QUANTITY, cost=cost)
        session.add(added)
        await session.flush()
        return Stored(subject=added, rows=[added])
    raise ValueError(f"unknown shape {shape!r}")


def _created_pair(world: World, *, cost_basis_mode: str | None = None) -> list[dict]:
    """A TRANSFER pair to create, source → dest, the receiving leg at index 1 and without a cost basis."""
    link_uuid = str(uuid.uuid4())
    giving = {"broker_id": world.source.id, "asset_id": world.asset.id, "type": "TRANSFER", "date": MOVE_DAY.isoformat(), "quantity": str(-TRANSFER_QUANTITY), "link_uuid": link_uuid}
    receiving = {"broker_id": world.dest.id, "asset_id": world.asset.id, "type": "TRANSFER", "date": MOVE_DAY.isoformat(), "quantity": str(TRANSFER_QUANTITY), "link_uuid": link_uuid}
    if cost_basis_mode is not None:
        receiving["cost_basis_mode"] = cost_basis_mode
    return [giving, receiving]


def _created_adjustment(world: World, *, broker: Broker, quantity: Decimal, cost_basis_mode: str | None = None) -> dict:
    """An ADJUSTMENT to create, without a cost basis."""
    created = {"broker_id": broker.id, "asset_id": world.asset.id, "type": "ADJUSTMENT", "date": MOVE_DAY.isoformat(), "quantity": str(quantity)}
    if cost_basis_mode is not None:
        created["cost_basis_mode"] = cost_basis_mode
    return created


async def _event(world: World, event_type: AssetEventType, value: Decimal) -> AssetEvent:
    """A manual event of the test's asset on ``MOVE_DAY`` (``provider_assignment_id`` None, as a user creates one)."""
    now = utcnow()
    event = AssetEvent(asset_id=world.asset.id, date=MOVE_DAY, type=event_type, value=value, currency=EUR, notes=f"{world.marker} {event_type.value}", created_at=now, updated_at=now)
    world.session.add(event)
    await world.session.flush()
    return event


async def _split_linked_adjustment(world: World) -> tuple[Transaction, AssetEvent]:
    """The ADJUSTMENT +10 that realizes a 2:1 SPLIT on ``source``, saved as the app saves it: created in Auto, linked.

    The Auto cost of a split-linked ADJUSTMENT is no cost at all (``_compute_wac_for_auto_items``, ``auto_cost.py``):
    its units come from the split's ratio, which the average rescales when it is computed, so the row is stored
    without a cost basis by design. That is checked here, so no test edits a row it only assumes.
    """
    split = await _event(world, AssetEventType.SPLIT, SPLIT_RATIO)
    created = {**_created_adjustment(world, broker=world.source, quantity=SPLIT_QUANTITY, cost_basis_mode="auto"), "asset_event_id": split.id}

    response = await _commit(world, creates=[created])

    assert response.committed is True and response.issues == [], f"scaffold: the Auto create of an ADJUSTMENT +{SPLIT_QUANTITY} linked to SPLIT id={split.id} was refused: {_render(response.issues)}"
    row_id = next(result.ids[0] for result in response.results if result.operation == "create" and result.index == 0)
    row = await world.session.get(Transaction, row_id)
    assert row is not None, f"scaffold: the created row id={row_id} is not in the session"
    stored = (row.type, row.quantity, row.asset_event_id, row.cost_basis_override, row.cost_basis_currency)
    assert stored == (TransactionType.ADJUSTMENT, SPLIT_QUANTITY, split.id, None, None), f"scaffold: the split-linked ADJUSTMENT must be stored linked and without a cost basis; (type, quantity, asset_event_id, cost, currency) = {stored}"
    return row, split


async def _link_change(world: World, link_change: str) -> tuple[int, int | None]:
    """The ``asset_event_id`` an update sends for ``link_change``, and the link the row has once it is applied.

    ``unlink`` sends 0: the unlink sentinel of ``TXUpdateItem`` (None leaves the link as it is; ``_apply_update_event``
    in ``batch_edits.py``), and what the app's ``buildUpdateDiff`` sends when a link is removed.
    ``relink-price-adjustment`` sends a PRICE_ADJUSTMENT event of the same asset, the other event type an ADJUSTMENT
    may realize (``event_suggestions.py``).
    """
    if link_change == "unlink":
        return 0, None
    if link_change == "relink-price-adjustment":
        price_adjustment = await _event(world, AssetEventType.PRICE_ADJUSTMENT, Decimal("1.5"))
        return price_adjustment.id, price_adjustment.id
    raise ValueError(f"unknown link change {link_change!r}")


async def _commit(world: World, *, creates: list[dict] | None = None, updates: list[dict] | None = None, promotes: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` runs it: commit requested, no user (so no access check)."""
    return await TransactionService(world.session).execute_batch(
        creates_raw=creates or [],
        updates_raw=updates or [],
        deletes=[],
        promotes_raw=promotes or [],
        commit=True,
    )


def _render(issues: list[TXValidationIssue]) -> str:
    """The issues, for a failure message."""
    return "; ".join(f"{issue.operation}[{issue.index}] ref_id={issue.ref_id} code={issue.code} field={issue.field} params={issue.params} error={issue.error!r}" for issue in issues) or "none"


def _cost_issues(response: TXBatchResponse) -> list[tuple]:
    """Every ``costBasisRequired`` issue, as ``(operation, index, ref_id, field, params)``."""
    return [(issue.operation, issue.index, issue.ref_id, issue.field, issue.params) for issue in response.issues if issue.code == COST_BASIS_REQUIRED]


def _update_results(response: TXBatchResponse) -> list[tuple]:
    """The update results, as ``(index, ids, status)`` in index order."""
    return sorted((result.index, tuple(result.ids), result.status) for result in response.results if result.operation == "update")


def _edit(rows: list[Transaction], edit: str, marker: str) -> list[dict]:
    """A notes-only or tags-only edit of every row given: what the app's diff sends when nothing else changed."""
    if edit == "notes":
        return [{"id": row.id, "description": f"{marker} notes edited"} for row in rows]
    if edit == "tags":
        return [{"id": row.id, "tags": EDITED_TAGS} for row in rows]
    raise ValueError(f"unknown edit {edit!r}")


def _assert_edit_landed(rows: list[Transaction], edit: str, marker: str) -> None:
    for row in rows:
        if edit == "notes":
            assert row.description == f"{marker} notes edited", f"row {row.id} ({row.type.value} {row.quantity}): notes {row.description!r} after a committed notes edit"
        else:
            assert row.tags == ",".join(EDITED_TAGS), f"row {row.id} ({row.type.value} {row.quantity}): tags {row.tags!r} after a committed tags edit"


def _requires_cost_basis(tx_type: TransactionType, quantity: Decimal) -> bool:
    """``_requires_cost_basis`` on an unsaved row of this type and quantity, called as the batch calls it.

    Through an instance without a session: the rule reads the row alone, and the call works whether it stays a
    staticmethod or not.
    """
    row = Transaction(broker_id=1, asset_id=1, type=tx_type, date=MOVE_DAY, quantity=quantity, amount=Decimal("0"))
    return bool(TransactionService(session=None)._requires_cost_basis(row))


def _metadata_says_required(tx_type: TransactionType, quantity: Decimal) -> bool:
    """What ``TX_TYPE_METADATA`` says, read the way N2 reads it: a pair type by its side, any other by its mode."""
    entry = TX_TYPE_METADATA[tx_type]
    mode = entry.cost_basis_mode if entry.cost_basis_pair is None else entry.cost_basis_pair[1 if quantity > 0 else 0]
    return mode == "required_qty_pos" and quantity > 0


def _patch_metadata(monkeypatch: pytest.MonkeyPatch, tx_type: TransactionType, attribute: str, value) -> None:
    """Patch one field of a ``TX_TYPE_METADATA`` entry IN PLACE, for this test only.

    The entry object itself is changed — not a copy put back in the dict — so whatever reads the metadata when it
    runs, through the dict or through the entry, sees the patch. A rule that copies the metadata at import time does
    not, and that is the defect these tests exist to refuse. ``monkeypatch`` restores the field at teardown.
    """
    monkeypatch.setattr(TX_TYPE_METADATA[tx_type], attribute, value)
    assert getattr(TX_TYPE_METADATA[tx_type], attribute) == value, f"scaffold: TX_TYPE_METADATA[{tx_type.value}].{attribute} does not show the patch"


# ============================================================================
# RED — EDITS OF A ROW STORED WITHOUT A COST
# ============================================================================


class TestEditsOfARowStoredWithoutCost:
    """RED before N2: the edits that change no type, quantity or cost of a row stored without a cost commit.

    Today ``_check_update_cost_basis`` checks the final state of EVERY update, so any edit of such a row is refused
    with ``costBasisRequired`` on the row — the subject's index, ``ref_id`` the row — and the batch does not commit.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    @pytest.mark.parametrize("edit", EDITS)
    async def test_notes_or_tags_edit_of_row_stored_without_cost_commits(self, world, edit, shape):
        """RED before N2: a notes-only or tags-only edit of a row stored without a cost commits, and repairs nothing."""
        stored = await _store(world, shape, cost=None)

        response = await _commit(world, updates=_edit(stored.rows, edit, world.marker))

        assert response.committed is True and response.issues == [], f"N2: a {edit}-only edit of a {SHAPE_LABELS[shape]} stored without a cost basis changes no type, quantity or cost, so it must commit and leave the row as it is. It was refused: {_render(response.issues)}"
        assert _update_results(response) == [(index, (row.id,), "success") for index, row in enumerate(stored.rows)], f"Committed, but not every row was updated: {response.results}"
        _assert_edit_landed(stored.rows, edit, world.marker)
        assert (stored.subject.cost_basis_override, stored.subject.cost_basis_currency) == (None, None), f"N2 repairs nothing: id={stored.subject.id} must keep no cost basis after a {edit} edit, it now has {stored.subject.cost_basis_override} {stored.subject.cost_basis_currency}"

    @pytest.mark.asyncio
    async def test_date_only_edit_of_adjustment_stored_without_cost_commits(self, world):
        """RED before N2, DERIVED: a date is none of the three changes the rule reads, so a date-only edit commits.

        Not in the coordinator's list: it follows from the decision «the rule applies to updates that change type,
        quantity or cost». It is the test that tells a cure listing what matters (type, quantity, cost, event link)
        from one listing what is harmless (notes, tags): the second refuses this edit. Drop it if a date was meant to
        count.
        """
        stored = await _store(world, "adjustment_in", cost=None)
        new_day = MOVE_DAY + timedelta(days=1)

        response = await _commit(world, updates=[{"id": stored.subject.id, "date": new_day.isoformat()}])

        assert response.committed is True and response.issues == [], f"N2: a date-only edit of an ADJUSTMENT +{ADJUSTMENT_QUANTITY} stored without a cost basis changes no type, quantity or cost, so it must commit. It was refused: {_render(response.issues)}"
        assert stored.subject.date == new_day, f"Committed, but the row's date is {stored.subject.date}, not {new_day}"
        assert (stored.subject.cost_basis_override, stored.subject.cost_basis_currency) == (None, None), f"N2 repairs nothing: the row now has {stored.subject.cost_basis_override} {stored.subject.cost_basis_currency}"


# ============================================================================
# RED — THE RULE READS THE METADATA
# ============================================================================


class TestTheRuleReadsTheMetadata:
    """RED before N2: the rule follows ``TX_TYPE_METADATA``, so a patched entry changes the answer.

    Today ``_requires_cost_basis`` is written by hand (TRANSFER and ADJUSTMENT with quantity > 0) and ignores the
    patch: it answers what it always answered.
    """

    @pytest.mark.parametrize(
        ("tx_type", "attribute", "patched", "quantity", "required"),
        [
            (TransactionType.ADJUSTMENT, "cost_basis_mode", "optional", ADJUSTMENT_QUANTITY, False),
            (TransactionType.TRANSFER, "cost_basis_pair", ["forbidden", "optional"], TRANSFER_QUANTITY, False),
            (TransactionType.BUY, "cost_basis_mode", "required_qty_pos", Decimal("3"), True),
        ],
        ids=["adjustment-made-optional", "transfer-receiver-made-optional", "buy-made-required"],
    )
    def test_requires_cost_basis_follows_patched_metadata(self, monkeypatch, tx_type, attribute, patched, quantity, required):
        """RED before N2: ``_requires_cost_basis`` answers what the patched metadata says, for any type."""
        _patch_metadata(monkeypatch, tx_type, attribute, patched)

        answer = _requires_cost_basis(tx_type, quantity)

        assert answer is required, f"N2: with TX_TYPE_METADATA[{tx_type.value}].{attribute} patched to {patched!r}, _requires_cost_basis({tx_type.value}, quantity={quantity}) must follow the metadata and answer {required}; it answered {answer}, so the rule is still written by hand"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    async def test_create_without_cost_commits_when_metadata_makes_it_optional(self, world, monkeypatch, shape):
        """RED before N2: a create without a cost commits once the metadata makes its cost basis optional.

        The ADJUSTMENT goes through ``_check_result_create_cost_basis``, the TRANSFER pair through
        ``_check_linked_create_cost_basis``: both ask ``_requires_cost_basis``.
        """
        if shape == "transfer_in":
            _patch_metadata(monkeypatch, TransactionType.TRANSFER, "cost_basis_pair", ["forbidden", "optional"])
            creates, subject_index = _created_pair(world), 1
        else:
            _patch_metadata(monkeypatch, TransactionType.ADJUSTMENT, "cost_basis_mode", "optional")
            creates, subject_index = [_created_adjustment(world, broker=world.dest, quantity=ADJUSTMENT_QUANTITY)], 0

        response = await _commit(world, creates=creates)

        assert response.committed is True and response.issues == [], f"N2: with TX_TYPE_METADATA patched to make its cost basis optional, a {SHAPE_LABELS[shape]} created without a cost must commit; it was refused, so the hand-written rule still decides: {_render(response.issues)}"
        created_id = next(result.ids[0] for result in response.results if result.operation == "create" and result.index == subject_index)
        created = await world.session.get(Transaction, created_id)
        assert created is not None and created.cost_basis_override is None, f"The {SHAPE_LABELS[shape]} id={created_id} was committed with a cost basis nobody gave: {created}"


# ============================================================================
# GUARDS — CREATES NEED A COST
# ============================================================================


class TestCreatesNeedACost:
    """Guard, green before and after N2: a create without a cost is refused on its own row."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    async def test_create_without_cost_is_refused_on_its_row(self, world, shape):
        """Guard: ``costBasisRequired`` on the create's index, field ``cost_basis_override``, ``params.type``; not committed.

        The row that needs the cost sits at index 1 behind a row that needs none — the pair's giving leg, or an
        ADJUSTMENT taking one unit away — so the index is the row's own, not a default.
        """
        if shape == "transfer_in":
            creates, expected_type = _created_pair(world), "TRANSFER"
        else:
            creates = [
                _created_adjustment(world, broker=world.source, quantity=Decimal("-1")),
                _created_adjustment(world, broker=world.dest, quantity=ADJUSTMENT_QUANTITY),
            ]
            expected_type = "ADJUSTMENT"

        response = await _commit(world, creates=creates)

        assert response.committed is False, f"A {SHAPE_LABELS[shape]} created without a cost basis was committed: {response.results}"
        assert _cost_issues(response) == [("create", 1, None, "cost_basis_override", {"type": expected_type})], f"Expected one costBasisRequired on create 1 alone: {_render(response.issues)}"
        assert [issue for issue in response.issues if issue.code != COST_BASIS_REQUIRED] == [], f"Only the cost basis may refuse this batch: {_render(response.issues)}"


# ============================================================================
# GUARDS — UPDATES THAT CHANGE WHAT THE RULE READS
# ============================================================================


class TestUpdatesThatChangeWhatTheRuleReads:
    """Guard, green before and after N2: an update that changes the quantity or the type, or names a cost basis mode,
    without a cost, is refused.

    Today every update is checked; after N2 these still are, because each changes the quantity or the type of the
    stored row, or names the mode.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", ["adjustment-out-flipped-in", "adjustment-in-more-units", "transfer-in-more-units"])
    async def test_quantity_change_without_cost_is_refused(self, world, case):
        """Guard: −5 → +5 on an ADJUSTMENT (the sign), or more units on a row stored without a cost, is refused."""
        session = world.session
        if case == "adjustment-out-flipped-in":
            # An ADJUSTMENT taking 5 units away needs no cost; flipped to +5, it adds units and does.
            subject = _stored_row(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("-5"))
            session.add(subject)
            await session.flush()
            updates, subject_index = [{"id": subject.id, "quantity": "5"}], 0
        elif case == "adjustment-in-more-units":
            stored = await _store(world, "adjustment_in", cost=None)
            subject = stored.subject
            updates, subject_index = [{"id": subject.id, "quantity": "7"}], 0
        else:
            stored = await _store(world, "transfer_in", cost=None)
            giving, subject = stored.rows
            updates, subject_index = [{"id": giving.id, "quantity": "-6"}, {"id": subject.id, "quantity": "6"}], stored.subject_index

        response = await _commit(world, updates=updates)

        assert response.committed is False, f"{case}: an update changing the quantity of a row without a cost basis was committed: {response.results}"
        assert _cost_issues(response) == [("update", subject_index, subject.id, "cost_basis_override", {"type": subject.type.value})], f"{case}: expected one costBasisRequired on update {subject_index} (id={subject.id}): {_render(response.issues)}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    async def test_manual_mode_without_cost_is_refused(self, world, shape):
        """Guard: ``cost_basis_mode: "manual"`` with no ``cost_basis_override``, on a row stored without a cost, is refused.

        The update names a cost basis mode — one of the cost fields of the decision — and gives no cost: the rule
        applies and the row has none. The app never sends it (``buildUpdateDiff`` sends a mode only for Auto); a
        client can. The mode is not stored, so it cannot be compared with the row: naming it is the change.
        """
        stored = await _store(world, shape, cost=None)

        response = await _commit(world, updates=[{"id": stored.subject.id, "cost_basis_mode": "manual"}])

        assert response.committed is False, f"cost_basis_mode=manual without a cost basis on the {SHAPE_LABELS[shape]} id={stored.subject.id} was committed: {response.results}"
        assert _cost_issues(response) == [("update", 0, stored.subject.id, "cost_basis_override", {"type": stored.subject.type.value})], f"Expected one costBasisRequired on update 0 (id={stored.subject.id}): {_render(response.issues)}"

    @pytest.mark.asyncio
    async def test_type_change_into_adjustment_without_cost_is_refused(self, world, monkeypatch):
        """Guard: a BUY +3 turned into an ADJUSTMENT +3 without a cost is refused — the type alone changed the answer.

        Scaffold. No real swap group reaches a type that needs a cost: TRANSFER and ADJUSTMENT are singletons, and
        BUY↔SELL, DEPOSIT↔WITHDRAWAL, DIVIDEND↔INTEREST, TAX↔FEE are all ``forbidden`` in the metadata. So the test
        lets BUY swap with ADJUSTMENT, through ``SWAP_GROUPS`` (read by ``get_swap_group`` when it runs). The
        quantity stays +3 and no cost is sent: only the type can make the rule apply. The cash goes to 0, as an
        ADJUSTMENT has none; cash is not one of the changes the rule reads.
        """
        session = world.session
        other_groups = [group for group in type_metadata.SWAP_GROUPS if TransactionType.BUY not in group]
        monkeypatch.setattr(type_metadata, "SWAP_GROUPS", [frozenset({TransactionType.BUY, TransactionType.SELL, TransactionType.ADJUSTMENT}), *other_groups])
        bought = _stored_row(world, broker=world.dest, tx_type=TransactionType.BUY, quantity=Decimal("3"), amount=Decimal("-300"), currency=EUR)
        session.add(bought)
        await session.flush()

        response = await _commit(world, updates=[{"id": bought.id, "type": "ADJUSTMENT", "cash": {"code": EUR, "amount": "0"}}])

        uncoded = [issue for issue in response.issues if issue.code is None]
        assert uncoded == [], f"scaffold: the BUY → ADJUSTMENT swap did not get through (SWAP_GROUPS patch not read?), so this proves nothing about the rule: {_render(uncoded)}"
        assert response.committed is False, f"A BUY +3 turned into an ADJUSTMENT +3 without a cost basis was committed: {response.results}"
        assert _cost_issues(response) == [("update", 0, bought.id, "cost_basis_override", {"type": "ADJUSTMENT"})], f"Expected one costBasisRequired on update 0 (id={bought.id}): {_render(response.issues)}"


# ============================================================================
# GUARDS — EDITS OF A ROW WITH ITS COST
# ============================================================================


class TestEditsOfARowWithCost:
    """Guard, green before and after N2: a notes-only or tags-only edit of a row that has its cost commits."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    @pytest.mark.parametrize("edit", EDITS)
    async def test_notes_or_tags_edit_of_row_with_cost_commits(self, world, edit, shape):
        """Guard: committed, the edit landed, the cost basis is the one the row was saved with."""
        stored = await _store(world, shape, cost=STORED_COST)

        response = await _commit(world, updates=_edit(stored.rows, edit, world.marker))

        assert response.committed is True and response.issues == [], f"A {edit}-only edit of a {SHAPE_LABELS[shape]} with its cost basis was refused: {_render(response.issues)}"
        assert _update_results(response) == [(index, (row.id,), "success") for index, row in enumerate(stored.rows)], f"Committed, but not every row was updated: {response.results}"
        _assert_edit_landed(stored.rows, edit, world.marker)
        assert (stored.subject.cost_basis_override, stored.subject.cost_basis_currency) == (STORED_COST.amount, STORED_COST.code), f"A {edit} edit changed the cost basis of id={stored.subject.id}: {stored.subject.cost_basis_override} {stored.subject.cost_basis_currency}"


# ============================================================================
# RED AND GUARDS — DECISION P5: AN EXPLICIT NULL EMPTIES A MANUAL COST
# ============================================================================


async def _commit_as_the_endpoint(world: World, *, updates: list[dict]) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` runs it, its transaction included: kept when the service answers
    committed, rolled back otherwise (``commit_transactions``, ``api/v1/transactions.py``).

    ``execute_batch`` applies an update to the row and flushes it before its checks can refuse it, and leaves the commit
    or the rollback to its caller: what a refused batch applied stays in the session until the caller rolls it back. A
    savepoint stands in for the request's transaction, as ``test_transaction_service.py``'s W-B17 test does: the test's
    rows, flushed before it, survive its rollback — their flush opened SQLite's transaction, so the savepoint nests in it
    (``begin_writes``, ``db/session.py``) — and the session fixture still rolls everything back: a savepoint released
    inside its transaction commits nothing.

    After a rollback the rows the batch touched are expired: read them back with ``_stored_cost``, which re-reads them,
    never through the attributes of an expired copy, which would load lazily outside the event loop.
    """
    savepoint = await world.session.begin_nested()
    response = await _commit(world, updates=updates)
    if response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


async def _stored_cost(world: World, tx_id: int) -> tuple[Decimal | None, str | None]:
    """``(cost_basis_override, cost_basis_currency)`` of row ``tx_id`` as the database holds it: what the user finds once
    the request is over. ``populate_existing`` makes ``get`` emit its SELECT even for a row the session holds, and
    overwrite that copy with what it reads."""
    row = await world.session.get(Transaction, tx_id, populate_existing=True)
    assert row is not None, f"scaffold: row id={tx_id} is not in the database"
    return row.cost_basis_override, row.cost_basis_currency


def _show(cost: tuple[Decimal | None, str | None]) -> str:
    """A stored cost basis, for a failure message."""
    amount, code = cost
    return "no cost basis" if (amount, code) == (None, None) else f"{amount} {code}"


def _sends_the_cost(update: dict) -> bool:
    """Whether the batch reads ``cost_basis_override`` as SENT in ``update``: in ``model_fields_set`` once parsed, as
    ``_parse_lenient`` parses it. An explicit null is sent; a key left out is not."""
    return "cost_basis_override" in transaction_schemas.TXUpdateItem.model_validate(update).model_fields_set


async def _legacy_row_with_cost(world: World, shape: str) -> Transaction:
    """A row stored with a cost basis of 42 EUR although its type and side take none: the handover cost decision 47
    writes on a giving leg, or what an older version or an API client left — no rule refuses a ``cost_basis_override``
    sent where none is allowed (rule 12 reads only ``cost_basis_mode``), on a create or on an update.

    ``buy``: a BUY +3 on ``dest`` paying 300 EUR (``dest`` allows a cash overdraft). ``adjustment_out``: an ADJUSTMENT −4
    on ``source``, which holds the BUY's 10 units, so it does not go short — the shape of a split TRANSFER's giving leg.
    """
    if shape == "buy":
        row = _stored_row(world, broker=world.dest, tx_type=TransactionType.BUY, quantity=Decimal("3"), cost=STORED_COST, amount=Decimal("-300"), currency=EUR)
    elif shape == "adjustment_out":
        row = _stored_row(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=-TRANSFER_QUANTITY, cost=STORED_COST)
    else:
        raise ValueError(f"unknown legacy shape {shape!r}")
    world.session.add(row)
    await world.session.flush()
    return row


# Decision P5 — an explicit null empties a manual cost where one is taken (TestDecisionP5AnExplicitNullEmptiesTheCost).
# The rows that carry a cost basis although their type and side take none, where the null is ignored (_legacy_row_with_cost).
LEGACY_SHAPES = ("buy", "adjustment_out")
LEGACY_LABELS = {"buy": "BUY +3", "adjustment_out": f"ADJUSTMENT -{TRANSFER_QUANTITY}"}
AUTO_MODES = ("auto", "auto-detail")


class TestDecisionP5AnExplicitNullEmptiesTheCost:
    """Decision P5 — the developer's, 16/10: «se lo svuoto attivamente vuol dire che lo voglio cancellare» — read as the
    coordinator's option (B), 16/10 11:42, to be reviewed by the developer. In an update, ``cost_basis_override: null``
    SENT (the key in ``model_fields_set``) removes the manual cost basis — ``cost_basis_override`` and
    ``cost_basis_currency`` together — where the row's final type and side take one (``cost_basis_allowed``), and is
    refused there with ``costBasisRequired`` when one is required: on today's table every side that takes a cost requires
    one (TRANSFER and ADJUSTMENT with quantity > 0), so the null always ends in that refusal and never removes anything.
    Elsewhere the null is ignored, and with ``cost_basis_mode`` ``auto``/``auto-detail`` too (the Auto cost is computed);
    a key left out changes nothing.

    Before W-B30 ``_apply_update_values`` (``batch_edits.py``) wrote the cost only when it was not None, so an explicit
    null read as a key left out and was ignored everywhere, a side that requires a cost included:

    - red before W-B30, now its guard: emptying the manual cost of a TRANSFER's receiving leg, a side that needs one, is
      refused with ``costBasisRequired`` on the update — N2's update check, once the cost is gone — and the cost stays
      (before W-B30 the update committed);
    - guards, green before W-B30 and since: a null sent on a row whose type and side take no cost — a BUY, an
      ADJUSTMENT −q carrying the handover cost decision 47 writes on a giving leg — is ignored, the update commits and
      the cost stays; a notes-only edit of the pair, the key left out, keeps the receiving leg's cost; an Auto update
      sending the null, as the form does, writes the Auto cost.

    The row that needs a cost is the receiving leg of a stored TRANSFER pair (``_store``), saved with 42 EUR; its Auto
    cost is ``source``'s average, 100 EUR (``UNIT_COST``), so "kept" and "recomputed" cannot be confused. Each test runs
    the batch as ``POST /transactions/commit`` does, its transaction included (``_commit_as_the_endpoint``), and reads
    the row back from the database (``_stored_cost``).
    """

    @pytest.mark.asyncio
    async def test_emptying_the_manual_cost_of_a_received_transfer_is_refused(self, world):
        """Red before W-B30 (decision P5), now its guard: ``{id, cost_basis_override: null}`` on the receiving leg is
        refused — one issue, ``costBasisRequired`` on update 0, ``ref_id`` the leg — and the database keeps its 42 EUR.

        The cure clears both columns, and N2's update check (``_check_update_cost_basis``) then sees a row that needs a
        cost and lost the one it was stored with. Before W-B30 the null kept the cost, and the update committed with no
        issue.
        """
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        subject_id = stored.subject.id
        update = {"id": subject_id, "cost_basis_override": None}
        assert _sends_the_cost(update), "scaffold: the update must SEND cost_basis_override (an explicit null), or this is the case of a key left out"

        response = await _commit_as_the_endpoint(world, updates=[update])

        stored_after = await _stored_cost(world, subject_id)
        assert response.committed is False, f"Decision P5: emptying the manual cost of a received TRANSFER is saved, and the receiving leg id={subject_id} holds {_show(stored_after)} — that leg needs a cost basis, so the update must be refused with costBasisRequired and the cost kept"
        assert [issue for issue in response.issues if issue.code != COST_BASIS_REQUIRED] == [], f"Only the missing cost basis may refuse this update: {_render(response.issues)}"
        assert _cost_issues(response) == [("update", 0, subject_id, "cost_basis_override", {"type": "TRANSFER"})], f"Expected one costBasisRequired on update 0 (id={subject_id}): {_render(response.issues)}"
        assert stored_after == (STORED_COST.amount, STORED_COST.code), f"The update was refused, yet the receiving leg id={subject_id} holds {_show(stored_after)} instead of the {STORED_COST.amount} {STORED_COST.code} it was saved with"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", LEGACY_SHAPES)
    async def test_a_null_where_no_cost_is_taken_is_ignored(self, world, shape):
        """Guard, green before W-B30 and since: ``{id, cost_basis_override: null}`` on a row whose type and side
        take no cost basis, yet carry one, is ignored — the update commits, and ``cost_basis_override`` and
        ``cost_basis_currency`` stay as stored, 42 EUR.

        The coordinator's decision (B), 16/10 11:42, to be reviewed by the developer: the null removes the MANUAL cost
        («toglie il costo manuale») where the type and side take one, and is ignored elsewhere. This protects the
        handover cost decision 47 writes on a giving leg — an ADJUSTMENT −q carrying its broker's Auto cost, the cost
        CP-16 hands its units over at — from a null sent with it; the BUY stands for any other side that takes none. The
        row neither allows nor requires a cost — checked first — and nothing else refuses the update: rule 12 reads only
        ``cost_basis_mode``, not sent, and the rest of the row is valid and unchanged. A cure that clears wherever the
        null is sent turns it red.
        """
        row = await _legacy_row_with_cost(world, shape)
        row_id = row.id
        sides = (type_metadata.cost_basis_allowed(row.type, row.quantity), _requires_cost_basis(row.type, row.quantity))
        assert sides == (False, False), f"precondition broken: a {LEGACY_LABELS[shape]} must neither allow nor require a cost basis; (cost_basis_allowed, _requires_cost_basis) = {sides}"
        stored_before = await _stored_cost(world, row_id)
        assert stored_before == (STORED_COST.amount, STORED_COST.code), f"scaffold: the {LEGACY_LABELS[shape]} id={row_id} must be stored with its cost basis, or a null that leaves it alone proves nothing; it holds {_show(stored_before)}"
        update = {"id": row_id, "cost_basis_override": None}
        assert _sends_the_cost(update), "scaffold: the update must SEND cost_basis_override (an explicit null), or this is the case of a key left out"

        response = await _commit_as_the_endpoint(world, updates=[update])

        stored_after = await _stored_cost(world, row_id)
        assert response.committed is True and response.issues == [], f"Decision P5 (B): a null cost sent on a {LEGACY_LABELS[shape]}, a side that takes no cost basis, must be ignored, yet the update was refused: {_render(response.issues)}"
        assert _update_results(response) == [(0, (row_id,), "success")], f"Committed, but the row was not updated: {response.results}"
        assert stored_after == stored_before, f"Decision P5 (B): a null sent on a {LEGACY_LABELS[shape]}, a side that takes no cost basis, changed its cost: id={row_id} held {_show(stored_before)}, now {_show(stored_after)} — on a giving leg, decision 47's handover cost"

    @pytest.mark.asyncio
    async def test_notes_edit_without_the_cost_key_keeps_the_cost(self, world):
        """Guard, green before W-B30 and since: a notes-only edit of the pair — what the app's diff sends, the cost
        key left out — commits, the notes land, and the receiving leg keeps its 42 EUR. A key left out is not a null.

        Both legs are edited, as the app edits them: a pair keeps one description.
        """
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        subject_id = stored.subject.id
        updates = _edit(stored.rows, "notes", world.marker)
        assert not any(_sends_the_cost(update) for update in updates), f"scaffold: no update may send cost_basis_override, or this is the case of an explicit null: {updates}"

        response = await _commit_as_the_endpoint(world, updates=updates)

        assert response.committed is True and response.issues == [], f"A notes-only edit of a received TRANSFER with its manual cost, the cost key left out, was refused: {_render(response.issues)}"
        assert _update_results(response) == [(index, (row.id,), "success") for index, row in enumerate(stored.rows)], f"Committed, but not every row was updated: {response.results}"
        _assert_edit_landed(stored.rows, "notes", world.marker)
        stored_after = await _stored_cost(world, subject_id)
        assert stored_after == (STORED_COST.amount, STORED_COST.code), f"Decision P5: a cost key left out keeps the cost, yet after a notes-only edit the receiving leg id={subject_id} holds {_show(stored_after)} instead of {STORED_COST.amount} {STORED_COST.code}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", AUTO_MODES)
    async def test_auto_update_sending_a_null_writes_the_auto_cost(self, world, mode):
        """Guard, green before W-B30 and since: ``{id, cost_basis_mode: auto, cost_basis_override: null}`` — what
        the form sends for a row in Auto (``buildUpdateDiff``, ``txPayloadHelpers.ts``) — is not refused for a missing
        cost, commits, and the receiving leg holds its Auto cost, ``source``'s average, 100 EUR: not the 42 it was saved
        with, not nothing. In Auto the null is ignored.
        """
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        subject_id = stored.subject.id
        update = {"id": subject_id, "cost_basis_mode": mode, "cost_basis_override": None}
        assert _sends_the_cost(update), "scaffold: the update must SEND cost_basis_override null, as the form does in Auto"

        response = await _commit_as_the_endpoint(world, updates=[update])

        assert _cost_issues(response) == [], f"Decision P5: in {mode} the null is ignored, yet the update of the received TRANSFER id={subject_id} was refused for a missing cost: {_render(response.issues)}"
        assert response.committed is True and response.issues == [], f"An {mode} update of a received TRANSFER sending a null cost was refused: {_render(response.issues)}"
        stored_after = await _stored_cost(world, subject_id)
        assert stored_after == (UNIT_COST, EUR), f"{mode} cost of the received TRANSFER id={subject_id}: expected {UNIT_COST} {EUR}, the average of source's BUY; the row holds {_show(stored_after)} (wac_results={response.wac_results})"


# ============================================================================
# GUARDS — AUTO COST
# ============================================================================


class TestAutoCost:
    """Guard, green before and after N2: an Auto create with an average available commits, with that average."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    async def test_auto_create_with_an_average_commits(self, world, shape):
        """Guard: committed, and the row carries the average of the BUY, 100 EUR.

        The TRANSFER's receiving leg averages its partner's broker (``source``) before the transfer; the ADJUSTMENT,
        created on ``source``, averages its own broker without itself.
        """
        if shape == "transfer_in":
            creates, subject_index = _created_pair(world, cost_basis_mode="auto"), 1
        else:
            creates, subject_index = [_created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")], 0

        response = await _commit(world, creates=creates)

        assert response.committed is True and response.issues == [], f"An Auto {SHAPE_LABELS[shape]} with an average available was refused: {_render(response.issues)}"
        created_id = next(result.ids[0] for result in response.results if result.operation == "create" and result.index == subject_index)
        created = await world.session.get(Transaction, created_id)
        assert created is not None, f"Committed, but the created row id={created_id} is not in the session"
        assert (created.cost_basis_override, created.cost_basis_currency) == (UNIT_COST, EUR), f"Auto cost of id={created_id}: expected {UNIT_COST} {EUR}, the average of the BUY; got {created.cost_basis_override} {created.cost_basis_currency} (wac_results={response.wac_results})"


# ============================================================================
# GUARDS — PROMOTE OF A ROW STORED WITHOUT A COST
# ============================================================================


class TestPromoteOfARowStoredWithoutCost:
    """Guard, green before and after N2: a promote cannot carry a row without a cost into a pair behind a notes edit."""

    @pytest.mark.asyncio
    async def test_promote_of_legacy_row_edited_in_same_batch_is_refused(self, world):
        """Guard: promote a stored ADJUSTMENT −5 (source) with a stored ADJUSTMENT +5 without a cost (dest), and edit
        the +5's notes in the same batch → refused, ``costBasisRequired`` on the +5.

        The promote makes the +5 the receiving leg of a TRANSFER. ``_check_promoted_saved_cost_basis`` skips the
        rows the batch also updates, because the update check covers them; today it does, since it checks every
        update. A cure that skips notes-only updates must still see this one — its type changes, ADJUSTMENT to
        TRANSFER — or stop the promote check from skipping it. Either issue is accepted: on the update or on the
        promote, both at index 0, with ``ref_id`` the +5. Otherwise a TRANSFER without a cost is committed, the
        defect closed by d7c148564 (devWiki problems/promote-skipped-cost-basis-check).
        """
        session = world.session
        giving = _stored_row(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("-5"))
        receiving = _stored_row(world, broker=world.dest, tx_type=TransactionType.ADJUSTMENT, quantity=Decimal("5"))
        session.add_all([giving, receiving])
        await session.flush()

        response = await _commit(
            world,
            updates=[{"id": receiving.id, "description": f"{world.marker} notes edited"}],
            promotes=[{"id_a": giving.id, "id_b": receiving.id}],
        )

        assert response.committed is False, f"A promote made the ADJUSTMENT +5 id={receiving.id}, stored without a cost basis, the receiving leg of a TRANSFER, and the batch was committed: {response.results}"
        on_receiver = [issue for issue in _cost_issues(response) if issue[2] == receiving.id]
        assert on_receiver in (
            [("update", 0, receiving.id, "cost_basis_override", {"type": "TRANSFER"})],
            [("promote", 0, receiving.id, "cost_basis_override", {"type": "TRANSFER"})],
        ), f"Expected one costBasisRequired on the receiving leg id={receiving.id}, on the update or on the promote: {_render(response.issues)}"


# ============================================================================
# RED AND GUARDS — THE SPLIT-LINKED ADJUSTMENT
# ============================================================================


class TestSplitLinkedAdjustment:
    """The ADJUSTMENT +qty that realizes a SPLIT: stored without a cost basis by design, its link standing for its cost.

    While the row points at a SPLIT event, the average reads its units as a rescale of the pool
    (``CostMovementKind.SPLIT``, ``financial_math/average_cost.py``). Unlinked, or linked to an event that is not a
    SPLIT, the same row is an acquisition of unknown cost. So an update that changes the link changes what the cost
    basis depends on, and is held to the rule like one that changes the type, the quantity or the cost.

    Before N2, every update of the row without Auto was refused. The first N2 cure let all of them through, link
    changes included, because its ``cost_fields`` compared type, quantity and cost only. The updates here carry no
    ``cost_basis_mode``, as an API client sends them: an Auto update is not checked here at all (its cost is
    recomputed), and the form opens a saved row without a manual cost in Auto.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("link_change", LINK_CHANGES)
    async def test_link_change_without_cost_is_refused(self, world, link_change):
        """RED with the first N2 cure, green once ``cost_fields`` carries ``asset_event_id``: ``costBasisRequired`` on
        update 0, ``ref_id`` the row, ``params.type`` ADJUSTMENT; not committed."""
        row, split = await _split_linked_adjustment(world)
        new_link, _linked_after = await _link_change(world, link_change)

        response = await _commit(world, updates=[{"id": row.id, "asset_event_id": new_link}])

        if response.committed:
            pytest.fail(
                f"{link_change}: the ADJUSTMENT +{SPLIT_QUANTITY} id={row.id}, linked to SPLIT id={split.id} and stored without a cost basis, was committed with asset_event_id={row.asset_event_id} and cost_basis_override={row.cost_basis_override}: "
                "an acquisition of unknown cost. Its link stands for its cost, so changing it must be held to the rule (cost_fields must carry asset_event_id)"
            )
        assert [issue for issue in response.issues if issue.code != COST_BASIS_REQUIRED] == [], f"{link_change}: only the cost basis may refuse this update: {_render(response.issues)}"
        assert _cost_issues(response) == [("update", 0, row.id, "cost_basis_override", {"type": "ADJUSTMENT"})], f"{link_change}: expected one costBasisRequired on update 0 (id={row.id}): {_render(response.issues)}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("edit", EDITS)
    async def test_notes_or_tags_edit_commits_and_keeps_the_link(self, world, edit):
        """Guard, green with the first N2 cure and after the fix: nothing the cost basis depends on changes, so a
        notes-only or tags-only edit commits, and the link and the missing cost stay as they are. (Before N2 it was
        refused, like any update of the row.)"""
        row, split = await _split_linked_adjustment(world)

        response = await _commit(world, updates=_edit([row], edit, world.marker))

        assert response.committed is True and response.issues == [], f"A {edit}-only edit of the split-linked ADJUSTMENT +{SPLIT_QUANTITY} id={row.id} changes nothing its cost basis depends on, and was refused: {_render(response.issues)}"
        assert _update_results(response) == [(0, (row.id,), "success")], f"Committed, but the row was not updated: {response.results}"
        _assert_edit_landed([row], edit, world.marker)
        assert (row.asset_event_id, row.cost_basis_override, row.cost_basis_currency) == (split.id, None, None), f"A {edit} edit changed what stands for the cost of id={row.id}: asset_event_id={row.asset_event_id}, cost {row.cost_basis_override} {row.cost_basis_currency}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("link_change", LINK_CHANGES)
    async def test_link_change_with_a_cost_commits(self, world, link_change):
        """Guard, green with the first N2 cure and after the fix: the same link change, with the row's cost in the same
        update, commits with that cost: the way out the refusal points to.

        The refusal is about the missing cost, never about the link. The keys are the ones the app's diff sends for
        it in manual mode: the link, and the cost (``buildUpdateDiff`` sends no mode for manual).
        """
        row, _split = await _split_linked_adjustment(world)
        new_link, linked_after = await _link_change(world, link_change)

        response = await _commit(world, updates=[{"id": row.id, "asset_event_id": new_link, "cost_basis_override": {"code": STORED_COST.code, "amount": str(STORED_COST.amount)}}])

        assert response.committed is True and response.issues == [], f"{link_change} with a cost basis on id={row.id} was refused: {_render(response.issues)}"
        assert _update_results(response) == [(0, (row.id,), "success")], f"Committed, but the row was not updated: {response.results}"
        assert (row.asset_event_id, row.cost_basis_override, row.cost_basis_currency) == (linked_after, STORED_COST.amount, STORED_COST.code), f"{link_change} with a cost: id={row.id} now has asset_event_id={row.asset_event_id}, cost {row.cost_basis_override} {row.cost_basis_currency}"


# ============================================================================
# GUARD — THE RULE AGREES WITH THE METADATA
# ============================================================================


class TestTheRuleAgreesWithTheMetadata:
    """Guard, green before and after N2: for every type and quantity sign, the rule says what the metadata says.

    Green today because the hand-written rule happens to match the metadata; after N2 because it reads it. A cure
    that reads it wrongly — the wrong side of a pair, the mode of a pair type — turns one of these red.
    """

    @pytest.mark.parametrize("quantity", [Decimal("-3"), Decimal("0"), Decimal("3")], ids=["qty-negative", "qty-zero", "qty-positive"])
    @pytest.mark.parametrize("tx_type", list(TransactionType), ids=lambda tx_type: tx_type.value)
    def test_requires_cost_basis_agrees_with_metadata(self, tx_type, quantity):
        """Guard: ``_requires_cost_basis(type, quantity)`` == the metadata's ``required_qty_pos`` with quantity > 0."""
        expected = _metadata_says_required(tx_type, quantity)

        answer = _requires_cost_basis(tx_type, quantity)

        entry = TX_TYPE_METADATA[tx_type]
        assert answer is expected, f"_requires_cost_basis({tx_type.value}, quantity={quantity}) answered {answer}; TX_TYPE_METADATA says {expected} (cost_basis_mode={entry.cost_basis_mode!r}, cost_basis_pair={entry.cost_basis_pair!r})"


# ============================================================================
# RED — DECISION 47: THE GIVING LEG OF A TRANSFER (SPLIT AND PROMOTE)
# ============================================================================


async def _run_batch(world: World, *, commit: bool, creates: list[dict] | None = None, updates: list[dict] | None = None, splits: list[dict] | None = None, promotes: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` (``commit=True``) or ``/validate`` (``commit=False``) runs it, with
    splits; no user, so no access check. It never commits: the session fixture rolls everything back."""
    return await TransactionService(world.session).execute_batch(
        creates_raw=creates or [],
        updates_raw=updates or [],
        deletes=[],
        splits_raw=splits or [],
        promotes_raw=promotes or [],
        commit=commit,
    )


async def _legs_now(world: World, giving: Transaction, receiving: Transaction) -> dict[str, tuple]:
    """The two legs as the batch left them in the session's transaction — re-read, the in-memory copies refreshed —
    as ``(type, quantity, related_transaction_id, cost_basis_override, cost_basis_currency)``."""
    ids = {"giving": giving.id, "receiving": receiving.id}
    statement = select(Transaction).where(Transaction.id.in_(list(ids.values()))).execution_options(populate_existing=True)
    rows = {row.id: row for row in (await world.session.execute(statement)).scalars()}
    return {label: (rows[tx_id].type, rows[tx_id].quantity, rows[tx_id].related_transaction_id, rows[tx_id].cost_basis_override, rows[tx_id].cost_basis_currency) for label, tx_id in ids.items()}


async def _assert_no_rate_nor_route(session: AsyncSession, currency: str, other: str = EUR) -> None:
    """Precondition: no rate and no route for ``currency``/``other`` exist, committed by anyone (as test_broker_service.py's
    ``_assert_no_fx_data``): the conversion the case needs is really missing, not merely assumed so."""
    base, quote = sorted((currency, other))
    rates = (await session.execute(select(func.count()).select_from(FxRate).where(FxRate.base == base, FxRate.quote == quote))).scalar_one()
    routes = (await session.execute(select(func.count()).select_from(FxConversionRoute).where(or_(and_(FxConversionRoute.base == base, FxConversionRoute.quote == quote), and_(FxConversionRoute.base == quote, FxConversionRoute.quote == base))))).scalar_one()
    assert (rates, routes) == (0, 0), f"precondition broken: {base}/{quote} has {rates} rate(s) and {routes} route(s) — this case needs a pair nobody stores"


async def _fx_conversion_pair(world: World) -> tuple[Transaction, Transaction]:
    """An FX_CONVERSION pair on ``dest`` (−100 EUR → +110 USD), linked both ways: a pair whose split needs no cost."""
    now = utcnow()
    sold = Transaction(broker_id=world.dest.id, type=TransactionType.FX_CONVERSION, date=MOVE_DAY, quantity=Decimal("0"), amount=Decimal("-100"), currency=EUR, description=f"{world.marker} EUR sold", created_at=now, updated_at=now)
    bought = Transaction(broker_id=world.dest.id, type=TransactionType.FX_CONVERSION, date=MOVE_DAY, quantity=Decimal("0"), amount=Decimal("110"), currency="USD", description=f"{world.marker} USD bought", created_at=now, updated_at=now)
    world.session.add_all([sold, bought])
    await world.session.flush()
    sold.related_transaction_id, bought.related_transaction_id = bought.id, sold.id
    await world.session.flush()
    return sold, bought


def _issue_view(issue: TXValidationIssue) -> dict:
    """What decision 47 fixes of an issue: where it is, its code, its field and its params — never its text."""
    return {"operation": issue.operation, "index": issue.index, "ref_id": issue.ref_id, "code": issue.code, "field": issue.field, "params": issue.params}


class TestDecision47TheGivingLegOfATransfer:
    """Decision 47 as N78-1 changed it (the developer's decision, 21/10/2026), RED until its cure but for the promote:
    where a batch takes a TRANSFER's giving leg out of its pair, the leg leaves as an ADJUSTMENT WITHOUT a value — an
    update of the same batch that gives it one is refused (``costBasisNotAllowed``) —, and a promote that makes a leg the
    giving side of a TRANSFER takes its cost away.

    ``source`` holds 10 units bought for 1 000 EUR (the ``world`` fixture): 100 EUR is its Auto cost, the cost its giving
    leg was handed over at before N78-1. The receiving leg carries 42 EUR (``STORED_COST``), never 100: a cure that copied
    the partner's cost — or still wrote the Auto cost on the giving leg — would show.
    """

    @pytest.mark.asyncio
    async def test_split_with_an_update_giving_the_giving_leg_a_cost_is_refused(self, world):
        """RED until N78-1: the batch splits the pair and, in an update, gives the giving leg a cost of 77 EUR — no
        ``cost_basis_mode``, as an API client sends a cost. The leg the split leaves is an ADJUSTMENT −4, which takes no
        value: one ``costBasisNotAllowed`` on update 0, ``ref_id`` the giving leg, and nothing else; not committed.

        Before N78-1 (the coordinator's decision 4, 16/10, a guard then): it committed, the giving leg an ADJUSTMENT −4 at
        77 EUR. The update runs after the split (``execute_batch``: split, then update), on the ADJUSTMENT the split left.
        """
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving, receiving = stored.rows
        own_cost = Currency(code=EUR, amount=Decimal("77"))
        assert own_cost.amount not in (UNIT_COST, STORED_COST.amount), "scaffold: the update's cost must differ from the Auto cost and from the receiving leg's"

        response = await _run_batch(world, commit=True, splits=[{"id_a": giving.id, "id_b": receiving.id}], updates=[{"id": giving.id, "cost_basis_override": {"code": own_cost.code, "amount": str(own_cost.amount)}}])

        refused = [(issue.operation, issue.index, issue.ref_id, issue.code) for issue in response.issues]
        assert (response.committed, refused) == (False, [("update", 0, giving.id, COST_BASIS_NOT_ALLOWED)]), (
            f"N78-1: the giving leg a split leaves is an ADJUSTMENT −{TRANSFER_QUANTITY}, which takes no value, so an update giving it {own_cost.amount} {own_cost.code} must be refused with "
            f"{COST_BASIS_NOT_ALLOWED} on update 0, ref_id {giving.id}, and nothing else; today committed={response.committed}, issues [{_render(response.issues)}]"
        )

    @pytest.mark.asyncio
    async def test_split_leaves_the_giving_leg_an_adjustment_without_a_value(self, world):
        """RED until N78-1: the split commits; the giving leg becomes an ADJUSTMENT −4 without ``cost_basis_override`` nor
        ``cost_basis_currency``; the receiving leg an ADJUSTMENT +4 that keeps its 42 EUR.

        Before N78-1 (decision 47): the giving leg left at ``source``'s Auto cost, 100 EUR (its BUY, the leg left out).
        """
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving, receiving = stored.rows

        response = await _run_batch(world, commit=True, splits=[{"id_a": giving.id, "id_b": receiving.id}])

        assert response.committed is True and response.issues == [], f"The split of the TRANSFER pair {giving.id}/{receiving.id} was refused: {_render(response.issues)}"
        assert [(result.operation, result.index, tuple(result.ids), result.status) for result in response.results] == [("split", 0, (giving.id, receiving.id), "success")]
        assert await _legs_now(world, giving, receiving) == {
            "giving": (TransactionType.ADJUSTMENT, -TRANSFER_QUANTITY, None, None, None),
            "receiving": (TransactionType.ADJUSTMENT, TRANSFER_QUANTITY, None, STORED_COST.amount, STORED_COST.code),
        }, f"N78-1: the giving leg id={giving.id} leaves without a value"

    @pytest.mark.asyncio
    async def test_split_leaves_the_giving_leg_without_a_value_beside_a_purchase_of_its_batch(self, world):
        """RED until N78-1: the same batch buys 10 more units on ``source`` for 3 000 EUR before the move; the split still
        leaves the giving leg an ADJUSTMENT −4 without a value — no average of the batch's final state is written.

        Before N78-1 (decision 47): the leg left at (1 000 + 3 000) / 20 = 200 EUR, computed in the batch's WAC stage."""
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving, receiving = stored.rows
        purchase = {
            "broker_id": world.source.id,
            "asset_id": world.asset.id,
            "type": "BUY",
            "date": LATER_BUY_DAY.isoformat(),
            "quantity": str(BUY_QUANTITY),
            "cash": {"code": EUR, "amount": str(LATER_BUY_PAID)},
            "description": f"{world.marker} buy in the split's batch",
        }
        expected_cost = (BUY_QUANTITY * UNIT_COST - LATER_BUY_PAID) / (2 * BUY_QUANTITY)
        assert expected_cost == Decimal("200"), "the oracle: (1 000 + 3 000) / 20"

        response = await _run_batch(world, commit=True, creates=[purchase], splits=[{"id_a": giving.id, "id_b": receiving.id}])

        assert response.committed is True and response.issues == [], f"A split beside a purchase was refused: {_render(response.issues)}"
        legs = await _legs_now(world, giving, receiving)
        assert legs["giving"] == (TransactionType.ADJUSTMENT, -TRANSFER_QUANTITY, None, None, None), f"N78-1: the giving leg id={giving.id} leaves without a value, never at the batch's average ({expected_cost} EUR): {legs['giving']}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", [pytest.param(True, id="commit"), pytest.param(False, id="validate")])
    async def test_split_whose_giving_legs_broker_lacks_a_conversion_still_goes_through(self, world, commit):
        """RED until N78-1: part of ``source``'s units were paid in PYG, which no rate converts — no average of ``source``
        exists, and none is needed: the giving leg leaves without a value. Both splits go through (index 0 is the split of
        an FX_CONVERSION pair), no issue; on /commit the giving leg is an ADJUSTMENT −4 without a value and the receiving
        leg keeps its 42 EUR; /validate (``commit=False``) answers clean.

        Before N78-1 (decision 47): one WAC_FX_UNAVAILABLE on split 1, ``ref_id`` the giving leg, params ``pairs`` and
        ``pair_details`` PYG/EUR; nothing committed. A real missing conversion: PYG is first proven absent from every rate
        and route, then the oracle — ``compute_wac_iterative`` on ``source`` up to the move without the leg — confirms
        there is no average and names PYG/EUR on the PYG purchase's day.
        """
        await _assert_no_rate_nor_route(world.session, PYG)
        now = utcnow()
        world.session.add(Transaction(broker_id=world.source.id, asset_id=world.asset.id, type=TransactionType.BUY, date=PYG_DAY, quantity=BUY_QUANTITY, amount=PYG_PAID, currency=PYG, description=f"{world.marker} buy in PYG", created_at=now, updated_at=now))
        sold, bought = await _fx_conversion_pair(world)
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving, receiving = stored.rows
        oracle = await compute_wac_iterative(world.session, broker_id=world.source.id, asset_id=world.asset.id, as_of_date=MOVE_DAY, asset_currency=EUR, excluded_tx_ids=[giving.id], use_cache=False)
        assert (oracle.wac, [(missing.pair, missing.dates) for missing in oracle.wac_missing_pairs]) == (None, [("PYG/EUR", [PYG_DAY])]), f"precondition broken: the giving leg's Auto cost must need PYG/EUR on {PYG_DAY}: {oracle}"

        response = await _run_batch(world, commit=commit, splits=[{"id_a": sold.id, "id_b": bought.id}, {"id_a": giving.id, "id_b": receiving.id}])

        endpoint = "/commit" if commit else "/validate"
        today = f"today committed={response.committed}, issues [{_render(response.issues)}]"
        assert (response.committed, [_issue_view(issue) for issue in response.issues]) == (commit, []), f"N78-1: the giving leg leaves without a value, so no conversion is missing and the splits go through ({endpoint}); {today}"
        if commit:
            assert await _legs_now(world, giving, receiving) == {
                "giving": (TransactionType.ADJUSTMENT, -TRANSFER_QUANTITY, None, None, None),
                "receiving": (TransactionType.ADJUSTMENT, TRANSFER_QUANTITY, None, STORED_COST.amount, STORED_COST.code),
            }

    @pytest.mark.asyncio
    @pytest.mark.parametrize("giving_first", [pytest.param(True, id="giving-side-as-id-a"), pytest.param(False, id="giving-side-as-id-b")])
    async def test_promote_into_a_transfer_takes_the_cost_off_the_giving_side(self, world, giving_first):
        """Green since decision 47, unchanged by N78-1: an ADJUSTMENT −4 on ``source`` carrying a cost — 100 EUR, as an
        old row may hold it (decision 47 wrote such costs before N78-1) — and an ADJUSTMENT +4 on ``dest`` carrying 42 EUR,
        promoted into a TRANSFER, in either order: the promote commits; the giving side loses ``cost_basis_override`` and ``cost_basis_currency`` — its new type takes
        no cost basis, ``cost_basis_allowed(TRANSFER, −4)`` is False — and the receiving side keeps its 42 EUR.

        Today the promote keeps both costs: a TRANSFER giving leg carrying a cost no screen can show or edit.
        """
        giving = _stored_row(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=-TRANSFER_QUANTITY, cost=Currency(code=EUR, amount=UNIT_COST))
        receiving = _stored_row(world, broker=world.dest, tx_type=TransactionType.ADJUSTMENT, quantity=TRANSFER_QUANTITY, cost=STORED_COST)
        world.session.add_all([giving, receiving])
        await world.session.flush()
        sides = (cost_basis_allowed(TransactionType.TRANSFER, -TRANSFER_QUANTITY), cost_basis_allowed(TransactionType.TRANSFER, TRANSFER_QUANTITY))
        assert sides == (False, True), f"precondition broken: TX_TYPE_METADATA must forbid a cost on a TRANSFER's giving side and allow it on its receiving side; cost_basis_allowed gives {sides}"
        first, second = (giving, receiving) if giving_first else (receiving, giving)

        response = await _run_batch(world, commit=True, promotes=[{"id_a": first.id, "id_b": second.id}])

        assert response.committed is True and response.issues == [], f"The promote of {first.id} and {second.id} into a TRANSFER was refused: {_render(response.issues)}"
        assert [(result.operation, result.index, tuple(result.ids), result.status) for result in response.results] == [("promote", 0, (first.id, second.id), "success")]
        assert await _legs_now(world, giving, receiving) == {
            "giving": (TransactionType.TRANSFER, -TRANSFER_QUANTITY, receiving.id, None, None),
            "receiving": (TransactionType.TRANSFER, TRANSFER_QUANTITY, giving.id, STORED_COST.amount, STORED_COST.code),
        }


# ============================================================================
# RED AND GUARDS — W-B69: AN AUTO COST OVER A POOL WITH AN UNREADABLE ROW
# ============================================================================

# The cure's TXValidationCode.AUTO_COST_UNREADABLE, as a literal: the member does not exist before it.
AUTO_COST_UNREADABLE = "autoCostUnreadable"
# W-B74's TXValidationCode.LEDGER_UNREADABLE, as a literal: the replay's refusal of a broker whose rows hold a quantity or
# an amount that reads None, which a W-B69 batch replaying source also gets once that cure is in.
LEDGER_UNREADABLE = "ledgerUnreadable"
# The two columns (a) and (d) plant 'n/a' in: RealDecimal reads either as None since W-B58.
UNREADABLE_COLUMNS = ("quantity", "amount")
# Every column a plant may overwrite: those two, and a stored cost basis (the contract's addition of 17/10).
PLANTABLE_COLUMNS = (*UNREADABLE_COLUMNS, "cost_basis_override")
AUTO_OPERATIONS = ("create", "update")
ENDPOINTS = (pytest.param(True, id="commit"), pytest.param(False, id="validate"))
# The incoming rows that take a cost basis, and the per-unit cost they are stored with: the 3 000 EUR the planted BUY pays
# for its 10 units, so that every readable plant averages the same.
INCOMING_KINDS = ("adjustment", "receiving-transfer")
PLANTED_COST = -LATER_BUY_PAID / BUY_QUANTITY
PLANT_LABELS = {
    "buy": f"BUY +{BUY_QUANTITY} for {-LATER_BUY_PAID} EUR",
    "adjustment": f"ADJUSTMENT +{BUY_QUANTITY} stored at {PLANTED_COST} EUR a unit",
    "receiving-transfer": f"receiving TRANSFER +{BUY_QUANTITY} stored at {PLANTED_COST} EUR a unit",
}
# source's pool with the planted row readable: (1 000 + 3 000) / 20.
READABLE_POOL_COST = (BUY_QUANTITY * UNIT_COST - LATER_BUY_PAID) / (2 * BUY_QUANTITY)
# What today's average makes of that pool with one column of the planted row unreadable: the defect, for the red messages.
TODAY_OVER_AN_UNREADABLE = {
    "quantity": "the average skips the row whose quantity reads None: 1 000 / 10 = 100, where the readable pool gives 200",
    "amount": "the average takes the BUY whose amount reads None as a free acquisition: 1 000 / 20 = 50, where the readable pool gives 200",
    "cost_basis_override": "the average takes the row whose cost basis reads None as an acquisition of unknown cost, entering at zero: 1 000 / 20 = 50, where the readable pool gives 200",
}
UI_LANGUAGES = ("en", "it", "fr", "es")
# What _raw_rows reads of a row: its raw values, and the storage class of the three columns a plant may overwrite.
_RAW_KINDS = ", ".join(f"typeof({column}) AS {column}_kind" for column in ("quantity", "amount", "cost_basis_override"))
_RAW_COLUMNS = f"id, type, date, quantity, amount, currency, related_transaction_id, cost_basis_override, cost_basis_currency, description, tags, {_RAW_KINDS}"
# A plant takes an id this far past every id in use, and the rows written after it the ids that follow: a number this large
# in an issue's text can only be one of them (``_ids_named``). Below it a number may be anything — the count, a day, an
# amount, or an id the lane reuses: each test rolls back, the AUTOINCREMENT counter with it, so the ``world``'s BUY is id 1
# in a fresh lane, as the count of an issue may be.
_ID_GAP = 1_000_000


async def _plant(world: World, *, kind: str = "buy", unreadable: tuple[str, ...] = (), day: date = LATER_BUY_DAY, asset_id: int | None = None) -> int:
    """A row of 10 units on ``source`` on ``day`` — of the ``world``'s asset, or ``asset_id`` — stored like any row, then
    each column of ``unreadable`` overwritten with 'n/a' through the same session; its id.

    ``kind``: ``buy``, a BUY paying 3 000 EUR, its cost basis NULL as a BUY's is; or an incoming row that takes a cost
    basis, stored at 300 EUR a unit (``PLANTED_COST``): ``adjustment``, an ADJUSTMENT +10, or ``receiving-transfer``, a
    TRANSFER +10 linked both ways to its giving leg on a third broker of the test's own, which no batch here touches.
    Readable, any of them is the second acquisition of ``source``'s pool, worth 3 000 EUR. Its id is ``_ID_GAP`` past every
    id in use, so that it, and every row written after it, can be told from any small number in an issue's text. Unreadable,
    what the case rests on is checked here, so no test refuses or accepts a row it only assumes unreadable: SQLite keeps the
    text (``typeof`` 'text', so not NULL: the cure's test for a stored cost basis); the facade's filters —
    ``compute_wac_iterative``: quantity not NULL and not 0 — still select the row; and its ORM copy, expired so that every
    later load re-reads it, loads with None in each overwritten column (``RealDecimal``, W-B58).
    """
    session = world.session
    now = utcnow()
    description = f"{world.marker} W-B69 planted {kind}"
    planted_id = ((await session.execute(select(func.max(Transaction.id)))).scalar_one() or 0) + _ID_GAP
    common = {"id": planted_id, "broker_id": world.source.id, "asset_id": asset_id or world.asset.id, "date": day, "quantity": BUY_QUANTITY, "description": description, "created_at": now, "updated_at": now}
    if kind == "buy":
        row = Transaction(type=TransactionType.BUY, amount=LATER_BUY_PAID, currency=EUR, **common)
    elif kind in INCOMING_KINDS:
        incoming_type = TransactionType.ADJUSTMENT if kind == "adjustment" else TransactionType.TRANSFER
        row = Transaction(type=incoming_type, amount=Decimal("0"), currency=None, cost_basis_override=PLANTED_COST, cost_basis_currency=EUR, **common)
    else:
        raise ValueError(f"unknown plant kind {kind!r}")
    session.add(row)
    await session.flush()
    row_id = row.id
    if kind == "receiving-transfer":
        # Its giving leg's broker allows shorting: it holds none of the units it gave, and none of these batches replays it.
        sender = Broker(name=f"{world.marker} W-B69 sender", description="W-B69: the broker the planted TRANSFER came from", allow_cash_overdraft=True, allow_asset_shorting=True, created_at=now, updated_at=now)
        session.add(sender)
        await session.flush()
        giving = Transaction(broker_id=sender.id, asset_id=row.asset_id, type=TransactionType.TRANSFER, date=day, quantity=-BUY_QUANTITY, amount=Decimal("0"), description=description, created_at=now, updated_at=now)
        session.add(giving)
        await session.flush()
        giving.related_transaction_id, row.related_transaction_id = row_id, giving.id
        await session.flush()
    if not unreadable:
        return row_id
    for column in unreadable:
        assert column in PLANTABLE_COLUMNS, f"scaffold: a plant overwrites {PLANTABLE_COLUMNS}, not {column!r}"
        await session.execute(text(f"UPDATE transactions SET {column} = 'n/a' WHERE id = :id"), {"id": row_id})
    kinds = (await session.execute(text(f"SELECT {', '.join(f'typeof({column}) AS {column}' for column in PLANTABLE_COLUMNS)} FROM transactions WHERE id = :id"), {"id": row_id})).one()._asdict()
    assert {column: kinds[column] for column in unreadable} == dict.fromkeys(unreadable, "text"), f"setup: the planted {kind} id={row_id} must hold 'n/a' as text in {unreadable}; typeof = {kinds}"
    selected = (await session.execute(select(func.count()).select_from(Transaction).where(Transaction.id == row_id, Transaction.quantity.is_not(None), Transaction.quantity != 0))).scalar_one()
    assert selected == 1, f"setup: the facade's filters (quantity IS NOT NULL, quantity != 0) must still select the planted {kind} id={row_id}, or it is not in the pool"
    session.expire(row)
    loaded = (await session.execute(select(Transaction).where(Transaction.id == row_id).execution_options(populate_existing=True))).scalar_one()
    read = {column: getattr(loaded, column) for column in PLANTABLE_COLUMNS}
    assert {column: read[column] for column in unreadable} == dict.fromkeys(unreadable), f"setup: RealDecimal must read the 'n/a' of id={row_id} as None (W-B58); the row loads {read}"
    return row_id


async def _world_brokers(world: World) -> list[int]:
    """Every broker of the test's own, by its marker: ``source``, ``dest``, and the one a ``receiving-transfer`` plant adds."""
    statement = select(Broker.id).where(Broker.name.startswith(world.marker, autoescape=True)).order_by(Broker.id)
    return list((await world.session.execute(statement)).scalars())


async def _other_asset(world: World) -> int:
    """A second asset of the test's own, in EUR: its rows lie outside every pool of the ``world``'s asset."""
    now = utcnow()
    other = Asset(display_name=f"{world.marker} other asset", asset_type=AssetType.STOCK, currency=EUR, created_at=now, updated_at=now)
    world.session.add(other)
    await world.session.flush()
    return other.id


@dataclass
class AutoBatch:
    """A batch whose row ``operation`` ``index`` asks for an Auto cost over ``source``'s pool (``_auto_batch``)."""

    operation: str
    index: int
    creates: list[dict]
    updates: list[dict]
    #: The stored row an update recomputes; None for a create, whose id the batch's results give (``_created_id``).
    row_id: int | None


async def _auto_batch(world: World, operation: str, mode: str, *, alone: bool = False) -> AutoBatch:
    """The Auto row, in ``mode``, and the rows its batch sends: the receiving leg of a TRANSFER pair source → dest, whose
    pool is its partner's broker, ``source``, up to the move, without the two legs (``_auto_cost_source``).

    ``create``: the pair (``_created_pair``), the receiving leg at index 1. ``update``: the stored pair (``_store``, the
    receiving leg at 42 EUR), both legs given the same new notes — a pair keeps one description — and the receiving leg
    the mode, at index 1. ``alone``: the receiving leg's update alone, at index 0 — the one batch that replays no day of
    ``source`` (the balance replay covers the brokers of the updated rows, ``earliest_date_by_broker``).
    """
    if operation == "create":
        assert not alone, "scaffold: a receiving leg is created with its giving leg"
        return AutoBatch(operation="create", index=1, creates=_created_pair(world, cost_basis_mode=mode), updates=[], row_id=None)
    stored = await _store(world, "transfer_in", cost=STORED_COST)
    giving, receiving = stored.rows
    if alone:
        return AutoBatch(operation="update", index=0, creates=[], updates=[{"id": receiving.id, "cost_basis_mode": mode}], row_id=receiving.id)
    notes = f"{world.marker} notes edited with the Auto cost"
    return AutoBatch(operation="update", index=1, creates=[], updates=[{"id": giving.id, "description": notes}, {"id": receiving.id, "description": notes, "cost_basis_mode": mode}], row_id=receiving.id)


async def _as_the_endpoint(world: World, *, commit: bool, creates: list[dict] | None = None, updates: list[dict] | None = None, splits: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` (``commit=True``) or ``/validate`` runs it, its transaction included:
    /commit keeps what the service answers committed and rolls back the rest, /validate always rolls back
    (``api/v1/transactions.py``). A savepoint stands in for the request's transaction, as in ``_commit_as_the_endpoint``;
    the session fixture still rolls everything back. Read the rows back by id afterwards (``_raw_rows``, ``_rows_by_id``),
    never through a copy the rollback expired. A batch refuses with issues: one that raises fails the test.
    """
    savepoint = await world.session.begin_nested()
    try:
        response = await _run_batch(world, commit=commit, creates=creates, updates=updates, splits=splits)
    except Exception as error:  # the contract: a refusal is an issue, nothing raises
        pytest.fail(f"W-B69: the batch must answer with its issues, never raise; it raised {type(error).__name__}: {error!r}")
    if commit and response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


async def _raw_rows(world: World, broker_ids: list[int]) -> dict[int, dict]:
    """Every row of ``broker_ids`` as SQLite holds it in the session's transaction, by id: raw values, and the storage class
    of the three columns a plant may overwrite — what the user finds once the request is over, the 'n/a' included."""
    statement = text(f"SELECT {_RAW_COLUMNS} FROM transactions WHERE broker_id IN :brokers ORDER BY id").bindparams(bindparam("brokers", expanding=True))
    return {row.id: row._asdict() for row in (await world.session.execute(statement, {"brokers": broker_ids})).all()}


def _changed(before: dict[int, dict], after: dict[int, dict]) -> dict[int, tuple]:
    """The rows two ``_raw_rows`` reads disagree on, by id: ``(before, after)``, None for a row absent on one side."""
    return {tx_id: (before.get(tx_id), after.get(tx_id)) for tx_id in sorted(set(before) | set(after)) if before.get(tx_id) != after.get(tx_id)}


async def _rows_by_id(world: World, ids: list[int]) -> dict[int, tuple]:
    """``(type, quantity, related_transaction_id, cost_basis_override, cost_basis_currency)`` of each row of ``ids`` the
    database still holds, re-read (``populate_existing``): a deleted row is absent."""
    statement = select(Transaction).where(Transaction.id.in_(ids)).execution_options(populate_existing=True)
    return {row.id: (row.type, row.quantity, row.related_transaction_id, row.cost_basis_override, row.cost_basis_currency) for row in (await world.session.execute(statement)).scalars()}


def _answered(response: TXBatchResponse, operation: str, index: int) -> tuple[Decimal, str] | None:
    """The Auto cost the batch answered for row ``operation`` ``index`` (``wac_results``), or None."""
    for item in response.wac_results or []:
        if item.operation == operation and item.index == index and item.wac is not None:
            return item.wac.amount, item.wac.code
    return None


def _created_id(response: TXBatchResponse, index: int) -> int:
    """The id of create ``index``, from the batch's results."""
    return next(result.ids[0] for result in response.results if result.operation == "create" and result.index == index)


def _endpoint(commit: bool) -> str:
    return "/commit" if commit else "/validate"


def _verdict(response: TXBatchResponse, operation: str, index: int) -> str:
    """What a batch did, for a failure message: committed, and with which Auto cost on row ``operation`` ``index``;
    validated clean with it; or refused, and for what."""
    cost = _show(_answered(response, operation, index) or (None, None))
    if response.committed:
        return f"the batch committed, saving an Auto cost of {cost} on {operation} {index}"
    if not response.issues:
        return f"the batch validated clean, answering an Auto cost of {cost} on {operation} {index}, the cost /commit saves"
    return f"the batch was refused with [{_render(response.issues)}] (Auto cost answered on {operation} {index}: {cost})"


async def _assert_refused_unreadable(world: World, response: TXBatchResponse, batch: AutoBatch, *, count: int, pool: str, mode: str, today: str, commit: bool, brokers: list[int], before: dict[int, dict], ledger: tuple[int, int] | None) -> None:
    """(a)'s assertions: one issue ``autoCostUnreadable`` ``{"count": count}`` on the Auto row's operation and index,
    ``ref_id`` None, ``field`` ``cost_basis_override`` — so no id in its ``ref_id`` or its ``params`` —; not committed; no
    transaction id in its text either (the pool may be another user's broker: ``_ids_named``); and every row of
    ``brokers`` as it was, the planted 'n/a' included. ``pool`` says what the pool holds, ``today`` what today's average
    makes of it.

    ``ledger`` is W-B74's part: ``(broker id, N)`` when the batch replays a broker whose rows hold N quantities or amounts
    that read None — then exactly two issues, the second ``ledgerUnreadable`` ``{brokerId, count: N}`` at index -1 —, None
    when it replays none: exactly one issue. Checked after W-B69's part, so a red names the missing half."""
    auto = _unreadable_issue(batch.operation, batch.index, ref_id=None, count=count)
    views = [_issue_view(issue) for issue in response.issues]
    where = f"{batch.operation} {batch.index} ({mode}, {_endpoint(commit)})"
    on_the_row = [view for view in views if view["code"] == AUTO_COST_UNREADABLE]
    assert (response.committed, on_the_row) == (False, [auto]), f"W-B69: an Auto cost over a pool with {pool} must be refused with {AUTO_COST_UNREADABLE} {{count: {count}}} on {where}; today {_verdict(response, batch.operation, batch.index)} — {today}"
    _assert_with_the_ledger(response, [auto], ledger, where)
    named = _ids_named(next(issue for issue in response.issues if issue.code == AUTO_COST_UNREADABLE), set(before) | {tx_id for result in response.results for tx_id in result.ids})
    assert named == [], f"W-B69: the pool may be another user's broker, so {AUTO_COST_UNREADABLE} names no transaction; it names {named}: {_render(response.issues)}"
    changed = _changed(before, await _raw_rows(world, brokers))
    assert changed == {}, f"W-B69: the refused batch changed rows of the test's brokers (before, after): {changed}"


def _ledger_issue(broker_id: int, count: int) -> dict:
    """The broker-level issue of W-B74's cure, as ``_issue_view`` shows it."""
    return {"operation": "create", "index": -1, "ref_id": None, "code": LEDGER_UNREADABLE, "field": None, "params": {"brokerId": broker_id, "count": count}}


def _in_order(views: list[dict]) -> list[dict]:
    """Issue views in a fixed order — by code, operation, index —: the contract counts the issues, it does not order them."""
    return sorted(views, key=lambda view: (view["code"] or "", view["operation"], view["index"]))


def _assert_with_the_ledger(response: TXBatchResponse, expected: list[dict], ledger: tuple[int, int] | None, where: str) -> None:
    """W-B74's part of a W-B69 refusal: the issues are exactly ``expected``, plus ``ledgerUnreadable`` ``{brokerId, count}``
    when ``ledger`` names the replayed broker and its count — and nothing else."""
    views = [_issue_view(issue) for issue in response.issues]
    if ledger is None:
        message = f"W-B74: the replay of source reads no quantity or amount that reads None — a stored cost basis is read by no balance —, so the batch keeps exactly its {len(expected)} W-B69 issue(s) on {where}, and no {LEDGER_UNREADABLE}; it answers [{_render(response.issues)}]"
        assert _in_order(views) == _in_order(expected), message
        return
    broker_id, count = ledger
    assert _in_order(views) == _in_order([*expected, _ledger_issue(broker_id, count)]), (
        f"W-B74: the batch replays broker {broker_id} (source), whose rows hold {count} quantity or amount that reads None, so beside its W-B69 issue on {where} it must carry "
        f"{LEDGER_UNREADABLE} {{brokerId: {broker_id}, count: {count}}} at index -1 — exactly these {len(expected) + 1} issues; today it answers [{_render(response.issues)}]"
    )


async def _assert_takes(world: World, response: TXBatchResponse, batch: AutoBatch, *, cost: Decimal, commit: bool, what: str) -> None:
    """A guard's assertions: no issue, committed on /commit; the Auto row answered ``cost`` EUR; and /commit saved it."""
    assert (response.committed, response.issues) == (commit, []), f"{what} was refused ({_endpoint(commit)}): {_render(response.issues)}"
    assert _answered(response, batch.operation, batch.index) == (cost, EUR), f"{what}: expected an Auto cost of {cost} {EUR}; {_verdict(response, batch.operation, batch.index)}"
    if commit:
        row_id = batch.row_id if batch.row_id is not None else _created_id(response, batch.index)
        stored = await _stored_cost(world, row_id)
        assert stored == (cost, EUR), f"{what}: the Auto row id={row_id} was committed with {_show(stored)}, not {cost} {EUR}"


def _leg_shown(raw: dict | None) -> str:
    """A row as ``_raw_rows`` reads it, for a failure message."""
    if raw is None:
        return "gone"
    return f"{raw['type']} {raw['quantity']} with cost {raw['cost_basis_override']} {raw['cost_basis_currency']}, linked to {raw['related_transaction_id']}"


def _unreadable_issue(operation: str, index: int, *, ref_id: int | None, count: int) -> dict:
    """The issue of W-B69's cure, as ``_issue_view`` shows it."""
    return {"operation": operation, "index": index, "ref_id": ref_id, "code": AUTO_COST_UNREADABLE, "field": "cost_basis_override", "params": {"count": count}}


def _ids_named(issue: TXValidationIssue, ids: set[int]) -> list[int]:
    """The ids of ``ids`` from ``_ID_GAP`` on — the planted rows and every row written after them — that the text of
    ``issue`` names. Its ``ref_id`` and its ``params`` the caller pins whole; below the gap a number of the text may be the
    count, a day or an amount, so the rows written before the plant (the ``world``'s) are not looked for."""
    named = {int(number) for number in re.findall(r"\d+", issue.error)}
    return sorted(named & {tx_id for tx_id in ids if tx_id >= _ID_GAP})


class TestWB69AnAutoRowOverAnUnreadablePool:
    """W-B69 — cases (a), (d), the stored cost basis (the contract's addition of 17/10) and the count: an Auto row whose
    pool holds a row that reads None in its quantity, its amount or a cost basis it stores is refused on its own
    coordinates, and its batch saves nothing. Green since W-B69's cure, but where W-B74 adds its part: a batch replaying
    ``source`` while its rows hold a quantity or an amount that reads None also gets ``ledgerUnreadable`` — contract
    updates, RED until W-B74's cure.

    The Auto row is the receiving leg of a TRANSFER pair source → dest, at index 1 (``_auto_batch``): created, or stored at
    42 EUR and recomputed by an update that also gives both legs new notes. Either way its pool is ``source`` up to the
    move without the pair's two legs — the ``world``'s BUY and the planted row —, and the batch replays ``source`` (the
    giving leg's broker). Before W-B69's cure the batch committed (or validated) with the average of what reads: 100 EUR
    without the row of quantity 'n/a'; 50 with the BUY of amount 'n/a' taken as free, or with the row whose stored cost
    basis is 'n/a' taken at an unknown cost, entering at zero.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("mode", AUTO_MODES)
    @pytest.mark.parametrize("operation", AUTO_OPERATIONS)
    @pytest.mark.parametrize("column", UNREADABLE_COLUMNS)
    async def test_auto_row_over_a_pool_with_an_unreadable_row_is_refused(self, world, column, operation, mode, commit):
        """W-B69 (a) — and (d) with ``column`` amount: ``autoCostUnreadable`` on the Auto row's operation and index,
        ``ref_id`` None, ``field`` ``cost_basis_override``, ``params`` ``{"count": 1}``; not committed; no transaction id in
        the issue, its params or its text (the pool may be another user's broker); and every row of the test's brokers as
        it was, the planted 'n/a' included: refused, nothing repaired (``_assert_refused_unreadable``).

        Contract update for W-B74, RED until its cure: the batch replays ``source``, whose planted BUY's quantity or amount
        reads None, so the issues are exactly two — that one, and ``ledgerUnreadable`` ``{brokerId: source, count: 1}`` at
        index -1."""
        await _plant(world, unreadable=(column,))
        batch = await _auto_batch(world, operation, mode)
        source_id, brokers = world.source.id, await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=commit, creates=batch.creates, updates=batch.updates)

        pool = f"an unreadable row (a {PLANT_LABELS['buy']} of source whose {column} is 'n/a')"
        await _assert_refused_unreadable(world, response, batch, count=1, pool=pool, mode=mode, today=TODAY_OVER_AN_UNREADABLE[column], commit=commit, brokers=brokers, before=before, ledger=(source_id, 1))

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("operation", AUTO_OPERATIONS)
    @pytest.mark.parametrize("kind", INCOMING_KINDS)
    async def test_auto_row_over_a_pool_with_an_unreadable_stored_cost_basis_is_refused(self, world, kind, operation, commit):
        """W-B69, the contract's addition of 17/10: a pool row that stores a cost basis — ``cost_basis_override`` not NULL
        in SQL — which reads None is unreadable like a quantity or an amount. (a)'s assertions, ``{"count": 1}``.

        The row is an incoming one that takes a cost basis, dated before the move: an ADJUSTMENT +10, or a receiving
        TRANSFER +10 (its giving leg on a third broker of the test's), stored at 300 EUR a unit, then 'n/a'; its quantity
        and its amount read. Before W-B69's cure the average took it as an acquisition of unknown cost, entering at zero:
        the Auto row got 1 000 / 20 = 50 EUR, saved by /commit and answered by /validate. A BUY's NULL cost basis is
        legitimate and refuses nothing: the readable guards hold that.

        W-B74, a guard of its own (green before and after its cure): the batch replays ``source``, but no balance reads a
        cost basis — the replay counts quantities and amounts —, so the issue stays exactly one, no ``ledgerUnreadable``.
        """
        await _plant(world, kind=kind, unreadable=("cost_basis_override",))
        batch = await _auto_batch(world, operation, "auto")
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=commit, creates=batch.creates, updates=batch.updates)

        pool = f"an unreadable stored cost basis (a {PLANT_LABELS[kind]} on source, its cost_basis_override then 'n/a')"
        await _assert_refused_unreadable(world, response, batch, count=1, pool=pool, mode="auto", today=TODAY_OVER_AN_UNREADABLE["cost_basis_override"], commit=commit, brokers=brokers, before=before, ledger=None)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("plants", "count", "ledger", "today"),
        [
            pytest.param((("buy", ("quantity",)), ("buy", ("amount",))), 2, 2, "the average skips the first row and takes the second as a free acquisition: 1 000 / 20 = 50", id="two-rows"),
            pytest.param((("buy", ("quantity", "amount")),), 1, 1, "the average skips the row: 1 000 / 10 = 100", id="one-row-quantity-and-amount"),
            pytest.param((("adjustment", ("quantity", "cost_basis_override")),), 1, 1, "the average skips the row: 1 000 / 10 = 100", id="one-row-quantity-and-cost-basis"),
        ],
    )
    async def test_count_is_the_number_of_unreadable_rows(self, world, plants, count, ledger, today):
        """W-B69: ``count`` counts rows, not values. Two rows of the pool unreadable — a BUY by its quantity, the next day's
        BUY by its amount — give ``{"count": 2}``; one row unreadable in two columns gives ``{"count": 1}``: a BUY by its
        quantity and its amount, DERIVED from «the number of such rows», or an ADJUSTMENT +10 by its quantity and its stored
        cost basis, as the contract's addition of 17/10 says. (a)'s assertions, on the create of the pair on /commit. Before
        W-B69's cure the batch committed: at 50 EUR for the two rows (the first skipped, the second free: 1 000 / 20), at
        100 for the one (skipped: 1 000 / 10).

        Contract update for W-B74, RED until its cure: creating the pair replays ``source``, so beside that issue
        ``ledgerUnreadable`` ``{brokerId: source, count}`` at index -1 — ``count`` the rows whose quantity or amount reads
        None, the same rows here (2, 1, 1): the ADJUSTMENT's quantity reads None, its cost basis adds no row."""
        for offset, (kind, columns) in enumerate(plants):
            await _plant(world, kind=kind, unreadable=columns, day=LATER_BUY_DAY + timedelta(days=offset))
        batch = await _auto_batch(world, "create", "auto")
        source_id, brokers = world.source.id, await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=True, creates=batch.creates)

        shape = " and ".join(f"a {PLANT_LABELS[kind]} whose {' and '.join(columns)} read 'n/a'" for kind, columns in plants)
        await _assert_refused_unreadable(world, response, batch, count=count, pool=f"{len(plants)} unreadable row(s) — {shape}", mode="auto", today=today, commit=True, brokers=brokers, before=before, ledger=(source_id, ledger))

    @pytest.mark.asyncio
    async def test_unreadable_row_of_another_asset_is_refused_by_the_replay_alone(self, world):
        """Contract update for W-B74, RED until its cure — formerly the case ``another-asset-create`` of the guard
        ``test_unreadable_row_outside_the_pool_refuses_nothing``. A BUY of quantity 'n/a' of another asset on ``source`` lies
        outside the Auto row's pool, so W-B69 refuses nothing: no ``autoCostUnreadable``. But creating the pair replays
        ``source``, whose rows hold it: exactly one issue, ``ledgerUnreadable`` ``{brokerId: source, count: 1}`` at index
        -1; not committed, nothing saved. Today the batch commits, the Auto row at the ``world``'s BUY alone, 100 EUR."""
        await _plant(world, unreadable=("quantity",), asset_id=await _other_asset(world))
        batch = await _auto_batch(world, "create", "auto")
        source_id, brokers = world.source.id, await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=True, creates=batch.creates)

        views = [_issue_view(issue) for issue in response.issues]
        assert (response.committed, views) == (False, [_ledger_issue(source_id, 1)]), (
            f"W-B74: creating the pair replays source (broker {source_id}), whose rows hold a BUY of another asset whose quantity reads None: the batch must be refused by the replay alone — "
            f"exactly one issue, {LEDGER_UNREADABLE} {{brokerId: {source_id}, count: 1}} at index -1, and no {AUTO_COST_UNREADABLE}, the row lying outside the Auto row's pool; today {_verdict(response, batch.operation, batch.index)}"
        )
        changed = _changed(before, await _raw_rows(world, brokers))
        assert changed == {}, f"W-B74: the refused batch changed rows of the test's brokers (before, after): {changed}"


class TestWB69TheSplitOfATransferOverAnUnreadablePool:
    """W-B69 (b), as N78-1 changed it (the developer's decision, 21/10/2026): the split of a TRANSFER pair leaves its
    giving leg an ADJUSTMENT without a value, so it computes no Auto cost over ``source`` — and never refuses with
    ``autoCostUnreadable``. A pool with an unreadable row still refuses the split through W-B74 alone
    (``ledgerUnreadable``: the split replays ``source``). RED until N78-1. Before it the split handed the giving leg over at
    ``source``'s Auto cost (decision 47, ``_handover_cost``), refused with ``autoCostUnreadable`` over such a pool."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("column", UNREADABLE_COLUMNS)
    async def test_split_over_a_pool_with_an_unreadable_row_computes_no_auto_cost(self, world, column, commit):
        """RED until N78-1: no ``autoCostUnreadable`` on the split — the giving leg needs no cost —; the split replays the
        brokers of its legs — ``dest``, then ``source`` —, and ``source`` holds the BUY whose quantity or amount reads
        None: the one issue is W-B74's ``ledgerUnreadable`` ``{brokerId: source, count: 1}`` at index -1; not committed;
        the pair intact and every other row as it was.

        Before N78-1: ``autoCostUnreadable`` on split 1, ``ref_id`` the giving leg, ``params`` ``{"count": 1}``, beside
        ``ledgerUnreadable``."""
        await _plant(world, unreadable=(column,))
        sold, bought = await _fx_conversion_pair(world)
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving, receiving = stored.rows
        giving_id, source_id, brokers = giving.id, world.source.id, [world.source.id, world.dest.id]
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=commit, splits=[{"id_a": sold.id, "id_b": bought.id}, {"id_a": giving.id, "id_b": receiving.id}])

        after = await _raw_rows(world, brokers)
        on_the_split = [view for view in (_issue_view(issue) for issue in response.issues) if view["code"] == AUTO_COST_UNREADABLE]
        assert (response.committed, on_the_split) == (False, []), (
            f"N78-1: the split leaves the giving leg id={giving_id} without a value, so it computes no Auto cost over source (a BUY of source whose {column} is 'n/a') and never answers "
            f"{AUTO_COST_UNREADABLE}; W-B74 still refuses the replay ({_endpoint(commit)}); today the batch answers committed={response.committed}, issues [{_render(response.issues)}], "
            f"and leaves the giving leg {_leg_shown(after.get(giving_id))}"
        )
        _assert_with_the_ledger(response, [], (source_id, 1), f"split 1 ({_endpoint(commit)})")
        changed = _changed(before, after)
        assert changed == {}, f"W-B69: the refused split changed rows of source and dest (before, after): {changed}"

    @pytest.mark.asyncio
    async def test_split_over_a_readable_pool_leaves_the_giving_leg_without_a_value(self, world):
        """RED until N78-1: with the planted BUY readable the split commits; the giving leg leaves as an ADJUSTMENT −4
        without a value, and the receiving leg becomes an ADJUSTMENT +4 that keeps its 42 EUR.

        Before N78-1 (decision 47): the giving leg left at ``source``'s average, (1 000 + 3 000) / 20 = 200 EUR."""
        await _plant(world)
        stored = await _store(world, "transfer_in", cost=STORED_COST)
        giving_id, receiving_id = stored.rows[0].id, stored.rows[1].id

        response = await _as_the_endpoint(world, commit=True, splits=[{"id_a": giving_id, "id_b": receiving_id}])

        assert response.committed is True and response.issues == [], f"The split of a TRANSFER pair over a readable pool was refused: {_render(response.issues)}"
        assert await _rows_by_id(world, [giving_id, receiving_id]) == {
            giving_id: (TransactionType.ADJUSTMENT, -TRANSFER_QUANTITY, None, None, None),
            receiving_id: (TransactionType.ADJUSTMENT, TRANSFER_QUANTITY, None, STORED_COST.amount, STORED_COST.code),
        }, f"N78-1: the giving leg id={giving_id} leaves without a value, never at source's average ({READABLE_POOL_COST} EUR)"


class TestWB69GuardsReadablePoolsAndRowsOutsideThePool:
    """Guards, green before and after W-B69's and W-B74's cures: an Auto row over a readable pool takes its average, and an
    unreadable row the pool does not hold refuses nothing in a batch that replays ``dest`` alone. Under a batch that
    replays ``source`` the same row is W-B74's to refuse: ``test_unreadable_row_of_another_asset_is_refused_by_the_replay_alone``."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("mode", AUTO_MODES)
    @pytest.mark.parametrize("operation", AUTO_OPERATIONS)
    async def test_auto_row_over_a_readable_pool_takes_its_average(self, world, operation, mode, commit):
        """Guard: (a)'s batches with the planted BUY readable — its cost basis NULL, as a BUY's is: no issue, and the Auto
        row's cost is ``source``'s average, (1 000 + 3 000) / 20 = 200 EUR — answered on /validate, answered and saved on
        /commit."""
        await _plant(world)
        batch = await _auto_batch(world, operation, mode)

        response = await _as_the_endpoint(world, commit=commit, creates=batch.creates, updates=batch.updates)

        await _assert_takes(world, response, batch, cost=READABLE_POOL_COST, commit=commit, what=f"An Auto {operation} ({mode}) over a readable pool")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("operation", AUTO_OPERATIONS)
    @pytest.mark.parametrize("kind", INCOMING_KINDS)
    async def test_auto_row_over_a_readable_stored_cost_basis_takes_its_average(self, world, kind, operation, commit):
        """Guard: the stored-cost-basis case with the planted row readable — an ADJUSTMENT +10 or a receiving TRANSFER +10
        at 300 EUR a unit: no issue, and the Auto row's cost is ``source``'s average, (1 000 + 10 × 300) / 20 = 200 EUR —
        answered on /validate, answered and saved on /commit. A cure that counted every stored cost basis, not only one that
        reads None, turns it red."""
        await _plant(world, kind=kind)
        batch = await _auto_batch(world, operation, "auto")

        response = await _as_the_endpoint(world, commit=commit, creates=batch.creates, updates=batch.updates)

        await _assert_takes(world, response, batch, cost=READABLE_POOL_COST, commit=commit, what=f"An Auto {operation} over a pool holding a readable {PLANT_LABELS[kind]}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("where", "operation"),
        [
            pytest.param("another-asset", "update", id="another-asset-update"),
            pytest.param("after-the-move", "update", id="after-the-move-update"),
        ],
    )
    async def test_unreadable_row_outside_the_pool_refuses_nothing(self, world, where, operation):
        """Guard: a BUY of quantity 'n/a' on ``source`` that the pool does not hold — of another asset, or dated a week
        after the move, past the pool's date — refuses nothing: the batch commits, and the Auto row takes the ``world``'s
        BUY alone, 100 EUR.

        The update recomputes the receiving leg alone (index 0), so the batch replays ``dest`` alone, never ``source``,
        which holds the row: W-B74's replay refuses a broker holding such a row at every date. The case
        ``another-asset-create`` this guard had replays ``source``, and is now
        ``test_unreadable_row_of_another_asset_is_refused_by_the_replay_alone``.
        """
        if where == "another-asset":
            await _plant(world, unreadable=("quantity",), asset_id=await _other_asset(world))
        else:
            await _plant(world, unreadable=("quantity",), day=MOVE_DAY + timedelta(days=7))
        batch = await _auto_batch(world, operation, "auto", alone=operation == "update")

        response = await _as_the_endpoint(world, commit=True, creates=batch.creates, updates=batch.updates)

        await _assert_takes(world, response, batch, cost=UNIT_COST, commit=True, what=f"An Auto {operation} beside an unreadable row outside the pool ({where}), its average the world's BUY alone,")


class TestWB69TheCodeAndItsMessages:
    """W-B69's code, listed since its cure: ``autoCostUnreadable``. And the gate that holds every code to its message in
    the app's four languages, green before and after each cure that adds a code, since it reads the enum: W-B74's
    ``ledgerUnreadable`` (its own reds in test_transaction_service.py) joins it with its cure."""

    def test_tx_validation_code_has_auto_cost_unreadable(self):
        """RED until W-B69: ``TXValidationCode.AUTO_COST_UNREADABLE == "autoCostUnreadable"`` — the app maps a refusal's code
        to ``transactions.errors.<code>``."""
        member = getattr(TXValidationCode, "AUTO_COST_UNREADABLE", None)

        assert member is not None and member.value == AUTO_COST_UNREADABLE, f"W-B69: TXValidationCode.AUTO_COST_UNREADABLE is {member!r}: expected a member of value {AUTO_COST_UNREADABLE!r}"

    def test_transaction_types_lists_auto_cost_unreadable(self):
        """RED until W-B69: the response ``GET /transactions/types`` builds (``get_transaction_types``) lists
        ``autoCostUnreadable`` in ``validation_codes`` (``VALIDATION_CODE_METADATA``)."""
        response = TXTypesResponse(transaction_types=list(TX_TYPE_METADATA.values()), event_types=EVENT_TYPE_METADATA)

        listed = sorted(info.code for info in response.validation_codes)

        assert AUTO_COST_UNREADABLE in listed, f"W-B69: GET /transactions/types does not list {AUTO_COST_UNREADABLE!r} in validation_codes: {listed}"

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    def test_every_code_has_its_message_in_every_language(self, language):
        """Gate, green today and after W-B69: every ``TXValidationCode`` has a non-empty ``transactions.errors.<code>`` in
        ``language``, read without the English fallback (``load_catalog(language, fallback=False)``). A code without one is
        a refusal the app cannot put in the user's words."""
        messages = flatten(load_catalog(language, fallback=False))

        missing = [code.value for code in TXValidationCode if not str(messages.get(f"transactions.errors.{code.value}") or "").strip()]

        assert missing == [], f"transactions.errors has no {language} message for {missing}"


# ============================================================================
# RED AND GUARDS — N78 (W-B72): A COST BASIS ON A TYPE AND SIDE THAT TAKE NONE
# ============================================================================

# The cure's code, as a literal: no rule answers it before N78.
COST_BASIS_NOT_ALLOWED = "costBasisNotAllowed"
# Rule 12's code, which speaks alone when the request names a mode.
COST_BASIS_MODE_INCOMPATIBLE = "costBasisModeIncompatible"
# N78's two messages: its new code's, and the one rule 12 has answered without a message until now.
N78_CODES = (COST_BASIS_NOT_ALLOWED, COST_BASIS_MODE_INCOMPATIBLE)
# What the other leg of a pair gets when a refusal at the parse leaves it alone in its link_uuid.
LINK_UUID_PAIR_COUNT = TXValidationCode.LINK_UUID_PAIR_COUNT.value
# The creates N78 refuses (_n78_refused_create), each at index 1 behind a row valid on its own. The giving side of an
# ADJUSTMENT has its own class since N78-1 (TestN78ACostBasisOnTheGivingSideOfAnAdjustment): refused too.
N78_CREATE_CASES = ("buy", "fx-conversion-leg")
N78_MODES = ("auto", "manual")
# The form's currency hint: the cost_basis_override it sends beside cost_basis_mode "auto", of which the batch reads the
# code alone (auto_cost.py); its amount is no average, so the Auto cost cannot be mistaken for it.
CURRENCY_HINT = {"code": EUR, "amount": "1"}
# The schema whose PydanticCustomError literals are the business-rule codes, and the wrapper _parse_lenient unpacks
# into the codes it packs: never shown, so it needs no message.
BUSINESS_RULES_SOURCE = Path(transaction_schemas.__file__)
BUSINESS_RULES_WRAPPER = "multipleBusinessRuleErrors"


def _cost_sent(cost: Currency = STORED_COST) -> dict:
    """A cost basis as a payload carries it: ``{"code", "amount"}``, the amount a string."""
    return {"code": cost.code, "amount": str(cost.amount)}


def _braced(params: dict) -> str:
    """Params as a message names them: ``{type: BUY, qty: 5}``."""
    return "{" + ", ".join(f"{key}: {value}" for key, value in params.items()) + "}"


def _type_and_qty(params: dict | None) -> tuple | dict | None:
    """N78's params ``{type, qty}`` as ``(type, quantity)``, the quantity read as a number: a stored row's quantity may print
    3 or 3.000000. Anything else as it is, for the message."""
    if isinstance(params, dict) and set(params) == {"type", "qty"}:
        try:
            return params["type"], Decimal(str(params["qty"]))
        except InvalidOperation:
            return params
    return params


def _n78_description(world: World) -> str:
    """The description of every row an N78 batch creates: what finds them again, or proves them absent."""
    return f"{world.marker} N78 batch"


async def _n78_batch_rows(world: World) -> list[int]:
    """The ids of the rows N78's batches sent that the database holds."""
    statement = select(Transaction.id).where(Transaction.description == _n78_description(world)).order_by(Transaction.id)
    return list((await world.session.execute(statement)).scalars())


async def _n78_as_the_endpoint(world: World, *, creates: list[dict] | None = None, updates: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` runs it, its transaction included — ``_commit_as_the_endpoint``, creates
    included: kept when the service answers committed, rolled back otherwise. Read the rows back by id afterwards
    (``_stored_cost``), never through a copy the rollback expired."""
    savepoint = await world.session.begin_nested()
    response = await _run_batch(world, commit=True, creates=creates, updates=updates)
    if response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


def _n78_issues(response: TXBatchResponse) -> list[TXValidationIssue]:
    """Every ``costBasisNotAllowed`` issue of the batch."""
    return [issue for issue in response.issues if issue.code == COST_BASIS_NOT_ALLOWED]


async def _n78_today(world: World, response: TXBatchResponse, operation: str, index: int) -> str:
    """What the batch did with row ``operation`` ``index``, for a red's message: committed, and the cost basis each of its
    rows now stores; or refused, and with what."""
    if not response.committed:
        return f"the batch was refused with [{_render(response.issues)}], none a {COST_BASIS_NOT_ALLOWED} on {operation} {index}"
    ids = next((result.ids for result in response.results if result.operation == operation and result.index == index), [])
    stored = []
    for tx_id in ids:
        stored.append(f"id={tx_id} holding {_show(await _stored_cost(world, tx_id))}")
    return f"the batch committed it with that cost basis stored: {operation} {index} is {', '.join(stored) or 'no row'}"


@dataclass
class N78Create:
    """A batch of creates whose row ``index`` carries a cost basis, without a mode, on a type and side that take none."""

    label: str
    creates: list[dict]
    index: int
    #: The params of its refusal: ``{"type": <type>, "qty": str(quantity)}``, the quantity as the payload parses.
    params: dict
    #: The other leg of its pair, left alone in its ``link_uuid`` once the row is refused at the parse; None outside a pair.
    partner_index: int | None = None


def _n78_refused_create(world: World, case: str) -> N78Create:
    """The create ``case`` names, at index 1 behind a row valid on its own — a DEPOSIT of 500 EUR on ``dest``, or the EUR leg
    of its FX_CONVERSION pair — so that the index of its refusal is its own, not a default.

    ``buy``: a BUY +5 on ``dest`` paying 500 EUR (``dest`` allows a cash overdraft). ``fx-conversion-leg``: the USD leg
    (+110) of an FX_CONVERSION pair on ``dest`` selling 100 EUR, its quantity left out (0). Each carries 42 EUR
    (``STORED_COST``) and no ``cost_basis_mode``, and is valid in every other respect: only its cost basis can refuse it.
    """
    day = MOVE_DAY.isoformat()
    description = _n78_description(world)
    deposit = {"broker_id": world.dest.id, "type": "DEPOSIT", "date": day, "cash": {"code": EUR, "amount": "500"}, "description": description}
    if case == "buy":
        buy = {"broker_id": world.dest.id, "asset_id": world.asset.id, "type": "BUY", "date": day, "quantity": "5", "cash": {"code": EUR, "amount": "-500"}, "cost_basis_override": _cost_sent(), "description": description}
        return N78Create(label="a BUY +5", creates=[deposit, buy], index=1, params={"type": "BUY", "qty": "5"})
    if case == "fx-conversion-leg":
        link_uuid = str(uuid.uuid4())
        sold = {"broker_id": world.dest.id, "type": "FX_CONVERSION", "date": day, "cash": {"code": EUR, "amount": "-100"}, "link_uuid": link_uuid, "description": description}
        bought = {"broker_id": world.dest.id, "type": "FX_CONVERSION", "date": day, "cash": {"code": "USD", "amount": "110"}, "link_uuid": link_uuid, "cost_basis_override": _cost_sent(), "description": description}
        return N78Create(label="the USD leg (+110) of an FX_CONVERSION pair", creates=[sold, bought], index=1, params={"type": "FX_CONVERSION", "qty": "0"}, partner_index=0)
    raise ValueError(f"unknown N78 create case {case!r}")


def _called_name(func: ast.expr) -> str | None:
    """The name a call calls: ``PydanticCustomError`` for ``PydanticCustomError(...)`` and ``module.PydanticCustomError(...)``."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _business_rule_codes() -> list[str]:
    """Every business-rule code of ``schemas/transactions/transactions.py``: the literal first argument of each
    ``PydanticCustomError`` it builds, but the wrapper ``multipleBusinessRuleErrors``.

    Read from the source's syntax tree, so a code a cure adds joins the gate by itself. A code passed by name instead of as
    a literal would escape it, which is checked; and so are codes every version has, so a parse that finds nothing cannot
    pass the gate.
    """
    tree = ast.parse(BUSINESS_RULES_SOURCE.read_text(encoding="utf-8"))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and _called_name(node.func) == "PydanticCustomError"]
    by_name = [node.lineno for node in calls if not (node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str))]
    assert by_name == [], f"scaffold: the gate reads each code as the literal first argument of PydanticCustomError; the calls at lines {by_name} of {BUSINESS_RULES_SOURCE.name} pass it otherwise, and escape the gate"
    codes = sorted({node.args[0].value for node in calls} - {BUSINESS_RULES_WRAPPER})
    assert {"qtyPositive", "cashRequired", COST_BASIS_MODE_INCOMPATIBLE} <= set(codes), f"scaffold: the business-rule codes read from {BUSINESS_RULES_SOURCE.name} miss codes every version has: {codes}"
    return codes


def _error_text(messages: dict, code: str) -> str:
    """The text of ``transactions.errors.<code>`` in a flattened catalogue, stripped; empty when it has none."""
    return str(messages.get(f"transactions.errors.{code}") or "").strip()


class TestN78ACostBasisWhereNoneIsTaken:
    """RED until N78 (W-B72): a ``cost_basis_override`` sent without a ``cost_basis_mode`` on a type and side that take none
    (``cost_basis_allowed`` False) is refused with ``costBasisNotAllowed`` ``{type, qty}`` — the giving side of an
    ADJUSTMENT too since N78-1, in its own class (``TestN78ACostBasisOnTheGivingSideOfAnAdjustment``).

    Today rule 12 reads only ``cost_basis_mode``: the batch commits the row with its cost basis stored — noise the math
    ignores on a row of quantity 0, but that the list, the export and the backup carry. Each test runs the batch as
    ``POST /transactions/commit`` does, its transaction included (``_n78_as_the_endpoint``), and reads the rows back.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", N78_CREATE_CASES)
    async def test_create_with_a_cost_basis_where_none_is_taken_is_refused_at_the_parse(self, world, case):
        """RED until N78: one ``costBasisNotAllowed`` on create 1, ``params`` ``{type, qty}`` — ``qty`` the quantity as
        parsed — the way the batch reports rule 12's codes; refused at the parse, so create 1 has no result; nothing else
        refuses the batch, but for the pair the other leg left alone in its ``link_uuid`` (``linkUuidPairCount``, accepted,
        not required); not committed, nothing it sent stored."""
        batch = _n78_refused_create(world, case)
        subject = batch.creates[batch.index]
        side = (TransactionType(subject["type"]), Decimal(subject.get("quantity", "0")))
        assert "cost_basis_mode" not in subject and not cost_basis_allowed(*side), f"precondition broken: {batch.label} must carry no cost_basis_mode, on a type and side that take no cost basis; cost_basis_allowed{side} = {cost_basis_allowed(*side)}"
        assert not (side[0] == TransactionType.ADJUSTMENT and side[1] < 0), f"scaffold: {batch.label} is the giving side of an ADJUSTMENT, whose class is TestN78ACostBasisOnTheGivingSideOfAnAdjustment"

        response = await _n78_as_the_endpoint(world, creates=batch.creates)

        refusal = f"{COST_BASIS_NOT_ALLOWED} {_braced(batch.params)} on create {batch.index}"
        on_the_row = [issue for issue in _n78_issues(response) if (issue.operation, issue.index) == ("create", batch.index)]
        if not on_the_row:
            pytest.fail(f"N78 (W-B72): {batch.label} created with a cost basis and no mode must be refused with {refusal}; today {await _n78_today(world, response, 'create', batch.index)}")
        assert [(issue.operation, issue.index) for issue in _n78_issues(response)] == [("create", batch.index)], f"N78: exactly one {refusal}, and none elsewhere: {_render(response.issues)}"
        assert on_the_row[0].params == batch.params, (
            f"N78: the {COST_BASIS_NOT_ALLOWED} of create {batch.index} must carry params {batch.params}, as rule 12's issues do; it carries {on_the_row[0].params!r}. "
            "_parse_lenient keeps the ctx of a business-rule error only when several are packed (multipleBusinessRuleErrors): a lone one gets params None"
        )
        assert response.committed is False, f"N78: the batch was refused, yet answered committed: {response.results}"
        assert ("create", batch.index) not in {(result.operation, result.index) for result in response.results}, f"N78: refused at the parse, create {batch.index} never reaches apply_creates, so it has no result: {response.results}"
        consequences = {("create", batch.partner_index, LINK_UUID_PAIR_COUNT)} if batch.partner_index is not None else set()
        others = [issue for issue in response.issues if issue.code != COST_BASIS_NOT_ALLOWED and (issue.operation, issue.index, issue.code) not in consequences]
        assert others == [], f"N78: only the cost basis may refuse this batch: {_render(others)}"
        assert await _n78_batch_rows(world) == [], "N78: the batch was refused, yet rows it sent are stored"

    @pytest.mark.asyncio
    async def test_update_setting_a_cost_basis_on_a_stored_buy_is_refused(self, world):
        """RED until N78: ``{id, cost_basis_override: 42 EUR}`` on a stored BUY +3 gets one ``costBasisNotAllowed`` on
        update 0, ``ref_id`` the BUY, ``params`` ``{type: BUY, qty: 3}`` (the quantity compared as a number), and nothing
        else; not committed, and the BUY still holds no cost basis. Today the update commits and the BUY holds 42 EUR."""
        buy = _stored_row(world, broker=world.dest, tx_type=TransactionType.BUY, quantity=Decimal("3"), amount=Decimal("-300"), currency=EUR)
        world.session.add(buy)
        await world.session.flush()
        buy_id = buy.id
        assert not cost_basis_allowed(TransactionType.BUY, Decimal("3")), "precondition broken: TX_TYPE_METADATA must refuse a cost basis on a BUY"
        assert await _stored_cost(world, buy_id) == (None, None), f"scaffold: the BUY id={buy_id} must be stored without a cost basis"

        response = await _n78_as_the_endpoint(world, updates=[{"id": buy_id, "cost_basis_override": _cost_sent()}])

        refusal = f"{COST_BASIS_NOT_ALLOWED} {{type: BUY, qty: 3}} on update 0"
        found = _n78_issues(response)
        if not found:
            pytest.fail(f"N78 (W-B72): an update setting a cost basis of {STORED_COST.amount} {STORED_COST.code} on the stored BUY +3 id={buy_id} must be refused with {refusal}; today {await _n78_today(world, response, 'update', 0)}")
        assert [(issue.operation, issue.index, issue.ref_id, _type_and_qty(issue.params)) for issue in found] == [("update", 0, buy_id, ("BUY", Decimal("3")))], f"N78: expected exactly one {refusal}, ref_id {buy_id}: {_render(found)}"
        assert response.committed is False, f"N78: the update was refused, yet the batch answered committed: {response.results}"
        assert [issue for issue in response.issues if issue.code != COST_BASIS_NOT_ALLOWED] == [], f"N78: only the cost basis may refuse this update: {_render(response.issues)}"
        stored_after = await _stored_cost(world, buy_id)
        assert stored_after == (None, None), f"N78: the update was refused, yet the BUY id={buy_id} holds {_show(stored_after)}"


class TestN78GuardsWhereACostBasisIsTaken:
    """Guards, green today and after N78: where ``cost_basis_allowed`` lets a cost basis in — a TRANSFER's receiving leg, an
    ADJUSTMENT adding quantity — a manual one commits, and an Auto row sending the form's currency hint commits with its
    Auto cost. A cure that judged a cost basis by its presence instead of by the type and side would turn them red."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", [None, "manual"], ids=["no-mode", "manual"])
    async def test_adjustment_in_with_a_manual_cost_basis_commits(self, world, mode):
        """Guard: an ADJUSTMENT +5 on ``dest`` at 42 EUR — without a mode, as the form sends a manual cost, or in ``manual``
        — commits, and holds 42 EUR."""
        created = {**_created_adjustment(world, broker=world.dest, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode=mode), "cost_basis_override": _cost_sent()}

        response = await _n78_as_the_endpoint(world, creates=[created])

        assert response.committed is True and response.issues == [], f"An ADJUSTMENT +{ADJUSTMENT_QUANTITY} with a manual cost basis (mode {mode}) was refused: {_render(response.issues)}"
        stored = await _stored_cost(world, _created_id(response, 0))
        assert stored == (STORED_COST.amount, STORED_COST.code), f"The ADJUSTMENT +{ADJUSTMENT_QUANTITY} was committed with {_show(stored)}, not the {STORED_COST.amount} {STORED_COST.code} it was sent with"

    @pytest.mark.asyncio
    async def test_received_transfer_with_a_manual_cost_basis_commits(self, world):
        """Guard: a TRANSFER pair source → dest whose receiving leg (index 1) carries 42 EUR without a mode commits; the
        receiving leg holds 42 EUR, the giving leg none."""
        giving, receiving = _created_pair(world)
        receiving["cost_basis_override"] = _cost_sent()

        response = await _n78_as_the_endpoint(world, creates=[giving, receiving])

        assert response.committed is True and response.issues == [], f"A TRANSFER pair whose receiving leg carries a manual cost basis was refused: {_render(response.issues)}"
        legs = {"giving": await _stored_cost(world, _created_id(response, 0)), "receiving": await _stored_cost(world, _created_id(response, 1))}
        assert legs == {"giving": (None, None), "receiving": (STORED_COST.amount, STORED_COST.code)}, f"The TRANSFER pair was committed with the cost bases {legs}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    async def test_auto_with_a_currency_hint_commits_with_its_auto_cost(self, world, shape):
        """Guard: an Auto row — ``cost_basis_mode`` ``auto`` and ``cost_basis_override`` the currency hint ``{EUR, 1}``, as the
        form's create payload sends it (``txPayloadHelpers.ts``) — on a TRANSFER's receiving leg or an ADJUSTMENT +5 on
        ``source`` commits, and holds its Auto cost, ``source``'s average, 100 EUR: not the hint's amount."""
        if shape == "transfer_in":
            creates, subject_index = _created_pair(world, cost_basis_mode="auto"), 1
        else:
            creates, subject_index = [_created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")], 0
        creates[subject_index]["cost_basis_override"] = dict(CURRENCY_HINT)

        response = await _n78_as_the_endpoint(world, creates=creates)

        assert response.committed is True and response.issues == [], f"An Auto {SHAPE_LABELS[shape]} sending a currency hint was refused: {_render(response.issues)}"
        stored = await _stored_cost(world, _created_id(response, subject_index))
        assert stored == (UNIT_COST, EUR), f"Auto cost of the {SHAPE_LABELS[shape]}: expected {UNIT_COST} {EUR}, the average of source's BUY; it holds {_show(stored)} (wac_results={response.wac_results})"


class TestN78ACostBasisOnTheGivingSideOfAnAdjustment:
    """N78-1 (the developer's decision, 21/10/2026), RED until its cure: an ADJUSTMENT with a quantity below 0 has no value,
    so rule 12b loses its exception — a cost basis the request sets on it, without a mode, is refused with
    ``costBasisNotAllowed`` ``{type, qty}``, as on every type and side ``cost_basis_allowed`` refuses (with a mode, rule 12's
    ``costBasisModeIncompatible`` speaks already). An update that does not send a cost on an old row storing one stays
    valid: ``TestN78GuardsStrayCostsAndNulls``, unchanged.

    Before N78-1 these were guards of the refined N78 (the coordinator's (a), 17/10): the stored cost was decision 47's
    handover cost, and both requests committed and held 42 EUR. Each test checks first that the table does refuse the side.
    """

    @pytest.mark.asyncio
    async def test_create_of_an_adjustment_out_with_a_cost_basis_is_refused_at_the_parse(self, world):
        """RED until N78-1: an ADJUSTMENT −5 on ``source`` — which holds the ``world``'s 10 units, so it does not go short —
        created with 42 EUR and no mode gets one ``costBasisNotAllowed`` on create 0, ``params`` ``{type: ADJUSTMENT,
        qty: -5}`` (the quantity compared as a number), and nothing else; refused at the parse, so create 0 has no result;
        not committed, nothing it sent stored. Before N78-1 it committed and held 42 EUR."""
        assert not cost_basis_allowed(TransactionType.ADJUSTMENT, -ADJUSTMENT_QUANTITY), "precondition broken: TX_TYPE_METADATA must refuse a cost basis on an ADJUSTMENT's giving side"
        created = {**_created_adjustment(world, broker=world.source, quantity=-ADJUSTMENT_QUANTITY), "cost_basis_override": _cost_sent(), "description": _n78_description(world)}

        response = await _n78_as_the_endpoint(world, creates=[created])

        refusal = f"{COST_BASIS_NOT_ALLOWED} {{type: ADJUSTMENT, qty: -{ADJUSTMENT_QUANTITY}}} on create 0"
        found = [(issue.operation, issue.index, _type_and_qty(issue.params)) for issue in response.issues]
        today = await _n78_today(world, response, "create", 0)
        what = f"an ADJUSTMENT -{ADJUSTMENT_QUANTITY} created with a cost basis of {STORED_COST.amount} {STORED_COST.code} and no mode"
        assert found == [("create", 0, ("ADJUSTMENT", -ADJUSTMENT_QUANTITY))] and all(issue.code == COST_BASIS_NOT_ALLOWED for issue in response.issues), f"N78-1: {what} has no value, so it must be refused with exactly {refusal}; today {today}"
        assert response.committed is False, f"N78-1: the create was refused, yet the batch answered committed: {response.results}"
        assert ("create", 0) not in {(result.operation, result.index) for result in response.results}, f"N78-1: refused at the parse, create 0 has no result: {response.results}"
        assert await _n78_batch_rows(world) == [], "N78-1: the batch was refused, yet the row it sent is stored"

    @pytest.mark.asyncio
    async def test_update_setting_a_cost_basis_on_a_stored_adjustment_out_is_refused(self, world):
        """RED until N78-1: ``{id, cost_basis_override: 42 EUR}``, no mode, on an ADJUSTMENT −4 stored on ``source`` without
        a cost gets one ``costBasisNotAllowed`` on update 0, ``ref_id`` the row, ``params`` ``{type: ADJUSTMENT, qty: -4}``,
        and nothing else; not committed, and the row still holds no cost basis. Before N78-1 it committed and held 42 EUR
        (decision 4's update of a giving leg)."""
        row = _stored_row(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=-TRANSFER_QUANTITY)
        world.session.add(row)
        await world.session.flush()
        row_id = row.id
        assert not cost_basis_allowed(TransactionType.ADJUSTMENT, -TRANSFER_QUANTITY), "precondition broken: TX_TYPE_METADATA must refuse a cost basis on an ADJUSTMENT's giving side"
        assert await _stored_cost(world, row_id) == (None, None), f"scaffold: the ADJUSTMENT -{TRANSFER_QUANTITY} id={row_id} must be stored without a cost basis"

        response = await _n78_as_the_endpoint(world, updates=[{"id": row_id, "cost_basis_override": _cost_sent()}])

        refusal = f"{COST_BASIS_NOT_ALLOWED} {{type: ADJUSTMENT, qty: -{TRANSFER_QUANTITY}}} on update 0"
        found = [(issue.operation, issue.index, issue.ref_id, issue.code, _type_and_qty(issue.params)) for issue in response.issues]
        today = await _n78_today(world, response, "update", 0)
        expected = [("update", 0, row_id, COST_BASIS_NOT_ALLOWED, ("ADJUSTMENT", -TRANSFER_QUANTITY))]
        assert found == expected, f"N78-1: a cost basis set with no mode on the ADJUSTMENT -{TRANSFER_QUANTITY} id={row_id} must be refused with exactly {refusal}, ref_id {row_id}; today {today}"
        assert response.committed is False, f"N78-1: the update was refused, yet the batch answered committed: {response.results}"
        stored = await _stored_cost(world, row_id)
        assert stored == (None, None), f"N78-1: the update was refused, yet the ADJUSTMENT -{TRANSFER_QUANTITY} id={row_id} holds {_show(stored)}"


class TestN78GuardsStrayCostsAndNulls:
    """Guards, green today and after N78: what N78 leaves alone. A row stored with a stray cost basis — as an older version,
    an API client or decision 47's handover left it — stays editable and keeps it; an explicit null, clearing, is never
    refused."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", LEGACY_SHAPES)
    async def test_notes_edit_of_a_row_with_a_stray_cost_basis_commits_and_keeps_it(self, world, shape):
        """Guard: a notes-only edit — the cost key left out — of a BUY +3 or an ADJUSTMENT −4 stored with a cost basis of
        42 EUR although its type and side take none (planted through the ORM, ``_legacy_row_with_cost``) commits; the notes
        land and the stray cost basis stays. N78 judges a cost basis the request sets, never one the row stores."""
        row = await _legacy_row_with_cost(world, shape)
        row_id = row.id
        side = (row.type, row.quantity)
        assert not cost_basis_allowed(*side), f"precondition broken: a {LEGACY_LABELS[shape]} must take no cost basis; cost_basis_allowed{side} = True"
        notes = f"{world.marker} notes edited"

        response = await _n78_as_the_endpoint(world, updates=[{"id": row_id, "description": notes}])

        assert response.committed is True and response.issues == [], f"N78: a notes-only edit of a {LEGACY_LABELS[shape]} stored with a stray cost basis sets no cost basis, so it must commit; it was refused: {_render(response.issues)}"
        stored = await _stored_cost(world, row_id)
        assert stored == (STORED_COST.amount, STORED_COST.code), f"N78: rows stored with a stray cost basis are kept, yet after a notes-only edit the {LEGACY_LABELS[shape]} id={row_id} holds {_show(stored)} instead of {STORED_COST.amount} {STORED_COST.code}"
        description = (await world.session.execute(select(Transaction.description).where(Transaction.id == row_id))).scalar_one()
        assert description == notes, f"Committed, but the notes of id={row_id} read {description!r}"

    @pytest.mark.asyncio
    async def test_create_with_an_explicit_null_cost_basis_commits(self, world):
        """Guard: a BUY +5 created with ``cost_basis_override: null`` — sent, and null — commits without a cost basis: a null
        sets nothing. The update that sends the null on a row with a stray cost basis is decision P5's guard
        (``test_a_null_where_no_cost_is_taken_is_ignored``); a promote resolving it on a cash pair is
        ``test_transaction_decimal_places.py``'s."""
        buy = {"broker_id": world.dest.id, "asset_id": world.asset.id, "type": "BUY", "date": MOVE_DAY.isoformat(), "quantity": "5", "cash": {"code": EUR, "amount": "-500"}, "cost_basis_override": None, "description": _n78_description(world)}
        assert "cost_basis_override" in transaction_schemas.TXCreateItem.model_validate(buy).model_fields_set, "scaffold: the create must SEND cost_basis_override (an explicit null), or this is the case of a key left out"

        response = await _n78_as_the_endpoint(world, creates=[buy])

        assert response.committed is True and response.issues == [], f"N78: an explicit null cost basis sets none, so a BUY sending it must commit; it was refused: {_render(response.issues)}"
        stored = await _stored_cost(world, _created_id(response, 0))
        assert stored == (None, None), f"The BUY sent with a null cost basis was committed with {_show(stored)}"


class TestN78AModeLetsRule12SpeakAlone:
    """Where the request names a mode, rule 12 speaks alone (N78: no double issue) — with its params since the
    coordinator's approval of 17/10: a LONE model-level business-rule error keeps its context as ``params`` in
    ``_parse_lenient``. The one issue is a guard, green today; its params are RED until that lone-params cure: today
    ``_parse_lenient`` keeps the ``ctx`` of a business-rule error only when ``multipleBusinessRuleErrors`` packs several, so
    a lone one reaches the app with ``params`` None, and its message without the type it names."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", N78_MODES)
    async def test_a_cost_basis_with_a_mode_where_none_is_taken_gets_rule_12s_issue_alone(self, world, mode):
        """RED until the lone-params cure (its params), a guard for the rest: a BUY +5 sent with a cost basis AND
        ``cost_basis_mode`` ``auto`` or ``manual`` is refused by rule 12 alone — one issue, ``costBasisModeIncompatible`` on
        create 0, no ``costBasisNotAllowed`` beside it, green today — and that lone issue carries ``params``
        ``{type: BUY, qty: 5}``, the quantity compared as a number: today None."""
        buy = {"broker_id": world.dest.id, "asset_id": world.asset.id, "type": "BUY", "date": MOVE_DAY.isoformat(), "quantity": "5", "cash": {"code": EUR, "amount": "-500"}, "cost_basis_override": _cost_sent(), "cost_basis_mode": mode, "description": _n78_description(world)}

        response = await _n78_as_the_endpoint(world, creates=[buy])

        assert response.committed is False, f"A BUY sent with cost_basis_mode={mode} was committed: {response.results}"
        assert [(issue.operation, issue.index, issue.code) for issue in response.issues] == [("create", 0, COST_BASIS_MODE_INCOMPATIBLE)], f"N78: with a mode, rule 12's {COST_BASIS_MODE_INCOMPATIBLE} speaks alone, no {COST_BASIS_NOT_ALLOWED} beside it: {_render(response.issues)}"
        params = response.issues[0].params
        assert _type_and_qty(params) == ("BUY", Decimal("5")), (
            f"N78 (W-B72), lone params: the lone {COST_BASIS_MODE_INCOMPATIBLE} of create 0 must carry params {{type: BUY, qty: 5}}, the context rule 12 gives it; today it carries {params!r}. "
            "_parse_lenient keeps the ctx of a business-rule error only when several are packed (multipleBusinessRuleErrors): a lone one gets params None"
        )


class TestN78TheMessages:
    """RED until N78: the messages of its two codes, and the gate that holds every business-rule code to its message.

    ``costBasisModeIncompatible`` is today the one business-rule code without a ``transactions.errors.<code>``, in any
    language, so the app shows the backend's raw English (``resolveIssueMessage``'s fallback); ``costBasisNotAllowed`` is
    new. Read without the English fallback (``load_catalog(language, fallback=False)``): what the sources translate.
    """

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    @pytest.mark.parametrize("code", N78_CODES)
    def test_n78_codes_have_their_message(self, code, language):
        """RED until N78: ``transactions.errors.<code>`` is a non-empty text in ``language``."""
        messages = flatten(load_catalog(language, fallback=False))

        assert _error_text(messages, code), f"N78 (W-B72): transactions.errors.{code} has no {language} message, so the app shows the backend's raw English"

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    def test_every_business_rule_code_has_its_message(self, language):
        """RED until N78 (``costBasisModeIncompatible``), then a gate: every business-rule code of
        ``schemas/transactions/transactions.py`` (``_business_rule_codes``) has a non-empty ``transactions.errors.<code>``
        in ``language``; a code a cure adds joins the gate by itself."""
        codes = _business_rule_codes()
        messages = flatten(load_catalog(language, fallback=False))

        missing = [code for code in codes if not _error_text(messages, code)]

        assert missing == [], f"N78 (W-B72): every business-rule code of {BUSINESS_RULES_SOURCE.name} needs transactions.errors.<code> in {language}; none for {missing} (of {len(codes)} codes)"


# ============================================================================
# RED AND GUARDS — W-B67: AN AUTO COST WRITTEN ON THE WRONG ROW OF A BATCH
# ============================================================================

# The manual cost basis, per unit, of W-B67's Manual row: neither the world's average (100) nor any Auto cost below.
WB67_MANUAL_COST = Currency(code=EUR, amount=Decimal("50"))
# What the world's BUY paid for its 10 units: the start of every pool below.
WORLD_PAID = BUY_QUANTITY * UNIT_COST
# The date-order case: three days after the world's BUY, D < D+1 < D+2, and the BUY of D+1, 5 units for 2 000 EUR (400 a unit).
WB67_D = MOVE_DAY
WB67_D_PLUS_1 = MOVE_DAY + timedelta(days=1)
WB67_D_PLUS_2 = MOVE_DAY + timedelta(days=2)
WB67_BUY_PAID = Decimal("-2000")


def _average(paid: Decimal, quantity: Decimal) -> Decimal:
    """An average cost as the batch stores it: the quotient, rounded to what ``cost_basis_override`` keeps
    (``round_computed_value``, as ``compute_wac_iterative`` rounds the average it answers)."""
    return round_computed_value(paid / quantity, Transaction, "cost_basis_override")


def _wb67_cost(cost: tuple | None) -> str:
    """A stored cost basis or an answered Auto cost, ``(amount, code)``, for a message: ``100 EUR``, or ``none``."""
    if cost is None or cost == (None, None):
        return "none"
    amount, code = cost
    return f"{amount.normalize():f} {code}"


def _wb67_answers(response: TXBatchResponse) -> list[tuple]:
    """``wac_results`` in its order, each item as ``(operation, index, (amount, code))`` — ``(operation, index, None)`` for
    an item without a cost, a split-linked Auto row's."""
    return [(item.operation, item.index, None if item.wac is None else (item.wac.amount, item.wac.code)) for item in response.wac_results or []]


@dataclass
class WB67Outcome:
    """What a W-B67 batch left once the request is over (``_wb67_outcome``)."""

    #: The cost basis each create named stores, by its index, read back by id: ``(amount, code)``, ``(None, None)`` without one.
    costs: dict[int, tuple]
    #: ``wac_results`` in its order (``_wb67_answers``).
    answers: list[tuple]
    #: Both as a sentence, for a failure message: which row holds what, and what ``wac_results`` said.
    today: str


async def _wb67_commit(world: World, creates: list[dict]) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` runs it, its transaction included (``_n78_as_the_endpoint``). Every W-B67
    batch is valid, today and after the cure, so it must commit: a refusal is not the defect these tests name."""
    response = await _n78_as_the_endpoint(world, creates=creates)
    assert response.committed is True and response.issues == [], f"W-B67: every row of this batch is valid, so the batch must commit; it was refused: {_render(response.issues)}"
    return response


async def _wb67_outcome(world: World, response: TXBatchResponse, names: dict[int, str]) -> WB67Outcome:
    """The cost basis the creates of ``names`` (index → what the row is) store, read back by id, and ``wac_results``."""
    ids = {index: _created_id(response, index) for index in names}
    costs = {index: await _stored_cost(world, tx_id) for index, tx_id in ids.items()}
    answers = _wb67_answers(response)
    held = "; ".join(f"create {index} ({names[index]}, id={ids[index]}) holds {_wb67_cost(cost)}" for index, cost in costs.items())
    said = ", ".join(f"{operation} {index}: {_wb67_cost(wac)}" for operation, index, wac in answers) or "no item"
    return WB67Outcome(costs=costs, answers=answers, today=f"{held}; wac_results said [{said}]")


def _same_key(creates: list[dict]) -> None:
    """Scaffold: the creates share broker, asset, date and type and carry no ``link_uuid`` — the key on which
    ``_find_created_tx_for_wac`` takes the newest row for each of them."""
    keys = {(create["broker_id"], create["asset_id"], create["date"], create["type"]) for create in creates}
    links = [create.get("link_uuid") for create in creates]
    assert len(keys) == 1 and links == [None] * len(creates), f"scaffold: the creates must share one (broker, asset, date, type) and carry no link_uuid; keys {keys}, link_uuids {links}"


def _split_linked_create(world: World, split: AssetEvent) -> dict:
    """The ADJUSTMENT +10 in ``auto`` that realizes ``split`` on ``source``, as ``_split_linked_adjustment`` sends it — here
    in the batch under test, beside the Auto row whose pool it rescales."""
    return {**_created_adjustment(world, broker=world.source, quantity=SPLIT_QUANTITY, cost_basis_mode="auto"), "asset_event_id": split.id}


async def _assert_split_linked(world: World, tx_id: int, link: tuple[int, AssetEventType, int]) -> None:
    """Scaffold: row ``tx_id`` is stored linked to the event ``link`` names — ``(event id, SPLIT, the test's asset id)``,
    taken before the batch —, read from the database: what makes it split-linked."""
    statement = select(Transaction.asset_event_id, AssetEvent.type, AssetEvent.asset_id).outerjoin(AssetEvent, Transaction.asset_event_id == AssetEvent.id).where(Transaction.id == tx_id)
    stored = tuple((await world.session.execute(statement)).one())
    assert stored == link, f"scaffold: the ADJUSTMENT +{SPLIT_QUANTITY} id={tx_id} must be stored linked to the SPLIT of the test's asset (event id, type, asset id) = {link}; it holds {stored}"


class TestWB67EachAutoCreateCostsItsOwnRow:
    """W-B67 — RED until its cure: two creates on one key (broker, asset, date, type, no ``link_uuid``) are one row to
    ``_find_created_tx_for_wac``, the newest. Each Auto create must cost its own row, and its ``wac_results`` item, on its own
    index, carry what that row stores (N84 (a)).

    The rows are ADJUSTMENTs +q on ``source``, whose pool is ``source`` up to their date without themselves
    (``_auto_cost_source``): the ``world``'s 10 units at 100 EUR, and what the batch adds on the day. Each batch is valid and
    commits, today and after the cure (``_wb67_commit``); its rows are read back by id (``_wb67_outcome``).
    """

    @pytest.mark.asyncio
    async def test_auto_then_manual_on_one_key_each_row_keeps_its_own_cost(self, world):
        """RED until W-B67's cure: an ADJUSTMENT +5 in ``auto`` (create 0), then an ADJUSTMENT +5 at a manual 50 EUR, no mode
        (create 1), on one key. The Manual row keeps its 50 EUR; the Auto row holds the average of its pool without itself —
        the BUY's 10 at 100 and the Manual 5 at 50: (1 000 + 250) / 15 —; ``wac_results`` is one item, on index 0, that cost.

        Today the Auto item finds the Manual row, the newest of the key, and overwrites its 50 with the average of a pool
        holding the Auto row at zero cost, 1 000 / 15; the Auto row commits without a cost, and index 0 answers 1 000 / 15."""
        auto = _created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")
        manual = {**_created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY), "cost_basis_override": _cost_sent(WB67_MANUAL_COST)}
        _same_key([auto, manual])
        auto_cost = (_average(WORLD_PAID + ADJUSTMENT_QUANTITY * WB67_MANUAL_COST.amount, BUY_QUANTITY + ADJUSTMENT_QUANTITY), EUR)
        manual_cost = (WB67_MANUAL_COST.amount, WB67_MANUAL_COST.code)

        response = await _wb67_commit(world, [auto, manual])

        outcome = await _wb67_outcome(world, response, {0: "the Auto row", 1: "the Manual row"})
        assert (outcome.costs, outcome.answers) == (
            {0: auto_cost, 1: manual_cost},
            [("create", 0, auto_cost)],
        ), f"W-B67: the Auto create (create 0) must cost its own row, at {_wb67_cost(auto_cost)} — the BUY and the Manual row, (1 000 + 250) / 15 —, and leave the Manual row (create 1) its {_wb67_cost(manual_cost)}; wac_results one item, create 0: {_wb67_cost(auto_cost)}. Today {outcome.today}"

    @pytest.mark.asyncio
    async def test_two_auto_rows_on_one_key_each_hold_the_average_before_the_other(self, world):
        """RED until W-B67's cure: two ADJUSTMENTs +5 in ``auto`` on one key (create 0, create 1). N84: the first is costed
        without the second, still to be costed (c), at the BUY's 100; the second with the first at its 100, 1 500 / 15 = 100.
        Both rows hold 100 EUR, and ``wac_results`` answers 100 on index 0 and on index 1.

        Today both items find the second row, the newest of the key: it is costed twice, at 1 000 / 15 — the first row in its
        pool at zero cost —, and the first row commits without a cost. Each item costing its own row without (c) would give
        1 000 / 15 and (1 000 + 5 × 1 000 / 15) / 15."""
        first = _created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")
        second = _created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")
        _same_key([first, second])
        expected = (UNIT_COST, EUR)
        at_zero = _average(WORLD_PAID, BUY_QUANTITY + ADJUSTMENT_QUANTITY)
        without_c = (at_zero, _average(WORLD_PAID + ADJUSTMENT_QUANTITY * at_zero, BUY_QUANTITY + ADJUSTMENT_QUANTITY))

        response = await _wb67_commit(world, [first, second])

        outcome = await _wb67_outcome(world, response, {0: "the first Auto row", 1: "the second Auto row"})
        assert (outcome.costs, outcome.answers) == ({0: expected, 1: expected}, [("create", 0, expected), ("create", 1, expected)]), (
            f"W-B67, N84: each Auto create must cost its own row — the first without the second, still to be costed, the second with the first at its cost —, so both rows hold {_wb67_cost(expected)} "
            f"and wac_results answers {_wb67_cost(expected)} on create 0 and on create 1. Today {outcome.today}. "
            f"(none and {_wb67_cost((at_zero, EUR))}: today's search, the newest row costed twice; {_wb67_cost((without_c[0], EUR))} and {_wb67_cost((without_c[1], EUR))}: each its own row, the other counted at zero, (a) without (c).)"
        )

    @pytest.mark.asyncio
    async def test_split_linked_and_plain_auto_rows_on_one_key_answer_on_their_own_index(self, world):
        """RED until W-B67's cure: an ADJUSTMENT +10 in ``auto`` linked to a 2:1 SPLIT of the asset (create 0) and a plain
        ADJUSTMENT +5 in ``auto`` (create 1), on one key. The split row gets no cost — its units are the split's rescale
        (``_compute_wac_for_auto_items``) — and ``wac_results`` answers none on index 0; the plain row holds the post-split
        average, 1 000 / 20 = 50 EUR, answered on index 1.

        Today the split row's item finds the plain row, the newest of the key, and answers the plain row's 50 on index 0; the
        rows hold what they should only because the plain row is costed by both items, and the split row by none."""
        split = await _event(world, AssetEventType.SPLIT, SPLIT_RATIO)
        link = (split.id, AssetEventType.SPLIT, world.asset.id)
        split_row = _split_linked_create(world, split)
        plain = _created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")
        _same_key([split_row, plain])
        post_split = (_average(WORLD_PAID, BUY_QUANTITY + SPLIT_QUANTITY), EUR)

        response = await _wb67_commit(world, [split_row, plain])

        await _assert_split_linked(world, _created_id(response, 0), link)
        outcome = await _wb67_outcome(world, response, {0: "the split-linked Auto row", 1: "the plain Auto row"})
        assert (outcome.costs, outcome.answers) == (
            {0: (None, None), 1: post_split},
            [("create", 0, None), ("create", 1, post_split)],
        ), f"W-B67: each Auto create must answer on its own index — create 0, split-linked, holds no cost and answers none; create 1 holds the post-split {_wb67_cost(post_split)}, answered on create 1. Today {outcome.today}"


class TestWB67AutoRowsAreCostedInDateOrder:
    """W-B67, N84 (b) — RED until its cure: the batch's Auto rows are costed in the order of their pool date, then by index,
    each entering the pools after it at its own cost; ``wac_results`` keeps its order, the creates by index."""

    @pytest.mark.asyncio
    async def test_auto_rows_sent_against_date_order_are_costed_in_date_order(self, world):
        """RED until W-B67's cure: on ``source``, an ADJUSTMENT +5 in ``auto`` on D+2 (create 0), one on D (create 1), and a
        BUY +5 on D+1 paying 2 000 EUR (create 2), every day after the ``world``'s BUY. The D row holds the BUY's 100; the D+2
        row (1 000 + 5 × 100 + 2 000) / 20 = 175, the D row in its pool at its own cost; ``wac_results`` answers 175 on
        create 0 and 100 on create 1, in index order. ``source`` allows a cash overdraft, which the ``world``'s BUY already
        relies on: no DEPOSIT is needed for the replay.

        Today each item finds its own row — they lie on different days — but they are costed by index: the D+2 row first,
        with the D row in its pool at zero cost, (1 000 + 0 + 2 000) / 20 = 150. Costing by index with the D row left out of
        the pool — (c) without (b) — gives (1 000 + 2 000) / 15 = 200. Three different values: the test proves the order."""
        late = {**_created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto"), "date": WB67_D_PLUS_2.isoformat()}
        early = {**_created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto"), "date": WB67_D.isoformat()}
        buy = {"broker_id": world.source.id, "asset_id": world.asset.id, "type": "BUY", "date": WB67_D_PLUS_1.isoformat(), "quantity": str(ADJUSTMENT_QUANTITY), "cash": {"code": EUR, "amount": str(WB67_BUY_PAID)}}
        early_cost = (UNIT_COST, EUR)
        late_cost = (_average(WORLD_PAID + ADJUSTMENT_QUANTITY * UNIT_COST - WB67_BUY_PAID, BUY_QUANTITY + 2 * ADJUSTMENT_QUANTITY), EUR)
        readings = {
            _average(WORLD_PAID - WB67_BUY_PAID, BUY_QUANTITY + 2 * ADJUSTMENT_QUANTITY): "today's behaviour — costed first, by index, with the D row in its pool at zero cost (ADD_UNKNOWN_COST)",
            _average(WORLD_PAID - WB67_BUY_PAID, BUY_QUANTITY + ADJUSTMENT_QUANTITY): "no date order — costed first, by index, with the D row, still to be costed, left out of its pool: (c) without (b)",
        }

        response = await _wb67_commit(world, [late, early, buy])

        outcome = await _wb67_outcome(world, response, {0: "the Auto row of D+2", 1: "the Auto row of D"})
        answered = {(operation, index): wac for operation, index, wac in outcome.answers}
        got = outcome.costs[0][0]
        reading = "no cost at all" if got is None else readings.get(got, "neither today's 150 nor the 200 of (c) without (b)")
        assert (outcome.costs, answered) == ({0: late_cost, 1: early_cost}, {("create", 0): late_cost, ("create", 1): early_cost}), (
            f"W-B67, N84 (b): the Auto rows are costed in date order — the D row first, at {_wb67_cost(early_cost)}, then the D+2 row with it in its pool at that cost, (1 000 + 5 × 100 + 2 000) / 20 = {_wb67_cost(late_cost)} —, "
            f"each answered on its own index. The D+2 row holds {_wb67_cost(outcome.costs[0])}: {reading}. Today {outcome.today}"
        )
        assert [(operation, index) for operation, index, _wac in outcome.answers] == [("create", 0), ("create", 1)], f"W-B67, N84: wac_results keeps its order — the creates by index, then the updates —, not the order the rows are costed in; it answers {outcome.answers}"


class TestWB67GuardsWhereTodaysSearchFindsTheRow:
    """W-B67 — guards, green today and after the cure: the batches whose Auto row today's search finds — the only row of its
    key, the newest, or a leg its ``link_uuid`` names — keep that row's cost, answered on its own index. A TRANSFER pair's
    Auto receiving leg alone is guarded already (``TestAutoCost``, and the W-B69 guard
    ``test_auto_row_over_a_readable_pool_takes_its_average``, which reads its ``wac_results`` item on index 1)."""

    @pytest.mark.asyncio
    async def test_a_lone_auto_adjustment_holds_the_average(self, world):
        """Guard: an ADJUSTMENT +5 in ``auto`` on ``source``, alone, holds the BUY's 100 EUR, answered on index 0."""
        response = await _wb67_commit(world, [_created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")])

        outcome = await _wb67_outcome(world, response, {0: "the Auto row"})
        expected = (UNIT_COST, EUR)
        assert (outcome.costs, outcome.answers) == ({0: expected}, [("create", 0, expected)]), f"A lone Auto ADJUSTMENT +{ADJUSTMENT_QUANTITY} must hold {_wb67_cost(expected)}, answered on create 0: {outcome.today}"

    @pytest.mark.asyncio
    async def test_manual_then_auto_on_one_key_each_row_keeps_its_own_cost(self, world):
        """Guard: an ADJUSTMENT +5 at a manual 50 EUR, no mode (create 0), then an ADJUSTMENT +5 in ``auto`` (create 1), on one
        key: the Manual row keeps its 50, the Auto row holds (1 000 + 250) / 15, and ``wac_results`` is that one item, on
        index 1. Right today because the Auto row is the newest of the key, the row today's search takes."""
        manual = {**_created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY), "cost_basis_override": _cost_sent(WB67_MANUAL_COST)}
        auto = _created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")
        _same_key([manual, auto])
        manual_cost = (WB67_MANUAL_COST.amount, WB67_MANUAL_COST.code)
        auto_cost = (_average(WORLD_PAID + ADJUSTMENT_QUANTITY * WB67_MANUAL_COST.amount, BUY_QUANTITY + ADJUSTMENT_QUANTITY), EUR)

        response = await _wb67_commit(world, [manual, auto])

        outcome = await _wb67_outcome(world, response, {0: "the Manual row", 1: "the Auto row"})
        assert (outcome.costs, outcome.answers) == ({0: manual_cost, 1: auto_cost}, [("create", 1, auto_cost)]), f"Manual then Auto on one key: the Manual row keeps {_wb67_cost(manual_cost)}, the Auto row holds {_wb67_cost(auto_cost)}, answered on create 1: {outcome.today}"

    @pytest.mark.asyncio
    async def test_a_split_linked_auto_row_stays_in_the_pool_of_an_auto_row_costed_before_it(self, world):
        """Guard, N84 (c)'s exception: a split-linked Auto row stays in the other Auto rows' pools, costed or not.

        A TRANSFER pair source → dest whose receiving leg is in ``auto`` (create 1; its ``link_uuid`` finds it, today too),
        and the ADJUSTMENT +10 in ``auto`` that realizes a 2:1 SPLIT on ``source`` the same day (create 2). The leg's pool
        date is its partner's, the split row's day: by index the leg is costed first, the split row still to be costed, and
        only the exception keeps the rescale in the leg's pool — ``source`` without the two legs. The leg holds the
        post-split 1 000 / 20 = 50 EUR, answered on create 1; the split row none, answered none on create 2. A cure that
        leaves the split row out gives the leg 100. Green today, which leaves no row out of a pool.

        The red ``test_split_linked_and_plain_auto_rows_on_one_key_answer_on_their_own_index`` costs its split row first: a
        cure without the exception fails it only if it leaves out the Auto rows without a cost, not those still to be
        handled. This guard fails such a cure either way."""
        split = await _event(world, AssetEventType.SPLIT, SPLIT_RATIO)
        link = (split.id, AssetEventType.SPLIT, world.asset.id)
        creates = [*_created_pair(world, cost_basis_mode="auto"), _split_linked_create(world, split)]
        post_split = (_average(WORLD_PAID, BUY_QUANTITY + SPLIT_QUANTITY), EUR)

        response = await _wb67_commit(world, creates)

        await _assert_split_linked(world, _created_id(response, 2), link)
        outcome = await _wb67_outcome(world, response, {1: "the Auto receiving leg", 2: "the split-linked Auto row"})
        assert (outcome.costs, outcome.answers) == (
            {1: post_split, 2: (None, None)},
            [("create", 1, post_split), ("create", 2, None)],
        ), f"N84 (c): the split-linked Auto row stays in the pool of the receiving leg, costed before it, so the leg holds the post-split {_wb67_cost(post_split)}, answered on create 1, and the split row none (100 EUR on the leg: the split row left out of its pool): {outcome.today}"


# ============================================================================
# RED AND CONTROLS — N88 (J-57): AN AUTO COST WITH NOTHING TO AVERAGE
# ============================================================================

# The cure's codes, as literals: the TXValidationCode members do not exist before it.
AUTO_COST_EMPTY_POOL = "autoCostEmptyPool"
AUTO_COST_UNKNOWN_POOL = "autoCostUnknownPool"
# The day of the rows an N88 test plants in a pool — the SELL that empties it, the units it holds —: after the world's BUY,
# before MOVE_DAY, the Auto rows' date.
N88_POOL_DAY = LATER_BUY_DAY
# A known cost of 0: the cost of free units (ADD_ZERO_COST), or a Manual cost of 0.
ZERO_COST = Currency(code=EUR, amount=Decimal("0"))
# What the SELL of the world's 10 units receives: any amount, the units are gone either way.
N88_SELL_PROCEEDS = Decimal("1200")
# The quantity of an N88 Auto row beside one of ADJUSTMENT_QUANTITY (5), or over a pool of 5.
N88_OTHER_QUANTITY = Decimal("3")
# What today's code makes of a pool with nothing to average, for the red messages.
N88_TODAY_EMPTY = "the empty pool averages to 0 EUR (compute_wac_iterative), which _write_auto_cost writes — a Currency of 0 is truthy — and the cost check skips, the row being Auto: a free acquisition, in silence"
N88_TODAY_UNKNOWN = "the units of unknown cost enter the average at zero (ADD_UNKNOWN_COST), so it is 0 EUR, which _write_auto_cost writes and the cost check skips: a free acquisition, in silence"


async def _n88_plant(world: World, *, broker: Broker, tx_type: TransactionType, quantity: Decimal, cost: Currency | None = None, amount: Decimal = Decimal("0"), currency: str | None = None) -> int:
    """A row of the ``world``'s asset on ``broker`` on ``N88_POOL_DAY``, written without the batch and its checks
    (``_stored_row``, its date moved before the Auto rows'); its id.

    An incoming row without ``cost`` is an acquisition of unknown cost (``ADD_UNKNOWN_COST``), which the batch refuses to
    create (``costBasisRequired``): an older version left it (``test_db/legacy_cost_rows.py``). With ``ZERO_COST``, a free
    acquisition (``ADD_ZERO_COST``).
    """
    row = _stored_row(world, broker=broker, tx_type=tx_type, quantity=quantity, cost=cost, amount=amount, currency=currency)
    row.date = N88_POOL_DAY
    world.session.add(row)
    await world.session.flush()
    return row.id


async def _pool(world: World, broker: Broker, *, without: tuple[int, ...] = ()) -> list[tuple]:
    """The rows an Auto ADJUSTMENT on ``broker`` on ``MOVE_DAY`` averages — the broker's rows of the ``world``'s asset up to
    that day, but ``without`` (the row itself, when it is stored) —, read before the batch, in date order, as ``(type,
    quantity, amount, cost_basis_override)``. What a pool holds is checked, never assumed."""
    where = [Transaction.broker_id == broker.id, Transaction.asset_id == world.asset.id, Transaction.date <= MOVE_DAY]
    if without:
        where.append(Transaction.id.notin_(without))
    statement = select(Transaction.type, Transaction.quantity, Transaction.amount, Transaction.cost_basis_override).where(*where).order_by(Transaction.date, Transaction.id)
    return [tuple(row) for row in (await world.session.execute(statement)).all()]


def _n88_issue(operation: str, index: int, code: str) -> dict:
    """The issue of N88's cure, as ``_n88_view`` shows it: on the Auto row's operation and index, ``field``
    ``cost_basis_override``, ``ref_id`` None and no params — W-B69's ``autoCostUnreadable`` without its count."""
    return {"operation": operation, "index": index, "ref_id": None, "code": code, "field": "cost_basis_override", "params": None}


def _n88_view(issue: TXValidationIssue) -> dict:
    """``_issue_view``, the contract's «no params» — None or empty — read alike, as None."""
    return {**_issue_view(issue), "params": issue.params or None}


def _wac_items(response: TXBatchResponse, operation: str, index: int) -> list:
    """The ``wac_results`` items on row ``operation`` ``index``, with a cost or without: a refused row has none."""
    return [item for item in response.wac_results or [] if (item.operation, item.index) == (operation, index)]


async def _n88_verdict(world: World, response: TXBatchResponse, rows: list[tuple[str, int]]) -> str:
    """What a batch did with its Auto rows ``rows``, for a red's message: ``_verdict``, for one row or several, and on a
    commit the cost basis each of them stores, read back by id."""
    answered = ", ".join(f"{operation} {index}: {_wb67_cost(_answered(response, operation, index))}" for operation, index in rows)
    if response.committed:
        stored = []
        for result in response.results:
            if (result.operation, result.index) in rows:
                for tx_id in result.ids:
                    stored.append(f"id={tx_id} ({result.operation} {result.index}) stores {_wb67_cost(await _stored_cost(world, tx_id))}")
        return f"the batch committed, answering the Auto cost(s) {answered}, and {', '.join(stored) or 'no row was stored'}"
    if not response.issues:
        return f"the batch validated clean, answering the Auto cost(s) {answered}, what /commit saves"
    return f"the batch was refused with [{_render(response.issues)}] (Auto cost(s) answered: {answered})"


async def _assert_nothing_to_average(world: World, response: TXBatchResponse, refused: list[tuple[str, int, str]], *, commit: bool, brokers: list[int], before: dict[int, dict], pool: str, today: str) -> None:
    """N88's assertions: the issues are exactly those ``refused`` names — ``(operation, index, code)``, each as
    ``_n88_issue`` shows it —; not committed; no ``wac_results`` item on a refused row; and every row of ``brokers`` as it
    was (``before``): no Auto row stored, no stored cost changed. ``pool`` says what the pool holds, ``today`` what today's
    code makes of it."""
    rows = [(operation, index) for operation, index, _code in refused]
    expected = [_n88_issue(operation, index, code) for operation, index, code in refused]
    named = " and ".join(f"{code} on {operation} {index}" for operation, index, code in refused)
    views = [_n88_view(issue) for issue in response.issues]
    verdict = await _n88_verdict(world, response, rows)
    assert (response.committed, _in_order(views)) == (
        False,
        _in_order(expected),
    ), f"N88: an Auto cost over {pool} has nothing to average, so the batch must be refused ({_endpoint(commit)}) with exactly {named} — field cost_basis_override, no params, ref_id None —; today {verdict} — {today}"
    answered = {row: _wac_items(response, *row) for row in rows}
    assert all(items == [] for items in answered.values()), f"N88: a refused Auto row gets no wac_results item; wac_results answers {answered}"
    changed = _changed(before, await _raw_rows(world, brokers))
    assert changed == {}, f"N88: the refused batch changed rows of the test's brokers (before, after): {changed}"


class TestN88AutoCostWithNothingToAverage:
    """N88 (J-57) — RED until its cure but for the controls: an Auto row whose pool has nothing to average is refused on its
    own coordinates — ``autoCostEmptyPool`` when the pool holds no units on its date, ``autoCostUnknownPool`` when it holds
    units but none at a known cost —, and its batch saves nothing. Free units keep their average of 0, a Manual 0 is
    accepted, and a pool in part of unknown cost keeps today's understated average (J-58, not N88's).

    The Auto rows are ADJUSTMENTs on ``MOVE_DAY``, whose pool is their own broker up to that day without themselves
    (``_auto_cost_source``): ``dest`` holds nothing of the asset but what a test plants, ``source`` the ``world``'s BUY, 10
    units for 1 000 EUR. Each batch runs as ``POST /transactions/commit`` or ``/validate`` runs it, its transaction included
    (``_as_the_endpoint``: a refusal is an issue, a batch that raises fails the test), and its rows are read back by id or by
    raw SQL. What each pool holds is checked before the batch (``_pool``), never assumed.

    B1 (J-57 complete), a control at the end: the receiving leg of a TRANSFER, whose pool is its partner's broker, over units
    of unknown cost — refused in Auto, committed at a Manual cost of 0, the answer Q-J57-1 (c) asks of the user.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("mode", AUTO_MODES)
    async def test_auto_adjustment_on_a_broker_that_never_held_the_asset_is_refused(self, world, mode, commit):
        """R1 (/commit) and R2 (/validate), RED until N88: an ADJUSTMENT +5 in ``mode`` on ``dest``, which never held the
        asset, gets one ``autoCostEmptyPool`` on create 0 — field ``cost_basis_override``, no params, ``ref_id`` None —, no
        ``wac_results`` item, and nothing is committed: the row is not stored.

        Today the empty pool averages to 0 EUR: /commit stores the row at a cost of 0, a free acquisition; /validate answers 0
        on create 0, with no issue."""
        pool = await _pool(world, world.dest)
        assert pool == [], f"precondition broken: dest must never have held the asset; its pool on {MOVE_DAY} holds {pool}"
        created = _created_adjustment(world, broker=world.dest, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode=mode)
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=commit, creates=[created])

        await _assert_nothing_to_average(world, response, [("create", 0, AUTO_COST_EMPTY_POOL)], commit=commit, brokers=brokers, before=before, pool=f"dest, a broker that never held the asset (an ADJUSTMENT +{ADJUSTMENT_QUANTITY} in {mode})", today=N88_TODAY_EMPTY)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    async def test_auto_adjustment_after_its_broker_sold_every_unit_is_refused(self, world, commit):
        """R3, RED until N88: ``source`` bought 10 units for 1 000 EUR (the ``world``'s BUY) and sold all 10 a week later (a
        SELL planted on ``N88_POOL_DAY``); an ADJUSTMENT +5 in ``auto`` later still, on ``MOVE_DAY``, has a pool with no unit
        on its date: one ``autoCostEmptyPool`` on create 0, no ``wac_results`` item, nothing committed. A pool emptied by
        sales is as empty as one never filled.

        Today the pool's average falls to 0 with its last unit: the row is stored, or answered, at 0."""
        await _n88_plant(world, broker=world.source, tx_type=TransactionType.SELL, quantity=-BUY_QUANTITY, amount=N88_SELL_PROCEEDS, currency=EUR)
        pool = await _pool(world, world.source)
        assert pool == [(TransactionType.BUY, BUY_QUANTITY, -WORLD_PAID, None), (TransactionType.SELL, -BUY_QUANTITY, N88_SELL_PROCEEDS, None)], f"precondition broken: source's pool on {MOVE_DAY} must be the BUY of 10 units and the SELL of all 10: {pool}"
        created = _created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=commit, creates=[created])

        await _assert_nothing_to_average(world, response, [("create", 0, AUTO_COST_EMPTY_POOL)], commit=commit, brokers=brokers, before=before, pool=f"source after it sold every unit it bought (an ADJUSTMENT +{ADJUSTMENT_QUANTITY} in auto)", today=f"BUY 10, SELL 10: {N88_TODAY_EMPTY}")

    @pytest.mark.asyncio
    async def test_two_auto_adjustments_on_an_empty_broker_are_both_refused(self, world):
        """R4, RED until N88 — its interplay with N84: an ADJUSTMENT +5 (create 0) and one +3 (create 1), both in ``auto``, on
        ``dest`` on ``MOVE_DAY``, in one batch. N84 costs the first without the second, still to be costed: an empty pool,
        refused. Refused, the first is never costed, so it stays out of the second's pool, empty too: two
        ``autoCostEmptyPool``, on create 0 and on create 1; no ``wac_results`` item; nothing committed.

        Today the first is written at 0 and leaves the rows still to be costed, so the second averages it as 5 free units
        (``ADD_ZERO_COST``): both are stored at 0. A cure that refused the first yet wrote it at 0 would hand the second 5
        free units and let it through at 0; one that wrote nothing on the first but let it into the second's pool would give
        the second 5 units of unknown cost, ``autoCostUnknownPool``."""
        pool = await _pool(world, world.dest)
        assert pool == [], f"precondition broken: dest must never have held the asset; its pool on {MOVE_DAY} holds {pool}"
        creates = [
            _created_adjustment(world, broker=world.dest, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto"),
            _created_adjustment(world, broker=world.dest, quantity=N88_OTHER_QUANTITY, cost_basis_mode="auto"),
        ]
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=True, creates=creates)

        await _assert_nothing_to_average(
            world,
            response,
            [("create", 0, AUTO_COST_EMPTY_POOL), ("create", 1, AUTO_COST_EMPTY_POOL)],
            commit=True,
            brokers=brokers,
            before=before,
            pool=f"dest, a broker that never held the asset (two ADJUSTMENTs in auto, +{ADJUSTMENT_QUANTITY} and +{N88_OTHER_QUANTITY}, one day, one batch; N84 keeps the first, refused, out of the second's pool)",
            today=f"{N88_TODAY_EMPTY}; then the second averages the first as {ADJUSTMENT_QUANTITY} free units, and is written at 0 too",
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    async def test_update_switching_to_auto_over_an_empty_pool_is_refused_and_keeps_its_cost(self, world, commit):
        """R5, RED until N88: an ADJUSTMENT +5 stored on ``dest`` at a Manual 42 EUR, ``dest`` holding nothing else of the
        asset; the update ``{id, cost_basis_mode: auto}`` recomputes its cost over ``dest`` without itself, an empty pool: one
        ``autoCostEmptyPool`` on update 0 — ``ref_id`` None, as W-B69's on an update —, no ``wac_results`` item, nothing
        committed, and the row keeps its 42 EUR.

        Today the update overwrites the 42 EUR with 0: /commit stores it, /validate answers it."""
        stored = await _store(world, "adjustment_in", cost=STORED_COST)
        row_id = stored.subject.id
        pool = await _pool(world, world.dest, without=(row_id,))
        assert pool == [], f"precondition broken: dest must hold nothing of the asset but the ADJUSTMENT id={row_id}; its pool on {MOVE_DAY} without it holds {pool}"
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=commit, updates=[{"id": row_id, "cost_basis_mode": "auto"}])

        await _assert_nothing_to_average(
            world,
            response,
            [("update", 0, AUTO_COST_EMPTY_POOL)],
            commit=commit,
            brokers=brokers,
            before=before,
            pool=f"dest without the updated row, which holds nothing else of the asset (an update switching the ADJUSTMENT +{ADJUSTMENT_QUANTITY} at {STORED_COST.amount} {STORED_COST.code} to auto)",
            today=f"{N88_TODAY_EMPTY}; the 0 overwrites the {STORED_COST.amount} {STORED_COST.code} the row was saved with",
        )
        stored_after = await _stored_cost(world, row_id)
        assert stored_after == (STORED_COST.amount, STORED_COST.code), f"N88: the refused update must leave the ADJUSTMENT id={row_id} its {STORED_COST.amount} {STORED_COST.code}; it holds {_show(stored_after)}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    async def test_auto_adjustment_over_units_of_unknown_cost_is_refused(self, world, commit):
        """R6, RED until N88: ``dest`` holds 5 units of unknown cost — an ADJUSTMENT +5 planted on ``N88_POOL_DAY`` without a
        cost basis —; an ADJUSTMENT +3 in ``auto`` on ``MOVE_DAY`` has units to average but none at a known cost: one
        ``autoCostUnknownPool`` on create 0, no ``wac_results`` item, nothing committed.

        Today the 5 units enter the average at zero (``ADD_UNKNOWN_COST``, the pool's cost incomplete): the row is stored, or
        answered, at 0."""
        await _n88_plant(world, broker=world.dest, tx_type=TransactionType.ADJUSTMENT, quantity=ADJUSTMENT_QUANTITY)
        pool = await _pool(world, world.dest)
        assert pool == [(TransactionType.ADJUSTMENT, ADJUSTMENT_QUANTITY, Decimal("0"), None)], f"precondition broken: dest's pool on {MOVE_DAY} must be one ADJUSTMENT +{ADJUSTMENT_QUANTITY} without a cost basis: {pool}"
        created = _created_adjustment(world, broker=world.dest, quantity=N88_OTHER_QUANTITY, cost_basis_mode="auto")
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _as_the_endpoint(world, commit=commit, creates=[created])

        await _assert_nothing_to_average(world, response, [("create", 0, AUTO_COST_UNKNOWN_POOL)], commit=commit, brokers=brokers, before=before, pool=f"{ADJUSTMENT_QUANTITY} units of unknown cost on dest (an ADJUSTMENT +{N88_OTHER_QUANTITY} in auto)", today=N88_TODAY_UNKNOWN)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    async def test_auto_adjustment_over_bought_units_takes_their_average(self, world, commit):
        """C1, control, green today and after N88: an ADJUSTMENT +5 in ``auto`` on ``source``, over the ``world``'s BUY of 10
        units for 1 000 EUR, takes their average, 100 EUR, with no issue — answered on /validate, answered and stored on
        /commit."""
        pool = await _pool(world, world.source)
        assert pool == [(TransactionType.BUY, BUY_QUANTITY, -WORLD_PAID, None)], f"precondition broken: source's pool on {MOVE_DAY} must be the world's BUY alone: {pool}"
        batch = AutoBatch(operation="create", index=0, creates=[_created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")], updates=[], row_id=None)

        response = await _as_the_endpoint(world, commit=commit, creates=batch.creates)

        await _assert_takes(world, response, batch, cost=UNIT_COST, commit=commit, what=f"An Auto ADJUSTMENT +{ADJUSTMENT_QUANTITY} over the BUY of {BUY_QUANTITY} units for {WORLD_PAID} EUR")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    async def test_auto_adjustment_over_free_units_keeps_their_zero(self, world, commit):
        """C2, control, green today and after N88: ``dest`` holds 10 free units — an ADJUSTMENT +10 planted at a Manual cost
        of 0 EUR (``ADD_ZERO_COST``): held, every one at a known cost of 0 —; an ADJUSTMENT +5 in ``auto`` takes their
        average, 0 EUR, with no issue — answered on /validate, answered and stored on /commit. N88 refuses a 0 with nothing
        behind it, never the 0 a pool's known cost gives."""
        await _n88_plant(world, broker=world.dest, tx_type=TransactionType.ADJUSTMENT, quantity=BUY_QUANTITY, cost=ZERO_COST)
        pool = await _pool(world, world.dest)
        assert pool == [(TransactionType.ADJUSTMENT, BUY_QUANTITY, Decimal("0"), ZERO_COST.amount)], f"precondition broken: dest's pool on {MOVE_DAY} must be one ADJUSTMENT +{BUY_QUANTITY} at a cost of 0: {pool}"
        batch = AutoBatch(operation="create", index=0, creates=[_created_adjustment(world, broker=world.dest, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")], updates=[], row_id=None)

        response = await _as_the_endpoint(world, commit=commit, creates=batch.creates)

        await _assert_takes(world, response, batch, cost=ZERO_COST.amount, commit=commit, what=f"An Auto ADJUSTMENT +{ADJUSTMENT_QUANTITY} over {BUY_QUANTITY} free units (a known cost of 0)")

    @pytest.mark.asyncio
    async def test_manual_zero_cost_on_a_broker_that_never_held_the_asset_commits(self, world):
        """C3, control, green today and after N88: an ADJUSTMENT +5 on ``dest``, which never held the asset, at a Manual cost
        of 0 EUR — no mode, as the form sends a manual cost — commits with no issue and stores 0 EUR. N88 judges the Auto
        cost alone: a 0 the user writes is the user's."""
        pool = await _pool(world, world.dest)
        assert pool == [], f"precondition broken: dest must never have held the asset; its pool on {MOVE_DAY} holds {pool}"
        created = {**_created_adjustment(world, broker=world.dest, quantity=ADJUSTMENT_QUANTITY), "cost_basis_override": _cost_sent(ZERO_COST)}

        response = await _as_the_endpoint(world, commit=True, creates=[created])

        assert response.committed is True and response.issues == [], f"An ADJUSTMENT +{ADJUSTMENT_QUANTITY} at a Manual cost of 0 on a broker that never held the asset was refused: {_render(response.issues)}"
        stored = await _stored_cost(world, _created_id(response, 0))
        assert stored == (ZERO_COST.amount, ZERO_COST.code), f"The ADJUSTMENT +{ADJUSTMENT_QUANTITY} was committed with {_show(stored)}, not the Manual {ZERO_COST.amount} {ZERO_COST.code} it was sent with"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    async def test_auto_adjustment_over_units_partly_of_unknown_cost_takes_todays_understated_average(self, world, commit):
        """C4, control — it documents J-58, which N88 does not refuse: ``source`` holds the ``world``'s 10 units bought for
        1 000 EUR and 10 more of unknown cost (an ADJUSTMENT +10 planted without a cost basis); an ADJUSTMENT +5 in ``auto``
        takes today's average, the known cost over every unit, 1 000 / 20 = 50 EUR — not 0, so N88 leaves it alone —, with
        no issue: answered on /validate, answered and stored on /commit.

        J-58 (17/10): the average of a pool only part of whose units have a known cost is understated, in silence; refusing
        it, as N88 refuses a 0, or warning in the preview, is the developer's decision, not taken. This control pins today's
        value: a cure of N88 that changes it reaches past N88; a cure of J-58 updates it."""
        await _n88_plant(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=BUY_QUANTITY)
        pool = await _pool(world, world.source)
        assert pool == [
            (TransactionType.BUY, BUY_QUANTITY, -WORLD_PAID, None),
            (TransactionType.ADJUSTMENT, BUY_QUANTITY, Decimal("0"), None),
        ], f"precondition broken: source's pool on {MOVE_DAY} must be the BUY of 10 units for {WORLD_PAID} EUR and an ADJUSTMENT +{BUY_QUANTITY} without a cost basis: {pool}"
        understated = _average(WORLD_PAID, 2 * BUY_QUANTITY)
        assert understated == Decimal("50"), "the oracle: 1 000 / 20"
        batch = AutoBatch(operation="create", index=0, creates=[_created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")], updates=[], row_id=None)

        response = await _as_the_endpoint(world, commit=commit, creates=batch.creates)

        await _assert_takes(world, response, batch, cost=understated, commit=commit, what=f"J-58, today: an Auto ADJUSTMENT +{ADJUSTMENT_QUANTITY} over {BUY_QUANTITY} units bought for {WORLD_PAID} EUR and {BUY_QUANTITY} of unknown cost")

    @staticmethod
    def _transfer(sender_id: int, receiver_id: int, asset_id: int, *, receiving: dict) -> list[dict]:
        """A TRANSFER pair to create on ``MOVE_DAY``, ``sender_id`` → ``receiver_id``, under a link of its own: the giving leg
        −4 at index 0, the receiving leg +4 at index 1, carrying ``receiving`` (its mode, or its cost basis)."""
        link_uuid = str(uuid.uuid4())
        giving = {"broker_id": sender_id, "asset_id": asset_id, "type": "TRANSFER", "date": MOVE_DAY.isoformat(), "quantity": str(-TRANSFER_QUANTITY), "link_uuid": link_uuid}
        received = {"broker_id": receiver_id, "asset_id": asset_id, "type": "TRANSFER", "date": MOVE_DAY.isoformat(), "quantity": str(TRANSFER_QUANTITY), "link_uuid": link_uuid, **receiving}
        return [giving, received]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    async def test_receiving_transfer_leg_over_units_of_unknown_cost_is_refused_in_auto_and_commits_at_a_manual_zero(self, world, commit):
        """B1 (J-57 complete), control, green today and after: N88 on the receiving leg of a TRANSFER, then the answer
        Q-J57-1 (c) asks of the user.

        ``dest`` holds 5 units of unknown cost — an ADJUSTMENT +5 planted on ``N88_POOL_DAY`` without a cost basis — and sends
        4 of them on ``MOVE_DAY`` to a receiver of the test's own, which holds nothing of the asset. In ``auto`` the receiving
        leg (create 1) averages its partner's broker, ``dest``, up to the partner's date, without the two legs
        (``_auto_cost_source``): units, none at a known cost. The batch refuses it with one ``autoCostUnknownPool`` on create
        1 — field ``cost_basis_override``, no params, ``ref_id`` None —, no ``wac_results`` item, nothing committed (/commit
        and /validate alike). The reds above cover ADJUSTMENTs and an update; ``test_wac_inline.py``'s P27 a TRANSFER from an
        empty pool, through the API.

        Then the same transfer with the receiving leg at a Manual cost of 0 EUR — no mode, as the form sends a manual cost:
        Q-J57-1 (c), 19/10, a blocking cost todo is answered only by a value, 0 included — commits with no issue. The leg
        stores 0 EUR, a known cost, and the lot it brings the receiver reads 0: the receiver's pool is that leg alone, 4 units
        at a unit cost of 0, their average 0 EUR.
        """
        await _n88_plant(world, broker=world.dest, tx_type=TransactionType.ADJUSTMENT, quantity=ADJUSTMENT_QUANTITY)
        now = utcnow()
        receiver = Broker(name=f"{world.marker} N88 receiver", description="N88 B1: the broker the transfer reaches", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
        world.session.add(receiver)
        await world.session.flush()
        sender_pool = await _pool(world, world.dest)
        assert sender_pool == [(TransactionType.ADJUSTMENT, ADJUSTMENT_QUANTITY, Decimal("0"), None)], f"precondition broken: dest's pool on {MOVE_DAY} must be one ADJUSTMENT +{ADJUSTMENT_QUANTITY} without a cost basis: {sender_pool}"
        receiver_pool = await _pool(world, receiver)
        assert receiver_pool == [], f"precondition broken: the receiver must hold nothing of the asset; its pool on {MOVE_DAY} holds {receiver_pool}"
        # The ids and both batches are taken before either runs: the refused batch's rollback expires what it touched.
        sender_id, receiver_id, asset_id = world.dest.id, receiver.id, world.asset.id
        auto_pair = self._transfer(sender_id, receiver_id, asset_id, receiving={"cost_basis_mode": "auto"})
        manual_zero_pair = self._transfer(sender_id, receiver_id, asset_id, receiving={"cost_basis_override": _cost_sent(ZERO_COST)})
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        refused = await _as_the_endpoint(world, commit=commit, creates=auto_pair)

        await _assert_nothing_to_average(
            world,
            refused,
            [("create", 1, AUTO_COST_UNKNOWN_POOL)],
            commit=commit,
            brokers=brokers,
            before=before,
            pool=f"dest's {ADJUSTMENT_QUANTITY} units of unknown cost (the receiving leg of a TRANSFER dest → receiver, in auto, averages its partner's broker up to the partner's date)",
            today=f"{N88_TODAY_UNKNOWN} — N88's defect, back on a receiving TRANSFER leg",
        )

        answered = await _as_the_endpoint(world, commit=True, creates=manual_zero_pair)

        assert (answered.committed, answered.issues) == (True, []), f"Q-J57-1 (c): the same transfer with the receiving leg at a Manual cost of 0 {EUR}, no mode, must commit with no issue: {_render(answered.issues)}"
        receiving_id = _created_id(answered, 1)
        stored = await _stored_cost(world, receiving_id)
        assert stored == (ZERO_COST.amount, ZERO_COST.code), f"The receiving leg id={receiving_id} was committed with {_show(stored)}, not the Manual {ZERO_COST.amount} {ZERO_COST.code} it was sent with"
        lot = await compute_wac_iterative(world.session, broker_id=receiver_id, asset_id=asset_id, as_of_date=MOVE_DAY, asset_currency=EUR, use_cache=False)
        read = ([(row.tx_id, row.type, row.quantity, row.unit_cost) for row in lot.wac_qualifying_txs], (lot.wac.amount, lot.wac.code) if lot.wac else None)
        assert read == (
            [(receiving_id, TransactionType.TRANSFER.value, TRANSFER_QUANTITY, ZERO_COST.amount)],
            (ZERO_COST.amount, EUR),
        ), f"The lot the receiving leg id={receiving_id} brings the receiver must read a cost of 0: its pool that leg alone, {TRANSFER_QUANTITY} units at a unit cost of 0, their average 0 {EUR}; (tx_id, type, quantity, unit_cost) of its rows, and its average: {read}"


# ============================================================================
# RED AND GUARDS — J-60: A MANUAL COST BASIS BELOW 0
# ============================================================================

# The cure's TXValidationCode.COST_BASIS_NEGATIVE, as a literal: the member does not exist before it.
COST_BASIS_NEGATIVE = "costBasisNegative"
# The codes of the other refusals a row at a negative cost gets beside it (TestJ60ANegativeCostDoesNotStopTheBatch).
DECIMAL_PLACES_EXCEEDED = TXValidationCode.DECIMAL_PLACES_EXCEEDED.value
BALANCE_ASSET_NEGATIVE = TXValidationCode.BALANCE_ASSET_NEGATIVE.value
# The manual cost basis every J-60 red sends, per unit: below 0, within every digit limit, in the asset's currency.
J60_NEGATIVE_COST = Currency(code=EUR, amount=Decimal("-1"))
# A manual cost basis goes without a mode, as the form sends it, or in "manual", as an API client may: both are read.
J60_MANUAL_MODES = (pytest.param(None, id="no-mode"), pytest.param("manual", id="manual"))
# A manual cost of zero as a payload writes it: "0", and "-0", which parses to Decimal("-0"), equal to 0 and not below it.
J60_ZERO_TEXTS = (pytest.param("0", id="zero"), pytest.param("-0", id="minus-zero"))
# The rows _store writes, as J-60's messages name them: an update red sends the receiving leg of a pair alone.
J60_SHAPE_LABELS = {"transfer_in": f"TRANSFER receiving leg +{TRANSFER_QUANTITY}", "adjustment_in": f"ADJUSTMENT +{ADJUSTMENT_QUANTITY}"}
# The Auto rows whose payload carries J60_NEGATIVE_COST (_j60_auto_batch).
J60_AUTO_CASES = ("adjustment-create", "transfer-create", "transfer-update")
# The other refusal of a row at a negative cost: one a stage before the sign's check finds, one only the batch's last finds.
J60_BESIDE_CASES = ("decimal-places", "short-balance")
# 11 decimal places, past the 10 a quantity keeps (test_transaction_decimal_places.py's "quantity-11-decimals"):
# decimalPlacesExceeded, a refusal that does not stop the batch, unlike the integer digits.
J60_QUANTITY_11_DECIMALS = Decimal("0.12345678901")
# The per-unit cost an older version stored on 10 units of source, for the guard over a pool averaging below 0: with the
# world's BUY, (1 000 − 3 000) / 20 = −100 EUR.
J60_LEGACY_NEGATIVE_COST = Currency(code=EUR, amount=Decimal("-300"))


def _j60_mode(mode: str | None) -> str:
    """A manual cost's mode, for a message."""
    return "no mode" if mode is None else f"cost_basis_mode {mode}"


def _j60_issue(operation: str, index: int, ref_id: int | None = None) -> dict:
    """J-60's issue as ``_j60_view`` shows it: ``costBasisNegative`` on ``cost_basis_override``, on the row's operation and
    index, ``ref_id`` the row an update names — None for a create or a promote, as ``check_decimal_limits`` gives them."""
    return {"operation": operation, "index": index, "ref_id": ref_id, "code": COST_BASIS_NEGATIVE, "field": "cost_basis_override"}


def _j60_view(issue: TXValidationIssue) -> dict:
    """``_issue_view`` without its params: where an issue lies and what it says. The params of ``costBasisNegative`` — none —
    are checked apart (``_assert_cost_basis_negative``); those of another code are its own tests' business."""
    view = _issue_view(issue)
    del view["params"]
    return view


async def _j60_as_the_endpoint(world: World, *, commit: bool, creates: list[dict] | None = None, updates: list[dict] | None = None, promotes: list[dict] | None = None) -> TXBatchResponse:
    """The batch as ``POST /transactions/commit`` (``commit=True``) or ``/validate`` runs it, its transaction included —
    ``_as_the_endpoint``, promotes included: /commit keeps what the service answers committed and rolls back the rest,
    /validate always rolls back. A refusal is an issue: a batch that raises fails the test. Read the rows back by id or raw
    afterwards (``_stored_cost``, ``_raw_rows``), never through a copy the rollback expired."""
    savepoint = await world.session.begin_nested()
    try:
        response = await _run_batch(world, commit=commit, creates=creates, updates=updates, promotes=promotes)
    except Exception as error:  # the contract: a refusal is an issue, nothing raises
        pytest.fail(f"J-60: the batch must answer with its issues, never raise; it raised {type(error).__name__}: {error!r}")
    if commit and response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


async def _j60_today(world: World, response: TXBatchResponse, operation: str, index: int) -> str:
    """What the batch did with row ``operation`` ``index``, for a red's message: committed, and the cost basis each of its
    rows now stores; validated clean; or refused, and with what."""
    if response.committed:
        ids = next((result.ids for result in response.results if (result.operation, result.index) == (operation, index)), [])
        stored = []
        for tx_id in ids:
            stored.append(f"id={tx_id} holding {_show(await _stored_cost(world, tx_id))}")
        return f"the batch committed, {operation} {index} saved with {', '.join(stored) or 'no row'}"
    if not response.issues:
        return f"the batch validated clean, nothing on {operation} {index}: /commit saves its cost below 0"
    return f"the batch was refused with [{_render(response.issues)}]"


async def _assert_cost_basis_negative(world: World, response: TXBatchResponse, *, row: tuple[str, int, int | None], what: str, commit: bool, brokers: list[int], before: dict[int, dict], beside: tuple[dict, ...] = ()) -> None:
    """J-60's assertions on a batch the sign's check refuses: its issues are exactly ``costBasisNegative`` on ``row`` —
    ``(operation, index, ref_id)`` — and ``beside``, the row's other refusals, which come in the same answer (as
    ``_j60_view`` shows them, in any order); the ``costBasisNegative`` carries no params, None or empty alike; the batch is
    not committed; and every row of ``brokers`` is as it was (``before``): nothing written. ``what`` says what it sends."""
    operation, index, ref_id = row
    expected = [_j60_issue(operation, index, ref_id), *beside]
    views = [_j60_view(issue) for issue in response.issues]
    today = await _j60_today(world, response, operation, index)
    also = "".join(f", beside {view['code']} on {view['operation']} {view['index']}" for view in beside)
    assert (response.committed, _in_order(views)) == (False, _in_order(expected)), f"J-60: {what} must be refused ({_endpoint(commit)}) with exactly {COST_BASIS_NEGATIVE} on {operation} {index} — ref_id {ref_id}, field cost_basis_override —{also}; today {today}"
    params = [issue.params for issue in response.issues if issue.code == COST_BASIS_NEGATIVE]
    assert not any(params), f"J-60: {COST_BASIS_NEGATIVE} carries no params (None or empty alike); it carries {params}"
    changed = _changed(before, await _raw_rows(world, brokers))
    assert changed == {}, f"J-60: the refused batch changed rows of the test's brokers (before, after): {changed}"


async def _j60_auto_batch(world: World, case: str, mode: str) -> AutoBatch:
    """An Auto row in ``mode`` whose payload carries ``J60_NEGATIVE_COST``, over ``source``'s pool: the ``world``'s BUY.

    ``adjustment-create``: an ADJUSTMENT +5 on ``source``, create 0. ``transfer-create``: the receiving leg of a TRANSFER pair
    source → dest, create 1; ``transfer-update``: the receiving leg of the stored pair, at 42 EUR, recomputed by an update
    that also gives both legs new notes, update 1 (both ``_auto_batch``).
    """
    if case == "adjustment-create":
        created = {**_created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode=mode), "cost_basis_override": _cost_sent(J60_NEGATIVE_COST)}
        return AutoBatch(operation="create", index=0, creates=[created], updates=[], row_id=None)
    if case not in J60_AUTO_CASES:
        raise ValueError(f"unknown J-60 Auto case {case!r}")
    batch = await _auto_batch(world, "create" if case == "transfer-create" else "update", mode)
    rows = batch.creates if batch.operation == "create" else batch.updates
    rows[batch.index]["cost_basis_override"] = _cost_sent(J60_NEGATIVE_COST)
    return batch


class TestJ60ANegativeManualCostOnACreate:
    """J-60 — RED until its cure: a create that sends a manual cost basis below 0 is refused on its own row, wherever a cost
    basis goes in: an ADJUSTMENT adding units and a TRANSFER's receiving leg. An ADJUSTMENT taking units out takes no cost
    at all since N78-1: any cost on it, below 0 or not, is ``costBasisNotAllowed`` (RED until N78-1).

    Each batch runs as ``POST /transactions/commit`` or ``/validate`` runs it, its transaction included
    (``_j60_as_the_endpoint``), and the rows of the test's brokers are read back raw, before and after (``_raw_rows``).
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("mode", J60_MANUAL_MODES)
    async def test_adjustment_in_at_a_negative_cost_is_refused(self, world, mode, commit):
        """RED until J-60: an ADJUSTMENT +5 on ``dest`` at −1 EUR, with no mode or in ``manual`` — N78's guard
        ``test_adjustment_in_with_a_manual_cost_basis_commits`` with its cost below 0 — gets one ``costBasisNegative`` on
        create 0, ``ref_id`` None; not committed, nothing written; /validate answers the same issue."""
        created = {**_created_adjustment(world, broker=world.dest, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode=mode), "cost_basis_override": _cost_sent(J60_NEGATIVE_COST)}
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _j60_as_the_endpoint(world, commit=commit, creates=[created])

        what = f"an ADJUSTMENT +{ADJUSTMENT_QUANTITY} on dest created at a manual cost of {J60_NEGATIVE_COST.amount} {EUR} ({_j60_mode(mode)})"
        await _assert_cost_basis_negative(world, response, row=("create", 0, None), what=what, commit=commit, brokers=brokers, before=before)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("mode", J60_MANUAL_MODES)
    async def test_transfer_whose_receiving_leg_has_a_negative_cost_is_refused(self, world, mode, commit):
        """RED until J-60: a TRANSFER pair source → dest whose receiving leg (create 1) carries −1 EUR, with no mode or in
        ``manual``, gets one ``costBasisNegative`` on create 1, ``ref_id`` None, and nothing else: the row stays in the batch,
        so its pair is not broken — no ``linkUuidPairCount`` on the giving leg —; not committed, nothing written."""
        giving, receiving = _created_pair(world, cost_basis_mode=mode)
        receiving["cost_basis_override"] = _cost_sent(J60_NEGATIVE_COST)
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _j60_as_the_endpoint(world, commit=commit, creates=[giving, receiving])

        what = f"a TRANSFER pair source → dest whose receiving leg (create 1) carries a manual cost of {J60_NEGATIVE_COST.amount} {EUR} ({_j60_mode(mode)})"
        await _assert_cost_basis_negative(world, response, row=("create", 1, None), what=what, commit=commit, brokers=brokers, before=before)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    async def test_adjustment_out_at_a_negative_cost_is_refused_as_any_cost_on_its_side(self, world, commit):
        """RED until N78-1: an ADJUSTMENT −5 on ``source`` — which holds the ``world``'s 10 units, so it does not go short —
        at a cost of −1 EUR, no mode. Its side takes no cost at all: one ``costBasisNotAllowed`` on create 0, refused at the
        parse — so no ``costBasisNegative``, the sign never read —, and nothing else; not committed, nothing written.

        Before N78-1 (J-60, the giving side then carrying decision 47's handover cost): one ``costBasisNegative`` on create
        0, ``ref_id`` None."""
        assert not cost_basis_allowed(TransactionType.ADJUSTMENT, -ADJUSTMENT_QUANTITY), "precondition broken: TX_TYPE_METADATA must refuse a cost basis on an ADJUSTMENT's giving side"
        created = {**_created_adjustment(world, broker=world.source, quantity=-ADJUSTMENT_QUANTITY), "cost_basis_override": _cost_sent(J60_NEGATIVE_COST)}
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _j60_as_the_endpoint(world, commit=commit, creates=[created])

        views = [(issue.operation, issue.index, issue.code) for issue in response.issues]
        assert (response.committed, views) == (False, [("create", 0, COST_BASIS_NOT_ALLOWED)]), (
            f"N78-1: an ADJUSTMENT -{ADJUSTMENT_QUANTITY} on source created at a cost of {J60_NEGATIVE_COST.amount} {EUR} (no mode) takes no cost, so it must be refused with exactly "
            f"{COST_BASIS_NOT_ALLOWED} on create 0 ({_endpoint(commit)}); today {await _j60_today(world, response, 'create', 0)}"
        )
        changed = _changed(before, await _raw_rows(world, brokers))
        assert changed == {}, f"N78-1: the refused batch changed rows of the test's brokers (before, after): {changed}"


class TestJ60ANegativeManualCostOnAnUpdate:
    """J-60 — RED until its cure: an update that sends a manual cost basis below 0 is refused on its own row, ``ref_id`` the
    row. An update is checked when it sends the cost, as ``check_decimal_limits`` reads it — whether or not the cost changes
    (the DERIVED red) —, never when it leaves it out (the guard
    ``test_notes_or_tags_edit_of_a_row_stored_at_a_negative_cost_commits_and_keeps_it``). Today each commits, and /validate
    answers clean."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("mode", J60_MANUAL_MODES)
    @pytest.mark.parametrize("shape", SHAPES)
    async def test_update_setting_a_negative_cost_is_refused(self, world, shape, mode, commit):
        """RED until J-60: ``{id, cost_basis_override: −1 EUR}`` — with no mode, as the app's diff sends a manual cost, or in
        ``manual`` — on a TRANSFER receiving leg (sent alone) or an ADJUSTMENT +5 stored at 42 EUR (``_store``) gets one
        ``costBasisNegative`` on update 0, ``ref_id`` the row; not committed, the row keeps its 42 EUR. Today it holds −1."""
        stored = await _store(world, shape, cost=STORED_COST)
        subject_id = stored.subject.id
        update = {"id": subject_id, "cost_basis_override": _cost_sent(J60_NEGATIVE_COST)}
        if mode is not None:
            update["cost_basis_mode"] = mode
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _j60_as_the_endpoint(world, commit=commit, updates=[update])

        what = f"an update setting a manual cost of {J60_NEGATIVE_COST.amount} {EUR} ({_j60_mode(mode)}) on the {J60_SHAPE_LABELS[shape]} id={subject_id}, stored at {STORED_COST.amount} {STORED_COST.code}"
        await _assert_cost_basis_negative(world, response, row=("update", 0, subject_id), what=what, commit=commit, brokers=brokers, before=before)

    @pytest.mark.asyncio
    async def test_update_resending_unchanged_the_negative_cost_a_row_stores_is_refused(self, world):
        """RED until J-60, DERIVED from «an update is checked when it sends the cost»: an ADJUSTMENT +5 an older version
        stored at −1 EUR, and an update sending its new notes with its cost, −1 EUR, unchanged — the whole row sent back, as
        an API client may; the app's diff never re-sends an unchanged cost (``buildUpdateDiff``). Refused: one
        ``costBasisNegative`` on update 0, ``ref_id`` the row; not committed, the notes not written. The analysis of 20/10
        lists it among what J-60 declares («un client dell'API che rimanda la riga intera … viene rifiutato»): it tells a
        check of the cost sent from one of the cost changed. Drop it if the stored value is to be compared. Today it commits."""
        stored = await _store(world, "adjustment_in", cost=J60_NEGATIVE_COST)
        row_id = stored.subject.id
        stored_before = await _stored_cost(world, row_id)
        assert stored_before == (J60_NEGATIVE_COST.amount, J60_NEGATIVE_COST.code), f"scaffold: the ADJUSTMENT id={row_id} must be stored at {J60_NEGATIVE_COST.amount} {EUR}, or the cost re-sent is a change; it holds {_show(stored_before)}"
        update = {"id": row_id, "description": f"{world.marker} notes edited", "cost_basis_override": _cost_sent(J60_NEGATIVE_COST)}
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _j60_as_the_endpoint(world, commit=True, updates=[update])

        what = f"an update re-sending, unchanged, the cost of {J60_NEGATIVE_COST.amount} {EUR} the ADJUSTMENT +{ADJUSTMENT_QUANTITY} id={row_id} stores, with new notes"
        await _assert_cost_basis_negative(world, response, row=("update", 0, row_id), what=what, commit=True, brokers=brokers, before=before)


class TestJ60ANegativeCostAPromoteResolves:
    """J-60 — RED until its cure: the cost basis a promote resolves (``resolved_fields.cost_basis_override``, the merge
    modal's choice) is the user's too, read where ``check_decimal_limits`` reads it (``_promote_cost_amount``): below 0 it
    is refused on the promote's index, ``ref_id`` None."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    async def test_promote_resolving_a_negative_cost_is_refused(self, world, commit):
        """RED until J-60: two saved ADJUSTMENTs — −4 on ``source`` without a cost, +4 on ``dest`` at 42 EUR — promoted into a
        TRANSFER with ``resolved_fields.cost_basis_override`` −1 EUR get one ``costBasisNegative`` on promote 0, ``ref_id``
        None; not committed, both rows as they were: ADJUSTMENTs, unlinked, the +4 at its 42 EUR. Today the promote commits
        and the receiving leg holds −1 EUR (``_apply_promote_cost_basis``); /validate answers clean."""
        giving = _stored_row(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=-TRANSFER_QUANTITY)
        receiving = _stored_row(world, broker=world.dest, tx_type=TransactionType.ADJUSTMENT, quantity=TRANSFER_QUANTITY, cost=STORED_COST)
        world.session.add_all([giving, receiving])
        await world.session.flush()
        giving_id, receiving_id = giving.id, receiving.id
        promote = {"id_a": giving_id, "id_b": receiving_id, "resolved_fields": {"cost_basis_override": _cost_sent(J60_NEGATIVE_COST)}}
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _j60_as_the_endpoint(world, commit=commit, promotes=[promote])

        what = f"a promote of the ADJUSTMENTs id={giving_id} (-{TRANSFER_QUANTITY}) and id={receiving_id} (+{TRANSFER_QUANTITY}, at {STORED_COST.amount} {STORED_COST.code}) into a TRANSFER, resolving a cost of {J60_NEGATIVE_COST.amount} {EUR}"
        await _assert_cost_basis_negative(world, response, row=("promote", 0, None), what=what, commit=commit, brokers=brokers, before=before)


class TestJ60ANegativeCostDoesNotStopTheBatch:
    """J-60 — RED until its cure for its ``costBasisNegative``, a guard for the other refusal: the sign's check does not stop
    the batch, unlike the integer digits and the dates (``execute_batch``), so a row at a negative cost gets its other
    refusals in the same answer — one a stage before the check finds, and one only the batch's last stage finds, which is
    there only if the check let the batch run on."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("beside", J60_BESIDE_CASES)
    async def test_a_negative_cost_comes_with_the_rows_other_refusal(self, world, beside, commit):
        """A row at −1 EUR, no mode, also refused for something else — on itself or on its pair's other leg — gets both
        issues in one answer; not committed, nothing written.

        ``decimal-places``: an ADJUSTMENT +0.12345678901 on ``dest``, 11 decimal places where a quantity keeps 10 —
        ``decimalPlacesExceeded`` on ``quantity``, from ``check_decimal_limits``, which does not stop the batch either; both
        issues on create 0. ``short-balance``: a TRANSFER pair source → dest of 15 units, its receiving leg (create 1) at −1
        EUR; ``source`` holds 10 and refuses shorting — ``balanceAssetNegative`` on the giving leg (create 0), from the
        balance replay, the batch's last stage: the case that tells a check that runs on from one that stops.

        N78-1 (the developer's decision, 21/10/2026): ``short-balance`` used to be an ADJUSTMENT −5 on ``dest`` at a handover
        cost of −1. An ADJUSTMENT taking units out takes no cost at all since, and that row is refused at the parse with
        ``costBasisNotAllowed`` alone, before the balance replay
        (``test_adjustment_out_at_a_negative_cost_is_refused_as_any_cost_on_its_side``): the subject — a negative cost
        beside a refusal only the last stage finds — moved to a TRANSFER's receiving leg, a side that takes a cost.
        """
        if beside == "decimal-places":
            limit = decimal_limit_issue(J60_QUANTITY_11_DECIMALS, Transaction, "quantity")
            digits = integer_digits_issue(J60_QUANTITY_11_DECIMALS, Transaction, "quantity")
            assert (limit[0] if limit else None, digits) == (
                DECIMAL_PLACES_EXCEEDED,
                None,
            ), f"precondition broken: {J60_QUANTITY_11_DECIMALS} must be refused for its decimal places, its integer digits within the limit (past it the batch stops early); decimal_limit_issue gives {limit}, integer_digits_issue {digits}"
            other = {"operation": "create", "index": 0, "ref_id": None, "code": DECIMAL_PLACES_EXCEEDED, "field": "quantity"}
            creates = [{**_created_adjustment(world, broker=world.dest, quantity=J60_QUANTITY_11_DECIMALS), "cost_basis_override": _cost_sent(J60_NEGATIVE_COST)}]
            row, what = ("create", 0, None), f"an ADJUSTMENT +{J60_QUANTITY_11_DECIMALS} on dest at a manual cost of {J60_NEGATIVE_COST.amount} {EUR}"
        else:
            moved = BUY_QUANTITY + ADJUSTMENT_QUANTITY
            assert world.source.allow_asset_shorting is False, "precondition broken: source must refuse shorting, or moving more than it holds is no refusal"
            other = {"operation": "create", "index": 0, "ref_id": None, "code": BALANCE_ASSET_NEGATIVE, "field": None}
            creates = _created_pair(world)
            creates[0]["quantity"], creates[1]["quantity"] = str(-moved), str(moved)
            creates[1]["cost_basis_override"] = _cost_sent(J60_NEGATIVE_COST)
            row, what = ("create", 1, None), f"a TRANSFER of {moved} units out of source, which holds {BUY_QUANTITY}, its receiving leg at a manual cost of {J60_NEGATIVE_COST.amount} {EUR}"
        brokers = await _world_brokers(world)
        before = await _raw_rows(world, brokers)

        response = await _j60_as_the_endpoint(world, commit=commit, creates=creates)

        await _assert_cost_basis_negative(world, response, row=row, what=f"{what}, also refused with {other['code']}", commit=commit, brokers=brokers, before=before, beside=(other,))


class TestJ60GuardsWhatTheSignLeavesAlone:
    """J-60 — guards, green today and after the cure: what the sign's check leaves alone. A Manual cost of 0 — a gift, the
    new shares of a split —, ``-0`` included: the check reads the value, not the minus sign of the text. An Auto cost, the
    batch's own average, recomputed: never checked, whatever the payload carries or (DERIVED) the pool averages. A row an
    older version stored at a negative cost, while an update leaves its cost out: the app sends differences only
    (``buildUpdateDiff``), so the row stays editable until its cost is touched."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("text", J60_ZERO_TEXTS)
    @pytest.mark.parametrize("shape", SHAPES)
    async def test_a_manual_cost_of_zero_commits(self, world, shape, text):
        """Guard: an ADJUSTMENT +5 on ``dest`` (create 0), or the receiving leg of a TRANSFER pair source → dest (create 1),
        at a Manual cost of ``text`` EUR, no mode, commits with no issue and stores 0 EUR. ``-0`` parses to ``Decimal("-0")``,
        which is not below 0. The stored zero is compared as a number, never by its sign: whether the database keeps the
        minus of a REAL −0.0 is not J-60's business."""
        if shape == "transfer_in":
            creates, subject_index = _created_pair(world), 1
        else:
            creates, subject_index = [_created_adjustment(world, broker=world.dest, quantity=ADJUSTMENT_QUANTITY)], 0
        creates[subject_index]["cost_basis_override"] = {"code": EUR, "amount": text}
        parsed = transaction_schemas.TXCreateItem.model_validate(creates[subject_index]).cost_basis_override.amount
        assert parsed == 0, f"scaffold: the cost basis {text!r} must parse to a zero; it parses to {parsed!r}"

        response = await _j60_as_the_endpoint(world, commit=True, creates=creates)

        assert (response.committed, response.issues) == (True, []), f"J-60: a Manual cost of {text!r} {EUR} (parsed {parsed!r}) on the {J60_SHAPE_LABELS[shape]} is not below 0, so it must commit; it was refused: {_render(response.issues)}"
        stored = await _stored_cost(world, _created_id(response, subject_index))
        assert stored == (ZERO_COST.amount, ZERO_COST.code), f"The {J60_SHAPE_LABELS[shape]} sent at a Manual cost of {text!r} {EUR} was committed with {stored[0]!r} {stored[1]}, not 0 {EUR}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    @pytest.mark.parametrize("mode", AUTO_MODES)
    @pytest.mark.parametrize("case", J60_AUTO_CASES)
    async def test_an_auto_row_sending_a_negative_amount_takes_its_average(self, world, case, mode, commit):
        """Guard: an Auto row whose payload carries a cost basis of −1 EUR — in ``auto`` or ``auto-detail``: the currency hint,
        its amount below 0, as the form would send back the preview's average over a pool of old negative costs — is not
        refused for its sign. The batch reads only the hint's currency and computes the amount (``auto_cost.py``), which the
        digit limits skip as well (``_decimal_limit_values``). No issue, and the row's cost is ``source``'s average, the
        ``world``'s BUY, 100 EUR — answered on /validate, answered and saved on /commit (``_assert_takes``): an ADJUSTMENT +5
        on ``source``, the receiving leg of a TRANSFER pair created, or stored at 42 EUR and recomputed by an update."""
        batch = await _j60_auto_batch(world, case, mode)

        response = await _j60_as_the_endpoint(world, commit=commit, creates=batch.creates, updates=batch.updates)

        await _assert_takes(world, response, batch, cost=UNIT_COST, commit=commit, what=f"J-60: an Auto {case} ({mode}) whose payload carries a cost basis of {J60_NEGATIVE_COST.amount} {EUR}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("commit", ENDPOINTS)
    async def test_an_auto_row_over_a_pool_averaging_below_zero_gets_no_cost_basis_negative(self, world, commit):
        """Guard, DERIVED from «an Auto cost is the batch's own average, never checked» — the analysis's reason to keep the
        check out of ``validate_cost_basis``, which runs once the Auto cost is written. ``source`` holds the ``world``'s 10
        units bought for 1 000 EUR and 10 an older version stored at −300 EUR a unit (an ADJUSTMENT +10 planted before the
        move, ``_n88_plant``): an ADJUSTMENT +5 in ``auto`` averages (1 000 − 3 000) / 20 = −100 EUR. The batch answers no
        ``costBasisNegative``: that refusal asks the user for a cost of 0 or more, which an Auto row cannot give. What else
        becomes of an average below 0 — today it is saved, or answered, at −100 EUR — is J-60's residue, not pinned here."""
        await _n88_plant(world, broker=world.source, tx_type=TransactionType.ADJUSTMENT, quantity=BUY_QUANTITY, cost=J60_LEGACY_NEGATIVE_COST)
        pool = await _pool(world, world.source)
        assert pool == [
            (TransactionType.BUY, BUY_QUANTITY, -WORLD_PAID, None),
            (TransactionType.ADJUSTMENT, BUY_QUANTITY, Decimal("0"), J60_LEGACY_NEGATIVE_COST.amount),
        ], f"precondition broken: source's pool on {MOVE_DAY} must be the BUY of {BUY_QUANTITY} units for {WORLD_PAID} EUR and an ADJUSTMENT +{BUY_QUANTITY} stored at {J60_LEGACY_NEGATIVE_COST.amount} EUR a unit: {pool}"
        average = _average(WORLD_PAID + BUY_QUANTITY * J60_LEGACY_NEGATIVE_COST.amount, 2 * BUY_QUANTITY)
        assert average == Decimal("-100"), "the oracle: (1 000 − 3 000) / 20"
        created = _created_adjustment(world, broker=world.source, quantity=ADJUSTMENT_QUANTITY, cost_basis_mode="auto")

        response = await _j60_as_the_endpoint(world, commit=commit, creates=[created])

        refused = [issue for issue in response.issues if issue.code == COST_BASIS_NEGATIVE]
        assert refused == [], f"J-60: an Auto cost is the batch's own average, never checked for its sign, so over a pool averaging {average} {EUR} the Auto row gets no {COST_BASIS_NEGATIVE}: {_render(refused)}; {_verdict(response, 'create', 0)}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", SHAPES)
    @pytest.mark.parametrize("edit", EDITS)
    async def test_notes_or_tags_edit_of_a_row_stored_at_a_negative_cost_commits_and_keeps_it(self, world, edit, shape):
        """Guard: a TRANSFER receiving leg — edited with its giving leg: a pair keeps one description and one set of tags —
        or an ADJUSTMENT +5, stored at −1 EUR straight into the session (``_store``), as an older version left it. A
        notes-only or tags-only edit, the cost key left out as the app's diff leaves it, commits; the edit lands, and the row
        keeps its −1 EUR: nothing repaired, nothing refused. Its cost is checked the day an update sends one
        (``test_update_setting_a_negative_cost_is_refused``)."""
        stored = await _store(world, shape, cost=J60_NEGATIVE_COST)
        subject_id = stored.subject.id
        stored_before = await _stored_cost(world, subject_id)
        assert stored_before == (J60_NEGATIVE_COST.amount, J60_NEGATIVE_COST.code), f"scaffold: the {J60_SHAPE_LABELS[shape]} id={subject_id} must be stored at {J60_NEGATIVE_COST.amount} {EUR}, or an edit that keeps it proves nothing; it holds {_show(stored_before)}"
        updates = _edit(stored.rows, edit, world.marker)
        assert not any(_sends_the_cost(update) for update in updates), f"scaffold: no update may send cost_basis_override, or the cost is touched: {updates}"

        response = await _commit_as_the_endpoint(world, updates=updates)

        assert response.committed is True and response.issues == [], f"J-60: a {edit}-only edit of the {J60_SHAPE_LABELS[shape]} stored at {J60_NEGATIVE_COST.amount} {EUR} leaves its cost out, so it is not checked and must commit; it was refused: {_render(response.issues)}"
        assert _update_results(response) == [(index, (row.id,), "success") for index, row in enumerate(stored.rows)], f"Committed, but not every row was updated: {response.results}"
        _assert_edit_landed(stored.rows, edit, world.marker)
        stored_after = await _stored_cost(world, subject_id)
        assert stored_after == stored_before, f"J-60 repairs nothing: after a {edit}-only edit the {J60_SHAPE_LABELS[shape]} id={subject_id} holds {_show(stored_after)}, not the {_show(stored_before)} it was stored at"


class TestJ60TheCodeAndItsMessage:
    """J-60 — RED until its cure: the code the app maps to its message, ``costBasisNegative``, listed by ``GET
    /transactions/types``, and its message in the app's four languages. The code and its key go in together: W-B69's gate
    ``test_every_code_has_its_message_in_every_language`` holds every ``TXValidationCode`` to its message, so the member
    alone turns that gate red."""

    def test_tx_validation_code_has_cost_basis_negative(self):
        """RED until J-60: ``TXValidationCode.COST_BASIS_NEGATIVE == "costBasisNegative"`` — the app maps a refusal's code to
        ``transactions.errors.<code>``."""
        member = getattr(TXValidationCode, "COST_BASIS_NEGATIVE", None)

        assert member is not None and member.value == COST_BASIS_NEGATIVE, f"J-60: TXValidationCode.COST_BASIS_NEGATIVE is {member!r}: expected a member of value {COST_BASIS_NEGATIVE!r}"

    def test_transaction_types_lists_cost_basis_negative(self):
        """RED until J-60: the response ``GET /transactions/types`` builds (``get_transaction_types``) lists
        ``costBasisNegative`` in ``validation_codes`` (``VALIDATION_CODE_METADATA``)."""
        response = TXTypesResponse(transaction_types=list(TX_TYPE_METADATA.values()), event_types=EVENT_TYPE_METADATA)

        listed = sorted(info.code for info in response.validation_codes)

        assert COST_BASIS_NEGATIVE in listed, f"J-60: GET /transactions/types does not list {COST_BASIS_NEGATIVE!r} in validation_codes: {listed}"

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    def test_cost_basis_negative_has_its_message(self, language):
        """RED until J-60: ``transactions.errors.costBasisNegative`` is a non-empty text in ``language``, read without the
        English fallback (``load_catalog(language, fallback=False)``): what the sources translate. Its words are the
        developer's approved texts, never asserted here."""
        messages = flatten(load_catalog(language, fallback=False))

        assert _error_text(messages, COST_BASIS_NEGATIVE), f"J-60: transactions.errors.{COST_BASIS_NEGATIVE} has no {language} message, so the app would show the backend's raw English"
