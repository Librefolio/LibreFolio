"""Real FX non-technical/core `ComponentSpec` builders for the AI Export runtime.

Owns exactly the five FX "core" component IDs (matching the placeholders
declared in `backend.app.services.ai_export.components.catalog` verbatim, so a
future catalog wiring can swap the placeholder builders for
`FX_CORE_COMPONENTS` without touching any `component_id`/`domains`/
`dependencies` metadata):

- `fx.pair_identity` - explicit quote-per-base pair identity.
- `fx.current_rate` - quote-per-base rate as of the snapshot instant.
- `fx.conversion_provenance` - direction/source/backfill provenance for the
  base/quote pair itself.
- `fx.exposure_base_quote` - every direct base/quote cash/position exposure
  row (broker-scoped), preserved in full (no top-N).
- `fx.exposure_provenance` - deduplicated conversion provenance for the
  exposure rows above (towards `target_currency`, possibly a third currency).

The FX *technical* components (`fx.rate_ohlc`, `fx.returns_volatility`,
`fx.indicators`, `fx.states_events`) belong to a sibling workstream and are
never referenced here.

Design notes:
- All rate data flows through the existing `backend.app.services.fx.convert_bulk`
  batch conversion service - never a hand-rolled provider route. `convert_bulk`
  only ever resolves a *direct* or *inverse* stored `FxRate` row (see
  `backend.app.db.models.FxRate`'s alphabetical storage invariant) and raises
  `RateNotFoundError` otherwise, so this module never fabricates a triangulated
  route either.
- The canonical daily base->quote rate series is loaded exactly once per
  request via `backend.app.services.ai_export.components.technical_shared.
  load_fx_rate_series` (a warm-up-inclusive range, memoized under its own
  request-scoped resource key): `fx.current_rate` and `fx.conversion_provenance`
  both consume it and select `scope.snapshot_as_of` out of the wider series,
  instead of maintaining a second, visible-period-only rate series loader
  under a separate key - see `_load_rate_series`'s docstring (parent
  integration gate, requirement 4).
- Direct exposure is sourced from a real `PortfolioService.get_report` call,
  scoped to `BuildScope.broker_scope` - never a look-through/inferred
  approximation. Every nonzero cash balance and every position whose trading
  (`Asset.currency`) or valuation (`PortfolioHolding.valuation_effective_currency`)
  currency directly matches base/quote is preserved as its own row.
- Every raw resource load (rate series, portfolio report, asset currencies,
  exposure conversions, rate source lookups) is routed through
  `BuildContext.db_resource`, so repeated builders within one request never
  re-run the same query (see the module docstring of
  `backend.app.services.ai_export.dependencies`).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from backend.app.db.models import Asset, FxRate
from backend.app.schemas.common import Currency, OpenDateRangeModel
from backend.app.schemas.portfolio import (
    PortfolioHolding,
    PortfolioReportQuery,
    PortfolioReportResponse,
    PortfolioSummary,
)
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.fx_payloads import (
    FxConversionProvenancePayload,
    FxCurrentRatePayload,
    FxExposureBaseQuotePayload,
    FxExposureConversion,
    FxExposureConversionBasis,
    FxExposureConversionSummary,
    FxExposureKind,
    FxExposureLinkage,
    FxExposureProvenancePayload,
    FxExposureRow,
    FxPairIdentityPayload,
    FxRateDirection,
)
from backend.app.services.ai_export.components.resources import FxRateObservation, FxRateSeriesResource
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.technical_shared import load_fx_rate_series
from backend.app.services.ai_export.components.types import BuildScope, Domain, PeriodBehavior, ResourceKey
from backend.app.services.ai_export.dependencies import BuildContext, BuildContextScopeError
from backend.app.services.fx import convert_bulk
from backend.app.utils.financial.valuation_utils import compute_holding_value, normalize_quote_base_quantity

# Relative tolerance used to decide whether an independently-resolved exposure
# rate (via `_load_exposure_conversions`/`convert_bulk`) "reconciles" with the
# rate implied by a position row's own (native_amount, target_amount) pair
# (`target_amount / native_amount`). Both ultimately read the same `FxRate`
# table for the same date, so in the common case they match near-exactly;
# the tolerance only absorbs Decimal rounding-order differences, never a
# genuinely different rate. See `_position_row_conversion`.
_EXPOSURE_RATE_RECONCILIATION_TOLERANCE = Decimal("0.0005")


# =============================================================================
# Shared scope/series helpers
# =============================================================================


def _require_fx_scope(context: BuildContext) -> BuildScope:
    scope = context.scope
    if scope is None:
        raise BuildContextScopeError("FX core components require a BuildContext constructed with a BuildScope")
    if scope.domain is not Domain.FX:
        raise BuildContextScopeError(f"FX core components require BuildScope.domain == FX, got {scope.domain!r}")
    return scope


def _direction_for(from_currency: str, to_currency: str) -> FxRateDirection:
    """Direction of a from_currency->to_currency conversion given `FxRate`'s alphabetical storage.

    Mirrors (without depending on) `backend.app.services.fx.convert_bulk`'s own
    internal `direct` flag: DIRECT when the pair is already stored in the
    requested order (`from_currency < to_currency`), INVERSE when the stored
    row is the reverse of it. Callers must never pass equal currencies.
    """
    if from_currency == to_currency:
        raise ValueError("direction is undefined for identity conversions")
    return FxRateDirection.DIRECT if from_currency < to_currency else FxRateDirection.INVERSE


async def _load_rate_series(context: BuildContext) -> FxRateSeriesResource:
    """Loads the canonical daily base->quote rate series consumed by `fx.current_rate`/`fx.conversion_provenance`.

    Delegates to the technical sibling wave's own `load_fx_rate_series`
    (`backend.app.services.ai_export.components.technical_shared`), which
    already loads a warm-up-inclusive range under its own memoized resource
    key (`_FX_TECHNICAL_RATE_SERIES_RESOURCE`): reusing that call instead of
    this module's previous separate visible-period-only loader/resource key
    (`FX_RATE_SERIES_RESOURCE`) removes the two-range seam that module's
    docstring flagged as "a decision this technical wave cannot make
    unilaterally" - the parent integration gate makes it here (requirement
    4): one warm-up-inclusive rate series per request, shared by
    `fx.current_rate`/`fx.conversion_provenance` and every FX technical
    component, with `fx.current_rate`/`fx.conversion_provenance` simply
    selecting the visible `scope.snapshot_as_of` date out of the wider
    series - never truncating it.
    """
    _require_fx_scope(context)
    return await load_fx_rate_series(context)


def _observation_for_date(series: FxRateSeriesResource, target_date: date) -> FxRateObservation:
    for observation in series.observations:
        if observation.requested_date == target_date:
            return observation
    raise RuntimeError(f"FX rate series does not include an observation for {target_date.isoformat()}")


async def _load_rate_source(context: BuildContext, currency_a: str, currency_b: str, effective_date: date) -> str:
    """Looks up the authoritative `FxRate.source` for the (currency_a, currency_b) pair at `effective_date`.

    `currency_a`/`currency_b` are normalized to the alphabetical storage order
    internally; callers may pass them in either order. Raises if no matching
    row exists - this only happens if the caller already resolved a rate for
    that exact date through `convert_bulk`, so a missing row here indicates a
    genuine internal inconsistency, never a "provider route" this module
    should paper over.
    """
    stored_base, stored_quote = sorted((currency_a, currency_b))
    key = ResourceKey(f"fx_core.rate_source::{stored_base}::{stored_quote}::{effective_date.isoformat()}", str)

    async def _loader(session) -> str:
        stmt = select(FxRate.source).where(FxRate.base == stored_base, FxRate.quote == stored_quote, FxRate.date == effective_date)
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()
        if source is None:
            raise RuntimeError(f"no stored FxRate.source for {stored_base}/{stored_quote} on {effective_date.isoformat()} despite a previously resolved observation")
        return source

    return await context.db_resource(key, _loader)


# =============================================================================
# fx.pair_identity
# =============================================================================


def _build_pair_identity(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> FxPairIdentityPayload:
    scope = _require_fx_scope(context)
    base, quote = scope.base_currency, scope.quote_currency
    stored_base, stored_quote = sorted((base, quote))
    direction = FxRateDirection.DIRECT if base == stored_base else FxRateDirection.INVERSE
    return FxPairIdentityPayload(
        base_currency=base,
        quote_currency=quote,
        stored_base_currency=stored_base,
        stored_quote_currency=stored_quote,
        direction=direction,
    )


# =============================================================================
# fx.current_rate
# =============================================================================


async def _build_current_rate(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> FxCurrentRatePayload:
    scope = _require_fx_scope(context)
    series = await _load_rate_series(context)
    observation = _observation_for_date(series, scope.snapshot_as_of)
    direction = _direction_for(scope.base_currency, scope.quote_currency)
    staleness_days = (observation.requested_date - observation.actual_date).days
    return FxCurrentRatePayload(
        base_currency=scope.base_currency,
        quote_currency=scope.quote_currency,
        direction=direction,
        requested_date=observation.requested_date,
        effective_date=observation.actual_date,
        rate=observation.rate,
        is_backward_filled=observation.backward_filled,
        staleness_days=staleness_days,
    )


# =============================================================================
# fx.conversion_provenance
# =============================================================================


async def _build_conversion_provenance(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> FxConversionProvenancePayload:
    scope = _require_fx_scope(context)
    series = await _load_rate_series(context)
    observation = _observation_for_date(series, scope.snapshot_as_of)
    direction = _direction_for(scope.base_currency, scope.quote_currency)
    source = await _load_rate_source(context, scope.base_currency, scope.quote_currency, observation.actual_date)
    return FxConversionProvenancePayload(
        base_currency=scope.base_currency,
        quote_currency=scope.quote_currency,
        direction=direction,
        requested_date=observation.requested_date,
        effective_date=observation.actual_date,
        is_backward_filled=observation.backward_filled,
        source=source,
    )


# =============================================================================
# fx.exposure_base_quote
# =============================================================================


@dataclass(frozen=True, slots=True)
class _CashCandidate:
    linked_currency: str
    amount: Decimal
    broker_id: int | None


@dataclass(frozen=True, slots=True)
class _PositionCandidate:
    """One matched position exposure row, honestly reflecting what is derivable.

    `target_amount` is always `PortfolioHolding.current_value` directly - the
    portfolio valuation engine already expresses it in `BuildScope.target_currency`,
    so it is never re-converted here. `native_amount` is `None` when no honest
    native-currency amount can be attributed (`valuation_effective_currency`
    does not match `linked_currency`): see `_position_candidates`.
    """

    linked_currency: str
    linkage: FxExposureLinkage
    native_amount: Decimal | None
    target_amount: Decimal
    valuation_source: str | None
    asset_id: int
    broker_id: int | None


@dataclass(frozen=True, slots=True)
class _AssetFacts:
    currency: str
    quote_base_quantity: int


@dataclass(frozen=True, slots=True)
class _AssetFactsMapResource:
    by_asset_id: Mapping[int, _AssetFacts]


@dataclass(frozen=True, slots=True)
class _ExposureConversion:
    rate_per_unit: Decimal
    metadata: FxExposureConversion
    source: str | None


_FX_EXPOSURE_REPORT_RESOURCE = ResourceKey("fx_core.exposure_report", PortfolioReportResponse)


async def _load_exposure_report(context: BuildContext) -> PortfolioReportResponse:
    scope = _require_fx_scope(context)

    async def _loader(session) -> PortfolioReportResponse:
        # Local import: avoids importing the (heavier) portfolio service at
        # module load time for FX-only requests that never build exposure.
        from backend.app.services.portfolio_service import PortfolioService  # noqa: PLC0415

        query = PortfolioReportQuery(
            broker_ids=list(scope.broker_scope) or None,
            date_range=OpenDateRangeModel(start=scope.period_start, end=scope.period_end),
            target_currency=scope.target_currency,
            include_summary=True,
            include_history=False,
            include_allocation_history=False,
            include_breakdown=True,
            include_positions_contribution=False,
        )
        return await PortfolioService(session).get_report(scope.user_id, query)

    return await context.db_resource(_FX_EXPOSURE_REPORT_RESOURCE, _loader)


def _cash_candidates(summary: PortfolioSummary | None, pair: frozenset[str]) -> list[_CashCandidate]:
    if summary is None:
        return []
    candidates: list[_CashCandidate] = []
    if summary.by_broker:
        sources: list[tuple[int | None, Currency]] = [(breakdown.broker_id, balance) for breakdown in summary.by_broker for balance in breakdown.cash_balances]
    else:
        sources = [(None, balance) for balance in summary.cash_balances]
    for broker_id, balance in sources:
        amount = Decimal(str(balance.amount))
        if balance.code in pair and not amount.is_zero():
            candidates.append(_CashCandidate(linked_currency=balance.code, amount=amount, broker_id=broker_id))
    return candidates


async def _load_asset_facts(context: BuildContext, asset_ids: Sequence[int]) -> Mapping[int, _AssetFacts]:
    """Loads `Asset.currency`/`Asset.quote_base_quantity` for exposure linkage/native-amount math, memoized per request."""
    ordered_ids = sorted(set(asset_ids))
    if not ordered_ids:
        return {}
    key = ResourceKey(f"fx_core.asset_facts::{','.join(str(asset_id) for asset_id in ordered_ids)}", _AssetFactsMapResource)

    async def _loader(session) -> _AssetFactsMapResource:
        stmt = select(Asset.id, Asset.currency, Asset.quote_base_quantity).where(Asset.id.in_(ordered_ids))
        result = await session.execute(stmt)
        mapping = {asset_id: _AssetFacts(currency=currency, quote_base_quantity=normalize_quote_base_quantity(quote_base_quantity)) for asset_id, currency, quote_base_quantity in result.all()}
        missing = set(ordered_ids) - set(mapping)
        if missing:
            raise RuntimeError(f"assets not found while loading exposure trading currencies: {sorted(missing)}")
        return _AssetFactsMapResource(by_asset_id=mapping)

    resource = await context.db_resource(key, _loader)
    return resource.by_asset_id


def _native_amount_for_holding(holding: PortfolioHolding, quote_base_quantity: int) -> Decimal | None:
    """Honest native-currency amount for `holding`, in `holding.valuation_effective_currency`.

    Mirrors exactly how `backend.app.services.portfolio_engine` derived
    `holding.current_value` before converting it to `target_currency`:
    - MARKET_PRICE valuations scale by `quote_base_quantity` via the same
      `compute_holding_value` helper the engine itself uses (e.g. a bond
      quoted per 100 face value): `(quantity / quote_base_quantity) * price`.
    - LAST_BUY_PRICE/LAST_SEED_COST valuations do not: `effective_unit_price`
      there is already a true per-unit price (`quantity * price`).
    Returns `None` when `valuation_effective_unit_price` is unknown - callers
    must not fabricate a native amount in that case.
    """
    if holding.valuation_effective_unit_price is None:
        return None
    price = Decimal(str(holding.valuation_effective_unit_price))
    quantity = Decimal(str(holding.quantity))
    if holding.valuation_source == "MARKET_PRICE":
        return compute_holding_value(quantity, price, quote_base_quantity)
    return quantity * price


async def _position_candidates(context: BuildContext, summary: PortfolioSummary | None, pair: frozenset[str]) -> list[_PositionCandidate]:
    if summary is None or not summary.holdings:
        return []
    asset_facts = await _load_asset_facts(context, [holding.asset_id for holding in summary.holdings])
    candidates: list[_PositionCandidate] = []
    for holding in summary.holdings:
        facts = asset_facts.get(holding.asset_id)
        trading_currency = facts.currency if facts is not None else None
        valuation_currency = holding.valuation_effective_currency

        native_amount: Decimal | None = None
        if valuation_currency is not None and valuation_currency in pair:
            # Prioritize the currency the value is *actually* denominated in:
            # only this currency can produce an honest native_amount below.
            linked_currency = valuation_currency
            linkage = FxExposureLinkage.TRADING_CURRENCY if valuation_currency == trading_currency else FxExposureLinkage.VALUATION_CURRENCY
            quote_base_quantity = facts.quote_base_quantity if facts is not None else 1
            native_amount = _native_amount_for_holding(holding, quote_base_quantity)
        elif trading_currency is not None and trading_currency in pair:
            # The asset trades in a currency that matches the pair, but the
            # value was actually valued in a *different* currency (or none is
            # known) - real exposure still exists, but native_amount must not
            # be fabricated by dividing/multiplying a different-currency value.
            linked_currency = trading_currency
            linkage = FxExposureLinkage.TRADING_CURRENCY
        else:
            continue

        if holding.current_value is None:
            raise RuntimeError(f"asset {holding.asset_id}: exposure position value unavailable (missing current_value)")
        target_amount = Decimal(str(holding.current_value))
        if not target_amount.is_finite():
            raise RuntimeError(f"asset {holding.asset_id}: exposure position value is not finite")
        candidates.append(
            _PositionCandidate(
                linked_currency=linked_currency,
                linkage=linkage,
                native_amount=native_amount,
                target_amount=target_amount,
                valuation_source=holding.valuation_source,
                asset_id=holding.asset_id,
                broker_id=holding.broker_id,
            )
        )
    return candidates


async def _load_exposure_conversions(
    context: BuildContext,
    linked_currencies: Sequence[str],
    target_currency: str,
    as_of: date,
) -> Mapping[str, _ExposureConversion]:
    """Resolves one rate-per-unit conversion per distinct `linked_currency`, memoized per request.

    Identical `(linked_currencies, target_currency, as_of)` inputs (e.g. one
    call from `fx.exposure_base_quote` and one from `fx.exposure_provenance`
    over the same resolved currency set) hit the same `db_resource` cache
    slot - no duplicate `convert_bulk`/source queries within one request.
    """
    conversions: dict[str, _ExposureConversion] = {}
    unique_currencies = sorted(set(linked_currencies))
    for currency in unique_currencies:
        if currency == target_currency:
            conversions[currency] = _ExposureConversion(
                rate_per_unit=Decimal(1),
                metadata=FxExposureConversion(basis=FxExposureConversionBasis.IDENTITY, direction=None, requested_date=as_of, effective_date=as_of, is_backward_filled=False),
                source=None,
            )
    to_convert = [currency for currency in unique_currencies if currency != target_currency]
    if not to_convert:
        return conversions

    key = ResourceKey(f"fx_core.exposure_rates::{'|'.join(to_convert)}::{target_currency}::{as_of.isoformat()}", list)

    async def _loader(session) -> list:
        batch = [(Currency(code=currency, amount=Decimal(1)), target_currency, as_of) for currency in to_convert]
        results, _errors = await convert_bulk(session, batch, raise_on_error=True)
        return results

    raw_results = await context.db_resource(key, _loader)
    for currency, result in zip(to_convert, raw_results, strict=True):
        if result is None:
            raise RuntimeError(f"convert_bulk unexpectedly returned no result for {currency}->{target_currency} on {as_of.isoformat()}")
        converted, actual_date, backward_filled = result
        if converted.code != target_currency or converted.amount <= 0:
            raise RuntimeError(f"invalid exposure conversion result for {currency}->{target_currency} on {as_of.isoformat()}")
        direction = _direction_for(currency, target_currency)
        source = await _load_rate_source(context, currency, target_currency, actual_date)
        conversions[currency] = _ExposureConversion(
            rate_per_unit=Decimal(str(converted.amount)),
            metadata=FxExposureConversion(basis=FxExposureConversionBasis.RESOLVED_RATE, direction=direction, requested_date=as_of, effective_date=actual_date, is_backward_filled=bool(backward_filled)),
            source=source,
        )
    return conversions


def _row_sort_key(row: FxExposureRow) -> tuple:
    return (
        row.kind.value,
        row.linkage.value,
        row.linked_currency,
        row.broker_id is None,
        row.broker_id or 0,
        row.asset_id is None,
        row.asset_id or 0,
    )


def _rate_reconciles(implied_rate: Decimal, resolved_rate: Decimal) -> bool:
    """Whether an independently-resolved rate matches a position row's own implied rate.

    Both `implied_rate` (`target_amount / native_amount`) and `resolved_rate`
    (from `_load_exposure_conversions`) ultimately read the same `FxRate` rows
    for the same date (see `backend.app.services.portfolio_engine`'s own
    `convert_bulk` usage), so they should match near-exactly; the tolerance
    only absorbs Decimal rounding-order differences.
    """
    if resolved_rate <= 0:
        return False
    return abs(implied_rate - resolved_rate) <= resolved_rate * _EXPOSURE_RATE_RECONCILIATION_TOLERANCE


def _position_row_conversion(candidate: _PositionCandidate, resolved: _ExposureConversion) -> FxExposureConversion:
    """Per-row conversion provenance for one position, never fabricating a rate.

    - `linked_currency == target_currency`: reuse the trivial IDENTITY metadata
      as-is (native_amount, when known, already equals target_amount by
      construction).
    - Otherwise, only claim the independently-resolved RESOLVED_RATE rate as
      this row's provenance when it reconciles (`_rate_reconciles`) with the
      rate implied by this row's own (native_amount, target_amount) pair -
      never to recompute target_amount, only to describe it honestly.
    - In every other case (native_amount unknown, or it does not reconcile),
      fall back to ENGINE_VALUATION: target_amount is asserted to come
      directly from the portfolio valuation engine, no rate is fabricated.
    """
    if resolved.metadata.basis is FxExposureConversionBasis.IDENTITY:
        return resolved.metadata
    if candidate.native_amount is not None and candidate.native_amount != 0:
        implied_rate = candidate.target_amount / candidate.native_amount
        if _rate_reconciles(implied_rate, resolved.rate_per_unit):
            return resolved.metadata
    return FxExposureConversion(
        basis=FxExposureConversionBasis.ENGINE_VALUATION,
        direction=None,
        requested_date=resolved.metadata.requested_date,
        effective_date=resolved.metadata.requested_date,
        is_backward_filled=False,
    )


async def _build_exposure_base_quote(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> FxExposureBaseQuotePayload:
    scope = _require_fx_scope(context)
    report = await _load_exposure_report(context)
    pair = frozenset({scope.base_currency, scope.quote_currency})
    cash_candidates = _cash_candidates(report.summary, pair)
    position_candidates = await _position_candidates(context, report.summary, pair)

    linked_currencies = sorted({candidate.linked_currency for candidate in cash_candidates} | {candidate.linked_currency for candidate in position_candidates})
    conversions = await _load_exposure_conversions(context, linked_currencies, scope.target_currency, scope.snapshot_as_of)

    rows: list[FxExposureRow] = []
    for candidate in cash_candidates:
        conversion = conversions[candidate.linked_currency]
        rows.append(
            FxExposureRow(
                kind=FxExposureKind.CASH,
                linkage=FxExposureLinkage.CASH_CURRENCY,
                linked_currency=candidate.linked_currency,
                native_amount=candidate.amount,
                target_amount=candidate.amount * conversion.rate_per_unit,
                conversion=conversion.metadata,
                asset_id=None,
                broker_id=candidate.broker_id,
            )
        )
    for candidate in position_candidates:
        resolved = conversions[candidate.linked_currency]
        row_conversion = _position_row_conversion(candidate, resolved)
        rows.append(
            FxExposureRow(
                kind=FxExposureKind.POSITION,
                linkage=candidate.linkage,
                linked_currency=candidate.linked_currency,
                # None whenever the chosen basis is ENGINE_VALUATION (either no honest
                # native amount was derivable, or a known one didn't reconcile with the
                # independently-resolved rate) - never claim a native amount alongside a
                # basis that says none was used (see `FxExposureRow._check_consistency`).
                native_amount=candidate.native_amount if row_conversion.basis is not FxExposureConversionBasis.ENGINE_VALUATION else None,
                # Always the engine's own value, already in target_currency - never re-derived from a rate.
                target_amount=candidate.target_amount,
                conversion=row_conversion,
                valuation_source=candidate.valuation_source,
                asset_id=candidate.asset_id,
                broker_id=candidate.broker_id,
            )
        )

    return FxExposureBaseQuotePayload(
        base_currency=scope.base_currency,
        quote_currency=scope.quote_currency,
        target_currency=scope.target_currency,
        as_of=scope.snapshot_as_of,
        broker_scope=scope.broker_scope,
        rows=tuple(sorted(rows, key=_row_sort_key)),
    )


# =============================================================================
# fx.exposure_provenance
# =============================================================================


async def _build_exposure_provenance(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> FxExposureProvenancePayload:
    scope = _require_fx_scope(context)
    base_quote_envelope = dependencies["fx.exposure_base_quote"]
    base_quote_payload = FxExposureBaseQuotePayload.model_validate(base_quote_envelope.payload)

    # Resolve the *full* distinct-currency set present in the sibling rows -
    # identical to what `_build_exposure_base_quote` already requested, so this
    # hits the same memoized `db_resource` slot (no duplicate `convert_bulk`
    # call) even though the reported `summaries` below may cover fewer currencies.
    all_linked_currencies = sorted({row.linked_currency for row in base_quote_payload.rows})
    conversions = await _load_exposure_conversions(context, all_linked_currencies, scope.target_currency, scope.snapshot_as_of)

    # Only report a currency here when at least one sibling row in that currency
    # actually used a resolved/identity conversion (`conversion.basis is not
    # ENGINE_VALUATION`) - a currency whose only rows fell back to
    # ENGINE_VALUATION never had this conversion applied/reconciled to any of
    # them, so surfacing it here would misrepresent it as their provenance (see
    # `FxExposureProvenancePayload`'s docstring).
    provenance_currencies = sorted({row.linked_currency for row in base_quote_payload.rows if row.conversion.basis is not FxExposureConversionBasis.ENGINE_VALUATION})

    summaries = tuple(
        FxExposureConversionSummary(
            linked_currency=currency,
            target_currency=scope.target_currency,
            direction=conversions[currency].metadata.direction,
            requested_date=conversions[currency].metadata.requested_date,
            effective_date=conversions[currency].metadata.effective_date,
            is_backward_filled=conversions[currency].metadata.is_backward_filled,
            source=conversions[currency].source,
        )
        for currency in provenance_currencies
    )
    return FxExposureProvenancePayload(
        base_currency=scope.base_currency,
        quote_currency=scope.quote_currency,
        target_currency=scope.target_currency,
        conversions=summaries,
    )


# =============================================================================
# ComponentSpec catalog fragment
# =============================================================================
#
# component_id/domains/dependencies/period_behavior below are deliberately
# identical to the placeholders in
# `backend.app.services.ai_export.components.catalog._FX_COMPONENTS` for the
# same five IDs, so a future catalog wiring can swap builders without
# changing any dataset/analysis that already references these IDs.

FX_CORE_COMPONENTS: tuple[ComponentSpec, ...] = (
    ComponentSpec(
        component_id="fx.pair_identity",
        version=1,
        domains=frozenset({Domain.FX}),
        output_model=FxPairIdentityPayload,
        builder=_build_pair_identity,
        period_behavior=PeriodBehavior.NONE,
    ),
    ComponentSpec(
        component_id="fx.current_rate",
        version=1,
        domains=frozenset({Domain.FX}),
        output_model=FxCurrentRatePayload,
        builder=_build_current_rate,
        dependencies=("fx.pair_identity",),
        period_behavior=PeriodBehavior.AS_OF,
    ),
    ComponentSpec(
        component_id="fx.conversion_provenance",
        version=1,
        domains=frozenset({Domain.FX}),
        output_model=FxConversionProvenancePayload,
        builder=_build_conversion_provenance,
        period_behavior=PeriodBehavior.NONE,
    ),
    ComponentSpec(
        component_id="fx.exposure_base_quote",
        version=1,
        domains=frozenset({Domain.FX}),
        output_model=FxExposureBaseQuotePayload,
        builder=_build_exposure_base_quote,
        period_behavior=PeriodBehavior.WINDOWED,
    ),
    ComponentSpec(
        component_id="fx.exposure_provenance",
        version=1,
        domains=frozenset({Domain.FX}),
        output_model=FxExposureProvenancePayload,
        builder=_build_exposure_provenance,
        dependencies=("fx.exposure_base_quote",),
        period_behavior=PeriodBehavior.NONE,
    ),
)


__all__ = ["FX_CORE_COMPONENTS"]
