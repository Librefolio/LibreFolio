"""The phases a plan goes through, as the planner reports them (V2 of project 67, ``REB-risposta-a-DEC-P4b.md``).

The planner calls an optional function, ``progress(phase, step=None, total=None)``, the shape of the Tool context's
``report_progress`` (V1), before each phase: ``validate``, ``model``, ``search``, ``verify``, ``report``, in that order.
``search`` carries ``step`` and ``total``: the named stage of the cascade it starts, over the named stages of the program
(the PAC's five; the Rebalancer's score, or the «Target first» chain, then its two tie-breaks). The canonical tie-break
vector, one stage per decision, is not counted: it would outgrow the platform's cap of messages per item.

A message carries a phase name and at most two whole counts: never a datum of the scenario or of the result, never a
percentage. Without the function nothing changes and nothing is spent: the calls are a ``None`` check.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

__all__ = ["PLANNER_PHASES", "PlannerPhase", "ProgressReporter", "report_phase"]

type PlannerPhase = Literal["validate", "model", "search", "verify", "report"]
type ProgressReporter = Callable[..., None]

#: The phases of a plan, in the order the planner reports them; the services declare them on their operation (V2-4).
PLANNER_PHASES: tuple[str, ...] = ("validate", "model", "search", "verify", "report")


def report_phase(progress: ProgressReporter | None, phase: PlannerPhase, step: int | None = None, total: int | None = None) -> None:
    """Tell ``progress`` that ``phase`` starts (``search``: its ``step`` of ``total``); nothing without a function."""
    if progress is None:
        return
    if step is None:
        progress(phase)
    else:
        progress(phase, step=step, total=total)
