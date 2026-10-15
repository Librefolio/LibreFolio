"""Current weight distribution for the planner source, valued by the portfolio engine and rounded with the largest-remainder method."""

from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from decimal import Decimal
from fractions import Fraction

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.portfolio import (
    PLANNER_CURRENT_WEIGHT_QUANTUM,
    PortfolioPlannerCurrentDistribution,
    PortfolioPlannerCurrentWeight,
    PortfolioPlannerSourceIssue,
)
from backend.app.services.pac_allocator.source.keys import ENGINE_PROVENANCE_ID, asset_key, current_weight_key, field_issue, normalized_fx_pair, text_param
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD


def _largest_remainder_weights(values: dict[int, Decimal]) -> dict[int, Decimal]:
    """Split exactly 1 into weight quanta proportional to non-negative values.

    Every exact share is floored to the quantum; the quanta still missing go to the
    largest remainders, ties to the lowest asset id, so the weights sum to exactly 1.
    """
    units = int(1 / PLANNER_CURRENT_WEIGHT_QUANTUM)
    total = sum((Fraction(value) for value in values.values()), Fraction(0))
    counts: dict[int, int] = {}
    remainders: list[tuple[Fraction, int]] = []
    for asset_id, value in values.items():
        exact = Fraction(value) * units / total
        counts[asset_id] = exact.numerator // exact.denominator
        remainders.append((exact - counts[asset_id], asset_id))
    missing_units = units - sum(counts.values())
    for _remainder, asset_id in sorted(remainders, key=lambda item: (-item[0], item[1]))[:missing_units]:
        counts[asset_id] += 1
    return {asset_id: (Decimal(count) * PLANNER_CURRENT_WEIGHT_QUANTUM).quantize(PLANNER_CURRENT_WEIGHT_QUANTUM) for asset_id, count in counts.items()}


async def build_planner_current_distribution(  # noqa: C901 — per-Asset valuation outcomes stay explicit
    session: AsyncSession,
    *,
    user_id: int,
    broker_ids: list[int],
    scenario_asset_ids: list[int],
    as_of: date_type,
    target_currency: str,
    issues: list[PortfolioPlannerSourceIssue],
) -> PortfolioPlannerCurrentDistribution:
    """Weight the scenario Assets by the portfolio engine's market value at ``as_of``.

    Same engine call as the portfolio summary, so the market values match the Dashboard
    positions for the same Brokers and date.
    The denominator is the scenario instead of every holding and cash stays out; a
    held Asset without a valuation withholds every weight instead of vanishing.
    """
    # Lazy: read at call time, so a test can replace PortfolioCalculationEngine on its module.
    from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415
    from backend.app.services.financial_math.portfolio.models import ValuationSource  # noqa: PLC0415

    engine_result = await PortfolioCalculationEngine(session).calculate(
        user_id=user_id,
        broker_ids=sorted(broker_ids),
        date_from=None,
        date_to=as_of,
        target_currency=target_currency,
    )
    scenario = set(scenario_asset_ids)
    positions_by_asset: dict[int, list] = defaultdict(list)
    for position in engine_result.position_states_end:
        if position.asset_id in scenario and position.quantity > QUANTITY_DUST_THRESHOLD:
            positions_by_asset[position.asset_id].append(position)

    values: dict[int, Decimal] = {}
    row_facts: list[dict] = []
    complete = True
    for asset_id in scenario_asset_ids:
        weight_id = current_weight_key(asset_id)
        positions = sorted(positions_by_asset.get(asset_id, []), key=lambda position: position.broker_id)
        if not positions:
            values[asset_id] = Decimal("0")
            row_facts.append(
                {
                    "weight_id": weight_id,
                    "asset_id": asset_key(asset_id),
                    "held": False,
                    "valuation_source": None,
                    "valuation_reference_date": None,
                    "valuation_days_before_requested": None,
                    "valuation_stale": False,
                }
            )
            continue

        # The engine values one Asset per date, so every Broker row shares the mark.
        valuation = positions[0]
        unvalued = next((position for position in positions if position.market_value is None), None)
        if unvalued is not None:
            complete = False
            if unvalued.valuation_source != ValuationSource.MISSING and unvalued.missing_fx_pair:
                first, second, _inverted = normalized_fx_pair(*unvalued.missing_fx_pair.split("/", 1))
                issues.append(
                    field_issue(
                        code="allocation.saved_fx_missing",
                        kind="missing",
                        severity="error",
                        section="current_distribution",
                        entity_kind="current_weight",
                        entity_id=weight_id,
                        field="weight",
                        params=[text_param("pair", f"{first}/{second}")],
                    )
                )
            else:
                issues.append(
                    field_issue(
                        code="allocation.price_missing",
                        kind="missing",
                        severity="error",
                        section="current_distribution",
                        entity_kind="current_weight",
                        entity_id=weight_id,
                        field="weight",
                    )
                )
        elif any(position.market_value < 0 for position in positions):
            complete = False
            issues.append(
                field_issue(
                    code="allocation.nonpositive_price",
                    kind="invalid",
                    severity="error",
                    section="current_distribution",
                    entity_kind="current_weight",
                    entity_id=weight_id,
                    field="weight",
                )
            )
        else:
            values[asset_id] = sum((position.market_value for position in positions), Decimal("0"))

        reference_date = valuation.valuation_reference_date
        row_facts.append(
            {
                "weight_id": weight_id,
                "asset_id": asset_key(asset_id),
                "held": True,
                "valuation_source": ValuationSource(valuation.valuation_source).value,
                "valuation_reference_date": reference_date,
                "valuation_days_before_requested": (as_of - reference_date).days if reference_date is not None else None,
                "valuation_stale": any(position.valuation_stale for position in positions),
            }
        )

    weights: dict[int, Decimal] = {}
    if not complete:
        status = "incomplete"
    elif sum(values.values(), Decimal("0")) <= 0:
        status = "no_holdings"
    else:
        status = "complete"
        weights = _largest_remainder_weights(values)

    return PortfolioPlannerCurrentDistribution(
        status=status,
        method="portfolio_engine_market_value",
        rounding="largest_remainder",
        weight_quantum="0.0001",
        as_of=as_of,
        provenance_id=ENGINE_PROVENANCE_ID,
        rows=[PortfolioPlannerCurrentWeight(**facts, weight=weights.get(asset_id)) for asset_id, facts in zip(scenario_asset_ids, row_facts, strict=True)],
    )
