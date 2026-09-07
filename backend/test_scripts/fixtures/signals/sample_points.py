"""Small deterministic neutral input series for signal contract tests."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from backend.app.schemas.signals import SignalEventPoint, SignalPricePoint

_CLOSE_VALUES = ("100", "102", "101", "105", "104", "108")


def make_signal_price_points() -> list[SignalPricePoint]:
    start = date(2026, 1, 1)
    points: list[SignalPricePoint] = []
    for index, raw_close in enumerate(_CLOSE_VALUES):
        close = Decimal(raw_close)
        points.append(
            SignalPricePoint(
                date=start + timedelta(days=index),
                open=close - Decimal("0.5"),
                high=close + Decimal("1.5"),
                low=close - Decimal("1.5"),
                close=close,
                volume=Decimal("1000000") + Decimal(index * 10000),
            )
        )
    return points


def make_signal_event_points() -> list[SignalEventPoint]:
    start = date(2026, 1, 1)
    return [
        SignalEventPoint(
            date=start + timedelta(days=1),
            type="DIVIDEND",
            value=Decimal("2"),
            metadata={"source": "fixture"},
        ),
        SignalEventPoint(
            date=start + timedelta(days=4),
            type="DIVIDEND",
            value=Decimal("1.5"),
            metadata={"source": "fixture"},
        ),
    ]


__all__ = ["make_signal_event_points", "make_signal_price_points"]
