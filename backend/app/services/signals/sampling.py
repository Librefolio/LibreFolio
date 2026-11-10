"""A signal result reduced onto the dates of a sampled series (Z-29s, O1): the price query's and the FX conversion's one
home of it (Z-29fx).

Each series of the result is reduced by its output's ``aggregation_profile``, read from the plugin as AI Export reads it
(``aggregation.sample_signal_series``), and the series reduced are then put on identical dates, as ``SignalResult`` wants
them (``aggregation.align_signal_series``).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date as date_type

import structlog

from backend.app.schemas.signals import SignalResult
from backend.app.services.assets.price_sampling import SampleResolution
from backend.app.services.signals.aggregation import align_signal_series, sample_signal_series
from backend.app.services.signals.registry import SignalPluginRegistry

logger = structlog.get_logger(__name__)


def sample_signal_result(signal: SignalResult, resolution: SampleResolution, render_dates: Sequence[date_type]) -> SignalResult:
    """``signal`` with each series reduced to ``render_dates`` (the sampled series' dates, one per bucket of
    ``resolution``) by its output's ``aggregation_profile``, then all on the same dates (O1). A series no output spec
    describes stays as it is, logged: none today."""
    if not signal.series:
        return signal
    plugin_class = SignalPluginRegistry.get_plugin(signal.signal_code)
    profiles = {output.key: output.aggregation_profile for output in plugin_class.output_specs} if plugin_class is not None else {}
    reduced = []
    for series in signal.series:
        profile = profiles.get(series.key)
        if profile is None:
            logger.warning("Signal series left daily on a sampled item: no output spec", signal_code=signal.signal_code, series_key=series.key)
            reduced.append(series)
            continue
        reduced.append(sample_signal_series(series, profile, resolution, render_dates))
    return signal.model_copy(update={"series": _align_reduced(signal.series, reduced)})


def _align_reduced(daily: list, reduced: list) -> list:
    """``reduced`` (``daily``'s series each reduced alone) on identical dates, as ``SignalResult`` wants them (O1,
    ``align_signal_series``). A series left as it was (no output spec, or a reduction that kept no value) keeps its daily
    dates and is not aligned with the others: a client does not read the step from the density of a signal."""
    done = [index for index, (before, after) in enumerate(zip(daily, reduced, strict=True)) if after is not before]
    for index, series in zip(done, align_signal_series([reduced[index] for index in done]), strict=True):
        reduced[index] = series
    return reduced
