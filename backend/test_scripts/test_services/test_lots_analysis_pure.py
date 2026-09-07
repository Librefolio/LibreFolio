"""Pure-calculation tests for LotsAnalysisService's private builders.

Isolation: PURE. Every helper exercised here is a *synchronous* method that
receives all of its inputs as arguments and never touches ``self.db``. The
service is therefore instantiated with ``db=None``: no session, no server, no
shared row is read or written, so this unit can run beside anything.

Why these tests exist. The public entry point ``get_lots_analysis`` is covered
by the API/e2e suites, but only over the mock dataset, which contains a single
shape of portfolio: LONG lots, a dense daily price series, and plain BUY/SELL
transactions. Everything the builders do for the *other* shapes a real user
produces -- a SHORT position, an unlisted asset with no price history at all
(``estimated_mode``), a gap in the price series, a manual ADJUSTMENT carrying a
cost-basis override, a share grant bought for zero, a transfer that crosses the
analysis scope -- was never executed. These are the branches pinned below.

Data doubles are built by hand from the FIFO engine's frozen dataclasses rather
than by running the engine, so each test states exactly the one situation it is
about and nothing else can drift into it.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

import backend.app.services.lots_analysis_service as module
from backend.app.db.models import PriceHistory, Transaction, TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import LotAnalysisType
from backend.app.services.fifo_lot_engine import (
    FifoEngineResult,
    FifoEvent,
    FifoLot,
    FragmentInterval,
    LotClosure,
)
from backend.app.services.lots_analysis_service import (
    LotsAnalysisService,
    _FxRateResolver,
    _parse_transfer_pair_id,
    _PerformanceSourceContext,
    _PriceHistoryLookup,
)
from backend.app.utils.financial.wac_utils import WACInputTX

# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #

D = Decimal


def _svc() -> LotsAnalysisService:
    """The service with no session: only sync, argument-driven helpers are used."""
    return LotsAnalysisService(db=None)


def _resolver(target: str = "EUR", rates: dict | None = None) -> _FxRateResolver:
    """An _FxRateResolver with its rate table already populated.

    ``load()`` is the only async part of the resolver and the only part that
    needs a session; it merely fills ``_rates`` with one converted unit per
    (currency, date). Filling that table directly is what keeps this unit PURE.
    """
    resolver = _FxRateResolver(target)
    for key, rate in (rates or {}).items():
        resolver._rates[key] = rate
    return resolver


def _lot(
    lot_id: int = 1,
    *,
    direction: str = "LONG",
    opening_date: date = date(2024, 1, 10),
    original_quantity: Decimal = D("100"),
    opening_unit_price: Decimal = D("10"),
    original_cost: Decimal = D("1000"),
    currency: str | None = "EUR",
    open_quantity: Decimal = D("100"),
    **kwargs,
) -> FifoLot:
    return FifoLot(
        lot_id=lot_id,
        asset_id=kwargs.pop("asset_id", 7),
        direction=direction,
        opening_transaction_id=kwargs.pop("opening_transaction_id", 100 + lot_id),
        opening_broker_id=kwargs.pop("opening_broker_id", 1),
        opening_date=opening_date,
        original_quantity=original_quantity,
        opening_unit_price=opening_unit_price,
        original_cost=original_cost,
        currency=currency,
        open_quantity=open_quantity,
        **kwargs,
    )


def _fragment(
    lot_id: int = 1,
    *,
    fragment_id: str = "frag-1",
    direction: str = "LONG",
    custody_type: str = "BROKER",
    quantity: Decimal = D("100"),
    unit_price: Decimal = D("10"),
    start_date: date = date(2024, 1, 10),
    broker_id: int | None = 1,
    end_date: date | None = None,
    **kwargs,
) -> FragmentInterval:
    return FragmentInterval(
        fragment_id=fragment_id,
        lot_id=lot_id,
        direction=direction,
        custody_type=custody_type,
        quantity=quantity,
        unit_price=unit_price,
        start_date=start_date,
        broker_id=broker_id,
        end_date=end_date,
        **kwargs,
    )


def _closure(
    lot_id: int = 1,
    *,
    transaction_id: int = 500,
    quantity: Decimal = D("40"),
    close_date: date = date(2024, 2, 1),
    close_reason: str = "SELL",
    fragment_id: str = "frag-1",
    open_unit_price: Decimal = D("10"),
    close_unit_price: Decimal = D("12"),
    realized_pnl: Decimal = D("80"),
    proceeds: Decimal = D("480"),
) -> LotClosure:
    return LotClosure(
        lot_id=lot_id,
        transaction_id=transaction_id,
        quantity=quantity,
        close_date=close_date,
        close_reason=close_reason,
        fragment_id=fragment_id,
        open_unit_price=open_unit_price,
        close_unit_price=close_unit_price,
        realized_pnl=realized_pnl,
        proceeds=proceeds,
    )


def _tx(
    tx_id: int = 1,
    *,
    tx_type: TransactionType = TransactionType.BUY,
    tx_date: date = date(2024, 1, 10),
    quantity: Decimal = D("100"),
    amount: Decimal = D("-1000"),
    currency: str | None = "EUR",
    broker_id: int = 1,
    asset_id: int | None = 7,
    cost_basis_override: Decimal | None = None,
    cost_basis_currency: str | None = None,
) -> Transaction:
    """An in-memory Transaction row. Never added to a session."""
    return Transaction(
        id=tx_id,
        broker_id=broker_id,
        asset_id=asset_id,
        type=tx_type,
        date=tx_date,
        quantity=quantity,
        amount=amount,
        currency=currency,
        cost_basis_override=cost_basis_override,
        cost_basis_currency=cost_basis_currency,
    )


def _price(day: date, close: Decimal | None = D("11"), currency: str = "EUR") -> PriceHistory:
    return PriceHistory(asset_id=7, date=day, close=close, currency=currency)


def _engine_result(
    *,
    lots: list[FifoLot] | None = None,
    fragments: list[FragmentInterval] | None = None,
    closures: list[LotClosure] | None = None,
    events: list[FifoEvent] | None = None,
) -> FifoEngineResult:
    return FifoEngineResult(
        asset_id=7,
        classified_events=events or [],
        lots=lots or [],
        fragment_intervals=fragments or [],
        closures=closures or [],
        issues=[],
    )


def _perf_context(
    *,
    transactions: list[Transaction] | None = None,
    engine_result: FifoEngineResult | None = None,
    lots_by_id: dict[int, FifoLot] | None = None,
    fragments_by_lot: dict[int, list[FragmentInterval]] | None = None,
    closures_by_lot: dict[int, list[LotClosure]] | None = None,
    tx_by_id: dict[int, Transaction] | None = None,
) -> _PerformanceSourceContext:
    txs = transactions if transactions is not None else []
    return _PerformanceSourceContext(
        transactions=txs,
        engine_result=engine_result or _engine_result(),
        lots_by_id=lots_by_id or {},
        fragments_by_lot=fragments_by_lot or {},
        closures_by_lot=closures_by_lot or {},
        tx_by_id=tx_by_id if tx_by_id is not None else {tx.id: tx for tx in txs},
    )


def _days(start: date, count: int) -> list[date]:
    return [start + timedelta(days=offset) for offset in range(count)]


# --------------------------------------------------------------------------- #
# _PriceHistoryLookup
# --------------------------------------------------------------------------- #


class TestPriceHistoryLookup:
    def test_resolve_returns_none_when_asset_has_no_usable_prices(self):
        """An unlisted asset: no PriceHistory row was ever stored for it."""
        assert _PriceHistoryLookup([]).resolve(date(2024, 3, 1)) is None

    def test_resolve_returns_none_before_the_first_known_price(self):
        """A lot opened before the asset started being quoted has nothing to fall back to."""
        lookup = _PriceHistoryLookup([_price(date(2024, 5, 1))])
        assert lookup.resolve(date(2024, 4, 30)) is None

    def test_resolve_uses_the_latest_price_at_or_before_the_query_date(self):
        lookup = _PriceHistoryLookup([_price(date(2024, 5, 1), D("10")), _price(date(2024, 5, 6), D("12"))])
        resolved = lookup.resolve(date(2024, 5, 4))
        assert (resolved.price, resolved.resolved_date, resolved.source) == (D("10"), date(2024, 5, 1), "fallback")

    def test_resolve_marks_an_exact_date_hit_as_exact(self):
        lookup = _PriceHistoryLookup([_price(date(2024, 5, 1), D("10"))])
        assert _PriceHistoryLookup([_price(date(2024, 5, 1), D("10"))]).resolve(date(2024, 5, 1)).source == "exact"
        assert lookup.latest().resolved_date == date(2024, 5, 1)

    def test_latest_returns_none_when_there_are_no_rows(self):
        """This is exactly what puts the whole analysis into estimated_mode."""
        assert _PriceHistoryLookup([]).latest() is None

    def test_rows_with_a_null_close_are_ignored(self):
        """A PriceHistory row can carry only volume/open; it is not a usable quote."""
        lookup = _PriceHistoryLookup([_price(date(2024, 5, 1), None)])
        assert lookup.latest() is None


# --------------------------------------------------------------------------- #
# _FxRateResolver
# --------------------------------------------------------------------------- #


class TestFxRateResolver:
    def test_convert_passes_none_through(self):
        """Callers hand it optional amounts (e.g. lot.original_cost may be absent)."""
        assert _resolver().convert(None, "USD", date(2024, 1, 1)) is None

    def test_convert_returns_none_when_no_rate_was_loaded_for_that_day(self):
        """FX for that date was never published, so the value is unknown, not zero."""
        assert _resolver("EUR").convert(D("100"), "USD", date(2024, 1, 1)) is None

    def test_convert_is_identity_for_the_target_currency(self):
        assert _resolver("EUR").convert(D("100"), "EUR", date(2024, 1, 1)) == D("100")

    def test_convert_is_identity_when_the_currency_is_unknown(self):
        assert _resolver("EUR").convert(D("100"), None, date(2024, 1, 1)) == D("100")

    def test_convert_applies_the_loaded_rate(self):
        resolver = _resolver("EUR", {("USD", date(2024, 1, 1)): D("0.9")})
        assert resolver.convert(D("100"), "USD", date(2024, 1, 1)) == D("90.0")

    def test_need_ignores_the_target_currency_and_deduplicates(self):
        resolver = _resolver("EUR")
        resolver.need("EUR", date(2024, 1, 1))
        resolver.need(None, date(2024, 1, 1))
        resolver.need("USD", date(2024, 1, 1))
        resolver.need("USD", date(2024, 1, 1))
        assert resolver._needs == [("USD", date(2024, 1, 1))]


# --------------------------------------------------------------------------- #
# _resolve_selected_lot_ids
# --------------------------------------------------------------------------- #


class TestResolveSelectedLotIds:
    def test_rejects_a_lot_id_that_does_not_exist(self):
        """The UI can hold a stale selection after the lots were recomputed."""
        with pytest.raises(ValueError, match="Unknown lot ids requested"):
            _svc()._resolve_selected_lot_ids([1, 99], {1: _lot(1)})

    def test_returns_every_lot_when_nothing_is_selected(self):
        """Insertion order is kept: the engine already yields lots oldest-first."""
        assert _svc()._resolve_selected_lot_ids(None, {2: _lot(2), 1: _lot(1)}) == [2, 1]

    def test_a_repeated_selection_is_deduplicated(self):
        assert _svc()._resolve_selected_lot_ids([1, 1, 2], {1: _lot(1), 2: _lot(2)}) == [1, 2]

    def test_keeps_only_the_selected_lots(self):
        assert _svc()._resolve_selected_lot_ids([2], {1: _lot(1), 2: _lot(2)}) == [2]


# --------------------------------------------------------------------------- #
# _collect_fx_needs
# --------------------------------------------------------------------------- #


class TestCollectFxNeeds:
    def _call(self, resolver, **overrides):
        kwargs = {
            "fx_resolver": resolver,
            "analyses": [],
            "lots_by_id": {},
            "selected_ids": [],
            "transactions": [],
            "price_lookup": _PriceHistoryLookup([]),
            "prices": [],
            "fragments": [],
            "events": [],
            "closures": [],
            "split_ratios_by_tx_id": {},
            "actual_to": date(2024, 6, 1),
            "computed_from": date(2024, 1, 1),
            "asset_currency": "EUR",
        }
        kwargs.update(overrides)
        _svc()._collect_fx_needs(**kwargs)

    def test_wac_skips_a_non_buy_without_a_cost_basis_override(self):
        """A SELL needs no acquisition FX: the WAC pool only prices what came in."""
        resolver = _resolver("EUR")
        self._call(
            resolver,
            analyses=[LotAnalysisType.BROKER_WAC_HISTORY],
            transactions=[_tx(1, tx_type=TransactionType.SELL, quantity=D("10"), currency="USD")],
        )
        assert resolver._needs == []

    def test_wac_requests_the_cost_basis_currency_of_an_adjustment(self):
        """A manual ADJUSTMENT-in prices the pool from cost_basis_currency, not tx.currency."""
        resolver = _resolver("EUR")
        self._call(
            resolver,
            analyses=[LotAnalysisType.CUMULATIVE_WAC_HISTORY],
            transactions=[
                _tx(
                    1,
                    tx_type=TransactionType.ADJUSTMENT,
                    quantity=D("10"),
                    currency="GBP",
                    cost_basis_override=D("5"),
                    cost_basis_currency="USD",
                )
            ],
        )
        assert resolver._needs == [("USD", date(2024, 1, 10))]

    def test_lot_summary_skips_the_reference_price_when_none_can_be_resolved(self):
        """The lot carries a reference price but the asset has no quotes at all."""
        resolver = _resolver("EUR")
        lot = _lot(1, currency="EUR", reference_unit_price=D("9"))
        self._call(
            resolver,
            analyses=[LotAnalysisType.LOT_SUMMARY],
            lots_by_id={1: lot},
            selected_ids=[1],
            price_lookup=_PriceHistoryLookup([]),
        )
        assert resolver._needs == []

    def test_gantt_ignores_a_fragment_of_an_unselected_lot(self):
        """The user narrowed the Gantt to one lot; the other lot's FX is not fetched."""
        resolver = _resolver("EUR")
        self._call(
            resolver,
            analyses=[LotAnalysisType.GANTT_TOPOLOGY],
            lots_by_id={1: _lot(1, currency="USD"), 2: _lot(2, currency="GBP")},
            selected_ids=[1],
            fragments=[_fragment(2, fragment_id="frag-2")],
        )
        assert resolver._needs == []

    def test_custody_history_ignores_an_event_with_no_matching_transaction(self):
        """Engine-synthesised events (e.g. a split leg) carry an id with no Transaction row.

        Two events go in and only the one backed by a real transaction registers
        an FX need, which is what makes the skip observable rather than assumed.
        """
        resolver = _resolver("EUR")
        self._call(
            resolver,
            analyses=[LotAnalysisType.CUSTODY_HISTORY],
            events=[
                FifoEvent(kind="SPLIT", date=date(2024, 3, 1), transaction_id=999),
                FifoEvent(kind="BUY", date=date(2024, 3, 2), transaction_id=1),
            ],
            transactions=[_tx(1, currency="USD")],
        )
        assert resolver._needs == [("USD", date(2024, 3, 2))]

    def test_custody_history_ignores_a_closure_of_an_unselected_lot(self):
        resolver = _resolver("EUR")
        self._call(
            resolver,
            analyses=[LotAnalysisType.EVENT_HISTORY],
            lots_by_id={1: _lot(1, currency="USD"), 2: _lot(2, currency="GBP")},
            selected_ids=[1],
            closures=[_closure(2)],
        )
        assert resolver._needs == []


# --------------------------------------------------------------------------- #
# _collect_performance_fx_needs
# --------------------------------------------------------------------------- #


class TestCollectPerformanceFxNeeds:
    def _call(self, resolver, **overrides):
        kwargs = {
            "fx_resolver": resolver,
            "analyses": [LotAnalysisType.PERFORMANCE_HISTORY],
            "transactions": [],
            "closures": [],
            "lots_by_id": {},
            "asset_currency": "EUR",
        }
        kwargs.update(overrides)
        _svc()._collect_performance_fx_needs(**kwargs)

    def test_does_nothing_when_performance_history_was_not_requested(self):
        resolver = _resolver("EUR")
        self._call(resolver, analyses=[LotAnalysisType.LOT_SUMMARY], transactions=[_tx(1, currency="USD")])
        assert resolver._needs == []

    def test_an_adjustment_with_a_cost_basis_override_needs_the_cost_basis_currency(self):
        """Recording an inherited position: the external cash flow is the declared cost."""
        resolver = _resolver("EUR")
        self._call(
            resolver,
            transactions=[
                _tx(
                    1,
                    tx_type=TransactionType.ADJUSTMENT,
                    quantity=D("10"),
                    amount=D("0"),
                    currency="GBP",
                    cost_basis_override=D("7"),
                    cost_basis_currency="USD",
                )
            ],
        )
        assert resolver._needs == [("USD", date(2024, 1, 10))]

    def test_an_adjustment_without_an_override_falls_back_to_the_transaction_amount(self):
        resolver = _resolver("EUR")
        self._call(
            resolver,
            transactions=[_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("-500"), currency="USD")],
        )
        assert resolver._needs == [("USD", date(2024, 1, 10))]

    def test_an_adjustment_with_neither_an_override_nor_an_amount_needs_nothing(self):
        """A pure quantity correction carries no money, so it moves no cash flow."""
        resolver = _resolver("EUR")
        self._call(
            resolver,
            transactions=[_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("0"), currency="USD")],
        )
        assert resolver._needs == []

    def test_a_zero_cost_override_falls_through_to_the_amount(self):
        """cost_basis_override == 0 is treated as "not set", per the (None, 0) test."""
        resolver = _resolver("EUR")
        self._call(
            resolver,
            transactions=[
                _tx(
                    1,
                    tx_type=TransactionType.ADJUSTMENT,
                    quantity=D("10"),
                    amount=D("-500"),
                    currency="USD",
                    cost_basis_override=D("0"),
                    cost_basis_currency="GBP",
                )
            ],
        )
        assert resolver._needs == [("USD", date(2024, 1, 10))]

    def test_a_closure_of_a_short_lot_needs_no_proceeds_fx(self):
        """Only LONG sells produce an external inflow in the performance series."""
        resolver = _resolver("EUR")
        self._call(
            resolver,
            closures=[_closure(1)],
            lots_by_id={1: _lot(1, direction="SHORT", currency="USD")},
        )
        assert resolver._needs == []

    def test_a_closure_whose_lot_is_unknown_is_skipped(self):
        resolver = _resolver("EUR")
        self._call(resolver, closures=[_closure(99)], lots_by_id={1: _lot(1, currency="USD")})
        assert resolver._needs == []

    def test_a_long_sell_closure_needs_the_lot_currency_on_the_close_date(self):
        resolver = _resolver("EUR")
        self._call(resolver, closures=[_closure(1)], lots_by_id={1: _lot(1, currency="USD")})
        assert resolver._needs == [("USD", date(2024, 2, 1))]


# --------------------------------------------------------------------------- #
# _adjustment_cash_flow_cost
# --------------------------------------------------------------------------- #


class TestAdjustmentCashFlowCost:
    def test_prefers_the_cost_basis_override_times_the_quantity(self):
        """The declared unit cost of an ADJUSTMENT-in is the external money that went in."""
        cost = _svc()._adjustment_cash_flow_cost(
            tx=_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("-999"), cost_basis_override=D("7"), cost_basis_currency="EUR"),
            asset_currency="EUR",
            fx_resolver=_resolver("EUR"),
        )
        assert cost == D("70")

    def test_converts_the_override_into_the_target_currency(self):
        cost = _svc()._adjustment_cash_flow_cost(
            tx=_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("0"), cost_basis_override=D("7"), cost_basis_currency="USD"),
            asset_currency="EUR",
            fx_resolver=_resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}),
        )
        assert cost == D("35.0")

    def test_falls_back_to_the_transaction_amount_when_no_override_is_set(self):
        cost = _svc()._adjustment_cash_flow_cost(
            tx=_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("-250"), currency="EUR"),
            asset_currency="EUR",
            fx_resolver=_resolver("EUR"),
        )
        assert cost == D("250")

    def test_returns_none_when_the_adjustment_carries_no_money_at_all(self):
        """A quantity-only correction must not inject a phantom cash flow."""
        cost = _svc()._adjustment_cash_flow_cost(
            tx=_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("0"), currency="EUR"),
            asset_currency="EUR",
            fx_resolver=_resolver("EUR"),
        )
        assert cost is None


# --------------------------------------------------------------------------- #
# _build_wac_row
# --------------------------------------------------------------------------- #


class TestBuildWacRow:
    def _row(self, tx, *, split_linked=False, rates=None):
        return _svc()._build_wac_row(
            tx=tx,
            split_linked=split_linked,
            asset_currency="EUR",
            target_currency="EUR",
            fx_resolver=_resolver("EUR", rates),
        )

    def test_a_buy_with_no_amount_has_a_zero_unit_cost(self):
        """A free share grant: quantity arrives, no money leaves. WAC must not divide by nothing."""
        row = self._row(_tx(1, tx_type=TransactionType.BUY, quantity=D("10"), amount=D("0")))
        assert row.unit_cost_converted == D("0")

    def test_a_buy_divides_the_converted_total_by_the_quantity(self):
        row = self._row(
            _tx(1, tx_type=TransactionType.BUY, quantity=D("10"), amount=D("-1000"), currency="USD"),
            rates={("USD", date(2024, 1, 10)): D("0.5")},
        )
        assert row.unit_cost_converted == D("50.0")

    def test_a_buy_keeps_the_native_unit_cost_when_no_rate_is_available(self):
        row = self._row(_tx(1, tx_type=TransactionType.BUY, quantity=D("10"), amount=D("-1000"), currency="USD"))
        assert row.unit_cost_converted == D("100")

    def test_a_split_linked_row_is_repriced_in_the_asset_currency(self):
        """A split leg carries no money of its own; it inherits the asset's currency."""
        row = self._row(_tx(1, currency="USD"), split_linked=True)
        assert (row.is_split_linked, row.original_currency, row.unit_cost_converted) == (True, "EUR", None)

    def test_an_adjustment_uses_the_cost_basis_override_as_the_unit_cost(self):
        row = self._row(_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("0"), cost_basis_override=D("4"), cost_basis_currency="EUR"))
        assert row.unit_cost_converted == D("4")

    def test_a_sell_carries_no_unit_cost(self):
        row = self._row(_tx(1, tx_type=TransactionType.SELL, quantity=D("-10"), amount=D("500")))
        assert row.unit_cost_converted is None


# --------------------------------------------------------------------------- #
# _compute_wac_series
# --------------------------------------------------------------------------- #


class TestComputeWacSeries:
    def _wac_tx(self, day: date, qty: Decimal, unit_cost: Decimal | None) -> WACInputTX:
        return WACInputTX(
            tx_id=1,
            type="BUY",
            date=day,
            quantity=qty,
            unit_cost_converted=unit_cost,
            original_currency="EUR",
            cost_basis_mode=None,
            is_split_linked=False,
        )

    def test_a_broker_with_no_transactions_produces_no_series(self):
        """A broker in scope that never traded this asset must not emit flat-zero points."""
        assert _svc()._compute_wac_series([], _days(date(2024, 1, 1), 3), "EUR") == []

    def test_dates_before_the_first_transaction_are_skipped(self):
        """The pool does not exist yet, so there is no average cost to report."""
        series = _svc()._compute_wac_series(
            [self._wac_tx(date(2024, 1, 3), D("10"), D("5"))],
            _days(date(2024, 1, 1), 4),
            "EUR",
        )
        assert [point[0] for point in series] == [date(2024, 1, 3), date(2024, 1, 4)]

    def test_the_pool_grows_as_transactions_are_absorbed(self):
        series = _svc()._compute_wac_series(
            [self._wac_tx(date(2024, 1, 1), D("10"), D("5")), self._wac_tx(date(2024, 1, 3), D("10"), D("15"))],
            _days(date(2024, 1, 1), 3),
            "EUR",
        )
        assert [point[2] for point in series] == [D("10"), D("10"), D("20")]


# --------------------------------------------------------------------------- #
# _build_performance_history
# --------------------------------------------------------------------------- #


class TestBuildPerformanceHistory:
    def _call(self, **overrides):
        kwargs = {
            "scope_broker_ids": [1],
            "history_dates": _days(date(2024, 1, 10), 5),
            "market_prices": {day: D("10") for day in _days(date(2024, 1, 10), 5)},
            "asset_currency": "EUR",
            "fx_resolver": _resolver("EUR"),
            "context": _perf_context(),
            "quote_base_quantity": 1,
        }
        kwargs.update(overrides)
        return _svc()._build_performance_history(**kwargs)

    def test_a_day_without_a_market_price_produces_no_nav_snapshot(self):
        """A market holiday inside the window: NAV is unknown, not carried forward."""
        prices = {day: D("10") for day in _days(date(2024, 1, 10), 5)}
        prices[date(2024, 1, 12)] = None
        points = self._call(
            market_prices=prices,
            context=_perf_context(
                transactions=[_tx(1)],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
            ),
        )
        assert {point.date for point in points} == set(_days(date(2024, 1, 10), 5))
        assert next(point for point in points if point.date == date(2024, 1, 12)).roi is None

    def test_a_lot_with_no_in_scope_fragments_contributes_nothing_to_nav(self):
        """The lot sits at a broker the user filtered out of the analysis."""
        points = self._call(
            context=_perf_context(
                transactions=[_tx(1)],
                fragments_by_lot={1: [_fragment(1)], 2: [_fragment(2, fragment_id="frag-2", broker_id=99)]},
                lots_by_id={1: _lot(1), 2: _lot(2)},
            ),
        )
        assert any(point.roi is not None for point in points)

    def test_a_transaction_of_an_out_of_scope_broker_is_not_a_cash_flow(self):
        points = self._call(context=_perf_context(transactions=[_tx(1, broker_id=99)]))
        assert all(point.roi is None for point in points)

    def test_an_adjustment_with_a_cost_contributes_a_negative_cash_flow(self):
        """Recording an inherited position is money in, exactly like a BUY."""
        points = self._call(
            context=_perf_context(
                transactions=[
                    _tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("100"), amount=D("-1000"), tx_date=date(2024, 1, 10)),
                ],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
            ),
        )
        assert any(point.roi is not None for point in points)

    def test_an_adjustment_with_no_cost_contributes_no_cash_flow(self):
        """A quantity-only correction must leave ROI undefined, not report 0%."""
        points = self._call(
            context=_perf_context(
                transactions=[_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("100"), amount=D("0"))],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
            ),
        )
        assert all(point.roi is None for point in points)

    def test_a_non_sell_closure_is_not_an_external_inflow(self):
        """A short cover (close_reason BUY) is not proceeds arriving from outside."""
        tx = _tx(1)
        points = self._call(
            context=_perf_context(
                transactions=[tx],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
                engine_result=_engine_result(closures=[_closure(1, close_reason="BUY", transaction_id=1)]),
            ),
        )
        roi_on_close = next(point for point in points if point.date == date(2024, 1, 14)).roi
        assert roi_on_close == self._roi_without_closure()

    def _roi_without_closure(self):
        points = self._call(
            context=_perf_context(
                transactions=[_tx(1)],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
            ),
        )
        return next(point for point in points if point.date == date(2024, 1, 14)).roi

    def test_a_sell_closure_of_an_unknown_lot_is_skipped(self):
        points = self._call(
            context=_perf_context(
                transactions=[_tx(1)],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
                engine_result=_engine_result(closures=[_closure(99, transaction_id=1, close_date=date(2024, 1, 14))]),
            ),
        )
        assert next(point for point in points if point.date == date(2024, 1, 14)).roi == self._roi_without_closure()

    def test_a_duplicated_transfer_leg_is_counted_once(self):
        """Both legs of a paired transfer reach the engine; the pair id deduplicates them."""
        event = FifoEvent(
            kind="TRANSFER_DEPART",
            date=date(2024, 1, 12),
            transaction_id=900,
            pair_id=42,
            quantity=D("10"),
            source_broker_id=1,
            destination_broker_id=99,
        )
        points = self._call(
            context=_perf_context(
                transactions=[_tx(1)],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
                engine_result=_engine_result(events=[event, event]),
            ),
        )
        assert len(points) == 5

    def test_an_arrive_leg_seen_from_the_source_side_is_ignored(self):
        """Only the DEPART leg describes the outflow of the in-scope broker."""
        points = self._call(
            context=_perf_context(
                transactions=[_tx(1)],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
                engine_result=_engine_result(
                    events=[
                        FifoEvent(
                            kind="TRANSFER_DEPART",
                            date=date(2024, 1, 12),
                            transaction_id=900,
                            pair_id=42,
                            quantity=D("10"),
                            source_broker_id=99,
                            destination_broker_id=1,
                        )
                    ]
                ),
            ),
        )
        assert all(point.roi == other.roi for point, other in zip(points, self._call(context=_perf_context(transactions=[_tx(1)], fragments_by_lot={1: [_fragment(1)]}, lots_by_id={1: _lot(1)})), strict=True))

    def test_a_fully_internal_transfer_is_not_an_external_flow(self):
        """Both brokers are in scope, so nothing entered or left the analysed perimeter."""
        points = self._call(
            scope_broker_ids=[1, 2],
            context=_perf_context(
                transactions=[_tx(1)],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
                engine_result=_engine_result(
                    events=[
                        FifoEvent(
                            kind="TRANSFER_DEPART",
                            date=date(2024, 1, 12),
                            transaction_id=900,
                            pair_id=42,
                            quantity=D("10"),
                            source_broker_id=1,
                            destination_broker_id=2,
                        )
                    ]
                ),
            ),
        )
        assert any(point.roi is not None for point in points)

    def test_a_transfer_on_an_unpriced_day_invalidates_the_series_from_that_date(self):
        """The transferred value cannot be measured, so ROI/TWRR stop being meaningful."""
        prices = {day: D("10") for day in _days(date(2024, 1, 10), 5)}
        prices[date(2024, 1, 12)] = None
        points = self._call(
            market_prices=prices,
            context=_perf_context(
                transactions=[_tx(1)],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
                engine_result=_engine_result(
                    events=[
                        FifoEvent(
                            kind="TRANSFER_DEPART",
                            date=date(2024, 1, 12),
                            transaction_id=900,
                            pair_id=42,
                            quantity=D("10"),
                            source_broker_id=1,
                            destination_broker_id=99,
                        )
                    ]
                ),
            ),
        )
        assert all(point.roi is None and point.twrr is None for point in points if point.date >= date(2024, 1, 12))

    def test_a_priced_external_transfer_becomes_a_cash_flow(self):
        points = self._call(
            context=_perf_context(
                transactions=[_tx(1)],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
                engine_result=_engine_result(
                    events=[
                        FifoEvent(
                            kind="TRANSFER_DEPART",
                            date=date(2024, 1, 12),
                            transaction_id=900,
                            pair_id=42,
                            quantity=D("10"),
                            source_broker_id=1,
                            destination_broker_id=99,
                        )
                    ]
                ),
            ),
        )
        assert any(point.roi is not None for point in points)

    def test_cash_flows_before_the_first_nav_are_carried_onto_it(self):
        """A BUY on a day with no price still has to be counted, at the first priced day."""
        prices = dict.fromkeys(_days(date(2024, 1, 10), 2))
        prices.update({day: D("10") for day in _days(date(2024, 1, 12), 3)})
        points = self._call(
            market_prices=prices,
            context=_perf_context(
                transactions=[_tx(1, tx_date=date(2024, 1, 10))],
                fragments_by_lot={1: [_fragment(1)]},
                lots_by_id={1: _lot(1)},
            ),
        )
        assert any(point.roi is not None for point in points if point.date >= date(2024, 1, 12))

    def test_no_priced_day_at_all_yields_an_empty_series(self):
        """An unlisted asset has no NAV, so ROI and TWRR are undefined everywhere."""
        points = self._call(
            market_prices=dict.fromkeys(_days(date(2024, 1, 10), 5)),
            context=_perf_context(transactions=[_tx(1)], fragments_by_lot={1: [_fragment(1)]}, lots_by_id={1: _lot(1)}),
        )
        assert all(point.roi is None and point.twrr is None for point in points)

    def test_no_cash_flow_at_all_yields_an_empty_series(self):
        """NAV exists but nothing was ever invested from outside: ROI has no base."""
        points = self._call(context=_perf_context(fragments_by_lot={1: [_fragment(1)]}, lots_by_id={1: _lot(1)}))
        assert all(point.roi is None for point in points)


# --------------------------------------------------------------------------- #
# _build_lot_summaries
# --------------------------------------------------------------------------- #


class TestBuildLotSummaries:
    def _call(self, **overrides):
        lot = overrides.pop("lot", _lot(1))
        kwargs = {
            "engine_result": _engine_result(lots=[lot], fragments=[_fragment(1)]),
            "lots_by_id": {1: lot},
            "selected_ids": [1],
            "fx_resolver": _resolver("EUR"),
            "market_prices": {date(2024, 2, 1): D("12")},
            "price_lookup": _PriceHistoryLookup([_price(date(2024, 1, 10), D("10"))]),
            "closures_by_lot": {},
            "income_by_lot": {},
            "fees_by_lot": {},
            "taxes_by_lot": {},
            "estimated_mode": False,
            "quote_base_quantity": 1,
            "analysis_end": date(2024, 3, 1),
        }
        kwargs.update(overrides)
        return _svc()._build_lot_summaries(**kwargs)[0]

    def test_a_short_lot_values_proceeds_minus_the_open_position(self):
        """Shorting: the money came in first, and the open leg is a liability.

        A SHORT lot reports cumulative_proceeds from the lot itself (the sale
        happened at opening), not from its closures, which are the covers.
        """
        lot = _lot(1, direction="SHORT", open_quantity=D("100"), original_cost=D("1000"), cumulative_proceeds=D("1500"))
        row = self._call(lot=lot, closures_by_lot={1: [_closure(1, close_reason="BUY", proceeds=D("900"))]})
        # open_value = 100 * 12 = 1200; proceeds = 1500 -> total 300, and pnl == total.
        assert (row.open_value, row.total_value, row.pnl) == (D("1200"), D("300"), D("300"))

    def test_a_lot_opened_at_zero_reports_no_relative_return(self):
        """A free grant has no reference price, so "x% versus entry" is undefined."""
        row = self._call(lot=_lot(1, opening_unit_price=D("0"), original_cost=D("0")))
        assert row.relative_return is None

    def test_an_unpriced_asset_falls_back_to_valuing_the_lot_at_cost(self):
        row = self._call(market_prices={}, estimated_mode=True)
        assert (row.value_source, row.open_value, row.market_pnl) == ("ESTIMATED_AT_COST", D("1000"), D("0"))

    def test_an_unpriced_short_lot_reports_no_value_at_all(self):
        """Valuing a short at cost would invert the sign, so the service refuses to guess."""
        row = self._call(lot=_lot(1, direction="SHORT"), market_prices={}, estimated_mode=True)
        assert (row.value_source, row.open_value, row.total_value, row.pnl) == (None, None, None, None)

    def test_an_unvalued_lot_reports_no_total_pnl_and_no_returns(self):
        row = self._call(market_prices={}, estimated_mode=False)
        assert (row.total_pnl, row.total_return, row.net_total_pnl, row.net_total_return, row.annualized_return) == (None, None, None, None, None)

    def test_an_unvalued_lot_still_reports_its_cash_yield(self):
        """Income actually landed in the account; it does not depend on a market price."""
        row = self._call(market_prices={}, estimated_mode=False, income_by_lot={1: D("50")})
        assert row.cash_yield == D("0.05")

    def test_a_lot_with_a_zero_opening_value_reports_no_cash_yield(self):
        row = self._call(lot=_lot(1, original_cost=D("0"), opening_unit_price=D("0")), income_by_lot={1: D("50")})
        assert (row.cash_yield, row.total_return) == (None, None)

    def test_a_closed_lot_reports_its_last_closure_date(self):
        row = self._call(
            lot=_lot(1, open_quantity=D("0")),
            closures_by_lot={1: [_closure(1, close_date=date(2024, 2, 1)), _closure(1, close_date=date(2024, 2, 20))]},
        )
        assert row.closing_date == date(2024, 2, 20)

    def test_a_lot_with_no_open_quantity_and_no_closures_has_no_closing_date(self):
        """Defensive shape of the same branch: nothing to take a max() over."""
        assert self._call(lot=_lot(1, open_quantity=D("0")), closures_by_lot={}).closing_date is None

    def test_a_priced_long_lot_reports_market_value_and_relative_return(self):
        row = self._call()
        assert (row.value_source, row.open_value, row.pnl, row.relative_return) == ("MARKET_PRICE", D("1200"), D("200"), D("0.2"))

    def test_fees_and_taxes_are_subtracted_from_the_net_figures(self):
        row = self._call(fees_by_lot={1: D("10")}, taxes_by_lot={1: D("15")})
        assert row.net_total_pnl == row.total_pnl - D("25")


# --------------------------------------------------------------------------- #
# _build_value_history / _build_return_history
# --------------------------------------------------------------------------- #


class TestBuildValueAndReturnHistory:
    """Both builders share the same market_price-is-None ladder, so both are pinned."""

    def _value(self, **overrides):
        lot = overrides.pop("lot", _lot(1))
        kwargs = {
            "selected_ids": [1],
            "lots_by_id": {1: lot},
            "fragments_by_lot": {1: [_fragment(1)]},
            "closures_by_lot": {},
            "market_prices": {},
            "history_dates": _days(date(2024, 1, 10), 3),
            "fx_resolver": _resolver("EUR"),
            "income_prefix_by_lot": {},
            "fees_prefix_by_lot": {},
            "taxes_prefix_by_lot": {},
            "estimated_mode": False,
            "quote_base_quantity": 1,
        }
        kwargs.update(overrides)
        return _svc()._build_value_history(**kwargs)

    def _returns(self, **overrides):
        lot = overrides.pop("lot", _lot(1))
        kwargs = {
            "selected_ids": [1],
            "lots_by_id": {1: lot},
            "fragments_by_lot": {1: [_fragment(1)]},
            "market_prices": {},
            "price_lookup": _PriceHistoryLookup([_price(date(2024, 1, 10), D("10"))]),
            "fx_resolver": _resolver("EUR"),
            "history_dates": _days(date(2024, 1, 10), 3),
            "closures_by_lot": {},
            "income_prefix_by_lot": {},
            "fees_prefix_by_lot": {},
            "taxes_prefix_by_lot": {},
            "estimated_mode": False,
            "quote_base_quantity": 1,
        }
        kwargs.update(overrides)
        return _svc()._build_return_history(**kwargs)

    # -- market price missing, position already closed ----------------------- #

    def test_value_of_a_closed_long_lot_on_an_unpriced_day_is_its_proceeds(self):
        """No open quantity left, so no quote is needed to state what the lot is worth."""
        lot = _lot(1, open_quantity=D("0"))
        closure = _closure(1, close_date=date(2024, 1, 10), proceeds=D("1200"))
        points = self._value(
            lot=lot,
            fragments_by_lot={1: [_fragment(1, end_date=date(2024, 1, 10))]},
            closures_by_lot={1: [closure]},
        )
        last = next(point for point in points if point.date == date(2024, 1, 12))
        assert (last.open_value, last.proceeds, last.total_value, last.pnl) == (D("0"), D("1200"), D("1200"), D("200"))

    def test_value_of_a_closed_short_lot_on_an_unpriced_day_uses_cumulative_proceeds(self):
        """A covered short is worth the money it took in, whatever the market does next."""
        lot = _lot(1, direction="SHORT", open_quantity=D("0"), cumulative_proceeds=D("1500"))
        points = self._value(
            lot=lot,
            fragments_by_lot={1: [_fragment(1, direction="SHORT", end_date=date(2024, 1, 10))]},
            closures_by_lot={1: [_closure(1, close_date=date(2024, 1, 10), close_reason="BUY", proceeds=D("900"))]},
        )
        last = next(point for point in points if point.date == date(2024, 1, 12))
        assert (last.open_value, last.proceeds, last.total_value, last.pnl) == (D("0"), D("1500"), D("1500"), D("1500"))

    def test_return_of_a_closed_long_lot_on_an_unpriced_day_is_computed(self):
        lot = _lot(1, open_quantity=D("0"))
        points = self._returns(
            lot=lot,
            fragments_by_lot={1: [_fragment(1, end_date=date(2024, 1, 10))]},
            closures_by_lot={1: [_closure(1, close_date=date(2024, 1, 10), proceeds=D("1200"))]},
        )
        last = next(point for point in points if point.date == date(2024, 1, 12))
        assert last.total_return == D("0.2")

    def test_return_of_a_closed_short_lot_on_an_unpriced_day_is_computed(self):
        lot = _lot(1, direction="SHORT", open_quantity=D("0"), cumulative_proceeds=D("1500"))
        points = self._returns(
            lot=lot,
            fragments_by_lot={1: [_fragment(1, direction="SHORT", end_date=date(2024, 1, 10))]},
            closures_by_lot={1: [_closure(1, close_date=date(2024, 1, 10), close_reason="BUY")]},
        )
        last = next(point for point in points if point.date == date(2024, 1, 12))
        assert last.total_return == D("0.5")

    # -- market price missing, position still open --------------------------- #

    def test_an_open_lot_on_an_unpriced_day_is_valued_at_cost_in_estimated_mode(self):
        """An unlisted holding: the only defensible mark is what it cost."""
        points = self._value(estimated_mode=True)
        assert {point.open_value for point in points} == {D("1000")}

    def test_an_open_lot_on_an_unpriced_day_emits_nothing_when_not_estimating(self):
        """A gap in a normally-quoted series must leave a hole, not a fabricated value."""
        assert self._value(estimated_mode=False) == []

    def test_an_open_short_lot_is_never_valued_at_cost(self):
        """estimated_mode only rescues LONG lots; a short at cost would flip the sign."""
        assert self._value(lot=_lot(1, direction="SHORT"), estimated_mode=True) == []

    def test_return_of_an_open_lot_on_an_unpriced_day_uses_the_cost_mark(self):
        points = self._returns(estimated_mode=True)
        assert {point.total_return for point in points} == {D("0")}

    def test_return_of_an_open_lot_emits_nothing_when_not_estimating(self):
        assert self._returns(estimated_mode=False) == []

    # -- priced days --------------------------------------------------------- #

    def test_a_priced_day_reports_the_market_value(self):
        points = self._value(market_prices={date(2024, 1, 11): D("12")})
        point = next(p for p in points if p.date == date(2024, 1, 11))
        assert (point.open_value, point.pnl) == (D("1200"), D("200"))

    def test_a_priced_day_reports_the_relative_return_against_the_reference(self):
        points = self._returns(market_prices={date(2024, 1, 11): D("12")})
        assert next(p for p in points if p.date == date(2024, 1, 11)).relative_return == D("0.2")

    def test_no_reference_price_leaves_the_relative_return_undefined(self):
        """The asset had no quote at the opening date and the lot was booked at zero."""
        points = self._returns(
            lot=_lot(1, opening_unit_price=D("0"), original_cost=D("1000")),
            price_lookup=_PriceHistoryLookup([]),
            market_prices={date(2024, 1, 11): D("12")},
        )
        assert next(p for p in points if p.date == date(2024, 1, 11)).relative_return is None

    def test_fees_and_taxes_lower_the_net_pnl_of_a_value_point(self):
        points = self._value(
            market_prices={date(2024, 1, 11): D("12")},
            fees_prefix_by_lot={1: {date(2024, 1, 10): D("5")}},
            taxes_prefix_by_lot={1: {date(2024, 1, 10): D("3")}},
        )
        point = next(p for p in points if p.date == date(2024, 1, 11))
        assert point.net_pnl == point.pnl - D("8")


# --------------------------------------------------------------------------- #
# Small builders
# --------------------------------------------------------------------------- #


class TestSmallBuilders:
    def test_converted_cumulative_proceeds_of_a_short_lot_uses_the_lot_total(self):
        """A short's proceeds arrived at opening, not at each closure."""
        lot = _lot(1, direction="SHORT", cumulative_proceeds=D("1500"), currency="USD")
        value = _svc()._converted_cumulative_proceeds(lot, [], _resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}))
        assert value == D("750.0")

    def test_converted_cumulative_proceeds_of_a_short_lot_falls_back_to_the_native_total(self):
        lot = _lot(1, direction="SHORT", cumulative_proceeds=D("1500"), currency="USD")
        assert _svc()._converted_cumulative_proceeds(lot, [], _resolver("EUR")) == D("1500")

    def test_converted_cumulative_proceeds_of_a_long_lot_sums_its_closures(self):
        lot = _lot(1)
        value = _svc()._converted_cumulative_proceeds(lot, [_closure(1, proceeds=D("300")), _closure(1, proceeds=D("200"))], _resolver("EUR"))
        assert value == D("500")

    def test_gantt_ignores_fragments_of_unselected_lots(self):
        segments = _svc()._build_gantt_segments(
            [_fragment(1), _fragment(2, fragment_id="frag-2")],
            [1],
            {1: _lot(1), 2: _lot(2)},
            _resolver("EUR"),
        )
        assert {segment.lot_id for segment in segments} == {1}

    def test_closure_rows_ignore_closures_of_unselected_lots(self):
        rows = _svc()._build_closure_rows([_closure(1), _closure(2)], {1}, {1: _lot(1), 2: _lot(2)}, _resolver("EUR"))
        assert {row.lot_id for row in rows} == {1}

    def test_income_events_skip_a_transaction_with_no_asset(self):
        """A broker-level dividend not attributed to an asset cannot be allocated to a lot."""
        events = _svc()._build_income_economic_events(
            income_transactions=[
                _tx(1, tx_type=TransactionType.DIVIDEND, asset_id=None, amount=D("50")),
                _tx(2, tx_type=TransactionType.DIVIDEND, amount=D("50")),
            ],
            fx_resolver=_resolver("EUR"),
            asset_currency="EUR",
            target_currency="EUR",
        )
        assert [event.transaction_id for event in events] == [2]

    def test_cost_events_skip_a_transaction_with_no_amount(self):
        """A FEE row with a null amount carries nothing to allocate."""
        events = _svc()._build_cost_economic_events(
            cost_transactions=[
                _tx(1, tx_type=TransactionType.FEE, amount=None),
                _tx(2, tx_type=TransactionType.FEE, amount=D("-10")),
            ],
            fx_resolver=_resolver("EUR"),
            asset_currency="EUR",
            target_currency="EUR",
        )
        assert [event.transaction_id for event in events] == [2]

    def test_engine_transactions_leave_a_non_trade_unconverted(self):
        """Only BUY/SELL carry a controvalue the engine needs pre-converted."""
        rows = _svc()._build_engine_transactions(
            [_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("-100"), currency="USD")],
            _resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}),
            "EUR",
            "EUR",
        )
        assert rows[0].target_amount is None

    def test_engine_transactions_convert_a_trade_controvalue(self):
        """The sign of the controvalue is preserved: a BUY stays negative."""
        rows = _svc()._build_engine_transactions(
            [_tx(1, amount=D("-1000"), currency="USD")],
            _resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}),
            "EUR",
            "EUR",
        )
        assert rows[0].target_amount == D("-500.0")

    def test_opening_reference_price_returns_nothing_when_no_quote_exists(self):
        """The lot knows its reference price but the quote series is empty."""
        lot = _lot(1, reference_unit_price=D("9"), reference_price_source="fallback")
        price, currency, resolved_date, source = _svc()._opening_reference_price(lot, _PriceHistoryLookup([]))
        assert (price, currency, resolved_date, source) == (None, None, lot.opening_date, "fallback")

    def test_opening_reference_price_uses_the_resolved_quote_currency(self):
        lot = _lot(1, reference_unit_price=D("9"))
        lookup = _PriceHistoryLookup([_price(date(2024, 1, 8), D("9"), "USD")])
        price, currency, resolved_date, _source = _svc()._opening_reference_price(lot, lookup)
        assert (price, currency, resolved_date) == (D("9"), "USD", date(2024, 1, 8))

    def test_opening_reference_price_scales_the_buy_price_by_the_quote_base(self):
        """A bond quoted per 100 units: the entry price must land on the same axis."""
        price, _currency, _resolved, source = _svc()._opening_reference_price(_lot(1, opening_unit_price=D("0.98")), _PriceHistoryLookup([]), 100)
        assert (price, source) == (D("98.00"), "exact")

    def test_price_history_skips_days_with_no_estimated_price(self):
        points = _svc()._build_price_history(
            selected_ids=[1],
            lots_by_id={1: _lot(1)},
            estimated_market_prices={date(2024, 1, 11): (D("12"), True)},
            history_dates=_days(date(2024, 1, 10), 3),
            target_currency="EUR",
            closures_by_lot={},
        )
        assert [(point.date, point.estimated) for point in points] == [(date(2024, 1, 11), True)]

    def test_a_split_impacts_a_lot_that_is_in_transit_through_the_broker(self):
        """Shares in flight on the split date still belong to the departing broker's pool."""
        event = FifoEvent(kind="SPLIT", date=date(2024, 2, 1), transaction_id=900, broker_id=1, ratio=D("2"))
        fragment = _fragment(
            5,
            fragment_id="frag-transit",
            custody_type="IN_TRANSIT",
            broker_id=None,
            start_date=date(2024, 1, 20),
            source_broker_id=1,
            destination_broker_id=2,
        )
        assert _svc()._impacted_lot_ids_for_split(event, [fragment]) == {5}

    def test_a_split_ignores_a_fragment_held_at_another_broker(self):
        event = FifoEvent(kind="SPLIT", date=date(2024, 2, 1), transaction_id=900, broker_id=1, ratio=D("2"))
        assert _svc()._impacted_lot_ids_for_split(event, [_fragment(5, broker_id=99)]) == set()

    def test_a_closed_lot_with_no_closures_ends_on_its_opening_date(self):
        assert _svc()._lot_history_end_date(_lot(1, open_quantity=D("0")), [], date(2024, 6, 1)) == date(2024, 1, 10)

    def test_a_closed_lot_ends_on_its_last_closure(self):
        end = _svc()._lot_history_end_date(_lot(1, open_quantity=D("0")), [_closure(1, close_date=date(2024, 2, 5))], date(2024, 6, 1))
        assert end == date(2024, 2, 5)

    def test_an_open_lot_runs_to_the_end_of_the_window(self):
        assert _svc()._lot_history_end_date(_lot(1), [], date(2024, 6, 1)) == date(2024, 6, 1)

    def test_extend_closed_runs_a_closed_lot_to_the_end_of_the_window(self):
        end = _svc()._lot_history_end_date(_lot(1, open_quantity=D("0")), [_closure(1)], date(2024, 6, 1), extend_closed=True)
        assert end == date(2024, 6, 1)


class TestWacHistoryBuilders:
    """A broker that holds none of this asset must produce no WAC series at all."""

    def test_a_broker_with_no_wac_rows_is_skipped(self):
        """Broker 2 is in the analysis scope but never traded this asset."""
        points = _svc()._build_broker_wac_history([1, 2], {1: []}, _days(date(2024, 1, 10), 2), "EUR")
        assert points == []

    def test_a_broker_with_wac_rows_produces_one_point_per_day(self):
        row = WACInputTX(
            tx_id=1,
            type="BUY",
            date=date(2024, 1, 10),
            quantity=D("10"),
            unit_cost_converted=D("5"),
            original_currency="EUR",
            cost_basis_mode=None,
            is_split_linked=False,
        )
        points = _svc()._build_broker_wac_history([1], {1: [row]}, _days(date(2024, 1, 10), 2), "EUR")
        assert [point.broker_id for point in points] == [1, 1]

    def test_an_asset_with_no_transactions_has_no_cumulative_wac(self):
        assert _svc()._build_cumulative_wac_history({}, _days(date(2024, 1, 10), 2), "EUR") == []


class TestEmptyResponse:
    def test_an_empty_response_still_carries_the_request_metadata(self):
        """Returned when the user has no brokers in scope, or the asset was never traded."""
        response = _svc()._empty_response(
            asset_id=7,
            target_currency="EUR",
            requested_analyses=[LotAnalysisType.LOT_SUMMARY],
            broker_ids=[],
            selected_lot_ids=None,
            requested_date_from=None,
            requested_date_to=date(2024, 6, 1),
            computed_date_from=None,
            computed_date_to=date(2024, 6, 1),
            status="COMPLETE",
        )
        assert (response.asset_id, response.calculation_status, response.calculation_metadata.broker_ids) == (7, "COMPLETE", [])
        assert response.data_quality.issues == []


class TestGetLotsAnalysisArgumentGuard:
    @pytest.mark.asyncio
    async def test_an_empty_analysis_list_is_rejected_before_any_query(self):
        """The guard runs before the first DB access, which is why db=None suffices here."""
        with pytest.raises(ValueError, match="requested_analyses must not be empty"):
            await _svc().get_lots_analysis(
                user_id=1,
                asset_id=7,
                broker_ids=None,
                date_from=None,
                date_to=None,
                target_currency="EUR",
                selected_lot_ids=None,
                requested_analyses=[],
            )


class TestFxRateResolverLoad:
    """``load`` is the resolver's only async step; convert_bulk is stubbed, so no session."""

    @pytest.mark.asyncio
    async def test_a_day_with_no_published_rate_is_left_unresolved(self, monkeypatch):
        """convert_bulk returns None for that pair: the amount stays unknown, not zero."""

        async def fake_convert_bulk(_session, conversions, raise_on_error=False):
            return [None] * len(conversions), []

        monkeypatch.setattr(module, "convert_bulk", fake_convert_bulk)
        resolver = _FxRateResolver("EUR")
        resolver.need("USD", date(2024, 1, 10))
        await resolver.load(None)
        assert resolver.convert(D("100"), "USD", date(2024, 1, 10)) is None

    @pytest.mark.asyncio
    async def test_a_resolved_rate_is_stored_and_reused(self, monkeypatch):
        calls: list[int] = []

        async def fake_convert_bulk(_session, conversions, raise_on_error=False):
            calls.append(len(conversions))
            return [(Currency(code="EUR", amount=D("0.9")), date(2024, 1, 10), False)], []

        monkeypatch.setattr(module, "convert_bulk", fake_convert_bulk)
        resolver = _FxRateResolver("EUR")
        resolver.need("USD", date(2024, 1, 10))
        await resolver.load(None)
        await resolver.load(None)  # nothing pending the second time
        assert (resolver.convert(D("100"), "USD", date(2024, 1, 10)), calls) == (D("90.0"), [1])


class TestParseTransferPairId:
    def test_rejects_a_fragment_id_that_is_not_a_transfer_leg(self):
        """Guards the split/transfer bookkeeping against being fed an ordinary fragment."""
        with pytest.raises(ValueError, match="does not contain transfer pair marker"):
            _parse_transfer_pair_id("lot:1/frag:0")

    def test_extracts_the_pair_id_from_a_transfer_fragment(self):
        assert _parse_transfer_pair_id("lot:1/transfer:42/leg:in") == 42
