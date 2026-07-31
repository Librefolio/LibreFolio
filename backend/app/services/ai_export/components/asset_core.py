"""Real `ComponentSpec` implementations for the eight non-technical Asset components.

Workstream E2 ("Asset core") wave: `asset.identity`, `asset.market_snapshot`,
`asset.position_scope`, `asset.provenance`, `asset.positions_by_broker`,
`asset.cost_value_pl`, `asset.performance`, `asset.lot_detail`. Every
`component_id`/`domains`/`dependencies`/`period_behavior` below matches
`backend.app.services.ai_export.components.catalog._ASSET_COMPONENTS`
exactly - see that module's docstring for why the wiring must stay stable
while the fail-closed placeholder builder is replaced by the real domain
logic implemented here.

The three *technical* Asset components (`asset.ohlc_returns`,
`asset.indicators`, `asset.states_events`) belong to a sibling technical-
shared wave and are intentionally NOT defined here.

Every builder below independently resolves `ASSET_METADATA_RESOURCE` first
(via `context.db_resource`, itself memoized) so `AssetNotFoundError`
propagates uniformly from every one of the eight components when
`scope.asset_id` does not exist - not only from `asset.identity`/
`asset.market_snapshot`, which are the only two with a declared dependency
on `asset.identity` in the frozen catalog wiring above.

This module is intentionally NOT wired into
`backend.app.services.ai_export.components.catalog` (that file is owned by
the parent integration step, per this workstream's ownership boundaries) -
see the plan's Phase 0 AI Export refinement workstream E2 section.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.services.ai_export.components.asset_payloads import (
    AssetAggregateCoverage,
    AssetBrokerCostValuePl,
    AssetBrokerPeriodPerformance,
    AssetBrokerPosition,
    AssetClassification,
    AssetCostValuePlPayload,
    AssetCoverageOmission,
    AssetFxConversionDirection,
    AssetFxConversionProvenance,
    AssetGeographicWeight,
    AssetIdentifiers,
    AssetIdentityPayload,
    AssetLotCustodyRow,
    AssetLotDetailPayload,
    AssetLotDetailRow,
    AssetMarketSnapshotPayload,
    AssetPerformancePayload,
    AssetPositionsByBrokerPayload,
    AssetPositionScopeBroker,
    AssetPositionScopePayload,
    AssetPriceObservation,
    AssetProvenancePayload,
    AssetProviderAssignmentInfo,
    AssetSectorWeight,
    AssetValuationSourceSemantic,
)
from backend.app.services.ai_export.components.asset_resources import (
    ASSET_LOTS_RESOURCE,
    ASSET_MARKET_PRICES_RESOURCE,
    ASSET_METADATA_RESOURCE,
    ASSET_REPORT_RESOURCE,
    AssetMetadataResource,
    load_asset_lots,
    load_asset_market_prices,
    load_asset_metadata,
    load_asset_report,
    market_snapshot_from_price_result,
    scoped_contributions,
    scoped_holdings,
)
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import Domain, PeriodBehavior
from backend.app.services.ai_export.dependencies import BuildContext

# =============================================================================
# Static methodology text for asset.provenance (never user/provider content)
# =============================================================================

_VALUATION_SOURCE_SEMANTICS: tuple[AssetValuationSourceSemantic, ...] = (
    AssetValuationSourceSemantic(code="MARKET_PRICE", description="Valued at the latest observed market price, converted to the report's target currency."),
    AssetValuationSourceSemantic(code="LAST_TRADE_PRICE", description="No market price was available; valued at the last observed transaction price (BUY, SELL or priced ADJUSTMENT) carried forward — a real trade, not an observed market return."),
    AssetValuationSourceSemantic(code="MISSING", description="No valuation could be determined by any hierarchy step; the position is excluded from valued totals."),
)

_PRICE_PROVENANCE_NOTE = (
    "Position valuations (asset.positions_by_broker, asset.cost_value_pl) use the Portfolio Engine's "
    "valuation hierarchy (valuation_source), which may fall back to WAC/cost when no market price is "
    "available. asset.market_snapshot is always the directly observed market price (or absent), never a "
    "WAC/cost substitute presented as a market price."
)


async def _require_asset_metadata(context: BuildContext) -> AssetMetadataResource:
    """Guard clause every builder below calls first: makes the "missing asset" failure uniform.

    Memoized by `BuildContext.db_resource`, so calling this from six
    independent builders costs at most one DB round trip per request.
    """
    scope = context.scope
    assert scope is not None  # BuildContext is always constructed with scope/session for ASSET domain requests
    return await context.db_resource(ASSET_METADATA_RESOURCE, load_asset_metadata(scope))


# =============================================================================
# asset.identity
# =============================================================================


async def _build_identity(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> AssetIdentityPayload:
    metadata = await _require_asset_metadata(context)

    classification = metadata.classification
    geographic_area: tuple[AssetGeographicWeight, ...] = ()
    sector_area: tuple[AssetSectorWeight, ...] = ()
    short_description: str | None = None
    if classification is not None:
        short_description = classification.short_description
        if classification.geographic_area is not None:
            geographic_area = tuple(AssetGeographicWeight(area=area, weight=weight) for area, weight in sorted(classification.geographic_area.distribution.items()))
        if classification.sector_area is not None:
            sector_area = tuple(AssetSectorWeight(sector=sector, weight=weight) for sector, weight in sorted(classification.sector_area.distribution.items()))

    return AssetIdentityPayload(
        asset_id=metadata.asset_id,
        display_name=metadata.display_name,
        currency=metadata.currency,
        asset_type=metadata.asset_type,
        quote_base_quantity=metadata.quote_base_quantity,
        active=metadata.active,
        identifiers=AssetIdentifiers(
            isin=metadata.identifier_isin,
            ticker=metadata.identifier_ticker,
            cusip=metadata.identifier_cusip,
            sedol=metadata.identifier_sedol,
            figi=metadata.identifier_figi,
            other=metadata.identifier_other,
        ),
        classification=AssetClassification(
            short_description=short_description,
            geographic_area=geographic_area,
            sector_area=sector_area,
        ),
    )


# =============================================================================
# asset.market_snapshot
# =============================================================================


async def _build_market_snapshot(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> AssetMarketSnapshotPayload:
    scope = context.scope
    assert scope is not None
    price_results = await context.db_resource(
        ASSET_MARKET_PRICES_RESOURCE,
        load_asset_market_prices(scope),
    )
    snapshot = market_snapshot_from_price_result(price_results.by_asset_id.get(scope.asset_id), scope)

    if snapshot.observation is None:
        return AssetMarketSnapshotPayload(
            asset_id=scope.asset_id,  # type: ignore[arg-type]
            as_of_date=scope.snapshot_as_of,
            target_currency=scope.target_currency,
        )

    observation = AssetPriceObservation(
        date=snapshot.observation.date,
        native_price=Currency(code=snapshot.observation.currency, amount=snapshot.observation.close),
        source_plugin_key=snapshot.observation.source_plugin_key,
    )
    conversion = None
    if snapshot.conversion_rate_date is not None and snapshot.conversion_direction is not None:
        conversion = AssetFxConversionProvenance(
            rate_date=snapshot.conversion_rate_date,
            direction=AssetFxConversionDirection(snapshot.conversion_direction),
            backward_fill_applied=bool(snapshot.conversion_backward_fill_applied),
        )
    return AssetMarketSnapshotPayload(
        asset_id=scope.asset_id,  # type: ignore[arg-type]
        as_of_date=scope.snapshot_as_of,
        target_currency=scope.target_currency,
        observed=observation,
        converted_price=snapshot.converted_amount,
        conversion=conversion,
    )


# =============================================================================
# asset.position_scope
# =============================================================================


async def _build_position_scope(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> AssetPositionScopePayload:
    await _require_asset_metadata(context)
    scope = context.scope
    assert scope is not None
    report = await context.db_resource(ASSET_REPORT_RESOURCE, load_asset_report(scope))
    holdings = scoped_holdings(report, scope.asset_id)  # type: ignore[arg-type]

    brokers = tuple(AssetPositionScopeBroker(broker_id=h.broker_id, broker_name=h.broker_name or f"broker#{h.broker_id}", quantity=h.quantity) for h in holdings)
    total_quantity = sum((b.quantity for b in brokers), start=Decimal("0"))
    return AssetPositionScopePayload(
        asset_id=scope.asset_id,  # type: ignore[arg-type]
        as_of_date=scope.snapshot_as_of,
        target_currency=scope.target_currency,
        brokers=brokers,
        total_quantity=total_quantity,
        broker_count=len(brokers),
    )


# =============================================================================
# asset.provenance
# =============================================================================


async def _build_provenance(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> AssetProvenancePayload:
    metadata = await _require_asset_metadata(context)
    scope = context.scope
    assert scope is not None

    provider = None
    if metadata.provider_code is not None:
        provider = AssetProviderAssignmentInfo(
            provider_code=metadata.provider_code,
            identifier_type=metadata.provider_identifier_type or "",
            identifier=metadata.provider_identifier,
            last_fetch_date=metadata.provider_last_fetch_date,
        )
    return AssetProvenancePayload(
        asset_id=scope.asset_id,  # type: ignore[arg-type]
        provider=provider,
        valuation_source_semantics=_VALUATION_SOURCE_SEMANTICS,
        price_provenance_note=_PRICE_PROVENANCE_NOTE,
    )


# =============================================================================
# asset.positions_by_broker
# =============================================================================


async def _build_positions_by_broker(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> AssetPositionsByBrokerPayload:
    await _require_asset_metadata(context)
    scope = context.scope
    assert scope is not None
    report = await context.db_resource(ASSET_REPORT_RESOURCE, load_asset_report(scope))
    holdings = scoped_holdings(report, scope.asset_id)  # type: ignore[arg-type]

    positions = tuple(
        AssetBrokerPosition(
            broker_id=h.broker_id,
            broker_name=h.broker_name or f"broker#{h.broker_id}",
            quantity=h.quantity,
            valuation_source=h.valuation_source,
            wac_per_unit=h.wac_per_unit,
            unit_price=(h.current_value / h.quantity if h.current_value is not None and h.quantity != 0 else None),
            current_value=h.current_value,
            unrealized_gain_loss=h.gain_loss,
            unrealized_gain_loss_percent=h.gain_loss_percent,
        )
        for h in holdings
    )
    return AssetPositionsByBrokerPayload(
        asset_id=scope.asset_id,  # type: ignore[arg-type]
        as_of_date=scope.snapshot_as_of,
        target_currency=scope.target_currency,
        positions=positions,
    )


# =============================================================================
# asset.cost_value_pl
# =============================================================================


async def _build_cost_value_pl(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> AssetCostValuePlPayload:
    await _require_asset_metadata(context)
    scope = context.scope
    assert scope is not None
    report = await context.db_resource(ASSET_REPORT_RESOURCE, load_asset_report(scope))
    holdings = scoped_holdings(report, scope.asset_id)  # type: ignore[arg-type]

    brokers: list[AssetBrokerCostValuePl] = []
    omitted: list[AssetCoverageOmission] = []
    valued_cost_basis: list[Decimal] = []
    valued_current_value: list[Decimal] = []
    valued_gain_loss: list[Decimal] = []
    for h in holdings:
        cost_basis = (h.wac_per_unit * h.quantity) if h.wac_per_unit is not None else None
        brokers.append(
            AssetBrokerCostValuePl(
                broker_id=h.broker_id,
                broker_name=h.broker_name or f"broker#{h.broker_id}",
                quantity=h.quantity,
                wac_per_unit=h.wac_per_unit,
                cost_basis=cost_basis,
                current_value=h.current_value,
                unrealized_gain_loss=h.gain_loss,
                unrealized_gain_loss_percent=h.gain_loss_percent,
            )
        )
        # A broker row only joins the aggregate "valued" subset when it carries
        # every field needed for reconciliation: cost_basis, current_value AND
        # the engine's own gain_loss (never recomputed from the first two,
        # which could silently paper over a partially-missing subset).
        missing_fields = [name for name, value in (("cost_basis", cost_basis), ("current_value", h.current_value), ("unrealized_gain_loss", h.gain_loss)) if value is None]
        if missing_fields:
            omitted.append(AssetCoverageOmission(broker_id=h.broker_id, missing_fields=tuple(missing_fields)))
            continue
        valued_cost_basis.append(cost_basis)  # type: ignore[arg-type]
        valued_current_value.append(h.current_value)  # type: ignore[arg-type]
        valued_gain_loss.append(h.gain_loss)  # type: ignore[arg-type]

    coverage = AssetAggregateCoverage(
        total_broker_count=len(brokers),
        valued_broker_count=len(valued_cost_basis),
        omitted=tuple(omitted),
        is_complete=not omitted,
    )
    has_valued_rows = bool(valued_cost_basis)
    return AssetCostValuePlPayload(
        asset_id=scope.asset_id,  # type: ignore[arg-type]
        as_of_date=scope.snapshot_as_of,
        target_currency=scope.target_currency,
        brokers=tuple(brokers),
        coverage=coverage,
        total_cost_basis=sum(valued_cost_basis, start=Decimal("0")) if has_valued_rows else None,
        total_current_value=sum(valued_current_value, start=Decimal("0")) if has_valued_rows else None,
        total_unrealized_gain_loss=sum(valued_gain_loss, start=Decimal("0")) if has_valued_rows else None,
    )


# =============================================================================
# asset.performance
# =============================================================================


async def _build_performance(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> AssetPerformancePayload:
    await _require_asset_metadata(context)
    scope = context.scope
    assert scope is not None
    report = await context.db_resource(ASSET_REPORT_RESOURCE, load_asset_report(scope))
    contributions = scoped_contributions(report, scope.asset_id)  # type: ignore[arg-type]

    brokers = tuple(
        AssetBrokerPeriodPerformance(
            broker_id=c.broker_id,
            broker_name=c.broker_name,
            start_value=c.start_value,
            end_value=c.end_value,
            period_pnl=c.period_pnl,
            period_pnl_percent=c.period_pnl_percent,
            period_realized_gain_loss=c.period_realized_gain_loss,
            period_unrealized_delta=c.period_unrealized_delta,
            period_income=c.period_income,
            period_fees_taxes=c.period_fees_taxes,
            is_fully_sold=c.is_fully_sold,
        )
        for c in contributions
    )

    # A broker row only joins the aggregate "valued" subset when start_value,
    # end_value AND period_pnl are all present together, so the aggregate
    # percent's numerator (total_period_pnl) and denominator
    # (total_start_value) subsets are guaranteed to match exactly - never an
    # independent per-field sum that could silently mix incoherent rows.
    omitted: list[AssetCoverageOmission] = []
    valued_start: list[Decimal] = []
    valued_end: list[Decimal] = []
    valued_pnl: list[Decimal] = []
    for b in brokers:
        missing_fields = [name for name, value in (("start_value", b.start_value), ("end_value", b.end_value), ("period_pnl", b.period_pnl)) if value is None]
        if missing_fields:
            omitted.append(AssetCoverageOmission(broker_id=b.broker_id, missing_fields=tuple(missing_fields)))
            continue
        valued_start.append(b.start_value)  # type: ignore[arg-type]
        valued_end.append(b.end_value)  # type: ignore[arg-type]
        valued_pnl.append(b.period_pnl)  # type: ignore[arg-type]

    coverage = AssetAggregateCoverage(
        total_broker_count=len(brokers),
        valued_broker_count=len(valued_start),
        omitted=tuple(omitted),
        is_complete=not omitted,
    )
    has_valued_rows = bool(valued_start)
    total_start_value = sum(valued_start, start=Decimal("0")) if has_valued_rows else None
    total_period_pnl = sum(valued_pnl, start=Decimal("0")) if has_valued_rows else None
    total_period_pnl_percent = (total_period_pnl / abs(total_start_value)) if (total_start_value is not None and total_start_value != 0) else None

    return AssetPerformancePayload(
        asset_id=scope.asset_id,  # type: ignore[arg-type]
        period=DateRangeModel(start=scope.period_start, end=scope.period_end),
        target_currency=scope.target_currency,
        brokers=brokers,
        coverage=coverage,
        total_start_value=total_start_value,
        total_end_value=sum(valued_end, start=Decimal("0")) if has_valued_rows else None,
        total_period_pnl=total_period_pnl,
        total_period_pnl_percent=total_period_pnl_percent,
    )


# =============================================================================
# asset.lot_detail (optional component - fails soft at the caller/integration level)
# =============================================================================


async def _build_lot_detail(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> AssetLotDetailPayload:
    await _require_asset_metadata(context)
    scope = context.scope
    assert scope is not None
    lots_response = await context.db_resource(ASSET_LOTS_RESOURCE, load_asset_lots(scope))

    eligible_lots = []
    omitted_degraded_lot_count = 0
    for lot in lots_response.lots or ():
        # Eligibility follows the shared FIFO status semantics
        # (`FifoEngineResult.get_lot_states()`): open/partial iff
        # `open_quantity != 0`, always retained regardless of `closing_date`.
        # A lot is only "closed" when `open_quantity == 0`, and closed lots
        # require the authoritative `closing_date` to apply the period
        # cutoff - never `closing_date` alone, and never treating a closed
        # row with a missing `closing_date` as if it were still open.
        is_closed = lot.open_quantity == Decimal("0")
        if not is_closed:
            pass  # open or partially closed - always included, no cutoff applies
        elif lot.closing_date is None:
            # Data-quality problem: a fully-closed lot must carry an
            # authoritative closing_date. Omit rather than silently treat as
            # open; no lot/transaction identifier is exposed in this
            # diagnostic - see `AssetLotDetailPayload.omitted_degraded_lot_count`.
            omitted_degraded_lot_count += 1
            continue
        elif lot.closing_date < scope.period_start:
            continue

        eligible_lots.append(lot)

    rows: list[AssetLotDetailRow] = []
    for index, lot in enumerate(
        sorted(
            eligible_lots,
            key=lambda item: (
                item.opening_date,
                item.opening_broker_id,
                item.lot_id,
            ),
        ),
        start=1,
    ):
        custody = tuple(AssetLotCustodyRow(broker_id=slice_.broker_id, custody_type=slice_.custody_type, quantity=slice_.quantity) for slice_ in lot.current_custody)
        rows.append(
            AssetLotDetailRow(
                lot_ref=f"L{index}",
                opening_broker_id=lot.opening_broker_id,
                opening_date=lot.opening_date,
                opening_unit_price=lot.opening_unit_price,
                original_quantity=lot.original_quantity,
                open_quantity=lot.open_quantity,
                closing_date=lot.closing_date,
                current_custody=custody,
            )
        )

    return AssetLotDetailPayload(
        asset_id=scope.asset_id,  # type: ignore[arg-type]
        period=DateRangeModel(start=scope.period_start, end=scope.period_end),
        target_currency=lots_response.target_currency,
        lots=tuple(rows),
        omitted_degraded_lot_count=omitted_degraded_lot_count,
    )


# =============================================================================
# ComponentSpec definitions - mirrors catalog.py's _ASSET_COMPONENTS wiring exactly
# =============================================================================

ASSET_IDENTITY_SPEC = ComponentSpec(
    component_id="asset.identity",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=AssetIdentityPayload,
    builder=_build_identity,
    dependencies=(),
    period_behavior=PeriodBehavior.NONE,
)

ASSET_MARKET_SNAPSHOT_SPEC = ComponentSpec(
    component_id="asset.market_snapshot",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=AssetMarketSnapshotPayload,
    builder=_build_market_snapshot,
    dependencies=("asset.identity",),
    period_behavior=PeriodBehavior.AS_OF,
)

ASSET_POSITION_SCOPE_SPEC = ComponentSpec(
    component_id="asset.position_scope",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=AssetPositionScopePayload,
    builder=_build_position_scope,
    dependencies=(),
    period_behavior=PeriodBehavior.AS_OF,
)

ASSET_PROVENANCE_SPEC = ComponentSpec(
    component_id="asset.provenance",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=AssetProvenancePayload,
    builder=_build_provenance,
    dependencies=(),
    period_behavior=PeriodBehavior.NONE,
)

ASSET_POSITIONS_BY_BROKER_SPEC = ComponentSpec(
    component_id="asset.positions_by_broker",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=AssetPositionsByBrokerPayload,
    builder=_build_positions_by_broker,
    dependencies=("asset.position_scope",),
    period_behavior=PeriodBehavior.AS_OF,
)

ASSET_COST_VALUE_PL_SPEC = ComponentSpec(
    component_id="asset.cost_value_pl",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=AssetCostValuePlPayload,
    builder=_build_cost_value_pl,
    dependencies=("asset.positions_by_broker",),
    period_behavior=PeriodBehavior.AS_OF,
)

ASSET_PERFORMANCE_SPEC = ComponentSpec(
    component_id="asset.performance",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=AssetPerformancePayload,
    builder=_build_performance,
    dependencies=("asset.cost_value_pl",),
    period_behavior=PeriodBehavior.WINDOWED,
)

ASSET_LOT_DETAIL_SPEC = ComponentSpec(
    component_id="asset.lot_detail",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=AssetLotDetailPayload,
    builder=_build_lot_detail,
    dependencies=("asset.positions_by_broker",),
    period_behavior=PeriodBehavior.WINDOWED,
)

ASSET_CORE_COMPONENTS: tuple[ComponentSpec, ...] = (
    ASSET_IDENTITY_SPEC,
    ASSET_MARKET_SNAPSHOT_SPEC,
    ASSET_POSITION_SCOPE_SPEC,
    ASSET_PROVENANCE_SPEC,
    ASSET_POSITIONS_BY_BROKER_SPEC,
    ASSET_COST_VALUE_PL_SPEC,
    ASSET_PERFORMANCE_SPEC,
    ASSET_LOT_DETAIL_SPEC,
)
"""Real ComponentSpec replacements for the eight non-technical Asset components.

Not wired into `backend.app.services.ai_export.components.catalog.
ALL_FOUNDATION_COMPONENTS` by this module (integration/catalog-swap is a
parent-integration concern, out of this workstream's file-ownership scope) -
see the plan's workstream E2 section and this module's docstring.
"""

__all__ = [
    "ASSET_CORE_COMPONENTS",
    "ASSET_COST_VALUE_PL_SPEC",
    "ASSET_IDENTITY_SPEC",
    "ASSET_LOT_DETAIL_SPEC",
    "ASSET_MARKET_SNAPSHOT_SPEC",
    "ASSET_PERFORMANCE_SPEC",
    "ASSET_POSITIONS_BY_BROKER_SPEC",
    "ASSET_POSITION_SCOPE_SPEC",
    "ASSET_PROVENANCE_SPEC",
]
