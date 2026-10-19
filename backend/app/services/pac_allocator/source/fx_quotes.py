"""Saved FX quotes for the planner source: the latest valid stored rate of every pair the copied facts need; a later
rate the planner cannot use (0, not finite) is skipped with a warning (X-R45b)."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import FxRate
from backend.app.schemas.portfolio import (
    PortfolioPlannerSourceFxQuote,
    PortfolioPlannerSourceIssue,
)
from backend.app.services.pac_allocator.source.keys import FX_PROVENANCE_ID, date_param, field_issue, fx_key, normalized_fx_pair, text_param


def _usable_rate(rate: Decimal | None) -> bool:
    """A saved rate the planner may quote (X-R45b): finite and above 0. A 0 or an infinity is what an older version could
    store; a finite rate past the column's limits stays a value (developer, 19/10)."""
    return rate is not None and rate.is_finite() and rate > 0


async def _previous_usable_row(session: AsyncSession, base: str, quote: str, before: date_type) -> FxRate | None:
    """The most recent saved row of the pair dated before ``before`` with a usable rate, or None (X-R45b). One query per
    row looked at: an unusable row is rare, so the first row before is almost always the answer."""
    cursor = before
    while True:
        row = (await session.execute(select(FxRate).where(FxRate.base == base, FxRate.quote == quote, FxRate.date < cursor).order_by(FxRate.date.desc()).limit(1))).scalar_one_or_none()
        if row is None or _usable_rate(row.rate):
            return row
        cursor = row.date


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
        .where(pair_filter, FxRate.date <= as_of)
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

        # X-R45b: a latest rate the planner cannot use (0 or not finite, which an older version could store) is skipped
        # for the previous valid one, and a warning says so; without one, the quote has no rate (saved_fx_invalid)
        used_row = saved_row
        if not _usable_rate(saved_row.rate):
            used_row = await _previous_usable_row(session, saved_row.base, saved_row.quote, saved_row.date) or saved_row
        fx_id = fx_key(pair, used_row.date, used_row.source)
        rate = used_row.rate if _usable_rate(used_row.rate) else None
        if used_row is not saved_row:
            issues.append(
                field_issue(
                    code="allocation.saved_fx_skipped",
                    kind="invalid",
                    severity="warning",
                    section="fx_quotes",
                    entity_kind="fx_quote",
                    entity_id=fx_id,
                    field="rate",
                    params=[text_param("pair", pair), date_param("skipped_date", saved_row.date), date_param("used_date", used_row.date)],
                )
            )
        elif rate is None:
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
                reference_date=used_row.date,
                source=used_row.source,
                days_before_requested=(as_of - used_row.date).days,
                provenance_id=FX_PROVENANCE_ID,
            )
        )

    return rows
