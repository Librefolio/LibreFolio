"""Pin of the Decimal exponents of an EUR-only portfolio (lot 41, step F-0 (e)).

Step F moves the engine's cash onto native per-currency balances. For a portfolio that
only ever sees the report currency nothing may change, down to the Decimal exponent:
``Decimal("1100.00000000")`` and ``Decimal("1100")`` compare equal as numbers, but their
``str()`` differ, and so do the API payloads built from them. Every assertion below is on
``str(value)``, never on the number, so a change of exponent is a failure.

The scenario mixes exponents on purpose (``1000.00``, ``200.0``, ``-123.456``, ``1.5``,
``-0.25``) and uses a fractional share (0.500000), whose six decimals add to the exponent
of every amount scaled by it. The expected strings come from an oracle run of the builder
before step F: step F must not change any of them.

Notation: target EUR; brokers A = 10 (share 1.000000) and B = 20 (share 0.500000); asset
X = 100 priced in EUR; D0 = 2025-01-01, D1 = 2025-01-02, D2 = 2025-01-03.

- D0: DEPOSIT 1000.00 at A, DEPOSIT 200.0 at B;
- D1: BUY 3 X for -123.456 at A (X quoted 41.152);
- D2: DIVIDEND 1.5 on X at A, FEE -0.25 at B (no asset) (X quoted 42.5).

Pure tests — no DB, no server. The helpers are copies of test_broker_internal_flows.py
(this directory has no cross-test-module imports).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.engine import (
    ClassifiedTransaction,
    DailyStateBuilder,
    PortfolioCalculationResult,
)
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A, B = 10, 20
X = 100
SHARE_A = "1.000000"
SHARE_B = "0.500000"

D0 = date(2025, 1, 1)
D1 = date(2025, 1, 2)
D2 = date(2025, 1, 3)
DAYS = (D0, D1, D2)

# =============================================================================
# HELPERS — copies of test_broker_internal_flows.py:77-180
# =============================================================================


def _tx(
    *,
    id: int = 1,
    broker_id: int = 10,
    type: str = "DEPOSIT",
    dt: str | date = "2025-01-01",
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
    tx.date = dt if isinstance(dt, date) else date.fromisoformat(dt)
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = related_id
    tx.cost_basis_override = Decimal(cost_basis_override) if cost_basis_override else None
    tx.cost_basis_currency = cost_basis_currency
    return tx


def _ctxn(
    tx: MagicMock,
    classification: str = "normal",
    share: str = "1",
    paired: MagicMock | None = None,
) -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification=classification, share=Decimal(share), paired_tx=paired)


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
    """The kwargs ``_builder`` passes to DailyStateBuilder: defaults, overrides, then the
    mark series, average costs and native cash computed once."""
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
        "date_from": date(2025, 1, 1),
        "date_to": date(2025, 1, 1),
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


def _builder(**overrides) -> DailyStateBuilder:
    """Create a DailyStateBuilder with sensible defaults, overriding any kwarg."""
    return DailyStateBuilder(**_builder_kwargs(**overrides))


def _build(**overrides):
    return _builder(**overrides).build()


# =============================================================================
# SCENARIO AND EXPECTED STRINGS (oracle run before step F)
# =============================================================================


def _scenario_overrides() -> dict:
    """The builder kwargs of the scenario in the module docstring."""
    classified = [
        _ctxn(_tx(id=1, broker_id=A, type="DEPOSIT", dt=D0, amount="1000.00"), share=SHARE_A),
        _ctxn(_tx(id=2, broker_id=B, type="DEPOSIT", dt=D0, amount="200.0"), share=SHARE_B),
        _ctxn(_tx(id=3, broker_id=A, type="BUY", dt=D1, amount="-123.456", quantity="3", asset_id=X), share=SHARE_A),
        _ctxn(_tx(id=4, broker_id=A, type="DIVIDEND", dt=D2, amount="1.5", asset_id=X), share=SHARE_A),
        _ctxn(_tx(id=5, broker_id=B, type="FEE", dt=D2, amount="-0.25"), share=SHARE_B),
    ]
    return {
        "classified_txs": classified,
        "external_cash_flows": [
            (D0, A, Decimal("1000.00") * Decimal(SHARE_A), "EUR"),
            (D0, B, Decimal("200.0") * Decimal(SHARE_B), "EUR"),
        ],
        "price_map": {X: [(D1, Decimal("41.152"), "EUR"), (D2, Decimal("42.5"), "EUR")]},
        "asset_currencies": {X: "EUR"},
        "date_from": D0,
        "date_to": D2,
    }


# field -> str() on (D0, D1, D2)
EXPECTED_DAILY: dict[str, tuple[str, str, str]] = {
    "cash_value": ("1100.00000000", "976.544000000", "977.919000000"),
    "market_value": ("0", "123.456000000", "127.5000000"),
    "nav_value": ("1100.00000000", "1100.000000000", "1105.419000000"),
    "open_cost_basis": ("0", "123.456000000", "123.456000000"),
    "book_value": ("1100.00000000", "1100.000000000", "1101.375000000"),
    "unrealized_gain_loss": ("0E-8", "0E-9", "4.044000000"),
    "external_cash_flow": ("1100.00000000", "0", "0"),
    "cumulative_external_cash_flow": ("1100.00000000", "1100.00000000", "1100.00000000"),
    "cash_from_contributed_capital": ("1100.00000000", "976.544000000", "976.419000000"),
    "cash_from_generated_returns": ("0E-8", "0E-9", "1.500000000"),
    "total_pnl": ("0E-8", "0E-9", "5.419000000"),
    "in_transit_market_value": ("0", "0", "0"),
}

# broker -> str() of (nav_contribution, capital_contribution, pnl_contribution) on D0, D1, D2
EXPECTED_BROKERS: dict[int, tuple[tuple[str, str, str], ...]] = {
    A: (
        ("1000.00000000", "1000.00000000", "0E-8"),
        ("1000.000000000", "1000.00000000", "0E-9"),
        ("1005.544000000", "1000.00000000", "5.544000000"),
    ),
    B: (
        ("100.0000000", "100.0000000", "0E-7"),
        ("100.0000000", "100.0000000", "0E-7"),
        ("99.87500000", "100.0000000", "-0.12500000"),
    ),
}

EXPECTED_D2_BY_TYPE = {"Liquidity": "977.919000000", "Unknown": "127.5000000"}
EXPECTED_CAPITAL_POOL = {A: "876.544000000", B: "99.87500000"}
EXPECTED_RETURNS_POOL = {A: "1.5000000", B: "0"}


@pytest.fixture(scope="module")
def result() -> PortfolioCalculationResult:
    return _build(**_scenario_overrides())


def _states_by_day(result: PortfolioCalculationResult, problems: list[str]) -> dict:
    """The daily states keyed by date; a missing day is recorded as a problem."""
    states = {state.date: state for state in result.daily_states}
    problems.extend(f"{day}: no daily state" for day in DAYS if day not in states)
    return states


def _str_map(values: dict) -> dict:
    return {key: str(value) for key, value in values.items()}


# =============================================================================
# TESTS
# =============================================================================


class TestEurCashExponents:
    """``str()`` of every EUR amount of the scenario, exponent included."""

    def test_daily_aggregates_keep_their_exponents(self, result):
        problems: list[str] = []
        states = _states_by_day(result, problems)
        for field_name, wanted_by_day in EXPECTED_DAILY.items():
            for day, want in zip(DAYS, wanted_by_day, strict=True):
                if day not in states:
                    continue
                got = str(getattr(states[day], field_name))
                if got != want:
                    problems.append(f"{day} {field_name}: expected {want}, got {got}")
        assert not problems, "\n".join(problems)

    def test_broker_contributions_keep_their_exponents(self, result):
        """nav / capital / pnl of each broker, and an in-transit part of 0 every day."""
        problems: list[str] = []
        states = _states_by_day(result, problems)
        for broker_id, wanted_by_day in EXPECTED_BROKERS.items():
            for day, wanted in zip(DAYS, wanted_by_day, strict=True):
                if day not in states:
                    continue
                contribution = states[day].broker_contributions.get(broker_id)
                if contribution is None:
                    problems.append(f"{day} broker {broker_id}: no contribution")
                    continue
                actual = (
                    str(contribution.nav_contribution),
                    str(contribution.capital_contribution),
                    str(contribution.pnl_contribution),
                    str(contribution.in_transit_contribution),
                )
                for field_name, got, want in zip(("nav_contribution", "capital_contribution", "pnl_contribution", "in_transit_contribution"), actual, (*wanted, "0"), strict=True):
                    if got != want:
                        problems.append(f"{day} broker {broker_id} {field_name}: expected {want}, got {got}")
        assert not problems, "\n".join(problems)

    def test_type_breakdown_keeps_its_exponents(self, result):
        """D2: cash as Liquidity, X (no asset type given) as Unknown."""
        problems: list[str] = []
        states = _states_by_day(result, problems)
        if D2 in states:
            got = _str_map(states[D2].by_type)
            if got != EXPECTED_D2_BY_TYPE:
                problems.append(f"{D2} by_type: expected {EXPECTED_D2_BY_TYPE}, got {got}")
        assert not problems, "\n".join(problems)

    def test_end_pools_keep_their_exponents(self, result):
        """Capital (K) and returns (R) pools per broker at date_to."""
        problems: list[str] = []
        capital = _str_map(result.end_state.capital_pool)
        returns = _str_map(result.end_state.returns_pool)
        if capital != EXPECTED_CAPITAL_POOL:
            problems.append(f"end_state.capital_pool: expected {EXPECTED_CAPITAL_POOL}, got {capital}")
        if returns != EXPECTED_RETURNS_POOL:
            problems.append(f"end_state.returns_pool: expected {EXPECTED_RETURNS_POOL}, got {returns}")
        assert not problems, "\n".join(problems)
