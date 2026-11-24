"""The simulation's own history: all the common history available, never the page's period (RN-16, developer's Q4 c).

The page's period chose the window the simulation was estimated on, so one asset over one horizon gave a median of
+1 400 % from «3M» and −39 % from «1Y». Like the historical replay, the simulation now prepares a window of its own:
from the day after the latest first quote among the scope's assets — the first day every one of them has a price
behind it — to the end of the data, the same end the page reads up to today. The page's period no longer reaches it.

Two ceilings shape that window before it is read. The price budget of one preparation (J-50, ``MAX_BULK_ITEM_DAYS``
per-day points over every asset) moves its start forward to the most recent days that fit, instead of refusing; the
bootstrap's history ceiling then keeps the most recent observations that cross the process boundary (in the plugin).
The result states the window it was estimated on; `history_truncated` says only the bootstrap's trim — a start moved by
the price budget (over 27 years of prices at 100 holdings) shows in the window's start date alone.

Who takes part (RN-16b, developer's Q7 «per ora B», 17/11/2026): a holding with less history than the horizon stays out
— its weight counted as cash, the page naming it — unless none reaches the horizon (:func:`simulation_participants`).

The period the days are drawn from (RSK-SIM1, P-7, 23/11/2026): by default all that common history; the user may choose a
period inside it (``SimulationParams.history_start``/``history_end``) — in turbulent times, drawing both the crashes and
the rebounds gives too rosy or too dark a cone. Who takes part is still decided on all the history available, so a short
period never drops a holding in silence (the coordinator's answer); the period only chooses which days are drawn. A start
before the common history moves to it, with a warning; the result states the window it could have drawn from
(``history_available_start``/``_end``) beside the one it drew from.
"""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, replace
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.risk.results import RiskExcludedAsset, RiskWarning
from backend.app.schemas.risk.scope import RiskQueryRequest
from backend.app.schemas.risk.vocabulary import RiskErrorCode, RiskHistoricalReplayExclusionTreatment, RiskScopeKind
from backend.app.services.platform.data_quality_thresholds import REPLAY_EXCLUDED_WEIGHT_WARNING_SHARE
from backend.app.services.risk.base import RiskExecutionContext, RiskSimulationHistoryContext, RiskUnavailableError
from backend.app.services.risk.eligibility import first_fx_rate_dates, load_price_window_facts
from backend.app.services.risk.results import build_execution_context
from backend.app.services.risk.scope import ScopeInputs, bounded_range, prepare_asset_series
from backend.app.utils.date_range_limits import MAX_BULK_ITEM_DAYS
from backend.app.utils.datetime_utils import latest_range_end


def first_useful_day(first_quote: date | None, first_rate: date | None) -> date | None:
    """A holding's first day the simulation can use (RN-16b, point 1): the later of its first price and its first rate
    into the page's currency, when it needs one. None for a holding never quoted."""
    if first_quote is None:
        return None
    return first_quote if first_rate is None else max(first_quote, first_rate)


@dataclass(frozen=True)
class SimulationParticipants:
    """Who the simulation's history is estimated on, who it leaves out for being shorter than the horizon, and who was
    never quoted (the preparation excludes those, as the page does)."""

    taking_part: tuple[int, ...]
    short: tuple[int, ...]
    never_quoted: tuple[int, ...]


def simulation_participants(first_days: Mapping[int, date | None], *, horizon_days: int, end: date) -> SimulationParticipants:
    """Which holdings the simulation's history is estimated on: the one place that decides.

    The developer's answer to Q7, 17/11/2026, «per ora B», in the consultant's rule (RN-16b): a holding takes part when
    its history — ``end`` minus its first useful day (:func:`first_useful_day`), in calendar days, the measure of the
    amber «history shorter than the horizon» line — reaches the horizon, the horizon itself included. A shorter one stays
    out: on a weighted scope its weight counts as cash at zero return (the historical replay's treatment), and the page
    names it. When no holding reaches the horizon, every quoted one takes part — Q4 c, with its amber line — and so does
    the only holding of one asset, which is never left out. The horizon decides, so changing it decides again. A holding
    never quoted takes no part.
    """
    quoted = {asset_id: first for asset_id, first in first_days.items() if first is not None}
    never_quoted = tuple(asset_id for asset_id, first in first_days.items() if first is None)
    reaching = tuple(asset_id for asset_id, first in quoted.items() if (end - first).days >= horizon_days)
    if not reaching:
        return SimulationParticipants(taking_part=tuple(quoted), short=(), never_quoted=never_quoted)
    return SimulationParticipants(taking_part=reaching, short=tuple(asset_id for asset_id in quoted if asset_id not in reaching), never_quoted=never_quoted)


def simulation_window(first_days: Mapping[int, date], *, end: date) -> DateRangeModel | None:
    """The window the simulation is estimated on, from the first useful days of the holdings that take part; None when
    none does.

    It starts the day after the latest of those days — so every participant has a price on the day before, the baseline
    the first return is measured from — and no earlier than the price budget allows for this many assets: the most recent
    days that fit (J-50). It ends at ``end``.
    """
    if not first_days:
        return None
    start = max(first_days.values()) + timedelta(days=1)
    budget_days = MAX_BULK_ITEM_DAYS // len(first_days)
    # Few holdings have a budget longer than the calendar before ``end`` (one holding: a million days): never earlier.
    if budget_days - 2 < (end - date.min).days:
        start = max(start, end - timedelta(days=budget_days - 2))
    return bounded_range(DateRangeModel(start=min(start, end), end=end))


def _short_history_warnings(short: tuple[int, ...], first_days: Mapping[int, date | None], *, horizon_days: int, end: date) -> list[RiskWarning]:
    """The page names each holding left out (RN-16b), with its history and the horizon. Degrading, as the replay's
    exclusions are: a part of the scope is not in the projection (its weight is idle cash), unlike a history that is
    only short."""
    warnings: list[RiskWarning] = []
    for asset_id in short:
        first = first_days[asset_id]
        history_days = (end - first).days if first is not None else 0
        warnings.append(
            RiskWarning(
                code="simulation_asset_shorter_than_horizon",
                message=f"Asset {asset_id} has {history_days} days of history, less than the {horizon_days}-day horizon: left out of the simulation, its weight counted as cash.",
                details={"asset_id": asset_id, "treatment": RiskHistoricalReplayExclusionTreatment.ZERO_RETURN_RESIDUAL.value},
                message_i18n_key="risk.warnings.simulation_excluded_short_history",
                message_params={"history_days": history_days, "horizon_days": horizon_days},
            )
        )
    return warnings


def _mostly_excluded_warning(excluded_ids: AbstractSet[int], weights: Mapping[int, float]) -> RiskWarning | None:
    """Past the replay's own threshold, the simulation describes a minority of the portfolio (RN-16c, the consultant):
    every holding left out counts — short, never quoted, without a rate — because the line says how much is covered,
    and the per-reason warnings say why. One meaning on both analytics, on one constant."""
    excluded_weight = sum(weights.get(asset_id, 0.0) for asset_id in excluded_ids)
    if excluded_weight <= REPLAY_EXCLUDED_WEIGHT_WARNING_SHARE:
        return None
    covered = max(0.0, 1.0 - excluded_weight)
    return RiskWarning(
        code="simulation_mostly_excluded",
        message=f"The simulation describes only {covered:.0%} of the portfolio: the rest is left out of it.",
        details={"excluded_weight_total": excluded_weight, "threshold": REPLAY_EXCLUDED_WEIGHT_WARNING_SHARE},
        message_i18n_key="risk.warnings.simulation_mostly_excluded",
        message_params={"covered": round(covered, 4)},
    )


def _without_assets(warnings: tuple[RiskWarning, ...], asset_ids: frozenset[int]) -> list[RiskWarning]:
    """The generic «excluded for insufficient history» warning, without the holdings a dedicated warning already names."""
    kept: list[RiskWarning] = []
    for warning in warnings:
        if warning.code == "assets_excluded" and (warning.details or {}).get("reason") == "insufficient_history":
            remaining = [asset_id for asset_id in warning.details.get("asset_ids", []) if asset_id not in asset_ids]
            if not remaining:
                continue
            warning = warning.model_copy(update={"details": {**warning.details, "asset_ids": remaining}})
        kept.append(warning)
    return kept


def _chosen_window(
    participant_days: Mapping[int, date],
    available: DateRangeModel,
    *,
    history_start: date | None,
    history_end: date | None,
) -> tuple[DateRangeModel, list[RiskWarning]]:
    """The window the days are drawn from: the user's period inside ``available``, or ``available`` itself.

    A chosen end earlier than the common one moves the window's end there, and the price budget (J-50) counts from it; a
    chosen start before the window's start — the common history's, or the budget's — moves to it, with a warning that
    names both days. A period that ends before the common history starts, or starts after the history ends, leaves
    nothing to draw from: refused.
    """
    if history_start is None and history_end is None:
        return available, []
    window = available
    if history_end is not None and history_end < available.end:
        if history_end < available.start:
            raise RiskUnavailableError(
                f"The chosen period ends on {history_end.isoformat()}, before the common history starts on {available.start.isoformat()}",
                code=RiskErrorCode.INSUFFICIENT_HISTORY,
                details={"history_end": history_end.isoformat(), "available_start": available.start.isoformat()},
            )
        window = simulation_window(participant_days, end=history_end) or available
    warnings: list[RiskWarning] = []
    if history_start is not None:
        if history_start < window.start:
            warnings.append(
                RiskWarning(
                    code="simulation_history_start_moved",
                    message=f"The chosen period starts on {history_start.isoformat()}, before the common history: the simulation draws from {window.start.isoformat()}.",
                    details={"requested_start": history_start.isoformat(), "used_start": window.start.isoformat()},
                    message_i18n_key="risk.warnings.simulation_history_start_moved",
                    message_params={"requested_start": history_start.isoformat(), "used_start": window.start.isoformat()},
                )
            )
        elif history_start > window.end:
            raise RiskUnavailableError(
                f"The chosen period starts on {history_start.isoformat()}, after the history ends on {window.end.isoformat()}",
                code=RiskErrorCode.INSUFFICIENT_HISTORY,
                details={"history_start": history_start.isoformat(), "available_end": window.end.isoformat()},
            )
        else:
            window = DateRangeModel(start=history_start, end=window.end)
    return window, warnings


async def prepare_simulation_context(
    db: AsyncSession,
    *,
    request: RiskQueryRequest,
    scope_inputs: ScopeInputs,
    never_priced_asset_ids: frozenset[int],
    horizon_days: int,
    market_holidays: AbstractSet[date] = frozenset(),
    history_start: date | None = None,
    history_end: date | None = None,
) -> RiskExecutionContext:
    """The execution context of a simulation, rebuilt whole from its own window and its own participants (weights, cash,
    exclusions, series, warnings). ``history_start``/``history_end``: the period the user chose to draw from, None for all
    the common history."""
    end = latest_range_end()
    facts = await load_price_window_facts(
        db,
        asset_ids=scope_inputs.requested_asset_ids,
        window_start=end,
        window_end=end,
        target_currency=request.target_currency,
        market_holidays=market_holidays,
    )
    first_rates = await first_fx_rate_dates(db, currencies={item.currency for item in facts.values() if item.currency}, target_currency=request.target_currency)
    first_days = {asset_id: first_useful_day(item.first_quote_ever, first_rates.get(item.currency) if item.currency else None) for asset_id, item in facts.items()}
    chosen = simulation_participants(first_days, horizon_days=horizon_days, end=end)
    participant_days = {asset_id: first_days[asset_id] for asset_id in chosen.taking_part}
    available = simulation_window(participant_days, end=end)
    if available is None:
        raise RiskUnavailableError(
            "No asset of the scope has a price to estimate the simulation on",
            code=RiskErrorCode.INSUFFICIENT_HISTORY,
        )
    window, period_warnings = _chosen_window(participant_days, available, history_start=history_start, history_end=history_end)
    short = frozenset(chosen.short)
    prepared = await prepare_asset_series(
        db,
        asset_ids=tuple(sorted(asset_id for asset_id in scope_inputs.requested_asset_ids if asset_id not in short)),
        date_range=window,
        target_currency=request.target_currency,
        market_holidays=market_holidays,
    )
    context = build_execution_context(
        request=request.model_copy(update={"date_range": window}),
        scope_inputs=scope_inputs,
        prepared=prepared,
        never_priced_asset_ids=never_priced_asset_ids,
    )
    warnings = list(_without_assets(tuple(context.execution_warnings), short)) + _short_history_warnings(chosen.short, first_days, horizon_days=horizon_days, end=end) + period_warnings
    if request.scope.kind == RiskScopeKind.PORTFOLIO:
        excluded_ids = {item.asset_id for item in context.excluded_assets} | short
        if (mostly := _mostly_excluded_warning(excluded_ids, scope_inputs.weights)) is not None:
            warnings.append(mostly)
    # RN-16c: the result's facts as precise as its warnings — a short holding has its own reason, with what it rests on.
    excluded_assets = tuple(
        RiskExcludedAsset(asset_id=item.asset_id, reason="shorter_than_horizon", details={"horizon_days": horizon_days, "first_useful_day": first_days[item.asset_id].isoformat()}) if item.asset_id in short and first_days.get(item.asset_id) is not None else item for item in context.excluded_assets
    )
    history = RiskSimulationHistoryContext(available=available, chosen=history_start is not None or history_end is not None)
    return replace(context, execution_warnings=tuple(warnings), excluded_assets=excluded_assets, simulation_history=history)
