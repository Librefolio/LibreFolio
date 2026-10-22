"""Pure-calculation tests for the lots analysis builders.

Isolation: PURE. The pure builders of the lots analysis live as plain functions
in ``backend/app/services/financial_math/lots/`` and are called directly. The
sync DTO builders that remain on ``LotsAnalysisService`` receive all of their
inputs as arguments and never touch ``self.db``, so they are still called on a
session-less ``LotsAnalysisService(db=None)``: no session, no server, no shared
row is read or written, so this unit can run beside anything.

Why these tests exist. The public entry point ``get_lots_analysis`` is covered
by the API/e2e suites, but only over the mock dataset, which contains a single
shape of portfolio: LONG lots, a dense daily price series, and plain BUY/SELL
transactions. Everything the builders do for the *other* shapes a real user
produces -- a SHORT position, an unlisted asset with no price history at all
(valued at cost), a gap in the price series, a manual ADJUSTMENT carrying a
cost-basis override, a share grant bought for zero, a transfer that crosses the
analysis scope -- was never executed. These are the branches pinned below.

Data doubles are built by hand from the FIFO engine's frozen dataclasses rather
than by running the engine, so each test states exactly the one situation it is
about and nothing else can drift into it.
"""

import random
from dataclasses import replace
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from types import SimpleNamespace

import pytest

import backend.app.schemas.portfolio as portfolio_module
import backend.app.services.financial_math.lots.conversions as conversions_module
import backend.app.services.financial_math.lots.histories as histories_module
import backend.app.services.financial_math.lots.prices as prices_module
from backend.app.db.models import PriceHistory, Transaction, TransactionType
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import BrokerWACHistoryPoint, CumulativeWACHistoryPoint, IssueCode, LotAnalysisType, LotsAnalysisResponse, LotTimelineEventKind
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services.financial_math.average_cost import (
    AverageCost,
    CostMovement,
    CostMovementKind,
    CostPosition,
    _ConversionRequest,
    _fold_average_costs,
    _ResolvedConversion,
)
from backend.app.services.financial_math.fifo.engine import run_fifo_lot_engine
from backend.app.services.financial_math.fifo.models import FifoEngineResult, FifoEvent, FifoInputTransaction, FifoLot, FragmentInterval, LotClosure
from backend.app.services.financial_math.lots.average_cost_lines import ALL_BROKERS, average_cost_points, build_broker_wac_history, build_cumulative_wac_history
from backend.app.services.financial_math.lots.conversions import FxRateResolver, collect_fx_needs, collect_performance_fx_needs
from backend.app.services.financial_math.lots.economic_events import build_cost_economic_events, build_engine_transactions, build_income_economic_events
from backend.app.services.financial_math.lots.histories import (
    PerformanceSourceContext,
    adjustment_cash_flow_cost,
    build_performance_history,
    build_price_history,
    build_return_history,
    build_value_history,
    group_closures,
    group_fragments,
    known_cumulative_proceeds,
    known_realized_pnl,
    lot_history_end_date,
)
from backend.app.services.financial_math.lots.prices import opening_reference_price
from backend.app.services.financial_math.lots.scope_boundary import BoundaryLeg
from backend.app.services.financial_math.price_marks import AssetPriceSeries, ObservationKind, PriceObservation, build_asset_price_series
from backend.app.services.lots_analysis_service import LotsAnalysisService, _parse_transfer_pair_id

# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #

D = Decimal


def _svc() -> LotsAnalysisService:
    """The service with no session: only sync, argument-driven helpers are used."""
    return LotsAnalysisService(db=None)


def _resolver(target: str = "EUR", rates: dict | None = None) -> FxRateResolver:
    """An FxRateResolver with its rate table already populated.

    ``load()`` is the only async part of the resolver and the only part that
    needs a session; it merely fills ``_rates`` with one converted unit per
    (currency, date). Filling that table directly is what keeps this unit PURE.
    """
    resolver = FxRateResolver(target)
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
    close_currency: str | None = None,
) -> LotClosure:
    """A closure double; ``close_currency`` (CP-7a) is the currency of its close leg, None for the report currency.

    It is set only when named, so a double in the report currency builds the same LotClosure as before CP-7a.
    """
    closure = LotClosure(
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
    return closure if close_currency is None else replace(closure, close_currency=close_currency)


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


def _quote(day: date, close: Decimal, currency: str = "EUR") -> PriceObservation:
    """A market close in the home's daily price series (financial_math.price_marks): what ``price_history`` holds that day."""
    return PriceObservation(date=day, unit_price=close, currency=currency, kind=ObservationKind.MARKET)


def _trade(day: date, unit_price: Decimal, currency: str = "EUR") -> PriceObservation:
    """A BUY or SELL price in the home's daily price series: the trade's amount over its quantity, in the trade's currency."""
    return PriceObservation(date=day, unit_price=unit_price, currency=currency, kind=ObservationKind.TRADE)


def _series(*observations: PriceObservation) -> AssetPriceSeries:
    """The asset's daily price series, which the lots read their prices and references from since CP-7b."""
    return AssetPriceSeries(list(observations))


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
) -> PerformanceSourceContext:
    txs = transactions if transactions is not None else []
    return PerformanceSourceContext(
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
# L1b — the resolver reads its rates as steps: the reader stubbed where ``conversions`` reads it
# --------------------------------------------------------------------------- #
#
# ``FxRateResolver.load`` asks ``unit_rate_steps`` (``fx/conversion.py``, imported by name into ``conversions``) for the
# windows of days its pending currencies need, once per load, and no longer asks ``convert_bulk``. The new names are
# read through ``conversions_module`` while a test runs (``raising=False`` when patched: before L1b the module does not
# read ``unit_rate_steps``), never imported at module level, so only the tests that use them fail and the file still
# collects. Each docstring says what HEAD does today.


class _FlatSteps:
    """A unit-rate reader in the shape of ``fx.conversion.UnitRateSteps`` with one rate from the first day of the calendar on:
    ``at`` answers it on any day (the resolver, not the reader, keeps to the days asked); None for no rate at all."""

    def __init__(self, rate: Decimal | None) -> None:
        self.rate = rate
        self.days = (date(1, 1, 1),) if rate is not None else ()
        self.values = (rate,) if rate is not None else ()

    def at(self, day: date) -> Decimal | None:
        return self.rate


def _stub_unit_rate_steps(monkeypatch, rates: dict[str, Decimal | None] | None = None, default: Decimal | None = D("1.25")) -> list[dict[tuple[str, str], list[tuple[date, date]]]]:
    """``conversions.unit_rate_steps`` replaced by a reader of one flat rate per source currency (``rates[source]``, else
    ``default``; None: no step), and the list it fills with the requests of each call, ``{(source, destination): windows}``.
    ``conversions.convert_bulk``, which ``load`` no longer asks, is replaced by a stub that refuses the call, so a ``load`` that
    still asks it fails on the spot instead of reaching a session. Both ``raising=False``: the first name is new in
    ``conversions`` and the second is dropped by the cure."""
    calls: list[dict[tuple[str, str], list[tuple[date, date]]]] = []

    async def unit_rate_steps(_session, requests):
        calls.append({pair: list(windows) for pair, windows in requests.items()})
        return {pair: _FlatSteps((rates or {}).get(pair[0], default)) for pair in requests}

    async def convert_bulk_refused(*_args, **_kwargs):
        raise AssertionError("FxRateResolver.load asked convert_bulk: it must read unit_rate_steps")

    monkeypatch.setattr(conversions_module, "unit_rate_steps", unit_rate_steps, raising=False)
    monkeypatch.setattr(conversions_module, "convert_bulk", convert_bulk_refused, raising=False)
    return calls


def _need_days(resolver: FxRateResolver):
    """``resolver.need_days``, read by name: before L1b it does not exist, and only the tests that call it fail."""
    need_days = getattr(resolver, "need_days", None)
    assert need_days is not None, "FxRateResolver has no need_days"
    return need_days


def _covered_days(windows: list[tuple[date, date]]) -> set[date]:
    """The days of ``windows`` (both ends included); a window that ends before it starts is a defect."""
    assert all(first <= last for first, last in windows), f"a window ends before it starts: {windows}"
    return {first + timedelta(days=offset) for first, last in windows for offset in range((last - first).days + 1)}


def _merged_windows(windows: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """Ascending windows with the overlapping and touching ones joined: what they cover, without a set of days."""
    merged: list[tuple[date, date]] = []
    for first, last in sorted(windows):
        if merged and first <= merged[-1][1] + timedelta(days=1):
            merged[-1] = (merged[-1][0], max(merged[-1][1], last))
        else:
            merged.append((first, last))
    return merged


class _Asked:
    """What a resolver was asked, as single days (``need``: its ``_needs``) or as windows (``need_days``, L1b): a test of what
    ``collect_fx_needs`` asks reads it the same before and after the cure. Wrap the resolver before the call."""

    def __init__(self, resolver: FxRateResolver, monkeypatch) -> None:
        self.resolver = resolver
        self.windows: list[tuple[str, date, date]] = []
        original = getattr(resolver, "need_days", None)
        if original is not None:

            def recording(currency, first, last):
                self.windows.append((currency, first, last))
                return original(currency, first, last)

            monkeypatch.setattr(resolver, "need_days", recording)

    def covers(self, currency: str, day: date) -> bool:
        return (currency, day) in set(self.resolver._needs) or any(asked == currency and first <= day <= last for asked, first, last in self.windows)

    def currencies(self) -> set[str]:
        return {currency for currency, _day in self.resolver._needs} | {currency for currency, _first, _last in self.windows}


# --------------------------------------------------------------------------- #
# FxRateResolver
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

    # -- B3a: a conversion that fails is recorded, never replaced ------------ #

    def test_missing_pairs_reports_each_failed_conversion_once_per_pair_and_date(self):
        """B3a: no USD or GBP rate was loaded, so these four conversions fail; each (pair, day) is reported once.

        Same "FROM/TO" pair as the average-cost gaps, dates ascending, entries ordered by pair:
        this is what the analysis merges into ``data_quality.missing_fx_pairs``.
        """
        resolver = _resolver("EUR")

        resolver.convert(D("100"), "USD", date(2024, 1, 12))
        resolver.convert(D("5"), "GBP", date(2024, 1, 11))
        resolver.convert(D("50"), "USD", date(2024, 1, 10))
        resolver.convert(D("7"), "USD", date(2024, 1, 12))  # same pair, same day: one date

        assert resolver.missing_pairs() == [
            WACMissingPairInfo(pair="GBP/EUR", dates=[date(2024, 1, 11)]),
            WACMissingPairInfo(pair="USD/EUR", dates=[date(2024, 1, 10), date(2024, 1, 12)]),
        ]

    def test_missing_pairs_ignores_identities_absent_amounts_and_successful_conversions(self):
        """B3a: only a conversion that was needed and could not be made is a gap.

        The target currency and an unknown or empty currency are identities, a None amount has
        nothing to convert, a loaded rate converts. The final miss, on a day the None amount
        already asked about, proves the resolver was recording all along.
        """
        resolver = _resolver("EUR", {("USD", date(2024, 1, 10)): D("0.9")})

        resolver.convert(D("100"), "EUR", date(2024, 1, 11))
        resolver.convert(D("100"), None, date(2024, 1, 11))
        resolver.convert(D("100"), "", date(2024, 1, 11))
        resolver.convert(None, "USD", date(2024, 1, 11))
        resolver.convert(D("100"), "USD", date(2024, 1, 10))
        assert resolver.missing_pairs() == []

        resolver.convert(D("100"), "USD", date(2024, 1, 11))
        assert resolver.missing_pairs() == [WACMissingPairInfo(pair="USD/EUR", dates=[date(2024, 1, 11)])]


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
# collect_fx_needs
# --------------------------------------------------------------------------- #


class TestCollectFxNeeds:
    def _call(self, resolver, **overrides):
        kwargs = {
            "fx_resolver": resolver,
            "analyses": [],
            "lots_by_id": {},
            "selected_ids": [],
            "transactions": [],
            "price_series": AssetPriceSeries([]),
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
        collect_fx_needs(**kwargs)

    def test_wac_analyses_ask_the_lots_resolver_for_no_rate(self):
        """The WAC lines convert through financial_math.average_cost, each acquisition at its own date.

        A BUY paid in USD and an ADJUSTMENT-in costed in USD both need a USD rate for the WAC
        lines; neither reaches this resolver, so it loads no rate the WAC lines never read. (Which
        currency an ADJUSTMENT-in is costed in is pinned by test_average_cost.py, U13/U16.)
        """
        resolver = _resolver("EUR")
        self._call(
            resolver,
            analyses=[LotAnalysisType.BROKER_WAC_HISTORY, LotAnalysisType.CUMULATIVE_WAC_HISTORY],
            transactions=[
                _tx(1, tx_type=TransactionType.BUY, quantity=D("10"), amount=D("-100"), currency="USD"),
                _tx(
                    2,
                    tx_type=TransactionType.ADJUSTMENT,
                    quantity=D("10"),
                    amount=D("0"),
                    currency="GBP",
                    cost_basis_override=D("5"),
                    cost_basis_currency="USD",
                ),
                _tx(3, tx_type=TransactionType.SELL, quantity=D("-5"), amount=D("60"), currency="USD"),
            ],
        )
        assert resolver._needs == []

    def test_lot_summary_skips_the_reference_price_when_none_can_be_resolved(self):
        """The lot carries a reference price but the asset's series has no observation at all."""
        resolver = _resolver("EUR")
        lot = _lot(1, currency="EUR", reference_unit_price=D("9"))
        self._call(
            resolver,
            analyses=[LotAnalysisType.LOT_SUMMARY],
            lots_by_id={1: lot},
            selected_ids=[1],
            price_series=AssetPriceSeries([]),
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

    def test_a_priced_adjustment_is_no_rate_the_market_series_reads(self, monkeypatch):
        """J-17: only BUY and SELL mark the asset, so the market series needs the currency a BUY was
        paid in on every day of the window, and never the cost-basis currency of an ADJUSTMENT — the
        adjustment carries a WAC, not a price, and leaves no mark to convert.

        Before J-17: the series also registered the ADJUSTMENT's cost-basis currency (GBP) on every day
        from 2024-01-01 to 2024-06-01, to convert the adjustment's mark.

        Read through ``_Asked``: the days are asked one by one (``need``) or as a window (``need_days``, L1b), the same.
        """
        resolver = _resolver("EUR")
        asked = _Asked(resolver, monkeypatch)
        self._call(
            resolver,
            analyses=[LotAnalysisType.PRICE_HISTORY],
            transactions=[
                _tx(1, tx_type=TransactionType.BUY, quantity=D("10"), amount=D("-100"), currency="USD"),
                _tx(2, tx_type=TransactionType.ADJUSTMENT, tx_date=date(2024, 2, 1), quantity=D("10"), amount=D("0"), currency=None, cost_basis_override=D("5"), cost_basis_currency="GBP"),
            ],
        )
        assert all(asked.covers("USD", day) for day in (date(2024, 1, 1), date(2024, 3, 15), date(2024, 6, 1))), "guard: a BUY's currency is read on every day of the window"
        assert asked.currencies() == {"USD"}, f"currencies the market series asks: {sorted(asked.currencies())}"

    @pytest.mark.asyncio
    async def test_the_market_series_asks_its_currencies_as_windows_not_day_by_day(self, monkeypatch):
        """L1b: the market price line reads each mark's currency on every day from ``computed_from`` to ``actual_to``; over a
        ~20 000-day range (1950-01-01, 20 000 days) a BUY in USD and a close in GBP are two currencies, asked as two windows —
        ``need`` called at most 40 times, not one per day — and the next ``load`` hands ``unit_rate_steps`` those two
        currencies over exactly [computed_from, actual_to] (the reader stubbed).

        Today: ``need`` is called 40 000 times, one per currency per day; the windows are never asked.
        """
        computed_from = date(1950, 1, 1)
        actual_to = computed_from + timedelta(days=19_999)
        resolver = _resolver("EUR")
        needs: list[str] = []
        original_need = resolver.need

        def counting_need(currency, day):
            needs.append(currency)
            original_need(currency, day)

        monkeypatch.setattr(resolver, "need", counting_need)
        self._call(
            resolver,
            analyses=[LotAnalysisType.PRICE_HISTORY],
            transactions=[_tx(1, tx_type=TransactionType.BUY, tx_date=computed_from, quantity=D("10"), amount=D("-100"), currency="USD")],
            prices=[_price(date(1950, 3, 1), D("11"), "GBP")],
            computed_from=computed_from,
            actual_to=actual_to,
        )
        assert len(needs) <= 40, f"{len(needs)} need() calls for 2 market currencies over {(actual_to - computed_from).days + 1} days; the cure asks them as windows"

        calls = _stub_unit_rate_steps(monkeypatch)
        await resolver.load(None)

        assert len(calls) == 1, f"one load, one unit_rate_steps call; got {len(calls)}"
        assert {pair: _merged_windows(windows) for pair, windows in calls[0].items()} == {("USD", "EUR"): [(computed_from, actual_to)], ("GBP", "EUR"): [(computed_from, actual_to)]}


# --------------------------------------------------------------------------- #
# collect_performance_fx_needs
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
        collect_performance_fx_needs(**kwargs)

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

    def test_a_short_lot_needs_its_currency_at_its_opening_date_and_its_closure_no_proceeds_rate(self):
        """MF-E2: a SHORT lot's opening sale is an external inflow of the performance series — its cumulative proceeds,
        converted from the lot's currency at its opening date (USD on 10 Jan 2024) —, so that rate is asked; its closure,
        in the report currency (``close_currency`` None), still asks for nothing.

        Before MF-E2 (read 20/10/2026) this test was ``test_a_closure_of_a_short_lot_needs_no_proceeds_fx`` and asserted
        ``[]`` («Only LONG sells produce an external inflow»): no flow read a short's proceeds.
        """
        resolver = _resolver("EUR")
        self._call(
            resolver,
            closures=[_closure(1)],
            lots_by_id={1: _lot(1, direction="SHORT", currency="USD")},
        )
        assert resolver._needs == [("USD", date(2024, 1, 10))]

    def test_a_closure_whose_lot_is_unknown_is_skipped(self):
        resolver = _resolver("EUR")
        self._call(resolver, closures=[_closure(99)], lots_by_id={1: _lot(1, currency="USD")})
        assert resolver._needs == []

    def test_a_long_sell_closure_needs_its_currency_on_the_close_date_and_the_lots_on_its_opening_date(self):
        """CP-7a: a USD lot sold in USD asks for USD on the sale's date (its proceeds) and on the lot's opening date (its cost).

        Before CP-7a it asked for the lot's currency on the close date only: [("USD", 1 Feb)].
        """
        resolver = _resolver("EUR")
        self._call(resolver, closures=[_closure(1, close_currency="USD")], lots_by_id={1: _lot(1, currency="USD")})
        assert sorted(resolver._needs) == [("USD", date(2024, 1, 10)), ("USD", date(2024, 2, 1))]


# --------------------------------------------------------------------------- #
# adjustment_cash_flow_cost
# --------------------------------------------------------------------------- #


class TestAdjustmentCashFlowCost:
    def test_prefers_the_cost_basis_override_times_the_quantity(self):
        """The declared unit cost of an ADJUSTMENT-in is the external money that went in."""
        cost = adjustment_cash_flow_cost(
            tx=_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("-999"), cost_basis_override=D("7"), cost_basis_currency="EUR"),
            asset_currency="EUR",
            fx_resolver=_resolver("EUR"),
        )
        assert cost == D("70")

    def test_converts_the_override_into_the_target_currency(self):
        cost = adjustment_cash_flow_cost(
            tx=_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("0"), cost_basis_override=D("7"), cost_basis_currency="USD"),
            asset_currency="EUR",
            fx_resolver=_resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}),
        )
        assert cost == D("35.0")

    def test_falls_back_to_the_transaction_amount_when_no_override_is_set(self):
        cost = adjustment_cash_flow_cost(
            tx=_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("-250"), currency="EUR"),
            asset_currency="EUR",
            fx_resolver=_resolver("EUR"),
        )
        assert cost == D("250")

    def test_returns_none_when_the_adjustment_carries_no_money_at_all(self):
        """A quantity-only correction must not inject a phantom cash flow."""
        cost = adjustment_cash_flow_cost(
            tx=_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("0"), currency="EUR"),
            asset_currency="EUR",
            fx_resolver=_resolver("EUR"),
        )
        assert cost is None


# --------------------------------------------------------------------------- #
# Average-cost lines -> WAC history points
# --------------------------------------------------------------------------- #
#
# The WAC lines are financial_math.average_cost lines: one per broker and one for every broker
# together (keyed ALL_BROKERS), built by _compute_average_cost_lines with a single
# compute_average_costs call. Here the lines come from the same pure fold, _fold_average_costs,
# with the conversions it would have received already resolved -- which keeps this unit PURE.


def _acquired(day: date, quantity: str, paid: str, currency: str = "EUR") -> CostMovement:
    return CostMovement(movement_id=None, transaction_type="BUY", date=day, kind=CostMovementKind.ACQUISITION, quantity=D(quantity), cost_amount=D(paid), cost_currency=currency)


def _sold(day: date, quantity: str) -> CostMovement:
    return CostMovement(movement_id=None, transaction_type="SELL", date=day, kind=CostMovementKind.REDUCTION, quantity=D(quantity))


def _line(key, *movements: CostMovement, resolved: dict | None = None) -> AverageCost:
    """The EUR line of an EUR asset folded from ``movements`` (in this order), as the lots page builds it.

    ``resolved`` answers the conversion requests; a request it lacks is a missing conversion, as
    a convert_bulk without that rate would report it -- never a zero.
    """
    position = CostPosition(key=key, asset_currency="EUR", movements=movements)
    return _fold_average_costs([position], report_currency="EUR", asset_leg=False, resolved=resolved or {})[key]


class TestAverageCostPoints:
    """``average_cost_points``: (date, WAC, pool quantity) for each history date, read off one line."""

    def test_a_line_without_movements_has_no_point(self):
        """A broker in scope that never traded this asset must not emit flat-zero points."""
        assert average_cost_points(_line(1), _days(date(2024, 1, 1), 3)) == []

    def test_dates_before_the_first_movement_have_no_point(self):
        """The pool does not exist yet, so there is no average cost to report."""
        line = _line(1, _acquired(date(2024, 1, 3), "10", "50"))

        points = average_cost_points(line, _days(date(2024, 1, 1), 4))

        assert points == [(date(2024, 1, 3), D("5"), D("10")), (date(2024, 1, 4), D("5"), D("10"))]

    def test_each_point_is_the_pool_after_the_last_movement_on_or_before_its_date(self):
        """10 for 50, then on one day 10 for 150 and a sale of 5 (purchase first): 5 → 10 per unit, 10 → 15 units."""
        line = _line(1, _acquired(date(2024, 1, 1), "10", "50"), _sold(date(2024, 1, 3), "-5"), _acquired(date(2024, 1, 3), "10", "150"))

        points = average_cost_points(line, _days(date(2024, 1, 1), 4))

        assert points == [
            (date(2024, 1, 1), D("5"), D("10")),
            (date(2024, 1, 2), D("5"), D("10")),
            (date(2024, 1, 3), D("10"), D("15")),
            (date(2024, 1, 4), D("10"), D("15")),
        ]

    def test_an_acquisition_counts_at_its_cost_in_the_report_currency(self):
        """10 for 110 EUR, then 10 paid 100 USD that the FX service turned into 90 EUR on that day: 200 EUR for 20."""
        paid_in_usd = _acquired(date(2024, 1, 2), "10", "100", "USD")
        resolved = {_ConversionRequest("USD", "EUR", date(2024, 1, 2), D("100")): _ResolvedConversion(amount=D("90"), rate_date=date(2024, 1, 2))}
        line = _line(1, _acquired(date(2024, 1, 1), "10", "110"), paid_in_usd, resolved=resolved)

        points = average_cost_points(line, _days(date(2024, 1, 1), 2))

        assert points == [(date(2024, 1, 1), D("11"), D("10")), (date(2024, 1, 2), D("10"), D("20"))]

    def test_a_day_whose_pool_lacks_part_of_its_cost_has_no_point_until_the_pool_empties(self):
        """No rate for the MGA purchase: from it until the pool empties the line draws nothing, not a wrong average."""
        line = _line(
            1,
            _acquired(date(2024, 1, 1), "10", "100"),
            _acquired(date(2024, 1, 3), "10", "5000", "MGA"),  # nothing resolves it: a missing conversion
            _sold(date(2024, 1, 5), "-20"),
            _acquired(date(2024, 1, 7), "4", "60"),
        )
        assert line.has_missing_report_fx, "precondition: the fold reports the MGA purchase as unconverted"

        points = average_cost_points(line, _days(date(2024, 1, 1), 8))

        assert points == [
            (date(2024, 1, 1), D("10"), D("10")),
            (date(2024, 1, 2), D("10"), D("10")),
            (date(2024, 1, 5), D("0"), D("0")),
            (date(2024, 1, 6), D("0"), D("0")),
            (date(2024, 1, 7), D("15"), D("4")),
            (date(2024, 1, 8), D("15"), D("4")),
        ]


# --------------------------------------------------------------------------- #
# build_performance_history
# --------------------------------------------------------------------------- #


class TestBuildPerformanceHistory:
    """No day is valued at cost here (``at_cost_until=None``): the rules of a day with a mark, or without one outside the days at cost; the days at cost are ``TestPerformanceHistoryAtCost``."""

    def _call(self, **overrides):
        kwargs = {
            "scope_broker_ids": [1],
            "history_dates": _days(date(2024, 1, 10), 5),
            "market_prices": {day: D("10") for day in _days(date(2024, 1, 10), 5)},
            "asset_currency": "EUR",
            "fx_resolver": _resolver("EUR"),
            "context": _perf_context(),
            "quote_base_quantity": 1,
            "at_cost_until": None,
        }
        kwargs.update(overrides)
        return build_performance_history(**kwargs)

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

    # -- B3a: an external cash flow that cannot be converted ----------------- #
    #
    # Each history below starts the same way: 100 bought for 1000 EUR on the 10th, priced 10 EUR
    # that day and one more each day after. On the 12th money moves in a currency with no rate
    # that day, so the series is known until the 11th and unknown from the 12th on -- never
    # computed with the native amount read as EUR.

    @staticmethod
    def _rising_prices() -> dict[date, Decimal]:
        """10 EUR on the 10th, one more each day: 14 EUR on the 14th."""
        return {day: D(10 + offset) for offset, day in enumerate(_days(date(2024, 1, 10), 5))}

    @staticmethod
    def _known_until_the_11th() -> list[tuple[date, Decimal | None, Decimal | None]]:
        """(date, roi, twrr): 1000 EUR invested, worth 1000 then 1100; nothing from the 12th."""
        return [
            (date(2024, 1, 10), D("0"), None),
            (date(2024, 1, 11), D("0.1"), D("0.1")),
            (date(2024, 1, 12), None, None),
            (date(2024, 1, 13), None, None),
            (date(2024, 1, 14), None, None),
        ]

    def test_a_buy_that_cannot_be_converted_voids_roi_and_twrr_from_its_date(self):
        """B3a: 50 more bought on the 12th for 600 USD, with no USD rate that day.

        The money invested on the 12th is unknown in EUR. The native fallback counted 600 USD as
        600 EUR (ROI 12.5% on the 12th); the 10th and the 11th, before that flow, are unchanged.
        """
        points = self._call(
            market_prices=self._rising_prices(),
            context=_perf_context(
                transactions=[_tx(1), _tx(2, tx_date=date(2024, 1, 12), quantity=D("50"), amount=D("-600"), currency="USD")],
                fragments_by_lot={1: [_fragment(1)], 2: [_fragment(2, fragment_id="frag-2", quantity=D("50"), start_date=date(2024, 1, 12))]},
                lots_by_id={1: _lot(1), 2: _lot(2, currency="USD", opening_date=date(2024, 1, 12), original_quantity=D("50"), original_cost=D("600"), opening_unit_price=D("12"), open_quantity=D("50"))},
            ),
        )

        assert [(point.date, point.roi, point.twrr) for point in points] == self._known_until_the_11th()

    def test_an_adjustment_in_whose_declared_cost_cannot_be_converted_voids_roi_and_twrr_from_its_date(self):
        """B3a: the 50 of the 12th recorded by ADJUSTMENT, declared at 12 USD each, no USD rate that day.

        cost_basis_override × quantity is the money that came in, and it is unknown in EUR exactly
        like the unconvertible BUY. The native fallback counted 600 USD as 600 EUR.
        """
        adjustment = _tx(2, tx_type=TransactionType.ADJUSTMENT, tx_date=date(2024, 1, 12), quantity=D("50"), amount=D("0"), cost_basis_override=D("12"), cost_basis_currency="USD")
        points = self._call(
            market_prices=self._rising_prices(),
            context=_perf_context(
                transactions=[_tx(1), adjustment],
                fragments_by_lot={1: [_fragment(1)], 2: [_fragment(2, fragment_id="frag-2", quantity=D("50"), start_date=date(2024, 1, 12))]},
                lots_by_id={1: _lot(1), 2: _lot(2, currency="USD", opening_date=date(2024, 1, 12), original_quantity=D("50"), original_cost=D("600"), opening_unit_price=D("12"), open_quantity=D("50"))},
            ),
        )

        assert [(point.date, point.roi, point.twrr) for point in points] == self._known_until_the_11th()

    def test_a_sale_whose_proceeds_cannot_be_converted_voids_roi_and_twrr_from_its_date(self):
        """B3a: a USD lot bought for 2000 USD at 0.5 (1000 EUR); 40 sold on the 12th for 960 USD, no USD rate that day.

        The cash that left on the 12th is unknown in EUR. The native fallback counted 960 USD as
        960 EUR and reported an ROI of 1700% on the 12th. Since CP-7a the sale's proceeds convert from
        its own currency (the closure's close_currency, USD), no longer from the lot's: the same here.
        """
        sell = _tx(2, tx_type=TransactionType.SELL, tx_date=date(2024, 1, 12), quantity=D("-40"), amount=D("960"), currency="USD")
        points = self._call(
            market_prices=self._rising_prices(),
            fx_resolver=_resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}),
            context=_perf_context(
                transactions=[_tx(1, amount=D("-2000"), currency="USD"), sell],
                fragments_by_lot={1: [_fragment(1, end_date=date(2024, 1, 12)), _fragment(1, fragment_id="frag-1b", quantity=D("60"), start_date=date(2024, 1, 12))]},
                lots_by_id={1: _lot(1, currency="USD", original_cost=D("2000"), opening_unit_price=D("20"), open_quantity=D("60"))},
                engine_result=_engine_result(closures=[_closure(1, transaction_id=2, quantity=D("40"), close_date=date(2024, 1, 12), proceeds=D("960"), close_currency="USD")]),
            ),
        )

        assert [(point.date, point.roi, point.twrr) for point in points] == self._known_until_the_11th()


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
            "price_series": _series(_quote(date(2024, 1, 10), D("10"))),
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

    def test_a_short_lot_values_its_proceeds_less_its_buy_backs_and_its_open_position(self):
        """Shorting: the money came in first, the buy-backs paid part of it out, and the open leg is a liability.

        100 sold short at 15: 1500 of proceeds, the lot's own (the sale happened at opening). 40 bought back at 12: 480,
        the cover's cost — its proceeds field, 900 here, is never read. 60 still open at 12: 720. Total value = pnl =
        1500 − 480 − 720 = 300, i.e. 100 × (15 − 12). R10 (CP-7a). Before it the buy-back was never subtracted: total
        value and pnl 1500 − 720 = 780. (The double used to keep its open quantity at 100 beside a cover of 40, which
        that formula could not see.)
        """
        lot = _lot(1, direction="SHORT", opening_unit_price=D("15"), original_cost=D("1500"), open_quantity=D("60"), cumulative_proceeds=D("1500"))
        cover = _closure(1, quantity=D("40"), close_reason="BUY", open_unit_price=D("15"), close_unit_price=D("12"), realized_pnl=D("120"), proceeds=D("900"))
        row = self._call(lot=lot, closures_by_lot={1: [cover]})
        # open_value = 60 * 12 = 720; 1500 of proceeds less 480 paid for the cover -> total 300, and pnl == total.
        assert (row.open_value, row.total_value, row.pnl) == (D("720"), D("300"), D("300"))

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

    # -- B3a: a figure that needs a missing conversion is None --------------- #

    def test_a_lot_whose_cost_cannot_be_converted_keeps_its_market_value_but_reports_no_pnl_or_return(self):
        """B3a: a USD lot with no USD rate at its opening date; the latest price is known in EUR.

        What the lot is worth today is known (100 × 12 EUR); what it cost in EUR is not, so every
        figure measured against that cost is unknown. The native fallback took 1000 USD for the
        opening value and 0 for the cost in the P&L: pnl 1200, return 125%, yield 5%.
        """
        row = self._call(lot=_lot(1, currency="USD"), income_by_lot={1: D("50")})

        assert (row.value_source, row.open_value) == ("MARKET_PRICE", D("1200"))
        derived = ("pnl", "market_pnl", "total_pnl", "total_return", "cash_yield", "net_total_pnl", "net_total_return", "annualized_return")
        assert {name: getattr(row, name) for name in derived} == dict.fromkeys(derived)

    def test_an_unpriced_lot_whose_cost_cannot_be_converted_is_not_valued_at_cost(self):
        """B3a: ESTIMATED_AT_COST values the open quantity at its cost in EUR; without a USD rate there is none.

        With the rate the same lot is valued at cost (the control, 1000 USD at 0.5); without it the
        native fallback valued it at 1000 "EUR".
        """
        lot = _lot(1, currency="USD")
        with_rate = self._call(lot=lot, market_prices={}, estimated_mode=True, fx_resolver=_resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}))
        assert (with_rate.value_source, with_rate.open_value) == ("ESTIMATED_AT_COST", D("500"))

        row = self._call(lot=lot, market_prices={}, estimated_mode=True)

        assert (row.value_source, row.open_value, row.pnl) == (None, None, None)

    # -- B3b: a base field is its conversion, or nothing ---------------------- #

    @staticmethod
    def _sold_twice() -> list[LotClosure]:
        """40 of the 100 units sold in two halves, in USD, 20 on 20 Jan and 20 on 1 Feb: 240 USD of proceeds and 40 of native gain each."""
        return [
            _closure(1, transaction_id=500, quantity=D("20"), close_date=date(2024, 1, 20), realized_pnl=D("40"), proceeds=D("240"), close_currency="USD"),
            _closure(1, transaction_id=501, quantity=D("20"), close_date=date(2024, 2, 1), realized_pnl=D("40"), proceeds=D("240"), close_currency="USD"),
        ]

    def test_with_every_rate_the_base_fields_are_the_converted_amounts(self):
        """B3b control: a USD lot whose opening and both sales have a USD rate (0.5, 0.5, 0.6).

        The cost and unit price at the opening rate (1000 × 0.5, 10 × 0.5), the proceeds each at their sale's rate
        (240 × 0.5 + 240 × 0.6). The realized P&L since CP-7a (decision 26): each sale's proceeds at its rate less the cost
        of its 20 units at the opening rate, (120 − 100) + (144 − 100) = 64. Before CP-7a: 44 = 40 × 0.5 + 40 × 0.6, each
        sale's native gain at the sale's rate.
        """
        rates = {("USD", date(2024, 1, 10)): D("0.5"), ("USD", date(2024, 1, 20)): D("0.5"), ("USD", date(2024, 2, 1)): D("0.6")}
        row = self._call(lot=_lot(1, currency="USD", open_quantity=D("60")), closures_by_lot={1: self._sold_twice()}, fx_resolver=_resolver("EUR", rates))

        assert (row.original_cost, row.opening_unit_price, row.realized_pnl, row.cumulative_proceeds) == (D("500"), D("5"), D("64"), D("264"))

    def test_the_cost_of_a_lot_without_a_rate_at_its_opening_is_unknown(self):
        """B3b: a USD lot with no USD rate at its opening date, analysed in EUR.

        original_cost and opening_unit_price are the cost in EUR at the opening date; without that rate
        they are unknown. Today the required fields carry the native 1000 and 10 USD as if they were euros.
        """
        row = self._call(lot=_lot(1, currency="USD"))

        assert (row.original_cost, row.opening_unit_price) == (None, None)

    def test_the_realized_figures_of_a_long_lot_with_a_sale_without_a_rate_are_unknown(self):
        """B3b: the same USD lot, costed at 0.5; its first sale (20 Jan) has a rate, its second (1 Feb) has none.

        realized_pnl and cumulative_proceeds need every sale in EUR, so they are unknown -- neither the
        known half alone nor, as today, the known half plus the native USD of the other (20 + 40, 120 + 240).
        """
        rates = {("USD", date(2024, 1, 10)): D("0.5"), ("USD", date(2024, 1, 20)): D("0.5")}
        row = self._call(lot=_lot(1, currency="USD", open_quantity=D("60")), closures_by_lot={1: self._sold_twice()}, fx_resolver=_resolver("EUR", rates))

        assert (row.original_cost, row.opening_unit_price) == (D("500"), D("5"))
        assert (row.realized_pnl, row.cumulative_proceeds) == (None, None)

    def test_the_proceeds_of_a_short_lot_without_a_rate_at_its_opening_are_unknown(self):
        """B3b: a USD short that sold 1500 USD at its opening, a day without a USD rate; its cover (1 Feb, in USD) has one.

        A short's proceeds arrived at its opening, so they are converted there: unknown, never 1500 "EUR".
        Its realized P&L is unknown too since CP-7a: the opening sale is one of its legs (40 × 10 at the opening
        rate, less the cover's 40 × 12 at 0.5). Before CP-7a: −40 = −80 × 0.5, the cover's rate only.
        """
        lot = _lot(1, direction="SHORT", currency="USD", open_quantity=D("60"), cumulative_proceeds=D("1500"))
        cover = _closure(1, quantity=D("40"), close_reason="BUY", realized_pnl=D("-80"), proceeds=D("0"), close_currency="USD")
        row = self._call(lot=lot, closures_by_lot={1: [cover]}, fx_resolver=_resolver("EUR", {("USD", date(2024, 2, 1)): D("0.5")}))

        assert (row.realized_pnl, row.cumulative_proceeds) == (None, None)

    # -- CP-7a, T-B6: a reference price that cannot be converted has no source -- #

    @pytest.mark.parametrize(
        ("lot_currency", "quote", "expected"),
        [
            pytest.param("USD", None, (None, None), id="its-own-price-in-USD-without-a-rate"),
            pytest.param("EUR", ("9", "USD"), (None, None), id="a-quote-in-USD-without-a-rate"),
            pytest.param("EUR", None, (D("10"), "exact"), id="GUARD-its-own-price-in-EUR"),
        ],
    )
    def test_a_reference_price_without_a_rate_has_no_source(self, lot_currency, quote, expected):
        """R8, T-B6: (reference_unit_price, reference_price_source) of the summary, no USD rate anywhere: no price, no source.

        The return history already reads it so (histories.py, build_return_history). Before CP-7a the source stayed beside
        the missing price: (None, "exact") for the lot's own USD price, (None, "fallback") for a quote in USD found on 8 Jan.
        GUARD: a reference that converts keeps its source. CP-7b moved it to the asset's price series (the quote of 8 Jan
        is now a market observation, the reference dated the opening day, 10 Jan): without any USD rate, the same values.
        """
        if quote is None:
            lot, series = _lot(1, currency=lot_currency), AssetPriceSeries([])
        else:
            lot = _lot(1, currency=lot_currency, reference_unit_price=D(quote[0]), reference_price_source="fallback")
            series = _series(_quote(date(2024, 1, 8), D(quote[0]), quote[1]))

        row = self._call(lot=lot, price_series=series)

        assert (row.reference_unit_price, row.reference_price_source) == expected


# --------------------------------------------------------------------------- #
# build_value_history / build_return_history
# --------------------------------------------------------------------------- #


class TestBuildValueAndReturnHistory:
    """Both builders share the same market_price-is-None ladder, so both are pinned.

    CP-7b: ``estimated_mode`` (one flag for the whole window) became ``at_cost_until``, the last day with no observation on
    or before it; every day up to it is valued at cost. ``_LAST_DAY`` puts the whole window at cost, as the flag did.
    """

    _LAST_DAY = date(2024, 1, 12)  # the last of the three history days the helpers use by default

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
            "at_cost_until": None,
            "quote_base_quantity": 1,
        }
        kwargs.update(overrides)
        return build_value_history(**kwargs)

    def _returns(self, **overrides):
        lot = overrides.pop("lot", _lot(1))
        kwargs = {
            "selected_ids": [1],
            "lots_by_id": {1: lot},
            "fragments_by_lot": {1: [_fragment(1)]},
            "market_prices": {},
            "price_series": _series(_quote(date(2024, 1, 10), D("10"))),
            "fx_resolver": _resolver("EUR"),
            "history_dates": _days(date(2024, 1, 10), 3),
            "closures_by_lot": {},
            "income_prefix_by_lot": {},
            "fees_prefix_by_lot": {},
            "taxes_prefix_by_lot": {},
            "at_cost_until": None,
            "quote_base_quantity": 1,
        }
        kwargs.update(overrides)
        return build_return_history(**kwargs)

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

    def test_value_of_a_closed_short_lot_on_an_unpriced_day_is_its_proceeds_less_its_buy_backs(self):
        """A covered short is worth the money it took in less what buying it back cost, whatever the market does next.

        100 sold short for 1500 and all bought back at 12 on 10 Jan (1200, the cover's cost — its proceeds field, 900 here,
        is never read): 300 on the unpriced 12th, total value and pnl alike. The proceeds field stays the opening sale's,
        1500 (GUARD). R10 (CP-7a). Before it the buy-back was never subtracted: total value and pnl 1500. (The cover used to
        be of 40 units only, on a lot closed whole.)
        """
        lot = _lot(1, direction="SHORT", open_quantity=D("0"), cumulative_proceeds=D("1500"))
        points = self._value(
            lot=lot,
            fragments_by_lot={1: [_fragment(1, direction="SHORT", end_date=date(2024, 1, 10))]},
            closures_by_lot={1: [_closure(1, quantity=D("100"), close_date=date(2024, 1, 10), close_reason="BUY", proceeds=D("900"))]},
        )
        last = next(point for point in points if point.date == date(2024, 1, 12))
        assert (last.open_value, last.proceeds, last.total_value, last.pnl) == (D("0"), D("1500"), D("300"), D("300"))

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
        """A covered short's return is its P&L after its buy-backs over its notional, on an unpriced day too: 0.2.

        100 sold short at 15 — a notional of 1500, its proceeds — and all bought back at 12 on 10 Jan, 1200: P&L 300, so
        (1500 + 300) / 1500 − 1 = 0.2, the lot summary's total P&L / opening value (CP-7a: R10 subtracts the buy-back, and a
        short's return reads against its notional). Before CP-7a: 0 = 1500 / 1500 − 1, a short read like a long — its
        proceeds taken for its value, its buy-back never subtracted.
        """
        lot = _lot(1, direction="SHORT", opening_unit_price=D("15"), original_cost=D("1500"), open_quantity=D("0"), cumulative_proceeds=D("1500"))
        cover = _closure(1, quantity=D("100"), close_date=date(2024, 1, 10), close_reason="BUY", open_unit_price=D("15"), close_unit_price=D("12"), realized_pnl=D("300"), proceeds=D("0"))
        points = self._returns(
            lot=lot,
            fragments_by_lot={1: [_fragment(1, direction="SHORT", unit_price=D("15"), end_date=date(2024, 1, 10))]},
            closures_by_lot={1: [cover]},
        )
        last = next(point for point in points if point.date == date(2024, 1, 12))
        assert last.total_return == D("0.2")

    # -- market price missing, position still open --------------------------- #

    def test_an_open_lot_on_an_unpriced_day_is_valued_at_cost_in_estimated_mode(self):
        """An unlisted holding: the only defensible mark is what it cost. No day of the window has an observation."""
        points = self._value(at_cost_until=self._LAST_DAY)
        assert {point.open_value for point in points} == {D("1000")}

    def test_an_open_lot_on_an_unpriced_day_emits_nothing_when_not_estimating(self):
        """A gap in a normally-quoted series must leave a hole, not a fabricated value."""
        assert self._value(at_cost_until=None) == []

    def test_an_open_short_lot_is_never_valued_at_cost(self):
        """The days at cost only rescue LONG lots; a short at cost would flip the sign."""
        assert self._value(lot=_lot(1, direction="SHORT"), at_cost_until=self._LAST_DAY) == []

    def test_return_of_an_open_lot_on_an_unpriced_day_uses_the_cost_mark(self):
        points = self._returns(at_cost_until=self._LAST_DAY)
        assert {point.total_return for point in points} == {D("0")}

    def test_return_of_an_open_lot_emits_nothing_when_not_estimating(self):
        assert self._returns(at_cost_until=None) == []

    def test_the_days_up_to_at_cost_until_are_at_cost_and_a_later_unpriced_day_is_a_gap(self):
        """CP-7b, the Dashboard's per-day rule in the lots (J-17): ``at_cost_until`` 11 Jan, a window of 10–14 Jan, X priced 12 EUR on the 13th only.

        (date, open value, P&L): 10 and 11 Jan have no observation on or before them, so the lot is worth its cost, 1000,
        P&L 0; the 13th is priced, 1200. The 12th and the 14th come after the cut without a market price — in the service a
        mark without a rate, since every day after the first observation has one — so they stay a gap, never at cost.
        Before CP-7b ``estimated_mode`` was one flag for the whole window and there was no cut to pass (TypeError).
        """
        points = self._value(history_dates=_days(date(2024, 1, 10), 5), market_prices={date(2024, 1, 13): D("12")}, at_cost_until=date(2024, 1, 11))

        assert [(point.date, point.open_value, point.pnl) for point in points] == [
            (date(2024, 1, 10), D("1000"), D("0")),
            (date(2024, 1, 11), D("1000"), D("0")),
            (date(2024, 1, 13), D("1200"), D("200")),
        ]

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
            price_series=AssetPriceSeries([]),
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

    # -- B3a: an amount that cannot be converted is never read as target ----- #

    def test_a_lot_whose_cost_cannot_be_converted_has_no_value_point(self):
        """B3a: a USD lot with no USD rate at its opening date, next to an EUR lot, both priced 12 EUR.

        The USD lot's cost in EUR is unknown, so no day can state its P&L: no point at all. The
        native fallback put 1000 USD in original_cost and drew a pnl of 200 from it. The EUR lot of
        the same call keeps all of its points.
        """
        days = _days(date(2024, 1, 10), 3)
        points = self._value(
            selected_ids=[1, 2],
            lots_by_id={1: _lot(1, currency="USD"), 2: _lot(2)},
            fragments_by_lot={1: [_fragment(1)], 2: [_fragment(2, fragment_id="frag-2")]},
            market_prices=dict.fromkeys(days, D("12")),
        )

        assert [(p.date, p.open_value, p.pnl) for p in points if p.lot_id == 2] == [(day, D("1200"), D("200")) for day in days]
        assert [(p.date, p.original_cost, p.pnl) for p in points if p.lot_id == 1] == []

    def test_a_closure_whose_proceeds_cannot_be_converted_ends_the_value_series_on_its_date(self):
        """B3a: a USD lot costed at 0.5 on its opening day; 40 sold on the 12th for 960 USD, no USD rate that day.

        The 10th and the 11th are fully known (100 × 12 EUR against a cost of 500 EUR) and stay.
        From the sale on its proceeds are unknown in EUR, so there is no point -- the native
        fallback added 960 USD to the EUR value. Since CP-7a the proceeds convert from the sale's
        own currency (close_currency, USD), no longer from the lot's: the same here.
        """
        days = _days(date(2024, 1, 10), 5)
        points = self._value(
            lot=_lot(1, currency="USD", open_quantity=D("60")),
            fragments_by_lot={1: [_fragment(1, end_date=date(2024, 1, 12)), _fragment(1, fragment_id="frag-1b", quantity=D("60"), start_date=date(2024, 1, 12))]},
            closures_by_lot={1: [_closure(1, close_date=date(2024, 1, 12), quantity=D("40"), proceeds=D("960"), close_currency="USD")]},
            market_prices=dict.fromkeys(days, D("12")),
            history_dates=days,
            fx_resolver=_resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}),
        )

        assert [(p.date, p.open_value, p.proceeds, p.original_cost, p.pnl) for p in points] == [
            (date(2024, 1, 10), D("1200"), D("0"), D("500"), D("700")),
            (date(2024, 1, 11), D("1200"), D("0"), D("500"), D("700")),
        ]

    def test_a_lot_whose_cost_cannot_be_converted_has_no_return_point(self):
        """B3a: the same USD and EUR lots: a return measured against an unknown cost cannot be stated.

        The native fallback divided the EUR value by 1000 USD and reported +20% for the USD lot.
        """
        days = _days(date(2024, 1, 10), 3)
        points = self._returns(
            selected_ids=[1, 2],
            lots_by_id={1: _lot(1, currency="USD"), 2: _lot(2)},
            fragments_by_lot={1: [_fragment(1)], 2: [_fragment(2, fragment_id="frag-2")]},
            market_prices=dict.fromkeys(days, D("12")),
        )

        assert [(p.date, p.total_return) for p in points if p.lot_id == 2] == [(day, D("0.2")) for day in days]
        assert [(p.date, p.total_return) for p in points if p.lot_id == 1] == []


# --------------------------------------------------------------------------- #
# J-33: the performance history values the days at cost
# --------------------------------------------------------------------------- #

# The quantized values ROI and TWRR come out of ``returns.py`` with (``_PREC_PCT``, six decimals), as strings.
_ZERO, _TEN, _TWENTY_ONE = "0.000000", "0.100000", "0.210000"


class TestPerformanceHistoryAtCost:
    """J-33: ``build_performance_history`` values the days at cost, as the value and return histories above do (CP-7b).

    ``at_cost_until`` is the last day with no observation on or before it (J-17 decision (a)). Up to it, a day without a
    mark gets a NAV at cost: the sum, over the in-scope fragments active that day, of ``residual_cost`` (the lot's cost at
    its opening rate, the fragment's quantity, the lot's original quantity) — a SHORT fragment minus its share of the lot's
    opening proceeds at the lot's opening rate (MF-E2, D3; before it a SHORT left the day without NAV) — no NAV when a cost
    has no rate. After it, a day without a mark (a mark without a rate) still gets none. A transfer crossing the scope on
    such a day moves cost, not market value: an incoming edge leg its own cost, an outgoing one
    (``hands_over_at_own_cost``) the cost of its closures, a replayed pair the cost of the pieces it moves.
    ``collect_performance_fx_needs`` asks for each LONG lot's currency at its opening date.

    Today the builder takes no ``at_cost_until`` (TypeError) and values only the days with a mark: the flows before the
    first one land on it, and ``calculate_twrr_period_series`` takes the first NAV as its base, so the jump from cost to
    the first price is in ROI and not in TWRR; a crossing transfer on a day without a mark voids ROI and TWRR from that
    day. Each docstring says what today's builder gives for its book, called without the keyword (``_book`` minus
    ``at_cost_until``). Values are read as the quantized strings the series return; None is no point.
    """

    # d0 … d10: 4–14 March 2024.
    _DAYS = _days(date(2024, 3, 4), 11)

    # -- builders ------------------------------------------------------------ #

    @staticmethod
    def _adjusted_in(tx_id: int, *, day: date, quantity: str = "10", broker_id: int = 1) -> Transaction:
        """An ADJUSTMENT-in at 100 EUR a unit, as the app stores one: no amount, the cost in its cost basis."""
        return _tx(tx_id, tx_type=TransactionType.ADJUSTMENT, tx_date=day, quantity=D(quantity), amount=D("0"), currency=None, broker_id=broker_id, cost_basis_override=D("100"), cost_basis_currency="EUR")

    @staticmethod
    def _long_lot(lot_id: int, *, day: date, quantity: str = "10", currency: str = "EUR", direction: str = "LONG") -> FifoLot:
        """A lot of ``quantity`` at 100 a unit, opened on ``day`` at broker 1, all still open."""
        return _lot(lot_id, direction=direction, opening_date=day, original_quantity=D(quantity), opening_unit_price=D("100"), original_cost=D(quantity) * 100, currency=currency, open_quantity=D(quantity))

    @staticmethod
    def _open_fragment(lot_id: int, *, day: date, quantity: str = "10", direction: str = "LONG") -> FragmentInterval:
        return _fragment(lot_id, fragment_id=f"frag-{lot_id}", direction=direction, quantity=D(quantity), unit_price=D("100"), start_date=day)

    def _adjusted_book(self, days: list[date], prices: dict[date, Decimal | None], at_cost_until: date | None, *, extra_lots: dict[int, tuple[FifoLot, FragmentInterval]] | None = None) -> dict:
        """The ADJUSTMENT-in of 10 at 100 on the first day (1 000 in), with ``extra_lots`` held beside it and no flow of theirs."""
        lots = {1: (self._long_lot(1, day=days[0]), self._open_fragment(1, day=days[0])), **(extra_lots or {})}
        context = _perf_context(transactions=[self._adjusted_in(1, day=days[0])], lots_by_id={lot_id: lot for lot_id, (lot, _) in lots.items()}, fragments_by_lot={lot_id: [fragment] for lot_id, (_, fragment) in lots.items()})
        return {"context": context, "history_dates": days, "market_prices": prices, "at_cost_until": at_cost_until}

    @staticmethod
    def _engine_book(rows: list, days: list[date], prices: dict[date, Decimal | None], at_cost_until: date, *, boundary_legs: dict | None = None) -> dict:
        """A book whose lots, fragments, closures and events come from the real engine over ``rows`` (brokers 1 and 2)."""
        result = run_fifo_lot_engine(rows, {1: False, 2: False}, target_currency="EUR")
        context = PerformanceSourceContext(
            transactions=rows,
            engine_result=result,
            lots_by_id={lot.lot_id: lot for lot in result.lots},
            fragments_by_lot=group_fragments(result.fragment_intervals),
            closures_by_lot=group_closures(result.closures),
            tx_by_id={row.id: row for row in rows},
            boundary_legs=boundary_legs or {},
        )
        return {"context": context, "history_dates": days, "market_prices": prices, "at_cost_until": at_cost_until}

    @staticmethod
    def _history(book: dict, *, scope_broker_ids: tuple[int, ...] = (1,), fx_resolver: FxRateResolver | None = None) -> list[tuple]:
        """(date, ROI, TWRR) of each day, the values as the quantized strings the series return, None for no point."""
        points = build_performance_history(
            scope_broker_ids=list(scope_broker_ids),
            history_dates=book["history_dates"],
            market_prices=book["market_prices"],
            asset_currency="EUR",
            fx_resolver=fx_resolver or _resolver("EUR"),
            context=book["context"],
            quote_base_quantity=1,
            at_cost_until=book["at_cost_until"],
        )
        return [(point.date, None if point.roi is None else str(point.roi), None if point.twrr is None else str(point.twrr)) for point in points]

    def _unpriced_then_110(self) -> tuple[list[date], dict[date, Decimal | None]]:
        """d0 … d5: no mark on d0–d3, 110 on d4 and d5."""
        days = self._DAYS[:6]
        return days, {day: (D("110") if day >= days[4] else None) for day in days}

    def _flat_then_ten_percent(self) -> list[tuple]:
        """d0 … d5 after J-33 for the transfer books: at cost until d3, the market 10% above cost from d4."""
        days = self._DAYS[:6]
        return [(days[0], _ZERO, None), *[(day, _ZERO, _ZERO) for day in days[1:4]], (days[4], _TEN, _TEN), (days[5], _TEN, _TEN)]

    # -- V1, V2: the days at cost carry NAV ----------------------------------- #

    def _v1_book(self) -> dict:
        days = self._DAYS
        prices = dict.fromkeys(days[:5]) | dict.fromkeys(days[5:10], D("110")) | {days[10]: D("121")}
        return self._adjusted_book(days, prices, days[4])

    def test_v1_the_days_at_cost_put_the_jump_to_the_first_price_in_twrr_as_in_roi(self):
        """V1: 10 adjusted in at a cost of 1 000 on d0, no mark on d0–d4, 110 on d5–d9 and 121 on d10, at cost until d4. NAV
        1 000 on d0–d4, 1 100 on d5–d9, 1 210 on d10; the 1 000 flows in on d0. ROI 0 on d0–d4, 10% on d5–d9, 21% on d10;
        TWRR, based on d0, 0 on d1–d4, 10% on d5–d9, 21% on d10: the jump from cost to the first price is in both.

        Today (read 17/10/2026): no point on d0–d4; the 1 000 lands on d5, the first NAV, so ROI 10% on d5–d9 and 21% on
        d10, while TWRR, based on d5, has no point on d5, 0 on d6–d9 and 10% on d10.
        """
        days = self._DAYS

        assert self._history(self._v1_book()) == [(days[0], _ZERO, None), *[(day, _ZERO, _ZERO) for day in days[1:5]], *[(day, _TEN, _TEN) for day in days[5:10]], (days[10], _TWENTY_ONE, _TWENTY_ONE)]

    def _v2_book(self) -> dict:
        days = self._DAYS[:5]
        return self._adjusted_book(days, dict.fromkeys(days), days[-1])

    def test_v2_an_asset_never_priced_has_roi_and_twrr_at_cost_every_day(self):
        """V2: the same 10 at 1 000 on d0, no mark at all on d0–d4, at cost until d4: NAV 1 000 every day, so ROI 0 every day
        and TWRR 0 from d1.

        Today (read 17/10/2026): no point at all — no mark, no NAV.
        """
        days = self._DAYS[:5]

        assert self._history(self._v2_book()) == [(days[0], _ZERO, None), *[(day, _ZERO, _ZERO) for day in days[1:]]]

    # -- GUARDS: the days at cost that still get no point --------------------- #
    #
    # (MF-E2, D3: the first of them, a day at cost with a short open, now gets a point — test_d3_… below.)

    def _short_book(self) -> dict:
        """Beside the 10 at 1 000 of d0, 5 sold short at 100 EUR on d2 (proceeds 500): the SHORT lot, its fragment and its
        opening SELL — the row the engine opens such a lot from."""
        days = self._DAYS[:5]
        short_lot = replace(self._long_lot(2, day=days[2], quantity="5", direction="SHORT"), cumulative_proceeds=D("500"))
        short = (short_lot, self._open_fragment(2, day=days[2], quantity="5", direction="SHORT"))
        book = self._adjusted_book(days, dict.fromkeys(days), days[-1], extra_lots={2: short})
        rows = [*book["context"].transactions, _tx(2, tx_type=TransactionType.SELL, tx_date=days[2], quantity=D("-5"), amount=D("500"))]
        book["context"] = replace(book["context"], transactions=rows, tx_by_id={row.id: row for row in rows})
        return book

    def test_d3_a_day_at_cost_with_a_short_lot_open_counts_minus_its_share_of_the_proceeds(self):
        """MF-E2, D3 (was the GUARD ``test_guard_a_day_at_cost_with_a_short_lot_open_gets_no_point``): beside the 10 at 1 000
        of d0, 5 sold short at 100 on d2 (proceeds 500), no mark on d0–d4, at cost until d4. On a day at cost a SHORT
        fragment counts minus its share of the lot's opening proceeds (here all 500), and the opening sale is a flow of +500
        on d2: NAV 1 000 on d0–d1, 500 on d2–d4. d2: TWRR (500 + 500 − 1 000) / 1 000 = 0; ROI (500 − 1 000 + 500) / capital
        1 500 (1 000 long + 500 short proceeds) = 0. So ROI 0 every day, TWRR 0 from d1 — a point on d2–d4 where there was
        none. d0 and d1, the long alone, are the presence barrier, unchanged.

        Before MF-E2 (read 20/10/2026), the guard's book had no proceeds on the short (the FifoLot default 0) and no SELL row,
        and asserted no point on d2–d4: [(d0, 0, None), (d1, 0, 0), (d2–d4, None, None)]. Today's builder gives that on this
        book too. The proceeds were added because with 0 the new rule could not be told from ignoring the short.
        """
        days = self._DAYS[:5]

        assert self._history(self._short_book()) == [(days[0], _ZERO, None), *[(day, _ZERO, _ZERO) for day in days[1:]]]

    def _cost_without_rate_book(self) -> dict:
        days = self._DAYS[:5]
        usd = (self._long_lot(2, day=days[2], quantity="5", currency="USD"), self._open_fragment(2, day=days[2], quantity="5"))
        return self._adjusted_book(days, dict.fromkeys(days), days[-1], extra_lots={2: usd})

    def test_guard_a_day_at_cost_with_a_lot_whose_cost_has_no_rate_gets_no_point(self):
        """GUARD: beside the 10 at 1 000 of d0, a USD lot of 5 open from d2 with no USD rate at its opening, no mark on d0–d4,
        at cost until d4. That lot's cost is unknown in EUR: d2–d4 get no point, as today; d0 and d1 are at cost (the
        presence barrier).

        Today (read 17/10/2026): no point at all — no mark. The absence on d2–d4 is today's; the barrier is new.
        """
        days = self._DAYS[:5]

        assert self._history(self._cost_without_rate_book()) == [(days[0], _ZERO, None), (days[1], _ZERO, _ZERO), *[(day, None, None) for day in days[2:]]]

    def _gap_after_the_cut_book(self) -> dict:
        days = self._DAYS[:5]
        prices = {days[0]: None, days[1]: None, days[2]: D("110"), days[3]: None, days[4]: D("110")}
        return self._adjusted_book(days, prices, days[1])

    def test_guard_a_day_after_at_cost_until_without_a_mark_gets_no_point(self):
        """GUARD: the 10 at 1 000 of d0, at cost until d1, 110 on d2 and d4, no mark on d3 — after the cut, a mark without a
        rate. d3 gets no point, as today; d0 and d1 are at cost, d2 and d4 at 110 (ROI 10%, TWRR 10% from d0).

        Today (read 17/10/2026): no point on d0–d1, d3 none either; the 1 000 lands on d2, so ROI 10% on d2 and d4, TWRR
        none on d2 and 0 on d4.
        """
        days = self._DAYS[:5]

        assert self._history(self._gap_after_the_cut_book()) == [(days[0], _ZERO, None), (days[1], _ZERO, _ZERO), (days[2], _TEN, _TEN), (days[3], None, None), (days[4], _TEN, _TEN)]

    # -- V3: a transfer crossing the scope on a day at cost moves its cost ---- #

    def _incoming_edge_leg_book(self) -> dict:
        days, prices = self._unpriced_then_110()
        leg = FifoInputTransaction(id=2, broker_id=1, asset_id=7, date=days[1], type="ADJUSTMENT", quantity=D("5"), cost_basis_override=D("100"), cost_basis_currency="EUR")
        return self._engine_book([self._adjusted_in(1, day=days[0]), leg], days, prices, days[3], boundary_legs={2: BoundaryLeg(2, "IN")})

    def test_v3a_an_incoming_edge_leg_on_a_day_at_cost_brings_in_its_cost(self):
        """V3a: the 10 at 1 000 of d0; on d1 a J-10 edge leg brings 5 in — the ADJUSTMENT-in copy carrying its cost basis, 100
        a unit, named IN in ``boundary_legs``; no mark on d0–d3, 110 on d4–d5, at cost until d3. The leg is an inflow of its
        cost, 500: NAV 1 000 then 1 500 at cost, 1 650 at 110; ROI and TWRR 0 until d3, 10% from d4 — the series goes on.

        Today (read 17/10/2026): no point at all. The leg, on a day without a mark, voids ROI and TWRR from d1; before it no
        day has a mark.
        """
        assert self._history(self._incoming_edge_leg_book()) == self._flat_then_ten_percent()

    def _outgoing_edge_leg_book(self) -> dict:
        days, prices = self._unpriced_then_110()
        leg = FifoInputTransaction(id=2, broker_id=1, asset_id=7, date=days[2], type="ADJUSTMENT", quantity=D("-4"), hands_over_at_own_cost=True)
        return self._engine_book([self._adjusted_in(1, day=days[0]), leg], days, prices, days[3], boundary_legs={2: BoundaryLeg(2, "OUT")})

    def test_v3b_an_outgoing_edge_leg_on_a_day_at_cost_takes_out_the_cost_of_its_pieces(self):
        """V3b: the 10 at 1 000 of d0; on d2 a J-10 edge leg sends 4 out, handing each piece over at its own FIFO cost
        (``hands_over_at_own_cost``; the engine closes 4 of lot 1, named OUT in ``boundary_legs``); no mark on d0–d3, 110 on
        d4–d5, at cost until d3. The leg is an outflow of the cost of its closures, 4 × 100 = 400: NAV 1 000, then 600 at
        cost, 660 at 110; TWRR flat on d2, (600 + 400 − 1 000) / 1 000 = 0; ROI and TWRR 0 until d3, 10% from d4.

        Today (read 17/10/2026): no point at all. The leg, on a day without a mark, voids ROI and TWRR from d2; before it no
        day has a mark.
        """
        assert self._history(self._outgoing_edge_leg_book()) == self._flat_then_ten_percent()

    def _replayed_transfer_book(self, direction: str) -> dict:
        """4 units moved on d2 between broker 1 (the scope) and broker 2, both legs that day, the receiving one with its cost."""
        days, prices = self._unpriced_then_110()
        source, destination = (2, 1) if direction == "arrives" else (1, 2)
        rows = [self._adjusted_in(1, day=days[0])]
        if direction == "arrives":
            rows.append(self._adjusted_in(2, day=days[0], broker_id=2))
        out_leg = _tx(3, tx_type=TransactionType.TRANSFER, tx_date=days[2], quantity=D("-4"), amount=D("0"), broker_id=source)
        in_leg = _tx(4, tx_type=TransactionType.TRANSFER, tx_date=days[2], quantity=D("4"), amount=D("0"), broker_id=destination, cost_basis_override=D("100"), cost_basis_currency="EUR")
        out_leg.related_transaction_id, in_leg.related_transaction_id = in_leg.id, out_leg.id
        return self._engine_book([*rows, out_leg, in_leg], days, prices, days[3])

    @pytest.mark.parametrize("direction", ["arrives", "leaves"])
    def test_v3c_a_replayed_transfer_crossing_the_scope_on_a_day_at_cost_moves_the_cost_of_its_pieces(self, direction):
        """V3c: the 10 at 1 000 of d0 at broker 1 (the scope); on d2 a pair moves 4 units across the scope, its two legs in
        the replay (the engine's TRANSFER_DEPART / ARRIVE and its ``lot:{id}/transfer:{pair}/to:{broker}`` pieces); no mark
        on d0–d3, 110 on d4–d5, at cost until d3. ``arrives``: 4 of a lot of 10 at 1 000 at broker 2 come in, an inflow of
        their cost, 400 (NAV 1 400 at cost, 1 540 at 110). ``leaves``: 4 of the scope's lot go out, an outflow of 400 (NAV 600
        at cost, 660 at 110). Either way ROI and TWRR 0 until d3 (TWRR flat on d2), 10% from d4.

        Today (read 17/10/2026): no point at all, both ways. The crossing event on d2, a day without a mark, voids ROI and
        TWRR from d2; before it no day has a mark.
        """
        assert self._history(self._replayed_transfer_book(direction)) == self._flat_then_ten_percent()

    # -- P4: the rates the days at cost need ---------------------------------- #

    @pytest.mark.parametrize(("cut", "expected"), [("d4", [("CHF", date(2024, 3, 6)), ("GBP", date(2024, 3, 5)), ("USD", date(2024, 3, 4))]), (None, [("GBP", date(2024, 3, 5))])], ids=["days-at-cost", "no-day-at-cost"])
    def test_p4_the_days_at_cost_need_each_long_lots_currency_at_its_opening_date(self, cut, expected):
        """P4: a USD LONG lot opened on d0, a GBP SHORT lot on d1 (sold for 1 000 GBP), a CHF LONG lot on d2, report EUR, no
        transaction. With days
        at cost (``at_cost_until`` d4) each LONG lot's cost is converted at its opening date: (USD, d0) and (CHF, d2) are
        asked. MF-E2: the SHORT lot's opening proceeds are a flow converted at its opening date, and on a day at cost its open
        units count minus their share of them at that same rate (D3), so (GBP, d1) is asked with or without days at cost.
        With no day at cost (None) nothing else is asked.

        Before MF-E2 (read 20/10/2026) the expectations were [(CHF, d2), (USD, d0)] and [] — «never the short's GBP» — and the
        short carried the FifoLot default proceeds, 0. (Before J-33: TypeError on ``at_cost_until``.)
        """
        days = self._DAYS
        resolver = _resolver("EUR")
        lots = {1: self._long_lot(1, day=days[0], currency="USD"), 2: replace(self._long_lot(2, day=days[1], currency="GBP", direction="SHORT"), cumulative_proceeds=D("1000")), 3: self._long_lot(3, day=days[2], currency="CHF")}

        collect_performance_fx_needs(fx_resolver=resolver, analyses=[LotAnalysisType.PERFORMANCE_HISTORY], transactions=[], closures=[], lots_by_id=lots, asset_currency="EUR", at_cost_until=days[4] if cut == "d4" else None)

        assert sorted(resolver._needs) == expected


# --------------------------------------------------------------------------- #
# Small builders
# --------------------------------------------------------------------------- #


def _s29_moved_lot(*, transit: bool = False) -> list[FragmentInterval]:
    """§29 point 2: the fragments of lot 1, opened at broker 1 on 10 Jan 2024 — ``frag-1`` at broker 1 until 20 Jan, then
    ``frag-1b`` at broker 2. With ``transit``, ``frag-1b`` ends on 25 Jan and the units are in transit from broker 2 to
    broker 3 since then (``frag-1c``: IN_TRANSIT, no broker)."""
    fragments = [
        _fragment(1, fragment_id="frag-1", broker_id=1, end_date=date(2024, 1, 20)),
        _fragment(1, fragment_id="frag-1b", broker_id=2, start_date=date(2024, 1, 20), end_date=date(2024, 1, 25) if transit else None),
    ]
    if transit:
        fragments.append(_fragment(1, fragment_id="frag-1c", custody_type="IN_TRANSIT", broker_id=None, start_date=date(2024, 1, 25), source_broker_id=2, destination_broker_id=3))
    return fragments


def _s29_closure_rows(closure: LotClosure, fragments: list[FragmentInterval]) -> list[dict]:
    """§29 point 2: (kind, fragment, broker) of the lot history's rows of ``closure``'s transaction, as
    ``_build_lot_event_rows`` builds them from a replay double — lot 1, opened at broker 1, its ``fragments`` and that one
    closure. Through the builder the service calls, never ``_build_closure_rows``, whose private signature the cure
    extends."""
    lot = _lot(1, opening_broker_id=1)
    result = _engine_result(lots=[lot], fragments=fragments, closures=[closure])
    rows = _svc()._build_lot_event_rows(engine_result=result, selected_ids=[1], fx_resolver=_resolver("EUR"), lots_by_id={1: lot})
    return [{"kind": str(row.kind), "fragment_id": row.fragment_id, "broker_id": row.broker_id} for row in rows if row.transaction_id == closure.transaction_id]


class TestSmallBuilders:
    def test_known_cumulative_proceeds_of_a_short_lot_uses_the_lot_total(self):
        """A short's proceeds arrived at opening, not at each closure."""
        lot = _lot(1, direction="SHORT", cumulative_proceeds=D("1500"), currency="USD")
        value = known_cumulative_proceeds(lot, [], _resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}))
        assert value == D("750.0")

    def test_known_cumulative_proceeds_of_a_short_lot_without_a_rate_are_unknown(self):
        """B3b: no rate at the opening date leaves them unknown, never the native 1500 USD read as euros."""
        lot = _lot(1, direction="SHORT", cumulative_proceeds=D("1500"), currency="USD")
        assert known_cumulative_proceeds(lot, [], _resolver("EUR")) is None

    def test_known_cumulative_proceeds_of_a_long_lot_sums_its_closures(self):
        lot = _lot(1)
        value = known_cumulative_proceeds(lot, [_closure(1, proceeds=D("300")), _closure(1, proceeds=D("200"))], _resolver("EUR"))
        assert value == D("500")

    def test_gantt_ignores_fragments_of_unselected_lots(self):
        segments = _svc()._build_gantt_segments(
            [_fragment(1), _fragment(2, fragment_id="frag-2")],
            [1],
            {1: _lot(1), 2: _lot(2)},
            _resolver("EUR"),
        )
        assert {segment.lot_id for segment in segments} == {1}

    def test_a_gantt_fragment_without_a_rate_at_its_start_has_no_unit_price(self):
        """B3b: a USD lot, 40 of it sold on 1 Feb, a day without a USD rate; it opened on a day with one (0.5).

        Each fragment's unit_price is its price in EUR at the fragment's start: 5 for the original
        fragment; unknown for the 60 left from 1 Feb -- today it carries the native 10 USD as euros.
        """
        segments = _svc()._build_gantt_segments(
            [_fragment(1, end_date=date(2024, 2, 1)), _fragment(1, fragment_id="frag-1b", quantity=D("60"), start_date=date(2024, 2, 1))],
            [1],
            {1: _lot(1, currency="USD", open_quantity=D("60"))},
            _resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}),
        )

        assert {segment.fragment_id: segment.unit_price for segment in segments} == {"frag-1": D("5"), "frag-1b": None}

    def test_closure_rows_ignore_closures_of_unselected_lots(self):
        rows = _svc()._build_closure_rows([_closure(1), _closure(2)], {1}, {1: _lot(1), 2: _lot(2)}, _resolver("EUR"))
        assert {row.lot_id for row in rows} == {1}

    # -- §29 point 2: the broker a closure row names ------------------------- #
    # The rule (developer, 19/10): a closure row names the broker its units leave, the broker of the fragment it closes
    # (LotClosure.fragment_id -> FragmentInterval.broker_id); a fragment without a broker, or one the replay does not
    # hold, keeps the lot's opening broker. The service-level reds and guards: test_financial/test_lots_closure_broker.py.

    def test_s29_p1_a_closure_row_names_the_broker_of_the_fragment_it_closes(self):
        """§29 point 2, P1 — RED until the cure. Lot 1 opened at broker 1 and sits at broker 2 from 20 Jan (``frag-1b``). A
        SELL of 40 on 1 Feb closes ``frag-1b``: its row names broker 2, the broker the units leave.

        Today: broker 1, the lot's opening broker (``_build_closure_rows`` writes ``lot.opening_broker_id``).
        """
        rows = _s29_closure_rows(_closure(1, fragment_id="frag-1b"), _s29_moved_lot())

        assert rows == [{"kind": "SELL", "fragment_id": "frag-1b", "broker_id": 2}]

    def test_s29_p2_guard_a_closure_of_the_opening_fragment_names_the_opening_broker(self):
        """§29 point 2, P2 — GUARD (green today and after). The same lot; a SELL of 40 on 15 Jan closes ``frag-1``, at
        broker 1: its row names broker 1 — the broker of the fragment it closes, not broker 2, where the lot sits
        afterwards."""
        rows = _s29_closure_rows(_closure(1, close_date=date(2024, 1, 15), fragment_id="frag-1"), _s29_moved_lot())

        assert rows == [{"kind": "SELL", "fragment_id": "frag-1", "broker_id": 1}]

    @pytest.mark.parametrize("transit", [False, True], ids=["fragment-not-in-the-replay", "fragment-in-transit"])
    def test_s29_p3_guard_a_closure_without_a_broker_to_read_keeps_the_opening_broker(self, transit):
        """§29 point 2, P3 — GUARD (green today and after): the cure's fallback. A SELL of 40 on 1 Feb closes ``frag-1c``,
        which is either not in the replay (lot 1's fragments are ``frag-1`` at broker 1 and ``frag-1b`` at broker 2) or the
        lot in transit from broker 2 to broker 3 since 25 Jan, a fragment without a broker (the engine closes no transit
        fragment: this is the safety net). Its row keeps the lot's opening broker, 1 — not 2, the last broker the lot was
        held at and the transit's source, nor 3, its destination."""
        rows = _s29_closure_rows(_closure(1, fragment_id="frag-1c"), _s29_moved_lot(transit=transit))

        assert rows == [{"kind": "SELL", "fragment_id": "frag-1c", "broker_id": 1}]

    def test_income_events_skip_a_transaction_with_no_asset(self):
        """A broker-level dividend not attributed to an asset cannot be allocated to a lot."""
        events = build_income_economic_events(
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
        events = build_cost_economic_events(
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
        rows = build_engine_transactions(
            [_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("10"), amount=D("-100"), currency="USD")],
            _resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}),
            "EUR",
            "EUR",
        )
        assert rows[0].target_amount is None

    def test_engine_transactions_convert_a_trade_controvalue(self):
        """The sign of the controvalue is preserved: a BUY stays negative."""
        rows = build_engine_transactions(
            [_tx(1, amount=D("-1000"), currency="USD")],
            _resolver("EUR", {("USD", date(2024, 1, 10)): D("0.5")}),
            "EUR",
            "EUR",
        )
        assert rows[0].target_amount == D("-500.0")

    def test_opening_reference_price_returns_nothing_when_no_quote_exists(self):
        """The lot knows its reference price but the asset's price series is empty."""
        lot = _lot(1, reference_unit_price=D("9"), reference_price_source="fallback")
        price, currency, reference_date, source = opening_reference_price(lot, AssetPriceSeries([]))
        assert (price, currency, reference_date, source) == (None, None, lot.opening_date, "fallback")

    def test_opening_reference_price_uses_the_resolved_quote_currency(self):
        """A USD close of 8 Jan carried onto the lot's opening, 10 Jan: the reference is in USD, dated 10 Jan.

        CP-7b (P21, every amount at the rate of its day): the reference is dated its opening day, so it converts at that
        day's rate. Before CP-7b it was dated the close's own day, 8 Jan.
        """
        lot = _lot(1, reference_unit_price=D("9"))
        series = _series(_quote(date(2024, 1, 8), D("9"), "USD"))
        price, currency, reference_date, _source = opening_reference_price(lot, series)
        assert (price, currency, reference_date) == (D("9"), "USD", date(2024, 1, 10))

    def test_opening_reference_price_scales_the_buy_price_by_the_quote_base(self):
        """A bond quoted per 100 units: the entry price must land on the same axis."""
        price, _currency, _resolved, source = opening_reference_price(_lot(1, opening_unit_price=D("0.98")), AssetPriceSeries([]), 100)
        assert (price, source) == (D("98.00"), "exact")

    def test_price_history_skips_days_with_no_estimated_price(self):
        points = build_price_history(
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
        assert lot_history_end_date(_lot(1, open_quantity=D("0")), [], date(2024, 6, 1)) == date(2024, 1, 10)

    def test_a_closed_lot_ends_on_its_last_closure(self):
        end = lot_history_end_date(_lot(1, open_quantity=D("0")), [_closure(1, close_date=date(2024, 2, 5))], date(2024, 6, 1))
        assert end == date(2024, 2, 5)

    def test_an_open_lot_runs_to_the_end_of_the_window(self):
        assert lot_history_end_date(_lot(1), [], date(2024, 6, 1)) == date(2024, 6, 1)

    def test_extend_closed_runs_a_closed_lot_to_the_end_of_the_window(self):
        end = lot_history_end_date(_lot(1, open_quantity=D("0")), [_closure(1)], date(2024, 6, 1), extend_closed=True)
        assert end == date(2024, 6, 1)


class TestWacHistoryBuilders:
    """Broker and cumulative WAC histories: one series per line, nothing for a broker without one."""

    def test_a_broker_in_scope_without_a_line_is_skipped(self):
        """Broker 2 is in the analysis scope but never traded this asset: it has no line, so no series at all."""
        lines = {1: _line(1, _acquired(date(2024, 1, 10), "10", "50"))}

        points = build_broker_wac_history([1, 2], lines, _days(date(2024, 1, 10), 2))

        assert points == [
            BrokerWACHistoryPoint(date=date(2024, 1, 10), broker_id=1, wac=D("5"), pool_qty=D("10")),
            BrokerWACHistoryPoint(date=date(2024, 1, 11), broker_id=1, wac=D("5"), pool_qty=D("10")),
        ]

    def test_each_broker_gets_its_own_line_in_scope_order(self):
        """Broker 2 listed first, its line starting a day later; the all-brokers line is not a broker's."""
        lines = {
            1: _line(1, _acquired(date(2024, 1, 10), "10", "50")),
            2: _line(2, _acquired(date(2024, 1, 11), "5", "100")),
            ALL_BROKERS: _line(ALL_BROKERS, _acquired(date(2024, 1, 10), "10", "50"), _acquired(date(2024, 1, 11), "5", "100")),
        }

        points = build_broker_wac_history([2, 1], lines, _days(date(2024, 1, 10), 2))

        assert [(point.broker_id, point.date, point.wac, point.pool_qty) for point in points] == [
            (2, date(2024, 1, 11), D("20"), D("5")),
            (1, date(2024, 1, 10), D("5"), D("10")),
            (1, date(2024, 1, 11), D("5"), D("10")),
        ]

    def test_the_cumulative_history_is_the_all_brokers_line(self):
        """10 for 50 at one broker, 5 for 100 at another: together 15 for 150, 10 per unit."""
        lines = {
            1: _line(1, _acquired(date(2024, 1, 10), "10", "50")),
            2: _line(2, _acquired(date(2024, 1, 11), "5", "100")),
            ALL_BROKERS: _line(ALL_BROKERS, _acquired(date(2024, 1, 10), "10", "50"), _acquired(date(2024, 1, 11), "5", "100")),
        }

        points = build_cumulative_wac_history(lines, _days(date(2024, 1, 10), 2))

        assert points == [
            CumulativeWACHistoryPoint(date=date(2024, 1, 10), wac=D("5"), pool_qty=D("10")),
            CumulativeWACHistoryPoint(date=date(2024, 1, 11), wac=D("10"), pool_qty=D("15")),
        ]

    def test_an_asset_without_an_all_brokers_line_has_no_cumulative_history(self):
        assert build_cumulative_wac_history({}, _days(date(2024, 1, 10), 2)) == []
        assert build_cumulative_wac_history({1: _line(1, _acquired(date(2024, 1, 10), "10", "50"))}, _days(date(2024, 1, 10), 2)) == []


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
    """``load`` is the resolver's only async step; ``unit_rate_steps`` is stubbed where ``conversions`` reads it (and
    ``convert_bulk``, which ``load`` no longer asks, refuses the call), so no session.

    Today both cases fail the same way: ``load`` asks ``convert_bulk`` — refused, «FxRateResolver.load asked convert_bulk: it
    must read unit_rate_steps» — and ``unit_rate_steps`` is never called.
    """

    @pytest.mark.asyncio
    async def test_a_day_with_no_published_rate_is_left_unresolved(self, monkeypatch):
        """The reader has no step for that pair: the amount stays unknown, not zero — and the reader was asked for exactly the
        pair and the day."""
        calls = _stub_unit_rate_steps(monkeypatch, default=None)
        resolver = FxRateResolver("EUR")
        resolver.need("USD", date(2024, 1, 10))
        await resolver.load(None)
        assert [{pair: _covered_days(windows) for pair, windows in call.items()} for call in calls] == [{("USD", "EUR"): {date(2024, 1, 10)}}]
        assert resolver.convert(D("100"), "USD", date(2024, 1, 10)) is None

    @pytest.mark.asyncio
    async def test_a_resolved_rate_is_stored_and_reused(self, monkeypatch):
        calls = _stub_unit_rate_steps(monkeypatch, {"USD": D("0.9")})
        resolver = FxRateResolver("EUR")
        resolver.need("USD", date(2024, 1, 10))
        await resolver.load(None)
        await resolver.load(None)  # nothing pending the second time
        assert (resolver.convert(D("100"), "USD", date(2024, 1, 10)), len(calls)) == (D("90.0"), 1)
        assert {pair: _covered_days(windows) for pair, windows in calls[0].items()} == {("USD", "EUR"): {date(2024, 1, 10)}}

    @pytest.mark.asyncio
    async def test_an_invalid_code_raises_at_load(self, monkeypatch):
        """GUARD (green today and after): a code pycountry rejects raises a ``ValueError`` at ``load`` — each pending currency is
        validated through ``Currency(code=…, amount=1)`` — whatever the reader would have said."""
        _stub_unit_rate_steps(monkeypatch)
        resolver = FxRateResolver("EUR")
        resolver.need("Z1", date(2024, 1, 10))
        with pytest.raises(ValueError):
            await resolver.load(None)


class TestFxRateResolverNeedDays:
    """L1b: ``need_days(currency, first, last)`` asks every day of a window; ``load`` hands the reader the pending windows of each
    pending currency, once per load. The reader is stubbed (a flat rate per currency): the cases read what ``load`` handed it
    by the days its windows cover — however the cure splits or joins them — and what ``convert`` then answers.

    Today: ``FxRateResolver`` has no ``need_days`` — «FxRateResolver has no need_days».
    """

    _FIRST, _LAST = date(2024, 1, 10), date(2024, 1, 20)

    @pytest.mark.asyncio
    async def test_a_window_answers_on_each_of_its_days_and_not_around_it(self, monkeypatch):
        """Two windows (one a single day) and a single-day ``need``: one reader call with one entry per currency, its windows
        covering exactly the days asked; ``convert`` answers on each of them with the reader's rate and on the day before and
        the day after a window with nothing."""
        resolver = FxRateResolver("EUR")
        need_days = _need_days(resolver)
        calls = _stub_unit_rate_steps(monkeypatch, {"USD": D("1.25"), "GBP": D("0.5"), "JPY": D("0.01")})
        need_days("USD", self._FIRST, self._LAST)
        need_days("GBP", self._FIRST, self._FIRST)
        resolver.need("JPY", date(2024, 2, 1))
        await resolver.load(None)

        assert len(calls) == 1, f"one load, one unit_rate_steps call; got {len(calls)}"
        assert set(calls[0]) == {("USD", "EUR"), ("GBP", "EUR"), ("JPY", "EUR")}, f"one entry per pending currency: {sorted(calls[0])}"
        assert _covered_days(calls[0][("USD", "EUR")]) == set(_days(self._FIRST, 11))
        assert _covered_days(calls[0][("GBP", "EUR")]) == {self._FIRST}
        assert _covered_days(calls[0][("JPY", "EUR")]) == {date(2024, 2, 1)}
        around = _days(self._FIRST - timedelta(days=1), 13)
        assert {day: resolver.convert(D("100"), "USD", day) for day in around} == {around[0]: None, **{day: D("125.00") for day in around[1:-1]}, around[-1]: None}
        assert [resolver.convert(D("100"), "GBP", day) for day in (self._FIRST - timedelta(days=1), self._FIRST, self._FIRST + timedelta(days=1))] == [None, D("50.0"), None]
        assert [resolver.convert(D("100"), "JPY", date(2024, 2, offset)) for offset in (1, 2)] == [D("1.00"), None]

    @pytest.mark.asyncio
    async def test_a_window_that_asks_nothing(self, monkeypatch):
        """A window that ends before it starts, a missing or blank code and the target's own code ask nothing: ``load`` does not
        call the reader, and the days of the reversed window stay unresolved (the target and the blanks convert as themselves)."""
        resolver = FxRateResolver("EUR")
        need_days = _need_days(resolver)
        calls = _stub_unit_rate_steps(monkeypatch)
        need_days("USD", self._LAST, self._FIRST)
        for currency in (None, "", "EUR"):
            need_days(currency, self._FIRST, self._LAST)
        await resolver.load(None)

        assert calls == [], f"nothing was asked, yet the reader was called with {calls}"
        assert resolver.convert(D("100"), "USD", date(2024, 1, 15)) is None
        assert [resolver.convert(D("100"), currency, date(2024, 1, 15)) for currency in ("EUR", None, "")] == [D("100")] * 3

    @pytest.mark.asyncio
    async def test_a_need_inside_a_loaded_window_is_already_answered(self, monkeypatch):
        """A ``need`` on a day a loaded window covers is not pending: the second ``load``, with nothing new, does not call the
        reader again, and the day answers."""
        resolver = FxRateResolver("EUR")
        need_days = _need_days(resolver)
        calls = _stub_unit_rate_steps(monkeypatch, {"USD": D("1.25")})
        need_days("USD", self._FIRST, self._LAST)
        await resolver.load(None)
        resolver.need("USD", date(2024, 1, 15))
        await resolver.load(None)

        assert len(calls) == 1, f"the reader was called {len(calls)} times, the second for a day the first window covers"
        assert resolver.convert(D("100"), "USD", date(2024, 1, 15)) == D("125.00")

    @pytest.mark.asyncio
    async def test_several_loads_accumulate(self, monkeypatch):
        """A second ``load`` hands the reader only what became pending — a new currency's window and a single day of the first
        currency outside its window — and the first load's days still answer beside the second's."""
        resolver = FxRateResolver("EUR")
        need_days = _need_days(resolver)
        calls = _stub_unit_rate_steps(monkeypatch, {"USD": D("1.25"), "GBP": D("0.5")})
        need_days("USD", self._FIRST, self._LAST)
        await resolver.load(None)
        need_days("GBP", self._FIRST, self._FIRST + timedelta(days=2))
        resolver.need("USD", date(2024, 2, 1))
        await resolver.load(None)

        assert len(calls) == 2, f"two loads, two reader calls; got {len(calls)}"
        assert {pair: _covered_days(windows) for pair, windows in calls[1].items()} == {("GBP", "EUR"): set(_days(self._FIRST, 3)), ("USD", "EUR"): {date(2024, 2, 1)}}
        assert [resolver.convert(D("100"), "USD", day) for day in (self._FIRST, self._LAST, date(2024, 2, 1), date(2024, 1, 25))] == [D("125.00"), D("125.00"), D("125.00"), None]
        assert [resolver.convert(D("100"), "GBP", day) for day in (self._FIRST, self._FIRST + timedelta(days=2), self._FIRST + timedelta(days=3))] == [D("50.0"), D("50.0"), None]

    @pytest.mark.asyncio
    async def test_a_code_is_read_normalised_and_the_target_by_another_spelling_is_the_target(self, monkeypatch):
        """'usd' and 'huf' read the USD and HUF rates (the reader is asked for ("USD", "EUR") and ("HUF", "EUR"), upper case);
        'eur' normalises to the target 'EUR': no entry for it (``unit_rate_steps`` refuses a pair of one currency) and it
        converts at exactly Decimal('1'), as ``convert_bulk``'s identity did. Each answer is read under the code as asked."""
        resolver = FxRateResolver("EUR")
        need_days = _need_days(resolver)
        calls = _stub_unit_rate_steps(monkeypatch, {"USD": D("1.25"), "HUF": D("0.0025")})
        day = date(2024, 1, 10)
        resolver.need("usd", day)
        resolver.need("eur", day)
        need_days("huf", day, day + timedelta(days=2))
        await resolver.load(None)

        assert [set(call) for call in calls] == [{("USD", "EUR"), ("HUF", "EUR")}], f"the reader was asked for {[sorted(call) for call in calls]}"
        assert resolver.convert(D("100"), "usd", day) == D("125.00")
        assert resolver.convert(D("100"), "huf", day + timedelta(days=1)) == D("0.2500")
        identity = resolver.convert(D("5"), "eur", day)
        assert identity is not None and identity.as_tuple() == D("5").as_tuple(), f"'eur' converts at exactly 1, not {identity!r}"


class TestParseTransferPairId:
    def test_rejects_a_fragment_id_that_is_not_a_transfer_leg(self):
        """Guards the split/transfer bookkeeping against being fed an ordinary fragment."""
        with pytest.raises(ValueError, match="does not contain transfer pair marker"):
            _parse_transfer_pair_id("lot:1/frag:0")

    def test_extracts_the_pair_id_from_a_transfer_fragment(self):
        assert _parse_transfer_pair_id("lot:1/transfer:42/leg:in") == 42


# =========================================================================== #
# CP-16 — decision 47 and J-9 in the lots builders
# =========================================================================== #
#
# Workstream J «Numeri e analisi», release 1.3. N78-1 (the developer's decision, 21/10/2026) replaced decision 47's
# reading: a negative ADJUSTMENT read from the database has no value, whatever cost_basis_override it stores — its
# units leave at 0, the lots performance history sees no flow and asks no rate for it (before N78-1 the stored value
# left as an external flow, the mirror of an ADJUSTMENT-in with a cost). J-9: a lot opened by an ADJUSTMENT-in priced by its override is in
# cost_basis_currency, so every builder that converts that lot — the summary, the lot history's opening row and the
# FX needs of that history — converts from that currency, not from the row's (usually None, which the FX resolver
# reads as already in the report currency). The engine side is pinned in
# test_financial/test_fifo_adjustment_out_with_cost.py, the end-to-end example in
# test_financial/test_adjustment_out_with_cost_numbers.py.
#
# Unlike the doubles above, these tests take their lots, fragments, closures and events from the real engine
# (run_fifo_lot_engine, pure as well): what changed is precisely what the engine hands to the builders, so a
# hand-built double would restate the expected engine output instead of testing it.
# Each docstring keeps the values its test read before CP-16; GUARD marks a test whose values CP-16 left as they were.


def _engine_run(*transactions: Transaction, shorting: bool = False) -> FifoEngineResult:
    """The engine as the service runs it on these in-memory rows: report currency EUR, broker 1 without shorting unless asked."""
    return run_fifo_lot_engine(list(transactions), {1: shorting}, target_currency="EUR")


class TestAdjustmentOutStoringAValuePerformanceHistory:
    """N78-1 in ``build_performance_history`` (lots/histories.py): an ADJUSTMENT-out has no value.

    Decision 47's example: 10 bought at 20 EUR on 1 Oct 2018, 4 taken out on 3 Oct by an ADJUSTMENT −4 — an in-memory
    database row, not a J-10 scope-boundary reading — storing 20 EUR a unit; X at 20, 20, 25, 25, 30 from 1 to 5 Oct.
    The stored value is ignored: the 4 units leave without a flow, as a row without a value. Before N78-1 (CP-16) the
    exit was the mirror of an ADJUSTMENT-in with a cost, a flow of +4 × 20 = +80 on 3 Oct; before CP-16 there was no
    flow either.

    No day is valued at cost here (``at_cost_until=None``): the rules of a day with a mark, or without one outside the days at cost; the days at cost are ``TestPerformanceHistoryAtCost``.
    """

    _DAYS = _days(date(2018, 10, 1), 5)
    _PRICES = dict(zip(_days(date(2018, 10, 1), 5), (D("20"), D("20"), D("25"), D("25"), D("30")), strict=True))

    def _history(self) -> list:
        buy = _tx(1, tx_date=date(2018, 10, 1), quantity=D("10"), amount=D("-200"), currency="EUR")
        handover = _tx(
            2,
            tx_type=TransactionType.ADJUSTMENT,
            tx_date=date(2018, 10, 3),
            quantity=D("-4"),
            amount=D("0"),
            currency=None,
            cost_basis_override=D("20"),
            cost_basis_currency="EUR",
        )
        result = _engine_run(buy, handover)
        context = PerformanceSourceContext(
            transactions=[buy, handover],
            engine_result=result,
            lots_by_id={lot.lot_id: lot for lot in result.lots},
            fragments_by_lot=group_fragments(result.fragment_intervals),
            closures_by_lot=group_closures(result.closures),
            tx_by_id={buy.id: buy, handover.id: handover},
        )
        return build_performance_history(
            scope_broker_ids=[1],
            history_dates=self._DAYS,
            market_prices=self._PRICES,
            asset_currency="EUR",
            fx_resolver=_resolver("EUR"),
            context=context,
            quote_base_quantity=1,
            at_cost_until=None,
        )

    def test_the_exit_is_no_external_flow_whatever_it_stores(self, monkeypatch):
        """The flows the series is computed from, net by date: −200 (the BUY) on 1 Oct, and nothing on 3 Oct.

        Read where build_performance_history hands them on — calculate_simple_roi_series, as histories imports it — and
        netted by date, so a flow counted from the row or from its closure shows. Before N78-1 (CP-16): also +80 on 3 Oct.
        """
        received: list[list] = []
        original = histories_module.calculate_simple_roi_series

        def spy(nav_snapshots, cash_flows):
            received.append(list(cash_flows))
            return original(nav_snapshots, cash_flows)

        monkeypatch.setattr(histories_module, "calculate_simple_roi_series", spy)

        self._history()

        assert len(received) == 1, "precondition: the series is computed once, the BUY being a flow"
        net_by_date: dict[date, Decimal] = {}
        for flow in received[0]:
            net_by_date[flow.date] = net_by_date.get(flow.date, D("0")) + flow.amount
        assert net_by_date == {date(2018, 10, 1): D("-200")}, f"N78-1: an ADJUSTMENT-out is no flow, whatever it stores; flows by date: {net_by_date}"

    def test_roi_and_twrr_read_the_exit_as_units_gone_without_a_flow(self):
        """The visible effect, from returns.py's definitions, on NAVs of 200, 200, 150 (6 × 25), 150 and 180 (6 × 30).

        ROI = (NAV − invested) / invested with invested = −Σ flows = 200 every day → 0, 0, −0.25, −0.25, −0.1. TWRR
        compounds (NAV + the day's flow − previous NAV) / previous NAV: 3 Oct 150 / 200 − 1 = −0.25, 5 Oct 180 / 150 − 1 =
        0.2, so 0.75 × 1.2 − 1 = −0.1. No TWRR on the first day.
        Before N78-1 (CP-16, the +80 flow): ROI 0.25, 0.25, 0.5 and TWRR 0.15, 0.15, 0.38 from 3 Oct.
        """
        points = self._history()

        assert [(point.date, point.roi, point.twrr) for point in points] == [
            (date(2018, 10, 1), D("0"), None),
            (date(2018, 10, 2), D("0"), D("0")),
            (date(2018, 10, 3), D("-0.25"), D("-0.25")),
            (date(2018, 10, 4), D("-0.25"), D("-0.25")),
            (date(2018, 10, 5), D("-0.1"), D("-0.1")),
        ]


class TestAdjustmentOutPerformanceFxNeeds:
    """N78-1: an ADJUSTMENT-out is no flow, so ``collect_performance_fx_needs`` asks no rate for it, whatever it stores."""

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
        collect_performance_fx_needs(**kwargs)

    def test_an_adjustment_out_storing_a_value_needs_no_rate(self):
        """An ADJUSTMENT −4 (an in-memory database row) storing 18 USD a unit, report EUR: nothing leaves, nothing is
        converted, no rate is asked. Before N78-1 (CP-16) ("USD", the row's date) was asked for the 72 USD it handed over.
        """
        resolver = _resolver("EUR")
        exit_row = _tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("-4"), amount=D("0"), currency=None, cost_basis_override=D("18"), cost_basis_currency="USD")

        self._call(resolver, transactions=[exit_row])

        assert resolver._needs == []

    def test_a_handover_without_a_cost_needs_nothing(self):
        """GUARD: an ADJUSTMENT −4 without an override moves no money, so no rate is asked — not even for an asset quoted in USD."""
        resolver = _resolver("EUR")

        self._call(resolver, asset_currency="USD", transactions=[_tx(1, tx_type=TransactionType.ADJUSTMENT, quantity=D("-4"), amount=D("0"), currency=None)])

        assert resolver._needs == []


class TestPricedAdjustmentInLotCurrency:
    """J-9 in the lots builders: the lot opened by an ADJUSTMENT +5 at 90 USD a unit, row currency None, report EUR.

    The engine gives that lot the currency its price is in, USD (J-9), and each builder that converts the lot reads it:
    with USD→EUR at 0.9 on the opening day, a cost of 5 × 90 = 450 USD is 405 EUR and a unit price of 90 USD is 81 EUR.
    Before CP-16 the lot was in None, which the FX resolver reads as already EUR: 450 and 90, a USD price shown as euros.
    """

    _OPENED = date(2024, 1, 10)

    def _priced_adjustment_in(self) -> Transaction:
        return _tx(
            1,
            tx_type=TransactionType.ADJUSTMENT,
            tx_date=self._OPENED,
            quantity=D("5"),
            amount=D("0"),
            currency=None,
            cost_basis_override=D("90"),
            cost_basis_currency="USD",
        )

    def _usd_at_090(self) -> FxRateResolver:
        return _resolver("EUR", {("USD", self._OPENED): D("0.9")})

    def _opening_rows(self, opening: Transaction) -> list[tuple[LotTimelineEventKind, Decimal | None]]:
        """(kind, unit price) of the lot history's opening row of ``opening``'s lot."""
        result = _engine_run(opening)
        rows = _svc()._build_lot_event_rows(
            engine_result=result,
            selected_ids=[opening.id],
            fx_resolver=self._usd_at_090(),
            lots_by_id={lot.lot_id: lot for lot in result.lots},
        )
        opening_kinds = (LotTimelineEventKind.BUY, LotTimelineEventKind.ADJUSTMENT_IN)
        return [(row.kind, row.unit_price) for row in rows if row.transaction_id == opening.id and row.kind in opening_kinds]

    def test_the_summary_converts_the_lots_cost_from_the_currency_it_is_in(self):
        """The lot summary (``_build_lot_summaries``): currency USD, original cost 405 EUR, opening unit price 81 EUR.

        Before CP-16: currency None, original cost 450, opening unit price 90 — the USD amounts read as euros.
        """
        result = _engine_run(self._priced_adjustment_in())

        rows = _svc()._build_lot_summaries(
            engine_result=result,
            lots_by_id={lot.lot_id: lot for lot in result.lots},
            selected_ids=[1],
            fx_resolver=self._usd_at_090(),
            market_prices={},
            price_series=AssetPriceSeries([]),
            closures_by_lot={},
            income_by_lot={},
            fees_by_lot={},
            taxes_by_lot={},
            estimated_mode=False,
            quote_base_quantity=1,
            analysis_end=date(2024, 3, 1),
        )
        row = next(row for row in rows if row.lot_id == 1)
        observed = {"currency": row.currency, "original_cost": row.original_cost, "opening_unit_price": row.opening_unit_price}

        assert observed == {"currency": "USD", "original_cost": D("405"), "opening_unit_price": D("81")}

    def test_the_opening_row_of_the_lot_history_converts_its_price_from_the_lots_currency(self):
        """The lot history's ADJUSTMENT_IN row (``_build_opening_and_split_rows``): unit price 90 USD × 0.9 = 81 EUR.

        An opening row converts its price from the lot's currency — the cost basis's for a priced ADJUSTMENT, the BUY's
        own for a BUY. Before CP-16 it converted with the row's currency (``tx.currency``, None): 90, a USD price shown
        as euros — the J-9 defect again, in the history.
        """
        assert self._opening_rows(self._priced_adjustment_in()) == [(LotTimelineEventKind.ADJUSTMENT_IN, D("81"))]

    def test_a_buys_opening_row_still_converts_from_its_own_currency(self):
        """GUARD: 10 bought at 20 USD — a BUY's lot is in the BUY's currency, so its row reads 20 × 0.9 = 18 EUR, as before CP-16."""
        buy = _tx(1, tx_date=self._OPENED, quantity=D("10"), amount=D("-200"), currency="USD")

        assert self._opening_rows(buy) == [(LotTimelineEventKind.BUY, D("18"))]

    def test_the_event_history_needs_the_lots_currency_on_its_opening_date(self):
        """``collect_fx_needs`` for EVENT_HISTORY alone, the lot selected: ("USD", the opening date), the rate its opening row needs.

        Before CP-16 the history registered only each event's row currency — None for this ADJUSTMENT — so nothing was asked.
        """
        adjustment = self._priced_adjustment_in()
        result = _engine_run(adjustment)
        resolver = _resolver("EUR")

        collect_fx_needs(
            fx_resolver=resolver,
            analyses=[LotAnalysisType.EVENT_HISTORY],
            lots_by_id={lot.lot_id: lot for lot in result.lots},
            selected_ids=[1],
            transactions=[adjustment],
            price_series=AssetPriceSeries([]),
            prices=[],
            fragments=result.fragment_intervals,
            events=result.classified_events,
            closures=result.closures,
            split_ratios_by_tx_id={},
            actual_to=date(2024, 3, 1),
            computed_from=self._OPENED,
            asset_currency="EUR",
        )

        assert resolver._needs == [("USD", self._OPENED)]


# =========================================================================== #
# CP-7a — developer's decision 26 (D-J1, option B): each leg of a closure at its own date
# =========================================================================== #
#
# Workstream J «Numeri e analisi», release 1.3. A FIFO lot's legs convert to the report currency each in its own currency
# at its own date: the cost in the lot's currency at the lot's opening date (the purchase rate), the proceeds in the
# closing transaction's currency (LotClosure.close_currency) at the close date (the sale rate). One conversion point,
# lots/conversions.py convert_closure; need_closure_rates asks for both rates. So a fully closed lot keeps no market P&L,
# its realized P&L is the Dashboard's, and a lot sold in another currency than it was bought in gets its proceeds in the
# right one. Before CP-7a every reader converted every figure in the lot's currency at the close date — the cost
# included — and the engine subtracted a sale's USD from a lot's EUR.
#
# The D-J1 example, R1: 1 unit bought at 100 USD on 2 Jan 2025 (USD→EUR 1.00), sold at 110 USD on 2 Jun 2025 (0.90).
# Proceeds 110 × 0.90 = 99 EUR, cost 100 × 1.00 = 100 EUR: realized −1 and, the lot being closed, market 0 — where the
# native gain of 10 USD at the sale's rate read +9 of realized P&L and −10 of market P&L.
#
# R10, in the same lot: a short lot's P&L — its total value — is its opening proceeds (at the opening rate) less the cost
# of every buy-back to date (ConvertedClosure.cost, in the BUY's currency at its date) less its open value. Before it a
# buy-back paid money out and nothing subtracted it.
#
# As in the CP-16 section, lots and closures come from the real engine (broker 1 allowing shorting, which only the short
# books use): what changed is what the engine hands over (close_currency; no native realized P&L across two currencies)
# and how the builders convert it. The two new names are read through the module while a test runs
# (conversions_module.convert_closure, conversions_module.need_closure_rates), never imported at module level: before
# CP-7a only the tests that call them fail, on the missing attribute, and the rest of the file still collects. Every
# other test here fails before CP-7a on its values. Each docstring says what its test read before CP-7a; GUARD marks a
# value CP-7a leaves as it was.

_JAN_2 = date(2025, 1, 2)  # every book opens on 2 Jan 2025...
_JUN_2 = date(2025, 6, 2)  # ...and closes, wholly or in part, on 2 Jun 2025
_SEP_1 = date(2025, 9, 1)  # the reading day of the summaries
_USD_1_THEN_090 = {("USD", _JAN_2): D("1.00"), ("USD", _JUN_2): D("0.90")}  # the D-J1 example's rates (R1, R2)
_USD_110_THEN_090 = {("USD", _JAN_2): D("1.10"), ("USD", _JUN_2): D("0.90")}  # the USD short's
_USD_090_ON_JUN_2 = {("USD", _JUN_2): D("0.90")}  # R3's: its lot is in EUR
_CONVERTED_FIGURES = ("open_unit_price", "close_unit_price", "proceeds", "cost", "realized_pnl")


def _cp7a_run(rows: list[Transaction]) -> FifoEngineResult:
    """The engine on a CP-7a book: report currency EUR, broker 1 allowing shorting (only the short books sell what they do not hold)."""
    return _engine_run(*rows, shorting=True)


def _bought_on_jan_2(quantity: str, unit_price: str, currency: str) -> Transaction:
    """Transaction 1: ``quantity`` bought at ``unit_price`` on 2 Jan."""
    return _tx(1, tx_date=_JAN_2, quantity=D(quantity), amount=-D(quantity) * D(unit_price), currency=currency)


def _sold_on_jun_2(quantity: str, unit_price: str, currency: str) -> Transaction:
    """Transaction 2: ``quantity`` sold at ``unit_price`` on 2 Jun."""
    return _tx(2, tx_type=TransactionType.SELL, tx_date=_JUN_2, quantity=-D(quantity), amount=D(quantity) * D(unit_price), currency=currency)


def _shorted_on_jan_2(quantity: str, unit_price: str, currency: str) -> Transaction:
    """Transaction 1: ``quantity`` sold short at ``unit_price`` on 2 Jan."""
    return _tx(1, tx_type=TransactionType.SELL, tx_date=_JAN_2, quantity=-D(quantity), amount=D(quantity) * D(unit_price), currency=currency)


def _bought_back_on_jun_2(quantity: str, unit_price: str, currency: str) -> Transaction:
    """Transaction 2: ``quantity`` bought back at ``unit_price`` on 2 Jun."""
    return _tx(2, tx_date=_JUN_2, quantity=D(quantity), amount=-D(quantity) * D(unit_price), currency=currency)


def _r1() -> list[Transaction]:
    """R1, the D-J1 example: 1 bought at 100 USD, sold at 110 USD."""
    return [_bought_on_jan_2("1", "100", "USD"), _sold_on_jun_2("1", "110", "USD")]


def _r2() -> list[Transaction]:
    """R2: 10 bought at 100 USD, 4 of them sold at 110 USD."""
    return [_bought_on_jan_2("10", "100", "USD"), _sold_on_jun_2("4", "110", "USD")]


def _r3() -> list[Transaction]:
    """R3: 1 bought at 100 EUR, sold at 110 USD — in another currency than it was bought in; the engine never asks which a broker trades in."""
    return [_bought_on_jan_2("1", "100", "EUR"), _sold_on_jun_2("1", "110", "USD")]


def _usd_short() -> list[Transaction]:
    """A short in USD: 1 sold at 50 USD (USD→EUR 1.10 on 2 Jan), bought back at 40 USD (0.90 on 2 Jun)."""
    return [_shorted_on_jan_2("1", "50", "USD"), _bought_back_on_jun_2("1", "40", "USD")]


def _short_half_bought_back() -> list[Transaction]:
    """R10: 10 sold short at 100 EUR, 5 of them bought back at 90 EUR."""
    return [_shorted_on_jan_2("10", "100", "EUR"), _bought_back_on_jun_2("5", "90", "EUR")]


def _short_bought_back_whole() -> list[Transaction]:
    """R10: the same short bought back whole, 10 at 90 EUR."""
    return [_shorted_on_jan_2("10", "100", "EUR"), _bought_back_on_jun_2("10", "90", "EUR")]


def _gbp_lot_sold_in_usd() -> list[Transaction]:
    """1 bought at 100 GBP, sold at 110 USD: each leg needs a rate of its own."""
    return [_bought_on_jan_2("1", "100", "GBP"), _sold_on_jun_2("1", "110", "USD")]


def _gbp_lot_handed_over_at_a_usd_cost() -> list[Transaction]:
    """10 bought at 20 GBP; on 2 Jun an ADJUSTMENT −4 storing 18 USD a unit (decision 47 before N78-1; ignored since), its own currency None."""
    handover = _tx(2, tx_type=TransactionType.ADJUSTMENT, tx_date=_JUN_2, quantity=D("-4"), amount=D("0"), currency=None, cost_basis_override=D("18"), cost_basis_currency="USD")
    return [_bought_on_jan_2("10", "20", "GBP"), handover]


def _lot_1_and_the_closure_of_transaction_2(result: FifoEngineResult) -> tuple[FifoLot, LotClosure]:
    """Lot 1 — every book opens one — and the closure transaction 2 made of it, both found by their ids."""
    closures = [closure for closure in result.closures if closure.lot_id == 1 and closure.transaction_id == 2]
    assert len(closures) == 1, f"precondition: transaction 2 closes lot 1 once, got {result.closures}"
    return result.get_lot(1), closures[0]


def _converted(rows: list[Transaction], resolver: FxRateResolver) -> dict:
    """``convert_closure`` (CP-7a, read through the module) of lot 1's closure by transaction 2, figure by figure."""
    lot, closure = _lot_1_and_the_closure_of_transaction_2(_cp7a_run(rows))
    converted = conversions_module.convert_closure(closure, lot, resolver)
    return {name: getattr(converted, name) for name in _CONVERTED_FIGURES}


def _summary_row(rows: list[Transaction], rates: dict, market_price: Decimal):
    """Lot 1's summary row (``_build_lot_summaries``) in EUR, X quoted ``market_price`` EUR on 1 Sep, the reading day."""
    result = _cp7a_run(rows)
    summaries = _svc()._build_lot_summaries(
        engine_result=result,
        lots_by_id={lot.lot_id: lot for lot in result.lots},
        selected_ids=[1],
        fx_resolver=_resolver("EUR", rates),
        market_prices={_SEP_1: market_price},
        price_series=AssetPriceSeries([]),
        closures_by_lot=group_closures(result.closures),
        income_by_lot={},
        fees_by_lot={},
        taxes_by_lot={},
        estimated_mode=False,
        quote_base_quantity=1,
        analysis_end=_SEP_1,
    )
    return next(summary for summary in summaries if summary.lot_id == 1)


def _needs_of_the_lot_analysis(analysis: LotAnalysisType, rows: list[Transaction]) -> set[tuple[str, date]]:
    """What ``collect_fx_needs`` asks for lot 1, the window reduced to 1 Sep: no market day asks for 2 Jan or 2 Jun."""
    result = _cp7a_run(rows)
    resolver = _resolver("EUR")
    collect_fx_needs(
        fx_resolver=resolver,
        analyses=[analysis],
        lots_by_id={lot.lot_id: lot for lot in result.lots},
        selected_ids=[1],
        transactions=rows,
        price_series=AssetPriceSeries([]),
        prices=[],
        fragments=result.fragment_intervals,
        events=result.classified_events,
        closures=result.closures,
        split_ratios_by_tx_id={},
        actual_to=_SEP_1,
        computed_from=_SEP_1,
        asset_currency="EUR",
    )
    return set(resolver._needs)


class TestConvertClosure:
    """``convert_closure`` (lots/conversions.py), the one conversion point of a closure: each leg in its currency at its date."""

    @pytest.mark.parametrize(
        ("book", "rates", "expected"),
        [
            pytest.param(_r1, _USD_1_THEN_090, ("100", "99", "99", "100", "-1"), id="R1-the-D-J1-example"),
            pytest.param(_r2, _USD_1_THEN_090, ("100", "99", "396", "400", "-4"), id="R2-four-of-ten-sold"),
            pytest.param(_r3, _USD_090_ON_JUN_2, ("100", "99", "99", "100", "-1"), id="R3-bought-in-EUR-sold-in-USD"),
            pytest.param(_usd_short, _USD_110_THEN_090, ("55", "36", "0", "36", "19"), id="a-USD-short-bought-back"),
        ],
    )
    def test_each_leg_converts_in_its_own_currency_at_its_own_date(self, book, rates, expected):
        """(open price, close price, proceeds, cost, realized) in EUR: the lot's leg at its opening rate, the closing leg at the close's.

        R1: 110 × 0.90 − 100 × 1.00 = −1. R2: 4 × 110 × 0.90 − 4 × 100 × 1.00 = 396 − 400 = −4. R3: 110 USD × 0.90 − 100 EUR = −1.
        The short: its opening sale, 50 × 1.10 = 55, less its buy-back, 40 × 0.90 = 36, which is its cost: 19; a short's
        closure has no proceeds. Before CP-7a: no convert_closure (AttributeError); the readers converted every figure in the
        lot's currency at the close date — R1 open price 90, realized +9; R2 +36; R3 close price and proceeds 110, realized +10;
        the short open price 45, realized +9.
        """
        assert _converted(book(), _resolver("EUR", rates)) == dict(zip(_CONVERTED_FIGURES, map(D, expected), strict=True))

    def test_without_the_sales_rate_the_closing_leg_and_the_realized_pnl_are_unknown(self):
        """R6: R1 without a USD rate on 2 Jun — close price, proceeds and realized None, never the native 110; USD/EUR on 2 Jun reported.

        The lot's leg keeps its purchase rate: open price and cost 100. Before CP-7a: no convert_closure (AttributeError); the
        readers already read this realized P&L as None, the sale's rate being the only one it needed.
        """
        resolver = _resolver("EUR", {("USD", _JAN_2): D("1.00")})

        assert _converted(_r1(), resolver) == {"open_unit_price": D("100"), "close_unit_price": None, "proceeds": None, "cost": D("100"), "realized_pnl": None}
        assert resolver.missing_pairs() == [WACMissingPairInfo(pair="USD/EUR", dates=[_JUN_2])]

    def test_without_the_purchase_rate_the_lots_leg_and_the_realized_pnl_are_unknown(self):
        """R6: R1 without a USD rate on 2 Jan — open price, cost and realized None; the proceeds, 99, stay known; USD/EUR on 2 Jan reported.

        Before CP-7a: no convert_closure (AttributeError); the realized P&L read +9 without ever asking for the purchase rate.
        """
        resolver = _resolver("EUR", {("USD", _JUN_2): D("0.90")})

        assert _converted(_r1(), resolver) == {"open_unit_price": None, "close_unit_price": D("99"), "proceeds": D("99"), "cost": None, "realized_pnl": None}
        assert resolver.missing_pairs() == [WACMissingPairInfo(pair="USD/EUR", dates=[_JAN_2])]


class TestTheLotsRealizedPnlAndProceeds:
    """``known_realized_pnl`` and ``known_cumulative_proceeds`` (lots/histories.py): the lot summary's sums, through convert_closure."""

    @pytest.mark.parametrize(
        ("book", "rates", "expected"),
        [
            pytest.param(_r1, _USD_1_THEN_090, (D("-1"), D("99")), id="R1"),
            pytest.param(_r2, _USD_1_THEN_090, (D("-4"), D("396")), id="R2"),
            pytest.param(_r3, _USD_090_ON_JUN_2, (D("-1"), D("99")), id="R3"),
            pytest.param(_usd_short, _USD_110_THEN_090, (D("19"), D("55")), id="USD-short"),
            pytest.param(_r1, {("USD", _JUN_2): D("0.90")}, (None, D("99")), id="R6-R1-without-the-purchase-rate"),
            pytest.param(_r1, {("USD", _JAN_2): D("1.00")}, (None, None), id="GUARD-R6-R1-without-the-sales-rate"),
        ],
    )
    def test_each_closure_counts_its_legs_at_their_own_dates(self, book, rates, expected):
        """(known_realized_pnl, known_cumulative_proceeds) of lot 1, in EUR.

        Before CP-7a: R1 (+9, 99), R2 (+36, 396), R3 (+10, 110 — the USD read as EUR), the USD short (+9, 55) and R1 without
        the purchase rate (+9, 99): the realized P&L was the native gain at the sale's rate. GUARDs: the proceeds of R1, R2, the
        short (its opening sale, 50 × 1.10) and R6, and R1 without the sale's rate, unknown before as after.
        """
        result = _cp7a_run(book())
        lot = result.get_lot(1)
        closures = [closure for closure in result.closures if closure.lot_id == 1]
        resolver = _resolver("EUR", rates)

        assert (known_realized_pnl(lot, closures, resolver), known_cumulative_proceeds(lot, closures, resolver)) == expected


class TestTheLotSummaryOfASoldLot:
    """``_build_lot_summaries``: market P&L = pnl − realized, the realized P&L now each leg at its own date."""

    @pytest.mark.parametrize(
        ("book", "rates", "expected"),
        [
            pytest.param(_r1, _USD_1_THEN_090, ("99", "-1", "-1", "0", "-1"), id="R1-closed"),
            pytest.param(_r2, _USD_1_THEN_090, ("396", "80", "-4", "84", "80"), id="R2-partly-sold"),
            pytest.param(_r3, _USD_090_ON_JUN_2, ("99", "-1", "-1", "0", "-1"), id="R3-closed-sold-in-USD"),
        ],
    )
    def test_the_split_between_realized_and_market_pnl(self, book, rates, expected):
        """(cumulative proceeds, pnl, realized, market, total P&L) in EUR, X quoted 114 EUR on 1 Sep (120 USD at 0.95).

        R1: closed, so market 0 and realized = pnl = 99 − 100 = −1. R2: 6 open worth 6 × 114 = 684, proceeds 396, cost 1000:
        pnl 80, realized −4, market 84 = 6 × 114 − 6 × 100 × 1.00, the open part's gain at today's price. R3: 99 − 100 = −1.
        Before CP-7a: R1 (99, −1, +9, −10, −1) and R2 (396, 80, +36, +44, 80) — the same total, split otherwise — and R3
        (110, +10, +10, 0, +10), the sale's 110 USD read as euros.
        """
        row = _summary_row(book(), rates, D("114"))

        assert (row.cumulative_proceeds, row.pnl, row.realized_pnl, row.market_pnl, row.total_pnl) == tuple(map(D, expected))


class TestShortLotsSubtractTheirBuyBacks:
    """R10 (CP-7a): a short lot's P&L — its total value — is its opening proceeds less every buy-back's cost to date less its open value.

    Each buy-back costs its ConvertedClosure.cost: the BUY's price, in its currency at its date. Before R10 a short read its
    opening proceeds less its open value only: what a buy-back paid out was never subtracted, so covering a short at the
    market price added the price paid to its P&L.
    """

    @pytest.mark.parametrize(
        ("book", "rates", "expected"),
        [
            pytest.param(_short_half_bought_back, {}, ("450", "100", "100", "50", "50"), id="half-bought-back"),
            pytest.param(_short_bought_back_whole, {}, ("0", "100", "100", "100", "0"), id="bought-back-whole"),
            pytest.param(_usd_short, _USD_110_THEN_090, ("0", "19", "19", "19", "0"), id="a-USD-short-bought-back-whole"),
        ],
    )
    def test_the_summary_subtracts_the_buy_backs(self, book, rates, expected):
        """(open value, total value, pnl, realized, market) of the short in EUR, X quoted 90 EUR on 1 Sep.

        Half bought back: 1000 − 5 × 90 paid − 5 × 90 still owed = 100; realized 5 × (100 − 90) = 50, market 50 on the 5 still
        open. Whole: 1000 − 900 = 100, all of it realized, market 0. The USD short: 55 − 36 = 19, all realized, market 0 —
        each leg at its own date. Before R10 (and CP-7a): (450, 550, 550, 50, 500), (0, 1000, 1000, 100, 900) and
        (0, 55, 55, +9, 46).
        """
        row = _summary_row(book(), rates, D("90"))

        assert (row.open_value, row.total_value, row.pnl, row.realized_pnl, row.market_pnl) == tuple(map(D, expected))

    def test_a_buy_back_at_the_market_price_does_not_move_the_value_history(self):
        """R10 on the value history of the half-bought-back short, X at 90 EUR from 1 to 3 Jun: (date, open value, total value, pnl).

        At 90 the short is worth 10 × (100 − 90) = 100 before the buy-back and after it: buying 5 back at 90 on 2 Jun pays 450
        out and removes 450 of liability. Before R10 the 450 paid out was never subtracted: 100 on 1 Jun (GUARD), then 550.
        """
        result = _cp7a_run(_short_half_bought_back())
        days = _days(date(2025, 6, 1), 3)

        points = build_value_history(
            selected_ids=[1],
            lots_by_id={lot.lot_id: lot for lot in result.lots},
            fragments_by_lot=group_fragments(result.fragment_intervals),
            closures_by_lot=group_closures(result.closures),
            market_prices=dict.fromkeys(days, D("90")),
            history_dates=days,
            fx_resolver=_resolver("EUR"),
            income_prefix_by_lot={},
            fees_prefix_by_lot={},
            taxes_prefix_by_lot={},
            at_cost_until=None,
            quote_base_quantity=1,
        )

        assert [(point.date, point.open_value, point.total_value, point.pnl) for point in points if point.lot_id == 1] == [
            (date(2025, 6, 1), D("900"), D("100"), D("100")),
            (date(2025, 6, 2), D("450"), D("100"), D("100")),
            (date(2025, 6, 3), D("450"), D("100"), D("100")),
        ]


class TestTheClosureRowsOfTheLotHistory:
    """``_build_closure_rows``: a closure row's open price at the lot's opening rate, its close price and proceeds at the close's."""

    @pytest.mark.parametrize(
        ("book", "rates", "expected"),
        [
            pytest.param(_r1, _USD_1_THEN_090, (LotTimelineEventKind.SELL, D("100"), D("99"), D("-1"), D("99")), id="R1"),
            pytest.param(_r3, _USD_090_ON_JUN_2, (LotTimelineEventKind.SELL, D("100"), D("99"), D("-1"), D("99")), id="R3-sold-in-USD"),
            pytest.param(_usd_short, _USD_110_THEN_090, (LotTimelineEventKind.BUY, D("55"), D("36"), D("19"), D("0")), id="USD-short-bought-back"),
        ],
    )
    def test_a_closure_row_converts_each_leg_at_its_own_date(self, book, rates, expected):
        """(kind, open price, close price, realized, proceeds) of transaction 2's row, in EUR.

        Before CP-7a every figure converted in the lot's currency at the close date: R1 (SELL, 90, 99, +9, 99), R3 (SELL, 100,
        110, +10, 110), the USD short (BUY, 45, 36, +9, 0).
        """
        result = _cp7a_run(book())
        rows = _svc()._build_closure_rows(result.closures, {1}, {lot.lot_id: lot for lot in result.lots}, _resolver("EUR", rates))

        assert [(row.kind, row.open_unit_price, row.close_unit_price, row.realized_pnl, row.proceeds) for row in rows if row.transaction_id == 2] == [expected]


class TestTheRatesAClosureNeeds:
    """The rates a closure needs: its own currency at its close date, its lot's at the lot's opening — need_closure_rates."""

    def test_need_closure_rates_asks_for_both_legs(self):
        """need_closure_rates (CP-7a, read through the module) alone: R1 asks for USD on 2 Jan and on 2 Jun; R3, whose lot is in EUR, on 2 Jun only.

        Before CP-7a: no need_closure_rates (AttributeError).
        """
        needs = {}
        for name, book in (("R1", _r1), ("R3", _r3)):
            lot, closure = _lot_1_and_the_closure_of_transaction_2(_cp7a_run(book()))
            resolver = _resolver("EUR")
            conversions_module.need_closure_rates(resolver, closure, lot)
            needs[name] = sorted(resolver._needs)

        assert needs == {"R1": [("USD", _JAN_2), ("USD", _JUN_2)], "R3": [("USD", _JUN_2)]}

    @pytest.mark.parametrize("analysis", [LotAnalysisType.LOT_SUMMARY, LotAnalysisType.RETURN_HISTORY])
    def test_the_lot_summary_asks_for_the_sales_currency_on_the_sales_date(self, analysis):
        """collect_fx_needs for 1 bought in GBP and sold in USD, read from 1 Sep: ("USD", 2 Jun) and ("GBP", 2 Jan) among the needs.

        The window starts after the sale, so no market day asks for 2 Jun: the closure must. Before CP-7a it asked for the lot's
        GBP on 2 Jun instead, and the sale's USD was never loaded.
        """
        assert {("USD", _JUN_2), ("GBP", _JAN_2)} <= _needs_of_the_lot_analysis(analysis, _gbp_lot_sold_in_usd())

    @pytest.mark.parametrize("analysis", [LotAnalysisType.EVENT_HISTORY, LotAnalysisType.CUSTODY_HISTORY])
    def test_the_lot_history_asks_no_rate_for_the_value_an_adjustment_out_stores(self, analysis):
        """collect_fx_needs for 10 bought in GBP, 4 taken out on 2 Jun by an ADJUSTMENT (an in-memory database row) storing
        18 USD a unit: ("GBP", 2 Jan) among the needs, ("USD", 2 Jun) not — N78-1: the units leave at 0, in the lot's
        currency, and nothing of the stored value is converted. No row is in USD, so only a closure in USD could ask.

        Before N78-1 (CP-7a): the closure carried the stored 18 USD and asked ("USD", 2 Jun).
        """
        needs = _needs_of_the_lot_analysis(analysis, _gbp_lot_handed_over_at_a_usd_cost())
        assert ("GBP", _JAN_2) in needs and ("USD", _JUN_2) not in needs, f"N78-1: no USD rate for the value an ADJUSTMENT-out stores; needs: {sorted(needs)}"

    def test_the_performance_history_asks_for_the_sales_currency_on_the_sales_date(self):
        """collect_performance_fx_needs for 1 bought in GBP and sold in USD: ("USD", 2 Jun) and ("GBP", 2 Jan) among the needs.

        Before CP-7a: ("GBP", 2 Jan) for the BUY and ("GBP", 2 Jun) for the sale, whose 110 USD were then read as GBP.
        """
        rows = _gbp_lot_sold_in_usd()
        result = _cp7a_run(rows)
        resolver = _resolver("EUR")

        collect_performance_fx_needs(
            fx_resolver=resolver,
            analyses=[LotAnalysisType.PERFORMANCE_HISTORY],
            transactions=rows,
            closures=result.closures,
            lots_by_id={lot.lot_id: lot for lot in result.lots},
            asset_currency="EUR",
        )

        assert {("USD", _JUN_2), ("GBP", _JAN_2)} <= set(resolver._needs)


class TestTheCashFlowOfASale:
    """``build_performance_history``: a SELL enters the cash flows at its proceeds, converted from its own currency at its date.

    No day is valued at cost here (``at_cost_until=None``): the rules of a day with a mark, or without one outside the days at cost; the days at cost are ``TestPerformanceHistoryAtCost``.
    """

    _DAYS = _days(date(2025, 6, 1), 3)

    @pytest.mark.parametrize(
        ("book", "rates", "expected_sale_flow"),
        [
            pytest.param(_r3, _USD_090_ON_JUN_2, D("99"), id="R3-a-lot-bought-in-EUR-sold-in-USD"),
            pytest.param(_r1, _USD_1_THEN_090, D("99"), id="GUARD-R1-a-USD-lot-sold-in-USD"),
        ],
    )
    def test_a_sale_enters_the_cash_flows_at_its_converted_proceeds(self, monkeypatch, book, rates, expected_sale_flow):
        """The flows, net by date: −100 for the purchase, carried onto 1 Jun (the first priced day), then the sale's 110 USD at 0.90 on 2 Jun.

        Read where build_performance_history hands them on — calculate_simple_roi_series, as histories imports it. Before CP-7a
        R3's sale entered at +110, its USD read as the lot's EUR; R1's at +99 (GUARD: lot and sale in USD).
        """
        received: list[list] = []
        original = histories_module.calculate_simple_roi_series

        def spy(nav_snapshots, cash_flows):
            received.append(list(cash_flows))
            return original(nav_snapshots, cash_flows)

        monkeypatch.setattr(histories_module, "calculate_simple_roi_series", spy)
        rows = book()
        result = _cp7a_run(rows)
        context = PerformanceSourceContext(
            transactions=rows,
            engine_result=result,
            lots_by_id={lot.lot_id: lot for lot in result.lots},
            fragments_by_lot=group_fragments(result.fragment_intervals),
            closures_by_lot=group_closures(result.closures),
            tx_by_id={row.id: row for row in rows},
        )

        build_performance_history(
            scope_broker_ids=[1],
            history_dates=self._DAYS,
            market_prices=dict.fromkeys(self._DAYS, D("100")),
            asset_currency="EUR",
            fx_resolver=_resolver("EUR", rates),
            context=context,
            quote_base_quantity=1,
            at_cost_until=None,
        )

        assert len(received) == 1, "precondition: the series is computed once, the purchase being a flow"
        net_by_date: dict[date, Decimal] = {}
        for flow in received[0]:
            net_by_date[flow.date] = net_by_date.get(flow.date, D("0")) + flow.amount
        assert net_by_date == {date(2025, 6, 1): D("-100"), _JUN_2: expected_sale_flow}


# =========================================================================== #
# CP-7b — the lots read their prices from the asset's daily price series (V1, with J-28)
# =========================================================================== #
#
# Workstream J «Numeri e analisi», release 1.3. The developer's decisions P2/J-17 («trades are prices, an adjustment
# isn't») and P21 («every amount at the rate of its day»), then option (a) of the CP-7b amendment («the Dashboard's
# per-day rule in the lots too: one rule in the whole app»). The lots read every price from the asset's daily price
# series (financial_math.price_marks.AssetPriceSeries, built by build_asset_price_series): the last observation on or
# before a day — a market close, or the average of that day's BUY/SELL prices, never an ADJUSTMENT — carried forward.
#
# * A lot opened by an ADJUSTMENT takes the series' mark on its opening day as its reference: ``exact`` for a close of
#   that day, ``fallback`` for anything else (a close carried forward, a trade price, carried or not). No mark, no
#   reference: the lot falls back to its own price, as before. A lot opened by a BUY keeps its own price.
# * opening_reference_price(lot, price_series) hands that reference over in the currency of the opening day's mark,
#   dated the opening day, so it converts at that day's rate; collect_fx_needs asks for that rate.
# * The days with no observation on or before them — the run before the asset's first close, BUY or SELL — are valued
#   at cost (last_day_without_observation gives the last of them); a later day without a market price stays a gap.
#
# Before CP-7b a PriceHistoryLookup read the stored closes alone: an ADJUSTMENT's lot took the last close however old,
# dated (and so converted) at that close's own day, and the lots were at cost only when the asset had no close at all.
#
# The reference is decided inside get_lots_analysis, before the FIFO engine runs, so the first class drives the whole
# service on in-memory rows: its loaders are doubles returning the test's rows, its session a double that hands over
# the asset. Everything is in EUR, so no rate is ever asked and nothing reaches a database: the unit stays PURE. The new
# name, last_day_without_observation, is read through its module while a test runs (prices_module), never imported at
# module level: before CP-7b only the tests that call it fail, and the rest of the file still collects. Each docstring
# says what its test read before CP-7b; GUARD marks a value CP-7b leaves as it was.

_MAR_10 = date(2024, 3, 10)  # five days before the opening
_MAR_12 = date(2024, 3, 12)  # three days before
_MAR_13 = date(2024, 3, 13)  # two days before
_MAR_15 = date(2024, 3, 15)  # transaction 2, an ADJUSTMENT +5 at 90 EUR a unit, opens the lot under test
_MAR_17 = date(2024, 3, 17)  # two days after
_MAR_18 = date(2024, 3, 18)  # three days after
_MAR_20 = date(2024, 3, 20)  # the reading day of every analysis of this section
_REFERENCE_ISSUES = {IssueCode.REFERENCE_PRICE_FALLBACK, IssueCode.REFERENCE_PRICE_UNAVAILABLE}


def _adjustment_in_at_90(day: date = _MAR_15) -> Transaction:
    """Transaction 2: 5 units received by an ADJUSTMENT at a cost basis of 90 EUR a unit — an inherited position."""
    return _tx(2, tx_type=TransactionType.ADJUSTMENT, tx_date=day, quantity=D("5"), amount=D("0"), currency=None, cost_basis_override=D("90"), cost_basis_currency="EUR")


def _bought_at_120(day: date) -> Transaction:
    """Transaction 1: 10 bought for 1200 EUR, 120 a unit."""
    return _tx(1, tx_date=day, quantity=D("10"), amount=D("-1200"), currency="EUR")


def _series_of(*rows: Transaction, closes: dict[date, str] | None = None) -> AssetPriceSeries:
    """The asset's series as the service builds it (build_asset_price_series), from EUR closes and transaction rows, quoted per unit."""
    return build_asset_price_series(
        price_rows=[(day, D(close), "EUR") for day, close in (closes or {}).items()],
        transactions=list(rows),
        split_linked_tx_ids=set(),
        asset_currency="EUR",
        quote_base_quantity=1,
    )


def _loader_returning(value):
    """A double of one of the service's async loaders: whatever it is asked, ``value``."""

    async def loader(*_args, **_kwargs):
        return value

    return loader


class _SessionWithTheAsset:
    """The session double: get_lots_analysis asks its session for the asset directly, for everything else through a loader."""

    def __init__(self, asset) -> None:
        self._asset = asset

    async def get(self, _model, _key):
        return self._asset


async def _analysis_on_rows(monkeypatch, *rows: Transaction, quotes: tuple[PriceHistory, ...] = ()) -> LotsAnalysisResponse:
    """get_lots_analysis (LOT_SUMMARY, in EUR, up to 20 Mar) on in-memory rows: asset 7 in EUR quoted per unit, broker 1 alone in scope.

    Each loader hands over what the database would for these rows — the transactions by date then id, the closes by
    date (the caller passes those up to the reading day), no split, no income, no cost — and monkeypatch fails on a
    loader the service no longer has, rather than letting the call reach the session double.
    """
    service = LotsAnalysisService(db=_SessionWithTheAsset(SimpleNamespace(id=7, display_name="X", currency="EUR", quote_base_quantity=1)))
    loaded = {
        "_get_scope_broker_ids": [1],
        "_load_transactions": sorted(rows, key=lambda row: (row.date, row.id)),
        "_load_split_ratios": {},
        "_load_broker_shorting": {1: False},
        "_load_prices": sorted(quotes, key=lambda row: row.date),
        "_load_income_transactions": [],
        "_load_cost_transactions": [],
    }
    for name, value in loaded.items():
        monkeypatch.setattr(service, name, _loader_returning(value))
    return await service.get_lots_analysis(
        user_id=1,
        asset_id=7,
        broker_ids=[1],
        date_from=None,
        date_to=_MAR_20,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=[LotAnalysisType.LOT_SUMMARY],
    )


def _reference_of(response: LotsAnalysisResponse, transaction_id: int) -> tuple:
    """(reference unit price, its source, the engine's reference issues) of the lot ``transaction_id`` opened, found by that id."""
    lots = [lot for lot in response.lots or [] if lot.opening_transaction_id == transaction_id]
    assert len(lots) == 1, f"precondition: transaction {transaction_id} opens one lot, got {response.lots}"
    assert response.data_quality is not None
    issues = [str(issue.code) for issue in response.data_quality.issues if issue.code in _REFERENCE_ISSUES and issue.message_params.get("lot_id") == lots[0].lot_id]
    return lots[0].reference_unit_price, lots[0].reference_price_source, issues


class TestTheReferenceOfALotOpenedByAnAdjustment:
    """The reference get_lots_analysis gives the lot transaction 2 opens — an ADJUSTMENT +5 at 90 EUR on 15 Mar — and a BUY's lot."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("closes", "buy_day", "expected"),
        [
            pytest.param({_MAR_15: "100"}, _MAR_15, (D("100"), "exact", []), id="GUARD-a-close-on-the-opening-day-wins-over-a-same-day-BUY"),
            pytest.param({_MAR_12: "100"}, None, (D("100"), "fallback", ["REFERENCE_PRICE_FALLBACK"]), id="GUARD-a-close-three-days-before-nothing-after"),
            pytest.param({_MAR_10: "100"}, _MAR_13, (D("120"), "fallback", ["REFERENCE_PRICE_FALLBACK"]), id="a-BUY-newer-than-the-last-close"),
            pytest.param({_MAR_10: "100"}, _MAR_15, (D("120"), "fallback", ["REFERENCE_PRICE_FALLBACK"]), id="a-BUY-on-the-opening-day-after-an-older-close"),
            pytest.param({}, _MAR_13, (D("120"), "fallback", ["REFERENCE_PRICE_FALLBACK"]), id="no-close-a-BUY-before"),
            pytest.param({_MAR_18: "100"}, _MAR_17, (D("90"), "exact", ["REFERENCE_PRICE_UNAVAILABLE"]), id="GUARD-nothing-on-or-before-the-opening-day"),
        ],
    )
    async def test_the_reference_is_the_mark_of_the_opening_day(self, monkeypatch, closes, buy_day, expected):
        """(reference unit price, source, the engine's reference issue) of the ADJUSTMENT's lot in EUR; the BUY, when there is one, is 10 at 120 EUR.

        (a) A close on the opening day is the reference, ``exact`` — over a BUY of the same day too: a close wins its day.
        (b) A close three days before, nothing after: that close, ``fallback``. (c) A BUY newer than the last close, before
        the opening day or on it: the BUY's 120, ``fallback``; before CP-7b the older close, 100, ``fallback``. (d) No close,
        a BUY before: the BUY's 120, ``fallback``; before CP-7b no reference (REFERENCE_PRICE_UNAVAILABLE), so the lot's own
        90, ``exact``. GUARD: with nothing on or before the opening day (a BUY and a close after it) there is still no
        reference, and the lot keeps its own 90.
        """
        rows = [_adjustment_in_at_90()] if buy_day is None else [_adjustment_in_at_90(), _bought_at_120(buy_day)]
        response = await _analysis_on_rows(monkeypatch, *rows, quotes=tuple(_price(day, D(close)) for day, close in closes.items()))

        assert _reference_of(response, 2) == expected

    @pytest.mark.asyncio
    async def test_a_lot_opened_by_a_buy_keeps_its_own_price(self, monkeypatch):
        """GUARD: 10 bought at 120 EUR on 13 Mar, a day X closed at 100 — the BUY's lot is referenced to its own price, exact, with no issue."""
        response = await _analysis_on_rows(monkeypatch, _bought_at_120(_MAR_13), quotes=(_price(_MAR_13, D("100")),))

        assert _reference_of(response, 1) == (D("120"), "exact", [])


class TestOpeningReferencePriceReadsTheSeries:
    """opening_reference_price(lot, price_series): the engine's reference, in the currency of the day's mark, dated the opening day.

    The price and its source are the ones the FIFO engine put on the lot, from the same series (the class above); what the
    function adds is the currency of the opening day's mark and the date the reference converts at. Before CP-7b it read a
    PriceHistoryLookup: handed a series, it fails on the mark, which has no ``resolved_date``.
    """

    def test_a_reference_carried_from_an_older_close_is_dated_the_opening_day(self):
        """(e) A lot opened on 15 Mar whose reference, 64, is a USD close of 10 Mar carried forward: (64, "USD", 15 Mar, "fallback").

        Dated its opening day, the reference converts at that day's rate (P21). Before CP-7b: 10 Mar, the close's own day.
        """
        lot = _lot(1, opening_date=_MAR_15, reference_unit_price=D("64"), reference_price_source="fallback")

        assert opening_reference_price(lot, _series(_quote(_MAR_10, D("64"), "USD"))) == (D("64"), "USD", _MAR_15, "fallback")

    def test_the_reference_is_in_the_currency_of_the_days_mark_a_trade_too(self):
        """(c) X closed at 120 USD on 10 Mar, then was bought at 96 GBP on 13 Mar: on 15 Mar the mark is the BUY's, so the reference is in GBP.

        The engine took the BUY's 96 as the lot's reference; the function names its currency, GBP — not the last close's
        USD, which the lookup of the closes alone gave before CP-7b, with that close's day, 10 Mar.
        """
        lot = _lot(1, opening_date=_MAR_15, reference_unit_price=D("96"), reference_price_source="fallback")
        series = _series(_quote(_MAR_10, D("120"), "USD"), _trade(_MAR_13, D("96"), "GBP"))

        assert opening_reference_price(lot, series) == (D("96"), "GBP", _MAR_15, "fallback")

    @pytest.mark.parametrize(
        "series",
        [
            pytest.param(_series(_quote(_MAR_17, D("100"))), id="a-first-close-after-the-opening-day"),
            pytest.param(
                build_asset_price_series(price_rows=[(_MAR_15, None, "EUR")], transactions=[], split_linked_tx_ids=set(), asset_currency="EUR", quote_base_quantity=1),
                id="a-price-row-without-a-close",
            ),
        ],
    )
    def test_no_mark_on_or_before_the_opening_day_hands_no_reference_over(self, series):
        """No mark on the opening day: the first observation comes after it, or the only row has no close (volume or open only),
        which is no quote. The reference the lot carries is not handed over: (None, None, 15 Mar, its source).

        The two cases of the old closes' lookup — nothing before the first close, a null close ignored — on the series.
        """
        lot = _lot(1, opening_date=_MAR_15, reference_unit_price=D("9"), reference_price_source="fallback")

        assert opening_reference_price(lot, series) == (None, None, _MAR_15, "fallback")


class TestTheReferenceAsksForTheRateOfItsOpeningDay:
    """collect_fx_needs (lots/conversions.py): the reference's rate is its mark's currency on the lot's opening day."""

    @pytest.mark.parametrize("analysis", [LotAnalysisType.LOT_SUMMARY, LotAnalysisType.RETURN_HISTORY])
    def test_the_reference_needs_the_marks_currency_on_the_opening_day(self, analysis):
        """(f) The EUR lot of 15 Mar referenced to a USD close of 10 Mar, read from 20 Mar: one need, ("USD", 15 Mar).

        No market day asks for anything (no close row, no trade) and the lot's own EUR needs no rate, so the one rate asked
        is the reference's. Before CP-7b: ("USD", 10 Mar), the close's day.
        """
        lot = _lot(1, opening_date=_MAR_15, currency="EUR", reference_unit_price=D("64"), reference_price_source="fallback")
        resolver = _resolver("EUR")

        collect_fx_needs(
            fx_resolver=resolver,
            analyses=[analysis],
            lots_by_id={1: lot},
            selected_ids=[1],
            transactions=[],
            price_series=_series(_quote(_MAR_10, D("64"), "USD")),
            prices=[],
            fragments=[],
            events=[],
            closures=[],
            split_ratios_by_tx_id={},
            actual_to=_MAR_20,
            computed_from=_MAR_20,
            asset_currency="USD",
        )

        assert resolver._needs == [("USD", _MAR_15)]


class TestLastDayWithoutObservation:
    """last_day_without_observation (lots/prices.py, read through the module) over 15–19 Mar: the last day valued at cost, or None.

    The last of the ascending days with no observation on or before it — no close, no BUY or SELL — which the lots value at
    cost, as the Dashboard values a holding (J-17); None when the first day already has one. Before CP-7b: no such function
    (AttributeError), and the lots were at cost only when the asset had no close at all, then on every day.
    """

    _DAYS = _days(_MAR_15, 5)

    @pytest.mark.parametrize(
        ("build_series", "expected"),
        [
            pytest.param(lambda: _series_of(), date(2024, 3, 19), id="no-observation-at-all-the-last-day"),
            pytest.param(lambda: _series_of(closes={_MAR_15: "100"}), None, id="the-first-day-observed-None"),
            pytest.param(lambda: _series_of(closes={_MAR_10: "100"}), None, id="an-older-close-carried-onto-the-first-day-None"),
            pytest.param(lambda: _series_of(closes={_MAR_17: "100"}), date(2024, 3, 16), id="a-first-close-mid-run-the-day-before-it"),
            pytest.param(lambda: _series_of(_bought_at_120(_MAR_17)), date(2024, 3, 16), id="a-first-BUY-mid-run-counts-like-a-close"),
            pytest.param(lambda: _series_of(_adjustment_in_at_90(_MAR_17)), date(2024, 3, 19), id="an-ADJUSTMENT-is-no-observation-the-last-day"),
        ],
    )
    def test_the_last_day_valued_at_cost(self, build_series, expected):
        """The series is the service's, built from rows (closes in EUR, transactions): a BUY observes like a close, an
        ADJUSTMENT at a cost never does (J-17), and a close older than the first day is carried onto it."""
        assert prices_module.last_day_without_observation(build_series(), self._DAYS) == expected


# =========================================================================== #
# R13-SEC8-2 — a lot opened before 1900: the analysis starts at the floor
# =========================================================================== #
#
# MF-SEC8-2 (MEDIUM, DoS). get_lots_analysis started its window at the first transaction: computed_from =
# transactions[0].date, the prices loaded from it, every day from it valued (history_dates), a rate asked for every day
# since for a foreign asset (collect_fx_needs), and display_from = date_from or computed_from. A lot stored in 1890 made
# it walk every day since 1890. The cure: computed_from = max(first transaction, EARLIEST_RANGE_START = 1900-01-01) and
# display_from clamped to it too — no price load, history point, income marker or daily rate before 1900 — while the
# FIFO engine still opens the lot on its own date, with its own quantity, cost and income. The floor is a literal here:
# the name is new. Driven like the CP-7b class above: get_lots_analysis on loader doubles and a session double; in EUR
# no rate is asked, and the USD case replaces the rates' reader where conversions reads it (convert_bulk; unit_rate_steps
# since L1b). Each docstring says what HEAD
# 94e170ae1 returns; GUARD marks a value the cure leaves as it was.

_SEC8_FLOOR = date(1900, 1, 1)
_SEC8_OPENED = date(1890, 1, 1)  # transaction 1, a BUY of 10 at 120 a unit
_SEC8_DIVIDEND_DAY = date(1890, 6, 1)  # transaction 2, a DIVIDEND of 50 on the lot
_SEC8_QUOTED = date(1900, 1, 5)  # the asset's only close, 150
_SEC8_END = date(1900, 1, 10)  # the reading day: near the floor, so the cured run walks ten days, HEAD's 3 662
_SEC8_HISTORIES = (LotAnalysisType.VALUE_HISTORY, LotAnalysisType.RETURN_HISTORY, LotAnalysisType.PRICE_HISTORY, LotAnalysisType.PERFORMANCE_HISTORY)


async def _sec8_analysis(
    monkeypatch,
    *,
    date_from: date | None,
    currency: str = "EUR",
    opening: Transaction | None = None,
    analyses: list[LotAnalysisType | str] | None = None,
) -> tuple[LotsAnalysisResponse, list[dict]]:
    """get_lots_analysis up to 10 Jan 1900 of asset 7 (in ``currency``, quoted per unit) for broker 1 alone: the summary,
    the four histories and the income markers, or ``analyses`` when given (Y-30's market price line). Returns the
    response and the arguments of every price load.

    The rows: 10 units bought for 1200 on 1890-01-01 (or ``opening`` in their place, Y-30), a DIVIDEND of 50 on
    1890-06-01, a close of 150 on 5 Jan 1900 — all in ``currency``. No split, no cost transaction.
    """
    service = LotsAnalysisService(db=_SessionWithTheAsset(SimpleNamespace(id=7, display_name="X", currency=currency, quote_base_quantity=1)))
    price_loads: list[dict] = []

    async def load_prices(*_args, **kwargs):
        price_loads.append(kwargs)
        return [_price(_SEC8_QUOTED, D("150"), currency)]

    loaded = {
        "_get_scope_broker_ids": [1],
        "_load_transactions": [opening if opening is not None else _tx(1, tx_date=_SEC8_OPENED, quantity=D("10"), amount=D("-1200"), currency=currency)],
        "_load_split_ratios": {},
        "_load_broker_shorting": {1: False},
        "_load_income_transactions": [_tx(2, tx_type=TransactionType.DIVIDEND, tx_date=_SEC8_DIVIDEND_DAY, quantity=D("0"), amount=D("50"), currency=currency)],
        "_load_cost_transactions": [],
    }
    for name, value in loaded.items():
        monkeypatch.setattr(service, name, _loader_returning(value))
    monkeypatch.setattr(service, "_load_prices", load_prices)
    response = await service.get_lots_analysis(
        user_id=1,
        asset_id=7,
        broker_ids=[1],
        date_from=date_from,
        date_to=_SEC8_END,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=[LotAnalysisType.LOT_SUMMARY, *_SEC8_HISTORIES, LotAnalysisType.INCOME_EVENTS] if analyses is None else list(analyses),
    )
    return response, price_loads


def _sec8_history_dates(response: LotsAnalysisResponse) -> dict[str, list[date]]:
    """The dates of every point of the four histories, by history."""
    return {name: [point.date for point in getattr(response, name) or []] for name in ("value_history", "return_history", "price_history", "performance_history")}


class TestALotOpenedBeforeTheFloor:
    """get_lots_analysis on a lot bought on 1890-01-01: nothing of the analysis' window before 1900-01-01."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("date_from", [pytest.param(None, id="no-date_from"), pytest.param(date(1, 1, 1), id="date_from-day-one")])
    async def test_the_window_starts_at_the_floor(self, monkeypatch, date_from):
        """computed_date_from 1900-01-01, the prices loaded from it, every history point and income marker on or after
        it, the value history starting on it. HEAD: computed_date_from 1890-01-01, the prices loaded from it, the
        histories from 1890-01-01 and the 1890 dividend's marker."""
        response, price_loads = await _sec8_analysis(monkeypatch, date_from=date_from)

        assert response.calculation_metadata.computed_date_from == _SEC8_FLOOR
        assert [load.get("date_from") for load in price_loads] == [_SEC8_FLOOR], f"price loads: {price_loads}"
        histories = _sec8_history_dates(response)
        assert all(histories.values()), f"precondition: every history has points, got {[name for name, dates in histories.items() if not dates]} empty"
        early = {name: (len(dates), min(dates)) for name, dates in histories.items() if min(dates) < _SEC8_FLOOR}
        assert early == {}, f"(points before the floor, first date) by history: {early}"
        assert min(histories["value_history"]) == _SEC8_FLOOR
        assert [event.date for event in response.income_events or [] if event.date < _SEC8_FLOOR] == []

    @pytest.mark.asyncio
    async def test_the_lot_keeps_its_own_date_and_numbers(self, monkeypatch):
        """GUARD: the lot opens on 1890-01-01 with its 10 units for 1200 and its 50 of income; on 1900-01-01 it is worth
        1200 (the BUY's 120, carried), its income 50; on 10 Jan 1900, 1500 (10 x 150)."""
        response, _ = await _sec8_analysis(monkeypatch, date_from=None)

        lots = [lot for lot in response.lots or [] if lot.opening_transaction_id == 1]
        assert len(lots) == 1, f"precondition: transaction 1 opens one lot, got {response.lots}"
        lot = lots[0]
        assert (lot.opening_date, lot.original_quantity, lot.open_quantity, lot.original_cost, lot.asset_income, lot.open_value) == (_SEC8_OPENED, D("10"), D("10"), D("1200"), D("50"), D("1500"))
        value_by_day = {point.date: point for point in response.value_history or [] if point.lot_id == lot.lot_id}
        assert (value_by_day[_SEC8_FLOOR].open_value, value_by_day[_SEC8_FLOOR].original_cost, value_by_day[_SEC8_FLOOR].income) == (D("1200"), D("1200"), D("50"))
        assert value_by_day[_SEC8_END].open_value == D("1500")

    @pytest.mark.asyncio
    async def test_a_foreign_lot_asks_no_daily_rate_before_the_floor(self, monkeypatch):
        """The same rows in USD, read in EUR: before the floor only the rows' own days are asked (the BUY's 1890-01-01,
        the dividend's 1890-06-01); the daily rates of the price line start on 1900-01-01. HEAD: every day from
        1890-01-01."""
        requested: set[tuple[str, date]] = set()

        async def recording_convert_bulk(_session, conversions, raise_on_error=False):
            requested.update((amount.code, day) for amount, _to, day in conversions)
            return [(Currency(code="EUR", amount=amount.amount * D("0.9")), day, False) for amount, _to, day in conversions], []

        async def recording_unit_rate_steps(_session, requests):
            for (source, _destination), windows in requests.items():
                requested.update((source, day) for day in _covered_days(list(windows)))
            return {pair: _FlatSteps(D("0.9")) for pair in requests}

        # The rates are read through whichever reader the resolver loads from: ``convert_bulk`` before L1b, ``unit_rate_steps``
        # after (``raising=False``: each name is absent from ``conversions`` on the other side of the cure).
        monkeypatch.setattr(conversions_module, "convert_bulk", recording_convert_bulk, raising=False)
        monkeypatch.setattr(conversions_module, "unit_rate_steps", recording_unit_rate_steps, raising=False)

        await _sec8_analysis(monkeypatch, date_from=None, currency="USD")

        before_the_floor = sorted(day for _currency, day in requested if day < _SEC8_FLOOR)
        assert before_the_floor == [_SEC8_OPENED, _SEC8_DIVIDEND_DAY], f"{len(before_the_floor)} days asked before the floor, from {before_the_floor[:1]}"
        assert ("USD", _SEC8_FLOOR) in requested, "the price line's daily rates start on the floor"


# =========================================================================== #
# Y-30 — the market price line, independent of the lots
# =========================================================================== #
#
# The price/WAC chart drew its price line from PRICE_HISTORY, which is per lot: with a FAILED replay (J-12) every lot
# section is None, so the chart lost the line, and on a day with no lot open it had a hole. Y-30 (N89) adds
# MARKET_PRICE_HISTORY: one point per day of the analysis' window that has a mark convertible to the target currency
# (build_market_price_history, beside build_price_history in financial_math/lots/histories.py), whatever lot is open.
# The new names are read through their modules while a test runs (histories_module, portfolio_module) and the analysis
# is asked for by its string: before Y-30 only these tests fail — AttributeError, ValueError ('MARKET_PRICE_HISTORY' is
# not a valid LotAnalysisType) — and the rest of the file still collects. Each docstring says what it reads today. The
# service-level contract is in test_financial/test_lots_market_price_history.py.

_MARKET_PRICE_HISTORY = "MARKET_PRICE_HISTORY"


class TestTheMarketPriceLineBuilder:
    """build_market_price_history(estimated_market_prices, history_dates, target_currency) and the point it builds."""

    def test_build_market_price_history_one_point_per_history_date_with_a_mark(self):
        """Five history days, 10–14 Jan 2024; marks on 13, 10 and 11 Jan (given in that order) and on 20 Jan, outside the
        history. One point per history day with a mark, in the history's order: 10 Jan (10, estimated), 11 Jan (11,
        estimated), 13 Jan (12.5, not estimated). 12 and 14 Jan have no mark, so no point; 20 Jan is no history day, so no
        point either. Every point is in the target currency given — USD here, never the response's default —, its
        ``estimated`` the mark's.

        Today: AttributeError — lots/histories.py has no build_market_price_history.
        """
        points = histories_module.build_market_price_history(
            estimated_market_prices={
                date(2024, 1, 13): (D("12.5"), False),
                date(2024, 1, 10): (D("10"), True),
                date(2024, 1, 20): (D("99"), False),
                date(2024, 1, 11): (D("11"), True),
            },
            history_dates=_days(date(2024, 1, 10), 5),
            target_currency="USD",
        )

        assert [(point.date, point.market_price, point.currency, point.estimated) for point in points] == [
            (date(2024, 1, 10), D("10"), "USD", True),
            (date(2024, 1, 11), D("11"), "USD", True),
            (date(2024, 1, 13), D("12.5"), "USD", False),
        ]

    def test_build_market_price_history_without_a_mark_has_no_point(self):
        """No mark on any history day: an empty line, not an error.

        Today: AttributeError — lots/histories.py has no build_market_price_history.
        """
        points = histories_module.build_market_price_history(estimated_market_prices={}, history_dates=_days(date(2024, 1, 10), 3), target_currency="EUR")

        assert points == []

    def test_market_price_history_point_is_the_lot_point_without_lot_id(self):
        """MarketPriceHistoryPoint is LotPriceHistoryPoint without ``lot_id``: ``date``, ``market_price``, ``currency``,
        ``estimated`` — False unless said —, a strict model (an extra field, ``lot_id`` included, is refused) whose
        ``currency`` must be an ISO code.

        Today: AttributeError — schemas/portfolio.py has no MarketPriceHistoryPoint.
        """
        point_type = portfolio_module.MarketPriceHistoryPoint

        assert set(point_type.model_fields) == {"date", "market_price", "currency", "estimated"}
        point = point_type(date=date(2024, 1, 10), market_price=D("10"), currency="USD")
        assert (point.date, point.market_price, point.currency, point.estimated) == (date(2024, 1, 10), D("10"), "USD", False)
        with pytest.raises(ValueError):
            point_type(date=date(2024, 1, 10), market_price=D("10"), currency="USD", lot_id=1)
        with pytest.raises(ValueError):
            point_type(date=date(2024, 1, 10), market_price=D("10"), currency="NOT-A-CODE")


class TestTheMarketPriceLineAtTheFloor:
    """get_lots_analysis on the rows of R13-SEC8-2 (``_sec8_analysis``: a lot opened on 1890-01-01, a close of 150 on
    5 Jan 1900, read on 10 Jan 1900), the market price line alone: in EUR no rate is asked, nothing reaches a database."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("date_from", [pytest.param(None, id="no-date_from"), pytest.param(date(1, 1, 1), id="date_from-day-one")])
    async def test_the_market_price_history_starts_at_the_floor(self, monkeypatch, date_from):
        """No point before 1900-01-01, and one on every day from it to 10 Jan 1900: on 1–4 Jan the 1890 BUY's 120 a unit,
        carried (a trade's mark: estimated); from 5 Jan the close, 150 (not estimated). The window starts at the floor, the
        price series does not: the BUY of 1890 still marks the floor.

        Today: ValueError — 'MARKET_PRICE_HISTORY' is not a valid LotAnalysisType.
        """
        response, _ = await _sec8_analysis(monkeypatch, date_from=date_from, analyses=[_MARKET_PRICE_HISTORY])

        line = [(point.date, point.market_price, point.estimated) for point in response.market_price_history]
        assert [day for day, _price, _estimated in line if day < _SEC8_FLOOR] == []
        assert line == [(day, D("120"), True) for day in _days(_SEC8_FLOOR, 4)] + [(day, D("150"), False) for day in _days(_SEC8_QUOTED, 6)]

    @pytest.mark.asyncio
    async def test_the_market_price_history_starts_on_the_first_mark_after_the_floor(self, monkeypatch):
        """The same rows, the lot opened by an ADJUSTMENT of 10 at a cost of 120 EUR a unit instead of the BUY — a cost,
        never a price —, so nothing marks a day before the close of 5 Jan 1900: no point before the floor, none on 1–4 Jan
        1900, and the first on 5 Jan, 150 (not estimated), then one a day to 10 Jan.

        Today: ValueError — 'MARKET_PRICE_HISTORY' is not a valid LotAnalysisType.
        """
        adjustment = _tx(1, tx_type=TransactionType.ADJUSTMENT, tx_date=_SEC8_OPENED, quantity=D("10"), amount=D("0"), currency=None, cost_basis_override=D("120"), cost_basis_currency="EUR")

        response, _ = await _sec8_analysis(monkeypatch, date_from=None, opening=adjustment, analyses=[_MARKET_PRICE_HISTORY])

        line = [(point.date, point.market_price, point.estimated) for point in response.market_price_history]
        assert line == [(day, D("150"), False) for day in _days(_SEC8_QUOTED, 6)]


# =========================================================================== #
# MF-E2 — short positions in the lots' performance history
# =========================================================================== #
#
# Workstream MF, lot E2. The developer's decision — option (b), convention (1) «gross exposure», D2 and D3 yes, E2-Q1 yes —
# «se i numeri vanno in negativo, bisogna mostrarli e comunicarli perché è la scelta dell'utente». After the cure,
# ``build_performance_history`` (lots/histories.py):
#
# * NAV of a day: Σ over the scope's open fragments, a LONG +q·p, a SHORT −q·p (p the day's converted mark). On a day at
#   cost a LONG its cost share, as today, and a SHORT minus its share of the opening proceeds — cumulative_proceeds · q /
#   original_quantity, converted at the lot's opening date (D3).
# * Flows: today's, plus, for every SHORT lot opened in the scope, +its proceeds (cumulative_proceeds at the opening rate)
#   on its opening date: money out of the position, like a long sale's proceeds. Without a rate the series stops from that
#   day (``invalid_external_flow_from``), as for the other flows.
# * Gross exposure of a day: Σ |value| of the open fragments.
# * TWRR compounds r_t = (NAV_t + CF_t − NAV_{t−1}) / exposure_{t−1}, 0 when that exposure is 0. ROI_t = (NAV_t + ΣCF≤t) /
#   capital_t, capital_t = max(0, −Σ long-leg flows ≤ t) + Σ short proceeds ≤ t (cumulative, E2-Q1), 0 when the capital
#   is 0. Short-leg flows are the opening proceeds and the buy-back costs (the closures of SHORT lots, by a BUY or by an
#   ADJUSTMENT-in with a cost); the rest of a BUY that covers a short and opens a long is long-leg. Both quantized as today.
# * No SHORT lot in the scope: exactly today's calculate_twrr_series / calculate_simple_roi_series, bit for bit.
#
# Today (HEAD b87d5d957, read 20/10/2026) a short's fragment counts +q·p, as if owned; a day at cost with a short open has
# no point; the opening sale is no flow, so a line starts on the buy-back: the worked example reads ROI −100% and TWRR
# −180% on its last day. Each docstring says what today's builder gives for its book.
#
# The expected values come from ``_e2_contract``: plain Decimal arithmetic on the contract, over figures each test reads
# off its book by hand — never from the module under test. Lots, fragments and closures come from the real engine (pure)
# except in the D3 double, which needs a state the engine never produces. Values are compared as Decimals (0 and 0.000000
# are one value), except in ``TestLongOnlyParity``, whose point is the exact representation.
#
# No scope sees a buy-back without its opening sale: a BUY covers only its own broker's short, and a shorted position never
# transfers — the engine refuses it (SHORT_TRANSFER_NOT_SUPPORTED, a FAILED analysis without performance history; pinned
# by test_financial/test_lots_failed_analysis_withholding.py::test_s4_transfer_issue_names_the_giving_leg[short] and
# test_financial_math/test_fifo_transfer_issue_names_the_giving_leg.py). That case does not exist, so it has no test.

_E2_PCT = D("0.000001")  # returns.py's _PREC_PCT, restated: the oracle reads nothing from the module under test


def _e2_contract(figures: list[tuple]) -> list[tuple[date, Decimal | None, Decimal | None]]:
    """(date, ROI, TWRR) of each day by the MF-E2 contract, in plain Decimal, independent of lots/histories.py.

    ``figures`` holds, for each day with a NAV, (day, NAV, flow, gross exposure, long-leg flow, short proceeds), read off
    the book by hand. ROI_t = (NAV_t + ΣCF≤t) / capital_t, capital_t = max(0, −Σ long-leg flows ≤ t) + Σ short proceeds ≤ t,
    0 when the capital is 0. TWRR compounds (NAV_t + CF_t − NAV_{t−1}) / exposure_{t−1}, 0 when that exposure is 0, and
    has no value on the first day. A day before the first flow has no point. Six places, half up, as returns.py rounds.
    """
    first_flow = min(row[0] for row in figures if D(row[2]) != 0)
    points: list[tuple[date, Decimal | None, Decimal | None]] = []
    compound, flows, long_leg, proceeds = D(1), D(0), D(0), D(0)
    previous: tuple[Decimal, Decimal] | None = None
    for day, nav, flow, exposure, long_leg_flow, short_proceeds in figures:
        nav, flow, exposure = D(nav), D(flow), D(exposure)
        flows += flow
        long_leg += D(long_leg_flow)
        proceeds += D(short_proceeds)
        capital = max(D(0), -long_leg) + proceeds
        roi = D(0) if capital == 0 else ((nav + flows) / capital).quantize(_E2_PCT, rounding=ROUND_HALF_UP)
        twrr = None
        if previous is not None:
            previous_nav, previous_exposure = previous
            compound *= 1 + (D(0) if previous_exposure == 0 else (nav + flow - previous_nav) / previous_exposure)
            twrr = (compound - 1).quantize(_E2_PCT, rounding=ROUND_HALF_UP)
        previous = (nav, exposure)
        points.append((day, roi, twrr) if day >= first_flow else (day, None, None))
    return points


def _e2_engine_book(rows: list[Transaction], shorting: dict[int, bool]) -> PerformanceSourceContext:
    """The performance context of ``rows`` as the engine replays them, report currency EUR, each broker's shorting as given."""
    result = run_fifo_lot_engine(rows, shorting, target_currency="EUR")
    assert result.analysis_status != "FAILED", f"precondition: the engine replays the book, got {result.issues}"
    return PerformanceSourceContext(
        transactions=rows,
        engine_result=result,
        lots_by_id={lot.lot_id: lot for lot in result.lots},
        fragments_by_lot=group_fragments(result.fragment_intervals),
        closures_by_lot=group_closures(result.closures),
        tx_by_id={row.id: row for row in rows},
    )


def _e2_history(context: PerformanceSourceContext, days: list[date], marks: list[str | None], *, scope: tuple[int, ...] = (1,), rates: dict | None = None, at_cost_until: date | None = None) -> list[tuple]:
    """(date, ROI, TWRR) of each day, as Decimals (None for no point); ``marks`` are the days' prices in EUR, None for none."""
    points = build_performance_history(
        scope_broker_ids=list(scope),
        history_dates=days,
        market_prices={day: None if mark is None else D(mark) for day, mark in zip(days, marks, strict=True)},
        asset_currency="EUR",
        fx_resolver=_resolver("EUR", rates),
        context=context,
        quote_base_quantity=1,
        at_cost_until=at_cost_until,
    )
    return [(point.date, point.roi, point.twrr) for point in points]


_E2_JAN = _days(date(2025, 1, 5), 4)  # the worked example: 5–8 Jan 2025
_E2_MAR = _days(date(2025, 3, 3), 5)  # two brokers: 3–7 Mar 2025
_E2_APR = _days(date(2025, 4, 7), 5)  # the flips: 7–11 Apr 2025
_E2_FX = _days(date(2025, 1, 5), 3)  # the USD short: 5–7 Jan 2025
_E2_FEB = _days(date(2025, 2, 3), 5)  # the short without a rate: 3–7 Feb 2025


class TestShortPositionsInThePerformanceHistory:
    """MF-E2: ``build_performance_history`` with SHORT lots in the scope (the contract is in the section's header)."""

    # -- the worked example (approved by the developer) ---------------------------------------------------------------

    def test_the_worked_example(self):
        """10 sold short at 100 on 5 Jan (proceeds 1 000), X at 90 on 6 Jan and 80 on 7 Jan, 10 bought back at 80 on 8 Jan
        (pays 800): a gain of 200. NAV −1 000, −900, −800, 0; flows +1 000 on 5 Jan (the opening sale) and −800 on 8 Jan
        (the buy-back, short-leg); exposure 1 000, 900, 800, 0; capital 1 000 every day (no long leg, 1 000 of proceeds).
        ROI 0, 10%, 20%, 20%; TWRR none on 5 Jan (the first day), 10%, 1.1 × 1.1111… − 1 = 22.2222%, and 22.2222% on 8 Jan
        ((0 − 800 + 800) / 800 = 0).

        Today (read 20/10/2026): no point on 5–7 Jan — the first flow is the buy-back — and on 8 Jan ROI −1 (−100%), TWRR −1.8
        (−180%): NAV +1 000, +900, +800, 0, the 800 a deposit, so 0.9 × 0.8889 × (1 + (0 − 800 − 800) / 800) − 1.
        """
        days = _E2_JAN
        rows = [_tx(1, tx_type=TransactionType.SELL, tx_date=days[0], quantity=D("-10"), amount=D("1000")), _tx(2, tx_date=days[3], quantity=D("10"), amount=D("-800"))]
        expected = _e2_contract([(days[0], -1000, 1000, 1000, 0, 1000), (days[1], -900, 0, 900, 0, 0), (days[2], -800, 0, 800, 0, 0), (days[3], 0, -800, 0, 0, 0)])
        assert expected == [(days[0], D("0"), None), (days[1], D("0.1"), D("0.1")), (days[2], D("0.2"), D("0.222222")), (days[3], D("0.2"), D("0.222222"))], "precondition: the oracle gives the approved figures"

        assert _e2_history(_e2_engine_book(rows, {1: True}), days, ["100", "90", "80", "80"]) == expected

    # -- a long and a short at two brokers ------------------------------------------------------------------------------

    @staticmethod
    def _two_brokers() -> PerformanceSourceContext:
        """Broker 1 (no shorting) buys 10 at 100 on 3 Mar; broker 2 (shorting) sells 5 short at 110 on 4 Mar (proceeds 550)
        and buys them back at 90 on 6 Mar (pays 450). X at 100, 110, 100, 90, 95 from 3 to 7 Mar."""
        days = _E2_MAR
        rows = [
            _tx(1, tx_date=days[0], quantity=D("10"), amount=D("-1000"), broker_id=1),
            _tx(2, tx_type=TransactionType.SELL, tx_date=days[1], quantity=D("-5"), amount=D("550"), broker_id=2),
            _tx(3, tx_date=days[3], quantity=D("5"), amount=D("-450"), broker_id=2),
        ]
        return _e2_engine_book(rows, {1: False, 2: True})

    @pytest.mark.parametrize(
        ("scope", "figures"),
        [
            pytest.param(
                (1, 2),
                [(_E2_MAR[0], 1000, -1000, 1000, -1000, 0), (_E2_MAR[1], 550, 550, 1650, 0, 550), (_E2_MAR[2], 500, 0, 1500, 0, 0), (_E2_MAR[3], 900, -450, 900, 0, 0), (_E2_MAR[4], 950, 0, 950, 0, 0)],
                id="scope-all",
            ),
            pytest.param(
                (1,),
                [(_E2_MAR[0], 1000, -1000, 1000, -1000, 0), (_E2_MAR[1], 1100, 0, 1100, 0, 0), (_E2_MAR[2], 1000, 0, 1000, 0, 0), (_E2_MAR[3], 900, 0, 900, 0, 0), (_E2_MAR[4], 950, 0, 950, 0, 0)],
                id="PARITY-the-long-broker-alone",
            ),
            pytest.param(
                (2,),
                [(_E2_MAR[0], 0, 0, 0, 0, 0), (_E2_MAR[1], -550, 550, 550, 0, 550), (_E2_MAR[2], -500, 0, 500, 0, 0), (_E2_MAR[3], 0, -450, 0, 0, 0), (_E2_MAR[4], 0, 0, 0, 0, 0)],
                id="the-short-broker-alone",
            ),
        ],
    )
    def test_a_long_and_a_short_at_two_brokers(self, scope, figures):
        """The book of ``_two_brokers`` read in three scopes; the replay holds both brokers' lots every time, as the service's
        performance re-run over the accessible brokers does.

        * Both brokers: NAV 1 000, 1 100 − 550, 1 000 − 500, 900, 950; exposure 1 000, 1 650, 1 500, 900, 950; flows −1 000
          (long-leg), +550 (short proceeds), −450 (the buy-back, short-leg); capital 1 000, then 1 550. ROI 0, 6.4516%,
          3.2258%, 0, 3.2258% (+50 on 1 550 on 7 Mar: −50 on the long, +100 on the short); TWRR —, 10%, 6.6667%, 3.1111%,
          8.8395%. Today: ROI 0, 65%, 50%, −37.931%, −34.4828%; TWRR —, 65%, 50%, −55%, −52.5% (the short read as owned).
        * The long broker alone — PARITY, green today and after: no SHORT lot in the scope (broker 2's lots are in the
          replay, out of the scope), so today's series: ROI = TWRR = 0, 10%, 0, −10%, −5%; TWRR none on 3 Mar.
        * The short broker alone: NAV 0 on 3 Mar (nothing open yet: TWRR's base for 4 Mar, exposure 0, so 0), then −550,
          −500, 0, 0; capital 550. ROI —, 0, 9.0909%, 18.1818%, 18.1818% (100 on 550); TWRR —, 0, 9.0909%, 20%, 20% (the
          6 Mar sub-period on the exposure of 5 Mar, 500). Today: no point until 6 Mar, then ROI −100% and TWRR −181.8182%
          on 6 and 7 Mar.
        """
        assert _e2_history(self._two_brokers(), _E2_MAR, ["100", "110", "100", "90", "95"], scope=scope) == _e2_contract(figures)

    # -- a SELL that closes a long and opens a short; a BUY that covers a short and opens a long -----------------------

    def test_a_sell_that_closes_a_long_and_opens_a_short_then_a_buy_that_covers_it_and_opens_a_long(self):
        """Broker 1 (shorting) buys 5 at 100 on 7 Apr; on 8 Apr sells 8 at 110 — 5 close the long (550, long-leg proceeds),
        3 open a short (330, short proceeds); on 10 Apr buys 5 at 100 — 3 cover the short (300, short-leg), 2 open a long
        (200, long-leg). X at 100, 110, 120, 100, 105 from 7 to 11 Apr.

        NAV 500, −330, −360, 200, 210; exposure 500, 330, 360, 200, 210; flows −500, +880, 0, −500, 0. Long leg −500, +50,
        +50, −150: capital 500, then max(0, −50) + 330 = 330, then 150 + 330 = 480. ROI 0, 15.1515%, 6.0606%, 16.6667%,
        18.75% (+50 on the first long, +30 on the short, +10 on the second long: 90 on 480); TWRR —, 10%, 0, 16.6667%, 22.5%
        (1.1 × (1 − 30/330) × (1 + 60/360) × 1.05).

        Today (read 20/10/2026): ROI 0, 0, 0 (the 550 out exceeds the 500 in: no capital), −55.5556%, −53.3333%; TWRR —, 76%,
        92%, −260%, −268%.
        """
        days = _E2_APR
        rows = [
            _tx(1, tx_date=days[0], quantity=D("5"), amount=D("-500")),
            _tx(2, tx_type=TransactionType.SELL, tx_date=days[1], quantity=D("-8"), amount=D("880")),
            _tx(3, tx_date=days[3], quantity=D("5"), amount=D("-500")),
        ]
        context = _e2_engine_book(rows, {1: True})
        lots = sorted((lot.lot_id, lot.direction, lot.original_quantity, lot.cumulative_proceeds) for lot in context.lots_by_id.values())
        assert lots == [(1, "LONG", D("5"), D("550")), (2, "SHORT", D("3"), D("330")), (3, "LONG", D("2"), D("0"))], "precondition: the SELL closes the long and opens a short, the BUY covers it and opens a long"
        figures = [(days[0], 500, -500, 500, -500, 0), (days[1], -330, 880, 330, 550, 330), (days[2], -360, 0, 360, 0, 0), (days[3], 200, -500, 200, -200, 0), (days[4], 210, 0, 210, 0, 0)]

        assert _e2_history(context, days, ["100", "110", "120", "100", "105"]) == _e2_contract(figures)

    # -- a short in another currency than the report ---------------------------------------------------------------------

    @staticmethod
    def _usd_short_rows() -> list[Transaction]:
        """10 sold short at 100 USD on 5 Jan (1 000 USD; USD→EUR 0.9 that day), bought back at 80 USD on 7 Jan (800 USD;
        1.0 that day)."""
        days = _E2_FX
        return [_tx(1, tx_type=TransactionType.SELL, tx_date=days[0], quantity=D("-10"), amount=D("1000"), currency="USD"), _tx(2, tx_date=days[2], quantity=D("10"), amount=D("-800"), currency="USD")]

    def test_a_short_sold_in_another_currency_converts_its_proceeds_at_its_opening_rate(self):
        """The USD short of ``_usd_short_rows``, the report in EUR, X marked 90, 85 and 80 EUR. The proceeds flow at the
        opening date's rate, 1 000 × 0.9 = 900 — not at the buy-back's, 1.0, nor unconverted —, the buy-back at its own,
        −800. NAV −900, −850, 0; capital 900. ROI 0, 5.5556%, 11.1111% (100 on 900); TWRR —, 5.5556%, 11.7647% (19/18 ×
        18/17 − 1).

        Today (read 20/10/2026): no point on 5–6 Jan, and on 7 Jan ROI −100%, TWRR −188.8889%.
        """
        days = _E2_FX
        rates = {("USD", days[0]): D("0.9"), ("USD", days[2]): D("1.0")}
        figures = [(days[0], -900, 900, 900, 0, 900), (days[1], -850, 0, 850, 0, 0), (days[2], 0, -800, 0, 0, 0)]

        assert _e2_history(_e2_engine_book(self._usd_short_rows(), {1: True}), days, ["90", "85", "80"], rates=rates) == _e2_contract(figures)

    def test_the_performance_history_asks_for_a_shorts_currency_on_its_opening_date(self):
        """``collect_performance_fx_needs`` for the USD short, no day at cost: (USD, 5 Jan) — the proceeds, at the opening
        rate — and (USD, 7 Jan) — the buy-back — are among the needs.

        Today (read 20/10/2026): (USD, 7 Jan) alone, for the BUY; the opening sale needs no rate.
        """
        rows = self._usd_short_rows()
        context = _e2_engine_book(rows, {1: True})
        resolver = _resolver("EUR")

        collect_performance_fx_needs(fx_resolver=resolver, analyses=[LotAnalysisType.PERFORMANCE_HISTORY], transactions=rows, closures=context.engine_result.closures, lots_by_id=context.lots_by_id, asset_currency="EUR", at_cost_until=None)

        assert {("USD", _E2_FX[0]), ("USD", _E2_FX[2])} - set(resolver._needs) == set()

    # -- a short whose proceeds have no rate ---------------------------------------------------------------------------

    def test_a_short_whose_proceeds_have_no_rate_stops_the_series_from_its_opening_day(self):
        """Broker 1 buys 10 at 100 EUR on 3 Feb; broker 2 (shorting) sells 5 short at 100 USD on 5 Feb, with no USD rate that
        day, and buys them back at 90 USD on 7 Feb (rate 1.0). Scope both, X at 100, 110, 100, 95, 90. The proceeds are
        unknown in EUR, so ROI and TWRR stop from 5 Feb, as for any flow without a rate; 3 and 4 Feb, the long alone, are the
        presence barrier: ROI 0 and 10%, TWRR — and 10%.

        Today (read 20/10/2026): the opening sale is no flow, so the series goes on: ROI 50%, 42.5%, −37.931% and TWRR 50%,
        42.5%, −55% on 5–7 Feb.
        """
        days = _E2_FEB
        rows = [
            _tx(1, tx_date=days[0], quantity=D("10"), amount=D("-1000"), broker_id=1),
            _tx(2, tx_type=TransactionType.SELL, tx_date=days[2], quantity=D("-5"), amount=D("500"), currency="USD", broker_id=2),
            _tx(3, tx_date=days[4], quantity=D("5"), amount=D("-450"), currency="USD", broker_id=2),
        ]
        expected = _e2_contract([(days[0], 1000, -1000, 1000, -1000, 0), (days[1], 1100, 0, 1100, 0, 0)]) + [(day, None, None) for day in days[2:]]

        assert _e2_history(_e2_engine_book(rows, {1: False, 2: True}), days, ["100", "110", "100", "95", "90"], scope=(1, 2), rates={("USD", days[4]): D("1.0")}) == expected

    # -- proceeds carried onto the first NAV keep their side (coordinator, 20/10: open point 1 of the reds) ---------------

    def test_a_shorts_proceeds_carried_onto_the_first_nav_stay_on_the_short_side(self):
        """10 sold short at 100 on 5 Jan, a day without a mark (a mark without a rate: no NAV), X at 90 on 6 Jan, 10 bought back
        at 80 on 7 Jan. The proceeds come before the first NAV, so they are carried onto it, 6 Jan — and stay the short side's:
        capital 1 000. 5 Jan no point; 6 Jan NAV −900, ROI (−900 + 1 000) / 1 000 = 10%, no TWRR (the first NAV); 7 Jan NAV 0,
        ROI 200 / 1 000 = 20%, TWRR (0 − 800 + 900) / 900 = 11.1111%. Merged into the long side, the carried +1 000 would leave
        no capital: ROI 0 on both days.

        Today (HEAD b87d5d957, read 20/10/2026): no point on 5–6 Jan, and on 7 Jan ROI −100%, TWRR −188.8889%.
        """
        days = _E2_JAN[:3]
        rows = [_tx(1, tx_type=TransactionType.SELL, tx_date=days[0], quantity=D("-10"), amount=D("1000")), _tx(2, tx_date=days[2], quantity=D("10"), amount=D("-800"))]
        expected = [(days[0], None, None), *_e2_contract([(days[1], -900, 1000, 900, 0, 1000), (days[2], 0, -800, 0, 0, 0)])]

        assert _e2_history(_e2_engine_book(rows, {1: True}), days, [None, "90", "80"]) == expected

    # -- an ADJUSTMENT-in that covers a short (coordinator, 20/10: open point 2 of the reds) --------------------------------
    #
    # The engine closes a short on an ADJUSTMENT-in as on a BUY (fifo/engine.py ``_apply_adjustment_in``, close_reason BUY,
    # at the ADJUSTMENT's cost basis). With a cost, that cost is the flow an ADJUSTMENT-in always was, and the part of it that
    # covers shorts is the short side's, like a BUY's buy-back. Without a cost it moves no money: no flow, and the debt is
    # gone — the quantity-correction reading.

    @staticmethod
    def _shorted_then_adjusted_in(cost: str | None) -> PerformanceSourceContext:
        """10 sold short at 100 on 5 Jan (proceeds 1 000); on 7 Jan an ADJUSTMENT +10, at a cost basis of ``cost`` EUR a unit
        or with none, as the app stores one: no amount, no currency of its own."""
        days = _E2_JAN[:3]
        adjustment = _tx(2, tx_type=TransactionType.ADJUSTMENT, tx_date=days[2], quantity=D("10"), amount=D("0"), currency=None, cost_basis_override=None if cost is None else D(cost), cost_basis_currency=None if cost is None else "EUR")
        context = _e2_engine_book([_tx(1, tx_type=TransactionType.SELL, tx_date=days[0], quantity=D("-10"), amount=D("1000")), adjustment], {1: True})
        closures = [(closure.lot_id, closure.transaction_id, closure.quantity, closure.close_reason) for closure in context.engine_result.closures]
        assert (closures, sorted(context.lots_by_id)) == ([(1, 2, D("10"), "BUY")], [1]), "precondition: the ADJUSTMENT closes the whole short and opens no lot"
        return context

    def test_an_adjustment_in_with_a_cost_that_covers_a_short_is_a_flow_of_the_short_side(self):
        """The ADJUSTMENT +10 at 80 of ``_shorted_then_adjusted_in``, X at 100, 90, 80. Its cost, 10 × 80 = 800, flows out on
        7 Jan and covers the short, so it is the short side's: the capital stays the 1 000 of proceeds. NAV −1 000, −900, 0;
        ROI 0, 10%, 20%; TWRR —, 10%, 22.2222% — the worked example with the ADJUSTMENT in place of the BUY. Counted on the
        long side, the 800 would join the capital: ROI 200 / 1 800 = 11.1111% on 7 Jan.

        Today (HEAD b87d5d957, read 20/10/2026): no point on 5–6 Jan — the first flow is the ADJUSTMENT's — and on 7 Jan ROI
        −100%, TWRR −180%.
        """
        days = _E2_JAN[:3]
        figures = [(days[0], -1000, 1000, 1000, 0, 1000), (days[1], -900, 0, 900, 0, 0), (days[2], 0, -800, 0, 0, 0)]

        assert _e2_history(self._shorted_then_adjusted_in("80"), days, ["100", "90", "80"]) == _e2_contract(figures)

    def test_an_adjustment_in_without_a_cost_that_covers_a_short_moves_no_money_and_clears_the_debt(self):
        """The ADJUSTMENT +10 of ``_shorted_then_adjusted_in`` without a cost, X at 100, 90, 80. It moves no money — no flow on
        7 Jan — and the short is closed, so the debt is gone: NAV −1 000, −900, 0, the one flow the proceeds, capital 1 000.
        ROI 0, 10%, (0 + 1 000) / 1 000 = 100%; TWRR —, 10%, 1.1 × (1 + 900 / 900) − 1 = 120%. A flow for the ADJUSTMENT would
        move the 7 Jan ROI off 100%; a debt left open (NAV −800) would read 20%.

        Today (HEAD b87d5d957, read 20/10/2026): no point at all — no flow, the short's sale being none.
        """
        days = _E2_JAN[:3]
        figures = [(days[0], -1000, 1000, 1000, 0, 1000), (days[1], -900, 0, 900, 0, 0), (days[2], 0, 0, 0, 0, 0)]
        expected = _e2_contract(figures)
        assert expected[2] == (days[2], D("1"), D("1.2")), "precondition: the oracle reads the debt cleared at no cost as the whole proceeds kept"

        assert _e2_history(self._shorted_then_adjusted_in(None), days, ["100", "90", "80"]) == expected

    # -- a flow on a day without NAV, after the first: on the next NAV day, in the gain and the capital (MF-E2b) --------
    #
    # Developer's decision A (coordinator, 20/10 10:39): «Quando il calcolo salta un giorno senza valore, i flussi di quel
    # giorno passano al primo giorno calcolabile.» ``returns.py`` counts every flow on the first snapshot on or after it, and
    # with a short in the scope ``_committed_capital_by_date`` reads the same moved flows: gain and capital never disagree.
    # (Option (a) of 20/10 left such a flow out of both; before it the capital counted it and the gain did not.)

    @staticmethod
    def _gap_book(shape: str, mark: str) -> tuple[list[Transaction], dict[int, bool], tuple[int, ...], list[tuple]]:
        """(rows, shorting, scope, figures of the NAV days 5 and 7 Jan, the 6 Jan flows on 7 Jan): X at 100 on 5 Jan and at
        ``mark`` on 7 Jan, no NAV on 6 Jan, the flow day."""
        days, price = _E2_JAN[:3], D(mark)
        if shape == "S1":
            rows = [_tx(1, tx_date=days[0], quantity=D("10"), amount=D("-1000")), _tx(2, tx_type=TransactionType.SELL, tx_date=days[1], quantity=D("-15"), amount=D("1500"))]
            return rows, {1: True}, (1,), [(days[0], 1000, -1000, 1000, -1000, 0), (days[2], -5 * price, 1500, 5 * price, 1000, 500)]
        rows = [_tx(1, tx_type=TransactionType.SELL, tx_date=days[0], quantity=D("-10"), amount=D("1000"), broker_id=1), _tx(2, tx_date=days[1], quantity=D("5"), amount=D("-500"), broker_id=2)]
        return rows, {1: True, 2: False}, (1, 2), [(days[0], -1000, 1000, 1000, 0, 1000), (days[2], -5 * price, -500, 15 * price, -500, 0)]

    @pytest.mark.parametrize(
        ("shape", "mark", "roi", "twrr"),
        [
            pytest.param("S1", "100", "0", "0", id="S1-a-sale-closes-a-long-and-opens-a-short-flat"),
            pytest.param("S2", "100", "0", "0", id="S2-a-long-bought-beside-a-short-flat"),
            pytest.param("S1", "90", "0.1", "0.05", id="S1-a-sale-closes-a-long-and-opens-a-short-at-90"),
            pytest.param("S2", "90", "0.033333", "0.05", id="S2-a-long-bought-beside-a-short-at-90"),
        ],
    )
    def test_a_flow_on_a_day_without_nav_enters_the_gain_and_the_capital_on_the_next_nav_day(self, shape, mark, roi, twrr):
        """X at 100 on 5 Jan and at ``mark`` on 7 Jan, no NAV on 6 Jan (a mark without a rate), the day the flow falls on.

        * S1, one broker: 10 bought at 100 on 5 Jan; on 6 Jan a SELL of 15 at 100 closes them (+1 000, the long side) and
          opens a short of 5 (+500 of proceeds). NAV 1 000, then −5 × ``mark`` on 7 Jan.
        * S2, two brokers: 10 sold short at 100 on 5 Jan at broker 1; on 6 Jan broker 2 buys 5 at 100 (−500, the long side).
          NAV −1 000, then −10 × ``mark`` + 5 × ``mark`` = −5 × ``mark`` on 7 Jan.

        The 6 Jan flows count on 7 Jan, in the gain and in the capital: the oracle puts them on 7 Jan's figures. Flat, the
        prices did not move and neither do the returns: 0 and 0 (S1 capital 500, the proceeds; S2 capital 1 500). At 90 the
        short gains 10 a unit: S1 ROI 50 / 500 = 10%, TWRR (−450 + 1 500 − 1 000) / 1 000 = 5%; S2 ROI 50 / 1 500 = 3.3333%
        (the long loses 50, the short gains 100), TWRR (−450 − 500 + 1 000) / 1 000 = 5%. The at-90 cases are what tells a
        capital that reads the moved flows from one still built from the snapshot days' alone (S1 5%, S2 5%).

        Before MF-E2b (HEAD 2e23bd03c, option (a)) this test was ``test_a_flow_on_a_day_without_nav_is_left_out_of_the_capital_as_of_the_gain``,
        flat only, expecting S1 −150% / −150% and S2 50% / 50% (the 6 Jan flows in neither). Today's values at 90: S1
        −145% / −145%, S2 55% / 55%.
        """
        days = _E2_JAN[:3]
        rows, shorting, scope, figures = self._gap_book(shape, mark)
        contract = _e2_contract(figures)
        assert (contract[1][1], contract[1][2]) == (D(roi), D(twrr)), "precondition: the oracle gives the stated figures"
        expected = [contract[0], (days[1], None, None), contract[1]]

        assert _e2_history(_e2_engine_book(rows, shorting), days, ["100", None, mark], scope=scope) == expected

    # -- D3: a day at cost with a short open, the share of its proceeds at its opening rate ------------------------------

    def test_d3_a_day_at_cost_reads_a_short_at_its_share_of_the_proceeds_at_its_opening_rate(self):
        """A contract double (``TestPerformanceHistoryAtCost``'s days, 4–8 Mar 2024, no mark at all, at cost until 8 Mar): the
        10 adjusted in at 1 000 EUR on d0; a USD SHORT lot of 10 sold on d1 for 1 000 USD (USD→EUR 0.9 on d1, 1.0 on d2, 1.1
        on d3, 1.2 on d4), 6 of it bought back on d3 at 100 USD (660 EUR). On a day at cost the open short counts −1 000 USD ×
        open / 10 at d1's 0.9: −900 on d1–d2, −360 on d3–d4 — never at the day's rate. NAV 1 000, 100, 100, 640, 640;
        exposure 1 000, 1 900, 1 900, 1 360, 1 360; flows −1 000, +900, 0, −660, 0; capital 1 900 from d1. ROI and TWRR 0
        until d2, then −6.3158% (−120 on 1 900: the 6 cost 660 against the 540 of proceeds they held).

        The double's cost, 800 USD, differs from its proceeds only so that the share reads the proceeds: the engine sets a
        short's cost to its proceeds, and in the service a day at cost has no trade (a SELL or a BUY is an observation), so
        none of this reaches it — the contract's D3 formula, stated where it can be told apart.

        Today (read 20/10/2026): (d0, 0, —), then no point on d1–d4 — a short open on a day at cost leaves it without NAV.
        """
        at_cost = TestPerformanceHistoryAtCost
        days = at_cost._DAYS[:5]
        long_lot = at_cost._long_lot(1, day=days[0])
        short_lot = _lot(2, direction="SHORT", opening_date=days[1], original_quantity=D("10"), opening_unit_price=D("100"), original_cost=D("800"), currency="USD", open_quantity=D("4"), realized_quantity=D("6"), cumulative_proceeds=D("1000"))
        fragments = [
            at_cost._open_fragment(1, day=days[0]),
            _fragment(2, fragment_id="frag-2", direction="SHORT", quantity=D("10"), unit_price=D("100"), start_date=days[1], end_date=days[3]),
            _fragment(2, fragment_id="frag-2b", direction="SHORT", quantity=D("4"), unit_price=D("100"), start_date=days[3]),
        ]
        buy_back = _closure(2, transaction_id=3, quantity=D("6"), close_date=days[3], close_reason="BUY", fragment_id="frag-2", open_unit_price=D("100"), close_unit_price=D("100"), realized_pnl=D("0"), proceeds=D("0"), close_currency="USD")
        rows = [
            at_cost._adjusted_in(1, day=days[0]),
            _tx(2, tx_type=TransactionType.SELL, tx_date=days[1], quantity=D("-10"), amount=D("1000"), currency="USD"),
            _tx(3, tx_date=days[3], quantity=D("6"), amount=D("-600"), currency="USD"),
        ]
        context = _perf_context(
            transactions=rows,
            engine_result=_engine_result(lots=[long_lot, short_lot], fragments=fragments, closures=[buy_back]),
            lots_by_id={1: long_lot, 2: short_lot},
            fragments_by_lot=group_fragments(fragments),
            closures_by_lot={2: [buy_back]},
        )
        rates = {("USD", days[1]): D("0.9"), ("USD", days[2]): D("1.0"), ("USD", days[3]): D("1.1"), ("USD", days[4]): D("1.2")}
        figures = [(days[0], 1000, -1000, 1000, -1000, 0), (days[1], 100, 900, 1900, 0, 900), (days[2], 100, 0, 1900, 0, 0), (days[3], 640, -660, 1360, 0, 0), (days[4], 640, 0, 1360, 0, 0)]

        assert _e2_history(context, days, [None] * 5, rates=rates, at_cost_until=days[4]) == _e2_contract(figures)


# --------------------------------------------------------------------------- #
# MF-E2 parity: a long-only book keeps today's series, bit for bit
# --------------------------------------------------------------------------- #

_PARITY_DAYS = _days(date(2024, 5, 6), 12)  # 6–17 May 2024


def _long_only_book(seed: int) -> dict:
    """A long-only book drawn from ``seed`` (``random.Random``, stable across Python 3 versions), over ``_PARITY_DAYS``.

    Brokers 1 and 2, neither shorting. 0, 2 or 3 days at cost first (no mark, an ADJUSTMENT-in with a cost on the first);
    then a mark a day, moving −5% … +6%, missing (None, after the cut) on about one day in eight; BUYs (one in five in
    USD, 0.9 EUR a USD) and SELLs that partly close what the broker holds; on about one book in three a day without a USD
    rate, which voids the series when a USD BUY falls on it. The scope is broker 1, or both.
    """
    rng = random.Random(seed)
    days = _PARITY_DAYS
    at_cost_days = rng.choice((0, 0, 2, 3))
    no_rate_day = days[rng.randint(4, len(days) - 1)] if rng.random() < 0.35 else None
    marks: dict[date, Decimal | None] = {}
    price = D(rng.randint(80, 120))
    for index, day in enumerate(days):
        if index < at_cost_days:
            marks[day] = None
            continue
        price = (price * D(rng.choice(("0.95", "0.98", "1", "1.03", "1.06")))).quantize(D("0.01"))
        marks[day] = None if index > at_cost_days and rng.random() < 0.12 else price
    rows: list[Transaction] = []
    held = {1: D(0), 2: D(0)}
    for index, day in enumerate(days):
        broker_id = rng.choice((1, 2))
        if index < at_cost_days:
            if index == 0:
                quantity = D(rng.randint(5, 15))
                rows.append(_tx(len(rows) + 1, tx_type=TransactionType.ADJUSTMENT, tx_date=day, quantity=quantity, amount=D(0), currency=None, broker_id=broker_id, cost_basis_override=D(rng.randint(90, 110)), cost_basis_currency="EUR"))
                held[broker_id] += quantity
            continue
        roll = rng.random()
        unit_price = marks[day] if marks[day] is not None else price
        if index == 0 or roll < 0.35 or held[broker_id] == 0 and roll < 0.6:
            quantity = D(rng.randint(1, 10))
            currency = "USD" if day == no_rate_day or rng.random() < 0.2 else "EUR"
            native = unit_price if currency == "EUR" else (unit_price / D("0.9")).quantize(D("0.01"))
            rows.append(_tx(len(rows) + 1, tx_date=day, quantity=quantity, amount=-(quantity * native), currency=currency, broker_id=broker_id))
            held[broker_id] += quantity
        elif roll < 0.6:
            quantity = D(rng.randint(1, int(held[broker_id])))
            rows.append(_tx(len(rows) + 1, tx_type=TransactionType.SELL, tx_date=day, quantity=-quantity, amount=quantity * unit_price, currency="EUR", broker_id=broker_id))
            held[broker_id] -= quantity
    rates = {("USD", day): D("0.9") for day in days if day != no_rate_day}
    scope = rng.choice(((1,), (1, 2)))
    return {"rows": rows, "marks": marks, "at_cost_until": days[at_cost_days - 1] if at_cost_days else None, "rates": rates, "scope": scope}


# Each seed's series (HEAD b87d5d957, read 20/10/2026; seeds 3, 4, 7, 10 and 47 moved by MF-E2b): one "ROI|TWRR" per day of
# ``_PARITY_DAYS``, each the str() of the Decimal the builder returned, "-" for None.
#
# MF-E2b (developer's decision A, 20/10): each of seeds 3, 4, 7, 10 and 47 has a trade on a day without NAV after the first
# (seed 3 a BUY on 8 May, 4 a SELL on 7 May, 7 a SELL on 12 May, 10 a SELL on 9 May and a BUY on 12 May, 47 a BUY on 12
# May), which returns.py dropped and now counts on the next NAV day; every other seed has none and keeps its series bit for
# bit. Before MF-E2b they read:
#   3: "-0.000023|- 0.059976|0.060000 -|- 3.223161|0.814750 3.349937|0.869227 3.262723|0.831750 0.751365|0.886614 0.856454|0.999818 0.479838|0.959830 0.545087|0.920614 0.637866|1.035943 0.555965|0.934136"
#   4: "0.000000|- -|- -0.263499|-0.315065 -0.186989|-0.315065 -0.227609|-0.349286 -0.205297|-0.310260 -0.298707|-0.324026 -0.274634|-0.324028 -0.310867|-0.357795 -0.802367|-0.357795 -|- -|-"
#   7: "0.000000|- 0.000000|0.000000 -0.076389|-0.076389 -0.150979|-0.122593 -0.116534|-0.166466 -0.183842|-0.208134 -|- -0.493863|-0.717903 -|- -|- -0.458448|-0.698164 -0.546659|-0.704210"
#   10: "0.000000|- -0.014342|-0.019964 0.011804|0.009437 -|- -0.035387|-0.037644 -0.054716|-0.056927 -|- -0.080648|-0.021416 -0.015747|0.007985 -0.013806|0.007985 -0.013806|0.007985 -0.033515|-0.012160"
#   47: "0.000000|- 0.000000|0.000000 0.084112|0.084112 0.069123|0.084110 0.380625|0.116634 0.109780|0.150091 -|- 0.447963|0.500558 0.375577|0.425543 0.375577|0.425543 2.210144|0.397007 0|0.480870"
_TODAY_LONG_ONLY_SERIES = {
    0: "0.000000|- 0.000000|0.000000 0.000000|0.000000 0.082796|0.082796 0.082796|0.082796 0.115269|0.115269 0.115269|0.115269 0.115269|0.115269 0.093011|0.093011 0.093011|0.093011 0.038387|0.038387 0.017823|0.038387",
    1: "-|- -|- -|- -|- -|- 0.000000|0.000000 -0.032694|-0.049949 -0.032694|-0.049949 -0.051991|-0.068902 -0.099435|-0.115499 -|- -|-",
    2: "0.000000|- 0.000000|0.000000 -|- 0.038778|0.038778 0.069889|0.069889 0.134111|0.134111 0.085147|0.202124 0.150242|0.274236 0.092770|0.210568 0.130920|0.210568 0.130920|0.210568 0.164864|0.246902",
    3: "-0.000023|- 0.059976|0.060000 -|- 0.017459|0.018341 0.048003|0.048911 0.026991|0.027880 0.031281|0.058667 0.093162|0.122191 0.050333|0.099752 0.033448|0.077746 0.095504|0.142463 0.040724|0.085334",
    4: "0.000000|- -|- -0.048968|-0.045343 -0.032040|-0.045343 -0.080401|-0.093040 -0.029334|-0.038646 -0.071323|-0.057833 -0.063908|-0.057836 -0.110667|-0.104899 -0.528291|-0.104899 -|- -|-",
    5: "0.000000|- 0.000000|0.000000 -0.013271|-0.015138 0.016327|0.014404 -0.003987|-0.005872 -|- 0.003586|0.003486 0.033681|0.033578 0.061831|0.095596 0.111456|0.073670 0.050187|0.052202 0.081686|0.083761",
    6: "0.000000|- -0.050000|-0.050000 0.007018|0.007018 0.007018|0.007018 -0.043311|-0.043311 -0.062500|-0.062500 -0.034430|-0.034430 0.023465|0.023465 0.002961|0.002961 0.001725|0.002961 0.095733|0.063158 0.149743|0.095066",
    7: "0.000000|- 0.000000|0.000000 -0.076389|-0.076389 -0.150979|-0.122593 -0.116534|-0.166466 -0.183842|-0.208134 -|- -0.171377|-0.175622 -|- -|- -0.113396|-0.117939 -0.170706|-0.135607",
    8: "-|- -|- 0.000000|0.000000 0.059964|0.059964 0.012590|0.006955 0.043005|0.037201 0.105636|0.099484 -|- 0.116021|0.109811 0.116021|0.109811 0.149509|0.143113 0.183951|0.177363",
    9: "0.000000|- 0.000000|0.000000 0.000000|0.000000 0.022151|0.022151 0.001720|0.001720 -0.048387|-0.048387 -0.019785|-0.019785 -0.068817|-0.068817 -0.012903|-0.012903 0.016667|0.016667 0.047204|0.047204 0.078602|0.078602",
    10: "0.000000|- -0.014342|-0.019964 0.011804|0.009437 -|- 0.020764|0.017236 0.000310|-0.003146 -|- -0.080648|-0.023620 -0.015747|0.005715 -0.013806|0.005715 -0.013806|0.005715 -0.033515|-0.014385",
    11: "0.000000|- 0.000000|0.000000 0.000000|0.000000 0.182426|0.247444 0.253411|0.322333 0.228345|0.295889 0.302069|0.373667 0.380216|0.456111 0.311232|0.383333 -|- 0.220762|0.287889 0.257413|0.326556",
    12: "0.000000|- 0.000000|0.000000 0.000000|0.000000 -0.118158|-0.135189 -0.088267|-0.178396 -0.060944|-0.153774 -0.106047|-0.128396 -0.052443|-0.076132 -0.128851|-0.122358 -0.146268|-0.139906 -0.048886|-0.139906 -|-",
    13: "-|- -|- 0.000000|0.000000 -0.019974|-0.019974 -0.039622|-0.039622 0.008456|0.018020 -|- -0.053504|-0.002388 0.001851|0.057425 0.001851|0.057425 -0.048236|0.004559 -0.048236|0.004559",
    14: "-|- -|- -|- 0.000026|0.000000 0.030011|0.029984 -0.021454|-0.021480 -0.021454|-0.021480 -0.021454|-0.021480 0.037288|0.037261 0.072850|0.099521 0.072850|0.099521 0.019212|0.044549",
    15: "0.000000|- -|- -0.081729|-0.069048 -0.081729|-0.069048 -|- -|- -|- -|- -|- -|- -|- -|-",
    20: "0.000000|- -|- 0.009434|0.009434 -0.050776|-0.041038 -0.022295|-0.012264 0.007027|0.017358 -0.013143|-0.003019 -0.013143|-0.003019 -0.042518|-0.052830 -0.013812|-0.024434 -0.094330|-0.043962 -0.139640|-0.091792",
    33: "0.000000|- 0.059954|0.059954 0.038735|0.038735 0.101091|0.101091 0|0.101091 0.017628|0.101091 0.012528|0.101091 -0.038094|0.046041 -0.029883|0.046038 -0.045665|-0.006273 -0.017010|0.023565 -0.033450|0.023565",
    36: "0.000000|- 0.000000|0.000000 -0.058010|-0.121698 -0.078012|-0.165660 -|- -|- -|- -|- -|- -|- -|- -|-",
    47: "0.000000|- 0.000000|0.000000 0.084112|0.084112 0.069123|0.084110 0.380625|0.116634 0.109780|0.150091 -|- 0.066843|0.130341 0.013509|0.073833 0.013509|0.073833 -0.017874|0.052338 0.134283|0.115510",
}


class TestLongOnlyParity:
    """MF-E2: with no SHORT lot in the scope the performance history is today's, bit for bit — green today, green after.

    Seeded long-only books (``_long_only_book``) through the real engine: BUYs, SELLs that partly close, days at cost,
    missing marks, USD flows, a flow without a rate (seeds 4, 15 and 36 stop on it), scope one broker or both; seed 33
    takes more out than it puts in on one day, where today's ROI is the bare ``0`` of calculate_simple_roi (no capital)
    and not ``0.000000`` (seed 47 did too until MF-E2b counted its gap-day BUY); seeds 3, 4, 7, 10 and 47 trade on a day
    without NAV, a flow that counts on the next NAV day since MF-E2b (their literals moved then; the old ones are in the
    comment above ``_TODAY_LONG_ONLY_SERIES``). Each book's series is compared, as the exact str() of every ROI and TWRR — "0" and
    "0.000000" told apart —, with the literals today's builder gave (``_TODAY_LONG_ONLY_SERIES``).

    Why pinned literals. A test may not read git, so today's function cannot be loaded beside the cured one. Checking that
    a long-only book still goes through calculate_twrr_series / calculate_simple_roi_series would say which functions are
    called, not that the NAVs and flows handed to them are unchanged; the literals pin the whole output — NAV, flows, the
    line's start, the invalidation, the quantization. The wider comparison, the cured builder against a frozen copy of
    today's over thousands of seeds, is a one-off run outside the suite.
    """

    @pytest.mark.parametrize("seed", sorted(_TODAY_LONG_ONLY_SERIES))
    def test_a_long_only_book_keeps_todays_series(self, seed):
        book = _long_only_book(seed)
        result = run_fifo_lot_engine(book["rows"], {1: False, 2: False}, target_currency="EUR")
        assert [lot.lot_id for lot in result.lots if lot.direction != "LONG"] == [] and result.analysis_status != "FAILED", "precondition: a long-only book the engine replays"
        context = PerformanceSourceContext(
            transactions=book["rows"],
            engine_result=result,
            lots_by_id={lot.lot_id: lot for lot in result.lots},
            fragments_by_lot=group_fragments(result.fragment_intervals),
            closures_by_lot=group_closures(result.closures),
            tx_by_id={row.id: row for row in book["rows"]},
        )

        points = build_performance_history(
            scope_broker_ids=list(book["scope"]),
            history_dates=_PARITY_DAYS,
            market_prices=book["marks"],
            asset_currency="EUR",
            fx_resolver=_resolver("EUR", book["rates"]),
            context=context,
            quote_base_quantity=1,
            at_cost_until=book["at_cost_until"],
        )

        assert " ".join(f"{'-' if point.roi is None else point.roi}|{'-' if point.twrr is None else point.twrr}" for point in points) == _TODAY_LONG_ONLY_SERIES[seed]


# --------------------------------------------------------------------------- #
# MF-E2b — a long-only trade on a day without NAV
# --------------------------------------------------------------------------- #


class TestGapFlowsInThePerformanceHistory:
    """MF-E2b (developer's decision A, coordinator 20/10 10:39) on a long-only book: the flow of a day without NAV counts on
    the next NAV day (``returns.py``), so the units it bought or sold no longer read as a gain or a loss. The rule itself is
    pinned in ``test_financial_math/test_returns_gap_flows.py``."""

    @pytest.mark.parametrize(
        ("trade", "quantity", "amount", "figures_on_jan_7"),
        [
            pytest.param("BUY", "5", "-500", (1500, -500, 1500, -500, 0), id="L1-a-second-buy"),
            pytest.param("SELL", "-5", "500", (500, 500, 500, 500, 0), id="L1-a-sale"),
        ],
    )
    def test_a_long_only_trade_on_a_day_without_nav_moves_no_return(self, trade, quantity, amount, figures_on_jan_7):
        """10 bought at 100 on 5 Jan (NAV 1 000); on 6 Jan, a day without NAV (a mark without a rate), 5 more bought at 100
        (−500) or 5 sold at 100 (+500); X at 100 on 7 Jan (NAV 1 500 or 500). The 6 Jan flow counts on 7 Jan: ROI 0 on a
        capital of 1 500 or 500; TWRR (1 500 − 500 − 1 000) / 1 000 = 0, or (500 + 500 − 1 000) / 1 000 = 0.

        Today (HEAD 2e23bd03c): the flow is dropped while its units are in the NAV — the BUY reads ROI +50% and TWRR +50%,
        the SELL −50% and −50% on 7 Jan.
        """
        days = _E2_JAN[:3]
        rows = [_tx(1, tx_date=days[0], quantity=D("10"), amount=D("-1000")), _tx(2, tx_type=TransactionType[trade], tx_date=days[1], quantity=D(quantity), amount=D(amount))]
        contract = _e2_contract([(days[0], 1000, -1000, 1000, -1000, 0), (days[2], *figures_on_jan_7)])
        assert (contract[1][1], contract[1][2]) == (D("0"), D("0")), "precondition: the oracle gives the stated figures"

        assert _e2_history(_e2_engine_book(rows, {1: False}), days, ["100", None, "100"]) == [contract[0], (days[1], None, None), contract[1]]
