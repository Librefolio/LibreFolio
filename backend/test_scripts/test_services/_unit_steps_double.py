"""A ``unit_rate_steps`` double for pure tests of ``PortfolioCalculationEngine._preload_fx_rates`` (P3, «formule veloci»).

Since P3 the preload asks the FX service no rate a day: it gathers each currency's needs as windows of days — the
range, a cash transit, single days — and makes one ``unit_rate_steps(session, {(currency, target): [(first, last), …]})``
call, then returns ``AskedDayRates(steps, windows)``. A pure test replaces ``unit_rate_steps`` on the engine module
(``portfolio_engine_module.unit_rate_steps``) with :class:`UnitStepsDouble` and asserts on the windows: the days they
cover are the ``(currency, day)`` the preload used to hand ``convert_bulk`` one by one.

The double answers every pair with a step on the first day of each of its windows, all of ``value`` (None: no step, as a
pair without any stored rate), so every asked day reads ``value``. Like the FX service it raises ``ValueError`` on a
pair of one currency and on a window that ends before it starts.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from backend.app.services.fx.conversion import UnitRateSteps

Pair = tuple[str, str]
Window = tuple[date, date]


@dataclass
class UnitStepsDouble:
    """``unit_rate_steps`` double: one step of ``value`` on the first day of every window asked; every call recorded."""

    value: Decimal | None = Decimal("1")
    sessions: list[Any] = field(default_factory=list)
    calls: list[dict[Pair, list[Window]]] = field(default_factory=list)

    async def __call__(self, session: Any, requests: Mapping[Pair, Iterable[Window]]) -> dict[Pair, UnitRateSteps]:
        asked = {pair: list(windows) for pair, windows in requests.items()}
        self.sessions.append(session)
        self.calls.append(asked)
        steps: dict[Pair, UnitRateSteps] = {}
        for (source, destination), windows in asked.items():
            if source == destination:
                raise ValueError(f"unit_rate_steps: {source}/{destination} is one currency, not a pair")
            for first, last in windows:
                if last < first:
                    raise ValueError(f"unit_rate_steps: the window {first} – {last} of {source}/{destination} ends before it starts")
            days = () if self.value is None else tuple(sorted({first for first, _last in windows}))
            steps[(source, destination)] = UnitRateSteps(source=source, destination=destination, days=days, values=(self.value,) * len(days), rate_days=days)
        return steps

    def only_call(self) -> dict[Pair, list[Window]]:
        """The windows of the one call made; fails unless exactly one was."""
        assert len(self.calls) == 1, f"one unit_rate_steps call expected, got {len(self.calls)}"
        return self.calls[0]

    def asked_keys(self) -> set[tuple[str, str, date]]:
        """Every ``(source, destination, day)`` the windows of the one call cover: what ``convert_bulk`` was handed before P3."""
        return {(source, destination, day) for (source, destination), windows in self.only_call().items() for day in window_days(windows)}

    def runs(self) -> dict[Pair, list[Window]]:
        """The windows of the one call as the days they cover, written as maximal runs: one canonical form whatever order,
        overlap or duplication the preload gathers them in."""
        return {pair: day_runs(window_days(windows)) for pair, windows in self.only_call().items()}


def window_days(windows: Iterable[Window]) -> set[date]:
    """Every day of ``windows``, both ends included."""
    return {date.fromordinal(ordinal) for first, last in windows for ordinal in range(first.toordinal(), last.toordinal() + 1)}


def day_runs(days: Iterable[date]) -> list[Window]:
    """``days`` as ascending maximal runs of consecutive days."""
    runs: list[Window] = []
    for day in sorted(set(days)):
        if runs and day == runs[-1][1] + timedelta(days=1):
            runs[-1] = (runs[-1][0], day)
        else:
            runs.append((day, day))
    return runs


def runs_of(keys: Sequence[tuple[str, str, date]] | set[tuple[str, str, date]]) -> dict[Pair, list[Window]]:
    """``(source, destination, day)`` keys as maximal runs by pair."""
    by_pair: dict[Pair, set[date]] = {}
    for source, destination, day in keys:
        by_pair.setdefault((source, destination), set()).add(day)
    return {pair: day_runs(days) for pair, days in by_pair.items()}
