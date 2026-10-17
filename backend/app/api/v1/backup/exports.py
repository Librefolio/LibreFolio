"""
Per-series snapshot exports (``/backup/asset/{id}/prices``, ``/backup/asset/{id}/events``,
``/backup/fx/{base}/{quote}/rates``).

They stream CSV/JSON of the current state of one historical series. Primary use case: the "download before
destructive operation" UX (currency change wipe, pair teardown). ``backup_router`` (``__init__.py``) gives these routes
the ``/backup`` prefix and the ``Backup & Export`` tag, after the full-instance routes of ``instance.py``.

The legacy endpoint ``GET /api/v1/assets/prices/{id}/export`` has been
removed (pre-beta, no external consumers). Use
``/backup/asset/{id}/prices`` directly.
"""

from datetime import date as date_type
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import Asset, AssetEvent, FxRate, PriceHistory, User
from backend.app.db.session import get_session_generator
from backend.app.services.platform.series_export import (
    EVENT_COLUMNS,
    FX_RATE_COLUMNS,
    PRICE_COLUMNS,
    BackupScope,
    slugify_for_filename,
    stream_rows_as_csv,
    stream_rows_as_json,
)

exports_router = APIRouter()


# =============================================================================
# PER-SERIES SNAPSHOT EXPORTS (R3-3b)
# =============================================================================
#
# These endpoints produce streaming CSV/JSON snapshots of a single historical
# series. They are the "download before destructive operation" backup
# mechanism used by the currency-change wipe UX (Policy D), but they are
# also useful as a general audit/export trail.
#
# Shape conventions (see ``series_export.py`` for details):
#   * ``?format=csv`` (default): ``text/csv`` with fixed column order.
#   * ``?format=json``: uniform envelope ``{scope, entity, exported_at,
#     row_count, rows:[...]}``.
# Decimal values are serialised as strings to preserve precision.
# =============================================================================


def _build_filename(scope: str, slug_parts: list[str], fmt: str) -> str:
    """Compose ``<scope>_<slug>_<today>.<fmt>``."""
    today = date_type.today().isoformat()
    slug = "_".join(p for p in slug_parts if p)
    return f"{scope}_{slug}_{today}.{fmt}"


@exports_router.get("/asset/{asset_id}/prices")
async def backup_asset_prices(
    asset_id: int,
    format: Literal["csv", "json"] = "csv",
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Stream the full price history of an asset as CSV or JSON.

    Columns (same in both formats, see ``series_export.PRICE_COLUMNS``):
    ``date, open, high, low, close, volume, currency, source_plugin_key, fetched_at``.

    ``currency`` is the per-row verbatim value from ``price_history.currency``
    (canary-forensic column, kept in DB but normally not exposed on the
    regular query endpoints).
    """
    asset = (await session.execute(select(Asset).where(Asset.id == asset_id))).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_id).order_by(PriceHistory.date.asc())
    rows_orm = list((await session.execute(stmt)).scalars().all())

    def _to_dict(r: PriceHistory) -> dict:
        return {
            "date": r.date.isoformat() if r.date else None,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
            "currency": r.currency,
            "source_plugin_key": r.source_plugin_key,
            "fetched_at": r.fetched_at,
        }

    rows = [_to_dict(r) for r in rows_orm]
    slug = slugify_for_filename(asset.display_name or f"asset-{asset_id}", f"asset-{asset_id}")
    filename = _build_filename("prices", [slug], format)

    if format == "json":
        entity = {"type": "asset", "id": asset_id, "slug": slug, "currency": asset.currency}
        return StreamingResponse(
            stream_rows_as_json(BackupScope.PRICES, entity, rows),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return StreamingResponse(
        stream_rows_as_csv(PRICE_COLUMNS, rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@exports_router.get("/asset/{asset_id}/events")
async def backup_asset_events(
    asset_id: int,
    format: Literal["csv", "json"] = "csv",
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Stream all ``AssetEvent`` rows of an asset as CSV or JSON.

    Columns: ``date, type, value, currency, source, provider_assignment_id,
    notes, created_at, updated_at`` where ``source`` is derived as
    ``MANUAL`` if ``provider_assignment_id IS NULL`` and ``PROVIDER``
    otherwise.

    Intended as the "download events before currency-change wipe" backup:
    the Policy D flow wipes all events, so the user should keep this
    snapshot if they want to manually re-insert anything afterwards.
    """
    asset = (await session.execute(select(Asset).where(Asset.id == asset_id))).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")

    stmt = select(AssetEvent).where(AssetEvent.asset_id == asset_id).order_by(AssetEvent.date.asc(), AssetEvent.id.asc())
    rows_orm = list((await session.execute(stmt)).scalars().all())

    def _to_dict(e: AssetEvent) -> dict:
        return {
            "date": e.date.isoformat() if e.date else None,
            "type": e.type.value if hasattr(e.type, "value") else str(e.type),
            "value": e.value,
            "currency": e.currency,
            "source": "MANUAL" if e.provider_assignment_id is None else "PROVIDER",
            "provider_assignment_id": e.provider_assignment_id,
            "notes": e.notes,
            "created_at": e.created_at,
            "updated_at": e.updated_at,
        }

    rows = [_to_dict(e) for e in rows_orm]
    slug = slugify_for_filename(asset.display_name or f"asset-{asset_id}", f"asset-{asset_id}")
    filename = _build_filename("events", [slug], format)

    if format == "json":
        entity = {"type": "asset", "id": asset_id, "slug": slug, "currency": asset.currency}
        return StreamingResponse(
            stream_rows_as_json(BackupScope.EVENTS, entity, rows),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return StreamingResponse(
        stream_rows_as_csv(EVENT_COLUMNS, rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@exports_router.get("/fx/{base}/{quote}/rates")
async def backup_fx_rates(
    base: str,
    quote: str,
    format: Literal["csv", "json"] = "csv",
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Stream all ``FxRate`` rows for a currency pair as CSV or JSON.

    ``base``/``quote`` are ISO 4217 codes (uppercase). The FX storage
    invariant requires ``base < quote`` alphabetically; if the caller
    passes the inverted pair we normalise transparently and mark the
    JSON envelope with ``inverted: true`` so downstream tools can
    reconstruct ``1/rate``. The CSV format always reflects the stored
    ``(base, quote)`` verbatim because it has no envelope to carry the
    flag.

    Columns: ``date, base, quote, rate, source, fetched_at``.
    """
    base_u = (base or "").upper()
    quote_u = (quote or "").upper()
    if not base_u or not quote_u or base_u == quote_u:
        raise HTTPException(status_code=400, detail="Invalid base/quote pair")

    # Normalise to storage order (base < quote alphabetically).
    inverted = base_u > quote_u
    stored_base, stored_quote = (quote_u, base_u) if inverted else (base_u, quote_u)

    stmt = select(FxRate).where(FxRate.base == stored_base, FxRate.quote == stored_quote).order_by(FxRate.date.asc())
    rows_orm = list((await session.execute(stmt)).scalars().all())

    def _to_dict(r: FxRate) -> dict:
        return {
            "date": r.date.isoformat() if r.date else None,
            "base": r.base,
            "quote": r.quote,
            "rate": r.rate,
            "source": r.source,
            "fetched_at": r.fetched_at,
        }

    rows = [_to_dict(r) for r in rows_orm]
    filename = _build_filename("fx", [stored_base.lower(), stored_quote.lower()], format)

    if format == "json":
        entity = {
            "type": "fx_pair",
            "base": stored_base,
            "quote": stored_quote,
            "requested_base": base_u,
            "requested_quote": quote_u,
            "inverted": inverted,
        }
        return StreamingResponse(
            stream_rows_as_json(BackupScope.FX_RATES, entity, rows),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return StreamingResponse(
        stream_rows_as_csv(FX_RATE_COLUMNS, rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
