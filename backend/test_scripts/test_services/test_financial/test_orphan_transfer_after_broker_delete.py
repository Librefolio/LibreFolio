"""
V-3 (D-J4), the numbers: the lots and the Dashboard of broker B once the broker that sent it a TRANSFER is
deleted — in the MIRROR, of broker A once the broker it sent to is deleted — and two Dashboard series
around an orphan cash leg (CASH LEGS).

Workstream W (lot N1b-1) writes the conversion of the surviving half; workstream J ("Numeri e
analisi") reviewed the expected numbers below on 15/10. What N1b-1 converts (coordinator, point 47):
an incoming TRANSFER half into an ADJUSTMENT, a CASH_TRANSFER / FX_CONVERSION half into a DEPOSIT or
a WITHDRAWAL by its sign; and, with decision 47, an outgoing TRANSFER half into an ADJUSTMENT −q handed
over at its own broker's Auto cost (MIRROR).

THE SCENARIO — S7 of test_portfolio_cost_currency.py, with a cost basis on the arrival. One user
owns brokers A and B, 100 % each. On 1 Oct 2018 A receives 200 EUR and buys 10 X for 200 EUR, 20
EUR a unit. On 3 Oct 4 X move from A to B by a linked TRANSFER pair; B's leg carries a cost basis
of 20 EUR per unit — the field is per unit (db/models.py) — so 80 EUR for the 4, the average cost
A gives away. X is quoted 25 EUR on 3 Oct and 30 EUR on 5 Oct, the day both readings are taken.
Then A is deleted through the real path, BrokerService.delete_bulk(force=True). Today the deletion
leaves B's leg a TRANSFER without its pair; N1b-1 makes it an ADJUSTMENT +4 with the same cost
basis (BR-U-073, test_broker_service.py).

(a) Lots analysis of X — LotsAnalysisService.get_lots_analysis, the entry point of S7/L4.
    Today: FAILED. The FIFO engine meets a TRANSFER without its pair: TRANSFER_PAIR_MISSING, a
    quantitative failure (financial_math/fifo/models.py, _QUANTITATIVE_FAILURE_CODES), and no lot.
    After: COMPLETE, no issue, one LONG lot opened by B's row — an ADJUSTMENT_IN event opens a lot
    at the cost basis as unit price (financial_math/fifo/engine.py). LOTS below, with J's two pins:
    - the lot's date: a NEW lot opened on 3 Oct, the transfer day, at the cost basis as unit price —
      not A's lot of 1 Oct carried over by FIFO — so the holding period restarts at the transfer;
    - its reference price: an ADJUSTMENT_IN lot looks it up on its opening day
      (financial_math/fifo/engine.py:345-372, through lots_analysis_service.py
      reference_price_lookup and financial_math/lots/prices.py opening_reference_price): 25 EUR on
      3 Oct, so its relative return is +20 % (30 against 25) while its P&L % — total_return, the
      "Total return" of the lots table: total_pnl / original_cost — is +50 % (120 against 80). The
      response carries both as fractions (lots_analysis_service.py, _build_lot_summaries): 0.2, 0.5.

(b) Dashboard — PortfolioService.get_summary for the user, in EUR, up to 5 Oct.
    Today: the classifier leaves an unlinked TRANSFER "normal" (financial_math/portfolio/
    classifier.py:104-107) and DailyStateBuilder._transfer_leg_capital books it as in-kind capital
    at market value on its own date: 4 × 25 = 100 EUR invested, 120 − 100 = 20 EUR of P&L.
    After: an ADJUSTMENT-in carrying a cost basis is a capital adjustment
    (DailyStateBuilder._is_capital_adjustment): the cost it brings into the pool is the capital,
    4 × 20 = 80 EUR, and nothing is booked at market value. DASHBOARD below. The holding itself —
    quantity, average cost, value, gain — reads the same today and after: financial_math.
    average_cost costs a TRANSFER-in and an ADJUSTMENT-in alike, at their cost basis.
    When B's owner does not own A (A goes with its owner's broker or account), the arrival came from
    outside their scope and counted at market value before the deletion too: 100 before, 80 after.

Case 1 runs each expectation twice: on a control book whose B holds that ADJUSTMENT +4 written as
such — green today, it proves the numbers are what the engines do with an ADJUSTMENT-in — and on
the orphan the deletion leaves, RED today. The orphan is found by its id: the conversion is expected
in place, as the app's own split does it (batch_edits.apply_splits).

CASE 2 — B's leg without a cost basis, S7's own arrival: the cost A carried would go with A. J's
decision (15/10): before A's rows go, the deletion writes on B's leg A's Auto cost, by the path the
Auto mode already takes for the receiving side of a TRANSFER — TransactionAutoCostMixin.
_auto_cost_source (transactions/auto_cost.py:173-186: the partner's broker, without the row and its
partner, up to the partner's date) and compute_wac_iterative (portfolio_service.py) — and writes
cost_basis_override and cost_basis_currency together, as the model wants them. A's pool on 3 Oct,
without its outgoing leg, is the 10 X bought at 20 EUR: B's row becomes the ADJUSTMENT +4 at 20 EUR
of case 1, and the lots and the Dashboard read LOTS and DASHBOARD. An empty pool inherits decision
P-1 (9/10): compute_wac_iterative gives 0 in the asset currency (portfolio_service.py:185-190) and
Auto writes it, `if wac_result.wac:` being true for a Currency of amount 0 (_write_auto_cost,
auto_cost.py:141) — BR-U-079 in test_broker_service.py. A leg that has a cost basis keeps it (case 1);
a split of the pair writes no cost (BR-U-076). Measured at 063e5b7cf (2026-10-15), before N1b-1:
                         before N1b-1: the orphan         an ADJUSTMENT +4 left without cost basis
                         TRANSFER                         (what a split leaves; the post-migration
                                                          fix too: OPTION A below)
  lots status            FAILED                           DEGRADED
  lots issues            TRANSFER_PAIR_MISSING,           MISSING_COST_BASIS
                         MISSING_COST_BASIS
  lots                   none                             1 LONG lot of 4 opened by B's row: unit
                                                          price 0, cost 0, value 120, P&L 120
  WAC lines (B, all)     no point                         no point
  Dashboard, B's X       4, WAC none, value 120, gain none (both)
  open cost basis        0                                0
  invested / P&L         100 / 20 (4 × 25 at market)      0 / 120 (no cost basis: no capital)
  issues                 MISSING_COST_BASIS               MISSING_COST_BASIS, MWRR_NOT_CALCULABLE (info:
                                                          no capital flow at all)

OPTION A — point 46, J 15/10. In a database where A went before 1.3, B's TRANSFER +4 without cost basis
has no sender left to give it an Auto cost: the post-migration fix (orphan_pair_halves, N1b-2) makes it the
ADJUSTMENT +4 without cost basis of the table's right column. Written directly — no deletion, no migration —
it reads: lots DEGRADED on MISSING_COST_BASIS, one LONG lot of 4 opened by B's row on 3 Oct at unit price 0
(cost 0, value 120, P&L 120; reference 25, so +20 % of relative return; no total return, nothing to divide
by), no WAC line; Dashboard 0 invested and 120 of P&L — no cost basis, no capital
(DailyStateBuilder._is_capital_adjustment) — net worth 120, B's X with no average cost nor gain, open cost
basis 0, and S5's MISSING_COST_BASIS banner (test_portfolio_cost_currency.py:556). The same row as the fix
finds it, a TRANSFER without its pair, reads 100 invested and 20 of P&L: the change J declares before the
migration, 100 → 0 and 20 → 120. Controls, green today.

MIRROR — B deleted: A's outgoing leg survives. Decision 47 (W's part; J's CP-16 reads it,
financial_math/fifo/engine.py): the deletion makes it an ADJUSTMENT −4 handed over at cost —
cost_basis_override and cost_basis_currency written together, A's Auto cost:
TransactionService._handover_cost, compute_wac_iterative over A up to 3 Oct without the leg, the 10 X
bought for 200 EUR, so 20 EUR a unit (BR-U-073/078/086 in test_broker_service.py). The numbers are
those of J's book (test_adjustment_out_with_cost_numbers.py: the same scenario, the leg written
directly), run twice as case 1's are: on a control book whose A holds that ADJUSTMENT −4 at 20 EUR
written as such — green today, after CP-16 — and on the orphan the deletion leaves, RED until decision
47. A alone on 5 Oct:
- lots: COMPLETE, no issue. The only lot is A's BUY of 1 Oct, 10 at 20; the ADJUSTMENT_OUT closes 4 of
  it at the row's 20 EUR (engine._handover_unit_price): realized 4 × (20 − 20) = 0, proceeds 4 × 20 =
  80, the value handed over at cost. Open 6, value 6 × 30 = 180, pnl 180 + 80 − 200 = 60, market 60,
  total 60, total return 60 / 200 = 0.3. A BUY lot opens with no reference price of its own, so its
  reference is its own unit price, 20, "exact" (lots/prices.py, opening_reference_price): relative
  return 30 / 20 − 1 = 0.5. The WAC lines are today's — 10 at 20, then 6 at 20 from 3 Oct: a reduction
  leaves the average as it was (financial_math/average_cost.py).
- Dashboard: invested 200 − 4 × 20 = 120 — an ADJUSTMENT −4 with a cost is a capital distribution
  (DailyStateBuilder._is_capital_adjustment) —, net worth 6 × 30 = 180, P&L 60; A's X 6 at 20, value
  180, gain 60; open cost basis 120; no warning.
Today the leg stays a TRANSFER without its pair: the lots FAIL on TRANSFER_PAIR_MISSING — and that
FAILED analysis still lists A's lot of 1 Oct with its 10 X open, value 300, P&L 100 —, and the Dashboard
books the orphan at market (_transfer_leg_capital, 4 × 25): invested 100, P&L 80. Not pinned here: a leg
whose Auto cost needs a missing conversion stays that TRANSFER (BR-U-087).

MIRROR IN ANOTHER CURRENCY (W-B55) — the MIRROR with X″, a USD asset, read in EUR: from the deletion to the numbers.
A's Auto cost (decision 47) is compute_wac_iterative's without a currency hint, so in the currency of A's last
purchase, each purchase converted at the rate of its own day; J-24 makes the Dashboard realize the exchange difference
on the handover day, as the lots already did (CP-7a): D at that day's rate, minus C, the historical cost the pool gives
up. One user owns A and B, 100 % each. On 3 Dec 2018 A receives 1000 USD and buys 10 X″ for 1000 USD, 100 USD a unit,
when 1 EUR = 1.25 USD (1 USD = 0.80 EUR): capital 800 EUR, 80 EUR a unit. On 5 Dec 4 X″ move from A to B by a linked
TRANSFER pair, when 1 EUR = 1.60 USD (1 USD = 0.625 EUR) and X″ is quoted 110 USD; B's leg carries no cost basis, it
goes with B. B deleted, A's −4 becomes an ADJUSTMENT at 100 USD a unit, in USD. A alone on 5 Dec, in EUR:
- Dashboard: D = 400 USD × 0.625 = 250 leaves the capital, invested 800 − 250 = 550; C = 4 × 80 = 320, realized
  D − C = −70; the 6 X″ left are worth 6 × 110 × 0.625 = 412.5 against 6 × 80 = 480, −67.5 unrealized; net worth
  412.5 (no cash: 1000 − 1000 USD), P&L 412.5 − 550 = −137.5; no warning.
- lots: COMPLETE, no issue; A's BUY lot of 10 at 800 hands 4 over at the handover's rate — proceeds 250, realized
  −70 —; open 6 worth 412.5, market −67.5, total −137.5. Its reference is its own unit price at the opening's rate,
  80: relative return 68.75 / 80 − 1. The WAC lines 10, then 6, at 80: a reduction leaves the average.
- the J-24 parity: the Dashboard's realized and P&L are the lot's, −70 and −137.5.
Control and orphan as in the MIRROR. Every reading stops on 5 Dec: ``fx_rates`` is global, and a later day would
value the 6 X″ at a rate the test did not write.

CASH LEGS — J (15/10): an orphan cash leg already counts as an external flow
(financial_math/portfolio/classifier.py:96-107), as the DEPOSIT or WITHDRAWAL it becomes, so capital
and P&L do not move. Two Dashboard series do, both corrections:
- the acquisition funding (GrowthChart, new capital against reinvested) —
  PortfolioService.get_acquisition_funding_history, each day's purchases split into from_new_capital
  and from_reinvested. The engine runs from the first row (date_from=None, portfolio_service.py:1596;
  financial_math/portfolio/engine.py:246) and keeps per-broker pools K (capital) and R (returns) and
  a global W (returns withdrawn), in financial_math/portfolio/daily_state.py: a DEPOSIT restores R
  from W first, the rest to K (:522-526); a WITHDRAWAL takes K first, then R, which goes to W
  (:528-534); a SELL gives K its cost and R its gain (:505-512); a BUY takes R first, then K, and that
  split is the series (:549-555); a CASH_TRANSFER / FX_CONVERSION moves pools only when
  linked_internal (:557-570). A day replays purchases before cash rows (:451-455). An orphan cash leg
  goes through no branch: today it moves the money but not the pools.
- the deposits of the P&L income mode — PortfolioService.get_deposit_history reads DEPOSIT only
  (portfolio_service.py:1560): an incoming leg that becomes a DEPOSIT appears on its day.
X is quoted 100 EUR on 2 Oct, 120 on 3 and 5 Oct, 100 on 6 and 7 Oct; every reading is on 7 Oct.
C1 — the incoming leg, A deleted. B: +1000 on 1 Oct, 10 X bought for 1000 on 2 Oct, sold for 1200
  on 3 Oct (K 1000, R 200), 1200 withdrawn on 4 Oct (K 0, R 0, W 200: the gain is out); on 5 Oct
  300 arrive from A by CASH_TRANSFER (A: +300 on 1 Oct); on 6 Oct 3 X bought for 300.
  Today: no pool moves on 5 Oct, so the purchase of 6 Oct is 300 new capital and 0 reinvested;
  deposits: 1000 on 1 Oct. After, a DEPOSIT of 300 restores R from W, 200, and K gets 100: the
  purchase is 100 new capital and 200 reinvested; deposits: 1000 on 1 Oct and 300 on 5 Oct.
  Without returns withdrawn before (W 0) the DEPOSIT goes whole to K and the purchase splits as
  today: only the deposit would appear.
C2 — the outgoing leg, B deleted. A: +1000 on 1 Oct, 10 X bought for 1000 on 2 Oct, 5 sold for 600
  on 3 Oct (K 500, R 100), its 600 sent to B by CASH_TRANSFER on 4 Oct, the other 5 sold for 600 on
  5 Oct, 6 X bought for 600 on 6 Oct.
  Today: no pool moves on 4 Oct, 5 Oct leaves K 1000 and R 200 — the 100 of gain already sent away
  still counted — so the purchase is 400 new capital and 200 reinvested. After, a WITHDRAWAL of
  600 takes K 500 and R 100 (W 100), 5 Oct leaves K 500 and R 100: the purchase is 500 new capital
  and 100 reinvested. Deposits: 1000 on 1 Oct, today and after.
  The second sale is what makes it move: a WITHDRAWAL takes K first and a BUY R first, so a purchase
  paid with what the leg leaves (all sold, part sent, the rest bought) splits alike today and after;
  it moves when K is refilled without R, here by the second sale's cost. W is global: a later
  DEPOSIT on any broker of the scope would first restore those 100 to its R.
Capital and P&L on 7 Oct, the same today and after: C1 invested 100 (1000 − 1200 + 300), net worth
300 (3 × 100), P&L 200; C2 invested 400 (1000 − 600), net worth 600 (6 × 100), P&L 200. Each series
runs on a control — the leg written as the DEPOSIT or WITHDRAWAL it becomes, no other broker —
green today, and on the orphan, RED today; capital and P&L are guards, green on both.

Rows are written straight into the session (no transaction validation) and never committed: the
``session`` fixture rolls back, so nothing outlives the test. Each test owns its user, brokers and
asset, and the prices it writes are its asset's. No FX — everything is in EUR — but in the MIRROR IN
ANOTHER CURRENCY, which writes the two EUR/USD rates it reads, on their own days: ``fx_rates`` is global
and unique on (date, base, quote), so a neighbour's row on those keys is deleted first, inside the same
rolled-back transaction, and comes back intact afterwards (J's pattern, ``_own_eur_usd_rate`` of
test_adjustment_out_with_cost_numbers.py). The days in between read them by backward fill; no figure
pinned here reads a rate of those days.
"""

import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, BrokerUserAccess, FxRate, PriceHistory, Transaction, TransactionType, User, UserRole
from backend.app.db.session import get_async_engine
from backend.app.schemas.brokers import BRDeleteItem
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import IssueSeverity, LotAnalysisType, LotsAnalysisResponse, PortfolioSummary
from backend.app.services.brokers.broker_service import BrokerService
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService
from backend.test_scripts.test_utils import print_section, print_success

REPORT = "EUR"
FUNDING_DAY = date(2018, 10, 1)  # A: +200 EUR, then 10 X for 200 EUR — 20 EUR a unit
TRANSFER_DAY = date(2018, 10, 3)  # 4 X leave A for B
READING_DAY = date(2018, 10, 5)  # date_to of both readings
PRICES = {TRANSFER_DAY: "25", READING_DAY: "30"}
COST_BASIS_PER_UNIT = "20"  # on B's leg: per unit, 4 × 20 = 80 EUR — the average cost A gives away

_TWENTY_FOR_FOUR = (Decimal("20"), Decimal("4"))  # a WAC line point: (average cost, pool quantity)

# (a) The lots analysis of X once B's arrival is an ADJUSTMENT +4 at 20 EUR a unit.
LOTS = {
    "calculation_status": "COMPLETE",
    "issue codes": [],
    "lots": [
        {
            "opens on": "B's arrival",  # the ADJUSTMENT_IN event of B's row opens it
            "broker": "B",
            "direction": "LONG",
            # J's pin (a): a NEW lot on the transfer day — not A's lot of 1 Oct carried over by FIFO —
            # so the holding period restarts at the transfer.
            "opening_date": TRANSFER_DAY,
            "original_quantity": Decimal("4"),
            "opening_unit_price": Decimal("20"),  # the cost basis per unit: the ADJUSTMENT_IN unit price
            "original_cost": Decimal("80"),  # 4 × 20
            "open_quantity": Decimal("4"),  # nothing has left B since
            "open_value": Decimal("120"),  # 4 × 30, the price of the reading day
            "pnl": Decimal("40"),  # 120 − 80
            # J's pin (b): the reference price is the close of the lot's opening day (fifo/engine.py:345-372)...
            "reference_unit_price": Decimal("25"),
            "reference_price_source": "exact",  # ...found on that day itself, not carried from an earlier one
            "relative_return": Decimal("0.2"),  # 30 / 25 − 1: +20 %, a fraction
            "total_return": Decimal("0.5"),  # the P&L %: total_pnl / original_cost = 40 / 80, +50 %, a fraction
        }
    ],
    # Today as after: 4 units at 20 from the transfer day — the arrival is costed at its cost basis whatever its type.
    "B's WAC line": {TRANSFER_DAY: _TWENTY_FOR_FOUR, date(2018, 10, 4): _TWENTY_FOR_FOUR, READING_DAY: _TWENTY_FOR_FOUR},
    "cumulative WAC line": {TRANSFER_DAY: _TWENTY_FOR_FOUR, date(2018, 10, 4): _TWENTY_FOR_FOUR, READING_DAY: _TWENTY_FOR_FOUR},
}

# (b) The Dashboard of the user, B being the only broker left.
DASHBOARD = {
    "brokers holding X": ["B"],
    "B": {
        "quantity": Decimal("4"),
        "wac_per_unit": Decimal("20"),  # the cost basis
        "current_value": Decimal("120"),  # 4 × 30
        "gain_loss": Decimal("40"),  # 120 − 4 × 20
    },
    "open_cost_basis": Decimal("80"),  # 4 × 20
    "net_worth": Decimal("120"),  # 4 × 30, and no cash at B
    "total_invested": Decimal("80"),  # the capital an ADJUSTMENT-in brings: its cost, 4 × 20 (today 100: 4 × 25, at market on 3 Oct)
    "total_gain_loss": Decimal("40"),  # 120 − 80 (today 20: 120 − 100)
    "warnings and errors": [],  # no cost, price or rate is missing
}

# (b) The same Dashboard for a user who owns B but not A, BEFORE A is deleted: the arrival comes from
# a broker outside their scope (linked_external_inflow), which DailyStateBuilder._transfer_leg_capital
# books as in-kind capital at market value on its date, 4 × 25 — today's engine, untouched by N1b-1.
DASHBOARD_ARRIVAL_FROM_OUTSIDE_THE_SCOPE = {**DASHBOARD, "total_invested": Decimal("100"), "total_gain_loss": Decimal("20")}  # 120 − 100

# Case 2: B's row once A is deleted — case 1's ADJUSTMENT +4, its cost basis written by the deletion.
# Today: a TRANSFER without cost basis (both None) and with its link cleared.
ARRIVAL_WITH_THE_AUTO_COST = {
    "broker": "B",
    "asset": "X",
    "type": TransactionType.ADJUSTMENT,
    "date": TRANSFER_DAY,
    "quantity": Decimal("4"),
    "cost_basis_override": Decimal("20"),  # A's Auto cost: its average cost on 3 Oct without its outgoing leg, 200 / 10
    "cost_basis_currency": "EUR",  # written with it: the model wants both or neither
    "related_transaction_id": None,
}

# OPTION A, point 46 (J 15/10): what orphan_pair_halves leaves of B's arrival without cost basis in a database
# where A went before 1.3 — an ADJUSTMENT +4 without cost basis, no sender left to give it an Auto cost.
LOTS_LEFT_WITHOUT_COST_BASIS = {
    "calculation_status": "DEGRADED",
    "issue codes": ["MISSING_COST_BASIS"],
    "lots": [
        {
            "opens on": "B's arrival",
            "broker": "B",
            "direction": "LONG",
            "opening_date": TRANSFER_DAY,  # a lot of its own from 3 Oct, as case 1's
            "original_quantity": Decimal("4"),
            "opening_unit_price": Decimal("0"),  # no cost basis: the ADJUSTMENT_IN opens its lot at zero
            "original_cost": Decimal("0"),
            "open_quantity": Decimal("4"),
            "open_value": Decimal("120"),  # 4 × 30: the value is known
            "pnl": Decimal("120"),  # 120 − 0: the whole value reads as gain
            "reference_unit_price": Decimal("25"),  # the close of the opening day, as case 1's
            "reference_price_source": "exact",
            "relative_return": Decimal("0.2"),  # 30 / 25 − 1: the price's move does not need a cost
            "total_return": None,  # total_pnl / original_cost: nothing to divide by
        }
    ],
    "B's WAC line": {},  # an unknown cost blanks the WAC lines (L3, test_portfolio_cost_currency.py)
    "cumulative WAC line": {},
}
DASHBOARD_LEFT_WITHOUT_COST_BASIS = {
    "brokers holding X": ["B"],
    "B": {"quantity": Decimal("4"), "wac_per_unit": None, "current_value": Decimal("120"), "gain_loss": None},  # 4 × 30; no average cost, no gain
    "open_cost_basis": Decimal("0"),  # the 4 X count at zero cost
    "net_worth": Decimal("120"),
    "total_invested": Decimal("0"),  # no cost basis, no capital: DailyStateBuilder._is_capital_adjustment needs one
    "total_gain_loss": Decimal("120"),  # 120 − 0
    "warnings and errors": ["MISSING_COST_BASIS"],
}
# The same row before the fix, a TRANSFER +4 without its pair as an older deletion left it (link NULL): its 4 X
# booked as capital at market on 3 Oct, 4 × 25 (DailyStateBuilder._transfer_leg_capital). The holding and the
# banner read the same; capital and P&L are what J declares before the migration: 100 → 0, 20 → 120.
DASHBOARD_BEFORE_THE_FIX = {**DASHBOARD_LEFT_WITHOUT_COST_BASIS, "total_invested": Decimal("100"), "total_gain_loss": Decimal("20")}  # 120 − 100

# MIRROR: A once B is deleted, read on 5 Oct. Decision 47: A's outgoing leg handed over at A's Auto cost.
HANDOVER_COST_PER_UNIT = "20"  # A's average on 3 Oct without its outgoing leg: 200 / 10
MIRROR_LEG = {
    "broker": "A",
    "asset": "X",
    "type": TransactionType.ADJUSTMENT,  # today a TRANSFER without its pair
    "date": TRANSFER_DAY,
    "quantity": Decimal("-4"),
    "cost_basis_override": Decimal(HANDOVER_COST_PER_UNIT),  # A's Auto cost (today None)
    "cost_basis_currency": "EUR",  # written with it: the model wants both or neither (today None)
    "related_transaction_id": None,  # its pair is gone
}
_SIX_AT_TWENTY, _TEN_AT_TWENTY = (Decimal("20"), Decimal("6")), (Decimal("20"), Decimal("10"))  # WAC line points
# The figures of a lot that its closures move: what a handover at cost changes.
_CLOSURE_FIELDS = ("cumulative_proceeds", "realized_pnl", "market_pnl", "total_pnl")
MIRROR_LOTS = {
    "calculation_status": "COMPLETE",  # today FAILED: the FIFO engine meets a TRANSFER without its pair
    "issue codes": [],  # today ["TRANSFER_PAIR_MISSING"]
    "lots": [
        {
            "opens on": "A's purchase",  # the only lot: A's BUY of 1 Oct
            "broker": "A",
            "direction": "LONG",
            "opening_date": FUNDING_DAY,
            "original_quantity": Decimal("10"),
            "opening_unit_price": Decimal("20"),  # 200 / 10
            "original_cost": Decimal("200"),
            "open_quantity": Decimal("6"),  # 4 handed over on 3 Oct
            "open_value": Decimal("180"),  # 6 × 30
            "pnl": Decimal("60"),  # 180 + 80 of proceeds − 200
            # A BUY lot has no reference price of its own: opening_reference_price falls back to its unit price, "exact".
            "reference_unit_price": Decimal("20"),
            "reference_price_source": "exact",
            "relative_return": Decimal("0.5"),  # 30 / 20 − 1
            "total_return": Decimal("0.3"),  # total_pnl / original_cost = 60 / 200
            "cumulative_proceeds": Decimal("80"),  # 4 × 20, the value handed over at cost (CP-16)
            "realized_pnl": Decimal("0"),  # 4 × (20 − 20): closed at the row's cost, which is the lot's
            "market_pnl": Decimal("60"),  # pnl − realized
            "total_pnl": Decimal("60"),  # market + realized + 0 of income: the Dashboard's P&L
        }
    ],
    # As today: 10 at 20, then 6 at 20 from 3 Oct — a reduction leaves the average as it was.
    "A's WAC line": {FUNDING_DAY: _TEN_AT_TWENTY, date(2018, 10, 2): _TEN_AT_TWENTY, TRANSFER_DAY: _SIX_AT_TWENTY, date(2018, 10, 4): _SIX_AT_TWENTY, READING_DAY: _SIX_AT_TWENTY},
    "cumulative WAC line": {FUNDING_DAY: _TEN_AT_TWENTY, date(2018, 10, 2): _TEN_AT_TWENTY, TRANSFER_DAY: _SIX_AT_TWENTY, date(2018, 10, 4): _SIX_AT_TWENTY, READING_DAY: _SIX_AT_TWENTY},
}
MIRROR_DASHBOARD = {
    "brokers holding X": ["A"],
    "A": {
        "quantity": Decimal("6"),  # 10 − 4
        "wac_per_unit": Decimal("20"),
        "current_value": Decimal("180"),  # 6 × 30
        "gain_loss": Decimal("60"),  # 180 − 6 × 20
    },
    "open_cost_basis": Decimal("120"),  # 6 × 20
    "net_worth": Decimal("180"),  # 6 × 30, and no cash: 200 − 200
    # 200 deposited − 4 × 20 handed over at cost, a capital distribution (today 100: the orphan leg at market, 4 × 25)
    "total_invested": Decimal("120"),
    "total_gain_loss": Decimal("60"),  # 180 − 120 (today 80: 180 − 100)
    "warnings and errors": [],
}

# MIRROR IN ANOTHER CURRENCY (W-B55, module docstring): X″ quoted in USD, A read in EUR on the handover day.
# FxRate stores the pair as EUR/USD (base < quote): 1 EUR = rate USD, so 1 USD = 1 / rate EUR.
# December 2018: no other test file writes EUR/USD on these days — the delete-then-add of _own_eur_usd_rate holds anyway.
FOREIGN_CURRENCY = "USD"
FOREIGN_FUNDING_DAY = date(2018, 12, 3)  # A: +1000 USD, then 10 X″ for 1000 USD — 100 USD a unit
FOREIGN_TRANSFER_DAY = date(2018, 12, 5)  # 4 X″ leave A for B
FOREIGN_READING_DAY = FOREIGN_TRANSFER_DAY  # date_to of every reading: no rate or price after the ones the test wrote
FOREIGN_EUR_USD_RATES = {FOREIGN_FUNDING_DAY: "1.25", FOREIGN_TRANSFER_DAY: "1.6"}  # 1 USD = 0.80 EUR, then 0.625
FOREIGN_PRICES = {FOREIGN_TRANSFER_DAY: "110"}  # USD
FOREIGN_HANDOVER_COST_PER_UNIT = "100"  # A's Auto cost: in USD, the currency of its last purchase, 1000 / 10
# (a) A's row once B is deleted: decision 47's ADJUSTMENT −4, its cost in the currency compute_wac_iterative chose.
FOREIGN_MIRROR_LEG = {
    "broker": "A",
    "asset": "X",
    "type": TransactionType.ADJUSTMENT,
    "date": FOREIGN_TRANSFER_DAY,
    "quantity": Decimal("-4"),
    "cost_basis_override": Decimal(FOREIGN_HANDOVER_COST_PER_UNIT),  # per unit, not converted: no currency hint
    "cost_basis_currency": FOREIGN_CURRENCY,  # the currency of A's last purchase, written with the cost
    "related_transaction_id": None,  # its pair is gone
}
_SIX_AT_EIGHTY, _TEN_AT_EIGHTY = (Decimal("80"), Decimal("6")), (Decimal("80"), Decimal("10"))  # WAC line points, in EUR
# (a) The lots of X″ at A, in EUR: each leg of the closure at its own date (CP-7a).
FOREIGN_MIRROR_LOTS = {
    "calculation_status": "COMPLETE",
    "issue codes": [],
    "lots": [
        {
            "opens on": "A's purchase",  # the only lot: A's BUY of 3 Dec
            "broker": "A",
            "direction": "LONG",
            "opening_date": FOREIGN_FUNDING_DAY,
            "original_quantity": Decimal("10"),
            "opening_unit_price": Decimal("80"),  # 100 USD at 0.80, the opening's rate
            "original_cost": Decimal("800"),  # 1000 USD at 0.80
            "open_quantity": Decimal("6"),  # 4 handed over on 5 Dec
            "open_value": Decimal("412.5"),  # 6 × 110 USD at 0.625, the reading day's rate
            "pnl": Decimal("-137.5"),  # 412.5 + 250 of proceeds − 800
            # A BUY lot has no reference price of its own: its unit price, at the opening's rate, "exact".
            "reference_unit_price": Decimal("80"),
            "reference_price_source": "exact",
            "relative_return": Decimal("-0.140625"),  # 68.75 / 80 − 1: 110 USD at 0.625 against 100 USD at 0.80
            "total_return": Decimal("-0.171875"),  # total_pnl / original_cost = −137.5 / 800
            "cumulative_proceeds": Decimal("250"),  # D: 4 × 100 USD at 0.625, the handover's rate
            "realized_pnl": Decimal("-70"),  # D − C = 250 − 4 × 80, the cost at the opening's rate
            "market_pnl": Decimal("-67.5"),  # pnl − realized: 412.5 − 6 × 80
            "total_pnl": Decimal("-137.5"),  # market + realized + 0 of income: the Dashboard's P&L
        }
    ],
    # 10 at 80, then 6 at 80 from 5 Dec: each purchase at its own day's rate, and a reduction leaves the average.
    "A's WAC line": {FOREIGN_FUNDING_DAY: _TEN_AT_EIGHTY, date(2018, 12, 4): _TEN_AT_EIGHTY, FOREIGN_TRANSFER_DAY: _SIX_AT_EIGHTY},
    "cumulative WAC line": {FOREIGN_FUNDING_DAY: _TEN_AT_EIGHTY, date(2018, 12, 4): _TEN_AT_EIGHTY, FOREIGN_TRANSFER_DAY: _SIX_AT_EIGHTY},
}
# (b) The Dashboard of A, in EUR: D leaves the capital, D − C is realized (J-24).
FOREIGN_MIRROR_DASHBOARD = {
    "brokers holding X": ["A"],
    "A": {
        "quantity": Decimal("6"),  # 10 − 4
        "wac_per_unit": Decimal("80"),  # the historical cost: 100 USD at 0.80
        "current_value": Decimal("412.5"),  # 6 × 110 USD at 0.625
        "gain_loss": Decimal("-67.5"),  # 412.5 − 6 × 80
    },
    "open_cost_basis": Decimal("480"),  # 6 × 80
    "net_worth": Decimal("412.5"),  # the 6 X″, and no cash: 1000 − 1000 USD
    "total_invested": Decimal("550"),  # 1000 USD at 0.80 − D, the 400 USD handed over at 0.625: 800 − 250
    "total_gain_loss": Decimal("-137.5"),  # 412.5 − 550: −70 realized, −67.5 unrealized
    "warnings and errors": [],
    "period_realized_gain_loss": Decimal("-70"),  # D − C = 250 − 320, from the first row to 5 Dec
}
# (c) The J-24 parity, the point of W-B55: the Dashboard's realized and P&L are A's lot's realized_pnl and total_pnl.
FOREIGN_PARITY = {"realized": Decimal("-70"), "P&L": Decimal("-137.5")}

# CASH LEGS (module docstring). Every reading is on 7 Oct.
CASH_READING_DAY = date(2018, 10, 7)
CASH_PRICES = {date(2018, 10, 2): "100", date(2018, 10, 3): "120", date(2018, 10, 5): "120", date(2018, 10, 6): "100", CASH_READING_DAY: "100"}


@dataclass(frozen=True)
class CashCase:
    """The surviving broker's own rows — (day, type, quantity of X, EUR amount) — and its cash leg: day, signed EUR amount."""

    rows: tuple[tuple[date, TransactionType, str, str], ...]
    leg_day: date
    leg_amount: str


CASH_CASES = {
    # C1 — B, the gain withdrawn before 300 arrive from A by CASH_TRANSFER, then a purchase; A deleted.
    "C1": CashCase(
        rows=(
            (date(2018, 10, 1), TransactionType.DEPOSIT, "0", "1000"),  # K 1000
            (date(2018, 10, 2), TransactionType.BUY, "10", "-1000"),  # from K; K 0
            (date(2018, 10, 3), TransactionType.SELL, "-10", "1200"),  # K + 1000 (cost), R + 200 (gain)
            (date(2018, 10, 4), TransactionType.WITHDRAWAL, "0", "-1200"),  # K − 1000, R − 200 → W 200
            (date(2018, 10, 6), TransactionType.BUY, "3", "-300"),  # the purchase the leg changes
        ),
        leg_day=date(2018, 10, 5),
        leg_amount="300",  # in, from A
    ),
    # C2 — A, half its X sold at a gain, its 600 sent to B by CASH_TRANSFER, the rest sold, then a purchase; B deleted.
    "C2": CashCase(
        rows=(
            (date(2018, 10, 1), TransactionType.DEPOSIT, "0", "1000"),  # K 1000
            (date(2018, 10, 2), TransactionType.BUY, "10", "-1000"),  # from K; K 0
            (date(2018, 10, 3), TransactionType.SELL, "-5", "600"),  # K 500, R 100
            (date(2018, 10, 5), TransactionType.SELL, "-5", "600"),  # K + 500, R + 100
            (date(2018, 10, 6), TransactionType.BUY, "6", "-600"),  # the purchase the leg changes
        ),
        leg_day=date(2018, 10, 4),
        leg_amount="-600",  # out, to B
    ),
}

# Both series once the other broker is deleted and the leg converted (N1b-1); the control reads them today.
# acquisition funding: purchase day → (from_new_capital, from_reinvested); deposits: day → amount.
CASH_SERIES = {
    "C1": {
        # 6 Oct today: (300, 0) — the orphan leg moved no pool. The DEPOSIT restores 200 of R from W, K gets 100.
        "acquisition funding": {date(2018, 10, 2): (Decimal("1000"), Decimal("0")), date(2018, 10, 6): (Decimal("100"), Decimal("200"))},
        "deposits": {date(2018, 10, 1): Decimal("1000"), date(2018, 10, 5): Decimal("300")},  # today no 5 Oct: DEPOSIT rows only
    },
    "C2": {
        # 6 Oct today: (400, 200) — the 100 of gain sent away still in R. The WITHDRAWAL takes K 500, then R 100.
        "acquisition funding": {date(2018, 10, 2): (Decimal("1000"), Decimal("0")), date(2018, 10, 6): (Decimal("500"), Decimal("100"))},
        "deposits": {date(2018, 10, 1): Decimal("1000")},  # today as after: a WITHDRAWAL is no deposit
    },
}

# Capital and P&L on 7 Oct, the same today and after: an orphan cash leg already counts as an external flow.
CASH_TOTALS = {
    "C1": {"net_worth": Decimal("300"), "total_invested": Decimal("100"), "total_gain_loss": Decimal("200")},  # 3 × 100; 1000 − 1200 + 300
    "C2": {"net_worth": Decimal("600"), "total_invested": Decimal("400"), "total_gain_loss": Decimal("200")},  # 6 × 100; 1000 − 600
}


# =============================================================================
# FIXTURES & HELPERS
# =============================================================================


@pytest.fixture(scope="module")
def engine():
    return get_async_engine()


@pytest_asyncio.fixture
async def session(engine):
    async with AsyncSession(engine, expire_on_commit=False) as s:
        yield s
        await s.rollback()


@dataclass
class Book:
    """One test's user, the broker the readings are about, asset X and that broker's leg of the transfer.

    The broker is B, its leg the arrival; in the MIRROR it is A, its leg the departure, and its purchase
    the BUY whose lot the lots page lists.
    """

    user: User
    broker: Broker
    asset: Asset
    leg: Transaction
    name: str = "B"
    leg_name: str = "B's arrival"
    purchase: Transaction | None = None


async def _owned_broker(session: AsyncSession, user: User, label: str) -> Broker:
    broker = Broker(name=f"Orphan transfer {label} {uuid4().hex[:12]}")
    session.add(broker)
    await session.flush()
    session.add(BrokerUserAccess(broker_id=broker.id, user_id=user.id, role=UserRole.OWNER, share_percentage=Decimal("1")))
    await session.flush()
    return broker


async def _new_user(session: AsyncSession) -> User:
    marker = uuid4().hex[:12]
    user = User(username=f"orphan_{marker}", email=f"orphan_{marker}@test.com", hashed_password="fakehash", is_active=True)
    session.add(user)
    await session.flush()
    return user


async def _user_and_asset(session: AsyncSession, label: str, prices: dict[date, str] = PRICES, currency: str = REPORT) -> tuple[User, Asset]:
    """A user and X, quoted ``prices`` in ``currency``: by default 25 EUR on the transfer day and 30 on the reading day."""
    user = await _new_user(session)
    asset = Asset(display_name=f"Orphan transfer {label} {uuid4().hex[:12]}", currency=currency, asset_type=AssetType.STOCK)
    session.add(asset)
    await session.flush()
    session.add_all(PriceHistory(asset_id=asset.id, date=day, close=Decimal(close), currency=currency, source_plugin_key="orphan_transfer_test") for day, close in prices.items())
    await session.flush()
    return user, asset


def _arrival(broker: Broker, asset: Asset, tx_type: TransactionType, cost_basis: str | None) -> Transaction:
    """B's +4 on the transfer day: no cash, a cost basis per unit or none."""
    return Transaction(
        broker_id=broker.id,
        asset_id=asset.id,
        type=tx_type,
        date=TRANSFER_DAY,
        quantity=Decimal("4"),
        cost_basis_override=None if cost_basis is None else Decimal(cost_basis),
        cost_basis_currency=None if cost_basis is None else REPORT,
    )


async def _transfer_book(session: AsyncSession, *, cost_basis: str | None, same_owner: bool = True) -> tuple[Book, User, Broker]:
    """The scenario up to the deletion: A's purchase and the linked TRANSFER pair. A belongs to B's owner, or to another user."""
    user, asset = await _user_and_asset(session, "orphan")
    owner_a = user if same_owner else await _new_user(session)
    broker_a = await _owned_broker(session, owner_a, "A")
    broker_b = await _owned_broker(session, user, "B")
    departure = Transaction(broker_id=broker_a.id, asset_id=asset.id, type=TransactionType.TRANSFER, date=TRANSFER_DAY, quantity=Decimal("-4"))
    arrival = _arrival(broker_b, asset, TransactionType.TRANSFER, cost_basis)
    session.add_all(
        [
            Transaction(broker_id=broker_a.id, type=TransactionType.DEPOSIT, date=FUNDING_DAY, amount=Decimal("200"), currency=REPORT),
            Transaction(broker_id=broker_a.id, asset_id=asset.id, type=TransactionType.BUY, date=FUNDING_DAY, quantity=Decimal("10"), amount=Decimal("-200"), currency=REPORT),
            departure,
            arrival,
        ]
    )
    await session.flush()
    # A linked pair references itself both ways: the ids exist only after the first flush.
    departure.related_transaction_id, arrival.related_transaction_id = arrival.id, departure.id
    await session.flush()
    return Book(user=user, broker=broker_b, asset=asset, leg=arrival), owner_a, broker_a


async def _delete_broker(session: AsyncSession, owner: User, broker: Broker) -> None:
    """The real path: BrokerService.delete_bulk with force, as DELETE /brokers?force=true and leave_broker call it."""
    response = await BrokerService(session).delete_bulk([BRDeleteItem(id=broker.id, force=True)], user_id=owner.id)
    assert [(result.success, result.message) for result in response.results] == [(True, None)]


async def _orphan_book(session: AsyncSession, *, cost_basis: str | None) -> Book:
    """The scenario, then A deleted: B's arrival is left without its pair."""
    book, owner_a, broker_a = await _transfer_book(session, cost_basis=cost_basis)
    await _delete_broker(session, owner_a, broker_a)
    return book


async def _control_book(session: AsyncSession, *, cost_basis: str | None, tx_type: TransactionType = TransactionType.ADJUSTMENT) -> Book:
    """B alone, holding its +4 written as ``tx_type`` — by default the ADJUSTMENT the deletion must leave — and nothing ever at A."""
    user, asset = await _user_and_asset(session, "control")
    broker_b = await _owned_broker(session, user, "B")
    arrival = _arrival(broker_b, asset, tx_type, cost_basis)
    session.add(arrival)
    await session.flush()
    return Book(user=user, broker=broker_b, asset=asset, leg=arrival)


async def _mirror_book(session: AsyncSession) -> Book:
    """The scenario, then B deleted: A's outgoing leg is left without its pair. The book of A."""
    book_b, owner_a, broker_a = await _transfer_book(session, cost_basis=COST_BASIS_PER_UNIT)
    departure = await session.get(Transaction, book_b.leg.related_transaction_id)
    # A's one BUY, found by what owns it: the broker this test made, the type.
    purchase = (await session.execute(select(Transaction).where(Transaction.broker_id == broker_a.id, Transaction.type == TransactionType.BUY))).scalar_one()
    await _delete_broker(session, book_b.user, book_b.broker)
    return Book(user=owner_a, broker=broker_a, asset=book_b.asset, leg=departure, name="A", leg_name="A's departure", purchase=purchase)


async def _mirror_control_book(session: AsyncSession) -> Book:
    """A alone, its −4 written as the ADJUSTMENT decision 47 makes the deletion of B leave — handed over at A's
    average, 20 EUR a unit, with its currency — and never a B. The book of A, as J's book of CP-16."""
    user, asset = await _user_and_asset(session, "mirror control")
    broker_a = await _owned_broker(session, user, "A")
    purchase = Transaction(broker_id=broker_a.id, asset_id=asset.id, type=TransactionType.BUY, date=FUNDING_DAY, quantity=Decimal("10"), amount=Decimal("-200"), currency=REPORT)
    handover = Transaction(
        broker_id=broker_a.id,
        asset_id=asset.id,
        type=TransactionType.ADJUSTMENT,
        date=TRANSFER_DAY,
        quantity=Decimal("-4"),
        cost_basis_override=Decimal(HANDOVER_COST_PER_UNIT),
        cost_basis_currency=REPORT,
    )
    session.add_all([Transaction(broker_id=broker_a.id, type=TransactionType.DEPOSIT, date=FUNDING_DAY, amount=Decimal("200"), currency=REPORT), purchase, handover])
    await session.flush()
    return Book(user=user, broker=broker_a, asset=asset, leg=handover, name="A", leg_name="A's departure", purchase=purchase)


async def _own_eur_usd_rate(session: AsyncSession, day: date, rate: str) -> None:
    """The EUR/USD rate of ``day`` the foreign book reads, written by it: 1 EUR = ``rate`` USD (J's pattern,
    test_adjustment_out_with_cost_numbers.py).

    ``fx_rates`` is global and unique on (date, base, quote). A neighbour's row on this key is deleted first, inside
    this test's transaction, which the ``session`` fixture rolls back: the neighbour's row comes back intact, and
    this test reads its own rate, never someone else's.
    """
    await session.execute(delete(FxRate).where(FxRate.date == day, FxRate.base == REPORT, FxRate.quote == FOREIGN_CURRENCY))
    session.add(FxRate(date=day, base=REPORT, quote=FOREIGN_CURRENCY, rate=Decimal(rate), source="TEST_W_B55"))
    await session.flush()


async def _foreign_purchase(session: AsyncSession, label: str) -> tuple[User, Asset, Broker, Transaction]:
    """W-B55's book up to the transfer: its two EUR/USD rates, a user, X″ quoted 110 USD on the transfer day, and A,
    which receives 1000 USD and buys 10 X″ with them on 3 Dec. The user, X″, A and the BUY."""
    for day, rate in FOREIGN_EUR_USD_RATES.items():
        await _own_eur_usd_rate(session, day, rate)
    user, asset = await _user_and_asset(session, label, prices=FOREIGN_PRICES, currency=FOREIGN_CURRENCY)
    broker_a = await _owned_broker(session, user, "A")
    purchase = Transaction(broker_id=broker_a.id, asset_id=asset.id, type=TransactionType.BUY, date=FOREIGN_FUNDING_DAY, quantity=Decimal("10"), amount=Decimal("-1000"), currency=FOREIGN_CURRENCY)
    session.add_all([Transaction(broker_id=broker_a.id, type=TransactionType.DEPOSIT, date=FOREIGN_FUNDING_DAY, amount=Decimal("1000"), currency=FOREIGN_CURRENCY), purchase])
    await session.flush()
    return user, asset, broker_a, purchase


async def _foreign_mirror_book(session: AsyncSession) -> Book:
    """W-B55's scenario, then B deleted through the real path: A's outgoing leg in USD is left without its pair. The book of A."""
    user, asset, broker_a, purchase = await _foreign_purchase(session, "foreign mirror")
    broker_b = await _owned_broker(session, user, "B")
    departure = Transaction(broker_id=broker_a.id, asset_id=asset.id, type=TransactionType.TRANSFER, date=FOREIGN_TRANSFER_DAY, quantity=Decimal("-4"))
    # B's leg carries no cost basis: it goes with B, and A's leg leaves at A's own Auto cost (decision 47) whatever it said.
    arrival = Transaction(broker_id=broker_b.id, asset_id=asset.id, type=TransactionType.TRANSFER, date=FOREIGN_TRANSFER_DAY, quantity=Decimal("4"))
    session.add_all([departure, arrival])
    await session.flush()
    # A linked pair references itself both ways: the ids exist only after the first flush.
    departure.related_transaction_id, arrival.related_transaction_id = arrival.id, departure.id
    await session.flush()
    await _delete_broker(session, user, broker_b)
    return Book(user=user, broker=broker_a, asset=asset, leg=departure, name="A", leg_name="A's departure", purchase=purchase)


async def _foreign_mirror_control_book(session: AsyncSession) -> Book:
    """A alone, its −4 written as the ADJUSTMENT decision 47 makes the deletion of B leave — at A's Auto cost, 100 USD a
    unit, with its currency — and never a B. The book of A."""
    user, asset, broker_a, purchase = await _foreign_purchase(session, "foreign mirror control")
    handover = Transaction(
        broker_id=broker_a.id,
        asset_id=asset.id,
        type=TransactionType.ADJUSTMENT,
        date=FOREIGN_TRANSFER_DAY,
        quantity=Decimal("-4"),
        cost_basis_override=Decimal(FOREIGN_HANDOVER_COST_PER_UNIT),
        cost_basis_currency=FOREIGN_CURRENCY,
    )
    session.add(handover)
    await session.flush()
    return Book(user=user, broker=broker_a, asset=asset, leg=handover, name="A", leg_name="A's departure", purchase=purchase)


async def _leg_now(session: AsyncSession, book: Book) -> dict | None:
    """The book's leg as the database holds it now — the in-memory copy refreshed — or None when it is gone."""
    statement = select(Transaction).where(Transaction.id == book.leg.id).execution_options(populate_existing=True)
    leg = (await session.execute(statement)).scalar_one_or_none()
    if leg is None:
        return None
    return {
        "broker": book.name if leg.broker_id == book.broker.id else leg.broker_id,
        "asset": "X" if leg.asset_id == book.asset.id else leg.asset_id,
        "type": leg.type,
        "date": leg.date,
        "quantity": leg.quantity,
        "cost_basis_override": leg.cost_basis_override,
        "cost_basis_currency": leg.cost_basis_currency,
        "related_transaction_id": leg.related_transaction_id,
    }


_BUILDERS = {"control": _control_book, "orphan": _orphan_book}
_ORIGINS = [
    pytest.param("control", id="control-adjustment-in-written-as-such"),
    pytest.param("orphan", id="orphan-left-by-deleting-broker-a"),
]
_MIRROR_BUILDERS = {"control": _mirror_control_book, "orphan": _mirror_book}
_MIRROR_ORIGINS = [
    pytest.param("control", id="control-adjustment-out-at-cost-written-as-such"),
    pytest.param("orphan", id="orphan-left-by-deleting-broker-b"),
]
_FOREIGN_MIRROR_BUILDERS = {"control": _foreign_mirror_control_book, "orphan": _foreign_mirror_book}
_FOREIGN_MIRROR_ORIGINS = [
    pytest.param("control", id="control-adjustment-out-at-cost-in-usd-written-as-such"),
    pytest.param("orphan", id="orphan-left-by-deleting-broker-b"),
]


async def _lots(session: AsyncSession, book: Book, *, date_to: date = READING_DAY) -> LotsAnalysisResponse:
    """The lots page of X for the user, in EUR, from the first movement to ``date_to`` (the reading day by default): lots and both WAC lines."""
    return await LotsAnalysisService(session).get_lots_analysis(
        user_id=book.user.id,
        asset_id=book.asset.id,
        broker_ids=None,
        date_from=None,
        date_to=date_to,
        target_currency=REPORT,
        selected_lot_ids=None,
        requested_analyses=[LotAnalysisType.LOT_SUMMARY, LotAnalysisType.BROKER_WAC_HISTORY, LotAnalysisType.CUMULATIVE_WAC_HISTORY],
    )


async def _dashboard(session: AsyncSession, book: Book, *, date_to: date = READING_DAY) -> PortfolioSummary:
    return await PortfolioService(session).get_summary(user_id=book.user.id, target_currency_override=REPORT, date_to=date_to)


def _amount(value: Currency | None) -> Decimal | None:
    return None if value is None else value.amount


def _opened_by(opening_transaction_id: int, book: Book) -> str | int:
    """The row that opened a lot, by the book's name for it — its leg, or its purchase — or else its id."""
    names = {book.leg.id: book.leg_name}
    if book.purchase is not None:
        names[book.purchase.id] = f"{book.name}'s purchase"
    return names.get(opening_transaction_id, opening_transaction_id)


def _lots_view(response: LotsAnalysisResponse, book: Book, *, closure_fields: tuple[str, ...] = ()) -> dict:
    quality = response.data_quality
    return {
        "calculation_status": response.calculation_status,
        "issue codes": [issue.code for issue in quality.issues] if quality is not None else None,
        "lots": [
            {
                "opens on": _opened_by(lot.opening_transaction_id, book),
                "broker": book.name if lot.opening_broker_id == book.broker.id else lot.opening_broker_id,
                "direction": lot.direction,
                "opening_date": lot.opening_date,
                "original_quantity": lot.original_quantity,
                "opening_unit_price": lot.opening_unit_price,
                "original_cost": lot.original_cost,
                "open_quantity": lot.open_quantity,
                "open_value": lot.open_value,
                "pnl": lot.pnl,
                "reference_unit_price": lot.reference_unit_price,
                "reference_price_source": lot.reference_price_source,
                "relative_return": lot.relative_return,
                "total_return": lot.total_return,
                **{name: getattr(lot, name) for name in closure_fields},
            }
            for lot in response.lots or []
        ],
        f"{book.name}'s WAC line": {point.date: (point.wac, point.pool_qty) for point in response.broker_wac_history or [] if point.broker_id == book.broker.id},
        "cumulative WAC line": {point.date: (point.wac, point.pool_qty) for point in response.cumulative_wac_history or []},
    }


def _dashboard_view(summary: PortfolioSummary, book: Book) -> dict:
    holdings_of_x = [holding for holding in summary.holdings if holding.asset_id == book.asset.id]
    at_broker = [holding for holding in holdings_of_x if holding.broker_id == book.broker.id]
    issues = summary.data_quality.issues if summary.data_quality is not None else []
    return {
        "brokers holding X": [book.name if holding.broker_id == book.broker.id else holding.broker_id for holding in holdings_of_x],
        book.name: {name: getattr(at_broker[0], name) for name in ("quantity", "wac_per_unit", "current_value", "gain_loss")} if len(at_broker) == 1 else at_broker,
        "open_cost_basis": _amount(summary.open_cost_basis),
        "net_worth": _amount(summary.net_worth),
        "total_invested": _amount(summary.total_invested),
        "total_gain_loss": _amount(summary.total_gain_loss),
        # MWRR availability (info) follows the capital flows, which is what moves here: left out.
        "warnings and errors": [issue.code for issue in issues if issue.severity != IssueSeverity.INFO],
    }


# The fields of a banner issue pinned the way S5 pins it (test_portfolio_cost_currency.py:556) — with the
# code and the CTA's target, as S7 and L3 add them.
_BANNER_FIELDS = ("code", "severity", "message_i18n_key", "message_params", "affected_asset_ids", "affected_asset_names", "cta_action", "cta_target", "group_key")


def _missing_cost_basis_banner(summary: PortfolioSummary) -> list[dict]:
    issues = summary.data_quality.issues if summary.data_quality is not None else []
    return [{name: getattr(issue, name) for name in _BANNER_FIELDS} for issue in issues if issue.code == "MISSING_COST_BASIS"]


def _expected_missing_cost_basis_banner(book: Book) -> list[dict]:
    """S5's banner: one MISSING_COST_BASIS warning naming X, the asset whose transaction the user must complete."""
    return [
        {
            "code": "MISSING_COST_BASIS",
            "severity": "warning",
            "message_i18n_key": "dataQuality.missingCostBasis",
            "message_params": {"count": 1},
            "affected_asset_ids": [book.asset.id],
            "affected_asset_names": [book.asset.display_name],
            "cta_action": "navigate_asset",
            "cta_target": str(book.asset.id),
            "group_key": "missing_cost_basis",
        }
    ]


async def _cash_book(session: AsyncSession, case: str, origin: str) -> User:
    """The case's surviving broker and the user owning it.

    Orphan: its leg is one half of a CASH_TRANSFER with another broker of the user, which is then
    deleted through the real path. Control: the leg is written as the DEPOSIT or WITHDRAWAL it
    becomes, and there never was another broker.
    """
    spec = CASH_CASES[case]
    user, asset = await _user_and_asset(session, f"cash {case}", prices=CASH_PRICES)
    survivor = await _owned_broker(session, user, f"{case} survivor")
    session.add_all(Transaction(broker_id=survivor.id, asset_id=None if quantity == "0" else asset.id, type=tx_type, date=day, quantity=Decimal(quantity), amount=Decimal(amount), currency=REPORT) for day, tx_type, quantity, amount in spec.rows)
    amount = Decimal(spec.leg_amount)
    if origin == "control":
        standalone_type = TransactionType.DEPOSIT if amount > 0 else TransactionType.WITHDRAWAL
        session.add(Transaction(broker_id=survivor.id, type=standalone_type, date=spec.leg_day, amount=amount, currency=REPORT))
        await session.flush()
        return user
    other = await _owned_broker(session, user, f"{case} other")
    leg = Transaction(broker_id=survivor.id, type=TransactionType.CASH_TRANSFER, date=spec.leg_day, amount=amount, currency=REPORT)
    other_leg = Transaction(broker_id=other.id, type=TransactionType.CASH_TRANSFER, date=spec.leg_day, amount=-amount, currency=REPORT)
    session.add_all([leg, other_leg])
    if amount > 0:  # the other broker sends: it was funded first
        session.add(Transaction(broker_id=other.id, type=TransactionType.DEPOSIT, date=date(2018, 10, 1), amount=amount, currency=REPORT))
    await session.flush()
    leg.related_transaction_id, other_leg.related_transaction_id = other_leg.id, leg.id
    await session.flush()
    await _delete_broker(session, user, other)
    return user


_CASH_ORIGINS = [
    pytest.param("control", id="control-deposit-or-withdrawal-written-as-such"),
    pytest.param("orphan", id="orphan-left-by-deleting-the-other-broker"),
]
_CASH_CASE_IDS = [
    pytest.param("C1", id="C1-incoming-leg-A-deleted"),
    pytest.param("C2", id="C2-outgoing-leg-B-deleted"),
]


async def _cash_series(session: AsyncSession, user: User) -> dict:
    """The two series J named, for the user up to the reading day: each purchase day's funding and each day's deposits."""
    service = PortfolioService(session)
    funding = await service.get_acquisition_funding_history(user_id=user.id, date_to=CASH_READING_DAY, target_currency_override=REPORT)
    deposits = await service.get_deposit_history(user_id=user.id, date_to=CASH_READING_DAY, target_currency_override=REPORT)
    return {
        "acquisition funding": {point.date: (point.from_new_capital.amount, point.from_reinvested.amount) for point in funding.points},
        "deposits": {point.date: point.deposit.amount for point in deposits.points},
    }


async def _cash_totals(session: AsyncSession, user: User) -> dict:
    summary = await PortfolioService(session).get_summary(user_id=user.id, target_currency_override=REPORT, date_to=CASH_READING_DAY)
    return {name: _amount(getattr(summary, name)) for name in ("net_worth", "total_invested", "total_gain_loss")}


# =============================================================================
# CASE 1 — B's leg carries a cost basis of 20 EUR a unit
# =============================================================================


class TestOrphanTransferWithCostBasis:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("origin", _ORIGINS)
    async def test_lots_of_x_once_broker_a_is_deleted(self, session, origin):
        """(a) Control green, orphan RED: COMPLETE, one NEW lot of 4 at 80 EUR opened by B's arrival on 3 Oct, reference 25, +20 % relative, +50 % total — today FAILED, TRANSFER_PAIR_MISSING."""
        print_section(f"V-3 (a) — lots of X once A is deleted ({origin})")
        book = await _BUILDERS[origin](session, cost_basis=COST_BASIS_PER_UNIT)

        response = await _lots(session, book)

        assert _lots_view(response, book) == LOTS
        print_success(f"V-3 (a) {origin}: COMPLETE, 4 at 80 EUR from 3 Oct, reference 25")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("origin", _ORIGINS)
    async def test_dashboard_once_broker_a_is_deleted(self, session, origin):
        """(b) Control green, orphan RED: 80 EUR invested — the ADJUSTMENT-in's cost — and 40 of P&L; today 100 at market value and 20."""
        print_section(f"V-3 (b) — Dashboard once A is deleted ({origin})")
        book = await _BUILDERS[origin](session, cost_basis=COST_BASIS_PER_UNIT)

        summary = await _dashboard(session, book)

        assert _dashboard_view(summary, book) == DASHBOARD
        print_success(f"V-3 (b) {origin}: 80 invested, 40 of P&L")

    @pytest.mark.asyncio
    async def test_dashboard_of_another_owner_read_before_and_after_broker_a_is_deleted(self, session):
        """(b) RED: B's owner does not own A, which goes with its owner's broker or account deletion — 100 invested before, the control's 80 after.

        The first reading also fills the Dashboard cache, keyed on the scope's transaction ids and their
        updated_at (financial_math/portfolio/engine.py, compute_tx_fingerprint): the scope of B's owner
        does not change, so a conversion that leaves updated_at as it was is served the figures of before.
        """
        print_section("V-3 (b) — Dashboard of B's owner when A belongs to someone else")
        book, owner_a, broker_a = await _transfer_book(session, cost_basis=COST_BASIS_PER_UNIT, same_owner=False)
        before = _dashboard_view(await _dashboard(session, book), book)
        assert before == DASHBOARD_ARRIVAL_FROM_OUTSIDE_THE_SCOPE, "precondition broken: before the deletion the arrival from outside the scope counts at market value, 4 × 25"

        await _delete_broker(session, owner_a, broker_a)

        after = _dashboard_view(await _dashboard(session, book), book)
        assert after == DASHBOARD
        print_success("V-3 (b) another owner: 100 invested before, 80 after")


# =============================================================================
# CASE 2 — B's leg without a cost basis: the deletion writes A's Auto cost on it (J 15/10)
# =============================================================================


class TestOrphanTransferWithoutCostBasis:
    @pytest.mark.asyncio
    async def test_arrival_without_cost_basis_takes_the_auto_cost_of_a_and_reads_as_case_1(self, session):
        """Case 2 (RED): B's row becomes an ADJUSTMENT +4 at A's Auto cost, 20 EUR, and the lots and the Dashboard read as case 1's — today a TRANSFER without cost basis, the lots FAILED, 100 invested and 20 of P&L."""
        print_section("V-3 case 2 — the arrival without a cost basis takes A's Auto cost")
        book = await _orphan_book(session, cost_basis=None)

        observed = {
            "B's row": await _leg_now(session, book),  # first: it refreshes the copy the readings below go through
            "lots": _lots_view(await _lots(session, book), book),
            "dashboard": _dashboard_view(await _dashboard(session, book), book),
        }
        for part, view in observed.items():
            print(f"{part}: {view}")

        assert observed == {"B's row": ARRIVAL_WITH_THE_AUTO_COST, "lots": LOTS, "dashboard": DASHBOARD}
        print_success("V-3 case 2: B's row at A's 20 EUR, the lots and the Dashboard of case 1")


# =============================================================================
# OPTION A, point 46 — what the post-migration fix leaves of a received TRANSFER without cost basis. Controls.
# =============================================================================


class TestReceivedTransferLeftWithoutCostBasis:
    """In a database where A went before 1.3, B's TRANSFER +4 without cost basis has no sender left to give it an
    Auto cost: orphan_pair_halves (N1b-2) makes it an ADJUSTMENT +4 without cost basis (option a, point 46, J 15/10).
    Written directly — no deletion, no migration — the row reads as below, green today."""

    @pytest.mark.asyncio
    async def test_lots_of_the_adjustment_in_without_cost_basis_the_fix_leaves(self, session):
        """Control: DEGRADED on MISSING_COST_BASIS; one LONG lot of 4 opened by B's row on 3 Oct at unit price 0 — cost 0, value 120, P&L 120, reference 25 (+20 %), no total return; no WAC line."""
        print_section("V-3 option a — lots of the ADJUSTMENT +4 without cost basis")
        book = await _control_book(session, cost_basis=None)

        observed = _lots_view(await _lots(session, book), book)
        print(f"lots: {observed}")

        assert observed == LOTS_LEFT_WITHOUT_COST_BASIS
        print_success("V-3 option a: DEGRADED, one lot of 4 at zero cost")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("held_as", "expected"),
        [
            pytest.param(TransactionType.TRANSFER, DASHBOARD_BEFORE_THE_FIX, id="before-the-fix-a-transfer-without-its-pair"),
            pytest.param(TransactionType.ADJUSTMENT, DASHBOARD_LEFT_WITHOUT_COST_BASIS, id="after-the-fix-an-adjustment-in-without-cost-basis"),
        ],
    )
    async def test_dashboard_of_a_received_transfer_without_cost_basis_before_and_after_the_fix(self, session, held_as, expected):
        """Controls: the fix moves the Dashboard from 100 invested and 20 of P&L to 0 invested and 120 of P&L — the change J declares before the migration — while the holding (4 X, 120, no average cost, no gain) and S5's MISSING_COST_BASIS banner stay."""
        print_section(f"V-3 option a — Dashboard of B's +4 without cost basis held as {held_as.value}")
        book = await _control_book(session, cost_basis=None, tx_type=held_as)

        summary = await _dashboard(session, book)
        observed = {"dashboard": _dashboard_view(summary, book), "MISSING_COST_BASIS banner": _missing_cost_basis_banner(summary)}
        for part, view in observed.items():
            print(f"{part}: {view}")

        assert observed == {"dashboard": expected, "MISSING_COST_BASIS banner": _expected_missing_cost_basis_banner(book)}
        print_success(f"V-3 option a ({held_as.value}): invested {expected['total_invested']}, P&L {expected['total_gain_loss']}, the banner")


# =============================================================================
# MIRROR — B deleted: A's outgoing leg handed over at A's Auto cost (decision 47, module docstring)
# =============================================================================


class TestOrphanOutgoingTransfer:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("origin", _MIRROR_ORIGINS)
    async def test_lots_of_x_at_a_once_broker_b_is_deleted(self, session, origin):
        """MIRROR (a) — control green, orphan RED until decision 47: A's leg an ADJUSTMENT −4 at A's Auto cost, 20 EUR; the lots COMPLETE, A's BUY lot handing 4 over at 20 — realized 0, proceeds 80, open 6 worth 180, P&L 60, total 60 —, the WAC lines 10 then 6 at 20. Today the orphan stays a TRANSFER and the lots FAIL on TRANSFER_PAIR_MISSING."""
        print_section(f"V-3 mirror (a) — lots of X once B is deleted ({origin})")
        book = await _MIRROR_BUILDERS[origin](session)

        observed = {
            "A's row": await _leg_now(session, book),  # first: it refreshes the copy the readings below go through
            "lots": _lots_view(await _lots(session, book), book, closure_fields=_CLOSURE_FIELDS),
        }
        for part, view in observed.items():
            print(f"{part}: {view}")

        assert observed == {"A's row": MIRROR_LEG, "lots": MIRROR_LOTS}
        print_success(f"V-3 mirror (a) {origin}: A's leg handed over at 20, the lots COMPLETE")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("origin", _MIRROR_ORIGINS)
    async def test_dashboard_of_a_once_broker_b_is_deleted(self, session, origin):
        """MIRROR (b) — control green, orphan RED until decision 47: 120 invested — 200 less the 4 × 20 handed over at cost —, net worth 180, P&L 60; A's X 6 at 20, value 180, gain 60. Today the orphan reads 100 invested (the leg at market, 4 × 25) and 80 of P&L."""
        print_section(f"V-3 mirror (b) — Dashboard of A once B is deleted ({origin})")
        book = await _MIRROR_BUILDERS[origin](session)

        observed = _dashboard_view(await _dashboard(session, book), book)
        print(f"dashboard: {observed}")

        assert observed == MIRROR_DASHBOARD
        print_success(f"V-3 mirror (b) {origin}: 120 invested, 60 of P&L")


# =============================================================================
# MIRROR IN ANOTHER CURRENCY (W-B55) — B deleted: A's leg in USD handed over at A's Auto cost, the exchange
# difference realized at the rate of its day (decision 47, J-24; module docstring)
# =============================================================================


class TestOrphanOutgoingTransferInAnotherCurrency:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("origin", _FOREIGN_MIRROR_ORIGINS)
    async def test_lots_of_x_at_a_once_broker_b_is_deleted(self, session, origin):
        """W-B55 (a): A's leg an ADJUSTMENT −4 at A's Auto cost, 100 USD — the currency of A's last purchase —; the lots COMPLETE, A's BUY lot of 10 at 800 EUR handing 4 over at the handover's rate — proceeds 250, realized −70 —, open 6 worth 412.5, market −67.5, total −137.5; the WAC lines 10 then 6 at 80."""
        print_section(f"W-B55 (a) — lots of X″ at A once B is deleted ({origin})")
        book = await _FOREIGN_MIRROR_BUILDERS[origin](session)

        observed = {
            "A's row": await _leg_now(session, book),  # first: it refreshes the copy the readings below go through
            "lots": _lots_view(await _lots(session, book, date_to=FOREIGN_READING_DAY), book, closure_fields=_CLOSURE_FIELDS),
        }
        for part, view in observed.items():
            print(f"{part}: {view}")

        assert observed == {"A's row": FOREIGN_MIRROR_LEG, "lots": FOREIGN_MIRROR_LOTS}
        print_success(f"W-B55 (a) {origin}: A's leg handed over at 100 USD, the lot realizes −70")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("origin", _FOREIGN_MIRROR_ORIGINS)
    async def test_dashboard_of_a_once_broker_b_is_deleted(self, session, origin):
        """W-B55 (b): 550 invested — 800 less D, the 400 USD handed over at 0.625 —, realized D − C = 250 − 320 = −70, net worth 412.5, P&L −137.5; A's X″ 6 at 80, value 412.5, gain −67.5."""
        print_section(f"W-B55 (b) — Dashboard of A once B is deleted ({origin})")
        book = await _FOREIGN_MIRROR_BUILDERS[origin](session)

        summary = await _dashboard(session, book, date_to=FOREIGN_READING_DAY)
        observed = {**_dashboard_view(summary, book), "period_realized_gain_loss": _amount(summary.period_realized_gain_loss)}
        print(f"dashboard: {observed}")

        assert observed == FOREIGN_MIRROR_DASHBOARD
        print_success(f"W-B55 (b) {origin}: 550 invested, −70 realized, −137.5 of P&L")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("origin", _FOREIGN_MIRROR_ORIGINS)
    async def test_the_dashboards_realized_is_the_lots_realized(self, session, origin):
        """W-B55 (c), the point: J-24's parity from the deletion on — one lot, A's BUY's, so the Dashboard's realized and P&L are the lot's realized_pnl and total_pnl, −70 and −137.5 on both sides."""
        print_section(f"W-B55 (c) — the Dashboard's realized and P&L against A's lot ({origin})")
        book = await _FOREIGN_MIRROR_BUILDERS[origin](session)

        summary = await _dashboard(session, book, date_to=FOREIGN_READING_DAY)
        lots = [lot for lot in (await _lots(session, book, date_to=FOREIGN_READING_DAY)).lots or [] if lot.opening_transaction_id == book.purchase.id]
        assert len(lots) == 1, f"precondition: one lot, opened by A's purchase — got {lots}"
        (lot,) = lots
        observed = {
            "Dashboard": {"realized": _amount(summary.period_realized_gain_loss), "P&L": _amount(summary.total_gain_loss)},
            "A's lot": {"realized": lot.realized_pnl, "P&L": lot.total_pnl},
        }
        print(f"parity: {observed}")

        assert observed == {"Dashboard": FOREIGN_PARITY, "A's lot": FOREIGN_PARITY}
        print_success(f"W-B55 (c) {origin}: the Dashboard and A's lot both realize −70, −137.5 of P&L")


# =============================================================================
# CASH LEGS — C1: the incoming leg, A deleted; C2: the outgoing leg, B deleted (module docstring)
# =============================================================================


class TestOrphanCashLeg:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("origin", _CASH_ORIGINS)
    @pytest.mark.parametrize("case", _CASH_CASE_IDS)
    async def test_acquisition_funding_and_deposits_once_the_other_broker_is_deleted(self, session, case, origin):
        """Control green, orphan RED: C1's 6 Oct purchase 100 new + 200 reinvested and a deposit of 300 on 5 Oct, C2's 500 new + 100 reinvested — today C1 300 + 0 and no deposit on 5 Oct, C2 400 + 200."""
        print_section(f"V-3 cash legs — funding and deposits ({case}, {origin})")
        user = await _cash_book(session, case, origin)

        observed = await _cash_series(session, user)
        for part, view in observed.items():
            print(f"{part}: {view}")

        assert observed == CASH_SERIES[case]
        print_success(f"V-3 cash legs {case} {origin}: the series of the standalone row")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("origin", _CASH_ORIGINS)
    @pytest.mark.parametrize("case", _CASH_CASE_IDS)
    async def test_capital_and_pnl_do_not_move_once_the_other_broker_is_deleted(self, session, case, origin):
        """Guard, green today and after N1b-1: an orphan cash leg already counts as an external flow (classifier.py:96-107), like the DEPOSIT or WITHDRAWAL it becomes."""
        print_section(f"V-3 cash legs — capital and P&L ({case}, {origin})")
        user = await _cash_book(session, case, origin)

        observed = await _cash_totals(session, user)
        print(f"totals: {observed}")

        assert observed == CASH_TOTALS[case]
        print_success(f"V-3 cash legs {case} {origin}: capital and P&L as with the standalone row")
