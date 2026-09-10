"""Initial-state valuation and row tracking arithmetic, independent of any solver."""

from __future__ import annotations

from decimal import Decimal, localcontext

from backend.app.services.pac_allocator.models import Checkpoint, InitialEvaluation, InitialRowEvaluation, NormalizationResult, ParsedMoneyVector, ParsedValue, check_budget, unavailable_reason
from backend.app.services.pac_allocator.numeric import HUNDRED, ZERO, decimal_context
from backend.app.utils.financial.valuation_utils import compute_holding_value


def reporting_value(amount: ParsedValue[Decimal], currency: str | None, state: NormalizationResult) -> ParsedValue[Decimal]:
    """Convert a supplied reference value, never exchange or route native cash."""
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
    return ParsedValue(None, reason) if reason is not None else ParsedValue(sum((value.require() for value in values), ZERO))


def _money_total(vector: ParsedMoneyVector, state: NormalizationResult, checkpoint: Checkpoint | None) -> ParsedValue[Decimal]:
    if vector.reason is not None:
        return ParsedValue(None, vector.reason)
    if not state.report_currency.available:
        return ParsedValue(None, state.report_currency.reason or "input_missing")
    converted = []
    for currency, amount in vector.entries:
        check_budget(checkpoint)
        converted.append(reporting_value(ParsedValue(amount), currency, state))
    return _sum_values(tuple(converted))


def evaluate_initial_state(state: NormalizationResult, *, checkpoint: Checkpoint | None = None) -> InitialEvaluation:
    """Evaluate complete dependencies only; unavailable rows never become zero."""
    with localcontext(decimal_context()):
        check_budget(checkpoint)
        rows: list[InitialRowEvaluation] = []
        for row in state.rows:
            check_budget(checkpoint)
            reason = unavailable_reason((row.quantity, row.quote.price, row.quote.currency, row.quote.basis))
            if not row.quote.date_valid:
                reason = "input_invalid"
            native = ParsedValue(None, reason) if reason is not None else ParsedValue(compute_holding_value(row.quantity.require(), row.quote.price.require(), row.quote.basis.require()))
            converted = reporting_value(native, row.quote.currency.value, state)
            rows.append(InitialRowEvaluation(native, converted))

        if not rows:
            invested = ParsedValue(None, "input_missing")
        elif not state.row_identity_valid:
            invested = ParsedValue(None, "input_invalid")
        else:
            invested = _sum_values(tuple(row.reporting_value for row in rows))
        existing_cash = _money_total(state.cash, state, checkpoint)
        contributions = _money_total(state.contributions, state, checkpoint)
        combined_cash = _sum_values((existing_cash, contributions)) if state.currency_domain_valid else ParsedValue(None, "outside_p1_domain")

        gaps = None
        max_gap = None
        squared_gap = None
        if state.targets_valid and invested.available and invested.require() > ZERO:
            gaps = tuple(HUNDRED * values.reporting_value.require() - row.target.require() * invested.require() for row, values in zip(state.rows, rows, strict=True))
            max_gap = max(abs(gap) for gap in gaps)
            squared_gap = sum((gap * gap for gap in gaps), ZERO)
        check_budget(checkpoint)
        return InitialEvaluation(tuple(rows), invested, existing_cash, contributions, combined_cash, gaps, max_gap, squared_gap)
