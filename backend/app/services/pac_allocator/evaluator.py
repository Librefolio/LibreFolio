"""Decimal P1 arithmetic for PAC budgets and portfolio target gaps."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, localcontext

from backend.app.services.pac_allocator.models import (
    Checkpoint,
    HoldingEvaluation,
    InstrumentEvaluation,
    MoneyEvaluation,
    NormalizationResult,
    PacEvaluation,
    PacNormalizationResult,
    ParsedContributionVector,
    ParsedMoneyVector,
    ParsedValue,
    RebalanceEvaluation,
    RebalanceNormalizationResult,
    check_budget,
    unavailable_reason,
)
from backend.app.services.pac_allocator.numeric import (
    HUNDRED,
    ZERO,
    decimal_context,
    exact_holding_value,
)


def reporting_value(
    amount: ParsedValue[Decimal],
    currency: str | None,
    state: NormalizationResult,
) -> ParsedValue[Decimal]:
    """Value a supplied fact; never exchange or route native cash."""
    reason = unavailable_reason((amount, state.report_currency))
    if reason is not None:
        return ParsedValue(None, reason)
    if currency is None:
        raise RuntimeError("Available native amount has no currency")
    value = amount.require()
    if currency == state.report_currency.require() or value == ZERO:
        return ParsedValue(value)
    rate = state.rate_map().get(currency)
    if rate is None:
        return ParsedValue(None, "input_missing")
    if not rate.available:
        return ParsedValue(None, rate.reason or "dependency_unavailable")
    return ParsedValue(value * rate.require())


def _sum_values(values: tuple[ParsedValue[Decimal], ...]) -> ParsedValue[Decimal]:
    reason = unavailable_reason(values)
    if reason is not None:
        return ParsedValue(None, reason)
    return ParsedValue(sum((value.require() for value in values), ZERO))


def _money_total(
    vector: ParsedMoneyVector | ParsedContributionVector,
    state: NormalizationResult,
    checkpoint: Checkpoint | None,
) -> ParsedValue[Decimal]:
    if vector.reason is not None:
        return ParsedValue(None, vector.reason)
    if not state.report_currency.available:
        return ParsedValue(
            None,
            state.report_currency.reason or "input_missing",
        )
    converted = []
    for currency, amount in vector.amount_entries():
        check_budget(checkpoint)
        converted.append(reporting_value(ParsedValue(amount), currency, state))
    return _sum_values(tuple(converted))


def _evaluate_money(
    state: NormalizationResult,
    checkpoint: Checkpoint | None,
) -> MoneyEvaluation:
    existing = _money_total(state.cash, state, checkpoint)
    contributions = _money_total(state.contributions, state, checkpoint)
    if not state.currency_domain_valid:
        combined = ParsedValue(None, "outside_p1_domain")
    else:
        combined = _sum_values((existing, contributions))
    return MoneyEvaluation(existing, contributions, combined)


def evaluate_pac_budget(
    state: PacNormalizationResult,
    *,
    checkpoint: Checkpoint | None = None,
) -> PacEvaluation:
    """Allocate reporting budget by target; do not derive orders or quantities."""
    with localcontext(decimal_context()):
        check_budget(checkpoint)
        money = _evaluate_money(state, checkpoint)
        allocations = []
        for target in state.targets:
            check_budget(checkpoint)
            reason = unavailable_reason((money.combined_cash, target.percent))
            if reason is None and state.asset_identity_valid and state.target_identity_valid and state.targets_valid:
                allocations.append(ParsedValue(money.combined_cash.require() * target.percent.require() / HUNDRED))
            else:
                allocations.append(
                    ParsedValue(
                        None,
                        reason or state.target_total.reason or "input_invalid",
                    )
                )
        check_budget(checkpoint)
        return PacEvaluation(money, tuple(allocations))


def evaluate_rebalancing(
    state: RebalanceNormalizationResult,
    *,
    checkpoint: Checkpoint | None = None,
) -> RebalanceEvaluation:
    """Aggregate canonical instruments and compare them with final targets."""
    with localcontext(decimal_context()):
        check_budget(checkpoint)
        holding_values = []
        by_instrument: dict[str, list[int]] = defaultdict(list)
        for index, holding in enumerate(state.holdings):
            check_budget(checkpoint)
            by_instrument[holding.instrument_key].append(index)
            reason = unavailable_reason(
                (
                    holding.quantity,
                    holding.quote.price,
                    holding.quote.currency,
                    holding.quote.basis,
                )
            )
            if not holding.quote.date_valid:
                reason = "input_invalid"
            if reason is None:
                native = ParsedValue(
                    exact_holding_value(
                        holding.quantity.require(),
                        holding.quote.price.require(),
                        holding.quote.basis.require(),
                    )
                )
            else:
                native = ParsedValue(None, reason)
            holding_values.append(
                HoldingEvaluation(
                    native_value=native,
                    reporting_value=reporting_value(
                        native,
                        holding.quote.currency.value,
                        state,
                    ),
                )
            )

        if not holding_values:
            invested = ParsedValue(None, "input_missing")
        elif not state.row_identity_valid:
            invested = ParsedValue(None, "input_invalid")
        else:
            invested = _sum_values(tuple(value.reporting_value for value in holding_values))

        instruments = []
        gap_numerators: list[Decimal] = []
        for target in state.targets:
            check_budget(checkpoint)
            indices = by_instrument.get(target.instrument_key, [])
            current_values = tuple(holding_values[index].reporting_value for index in indices)
            current = _sum_values(current_values) if current_values else ParsedValue(None, "input_invalid")
            target_reason = unavailable_reason((invested, target.percent))
            if target_reason is None and state.target_identity_valid and state.targets_valid:
                target_value = ParsedValue(invested.require() * target.percent.require() / HUNDRED)
            else:
                target_value = ParsedValue(
                    None,
                    target_reason or state.target_total.reason or "input_invalid",
                )
            gap_reason = unavailable_reason((target_value, current))
            value_gap = ParsedValue(target_value.require() - current.require()) if gap_reason is None else ParsedValue(None, gap_reason)
            gap_numerator = None
            if value_gap.available and invested.available and invested.require() > ZERO:
                gap_numerator = target.percent.require() * invested.require() - HUNDRED * current.require()
                gap_numerators.append(gap_numerator)
            instruments.append(
                InstrumentEvaluation(
                    instrument_key=target.instrument_key,
                    current_reporting=current,
                    target_value_reporting=target_value,
                    value_gap_reporting=value_gap,
                    gap_numerator=gap_numerator,
                )
            )

        complete_gaps = state.targets_valid and len(gap_numerators) == len(state.targets) and bool(state.targets)
        maximum = max(abs(value) for value in gap_numerators) if complete_gaps else None
        squared = sum((value * value for value in gap_numerators), ZERO) if complete_gaps else None
        money = _evaluate_money(state, checkpoint)
        check_budget(checkpoint)
        return RebalanceEvaluation(
            holdings=tuple(holding_values),
            instruments=tuple(instruments),
            invested=invested,
            money=money,
            max_gap_numerator=maximum,
            squared_gap_numerator=squared,
        )
