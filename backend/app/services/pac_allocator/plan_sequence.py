"""The plan's step counter: an executable order (contract §6.3 of project 67, specification §15 n. 7).

A plan is a set of steps — deposits, transfers between Brokers, the conversions the user makes, purchases — each with one
number of a counter shared by every list. Followed by its numbers, the plan must be doable: every step finds, in the cash
it spends, what the steps before it left there. The engine decides *what* to do; this module decides only *in which
order*, from the posted amounts the ledger reconciles (the minor unit of each currency), so no tolerance is needed: a
balance is never below zero, exactly.

The order is built greedily. At each turn the first step that the balances can pay, in the contract's order of kinds
(deposits, conversions, transfers, purchases) and then in its list's order, takes the next number. So an exchange comes
before a transfer that spends its proceeds, a transfer before an exchange or a purchase that spends what it brings, and
the purchases after the cash they need. A conversion the Broker makes by itself (``automatic``) has no number: it happens
when a step spends its currency on that Broker, and the replay applies it there.

Greedy is not a search: it can refuse a plan that has an order, when cash leaves a cell and comes back to it (an exchange
of a cell's euros taken first, while a transfer out and back would have come before it). No engine plan has shown it;
``test_the_known_limit_cash_that_returns_to_its_cell`` pins it. A sale (F3b of project 67) adds a credit to its cell:
``step_flows`` reads purchases only until then.

``assert_executable`` is the invariant, checked on every plan the report builds: it replays the published steps in their
numbers and refuses a balance below zero, or final balances that differ from the ledger's. A plan the counter cannot
number raises ``PlanNotExecutableError``: a defect to report, never a plan to publish.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from typing import Literal

__all__ = ["PlanNotExecutableError", "PlanStepFlow", "assert_executable", "executable_order", "step_flows"]

Cell = tuple[str, str]
StepKind = Literal["funding", "conversion", "transfer", "order"]
_KIND_ORDER: dict[StepKind, int] = {"funding": 0, "conversion": 1, "transfer": 2, "order": 3}


class PlanNotExecutableError(ValueError):
    """The counter found no step the balances could pay, or a published order takes a balance below zero (or ends away
    from the ledger): the plan cannot be followed as numbered."""


@dataclass(frozen=True)
class PlanStepFlow:
    """One step's money: what it takes from which cell (Broker, currency) and what it adds where. ``numbered`` is false for a
    conversion the Broker makes by itself, which the plan does not number."""

    key: str
    kind: StepKind
    debits: tuple[tuple[Cell, Fraction], ...]
    credits: tuple[tuple[Cell, Fraction], ...]
    numbered: bool = True
    sequence: int | None = field(default=None, compare=False)


def _fraction(value: Decimal | str | Fraction) -> Fraction:
    return value if isinstance(value, Fraction) else Fraction(Decimal(str(value)))


def step_flows(funding_actions: Iterable, transfers: Iterable, conversions: Iterable, order_rows: Iterable, cash_cell_by_id: Mapping[str, Cell]) -> list[PlanStepFlow]:
    """The flows of the published rows, in the contract's order of kinds and each list's own order. ``cash_cell_by_id``
    resolves a deposit's ``existing_cash`` source to its cell; a contribution comes from outside the plan."""
    flows: list[PlanStepFlow] = []
    for action in funding_actions:
        destination = (action.destination_broker_id, action.amount.currency)
        amount = _fraction(action.amount.amount)
        debits = ((cash_cell_by_id[action.source.cash_id], amount),) if action.source.kind == "existing_cash" else ()
        flows.append(PlanStepFlow(action.action_id, "funding", debits, ((destination, amount),), sequence=action.sequence))
    for conversion in conversions:
        debit = ((conversion.broker_id, conversion.source_debit.currency), _fraction(conversion.source_debit.amount))
        credit = ((conversion.broker_id, conversion.destination_credit.currency), _fraction(conversion.destination_credit.amount))
        flows.append(PlanStepFlow(conversion.conversion_id, "conversion", (debit,), (credit,), numbered=conversion.mode == "manual", sequence=conversion.sequence))
    for transfer in transfers:
        amount = _fraction(transfer.amount.amount)
        currency = transfer.amount.currency
        flows.append(PlanStepFlow(transfer.transfer_id, "transfer", (((transfer.source_broker_id, currency), amount),), (((transfer.destination_broker_id, currency), amount),), sequence=transfer.sequence))
    for order in order_rows:
        cell = (order.broker_id, order.cash_debit.currency)
        spent = _fraction(order.cash_debit.amount) + _fraction(order.fee.amount)
        flows.append(PlanStepFlow(order.order_id, "order", ((cell, spent),), (), sequence=order.sequence))
    return flows


class _Balances:
    def __init__(self, initial: Mapping[Cell, Fraction]) -> None:
        self.cells: dict[Cell, Fraction] = dict(initial)

    def can_pay(self, step: PlanStepFlow) -> bool:
        needed: dict[Cell, Fraction] = {}
        for cell, amount in step.debits:
            needed[cell] = needed.get(cell, Fraction(0)) + amount
        return all(self.cells.get(cell, Fraction(0)) >= amount for cell, amount in needed.items())

    def apply(self, step: PlanStepFlow) -> None:
        for cell, amount in step.debits:
            self.cells[cell] = self.cells.get(cell, Fraction(0)) - amount
        for cell, amount in step.credits:
            self.cells[cell] = self.cells.get(cell, Fraction(0)) + amount


def _apply_automatic_for(step: PlanStepFlow, balances: _Balances, automatic: list[PlanStepFlow]) -> None:
    """The conversions a Broker makes by itself, applied before the first step that spends their currency on that Broker:
    an order, or a transfer of their proceeds."""
    for cell, _amount in step.debits:
        for conversion in [conversion for conversion in automatic if any(credit_cell == cell for credit_cell, _ in conversion.credits)]:
            if balances.can_pay(conversion):
                balances.apply(conversion)
                automatic.remove(conversion)


def executable_order(initial: Mapping[Cell, Fraction], flows: Sequence[PlanStepFlow]) -> list[PlanStepFlow]:
    """The numbered steps in an order every balance can follow; the automatic conversions are applied where an order needs
    them and are not returned. Raises ``PlanNotExecutableError`` when no remaining step can be paid."""
    balances = _Balances(initial)
    pending = sorted((flow for flow in flows if flow.numbered), key=lambda flow: _KIND_ORDER[flow.kind])
    automatic = [flow for flow in flows if not flow.numbered]
    ordered: list[PlanStepFlow] = []
    while pending:
        for step in pending:
            _apply_automatic_for(step, balances, automatic)
            if balances.can_pay(step):
                balances.apply(step)
                ordered.append(step)
                pending.remove(step)
                break
        else:
            raise PlanNotExecutableError(f"no step can be paid with the balances left: {[step.key for step in pending]}")
    return ordered


def assert_executable(initial: Mapping[Cell, Fraction], flows: Sequence[PlanStepFlow], final: Mapping[Cell, Fraction] | None = None) -> None:
    """The invariant: the numbered steps, replayed in their published numbers, never take a balance below zero; with
    ``final``, every cell ends where the ledger says. Raises ``PlanNotExecutableError`` otherwise."""
    balances = _Balances(initial)
    automatic = [flow for flow in flows if not flow.numbered]
    numbered = sorted((flow for flow in flows if flow.numbered), key=lambda flow: flow.sequence if flow.sequence is not None else 0)
    for step in numbered:
        _apply_automatic_for(step, balances, automatic)
        if not balances.can_pay(step):
            raise PlanNotExecutableError(f"step {step.sequence} ({step.key}) spends more than its cash holds at that point")
        balances.apply(step)
    for conversion in automatic:
        if not balances.can_pay(conversion):
            raise PlanNotExecutableError(f"the automatic conversion {conversion.key} spends more than its cash holds")
        balances.apply(conversion)
    if final is not None:
        for cell, amount in final.items():
            if balances.cells.get(cell, Fraction(0)) != amount:
                raise PlanNotExecutableError(f"cell {cell} ends at {balances.cells.get(cell, Fraction(0))}, the ledger says {amount}")
