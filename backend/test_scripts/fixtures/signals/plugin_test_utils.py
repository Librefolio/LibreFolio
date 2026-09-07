"""Shared deterministic helpers for production signal plugin tests."""

from __future__ import annotations

from typing import Iterable

import numpy as np

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.signals import (
    SignalBandSeries,
    SignalDomain,
    SignalExecutionContext,
    SignalPricePoint,
    SignalSourceCapability,
    SignalVolumeKind,
)
from scripts.spikes.signals.run_signal_backend_spike import (
    generate_datasets,
    load_manifest,
)

VISIBLE_POINTS = 128

# Fixture datasets are synthetic OHLCV series with no real provider behind
# them. Volume-dependent plugins (MFI, OBV) now require a source that
# declares `supports_meaningful_volume`; grant it by default here so the many
# existing plugin tests built on this shared fixture keep exercising their
# actual math instead of getting gated on capability they never asked about.
_DEFAULT_SOURCE_CAPABILITY = SignalSourceCapability(
    supports_meaningful_volume=True,
    volume_kind=SignalVolumeKind.TRADED_SHARES,
)


def load_signal_frames(names: Iterable[str]):
    generated = generate_datasets(load_manifest())
    return {name: generated[name] for name in names}


def frame_to_points(frame) -> list[SignalPricePoint]:
    return [
        SignalPricePoint(
            date=index.date(),
            open=str(row.open),
            high=str(row.high),
            low=str(row.low),
            close=str(row.close),
            volume=str(row.volume),
        )
        for index, row in frame.iterrows()
    ]


def execution_context(
    points: list[SignalPricePoint],
    *,
    visible_points: int = VISIBLE_POINTS,
    domain: SignalDomain = SignalDomain.ASSET,
    source_capability: SignalSourceCapability = _DEFAULT_SOURCE_CAPABILITY,
) -> SignalExecutionContext:
    visible = points[-visible_points:]
    return SignalExecutionContext(
        domain=domain,
        requested_range=DateRangeModel(
            start=visible[0].date,
            end=visible[-1].date,
        ),
        source_reference=f"{domain.value}:plugin-test",
        source_capability=source_capability,
    )


def numeric_matrix(computation) -> np.ndarray:
    columns: list[list[float]] = []
    for series in computation.series:
        if isinstance(series, SignalBandSeries):
            columns.extend(
                [
                    [np.nan if point.lower is None else point.lower for point in series.points],
                    [np.nan if point.middle is None else point.middle for point in series.points],
                    [np.nan if point.upper is None else point.upper for point in series.points],
                ]
            )
        else:
            columns.append([np.nan if point.value is None else point.value for point in series.points])
    return np.asarray(columns, dtype=float).T


def normalized_error(
    reference: np.ndarray,
    candidate: np.ndarray,
) -> float:
    finite = np.isfinite(reference)
    if not finite.any():
        raise ValueError("reference has no finite values")
    if not np.isfinite(candidate[finite]).all():
        raise ValueError("candidate is non-finite where reference is finite")
    scale = max(1.0, float(np.max(np.abs(reference[finite]))))
    return float(np.max(np.abs(reference[finite] - candidate[finite])) / scale)


__all__ = [
    "VISIBLE_POINTS",
    "execution_context",
    "frame_to_points",
    "load_signal_frames",
    "normalized_error",
    "numeric_matrix",
]
