"""
FX rate sync from the providers: the pair-based sync along the user's conversion routes (``sync_pairs_bulk``), with
the cache of the provider fetches, and the unwired multi-provider orchestrator (``ensure_rates_multi_source``).
"""

import asyncio
import time
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, func, or_
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.app.db.models import FxConversionRoute, FxRate
from backend.app.db.precision import fx_rate_limits_text, storable_fx_rate
from backend.app.db.session import get_async_engine
from backend.app.logging_config import get_logger
from backend.app.schemas.refresh import FXSyncBulkResponse, FXSyncLegDetail, FXSyncPairResult, SyncDateRangeModel, SyncStatus
from backend.app.services.fx.base import FXProviderStartDate, FXRateLimitedError, FXServiceError
from backend.app.services.fx.conversion import compute_chain_rate
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx.runtime import call_fx_provider, configured_fx_provider, settings_cache_part
from backend.app.services.fx.storage import normalize_storable_rate
from backend.app.utils.datetime_utils import EARLIEST_RANGE_START
from backend.app.utils.runtime.cache import clear_cache, get_ttl_cache
from backend.app.utils.sql_chunks import chunks

logger = get_logger(__name__)

# Cache for FX provider fetch responses — TTL 5min since FX rates update daily.
# Prevents provider rate-limiting if user triggers repeated syncs.
_fx_fetch_cache = get_ttl_cache("fx_provider_responses", maxsize=200, ttl=300)


def _is_date_within_sync_range(target_date: date, start_date: FXProviderStartDate, end_date: date) -> bool:
    """Return True when target_date falls inside requested sync range, never before ``EARLIEST_RANGE_START`` (X-R65)."""
    if target_date < EARLIEST_RANGE_START:
        return False
    if start_date == "min":
        return target_date <= end_date
    return start_date <= target_date <= end_date


def _warn_unusable_rates(pair: str, provider: str, days: list[date]) -> None:
    """One warning per pair and sync for its rates ``fx_rates.rate`` cannot keep, skipped (X-R38): never stored, never
    raising, the pair's other dates stored. At most ten dates are listed; ``skipped`` counts them all."""
    if not days:
        return
    ordered = sorted(set(days))
    logger.warning(
        "FX rates skipped: the column cannot keep them",
        pair=pair,
        provider=provider,
        skipped=len(ordered),
        dates=[day.isoformat() for day in ordered[:10]],
        limits=fx_rate_limits_text(),
    )


def _collect_leg_rates(
    rates_by_currency: dict,
    provider_code: str,
    leg_rates: dict[tuple, Decimal],
    leg_unusable: dict[tuple[str, str, str], list[date]],
) -> None:
    """A provider's observations into ``leg_rates``, normalized (alphabetical pair, the rate inverted when needed). One
    that is not a finite rate above 0, or whose inverse overflows or underflows to 0 (X-R50), goes into ``leg_unusable``
    instead: skipped, and said by the pairs whose route uses the leg (X-R38)."""
    for _currency, observations in rates_by_currency.items():
        for obs_date, obs_base, obs_quote, rate in observations:
            normalized = normalize_storable_rate(obs_base, obs_quote, rate)
            if normalized is None:
                leg_unusable.setdefault((min(obs_base, obs_quote), max(obs_base, obs_quote), provider_code), []).append(obs_date)
                continue
            norm_base, norm_quote, norm_rate = normalized
            leg_rates[(norm_base, norm_quote, obs_date)] = norm_rate


def _storable_chain_rates(route, steps: list[dict], leg_rates: dict[tuple, Decimal], dates: list[date]) -> tuple[list[tuple[date, str, str, Decimal]], list[date]]:
    """Each date's chain rate, normalized and truncated to what ``fx_rates.rate`` keeps, and the dates skipped (X-R38): a
    leg present but unusable, or a chain rate the column cannot keep (``1E+20``, or 0 once truncated). A date a leg lacks
    is ``compute_chain_rate``'s strict date matching, not a skip."""
    computed: list[tuple[date, str, str, Decimal]] = []
    unusable: list[date] = []
    for d in dates:
        chain_rate = compute_chain_rate(steps, leg_rates, d)
        if chain_rate is None:
            if all((min(s["from"], s["to"]), max(s["from"], s["to"]), d) in leg_rates for s in steps):
                unusable.append(d)
            continue
        normalized = normalize_storable_rate(route.base, route.quote, chain_rate)
        stored = None if normalized is None else storable_fx_rate(normalized[2])
        if stored is None:
            unusable.append(d)
            continue
        computed.append((d, normalized[0], normalized[1], stored))
    return computed, unusable


# ============================================================================
# MULTI-PROVIDER ORCHESTRATOR
# ============================================================================
# Intentionally unwired: no production caller invokes this function (verified
# 2026-09-03 — only backend/test_scripts/test_db/test_fx_rates_persistence.py).
# The live sync path is sync_pairs_bulk(), which walks the user's configured
# conversion routes with provider fallback and the MANUAL sentinel. This older
# single-provider orchestrator survives as the designated extension point for
# future multi-base providers (see the ARCHITECTURAL NOTE on base_currencies
# above): when a provider returning multiple base currencies lands, explicit
# base_currency routing belongs here. The persistence tests double as the
# contract spec for that future wiring — remove the function only together
# with them.
async def _stored_rates(session: AsyncSession, conditions: list) -> list[FxRate]:
    """The stored rates matching any of ``conditions`` (one per pair and range), in chunks of OR terms (MF-SEC9a).

    SQLite refuses an OR of a thousand terms: a sync of about 46 currencies has that many pairs. The refusal was
    caught by the caller as «table missing», so every rate was counted as new; read in chunks, the change detection holds.
    """
    rates: list[FxRate] = []
    for chunk in chunks(conditions):
        result = await session.execute(select(FxRate).where(or_(*chunk)))
        rates.extend(result.scalars().all())
    return rates


async def ensure_rates_multi_source(  # noqa: C901 — linear staged sync pipeline, per-item checks only
    session,  # AsyncSession
    date_range: tuple[date, date],
    currencies: list[str],
    provider_code: str,
    base_currency: str | None = None,
) -> dict[str, int]:
    """
    Synchronize FX rates using configured provider.

    This orchestrator uses the provider system to fetch rates from the appropriate source.
    It supports both single-base and multi-base providers.

    Algorithm:
    1. Get provider instance from factory
    2. Validate base_currency (if specified) against provider's supported bases
    3. Fetch rates from provider API with specified base
    4. Normalize rates for storage (alphabetical ordering)
    5. Batch upsert to database

    Args:
        session: Database session
        date_range: (start_date, end_date) inclusive
        currencies: List of currency codes to sync
        provider_code: Provider to use (default: 'ECB')
        base_currency: Base currency to use for multi-base providers.
                      If None, uses provider's default base_currency.
                      Must be one of provider's base_currencies.

    Returns:
        Dict with sync statistics:
        {
            'provider': 'ECB',
            'base_currency': 'EUR',
            'total_fetched': 100,
            'total_changed': 50,
            'currencies_synced': ['USD', 'GBP', ...]
        }

    Raises:
        ValueError: If base_currency is not supported by provider
        FXServiceError: If provider not found or API request fails
    """

    if not provider_code:
        raise FXServiceError("Provider code is required")

    # MANUAL provider: skip sync silently — manual pairs don't auto-sync
    if provider_code.upper() == "MANUAL":
        logger.debug(f"MANUAL provider: skipping sync for {len(currencies)} currencies " f"({date_range[0]} to {date_range[1]}) — manual-only pair")
        return {
            "provider": "MANUAL",
            "base_currency": "",
            "total_fetched": 0,
            "total_changed": 0,
            "currencies_synced": [],
        }

    # Get provider instance from registry, with the instance's settings
    provider = await configured_fx_provider(provider_code)
    if not provider:
        available = [p["code"] for p in FXProviderRegistry.list_providers()]
        raise FXServiceError(f"Unknown FX provider: {provider_code}. " f"Available providers: {', '.join(available) if available else 'none registered'}")

    # Validate base_currency if specified
    if base_currency is not None:
        if base_currency not in provider.base_currencies:
            raise ValueError(f"Provider {provider.code} does not support {base_currency} as base. " f"Supported bases: {', '.join(provider.base_currencies)}")

    actual_base = base_currency if base_currency else provider.base_currency

    logger.debug(f"Syncing FX rates using {provider.name} ({provider.code}) " f"with base {actual_base} " f"for {len(currencies)} currencies from {date_range[0]} to {date_range[1]}")

    start_date, end_date = date_range

    # ========================================================================
    # PARALLEL EXECUTION: API fetch + DB query
    # ========================================================================

    # Build DB query for all possible pairs in the requested currencies and date range
    # This query fetches ALL rates between any of the requested currencies
    # (e.g., if currencies=['USD', 'GBP'], fetch USD/GBP, GBP/USD, etc.)
    all_pairs_conditions = []

    # Pairs between requested currencies
    for i, curr1 in enumerate(currencies):
        for curr2 in currencies[i + 1 :]:  # Avoid duplicates, only pairs
            # Store alphabetically: smaller currency as base
            if curr1 < curr2:
                base, quote = curr1, curr2
            else:
                base, quote = curr2, curr1

            all_pairs_conditions.append(
                and_(
                    FxRate.base == base,
                    FxRate.quote == quote,
                    FxRate.date >= start_date,
                    FxRate.date <= end_date,
                )
            )

    # Also include pairs with the base currency (if different from requested currencies)
    if actual_base not in currencies:
        for currency in currencies:
            if actual_base < currency:
                base, quote = actual_base, currency
            else:
                base, quote = currency, actual_base

            all_pairs_conditions.append(
                and_(
                    FxRate.base == base,
                    FxRate.quote == quote,
                    FxRate.date >= start_date,
                    FxRate.date <= end_date,
                )
            )

    # Create tasks for parallel execution
    fetch_task = asyncio.create_task(call_fx_provider(provider, lambda: provider.fetch_rates(date_range, currencies, base_currency=base_currency)))

    if all_pairs_conditions:
        db_task = asyncio.create_task(_stored_rates(session, all_pairs_conditions))
    else:
        # No pairs to query (shouldn't happen, but handle gracefully)
        db_task = None

    # Wait for both operations to complete
    # Handle case where fx_rates table doesn't exist yet (fresh database)
    if db_task:
        try:
            rates_by_currency, existing_rates = await asyncio.gather(fetch_task, db_task)
            existing_lookup = {(rate.base, rate.quote, rate.date): rate.rate for rate in existing_rates}
            logger.debug(f"Change detection: {len(existing_lookup)} existing rate(s) found in DB " f"for {len(all_pairs_conditions)} pair condition(s)")
        except Exception as e:
            # If table doesn't exist or other DB error, proceed with empty lookup
            # All rates will be considered new inserts
            logger.warning(f"Could not query existing rates (table may not exist yet): {e}. " f"Proceeding with fresh sync - all rates will be inserted.")
            rates_by_currency = await fetch_task
            existing_lookup = {}
    else:
        rates_by_currency = await fetch_task
        existing_lookup = {}

    # ========================================================================
    # Process API results and normalize for storage
    # ========================================================================

    # Statistics
    total_fetched = 0
    total_changed = 0
    currencies_synced = []

    # Normalize all observations and collect unique pairs from API
    all_normalized = []  # [(currency, obs_date, base, quote, rate as stored), ...]
    api_pairs = set()  # {(base, quote, date), ...}
    kept_by_currency: dict[str, list[tuple[date, str, str, Decimal]]] = {}  # what the batch insert writes

    for currency, observations in rates_by_currency.items():
        if not observations:
            logger.debug(f"No rates available for {currency} in date range")
            continue

        currencies_synced.append(currency)
        total_fetched += len(observations)

        # Normalize for storage (alphabetical ordering), truncated to what fx_rates.rate keeps. An observation it cannot
        # keep is skipped, never stored and never raising, and said once for its pair (X-R38)
        skipped: dict[str, list[date]] = {}
        for obs_date, base, quote, rate in observations:
            normalized = normalize_storable_rate(base, quote, rate)
            stored = None if normalized is None else storable_fx_rate(normalized[2])
            if stored is None:
                skipped.setdefault(f"{min(base, quote)}/{max(base, quote)}", []).append(obs_date)
                continue
            norm_base, norm_quote, _norm_rate = normalized
            all_normalized.append((currency, obs_date, norm_base, norm_quote, stored))
            kept_by_currency.setdefault(currency, []).append((obs_date, norm_base, norm_quote, stored))
            api_pairs.add((norm_base, norm_quote, obs_date))
        for pair, days in skipped.items():
            _warn_unusable_rates(pair, provider.code, days)

    # ========================================================================
    # Compare DB vs API: Log rates in DB but not in API
    # ========================================================================

    db_only_pairs = set(existing_lookup.keys()) - api_pairs
    if db_only_pairs:
        logger.debug(f"Found {len(db_only_pairs)} rate(s) in database not returned by API " f"(this is normal if API doesn't provide historical data for some pairs)")
        # Optional: Log first few examples at debug level
        for base, quote, rate_date in list(db_only_pairs)[:5]:
            logger.log(5, f"  DB-only rate: {base}/{quote} on {rate_date}")

    # Track changes per currency (for logging)
    changes_by_currency = {}

    # Process each normalized observation
    for currency, obs_date, base, quote, rate_value in all_normalized:
        key = (base, quote, obs_date)
        old_rate = existing_lookup.get(key)

        # The new rate is already truncated to DB precision (storable_fx_rate)
        # This prevents false "updates" when values are identical after truncation
        rate_truncated = rate_value

        if old_rate is None:
            # New insert
            if currency not in changes_by_currency:
                changes_by_currency[currency] = 0
            changes_by_currency[currency] += 1
        else:
            # The old rate as the column keeps it: a legacy one it cannot keep (inf, 1e60, 0) is None, a change the
            # new rate overwrites, never a raise (X-R38)
            old_rate_truncated = storable_fx_rate(old_rate)
            if old_rate_truncated != rate_truncated:
                # Updated value (only if different after truncation)
                if currency not in changes_by_currency:
                    changes_by_currency[currency] = 0
                changes_by_currency[currency] += 1
                logger.log(5, f"Updated rate: {base}/{quote} on {obs_date}: {old_rate_truncated} -> {rate_truncated}")
        # else: Same value after truncation, no change to log

    total_changed = sum(changes_by_currency.values())

    if total_changed == 0 and total_fetched > 0:
        logger.debug(f"All {total_fetched} fetched rate(s) already exist in DB with same values " f"(existing_lookup={len(existing_lookup)}, all_normalized={len(all_normalized)})")

    # Process each currency for batch insert
    for currency, observations in rates_by_currency.items():
        if not observations:
            continue

        # Normalized and truncated to DB precision above, the observations no column can keep left out (X-R38)
        normalized_observations = kept_by_currency.get(currency, [])

        if normalized_observations:
            _, base, quote, _ = normalized_observations[0]
            changed_count = changes_by_currency.get(currency, 0)

            # Batch INSERT/UPDATE with truncated rates
            values_list = [
                {
                    "date": obs_date,
                    "base": base,
                    "quote": quote,
                    "rate": rate_value,
                    "source": provider.code,
                    "fetched_at": func.current_timestamp(),
                }
                for obs_date, base, quote, rate_value in normalized_observations
            ]

            batch_stmt = insert(FxRate).values(values_list)
            batch_stmt = batch_stmt.on_conflict_do_update(
                index_elements=["date", "base", "quote"],
                set_={
                    "rate": batch_stmt.excluded.rate,
                    "source": batch_stmt.excluded.source,
                    "fetched_at": func.current_timestamp(),
                },
            )

            await session.execute(batch_stmt)

            logger.debug(f"Synced {currency}: {len(observations)} fetched, " f"{changed_count} changed")

    await session.commit()

    logger.info(f"Sync complete: {total_fetched} rates fetched, {total_changed} changed " f"from {provider.name} using base {actual_base}")

    return {
        "provider": provider.code,
        "base_currency": actual_base,
        "total_fetched": total_fetched,
        "total_changed": total_changed,
        "currencies_synced": currencies_synced,
    }


# ============================================================================
# PAIR-BASED SYNC (New API)
# ============================================================================


async def _count_actual_changes(
    session,  # AsyncSession
    computed_rates: list[tuple[date, str, str, Decimal]],
) -> int:
    """
    Count how many of the computed rates are actually new or changed vs DB.

    Loads existing rates for the same (base, quote, date) tuples from the DB,
    compares with truncated precision, and returns the count of genuine changes.
    This avoids reporting points_changed == points_fetched when re-syncing
    the same date range with identical data.

    Args:
        session: AsyncSession for DB queries
        computed_rates: list of (date, base, quote, rate) — rate already truncated

    Returns:
        Number of rates that are new inserts or actual value changes.
    """
    if not computed_rates:
        return 0

    # Build lookup of new rates
    _new_lookup = {(d, b, q): r for d, b, q, r in computed_rates}

    # Load existing rates for comparison
    conditions = []
    for d, b, q, _ in computed_rates:
        conditions.append(and_(FxRate.base == b, FxRate.quote == q, FxRate.date == d))

    # Batch query — chunk if too many conditions (SQLite limit ~999 params)
    existing_lookup: dict[tuple, Decimal] = {}
    chunk_size = 200
    for i in range(0, len(conditions), chunk_size):
        chunk = conditions[i : i + chunk_size]
        stmt = select(FxRate.base, FxRate.quote, FxRate.date, FxRate.rate).where(or_(*chunk))
        result = await session.execute(stmt)
        for row in result.all():
            existing_lookup[(row[2], row[0], row[1])] = row[3]

    # Count changes
    changed = 0
    for d, b, q, new_rate in computed_rates:
        key = (d, b, q)
        old_rate = existing_lookup.get(key)
        if old_rate is None:
            # New insert
            changed += 1
        elif storable_fx_rate(old_rate) != new_rate:
            # Value actually changed; a legacy rate no column can keep (inf, 1e60, 0) is None: a change, never a raise (X-R38)
            changed += 1
    return changed


def _note_provider_failure(provider_code: str, error: Exception, provider_refusals: dict[str, float | None]) -> None:
    """Log a provider's failed fetch; a pause after «too many requests» is recorded for the results, at INFO level."""
    if isinstance(error, FXRateLimitedError):
        provider_refusals[provider_code.upper()] = error.retry_after
        logger.info("FX provider paused after too many requests: its legs fail, the next route is tried", provider=provider_code, retry_after=error.retry_after)
        return
    logger.exception(f"Provider {provider_code} fetch failed: {error}")


def _with_fx_refusal(result: FXSyncPairResult, routes: list[FxConversionRoute], provider_refusals: dict[str, float | None]) -> FXSyncPairResult:
    """``result`` marked ``RATE_LIMITED`` when it failed, wholly or partly, and one of its routes uses a provider that
    refused for too many requests or was paused. ``retry_after`` is the shortest wait among them: the first moment a
    route may work again. A pair another route served in full stays as it is.
    """
    if result.status not in (SyncStatus.FAILED, SyncStatus.PARTIAL) or not provider_refusals:
        return result
    providers = {step["provider"].upper() for route in routes for step in route.parsed_steps}
    waits = [provider_refusals[code] for code in providers if code in provider_refusals]
    if not waits:
        return result
    known = [wait for wait in waits if wait is not None]
    return result.model_copy(update={"error_code": FXRateLimitedError.error_code, "retry_after": min(known) if known else None})


async def sync_pairs_bulk(  # noqa: C901 — TODO(P2-refactor): 3-phase concurrent orchestrator with nested closures
    session,  # AsyncSession — used only for reading route config
    pairs: list[str],  # ["EUR-USD", "CHF-CNY"]
    date_range: tuple[FXProviderStartDate, date],
) -> "FXSyncBulkResponse":
    """
    Sync multiple FX pairs using the 3-phase pipeline:

    Phase 1: Collect legs from all routes, group by provider, create Events
    Phase 2: Fetch in parallel per provider, populate leg_rates, signal Events
    Phase 3: Route coroutines await Events, compute chain rates, upsert+commit

    Parallelization:
    - Inter-provider: different providers fetched in parallel
    - Intra-provider: currencies within same provider fetched in parallel (asyncio.gather in ECB/FED/BOE)
    - Route computation: routes awaiting different legs proceed as soon as their data is ready

    Commit per pair (not atomic bulk): partial success OK.
    """
    start_date, end_date = date_range
    _t_start_ns = time.monotonic_ns()

    # Load ALL route configurations in one query
    stmt = select(FxConversionRoute).order_by(FxConversionRoute.base, FxConversionRoute.quote, FxConversionRoute.priority)
    db_result = await session.execute(stmt)
    all_routes = db_result.scalars().all()

    # Build lookup: (base, quote) → [route1, route2, ...] ordered by priority
    route_lookup: dict[tuple[str, str], list] = {}
    for r in all_routes:
        key = (r.base, r.quote)
        if key not in route_lookup:
            route_lookup[key] = []
        route_lookup[key].append(r)

    # ── Phase 1: Collect legs, group by provider, create Events ──
    # For each pair, collect legs from ALL routes (for fallback support)
    pair_routes_map: dict[str, list[FxConversionRoute]] = {}  # pair_slug → [route1, route2, ...]
    provider_legs: dict[str, set[str]] = {}  # provider_code → {target_currencies}
    leg_events: dict[tuple[str, str, str], asyncio.Event] = {}  # (norm_base, norm_quote, provider) → Event
    leg_rates: dict[tuple, Decimal] = {}  # (norm_base, norm_quote, date) → rate
    leg_errors: dict[tuple[str, str, str], str] = {}  # (norm_base, norm_quote, provider) → error msg
    leg_unusable: dict[tuple[str, str, str], list[date]] = {}  # (norm_base, norm_quote, provider) → dates not normalizable (X-R38)
    provider_refusals: dict[str, float | None] = {}  # PROVIDER CODE (upper) → retry_after: paused or refused for too many requests

    for pair_slug in pairs:
        base, quote = pair_slug.split("-")
        routes = route_lookup.get((base, quote), [])
        if not routes:
            pair_routes_map[pair_slug] = []
            continue

        pair_routes_map[pair_slug] = routes

        # Collect legs from ALL routes (not just primary) so fallback data is available
        for route in routes:
            steps = route.parsed_steps

            # Skip MANUAL-only routes
            if all(s["provider"].upper() == "MANUAL" for s in steps):
                continue

            for step in steps:
                provider_code = step["provider"]
                if provider_code.upper() == "MANUAL":
                    continue

                provider = FXProviderRegistry.get_provider_instance(provider_code)
                if not provider:
                    continue

                fc, tc = step["from"], step["to"]
                base_cur = provider.base_currency

                # Determine target currency from provider's perspective
                if fc == base_cur:
                    target_cur = tc
                elif tc == base_cur:
                    target_cur = fc
                else:
                    # Neither from nor to is the provider's base — error
                    continue

                if provider_code not in provider_legs:
                    provider_legs[provider_code] = set()
                provider_legs[provider_code].add(target_cur)

                # Create Event for this leg
                norm_b = min(fc, tc)
                norm_q = max(fc, tc)
                leg_key = (norm_b, norm_q, provider_code)
                if leg_key not in leg_events:
                    leg_events[leg_key] = asyncio.Event()

    # ── Phase 2: Fetch in parallel per provider ──
    async def _fetch_provider(provider_code: str, target_currencies: set[str]):
        """Fetch all currencies for one provider, populate leg_rates, signal Events."""
        try:
            provider = await configured_fx_provider(provider_code)
            if not provider:
                raise FXServiceError(f"Unknown provider: {provider_code}")

            # Check TTL cache — skip provider fetch if recent data available (the settings are part of the key)
            cache_key = (provider_code, frozenset(target_currencies), date_range, settings_cache_part(provider))
            cached_result, cache_hit = _fx_fetch_cache.get(cache_key)
            if cache_hit:
                logger.debug("FX provider cache hit, skipping fetch", provider=provider_code, currencies=len(target_currencies))
                rates_by_currency = cached_result
            else:
                rates_by_currency = await call_fx_provider(provider, lambda: provider.fetch_rates(date_range, list(target_currencies), base_currency=None))
                _fx_fetch_cache.set(cache_key, rates_by_currency)

            _collect_leg_rates(rates_by_currency, provider_code, leg_rates, leg_unusable)

            # Signal all events for this provider
            for target_cur in target_currencies:
                base_cur = provider.base_currency
                norm_b = min(base_cur, target_cur)
                norm_q = max(base_cur, target_cur)
                leg_key = (norm_b, norm_q, provider_code)
                if leg_key in leg_events:
                    leg_events[leg_key].set()

        except Exception as e:
            _note_provider_failure(provider_code, e, provider_refusals)
            provider = FXProviderRegistry.get_provider_instance(provider_code)
            base_cur = provider.base_currency if provider else ""
            for target_cur in target_currencies:
                norm_b = min(base_cur, target_cur)
                norm_q = max(base_cur, target_cur)
                leg_key = (norm_b, norm_q, provider_code)
                leg_errors[leg_key] = str(e)
                if leg_key in leg_events:
                    leg_events[leg_key].set()  # Signal anyway so coroutines don't hang

    provider_tasks = [_fetch_provider(prov, targets) for prov, targets in provider_legs.items()]
    if provider_tasks:
        await asyncio.gather(*provider_tasks)

    # ── Phase 3: Route coroutines — await Events, compute, upsert+commit ──
    # With fallback: try routes in priority order, skip to next if legs failed
    async def _process_route(pair_slug: str) -> FXSyncPairResult:  # noqa: C901 — route fallback chain, per-route error/continue paths
        """Process a single pair: try routes in priority order, use first one with all legs available."""
        t_route_start = time.monotonic_ns()  # Per-route timer
        routes = pair_routes_map.get(pair_slug, [])

        if not routes:
            return FXSyncPairResult(
                pair=pair_slug,
                status=SyncStatus.FAILED,
                provider_used=None,
                points_fetched=0,
                points_changed=0,
                message=None,
                errors=[f"No route configuration found for {pair_slug}"],
                elapsed_ms=(time.monotonic_ns() - t_route_start) // 1_000_000,
            )

        # Check if ALL routes are MANUAL-only
        if all(all(s["provider"].upper() == "MANUAL" for s in r.parsed_steps) for r in routes):
            return FXSyncPairResult(
                pair=pair_slug,
                status=SyncStatus.SKIPPED,
                provider_used=None,
                points_fetched=0,
                points_changed=0,
                message="Manual-only pair, nothing to sync",
                elapsed_ms=None,
            )

        fallback_errors: list[str] = []

        for route_idx, route in enumerate(routes):
            steps = route.parsed_steps

            # Skip MANUAL-only routes in loop
            if all(s["provider"].upper() == "MANUAL" for s in steps):
                continue

            try:
                # Wait for all leg events of THIS route
                my_events = []
                my_leg_keys = []
                for step in steps:
                    fc, tc = step["from"], step["to"]
                    prov = step["provider"]
                    if prov.upper() == "MANUAL":
                        continue
                    norm_b = min(fc, tc)
                    norm_q = max(fc, tc)
                    leg_key = (norm_b, norm_q, prov)
                    if leg_key in leg_events:
                        my_events.append(leg_events[leg_key].wait())
                        my_leg_keys.append(leg_key)

                if my_events:
                    try:
                        await asyncio.wait_for(asyncio.gather(*my_events), timeout=120.0)
                    except TimeoutError:
                        err_msg = f"Route {route_idx + 1}: timeout waiting for legs (120s)"
                        fallback_errors.append(err_msg)
                        logger.warning(f"Pair {pair_slug}: {err_msg}, trying next route...")
                        continue  # Try next route

                # Check for failed legs in this route
                failed_legs = [lk for lk in my_leg_keys if lk in leg_errors]
                if failed_legs:
                    failed_desc = ", ".join(f"{lk[0]}-{lk[1]}({lk[2]}): {leg_errors[lk]}" for lk in failed_legs)
                    err_msg = f"Route {route_idx + 1}: legs failed — {failed_desc}"
                    fallback_errors.append(err_msg)
                    logger.warning(f"Pair {pair_slug}: {err_msg}, trying next route...")
                    continue  # Try next route

                # ── All legs OK for this route — compute rates ──
                if len(steps) == 1:
                    result = await _compute_single_step(pair_slug, route, steps[0], t_route_start, fallback_errors)
                else:
                    result = await _compute_multi_step(pair_slug, route, steps, t_route_start, fallback_errors)

                # If fallback was used, log it
                if route_idx > 0 and result.status in (SyncStatus.OK, SyncStatus.PARTIAL):
                    non_manual_step_provider_codes = [s["provider"] for s in steps if s["provider"].upper() != "MANUAL"]
                    logger.warning(f"Pair {pair_slug}: primary route failed, used fallback route {route_idx + 1} " f"(providers: {', '.join(non_manual_step_provider_codes)})")

                return result

            except Exception as e:
                err_msg = f"Route {route_idx + 1}: {e}"
                fallback_errors.append(err_msg)
                logger.warning(f"Pair {pair_slug}: {err_msg}, trying next route...")
                continue  # Try next route

        # All routes exhausted
        elapsed_ms = (time.monotonic_ns() - t_route_start) // 1_000_000
        logger.error(f"Pair {pair_slug}: all {len(routes)} route(s) failed")
        return FXSyncPairResult(
            pair=pair_slug,
            status=SyncStatus.FAILED,
            provider_used=None,
            points_fetched=0,
            points_changed=0,
            message=f"All {len(routes)} route(s) failed for {pair_slug}",
            errors=fallback_errors,
            elapsed_ms=elapsed_ms,
        )

    def _unusable_leg_dates(steps: list[dict]) -> list[date]:
        """The dates in range whose observation of one of the route's legs could not be normalized (X-R38)."""
        days: list[date] = []
        for step in steps:
            key = (min(step["from"], step["to"]), max(step["from"], step["to"]), step["provider"])
            days.extend(d for d in leg_unusable.get(key, []) if _is_date_within_sync_range(d, start_date, end_date))
        return days

    async def _compute_single_step(
        pair_slug: str,
        route,
        step: dict,
        t_route_start: int,
        fallback_errors: list[str],
    ) -> FXSyncPairResult:
        """Compute rates for a single-step route."""
        provider_code = step["provider"]
        fc, tc = step["from"], step["to"]

        norm_b = min(route.base, route.quote)
        norm_q = max(route.base, route.quote)

        computed_rates = []
        unusable = _unusable_leg_dates([step])
        for key, rate in leg_rates.items():
            if key[0] == norm_b and key[1] == norm_q:
                d = key[2]
                if _is_date_within_sync_range(d, start_date, end_date):
                    # What fx_rates.rate keeps; a rate it cannot keep is skipped, never stored (X-R38)
                    stored = storable_fx_rate(rate)
                    if stored is None:
                        unusable.append(d)
                        continue
                    computed_rates.append((d, norm_b, norm_q, stored))
        _warn_unusable_rates(pair_slug, provider_code, unusable)

        if computed_rates:
            async with AsyncSession(get_async_engine(), expire_on_commit=False) as pair_session:
                actual_changed = await _count_actual_changes(pair_session, computed_rates)

                values_list = [
                    {
                        "date": d,
                        "base": b,
                        "quote": q,
                        "rate": r,
                        "source": provider_code,
                        "fetched_at": func.current_timestamp(),
                    }
                    for d, b, q, r in computed_rates
                ]
                batch_stmt = insert(FxRate).values(values_list)
                batch_stmt = batch_stmt.on_conflict_do_update(
                    index_elements=["date", "base", "quote"],
                    set_={
                        "rate": batch_stmt.excluded.rate,
                        "source": batch_stmt.excluded.source,
                        "fetched_at": func.current_timestamp(),
                    },
                )
                await pair_session.execute(batch_stmt)
                await pair_session.commit()
        else:
            actual_changed = 0

        elapsed_ms = (time.monotonic_ns() - t_route_start) // 1_000_000
        partial_msg = None
        if not computed_rates and unusable:
            partial_msg = f"Provider {provider_code} returned no rate the database can keep for {route.base}/{route.quote} in {start_date}–{end_date}: {fx_rate_limits_text()}"
        elif not computed_rates:
            partial_msg = f"Provider {provider_code} returned no data for " f"{route.base}/{route.quote} in {start_date}–{end_date}"
        # Build per-leg detail for single-step route
        leg_detail = None
        if not computed_rates:
            leg_detail = [
                FXSyncLegDetail(
                    provider=provider_code,
                    leg=f"{fc}→{tc}",
                    dates_available=0,
                    error=None,
                )
            ]
        return FXSyncPairResult(
            pair=pair_slug,
            status=SyncStatus.OK if computed_rates else SyncStatus.PARTIAL,
            provider_used=provider_code,
            points_fetched=len(computed_rates),
            points_changed=actual_changed,
            message=partial_msg,
            errors=fallback_errors or [],
            detail=leg_detail,
            elapsed_ms=elapsed_ms,
        )

    async def _compute_multi_step(
        pair_slug: str,
        route,
        steps: list[dict],
        t_route_start: int,
        fallback_errors: list[str],
    ) -> FXSyncPairResult:
        """Compute rates for a multi-step chain route."""
        step_provider_codes = [s["provider"] for s in steps]
        source = "CHAIN:" + "+".join(step_provider_codes)

        # Collect all dates from leg_rates
        all_dates = sorted({key[2] for key in leg_rates.keys() if _is_date_within_sync_range(key[2], start_date, end_date)})

        computed_rates, unusable = _storable_chain_rates(route, steps, leg_rates, all_dates)
        _warn_unusable_rates(pair_slug, source, _unusable_leg_dates(steps) + unusable)

        if computed_rates:
            async with AsyncSession(get_async_engine(), expire_on_commit=False) as pair_session:
                actual_changed = await _count_actual_changes(pair_session, computed_rates)

                values_list = [
                    {
                        "date": d,
                        "base": b,
                        "quote": q,
                        "rate": r,
                        "source": source,
                        "fetched_at": func.current_timestamp(),
                    }
                    for d, b, q, r in computed_rates
                ]
                batch_stmt = insert(FxRate).values(values_list)
                batch_stmt = batch_stmt.on_conflict_do_update(
                    index_elements=["date", "base", "quote"],
                    set_={
                        "rate": batch_stmt.excluded.rate,
                        "source": batch_stmt.excluded.source,
                        "fetched_at": func.current_timestamp(),
                    },
                )
                await pair_session.execute(batch_stmt)
                await pair_session.commit()
        else:
            actual_changed = 0

        elapsed_ms = (time.monotonic_ns() - t_route_start) // 1_000_000

        # Build per-leg detail for diagnostics
        chain_leg_details = []
        for step in steps:
            fc, tc = step["from"], step["to"]
            prov = step["provider"]
            norm_b = min(fc, tc)
            norm_q = max(fc, tc)
            leg_key_prefix = (norm_b, norm_q)
            # Count dates this leg has in the requested range
            leg_date_count = sum(1 for key in leg_rates.keys() if key[0] == leg_key_prefix[0] and key[1] == leg_key_prefix[1] and _is_date_within_sync_range(key[2], start_date, end_date))
            # Check if this leg had errors
            leg_err_key = (norm_b, norm_q, prov)
            leg_error = leg_errors.get(leg_err_key)
            chain_leg_details.append(
                FXSyncLegDetail(
                    provider=prov,
                    leg=f"{fc}→{tc}",
                    dates_available=leg_date_count,
                    error=str(leg_error) if leg_error else None,
                )
            )

        # Build human-readable message and errors list
        chain_errors: list[str] = list(fallback_errors) if fallback_errors else []
        if computed_rates:
            chain_partial_msg = None
            chain_detail = chain_leg_details  # always include detail for chains
        else:
            leg_summaries = []
            for ld in chain_leg_details:
                if ld.error:
                    leg_summaries.append(f"  • {ld.leg} ({ld.provider}): ERROR — {ld.error}")
                    chain_errors.append(f"{ld.leg} ({ld.provider}): {ld.error}")
                elif ld.dates_available == 0:
                    leg_summaries.append(f"  • {ld.leg} ({ld.provider}): 0 dates — no data returned")
                else:
                    leg_summaries.append(f"  • {ld.leg} ({ld.provider}): {ld.dates_available} dates available")
            chain_partial_msg = f"Chain {source} produced no complete rates for " f"{route.base}/{route.quote} in {start_date}–{end_date} " f"({len(all_dates)} dates checked).\n" f"Per-leg breakdown:\n" + "\n".join(leg_summaries)
            chain_detail = chain_leg_details

        return FXSyncPairResult(
            pair=pair_slug,
            status=SyncStatus.OK if computed_rates else SyncStatus.PARTIAL,
            provider_used=source,
            points_fetched=len(computed_rates),
            points_changed=actual_changed,
            message=chain_partial_msg,
            errors=chain_errors or [],
            detail=chain_detail,
            elapsed_ms=elapsed_ms,
        )

    # ── Dispatch all routes and assemble response ──
    pair_results = await asyncio.gather(*[_process_route(slug) for slug in pairs])
    result_list = [_with_fx_refusal(result, pair_routes_map.get(result.pair, []), provider_refusals) for result in pair_results]

    success_count = sum(1 for r in result_list if r.status in (SyncStatus.OK, SyncStatus.PARTIAL, SyncStatus.SKIPPED))
    total_changed = sum(r.points_changed for r in result_list)

    if total_changed > 0:
        # Fresh FX rates change every converted valuation: portfolio reports and engine
        # blobs cached before this sync would keep showing the old data-quality banner
        # (and stale totals) for their whole TTL (30 min / 24 h).
        clear_cache("portfolio_layer2")
        clear_cache("portfolio_blob")

    return FXSyncBulkResponse(
        results=result_list,
        success_count=success_count,
        date_range=SyncDateRangeModel(start=start_date, end=end_date),
        total_points_changed=total_changed,
    )
