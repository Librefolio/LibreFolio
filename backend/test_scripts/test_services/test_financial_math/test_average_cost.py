"""
Unit tests for the single average-cost implementation (issue #32, workstream P).

Module under test: ``backend/app/services/financial_math/average_cost.py`` —
``compute_average_costs``, ``cost_movement_from_transaction``, ``determine_target_currency``
and the value objects they exchange (CostMovement, CostPosition, CostStep, AverageCost, ...).

What the function owes its callers, in one line: every acquisition costs what was actually
paid, converted into the report currency T at its own date through the FX service — one
batched call for every position — and every conversion it could not make is reported with
its pair and dates instead of becoming a silent zero.

Pure: no database, no server, no network. The module's only I/O is ``convert_bulk``; every
test replaces the module attribute ``average_cost.convert_bulk`` with a double, so every
figure is exact and every conversion request is observable. Where nothing needs converting
the double is a probe that records and fails, and the session is ``None``: nothing may
touch it.

Red-first: written before the module exists. Until it does, collection stops at the import
below with ModuleNotFoundError — that is the expected red state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.db.models import TransactionType
from backend.app.schemas.common import Currency
from backend.app.services.financial_math import average_cost
from backend.app.services.financial_math.average_cost import (
    AverageCost,
    CostConversion,
    CostEffect,
    CostMovement,
    CostMovementKind,
    CostPosition,
    MissingConversion,
    compute_average_costs,
    cost_movement_from_transaction,
    determine_target_currency,
)
from backend.test_scripts.test_utils import print_section, print_success

D1 = date(2024, 1, 10)
D1B = date(2024, 1, 11)
D2 = date(2024, 2, 12)
D3 = date(2024, 3, 11)
D4 = date(2024, 4, 15)
D5 = date(2024, 5, 13)

ACQ = CostMovementKind.ACQUISITION
RED = CostMovementKind.REDUCTION
SPLIT = CostMovementKind.SPLIT

_NOT_PASSED = object()


# =============================================================================
# convert_bulk doubles
# =============================================================================


@dataclass
class FakeFx:
    """``convert_bulk`` double: fixed directional rates, unlimited backward fill, every call recorded.

    ``rates[(from, to)][day]`` is the number of ``to`` units for one ``from`` unit from
    ``day`` on. Results are aligned with the input, as in the FX service:
    ``(Currency, rate_date, rate_date < requested_date)``, or ``None`` when no rate exists
    on or before the requested date.
    """

    rates: dict[tuple[str, str], dict[date, Decimal]] = field(default_factory=dict)
    calls: list[list[tuple[Currency, str, date]]] = field(default_factory=list)
    sessions: list[object] = field(default_factory=list)
    raise_on_error_args: list[object] = field(default_factory=list)

    async def __call__(self, session, conversions, raise_on_error=_NOT_PASSED):
        batch = list(conversions)
        self.sessions.append(session)
        self.raise_on_error_args.append(raise_on_error)
        self.calls.append(batch)
        results: list[tuple[Currency, date, bool] | None] = []
        errors: list[str] = []
        for index, (amount, to_currency, day) in enumerate(batch):
            series = self.rates.get((amount.code, to_currency), {})
            known = [rate_day for rate_day in series if rate_day <= day]
            if not known:
                results.append(None)
                errors.append(f"Conversion {index}: no {amount.code}/{to_currency} rate on or before {day}")
                continue
            rate_day = max(known)
            results.append((Currency(code=to_currency, amount=amount.amount * series[rate_day]), rate_day, rate_day < day))
        return results, errors

    @property
    def requests(self) -> set[tuple[str, Decimal, str, date]]:
        """Every ``(from, amount, to, date)`` requested, duplicates collapsed."""
        return {(amount.code, amount.amount, to_currency, day) for batch in self.calls for amount, to_currency, day in batch}

    @property
    def identity_requests(self) -> list[tuple[str, str, date]]:
        """Requests whose source and target currency coincide: the FX service is never asked for those."""
        return [(amount.code, to_currency, day) for batch in self.calls for amount, to_currency, day in batch if amount.code == to_currency]


@dataclass
class ForbiddenFx:
    """Probe for histories where nothing needs converting: it records the call, then fails loudly.

    The record is what the tests assert on, so a caller that swallowed the exception would
    still be caught.
    """

    calls: list[tuple[tuple, dict]] = field(default_factory=list)

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        raise AssertionError("convert_bulk must not be called: nothing in this history needs converting")


@pytest.fixture
def forbidden_fx(monkeypatch) -> ForbiddenFx:
    probe = ForbiddenFx()
    monkeypatch.setattr(average_cost, "convert_bulk", probe)
    return probe


def install_fx(monkeypatch, rates: dict[tuple[str, str], dict[date, str]]) -> FakeFx:
    fx = FakeFx(rates={pair: {day: Decimal(rate) for day, rate in series.items()} for pair, series in rates.items()})
    monkeypatch.setattr(average_cost, "convert_bulk", fx)
    return fx


# =============================================================================
# Builders
# =============================================================================


def acquisition(day: date, quantity: str, cost: str | None, currency: str | None, *, movement_id: int | None = None, transaction_type: str = "BUY") -> CostMovement:
    return CostMovement(
        movement_id=movement_id,
        transaction_type=transaction_type,
        date=day,
        kind=ACQ,
        quantity=Decimal(quantity),
        cost_amount=None if cost is None else Decimal(cost),
        cost_currency=currency,
    )


def reduction(day: date, quantity: str, *, movement_id: int | None = None, transaction_type: str = "SELL") -> CostMovement:
    return CostMovement(movement_id=movement_id, transaction_type=transaction_type, date=day, kind=RED, quantity=Decimal(quantity))


def split(day: date, quantity: str, *, movement_id: int | None = None) -> CostMovement:
    return CostMovement(movement_id=movement_id, transaction_type="ADJUSTMENT", date=day, kind=SPLIT, quantity=Decimal(quantity))


async def compute_one(position: CostPosition, *, report_currency: str, asset_leg: bool = True, session: object = None) -> AverageCost:
    results = await compute_average_costs(session, [position], report_currency=report_currency, asset_leg=asset_leg)
    assert set(results) == {position.key}, f"one position in, one result out keyed by it: got {list(results)}"
    return results[position.key]


def movement_ids(result: AverageCost) -> list[int | None]:
    return [step.movement.movement_id for step in result.steps]


# =============================================================================
# U1 — single currency: the arithmetic, and no FX service at all
# =============================================================================


class TestSingleCurrency:
    @pytest.mark.asyncio
    async def test_u1_buys_sale_zero_cost_and_split_never_convert(self, forbidden_fx):
        """P = A = T = EUR: exact sums, proportional exit, zero-cost add and split rescale, without a single conversion."""
        print_section("U1 — single currency history, no conversion")
        position = CostPosition(
            key=("asset", 1),
            asset_currency="EUR",
            movements=(
                acquisition(D1, "10", "1000", "EUR", movement_id=1),
                acquisition(D2, "10", "2000", "EUR", movement_id=2),
                reduction(D3, "-5", movement_id=3),
                acquisition(D4, "5", "0", "EUR", movement_id=4, transaction_type="ADJUSTMENT"),
                split(D5, "20", movement_id=5),
            ),
        )

        result = await compute_one(position, report_currency="EUR")

        assert forbidden_fx.calls == []
        assert [(step.movement.movement_id, step.effect, step.quantity, step.cost_report, step.cost_report_change) for step in result.steps] == [
            (1, CostEffect.ADD, Decimal("10"), Decimal("1000"), Decimal("1000")),
            (2, CostEffect.ADD, Decimal("20"), Decimal("3000"), Decimal("2000")),
            (3, CostEffect.REDUCE, Decimal("15"), Decimal("2250"), Decimal("-750")),
            (4, CostEffect.ADD_ZERO_COST, Decimal("20"), Decimal("2250"), Decimal("0")),
            (5, CostEffect.SPLIT_RESCALE, Decimal("40"), Decimal("2250"), Decimal("0")),
        ]
        # Paid in the asset currency: the asset leg is the same money, step by step.
        assert [(step.cost_asset, step.cost_asset_change) for step in result.steps] == [
            (Decimal("1000"), Decimal("1000")),
            (Decimal("3000"), Decimal("2000")),
            (Decimal("2250"), Decimal("-750")),
            (Decimal("2250"), Decimal("0")),
            (Decimal("2250"), Decimal("0")),
        ]
        assert [(step.report_complete, step.asset_complete) for step in result.steps] == [(True, True)] * 5
        assert [step.conversion for step in result.steps] == [None] * 5
        assert result.steps[2].unit_cost_report == Decimal("150")

        assert (result.quantity, result.cost_report, result.cost_asset) == (Decimal("40"), Decimal("2250"), Decimal("2250"))
        assert (result.unit_cost_report, result.unit_cost_asset) == (Decimal("56.25"), Decimal("56.25"))
        assert (result.key, result.report_currency, result.asset_currency, result.asset_leg) == (("asset", 1), "EUR", "EUR", True)
        assert (result.report_complete, result.asset_complete, result.has_missing_report_fx) == (True, True, False)
        assert (result.missing, result.unknown_cost_movement_ids, result.oversold_movement_ids) == ((), (), ())
        print_success("U1: 2250 for 40 units, 56.25 each, no convert_bulk call")


# =============================================================================
# U2–U6 — conversions through the FX service
# =============================================================================


class TestConversionsThroughFxService:
    @pytest.mark.asyncio
    async def test_u2_issue_32_paid_in_report_currency_costs_exactly_what_was_paid(self, monkeypatch):
        """#32: an ISK asset bought with EUR, report in EUR, costs the 400 EUR paid — not 0, not 399.99…"""
        print_section("U2 — issue #32: P = T = EUR, A = ISK")
        fx = install_fx(monkeypatch, {("EUR", "ISK"): {D1: "150", D2: "140", D3: "160"}})
        session = object()
        position = CostPosition(
            key="issue-32",
            asset_currency="ISK",
            movements=(
                acquisition(D1, "10", "100", "EUR", movement_id=11),
                acquisition(D2, "5", "150", "EUR", movement_id=12),
                acquisition(D3, "5", "150", "EUR", movement_id=13),
            ),
        )

        result = await compute_one(position, report_currency="EUR", session=session)

        assert result.cost_report == Decimal("400")
        assert result.unit_cost_report == Decimal("20")
        # Asset leg: each EUR payment times that day's EUR→ISK rate: 15000 + 21000 + 24000.
        assert result.cost_asset == Decimal("60000")
        assert result.unit_cost_asset == Decimal("3000")
        assert len(fx.calls) == 1, f"one batched convert_bulk call expected, got {len(fx.calls)}"
        assert fx.sessions == [session]
        assert fx.identity_requests == [], "EUR→EUR must never reach the FX service: the payment is already in the report currency"
        assert fx.requests == {("EUR", Decimal("1"), "ISK", D1), ("EUR", Decimal("1"), "ISK", D2), ("EUR", Decimal("1"), "ISK", D3)}
        assert [step.cost_report_change for step in result.steps] == [Decimal("100"), Decimal("150"), Decimal("150")]
        assert [step.cost_asset_change for step in result.steps] == [Decimal("15000"), Decimal("21000"), Decimal("24000")]
        assert [(step.effect, step.report_complete, step.asset_complete) for step in result.steps] == [(CostEffect.ADD, True, True)] * 3
        # Nothing went through convert_bulk on the T leg, so there is no T-leg provenance.
        assert [step.conversion for step in result.steps] == [None] * 3
        assert result.missing == ()
        print_success("U2: 400 EUR exactly, 60000 ISK, one call, no EUR→EUR request")

    @pytest.mark.asyncio
    async def test_u2b_without_asset_leg_nothing_is_converted(self, forbidden_fx):
        """Same history with asset_leg=False: P = T, so there is nothing left to convert."""
        print_section("U2b — issue #32 with the asset leg off")
        position = CostPosition(
            key="issue-32",
            asset_currency="ISK",
            movements=(
                acquisition(D1, "10", "100", "EUR", movement_id=11),
                acquisition(D2, "5", "150", "EUR", movement_id=12),
                acquisition(D3, "5", "150", "EUR", movement_id=13),
            ),
        )

        result = await compute_one(position, report_currency="EUR", asset_leg=False)

        assert forbidden_fx.calls == []
        assert (result.cost_report, result.unit_cost_report) == (Decimal("400"), Decimal("20"))
        assert (result.cost_asset, result.unit_cost_asset, result.asset_leg) == (None, None, False)
        assert (result.report_complete, result.asset_complete) == (True, False)
        assert [(step.cost_asset, step.cost_asset_change, step.asset_complete) for step in result.steps] == [(None, None, False)] * 3
        print_success("U2b: 400 EUR, no call, asset leg absent")

    @pytest.mark.asyncio
    async def test_u3_paid_in_asset_currency_is_converted_at_each_purchase_date(self, monkeypatch):
        """P = A = USD ≠ T = EUR: each purchase at its own date's rate; the asset leg is the amount paid."""
        print_section("U3 — P = A ≠ T: historical cost with provenance")
        rate_day_2 = D2 - timedelta(days=3)  # the D2 purchase is converted with a rate stored three days earlier
        fx = install_fx(monkeypatch, {("USD", "EUR"): {D1: "0.9", rate_day_2: "0.8"}})
        position = CostPosition(
            key="usd-asset",
            asset_currency="USD",
            movements=(
                acquisition(D1, "10", "100", "USD", movement_id=21),
                acquisition(D2, "10", "100", "USD", movement_id=22),
            ),
        )

        result = await compute_one(position, report_currency="EUR", session=object())

        assert (result.cost_report, result.cost_asset) == (Decimal("170"), Decimal("200"))
        assert len(fx.calls) == 1
        # Only P→T: the asset leg needs no rate when the payment is already in the asset currency.
        assert fx.requests == {("USD", Decimal("100"), "EUR", D1), ("USD", Decimal("100"), "EUR", D2)}
        assert [(step.effect, step.cost_report_change, step.cost_asset_change) for step in result.steps] == [
            (CostEffect.ADD, Decimal("90"), Decimal("100")),
            (CostEffect.ADD, Decimal("80"), Decimal("100")),
        ]
        first, second = result.steps
        assert first.conversion == CostConversion(
            original_amount=Decimal("100"),
            original_currency="USD",
            converted_amount=Decimal("90"),
            rate=Decimal("0.9"),
            rate_date=D1,
            days_back=0,
        )
        assert second.conversion == CostConversion(
            original_amount=Decimal("100"),
            original_currency="USD",
            converted_amount=Decimal("80"),
            rate=Decimal("0.8"),
            rate_date=rate_day_2,
            days_back=3,
        )
        print_success("U3: 170 EUR / 200 USD, provenance with a 3-day backward fill")

    @pytest.mark.asyncio
    async def test_u4_paid_in_a_third_currency_goes_through_the_report_currency(self, monkeypatch):
        """P = GBP ∉ {A = USD, T = EUR}: C_T = paid × r(P→T); C_A = C_T × r(T→A), so the FX effect is 0 on the purchase day."""
        print_section("U4 — P ∉ {A, T}: via T, zero exchange effect at purchase")
        fx = install_fx(monkeypatch, {("GBP", "EUR"): {D1: "1.2"}, ("EUR", "USD"): {D1: "1.25"}})
        position = CostPosition(key="gbp-paid", asset_currency="USD", movements=(acquisition(D1, "10", "100", "GBP", movement_id=31),))

        result = await compute_one(position, report_currency="EUR", session=object())

        assert (result.cost_report, result.cost_asset) == (Decimal("120"), Decimal("150"))
        assert len(fx.calls) == 1
        assert fx.requests == {("GBP", Decimal("100"), "EUR", D1), ("EUR", Decimal("1"), "USD", D1)}
        usd_to_eur_on_purchase_day = Decimal("0.8")  # 1 / 1.25, exact
        assert result.cost_asset * usd_to_eur_on_purchase_day - result.cost_report == Decimal("0")
        assert result.steps[0].conversion == CostConversion(
            original_amount=Decimal("100"),
            original_currency="GBP",
            converted_amount=Decimal("120"),
            rate=Decimal("1.2"),
            rate_date=D1,
            days_back=0,
        )
        print_success("U4: 120 EUR / 150 USD, exchange effect 0 on the purchase day")

    @pytest.mark.asyncio
    async def test_u5_missing_report_rate_adds_quantity_not_cost_until_the_pool_empties(self, monkeypatch):
        """No GBP rate at all: quantity in, cost out of the sum, the pool marked incomplete — until it empties."""
        print_section("U5 — T-leg conversion missing")
        fx = install_fx(monkeypatch, {("EUR", "USD"): {D1: "1.25"}})  # the asset leg has its rate: only GBP is missing
        position = CostPosition(
            key="gbp-missing",
            asset_currency="USD",
            movements=(
                acquisition(D1B, "2", "20", "GBP", movement_id=42),  # input order is not date order, on purpose
                acquisition(D1, "10", "100", "GBP", movement_id=41),
                acquisition(D2, "5", "50", "EUR", movement_id=43),
                reduction(D3, "-17", movement_id=44),
            ),
        )

        result = await compute_one(position, report_currency="EUR", session=object())

        assert len(fx.calls) == 1
        assert fx.raise_on_error_args == [False], "a missing rate must come back as None, not as an exception that loses the whole batch"
        assert fx.requests == {
            ("GBP", Decimal("100"), "EUR", D1),
            ("GBP", Decimal("20"), "EUR", D1B),
            ("EUR", Decimal("1"), "USD", D1),
            ("EUR", Decimal("1"), "USD", D1B),
            ("EUR", Decimal("1"), "USD", D2),
        }
        assert movement_ids(result) == [41, 42, 43, 44]
        missing_d1, missing_d1b, paid_in_eur, full_exit = result.steps
        for step, quantity in ((missing_d1, Decimal("10")), (missing_d1b, Decimal("12"))):
            assert step.effect == CostEffect.ADD_MISSING_FX
            assert (step.quantity, step.cost_report, step.cost_report_change) == (quantity, Decimal("0"), Decimal("0"))
            assert step.cost_asset == Decimal("0"), "without C_T the asset cost of this purchase is unknown too: the known part stays 0"
            assert (step.report_complete, step.asset_complete) == (False, False)
            assert step.conversion is None
        assert paid_in_eur.effect == CostEffect.ADD
        assert (paid_in_eur.quantity, paid_in_eur.cost_report, paid_in_eur.cost_report_change) == (Decimal("17"), Decimal("50"), Decimal("50"))
        assert paid_in_eur.cost_asset == Decimal("62.5")  # 50 EUR × 1.25, the known part of the asset leg
        assert (paid_in_eur.report_complete, paid_in_eur.asset_complete) == (False, False), "the GBP purchases are still in the pool"
        assert full_exit.effect == CostEffect.REDUCE
        assert (full_exit.quantity, full_exit.cost_report, full_exit.cost_asset) == (Decimal("0"), Decimal("0"), Decimal("0"))
        assert (full_exit.cost_report_change, full_exit.cost_asset_change) == (Decimal("-50"), Decimal("-62.5"))
        assert (full_exit.report_complete, full_exit.asset_complete) == (True, True), "an empty pool is complete again"

        assert result.missing == (MissingConversion(pair="GBP/EUR", dates=(D1, D1B), leg="report"),)
        assert result.has_missing_report_fx is True, "the history keeps the missing conversion after the pool empties"
        assert (result.quantity, result.cost_report, result.report_complete) == (Decimal("0"), Decimal("0"), True)
        assert result.oversold_movement_ids == ()
        print_success("U5: quantity counted, cost withheld, GBP/EUR reported with both dates")

    @pytest.mark.asyncio
    async def test_u5b_missing_dates_are_sorted_and_unique(self, monkeypatch):
        """Two purchases on one date and one on another, all unconvertible: one entry, each date once, in order."""
        print_section("U5b — missing dates sorted and unique")
        fx = install_fx(monkeypatch, {})
        position = CostPosition(
            key="gbp-dates",
            asset_currency="EUR",
            movements=(
                acquisition(D2, "1", "10", "GBP", movement_id=51),
                acquisition(D1, "1", "10", "GBP", movement_id=52),
                acquisition(D1, "2", "30", "GBP", movement_id=53),
            ),
        )

        result = await compute_one(position, report_currency="EUR", session=object())

        assert len(fx.calls) == 1
        assert result.missing == (MissingConversion(pair="GBP/EUR", dates=(D1, D2), leg="report"),)
        assert [step.effect for step in result.steps] == [CostEffect.ADD_MISSING_FX] * 3
        assert (result.quantity, result.cost_report, result.report_complete) == (Decimal("4"), Decimal("0"), False)
        print_success("U5b: GBP/EUR on D1 and D2, once each")

    @pytest.mark.asyncio
    async def test_u6_missing_asset_rate_keeps_the_report_cost_exact(self, monkeypatch):
        """No EUR/USD rate: the report leg is exact and complete; only the asset leg is incomplete, reported as A/T."""
        print_section("U6 — asset-leg conversion missing")
        fx = install_fx(monkeypatch, {})
        position = CostPosition(
            key="asset-leg-missing",
            asset_currency="USD",
            movements=(
                acquisition(D1, "10", "100", "EUR", movement_id=61),
                acquisition(D2, "5", "50", "EUR", movement_id=62),
            ),
        )

        result = await compute_one(position, report_currency="EUR", session=object())

        assert len(fx.calls) == 1
        assert fx.requests == {("EUR", Decimal("1"), "USD", D1), ("EUR", Decimal("1"), "USD", D2)}
        assert (result.cost_report, result.unit_cost_report) == (Decimal("150"), Decimal("10"))
        assert (result.report_complete, result.asset_complete) == (True, False)
        assert result.cost_asset == Decimal("0"), "nothing of the asset leg is known"
        assert [(step.effect, step.report_complete, step.asset_complete) for step in result.steps] == [(CostEffect.ADD, True, False)] * 2
        assert result.missing == (MissingConversion(pair="USD/EUR", dates=(D1, D2), leg="asset"),)
        assert result.has_missing_report_fx is False
        print_success("U6: 150 EUR exact, USD/EUR reported on the asset leg")


# =============================================================================
# U7–U10 — pool arithmetic
# =============================================================================


class TestPoolArithmetic:
    @pytest.mark.asyncio
    async def test_u7_reductions_conserve_cost_exactly_and_flag_oversold(self, forbidden_fx):
        """100 for 3 units leaves in two sales whose removed costs add up to 100 exactly; a sale beyond the pool is clamped and flagged."""
        print_section("U7 — exact conservation, full exit, oversold")
        position = CostPosition(
            key="conservation",
            asset_currency="EUR",
            movements=(
                acquisition(D1, "3", "100", "EUR", movement_id=71),
                reduction(D2, "-1", movement_id=72),
                reduction(D3, "-2", movement_id=73),
                acquisition(D4, "2", "10", "EUR", movement_id=74),
                reduction(D5, "-5", movement_id=75),
            ),
        )

        result = await compute_one(position, report_currency="EUR")

        assert forbidden_fx.calls == []
        steps = {step.movement.movement_id: step for step in result.steps}
        one_third_out, rest_out, refill, oversold = steps[72], steps[73], steps[74], steps[75]
        # Σ acquisitions = C left + Σ removed, at every step and to the last digit.
        assert one_third_out.cost_report - one_third_out.cost_report_change == Decimal("100")
        assert -(one_third_out.cost_report_change + rest_out.cost_report_change) == Decimal("100")
        assert -(one_third_out.cost_asset_change + rest_out.cost_asset_change) == Decimal("100")
        assert (rest_out.quantity, rest_out.cost_report, rest_out.cost_asset) == (Decimal("0"), Decimal("0"), Decimal("0"))
        assert (refill.quantity, refill.cost_report) == (Decimal("2"), Decimal("10"))
        assert (oversold.effect, oversold.quantity, oversold.cost_report, oversold.cost_report_change) == (CostEffect.REDUCE, Decimal("0"), Decimal("0"), Decimal("-10"))
        assert result.oversold_movement_ids == (75,)
        print_success("U7: 100 out exactly, oversold sale clamped and flagged")

    @pytest.mark.asyncio
    async def test_u8_split_forward_and_back_rescales_without_moving_cost(self, forbidden_fx):
        """A split changes the quantity, never the cost; reversing past zero empties the pool."""
        print_section("U8 — split rescale")
        position = CostPosition(
            key="split",
            asset_currency="EUR",
            movements=(
                acquisition(D1, "15", "1500", "EUR", movement_id=81),
                split(D2, "15", movement_id=82),
                split(D3, "-15", movement_id=83),
                split(D4, "-15", movement_id=84),
            ),
        )

        result = await compute_one(position, report_currency="EUR")

        assert forbidden_fx.calls == []
        assert [(step.effect, step.quantity, step.cost_report, step.unit_cost_report) for step in result.steps[:3]] == [
            (CostEffect.ADD, Decimal("15"), Decimal("1500"), Decimal("100")),
            (CostEffect.SPLIT_RESCALE, Decimal("30"), Decimal("1500"), Decimal("50")),
            (CostEffect.SPLIT_RESCALE, Decimal("15"), Decimal("1500"), Decimal("100")),
        ]
        assert [step.cost_report_change for step in result.steps[1:3]] == [Decimal("0"), Decimal("0")]
        emptied = result.steps[3]
        assert emptied.effect == CostEffect.SPLIT_RESCALE
        assert (emptied.quantity, emptied.cost_report, emptied.cost_asset) == (Decimal("0"), Decimal("0"), Decimal("0"))
        assert result.oversold_movement_ids == ()
        print_success("U8: 1500 kept through ×2 and ÷2, then emptied")

    @pytest.mark.asyncio
    async def test_u9_same_day_additions_come_before_reductions(self, forbidden_fx):
        """A sale and a purchase on one date: the purchase first, so the sale is never oversold."""
        print_section("U9 — same-day additions before reductions")
        position = CostPosition(
            key="same-day",
            asset_currency="EUR",
            movements=(
                reduction(D1, "-5", movement_id=1),
                acquisition(D1, "10", "100", "EUR", movement_id=2),
            ),
        )

        result = await compute_one(position, report_currency="EUR")

        assert forbidden_fx.calls == []
        assert movement_ids(result) == [2, 1]
        assert result.oversold_movement_ids == ()
        assert (result.quantity, result.cost_report) == (Decimal("5"), Decimal("50"))
        print_success("U9: purchase processed before the same-day sale")

    @pytest.mark.asyncio
    async def test_u9b_within_a_same_day_group_the_callers_order_is_kept(self, forbidden_fx):
        """The order is (date, additions before reductions) and nothing else: no sort by id inside a group."""
        print_section("U9b — caller order kept inside a group")
        position = CostPosition(
            key="caller-order",
            asset_currency="EUR",
            movements=(
                reduction(D1, "-1", movement_id=8),
                acquisition(D1, "3", "30", "EUR", movement_id=9),
                reduction(D1, "-2", movement_id=3),
                acquisition(D1, "7", "70", "EUR", movement_id=4),
            ),
        )

        result = await compute_one(position, report_currency="EUR")

        assert forbidden_fx.calls == []
        assert movement_ids(result) == [9, 4, 8, 3]
        assert [(step.quantity, step.cost_report) for step in result.steps] == [
            (Decimal("3"), Decimal("30")),
            (Decimal("10"), Decimal("100")),
            (Decimal("9"), Decimal("90")),
            (Decimal("7"), Decimal("70")),
        ]
        print_success("U9b: 9, 4 then 8, 3 — as the caller listed them")

    @pytest.mark.asyncio
    async def test_u10_unknown_cost_adds_quantity_and_flags_the_movement(self, forbidden_fx):
        """A TRANSFER-in without cost basis: quantity in, cost unknown — reported, never converted, never guessed."""
        print_section("U10 — unknown cost")
        position = CostPosition(key="unknown", asset_currency="USD", movements=(acquisition(D1, "10", None, None, movement_id=101, transaction_type="TRANSFER"),))

        result = await compute_one(position, report_currency="EUR")

        assert forbidden_fx.calls == [], "an unknown cost has nothing to convert, on either leg"
        step = result.steps[0]
        assert step.effect == CostEffect.ADD_UNKNOWN_COST
        assert (step.quantity, step.cost_report, step.cost_report_change, step.conversion) == (Decimal("10"), Decimal("0"), Decimal("0"), None)
        assert (step.report_complete, step.asset_complete) == (False, False)
        assert result.unknown_cost_movement_ids == (101,)
        assert (result.cost_report, result.unit_cost_report, result.report_complete) == (Decimal("0"), Decimal("0"), False)
        assert (result.missing, result.has_missing_report_fx) == ((), False)
        print_success("U10: add_unknown_cost, id 101 reported, nothing converted")


# =============================================================================
# U11–U12 — batching and the timeline
# =============================================================================


class TestBatchAndTimeline:
    @pytest.mark.asyncio
    async def test_u11_all_positions_share_one_batched_conversion(self, monkeypatch):
        """Two positions, four conversions: one convert_bulk call, one result per key."""
        print_section("U11 — one call for every position")
        fx = install_fx(
            monkeypatch,
            {
                ("GBP", "EUR"): {D1: "1.2"},
                ("EUR", "USD"): {D1: "1.25"},
                ("USD", "EUR"): {D2: "0.8"},
                ("EUR", "CHF"): {D2: "0.95"},
            },
        )
        gbp_paid = CostPosition(key=(1, 10), asset_currency="USD", movements=(acquisition(D1, "10", "100", "GBP", movement_id=111),))
        usd_paid = CostPosition(
            key=(2, 10),
            asset_currency="CHF",
            movements=(
                acquisition(D2, "4", "50", "USD", movement_id=112),
                reduction(D3, "-2", movement_id=113),
            ),
        )

        results = await compute_average_costs(object(), [gbp_paid, usd_paid], report_currency="EUR")

        assert len(fx.calls) == 1, f"one batched convert_bulk call for all positions expected, got {len(fx.calls)}"
        assert fx.requests == {
            ("GBP", Decimal("100"), "EUR", D1),
            ("EUR", Decimal("1"), "USD", D1),
            ("USD", Decimal("50"), "EUR", D2),
            ("EUR", Decimal("1"), "CHF", D2),
        }
        assert set(results) == {(1, 10), (2, 10)}
        first, second = results[(1, 10)], results[(2, 10)]
        assert (first.key, first.asset_currency, first.report_currency) == ((1, 10), "USD", "EUR")
        assert (first.quantity, first.cost_report, first.cost_asset) == (Decimal("10"), Decimal("120"), Decimal("150"))
        assert (second.key, second.asset_currency, second.report_currency) == ((2, 10), "CHF", "EUR")
        # 50 USD × 0.8 = 40 EUR, × 0.95 = 38 CHF; half sold.
        assert (second.quantity, second.cost_report, second.cost_asset) == (Decimal("2"), Decimal("20"), Decimal("19"))
        print_success("U11: two positions, one call")

    @pytest.mark.asyncio
    async def test_u11b_duplicate_position_keys_are_rejected(self, monkeypatch):
        print_section("U11b — duplicate keys")
        install_fx(monkeypatch, {})
        twin = CostPosition(key="same", asset_currency="EUR", movements=(acquisition(D1, "1", "10", "EUR", movement_id=1),))
        other = CostPosition(key="same", asset_currency="EUR", movements=())

        with pytest.raises(ValueError):
            await compute_average_costs(None, [twin, other], report_currency="EUR")
        print_success("U11b: ValueError on a repeated key")

    @pytest.mark.asyncio
    async def test_u12_state_at_step_for_and_proportional_cost(self, forbidden_fx):
        """The timeline answers 'the pool on day X' and 'after movement N'; the cost of the whole pool is exactly its cost."""
        print_section("U12 — state_at / step_for / cost_*_for")
        position = CostPosition(
            key="timeline",
            asset_currency="EUR",
            movements=(
                acquisition(D1, "1", "40", "EUR", movement_id=121),
                acquisition(D1, "2", "60", "EUR", movement_id=122),
                reduction(D3, "-1", movement_id=123),
                reduction(D4, "-2", movement_id=124),
            ),
        )

        result = await compute_one(position, report_currency="EUR")

        assert forbidden_fx.calls == []
        assert result.state_at(D1 - timedelta(days=1)) is None, "before the first movement there is no pool"
        end_of_d1 = result.state_at(D1)
        assert end_of_d1 == result.step_for(122), "a date answers with the last step of that date"
        assert (end_of_d1.quantity, end_of_d1.cost_report) == (Decimal("3"), Decimal("100"))
        assert result.state_at(D2) == end_of_d1, "between movements the pool is the one left by the previous step"
        assert result.state_at(D3) == result.step_for(123)
        assert result.state_at(D5) == result.steps[-1]
        assert result.step_for(121).quantity == Decimal("1")
        assert result.step_for(999) is None

        assert end_of_d1.cost_report_for(Decimal("3")) == Decimal("100")
        assert end_of_d1.cost_report_for(Decimal("1.5")) == Decimal("50")
        assert end_of_d1.cost_asset_for(Decimal("3")) == Decimal("100")
        assert end_of_d1.cost_asset_for(Decimal("1.5")) == Decimal("50")
        # 100 - 100/3 for 2 units: C × Q / Q would round, the whole pool must not.
        after_sale = result.step_for(123)
        assert after_sale.cost_report_for(after_sale.quantity) == after_sale.cost_report
        assert after_sale.cost_asset_for(after_sale.quantity) == after_sale.cost_asset
        emptied = result.step_for(124)
        assert emptied.quantity == Decimal("0")
        assert (emptied.cost_report_for(Decimal("1")), emptied.unit_cost_report) == (Decimal("0"), Decimal("0"))
        print_success("U12: lookups by date and id, exact cost of the whole pool")

    @pytest.mark.asyncio
    async def test_u12b_a_position_without_movements_is_an_empty_complete_pool(self, forbidden_fx):
        print_section("U12b — no movements")
        empty = CostPosition(key="empty", asset_currency="USD", movements=())

        with_leg = await compute_one(empty, report_currency="EUR")
        without_leg = await compute_one(empty, report_currency="EUR", asset_leg=False)

        assert forbidden_fx.calls == []
        assert with_leg.steps == ()
        assert (with_leg.quantity, with_leg.cost_report, with_leg.cost_asset, with_leg.unit_cost_report) == (Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"))
        assert (with_leg.report_complete, with_leg.asset_complete) == (True, True)
        assert with_leg.state_at(D1) is None
        assert (without_leg.cost_asset, without_leg.report_complete, without_leg.asset_complete) == (None, True, False)
        print_success("U12b: empty pool, complete, no call")


# =============================================================================
# U13 — cost_movement_from_transaction: the one rule "transaction → movement"
# =============================================================================


def transaction(*, tx_id=7, tx_type="BUY", day=D1, quantity="10", amount="-100", currency="USD", cbo=None, cbo_currency=None) -> SimpleNamespace:
    """A transaction-shaped object: the adapter reads these eight attributes and nothing else."""
    return SimpleNamespace(
        id=tx_id,
        type=tx_type,
        date=day,
        quantity=None if quantity is None else Decimal(quantity),
        amount=None if amount is None else Decimal(amount),
        currency=currency,
        cost_basis_override=None if cbo is None else Decimal(cbo),
        cost_basis_currency=cbo_currency,
    )


def adapt(tx: SimpleNamespace, *, split_linked: bool = False, share: Decimal | None = None) -> CostMovement | None:
    """The adapter on an ISK asset; ``share`` omitted means the default (the whole row)."""
    extra = {} if share is None else {"share": share}
    return cost_movement_from_transaction(tx, asset_currency="ISK", split_linked=split_linked, **extra)


def movement(movement_id: int | None, transaction_type: str, kind: CostMovementKind, quantity: str, cost: str | None = None, currency: str | None = None) -> CostMovement:
    return CostMovement(
        movement_id=movement_id,
        transaction_type=transaction_type,
        date=D1,
        kind=kind,
        quantity=Decimal(quantity),
        cost_amount=None if cost is None else Decimal(cost),
        cost_currency=currency,
    )


class TestTransactionAdapter:
    def test_u13_buy_costs_what_was_paid_in_the_payment_currency(self):
        print_section("U13 — BUY rows")
        for tx_type in (TransactionType.BUY, "BUY"):
            assert adapt(transaction(tx_type=tx_type)) == movement(7, "BUY", ACQ, "10", "100", "USD"), f"type given as {tx_type!r}"
        assert adapt(transaction(currency=None)) == movement(7, "BUY", ACQ, "10", "100", "ISK"), "no payment currency on the row: the asset currency"
        assert adapt(transaction(amount="100")) == movement(7, "BUY", ACQ, "10", "100", "USD"), "a mis-signed amount is still what was paid"
        assert adapt(transaction(amount="0")) == movement(7, "BUY", ACQ, "10", "0", "USD"), "no amount: a zero cost, never an unknown one"
        assert adapt(transaction(amount=None)) == movement(7, "BUY", ACQ, "10", "0", "USD")
        assert adapt(transaction(), share=Decimal("0.5")) == movement(7, "BUY", ACQ, "5", "50", "USD"), "the owner's share scales quantity and cost together"
        assert adapt(transaction(tx_id=None)) == movement(None, "BUY", ACQ, "10", "100", "USD"), "a pending row has no id yet"
        print_success("U13: BUY → acquisition at |amount| × share")

    def test_u13_transfer_or_adjustment_in_costs_its_cost_basis_override(self):
        print_section("U13 — TRANSFER / ADJUSTMENT in")
        assert adapt(transaction(tx_type=TransactionType.TRANSFER, amount="0", currency=None, cbo="12", cbo_currency="EUR")) == movement(7, "TRANSFER", ACQ, "10", "120", "EUR")
        assert adapt(transaction(tx_type="ADJUSTMENT", amount="0", currency=None, cbo="12")) == movement(7, "ADJUSTMENT", ACQ, "10", "120", "ISK"), "no cost-basis currency: the asset currency"
        assert adapt(transaction(tx_type="TRANSFER", amount="0", currency=None, cbo="12", cbo_currency="EUR"), share=Decimal("0.5")) == movement(7, "TRANSFER", ACQ, "5", "60", "EUR")
        assert adapt(transaction(tx_type=TransactionType.ADJUSTMENT, amount="0", currency=None)) == movement(7, "ADJUSTMENT", ACQ, "10"), "without a cost basis the cost is unknown, not zero"
        print_success("U13: CBO × quantity × share, or unknown")

    def test_u13_negative_quantity_is_a_reduction_whatever_the_type(self):
        print_section("U13 — reductions")
        assert adapt(transaction(tx_type=TransactionType.SELL, quantity="-5", amount="600")) == movement(7, "SELL", RED, "-5")
        assert adapt(transaction(tx_type="TRANSFER", quantity="-3", amount="0", currency=None, cbo="12", cbo_currency="EUR")) == movement(7, "TRANSFER", RED, "-3")
        assert adapt(transaction(tx_type="SELL", quantity="-5", amount="600"), share=Decimal("0.5")) == movement(7, "SELL", RED, "-2.5")
        print_success("U13: quantity < 0 → reduction, no cost")

    def test_u13_split_linked_rows_are_splits_whatever_their_sign_or_type(self):
        print_section("U13 — split-linked rows")
        assert adapt(transaction(tx_type=TransactionType.ADJUSTMENT, amount="0", currency=None), split_linked=True) == movement(7, "ADJUSTMENT", SPLIT, "10")
        assert adapt(transaction(tx_type="ADJUSTMENT", quantity="-5", amount="0", currency=None), split_linked=True) == movement(7, "ADJUSTMENT", SPLIT, "-5")
        assert adapt(transaction(tx_type="ADJUSTMENT", amount="0", currency=None), split_linked=True, share=Decimal("0.5")) == movement(7, "ADJUSTMENT", SPLIT, "5")
        as_split = adapt(transaction(tx_type="BUY"), split_linked=True)
        assert (as_split.kind, as_split.quantity, as_split.cost_amount, as_split.cost_currency) == (SPLIT, Decimal("10"), None, None), "the split link wins over the BUY type"
        print_success("U13: split link → split, signed quantity × share")

    def test_u13_rows_that_move_no_quantity_are_not_movements(self):
        print_section("U13 — rows without quantity")
        assert adapt(transaction(quantity=None)) is None
        assert adapt(transaction(quantity="0")) is None
        assert adapt(transaction(tx_type="DIVIDEND", quantity="0", amount="20")) is None
        assert adapt(transaction(), share=Decimal("0")) is None, "a 0% share moves nothing"
        assert adapt(transaction(quantity="0"), split_linked=True) is None
        print_success("U13: None for every row that moves no quantity")


# =============================================================================
# U14 — determine_target_currency
# =============================================================================


class TestTargetCurrency:
    def test_u14_the_latest_acquisition_names_the_currency(self):
        print_section("U14 — latest acquisition")
        assert determine_target_currency([acquisition(D1, "1", "10", "USD"), acquisition(D2, "1", "10", "GBP"), reduction(D3, "-1")], "CHF") == "GBP"
        assert determine_target_currency([acquisition(D2, "1", "10", "GBP"), acquisition(D1, "1", "10", "USD")], "CHF") == "GBP", "latest by date, not last in the list"
        assert determine_target_currency([acquisition(D1, "1", "0", "GBP")], "ISK") == "GBP", "a zero cost is still a cost in a currency"
        print_success("U14: GBP")

    def test_u14_a_tie_on_the_date_goes_to_the_first_in_input_order(self):
        print_section("U14 — same-date tie")
        assert determine_target_currency([acquisition(D1, "1", "10", "USD"), acquisition(D2, "1", "10", "CHF"), acquisition(D2, "1", "10", "GBP")], "EUR") == "CHF"
        assert determine_target_currency([acquisition(D2, "1", "10", "GBP"), acquisition(D2, "1", "10", "CHF")], "EUR") == "GBP"
        print_success("U14: first of the latest date")

    def test_u14_a_latest_split_or_unknown_cost_falls_back_to_the_asset_currency(self):
        print_section("U14 — split / unknown cost")
        assert determine_target_currency([acquisition(D1, "1", "10", "GBP"), split(D2, "1")], "ISK") == "ISK"
        assert determine_target_currency([acquisition(D1, "1", "10", "GBP"), acquisition(D2, "1", None, None, transaction_type="TRANSFER")], "ISK") == "ISK"
        print_success("U14: asset currency")

    def test_u14_without_any_addition_the_asset_currency(self):
        print_section("U14 — nothing added")
        assert determine_target_currency([], "ISK") == "ISK"
        assert determine_target_currency([reduction(D1, "-1")], "ISK") == "ISK"
        assert determine_target_currency([split(D1, "-5")], "ISK") == "ISK"
        print_success("U14: asset currency")


# =============================================================================
# U15 — CostMovement refuses what cannot be a movement
# =============================================================================


def _movement_kwargs(**overrides) -> dict:
    base = {"movement_id": 1, "transaction_type": "BUY", "date": D1, "kind": ACQ, "quantity": Decimal("1"), "cost_amount": Decimal("10"), "cost_currency": "EUR"}
    return {**base, **overrides}


class TestMovementValidation:
    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param(_movement_kwargs(quantity=Decimal("0")), id="acquisition-zero-quantity"),
            pytest.param(_movement_kwargs(kind=RED, quantity=Decimal("0"), cost_amount=None, cost_currency=None), id="reduction-zero-quantity"),
            pytest.param(_movement_kwargs(kind=SPLIT, quantity=Decimal("0"), cost_amount=None, cost_currency=None), id="split-zero-quantity"),
            pytest.param(_movement_kwargs(quantity=Decimal("-1")), id="acquisition-negative-quantity"),
            pytest.param(_movement_kwargs(kind=RED, quantity=Decimal("1"), cost_amount=None, cost_currency=None), id="reduction-positive-quantity"),
            pytest.param(_movement_kwargs(kind=RED, quantity=Decimal("-1")), id="reduction-with-cost"),
            pytest.param(_movement_kwargs(kind=SPLIT, quantity=Decimal("1")), id="split-with-cost"),
            pytest.param(_movement_kwargs(cost_currency=None), id="cost-without-currency"),
        ],
    )
    def test_u15_invalid_movements_are_rejected(self, kwargs):
        with pytest.raises(ValueError):
            CostMovement(**kwargs)

    def test_u15_valid_edge_movements_are_accepted(self):
        print_section("U15 — accepted edges")
        assert CostMovement(**_movement_kwargs(cost_amount=Decimal("-10"))).cost_amount == Decimal("-10"), "no sign check on the cost"
        assert CostMovement(**_movement_kwargs(kind=SPLIT, quantity=Decimal("-5"), cost_amount=None, cost_currency=None)).quantity == Decimal("-5"), "a split may shrink the quantity"
        assert CostMovement(**_movement_kwargs(cost_amount=None, cost_currency=None)).cost_amount is None, "an unknown cost is a valid acquisition"
        print_success("U15: negative cost, negative split, unknown cost accepted")


# =============================================================================
# U16 — cases carried over from deleted tests
# =============================================================================
#
# test_financial_utils.py tested wac_utils.compute_wac_from_txlist, deleted with this module's
# arrival. Its cases live on above: FU-1 → U12b, FU-3/FU-4 → U1, FU-5 → U9, FU-6 → U7,
# FU-7 → U13, FU-11 → U7, FU-13/FU-14 → U8, FU-9/FU-10 → U14. FU-8 changed meaning on purpose:
# a transfer-in without cost basis is an unknown cost now (U10), no longer a zero one; a free
# acquisition is still ADD_ZERO_COST (U1). The FU cases below had no equivalent, nor had the
# cost-basis currency rule of the lots service's former per-row WAC conversion.


class TestCarriedOverFromWacUtils:
    @pytest.mark.asyncio
    async def test_u16_repeated_sales_keep_the_unit_cost_of_a_single_purchase(self, forbidden_fx):
        """FU-2 + FU-12: 20 bought for 1000 cost 50 each; three sales of 5 take 250 each and leave 50 per unit."""
        print_section("U16 — one purchase, three sales")
        position = CostPosition(
            key="single-purchase",
            asset_currency="EUR",
            movements=(
                acquisition(D1, "20", "1000", "EUR", movement_id=161),
                reduction(D2, "-5", movement_id=162),
                reduction(D3, "-5", movement_id=163),
                reduction(D4, "-5", movement_id=164),
            ),
        )

        result = await compute_one(position, report_currency="EUR")

        assert forbidden_fx.calls == []
        assert [(step.movement.movement_id, step.effect, step.quantity, step.cost_report, step.cost_report_change, step.unit_cost_report) for step in result.steps] == [
            (161, CostEffect.ADD, Decimal("20"), Decimal("1000"), Decimal("1000"), Decimal("50")),
            (162, CostEffect.REDUCE, Decimal("15"), Decimal("750"), Decimal("-250"), Decimal("50")),
            (163, CostEffect.REDUCE, Decimal("10"), Decimal("500"), Decimal("-250"), Decimal("50")),
            (164, CostEffect.REDUCE, Decimal("5"), Decimal("250"), Decimal("-250"), Decimal("50")),
        ]
        print_success("U16: 50 per unit from the purchase to the last sale")

    @pytest.mark.asyncio
    async def test_u16_a_sale_after_a_split_takes_the_rescaled_unit_cost(self, forbidden_fx):
        """FU-16: 15 bought for 1500, split 2:1 → 30 at 50; selling 10 takes 500 and leaves 20 at 50."""
        print_section("U16 — split, then a sale")
        position = CostPosition(
            key="split-then-sale",
            asset_currency="EUR",
            movements=(
                acquisition(D1, "15", "1500", "EUR", movement_id=165),
                split(D2, "15", movement_id=166),
                reduction(D3, "-10", movement_id=167),
            ),
        )

        result = await compute_one(position, report_currency="EUR")

        assert forbidden_fx.calls == []
        assert [(step.effect, step.quantity, step.cost_report, step.cost_report_change, step.unit_cost_report) for step in result.steps] == [
            (CostEffect.ADD, Decimal("15"), Decimal("1500"), Decimal("1500"), Decimal("100")),
            (CostEffect.SPLIT_RESCALE, Decimal("30"), Decimal("1500"), Decimal("0"), Decimal("50")),
            (CostEffect.REDUCE, Decimal("20"), Decimal("1000"), Decimal("-500"), Decimal("50")),
        ]
        print_success("U16: the sale takes 10 × 50, not 10 × 100")

    def test_u16_a_split_linked_row_ignores_a_stray_cost_basis(self):
        """FU-15: an ADJUSTMENT linked to a split carries no cost, even with a cost_basis_override of 999 on the row."""
        print_section("U16 — split link over a stray cost basis")
        stray = transaction(tx_type=TransactionType.ADJUSTMENT, quantity="15", amount="0", currency=None, cbo="999", cbo_currency="EUR")

        assert adapt(stray, split_linked=True) == movement(7, "ADJUSTMENT", SPLIT, "15")
        # Control: without the link the same row is an acquisition at its cost basis — the link is what drops it.
        assert adapt(stray) == movement(7, "ADJUSTMENT", ACQ, "15", "14985", "EUR")
        print_success("U16: split, no cost; 14985 EUR only without the link")

    def test_u16_an_adjustment_in_is_costed_in_its_cost_basis_currency_not_the_rows(self):
        """Carried over from the lots service's WAC-row tests: cost_basis_currency names the currency, tx.currency does not."""
        print_section("U16 — cost-basis currency over the row's currency")
        opening = transaction(tx_type=TransactionType.ADJUSTMENT, quantity="10", amount="0", currency="GBP", cbo="5", cbo_currency="USD")

        assert adapt(opening) == movement(7, "ADJUSTMENT", ACQ, "10", "50", "USD")
        print_success("U16: 50 USD, not GBP")
