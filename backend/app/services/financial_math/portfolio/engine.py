"""Portfolio calculation engine: loads the data of a scope, runs the classifier and the daily-state builder, and caches the result."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import and_, func, or_, select

from backend.app.db.models import Asset, BrokerUserAccess, FxConversionRoute, FxRate, PriceHistory, Transaction, TransactionType
from backend.app.schemas.common import Currency as CurrencySchema
from backend.app.services.accounts.settings_service import get_effective_base_currency
from backend.app.services.financial_math.average_cost import (
    compute_average_costs,
)
from backend.app.services.financial_math.native_cash import cash_movement_from_transaction, compute_native_cash, effective_share
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.derived_views import build_cost_positions
from backend.app.services.financial_math.portfolio.models import ClassifiedTransaction, InTransitInterval, PortfolioCalculationResult, SplitHistory, SplitRecord
from backend.app.services.financial_math.price_marks import AssetPriceSeries, build_asset_price_series
from backend.app.services.financial_math.splits import is_valid_split_ratio, load_split_links
from backend.app.services.fx.conversion import convert_bulk
from backend.app.utils.datetime_utils import latest_range_end
from backend.app.utils.runtime.cache import get_ttl_cache

logger = structlog.get_logger(__name__)


# Portfolio engine blob cache: stores PortfolioCalculationResult keyed by
# (user, brokers, currency, fingerprints). Range-aware: can be sliced or extended.
_portfolio_blob_cache = get_ttl_cache("portfolio_blob", maxsize=30, ttl=86400)  # 24h


# =============================================================================
# PORTFOLIO CALCULATION ENGINE — Async orchestrator
# =============================================================================


def compute_tx_fingerprint(transactions: list[Transaction]) -> str:
    """Compute a hash fingerprint over transaction IDs and updated_at timestamps.

    Any transaction insert, update, or delete changes this fingerprint,
    automatically invalidating cached portfolio results.
    """
    h = hashlib.md5(usedforsecurity=False)
    for tx in transactions:
        h.update(f"{tx.id}:{tx.updated_at.isoformat()}".encode())
    return h.hexdigest()


async def compute_portfolio_fx_cache_identity(
    db,
    scope_broker_ids: set[int],
    target_currency: str,
    date_to: date_type,
) -> str:
    """Fingerprint all FX data/config that can affect a portfolio scope.

    This is the shared identity contract for both portfolio cache layers.
    Dependencies are limited to cash and cost-basis currencies present in
    scoped transactions, held assets, and their price history, paired with the
    target currency.
    """
    if not scope_broker_ids:
        return "no_fx"

    tx_rows = (
        await db.execute(
            select(
                Transaction.currency,
                Transaction.cost_basis_currency,
                Transaction.asset_id,
                Transaction.quantity,
            ).where(Transaction.broker_id.in_(scope_broker_ids))
        )
    ).all()
    source_currencies = {currency for cash_currency, cost_basis_currency, _, _ in tx_rows for currency in (cash_currency, cost_basis_currency) if currency}
    held_asset_ids = {asset_id for _, _, asset_id, quantity in tx_rows if asset_id is not None and quantity and quantity != 0}

    if held_asset_ids:
        asset_currency_rows = (await db.execute(select(Asset.currency).where(Asset.id.in_(held_asset_ids)).distinct())).scalars()
        source_currencies.update(currency for currency in asset_currency_rows if currency)

        price_currency_rows = (await db.execute(select(PriceHistory.currency).where(PriceHistory.asset_id.in_(held_asset_ids)).where(PriceHistory.date <= date_to).distinct())).scalars()
        source_currencies.update(currency for currency in price_currency_rows if currency)

    normalized_target = target_currency.strip().upper()
    pairs = sorted({tuple(sorted((currency.strip().upper(), normalized_target))) for currency in source_currencies if currency.strip().upper() != normalized_target})
    if not pairs:
        return "no_fx"

    pair_conditions = [and_(FxRate.base == base, FxRate.quote == quote) for base, quote in pairs]
    rate_rows = (await db.execute(select(FxRate).where(or_(*pair_conditions)).where(FxRate.date <= date_to).order_by(FxRate.base, FxRate.quote, FxRate.date, FxRate.id))).scalars()

    route_conditions = [and_(FxConversionRoute.base == base, FxConversionRoute.quote == quote) for base, quote in pairs]
    route_rows = (await db.execute(select(FxConversionRoute).where(or_(*route_conditions)).order_by(FxConversionRoute.base, FxConversionRoute.quote, FxConversionRoute.priority, FxConversionRoute.id))).scalars()

    payload = {
        "pairs": pairs,
        "rates": [
            (
                rate.base,
                rate.quote,
                rate.date.isoformat(),
                str(rate.rate),
                rate.source,
                rate.fetched_at.isoformat(),
            )
            for rate in rate_rows
        ],
        "routes": [
            (
                route.base,
                route.quote,
                route.priority,
                route.parsed_steps,
                route.updated_at.isoformat(),
            )
            for route in route_rows
        ],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


class PortfolioCalculationEngine:
    """Async orchestrator that loads data from DB and runs the calculation pipeline.

    Usage:
        engine = PortfolioCalculationEngine(db_session)
        result = await engine.calculate(user_id, broker_ids, date_from, date_to, currency)
        views = DerivedViewsBuilder(result.daily_states, result.target_currency)
    """

    def __init__(self, db) -> None:
        """Initialize with an async DB session."""
        self.db = db

    async def calculate(  # noqa: C901 — TODO(P2-refactor): long pipeline orchestrator; extract stage helpers
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency: str | None = None,
        include_candles: bool = False,
        include_acquisition_funding: bool = False,
        period_start: date_type | None = None,
    ) -> PortfolioCalculationResult:
        """Run the full portfolio calculation pipeline.

        The cost of every position comes from one compute_average_costs call for the whole
        scope (financial_math.average_cost) — historical cost in the target currency, each
        acquisition converted at its own date — that the daily replay then follows.

        ``include_candles`` (G1b, default False) additionally resolves each held asset's
        daily OHLC and composes the synthetic total-P&L candle (plan §4.3) — kept opt-in
        per plan §4.1 so ordinary report generation never pays for it.

        ``include_acquisition_funding`` (batch 2, default False) additionally surfaces
        the engine's existing per-BUY K/R-pool draw as a daily new-vs-reinvested output
        (see AcquisitionFundingContribution) — kept opt-in for consistency, though the
        extra cost is negligible (pure bookkeeping capture, no new data resolution).

        ``period_start`` (MF-A) names the day whose end ``position_states_start`` is taken at — the start of the
        caller's period while the states run from ``date_from`` (t=0 for the Dashboard). Without it the snapshot is
        ``date_from``'s. It is part of the blob-cache key, so a cached run never answers with another day's
        snapshot.
        """
        # ── 1. Resolve target currency ──
        if target_currency is None:
            target_currency = await get_effective_base_currency(self.db, user_id)

        # ── 2. Resolve scope ──
        all_access_stmt = select(BrokerUserAccess).where(BrokerUserAccess.user_id == user_id)
        all_access_result = await self.db.execute(all_access_stmt)
        all_accesses = list(all_access_result.scalars().all())

        # S = scope (filtered subset for portfolio aggregation)
        if broker_ids:
            accesses = [a for a in all_accesses if a.broker_id in set(broker_ids)]
        else:
            accesses = all_accesses

        if not accesses:
            return PortfolioCalculationResult(
                daily_states=[],
                scope_broker_ids=[],
                target_currency=target_currency,
                date_from=date_from or date_type.today(),
                date_to=date_to or date_type.today(),
            )

        scope_broker_ids = {a.broker_id for a in accesses}
        # F2 — ownership scaling: an OWNER's share scales the broker's contribution
        # (0% is valid and contributes nothing). EDITOR/VIEWER rows always carry
        # share 0 by schema rule but must still see full data → scale 1 for them.
        broker_shares = {a.broker_id: effective_share(a.role, a.share_percentage) for a in accesses}

        # ── 3. Load ALL transactions for scope brokers ──
        tx_stmt = select(Transaction).where(Transaction.broker_id.in_(scope_broker_ids)).order_by(Transaction.date, Transaction.id)
        tx_result = await self.db.execute(tx_stmt)
        all_txs = list(tx_result.scalars().all())

        if not all_txs:
            return PortfolioCalculationResult(
                daily_states=[],
                scope_broker_ids=list(scope_broker_ids),
                target_currency=target_currency,
                date_from=date_from or date_type.today(),
                date_to=date_to or date_type.today(),
            )

        # ── 3b. Load ADJUSTMENT rows linked to unique SPLIT AssetEvents ──
        # A split rescales the average-cost pool instead of adding or reducing it: it
        # redistributes existing cost over a new quantity, it never adds/removes cost.
        split_linked_tx_ids: set[int] = set()
        split_records_by_event_id: dict[int, SplitRecord] = {}
        for link in await load_split_links(self.db, all_txs):
            if not is_valid_split_ratio(link.ratio):
                raise ValueError(f"SPLIT AssetEvent {link.event_id} must have a positive finite ratio")
            split_linked_tx_ids.add(link.transaction_id)
            split_records_by_event_id[link.event_id] = SplitRecord(event_id=link.event_id, asset_id=link.event_asset_id, date=link.event_date, ratio=link.ratio)

        split_history_lists: dict[int, list[SplitRecord]] = defaultdict(list)
        for split in split_records_by_event_id.values():
            split_history_lists[split.asset_id].append(split)
        split_history: dict[int, SplitHistory] = {asset_id: tuple(sorted(history, key=lambda record: (record.date, record.event_id))) for asset_id, history in split_history_lists.items()}

        # ── 4. Classify transactions ──
        classifier = ScopeAwareTransactionClassifier(scope_broker_ids, all_txs, broker_shares)
        needed_ids = classifier.get_needed_paired_ids()

        external_paired: dict[int, Transaction] = {}
        if needed_ids:
            ext_stmt = select(Transaction).where(Transaction.id.in_(needed_ids))
            ext_result = await self.db.execute(ext_stmt)
            external_paired = {tx.id: tx for tx in ext_result.scalars().all()}

        classification = classifier.classify(external_paired)

        # ── 5. Determine date range ──
        # R13-SEC7-1: the replay walks every day of the range, so neither end runs free. It starts no earlier than the
        # first transaction (before it there is nothing to replay, and a period starting earlier already starts empty)
        # and ends no later than latest_range_end(), tomorrow. A range that ends before the first transaction has no day.
        first_tx_date = min(tx.date for tx in all_txs)
        actual_from = max(date_from, first_tx_date) if date_from else first_tx_date
        actual_to = min(date_to or date_type.today(), latest_range_end())
        if actual_from > actual_to:
            return PortfolioCalculationResult(
                daily_states=[],
                scope_broker_ids=list(scope_broker_ids),
                target_currency=target_currency,
                date_from=actual_to,
                date_to=actual_to,
            )

        # ── 5b. Blob cache check (range-aware) ──
        tx_fingerprint = compute_tx_fingerprint(all_txs)
        held_asset_ids = {tx.asset_id for tx in all_txs if tx.asset_id and tx.quantity and tx.quantity != 0}
        price_fingerprint = await self._compute_price_fingerprint(held_asset_ids, actual_to)
        fx_fingerprint = await compute_portfolio_fx_cache_identity(
            self.db,
            scope_broker_ids,
            target_currency,
            actual_to,
        )
        # Split events influence valuation without necessarily changing scope
        # Transaction.updated_at values.
        split_fingerprint = (
            tuple(sorted(split_linked_tx_ids)),
            tuple(sorted((record.event_id, record.asset_id, record.date.isoformat(), str(record.ratio)) for record in split_records_by_event_id.values())),
        )

        # Blob key: independent of date range (blob stores its own range).
        # The access fingerprint (role + share per broker) MUST be part of the
        # key: editing a share or a role changes every scaled number, and the
        # tx/price fingerprints don't move (F2 follow-up: users changed their
        # ownership % and kept seeing the old values for the 24h TTL).
        access_fingerprint = tuple(sorted((a.broker_id, getattr(a.role, "value", a.role), str(a.share_percentage)) for a in accesses))
        blob_key = (
            user_id,
            tuple(sorted(scope_broker_ids)),
            access_fingerprint,
            target_currency,
            tx_fingerprint,
            price_fingerprint,
            fx_fingerprint,
            split_fingerprint,
            include_candles,
            include_acquisition_funding,
            # The day of position_states_start: the named period start, else the requested start (the first replayed
            # day); a run from t=0 never answers for a later date_from with its own first day's snapshot.
            period_start or date_from,
        )

        cached_blob, blob_hit = _portfolio_blob_cache.get(blob_key)
        if blob_hit and cached_blob is not None:
            blob_from = cached_blob.date_from
            blob_to = cached_blob.date_to
            # Check if requested range exactly matches the blob's range.
            # NOTE: must be an EXACT match on blob_to, not a superset check
            # (blob_to >= actual_to). The blob's daily_states/position_states_end/
            # end_state are not trimmed to actual_to before being returned, so a
            # "wider" cached blob would leak days beyond the requested date_to
            # into every downstream consumer (get_history, get_summary, ...).
            if blob_from <= actual_from and blob_to == actual_to:
                logger.debug("Portfolio blob cache hit (exact match)", user_id=user_id)
                return cached_blob
            # A blob that ends earlier is not resumed (EngineEndState is kept for that): the range is recomputed.
            logger.debug("Portfolio blob cache miss (range mismatch)", user_id=user_id, blob_range=f"{blob_from}..{blob_to}", requested=f"{actual_from}..{actual_to}")

        # ── 6. Preload prices (bulk) ──
        price_map: dict[int, list[tuple[date_type, Decimal, str]]] = {}
        # G1b: per-asset OHLC keyed by date, from the same already-loaded rows — no extra query.
        ohlc_map: dict[int, dict[date_type, tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]]] = {}
        if held_asset_ids:
            price_stmt = select(PriceHistory).where(PriceHistory.asset_id.in_(held_asset_ids)).where(PriceHistory.date <= actual_to).order_by(PriceHistory.asset_id, PriceHistory.date)
            price_result = await self.db.execute(price_stmt)
            for ph in price_result.scalars().all():
                price_map.setdefault(ph.asset_id, []).append((ph.date, ph.close, ph.currency))
                if include_candles:
                    ohlc_map.setdefault(ph.asset_id, {})[ph.date] = (ph.open, ph.high, ph.low)

        # ── 7. Preload quote_base_quantity ──
        quote_base_map: dict[int, int | None] = {}
        assets_list: list = []
        if held_asset_ids:
            asset_stmt = select(Asset).where(Asset.id.in_(held_asset_ids))
            asset_result = await self.db.execute(asset_stmt)
            assets_list = list(asset_result.scalars().all())
            for a in assets_list:
                quote_base_map[a.id] = a.quote_base_quantity

        # ── 8. Build asset_currencies map ──
        asset_currencies: dict[int, str] = {}
        for a in assets_list:
            asset_currencies[a.id] = a.currency or target_currency

        # ── 9. Preload asset classification + types ──
        asset_classifications: dict[int, dict | None] = {}
        asset_types: dict[int, str] = {}
        for a in assets_list:
            asset_types[a.id] = a.asset_type.value if a.asset_type else "Unknown"
            if a.classification_params:
                try:
                    asset_classifications[a.id] = json.loads(a.classification_params)
                except Exception:
                    asset_classifications[a.id] = None
            else:
                asset_classifications[a.id] = None

        # ── 10. Preload FX rates ──
        fx_rate_map = await self._preload_fx_rates(
            classification.classified,
            classification.in_transit_intervals,
            classification.external_cash_flows,
            price_map,
            asset_currencies,
            target_currency,
            actual_from,
            actual_to,
        )

        # ── 10a. Average cost of every position: historical cost in target currency (and in the
        # asset currency, for the unrealized split), each acquisition converted at its own date ──
        average_costs = await compute_average_costs(
            self.db,
            build_cost_positions(classification.classified, asset_currencies, target_currency, split_linked_tx_ids, date_to=actual_to),
            report_currency=target_currency,
        )

        # ── 10b. Unified price-resolver series per held asset — the single valuation brain ──
        # Each held asset gets one AssetPriceSeries fed with both asset-system quotes and observed
        # trades, in the asset's *native* currency — DailyStateBuilder converts each mark to the
        # reporting currency at the valuation date. It values MARKET_PRICE (real quote, exact/carried)
        # and LAST_TRADE_PRICE (trade-derived) from one source.
        mark_series: dict[int, AssetPriceSeries] | None = None
        if held_asset_ids:
            txs_by_asset: dict[int, list[Transaction]] = defaultdict(list)
            for tx in all_txs:
                if tx.asset_id:
                    txs_by_asset[tx.asset_id].append(tx)
            mark_series = {}
            for aid in held_asset_ids:
                series = build_asset_price_series(
                    price_rows=price_map.get(aid, []),
                    transactions=txs_by_asset.get(aid, []),
                    split_linked_tx_ids=split_linked_tx_ids,
                    asset_currency=asset_currencies.get(aid, target_currency),
                    quote_base_quantity=quote_base_map.get(aid) or 1,
                    ohlc_by_date=ohlc_map.get(aid),
                )
                if series.has_observations:
                    mark_series[aid] = series

        # ── 10c. Native cash of every broker: balances in their own currencies, valued at each
        # day's rate, and the period flows; each movement at its broker's share ──
        native_cash = await compute_native_cash(
            self.db,
            [movement for movement in (cash_movement_from_transaction(ctxn.tx, share=ctxn.share) for ctxn in classification.classified if ctxn.tx.date <= actual_to) if movement is not None],
            report_currency=target_currency,
            rates_until=actual_to,
        )

        # ── 11. Build daily states ──
        builder = DailyStateBuilder(
            classified_txs=classification.classified,
            in_transit_intervals=classification.in_transit_intervals,
            external_cash_flows=classification.external_cash_flows,
            price_map=price_map,
            quote_base_map=quote_base_map,
            fx_rate_map=fx_rate_map,
            asset_classifications=asset_classifications,
            asset_types=asset_types,
            asset_currencies=asset_currencies,
            average_costs=average_costs,
            native_cash=native_cash,
            target_currency=target_currency,
            date_from=actual_from,
            date_to=actual_to,
            split_linked_tx_ids=split_linked_tx_ids,
            split_history=split_history,
            mark_series=mark_series,
            compute_candles=include_candles,
            compute_acquisition_funding=include_acquisition_funding,
            period_start=period_start,
        )
        result = builder.build()
        # J-43: the pairs between brokers owned at different shares, for the data-quality report (the cache key holds the shares).
        result.share_mismatches = classification.share_mismatches

        # ── 12. Store in blob cache ──
        _portfolio_blob_cache.set(blob_key, result)
        logger.debug("Portfolio blob cache stored", user_id=user_id, n_states=len(result.daily_states), range=f"{actual_from}..{actual_to}")

        return result

    async def _compute_price_fingerprint(
        self,
        held_asset_ids: set[int],
        date_to: date_type,
    ) -> str:
        """Compute a lightweight fingerprint of price data for cache invalidation.

        Uses COUNT + MAX(fetched_at) as a proxy — any price insert/update
        changes at least one of these, invalidating the cache key.
        """
        if not held_asset_ids:
            return "no_assets"
        stmt = (
            select(
                func.count(PriceHistory.id),
                func.max(PriceHistory.fetched_at),
            )
            .where(PriceHistory.asset_id.in_(held_asset_ids))
            .where(PriceHistory.date <= date_to)
        )
        row = (await self.db.execute(stmt)).one()
        count = row[0] or 0
        max_fetched = row[1].isoformat() if row[1] else "none"
        return f"{count}:{max_fetched}"

    async def _preload_fx_rates(  # noqa: C901 — sequential fx-need collection loops, no decision logic
        self,
        classified_txs: list[ClassifiedTransaction],
        in_transit_intervals: list[InTransitInterval],
        external_cash_flows: list[tuple[date_type, int, Decimal, str]],
        price_map: dict[int, list[tuple[date_type, Decimal, str]]],
        asset_currencies: dict[int, str],
        target_currency: str,
        date_from: date_type,
        date_to: date_type,
    ) -> dict[tuple[str, str, date_type], Decimal]:
        """Pre-load all FX rates needed for the calculation in one bulk call.

        Includes rates for:
        - Transaction amounts → target_currency (all tx dates)
        - Priced outgoing ADJUSTMENTs → their cost basis (or asset) currency at their date (J-24: the
          value they hand over leaves the capital at that day's rate)
        - External cash flows → target_currency
        - Price currencies → target_currency (every day in range)
        - Asset currencies (resolver marks, unrealized split) → target_currency (every day in range)
        - TRANSFER legs before the range → price/asset currencies at the leg date (lot 41: the
          internal broker flows and the in-kind transfer capital value securities on that date)
        - In-transit cash → target_currency (every day of the transit); in-transit cost → at arrival

        Cost conversions are not here: compute_average_costs makes its own, at each movement's date.
        """
        # Collect all (from_ccy, date) pairs needed
        fx_needs: set[tuple[str, date_type]] = set()

        # From transaction amounts
        for ctxn in classified_txs:
            tx = ctxn.tx
            if tx.amount and tx.amount != 0 and tx.currency and tx.currency != target_currency:
                fx_needs.add((tx.currency, tx.date))

        # From priced outgoing ADJUSTMENTs (J-24): the value they hand over, at the rate of their date, also before
        # the range, in the cost basis currency or the asset's
        for ctxn in classified_txs:
            tx = ctxn.tx
            if tx.type != TransactionType.ADJUSTMENT or tx.cost_basis_override is None or not tx.quantity or tx.quantity > 0:
                continue
            handover_ccy = tx.cost_basis_currency or asset_currencies.get(tx.asset_id)
            if handover_ccy and handover_ccy != target_currency:
                fx_needs.add((handover_ccy, tx.date))

        # From external cash flows
        for dt, _, _, ccy in external_cash_flows:
            if ccy != target_currency:
                fx_needs.add((ccy, dt))

        # From price currencies — need rate for every day in range
        price_currencies: set[str] = set()
        for prices in price_map.values():
            for _, _, ccy in prices:
                if ccy != target_currency:
                    price_currencies.add(ccy)

        # From asset currencies (resolver marks + unrealized split, every day in range)
        asset_ccys_non_target: set[str] = set()
        for ccy in asset_currencies.values():
            if ccy != target_currency:
                asset_ccys_non_target.add(ccy)

        # For price/asset currencies we need rates for every day in range
        all_non_target_ccys = price_currencies | asset_ccys_non_target
        if all_non_target_ccys:
            current = date_from
            while current <= date_to:
                for ccy in all_non_target_ccys:
                    fx_needs.add((ccy, current))
                current += timedelta(days=1)

        # From TRANSFER legs before the range: the loop above starts at date_from
        for ctxn in classified_txs:
            tx = ctxn.tx
            if tx.type != TransactionType.TRANSFER or tx.asset_id is None or not tx.quantity or tx.date >= date_from:
                continue
            leg_ccys = {ccy for _, _, ccy in price_map.get(tx.asset_id, [])}
            asset_ccy = asset_currencies.get(tx.asset_id)
            if asset_ccy:
                leg_ccys.add(asset_ccy)
            for ccy in leg_ccys:
                if ccy != target_currency:
                    fx_needs.add((ccy, tx.date))

        # From in-transit intervals: cash every day of the transit, cost at the arrival date
        for interval in in_transit_intervals:
            dep = interval.departure_leg
            if interval.tx_type == "cash" and dep.currency and dep.currency != target_currency:
                current = interval.start_date
                while current <= interval.end_date:
                    fx_needs.add((dep.currency, current))
                    current += timedelta(days=1)
            if interval.cost_basis_currency and interval.cost_basis_currency != target_currency:
                fx_needs.add((interval.cost_basis_currency, interval.arrival_leg.date))

        if not fx_needs:
            return {}

        # Batch convert
        fx_needs_list = list(fx_needs)
        bulk_items = [(CurrencySchema(code=ccy, amount=Decimal("1")), target_currency, dt) for ccy, dt in fx_needs_list]

        results, _ = await convert_bulk(self.db, bulk_items, raise_on_error=False)

        fx_rate_map: dict[tuple[str, str, date_type], Decimal] = {}
        for i, (ccy, dt) in enumerate(fx_needs_list):
            if i < len(results) and results[i] is not None:
                converted_amount = results[i][0].amount if results[i] else None
                if converted_amount is not None:
                    fx_rate_map[(ccy, target_currency, dt)] = converted_amount

        return fx_rate_map
