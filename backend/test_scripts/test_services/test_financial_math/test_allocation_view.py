"""Lane 80, lot ALF-B1b — the filtered allocation view of the «Allocazione» tab (``portfolio/allocation_view.py``).

The contract (``allocation_view``'s docstring, the consultant's answers in the lane's analysis §12):

- the total is the NAV, and ``base + outside + excluded = NAV`` on every view;
- «outside» is only what the class filter leaves out (an asset's class is ``type_rules.asset_type_content``: «solo
  azioni» takes ETF_STOCK too), the cash included when Liquidity is off;
- «excluded» holds the user's rows (an asset whole, an asset's part in ``Unknown``/``Other`` where the bucket exists)
  and the unattributable ones (the securities in transit, always; the cash in the geography when Liquidity is on);
- the filters apply class → excluded asset → excluded bucket, and an amount counts once;
- the matrix is the whole portfolio, whatever the filters, and adds up to the NAV with its unattributed amounts; the
  asset dimension has none;
- shares from ``weights.slice_percents`` and ``percent_of`` only, to 0.01; a base at or below zero has no share.

What is tested:

1. ``TestNoFilterIsTodaysAllocation`` — on the engine's book of ``test_asset_allocation.py`` (an asset on two brokers,
   a security and some cash in transit, an asset never valued, profiles with ``Other``, a profile step inside the
   window), with real asset types: in every dimension the view of each day and its history are today's
   ``build_allocation_current``/``build_allocation_history`` (and the asset views): the same keys, amounts and
   shares, the same steps.
2. ``TestTheIdentity`` — base + outside + excluded = NAV on every day of the book, for several filters; the matrix
   adds up to the NAV; the in-transit security is unattributable in every dimension.
3. ``TestTheFilters`` — hand-made states: «solo azioni», the cash in the geography, an excluded bucket, a bucket
   that does not exist in the dimension, an excluded asset, an asset both off and excluded, negative cash, a base at
   or below zero, the scope lists, the matrix rows, an empty view, an invalid bucket.
4. ``TestTheHistory`` — the selection in steps: a profile step opens a step on its own day, the base of a step is the
   sum of its components, a filtered history leaves the class out.

Pure: the builder fed by hand and hand-made states, no database, no server. Amounts in the books are short decimals,
so every identity is exact (``==``), not within a tolerance.

RED on HEAD c539c2d30, by absence: ``financial_math.portfolio.allocation_view`` does not exist (``ImportError`` at
collection).

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from functools import cache

import pytest

from backend.app.services.financial_math.portfolio.allocation_view import (
    LIQUIDITY,
    MATRIX_DIMENSIONS,
    AllocationDimension,
    AllocationFilters,
    AllocationView,
    UnattributableReason,
    build_allocation_view,
)
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState, DailyStates, PortfolioCalculationResult, StateSegment
from backend.test_scripts.test_services.test_financial_math.test_asset_allocation import (
    BOOK_FROM,
    BOOK_TO,
    GEO_1,
    GEO_2,
    QUIET_06,
    QUIET_18,
    G,
    W,
    X,
    _book,
    _builder_kwargs,
    _classifications,
    _days,
    _steps,
    _whole,
)

ZERO = Decimal("0")
ALL_DIMENSIONS = list(AllocationDimension)
#: Real types for the book: X an equity ETF, W a share, G a bond (never valued: no GBP rate)
TYPES = {X: "ETF_STOCK", W: "STOCK", G: "BOND"}
NAMES = {X: "Alpha ETF", W: "Omega"}
#: A day with X in transit from A to B (04-07 → 04-10) and one with cash in transit (04-12 → 04-15)
SECURITY_IN_TRANSIT, CASH_IN_TRANSIT = date(2025, 4, 8), date(2025, 4, 13)


# =============================================================================
# The engine's book
# =============================================================================


def _classifications_with_a_step() -> dict:
    """X's geography changes on QUIET_18 (GEO_1 → GEO_2, whose «Other» becomes Unknown); its sector is SECTOR_1."""
    return _classifications(_steps((BOOK_FROM, QUIET_18 - timedelta(days=1), GEO_1), (QUIET_18, BOOK_TO, GEO_2)))


@cache
def _result() -> PortfolioCalculationResult:
    book = _book()
    book["asset_types"] = dict(TYPES)
    book["asset_classifications"] = _classifications_with_a_step()
    return DailyStateBuilder(**_builder_kwargs(**book, date_from=BOOK_FROM)).build()


def _view(states, dimension, filters=None, *, include_history=False, date_from=None) -> AllocationView:
    result = _result()
    return build_allocation_view(
        states,
        asset_types=result.asset_types,
        asset_classifications=result.asset_classifications,
        dimension=dimension,
        filters=filters,
        date_from=date_from,
        include_history=include_history,
        names=NAMES,
    )


def _states_through(day: date) -> list[DailyPortfolioState]:
    """The book's states up to ``day``: a view of them is the view of ``day``."""
    return [_result().daily_states.state_on(d) for d in _days(BOOK_FROM, day)]


def _todays_current(states, dimension: AllocationDimension) -> list[dict]:
    builder = DerivedViewsBuilder(states, "EUR")
    if dimension is AllocationDimension.ASSET:
        return builder.build_asset_allocation_current(NAMES)
    by_type, by_sector, by_geography = builder.build_allocation_current()
    return {AllocationDimension.TYPE: by_type, AllocationDimension.SECTOR: by_sector, AllocationDimension.GEOGRAPHY: by_geography}[dimension]


def _slice_rows(view: AllocationView) -> list[tuple]:
    """(key, amount, share) of each slice, in order, keyed as today's views name them."""
    rows = []
    for item in view.slices:
        key = item.key if view.dimension is not AllocationDimension.ASSET else (item.asset_id, item.key)
        rows.append((key, item.amount, item.share_of_selection))
    return rows


def _today_rows(items: list[dict], dimension: AllocationDimension) -> list[tuple]:
    if dimension is AllocationDimension.ASSET:
        return [((item["id"], LIQUIDITY if item["id"] is None else str(item["id"])), item["amount"], item["value"]) for item in items]
    return [(item["name"], item["amount"], item["value"]) for item in items]


def _sum_of_view(view: AllocationView) -> Decimal:
    return view.base + view.outside.amount + view.excluded.amount


def _sum_of_matrix(view: AllocationView) -> Decimal:
    assert view.matrix is not None
    return sum((cell.amount for cell in view.matrix.cells), ZERO) + sum((row.amount for row in view.matrix.unattributed), ZERO)


def _unattributable(view: AllocationView) -> dict[UnattributableReason, Decimal]:
    return {row.reason: row.amount for row in view.excluded.unattributable}


class TestNoFilterIsTodaysAllocation:
    def test_preconditions_of_the_book(self):
        result = _result()
        assert result.asset_types == TYPES
        assert X in result.daily_states.state_on(SECURITY_IN_TRANSIT).by_asset
        assert result.daily_states.state_on(SECURITY_IN_TRANSIT).in_transit_asset_market_value > 0, "X is in transit"
        assert result.daily_states.state_on(CASH_IN_TRANSIT).in_transit_cash_value > 0, "cash is in transit"
        assert G not in result.daily_states[-1].by_asset, "G is never valued"

    @pytest.mark.parametrize("dimension", ALL_DIMENSIONS)
    def test_every_day_is_todays_current_allocation(self, dimension):
        for day in _days(date(2025, 4, 2), BOOK_TO):
            states = _states_through(day)
            got = _slice_rows(_view(states, dimension))
            expected = _today_rows(_todays_current(states, dimension), dimension)
            assert got == expected, f"{day} {dimension}: {got} != {expected}"

    @pytest.mark.parametrize("date_from", [BOOK_FROM, QUIET_06, QUIET_18 + timedelta(days=1)], ids=["book-start", "quiet-day", "after-the-profile-step"])
    @pytest.mark.parametrize("dimension", ALL_DIMENSIONS)
    def test_the_history_is_todays_history(self, dimension, date_from):
        """From the book's start, and from a day inside a segment (the period start of a run from t=0, as the report
        asks): the first row then reads a state dated before ``date_from``, and its weights are that segment's."""
        segment_starts = [segment.start for segment in _result().daily_states.segments]
        assert date_from == BOOK_FROM or date_from not in segment_starts, "precondition: a quiet day, the first row is clipped"
        builder = DerivedViewsBuilder(_result().daily_states, "EUR")
        if dimension is AllocationDimension.ASSET:
            expected = builder.build_asset_allocation_history(NAMES, date_from)
        else:
            expected = builder.build_allocation_history(dimension.value, date_from)
        got = _view(_result().daily_states, dimension, include_history=True, date_from=date_from).history
        assert [{key: value for key, value in step.items() if key != "base"} for step in got] == expected
        assert got[0]["date"] == date_from
        assert got, "precondition: the window has steps"


class TestTheIdentity:
    FILTERS = (
        AllocationFilters(),
        AllocationFilters(classes=frozenset({"STOCK"})),
        AllocationFilters(classes=frozenset({"STOCK", LIQUIDITY}), exclude_buckets=frozenset({"Unknown"})),
        AllocationFilters(exclude_asset_ids=frozenset({X}), exclude_buckets=frozenset({"Unknown", "Other"})),
        AllocationFilters(classes=frozenset()),
        AllocationFilters(classes=frozenset({"BOND"}), types=frozenset({"ETF_STOCK"})),
    )

    @pytest.mark.parametrize("dimension", ALL_DIMENSIONS)
    @pytest.mark.parametrize("filters", FILTERS, ids=lambda f: f"classes={sorted(f.classes) if f.classes is not None else None}-types={sorted(f.types)}-ex={sorted(f.exclude_buckets)}-assets={sorted(f.exclude_asset_ids)}")
    def test_base_outside_excluded_is_the_nav_every_day(self, dimension, filters):
        for day in _days(date(2025, 4, 2), BOOK_TO):
            view = _view(_states_through(day), dimension, filters)
            assert view.portfolio_total == _result().daily_states.state_on(day).nav_value
            assert _sum_of_view(view) == view.portfolio_total, f"{day}: {view.base} + {view.outside.amount} + {view.excluded.amount} != {view.portfolio_total}"
            assert view.base == sum((item.amount for item in view.slices), ZERO)
            assert view.outside.amount == sum((row.amount for row in view.outside.by_class), ZERO)

    @pytest.mark.parametrize("dimension", sorted(MATRIX_DIMENSIONS))
    def test_the_matrix_is_the_nav_whatever_the_filters(self, dimension):
        for day in (SECURITY_IN_TRANSIT, CASH_IN_TRANSIT, BOOK_TO):
            states = _states_through(day)
            whole = _view(states, dimension)
            filtered = _view(states, dimension, AllocationFilters(classes=frozenset({"STOCK"}), exclude_asset_ids=frozenset({W})))
            assert _sum_of_matrix(whole) == whole.portfolio_total, f"{day} {dimension}"
            assert filtered.matrix == whole.matrix, "the filters only highlight: the matrix stays the portfolio's"

    @pytest.mark.parametrize("dimension", ALL_DIMENSIONS)
    def test_the_security_in_transit_is_unattributable_in_every_dimension(self, dimension):
        state = _result().daily_states.state_on(SECURITY_IN_TRANSIT)
        for filters in (AllocationFilters(), AllocationFilters(classes=frozenset())):
            view = _view(_states_through(SECURITY_IN_TRANSIT), dimension, filters)
            assert _unattributable(view)[UnattributableReason.IN_TRANSIT] == state.in_transit_asset_market_value, "always, whatever the class filter"
        if dimension in MATRIX_DIMENSIONS:
            assert {row.reason: row.amount for row in view.matrix.unattributed}[UnattributableReason.IN_TRANSIT] == state.in_transit_asset_market_value

    def test_the_cash_in_transit_is_liquidity(self):
        state = _result().daily_states.state_on(CASH_IN_TRANSIT)
        view = _view(_states_through(CASH_IN_TRANSIT), AllocationDimension.SECTOR)
        liquidity = next(item for item in view.slices if item.key == LIQUIDITY)
        assert liquidity.amount == state.cash_value + state.in_transit_cash_value


# =============================================================================
# Hand-made states
# =============================================================================

DAY = date(2025, 4, 18)
ETF, SHARE, BOND, CRYPTO = 1, 2, 3, 4
HAND_TYPES = {ETF: "ETF_STOCK", SHARE: "STOCK", BOND: "ETF_BOND", CRYPTO: "CRYPTO"}


def _state(by_asset: dict[int, str], *, cash: str = "0", in_transit_cash: str = "0", in_transit_asset: str = "0", day: date = DAY) -> DailyPortfolioState:
    """A state with its by_asset, cash and in-transit values; the NAV is their sum, every other figure irrelevant."""
    amounts = {asset_id: Decimal(amount) for asset_id, amount in by_asset.items()}
    market_value = sum(amounts.values(), ZERO)
    cash_value, it_cash, it_asset = Decimal(cash), Decimal(in_transit_cash), Decimal(in_transit_asset)
    nav = market_value + cash_value + it_cash + it_asset
    return DailyPortfolioState(
        date=day,
        cash_value=cash_value,
        market_value=market_value,
        broker_nav_value=market_value + cash_value,
        in_transit_cash_value=it_cash,
        in_transit_asset_market_value=it_asset,
        in_transit_market_value=it_cash + it_asset,
        nav_value=nav,
        open_cost_basis=market_value,
        in_transit_asset_cost_basis=it_asset,
        in_transit_book_value=it_cash + it_asset,
        book_value=nav,
        unrealized_gain_loss=ZERO,
        external_cash_flow=ZERO,
        cumulative_external_cash_flow=nav,
        book_asset_like=market_value,
        cash_from_contributed_capital=cash_value + it_cash,
        cash_from_generated_returns=ZERO,
        total_pnl=ZERO,
        by_asset=amounts,
    )


#: ETF: 60 % USA, 40 % Other (→ Unknown); 70 % Technology, 30 % Other. SHARE: Italy, Utilities. BOND, CRYPTO: no profile
HAND_CLASSIFICATIONS = {
    ETF: {"geography": _whole({"USA": "0.6000", "Other": "0.4000"}), "sector": _whole({"Technology": "0.7000", "Other": "0.3000"})},
    SHARE: {"geography": _whole({"ITA": "1.0000"}), "sector": _whole({"Utilities": "1.0000"})},
    BOND: None,
}


def _hand_view(states, dimension, filters=None, *, include_history=False, date_from=None) -> AllocationView:
    return build_allocation_view(
        states if isinstance(states, list | DailyStates) else [states],
        asset_types=HAND_TYPES,
        asset_classifications=HAND_CLASSIFICATIONS,
        dimension=dimension,
        filters=filters,
        date_from=date_from,
        include_history=include_history,
    )


def _amounts(view: AllocationView) -> dict[str, Decimal]:
    return {item.key: item.amount for item in view.slices}


#: ETF 1000, SHARE 500, BOND 300, CRYPTO 200, cash 100 + 50 in transit, a security of 40 in transit: NAV 2190
PORTFOLIO = _state({ETF: "1000", SHARE: "500", BOND: "300", CRYPTO: "200"}, cash="100", in_transit_cash="50", in_transit_asset="40")


class TestTheFilters:
    def test_only_stocks_takes_the_equity_etf(self):
        view = _hand_view(PORTFOLIO, AllocationDimension.TYPE, AllocationFilters(classes=frozenset({"STOCK"})))
        assert _amounts(view) == {"ETF_STOCK": Decimal("1000"), "STOCK": Decimal("500")}
        assert view.base == Decimal("1500")
        assert {row.asset_class: row.amount for row in view.outside.by_class} == {"BOND": Decimal("300"), "CRYPTO": Decimal("200"), LIQUIDITY: Decimal("150")}
        assert _unattributable(view) == {UnattributableReason.IN_TRANSIT: Decimal("40")}
        assert view.portfolio_total == Decimal("2190") == _sum_of_view(view)
        assert [item.share_of_selection for item in view.slices] == [Decimal("66.67"), Decimal("33.33")]
        assert [item.share_of_portfolio for item in view.slices] == [Decimal("45.66"), Decimal("22.83")]
        assert view.base_share_of_portfolio == Decimal("68.49")

    def test_a_class_kept_in_part_keeps_the_types_named(self):
        """86, D-13: STOCK is not in ``classes``, its ETF_STOCK is in ``types``: the share stays outside, with its class."""
        view = _hand_view(PORTFOLIO, AllocationDimension.TYPE, AllocationFilters(classes=frozenset({"BOND"}), types=frozenset({"ETF_STOCK"})))
        assert _amounts(view) == {"ETF_STOCK": Decimal("1000"), "ETF_BOND": Decimal("300")}
        assert {row.asset_class: row.amount for row in view.outside.by_class} == {"STOCK": Decimal("500"), "CRYPTO": Decimal("200"), LIQUIDITY: Decimal("150")}
        assert view.portfolio_total == _sum_of_view(view)

    def test_a_whole_class_takes_every_type_and_a_type_named_twice_counts_once(self):
        whole = _hand_view(PORTFOLIO, AllocationDimension.SECTOR, AllocationFilters(classes=frozenset({"STOCK"})))
        named = _hand_view(PORTFOLIO, AllocationDimension.SECTOR, AllocationFilters(classes=frozenset({"STOCK"}), types=frozenset({"ETF_STOCK", "STOCK"})))
        assert named == whole

    @pytest.mark.parametrize(
        "filters",
        [AllocationFilters(types=frozenset({"ETF_STOCK"})), AllocationFilters(classes=None, types=frozenset())],
        ids=["every-class-and-a-type", "every-class"],
    )
    def test_with_every_class_the_types_say_nothing(self, filters):
        assert _hand_view(PORTFOLIO, AllocationDimension.TYPE, filters) == _hand_view(PORTFOLIO, AllocationDimension.TYPE)

    def test_a_type_the_scope_does_not_hold_has_no_effect(self):
        view = _hand_view(PORTFOLIO, AllocationDimension.TYPE, AllocationFilters(classes=frozenset(), types=frozenset({"ETF_CRYPTO"})))
        assert view.base == ZERO and view.slices == ()

    def test_the_type_filter_holds_in_the_history_too(self):
        filters = AllocationFilters(classes=frozenset(), types=frozenset({"ETF_STOCK"}))
        view = _hand_view([PORTFOLIO], AllocationDimension.TYPE, filters, include_history=True)
        assert {component["name"] for step in view.history for component in step["components"]} == {"ETF_STOCK"}

    def test_the_classes_carry_their_types_and_the_amounts_add_up(self):
        view = _hand_view(PORTFOLIO, AllocationDimension.SECTOR, AllocationFilters(classes=frozenset()))
        types = {row.asset_class: [(item.asset_type, item.amount) for item in row.types] for row in view.classes}
        assert types == {"STOCK": [("ETF_STOCK", Decimal("1000")), ("STOCK", Decimal("500"))], "BOND": [("ETF_BOND", Decimal("300"))], "CRYPTO": [("CRYPTO", Decimal("200"))], LIQUIDITY: []}
        for row in view.classes:
            assert not row.types or sum((item.amount for item in row.types), ZERO) == row.amount

    def test_the_type_dimension_has_no_matrix(self):
        """86, D-15: each type sits in one class, so the matrix would be one block per row."""
        assert _hand_view(PORTFOLIO, AllocationDimension.TYPE).matrix is None

    def test_the_geography_has_no_liquidity(self):
        on = _hand_view(PORTFOLIO, AllocationDimension.GEOGRAPHY)
        assert LIQUIDITY not in _amounts(on)
        assert _unattributable(on) == {UnattributableReason.IN_TRANSIT: Decimal("40"), UnattributableReason.NO_COUNTRY: Decimal("150")}
        assert on.outside.amount == ZERO, "Liquidity is on: the cash is not outside the filter"
        assert _amounts(on) == {"USA": Decimal("600"), "Unknown": Decimal("400") + Decimal("300") + Decimal("200"), "ITA": Decimal("500")}
        off = _hand_view(PORTFOLIO, AllocationDimension.GEOGRAPHY, AllocationFilters(classes=frozenset({"STOCK", "BOND", "CRYPTO"})))
        assert UnattributableReason.NO_COUNTRY not in _unattributable(off)
        assert {row.asset_class: row.amount for row in off.outside.by_class} == {LIQUIDITY: Decimal("150")}
        assert _sum_of_view(on) == _sum_of_view(off) == PORTFOLIO.nav_value

    def test_an_excluded_bucket_takes_only_the_assets_part_in_it(self):
        view = _hand_view(PORTFOLIO, AllocationDimension.SECTOR, AllocationFilters(exclude_buckets=frozenset({"Other"})))
        assert {row.key: row.amount for row in view.excluded.by_bucket} == {"Other": Decimal("300")}, "the ETF's 30 % only"
        assert _amounts(view)["Technology"] == Decimal("700"), "the rest of the ETF stays"
        technology = next(item for item in view.slices if item.key == "Technology")
        assert [(member.asset_id, member.amount, member.share_of_slice) for member in technology.assets] == [(ETF, Decimal("700"), Decimal("100.00"))]
        assert _sum_of_view(view) == PORTFOLIO.nav_value

    def test_both_buckets_in_the_sector(self):
        view = _hand_view(PORTFOLIO, AllocationDimension.SECTOR, AllocationFilters(exclude_buckets=frozenset({"Other", "Unknown"})))
        assert {row.key: row.amount for row in view.excluded.by_bucket} == {"Unknown": Decimal("500"), "Other": Decimal("300")}
        assert _amounts(view) == {"Technology": Decimal("700"), "Utilities": Decimal("500"), LIQUIDITY: Decimal("150")}

    def test_a_bucket_absent_from_the_dimension_has_no_effect(self):
        for dimension, bucket in ((AllocationDimension.GEOGRAPHY, "Other"), (AllocationDimension.ASSET, "Unknown"), (AllocationDimension.ASSET, "Other"), (AllocationDimension.TYPE, "Other")):
            plain = _hand_view(PORTFOLIO, dimension)
            filtered = _hand_view(PORTFOLIO, dimension, AllocationFilters(exclude_buckets=frozenset({bucket})))
            assert filtered == plain, f"{bucket} in {dimension}: no effect, no error"

    def test_the_unknown_type_is_excludable(self):
        state = _state({ETF: "1000", 9: "70"})  # asset 9 has no type: the replay names it Unknown
        view = _hand_view(state, AllocationDimension.TYPE, AllocationFilters(exclude_buckets=frozenset({"Unknown"})))
        assert {row.key: row.amount for row in view.excluded.by_bucket} == {"Unknown": Decimal("70")}
        assert {row.asset_class for row in view.classes} >= {"Unknown", "STOCK"}

    def test_an_excluded_asset_goes_whole(self):
        view = _hand_view(PORTFOLIO, AllocationDimension.SECTOR, AllocationFilters(exclude_asset_ids=frozenset({ETF})))
        assert [(row.asset_id, row.amount) for row in view.excluded.by_asset] == [(ETF, Decimal("1000"))]
        assert set(_amounts(view)) == {"Utilities", "Unknown", LIQUIDITY}, "none of the ETF's sectors is left"
        assert view.base == Decimal("500") + Decimal("300") + Decimal("200") + Decimal("150")
        assert _sum_of_view(view) == PORTFOLIO.nav_value

    def test_an_asset_off_by_class_and_excluded_counts_once_outside(self):
        view = _hand_view(PORTFOLIO, AllocationDimension.TYPE, AllocationFilters(classes=frozenset({"BOND", LIQUIDITY}), exclude_asset_ids=frozenset({ETF})))
        assert view.excluded.by_asset == (), "the class comes first"
        assert {row.asset_class: row.amount for row in view.outside.by_class} == {"STOCK": Decimal("1500"), "CRYPTO": Decimal("200")}
        assert _sum_of_view(view) == PORTFOLIO.nav_value

    def test_negative_cash_is_a_slice_below_zero(self):
        state = _state({ETF: "1000", SHARE: "500"}, cash="-300")
        view = _hand_view(state, AllocationDimension.SECTOR)
        assert _amounts(view)[LIQUIDITY] == Decimal("-300")
        assert view.base == Decimal("1200") == view.portfolio_total
        shares = {item.key: item.share_of_selection for item in view.slices}
        assert shares[LIQUIDITY] == Decimal("-25.00") and shares["Technology"] == Decimal("58.33")
        geography = _hand_view(state, AllocationDimension.GEOGRAPHY)
        assert _unattributable(geography) == {UnattributableReason.NO_COUNTRY: Decimal("-300")}
        assert geography.base == Decimal("1500") and _sum_of_view(geography) == state.nav_value

    def test_a_base_at_or_below_zero_has_no_share(self):
        state = _state({ETF: "100"}, cash="-400")
        view = _hand_view(state, AllocationDimension.TYPE)
        assert view.base == Decimal("-300")
        assert [item.share_of_selection for item in view.slices] == [None, None], "MF-C2: every slice is None"
        assert [item.share_of_portfolio for item in view.slices] == [None, None], "the NAV is below zero too"
        assert view.base_share_of_portfolio is None
        empty_selection = _hand_view(PORTFOLIO, AllocationDimension.TYPE, AllocationFilters(classes=frozenset()))
        assert (empty_selection.base, empty_selection.slices, empty_selection.base_share_of_portfolio) == (ZERO, (), Decimal("0.00"))

    def test_the_asset_dimension(self):
        view = _hand_view(PORTFOLIO, AllocationDimension.ASSET, AllocationFilters(exclude_asset_ids=frozenset({CRYPTO})))
        assert [(item.key, item.asset_id, item.amount) for item in view.slices] == [
            (str(ETF), ETF, Decimal("1000")),
            (str(SHARE), SHARE, Decimal("500")),
            (str(BOND), BOND, Decimal("300")),
            (LIQUIDITY, None, Decimal("150")),
        ]
        assert all(item.assets == () for item in view.slices), "an asset's slice is the asset"
        assert view.matrix is None

    def test_the_matrix_rows_and_columns(self):
        sector = _hand_view(PORTFOLIO, AllocationDimension.SECTOR)
        assert sector.matrix.rows == ("STOCK", "BOND", "CRYPTO", LIQUIDITY)
        cells = {(cell.asset_class, cell.key): cell.amount for cell in sector.matrix.cells}
        assert cells[("STOCK", "Technology")] == Decimal("700") and ("STOCK", "Unknown") not in cells
        assert cells[("BOND", "Unknown")] == Decimal("300") and cells[("CRYPTO", "Unknown")] == Decimal("200")
        assert cells[("STOCK", "Other")] == Decimal("300") and cells[("STOCK", "Utilities")] == Decimal("500")
        assert cells[(LIQUIDITY, LIQUIDITY)] == Decimal("150")
        assert sector.matrix.unattributed == tuple(row for row in sector.excluded.unattributable if row.reason is UnattributableReason.IN_TRANSIT)
        geography = _hand_view(PORTFOLIO, AllocationDimension.GEOGRAPHY)
        assert LIQUIDITY not in geography.matrix.rows
        assert {row.reason: row.amount for row in geography.matrix.unattributed} == {UnattributableReason.NO_COUNTRY: Decimal("150"), UnattributableReason.IN_TRANSIT: Decimal("40")}
        for view in (sector, geography):
            assert _sum_of_matrix(view) == PORTFOLIO.nav_value
        first = next(cell for cell in sector.matrix.cells if cell.key == "Technology")
        assert first.share_of_portfolio == Decimal("31.96")

    def test_the_scope_lists_what_the_window_held(self):
        earlier = _state({ETF: "900", CRYPTO: "100"}, cash="0", day=DAY - timedelta(days=3))
        now = _state({ETF: "1000"}, cash="0")
        view = _hand_view([earlier, now], AllocationDimension.TYPE, date_from=earlier.date)
        assert [(row.asset_id, row.asset_class, row.amount) for row in view.assets] == [(ETF, "STOCK", Decimal("1000")), (CRYPTO, "CRYPTO", ZERO)]
        assert [(row.asset_class, row.amount) for row in view.classes] == [("STOCK", Decimal("1000")), ("CRYPTO", ZERO)], "no cash in the window: no Liquidity class"
        later_only = _hand_view([earlier, now], AllocationDimension.TYPE, date_from=DAY)
        assert [row.asset_id for row in later_only.assets] == [ETF], "the window starts after CRYPTO left"
        with_cash = _hand_view([_state({ETF: "900"}, cash="10", day=DAY - timedelta(days=1)), now], AllocationDimension.TYPE)
        assert (LIQUIDITY, ZERO) in [(row.asset_class, row.amount) for row in with_cash.classes], "cash held earlier in the window: listed"

    def test_the_liquidity_class_on_the_engines_states(self):
        """On the engine's ``DailyStates`` (segments): cash held only earlier in the window lists the class, with the
        view's day's zero; no cash in the window, no class."""
        earlier = _state({ETF: "900"}, cash="25", day=DAY - timedelta(days=5))
        now = _state({ETF: "1000"}, cash="0")
        states = DailyStates([StateSegment(start=earlier.date, end=DAY - timedelta(days=1), state=earlier), StateSegment(start=DAY, end=DAY, state=now)])
        whole = _hand_view(states, AllocationDimension.TYPE, date_from=earlier.date)
        assert [(row.asset_class, row.amount) for row in whole.classes] == [("STOCK", Decimal("1000")), (LIQUIDITY, ZERO)]
        assert DerivedViewsBuilder(states, "EUR").allocation_has_cash(earlier.date) is True
        assert DerivedViewsBuilder(states, "EUR").allocation_has_cash(DAY) is False
        last_day_only = _hand_view(states, AllocationDimension.TYPE, date_from=DAY)
        assert [row.asset_class for row in last_day_only.classes] == ["STOCK"], "no cash from DAY on: no Liquidity class"

    def test_an_empty_view(self):
        for dimension in ALL_DIMENSIONS:
            view = build_allocation_view([], asset_types={}, asset_classifications={}, dimension=dimension, include_history=True)
            assert (view.as_of, view.portfolio_total, view.base, view.slices, view.classes, view.history) == (None, ZERO, ZERO, (), (), [])
            assert (view.matrix is None) is (dimension not in MATRIX_DIMENSIONS)

    def test_liquidity_is_not_an_excludable_bucket(self):
        with pytest.raises(ValueError, match="not an excludable bucket"):
            AllocationFilters(exclude_buckets=frozenset({LIQUIDITY}))


class TestTheHistory:
    def test_a_profile_step_opens_a_step_on_its_day(self):
        steps = _view(_result().daily_states, AllocationDimension.GEOGRAPHY, include_history=True, date_from=BOOK_FROM).history
        assert QUIET_18 in [step["date"] for step in steps], "GEO_1 → GEO_2 on a quiet day: a step starts there"
        before = next(step for step in steps if step["date"] <= QUIET_18 - timedelta(days=1) <= step["through"])
        on = next(step for step in steps if step["date"] == QUIET_18)
        assert "USA" in {c["name"] for c in before["components"]} and "USA" not in {c["name"] for c in on["components"]}
        assert "DEU" in {c["name"] for c in on["components"]}

    @pytest.mark.parametrize("dimension", ALL_DIMENSIONS)
    def test_the_base_of_a_step_is_the_sum_of_its_slices(self, dimension):
        filters = AllocationFilters(classes=frozenset({"STOCK"}))
        steps = _view(_result().daily_states, dimension, filters, include_history=True, date_from=BOOK_FROM).history
        assert steps, "precondition"
        for step in steps:
            assert step["base"] == sum((component["amount"] for component in step["components"]), ZERO)
            assert LIQUIDITY not in {component["name"] for component in step["components"]}, "Liquidity is off"
            assert step["through"] >= step["date"]
        assert steps[-1]["through"] == BOOK_TO
        current = _view(_result().daily_states, dimension, filters)
        assert steps[-1]["base"] == current.base, "the last step is the view of the last day"
