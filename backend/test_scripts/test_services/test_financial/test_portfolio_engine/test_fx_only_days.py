"""RED tests for lot CP-6: a day on which only a term of the valuation moves is evaluated again (B11, decision 28).

Decision 28 (developer, 15/10): «bisogna ricalcolare ogni volta che cambia uno dei termini della
formula» — recompute whenever any term of the formula changes.

The defect (``DailyStateBuilder.build``, frame loop, @ 63e0374a3). The frame evaluates the "dirty"
days only and copies the previous state on every other day. A day is dirty for its cash deltas, its
position transactions, the external and internal flows, the rate-change days of foreign CASH
(``NativeCash.rate_change_days``), the in-transit edges, a market close different from the previous
close, the splits and ``frame_start`` (J1: one replay from the first movement, states from
``date_from``; that last seed is now the first replayed day, ``date_from`` and the period's start).
But a day also reads, at its own date:

- the exact-day rate of a security's currency in ``fx_rate_map`` (``_market_value_for``; the fx part
  of ``_add_unrealized_part``);
- the exact-day rate of the cash in transit (``_compute_in_transit`` -> ``_convert``);
- the mark of ``AssetPriceSeries``: the latest observation, market or trade. A market quote equal to
  the previous market close still changes the mark when a trade set it in between, and a new quote
  resets the price's age.

A day on which only one of those terms moves is a stale copy of the day before, while
``position_states_end`` is valued afresh at ``date_to``: the summary and the broker card are right,
the daily lines are not (devWiki ``problems/dirty-days-ignore-fx-only-moves``).

The fix the RED tests are written for (CP-6):

1. a frame day is dirty when, for a currency the engine reads every day from ``fx_rate_map`` (the
   non-report currencies of the ``price_map`` prices and of ``asset_currencies``), the exact-day rate
   differs from the previous day's — a rate that appears or disappears counts; likewise, inside each
   cash in-transit interval, for its departure currency;
2. every frame day with a market quote in ``price_map`` is dirty;
3. ``native_cash.change_days(read, currencies, days)``, public and pure: the days of the calendar on
   which ``read`` gives a currency a value different from the calendar's previous day (None before
   the first day). ``NativeCash`` reads it with its last-known rate, the engine with the exact day.

Notation: report currency EUR; brokers A = 10 and B = 20; X = 100 is quoted in USD, Y = 200 in EUR,
Z = 300 in USD; D1 = 2025-01-01 ... D5 = 2025-01-05 ("day k" of the plan is Dk). Rates are exact-day
``(currency, "EUR", day)`` entries of ``fx_rate_map``: a day that is not listed has no rate. Each RED
test quotes, as "Today", what the builder gives before the fix.

The securities are bought with EUR: a purchase settled in USD makes ``NativeCash`` hold USD, and
every USD rate change is then already a dirty day (lot 41 F) — the defect would not show.

Pure tests — no DB, no server. The helpers are copies of test_foreign_cash_revaluation.py and
test_broker_internal_flows.py (this directory has no cross-test-module imports).
``native_cash.change_days`` does not exist before the fix: it is read as
``native_cash_module.change_days`` inside each test, never imported at module level, so this file
collects and its other tests run; until the fix, those tests fail with an AttributeError.
"""

import dataclasses
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.services.financial_math import native_cash as native_cash_module
from backend.app.services.financial_math.native_cash import CashMovement, NativeCash
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState, PortfolioCalculationResult, UnrealizedSplit
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.app.services.platform.data_quality_thresholds import STALE_PRICE_THRESHOLD_DAYS
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A, B = 10, 20
X, Y, Z = 100, 200, 300

D1 = date(2025, 1, 1)
D2 = date(2025, 1, 2)
D3 = date(2025, 1, 3)
D4 = date(2025, 1, 4)
D5 = date(2025, 1, 5)
CALENDAR = (D1, D2, D3, D4, D5)

# R7: the first day on which a price quoted on D1 and carried is older than the threshold, and the day after it.
STALE_DAY = D1 + timedelta(days=STALE_PRICE_THRESHOLD_DAYS + 1)
REQUOTE_DAY = STALE_DAY + timedelta(days=1)

# =============================================================================
# HELPERS — copies of test_foreign_cash_revaluation.py and test_broker_internal_flows.py
# =============================================================================


def _tx(
    *,
    id: int = 1,
    broker_id: int = A,
    type: str = "DEPOSIT",
    dt: date = D1,
    amount: str = "0",
    currency: str | None = "EUR",
    quantity: str = "0",
    asset_id: int | None = None,
    related_id: int | None = None,
    cost_basis_override: str | None = None,
    cost_basis_currency: str | None = None,
) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.broker_id = broker_id
    tx.type = TransactionType(type)
    tx.date = dt
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = related_id
    tx.cost_basis_override = Decimal(cost_basis_override) if cost_basis_override else None
    tx.cost_basis_currency = cost_basis_currency
    return tx


def _mark_series_from(classified_txs, price_map, asset_currencies, quote_base_map=None, split_linked_tx_ids=None):
    """Mirror PortfolioCalculationEngine: one AssetPriceSeries per asset from prices + trades."""
    txs_by_asset: dict[int, list] = {}
    for ctxn in classified_txs:
        tx = ctxn.tx
        if tx.asset_id is not None:
            txs_by_asset.setdefault(tx.asset_id, []).append(tx)
    mark_series = {}
    for aid in set(txs_by_asset) | set(price_map or {}):
        series = build_asset_price_series(
            price_rows=(price_map or {}).get(aid, []),
            transactions=txs_by_asset.get(aid, []),
            split_linked_tx_ids=split_linked_tx_ids or set(),
            asset_currency=(asset_currencies or {}).get(aid, "EUR"),
            quote_base_quantity=(quote_base_map or {}).get(aid) or 1,
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _builder_kwargs(**overrides) -> dict:
    """The kwargs DailyStateBuilder gets: defaults, overrides, then the mark series, average costs
    and native cash computed as ``calculate()`` would, from the builder's own rate map."""
    defaults = {
        "classified_txs": [],
        "in_transit_intervals": [],
        "external_cash_flows": [],
        "price_map": {},
        "quote_base_map": {},
        "asset_currencies": {},
        "fx_rate_map": {},
        "asset_classifications": {},
        "asset_types": {},
        "target_currency": "EUR",
        "date_from": D1,
        "date_to": D1,
    }
    defaults.update(overrides)
    if "mark_series" not in defaults:
        defaults["mark_series"] = _mark_series_from(
            defaults["classified_txs"],
            defaults["price_map"],
            defaults["asset_currencies"],
            defaults["quote_base_map"],
            defaults.get("split_linked_tx_ids"),
        )
    if "average_costs" not in defaults:
        defaults["average_costs"] = engine_average_costs(
            defaults["classified_txs"],
            asset_currencies=defaults["asset_currencies"],
            target_currency=defaults["target_currency"],
            fx_rate_map=defaults["fx_rate_map"],
            split_linked_tx_ids=defaults.get("split_linked_tx_ids"),
            date_to=defaults["date_to"],
        )
    if "native_cash" not in defaults:
        defaults["native_cash"] = engine_native_cash(
            defaults["classified_txs"],
            target_currency=defaults["target_currency"],
            fx_rate_map=defaults["fx_rate_map"],
            date_to=defaults["date_to"],
        )
    return defaults


def _build(**overrides) -> PortfolioCalculationResult:
    return DailyStateBuilder(**_builder_kwargs(**overrides)).build()


def _transfer_pair(out_id: int, in_id: int, *, sender: int, receiver: int, out_dt: date, in_dt: date, qty: str, asset_id: int = X) -> tuple[MagicMock, MagicMock]:
    """Two linked security legs: -qty on the sender, +qty on the receiver, amount 0, no currency."""
    common = {"type": "TRANSFER", "amount": "0", "currency": None, "asset_id": asset_id}
    out_leg = _tx(id=out_id, broker_id=sender, dt=out_dt, quantity=f"-{qty}", related_id=in_id, **common)
    in_leg = _tx(id=in_id, broker_id=receiver, dt=in_dt, quantity=qty, related_id=out_id, **common)
    return out_leg, in_leg


def _cash_pair(out_id: int, in_id: int, *, sender: int, receiver: int, out_dt: date, in_dt: date, amount: str, currency: str) -> tuple[MagicMock, MagicMock]:
    """Two linked CASH_TRANSFER legs: -amount on the sender, +amount on the receiver, same currency."""
    out_leg = _tx(id=out_id, broker_id=sender, type="CASH_TRANSFER", dt=out_dt, amount=f"-{amount}", currency=currency, related_id=in_id)
    in_leg = _tx(id=in_id, broker_id=receiver, type="CASH_TRANSFER", dt=in_dt, amount=amount, currency=currency, related_id=out_id)
    return out_leg, in_leg


def _rates(currency: str, rates: dict[date, str]) -> dict[tuple[str, str, date], Decimal]:
    """``currency``->EUR on the given days only (the map is exact-day: any other day has no rate)."""
    return {(currency, "EUR", day): Decimal(rate) for day, rate in rates.items()}


def _usd_rates(rates: dict[date, str]) -> dict[tuple[str, str, date], Decimal]:
    return _rates("USD", rates)


def _quotes(asset_id: int, currency: str, closes: dict[date, str]) -> dict[int, list[tuple[date, Decimal, str]]]:
    """The market quotes (``price_map`` rows) of one asset: a close in ``currency`` on each given day."""
    return {asset_id: [(day, Decimal(close), currency) for day, close in sorted(closes.items())]}


def _days(first: date, last: date) -> tuple[date, ...]:
    return tuple(first + timedelta(days=offset) for offset in range((last - first).days + 1))


def _classify(txs, scope):
    """Run the real classifier, transactions in loading order (date, id), every broker at share 1."""
    classifier = ScopeAwareTransactionClassifier(
        scope_broker_ids=set(scope),
        all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)),
        broker_shares=dict.fromkeys(scope, Decimal("1")),
    )
    return classifier.classify()


def _overrides(classification, *, date_to: date, price_map=None, fx_rate_map=None, asset_currencies=None) -> dict:
    """Builder kwargs for a classified scenario from D1; every asset is a "Stock" with no
    classification, quoted in EUR unless ``asset_currencies`` says otherwise."""
    price_map = price_map or {}
    asset_ids = {ctxn.tx.asset_id for ctxn in classification.classified if ctxn.tx.asset_id is not None} | set(price_map)
    return {
        "classified_txs": classification.classified,
        "in_transit_intervals": classification.in_transit_intervals,
        "external_cash_flows": classification.external_cash_flows,
        "price_map": price_map,
        "fx_rate_map": fx_rate_map or {},
        "asset_currencies": dict.fromkeys(asset_ids, "EUR") | (asset_currencies or {}),
        "asset_types": dict.fromkeys(asset_ids, "Stock"),
        "asset_classifications": dict.fromkeys(asset_ids),
        "date_from": D1,
        "date_to": date_to,
    }


# =============================================================================
# EXPECTATION CHECKERS — collect every mismatch, so a red shows the whole picture at once
# =============================================================================


def _states(result: PortfolioCalculationResult) -> dict[date, DailyPortfolioState]:
    return {s.date: s for s in result.daily_states}


def _wanted(value):
    """An expected value: a string is a Decimal, anything else is compared as it is."""
    return Decimal(value) if isinstance(value, str) else value


def _state_problems(result: PortfolioCalculationResult, expected: dict[date, dict[str, object]]) -> list[str]:
    """``expected``: {day: {DailyPortfolioState field: value}}; Decimals as strings, compared with ==."""
    states = _states(result)
    problems: list[str] = []
    for day, fields in expected.items():
        state = states.get(day)
        if state is None:
            problems.append(f"{day}: no state emitted")
            continue
        problems.extend(f"{day}: {name}={getattr(state, name)}, expected {_wanted(value)}" for name, value in fields.items() if getattr(state, name) != _wanted(value))
    return problems


def _line_problems(result: PortfolioCalculationResult, expected: dict[date, dict[int, dict[str, str]]]) -> list[str]:
    """``expected``: {day: {broker_id: {BrokerDailyContribution field: Decimal string}}}."""
    states = _states(result)
    problems: list[str] = []
    for day, lines in expected.items():
        state = states.get(day)
        if state is None:
            problems.append(f"{day}: no state emitted")
            continue
        for broker_id, fields in lines.items():
            line = state.broker_contributions.get(broker_id)
            if line is None:
                problems.append(f"{day}/broker {broker_id}: no broker contribution")
                continue
            problems.extend(f"{day}/broker {broker_id}: {name}={getattr(line, name)}, expected {value}" for name, value in fields.items() if getattr(line, name) != Decimal(value))
    return problems


_LINE_SUMS = (("nav_contribution", "nav_value"), ("capital_contribution", "cumulative_external_cash_flow"), ("pnl_contribution", "total_pnl"))


def _invariant_problems(result: PortfolioCalculationResult) -> list[str]:
    """The G1a invariant on every day: the broker lines add up to the aggregate, and P_b = V_b - C_b."""
    problems: list[str] = []
    for state in result.daily_states:
        lines = list(state.broker_contributions.values())
        for line_field, state_field in _LINE_SUMS:
            total = sum((getattr(line, line_field) for line in lines), Decimal("0"))
            if total != getattr(state, state_field):
                problems.append(f"{state.date}: sum({line_field})={total} != {state_field}={getattr(state, state_field)}")
        problems.extend(f"{state.date}/broker {line.broker_id}: pnl {line.pnl_contribution} != nav {line.nav_contribution} - capital {line.capital_contribution}" for line in lines if line.pnl_contribution != line.nav_contribution - line.capital_contribution)
    return problems


_STATE_VALUE_FIELDS = tuple(field.name for field in dataclasses.fields(DailyPortfolioState) if field.name != "date")


def _difference_problems(earlier: DailyPortfolioState, later: DailyPortfolioState) -> list[str]:
    """Every field but the date on which ``later`` differs from ``earlier``."""
    return [f"{later.date}: {name}={getattr(later, name)}, on {earlier.date} {getattr(earlier, name)}" for name in _STATE_VALUE_FIELDS if getattr(later, name) != getattr(earlier, name)]


# =============================================================================
# SCENARIOS
# =============================================================================


def _x_bought_with_eur(*, cost: str, rates: dict[date, str], closes: dict[date, str], date_to: date, later: tuple[MagicMock, ...] = ()) -> dict:
    """A deposits ``cost`` EUR on D1 and buys 10 X with it the same day.

    The purchase is settled in EUR, so the book holds no USD cash: ``NativeCash`` has no USD rate
    change day, and a day that moves only the USD rate is dirty for no reason the builder knows today.
    """
    deposit = _tx(id=1, type="DEPOSIT", amount=cost)
    buy = _tx(id=2, type="BUY", amount=f"-{cost}", quantity="10", asset_id=X)
    classification = _classify([deposit, buy, *later], {A})
    return _overrides(classification, date_to=date_to, price_map=_quotes(X, "USD", closes), fx_rate_map=_usd_rates(rates), asset_currencies={X: "USD"})


def _r1_book() -> dict:
    """R1 and R2: 10 X bought for 900 EUR on D1 (100 USD at 0.90), quoted on D1 only; USD 0.90, 0.90, 0.80 on D1-D3."""
    return _x_bought_with_eur(cost="900", rates={D1: "0.90", D2: "0.90", D3: "0.80"}, closes={D1: "100"}, date_to=D3)


def _r7_book(*later: MagicMock) -> dict:
    """R7: 10 X bought for 900 EUR on D1, quoted 100 USD on D1 and again on REQUOTE_DAY; USD 0.90 every day."""
    return _x_bought_with_eur(cost="900", rates=dict.fromkeys(_days(D1, REQUOTE_DAY), "0.90"), closes={D1: "100", REQUOTE_DAY: "100"}, date_to=REQUOTE_DAY, later=later)


def _split(asset: str = "0", fx: str = "0", unsplit: str = "0") -> UnrealizedSplit:
    return UnrealizedSplit(asset=Decimal(asset), fx=Decimal(fx), unsplit=Decimal(unsplit))


# =============================================================================
# R1, R2, R5 — A FOREIGN SECURITY ON A DAY THAT MOVES ONLY ITS RATE
# =============================================================================


class TestForeignSecurityOnAnFxOnlyDay:
    """X is held at A and quoted on D1 only; on D3 nothing happens but the USD rate."""

    def test_r1_the_security_is_valued_at_the_rate_of_the_day(self):
        """R1 — D3 values X at D3's rate: MV = 10 x 100 x 0.80 = 800, NAV 800, P = 800 - 900 = -100, and
        A's line 800 / 900 / -100 (nav / capital / pnl). D1 and D2, at 0.90, are 900.

        Today: D3 is a copy of D2 — MV 900, NAV 900, P 0, A's line 900 / 900 / 0.
        """
        result = _build(**_r1_book())

        at_090 = {"market_value": "900", "nav_value": "900", "total_pnl": "0"}
        problems = [
            *_state_problems(result, {D1: at_090, D2: at_090, D3: {"market_value": "800", "nav_value": "800", "cumulative_external_cash_flow": "900", "total_pnl": "-100"}}),
            *_line_problems(result, {D3: {A: {"nav_contribution": "800", "capital_contribution": "900", "pnl_contribution": "-100"}}}),
            *_invariant_problems(result),
        ]
        assert not problems, "\n".join(problems)

    def test_r2_the_last_daily_state_is_the_valuation_of_the_end_positions(self):
        """R2 — with ``date_to`` = D3, the last daily state's market value is the sum of the market
        values of ``position_states_end`` (what the broker card shows), both at D3's rate: 800.

        Today: the end positions say 800, the last daily state 900 (the copy of D2).
        """
        result = _build(**_r1_book())

        card = sum((ps.market_value for ps in result.position_states_end if ps.market_value is not None), Decimal("0"))
        last = result.daily_states[-1]
        problems = [] if last.date == D3 else [f"last daily state on {last.date}, expected {D3}"]
        if card != Decimal("800"):
            problems.append(f"position_states_end market value {card}, expected 800")
        if last.market_value != card:
            problems.append(f"{last.date}: market_value={last.market_value}, position_states_end market value {card}")
        assert not problems, "\n".join(problems)

    def test_r5_the_fx_part_of_the_unrealized_split_uses_the_rate_of_the_day(self):
        """R5 — 10 X bought for 800 EUR on D1 (100 USD at 0.80: C_T = 800 EUR, C_A = 800 x 1.25 =
        1000 USD), quoted on D1 only; USD 0.80, 0.80, 0.75. On D3 the USD split is
        asset = MV - C_A x r = 750 - 750 = 0, fx = C_A x r - C_T = 750 - 800 = -50, unsplit 0.

        R1's book with a purchase rate whose inverse is a finite decimal: the USD cost of a purchase
        paid in EUR is C_T x (1 / rate), which at 0.90 is 999.9999999999999999999999999, and then no
        part of the split is an exact Decimal.

        Today: D3 is a copy of D2 — MV 800, asset 0, fx 0, unsplit 0.
        """
        result = _build(**_x_bought_with_eur(cost="800", rates={D1: "0.80", D2: "0.80", D3: "0.75"}, closes={D1: "100"}, date_to=D3))

        problems = _state_problems(
            result,
            {
                D2: {"market_value": "800", "unrealized_by_currency": {"USD": _split()}},
                D3: {"market_value": "750", "unrealized_by_currency": {"USD": _split(fx="-50")}},
            },
        )
        assert not problems, "\n".join(problems)


# =============================================================================
# R3, R4 — VALUES IN TRANSIT ON A DAY THAT MOVES ONLY THEIR RATE
# =============================================================================


class TestInTransitOnAnFxOnlyDay:
    """Cash and securities in transit are valued at the rate of each day of the transit.

    The FX-only day is strictly inside the transit: its first day, its last day and the day after it
    are dirty edges already.
    """

    def test_r3_usd_cash_in_transit_at_the_rate_of_the_day(self):
        """R3 — A deposits 1000 USD on D1 and sends them to B the same day; B receives them on D5 (in
        transit D1-D4). USD 0.90, 0.90, 0.80, 0.80: the cash in transit is 900, 900, 800, 800, and NAV
        800 on D3, all of it on A's line (the departure broker).

        Green before the fix too: the transit's own legs are USD cash movements, so ``NativeCash``
        holds USD and D3 is one of its rate-change days (lot 41 F). Kept as the plan's R3: the same
        value must hold after the fix. The in-transit term on its own is R3b.
        """
        deposit = _tx(id=1, type="DEPOSIT", amount="1000", currency="USD")
        out_leg, in_leg = _cash_pair(2, 3, sender=A, receiver=B, out_dt=D1, in_dt=D5, amount="1000", currency="USD")
        classification = _classify([deposit, out_leg, in_leg], {A, B})
        result = _build(**_overrides(classification, date_to=D4, fx_rate_map=_usd_rates({D1: "0.90", D2: "0.90", D3: "0.80", D4: "0.80"})))

        problems = [
            *_state_problems(
                result,
                {
                    D1: {"in_transit_cash_value": "900"},
                    D2: {"in_transit_cash_value": "900"},
                    D3: {"in_transit_cash_value": "800", "nav_value": "800"},
                    D4: {"in_transit_cash_value": "800"},
                },
            ),
            *_line_problems(result, {D3: {A: {"in_transit_contribution": "800"}}}),
            *_invariant_problems(result),
        ]
        assert not problems, "\n".join(problems)

    def test_r3b_cash_in_transit_whose_rate_appears_inside_the_transit(self):
        """R3b — A sends 1000 USD to B on D1, received on D5 (in transit D1-D4), and the USD rates start
        on D3 (0.80 on D3 and D4): D1 and D2 have none. The departure cannot be converted at its own
        date, so it is a missing conversion and ``NativeCash`` holds no USD: on D3 the only term that
        moves is the exact-day rate of the cash in transit (it appears). D3: in transit 1000 x 0.80 =
        800, no missing pair, NAV 800, all of it on A's line (the departure broker). D1 and D2: in
        transit 0, USD/EUR missing. D4, the transit's last day, is dirty already: 800.

        Today: D3 is a copy of D2 — in transit 0, missing {USD/EUR}, NAV 0.
        """
        out_leg, in_leg = _cash_pair(1, 2, sender=A, receiver=B, out_dt=D1, in_dt=D5, amount="1000", currency="USD")
        classification = _classify([out_leg, in_leg], {A, B})
        result = _build(**_overrides(classification, date_to=D4, fx_rate_map=_usd_rates({D3: "0.80", D4: "0.80"})))

        no_rate = {"in_transit_cash_value": "0", "missing_fx_pairs": {"USD/EUR"}}
        at_080 = {"in_transit_cash_value": "800", "missing_fx_pairs": set(), "nav_value": "800"}
        problems = [
            *_state_problems(result, {D1: no_rate, D2: no_rate, D3: at_080, D4: at_080}),
            *_line_problems(result, {D3: {A: {"in_transit_contribution": "800", "nav_contribution": "800"}}}),
            *_invariant_problems(result),
        ]
        assert not problems, "\n".join(problems)

    def test_r4_a_security_in_transit_at_the_rate_of_the_day(self):
        """R4 — 10 X bought for 900 EUR at A on D1 (quoted 100 USD on D1 only), sent to B on D2 and
        received on D5 (in transit D2-D4); USD 0.90, 0.90, 0.80, 0.80, 0.80. D3 moves only the rate,
        with no quote: the X in transit is worth 10 x 100 x 0.80 = 800, NAV 800, on A's line
        (800 / 900 / -100). D2, at 0.90, is 900; D4, the transit's last day, is dirty already: 800.

        Today: D3 is a copy of D2 — 900 in transit, NAV 900, A's line 900 / 900 / 0.
        """
        deposit = _tx(id=1, type="DEPOSIT", amount="900")
        buy = _tx(id=2, type="BUY", amount="-900", quantity="10", asset_id=X)
        out_leg, in_leg = _transfer_pair(3, 4, sender=A, receiver=B, out_dt=D2, in_dt=D5, qty="10")
        classification = _classify([deposit, buy, out_leg, in_leg], {A, B})
        rates = _usd_rates({D1: "0.90", D2: "0.90", D3: "0.80", D4: "0.80", D5: "0.80"})
        result = _build(**_overrides(classification, date_to=D4, price_map=_quotes(X, "USD", {D1: "100"}), fx_rate_map=rates, asset_currencies={X: "USD"}))

        problems = [
            *_state_problems(
                result,
                {
                    D2: {"in_transit_asset_market_value": "900", "nav_value": "900"},
                    D3: {"in_transit_asset_market_value": "800", "nav_value": "800"},
                    D4: {"in_transit_asset_market_value": "800", "nav_value": "800"},
                },
            ),
            *_line_problems(result, {D3: {A: {"in_transit_contribution": "800", "nav_contribution": "800", "capital_contribution": "900", "pnl_contribution": "-100"}}}),
            *_invariant_problems(result),
        ]
        assert not problems, "\n".join(problems)


# =============================================================================
# R6, R7 — A MARKET QUOTE EQUAL TO THE PREVIOUS CLOSE IS STILL A NEW TERM
# =============================================================================


class TestMarketQuoteDays:
    """The mark is the latest observation, market or trade, and its age is part of the day."""

    def test_r6_a_quote_equal_to_the_last_close_replaces_the_trade_mark(self):
        """R6 — X quoted 100 USD on D1 and 100 again on D3; on D2 A deposits 1050 USD and buys 10 X at
        105 USD (a trade mark); USD 0.90 every day. D2 values X at the trade: 10 x 105 x 0.90 = 945,
        transaction-implied (last quote D1). D3 values it at the market again: 10 x 100 x 0.90 = 900,
        NAV 900, not implied.

        Today: D3's close equals D1's, so D3 is a copy of D2 — 945, NAV 945, implied {X} (last quote D1).
        """
        deposit = _tx(id=1, type="DEPOSIT", dt=D2, amount="1050", currency="USD")
        buy = _tx(id=2, type="BUY", dt=D2, amount="-1050", currency="USD", quantity="10", asset_id=X)
        classification = _classify([deposit, buy], {A})
        rates = _usd_rates(dict.fromkeys(CALENDAR[:3], "0.90"))
        result = _build(**_overrides(classification, date_to=D3, price_map=_quotes(X, "USD", {D1: "100", D3: "100"}), fx_rate_map=rates, asset_currencies={X: "USD"}))

        problems = _state_problems(
            result,
            {
                D2: {"market_value": "945", "nav_value": "945", "transaction_implied_asset_ids": {X}, "transaction_implied_last_quote_dates": {X: D1}},
                D3: {"market_value": "900", "nav_value": "900", "transaction_implied_asset_ids": set(), "transaction_implied_last_quote_dates": {}},
            },
        )
        assert not problems, "\n".join(problems)

    def test_r7_the_price_turns_stale_with_age_and_a_new_quote_makes_it_fresh(self):
        """R7 — X quoted 100 USD on D1 and 100 again on REQUOTE_DAY, nothing else happening (USD 0.90
        every day). STALE_DAY = D1 + STALE_PRICE_THRESHOLD_DAYS + 1 is the first day the carried price
        is older than the threshold: X is stale there. On REQUOTE_DAY the new quote is fresh.

        Today: every day after D1 is a copy of D1, where the price was fresh: X is never stale, neither
        on STALE_DAY nor on REQUOTE_DAY.

        Rate days and quote days do not reach STALE_DAY, where only the price's age moves: this test
        stays red until the first stale day of a carried mark is a dirty day too.
        """
        result = _build(**_r7_book())

        problems = _state_problems(result, {STALE_DAY: {"stale_price_asset_ids": {X}}, REQUOTE_DAY: {"stale_price_asset_ids": set()}})
        assert not problems, "\n".join(problems)

    def test_r7b_a_new_quote_equal_to_the_last_close_resets_the_age(self):
        """R7b — R7 with a 100 EUR deposit at A on STALE_DAY, which evaluates that day: X is stale there
        (its price is STALE_PRICE_THRESHOLD_DAYS + 1 days old). On REQUOTE_DAY the quote equals the last
        close, but it is new: X is fresh.

        Today: REQUOTE_DAY's close equals D1's, so REQUOTE_DAY is a copy of STALE_DAY — X still stale.
        """
        result = _build(**_r7_book(_tx(id=3, type="DEPOSIT", dt=STALE_DAY, amount="100")))

        problems = _state_problems(result, {STALE_DAY: {"stale_price_asset_ids": {X}}, REQUOTE_DAY: {"stale_price_asset_ids": set()}})
        assert not problems, "\n".join(problems)


# =============================================================================
# GUARDS — green before the fix and after it
# =============================================================================


class TestGuards:
    """Days whose terms do not move, or whose every term is already a dirty-day source, keep their values."""

    def test_guard_a_book_of_eur_securities_every_day(self):
        """A deposits 1000 EUR and buys 10 Y (EUR) for 500 EUR on D1; Y closes 50, 50, 55, -, 52 on D1-D5:
        D2 repeats D1's close, D4 carries D3's. Every day by hand: cash 500, capital 1000, cost 500,
        MV 500, 500, 550, 550, 520, NAV = MV + 500, P = unrealized = MV - 500, all of it the EUR
        split's asset part; no stale, implied or missing data.
        """
        deposit = _tx(id=1, type="DEPOSIT", amount="1000")
        buy = _tx(id=2, type="BUY", amount="-500", quantity="10", asset_id=Y)
        classification = _classify([deposit, buy], {A})
        result = _build(**_overrides(classification, date_to=D5, price_map=_quotes(Y, "EUR", {D1: "50", D2: "50", D3: "55", D5: "52"})))

        rows = {D1: ("500", "1000", "0"), D2: ("500", "1000", "0"), D3: ("550", "1050", "50"), D4: ("550", "1050", "50"), D5: ("520", "1020", "20")}
        expected = {
            day: {
                "cash_value": "500",
                "market_value": market_value,
                "nav_value": nav,
                "cumulative_external_cash_flow": "1000",
                "open_cost_basis": "500",
                "unrealized_gain_loss": pnl,
                "total_pnl": pnl,
                "unrealized_by_currency": {"EUR": _split(asset=pnl)},
                "stale_price_asset_ids": set(),
                "transaction_implied_asset_ids": set(),
                "missing_price_asset_ids": set(),
                "missing_fx_pairs": set(),
            }
            for day, (market_value, nav, pnl) in rows.items()
        }
        problems = [*_state_problems(result, expected), *_invariant_problems(result)]
        assert not problems, "\n".join(problems)

    def test_guard_a_usd_security_with_a_new_quote_every_day(self):
        """10 X bought for 800 EUR on D1 (100 USD at 0.80: C_T 800 EUR, C_A 1000 USD); X closes 100, 101,
        102, 103, 104 USD and USD is 0.80, 0.80, 0.75, 0.78, 0.78 on D1-D5. Every day is dirty already
        (a new close), so every day by hand: cash 0, capital 800, MV = NAV = 800, 808, 765, 803.4,
        811.2, P = MV - 800, and the USD split asset = MV - 1000 x r, fx = 1000 x r - 800.
        """
        result = _build(**_x_bought_with_eur(cost="800", rates={D1: "0.80", D2: "0.80", D3: "0.75", D4: "0.78", D5: "0.78"}, closes={D1: "100", D2: "101", D3: "102", D4: "103", D5: "104"}, date_to=D5))

        rows = {D1: ("800", "0", "0", "0"), D2: ("808", "8", "8", "0"), D3: ("765", "-35", "15", "-50"), D4: ("803.4", "3.4", "23.4", "-20"), D5: ("811.2", "11.2", "31.2", "-20")}
        expected = {
            day: {
                "cash_value": "0",
                "market_value": market_value,
                "nav_value": market_value,
                "cumulative_external_cash_flow": "800",
                "open_cost_basis": "800",
                "total_pnl": pnl,
                "unrealized_by_currency": {"USD": _split(asset=asset, fx=fx)},
                "stale_price_asset_ids": set(),
                "transaction_implied_asset_ids": set(),
                "missing_fx_pairs": set(),
            }
            for day, (market_value, pnl, asset, fx) in rows.items()
        }
        problems = [*_state_problems(result, expected), *_invariant_problems(result)]
        assert not problems, "\n".join(problems)

    def test_guard_an_fx_only_day_of_a_currency_not_held_changes_nothing(self):
        """A deposits 1000 EUR and on D1 buys 10 Y (EUR, closes 50 on D1 only) for 500 EUR and 5 Z (USD)
        for 400 EUR; on D2 it sells the 5 Z for 400 EUR. USD is 0.80 on D1-D3 and 0.75 on D4-D5; GBP,
        never held, 1.20 on D1-D3 and 1.10 on D4-D5. D4 moves only rates of currencies the book does not
        hold (USD is still an asset currency, so the fix may evaluate D4 again): D4 equals D3, and D5
        equals D4, on every field but the date. D3: cash 500, MV 500, NAV 1000, P 0.
        """
        deposit = _tx(id=1, type="DEPOSIT", amount="1000")
        buy_y = _tx(id=2, type="BUY", amount="-500", quantity="10", asset_id=Y)
        buy_z = _tx(id=3, type="BUY", amount="-400", quantity="5", asset_id=Z)
        sell_z = _tx(id=4, type="SELL", dt=D2, amount="400", quantity="-5", asset_id=Z)
        classification = _classify([deposit, buy_y, buy_z, sell_z], {A})
        price_map = _quotes(Y, "EUR", {D1: "50"}) | _quotes(Z, "USD", {D1: "100", D2: "100"})
        rates = _usd_rates({D1: "0.80", D2: "0.80", D3: "0.80", D4: "0.75", D5: "0.75"}) | _rates("GBP", {D1: "1.20", D2: "1.20", D3: "1.20", D4: "1.10", D5: "1.10"})
        result = _build(**_overrides(classification, date_to=D5, price_map=price_map, fx_rate_map=rates, asset_currencies={Z: "USD"}))

        states = _states(result)
        problems = [
            *_state_problems(result, {D3: {"cash_value": "500", "market_value": "500", "nav_value": "1000", "total_pnl": "0"}}),
            *_difference_problems(states[D3], states[D4]),
            *_difference_problems(states[D4], states[D5]),
            *_invariant_problems(result),
        ]
        assert not problems, "\n".join(problems)


# =============================================================================
# native_cash.change_days — the one pure function for both readings
# =============================================================================


def _points(rates: dict[tuple[str, date], str]) -> dict[tuple[str, date], Decimal]:
    return {key: Decimal(rate) for key, rate in rates.items()}


def _exact_day(rates: dict[tuple[str, date], str]):
    """The engine's reading: the rate of exactly that day, None when the day has none."""
    points = _points(rates)

    def read(currency: str, day: date) -> Decimal | None:
        return points.get((currency, day))

    return read


def _last_known(rates: dict[tuple[str, date], str]):
    """The cash's reading: the latest rate on or before the day, None before the first one."""
    points = sorted(_points(rates).items())

    def read(currency: str, day: date) -> Decimal | None:
        known = [rate for (point_currency, point_day), rate in points if point_currency == currency and point_day <= day]
        return known[-1] if known else None

    return read


_USD_WITH_A_GAP = {("USD", D1): "0.90", ("USD", D2): "0.90", ("USD", D4): "0.90", ("USD", D5): "0.90"}


class TestChangeDays:
    """``change_days(read, currencies, days)``: the calendar days on which ``read`` gives a currency of
    ``currencies`` a value different from the calendar's previous day, None before the first day.

    Red before the fix on the missing attribute: ``native_cash`` has no ``change_days`` yet.
    """

    def test_exact_day_reading_counts_the_day_a_rate_disappears_and_the_day_it_comes_back(self):
        """USD 0.90 on D1, D2, D4, D5 and nothing on D3: the exact-day reading changes on D1 (first
        day, None before), on D3 (0.90 -> None) and on D4 (None -> 0.90)."""
        change_days = native_cash_module.change_days

        assert change_days(_exact_day(_USD_WITH_A_GAP), {"USD"}, CALENDAR) == (D1, D3, D4)

    def test_last_known_reading_sees_no_change_across_a_gap(self):
        """The same rates read as the cash reads them: D3 carries D2's 0.90, so only D1 changes."""
        change_days = native_cash_module.change_days

        assert change_days(_last_known(_USD_WITH_A_GAP), {"USD"}, CALENDAR) == (D1,)

    def test_a_rate_present_on_the_first_calendar_day_counts(self):
        """USD 0.90 every day, calendar D2-D4: D2 counts (None before the calendar), D3 and D4 do not."""
        change_days = native_cash_module.change_days
        flat = {("USD", day): "0.90" for day in CALENDAR}

        assert change_days(_exact_day(flat), {"USD"}, (D2, D3, D4)) == (D2,)

    def test_a_rate_absent_on_the_first_calendar_day_is_no_change(self):
        """USD 0.90 on D2 and D3 only, calendar D1-D3: D1 reads None as the day before it, so it is no
        change; D2 is (the rate appears)."""
        change_days = native_cash_module.change_days

        assert change_days(_exact_day({("USD", D2): "0.90", ("USD", D3): "0.90"}), {"USD"}, (D1, D2, D3)) == (D2,)

    def test_the_change_days_of_several_currencies_are_merged_sorted_and_unique(self):
        """USD 0.90, 0.90, 0.80, 0.85, 0.85 changes on D1, D3, D4; GBP, from D2, 1.20, 1.20, 1.10, 1.10
        on D2, D4: together D1, D2, D3, D4, in calendar order, D4 once."""
        change_days = native_cash_module.change_days
        usd = {("USD", day): rate for day, rate in zip(CALENDAR, ("0.90", "0.90", "0.80", "0.85", "0.85"), strict=True)}
        gbp = {("GBP", day): rate for day, rate in zip(CALENDAR[1:], ("1.20", "1.20", "1.10", "1.10"), strict=True)}

        assert change_days(_exact_day(usd | gbp), {"USD", "GBP"}, CALENDAR) == (D1, D2, D3, D4)

    def test_a_currency_outside_the_set_is_ignored(self):
        """CHF moves on D2 and D3, but only USD (0.90 every day) is asked: only D1 changes."""
        change_days = native_cash_module.change_days
        rates = {("USD", day): "0.90" for day in CALENDAR} | {("CHF", D1): "1.05", ("CHF", D2): "1.10", ("CHF", D3): "1.05"}

        assert change_days(_exact_day(rates), {"USD"}, CALENDAR) == (D1,)

    def test_last_known_reading_on_the_rate_points_keeps_rate_change_days(self):
        """``NativeCash`` keeps its rate-change days when it reads them through ``change_days``, with its
        last-known rate on the calendar of its rate points. A holds USD (0.90 on D1, 0.95 on D3 and D4),
        B holds GBP (1.20 on D2, 1.25 on D4); CHF has rates but no cash. Today's answer: D1, D2, D3, D4.
        """
        change_days = native_cash_module.change_days
        rates = {("USD", D1): "0.90", ("USD", D3): "0.95", ("USD", D4): "0.95", ("GBP", D2): "1.20", ("GBP", D4): "1.25", ("CHF", D3): "1.05"}
        movements = (
            CashMovement(movement_id=1, transaction_type="DEPOSIT", date=D1, broker_id=A, asset_id=None, currency="USD", amount=Decimal("1000")),
            CashMovement(movement_id=2, transaction_type="DEPOSIT", date=D2, broker_id=B, asset_id=None, currency="GBP", amount=Decimal("100")),
        )
        cash = NativeCash(report_currency="EUR", movements=movements, converted=(Decimal("900"), Decimal("120")), unit_rates=_points(rates))
        rate_points = tuple(sorted({day for _currency, day in rates}))

        assert cash.rate_change_days(None, D5) == (D1, D2, D3, D4)
        assert change_days(_last_known(rates), {"USD", "GBP"}, rate_points) == cash.rate_change_days(None, D5)
