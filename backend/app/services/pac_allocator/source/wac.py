"""Average purchase cost (WAC) contexts for the planner source, with the saved FX evidence the runtime cost used."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, FxRate
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    PortfolioPlannerSourceIssue,
    PortfolioPlannerSourceWacFxEvidence,
    PortfolioPlannerWacContext,
)
from backend.app.services.financial_math.fx_rates import oriented_rate
from backend.app.services.pac_allocator.source.keys import WAC_PROVENANCE_ID, asset_key, broker_key, field_issue, holding_key, normalized_fx_pair, usable_rate, validated_currency, wac_key
from backend.app.utils.sql_chunks import chunks


def _rates_match(left: Decimal, right: Decimal) -> bool:
    """Accept only Decimal-context round-off from derived inverse rates."""

    scale = max(abs(left), abs(right), Decimal("1"))
    return abs(left - right) <= scale * Decimal("1e-24")


async def _load_wac_fx_rows(
    session: AsyncSession,
    *,
    keys: set[tuple[str, str, date_type]],
) -> dict[tuple[str, str, date_type], FxRate]:
    """The saved rows at exactly the (base, quote, date) the cost conversions used, in one read per chunk.

    The average cost already chose each rate (``convert_bulk``, with its backward fill): this only reads that row back,
    for its source and to fail closed when it has changed or gone since. No window, no backward fill of its own. One OR
    term per key, read ``OR_TERMS_PER_QUERY`` at a time (MF-SEC9a): SQLite refuses an OR of a thousand terms, and weekly
    foreign buys over twenty years are as many keys.
    """

    if not keys:
        return {}
    rows: dict[tuple[str, str, date_type], FxRate] = {}
    for chunk in chunks(sorted(keys)):
        stored_rows = (
            await session.execute(
                select(FxRate).where(
                    or_(*[and_(FxRate.base == base, FxRate.quote == quote, FxRate.date == rate_date) for base, quote, rate_date in chunk]),
                )
            )
        ).scalars()
        rows.update({key: row for row in stored_rows if (key := (row.base, row.quote, row.date)) in keys})
    return rows


async def build_planner_wac_contexts(  # noqa: C901 — sequential WAC/evidence mapping is intentionally fail-closed
    session: AsyncSession,
    *,
    holding_rows: list,
    selected_asset_ids: set[int],
    assets_by_id: dict[int, Asset],
    as_of: date_type,
    target_currency: str,
    issues: list[PortfolioPlannerSourceIssue],
) -> list[PortfolioPlannerWacContext]:
    # Resolved at call time, not at module load: tests patch portfolio_service.compute_wac_iterative.
    from backend.app.services.portfolio_service import compute_wac_iterative  # noqa: PLC0415

    prepared: list[tuple[int, int, object | None]] = []
    fx_keys: set[tuple[str, str, date_type]] = set()

    # Deliberately sequential: one AsyncSession is shared, and no provisional
    # item cap or silent truncation belongs in this domain endpoint.
    for broker_id, asset_id, _custody_quantity in sorted(
        holding_rows,
        key=lambda row: (row[1], row[0]),
    ):
        if asset_id is None or asset_id not in selected_asset_ids:
            continue
        asset = assets_by_id.get(asset_id)
        asset_currency = validated_currency(asset.currency if asset else None)
        if asset is None or asset_currency is None:
            if asset is not None:
                issues.append(
                    field_issue(
                        code="allocation.currency_spec_missing",
                        kind="missing",
                        severity="error",
                        section="wac_contexts",
                        entity_kind="wac_context",
                        entity_id=wac_key(asset_id, broker_id, as_of, target_currency),
                        field="unit_cost",
                    )
                )
            prepared.append((broker_id, asset_id, None))
            continue
        result = await compute_wac_iterative(
            session=session,
            broker_id=broker_id,
            asset_id=asset_id,
            as_of_date=as_of,
            asset_currency=asset_currency,
            target_currency_override=target_currency,
            use_cache=False,
        )
        prepared.append((broker_id, asset_id, result))
        for qualifying_tx in result.wac_qualifying_txs:
            fx_info = qualifying_tx.fx_info
            source_currency = validated_currency(qualifying_tx.original_currency)
            if fx_info is None or fx_info.fx_rate_date is None or source_currency is None or qualifying_tx.fx_rate_used is None or source_currency == target_currency:
                continue
            base, quote, _inverted = normalized_fx_pair(source_currency, target_currency)
            fx_keys.add((base, quote, fx_info.fx_rate_date))

    saved_fx_rows = await _load_wac_fx_rows(session, keys=fx_keys)
    rows: list[PortfolioPlannerWacContext] = []
    for broker_id, asset_id, result in prepared:
        holding_id = holding_key(asset_id, broker_id)
        wac_id = wac_key(asset_id, broker_id, as_of, target_currency)
        issues.append(
            field_issue(
                code="allocation.fiscal_currency_missing",
                kind="missing",
                severity="warning",
                section="wac_contexts",
                entity_kind="wac_context",
                entity_id=wac_id,
                field="fiscal_currency",
            )
        )

        evidence_by_key: dict[
            tuple[str, str, date_type | None, Decimal | None, str | None],
            PortfolioPlannerSourceWacFxEvidence,
        ] = {}
        evidence_incomplete = False
        if result is not None:
            for qualifying_tx in result.wac_qualifying_txs:
                if qualifying_tx.original_currency is None:
                    continue
                source_currency = validated_currency(qualifying_tx.original_currency)
                if source_currency == target_currency:
                    continue
                fx_info = qualifying_tx.fx_info
                rate = qualifying_tx.fx_rate_used
                if source_currency is None or fx_info is None or fx_info.fx_rate_date is None or rate is None:
                    evidence_incomplete = True
                    continue
                base, quote, inverted = normalized_fx_pair(source_currency, target_currency)
                saved_row = saved_fx_rows.get((base, quote, fx_info.fx_rate_date))
                saved_directed_rate: Decimal | None = None
                # A saved 0 or infinity is no evidence, as for the quotes: never an infinite rate in it (X-R45b, MF)
                if saved_row is not None and usable_rate(saved_row.rate):
                    saved_directed_rate = oriented_rate(saved_row.rate, source_currency, target_currency)
                if saved_row is None or saved_directed_rate is None or not _rates_match(saved_directed_rate, rate):
                    evidence_incomplete = True
                    evidence = PortfolioPlannerSourceWacFxEvidence(
                        source_currency=source_currency,
                        destination_currency=target_currency,
                        rate=None,
                        reference_date=None,
                        source=None,
                        inverted=inverted,
                        status="missing",
                    )
                else:
                    evidence = PortfolioPlannerSourceWacFxEvidence(
                        source_currency=source_currency,
                        destination_currency=target_currency,
                        rate=saved_directed_rate,
                        reference_date=fx_info.fx_rate_date,
                        source=saved_row.source,
                        inverted=inverted,
                        status="available",
                    )
                evidence_key = (
                    evidence.source_currency,
                    evidence.destination_currency,
                    evidence.reference_date,
                    evidence.rate,
                    evidence.source,
                )
                evidence_by_key[evidence_key] = evidence

            for missing_pair in result.wac_missing_pairs:
                try:
                    source_currency, destination_currency = missing_pair.pair.split("/", maxsplit=1)
                    source_currency = Currency.validate_code(source_currency)
                    destination_currency = Currency.validate_code(destination_currency)
                except (TypeError, ValueError):
                    evidence_incomplete = True
                    continue
                _base, _quote, inverted = normalized_fx_pair(
                    source_currency,
                    destination_currency,
                )
                evidence = PortfolioPlannerSourceWacFxEvidence(
                    source_currency=source_currency,
                    destination_currency=destination_currency,
                    rate=None,
                    reference_date=None,
                    source=None,
                    inverted=inverted,
                    status="missing",
                )
                evidence_key = (
                    evidence.source_currency,
                    evidence.destination_currency,
                    evidence.reference_date,
                    evidence.rate,
                    evidence.source,
                )
                evidence_by_key[evidence_key] = evidence
                evidence_incomplete = True

        evidence = sorted(
            evidence_by_key.values(),
            key=lambda item: (
                item.source_currency,
                item.destination_currency,
                item.reference_date or date_type.min,
                str(item.rate) if item.rate is not None else "",
                item.source or "",
            ),
        )
        unit_cost = None
        if result is not None and result.wac is not None and result.wac.code == target_currency and not evidence_incomplete:
            unit_cost = result.wac.amount

        if evidence_incomplete or (result is not None and result.wac_missing_pairs):
            issues.append(
                field_issue(
                    code="allocation.wac_fx_missing",
                    kind="missing",
                    severity="error",
                    section="wac_contexts",
                    entity_kind="wac_context",
                    entity_id=wac_id,
                    field="fx_evidence",
                )
            )
        elif unit_cost is None:
            issues.append(
                field_issue(
                    code="allocation.wac_missing",
                    kind="missing",
                    severity="error",
                    section="wac_contexts",
                    entity_kind="wac_context",
                    entity_id=wac_id,
                    field="unit_cost",
                )
            )

        rows.append(
            PortfolioPlannerWacContext(
                wac_id=wac_id,
                holding_id=holding_id,
                asset_id=asset_key(asset_id),
                broker_id=broker_key(broker_id),
                method="runtime_wac",
                unit_cost=unit_cost,
                fiscal_currency=None,
                target_currency=target_currency,
                as_of=as_of,
                fx_evidence=evidence,
                provenance_id=WAC_PROVENANCE_ID,
            )
        )
    return rows
