"""Saved FX quotes for the planner source: the latest stored rate of every pair the copied facts need."""

from __future__ import annotations

from datetime import date as date_type

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import FxRate
from backend.app.db.precision import usable_fx_rate_clause
from backend.app.schemas.portfolio import (
    PortfolioPlannerSourceFxQuote,
    PortfolioPlannerSourceIssue,
)
from backend.app.services.pac_allocator.source.keys import FX_PROVENANCE_ID, field_issue, fx_key, normalized_fx_pair, text_param


async def _load_latest_planner_fx_rows(
    session: AsyncSession,
    *,
    directed_pairs: list[tuple[str, str]],
    as_of: date_type,
) -> dict[tuple[str, str], FxRate]:
    normalized_pairs = {normalized_fx_pair(source_currency, destination_currency)[:2] for source_currency, destination_currency in directed_pairs}
    if not normalized_pairs:
        return {}

    pair_filter = or_(*[and_(FxRate.base == base, FxRate.quote == quote) for base, quote in sorted(normalized_pairs)])
    latest_dates = (
        select(
            FxRate.base.label("base"),
            FxRate.quote.label("quote"),
            func.max(FxRate.date).label("latest_date"),
        )
        # X-R45: the latest *usable* row per pair, so a rate an older version stored as 0 or inf never wins over an
        # earlier real one
        .where(pair_filter, FxRate.date <= as_of, usable_fx_rate_clause())
        .group_by(FxRate.base, FxRate.quote)
        .subquery()
    )
    rows = (
        await session.execute(
            select(FxRate).join(
                latest_dates,
                and_(
                    FxRate.base == latest_dates.c.base,
                    FxRate.quote == latest_dates.c.quote,
                    FxRate.date == latest_dates.c.latest_date,
                ),
            )
        )
    ).scalars()
    return {(row.base, row.quote): row for row in rows}


async def build_planner_fx_quotes(
    session: AsyncSession,
    *,
    request_pairs: list[str],
    as_of: date_type,
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerSourceFxQuote]:
    directed_pairs = [tuple(pair.split("/", maxsplit=1)) for pair in request_pairs]
    saved_rows = await _load_latest_planner_fx_rows(
        session,
        directed_pairs=directed_pairs,
        as_of=as_of,
    )
    rows: list[PortfolioPlannerSourceFxQuote] = []

    for pair in sorted(request_pairs):
        base, quote = pair.split("/", maxsplit=1)
        saved_row = saved_rows.get((base, quote))
        if saved_row is None:
            fx_id = fx_key(pair, as_of, "missing")
            rows.append(
                PortfolioPlannerSourceFxQuote(
                    fx_quote_id=fx_id,
                    pair=pair,
                    rate=None,
                    reference_date=None,
                    source=None,
                    days_before_requested=None,
                    provenance_id=FX_PROVENANCE_ID,
                )
            )
            issues.append(
                field_issue(
                    code="allocation.saved_fx_missing",
                    kind="missing",
                    severity="error",
                    section="fx_quotes",
                    entity_kind="fx_quote",
                    entity_id=fx_id,
                    field="rate",
                    params=[text_param("pair", pair)],
                )
            )
            continue

        fx_id = fx_key(pair, saved_row.date, saved_row.source)
        rate = saved_row.rate if saved_row.rate > 0 else None
        if rate is None:
            issues.append(
                field_issue(
                    code="allocation.saved_fx_invalid",
                    kind="invalid",
                    severity="error",
                    section="fx_quotes",
                    entity_kind="fx_quote",
                    entity_id=fx_id,
                    field="rate",
                    params=[text_param("pair", pair)],
                )
            )
        rows.append(
            PortfolioPlannerSourceFxQuote(
                fx_quote_id=fx_id,
                pair=pair,
                rate=rate,
                reference_date=saved_row.date,
                source=saved_row.source,
                days_before_requested=(as_of - saved_row.date).days,
                provenance_id=FX_PROVENANCE_ID,
            )
        )

    return rows
