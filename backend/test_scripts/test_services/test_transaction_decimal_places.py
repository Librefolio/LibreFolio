"""
C-97a — how many decimal places a transaction keeps, and where a batch refuses more (workstream W, GitHub issue #43:
crypto users need more decimal places).

Today. ``Transaction.quantity`` is ``Numeric(18, 6)``: SQLite stores the double the ORM binds, and SQLAlchemy rounds it
to 6 decimals when it reads it back, so a BUY of 0.12345678 BTC reads 0.123457, and nothing says so. Nothing limits the
decimal places of a value on input either: ``TXCreateItem`` and ``TXUpdateItem`` accept any, the batch saves them, the
read rounds them. The balances are SQL sums of those doubles, read back at 6 decimals too.

The contract (the developer's decisions, 16/10; D5 and D6 the coordinator's, 16/10 17:05):

1. A quantity keeps up to 10 decimal places and reads back exactly (``RealDecimal(22, 10)``: the shortest decimal of the
   stored double, at most 15 significant digits, padded to 6 decimals when it has fewer, so ``10`` still reads
   ``10.000000``). A cash amount stays at 6. The manual cost basis is a PER-UNIT price (``financial_math/average_cost.py``
   multiplies it by the quantity), so its column becomes ``RealDecimal(24, 12)`` and it keeps up to 12 decimal places
   (D5): a PEPE bought at 0.0000034573 EUR a unit keeps that cost.
2. Over the limit the batch refuses — it never rounds — at confirmation, ``POST /transactions/validate`` and ``/commit``
   (``execute_batch``), and not at BRIM parse (decision D2; a value a BRIM plugin computes is rounded by the plugin,
   D6, outside this file). The stage ``check_decimal_limits``, right after ``parse_inputs``, adds for each create and
   each update one issue per field over its limit, the scale read from the model — ``quantity`` (10), ``cash.amount``
   (6), ``cost_basis_override`` (its amount, 12): ``decimalPlacesExceeded`` with ``{"max": 10 | 6 | 12}`` when
   the decimals, trailing zeros not counted, exceed the field's max, otherwise ``significantDigitsExceeded`` with
   ``{"max": 15}`` past 15 significant digits (decision D1). On the row's ``operation`` and ``index``, ``ref_id`` the
   updated id (None for a create), with an English ``error`` that names the field. The batch is not committed, and the
   row stays in it, so a linked pair is not broken by the refusal. Both codes are members of ``TXValidationCode``, so
   ``GET /transactions/types`` lists them in ``validation_codes``.
3. The balances are summed in Python with exact ``Decimal`` (``financial_math``'s ``position_quantities`` and
   ``native_balances``): two BUYs of 99999.1234567891 hold exactly 199998.2469135782 in ``get_asset_holdings`` and in
   ``get_balances_at_end_of`` — today 199998.246914, and 199998.2469135780 with the new column under an SQL sum. The
   cash balances keep today's results.
4. The asset list reads an asset as held where the exact sum of its quantities on a broker exceeds
   ``QUANTITY_DUST_THRESHOLD``.
5. An Auto cost basis is not checked. With ``cost_basis_mode`` ``auto`` or ``auto-detail`` the backend recomputes the
   amount — the average of the source pool (``_compute_wac_for_auto_items``, ``auto_cost.py``) — and reads only the
   currency of the ``cost_basis_override`` sent, so ``check_decimal_limits`` leaves that amount out
   (``_decimal_limit_values``): an Auto create or update is accepted whatever amount it carries, and the row holds the
   Auto cost, not that amount. A manual cost basis — ``manual``, or no mode with an explicit override — stays checked:
   over the limit it is refused, never rounded (D2). Found by the E2E «TRANSFER (asset) create → commit (dual brokers +
   asset + qty)» (``frontend/e2e/transactions/tx-commit-all-types.spec.ts:532``): the Form sends back the preview's
   average, a repeating decimal (100 / 3) in full, and the commit was refused with ``decimalPlacesExceeded``
   ``{"max": 12}`` on ``cost_basis_override``.
6. R13-SEC2 (W-B58, E's security review of 17/10): the integer digits. A quantity and a cash amount keep at most 15
   digits before the decimal point (``REAL_SIGNIFICANT_DIGITS``: the coordinator's decision N63, 17/10), a manual cost
   basis — a per-unit price — the ``precision - scale`` of its column, 12 (``max_integer_digits``); past that
   ``check_decimal_limits`` adds ``integerDigitsExceeded`` with ``{"max": 15}`` or ``{"max": 12}`` on the field: the
   third check, after the decimal places and the significant digits, so a value over two limits keeps the code of the
   first. The promotion's ``resolved_fields.cost_basis_override`` (a ``{code, amount}`` currency dict) is checked against
   the column ``cost_basis_override`` too: the issue sits on ``operation="promote"``, the promote's index,
   ``field="cost_basis_override"``, with any of the three codes and its ``{"max": N}``. A checked value past its
   column's integer digits — whichever code it gets — stops the batch right after ``check_decimal_limits``: the later
   stages compute with the values (products, averages, the float a REAL takes), and a value of a million digits
   overflows them. So such a batch raises nothing (no 500), every issue it answers carries a code (none reads «Balance
   validation error»), and nothing is saved. ``TXValidationCode.INTEGER_DIGITS_EXCEEDED = "integerDigitsExceeded"``,
   listed by ``GET /transactions/types``.
7. R13-SEC2: a row the file holds as a REAL today's read cannot turn into a Decimal — a quantity of 1e60, an infinite one
   (SQLite reads the literal ``1e999`` as +inf), an infinite close — no longer breaks anyone: ``list_assets``, which reads
   every user's quantities, raises nothing; the infinite quantity loads as None and its row can be deleted through the
   batch; the quantity of 1e60 loads as 1E+60; the infinite close loads as None.
8. W-B60 (17/10, the follow-up of W-B58): a cash amount reads back exactly. ``Transaction.amount`` was a plain
   ``Numeric(18, 6)``, read through ``'%.6f'`` of the stored double, so from about 11 integer digits the double's noise
   landed in the 6 decimals; it becomes ``RealDecimal(18, 6)`` — same declaration, same DDL, no migration. A BUY committed
   through the batch with a cash amount of -123456789012.345 EUR (15 significant digits, 12 before the point: within
   N63's 15) reads back -123456789012.345000, column by column and through the service (``get_by_ids``), and the control
   totals (``compute_control_totals``: what a backup records and a restore checks) give its broker's EUR line as
   -123456789012.345. What reads well today keeps its form: -100 EUR reads -100.000000.
9. R13-SEC7-3 (E's R13-SEC7, 17/10; night decision N74): the date of a transaction is checked at write,
   ``1900-01-01 <= date <= tomorrow`` — lot N74 (Fineco, safe rows; decision N74 as re-decided, 19/10) moves the last day
   from today + 1 year (UTC) to the server's tomorrow: ``transaction_date_bounds()`` takes no argument and returns
   ``EARLIEST_RANGE_START`` .. ``latest_range_end()`` (both ``utils/datetime_utils``): 1900-01-01 .. the server's local
   date + 1 day, the one day of slack for a user whose today is already the server's tomorrow (a price or a rate written
   by hand has the same last day, N83). A new batch
   stage next to ``check_decimal_limits`` covers the creates (``TXCreateItem.date``), the
   updates (``TXUpdateItem.date``, when given) and the promotes (``resolved_fields["date"]``, an ISO string): out of
   range, the row gets ``dateOutOfRange`` on ``field="date"``, ``params={"min": "1900-01-01", "max": <ISO of the server's
   tomorrow>}``, and the batch stops right after the access check, as for the integer digits: not committed, nothing
   written, no exception (a row of 0001-01-01 made the replay walk every day since year one; one of 9999-12-31 made it
   overflow). ``TXValidationCode.DATE_OUT_OF_RANGE = "dateOutOfRange"``, listed by ``GET /transactions/types``. And the
   bound R13-SEC7-3 puts on every ``Currency`` amount at the boundary (``adjusted()`` within [-100, 100]) reaches the
   batch's own parse: a cash amount past it is refused by ``_parse_lenient`` (``value_error`` on ``cash.amount``), before
   any limit of rule 6 is read. So does a promote's resolved cost basis that ``Currency`` refuses — past the bound, or no
   number at all: it is the one issue of its promote, ``value_error`` on ``cost_basis_override.amount``, no params, and
   the batch stops; no ``ValidationError`` leaves the batch.
10. H-41 (same lot, R13-SEC7-3): the fields a promote resolves are typed like a create's. ``TXPromoteBatchItem
    .resolved_fields`` becomes the ``StrictModel`` ``TXPromoteResolvedFields``: ``description`` a text of at most 500
    characters, ``tags`` through ``validate_tags_list`` (a text split on its commas, a list's items as texts), ``date`` a
    date (an explicit null refused), ``cost_basis_override`` a ``Currency``, no other key (``extra_forbidden``). A key left
    out leaves the rows alone; an explicit null clears ``description``, ``tags`` and ``cost_basis_override``, as before. A
    refusal is an issue of the batch's lenient parse on the promote — pydantic's type as the code, ``field`` the merged
    field's own name without ``resolved_fields.`` (``description``, ``tags``, ``date``, ``cost_basis_override``,
    ``cost_basis_override.code``, an unknown key's name), ``params`` pydantic's own context when it is plain data (W-B70,
    the coordinator's D-W70-1, 17/10: ``{max_length}``, a date's parsing error ``{error}``, ``{class_name}``), None
    otherwise — and that promote is not applied: not committed, nothing saved, nothing raised.
11. N78 (W-B72; night decision N78), the promote's side of a cost basis on a type and side that take none: a resolved
    non-null ``cost_basis_override`` where NEITHER leg can take one under the target type — ``cost_basis_allowed(target,
    leg.quantity)`` False for both, a WITHDRAWAL and a DEPOSIT promoted into a CASH_TRANSFER or an FX_CONVERSION — is
    refused: one ``costBasisNotAllowed`` on the promote, ``field`` ``cost_basis_override``, ``params`` ``{type: <target>,
    qty: …}``, and the promote is not applied. Today ``_apply_promote_cost_basis`` puts it on both legs of such a pair. N78's
    creates, updates, messages and gate are ``test_transaction_cost_basis_rule.py``'s.

Reds — fail today, pass once the contract holds:

- ``TestQuantitiesKeepTenDecimals``: a BUY, a SELL and an ADJUSTMENT +q of 0.12345678 and of 0.1234567891 units created
  through the batch, and a quantity updated to 0.1234567891, read back from the database as sent (today 0.123457; the
  batch commits, which each test checks first, so the red is the read-back);
- ``TestOverTheLimitIsRefusedAtConfirmation``: a create over a limit is refused on its own row, on ``/validate`` and on
  ``/commit``, with the exact ``(operation, index, ref_id, code, field, params)``; an update too, ``ref_id`` its id;
  nothing is written or changed (today the batch commits and the read rounds). A linked pair one leg of which is over a
  limit is refused on that leg alone, both legs still in the batch, no broken pair reported — a RED, not a guard: before
  ``check_decimal_limits`` the pair committed whole, with no issue at all. A cost basis is over the limit at 13 decimals,
  ``{"max": 12}`` (D5): red until its column is ``RealDecimal(24, 12)``, the check reading 6 from today's model;
- ``TestAPerUnitCostKeepsTwelveDecimals`` (D5): a received TRANSFER and an ADJUSTMENT +1 at a manual per-unit cost of
  0.0000034573 EUR are saved, and the cost reads back exactly (today refused with ``{"max": 6}``; before the check,
  saved and read back 0.000003);
- ``TestAnAutoCostBasisIsNotChecked`` (rule 5): a received TRANSFER, an ADJUSTMENT +1 and an update of a stored
  ADJUSTMENT +1, in ``auto`` or ``auto-detail``, whose cost basis carries the pool's repeating average — 100 / 3 as the
  preview answers it (26 decimals), or 1000000 / 3 as a double prints it (16 significant digits) — are accepted on
  ``/validate`` and on ``/commit``; committed with an amount that is not the pool's average (125 / 3), the row holds the
  Auto cost, 100 / 3 read back 33.333333333333 EUR, not the amount sent (today refused on its row,
  ``decimalPlacesExceeded`` ``{"max": 12}`` or ``significantDigitsExceeded`` ``{"max": 15}``, and nothing is written);
- ``TestBalancesAreSummedExactly.test_two_buys_of_ten_decimals_sum_exactly`` (today 199998.246914);
- ``TestTheCodesAreListed``: ``TXValidationCode`` and ``GET /transactions/types``'s ``validation_codes`` carry both codes;
- ``TestTooManyIntegerDigitsAreRefused`` (rule 6, R13-SEC2): a create past its integer digits — a quantity of 1E+60,
  of 16 digits or of 1E+400, or a cash amount of -1E+15 (``{"max": 15}``), a cost basis of 1E+60 or of 13 digits
  (``{"max": 12}``) — is refused on its row with exactly ``integerDigitsExceeded`` on ``/validate`` and ``/commit``,
  nothing written; an update of a quantity to 1E+60 too (today the 16 digits, the -1E+15 EUR, the 13-digit cost and the
  update pass unrefused, and the creates of 1E+60 and 1E+400 make ``validate_cost_basis`` raise as it reloads the row: a
  500). On an ordinary broker (no overdraft, no shorting), through ``/validate`` and ``/commit``: a BUY of 1E+1000000
  units gets ``integerDigitsExceeded`` ``{"max": 15}`` on its quantity and raises nothing (before W-B58,
  ``decimal.Overflow`` in ``decimal_limit_issue``'s ``normalize``: a 500); one of -1E+1000000 EUR — the case
  ``c-cash-amount--1E+1000000``, re-pinned by R13-SEC7-3 (rule 9): its cash amount is a ``Currency``, bounded at the
  boundary — is refused by the batch's lenient parse instead, ``value_error`` on ``cash.amount``, no params, an English
  error naming the exponent, and gets no limit issue (red until the bound: it still reaches ``check_decimal_limits``
  and gets ``integerDigitsExceeded``), raising nothing, not committed, nothing saved; a BUY of 400 ones keeps
  ``significantDigitsExceeded`` ``{"max": 15}`` on its quantity and gets no issue without a code (today the row goes on
  as a float inf, and ``validate_cost_basis`` raises ``TypeError`` reloading it, before the balance replay could add its
  raw «Balance validation error»); nothing is saved;
- ``TestAPromotedCostBasisIsChecked`` (rule 6): a promote whose resolved cost basis has 13 decimals, 16 significant
  digits, 13 integer digits, or is 1E+60, is refused on its own index (1, behind a valid promote) with the code and the
  ``{"max": N}`` of its limit (12 for the integer digits), nothing changed (today both promotes commit, the cost basis
  unchecked);
- ``TestCorruptRowsAreReadWithoutRaising`` (rule 7): today ``InvalidOperation`` (the REAL 1e60) and ``TypeError``
  (the REAL inf) on every read, the asset list's and the delete's included;
- ``TestACashAmountReadsBackExactly`` (rule 8, W-B60): today the BUY's cash amount reads back -123456789012.345001, and
  the control totals give -123456789012.345001: the double's noise;
- ``TestTheCodesAreListed``: ``TXValidationCode.INTEGER_DIGITS_EXCEEDED``, and ``validation_codes`` lists it.
- ``TestTheDateIsCheckedAtWrite`` (rule 9, R13-SEC7-3): a create dated 1899-12-31, 0001-01-01, the day after tomorrow
  or 9999-12-31 (on ``/validate`` and ``/commit``), an update moving a stored row to 1899-12-31, a promote resolving the
  date 1899-12-31 — each refused on its own row with exactly ``dateOutOfRange`` and its ``{"min", "max"}``, the batch
  stopped before applying anything (no result), nothing written, no exception (today they commit, or the replay refuses
  them for another reason: a codeless «Balance validation error» on 9999-12-31, a short position on 1899-12-31). Lot N74
  re-reds them all: today's refusals carry ``max`` = UTC today + 1 year, not the server's tomorrow, and the day after
  tomorrow commits; ``test_n74_a_create_dated_the_day_after_tomorrow_is_refused_up_to_tomorrow`` says it alone;
- ``TestTheDateFloorIsTheReplayFloor`` (rule 9, MF-SEC8-2): N74's 1900-01-01 is ``EARLIEST_RANGE_START`` of
  ``utils/datetime_utils``, the replay floor, imported — ``transaction_batch_stages`` keeps no ``TRANSACTION_DATE_MIN``
  of its own (today it does, a copy);
- ``TestAPromotedCostBasisCurrencyRefuses`` (rule 9): a promote (index 1, behind a valid one) resolving a cost basis of
  1E+101, 1E+5000000, 0E-999999999 or «abc» EUR, on ``/validate`` and ``/commit``, gets exactly one issue,
  ``value_error`` on ``cost_basis_override.amount``, no params, its English error naming the exponent (the text of «abc»
  not pinned); nothing else, not committed, the four rows unchanged, nothing raised (today 1E+101 and 1E+5000000 get
  ``integerDigitsExceeded`` ``{"max": 12}``, the zero commits, «abc» raises ``ValidationError`` out of the batch);
- ``TestTheResolvedFieldsAreTyped`` (rule 10, H-41): a promote (index 1, behind a valid one) resolving a description of
  123, ``inf``, ["a"] or 501 characters, tags of 123 or ``{"a": 1}``, the date «not-a-date», «2026-02-30» or an explicit
  null, a cost basis «12» or without its code, or the unknown key ``quantity``, on ``/validate`` and ``/commit``, gets
  exactly one issue, ``("promote", 1, <pydantic's type>, <the merged field>, <pydantic's context when plain, else None>)``;
  the pair still reads as the list builds it; nothing else, not committed, the four rows unchanged, nothing raised (today a
  number or ``inf`` as the description commits and the pair's read fails with ``string_type``, a malformed date or tags
  raise out of the batch, ``{"a": 1}`` commits the tag «a», the unknown key is ignored; the two cost bases already get
  their issue since R13-SEC7-3; since H-41, W-B70's red: the four whose context is plain data — 501 characters, the two
  dates, the cost basis «12» — carry no params). Tags «a, b» are stored «a,b» on both rows (today «a,,, ,b»:
  ``tags_to_csv`` joins a text's characters);
- ``TestTheCodesAreListed``: ``TXValidationCode.DATE_OUT_OF_RANGE``, and ``validation_codes`` lists ``dateOutOfRange``.
- ``TestN78APromotedCostBasisWhereNoLegTakesOne`` (rule 11): a WITHDRAWAL/DEPOSIT pair promoted into a CASH_TRANSFER or an
  FX_CONVERSION resolving 12.5 EUR, behind a valid promote, is refused on promote 1 (today it commits, both legs holding
  12.5 EUR).

Guards — green today, and the cure must keep them green:

- ``TestWhatTheLimitLeavesAlone``: trailing zeros are not counted (1.50000000000000 units, a cash amount of
  -150.1000000, a cost basis of 1.5000000000000 commit, and read back as their value); a whole and a 6-decimal quantity
  read back in today's form, ``10.000000`` and ``1.234567``;
- ``TestBalancesAreSummedExactly``: the cash at the end of a day keeps today's results, and the quantities their date
  bounds and exclusions (``as_of``, ``exclude_tx_ids``);
- ``TestTheAssetListReadsHoldingsExactly``: a position bought 0.1 + 0.2 and sold 0.3 is not held, one sold 0.2999 is;
- ``TestBrimParseDoesNotRefuse`` (D2): a BRIM row over a limit is not refused at parse (``BRIMProvider._create_transaction``,
  the constructor every plugin calls): the item is returned with its values as read, and no parse issue is recorded.
  The rounding of D6 is the plugin's, on the values it computes (``round_computed_value``), not this constructor's.
- ``TestAnAutoCostBasisIsNotChecked``'s manual cases (rule 5, D2): the same amounts with ``cost_basis_mode`` ``manual``
  are refused on their row, ``decimalPlacesExceeded`` ``{"max": 12}`` or ``significantDigitsExceeded`` ``{"max": 15}``;
  no mode with an explicit override is pinned by ``TestOverTheLimitIsRefusedAtConfirmation``.
- ``TestTooManyIntegerDigitsAreRefused`` (rule 6): the integer limit is reached, not passed — a BUY of 999999999999999
  units for -999999999999999 EUR (15 digits each), one of 13-digit units for -1E+13 EUR (accepted under N63), a cost
  basis of 999999999999.999 (12 integer digits) commit;
- ``TestAPromotedCostBasisIsChecked`` (rule 6): a promote whose resolved cost basis keeps 12 decimals commits, and the
  receiving leg holds it exactly;
- ``TestACashAmountReadsBackExactly`` (rule 8): cash amounts of -100 and -1234.5 EUR read back -100.000000 and
  -1234.500000, column by column and through the service, as ``Numeric(18, 6)`` reads them today.
- ``TestTheDateIsCheckedAtWrite`` (rule 9): a create dated 1900-01-01, tomorrow (the server's), or an ordinary day
  commits and keeps its date; an update moving a stored row to 1900-01-01 commits.
- ``TestAPromotedCostBasisCurrencyRefuses`` (rule 9): a resolved cost basis of 1E+100 EUR, inside the bound, keeps W-B58's
  ``integerDigitsExceeded`` ``{"max": 12}`` on ``cost_basis_override``, nothing else, on ``/validate`` and ``/commit``.
- ``TestTheResolvedFieldsAreTyped`` (rule 10): accepted on both endpoints, and committed on the second pair by
  ``/commit`` — a description of 500 characters and the tags ["a", "b"] on both rows (stored «a,b»), a date inside N74 on
  both rows, a cost basis of 12.5 EUR on the receiving leg only (decision 47), ``{"tags": ["a"]}`` without touching the
  descriptions, ``{}`` changing nothing; an explicit null clears the description and the tags on both rows; an explicit
  null cost basis clears the receiving leg's, which the TRANSFER then requires (``costBasisRequired`` on promote 1).
- ``TestN78APromotedCostBasisWhereNoLegTakesOne`` (rule 11): an asset pair promoted into a TRANSFER resolving 12.5 EUR, in
  either order, commits with it on the receiving leg only (decision 47); a cash pair resolving an explicit null commits.

Derived — read from the contract's general rule, not in the brief's list; drop them if the rule was meant narrower: a
quantity over both limits gets ``decimalPlacesExceeded`` alone (the "otherwise"); a cash amount past 15 significant
digits gets ``significantDigitsExceeded``; a row over the limit on two fields gets one issue per field.

Ownership. Every test builds its own asset and brokers under a unique marker, in one session rolled back at the end. A
batch runs as the endpoint runs it, its transaction included (``_run_as_the_endpoint``), so a refused batch leaves the
database as it found it, and nothing reaches the lane's database. The corrupt rows of rule 7 are written the same way —
with the ORM, then overwritten by raw SQL — inside that session, and rolled back with it: no other connection ever sees
them.

Run: ``./dev.py test services transaction-decimal-places`` (the action ``services_transaction_decimal_places``).
"""

import sys
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

# Before any app module that reads DATABASE_URL: this lane's test database.
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, PriceHistory, Transaction, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets.assets import FAAinfoFiltersRequest
from backend.app.schemas.brim import BRIMParseOutput
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.batch import TXBatchResponse, TXPromoteResolvedFields, TXValidationCode, TXValidationIssue
from backend.app.schemas.transactions.transactions import TXQueryParams
from backend.app.schemas.transactions.type_metadata import EVENT_TYPE_METADATA, TX_TYPE_METADATA, TXTypesResponse, cost_basis_allowed
from backend.app.services.assets.crud import AssetCRUDService
from backend.app.services.brim.brim_provider import BRIMProvider
from backend.app.services.financial_math.ledger_totals import compute_control_totals
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD
from backend.app.services.transactions import transaction_batch_stages
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils import datetime_utils
from backend.app.utils.datetime_utils import utcnow

EUR = "EUR"
USD = "USD"
# The days of a test: the rows written before the batch, the batch's, and the day after the one a balance is read at.
SEED_DAY = date(2025, 3, 3)
DAY = date(2025, 3, 10)
NEXT_DAY = DAY + timedelta(days=1)

# The two codes of C-97a, compared as strings: TXValidationCode has no member for them yet, and a red must fail when it
# runs, not when it is collected.
DECIMAL_PLACES_EXCEEDED = "decimalPlacesExceeded"
SIGNIFICANT_DIGITS_EXCEEDED = "significantDigitsExceeded"
DECIMAL_CODES = (DECIMAL_PLACES_EXCEEDED, SIGNIFICANT_DIGITS_EXCEEDED)
# The params of a refusal: 10 decimals for a quantity, 6 for a cash amount, 12 for a per-unit cost basis (D5), 15
# significant digits for any of them.
QUANTITY_MAX = {"max": 10}
CASH_MAX = {"max": 6}
COST_MAX = {"max": 12}
DIGITS_MAX = {"max": 15}
# A per-unit cost basis over D5's limit on its decimals alone: 13 decimals, 13 significant digits.
COST_13_DECIMALS = "0.1234567890123"
# A PEPE's per-unit cost: 10 decimals, within D5's 12, which a 6-decimal column reads 0.000003 and refuses.
PEPE_UNIT_COST = "0.0000034573"
# R13-SEC2 (rule 6): the third code, past the digits a column keeps before the decimal point — compared as a string, as
# the two above. The coordinator's decision N63 (17/10): 15 for a quantity and a cash amount (REAL_SIGNIFICANT_DIGITS),
# 12 for a per-unit cost basis (precision - scale of (24, 12)).
INTEGER_DIGITS_EXCEEDED = "integerDigitsExceeded"
QUANTITY_INTEGER_MAX = {"max": 15}
CASH_INTEGER_MAX = {"max": 15}
COST_INTEGER_MAX = {"max": 12}
# Every code of a value over its column's limit: what _decimal_issues collects and _other_issues leaves out.
LIMIT_CODES = (*DECIMAL_CODES, INTEGER_DIGITS_EXCEEDED)
# R13-SEC2 (rule 7): what a corrupt file holds, as SQLite literals: a REAL of 1e60, and +inf (SQLite reads 1e999 as Inf).
HUGE_REAL = "1e60"
INFINITE_REAL = "1e999"

ENDPOINTS = ("validate", "commit")
# What a test reads back, column by column: through each column's type, as the user finds the row once the request is over.
STORED_COLUMNS = (Transaction.quantity, Transaction.amount, Transaction.currency, Transaction.cost_basis_override, Transaction.cost_basis_currency, Transaction.description)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def engine():
    """The app's async engine, on this lane's test database."""
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    """One session per test, rolled back at the end: nothing a test writes reaches the lane's database."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@dataclass(frozen=True)
class World:
    """One test's own ground, by id — a rolled-back savepoint expires the objects it touched, and an expired attribute
    would load lazily outside the event loop: a crypto asset, the broker the tests buy on (``main``) and the broker a
    TRANSFER reaches (``other``). Both may overdraw their cash (a BUY spends cash no DEPOSIT brought) and may not go
    short, as a broker does by default, so every batch replays its balances."""

    session: AsyncSession
    marker: str
    asset_id: int
    main_id: int
    other_id: int

    @property
    def batch_description(self) -> str:
        """The description of every row a batch of this test sends: what finds those rows again, or proves them absent."""
        return f"{self.marker} batch"


@pytest_asyncio.fixture
async def world(session) -> World:
    """The test's asset and brokers, under a marker of its own."""
    marker = f"C97a-decimals {uuid.uuid4().hex}"
    now = utcnow()
    asset = Asset(display_name=f"{marker} coin", asset_type=AssetType.CRYPTO, currency=EUR, created_at=now, updated_at=now)
    main = Broker(name=f"{marker} main", description="C-97a: the broker the tests buy on", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    other = Broker(name=f"{marker} other", description="C-97a: the broker a TRANSFER reaches", allow_cash_overdraft=True, allow_asset_shorting=False, created_at=now, updated_at=now)
    session.add_all([asset, main, other])
    await session.flush()
    return World(session=session, marker=marker, asset_id=asset.id, main_id=main.id, other_id=other.id)


# ============================================================================
# HELPERS
# ============================================================================


async def _insert(world: World, **columns) -> int:
    """A row written with the ORM, without the batch and its checks; its id."""
    now = utcnow()
    row = Transaction(description=f"{world.marker} seed", created_at=now, updated_at=now, **columns)
    world.session.add(row)
    await world.session.flush()
    return row.id


async def _seed_position(world: World, tx_type: TransactionType, quantity: str, *, day: date = SEED_DAY, amount: str = "0", cost: str | None = None, asset_id: int | None = None) -> int:
    """A row of ``quantity`` units of the test's asset (or of ``asset_id``) on ``main``, moving ``amount`` EUR of cash,
    with a manual cost basis of ``cost`` EUR when given."""
    return await _insert(
        world,
        broker_id=world.main_id,
        asset_id=asset_id or world.asset_id,
        type=tx_type,
        date=day,
        quantity=Decimal(quantity),
        amount=Decimal(amount),
        currency=EUR if Decimal(amount) != 0 else None,
        cost_basis_override=Decimal(cost) if cost is not None else None,
        cost_basis_currency=EUR if cost is not None else None,
    )


async def _seed_cash(world: World, tx_type: TransactionType, amount: str, currency: str, *, day: date) -> int:
    """A cash row on ``main``, without an asset."""
    return await _insert(world, broker_id=world.main_id, asset_id=None, type=tx_type, date=day, quantity=Decimal("0"), amount=Decimal(amount), currency=currency)


async def _new_asset(world: World, label: str) -> int:
    """One more asset of the test, under its marker."""
    now = utcnow()
    asset = Asset(display_name=f"{world.marker} {label}", asset_type=AssetType.CRYPTO, currency=EUR, created_at=now, updated_at=now)
    world.session.add(asset)
    await world.session.flush()
    return asset.id


def _row(world: World, tx_type: str, quantity: str, *, cash: str | None = None, cost: str | None = None, broker_id: int | None = None) -> dict:
    """A create as the app sends it (``TXCreateItem``), every decimal a string: of the test's asset on ``DAY``, on ``main``
    unless ``broker_id`` says otherwise, moving ``cash`` EUR, with a manual cost basis of ``cost`` EUR."""
    row = {"broker_id": broker_id or world.main_id, "asset_id": world.asset_id, "type": tx_type, "date": DAY.isoformat(), "quantity": quantity, "description": world.batch_description}
    if cash is not None:
        row["cash"] = {"code": EUR, "amount": cash}
    if cost is not None:
        row["cost_basis_override"] = {"code": EUR, "amount": cost}
    return row


async def _run_as_the_endpoint(world: World, *, creates: list[dict] | None = None, updates: list[dict] | None = None, deletes: list[int] | None = None, promotes: list[dict] | None = None, endpoint: str = "commit") -> TXBatchResponse:
    """The batch as ``POST /transactions/<endpoint>`` runs it, its transaction included: ``/commit`` keeps it when the
    service answers committed and rolls it back otherwise, ``/validate`` always rolls it back (``api/v1/transactions.py``);
    no user, so no access check.

    ``execute_batch`` applies and flushes the rows it keeps, a refused one included, and leaves the commit or the
    rollback to its caller. A savepoint stands in for the request's transaction, as in
    ``test_transaction_cost_basis_rule.py``: the rows the test wrote before it survive its rollback (their flush opened
    SQLite's transaction, so the savepoint nests in it), and the session fixture still rolls everything back.
    """
    savepoint = await world.session.begin_nested()
    response = await TransactionService(world.session).execute_batch(creates_raw=creates or [], updates_raw=updates or [], deletes=deletes or [], promotes_raw=promotes or [], commit=endpoint == "commit")
    if endpoint == "commit" and response.committed:
        await savepoint.commit()
    else:
        await savepoint.rollback()
    return response


async def _run_never_raising(world: World, story: str, **batch) -> TXBatchResponse:
    """``_run_as_the_endpoint(world, **batch)``; an exception fails the test and names it: the endpoint would answer 500
    instead of a refusal (R13-SEC2). Whatever the batch left half-done goes with the session fixture's rollback."""
    try:
        return await _run_as_the_endpoint(world, **batch)
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"R13-SEC2: {story}: execute_batch raised {exc!r}, so /transactions/{batch.get('endpoint', 'commit')} answers 500 instead of a refusal")


async def _stored(world: World, ids) -> dict[int, dict]:
    """The rows ``ids`` as the database holds them, by id, read column by column (``STORED_COLUMNS``). Never through the
    ORM objects, which a rolled-back savepoint leaves expired."""
    statement = select(Transaction.id, *STORED_COLUMNS).where(Transaction.id.in_(list(ids)))
    return {row["id"]: {column: value for column, value in row.items() if column != "id"} for row in (await world.session.execute(statement)).mappings()}


async def _batch_rows(world: World) -> list[int]:
    """The ids of the rows this test's batches sent that the database holds, found by their description."""
    statement = select(Transaction.id).where(Transaction.description == world.batch_description)
    return list((await world.session.execute(statement)).scalars())


def _created_ids(response: TXBatchResponse) -> dict[int, int]:
    """The id each create of the batch got, by its index."""
    return {result.index: result.ids[0] for result in response.results if result.operation == "create" and result.ids}


def _in_batch(response: TXBatchResponse) -> set[tuple[str, int]]:
    """The ``(operation, index)`` of every row the batch applied and reports: the rows it kept."""
    return {(result.operation, result.index) for result in response.results}


def _issue_order(issue: tuple) -> tuple:
    """A fixed order for ``(operation, index, ref_id, code, field, params)`` issues: their order is not the subject."""
    operation, index, ref_id, code, field, _params = issue
    return (operation, index, ref_id or 0, code or "", field or "")


def _decimal_issues(response: TXBatchResponse) -> list[tuple]:
    """The batch's refusals over a column's limit — decimal places, significant digits, integer digits (R13-SEC2) — as
    ``(operation, index, ref_id, code, field, params)``, sorted."""
    return sorted(((issue.operation, issue.index, issue.ref_id, issue.code, issue.field, issue.params) for issue in response.issues if issue.code in LIMIT_CODES), key=_issue_order)


def _other_issues(response: TXBatchResponse) -> list[TXValidationIssue]:
    """Every issue of the batch that is not a refusal over a column's limit."""
    return [issue for issue in response.issues if issue.code not in LIMIT_CODES]


def _render(issues: list[TXValidationIssue]) -> str:
    """The issues, for a failure message."""
    return "; ".join(f"{issue.operation}[{issue.index}] ref_id={issue.ref_id} code={issue.code} field={issue.field} params={issue.params} error={issue.error!r}" for issue in issues) or "none"


def _words(text: str) -> str:
    """``text`` as lower-case words: ``cash.amount`` and «Cash amount» read alike."""
    return " ".join(text.lower().replace(".", " ").replace("_", " ").split())


def _assert_errors_name_their_fields(response: TXBatchResponse) -> None:
    """Each refusal over a column's limit carries an English ``error`` that names its field, as sent (``cash.amount``) or
    in words."""
    for issue in response.issues:
        if issue.code in LIMIT_CODES:
            assert issue.error and _words(issue.field or "") in _words(issue.error), f"C-97a: the error of {issue.code} on {issue.operation}[{issue.index}] must be an English text naming its field {issue.field!r}; it reads {issue.error!r}"


# ============================================================================
# RED — A QUANTITY KEEPS 10 DECIMALS
# ============================================================================

SENT_QUANTITIES = ("0.12345678", "0.1234567891")
ROUND_TRIP_SHAPES = ("buy", "sell", "adjustment_in")


def _round_trip_batch(world: World, shape: str, quantity: str) -> tuple[list[dict], int]:
    """The creates that write a ``shape`` row of ``quantity`` units (that many leave on a SELL), and that row's index.

    The SELL sells units a BUY of the same batch and day brings, sent before it: ``main`` may not go short. The ADJUSTMENT
    adds units, so it carries the cost basis it needs.
    """
    if shape == "buy":
        return [_row(world, "BUY", quantity, cash="-10")], 0
    if shape == "sell":
        return [_row(world, "BUY", "1", cash="-100"), _row(world, "SELL", f"-{quantity}", cash="10")], 1
    if shape == "adjustment_in":
        return [_row(world, "ADJUSTMENT", quantity, cost="100")], 0
    raise ValueError(f"unknown shape {shape!r}")


class TestQuantitiesKeepTenDecimals:
    """RED: a quantity of up to 10 decimals reads back from the database as it was sent.

    Today ``Numeric(18, 6)`` rounds it to 6 decimals when it is read: 0.12345678 reads 0.123457, 0.1234567891 too. The
    batch commits — each test checks that first — so the red is the read-back alone.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("quantity", SENT_QUANTITIES)
    @pytest.mark.parametrize("shape", ROUND_TRIP_SHAPES)
    async def test_created_quantity_reads_back_as_sent(self, world, shape, quantity):
        """RED: committed through ``/commit``, and the row's quantity reads back equal to what the batch received."""
        creates, subject_index = _round_trip_batch(world, shape, quantity)
        sent = Decimal(creates[subject_index]["quantity"])

        response = await _run_as_the_endpoint(world, creates=creates)

        assert response.committed is True and response.issues == [], f"scaffold: a {shape} of {sent} units, within the limit of 10 decimals, was refused: {_render(response.issues)}"
        subject_id = _created_ids(response)[subject_index]
        stored = (await _stored(world, [subject_id]))[subject_id]["quantity"]
        assert stored == sent, f"C-97a: a {shape} of {sent} units (id={subject_id}) reads back {stored} from the database; a quantity keeps up to 10 decimal places and reads back exactly"

    @pytest.mark.asyncio
    async def test_updated_quantity_reads_back_as_sent(self, world):
        """RED: an update of a stored BUY's quantity to 0.1234567891 commits, and the row reads it back."""
        subject_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        sent = Decimal("0.1234567891")

        response = await _run_as_the_endpoint(world, updates=[{"id": subject_id, "quantity": str(sent)}])

        assert response.committed is True and response.issues == [], f"scaffold: an update of BUY id={subject_id} to {sent} units, within the limit of 10 decimals, was refused: {_render(response.issues)}"
        stored = (await _stored(world, [subject_id]))[subject_id]["quantity"]
        assert stored == sent, f"C-97a: BUY id={subject_id} updated to {sent} units reads back {stored} from the database; a quantity keeps up to 10 decimal places and reads back exactly"


# ============================================================================
# GUARDS — WHAT THE LIMIT LEAVES ALONE
# ============================================================================

# A create within the limits once its trailing zeros are dropped, though not before; the column it is read back from, and
# the value it must read back as.
TRAILING_ZEROS = [
    pytest.param({"tx_type": "BUY", "quantity": "1.50000000000000", "cash": "-150"}, "quantity", Decimal("1.5"), id="quantity-1.50000000000000"),
    pytest.param({"tx_type": "BUY", "quantity": "1", "cash": "-150.1000000"}, "amount", Decimal("-150.1"), id="cash-amount--150.1000000"),
    pytest.param({"tx_type": "ADJUSTMENT", "quantity": "1", "cost": "1.5000000000000"}, "cost_basis_override", Decimal("1.5"), id="cost-basis-1.5000000000000"),
]


class TestWhatTheLimitLeavesAlone:
    """Guards, green today and after C-97a: what the refusal must not catch, and the form a read keeps."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("subject", "column", "value"), TRAILING_ZEROS)
    async def test_trailing_zeros_are_not_counted(self, world, subject, column, value):
        """Guard: 1.50000000000000 units (14 decimals, 13 of them trailing zeros; 15 digits in all, so within D1 however
        they are counted), a cash amount of -150.1000000 (7 decimals, 6 of them zeros, over 6 only if they count) and a
        per-unit cost basis of 1.5000000000000 (13 decimals, 12 of them zeros: over D5's 12 only if they count; 14 digits
        in all) commit, and read back as their value. A cure that counts the trailing zeros refuses them."""
        response = await _run_as_the_endpoint(world, creates=[_row(world, **subject)])

        assert response.committed is True and response.issues == [], f"C-97a: trailing zeros are not decimal places, so {subject} is within the limits and must commit; it was refused: {_render(response.issues)}"
        tx_id = _created_ids(response)[0]
        stored = (await _stored(world, [tx_id]))[tx_id][column]
        assert stored == value, f"The create {subject} (id={tx_id}) reads back {column}={stored}, not {value}"

    @pytest.mark.asyncio
    async def test_whole_and_six_decimal_quantities_read_back_in_todays_form(self, world):
        """Guard: a quantity of 10 reads back ``10.000000`` and one of 1.234567 ``1.234567``, as ``Numeric(18, 6)`` reads
        them today; ``RealDecimal`` pads to 6 decimals a value that has fewer."""
        creates = [_row(world, "BUY", "10", cash="-100"), _row(world, "BUY", "1.234567", cash="-10")]

        response = await _run_as_the_endpoint(world, creates=creates)

        assert response.committed is True and response.issues == [], f"scaffold: two BUYs within the limits were refused: {_render(response.issues)}"
        created = _created_ids(response)
        stored = await _stored(world, created.values())
        forms = {creates[index]["quantity"]: str(stored[tx_id]["quantity"]) for index, tx_id in created.items()}
        assert forms == {"10": "10.000000", "1.234567": "1.234567"}, f"A quantity of 6 decimals or fewer reads back in today's form, padded to 6 decimals; sent → read: {forms}"


# ============================================================================
# RED — OVER THE LIMIT, REFUSED AT CONFIRMATION
# ============================================================================

# The create a refusal is about — sent at index 1, behind a valid BUY, so the refusal's index is its row's and not a
# default — and the decimal issues it gets, as (code, field, params). The three "derived" cases read the contract's
# general rule (decimals first, D1 on every field, one issue per field); they are not in the brief's list.
CREATE_REFUSALS = [
    pytest.param({"tx_type": "BUY", "quantity": "0.12345678901", "cash": "-10"}, [(DECIMAL_PLACES_EXCEEDED, "quantity", QUANTITY_MAX)], id="quantity-11-decimals"),
    pytest.param({"tx_type": "BUY", "quantity": "1234567890123.456", "cash": "-10"}, [(SIGNIFICANT_DIGITS_EXCEEDED, "quantity", DIGITS_MAX)], id="quantity-16-significant-digits"),
    pytest.param({"tx_type": "BUY", "quantity": "1", "cash": "-100.1234567"}, [(DECIMAL_PLACES_EXCEEDED, "cash.amount", CASH_MAX)], id="cash-amount-7-decimals"),
    pytest.param({"tx_type": "ADJUSTMENT", "quantity": "1", "cost": COST_13_DECIMALS}, [(DECIMAL_PLACES_EXCEEDED, "cost_basis_override", COST_MAX)], id="adjustment-in-cost-basis-13-decimals"),
    pytest.param({"tx_type": "BUY", "quantity": "12345678.123456789012", "cash": "-10"}, [(DECIMAL_PLACES_EXCEEDED, "quantity", QUANTITY_MAX)], id="derived-quantity-over-both-limits-decimals-first"),
    pytest.param({"tx_type": "BUY", "quantity": "1", "cash": "-12345678901234.56"}, [(SIGNIFICANT_DIGITS_EXCEEDED, "cash.amount", DIGITS_MAX)], id="derived-cash-amount-16-significant-digits"),
    pytest.param({"tx_type": "BUY", "quantity": "0.12345678901", "cash": "-100.1234567"}, [(DECIMAL_PLACES_EXCEEDED, "cash.amount", CASH_MAX), (DECIMAL_PLACES_EXCEEDED, "quantity", QUANTITY_MAX)], id="derived-one-issue-per-field"),
]

# The stored row an update over a limit edits (a BUY of 1 for 100 EUR, or an ADJUSTMENT +1 with its cost basis of 100
# EUR), the update's change, and the field and params of its refusal.
UPDATE_REFUSALS = [
    pytest.param("buy", {"quantity": "0.12345678901"}, "quantity", QUANTITY_MAX, id="quantity-11-decimals"),
    pytest.param("buy", {"cash": {"code": EUR, "amount": "-100.1234567"}}, "cash.amount", CASH_MAX, id="cash-amount-7-decimals"),
    pytest.param("adjustment_in", {"cost_basis_override": {"code": EUR, "amount": COST_13_DECIMALS}}, "cost_basis_override", COST_MAX, id="cost-basis-13-decimals"),
]

PAIR_SHAPES = ("transfer-received-cost-basis", "fx-conversion-cash-amount")


class TestOverTheLimitIsRefusedAtConfirmation:
    """RED: a value over its field's limit is refused at confirmation — never rounded — on its own row.

    Before ``check_decimal_limits`` nothing checked: the batch committed, and the read rounded the value. ``/validate``
    and ``/commit`` run the same ``execute_batch``, so a create is refused on both; the updates and the pairs run as
    ``/commit``. Each test asserts the refusal first, so a red names what is missing. A per-unit cost basis is checked
    against D5's 12 decimals, read from the model: red until its column is ``RealDecimal(24, 12)`` (the check reads 6
    from today's ``Numeric(18, 6)`` and answers ``{"max": 6}``).
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize(("subject", "expected"), CREATE_REFUSALS)
    async def test_create_over_the_limit_is_refused_on_its_row(self, world, subject, expected, endpoint):
        """RED: exactly the expected issues on create 1 (``ref_id`` None), nothing else; not committed; the row still in
        the batch; no row of the batch in the database."""
        barrier_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        creates = [_row(world, "BUY", "1", cash="-100"), _row(world, **subject)]

        response = await _run_as_the_endpoint(world, creates=creates, endpoint=endpoint)

        refusals = sorted((("create", 1, None, code, field, params) for code, field, params in expected), key=_issue_order)
        assert _decimal_issues(response) == refusals, f"C-97a, /{endpoint}: the create {subject} must be refused on its own row with exactly {refusals}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"C-97a, /{endpoint}: only the decimals may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, f"C-97a: /{endpoint} refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        assert ("create", 1) in _in_batch(response), f"C-97a: the refused row stays in the batch (applied and reported), so a pair it belongs to is not broken; the results are {response.results}"
        assert barrier_id in await _stored(world, [barrier_id]), f"scaffold: the read-back no longer sees row id={barrier_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"C-97a: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("stored_shape", "change", "field", "params"), UPDATE_REFUSALS)
    async def test_update_over_the_limit_is_refused_on_its_row(self, world, stored_shape, change, field, params):
        """RED: an update over a limit, sent at index 1 behind a valid notes edit of another row, is refused on update 1
        with ``ref_id`` its id; not committed; both rows read back as they were stored."""
        neighbour_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        if stored_shape == "buy":
            subject_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        else:
            subject_id = await _seed_position(world, TransactionType.ADJUSTMENT, "1", cost="100")
        before = await _stored(world, [neighbour_id, subject_id])
        updates = [{"id": neighbour_id, "description": f"{world.marker} neighbour edited"}, {"id": subject_id, **change}]

        response = await _run_as_the_endpoint(world, updates=updates)

        refusal = ("update", 1, subject_id, DECIMAL_PLACES_EXCEEDED, field, params)
        assert _decimal_issues(response) == [refusal], f"C-97a: the update {change} of id={subject_id} must be refused on its own row with exactly {refusal}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"C-97a: only the decimals may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, "C-97a: /commit refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        assert ("update", 1) in _in_batch(response), f"C-97a: the refused update stays in the batch (applied and reported); the results are {response.results}"
        after = await _stored(world, [neighbour_id, subject_id])
        assert after == before, f"C-97a: the batch was refused, yet the stored rows changed: before {before}, after {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("pair", PAIR_SHAPES)
    async def test_pair_with_one_leg_over_the_limit_is_refused_on_that_leg_alone(self, world, pair):
        """RED — not a guard: before ``check_decimal_limits`` the pair committed whole, with no issue at all; the cost
        basis case stays red until D5's column (13 decimals, ``{"max": 12}``).

        A linked pair one leg of which is over a limit — the received TRANSFER's cost basis, or one side of an exchange —
        gets the decimal issue on that leg (create 1) and nothing else: not also a broken pair (``linkUuidPairCount``),
        which a cure that drops the refused row before the link stage would add, nor a missing cost basis. Both legs stay
        in the batch; nothing is written.
        """
        link_uuid = str(uuid.uuid4())
        if pair == "transfer-received-cost-basis":
            # The units the giving leg moves: main may not go short.
            await _seed_position(world, TransactionType.BUY, "1", amount="-100")
            legs = [{**_row(world, "TRANSFER", "-1"), "link_uuid": link_uuid}, {**_row(world, "TRANSFER", "1", cost=COST_13_DECIMALS, broker_id=world.other_id), "link_uuid": link_uuid}]
            refusal = ("create", 1, None, DECIMAL_PLACES_EXCEEDED, "cost_basis_override", COST_MAX)
        else:
            giving = {"broker_id": world.main_id, "type": "FX_CONVERSION", "date": DAY.isoformat(), "quantity": "0", "cash": {"code": EUR, "amount": "-100"}, "link_uuid": link_uuid, "description": world.batch_description}
            legs = [giving, {**giving, "cash": {"code": USD, "amount": "107.1234567"}}]
            refusal = ("create", 1, None, DECIMAL_PLACES_EXCEEDED, "cash.amount", CASH_MAX)

        response = await _run_as_the_endpoint(world, creates=legs)

        assert _decimal_issues(response) == [refusal], f"C-97a: a {pair} pair must be refused on its leg over the limit with exactly {refusal}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"C-97a: the refusal of one leg must not also report the pair broken (linkUuidPairCount) or anything else: {_render(_other_issues(response))}"
        assert response.committed is False, "C-97a: /commit refused the pair, yet answered committed"
        assert {("create", 0), ("create", 1)} <= _in_batch(response), f"C-97a: both legs stay in the batch, the refused one included; the results are {response.results}"
        written = await _batch_rows(world)
        assert written == [], f"C-97a: the pair was refused, yet the database holds its rows {written}"


# ============================================================================
# RED — D5: A PER-UNIT COST KEEPS 12 DECIMALS
# ============================================================================

PER_UNIT_COST_SHAPES = ("transfer_received", "adjustment_in")


def _per_unit_cost_batch(world: World, shape: str, cost: str) -> tuple[list[dict], int]:
    """The creates that write a ``shape`` row receiving one unit at a manual per-unit cost of ``cost`` EUR, and that
    row's index: the receiving leg of a TRANSFER ``main`` → ``other`` (the caller seeds the unit ``main`` gives), or an
    ADJUSTMENT +1 on ``main``."""
    if shape == "transfer_received":
        link_uuid = str(uuid.uuid4())
        return [{**_row(world, "TRANSFER", "-1"), "link_uuid": link_uuid}, {**_row(world, "TRANSFER", "1", cost=cost, broker_id=world.other_id), "link_uuid": link_uuid}], 1
    if shape == "adjustment_in":
        return [_row(world, "ADJUSTMENT", "1", cost=cost)], 0
    raise ValueError(f"unknown shape {shape!r}")


class TestAPerUnitCostKeepsTwelveDecimals:
    """RED (decision D5): ``cost_basis_override`` is a PER-UNIT price — ``financial_math/average_cost.py`` multiplies it
    by the quantity — so it keeps up to 12 decimal places (``RealDecimal(24, 12)``) and reads back exactly.

    Today the column is ``Numeric(18, 6)`` and ``check_decimal_limits`` reads its scale from the model, so a PEPE's
    0.0000034573 EUR a unit — 10 decimals — is refused with ``decimalPlacesExceeded`` ``{"max": 6}`` (before the check
    it was saved, and read back 0.000003: a cost of 3 EUR a million units instead of 3.4573).
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", PER_UNIT_COST_SHAPES)
    async def test_pepe_unit_cost_is_saved_and_reads_back_exactly(self, world, shape):
        """RED: committed through ``/commit`` with no issue, and the receiving row's cost basis reads back exactly
        0.0000034573 EUR from the database."""
        if shape == "transfer_received":
            # The unit the giving leg moves: main may not go short.
            await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        creates, subject_index = _per_unit_cost_batch(world, shape, PEPE_UNIT_COST)

        response = await _run_as_the_endpoint(world, creates=creates)

        assert response.committed is True and response.issues == [], f"D5: a per-unit cost of {PEPE_UNIT_COST} EUR has 10 decimals, within the 12 a per-unit cost keeps, yet the {shape} was refused: {_render(response.issues)}"
        subject_id = _created_ids(response)[subject_index]
        stored = (await _stored(world, [subject_id]))[subject_id]
        cost = (stored["cost_basis_override"], stored["cost_basis_currency"])
        assert cost == (Decimal(PEPE_UNIT_COST), EUR), f"D5: the {shape} id={subject_id} was saved at {PEPE_UNIT_COST} EUR a unit and reads back a cost basis of {cost[0]} {cost[1]}"


# ============================================================================
# RED AND GUARDS — RULE 5: AN AUTO COST BASIS IS NOT CHECKED
# ============================================================================

# The modes in which the backend computes the cost basis itself, and reads only the currency of the one sent.
AUTO_MODES = ("auto", "auto-detail")


@dataclass(frozen=True)
class RepeatingAverage:
    """A pool whose average cost repeats forever — a BUY of 3 units on ``main`` for ``pool_cost`` EUR — and that average
    as a client sends it back in Auto (``sent``): over the limit of a manual cost basis, which refuses it with ``code``
    and ``params``."""

    pool_cost: str
    sent: str
    code: str
    params: dict


# 100 / 3 in full, as the batch's own preview answers it (``wac_results``) and the Bulk modal copies it back into an Auto
# row's cost basis (``TransactionBulkModal.svelte``): 28 significant digits, 26 decimals. The E2E's shape.
HUNDRED_OVER_THREE = RepeatingAverage(pool_cost="100", sent="33.33333333333333333333333333", code=DECIMAL_PLACES_EXCEEDED, params=COST_MAX)
# 1000000 / 3 as a double prints it: 10 decimals, within the 12, but 16 significant digits.
MILLION_OVER_THREE = RepeatingAverage(pool_cost="1000000", sent="333333.3333333333", code=SIGNIFICANT_DIGITS_EXCEEDED, params=DIGITS_MAX)
REPEATING_AVERAGES = [
    pytest.param(HUNDRED_OVER_THREE, id="100-over-3-26-decimals"),
    pytest.param(MILLION_OVER_THREE, id="1000000-over-3-16-significant-digits"),
]

# The Auto cost of HUNDRED_OVER_THREE's pool, 100 / 3, as ``RealDecimal(24, 12)`` reads it back: the double
# 33.333333333333336, cut to 15 significant digits, then to 12 decimals.
AUTO_COST_OF_HUNDRED_OVER_THREE = Decimal("33.333333333333")
# An amount over the limit that is not that pool's average — 125 / 3 in full, as a preview taken before the pool changed
# would answer — so the row tells the amount sent (it would read back 41.666666666667) from the Auto cost.
NOT_THE_POOLS_AVERAGE = "41.66666666666666666666666667"

# The rows the outcome is read on: the two creates of ``_per_unit_cost_batch``, and the update of a stored ADJUSTMENT +1.
AUTO_COST_SUBJECTS = [
    pytest.param("create", "transfer_received", id="create-transfer_received"),
    pytest.param("create", "adjustment_in", id="create-adjustment_in"),
    pytest.param("update", "adjustment_in", id="update-adjustment_in"),
]


async def _seed_pool(world: World, cost: str) -> int:
    """The pool every Auto cost of these tests averages, written before ``DAY``: a BUY of 3 units on ``main`` for ``cost``
    EUR; its id. A received TRANSFER averages its partner's broker, ``main``, before the transfer, an ADJUSTMENT its own
    broker without itself (``_auto_cost_source``, ``auto_cost.py``); the BUY also brings the unit a TRANSFER's giving
    leg moves (``main`` may not go short)."""
    return await _seed_position(world, TransactionType.BUY, "3", amount=f"-{cost}")


def _deposit(world: World) -> dict:
    """A create of a DEPOSIT of 100 EUR on ``main``: a row without an asset, so in no pool."""
    return {"broker_id": world.main_id, "type": "DEPOSIT", "date": DAY.isoformat(), "quantity": "0", "cash": {"code": EUR, "amount": "100"}, "description": world.batch_description}


def _cost_basis_creates(world: World, shape: str, mode: str, amount: str) -> tuple[list[dict], int]:
    """The creates of a ``shape`` row (``_per_unit_cost_batch``) receiving one unit with ``cost_basis_mode`` ``mode`` and a
    cost basis of ``amount`` EUR, and that row's index. Behind a DEPOSIT (``_deposit``): the row's index is not a
    default, and the pool its Auto cost averages stays the seeded one."""
    creates, subject_index = _per_unit_cost_batch(world, shape, amount)
    creates[subject_index] = {**creates[subject_index], "cost_basis_mode": mode}
    return [_deposit(world), *creates], subject_index + 1


async def _cost_basis_update(world: World, mode: str, amount: str) -> tuple[list[dict], int, int]:
    """The updates that set a stored ADJUSTMENT +1 (on ``DAY``, at a manual cost of 100 EUR) to ``cost_basis_mode``
    ``mode`` with a cost basis of ``amount`` EUR — sent at index 1, behind a notes edit of a stored DEPOSIT on ``main``,
    in no pool — then the ADJUSTMENT's id and the DEPOSIT's."""
    neighbour_id = await _seed_cash(world, TransactionType.DEPOSIT, "100", EUR, day=SEED_DAY)
    subject_id = await _seed_position(world, TransactionType.ADJUSTMENT, "1", day=DAY, cost="100")
    updates = [{"id": neighbour_id, "description": f"{world.marker} neighbour edited"}, {"id": subject_id, "cost_basis_mode": mode, "cost_basis_override": {"code": EUR, "amount": amount}}]
    return updates, subject_id, neighbour_id


class TestAnAutoCostBasisIsNotChecked:
    """Rule 5: an Auto cost basis is not checked. Found by the E2E «TRANSFER (asset) create → commit (dual brokers +
    asset + qty)» (``frontend/e2e/transactions/tx-commit-all-types.spec.ts:532``), whose commit was refused with
    ``decimalPlacesExceeded`` ``{"max": 12}`` on ``cost_basis_override``.

    With ``cost_basis_mode`` ``auto`` or ``auto-detail`` the amount of the ``cost_basis_override`` sent is not used:
    ``_compute_wac_for_auto_items`` (``auto_cost.py``) reads its currency alone, recomputes the average of the source
    pool and writes it on the row. The Form sends back the preview's average, which can repeat forever (100 / 3), and
    ``check_decimal_limits`` refuses it whatever the mode: an amount the batch would have discarded. The cure:
    ``_decimal_limit_values`` leaves out the cost basis of an Auto row.

    REDS: an Auto create or update carrying such an amount is accepted, and the row holds the Auto cost, not the amount
    sent. GUARDS: the same amounts as a ``manual`` cost basis stay refused on their row, never rounded (D2). No mode with
    an explicit override is a manual cost basis too: ``TestOverTheLimitIsRefusedAtConfirmation`` pins it.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize("average", REPEATING_AVERAGES)
    @pytest.mark.parametrize("mode", AUTO_MODES)
    @pytest.mark.parametrize("shape", PER_UNIT_COST_SHAPES)
    async def test_auto_create_carrying_the_previews_average_is_accepted(self, world, shape, mode, average, endpoint):
        """RED, the defect of ``tx-commit-all-types.spec.ts:532``: a received TRANSFER (the E2E's own row) or an
        ADJUSTMENT +1 in ``mode``, whose cost basis carries the pool's repeating average, gets no decimal issue on
        ``/validate`` nor on ``/commit``, nor any other issue, and ``/commit`` commits.

        Red today: ``check_decimal_limits`` checks the amount whatever the mode and refuses it on the row —
        ``decimalPlacesExceeded`` ``{"max": 12}`` for 100 / 3 in full, ``significantDigitsExceeded`` ``{"max": 15}`` for
        1000000 / 3 — so nothing is committed.
        """
        await _seed_pool(world, average.pool_cost)
        creates, subject_index = _cost_basis_creates(world, shape, mode, average.sent)

        response = await _run_as_the_endpoint(world, creates=creates, endpoint=endpoint)

        assert _decimal_issues(response) == [], f"C-97a rule 5, /{endpoint}: an {mode} cost basis is the backend's to compute, so the amount {average.sent} EUR of the {shape} (create {subject_index}) must not be checked; the batch answered: {_render(response.issues)}"
        assert response.issues == [], f"C-97a rule 5, /{endpoint}: nothing else may refuse the {mode} {shape}: {_render(response.issues)}"
        assert response.committed is (endpoint == "commit"), f"C-97a rule 5: /{endpoint} found no issue, so it must answer committed={endpoint == 'commit'}; it answered {response.committed}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize("average", REPEATING_AVERAGES)
    @pytest.mark.parametrize("mode", AUTO_MODES)
    async def test_auto_update_carrying_the_previews_average_is_accepted(self, world, mode, average, endpoint):
        """RED, the defect of ``tx-commit-all-types.spec.ts:532`` on an update: a stored ADJUSTMENT +1 set to ``mode``
        with the pool's repeating average as its cost basis, sent at index 1 behind a notes edit, gets no decimal issue —
        none on update 1, ``ref_id`` its id — on ``/validate`` nor on ``/commit``, nor any other issue, and ``/commit``
        commits.

        Red today: ``check_decimal_limits`` refuses the amount on update 1, ``ref_id`` the ADJUSTMENT's id, as if it were
        a manual cost basis.
        """
        await _seed_pool(world, average.pool_cost)
        updates, subject_id, _neighbour_id = await _cost_basis_update(world, mode, average.sent)

        response = await _run_as_the_endpoint(world, updates=updates, endpoint=endpoint)

        assert _decimal_issues(response) == [], f"C-97a rule 5, /{endpoint}: an {mode} cost basis is the backend's to compute, so the amount {average.sent} EUR of the update of ADJUSTMENT id={subject_id} must not be checked; the batch answered: {_render(response.issues)}"
        assert response.issues == [], f"C-97a rule 5, /{endpoint}: nothing else may refuse the {mode} update of id={subject_id}: {_render(response.issues)}"
        assert response.committed is (endpoint == "commit"), f"C-97a rule 5: /{endpoint} found no issue, so it must answer committed={endpoint == 'commit'}; it answered {response.committed}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", AUTO_MODES)
    @pytest.mark.parametrize(("operation", "shape"), AUTO_COST_SUBJECTS)
    async def test_the_row_holds_the_auto_cost_not_the_amount_sent(self, world, operation, shape, mode):
        """RED, the outcome that proves the amount ignored, not merely tolerated (the defect of
        ``tx-commit-all-types.spec.ts:532``): a create or an update in ``mode`` carrying 125 / 3 in full — not the pool's
        average — commits through ``/commit``, and the row holds the Auto cost the backend computes: the pool's average,
        100 / 3, read back 33.333333333333, in EUR, the currency sent. Not the amount sent (read back 41.666666666667),
        nor, for the update, the 100 EUR the row was stored with. So the amount the cure leaves unchecked never reaches
        the database.

        Red today: the batch refuses the amount sent (``decimalPlacesExceeded`` ``{"max": 12}``) and writes nothing.
        """
        await _seed_pool(world, HUNDRED_OVER_THREE.pool_cost)
        if operation == "update":
            updates, subject_id, _neighbour_id = await _cost_basis_update(world, mode, NOT_THE_POOLS_AVERAGE)
            response = await _run_as_the_endpoint(world, updates=updates)
        else:
            creates, subject_index = _cost_basis_creates(world, shape, mode, NOT_THE_POOLS_AVERAGE)
            response = await _run_as_the_endpoint(world, creates=creates)
            subject_id = _created_ids(response).get(subject_index)

        assert response.committed is True and response.issues == [], f"C-97a rule 5: the {mode} {operation} of the {shape} carrying {NOT_THE_POOLS_AVERAGE} EUR must commit, its amount being the backend's to compute; it was refused: {_render(response.issues)}"
        stored = (await _stored(world, [subject_id]))[subject_id]
        cost, expected = (stored["cost_basis_override"], stored["cost_basis_currency"]), (AUTO_COST_OF_HUNDRED_OVER_THREE, EUR)
        assert cost == expected, f"C-97a rule 5: in {mode} the {shape} id={subject_id} must hold the Auto cost, the pool's 100 / 3 read back {expected[0]} {expected[1]}, not the {NOT_THE_POOLS_AVERAGE} sent; it holds {cost[0]} {cost[1]}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize("average", REPEATING_AVERAGES)
    @pytest.mark.parametrize("shape", PER_UNIT_COST_SHAPES)
    async def test_manual_create_carrying_the_same_amount_is_still_refused(self, world, shape, average, endpoint):
        """Guard (D2): the same amounts as a ``manual`` cost basis are the user's own, kept as sent, so over the limit
        they are refused on their row — exactly ``(create, index, None, code, cost_basis_override, params)`` — and never
        rounded: not committed, the row still in the batch, nothing written.

        Green today: ``check_decimal_limits`` checks every cost basis. A cure for ``tx-commit-all-types.spec.ts:532``
        that stops checking it whatever the mode turns it red.
        """
        barrier_id = await _seed_pool(world, average.pool_cost)
        creates, subject_index = _cost_basis_creates(world, shape, "manual", average.sent)

        response = await _run_as_the_endpoint(world, creates=creates, endpoint=endpoint)

        refusal = ("create", subject_index, None, average.code, "cost_basis_override", average.params)
        assert _decimal_issues(response) == [refusal], f"D2, /{endpoint}: a manual cost basis of {average.sent} EUR on the {shape} at create {subject_index} must be refused on its own row with exactly {refusal}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"D2, /{endpoint}: only the decimals may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, f"D2: /{endpoint} refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        assert ("create", subject_index) in _in_batch(response), f"D2: the refused row stays in the batch (applied and reported); the results are {response.results}"
        assert barrier_id in await _stored(world, [barrier_id]), f"scaffold: the read-back no longer sees row id={barrier_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"D2: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("average", REPEATING_AVERAGES)
    async def test_manual_update_carrying_the_same_amount_is_still_refused(self, world, average):
        """Guard (D2): an update setting a stored ADJUSTMENT +1 to a ``manual`` cost basis of the same amounts, sent at
        index 1 behind a notes edit, is refused on update 1 with ``ref_id`` its id; not committed; both rows read back as
        they were stored.

        Green today: ``check_decimal_limits`` checks every cost basis. A cure for ``tx-commit-all-types.spec.ts:532``
        that stops checking it whatever the mode turns it red.
        """
        await _seed_pool(world, average.pool_cost)
        updates, subject_id, neighbour_id = await _cost_basis_update(world, "manual", average.sent)
        before = await _stored(world, [neighbour_id, subject_id])

        response = await _run_as_the_endpoint(world, updates=updates)

        refusal = ("update", 1, subject_id, average.code, "cost_basis_override", average.params)
        assert _decimal_issues(response) == [refusal], f"D2: a manual cost basis of {average.sent} EUR on the update of ADJUSTMENT id={subject_id} must be refused on its own row with exactly {refusal}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"D2: only the decimals may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, "D2: /commit refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        assert ("update", 1) in _in_batch(response), f"D2: the refused update stays in the batch (applied and reported); the results are {response.results}"
        after = await _stored(world, [neighbour_id, subject_id])
        assert after == before, f"D2: the batch was refused, yet the stored rows changed: before {before}, after {after}"


# ============================================================================
# RED AND GUARDS — RULE 6 (R13-SEC2): THE INTEGER DIGITS
# ============================================================================

# A create past its integer digits on ``main`` — sent at index 1, behind a valid BUY — and the limit issues it gets, as
# (code, field, params): few digits and no decimal, so only the integer digits refuse it — 15 for a quantity and a cash
# amount, 12 for a cost basis (decision N63). 1E+400 is beyond a double too: before the cure it became a REAL inf.
INTEGER_CREATE_REFUSALS = [
    pytest.param({"tx_type": "BUY", "quantity": "1E+60", "cash": "-10"}, [(INTEGER_DIGITS_EXCEEDED, "quantity", QUANTITY_INTEGER_MAX)], id="quantity-1E+60"),
    pytest.param({"tx_type": "BUY", "quantity": "1000000000000000", "cash": "-10"}, [(INTEGER_DIGITS_EXCEEDED, "quantity", QUANTITY_INTEGER_MAX)], id="quantity-16-integer-digits"),
    pytest.param({"tx_type": "BUY", "quantity": "1E+400", "cash": "-10"}, [(INTEGER_DIGITS_EXCEEDED, "quantity", QUANTITY_INTEGER_MAX)], id="quantity-1E+400-beyond-a-double"),
    pytest.param({"tx_type": "BUY", "quantity": "1", "cash": "-1E+15"}, [(INTEGER_DIGITS_EXCEEDED, "cash.amount", CASH_INTEGER_MAX)], id="cash-amount--1E+15"),
    pytest.param({"tx_type": "ADJUSTMENT", "quantity": "1", "cost": "1E+60"}, [(INTEGER_DIGITS_EXCEEDED, "cost_basis_override", COST_INTEGER_MAX)], id="adjustment-in-cost-basis-1E+60"),
    pytest.param({"tx_type": "ADJUSTMENT", "quantity": "1", "cost": "1000000000000"}, [(INTEGER_DIGITS_EXCEEDED, "cost_basis_override", COST_INTEGER_MAX)], id="adjustment-in-cost-basis-13-integer-digits"),
]

# A value of a million digits on an ordinary broker: the subject's fields, and the limit issue its row gets as
# (code, field, params). The coordinator's (a); (b) has its own test, and so has (c) since R13-SEC7-3 — a cash amount is
# a Currency, refused at the boundary before any limit is read (``test_a_cash_amount_of_a_million_digits_is_refused_at_the_boundary_without_raising``).
MILLION_DIGIT_REFUSALS = [
    pytest.param({"quantity": "1E+1000000", "cash": "-10"}, (INTEGER_DIGITS_EXCEEDED, "quantity", QUANTITY_INTEGER_MAX), id="a-quantity-1E+1000000"),
]
#: (c) since R13-SEC7-3: a BUY of 1 unit for -1E+1000000 EUR, whose cash amount the Currency's bound refuses at the parse.
MILLION_DIGIT_CASH = {"quantity": "1", "cash": "-1E+1000000"}
FOUR_HUNDRED_ONES = "1" * 400


async def _ordinary_broker(world: World) -> tuple[int, int]:
    """A broker of the test with the default settings — no cash overdraft, no asset shorting — holding a DEPOSIT of 100
    EUR on ``SEED_DAY``: a BUY of 10 EUR is valid there but for its digits, whatever ``main`` allows. Its id, and the
    deposit's (a row written before the batch, which the read-back must still see)."""
    now = utcnow()
    broker = Broker(name=f"{world.marker} ordinary", description="R13-SEC2: a broker with the default settings", created_at=now, updated_at=now)
    world.session.add(broker)
    await world.session.flush()
    assert (broker.allow_cash_overdraft, broker.allow_asset_shorting) == (False, False), f"scaffold: a broker's defaults changed, it allows (overdraft, shorting) = {(broker.allow_cash_overdraft, broker.allow_asset_shorting)}"
    broker_id = broker.id
    deposit_id = await _insert(world, broker_id=broker_id, asset_id=None, type=TransactionType.DEPOSIT, date=SEED_DAY, quantity=Decimal("0"), amount=Decimal("100"), currency=EUR)
    return broker_id, deposit_id


def _million_digit_batch(world: World, broker_id: int, subject: dict) -> list[dict]:
    """A valid BUY of 1 unit for 10 EUR on ``broker_id``, then the subject: a BUY of ``subject["quantity"]`` units for
    ``subject["cash"]`` EUR there, at index 1."""
    return [_row(world, "BUY", "1", cash="-10", broker_id=broker_id), _row(world, "BUY", subject["quantity"], cash=subject["cash"], broker_id=broker_id)]


class TestTooManyIntegerDigitsAreRefused:
    """Rule 6 (R13-SEC2): a quantity or a cash amount past 15 integer digits, a manual cost basis past 12 (decision N63),
    is refused at confirmation with ``integerDigitsExceeded`` and that ``{"max": N}``, never stored; and a checked value
    past its column's integer digits, whichever code it gets, stops the batch right after ``check_decimal_limits``.

    Today the limit has no magnitude, and the row goes on through the stages: created, flushed, then reloaded by
    ``validate_cost_basis`` (``_check_result_create_cost_basis``) through the column's type — a quantity or a cost basis
    of 1E+60 raises ``InvalidOperation`` there, one of 1E+400 or of 400 digits (a REAL inf) ``TypeError``: a 500 on
    ``/validate`` and ``/commit``; a quantity of 16 digits, a cash amount of -1E+15, a cost basis of 13 digits and an
    update to 1E+60 pass unrefused (``/commit`` commits them); ``decimal_limit_issue`` raises ``decimal.Overflow`` on
    ``1E+1000000``. The refused row is not asserted in the results: the batch stops before applying it.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize(("subject", "expected"), INTEGER_CREATE_REFUSALS)
    async def test_create_past_the_integer_digits_is_refused_on_its_row(self, world, subject, expected, endpoint):
        """Red today: nothing refuses it — a quantity of 16 digits, a cash amount of -1E+15 and a cost basis of 13 digits
        get no issue (``/commit`` commits them); a quantity or a cost basis of 1E+60 makes ``validate_cost_basis`` raise
        ``InvalidOperation`` as it reloads the row, 1E+400 ``TypeError`` (a REAL inf): a 500.

        Contract: exactly the expected issues on create 1 (``ref_id`` None), each with an English ``error`` naming its
        field, nothing else; not committed; no row of the batch in the database.
        """
        barrier_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        creates = [_row(world, "BUY", "1", cash="-100"), _row(world, **subject)]

        response = await _run_never_raising(world, f"the create {subject}", creates=creates, endpoint=endpoint)

        refusals = sorted((("create", 1, None, code, field, params) for code, field, params in expected), key=_issue_order)
        assert _decimal_issues(response) == refusals, f"R13-SEC2, /{endpoint}: the create {subject} must be refused on its own row with exactly {refusals}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"R13-SEC2, /{endpoint}: only the integer digits may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, f"R13-SEC2: /{endpoint} refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        assert barrier_id in await _stored(world, [barrier_id]), f"scaffold: the read-back no longer sees row id={barrier_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"R13-SEC2: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    async def test_update_of_a_quantity_past_the_integer_digits_is_refused_on_its_row(self, world):
        """Red today: the update of a stored BUY's quantity to 1E+60 commits.

        Contract: refused on update 1 (behind a valid notes edit), ``ref_id`` its id, ``integerDigitsExceeded``
        ``{"max": 15}`` on ``quantity``, nothing else; not committed; both rows read back as they were stored.
        """
        neighbour_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        subject_id = await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        before = await _stored(world, [neighbour_id, subject_id])
        updates = [{"id": neighbour_id, "description": f"{world.marker} neighbour edited"}, {"id": subject_id, "quantity": "1E+60"}]

        response = await _run_never_raising(world, f"the update of BUY id={subject_id} to 1E+60 units", updates=updates)

        refusal = ("update", 1, subject_id, INTEGER_DIGITS_EXCEEDED, "quantity", QUANTITY_INTEGER_MAX)
        assert _decimal_issues(response) == [refusal], f"R13-SEC2: the update of id={subject_id} to 1E+60 units must be refused on its own row with exactly {refusal}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"R13-SEC2: only the integer digits may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, "R13-SEC2: /commit refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        after = await _stored(world, [neighbour_id, subject_id])
        assert after == before, f"R13-SEC2: the batch was refused, yet the stored rows changed: before {before}, after {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize(("subject", "refusal"), MILLION_DIGIT_REFUSALS)
    async def test_a_value_of_a_million_digits_is_refused_without_raising(self, world, subject, refusal, endpoint):
        """Red today: ``decimal.Overflow`` in ``decimal_limit_issue``'s ``normalize`` (a context of 60 digits, ``Emax``
        999999): the endpoint answers 500.

        Contract (the coordinator's (a), on an ordinary broker — no overdraft, no shorting — so nothing but the digits
        can refuse the row): no exception; the subject's row, create 1, gets ``integerDigitsExceeded`` ``{"max": 15}``
        (decision N63) on its field (``quantity`` for a BUY of 1E+1000000 units), the only limit issue of the batch; not
        committed; nothing saved. The coordinator's (c), a cash amount of -1E+1000000 EUR, has its own test since
        R13-SEC7-3: ``test_a_cash_amount_of_a_million_digits_is_refused_at_the_boundary_without_raising``.
        """
        broker_id, deposit_id = await _ordinary_broker(world)
        code, field, params = refusal

        response = await _run_never_raising(world, f"a BUY of {subject['quantity']} units for {subject['cash']} EUR on an ordinary broker", creates=_million_digit_batch(world, broker_id, subject), endpoint=endpoint)

        expected = [("create", 1, None, code, field, params)]
        assert _decimal_issues(response) == expected, f"R13-SEC2, /{endpoint}: the BUY of {subject['quantity']} units for {subject['cash']} EUR must be refused on its own row with {expected}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert response.committed is False, f"R13-SEC2: /{endpoint} refused the batch, yet answered committed"
        assert deposit_id in await _stored(world, [deposit_id]), f"scaffold: the read-back no longer sees the deposit id={deposit_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"R13-SEC2: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    async def test_a_cash_amount_of_a_million_digits_is_refused_at_the_boundary_without_raising(self, world, endpoint):
        """The coordinator's (c), formerly the case ``c-cash-amount--1E+1000000`` of
        ``test_a_value_of_a_million_digits_is_refused_without_raising``: re-pinned by R13-SEC7-3, a contract change.

        Red until the bound: the cash amount reaches ``check_decimal_limits``, which answers ``integerDigitsExceeded``
        ``{"max": 15}`` on ``cash.amount`` (W-B58's contract for this case).

        Contract: a cash amount is a ``Currency``, whose amount's exponent is bounded (``adjusted()`` within [-100, 100]),
        so the row fails the batch's lenient parse (``_parse_lenient``) and never reaches ``check_decimal_limits``: on
        create 1, exactly one issue, ``value_error`` on ``cash.amount``, ``params`` None, an English error naming the
        exponent; no limit issue in the batch. The case's purpose is unchanged: on an ordinary broker (no overdraft, no
        shorting), through ``/validate`` and ``/commit``, no exception, not committed, nothing saved.
        """
        broker_id, deposit_id = await _ordinary_broker(world)

        response = await _run_never_raising(world, f"a BUY of {MILLION_DIGIT_CASH['quantity']} unit for {MILLION_DIGIT_CASH['cash']} EUR on an ordinary broker", creates=_million_digit_batch(world, broker_id, MILLION_DIGIT_CASH), endpoint=endpoint)

        on_its_row = [issue for issue in response.issues if (issue.operation, issue.index) == ("create", 1)]
        refusal = [(issue.ref_id, issue.code, issue.field, issue.params) for issue in on_its_row]
        assert refusal == [(None, "value_error", "cash.amount", None)], f"R13-SEC7-3, /{endpoint}: -1E+1000000 EUR must be refused by the batch's lenient parse, exactly value_error on cash.amount, no params; committed={response.committed}, issues: {_render(response.issues)}"
        assert "exponent" in (on_its_row[0].error or "").lower(), f"R13-SEC7-3, /{endpoint}: the parse refusal's English error must name the exponent; it reads {on_its_row[0].error!r}"
        assert _decimal_issues(response) == [], f"R13-SEC7-3, /{endpoint}: the row is refused before check_decimal_limits, so the batch holds no limit issue: {_render(response.issues)}"
        assert response.committed is False, f"R13-SEC7-3: /{endpoint} refused the batch, yet answered committed"
        assert deposit_id in await _stored(world, [deposit_id]), f"scaffold: the read-back no longer sees the deposit id={deposit_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"R13-SEC7-3: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    async def test_a_quantity_of_400_digits_keeps_the_significant_digit_code_and_every_issue_has_a_code(self, world, endpoint):
        """Red today: the quantity gets ``significantDigitsExceeded``, then its row goes on through the stages as a float
        inf (a double holds no 400 digits): ``validate_cost_basis`` reloads it and raises ``TypeError`` (a 500) — measured
        in this worktree, before the balance replay, which would otherwise add «Balance validation error: …», an issue
        without a code that the app can only show as a raw English text.

        Contract (the coordinator's (b), on an ordinary broker): no exception; the issue on ``quantity`` keeps the first
        code in order, ``significantDigitsExceeded`` ``{"max": 15}`` (past 15 integer digits too, so the batch stops
        right after ``check_decimal_limits``); every issue of the response has a code, none reads «Balance validation
        error»; not committed; nothing saved.
        """
        broker_id, deposit_id = await _ordinary_broker(world)
        subject = {"quantity": FOUR_HUNDRED_ONES, "cash": "-10"}

        response = await _run_never_raising(world, "a BUY of 400 ones (a quantity of 400 digits) on an ordinary broker", creates=_million_digit_batch(world, broker_id, subject), endpoint=endpoint)

        expected = [("create", 1, None, SIGNIFICANT_DIGITS_EXCEEDED, "quantity", DIGITS_MAX)]
        assert _decimal_issues(response) == expected, f"R13-SEC2, /{endpoint}: a quantity of 400 digits must keep the first code in order, {expected}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        without_code = [issue for issue in response.issues if issue.code is None]
        assert without_code == [], f"R13-SEC2, /{endpoint}: every issue must carry a code — the app translates the code, a raw text reaches the user in English; these have none: {_render(without_code)}"
        raw_balance = [issue for issue in response.issues if "Balance validation error" in (issue.error or "")]
        assert raw_balance == [], f"R13-SEC2, /{endpoint}: the batch must stop before the balance replay, which cannot replay a quantity of 400 digits: {_render(raw_balance)}"
        assert response.committed is False, f"R13-SEC2: /{endpoint} refused the batch, yet answered committed"
        assert deposit_id in await _stored(world, [deposit_id]), f"scaffold: the read-back no longer sees the deposit id={deposit_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"R13-SEC2: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "subject",
        [
            pytest.param({"tx_type": "BUY", "quantity": "999999999999999", "cash": "-999999999999999"}, id="quantity-and-cash-amount-15-integer-digits"),
            pytest.param({"tx_type": "BUY", "quantity": "1000000000000", "cash": "-1E+13"}, id="quantity-13-and-cash-amount-14-integer-digits"),
            pytest.param({"tx_type": "ADJUSTMENT", "quantity": "1", "cost": "999999999999.999"}, id="cost-basis-12-integer-digits-15-significant-digits"),
        ],
    )
    async def test_guard_the_integer_digits_at_the_limit_commit(self, world, subject):
        """Guard: green today and after. The integer limit is reached, not passed: 15 digits for a quantity and a cash
        amount (decision N63: 13 and 14 commit too), 12 for a cost basis; the create commits with no issue."""
        response = await _run_never_raising(world, f"the create {subject}", creates=[_row(world, **subject)])

        assert response.committed is True and response.issues == [], f"R13-SEC2: {subject} is within the integer digits of its fields (15 for a quantity and a cash amount, 12 for a cost basis), so it must commit; it was refused: {_render(response.issues)}"


# A promote's resolved cost basis over a limit of its column, ``cost_basis_override`` (24, 12): the code and params of
# its refusal. The first two leave the batch going to its end, uncommitted; the last two, past the integer digits,
# stop it right after ``check_decimal_limits``.
PROMOTED_COSTS_OVER_A_LIMIT = [
    pytest.param(COST_13_DECIMALS, DECIMAL_PLACES_EXCEEDED, COST_MAX, id="13-decimals"),
    pytest.param("3333.333333333333", SIGNIFICANT_DIGITS_EXCEEDED, DIGITS_MAX, id="16-significant-digits"),
    pytest.param("1000000000000", INTEGER_DIGITS_EXCEEDED, COST_INTEGER_MAX, id="13-integer-digits"),
    pytest.param("1E+60", INTEGER_DIGITS_EXCEEDED, COST_INTEGER_MAX, id="1E+60"),
]


async def _promotable_pair(world: World) -> tuple[int, int]:
    """A stored pair a promote turns into a TRANSFER (``promote_from``: same asset, other broker, opposite quantity): an
    ADJUSTMENT −1 on ``main`` and an ADJUSTMENT +1 on ``other`` at a manual cost of 100 EUR a unit. Their ids (giving,
    receiving); the caller seeds the unit ``main`` gives (it may not go short)."""
    giving_id = await _seed_position(world, TransactionType.ADJUSTMENT, "-1")
    receiving_id = await _insert(world, broker_id=world.other_id, asset_id=world.asset_id, type=TransactionType.ADJUSTMENT, date=SEED_DAY, quantity=Decimal("1"), amount=Decimal("0"), currency=None, cost_basis_override=Decimal("100"), cost_basis_currency=EUR)
    return giving_id, receiving_id


async def _pair_state(world: World, ids) -> dict[int, tuple]:
    """What a promote changes on the rows ``ids``, as the database holds them: (type, related id, cost basis, currency)."""
    statement = select(Transaction.id, Transaction.type, Transaction.related_transaction_id, Transaction.cost_basis_override, Transaction.cost_basis_currency).where(Transaction.id.in_(list(ids)))
    return {row.id: (row.type, row.related_transaction_id, row.cost_basis_override, row.cost_basis_currency) for row in await world.session.execute(statement)}


def _limit_issues_without_ref(response: TXBatchResponse) -> list[tuple]:
    """The batch's refusals over a column's limit as ``(operation, index, code, field, params)``, sorted: which row a
    promote's ``ref_id`` names is not the subject."""
    return sorted((operation, index, code, field, params) for operation, index, _ref_id, code, field, params in _decimal_issues(response))


class TestAPromotedCostBasisIsChecked:
    """Rule 6 (R13-SEC2): the cost basis a promote resolves (``resolved_fields.cost_basis_override``, the PromoteMergeModal's
    merged value) is checked against the column ``cost_basis_override`` like a create's.

    Today ``_apply_promote_cost_basis`` writes it without a check: the REAL rounds what it cannot keep, and nothing limits
    its magnitude.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize(("amount", "code", "params"), PROMOTED_COSTS_OVER_A_LIMIT)
    async def test_promote_with_a_resolved_cost_basis_over_a_limit_is_refused_on_its_index(self, world, amount, code, params, endpoint):
        """Red today: no issue — ``/commit`` commits both promotes, the second with that cost basis on its receiving leg.

        Contract: two promotes of stored pairs, the second (index 1) resolving a cost basis of ``amount`` EUR: exactly one
        limit issue, ``operation="promote"``, index 1, ``field="cost_basis_override"``, ``code`` with ``params``, its
        English ``error`` naming the field; nothing else; not committed; all four rows as they were stored.
        """
        await _seed_position(world, TransactionType.BUY, "2", amount="-200")
        first = await _promotable_pair(world)
        second = await _promotable_pair(world)
        before = await _pair_state(world, [*first, *second])
        promotes = [{"id_a": first[0], "id_b": first[1]}, {"id_a": second[0], "id_b": second[1], "resolved_fields": {"cost_basis_override": {"code": EUR, "amount": amount}}}]

        response = await _run_never_raising(world, f"a promote resolving a cost basis of {amount} EUR", promotes=promotes, endpoint=endpoint)

        expected = [("promote", 1, code, "cost_basis_override", params)]
        assert _limit_issues_without_ref(response) == expected, f"R13-SEC2, /{endpoint}: the promote resolving a cost basis of {amount} EUR must be refused on its own index with {expected}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"R13-SEC2, /{endpoint}: only the limit may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, f"R13-SEC2: /{endpoint} refused the batch, yet answered committed"
        _assert_errors_name_their_fields(response)
        after = await _pair_state(world, [*first, *second])
        assert after == before, f"R13-SEC2: the batch was refused, yet the stored rows changed: before {before}, after {after}"

    @pytest.mark.asyncio
    async def test_guard_a_promote_with_a_resolved_cost_basis_of_12_decimals_commits(self, world):
        """Guard: green today and after. A resolved cost basis of 0.000003457312 EUR (12 decimals, the maximum) commits,
        and the receiving leg holds it exactly; the giving leg holds none (decision 47)."""
        await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        giving_id, receiving_id = await _promotable_pair(world)
        promotes = [{"id_a": giving_id, "id_b": receiving_id, "resolved_fields": {"cost_basis_override": {"code": EUR, "amount": "0.000003457312"}}}]

        response = await _run_never_raising(world, "a promote resolving a cost basis of 0.000003457312 EUR", promotes=promotes)

        assert response.committed is True and response.issues == [], f"R13-SEC2: a resolved cost basis of 12 decimals is within the limit, yet the promote was refused: {_render(response.issues)}"
        state = await _pair_state(world, [giving_id, receiving_id])
        expected = {giving_id: (TransactionType.TRANSFER, receiving_id, None, None), receiving_id: (TransactionType.TRANSFER, giving_id, Decimal("0.000003457312"), EUR)}
        assert state == expected, f"The promoted pair reads back {state}: expected {expected}"


# A promote's resolved cost basis that ``Currency`` refuses (R13-SEC7-3, rule 9), and whether its English error must name
# the exponent: past the bound (``adjusted()`` outside [-100, 100]) — just past it, far past it, a zero whose exponent is
# -999999999 (a zero's ``adjusted()`` is its exponent) — and no number at all, whose text is not pinned.
PROMOTED_COSTS_CURRENCY_REFUSES = [
    pytest.param("1E+101", True, id="1E+101"),
    pytest.param("1E+5000000", True, id="1E+5000000"),
    pytest.param("0E-999999999", True, id="0E-999999999"),
    pytest.param("abc", False, id="abc"),
]


async def _two_promotes_resolving(world: World, amount: str | None = None, *, resolved_fields: dict | None = None) -> tuple[list[int], list[dict]]:
    """``TestAPromotedCostBasisIsChecked``'s ground: two stored pairs, and their promotes, the second (index 1) resolving
    ``resolved_fields`` — by default a cost basis of ``amount`` EUR. The four ids (giving, receiving, giving, receiving),
    and the promotes."""
    if resolved_fields is None:
        resolved_fields = {"cost_basis_override": {"code": EUR, "amount": amount}}
    await _seed_position(world, TransactionType.BUY, "2", amount="-200")
    first = await _promotable_pair(world)
    second = await _promotable_pair(world)
    promotes = [{"id_a": first[0], "id_b": first[1]}, {"id_a": second[0], "id_b": second[1], "resolved_fields": resolved_fields}]
    return [*first, *second], promotes


class TestAPromotedCostBasisCurrencyRefuses:
    """R13-SEC7-3 (rule 9): a resolved cost basis that ``Currency`` refuses is an issue of its promote, and the batch stops.

    ``_promote_cost_amount`` reads ``resolved_fields.cost_basis_override`` through ``Currency.model_validate`` and answers
    None when it is refused, so nothing checks the value; ``_apply_promote_cost_basis`` (``batch_creates.py``) validates it
    again, unguarded, and its ``ValidationError`` leaves the batch: a 500. Today that is the fate of «abc». Once
    ``Currency`` bounds the exponent it would be the fate of every value past the bound, which today get W-B58's
    ``integerDigitsExceeded`` ``{"max": 12}`` (1E+101, 1E+5000000) or commit (a zero of exponent -999999999).
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize(("amount", "names_the_exponent"), PROMOTED_COSTS_CURRENCY_REFUSES)
    async def test_a_resolved_cost_basis_currency_refuses_is_the_one_issue_of_its_promote(self, world, amount, names_the_exponent, endpoint):
        """Red today: 1E+101 and 1E+5000000 get ``integerDigitsExceeded`` ``{"max": 12}`` on ``cost_basis_override``; the
        zero of exponent -999999999 commits; «abc» raises ``ValidationError`` out of the batch.

        Contract: exactly one issue, on ``operation="promote"``, index 1: ``value_error`` on ``cost_basis_override.amount``,
        ``params`` None, its English error naming the exponent (for «abc» the text is not pinned); no limit issue, nothing
        else; not committed; the four rows as they were stored; nothing raises.
        """
        ids, promotes = await _two_promotes_resolving(world, amount)
        before = await _pair_state(world, ids)

        response = await _run_never_raising(world, f"a promote resolving a cost basis of {amount} EUR", promotes=promotes, endpoint=endpoint)

        issues = [(issue.operation, issue.index, issue.code, issue.field, issue.params) for issue in response.issues]
        expected = [("promote", 1, "value_error", "cost_basis_override.amount", None)]
        assert issues == expected, f"R13-SEC7-3, /{endpoint}: a resolved cost basis of {amount} EUR, which Currency refuses, must be the one issue of its promote, {expected}; committed={response.committed}, issues: {_render(response.issues)}"
        if names_the_exponent:
            assert "exponent" in (response.issues[0].error or "").lower(), f"R13-SEC7-3, /{endpoint}: the refusal of {amount} EUR must name the exponent in its English error; it reads {response.issues[0].error!r}"
        assert response.committed is False, f"R13-SEC7-3: /{endpoint} refused the batch, yet answered committed"
        after = await _pair_state(world, ids)
        assert after == before, f"R13-SEC7-3: the batch was refused, yet the stored rows changed: before {before}, after {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    async def test_guard_a_resolved_cost_basis_at_the_bound_keeps_the_integer_digit_refusal(self, world, endpoint):
        """Guard: green today and after. 1E+100 is inside the bound (``adjusted()`` 100), so ``Currency`` keeps it and W-B58's
        check refuses it on its index, ``integerDigitsExceeded`` ``{"max": 12}`` on ``cost_basis_override``, nothing else;
        not committed; the four rows as they were stored; nothing raises."""
        ids, promotes = await _two_promotes_resolving(world, "1E+100")
        before = await _pair_state(world, ids)

        response = await _run_never_raising(world, "a promote resolving a cost basis of 1E+100 EUR", promotes=promotes, endpoint=endpoint)

        expected = [("promote", 1, INTEGER_DIGITS_EXCEEDED, "cost_basis_override", COST_INTEGER_MAX)]
        assert _limit_issues_without_ref(response) == expected, f"R13-SEC7-3, /{endpoint}: a resolved cost basis of 1E+100 EUR, inside the bound, must keep W-B58's refusal {expected}; committed={response.committed}, issues: {_render(response.issues)}"
        assert _other_issues(response) == [], f"R13-SEC7-3, /{endpoint}: only the limit may refuse this batch: {_render(_other_issues(response))}"
        assert response.committed is False, f"R13-SEC7-3: /{endpoint} refused the batch, yet answered committed"
        after = await _pair_state(world, ids)
        assert after == before, f"R13-SEC7-3: the batch was refused, yet the stored rows changed: before {before}, after {after}"


# ============================================================================
# RED AND GUARDS — RULE 10 (H-41): A PROMOTE'S RESOLVED FIELDS ARE TYPED
# ============================================================================

# A promote's resolved fields the typed model refuses, and the issue its batch answers on the promote: pydantic's type, the
# merged field's own name, without ``resolved_fields.``, and whether it carries params — pydantic's own context, when it is
# plain data (W-B70, D-W70-1): ``{max_length}``, a date's parsing error ``{error}``, ``{class_name}`` of a cost basis that is
# no object; never a value_error's (the exception itself), nor an error without context. A value of the wrong kind (a JSON
# ``Infinity`` arrives as a float), a text past 500 characters, tags that are neither a list nor a text, a date that is none
# or an explicit null, a cost basis that is no currency, a key the model does not know.
RESOLVED_FIELDS_REFUSED = [
    pytest.param({"description": 123}, "string_type", "description", False, id="description-123"),
    pytest.param({"description": float("inf")}, "string_type", "description", False, id="description-inf"),
    pytest.param({"description": ["a"]}, "string_type", "description", False, id="description-list"),
    pytest.param({"description": "x" * 501}, "string_too_long", "description", True, id="description-501-characters"),
    pytest.param({"tags": 123}, "value_error", "tags", False, id="tags-123"),
    pytest.param({"tags": {"a": 1}}, "value_error", "tags", False, id="tags-object"),
    pytest.param({"date": "not-a-date"}, "date_from_datetime_parsing", "date", True, id="date-not-a-date"),
    pytest.param({"date": "2026-02-30"}, "date_from_datetime_parsing", "date", True, id="date-2026-02-30"),
    pytest.param({"date": None}, "value_error", "date", False, id="date-explicit-null"),
    pytest.param({"cost_basis_override": "12"}, "model_type", "cost_basis_override", True, id="cost-basis-not-an-object"),
    pytest.param({"cost_basis_override": {"amount": "1"}}, "missing", "cost_basis_override.code", False, id="cost-basis-without-code"),
    pytest.param({"quantity": "5"}, "extra_forbidden", "quantity", False, id="unknown-key-quantity"),
]
# The plain data a context may hold to become params (D-W70-1): str, int, float, bool, None.
PLAIN_DATA = (str, int, float, bool, type(None))

# A promote's resolved fields the typed model keeps, and what ``/commit`` stores on the second pair: its merged fields
# (``description``, the ``tags`` CSV, ``date``) on both rows, and the (cost, currency) of its receiving leg.
RESOLVED_FIELDS_KEPT = [
    pytest.param({"description": "d" * 500}, {"description": "d" * 500}, None, id="description-500-characters"),
    pytest.param({"tags": ["a", "b"]}, {"tags": "a,b"}, None, id="tags-list"),
    pytest.param({"date": DAY.isoformat()}, {"date": DAY}, None, id="date-inside-N74"),
    pytest.param({"cost_basis_override": {"code": EUR, "amount": "12.5"}}, None, (Decimal("12.5"), EUR), id="cost-basis-on-the-receiving-leg-only"),
    pytest.param({"description": None}, {"description": None}, None, id="description-explicit-null-clears-it"),
    pytest.param({"tags": ["a"]}, {"tags": "a"}, None, id="tags-alone-leave-the-descriptions"),
    pytest.param({}, None, None, id="empty-changes-nothing"),
]
# Where each merged field sits in ``_merged_fields``.
MERGED_FIELD_POSITIONS = {"description": 0, "tags": 1, "date": 2}


async def _merged_fields(world: World, ids) -> dict[int, tuple]:
    """What a promote's resolved fields change on the rows ``ids``, as the database holds them: (description, tags, date)."""
    statement = select(Transaction.id, Transaction.description, Transaction.tags, Transaction.date).where(Transaction.id.in_(list(ids)))
    return {row.id: (row.description, row.tags, row.date) for row in await world.session.execute(statement)}


async def _four_rows(world: World, ids) -> tuple[dict, dict]:
    """The four rows of ``_two_promotes_resolving`` as the database holds them: ``_pair_state`` and ``_merged_fields``."""
    return await _pair_state(world, ids), await _merged_fields(world, ids)


def _promoted(before: tuple[dict, dict], ids: list[int], *, merged: dict | None = None, receiving_cost: tuple | None = None) -> tuple[dict, dict]:
    """``before`` once both promotes committed: each pair a TRANSFER linked both ways, the giving leg without a cost basis
    (decision 47), the receiving leg with its own — ``receiving_cost`` on the second's when given — and the second pair's
    merged fields, on both rows, updated with ``merged``."""
    pairs, fields = before
    promoted_pairs = {}
    for giving, receiving in ((ids[0], ids[1]), (ids[2], ids[3])):
        promoted_pairs[giving] = (TransactionType.TRANSFER, receiving, None, None)
        cost = receiving_cost if receiving == ids[3] and receiving_cost is not None else pairs[receiving][2:]
        promoted_pairs[receiving] = (TransactionType.TRANSFER, giving, *cost)
    promoted_fields = dict(fields)
    for row_id in ids[2:]:
        values = list(fields[row_id])
        for key, value in (merged or {}).items():
            values[MERGED_FIELD_POSITIONS[key]] = value
        promoted_fields[row_id] = tuple(values)
    return promoted_pairs, promoted_fields


async def _read_as_the_list_does(world: World, ids: list[int]) -> tuple[str | None, list[int]]:
    """The rows ``ids`` read as ``GET /transactions`` builds them — ``TransactionService.query``, each row through
    ``TXReadItem.from_db_model`` — in the session that ran the batch: (None, the ids read) when they read, otherwise (the
    refusal, which the endpoint answers with a 500, [])."""
    try:
        items = await TransactionService(world.session).query(TXQueryParams(ids=ids))
    except ValidationError as exc:
        return "; ".join(f"{'.'.join(str(part) for part in error['loc'])}: {error['type']} ({error['msg']})" for error in exc.errors()), []
    return None, [item.id for item in items]


def _shown(resolved_fields: dict) -> str:
    """``resolved_fields`` for a message: a long text by its length."""
    shown = {key: f"<{len(value)} characters>" if isinstance(value, str) and len(value) > 40 else value for key, value in resolved_fields.items()}
    return f"resolved_fields {shown}"


def _resolved_fields_error(resolved_fields: dict) -> dict:
    """The one error pydantic itself reports for ``resolved_fields`` under ``TXPromoteResolvedFields``: what the promote's
    issue is made of, read from pydantic so that no text of its is pinned here."""
    try:
        TXPromoteResolvedFields.model_validate(resolved_fields)
    except ValidationError as exc:
        errors = exc.errors()
        assert len(errors) == 1, f"scaffold: {_shown(resolved_fields)} must be refused by one error of pydantic's; it answers {errors}"
        return errors[0]
    pytest.fail(f"scaffold: TXPromoteResolvedFields accepts {_shown(resolved_fields)}: the case refuses nothing")


def _plain_params(error: dict) -> dict | None:
    """The params D-W70-1 gives ``error``: a copy of its context when every value is plain data (``PLAIN_DATA``); None when
    it has none, or holds one that is not (a value_error's exception)."""
    context = error.get("ctx")
    if not context or not all(isinstance(value, PLAIN_DATA) for value in context.values()):
        return None
    return dict(context)


async def _tag(world: World, ids, tags: str) -> None:
    """Store ``tags`` on the rows ``ids``, through their ORM objects: the session and the database then agree on them."""
    for row_id in ids:
        row = await world.session.get(Transaction, row_id)
        row.tags = tags
    await world.session.flush()


async def _assert_accepted(world: World, ids: list[int], promotes: list[dict], endpoint: str, story: str, *, merged: dict | None = None, receiving_cost: tuple | None = None) -> None:
    """The batch of ``promotes`` is accepted: no issue, nothing raised; ``/validate`` writes nothing, ``/commit`` commits
    both pairs as ``_promoted`` reads them (``merged``, ``receiving_cost``)."""
    before = await _four_rows(world, ids)

    response = await _run_never_raising(world, story, promotes=promotes, endpoint=endpoint)

    assert response.issues == [], f"H-41, /{endpoint}: {story} must be accepted; issues: {_render(response.issues)}"
    assert response.committed is (endpoint == "commit"), f"H-41: /{endpoint} accepted {story}, yet answered committed={response.committed}"
    expected = _promoted(before, ids, merged=merged, receiving_cost=receiving_cost) if endpoint == "commit" else before
    after = await _four_rows(world, ids)
    assert after == expected, f"H-41, /{endpoint}: after {story} the four rows read {after}; expected {expected}"


class TestTheResolvedFieldsAreTyped:
    """Rule 10 (H-41): the fields a promote resolves are typed like a create's.

    ``TXPromoteBatchItem.resolved_fields`` is a ``Dict[str, Any]`` that ``batch_creates._apply_promote_resolved_fields``
    applies as it is. A number in ``description`` reaches the Text column, and the list's read of the row
    (``TXReadItem.description: Optional[str]``) is a 500; a malformed ``date`` or ``tags`` raises out of the batch, a 500;
    an unknown key is ignored. It becomes the ``StrictModel`` ``TXPromoteResolvedFields`` — ``description`` a text of at
    most 500 characters, ``tags`` through ``validate_tags_list``, ``date`` a date (an explicit null refused),
    ``cost_basis_override`` a ``Currency``, no other key. A refusal is an issue of the batch's lenient parse on the promote,
    pydantic's type, ``field`` the merged field's own name, ``params`` pydantic's own context when it is plain data (W-B70,
    D-W70-1), None otherwise; that promote is not applied, nothing is saved.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize(("resolved_fields", "code", "field", "carries_params"), RESOLVED_FIELDS_REFUSED)
    async def test_a_resolved_field_the_model_refuses_is_the_one_issue_of_its_promote(self, world, resolved_fields, code, field, carries_params, endpoint):
        """Red today: a description of 123 or ``inf`` commits, and the pair no longer reads (``string_type``); a list
        description, tags of 123 and the three dates raise out of the batch; 501 characters, tags ``{"a": 1}`` (stored
        «a») and the unknown key commit. The cost basis cases already get their issue from ``check_decimal_limits``
        (R13-SEC7-3), which reads the resolved cost basis through ``Currency``. Since H-41, red for W-B70 (D-W70-1) where
        pydantic's context is plain data — 501 characters (``{max_length: 500}``), the two dates (``{error: <pydantic's
        text>}``), the cost basis «12» (``{class_name: "Currency"}``) —: today their issue carries no params.

        Contract: exactly one issue, ``("promote", 1, code, field, params)``, ``params`` the context pydantic itself
        reports for these resolved fields when it is plain data (read from pydantic, never pinned), None otherwise; the
        pair still reads as the list builds it; not committed; the four rows as they were stored; nothing raises.
        """
        error = _resolved_fields_error(resolved_fields)
        assert error["type"] == code, f"scaffold: pydantic refuses {_shown(resolved_fields)} with {error['type']}, not {code}"
        params = _plain_params(error)
        assert (params is not None) == carries_params, f"scaffold: pydantic's context for {_shown(resolved_fields)} is {error.get('ctx')!r}: the case expects {'plain params' if carries_params else 'no params'}"
        ids, promotes = await _two_promotes_resolving(world, resolved_fields=resolved_fields)
        before = await _four_rows(world, ids)
        story = f"a promote resolving {_shown(resolved_fields)}"

        response = await _run_never_raising(world, story, promotes=promotes, endpoint=endpoint)

        refusal, read_ids = await _read_as_the_list_does(world, ids[2:])
        assert refusal is None, f"H-41, /{endpoint}: after {story} (committed={response.committed}), the pair no longer reads as GET /transactions builds it, in the batch's session: {refusal}"
        assert read_ids == ids[2:], f"scaffold: the list's read answered the rows {read_ids}, not the pair {ids[2:]}: its reading proves nothing"
        issues = [(issue.operation, issue.index, issue.code, issue.field, issue.params) for issue in response.issues]
        expected = [("promote", 1, code, field, params)]
        assert issues == expected, f"H-41, W-B70 (D-W70-1), /{endpoint}: {story} must be refused at the batch's parse with exactly {expected}; committed={response.committed}, issues: {_render(response.issues)}"
        assert response.committed is False, f"H-41: /{endpoint} refused the batch, yet answered committed"
        after = await _four_rows(world, ids)
        assert after == before, f"H-41: the batch was refused, yet the stored rows changed: before {before}, after {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    async def test_a_tags_text_is_stored_as_its_csv_on_both_rows(self, world, endpoint):
        """Red today on ``/commit``: ``tags_to_csv`` joins the characters of a text, so «a, b» is stored «a,,, ,b» (the
        list's read splits it back to ["a", "b"], which hides it). Contract: a text goes through ``validate_tags_list`` as
        on a create, and both rows store «a,b»; ``/validate`` accepts it and writes nothing."""
        ids, promotes = await _two_promotes_resolving(world, resolved_fields={"tags": "a, b"})

        await _assert_accepted(world, ids, promotes, endpoint, "a promote resolving the tags «a, b»", merged={"tags": "a,b"})

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize(("resolved_fields", "merged", "receiving_cost"), RESOLVED_FIELDS_KEPT)
    async def test_guard_resolved_fields_the_model_keeps_are_applied(self, world, resolved_fields, merged, receiving_cost, endpoint):
        """Guard: green today and after. Accepted; ``/commit`` stores the merged fields on both rows of the second pair, a
        cost basis on its receiving leg only (decision 47); a key left out leaves the rows alone, an explicit null clears
        it; ``{}`` changes nothing."""
        ids, promotes = await _two_promotes_resolving(world, resolved_fields=resolved_fields)

        await _assert_accepted(world, ids, promotes, endpoint, f"a promote resolving {_shown(resolved_fields)}", merged=merged, receiving_cost=receiving_cost)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    async def test_guard_an_explicit_null_clears_the_tags_of_both_rows(self, world, endpoint):
        """Guard: green today and after. The second pair stored with the tags «old,tags»; ``{"tags": null}`` clears them on
        both rows."""
        ids, promotes = await _two_promotes_resolving(world, resolved_fields={"tags": None})
        await _tag(world, ids[2:], "old,tags")

        await _assert_accepted(world, ids, promotes, endpoint, "a promote resolving an explicit null tags", merged={"tags": None})

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    async def test_guard_an_explicit_null_clears_the_cost_basis_which_the_transfer_then_requires(self, world, endpoint):
        """Guard: green today and after. ``{"cost_basis_override": null}`` clears the receiving leg's cost basis, and the
        TRANSFER the promote makes requires one there: ``costBasisRequired`` on promote 1, ``ref_id`` that leg, nothing
        else; not committed; the four rows as they were stored. A null read as «left out» would keep the 100 EUR and
        commit."""
        ids, promotes = await _two_promotes_resolving(world, resolved_fields={"cost_basis_override": None})
        before = await _four_rows(world, ids)

        response = await _run_never_raising(world, "a promote resolving an explicit null cost basis", promotes=promotes, endpoint=endpoint)

        issues = [(issue.operation, issue.index, issue.ref_id, issue.code, issue.field, issue.params) for issue in response.issues]
        expected = [("promote", 1, ids[3], TXValidationCode.COST_BASIS_REQUIRED.value, "cost_basis_override", {"type": "TRANSFER"})]
        assert issues == expected, f"H-41, /{endpoint}: an explicit null cost basis clears the receiving leg's, which the TRANSFER requires: expected {expected}; committed={response.committed}, issues: {_render(response.issues)}"
        assert response.committed is False, f"H-41: /{endpoint} refused the batch, yet answered committed"
        after = await _four_rows(world, ids)
        assert after == before, f"H-41: the batch was refused, yet the stored rows changed: before {before}, after {after}"


# ============================================================================
# RED AND GUARDS — RULE 11 (N78, W-B72): A PROMOTED COST BASIS WHERE NO LEG TAKES ONE
# ============================================================================

# N78's code, as a literal: no rule answers it before its cure.
COST_BASIS_NOT_ALLOWED = "costBasisNotAllowed"
# The pair types a WITHDRAWAL and a DEPOSIT are promoted into (promote_from): on neither leg, both at quantity 0, does
# TX_TYPE_METADATA let a cost basis in.
CASH_PAIR_TARGETS = (TransactionType.CASH_TRANSFER, TransactionType.FX_CONVERSION)
# The cost basis a promote resolves: the PromoteMergeModal's merged value.
RESOLVED_COST = {"code": EUR, "amount": "12.5"}


async def _cash_pair(world: World, target: TransactionType) -> tuple[int, int]:
    """A stored pair a promote turns into ``target`` (``promote_from``), neither row with a cost basis: a WITHDRAWAL of 100
    EUR on ``main``, and a DEPOSIT of 100 EUR on ``other`` (CASH_TRANSFER: same currency, other broker, opposite amounts) or
    of 110 USD on ``main`` (FX_CONVERSION: other currency, same broker). Their ids (withdrawal, deposit)."""
    withdrawal_id = await _seed_cash(world, TransactionType.WITHDRAWAL, "-100", EUR, day=SEED_DAY)
    if target == TransactionType.CASH_TRANSFER:
        deposit_id = await _insert(world, broker_id=world.other_id, asset_id=None, type=TransactionType.DEPOSIT, date=SEED_DAY, quantity=Decimal("0"), amount=Decimal("100"), currency=EUR)
    elif target == TransactionType.FX_CONVERSION:
        deposit_id = await _seed_cash(world, TransactionType.DEPOSIT, "110", USD, day=SEED_DAY)
    else:
        raise ValueError(f"no cash pair is promoted into {target.value}")
    return withdrawal_id, deposit_id


async def _quantities(world: World, ids) -> list[Decimal]:
    """The quantity of each row ``ids`` as the database holds it, in id order."""
    statement = select(Transaction.quantity).where(Transaction.id.in_(list(ids))).order_by(Transaction.id)
    return list((await world.session.execute(statement)).scalars())


def _type_and_qty(params: dict | None) -> tuple | dict | None:
    """N78's params ``{type, qty}`` as ``(type, quantity)``, the quantity read as a number: a stored row's quantity may print
    0 or 0.000000. Anything else as it is, for the message."""
    if isinstance(params, dict) and set(params) == {"type", "qty"}:
        try:
            return params["type"], Decimal(str(params["qty"]))
        except InvalidOperation:
            return params
    return params


class TestN78APromotedCostBasisWhereNoLegTakesOne:
    """Rule 11 (N78, W-B72): a promote's resolved non-null cost basis where neither leg can take one under the target type
    is refused on the promote, and the promote is not applied.

    Today ``_apply_promote_cost_basis`` (``batch_creates.py``) puts a resolved cost basis on the leg of positive quantity,
    or on BOTH legs when neither has one: a cash pair's, whose new type takes none on either side. Decision 47's rule for
    an asset pair, the receiving leg only, stays; an explicit null is never refused.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("target", CASH_PAIR_TARGETS, ids=lambda target: target.value)
    async def test_promote_of_a_cash_pair_resolving_a_cost_basis_is_refused(self, world, target):
        """RED until N78. Two promotes — an asset pair into a TRANSFER (index 0, valid) and a WITHDRAWAL/DEPOSIT pair into
        ``target`` resolving 12.5 EUR (index 1) — get exactly one ``costBasisNotAllowed`` on promote 1, ``field``
        ``cost_basis_override``, ``params`` ``{type: <target>, qty}`` (``qty`` a leg's, 0 for both, compared as a number);
        nothing else; promote 1 has no result (not applied); not committed; the four rows as they were stored. Today the
        batch commits, both cash legs holding 12.5 EUR."""
        await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        asset_pair = await _promotable_pair(world)
        cash_pair = await _cash_pair(world, target)
        quantities = await _quantities(world, cash_pair)
        assert [cost_basis_allowed(target, quantity) for quantity in quantities] == [False, False], f"precondition broken: neither leg of the cash pair may take a cost basis as a {target.value}; their quantities read {quantities}"
        ids = [*asset_pair, *cash_pair]
        before = await _pair_state(world, ids)
        promotes = [{"id_a": asset_pair[0], "id_b": asset_pair[1]}, {"id_a": cash_pair[0], "id_b": cash_pair[1], "resolved_fields": {"cost_basis_override": RESOLVED_COST}}]

        response = await _run_never_raising(world, f"a promote of a cash pair into a {target.value} resolving a cost basis", promotes=promotes)

        refusal = f"{COST_BASIS_NOT_ALLOWED} {{type: {target.value}, qty: 0}} on promote 1, field cost_basis_override"
        found = [issue for issue in response.issues if issue.code == COST_BASIS_NOT_ALLOWED]
        if not any((issue.operation, issue.index) == ("promote", 1) for issue in found):
            today = await _pair_state(world, cash_pair)
            pytest.fail(
                f"N78 (W-B72): a promote of a WITHDRAWAL/DEPOSIT pair into a {target.value}, whose legs take no cost basis, resolving {RESOLVED_COST['amount']} {RESOLVED_COST['code']} must be refused with {refusal}; "
                f"today committed={response.committed}, issues [{_render(response.issues)}], and the cash pair reads {today} (type, related id, cost basis, currency)"
            )
        assert [(issue.operation, issue.index, issue.field, _type_and_qty(issue.params)) for issue in found] == [("promote", 1, "cost_basis_override", (target.value, Decimal("0")))], f"N78: expected exactly one {refusal}: {_render(found)}"
        assert [issue for issue in response.issues if issue.code != COST_BASIS_NOT_ALLOWED] == [], f"N78: only the cost basis may refuse this batch: {_render(response.issues)}"
        assert ("promote", 1) not in _in_batch(response), f"N78: the refused promote is not applied, so it has no result: {response.results}"
        assert response.committed is False, "N78: the batch was refused, yet answered committed"
        after = await _pair_state(world, ids)
        assert after == before, f"N78: the batch was refused, yet the stored rows changed: before {before}, after {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("giving_first", [pytest.param(True, id="giving-leg-as-id-a"), pytest.param(False, id="receiving-leg-as-id-a")])
    async def test_guard_a_promote_of_an_asset_pair_puts_the_resolved_cost_basis_on_the_receiving_leg_only(self, world, giving_first):
        """Guard: green today and after N78 (decision 47). An ADJUSTMENT −1 and an ADJUSTMENT +1 promoted into a TRANSFER, in
        either order, resolving 12.5 EUR: the receiving leg takes a cost basis, so the promote commits; the receiving leg
        holds 12.5 EUR, the giving leg none."""
        await _seed_position(world, TransactionType.BUY, "1", amount="-100")
        giving_id, receiving_id = await _promotable_pair(world)
        first, second = (giving_id, receiving_id) if giving_first else (receiving_id, giving_id)
        promotes = [{"id_a": first, "id_b": second, "resolved_fields": {"cost_basis_override": RESOLVED_COST}}]

        response = await _run_never_raising(world, "a promote of an asset pair resolving a cost basis", promotes=promotes)

        assert response.committed is True and response.issues == [], f"N78: a TRANSFER's receiving leg takes a cost basis, so the promote must commit; it was refused: {_render(response.issues)}"
        state = await _pair_state(world, [giving_id, receiving_id])
        expected = {giving_id: (TransactionType.TRANSFER, receiving_id, None, None), receiving_id: (TransactionType.TRANSFER, giving_id, Decimal(RESOLVED_COST["amount"]), EUR)}
        assert state == expected, f"Decision 47: the resolved cost basis goes on the receiving leg only; the promoted pair reads {state}, expected {expected}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("target", CASH_PAIR_TARGETS, ids=lambda target: target.value)
    async def test_guard_a_promote_of_a_cash_pair_resolving_an_explicit_null_commits(self, world, target):
        """Guard: green today and after N78. A WITHDRAWAL/DEPOSIT pair promoted into ``target`` resolving
        ``{"cost_basis_override": null}`` — clearing — commits: both rows ``target``, linked both ways, without a cost basis."""
        withdrawal_id, deposit_id = await _cash_pair(world, target)
        promotes = [{"id_a": withdrawal_id, "id_b": deposit_id, "resolved_fields": {"cost_basis_override": None}}]

        response = await _run_never_raising(world, f"a promote of a cash pair into a {target.value} resolving a null cost basis", promotes=promotes)

        assert response.committed is True and response.issues == [], f"N78: an explicit null cost basis is never refused, yet the promote into a {target.value} was: {_render(response.issues)}"
        state = await _pair_state(world, [withdrawal_id, deposit_id])
        expected = {withdrawal_id: (target, deposit_id, None, None), deposit_id: (target, withdrawal_id, None, None)}
        assert state == expected, f"The promoted cash pair reads {state}, expected {expected}"


# ============================================================================
# RED AND GUARDS — BALANCES SUMMED EXACTLY
# ============================================================================

TEN_DECIMALS_BUY = "99999.1234567891"
EXACT_HOLDING = Decimal("199998.2469135782")
HOLDING_READS = ("get_asset_holdings", "get_asset_holdings-as-of", "get_balances_at_end_of")


async def _read_quantities(service: TransactionService, broker_id: int, read: str) -> dict[int, Decimal]:
    """The quantity per asset of ``broker_id`` that ``read`` answers: over every row, or over the rows up to ``DAY``.
    ``get_asset_holdings`` feeds the broker summary, ``get_balances_at_end_of`` the BRIM gap-fix."""
    if read == "get_asset_holdings":
        return await service.get_asset_holdings(broker_id)
    if read == "get_asset_holdings-as-of":
        return await service.get_asset_holdings(broker_id, as_of=DAY)
    if read == "get_balances_at_end_of":
        return (await service.get_balances_at_end_of(broker_id, DAY))[1]
    raise ValueError(f"unknown read {read!r}")


class TestBalancesAreSummedExactly:
    """Rule 3: the balances are summed in Python with exact ``Decimal``, not by SQL over the stored doubles."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("read", HOLDING_READS)
    async def test_two_buys_of_ten_decimals_sum_exactly(self, world, read):
        """RED: two BUYs of 99999.1234567891 (15 significant digits, 10 decimals: within both limits) hold exactly
        199998.2469135782. Today the SQL sum, read through ``Numeric(18, 6)``, answers 199998.246914; with the new column
        and an SQL sum it would answer 199998.2469135780, the sum's double cut to 15 significant digits."""
        for _ in range(2):
            await _seed_position(world, TransactionType.BUY, TEN_DECIMALS_BUY, day=DAY, amount="-1000")

        held = (await _read_quantities(TransactionService(world.session), world.main_id, read)).get(world.asset_id)

        assert held == EXACT_HOLDING, f"C-97a rule 3: {read} on two BUYs of {TEN_DECIMALS_BUY} must answer their exact sum {EXACT_HOLDING}; it answers {held}"

    @pytest.mark.asyncio
    async def test_cash_balances_at_the_end_of_a_day_keep_todays_results(self, world):
        """Guard: the cash ``get_balances_at_end_of`` answers is today's — deposits of 0.1 and 0.2 EUR (a sum the doubles
        miss at the 17th digit), a deposit an exclusion leaves out, a currency whose movements cancel out (kept, at 0),
        a deposit the day after (not counted)."""
        await _seed_cash(world, TransactionType.DEPOSIT, "0.1", EUR, day=SEED_DAY)
        await _seed_cash(world, TransactionType.DEPOSIT, "0.2", EUR, day=SEED_DAY)
        excluded_id = await _seed_cash(world, TransactionType.DEPOSIT, "1000", EUR, day=DAY)
        await _seed_cash(world, TransactionType.DEPOSIT, "5", USD, day=DAY)
        await _seed_cash(world, TransactionType.WITHDRAWAL, "-5", USD, day=DAY)
        await _seed_cash(world, TransactionType.DEPOSIT, "7", EUR, day=NEXT_DAY)
        await _seed_position(world, TransactionType.BUY, "1", day=DAY, amount="-40.25")
        service = TransactionService(world.session)

        cash = (await service.get_balances_at_end_of(world.main_id, DAY))[0]
        cash_without = (await service.get_balances_at_end_of(world.main_id, DAY, exclude_tx_ids=[excluded_id]))[0]

        assert cash == {EUR: Decimal("960.05"), USD: Decimal("0")}, f"The cash of broker {world.main_id} at the end of {DAY}: expected 960.05 EUR and 0 USD, as today; got {cash}"
        assert cash_without == {EUR: Decimal("-39.95"), USD: Decimal("0")}, f"The same, without the deposit id={excluded_id}: expected -39.95 EUR and 0 USD, as today; got {cash_without}"

    @pytest.mark.asyncio
    async def test_quantities_keep_their_date_bounds_and_exclusions(self, world):
        """Guard: the quantities keep today's bounds — the day ``as_of`` included, the day after left out, the rows
        ``exclude_tx_ids`` names left out — in both reads; whole quantities, which the doubles sum exactly."""
        await _seed_position(world, TransactionType.BUY, "3", day=SEED_DAY, amount="-30")
        excluded_id = await _seed_position(world, TransactionType.BUY, "4", day=DAY, amount="-40")
        await _seed_position(world, TransactionType.SELL, "-2", day=DAY, amount="25")
        await _seed_position(world, TransactionType.BUY, "100", day=NEXT_DAY, amount="-1000")
        service = TransactionService(world.session)

        reads = {
            "get_balances_at_end_of(DAY)": (await service.get_balances_at_end_of(world.main_id, DAY))[1],
            "get_balances_at_end_of(DAY) without the BUY of 4": (await service.get_balances_at_end_of(world.main_id, DAY, exclude_tx_ids=[excluded_id]))[1],
            "get_asset_holdings(as_of=DAY)": await service.get_asset_holdings(world.main_id, as_of=DAY),
            "get_asset_holdings()": await service.get_asset_holdings(world.main_id),
        }

        expected = {
            "get_balances_at_end_of(DAY)": {world.asset_id: Decimal("5")},
            "get_balances_at_end_of(DAY) without the BUY of 4": {world.asset_id: Decimal("1")},
            "get_asset_holdings(as_of=DAY)": {world.asset_id: Decimal("5")},
            "get_asset_holdings()": {world.asset_id: Decimal("105")},
        }
        assert reads == expected, f"The quantities of broker {world.main_id} must keep today's date bounds and exclusions: expected {expected}, got {reads}"


# ============================================================================
# GUARD — THE ASSET LIST READS HOLDINGS EXACTLY
# ============================================================================


class TestTheAssetListReadsHoldingsExactly:
    """Guard, green today and after C-97a (rule 4): an asset is held where the sum of its quantities on a broker exceeds
    ``QUANTITY_DUST_THRESHOLD`` (``AssetCRUDService.list_assets``, today an SQL ``HAVING`` over the doubles)."""

    @pytest.mark.asyncio
    async def test_bought_point_one_and_point_two_then_sold_point_three_is_not_held(self, world):
        """Guard: the test's asset, bought 0.1 + 0.2 and sold 0.3, is held by nobody — its doubles sum to about 5.6e-17,
        its exact sum to 0. The control asset, sold 0.2999, keeps 0.0001, above the threshold: held, which proves the
        list reads the holdings at all. No user is passed, so a holding reads as held by others."""
        control_id = await _new_asset(world, "control coin")
        sold = {world.asset_id: "-0.3", control_id: "-0.2999"}
        for asset_id, sold_quantity in sold.items():
            await _seed_position(world, TransactionType.BUY, "0.1", amount="-10", asset_id=asset_id)
            await _seed_position(world, TransactionType.BUY, "0.2", amount="-20", asset_id=asset_id)
            await _seed_position(world, TransactionType.SELL, sold_quantity, day=DAY, amount="30", asset_id=asset_id)
        control_residual = Decimal("0.1") + Decimal("0.2") + Decimal(sold[control_id])
        assert control_residual > QUANTITY_DUST_THRESHOLD, f"scaffold: the control keeps {control_residual}, not above the threshold {QUANTITY_DUST_THRESHOLD}"

        listed = await AssetCRUDService.list_assets(FAAinfoFiltersRequest(search=world.marker), world.session)

        flags = {asset.id: (asset.held_by_me, asset.held_by_others) for asset in listed}
        assert {world.asset_id, control_id} <= set(flags), f"scaffold: the list searched by the test's marker lacks its assets {world.asset_id} and {control_id}: {sorted(flags)}"
        assert flags[control_id] == (False, True), f"Presence control: the control asset id={control_id} keeps {control_residual}, so it is held (by others, no user being passed); (held_by_me, held_by_others) = {flags[control_id]}"
        assert flags[world.asset_id] == (False, False), f"C-97a rule 4: asset id={world.asset_id} was bought 0.1 + 0.2 and sold 0.3, so it is held by nobody; (held_by_me, held_by_others) = {flags[world.asset_id]}"


# ============================================================================
# RED — RULE 7 (R13-SEC2): CORRUPT ROWS ARE READ WITHOUT RAISING
# ============================================================================


async def _raw(world: World, table: str, column: str, row_id: int) -> tuple[str, object]:
    """SQLite's storage class and the raw value of ``column`` of row ``row_id`` in ``table``, read past every column type."""
    row = (await world.session.execute(text(f"SELECT typeof({column}), {column} FROM {table} WHERE id = :id"), {"id": row_id})).one()
    return row[0], row[1]


async def _corrupt(world: World, row, table: str, column: str, literal: str) -> int:
    """Write ``row`` with the ORM, drop it from the session, and overwrite its ``column`` with the SQLite literal ``literal``
    by raw SQL — as an older version (nothing refused ``Decimal('1E+400')``) or another tool leaves it — so the next load
    reads the file. Its id, once the file is shown to hold that REAL."""
    world.session.add(row)
    await world.session.flush()
    row_id = row.id
    world.session.expunge(row)
    await world.session.execute(text(f"UPDATE {table} SET {column} = {literal} WHERE id = :id"), {"id": row_id})
    held = await _raw(world, table, column, row_id)
    assert held == ("real", float(literal)), f"scaffold: {table}.{column} of row {row_id} holds {held}, not the REAL {literal}"
    return row_id


async def _corrupt_quantity(world: World, broker_id: int, asset_id: int, literal: str) -> int:
    """A BUY of ``asset_id`` on ``broker_id`` whose quantity the file holds as the REAL ``literal``; its id."""
    now = utcnow()
    row = Transaction(broker_id=broker_id, asset_id=asset_id, type=TransactionType.BUY, date=SEED_DAY, quantity=Decimal("1"), amount=Decimal("-1"), currency=EUR, description=f"{world.marker} corrupt", created_at=now, updated_at=now)
    return await _corrupt(world, row, "transactions", "quantity", literal)


async def _corrupt_close(world: World, literal: str) -> int:
    """A price of the test's asset whose close the file holds as the REAL ``literal``; its id."""
    row = PriceHistory(asset_id=world.asset_id, date=SEED_DAY, close=Decimal("1"), currency=EUR, source_plugin_key="MANUAL", fetched_at=utcnow())
    return await _corrupt(world, row, "price_history", "close", literal)


class TestCorruptRowsAreReadWithoutRaising:
    """Rule 7 (R13-SEC2, E's attack): rows whose REAL today's read cannot turn into a Decimal — a quantity of 1e60
    (``InvalidOperation``: padded to 6 decimals in 60 digits), an infinite quantity or close (``TypeError``: the exponent
    ``'F'`` compared with an int). The asset list reads every user's quantities, so one such row answers 500 to every
    user, and the row cannot be deleted through the app, since deleting it loads it.
    """

    @pytest.mark.asyncio
    async def test_the_asset_list_reads_a_quantity_of_1e60_and_an_infinite_one_without_raising(self, world):
        """Red today: ``list_assets`` raises — ``InvalidOperation`` on the REAL 1e60, ``TypeError`` on the inf.

        Contract: no exception; the test's two assets are listed, and the one holding 1e60 on ``main`` reads as held (by
        others, no user being passed): its quantity reads 1E+60. The infinite one, read as None, is not asserted.
        """
        infinite_asset_id = await _new_asset(world, "infinite coin")
        await _corrupt_quantity(world, world.main_id, world.asset_id, HUGE_REAL)
        await _corrupt_quantity(world, world.other_id, infinite_asset_id, INFINITE_REAL)

        try:
            listed = await AssetCRUDService.list_assets(FAAinfoFiltersRequest(search=world.marker), world.session)
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"R13-SEC2: list_assets raised {exc!r} on a quantity the file holds as the REAL {HUGE_REAL} or {INFINITE_REAL}: GET /assets answers 500 to every user")

        flags = {asset.id: (asset.held_by_me, asset.held_by_others) for asset in listed}
        assert {world.asset_id, infinite_asset_id} <= set(flags), f"R13-SEC2: the list searched by the test's marker lacks its assets {world.asset_id} and {infinite_asset_id}: {sorted(flags)}"
        assert flags[world.asset_id] == (False, True), f"R13-SEC2: asset id={world.asset_id} holds a quantity of 1e60 on broker {world.main_id}, which reads 1E+60: held by others (no user being passed); (held_by_me, held_by_others) = {flags[world.asset_id]}"

    @pytest.mark.asyncio
    async def test_a_quantity_of_1e60_loads_as_1e60_and_an_infinite_one_as_none(self, world):
        """Red today: loading either row raises — ``InvalidOperation`` on 1e60, ``TypeError`` on the inf.

        Contract: through ``TransactionService.get_by_ids`` (what the batch loads), the 1e60 row's quantity reads
        ``1E+60`` and the infinite one's None.
        """
        huge_id = await _corrupt_quantity(world, world.main_id, world.asset_id, HUGE_REAL)
        infinite_id = await _corrupt_quantity(world, world.other_id, world.asset_id, INFINITE_REAL)

        try:
            loaded = {row.id: row.quantity for row in await TransactionService(world.session).get_by_ids([huge_id, infinite_id])}
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"R13-SEC2: loading the transactions id={huge_id} (quantity REAL {HUGE_REAL}) and id={infinite_id} (REAL {INFINITE_REAL}) raised {exc!r}")

        assert loaded == {huge_id: Decimal("1E+60"), infinite_id: None}, f"R13-SEC2: the quantities load as {loaded}: expected 1E+60 for id={huge_id} and None for id={infinite_id}"

    @pytest.mark.asyncio
    async def test_a_transaction_of_infinite_quantity_can_be_deleted_through_the_batch(self, world):
        """Red today: the delete loads the row first (``preload_and_authorize`` → ``get_by_ids``), and the load raises
        ``TypeError``: the row cannot leave the database through the app.

        Contract: ``/commit`` with the row's id in ``deletes`` commits with no issue, reports the delete, and the row is
        gone.
        """
        infinite_id = await _corrupt_quantity(world, world.other_id, world.asset_id, INFINITE_REAL)

        response = await _run_never_raising(world, f"the delete of transaction id={infinite_id}, whose quantity the file holds as the REAL {INFINITE_REAL}", deletes=[infinite_id])

        assert response.committed is True and response.issues == [], f"R13-SEC2: the delete of id={infinite_id} must commit; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
        assert ("delete", 0) in _in_batch(response), f"R13-SEC2: the delete of id={infinite_id} is not reported: {response.results}"
        remaining = list((await world.session.execute(select(Transaction.id).where(Transaction.id == infinite_id))).scalars())
        assert remaining == [], f"R13-SEC2: the delete of id={infinite_id} was committed, yet the row is still there"

    @pytest.mark.asyncio
    async def test_a_price_whose_close_is_infinite_loads_without_one(self, world):
        """Red today: loading the row raises ``TypeError``.

        Contract: the price row loads, its close None.
        """
        price_id = await _corrupt_close(world, INFINITE_REAL)

        try:
            row = (await world.session.execute(select(PriceHistory).where(PriceHistory.id == price_id))).scalar_one()
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"R13-SEC2: loading the price id={price_id}, whose close the file holds as the REAL {INFINITE_REAL}, raised {exc!r}")

        assert row.close is None, f"R13-SEC2: the price id={price_id} loads a close of {row.close!r}: expected None"


# ============================================================================
# RED AND GUARD — RULE 8 (W-B60): A CASH AMOUNT READS BACK EXACTLY
# ============================================================================

# A cash amount of 15 significant digits, 12 of them before the point (within N63's 15): a double holds it exactly
# enough, and ``'%.6f'`` of that double reads -123456789012.345001.
TWELVE_INTEGER_DIGIT_AMOUNT = "-123456789012.345"


async def _loaded_amount(world: World, tx_id: int) -> object:
    """The amount of row ``tx_id`` as the service loads it (``get_by_ids``), from the database. The object the batch left
    in the session holds the value the batch assigned, not the one read back: it is expired first, so the load fills it
    from the file, through the column's type."""
    cached = await world.session.get(Transaction, tx_id)
    if cached is not None:
        world.session.expire(cached)
    loaded = await TransactionService(world.session).get_by_ids([tx_id])
    assert [row.id for row in loaded] == [tx_id], f"scaffold: get_by_ids([{tx_id}]) loaded {[row.id for row in loaded]}"
    return loaded[0].amount


async def _committed_buy(world: World, cash: str) -> int:
    """A BUY of one unit of the test's asset on ``main`` for ``cash`` EUR, committed through ``/commit``; its id."""
    response = await _run_as_the_endpoint(world, creates=[_row(world, "BUY", "1", cash=cash)])
    assert response.committed is True and response.issues == [], f"scaffold: a BUY of 1 unit for {cash} EUR, within every limit, was refused: {_render(response.issues)}"
    return _created_ids(response)[0]


class TestACashAmountReadsBackExactly:
    """Rule 8 (W-B60): ``Transaction.amount`` reads back the decimal written, with 6 decimals as today.

    Today it is a plain ``Numeric(18, 6)``: SQLAlchemy reads the stored double through ``'%.6f'``, and from about 11
    integer digits the double's noise lands in the 6 decimals. Compared as text, so the 6 decimals are pinned.
    """

    @pytest.mark.asyncio
    async def test_a_cash_amount_of_15_significant_digits_reads_back_exactly(self, world):
        """Red today: the BUY commits, and its cash amount of -123456789012.345 EUR reads back -123456789012.345001, column
        by column and through the service alike.

        Contract (W-B60): -123456789012.345000 both ways: the value sent, with 6 decimals.
        """
        tx_id = await _committed_buy(world, TWELVE_INTEGER_DIGIT_AMOUNT)

        stored = (await _stored(world, [tx_id]))[tx_id]["amount"]
        loaded = await _loaded_amount(world, tx_id)

        reads = {"column by column": str(stored), "through get_by_ids": str(loaded)}
        expected = dict.fromkeys(reads, "-123456789012.345000")
        assert reads == expected, f"W-B60: the BUY id={tx_id} was committed with a cash amount of {TWELVE_INTEGER_DIGIT_AMOUNT} EUR, and reads back {reads}: expected -123456789012.345000, the value sent with 6 decimals"

    @pytest.mark.asyncio
    async def test_the_control_totals_give_the_cash_amount_exactly(self, world):
        """Red today: the control totals read the amount through the column's type, so the broker's EUR line is the
        double's noise, -123456789012.345001 — what a backup would record, and a restore compare.

        Contract (W-B60): the line of the test's broker ``main`` — the only cash it holds is the BUY's — is
        -123456789012.345, in the canonical text of ``ControlTotals.to_json``. Only this broker's lines are read: the
        ledger is the whole lane's.
        """
        await _committed_buy(world, TWELVE_INTEGER_DIGIT_AMOUNT)

        totals = (await compute_control_totals(world.session)).to_json()

        lines = [line for line in totals["cash"] if line["broker_id"] == world.main_id]
        expected = [{"broker_id": world.main_id, "currency": EUR, "balance": "-123456789012.345"}]
        assert lines == expected, f"W-B60: the control totals of broker {world.main_id}, whose only cash is a BUY for {TWELVE_INTEGER_DIGIT_AMOUNT} EUR, give the cash lines {lines}: expected {expected}"

    @pytest.mark.asyncio
    async def test_guard_a_cash_amount_that_reads_well_today_keeps_its_form(self, world):
        """Guard: green today and after. Cash amounts of -100 and -1234.5 EUR read back -100.000000 and -1234.500000,
        column by column and through the service, as ``Numeric(18, 6)`` reads them today."""
        ids = {cash: await _committed_buy(world, cash) for cash in ("-100", "-1234.5")}

        stored = await _stored(world, ids.values())
        reads = {cash: (str(stored[tx_id]["amount"]), str(await _loaded_amount(world, tx_id))) for cash, tx_id in ids.items()}

        expected = {"-100": ("-100.000000",) * 2, "-1234.5": ("-1234.500000",) * 2}
        assert reads == expected, f"W-B60: cash amounts sent → (column by column, through get_by_ids): {reads}; expected {expected}, today's form"


# ============================================================================
# GUARD — D2: BRIM PARSE DOES NOT REFUSE
# ============================================================================


class _ParseOnlyProvider(BRIMProvider):
    """A BRIM plugin reduced to the parent's row constructor, ``_create_transaction``: what every plugin calls."""

    @property
    def provider_code(self) -> str:
        return "c97a_parse_only"

    @property
    def provider_name(self) -> str:
        return "C-97a parse-only"

    @property
    def description(self) -> str:
        return "Builds rows through BRIMProvider._create_transaction for the C-97a tests"

    def can_parse(self, file_path) -> bool:
        return False

    def parse(self, file_path, broker_id) -> BRIMParseOutput:
        return BRIMParseOutput()


# A row a broker's file can carry, over a limit of the batch, as a plugin hands it to _create_transaction.
BRIM_ROWS = [
    pytest.param({"type": "BUY", "quantity": Decimal("0.123456789012"), "cash": Currency(code=EUR, amount=Decimal("-100"))}, id="quantity-12-decimals"),
    pytest.param({"type": "BUY", "quantity": Decimal("1234567890123.456"), "cash": Currency(code=EUR, amount=Decimal("-100"))}, id="quantity-16-significant-digits"),
    pytest.param({"type": "BUY", "quantity": Decimal("1"), "cash": Currency(code=EUR, amount=Decimal("-100.1234567"))}, id="cash-amount-7-decimals"),
    pytest.param({"type": "ADJUSTMENT", "quantity": Decimal("1"), "cost_basis_override": Currency(code=EUR, amount=Decimal(COST_13_DECIMALS))}, id="cost-basis-13-decimals"),
]


class TestBrimParseDoesNotRefuse:
    """Guard (decision D2), green today and after C-97a: the limit is the batch's, at confirmation. A BRIM row over it is
    parsed — the import shows it, and its confirmation refuses it — so ``TXCreateItem`` must not refuse it, nor round it.
    """

    @pytest.mark.parametrize("fields", BRIM_ROWS)
    def test_brim_row_over_the_limit_is_parsed_as_it_reads(self, fields):
        """Guard: the item is returned and listed, its values as the file reads them, and no parse issue is recorded."""
        transactions: list = []
        issues: list = []

        item = _ParseOnlyProvider()._create_transaction(row_num=7, transactions=transactions, validation_issues=issues, context="C-97a", broker_id=1, asset_id=100, date=DAY, **fields)

        assert issues == [], f"D2: the decimal limit is checked at confirmation, not at BRIM parse; the row {fields} got parse issues {issues}"
        assert item is not None and transactions == [item], f"D2: the row {fields} must be parsed into an item and listed; got {item!r}, listed {transactions}"
        read = {name: getattr(item, name) for name in fields}
        assert read == fields, f"D2: the parse keeps the values as the file reads them, neither refused nor rounded: sent {fields}, parsed {read}"


# ============================================================================
# RED AND GUARDS — RULE 9 (R13-SEC7-3, NIGHT DECISION N74): THE DATE AT WRITE
# ============================================================================

# Compared as a string: TXValidationCode has no member for it yet, and a red must fail when it runs, not when it is
# collected.
DATE_OUT_OF_RANGE = "dateOutOfRange"
DATE_MIN = date(1900, 1, 1)

# The dates a row may not carry: the day before 1900-01-01, the first day of the calendar (today's replay then walks every
# day since year one), the day after tomorrow (the server's, resolved when the test runs: lot N74's last day is tomorrow),
# the last day of the calendar (today's replay overflows, adding a day to it).
DATES_OUT_OF_RANGE = [
    pytest.param("1899-12-31", id="1899-12-31"),
    pytest.param("0001-01-01", id="0001-01-01"),
    pytest.param("max+1", id="day-after-tomorrow"),
    pytest.param("9999-12-31", id="9999-12-31"),
]
# The dates a create keeps: both ends of the range (the latest, the server's tomorrow, resolved when the test runs), and an
# ordinary day.
DATES_WITHIN_RANGE = [
    pytest.param("1900-01-01", id="1900-01-01-the-first-day"),
    pytest.param("max", id="tomorrow-the-last-day"),
    pytest.param(DAY.isoformat(), id="an-ordinary-day"),
]


def _server_today() -> date:
    """The server's local date, read here on its own — ``date.today()`` — never through ``latest_range_end()``, the helper
    the bound under test is built on (lot N74)."""
    return date.today()


def _tomorrow(day: date) -> date:
    """The last day a transaction may carry while the server's date is ``day`` (lot N74): the day after it."""
    return day + timedelta(days=1)


def _resolve_day(day: str) -> str:
    """The ISO date a parameter names: ``max`` is the server's tomorrow, ``max+1`` the day after, any other an ISO date."""
    latest = _tomorrow(_server_today())
    return {"max": latest.isoformat(), "max+1": (latest + timedelta(days=1)).isoformat()}.get(day, day)


def _dated_deposit(world: World, broker_id: int, day: str) -> dict:
    """A DEPOSIT of 10 EUR on ``broker_id`` dated ``day``, as the app sends it, with the test's batch description."""
    return {"broker_id": broker_id, "type": "DEPOSIT", "date": day, "cash": {"code": EUR, "amount": "10"}, "description": world.batch_description}


async def _run_dated(world: World, story: str, **batch) -> TXBatchResponse:
    """``_run_as_the_endpoint(world, **batch)``; an exception fails the test and names it: the endpoint would answer 500."""
    try:
        return await _run_as_the_endpoint(world, **batch)
    except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
        pytest.fail(f"R13-SEC7-3: {story}: execute_batch raised {exc!r}, so /transactions/{batch.get('endpoint', 'commit')} answers 500 instead of a refusal")


def _assert_refused_on_its_date(response: TXBatchResponse, today_before: date, row: tuple, story: str, *, with_ref_id: bool = True) -> None:
    """The batch answers exactly one issue, ``dateOutOfRange`` on ``field="date"`` of ``row`` (operation, index, ref_id),
    ``params`` ``{"min": "1900-01-01", "max": <the server's tomorrow>}`` — the server's date read before (``today_before``)
    or after the batch, so that a midnight falling during it cannot fail the test — then nothing: not committed, no result
    (the batch stopped right after the access check). ``with_ref_id=False`` leaves the ref_id out (a promote's: which row
    it names is not the subject)."""
    maxima = sorted({_tomorrow(today_before).isoformat(), _tomorrow(_server_today()).isoformat()})
    operation, index, ref_id = row
    accepted = [(operation, index, ref_id if with_ref_id else None, DATE_OUT_OF_RANGE, "date", {"min": DATE_MIN.isoformat(), "max": latest}) for latest in maxima]
    issues = [(issue.operation, issue.index, issue.ref_id if with_ref_id else None, issue.code, issue.field, issue.params) for issue in response.issues]
    assert len(issues) == 1 and issues[0] in accepted, f"R13-SEC7-3: {story} must be refused on its own row with exactly {accepted[-1]}; the batch answered committed={response.committed}, issues: {_render(response.issues)}"
    assert response.committed is False, f"R13-SEC7-3: {story}: the batch was refused, yet answered committed"
    assert response.results == [], f"R13-SEC7-3: {story}: the batch must stop right after the access check, before applying any row; it reports {[(result.operation, result.index, result.status) for result in response.results]}"


async def _dates(world: World, ids) -> dict[int, tuple]:
    """The date and description of the rows ``ids``, as the database holds them, by id."""
    statement = select(Transaction.id, Transaction.date, Transaction.description).where(Transaction.id.in_(list(ids)))
    return {row.id: (row.date, row.description) for row in await world.session.execute(statement)}


class TestTheDateIsCheckedAtWrite:
    """Rule 9 (R13-SEC7-3, N74): a row's date lies within ``1900-01-01 .. tomorrow`` — the server's tomorrow
    (``latest_range_end()``: its local date + 1 day) since lot N74, which replaced today + 1 year (UTC).

    Before R13-SEC7-3 nothing checked it: a create, an update or a promote out of range committed — unless the balance
    replay refused it for another reason, a short position or, on 9999-12-31, a codeless «Balance validation error» (it
    overflows adding a day). The subject row sits alone on ``main`` (the row before it on ``other``), so that replay of
    0001-01-01 is one day long. Today (before lot N74's cure) the refusals carry ``max`` = UTC today + 1 year, and the day
    after tomorrow commits: every refusal below is red on its ``max``, the day after tomorrow on its commit.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    @pytest.mark.parametrize("day", DATES_OUT_OF_RANGE)
    async def test_a_create_dated_out_of_range_is_refused_on_its_row(self, world, day, endpoint):
        """Red today (lot N74): the DEPOSIT dated the day after tomorrow commits; the other dates are refused with
        ``max`` = UTC today + 1 year, not the server's tomorrow.

        Contract: a valid DEPOSIT on ``other``, then the subject on ``main`` dated ``day``: exactly ``dateOutOfRange`` on
        create 1, ``field="date"``, ``{"min", "max"}`` (``max`` the server's tomorrow); not committed, no result, nothing
        written, no exception.
        """
        barrier_id = await _insert(world, broker_id=world.other_id, asset_id=None, type=TransactionType.DEPOSIT, date=SEED_DAY, quantity=Decimal("0"), amount=Decimal("100"), currency=EUR)
        today_before = _server_today()
        sent = _resolve_day(day)

        response = await _run_dated(world, f"a DEPOSIT dated {sent}", creates=[_dated_deposit(world, world.other_id, DAY.isoformat()), _dated_deposit(world, world.main_id, sent)], endpoint=endpoint)

        _assert_refused_on_its_date(response, today_before, ("create", 1, None), f"/{endpoint}: a DEPOSIT dated {sent}")
        assert barrier_id in await _stored(world, [barrier_id]), f"scaffold: the read-back no longer sees row id={barrier_id}, written before the batch, so finding no row of the batch would prove nothing"
        written = await _batch_rows(world)
        assert written == [], f"R13-SEC7-3: /{endpoint} refused the batch, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    async def test_n74_a_create_dated_the_day_after_tomorrow_is_refused_up_to_tomorrow(self, world):
        """Red today: the DEPOSIT dated the day after tomorrow commits — the last day is still UTC today + 1 year.

        Contract (lot N74): ``transaction_date_bounds()`` takes no argument and returns ``EARLIEST_RANGE_START`` ..
        ``latest_range_end()``, whose last day is the server's tomorrow, so a create dated the day after it gets exactly
        ``dateOutOfRange`` on ``field="date"`` of its row, with ``params.max`` the server's tomorrow; not committed, no
        result, nothing written.
        """
        today_before = _server_today()
        sent = (_tomorrow(today_before) + timedelta(days=1)).isoformat()
        story = f"N74: a DEPOSIT dated the day after tomorrow ({sent})"

        response = await _run_dated(world, story, creates=[_dated_deposit(world, world.main_id, sent)])

        _assert_refused_on_its_date(response, today_before, ("create", 0, None), story)
        written = await _batch_rows(world)
        assert written == [], f"{story}: the batch was refused, yet the database holds its rows {written}"

    @pytest.mark.asyncio
    async def test_an_update_moving_a_row_out_of_range_is_refused_on_its_row(self, world):
        """Red today (lot N74): the update is refused, but with ``max`` = UTC today + 1 year, not the server's tomorrow.

        Contract: behind a valid notes edit (update 0), the update of a stored DEPOSIT to 1899-12-31 (update 1) gets
        exactly ``dateOutOfRange`` on its row, ``ref_id`` its id; not committed, no result; both rows read back as stored.
        """
        neighbour_id = await _insert(world, broker_id=world.other_id, asset_id=None, type=TransactionType.DEPOSIT, date=SEED_DAY, quantity=Decimal("0"), amount=Decimal("100"), currency=EUR)
        subject_id = await _insert(world, broker_id=world.main_id, asset_id=None, type=TransactionType.DEPOSIT, date=SEED_DAY, quantity=Decimal("0"), amount=Decimal("100"), currency=EUR)
        before = await _dates(world, [neighbour_id, subject_id])
        today_before = _server_today()

        response = await _run_dated(world, f"the update of DEPOSIT id={subject_id} to 1899-12-31", updates=[{"id": neighbour_id, "description": f"{world.marker} neighbour edited"}, {"id": subject_id, "date": "1899-12-31"}])

        _assert_refused_on_its_date(response, today_before, ("update", 1, subject_id), f"the update of DEPOSIT id={subject_id} to 1899-12-31")
        after = await _dates(world, [neighbour_id, subject_id])
        assert after == before, f"R13-SEC7-3: the batch was refused, yet the stored rows changed: before {before}, after {after}"

    @pytest.mark.asyncio
    async def test_a_promote_resolving_a_date_out_of_range_is_refused_on_its_index(self, world):
        """Red today (lot N74): the promote is refused, but with ``max`` = UTC today + 1 year, not the server's tomorrow.
        (Before R13-SEC7-3 the promote applied 1899-12-31 to both legs, and the replay refused the batch for the giving
        leg's short position, ``balanceAssetNegative``, not for its date.)

        Contract: behind a valid promote (index 0), the promote resolving the date 1899-12-31 (index 1) gets exactly
        ``dateOutOfRange`` on its index; not committed, no result; all four rows as they were stored, dates included.
        """
        await _seed_position(world, TransactionType.BUY, "2", amount="-200")
        first = await _promotable_pair(world)
        second = await _promotable_pair(world)
        ids = [*first, *second]
        before = (await _pair_state(world, ids), await _dates(world, ids))
        today_before = _server_today()
        promotes = [{"id_a": first[0], "id_b": first[1]}, {"id_a": second[0], "id_b": second[1], "resolved_fields": {"date": "1899-12-31"}}]

        response = await _run_dated(world, "a promote resolving the date 1899-12-31", promotes=promotes)

        _assert_refused_on_its_date(response, today_before, ("promote", 1, None), "a promote resolving the date 1899-12-31", with_ref_id=False)
        after = (await _pair_state(world, ids), await _dates(world, ids))
        assert after == before, f"R13-SEC7-3: the batch was refused, yet the stored rows changed: before {before}, after {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("day", DATES_WITHIN_RANGE)
    async def test_guard_a_create_dated_within_the_range_commits_and_keeps_its_date(self, world, day):
        """Guard: green today and after. A DEPOSIT dated 1900-01-01, the server's tomorrow (lot N74's last day; today still
        inside UTC today + 1 year) or an ordinary day commits, and reads back its date."""
        sent = _resolve_day(day)

        response = await _run_dated(world, f"a DEPOSIT dated {sent}", creates=[_dated_deposit(world, world.main_id, sent)])

        assert response.committed is True and response.issues == [], f"R13-SEC7-3: a DEPOSIT dated {sent} is within 1900-01-01 .. tomorrow, so it must commit; it was refused: {_render(response.issues)}"
        created_id = _created_ids(response)[0]
        stored = (await _dates(world, [created_id]))[created_id][0]
        assert stored.isoformat() == sent, f"R13-SEC7-3: the DEPOSIT id={created_id} was sent dated {sent}; it reads back {stored}"

    @pytest.mark.asyncio
    async def test_guard_an_update_moving_a_row_to_1900_01_01_commits(self, world):
        """Guard: green today and after. The first day of the range is a day a row may move to."""
        subject_id = await _insert(world, broker_id=world.main_id, asset_id=None, type=TransactionType.DEPOSIT, date=SEED_DAY, quantity=Decimal("0"), amount=Decimal("100"), currency=EUR)

        response = await _run_dated(world, f"the update of DEPOSIT id={subject_id} to 1900-01-01", updates=[{"id": subject_id, "date": DATE_MIN.isoformat()}])

        assert response.committed is True and response.issues == [], f"R13-SEC7-3: 1900-01-01 is within the range, so the update must commit; it was refused: {_render(response.issues)}"
        stored = (await _dates(world, [subject_id]))[subject_id][0]
        assert stored == DATE_MIN, f"R13-SEC7-3: DEPOSIT id={subject_id} was moved to {DATE_MIN}; it reads back {stored}"


class TestTheDateFloorIsTheReplayFloor:
    """Rule 9 (N74) and MF-SEC8-2: the first day a transaction may carry is the first day every replay and history walk
    starts from, ``EARLIEST_RANGE_START`` (``utils/datetime_utils``) — the same constant, never a copy that could drift."""

    def test_the_date_floor_is_the_replay_floor_never_a_copy(self):
        """Red today: ``transaction_batch_stages`` defines its own ``TRANSACTION_DATE_MIN = date(1900, 1, 1)`` and has no
        ``EARLIEST_RANGE_START``.

        Contract: no ``TRANSACTION_DATE_MIN``; ``transaction_batch_stages.EARLIEST_RANGE_START`` is
        ``datetime_utils.EARLIEST_RANGE_START`` (the object, imported); ``transaction_date_bounds()`` starts there (lot
        N74: it takes no argument and returns ``EARLIEST_RANGE_START`` .. ``latest_range_end()``; only its first day is
        read here).
        """
        floor = datetime_utils.EARLIEST_RANGE_START
        violations: list[str] = []
        if hasattr(transaction_batch_stages, "TRANSACTION_DATE_MIN"):
            violations.append(f"transaction_batch_stages still defines its own TRANSACTION_DATE_MIN = {transaction_batch_stages.TRANSACTION_DATE_MIN}")
        imported = getattr(transaction_batch_stages, "EARLIEST_RANGE_START", None)
        if imported is None:
            violations.append("transaction_batch_stages has no EARLIEST_RANGE_START")
        elif imported is not floor:
            violations.append(f"transaction_batch_stages.EARLIEST_RANGE_START ({imported}) is not the object datetime_utils.EARLIEST_RANGE_START")
        first = transaction_batch_stages.transaction_date_bounds()[0]
        if first != floor:
            violations.append(f"transaction_date_bounds() starts on {first}, not on {floor}")

        assert violations == [], f"N74's floor is the replay floor, EARLIEST_RANGE_START (MF-SEC8-2), never a copy: {'; '.join(violations)}"


# ============================================================================
# RED — THE CODES ARE LISTED
# ============================================================================


class TestTheCodesAreListed:
    """RED: both codes are members of ``TXValidationCode`` — the frontend maps a code to ``transactions.errors.<code>`` —
    so ``GET /transactions/types`` lists them in ``validation_codes``; and so is the integer-digit code of R13-SEC2."""

    def test_validation_code_has_both_decimal_codes(self):
        """RED: today ``TXValidationCode`` has neither value."""
        values = {member.value for member in TXValidationCode}

        missing = sorted(set(DECIMAL_CODES) - values)

        assert missing == [], f"C-97a: TXValidationCode has no member of value {missing}"

    def test_transaction_types_lists_both_decimal_codes(self):
        """RED: the response ``GET /transactions/types`` builds (``get_transaction_types``) lists neither today."""
        response = TXTypesResponse(transaction_types=list(TX_TYPE_METADATA.values()), event_types=EVENT_TYPE_METADATA)

        missing = sorted(set(DECIMAL_CODES) - {info.code for info in response.validation_codes})

        assert missing == [], f"C-97a: GET /transactions/types does not list {missing} in validation_codes"

    def test_validation_code_has_the_integer_digits_code(self):
        """Red today: ``TXValidationCode`` has no ``INTEGER_DIGITS_EXCEEDED`` (rule 6, R13-SEC2): the app could not map
        the refusal to ``transactions.errors.integerDigitsExceeded``."""
        member = getattr(TXValidationCode, "INTEGER_DIGITS_EXCEEDED", None)

        assert member is not None and member.value == INTEGER_DIGITS_EXCEEDED, f"R13-SEC2: TXValidationCode.INTEGER_DIGITS_EXCEEDED is {member!r}: expected the value {INTEGER_DIGITS_EXCEEDED!r}"

    def test_transaction_types_lists_the_integer_digits_code(self):
        """Red today: ``GET /transactions/types`` does not list ``integerDigitsExceeded`` in ``validation_codes``."""
        response = TXTypesResponse(transaction_types=list(TX_TYPE_METADATA.values()), event_types=EVENT_TYPE_METADATA)

        listed = {info.code for info in response.validation_codes}

        assert INTEGER_DIGITS_EXCEEDED in listed, f"R13-SEC2: GET /transactions/types does not list {INTEGER_DIGITS_EXCEEDED!r} in validation_codes"

    def test_validation_code_has_the_date_out_of_range_code(self):
        """Red today: ``TXValidationCode`` has no ``DATE_OUT_OF_RANGE`` (rule 9, R13-SEC7-3): the app could not map the
        refusal to ``transactions.errors.dateOutOfRange``."""
        member = getattr(TXValidationCode, "DATE_OUT_OF_RANGE", None)

        assert member is not None and member.value == DATE_OUT_OF_RANGE, f"R13-SEC7-3: TXValidationCode.DATE_OUT_OF_RANGE is {member!r}: expected the value {DATE_OUT_OF_RANGE!r}"

    def test_transaction_types_lists_the_date_out_of_range_code(self):
        """Red today: ``GET /transactions/types`` does not list ``dateOutOfRange`` in ``validation_codes``."""
        response = TXTypesResponse(transaction_types=list(TX_TYPE_METADATA.values()), event_types=EVENT_TYPE_METADATA)

        listed = {info.code for info in response.validation_codes}

        assert DATE_OUT_OF_RANGE in listed, f"R13-SEC7-3: GET /transactions/types does not list {DATE_OUT_OF_RANGE!r} in validation_codes"
