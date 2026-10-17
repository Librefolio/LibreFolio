"""FX provider endpoints (``/fx/providers``): the provider catalog and the user's conversion routes."""

import json
from typing import List, Optional, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError
from sqlmodel import delete as sql_delete
from sqlmodel import select

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import FxConversionRoute, User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.fx import (
    FXConversionRouteItem,
    FXConversionRouteReadItem,
    FXConversionRouteResult,
    FXConversionRoutesResponse,
    FXCreateRoutesResponse,
    FXDeleteRouteItem,
    FXDeleteRouteResult,
    FXDeleteRoutesResponse,
    FXProviderInfo,
    FXRouteStep,
)
from backend.app.services.fx.catalog import get_supported_currencies_cached
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.fx.runtime import configured_fx_provider
from backend.app.services.fx_providers.manual.plugin import MANUAL_PRIORITY

logger = get_logger(__name__)

router_providers = APIRouter(prefix="/providers", tags=["FX Providers"])


# ============================================================================
# ENDPOINTS
# ============================================================================


def _build_providers_description() -> str:
    """Build dynamic description listing all installed FX providers."""
    try:
        installed = FXProviderRegistry.list_providers()
        codes = ", ".join(p["code"] for p in installed)
    except Exception:
        codes = "(auto-discovered at runtime)"
    return (
        "Get the list of available FX rate providers.\n\n"
        "Returns information about each provider including:\n"
        "- Provider code and name\n"
        "- Default base currency\n"
        "- All supported base currencies (for multi-base providers)\n"
        "- All target currencies (from get_supported_currencies)\n"
        "- Description and icon URL\n\n"
        "Note: This endpoint absorbed the former GET /fx/currencies endpoint.\n"
        "Target currencies are now returned per-provider instead of a separate call.\n\n"
        f"Installed providers: {codes}\n\n"
        "Use the `providers` query parameter to filter by specific provider codes."
    )


@router_providers.get("", response_model=List[FXProviderInfo], description=_build_providers_description())
async def list_providers(
    providers: Optional[List[str]] = Query(
        None,
        description="Optional list of provider codes to filter. If empty, returns all providers.",
    ),
    _current_user: User = Depends(get_current_user),
):
    """Get the list of available FX rate providers, optionally filtered."""
    try:
        # Get all providers from registry
        providers_list = FXProviderRegistry.list_providers()

        # Filter out the testing providers and MANUAL (the sentinel of hand-entered rates) from the public list
        providers_list = [p for p in providers_list if p["code"] != "MANUAL" and not getattr(FXProviderRegistry.get_plugin(p["code"]), "test_only", True)]

        # Filter by requested provider codes (case-insensitive)
        if providers:
            requested = {p.upper() for p in providers}
            providers_list = [p for p in providers_list if p["code"].upper() in requested]

        # Build provider info from instances
        result = []
        for provider_dict in providers_list:
            code = provider_dict["code"]
            instance = await configured_fx_provider(code)

            # Get base currencies (property always available in base class)
            base_currencies = instance.base_currencies

            # Target currencies: cached 24 h; the last known list when the provider fails (services/fx/catalog.py)
            target_currencies = await get_supported_currencies_cached(code, instance)

            result.append(
                FXProviderInfo(
                    code=code,
                    name=provider_dict["name"],
                    base_currency=instance.base_currency,
                    base_currencies=base_currencies,
                    target_currencies=sorted(target_currencies),
                    description=getattr(instance, "description", f'{provider_dict["name"]} FX rate provider'),
                    description_i18n=getattr(instance, "description_i18n", {}),
                    warning_i18n=getattr(instance, "warning_i18n", {}),
                    icon_url=instance.icon,
                    docs_url=getattr(instance, "docs_url", None),
                )
            )

        return result
    except Exception as e:
        logger.exception(f"Error listing FX providers: {e}")
        raise HTTPException(status_code=500, detail="Internal error while listing FX providers") from e


# ============================================================================
# PROVIDER CONFIGURATION ENDPOINTS
# ============================================================================


class _RouteMetadata(TypedDict):
    is_chain: bool
    providers_used: list[str]


def _route_metadata(route: FxConversionRoute) -> _RouteMetadata:
    return {"is_chain": route.is_chain, "providers_used": sorted(route.providers_used)}


@router_providers.get("/routes", response_model=FXConversionRoutesResponse)
async def list_routes(session: AsyncSession = Depends(get_session_generator), _current_user: User = Depends(get_current_user)):
    """
    Get the list of configured conversion routes.

    Returns all configured routes ordered by base, quote, and priority.
    Each route contains ordered chain_steps, a derived is_chain flag and sorted
    configured providers_used membership (not successful-fetch provenance).

    Returns:
        List of conversion route configurations
    """
    try:
        stmt = select(FxConversionRoute).order_by(FxConversionRoute.base, FxConversionRoute.quote, FxConversionRoute.priority)
        result = await session.execute(stmt)
        routes = result.scalars().all()

        routes_list = [
            FXConversionRouteReadItem(
                base=r.base,
                quote=r.quote,
                priority=r.priority,
                chain_steps=[FXRouteStep(**s) for s in json.loads(r.chain_steps)],
                **_route_metadata(r),
            )
            for r in routes
        ]

        return FXConversionRoutesResponse(items=routes_list)
    except Exception as e:
        logger.exception(f"Error listing conversion routes: {e}")
        raise HTTPException(status_code=500, detail="Internal error while listing conversion routes") from e


@router_providers.post("/routes", response_model=FXCreateRoutesResponse, status_code=201)
async def create_routes_bulk(  # noqa: C901 — flat bulk upsert loop, per-item validation
    routes: List[FXConversionRouteItem],
    replace: bool = Query(False, description="Keep exactly the routes posted for each pair the request names: its other priorities are deleted in the same transaction (X-R75)"),
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """
    Create or update multiple conversion routes in a single atomic transaction.

    **The pair is normalised, not validated.** A route posted as ``EUR-DKK`` is
    stored — and later listed, and addressed by the UI — as ``DKK-EUR``: the
    endpoint sorts the two codes alphabetically and the caller is told nothing.
    It is the same convention the rates use (see ``normalize_rate_for_storage``
    in ``services/fx/storage.py``), and it is what makes a pair one row instead of two
    that can disagree. But a client that posts one direction and then looks for
    that direction finds nothing, so it is worth saying out loud here rather
    than leaving it to be discovered from the response.

    Validations:
    - Provider codes must be registered in FXProviderRegistry
    - Chain steps must be valid (continuity, no repeated edges, matching endpoints)

    **Replace** (``?replace=true``, X-R75): each pair the request names keeps exactly the routes posted for it; its
    other priorities are deleted in the same transaction, after the validation. So an edit is one request, and a
    refusal (400, 409, 500) leaves the pair as it was. The MANUAL rules hold as without it: a real provider posted
    removes the MANUAL route, and the MANUAL item alone (priority 999) leaves the pair manual. A pair not configured
    yet, such as an intermediate pair of a chain, is created; one another request configured meanwhile keeps only what
    is posted for it.

    Args:
        routes: List of routes to create/update
        replace: Keep exactly the posted routes of each pair named (default: upsert only)
        session: Database session

    Returns:
        Results for each route operation
    """
    results = []
    success_count = 0
    error_count = 0

    try:
        available_providers = {p["code"] for p in FXProviderRegistry.list_providers()}

        for route_item in routes:
            chain_steps_json = json.dumps([{"from": s.from_currency, "to": s.to_currency, "provider": s.provider} for s in route_item.chain_steps])

            # Validate all provider codes in chain_steps
            invalid_providers = []
            for step in route_item.chain_steps:
                if step.provider.upper() not in available_providers:
                    invalid_providers.append(step.provider)

            if invalid_providers:
                submitted_route = FxConversionRoute(
                    base=route_item.base,
                    quote=route_item.quote,
                    priority=route_item.priority,
                    chain_steps=chain_steps_json,
                )
                results.append(
                    FXConversionRouteResult(
                        success=False,
                        action="error",
                        base=route_item.base,
                        quote=route_item.quote,
                        priority=route_item.priority,
                        chain_steps=route_item.chain_steps,
                        message=f"Unknown provider(s): {', '.join(invalid_providers)}",
                        **_route_metadata(submitted_route),
                    )
                )
                error_count += 1
                continue

            # Normalize base/quote to alphabetical order
            base = min(route_item.base.upper(), route_item.quote.upper())
            quote = max(route_item.base.upper(), route_item.quote.upper())

            # Check if already exists
            stmt = select(FxConversionRoute).where(
                FxConversionRoute.base == base,
                FxConversionRoute.quote == quote,
                FxConversionRoute.priority == route_item.priority,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.chain_steps = chain_steps_json
                session.add(existing)
                stored_route = existing
                action = "updated"
            else:
                new_route = FxConversionRoute(
                    base=base,
                    quote=quote,
                    priority=route_item.priority,
                    chain_steps=chain_steps_json,
                )
                session.add(new_route)
                stored_route = new_route
                action = "created"

            results.append(
                FXConversionRouteResult(
                    success=True,
                    action=action,
                    base=base,
                    quote=quote,
                    priority=route_item.priority,
                    chain_steps=route_item.chain_steps,
                    message=None,
                    **_route_metadata(stored_route),
                )
            )
            success_count += 1

        if error_count > 0:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "message": f"Validation failed for {error_count} route(s). Transaction rolled back.",
                    "results": [r.model_dump() for r in results],
                },
            )

        if replace:
            # X-R75: each pair the request names keeps exactly the priorities posted for it, in this transaction: a
            # refusal from here on rolls the whole edit back, so a pair never loses its routes to a failed save.
            posted: dict[tuple[str, str], set[int]] = {}
            for route_item in routes:
                pair = (min(route_item.base.upper(), route_item.quote.upper()), max(route_item.base.upper(), route_item.quote.upper()))
                posted.setdefault(pair, set()).add(route_item.priority)
            for (pair_base, pair_quote), priorities in posted.items():
                await session.execute(sql_delete(FxConversionRoute).where(FxConversionRoute.base == pair_base, FxConversionRoute.quote == pair_quote, FxConversionRoute.priority.not_in(priorities)))

        # Auto-remove MANUAL sentinel for pairs that now have real providers
        pairs_with_real_providers = set()
        for route_item in routes:
            has_real = any(s.provider.upper() != "MANUAL" for s in route_item.chain_steps)
            if has_real:
                b = min(route_item.base.upper(), route_item.quote.upper())
                q = max(route_item.base.upper(), route_item.quote.upper())
                pairs_with_real_providers.add((b, q))

        for base, quote in pairs_with_real_providers:
            # Delete MANUAL routes for this pair
            _manual_del = sql_delete(FxConversionRoute).where(
                FxConversionRoute.base == base,
                FxConversionRoute.quote == quote,
                # A route is MANUAL if chain_steps contains only MANUAL provider
                # We check by looking for routes where chain_steps has MANUAL
            )
            # More targeted: find MANUAL routes
            manual_stmt = select(FxConversionRoute).where(
                FxConversionRoute.base == base,
                FxConversionRoute.quote == quote,
            )
            manual_result = await session.execute(manual_stmt)
            manual_routes = manual_result.scalars().all()
            for mr in manual_routes:
                steps = mr.parsed_steps
                if all(s["provider"].upper() == "MANUAL" for s in steps):
                    await session.delete(mr)
                    logger.info(f"Auto-removed MANUAL sentinel for {base}/{quote} (real provider added)")

        await session.commit()

        return FXCreateRoutesResponse(results=results, success_count=success_count, error_count=error_count)

    except HTTPException:
        raise
    except (IntegrityError, StaleDataError) as e:
        # Two writers, one row. The upsert reads before it writes, so a second
        # caller working on the same (base, quote, priority) lands either on the
        # insert — `UNIQUE constraint failed` because both passed the existence
        # check — or on the update, with `expected to update 1 row(s); 0 were
        # matched` because the row went away in between.
        #
        # It is a genuine conflict, not a server fault: 409, and a sentence the
        # UI can show as it stands. What must *not* travel is the driver's text,
        # which carries the INSERT statement and its bound parameters and was
        # being rendered verbatim in the add-pair dialog.
        #
        # Retrying is the user's move, not ours: the client cannot know whether
        # the other writer meant to replace this route or a different one.
        await session.rollback()
        logger.warning("Concurrent write on fx_conversion_routes: %s", e)
        raise HTTPException(
            status_code=409,
            detail="This conversion route was modified by another request at the same time. Nothing was saved — please try again.",
        ) from e
    except Exception as e:
        await session.rollback()
        logger.exception(f"Error saving conversion routes: {e}")
        raise HTTPException(status_code=500, detail="Internal error while saving conversion routes") from e


@router_providers.delete("/routes", response_model=FXDeleteRoutesResponse)
async def delete_routes_bulk(  # noqa: C901 — sequential batch stages: preload, replay, sentinel reinstate
    routes: List[FXDeleteRouteItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """
    Delete multiple conversion routes.

    If priority is specified, deletes only that specific priority level.
    If priority is omitted, deletes ALL priorities for that pair.

    Args:
        routes: List of FXDeleteRouteItem to delete
        session: Database session

    Returns:
        FXDeleteRoutesResponse with results for each deletion operation
    """
    results = []
    total_deleted = 0

    try:
        # P0-5b (audit 08): no N+1. Before: 1 DELETE per item plus 1 SELECT per
        # affected pair. After: 1 preload SELECT, at most 2 batched DELETEs,
        # and 1 post-delete SELECT for the MANUAL-sentinel check.
        #
        # The unique constraint on (base, quote, priority) makes each targeted
        # row individually identifiable, so per-item deleted_count can be
        # replayed in memory from the preload — the loop below consumes the
        # preloaded keys in request order, exactly mirroring the old sequential
        # DELETE semantics (duplicate items: first one reports the row, later
        # ones report "not found").
        normalized_items = [(min(item.base, item.quote), max(item.base, item.quote), item.priority) for item in routes]
        pair_keys = {(norm_base, norm_quote) for norm_base, norm_quote, _ in normalized_items}

        existing_keys: set[tuple[str, str, int]] = set()
        if pair_keys:
            preload_stmt = select(FxConversionRoute.base, FxConversionRoute.quote, FxConversionRoute.priority).where(tuple_(FxConversionRoute.base, FxConversionRoute.quote).in_(pair_keys))
            existing_keys = {(row_base, row_quote, row_priority) for row_base, row_quote, row_priority in (await session.execute(preload_stmt)).all()}

        for norm_base, norm_quote, priority in normalized_items:
            if priority is not None:
                deleted_count = 1 if (norm_base, norm_quote, priority) in existing_keys else 0
                existing_keys.discard((norm_base, norm_quote, priority))
            else:
                deleted_count = sum(1 for row_base, row_quote, _ in existing_keys if (row_base, row_quote) == (norm_base, norm_quote))
                existing_keys = {key for key in existing_keys if (key[0], key[1]) != (norm_base, norm_quote)}

            if deleted_count == 0:
                priority_str = f" with priority={priority}" if priority else ""
                results.append(
                    FXDeleteRouteResult(
                        success=True,
                        base=norm_base,
                        quote=norm_quote,
                        priority=priority,
                        deleted_count=0,
                        message=f"Route {norm_base}/{norm_quote}{priority_str} not found (nothing to delete)",
                    )
                )
            else:
                results.append(
                    FXDeleteRouteResult(
                        success=True,
                        base=norm_base,
                        quote=norm_quote,
                        priority=priority,
                        deleted_count=deleted_count,
                        message=None,
                    )
                )
            total_deleted += deleted_count

        # Apply the deletions with at most two statements: full-pair deletes
        # (priority omitted) and priority-targeted deletes. The union matches
        # exactly the rows consumed by the in-memory replay above, regardless
        # of execution order.
        full_delete_pairs = {(norm_base, norm_quote) for norm_base, norm_quote, priority in normalized_items if priority is None}
        targeted_triples = {(norm_base, norm_quote, priority) for norm_base, norm_quote, priority in normalized_items if priority is not None and (norm_base, norm_quote) not in full_delete_pairs}

        if targeted_triples:
            await session.execute(sql_delete(FxConversionRoute).where(tuple_(FxConversionRoute.base, FxConversionRoute.quote, FxConversionRoute.priority).in_(targeted_triples)))
        if full_delete_pairs:
            await session.execute(sql_delete(FxConversionRoute).where(tuple_(FxConversionRoute.base, FxConversionRoute.quote).in_(full_delete_pairs)))

        # Auto-reinstate MANUAL sentinel for pairs that have no routes left
        # (but NOT for pairs that were fully deleted with priority=None — that's intentional removal)
        fully_deleted_pairs = set()
        for route_item in routes:
            if route_item.priority is None:
                b = min(route_item.base, route_item.quote)
                q = max(route_item.base, route_item.quote)
                fully_deleted_pairs.add((b, q))

        affected_pairs = set()
        for route_item in routes:
            b = min(route_item.base, route_item.quote)
            q = max(route_item.base, route_item.quote)
            if (b, q) not in fully_deleted_pairs:
                affected_pairs.add((b, q))

        # P0-5b: ONE post-delete SELECT for every affected pair, grouped in
        # memory, instead of one SELECT per pair.
        remaining_by_pair: dict[tuple[str, str], list[FxConversionRoute]] = {}
        if affected_pairs:
            remaining_stmt = select(FxConversionRoute).where(tuple_(FxConversionRoute.base, FxConversionRoute.quote).in_(affected_pairs))
            for remaining_route in (await session.execute(remaining_stmt)).scalars().all():
                remaining_by_pair.setdefault((remaining_route.base, remaining_route.quote), []).append(remaining_route)

        for base, quote in affected_pairs:
            remaining_routes = remaining_by_pair.get((base, quote), [])

            # Check if any non-MANUAL route exists
            has_real = False
            for r in remaining_routes:
                steps = r.parsed_steps
                if not all(s["provider"].upper() == "MANUAL" for s in steps):
                    has_real = True
                    break

            if not has_real and not any(all(s["provider"].upper() == "MANUAL" for s in r.parsed_steps) for r in remaining_routes):
                manual_route = FxConversionRoute(
                    base=base,
                    quote=quote,
                    priority=MANUAL_PRIORITY,
                    chain_steps=json.dumps([{"from": base, "to": quote, "provider": "MANUAL"}]),
                )
                session.add(manual_route)
                logger.info(f"Auto-reinstated MANUAL sentinel for {base}/{quote} (no real providers left)")

        await session.commit()

        return FXDeleteRoutesResponse(
            results=results,
            success_count=len([r for r in results if r.success]),
            total_deleted=total_deleted,
        )

    except Exception as e:
        await session.rollback()
        logger.exception(f"Error deleting conversion routes: {e}")
        raise HTTPException(status_code=500, detail="Internal error while deleting conversion routes") from e
