"""A conversion of ``POST /fx/currencies/convert`` sampled for a compact chart (Z-29fx).

The FX list's cards draw a few hundred points at most, as the asset list's do (Z-29b): a conversion's ``max_points``,
``resolution`` or ``sample_like`` asks for the results of one day a week or a month instead of every day, with the price
query's own rule (``services/assets/price_sampling.py``: the step, the buckets, the references). The conversion is still
computed day by day (its signals and the day budget need every day) and reduced in memory: each date of the sample keeps
the daily result of that date, unchanged.

Pure: the conversions' own fields and the days their daily results start on.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from backend.app.services.assets.price_sampling import SampleResolution, choose_resolution, sample_dates


@dataclass(frozen=True)
class FXSamplePlan:
    """How one sampled conversion answers: its step, the fill's first day it starts from (the later of the two first days
    for a follower; None with nothing to fill) and the dates it keeps."""

    resolution: SampleResolution
    first: date | None
    dates: tuple[date, ...]


def asks_sample(conversion: Any) -> bool:
    """Whether a conversion asks to be sampled: ``max_points``, ``resolution`` or ``sample_like``."""
    return any(getattr(conversion, name, None) is not None for name in ("max_points", "resolution", "sample_like"))


def _own_step(conversion: Any, first: date, end: date) -> SampleResolution:
    """The step a conversion's own ``max_points`` or ``resolution`` gives on a fill from ``first`` to ``end``; daily with
    neither."""
    if conversion.max_points is not None:
        return choose_resolution(first, end, conversion.max_points)
    if conversion.resolution is not None:
        return conversion.resolution
    return "daily"


def plan_conversion_samples(conversions: Sequence[Any], firsts: Mapping[int, date | None], ends: Mapping[int, date], references: Mapping[int, int]) -> dict[int, FXSamplePlan]:
    """By position, the plan of each conversion that asks to be sampled (``asks_sample``).

    ``firsts`` holds, by position, the fill's first day F: the first day of the cut range whose conversion has a result
    (the range's start when a rate precedes it); ``ends`` the cut range's end; ``references`` the position each
    ``sample_like`` names (``resolve_sample_references``). With ``max_points`` the step is ``choose_resolution(F, end)``,
    with ``resolution`` the one asked. A follower takes the step of the conversion it names, on that conversion's own fill,
    from the later of the two first days; on its own fill when the named one has none. A conversion with nothing to fill
    answers nothing, daily.
    """
    plans: dict[int, FXSamplePlan] = {}
    for index, conversion in enumerate(conversions):
        if not asks_sample(conversion):
            continue
        own_first, end = firsts.get(index), ends.get(index)
        if own_first is None or end is None:
            plans[index] = FXSamplePlan("daily", None, ())
            continue
        first = own_first
        if index in references:
            named = references[index]
            named_first = firsts.get(named)
            if named_first is not None:
                step = _own_step(conversions[named], named_first, ends.get(named, end))
                first = max(named_first, own_first)
            else:
                step = _own_step(conversions[named], own_first, end)
        else:
            step = _own_step(conversion, own_first, end)
        plans[index] = FXSamplePlan(step, first, tuple(sample_dates(first, end, step)))
    return plans
