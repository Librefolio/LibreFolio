"""W-B94 road (b) — an unpriced asset transferred in from outside the scope is valued at its transfer cost as a price.

Module under test: ``backend/app/services/financial_math/portfolio/daily_state.py`` (``DailyStateBuilder``: valuation,
``transaction_implied_asset_ids``, the in-kind capital of a TRANSFER leg with no internal partner), fed the way
``PortfolioCalculationEngine.calculate`` feeds it — the mark series from ``build_asset_price_series`` over the scope's
transactions, the average costs from the same rate map. The rule itself lives in
``backend/app/services/financial_math/price_marks.py``; its pure tests are
``test_financial_math/test_price_marks_transfer_estimate.py``.

Developer decision (30/10/2026, W-B94 road (b)): the cost of an incoming TRANSFER leg (``cost_basis_override`` per unit,
in ``cost_basis_currency``) is an estimated observation (kind TRADE) when the asset has no quote and no BUY/SELL on or
before that day. For the portfolio this moves such an asset from ``ESTIMATED_AT_COST`` (its book cost, converted at the
acquisition day's rate and then frozen) to ``LAST_TRADE_PRICE`` (the transfer's unit cost in its own currency, converted
at each day's rate, the asset in the transaction-implied set). The in-kind capital of the leg — at market value on its
own day — stays equal to the cost it brings, so the transfer is neutral on its day.

Scenario: report EUR; broker B = 20 is the scope; asset X = 500, a USD stock never quoted nor traded; on D1 B receives
10 units of X by a TRANSFER with a cost basis of 50 USD a unit, its other leg outside the scope — an orphan
(``TestOrphanTransferIn``: no partner at all) or a leg at broker A = 10 outside the scope (``TestLinkedExternalTransferIn``,
classified ``linked_external_inflow`` by the real classifier). USD→EUR 0.9 on D1, 0.8 on D2, 0.7 on D3, so the cost is
10 × 50 × 0.9 = 450 EUR.

=====  ========================================  ===========================================
day    HEAD (ESTIMATED_AT_COST)                  after the fix (LAST_TRADE_PRICE)
=====  ========================================  ===========================================
D1     value 450, capital 450, P&L 0             value 450, capital 450, P&L 0
D2     value 450, capital 450, P&L 0             value 400, capital 450, P&L -50
D3     value 450, capital 450, P&L 0             value 350, capital 450, P&L -100
=====  ========================================  ===========================================

RED on HEAD ``b6a8b1625``: ``test_valued_at_the_transfer_cost_converted_at_each_days_rate``,
``test_the_asset_is_transaction_implied`` and ``test_the_closing_position_reports_the_transfer_cost_as_its_price`` of
both classes (HEAD: ``ESTIMATED_AT_COST`` 450 every day, the implied set empty, no effective price). Declared parity
guards, green on HEAD and after the fix: ``test_the_transfer_is_neutral_on_its_day`` of both classes (capital = value =
450 on D1, P&L 0, one market-value transfer of capital and cost 450, no cash flow) and
``TestQuotedAssetTransferredInAtAWeekend`` (an asset quoted 200 USD on FRI transferred in on SAT at a cost of 50: valued
at the carried quote, capital at that market value — never the transfer's 50).

Pure tests — no DB, no server, no network. Helpers are copies of ``test_daily_state_builder.py`` (this directory has no
cross-test-module imports). Runs in ``./dev.py test services roi-fifo-utils`` (the whole of ``test_financial/``);
alone: ``./dev.py test services transfer-cost-estimate``.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from backend.app.db.models import TransactionType
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, PortfolioCalculationResult, ValuationSource
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A, B = 10, 20
X = 500
D1, D2, D3 = date(2025, 1, 1), date(2025, 1, 2), date(2025, 1, 3)
FRI, SAT, SUN = date(2025, 1, 3), date(2025, 1, 4), date(2025, 1, 5)
USD_EUR = {("USD", "EUR", D1): Decimal("0.9"), ("USD", "EUR", D2): Decimal("0.8"), ("USD", "EUR", D3): Decimal("0.7")}

# =============================================================================
# HELPERS — copies of test_daily_state_builder.py
# =============================================================================


def _tx(
    *,
    id: int,
    broker_id: int = B,
    type: str = "TRANSFER",
    dt: date = D1,
    amount: str | None = None,
    currency: str | None = None,
    quantity: str = "0",
    asset_id: int | None = X,
    related_id: int | None = None,
    cost_basis_override: str | None = None,
    cost_basis_currency: str | None = None,
) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.broker_id = broker_id
    tx.type = TransactionType(type)
    tx.date = dt
    tx.amount = Decimal(amount) if amount is not None else None
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = related_id
    tx.cost_basis_override = Decimal(cost_basis_override) if cost_basis_override else None
    tx.cost_basis_currency = cost_basis_currency
    tx.asset_event_id = None
    return tx


def _ctxn(tx: MagicMock, classification: str = "normal", paired: MagicMock | None = None) -> ClassifiedTransaction:
    return ClassifiedTransaction(tx=tx, classification=classification, share=Decimal("1"), paired_tx=paired)


def _mark_series_from(classified_txs, price_map, asset_currencies):
    """Mirror PortfolioCalculationEngine: one AssetPriceSeries per asset from its quotes and the scope's rows."""
    txs_by_asset: dict[int, list] = {}
    for ctxn in classified_txs:
        if ctxn.tx.asset_id is not None:
            txs_by_asset.setdefault(ctxn.tx.asset_id, []).append(ctxn.tx)
    mark_series = {}
    for aid in set(txs_by_asset) | set(price_map):
        series = build_asset_price_series(
            price_rows=price_map.get(aid, []),
            transactions=txs_by_asset.get(aid, []),
            split_linked_tx_ids=set(),
            asset_currency=asset_currencies.get(aid, "EUR"),
            quote_base_quantity=1,
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _build(classified, *, date_from: date = D1, date_to: date = D3, fx_rate_map=None, price_map=None, external_cash_flows=None) -> PortfolioCalculationResult:
    """The states date_from..date_to of a classified ledger: X is a USD "Stock" with no classification, report EUR."""
    fx_rate_map = USD_EUR if fx_rate_map is None else fx_rate_map
    price_map = price_map or {}
    asset_currencies = {X: "USD"}
    return DailyStateBuilder(
        classified_txs=classified,
        in_transit_intervals=[],
        external_cash_flows=external_cash_flows or [],
        price_map=price_map,
        quote_base_map={},
        fx_rate_map=fx_rate_map,
        asset_classifications={X: None},
        asset_types={X: "Stock"},
        asset_currencies=asset_currencies,
        mark_series=_mark_series_from(classified, price_map, asset_currencies),
        average_costs=engine_average_costs(classified, asset_currencies=asset_currencies, target_currency="EUR", fx_rate_map=fx_rate_map, date_to=date_to),
        native_cash=engine_native_cash(classified, target_currency="EUR", fx_rate_map=fx_rate_map, date_to=date_to),
        target_currency="EUR",
        date_from=date_from,
        date_to=date_to,
    ).build()


def _day_problems(states, day: date, **expected) -> list[str]:
    """Mismatches between the DailyPortfolioState of ``day`` and ``expected`` (field -> value)."""
    state = next((s for s in states if s.date == day), None)
    if state is None:
        return [f"{day}: no state emitted"]
    return [f"{day}: {name}={getattr(state, name)!r}, expected {want!r}" for name, want in expected.items() if getattr(state, name) != want]


def _orphan_transfer_in() -> list[ClassifiedTransaction]:
    """B receives 10 X on D1 by a TRANSFER with no partner (``related_transaction_id`` None): classification normal."""
    return [_ctxn(_tx(id=1, quantity="10", cost_basis_override="50", cost_basis_currency="USD"))]


def _linked_external_transfer_in() -> list[ClassifiedTransaction]:
    """B receives 10 X on D1 from A, outside the scope: the real classifier, B's row only (as the engine loads the
    scope's rows), A's leg handed over as ``external_paired``."""
    giving = _tx(id=1, broker_id=A, quantity="-10", related_id=2, cost_basis_override="50", cost_basis_currency="USD")
    receiving = _tx(id=2, broker_id=B, quantity="10", related_id=1, cost_basis_override="50", cost_basis_currency="USD")
    classification = ScopeAwareTransactionClassifier(scope_broker_ids={B}, all_transactions=[receiving], broker_shares={B: Decimal("1")}).classify(external_paired={1: giving})
    assert [c.classification for c in classification.classified] == ["linked_external_inflow"], "precondition: the leg crosses the scope"
    return classification.classified


class _TransferInFromOutside:
    """The four checks, for the ledger ``_ledger`` builds (an orphan or a linked-external TRANSFER-in)."""

    @staticmethod
    def _ledger() -> list[ClassifiedTransaction]:
        raise NotImplementedError

    def test_valued_at_the_transfer_cost_converted_at_each_days_rate(self):
        """D1..D3: LAST_TRADE_PRICE at 50 USD × each day's rate — 450, 400, 350; capital 450; P&L 0, -50, -100.

        HEAD: ESTIMATED_AT_COST — 450 every day, P&L 0 every day (the cost frozen at D1's rate)."""
        result = _build(self._ledger())
        problems: list[str] = []
        for day, value, pnl in ((D1, "450", "0"), (D2, "400", "-50"), (D3, "350", "-100")):
            problems += _day_problems(
                result.daily_states,
                day,
                market_value=Decimal(value),
                nav_value=Decimal(value),
                cumulative_external_cash_flow=Decimal("450"),
                total_pnl=Decimal(pnl),
                missing_price_asset_ids=set(),
                nav_complete=True,
            )
        assert not problems, "\n".join(problems)

    def test_the_asset_is_transaction_implied(self):
        """Valued from a trade-derived mark, X is in the implied set every day, with no market quote before it.

        HEAD: the implied set is empty (an at-cost valuation is not transaction-implied)."""
        result = _build(self._ledger())
        problems: list[str] = []
        for day in (D1, D2, D3):
            problems += _day_problems(result.daily_states, day, transaction_implied_asset_ids={X}, transaction_implied_last_quote_dates={X: None})
        assert not problems, "\n".join(problems)

    def test_the_closing_position_reports_the_transfer_cost_as_its_price(self):
        """D3's position: LAST_TRADE_PRICE, effective and reference price 50 USD observed on D1 (two days back: not
        stale), market value 350 against a cost basis of 450, unrealized -100.

        HEAD: ESTIMATED_AT_COST, market value 450, no effective or reference price, unrealized 0."""
        result = _build(self._ledger())
        (position,) = result.position_states_end
        expected = {
            "valuation_source": ValuationSource.LAST_TRADE_PRICE,
            "market_value": Decimal("350"),
            "cost_basis": Decimal("450"),
            "unrealized_pnl": Decimal("-100"),
            "valuation_effective_unit_price": Decimal("50"),
            "valuation_effective_currency": "USD",
            "valuation_reference_date": D1,
            "valuation_reference_unit_price": Decimal("50"),
            "valuation_reference_currency": "USD",
            "valuation_stale": False,
            "missing_fx_pair": None,
        }
        problems = [f"{position.date}/asset {position.asset_id}: {name}={getattr(position, name)!r}, expected {want!r}" for name, want in expected.items() if getattr(position, name) != want]
        assert not problems, "\n".join(problems)

    def test_the_transfer_is_neutral_on_its_day(self):
        """Parity guard: on D1 the in-kind capital equals the value the leg brings — 450 either way (at cost on HEAD, at
        50 USD × 0.9 after the fix) — so P&L 0; one market-value transfer of capital and cost 450; no cash flow."""
        result = _build(self._ledger())
        problems = _day_problems(result.daily_states, D1, market_value=Decimal("450"), cumulative_external_cash_flow=Decimal("450"), total_pnl=Decimal("0"), external_cash_flow=Decimal("0"))
        assert not problems, "\n".join(problems)
        transfers = [(t.date, t.broker_id, t.asset_id, t.capital, t.cost) for t in result.market_value_transfers]
        assert transfers == [(D1, B, X, Decimal("450"), Decimal("450"))]


class TestOrphanTransferIn(_TransferInFromOutside):
    @staticmethod
    def _ledger() -> list[ClassifiedTransaction]:
        return _orphan_transfer_in()


class TestLinkedExternalTransferIn(_TransferInFromOutside):
    @staticmethod
    def _ledger() -> list[ClassifiedTransaction]:
        return _linked_external_transfer_in()


class TestQuotedAssetTransferredInAtAWeekend:
    """Parity guard (green on HEAD and after the fix): X quoted 200 USD up to FRI, 10 units transferred in from outside
    on SAT at a cost of 50 USD. USD→EUR 0.9 FRI..SUN. SAT and SUN: MARKET_PRICE at FRI's 200 carried — value 1 800, and
    the leg's capital is that market value (1 800), so P&L 0; never the transfer's 50 (450)."""

    def test_the_carried_quote_values_the_position_and_the_leg(self):
        rates = {("USD", "EUR", day): Decimal("0.9") for day in (FRI, SAT, SUN)}
        ledger = [_ctxn(_tx(id=1, dt=SAT, quantity="10", cost_basis_override="50", cost_basis_currency="USD"))]
        result = _build(ledger, date_from=FRI, date_to=SUN, fx_rate_map=rates, price_map={X: [(FRI, Decimal("200"), "USD")]})
        problems: list[str] = []
        for day in (SAT, SUN):
            problems += _day_problems(
                result.daily_states,
                day,
                market_value=Decimal("1800"),
                cumulative_external_cash_flow=Decimal("1800"),
                total_pnl=Decimal("0"),
                transaction_implied_asset_ids=set(),
            )
        assert not problems, "\n".join(problems)
        (position,) = result.position_states_end
        assert (position.valuation_source, position.valuation_reference_date, position.valuation_reference_unit_price) == (ValuationSource.MARKET_PRICE, FRI, Decimal("200"))
