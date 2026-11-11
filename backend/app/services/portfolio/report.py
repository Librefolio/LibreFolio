"""The portfolio report of ``PortfolioService``: all the sections of one answer, cached at layer 2."""

from __future__ import annotations

import hashlib
from datetime import date as date_type

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    BrokerUserAccess,
    PriceHistory,
    Transaction,
)
from backend.app.schemas.common import DateSpan
from backend.app.schemas.portfolio.history import AcquisitionFundingSeries, BrokerPnlHistory, CostHistorySeries, DepositHistorySeries, IncomeHistorySeries, MwrrLinePoint, PnlCandleSeries, PortfolioHistoryPoint
from backend.app.schemas.portfolio.report import AllocationHistoryDimensions, PortfolioReportMetadata, PortfolioReportQuery, PortfolioReportResponse
from backend.app.schemas.portfolio.summary import AllocationHistoryPoint, PortfolioSummary, PositionsContribution
from backend.app.services.financial_math.yield_on_cost import (
    compute_yield_on_cost_dependency_identity,
)
from backend.app.services.portfolio import engine_facts
from backend.app.utils.datetime_utils import latest_range_end
from backend.app.utils.runtime.cache import get_ttl_cache

_logger = structlog.get_logger(__name__)

# Layer 2 cache: full report results keyed by scope/query plus tx, price, FX and split identities.
_portfolio_l2_cache = get_ttl_cache("portfolio_layer2", maxsize=20, ttl=1800)  # 30 min


class PortfolioReportMixin:
    """The portfolio report of ``PortfolioService``: all the sections of one answer, cached at layer 2.

    Mixed into ``PortfolioService`` (``portfolio_service.py``), which provides ``db``.
    """

    db: AsyncSession

    async def get_report(  # noqa: C901 — TODO(P2-refactor): include-flag orchestration
        self,
        user_id: int,
        query: PortfolioReportQuery,
    ) -> PortfolioReportResponse:
        """Run the engine ONCE and return all requested views in a single response.

        Avoids the need for separate summary/history/allocation-history calls from
        the dashboard. A single POST /portfolio/report is enough for a full page load.

        Uses Layer 2 cache: keyed by (user, scope, date_range, query_features, data_fingerprint).
        """
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.engine import compute_portfolio_fx_cache_identity, compute_tx_fingerprint  # noqa: PLC0415

        today = date_type.today()
        base_currency = query.target_currency or await self._get_base_currency(user_id)
        date_from = query.date_range.resolved_start() if query.date_range else None
        date_to = query.date_range.resolved_end() if query.date_range else None
        # R13-SEC7-1: the report — history, summary, metadata, cache key — ends by latest_range_end(), and a start after
        # that end moves to it
        if date_to is not None:
            date_to = min(date_to, latest_range_end())
        effective_date_to = date_to or today
        if date_from is not None:
            date_from = min(date_from, effective_date_to)

        # ── 0. Layer 2 cache check ──
        # Build a fingerprint from transactions + prices to detect data changes
        l2_key = None
        broker_ids_for_scope = query.broker_ids
        scope_stmt = select(BrokerUserAccess).where(BrokerUserAccess.user_id == user_id)
        if broker_ids_for_scope:
            scope_stmt = scope_stmt.where(BrokerUserAccess.broker_id.in_(broker_ids_for_scope))
        scope_result = await self.db.execute(scope_stmt)
        scope_accesses = list(scope_result.scalars().all())
        scope_broker_ids = sorted({a.broker_id for a in scope_accesses})
        # Role/share edits change every scaled number but not the data
        # fingerprints — they must bust the cache (F2 follow-up).
        access_fp = tuple(sorted((a.broker_id, getattr(a.role, "value", a.role), str(a.share_percentage)) for a in scope_accesses))

        if scope_broker_ids:
            # Quick fingerprints for cache key (lightweight queries)
            tx_stmt = select(Transaction).where(Transaction.broker_id.in_(scope_broker_ids)).order_by(Transaction.date, Transaction.id)
            tx_result = await self.db.execute(tx_stmt)
            all_txs_for_fp = list(tx_result.scalars().all())
            tx_fp = compute_tx_fingerprint(all_txs_for_fp) if all_txs_for_fp else "no_txs"

            held_ids = {tx.asset_id for tx in all_txs_for_fp if tx.asset_id and tx.quantity and tx.quantity != 0}
            price_fp = "no_assets"
            if held_ids:
                pf_stmt = select(func.count(PriceHistory.id), func.max(PriceHistory.fetched_at)).where(PriceHistory.asset_id.in_(held_ids)).where(PriceHistory.date <= effective_date_to)
                pf_row = (await self.db.execute(pf_stmt)).one()
                price_fp = f"{pf_row[0] or 0}:{pf_row[1].isoformat() if pf_row[1] else 'none'}"

            fx_fp = await compute_portfolio_fx_cache_identity(
                self.db,
                set(scope_broker_ids),
                base_currency,
                effective_date_to,
            )
            yield_on_cost_fp = await compute_yield_on_cost_dependency_identity(
                self.db,
                user_id=user_id,
                scope_transactions=all_txs_for_fp,
                as_of_date=effective_date_to,
            )
            # The report shows each asset's name, icon, type, currency and classification: an edit of those changes no
            # transaction, price or rate, so it has a fingerprint of its own.
            asset_ids_for_fp = sorted({tx.asset_id for tx in all_txs_for_fp if tx.asset_id})
            asset_fp = "no_assets"
            if asset_ids_for_fp:
                asset_fp_stmt = select(Asset.id, Asset.display_name, Asset.icon_url, Asset.asset_type, Asset.currency, Asset.classification_params).where(Asset.id.in_(asset_ids_for_fp)).order_by(Asset.id)
                asset_fp_rows = (await self.db.execute(asset_fp_stmt)).all()
                asset_fp = hashlib.sha256(repr([tuple(row) for row in asset_fp_rows]).encode("utf-8")).hexdigest()

            l2_key = (
                user_id,
                tuple(scope_broker_ids),
                tuple(sorted(broker_ids_for_scope)) if broker_ids_for_scope else None,
                access_fp,
                base_currency,
                str(date_from),
                str(date_to),
                str(effective_date_to),
                query.include_summary,
                query.include_history,
                query.include_allocation_history,
                query.include_breakdown,
                query.include_positions_contribution,
                query.include_broker_pnl_history,
                query.include_pnl_candles,
                query.include_income_history,
                query.include_cost_history,
                query.include_deposit_history,
                query.include_acquisition_funding,
                query.apply_ownership_share,
                tx_fp,
                price_fp,
                fx_fp,
                yield_on_cost_fp,
                asset_fp,
            )

            cached, hit = _portfolio_l2_cache.get(l2_key)
            if hit:
                _logger.debug("Portfolio L2 cache hit", user_id=user_id)
                return cached

        # ── 1. Single engine run: the page's run, shared with the Performance table and the positions chart (FB-14) ──
        engine_result = await self._engine_run(
            user_id=user_id,
            broker_ids=query.broker_ids,
            date_from=date_from,
            date_to=effective_date_to,
            target_currency=base_currency,
            include_candles=query.include_pnl_candles,
            apply_ownership_share=query.apply_ownership_share,
        )

        views = DerivedViewsBuilder(engine_result.daily_states, base_currency)

        included: list[str] = []

        # ── 2. Summary (reuses get_summary logic inline to share engine result) ──
        summary: PortfolioSummary | None = None
        if query.include_summary:
            included.append("summary")
            summary = await self.get_summary(
                user_id=user_id,
                broker_ids=query.broker_ids,
                target_currency_override=base_currency,
                include_breakdown=query.include_breakdown,
                date_from=date_from,
                date_to=effective_date_to,
                _precomputed_engine_result=engine_result,
            )

        # ── 3. History ──
        history: list[PortfolioHistoryPoint] | None = None
        mwrr_line: list[MwrrLinePoint] | None = None
        if query.include_history:
            included.append("history")
            history_steps = await self.get_history_steps(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_engine_result=engine_result,
            )
            history, mwrr_line = history_steps.history, history_steps.mwrr_line

        # ── 4. Allocation history (all 4 dimensions from same engine result) ──
        alloc_history: AllocationHistoryDimensions | None = None
        if query.include_allocation_history:
            included.append("allocation_history")
            history_asset_names = {asset_id: asset.display_name for asset_id, asset in (await self._get_assets_map(views.allocation_asset_ids(date_from))).items()}
            alloc_history = AllocationHistoryDimensions(
                type=[AllocationHistoryPoint(**p) for p in views.build_allocation_history("type", date_from=date_from)],
                sector=[AllocationHistoryPoint(**p) for p in views.build_allocation_history("sector", date_from=date_from)],
                geography=[AllocationHistoryPoint(**p) for p in views.build_allocation_history("geography", date_from=date_from)],
                asset=[AllocationHistoryPoint(**p) for p in views.build_asset_allocation_history(history_asset_names, date_from=date_from)],
            )

        # ── 4b. Positions contribution (per-asset period P&L attribution) ──
        positions_contribution: PositionsContribution | None = None
        if query.include_positions_contribution:
            included.append("positions_contribution")
            positions_contribution = await self.get_positions_contribution(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_engine_result=engine_result,
                apply_ownership_share=query.apply_ownership_share,
            )

        # ── 4c. Broker P&L history (additive per-broker overlay for GrowthChart P&L mode) ──
        broker_pnl_history: list[BrokerPnlHistory] | None = None
        if query.include_broker_pnl_history:
            included.append("broker_pnl_history")
            broker_pnl_history = await self.get_broker_pnl_history(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_engine_result=engine_result,
            )

        # ── 4d. Synthetic total-P&L candle series (GrowthChart P&L candles submode, G1b) ──
        pnl_candles: PnlCandleSeries | None = None
        if query.include_pnl_candles:
            included.append("pnl_candles")
            pnl_candles = await self.get_pnl_candles(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_engine_result=engine_result,
            )

        # ── 4e. Signed personal income history (GrowthChart P&L income submode, G1c) ──
        income_history: IncomeHistorySeries | None = None
        if query.include_income_history:
            included.append("income_history")
            income_history = await self.get_income_history(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_native_cash=engine_result.native_cash,
            )

        # ── 4f. Signed FEE+TAX cost history (batch 2 — Income submode's costs dimension) ──
        cost_history: CostHistorySeries | None = None
        if query.include_cost_history:
            included.append("cost_history")
            cost_history = await self.get_cost_history(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_native_cash=engine_result.native_cash,
            )

        # ── 4g. DEPOSIT history (batch 2 — Income submode's deposit-size dimension) ──
        deposit_history: DepositHistorySeries | None = None
        if query.include_deposit_history:
            included.append("deposit_history")
            deposit_history = await self.get_deposit_history(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_native_cash=engine_result.native_cash,
            )

        # ── 4h. New-vs-reinvested BUY funding split (batch 2 — Income submode's
        # acquisition-size dimension). The page's run always carries it (_engine_run, FB-14).
        acquisition_funding: AcquisitionFundingSeries | None = None
        if query.include_acquisition_funding:
            included.append("acquisition_funding")
            acquisition_funding = await self.get_acquisition_funding_history(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_engine_result=engine_result,
            )

        # ── 5. Data quality from engine (already computed if summary was built) ──
        if summary:
            data_quality = summary.data_quality
        else:
            configured_fx_pairs, real_provider_fx_pairs = await self._get_configured_fx_pair_sets()
            held_quote_facts = await self._held_asset_quote_facts(engine_result)
            data_quality = views.build_data_quality_report(
                missing_fx_pairs_dto=engine_facts._engine_missing_fx_pairs(engine_result, date_from, effective_date_to) or None,
                missing_cost_basis_assets=await self._missing_cost_basis_assets(engine_result) or None,
                invalid_split_assets=await self._invalid_split_assets(engine_result) or None,
                non_iso_currency_assets=self._non_iso_currency_assets(held_quote_facts) or None,
                report_currency=base_currency,
                mwrr_available=False,
                share_mismatches=engine_result.share_mismatches,
                configured_fx_pairs=configured_fx_pairs,
                real_provider_fx_pairs=real_provider_fx_pairs,
                period_from=date_from,
                period_to=effective_date_to,
            )

        # ── 6. Metadata ──
        computed_from = engine_result.daily_states[0].date if engine_result.daily_states else None
        computed_to = engine_result.daily_states[-1].date if engine_result.daily_states else None

        metadata = PortfolioReportMetadata(
            broker_ids=query.broker_ids,
            target_currency=base_currency,
            requested_date_from=date_from,
            requested_date_to=date_to,
            computed_date_from=computed_from,
            computed_date_to=computed_to,
            generated_at=today,
            included_features=included,
        )

        # The window of the step series (D-P4): the days of the period that have a state
        step_series_included = query.include_history or query.include_allocation_history or query.include_broker_pnl_history or query.include_pnl_candles
        window = views.window_range(date_from, effective_date_to) if step_series_included and engine_result.daily_states else None

        report = PortfolioReportResponse(
            metadata=metadata,
            range=DateSpan(start=window[0], end=window[1]) if window is not None else None,
            summary=summary,
            history=history,
            mwrr_line=mwrr_line,
            allocation_history=alloc_history,
            data_quality=data_quality,
            positions_contribution=positions_contribution,
            broker_pnl_history=broker_pnl_history,
            pnl_candles=pnl_candles,
            income_history=income_history,
            cost_history=cost_history,
            deposit_history=deposit_history,
            acquisition_funding=acquisition_funding,
        )

        # Store in Layer 2 cache
        if l2_key is not None:
            _portfolio_l2_cache.set(l2_key, report)
            _logger.debug("Portfolio L2 cache stored", user_id=user_id)

        return report
