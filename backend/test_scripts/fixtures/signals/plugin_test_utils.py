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
)
from scripts.spikes.signals.run_signal_backend_spike import (
    generate_datasets,
    load_manifest,
)

VISIBLE_POINTS = 128


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
) -> SignalExecutionContext:
    visible = points[-visible_points:]
    return SignalExecutionContext(
        domain=domain,
        requested_range=DateRangeModel(
            start=visible[0].date,
            end=visible[-1].date,
        ),
        source_reference=f"{domain.value}:plugin-test",
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
