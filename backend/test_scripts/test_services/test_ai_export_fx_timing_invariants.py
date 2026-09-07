"""Fail-closed contract + observed-math tests for `fx.timing_context`.

Two things live in `components/fx_timing_context.py` and both are covered here:

1. the payload models, whose `model_validator`s are the last checkpoint before a
   timing claim reaches a prompt, and
2. the observed-only math helpers (`_trailing_return`, `_period_return`,
   `_daily_return_volatility`, `_build_observed_range`, `_build_source_history`),
   which are pure functions over a genuine observation series.

The module's stated design rule is that this component is *observed-only and
never predictive*: a flat range must be reported as `None` + an explicit reason
rather than a fabricated 0.5, partial source history must be flagged with a
machine-readable reason, and a backward-filled carry-forward must never be
counted as a fresh data point. Those are exactly the behaviours pinned below -
they are the difference between "the rate sat mid-range" being evidence and
being an invention.

Isolation: PURE (value objects, pure functions and a scope-less BuildContext -
no DB, no server, no network).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.services.ai_export.components import fx_timing_context as ftc
from backend.app.services.ai_export.components.fx_timing_context import (
    ALL_NEUTRAL_SCENARIO_INPUTS,
    INDISPENSABLE_SCENARIO_INPUTS,
    REASON_FLAT_RANGE,
    REASON_HISTORY_STARTS_LATE,
    REASON_NO_GENUINE_OBSERVATIONS,
    REASON_NO_OBSERVED_RATES,
    REFINEMENT_SCENARIO_INPUTS,
    FxObservedRangePosition,
    FxObservedReturns,
    FxSourceHistoryCoverage,
    FxTimingContextPayload,
)
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.resources import FxRateObservation, FxRateSeriesResource
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, BuildContextScopeError, build_bucket_plan_for_scope

PERIOD_START = date(2026, 1, 1)
PERIOD_END = date(2026, 3, 31)
D1 = date(2026, 3, 20)
D2 = date(2026, 3, 25)
D3 = PERIOD_END


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _observation(day: date, rate: str, *, backward_filled: bool = False, actual: date | None = None) -> FxRateObservation:
    return FxRateObservation(requested_date=day, actual_date=actual or day, rate=Decimal(rate), backward_filled=backward_filled)


def _series(*observations: FxRateObservation) -> FxRateSeriesResource:
    return FxRateSeriesResource.from_observations(observations)


def _scope(domain: Domain = Domain.FX, **overrides) -> BuildScope:
    kwargs = {
        "request_id": "fx-timing-unit",
        "user_id": 1,
        "domain": domain,
        "detail_level": DetailLevel.STANDARD,
        "period_start": PERIOD_START,
        "period_end": PERIOD_END,
        "target_currency": "EUR",
    }
    if domain is Domain.FX:
        kwargs["base_currency"] = "USD"
        kwargs["quote_currency"] = "EUR"
    kwargs.update(overrides)
    return BuildScope(**kwargs)


def _range_position(**overrides) -> FxObservedRangePosition:
    kwargs = {
        "observed_minimum": Decimal("0.90"),
        "observed_minimum_date": D1,
        "observed_maximum": Decimal("0.95"),
        "observed_maximum_date": D2,
        "range_position_ratio": 0.4,
        "distance_to_min_ratio": 0.02,
        "distance_to_max_ratio": 0.03,
    }
    kwargs.update(overrides)
    return FxObservedRangePosition(**kwargs)


def _coverage(**overrides) -> FxSourceHistoryCoverage:
    kwargs = {
        "requested_period_start": PERIOD_START,
        "requested_period_end": PERIOD_END,
        "available_start": PERIOD_START,
        "requested_calendar_days": (PERIOD_END - PERIOD_START).days + 1,
        "covered_calendar_days": (PERIOD_END - PERIOD_START).days + 1,
        "coverage_ratio": 1.0,
        "observed_observation_count": 60,
        "backfilled_observation_count": 30,
        "earliest_source_date": PERIOD_START,
        "complete": True,
        "is_partial_history": False,
        "partial_history_reason": None,
    }
    kwargs.update(overrides)
    return FxSourceHistoryCoverage(**kwargs)


def _payload(**overrides) -> FxTimingContextPayload:
    kwargs = {
        "base_currency": "USD",
        "quote_currency": "EUR",
        "as_of": PERIOD_END,
        "effective_date": PERIOD_END,
        "current_rate": Decimal("0.92"),
        "is_backward_filled": False,
        "staleness_days": 0,
        "source": "ECB",
        "observed_range": _range_position(),
        "observed_returns": FxObservedReturns(),
        "source_history": _coverage(),
        "indispensable_user_inputs": INDISPENSABLE_SCENARIO_INPUTS,
        "refinement_user_inputs": REFINEMENT_SCENARIO_INPUTS,
        "missing_user_inputs": ALL_NEUTRAL_SCENARIO_INPUTS,
    }
    kwargs.update(overrides)
    return FxTimingContextPayload(**kwargs)


# ---------------------------------------------------------------------------
# 1. FxObservedRangePosition - resolved vs unavailable range position
# ---------------------------------------------------------------------------


def test_range_position_accepts_a_resolved_position():
    assert _range_position().range_position_ratio == pytest.approx(0.4)


def test_range_position_accepts_an_empty_range_with_a_reason():
    empty = FxObservedRangePosition(range_position_unavailable_reason=REASON_NO_OBSERVED_RATES)
    assert empty.observed_minimum is None


def test_range_position_rejects_a_non_positive_observed_extreme():
    # A zero/negative FX rate is not a rate; it would make every derived ratio
    # meaningless (and the distance-to-min division unsafe).
    with pytest.raises(ValidationError, match="observed extreme must be a finite, positive Decimal"):
        _range_position(observed_minimum=Decimal("0"))


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"observed_maximum": None, "observed_maximum_date": None}, "must both be present or both absent"),
        ({"observed_minimum_date": None}, "observed_minimum requires observed_minimum_date"),
        ({"observed_maximum_date": None}, "observed_maximum requires observed_maximum_date"),
    ],
    ids=["half-populated-extremes", "min-without-date", "max-without-date"],
)
def test_range_position_rejects_partially_populated_extremes(overrides: dict, message: str):
    # Situation: only one side of the envelope survives a refactor, which would
    # publish an extreme with no date to attribute it to.
    with pytest.raises(ValidationError, match=message):
        _range_position(**overrides)


def test_range_position_rejects_an_inverted_envelope():
    with pytest.raises(ValidationError, match="observed_maximum must not be below observed_minimum"):
        _range_position(observed_minimum=Decimal("0.99"), observed_maximum=Decimal("0.90"))


def test_range_position_requires_a_reason_when_the_ratio_is_absent():
    # This is the "never fabricate 0.5" rule in enforceable form: an absent
    # position must say *why* it is absent (flat range, or no observations).
    with pytest.raises(ValidationError, match="an unavailable range_position requires a range_position_unavailable_reason"):
        _range_position(range_position_ratio=None)


def test_range_position_rejects_a_reason_alongside_a_resolved_ratio():
    with pytest.raises(ValidationError, match="a resolved range_position must not carry an unavailable reason"):
        _range_position(range_position_unavailable_reason=REASON_FLAT_RANGE)


@pytest.mark.parametrize(
    "field",
    ["range_position_ratio", "distance_to_min_ratio", "distance_to_max_ratio"],
)
def test_empty_range_must_leave_every_derived_ratio_unset(field: str):
    # Situation: the extremes are dropped (no observations) but a stale derived
    # ratio survives, so the payload would show a distance to an absent low.
    with pytest.raises(ValidationError, match="no observed extremes must leave every derived ratio unset"):
        FxObservedRangePosition(**{field: 0.5, "range_position_unavailable_reason": REASON_NO_OBSERVED_RATES})


def test_empty_range_requires_an_unavailable_reason():
    with pytest.raises(ValidationError, match="an empty observed range requires range_position_unavailable_reason"):
        FxObservedRangePosition()


# ---------------------------------------------------------------------------
# 2. FxSourceHistoryCoverage - partial history must be explicit
# ---------------------------------------------------------------------------


def test_coverage_accepts_a_complete_and_a_partial_history():
    assert _coverage().complete is True
    partial = _coverage(available_start=D1, complete=False, is_partial_history=True, partial_history_reason=REASON_HISTORY_STARTS_LATE, coverage_ratio=0.13)
    assert partial.partial_history_reason == REASON_HISTORY_STARTS_LATE


def test_coverage_rejects_an_inverted_requested_period():
    with pytest.raises(ValidationError, match="requested_period_end must not precede requested_period_start"):
        _coverage(requested_period_start=PERIOD_END, requested_period_end=PERIOD_START, available_start=None)


@pytest.mark.parametrize("complete,partial", [(True, True), (False, False)])
def test_coverage_rejects_a_completeness_flag_pair_that_is_not_an_inverse(complete: bool, partial: bool):
    # `is_partial_history` is documented as the exact inverse of `complete`; if
    # they drift, a reader cannot tell which one the renderer trusted.
    with pytest.raises(ValidationError, match="complete and is_partial_history must be exact opposites"):
        _coverage(complete=complete, is_partial_history=partial, partial_history_reason=None)


def test_partial_history_requires_a_machine_readable_reason():
    with pytest.raises(ValidationError, match="partial history requires partial_history_reason"):
        _coverage(complete=False, is_partial_history=True, partial_history_reason=None)


def test_complete_history_must_not_carry_a_partial_reason():
    with pytest.raises(ValidationError, match="complete history must not carry a partial_history_reason"):
        _coverage(partial_history_reason=REASON_HISTORY_STARTS_LATE)


def test_coverage_rejects_an_available_start_before_the_requested_period():
    # Situation: the loader widened the series for indicator warm-up and the
    # widened start leaked into the coverage report, inflating it above 100%.
    with pytest.raises(ValidationError, match="available_start must not precede requested_period_start"):
        _coverage(available_start=PERIOD_START - timedelta(days=10))


# ---------------------------------------------------------------------------
# 3. FxTimingContextPayload - the assembled component payload
# ---------------------------------------------------------------------------


def test_timing_payload_accepts_a_consistent_snapshot():
    payload = _payload()
    assert (payload.base_currency, payload.quote_currency) == ("USD", "EUR")
    assert payload.rate_semantics == "quote_currency_per_base_currency"


def test_timing_payload_normalizes_currency_codes():
    payload = _payload(base_currency=" usd ", quote_currency="eur")
    assert (payload.base_currency, payload.quote_currency) == ("USD", "EUR")


def test_timing_payload_rejects_an_identity_pair():
    with pytest.raises(ValidationError, match="base_currency and quote_currency must differ"):
        _payload(quote_currency="USD")


def test_timing_payload_rejects_a_non_positive_current_rate():
    with pytest.raises(ValidationError, match="current_rate must be a finite, positive Decimal"):
        _payload(current_rate=Decimal("0"))


def test_timing_payload_rejects_an_effective_date_in_the_future():
    # The series never extends past `snapshot_as_of`; an effective date after
    # `as_of` would mean a future rate was consulted.
    with pytest.raises(ValidationError, match="effective_date must not be after as_of"):
        _payload(effective_date=PERIOD_END + timedelta(days=1))


def test_timing_payload_rejects_a_staleness_that_does_not_match_its_dates():
    with pytest.raises(ValidationError, match=r"staleness_days must equal \(as_of - effective_date\).days"):
        _payload(staleness_days=5)


def test_timing_payload_rejects_a_backfill_flag_that_contradicts_staleness():
    # Situation: a carry-forward rate is reported as fresh; the reader would
    # treat a stale quote as a genuine observation of today.
    with pytest.raises(ValidationError, match=r"is_backward_filled must match staleness_days > 0"):
        _payload(is_backward_filled=True)


def test_timing_payload_accepts_a_declared_backfill():
    payload = _payload(effective_date=PERIOD_END - timedelta(days=3), staleness_days=3, is_backward_filled=True)
    assert payload.staleness_days == 3


def test_timing_payload_rejects_duplicate_missing_user_inputs():
    duplicated = INDISPENSABLE_SCENARIO_INPUTS + (INDISPENSABLE_SCENARIO_INPUTS[0],)
    with pytest.raises(ValidationError, match="missing_user_inputs must be unique"):
        _payload(refinement_user_inputs=(INDISPENSABLE_SCENARIO_INPUTS[0],), missing_user_inputs=duplicated)


def test_timing_payload_rejects_missing_inputs_that_are_not_the_concatenation():
    # The two lists exist so the reader can tell a decision-blocking gap from a
    # refinement; a hand-built `missing_user_inputs` would break that split.
    with pytest.raises(ValidationError, match="missing_user_inputs must concatenate"):
        _payload(missing_user_inputs=INDISPENSABLE_SCENARIO_INPUTS)


def test_timing_payload_rejects_a_coverage_window_that_does_not_end_at_as_of():
    # Situation: the coverage report is computed against the bucket plan instead
    # of the snapshot instant, so staleness and coverage describe two periods.
    with pytest.raises(ValidationError, match=r"source_history.requested_period_end must equal as_of"):
        _payload(source_history=_coverage(requested_period_end=PERIOD_END - timedelta(days=1), covered_calendar_days=89, coverage_ratio=0.99))


# ---------------------------------------------------------------------------
# 4. _require_fx_scope - the component refuses to build outside FX
# ---------------------------------------------------------------------------


def test_require_fx_scope_rejects_a_context_built_without_a_scope():
    context = BuildContext(ComponentRegistry(()), request_id="fx-timing-unit")
    with pytest.raises(BuildContextScopeError, match="requires a BuildContext constructed with a BuildScope"):
        ftc._require_fx_scope(context)


def test_require_fx_scope_rejects_a_non_fx_domain():
    # Situation: the component is wired into the portfolio registry by mistake;
    # without this guard it would read `scope.base_currency is None` and build a
    # pair out of nothing.
    scope = _scope(Domain.PORTFOLIO)
    context = BuildContext(ComponentRegistry(()), request_id="fx-timing-unit", scope=scope, bucket_plan=build_bucket_plan_for_scope(scope))
    with pytest.raises(BuildContextScopeError, match="requires BuildScope.domain == FX"):
        ftc._require_fx_scope(context)


def test_require_fx_scope_returns_the_scope_for_an_fx_domain():
    scope = _scope()
    context = BuildContext(ComponentRegistry(()), request_id="fx-timing-unit", scope=scope, bucket_plan=build_bucket_plan_for_scope(scope))
    assert ftc._require_fx_scope(context) is scope


# ---------------------------------------------------------------------------
# 5. _genuine_observed_points - backfill and carry-forward are not observations
# ---------------------------------------------------------------------------


def test_genuine_points_keep_only_in_window_first_hand_observations():
    series = _series(
        _observation(PERIOD_START - timedelta(days=1), "0.80"),  # before the window
        _observation(D1, "0.90"),
        _observation(D2, "0.95", backward_filled=True),  # backward filled
        _observation(D3, "0.92", actual=D2),  # carried forward from an earlier day
    )
    assert ftc._genuine_observed_points(series, start=PERIOD_START, end=PERIOD_END) == ((D1, Decimal("0.90")),)


# ---------------------------------------------------------------------------
# 6. _trailing_return / _period_return / _daily_return_volatility
# ---------------------------------------------------------------------------


def test_trailing_return_is_none_without_points():
    assert ftc._trailing_return((), as_of=D3, days=30) is None


def test_trailing_return_is_none_when_history_does_not_reach_the_anchor():
    # Situation: a 30-day window requested over a series that only starts a week
    # ago - reporting a "1M return" there would be a lie about the window.
    points = ((D2, Decimal("0.90")), (D3, Decimal("0.95")))
    assert ftc._trailing_return(points, as_of=D3, days=365) is None


def test_trailing_return_is_none_when_the_anchor_is_the_last_point():
    points = ((D3, Decimal("0.90")),)
    assert ftc._trailing_return(points, as_of=D3, days=0) is None


def test_trailing_return_uses_the_last_observation_on_or_before_the_anchor():
    points = ((D1, Decimal("1.00")), (D2, Decimal("1.10")), (D3, Decimal("1.20")))
    # Anchor = D3 - 6d = 2026-03-25 -> exactly D2, so the return is 1.20/1.10 - 1.
    assert ftc._trailing_return(points, as_of=D3, days=6) == pytest.approx(1.20 / 1.10 - 1)


def test_period_return_needs_at_least_two_points():
    assert ftc._period_return(((D3, Decimal("1.00")),)) is None


def test_period_return_spans_the_first_and_last_observation():
    points = ((D1, Decimal("1.00")), (D2, Decimal("1.10")), (D3, Decimal("1.25")))
    assert ftc._period_return(points) == pytest.approx(0.25)


def test_daily_return_volatility_needs_at_least_two_returns():
    assert ftc._daily_return_volatility(((D2, Decimal("1.00")), (D3, Decimal("1.10")))) is None


def test_daily_return_volatility_is_zero_for_a_constant_series():
    points = tuple((PERIOD_START + timedelta(days=index), Decimal("1.00")) for index in range(4))
    assert ftc._daily_return_volatility(points) == pytest.approx(0.0)


def test_daily_return_volatility_is_the_population_stdev_of_daily_returns():
    points = ((D1, Decimal("1.00")), (D2, Decimal("1.10")), (D3, Decimal("1.10")))
    # Returns are [0.10, 0.0]; population stdev of two values is half their gap.
    assert ftc._daily_return_volatility(points) == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# 7. _build_observed_range - the "never fabricate a midpoint" rule
# ---------------------------------------------------------------------------


def test_observed_range_without_points_reports_the_no_observation_reason():
    result = ftc._build_observed_range((), current_rate=Decimal("0.92"))
    assert result.observed_minimum is None
    assert result.range_position_unavailable_reason == REASON_NO_OBSERVED_RATES


def test_flat_observed_range_reports_no_position_and_the_flat_reason():
    # The module's headline rule: an identical min/max must never become 0.5.
    points = ((D1, Decimal("0.90")), (D2, Decimal("0.90")))
    result = ftc._build_observed_range(points, current_rate=Decimal("0.90"))
    assert result.range_position_ratio is None
    assert result.range_position_unavailable_reason == REASON_FLAT_RANGE
    assert (result.observed_minimum, result.observed_maximum) == (Decimal("0.90"), Decimal("0.90"))


def test_observed_range_positions_the_current_rate_between_the_extremes():
    points = ((D1, Decimal("0.90")), (D2, Decimal("1.00")), (D3, Decimal("0.95")))
    result = ftc._build_observed_range(points, current_rate=Decimal("0.95"))
    assert result.range_position_ratio == pytest.approx(0.5)
    assert result.distance_to_min_ratio == pytest.approx(0.95 / 0.90 - 1)
    assert result.distance_to_max_ratio == pytest.approx(1.00 / 0.95 - 1)


@pytest.mark.parametrize("current,expected", [(Decimal("0.50"), 0.0), (Decimal("2.00"), 1.0)])
def test_observed_range_clamps_a_current_rate_outside_the_observed_envelope(current: Decimal, expected: float):
    # Situation described in the source comment: on the last-bucket backfill edge
    # the as-of rate is carried from outside the genuine window, so the raw
    # position can fall slightly outside 0..1. Clamping keeps the field within
    # its declared bounds instead of raising.
    points = ((D1, Decimal("0.90")), (D2, Decimal("1.00")))
    result = ftc._build_observed_range(points, current_rate=current)
    assert result.range_position_ratio == pytest.approx(expected)
    assert result.distance_to_min_ratio >= 0.0
    assert result.distance_to_max_ratio >= 0.0


def test_observed_range_breaks_ties_on_the_earliest_date():
    # min/max are keyed on (value, date), so the first day that touched the
    # extreme is the one attributed - a later equal touch must not steal it.
    points = ((D1, Decimal("0.90")), (D2, Decimal("0.90")), (D3, Decimal("1.00")))
    result = ftc._build_observed_range(points, current_rate=Decimal("0.95"))
    assert result.observed_minimum_date == D1


# ---------------------------------------------------------------------------
# 8. _build_source_history - the three completeness verdicts
# ---------------------------------------------------------------------------


def test_source_history_is_complete_when_the_period_start_is_covered():
    series = _series(_observation(PERIOD_START, "0.90"), _observation(D3, "0.95"))
    coverage = ftc._build_source_history(series, scope=_scope())
    assert coverage.complete is True
    assert coverage.is_partial_history is False
    assert coverage.partial_history_reason is None
    assert coverage.coverage_ratio == pytest.approx(1.0)
    assert (coverage.observed_observation_count, coverage.backfilled_observation_count) == (2, 0)


def test_source_history_counts_a_backward_filled_start_as_covered():
    # Documented rule: a weekend/holiday backfilled start is still covered and
    # must not be reported as a source-history gap.
    series = _series(_observation(PERIOD_START, "0.90", backward_filled=True, actual=PERIOD_START - timedelta(days=2)), _observation(D3, "0.95"))
    coverage = ftc._build_source_history(series, scope=_scope())
    assert coverage.complete is True
    assert (coverage.observed_observation_count, coverage.backfilled_observation_count) == (1, 1)


def test_source_history_flags_a_late_start_with_genuine_observations():
    series = _series(_observation(D1, "0.90"), _observation(D3, "0.95"))
    coverage = ftc._build_source_history(series, scope=_scope())
    assert coverage.is_partial_history is True
    assert coverage.partial_history_reason == REASON_HISTORY_STARTS_LATE
    assert coverage.available_start == D1
    assert coverage.coverage_ratio < 1.0


def test_source_history_flags_a_window_with_no_genuine_observation_at_all():
    # Situation: every visible point is a carry-forward, so there is nothing
    # first-hand to compute returns or a range from - a different verdict from
    # "history simply starts late".
    series = _series(_observation(D1, "0.90", backward_filled=True, actual=date(2025, 12, 30)))
    coverage = ftc._build_source_history(series, scope=_scope())
    assert coverage.partial_history_reason == REASON_NO_GENUINE_OBSERVATIONS
    assert coverage.observed_observation_count == 0


def test_source_history_reports_zero_coverage_for_an_empty_visible_window():
    series = _series(_observation(PERIOD_START - timedelta(days=5), "0.90"))
    coverage = ftc._build_source_history(series, scope=_scope())
    assert coverage.available_start is None
    assert coverage.covered_calendar_days == 0
    assert coverage.coverage_ratio == pytest.approx(0.0)
    assert coverage.partial_history_reason == REASON_NO_GENUINE_OBSERVATIONS
    # `earliest_source_date` still reports the out-of-window point: it exists to
    # tell the reader how far back the *source* goes, not the visible window.
    assert coverage.earliest_source_date == PERIOD_START - timedelta(days=5)
