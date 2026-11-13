"""MF-C2 — the allocation views on a day whose slices add up to zero or less: every ``value`` is None, the amounts stay.

Developer's decision (ondata 6; backlog ``BACKLOG_POST_1.2.md`` «MF-C2»). ``weights.slice_percents`` divided by the
signed sum, and by 1 when the sum was zero: stocks bought on overdraft (``{Stock: 500, Liquidity: −500}``) read
50000 % / −50000 %, a negative sum flipped every slice's sign, and an emptied portfolio (``{Liquidity: 0}``) read 0 %.
Now, when a day's slices add up to zero or less, every slice of that day and dimension has ``"value": None`` (never
quantized), while ``name``, ``amount``, ``id``, ``emoji`` and the order (by amount, descending) are unchanged. With a
positive sum nothing changes, negative cash included (the cash slice below zero, the others above 100).

Module under test: ``backend/app/services/financial_math/portfolio/derived_views.py`` —
``DerivedViewsBuilder.build_allocation_current`` (type, sector with its emoji, geography),
``build_allocation_history`` and the asset dimension (``build_asset_allocation_current/history``, i.e.
``_asset_components``: the held assets plus Liquidity = cash + cash in transit). The contract the report validates the
components against: ``schemas/portfolio.py`` ``AllocationItem.value`` Optional, so ``AllocationHistoryPoint.components``
accept a None value too.

What is tested (pure: hand-made ``DailyPortfolioState``s, no database, no server, no network):

1. ``TestCurrent`` — the three dimensions on a day with sum 0, sum < 0 and all zero; the parity day (positive sum,
   negative cash: 150.00 / −50.00, exactly as before).
2. ``TestHistory`` — one dimension over a list of states: the non-positive days are None, the positive ones unchanged.
3. ``TestAssetDimension`` — current and history on the same three kinds of day, and the parity day.
4. ``TestTheContract`` — ``AllocationItem`` and ``AllocationHistoryPoint`` accept ``value=None``; it serialises as null.

RED on the tree of 2026-10-28 (HEAD ed2f59268): the views give ``Decimal('50000.00')`` / ``Decimal('-50.00')`` /
``Decimal('0.00')`` where None is expected (``AssertionError``), and the schema refuses ``value=None``
(``ValidationError``). The parity tests are green and must stay green.

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory).
"""

from __future__ import annotations

from dataclasses import MISSING, fields
from datetime import date
from decimal import Decimal

import pytest

from backend.app.schemas.portfolio.summary import AllocationHistoryPoint, AllocationItem
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState
from backend.app.utils.asset.sector import sector_emoji

ZERO = Decimal("0")
X, W = 100, 500
NAMES = {X: "Alpha Corp", W: "Omega Fund"}
D1, D2, D3, D4 = (date(2026, 3, d) for d in (2, 3, 4, 5))

# Every required field of the dataclass the views do not read: zero, read off the dataclass (as in
# test_allocation_emoji.py) so that a new field does not break a test about the allocation.
_UNRELATED = {f.name: ZERO for f in fields(DailyPortfolioState) if f.init and f.default is MISSING and f.default_factory is MISSING and f.name not in {"date", "cash_value", "in_transit_cash_value"}}


def _d(text: str) -> Decimal:
    return Decimal(text)


def _state(day: date, *, stock: str, cash: str, in_transit_cash: str = "0", geography: str | None = None) -> DailyPortfolioState:
    """One day of a single-asset portfolio, in the shape DailyStateBuilder writes it: asset X worth ``stock`` (type
    Stock, sector Technology, geography USA unless ``geography`` overrides that slice's amount), and Liquidity =
    ``cash + in_transit_cash`` in the type and sector dimensions (never in geography)."""
    stock_amount, cash_amount, it_cash = _d(stock), _d(cash), _d(in_transit_cash)
    liquidity = cash_amount + it_cash
    by_asset = {X: stock_amount} if stock_amount != 0 else {}
    by_type = ({"Stock": stock_amount} if by_asset else {}) | {"Liquidity": liquidity}
    by_sector = ({"Technology": stock_amount} if by_asset else {}) | {"Liquidity": liquidity}
    by_geography = {"USA": _d(geography) if geography is not None else stock_amount} if by_asset else {}
    return DailyPortfolioState(
        date=day,
        **_UNRELATED,
        cash_value=cash_amount,
        in_transit_cash_value=it_cash,
        by_type=by_type,
        by_sector=by_sector,
        by_geography=by_geography,
        by_asset=by_asset,
    )


#: Days whose slices add up to zero or less, in every dimension that has a Liquidity slice
NON_POSITIVE_DAYS = {
    "net-zero-overdraft": {"stock": "500", "cash": "-500"},
    "negative-sum": {"stock": "100", "cash": "-300"},
    "negative-sum-with-cash-in-transit": {"stock": "100", "cash": "-150", "in_transit_cash": "20"},
    "emptied-portfolio": {"stock": "0", "cash": "0"},
}


def _amounts(components: list[dict]) -> list[tuple]:
    return [(c["name"], c["amount"]) for c in components]


def _assert_no_value(components: list[dict], expected_amounts: list[tuple], *, where: str) -> None:
    """Every component has the key ``value`` set to None; names, amounts (by value and exponent) and order as given."""
    assert components, f"{where}: precondition — there are slices"
    assert _amounts(components) == expected_amounts, f"{where}: names, amounts or order changed"
    for component, (_, amount) in zip(components, expected_amounts, strict=True):
        assert str(component["amount"]) == str(amount), f"{where}: {component['name']} amount {component['amount']!r}, expected {amount!r}"
    assert "value" in {key for c in components for key in c}, f"{where}: the value key must stay, set to None"
    assert [c.get("value", "missing") for c in components] == [None] * len(components), f"{where}: expected every value None, got {[(c['name'], c.get('value', 'missing')) for c in components]}"


def _type_amounts(state: DailyPortfolioState) -> list[tuple]:
    return sorted(state.by_type.items(), key=lambda item: -item[1])


# =============================================================================
# 1. build_allocation_current
# =============================================================================


class TestCurrent:
    @pytest.mark.parametrize("day", list(NON_POSITIVE_DAYS.values()), ids=list(NON_POSITIVE_DAYS))
    def test_type_and_sector_have_no_value_the_amounts_stay(self, day):
        state = _state(D1, **day)
        assert sum(state.by_type.values(), ZERO) <= 0, "precondition: the slices add up to zero or less"
        by_type, by_sector, _ = DerivedViewsBuilder([state], "EUR").build_allocation_current()
        _assert_no_value(by_type, _type_amounts(state), where="by_type")
        _assert_no_value(by_sector, sorted(state.by_sector.items(), key=lambda item: -item[1]), where="by_sector")

    def test_the_sector_emoji_and_the_type_none_emoji_are_kept(self):
        by_type, by_sector, _ = DerivedViewsBuilder([_state(D1, stock="500", cash="-500")], "EUR").build_allocation_current()
        assert [(c["name"], c["emoji"]) for c in by_sector] == [("Technology", sector_emoji("Technology")), ("Liquidity", sector_emoji("Liquidity"))]
        assert [c["emoji"] for c in by_type] == [None, None]
        assert [c["value"] for c in by_sector] == [None, None], f"got {by_sector}"

    def test_a_negative_geography_has_no_value(self):
        """Geography carries no Liquidity: its sum goes below zero only with an asset valued below zero."""
        _, _, by_geography = DerivedViewsBuilder([_state(D1, stock="100", cash="50", geography="-100")], "EUR").build_allocation_current()
        _assert_no_value(by_geography, [("USA", _d("-100"))], where="by_geography")

    def test_each_dimension_reads_its_own_sum(self):
        """The rule is per dimension: geography (no Liquidity) keeps its 100 % when type and sector cancel out."""
        by_type, _, by_geography = DerivedViewsBuilder([_state(D1, stock="500", cash="-500")], "EUR").build_allocation_current()
        assert [c["value"] for c in by_type] == [None, None], f"got {by_type}"
        assert [(c["name"], c["value"]) for c in by_geography] == [("USA", _d("100.00"))]

    def test_parity_positive_sum_with_negative_cash(self):
        """Unchanged: the cash slice below zero, the others above 100, quantized to 0.01."""
        by_type, by_sector, by_geography = DerivedViewsBuilder([_state(D1, stock="1500", cash="-500")], "EUR").build_allocation_current()
        assert [(c["name"], str(c["value"]), c["amount"]) for c in by_type] == [("Stock", "150.00", _d("1500")), ("Liquidity", "-50.00", _d("-500"))]
        assert [(c["name"], str(c["value"])) for c in by_sector] == [("Technology", "150.00"), ("Liquidity", "-50.00")]
        assert [(c["name"], str(c["value"])) for c in by_geography] == [("USA", "100.00")]


# =============================================================================
# 2. build_allocation_history
# =============================================================================


class TestHistory:
    def test_the_non_positive_days_have_no_value_the_positive_ones_are_unchanged(self):
        states = [
            _state(D1, stock="1000", cash="500"),
            _state(D2, stock="500", cash="-500"),
            _state(D3, stock="100", cash="-300"),
            _state(D4, stock="0", cash="0"),
        ]
        history = DerivedViewsBuilder(states, "EUR").build_allocation_history("type")
        assert [(point["date"], point["through"]) for point in history] == [(D1, D1), (D2, D2), (D3, D3), (D4, D4)], "precondition: one step a day"
        first = history[0]["components"]
        assert [(c["name"], str(c["value"]), c["amount"]) for c in first] == [("Stock", "66.67", _d("1000")), ("Liquidity", "33.33", _d("500"))]
        for point, state in zip(history[1:], states[1:], strict=True):
            _assert_no_value(point["components"], _type_amounts(state), where=f"type on {point['date']}")

    @pytest.mark.parametrize("dimension", ["type", "sector"])
    def test_every_dimension_with_a_liquidity_slice(self, dimension):
        state = _state(D1, stock="500", cash="-500")
        (point,) = DerivedViewsBuilder([state], "EUR").build_allocation_history(dimension)
        attr = {"type": state.by_type, "sector": state.by_sector}[dimension]
        _assert_no_value(point["components"], sorted(attr.items(), key=lambda item: -item[1]), where=dimension)

    def test_parity_positive_sum_with_negative_cash(self):
        (point,) = DerivedViewsBuilder([_state(D1, stock="1500", cash="-500")], "EUR").build_allocation_history("type")
        assert [(c["name"], str(c["value"]), c["amount"]) for c in point["components"]] == [("Stock", "150.00", _d("1500")), ("Liquidity", "-50.00", _d("-500"))]


# =============================================================================
# 3. The asset dimension (_asset_components)
# =============================================================================


def _asset_amounts(state: DailyPortfolioState) -> list[tuple]:
    slices = [(NAMES[asset_id], amount) for asset_id, amount in state.by_asset.items()] + [("Liquidity", state.cash_value + state.in_transit_cash_value)]
    return sorted(slices, key=lambda item: -item[1])


class TestAssetDimension:
    @pytest.mark.parametrize("day", list(NON_POSITIVE_DAYS.values()), ids=list(NON_POSITIVE_DAYS))
    def test_current_has_no_value_ids_and_emoji_kept(self, day):
        state = _state(D1, **day)
        got = DerivedViewsBuilder([state], "EUR").build_asset_allocation_current(NAMES)
        _assert_no_value(got, _asset_amounts(state), where="asset current")
        assert {c["name"]: c["id"] for c in got} == {NAMES.get(asset_id, ""): asset_id for asset_id in state.by_asset} | {"Liquidity": None}
        assert all("emoji" in c and c["emoji"] is None for c in got)

    def test_an_emptied_portfolio_is_a_liquidity_slice_without_value(self):
        """The last day of a portfolio sold out and withdrawn: no asset, Liquidity 0 — 0.00 % before, None now."""
        got = DerivedViewsBuilder([_state(D1, stock="0", cash="0")], "EUR").build_asset_allocation_current(NAMES)
        assert got == [{"name": "Liquidity", "id": None, "value": None, "amount": ZERO, "emoji": None}], f"got {got}"

    def test_history_non_positive_days_have_no_value(self):
        states = [_state(D1, stock="300", cash="100"), _state(D2, stock="500", cash="-500"), _state(D3, stock="0", cash="0")]
        history = DerivedViewsBuilder(states, "EUR").build_asset_allocation_history(NAMES)
        assert [point["date"] for point in history] == [D1, D2, D3], "precondition: one step a day"
        assert [(c["name"], str(c["value"])) for c in history[0]["components"]] == [("Alpha Corp", "75.00"), ("Liquidity", "25.00")]
        for point, state in zip(history[1:], states[1:], strict=True):
            _assert_no_value(point["components"], _asset_amounts(state), where=f"asset on {point['date']}")
            assert all("emoji" not in c or c["emoji"] is None for c in point["components"])

    def test_parity_positive_sum_with_negative_cash(self):
        got = DerivedViewsBuilder([_state(D1, stock="300", cash="-150", in_transit_cash="0")], "EUR").build_asset_allocation_current(NAMES)
        assert [(c["name"], c["id"], str(c["value"]), c["amount"]) for c in got] == [("Alpha Corp", X, "200.00", _d("300")), ("Liquidity", None, "-100.00", _d("-150"))]


# =============================================================================
# 4. The contract
# =============================================================================


class TestTheContract:
    def test_allocation_item_accepts_no_value(self):
        item = AllocationItem(name="Liquidity", value=None, amount=_d("-500"))
        assert item.value is None and item.amount == _d("-500")
        assert item.model_dump(mode="json")["value"] is None, "null in the JSON, never dropped"

    def test_allocation_item_value_is_still_a_declared_field(self):
        """Optional, not removed: a positive-sum slice still carries its percentage."""
        assert AllocationItem(name="Stock", value=_d("150.00"), amount=_d("1500")).value == _d("150.00")

    def test_allocation_history_point_accepts_components_without_value(self):
        components = [{"name": "Alpha Corp", "id": X, "value": None, "amount": _d("500")}, {"name": "Liquidity", "id": None, "value": None, "amount": _d("-500")}]
        point = AllocationHistoryPoint(date=D1, through=D1, components=components)
        assert [c.value for c in point.components] == [None, None]

    def test_the_views_components_validate(self):
        """What the report does with them (``AllocationItem(**item)``, ``AllocationHistoryPoint(**point)``)."""
        views = DerivedViewsBuilder([_state(D1, stock="500", cash="-500")], "EUR")
        by_type, by_sector, _ = views.build_allocation_current()
        items = [AllocationItem(**item) for item in by_type + by_sector + views.build_asset_allocation_current(NAMES)]
        assert [item.value for item in items] == [None] * len(items), f"got {[(item.name, item.value) for item in items]}"
        points = [AllocationHistoryPoint(**point) for point in views.build_allocation_history("type")]
        assert [c.value for c in points[0].components] == [None, None]
