"""Limits on entries as the replay and the SCIP rows read them (V5, A3 of project 67): the entries, and every limit as an amount.

An entry is an Asset or a cash cell (Broker and currency). A limit is an amount in the valuation currency or a share of the
Tool's reference (decisioni M17); ``resolve_scenario_limits`` turns each into an amount against one reference, which in the
PAC is ``accounting.fixed_reference``. Leaf module: the checks before the calculation, which need the evaluator, are in
``pac_allocator/limits.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.app.services.pac_allocator.models import ExactLimit, ExactPlannerScenario
from backend.app.services.pac_allocator.numeric import ExactRatio


@dataclass(frozen=True, slots=True)
class LimitEntry:
    """One entry of the plan that can carry limits: an Asset, or the cash of a Broker in a currency."""

    kind: Literal["asset", "cash"]
    asset_id: str | None = None
    broker_id: str | None = None
    currency: str | None = None

    @property
    def key(self) -> str:
        """``asset:<asset id>`` or ``cash:<broker id>:<currency>``: stable, and the order entries are listed in."""
        return f"asset:{self.asset_id}" if self.kind == "asset" else f"cash:{self.broker_id}:{self.currency}"


@dataclass(frozen=True, slots=True)
class ResolvedBounds:
    """The minimum and the maximum of one entry as amounts in the valuation currency; ``None`` is no bound."""

    minimum: ExactRatio | None
    maximum: ExactRatio | None


@dataclass(frozen=True, slots=True)
class ResolvedLimits:
    """Every limit of a scenario as amounts, against one reference: what the replay and the SCIP rows apply."""

    reference: ExactRatio
    by_entry: dict[LimitEntry, ResolvedBounds]

    def assets(self) -> dict[str, ResolvedBounds]:
        return {entry.asset_id: bounds for entry, bounds in self.by_entry.items() if entry.kind == "asset"}

    def cash(self) -> dict[tuple[str, str], ResolvedBounds]:
        return {(entry.broker_id, entry.currency): bounds for entry, bounds in self.by_entry.items() if entry.kind == "cash"}


def resolve_limit(limit: ExactLimit | None, reference: ExactRatio) -> ExactRatio | None:
    """A limit as an amount: an amount as it is, a share of ``reference``; ``None`` for no limit."""
    if limit is None:
        return None
    return limit.value if limit.kind == "amount" else limit.value * reference


def entries_with_limits(scenario: ExactPlannerScenario) -> list[tuple[LimitEntry, ExactLimit | None, ExactLimit | None]]:
    rows = [(LimitEntry("asset", asset_id=item.asset_id), item.minimum, item.maximum) for item in scenario.target_weights if item.minimum is not None or item.maximum is not None]
    rows += [(LimitEntry("cash", broker_id=item.broker_id, currency=item.currency), item.minimum, item.maximum) for item in scenario.cash_limits]
    return sorted(rows, key=lambda row: row[0].key)


def limited_entries(scenario: ExactPlannerScenario) -> tuple[LimitEntry, ...]:
    """Every entry that carries a minimum or a maximum, in key order: what a «no solution» names (M20)."""
    return tuple(entry for entry, _, _ in entries_with_limits(scenario))


def resolve_scenario_limits(scenario: ExactPlannerScenario, reference: ExactRatio) -> ResolvedLimits:
    """Every limit of ``scenario`` resolved to an amount against ``reference``."""
    return ResolvedLimits(
        reference=reference,
        by_entry={entry: ResolvedBounds(resolve_limit(minimum, reference), resolve_limit(maximum, reference)) for entry, minimum, maximum in entries_with_limits(scenario)},
    )


def uninvested_maximum(scenario: ExactPlannerScenario, ledger_cells: tuple[tuple[str, str], ...], resolved: ResolvedLimits) -> ExactRatio | None:
    """V10's bound (decisioni D8): the sum of every cash cell's maximum in the valuation currency, or ``None`` when V10 is off.

    It applies only when every cell of the ledger has a maximum **and** the scenario holds no contribution: money that is not
    deposited stays outside every cell, so no maximum can oblige a plan to waste it. A cash limit is an amount in the valuation
    currency, whatever the cell's own currency, so the sum needs no rate.
    """
    if scenario.contributions or not ledger_cells:
        return None
    cash = resolved.cash()
    total = ExactRatio(0)
    for broker_id, currency in ledger_cells:
        bounds = cash.get((broker_id, currency))
        if bounds is None or bounds.maximum is None:
            return None
        total += bounds.maximum
    return total
