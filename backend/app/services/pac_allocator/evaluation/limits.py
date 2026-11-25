"""Limits on entries as the replay and the SCIP rows read them (V5, A3 of project 67): the entries, and every limit as an amount.

An entry is an Asset or a cash cell (Broker and currency). A limit is an amount in the valuation currency or a share of the
Tool's reference (decisioni M17); ``resolve_scenario_limits`` turns each into an amount against one reference, which in the
PAC is ``accounting.fixed_reference``. Leaf module: the checks before the calculation, which need the evaluator, are in
``pac_allocator/limits.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from backend.app.services.pac_allocator.evaluation.scenario import ScenarioIndex, order_prices, to_valuation
from backend.app.services.pac_allocator.models import ExactAccountingEvaluation, ExactLimit, ExactOrderRoute, ExactPlannerScenario
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
    rows += [(LimitEntry("cash", broker_id=item.broker_id, currency=item.currency), item.minimum, item.maximum) for item in scenario.cash_entries if item.minimum is not None or item.maximum is not None]
    return sorted(rows, key=lambda row: row[0].key)


def limited_entries(scenario: ExactPlannerScenario) -> tuple[LimitEntry, ...]:
    """Every entry that carries a minimum or a maximum, in key order: what a «no solution» names (M20)."""
    return tuple(entry for entry, _, _ in entries_with_limits(scenario))


def plan_reference(scenario: ExactPlannerScenario, accounting: ExactAccountingEvaluation) -> ExactRatio:
    """``R``, the plan's reference: ``fixed_reference`` in the PAC (the cash its routes can bring to a purchase), ``F`` in the
    Rebalancer. A share limit reads it (specifica §15 n. 17); so do the targets, the uninvested ``N`` and the scale of the
    distance (lot SLIP of project 67, SLIP-0 §6.2). The money lost ``C = F − W`` does not: trapped cash is in both terms."""
    return accounting.initial_wealth if scenario.product == "rebalancer" else accounting.fixed_reference


def resolve_scenario_limits(scenario: ExactPlannerScenario, reference: ExactRatio) -> ResolvedLimits:
    """Every limit of ``scenario`` resolved to an amount against ``reference``."""
    return ResolvedLimits(
        reference=reference,
        by_entry={entry: ResolvedBounds(resolve_limit(minimum, reference), resolve_limit(maximum, reference)) for entry, minimum, maximum in entries_with_limits(scenario)},
    )


def buy_value_per_quantum(index: ScenarioIndex, route: ExactOrderRoute) -> ExactRatio:
    """What one quantum of a buy route adds to its Asset's final value, in the valuation currency, exactly.

    The replay values an order's ``mid_value`` as the economic quantity at the mid price (``economics._evaluate_orders``): a
    whole-quantity route buys ``step`` units per quantum, an amount route spends ``step`` of cash per quantum, which is
    ``step / execution price`` units. A limit that depends on one decision turns into an integer bound on it with this number.
    """
    capability = index.capabilities[(route.broker_id, route.capability_id)]
    prices = order_prices(index, route)
    quantity = capability.order_step if capability.kind == "whole_quantity" else capability.order_step / prices.execution_native
    return to_valuation(index, quantity * prices.mid_native, index.assets[route.asset_id].quote.price.currency)
