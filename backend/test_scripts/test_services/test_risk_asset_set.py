"""Pure plugin tests for the weightless ASSET_SET risk analytics family.

Two clauses are defended here, and everything else in this file serves one of them.

CLAUSE ⓪ — ONE REQUEST, ONE PREPARATION. The five asset-set codes exist so that a
comparison surface can ask five questions about the same selection. Splitting that
into five requests would build five joint calendars, and the per-asset figures would
then be measured over different day sets while still looking like one table. The
service already guarantees one preparation per request; what these tests prove is
that a *five-code design* does not quietly fragment that guarantee.

CLAUSE ① — A WEIGHTLESS SELECTION HAS NO WHOLE. There is no set-level aggregate in
any of these payloads, and on the risk/return scatter that absence is what makes the
Capital Market Line undrawable — the judgement "paid well for the risk" cannot be
restored through the data. The defence is a shape, so it is tested as a shape.

No DB, no server, no network: every context here is built from an in-memory prepared
series set, and each test owns the fixture it measures.
"""

from __future__ import annotations

import math
import statistics
from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.portfolio import DataQualityReport
from backend.app.schemas.prices import FAPricePoint, FAPriceQueryResult
from backend.app.schemas.risk import (
    AssetReturnPoint,
    AssetReturnSeries,
    AssetSetRiskScope,
    AssetValuationPoint,
    AssetValuationSeries,
    PreparedAssetSeries,
    PreparedAssetSeriesSet,
    RiskAnalyticOutput,
    RiskAnalyticRequest,
    RiskAssetSetComparisonItem,
    RiskAssetSetComparisonOutput,
    RiskAssetSetDrawdownOutput,
    RiskAssetSetKpiOutput,
    RiskAssetSetReturnItem,
    RiskAssetSetReturnOutput,
    RiskAssetSetVarCvarOutput,
    RiskDrawdownRecoveryStatus,
    RiskErrorCode,
    RiskMode,
    RiskOutputKind,
    RiskQueryRequest,
    RiskReturnBasis,
    RiskReturnItem,
    RiskReturnOutput,
    RiskScopeKind,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry
from backend.app.services.risk.base import RiskAnalytic, RiskExecutionContext, RiskUnavailableError
from backend.app.services.risk.service import RiskService, _AnalyticPlan, _ScopeInputs
from backend.app.services.risk_plugins.asset_risk_return import AssetRiskReturnAnalytic
from backend.app.services.risk_plugins.asset_set_comparison import (
    AssetSetComparisonAnalytic,
    AssetSetComparisonParams,
)
from backend.app.services.risk_plugins.asset_set_drawdown import (
    AssetSetDrawdownAnalytic,
    AssetSetDrawdownParams,
)
from backend.app.services.risk_plugins.asset_set_kpi import AssetSetKpiAnalytic, AssetSetKpiParams
from backend.app.services.risk_plugins.asset_set_risk_return import (
    AssetSetRiskReturnAnalytic,
    AssetSetRiskReturnParams,
)
from backend.app.services.risk_plugins.asset_set_var import AssetSetVarAnalytic, AssetSetVarParams
from backend.app.services.series_preparation import prepare_asset_series_set

# ---------------------------------------------------------------------------
# Fixture material.
#
# 🔴 EVERY NUMBER BELOW IS A PROPERTY OF THIS FILE, NOT OF THE PRODUCT. The series
# are deterministic closed forms — no RNG, no database, no captured snapshot — and
# expectations are derived from them either by an independent stdlib computation
# (`statistics`) or by a relation that must hold whatever the values are. Nothing
# here is a "product constant": change a series and the derived expectation moves
# with it, which is the only way a fixture-based number can stay honest.
# ---------------------------------------------------------------------------

BASELINE = date(2026, 1, 1)
OBSERVATIONS = 30

CHOPPY_ASSET_ID = 101
STEADY_ASSET_ID = 102
REFERENCE_ASSET_ID = 103
FLAT_GAINER_ASSET_ID = 104
STILL_UNDERWATER_ASSET_ID = 105
RECOVERED_ASSET_ID = 106


def _wave(amplitude: float, phase: float, drift: float) -> list[float]:
    """One deterministic oscillation with a drift, rounded to kill float noise."""
    return [round(amplitude * math.sin(index * phase) + drift, 10) for index in range(OBSERVATIONS)]


# Real downside on both sides of zero: without it a 95% tail is all gains and the
# VaR estimator floors to zero, which measures the fixture rather than the product.
CHOPPY = _wave(0.02, 0.7, 0.001)
STEADY = _wave(0.012, 0.4, 0.002)
REFERENCE = _wave(0.009, 0.55, 0.0015)
# Constant: zero sample volatility and zero downside deviation, so Sharpe and Sortino
# are undefined rather than nil, and no observation ever loses.
FLAT_GAINER = [0.002] * OBSERVATIONS
# Rises, falls, and never regains the old peak before the window ends.
STILL_UNDERWATER = [0.01] * 10 + [-0.015] * 10 + [0.002] * 10
# Rises, falls, climbs back through the old peak, then stands still on it.
RECOVERED = [0.01] * 5 + [-0.02] * 5 + [0.03] * 10 + [0.0] * 10

ASSET_SET_ANALYTIC_CLASSES: tuple[type[RiskAnalytic], ...] = (
    AssetSetKpiAnalytic,
    AssetSetVarAnalytic,
    AssetSetDrawdownAnalytic,
    AssetSetRiskReturnAnalytic,
    AssetSetComparisonAnalytic,
)
ASSET_SET_PARAMETERS: dict[str, dict[str, object]] = {
    "asset_set_kpi": {},
    "asset_set_var": {},
    "asset_set_drawdown": {},
    "asset_set_risk_return": {},
    "asset_set_comparison": {"comparison_asset_id": REFERENCE_ASSET_ID},
}


def make_prepared_set(returns_by_asset: dict[int, list[float]]) -> PreparedAssetSeriesSet:
    """Build one prepared set on a single daily calendar shared by every asset.

    Same construction style as ``test_risk_analytics.make_prepared_set``: the return
    points are the subject and the valuation points are the wealth path implied by
    them, so a plugin reading either sees the same series.
    """
    observations = len(next(iter(returns_by_asset.values())))
    assert all(len(values) == observations for values in returns_by_asset.values())
    valuation_dates = [BASELINE + timedelta(days=index) for index in range(observations + 1)]
    return_dates = valuation_dates[1:]
    prepared: list[PreparedAssetSeries] = []
    for asset_id, returns in returns_by_asset.items():
        wealth = Decimal("100")
        valuation_points = [
            AssetValuationPoint(
                valuation_date=BASELINE,
                effective_price_date=BASELINE,
                is_price_carried_forward=False,
                native_close=wealth,
                native_currency="EUR",
                target_close=wealth,
                target_currency="EUR",
            )
        ]
        return_points: list[AssetReturnPoint] = []
        for previous_date, current_date, value in zip(valuation_dates[:-1], valuation_dates[1:], returns, strict=True):
            wealth *= Decimal(str(1 + value))
            valuation_points.append(
                AssetValuationPoint(
                    valuation_date=current_date,
                    effective_price_date=current_date,
                    is_price_carried_forward=False,
                    native_close=wealth,
                    native_currency="EUR",
                    target_close=wealth,
                    target_currency="EUR",
                )
            )
            return_points.append(
                AssetReturnPoint(
                    date=current_date,
                    previous_valuation_date=previous_date,
                    value=value,
                )
            )
        prepared.append(
            PreparedAssetSeries(
                valuations=AssetValuationSeries(asset_id=asset_id, target_currency="EUR", points=valuation_points),
                returns=AssetReturnSeries(asset_id=asset_id, target_currency="EUR", points=return_points),
            )
        )
    return PreparedAssetSeriesSet(
        requested_range=DateRangeModel(start=return_dates[0], end=return_dates[-1]),
        baseline_date=BASELINE,
        effective_range=DateRangeModel(start=return_dates[0], end=return_dates[-1]),
        target_currency="EUR",
        series=prepared,
        joint_valuation_dates=valuation_dates,
        joint_return_dates=return_dates,
        n_observations=observations,
        calendar_days=observations,
        annualization_factor=365.0,
        calendar_coverage=1.0,
        fresh_quote_coverage=1.0,
        data_quality=DataQualityReport(),
        fx_fingerprint="0" * 64,
    )


def asset_set_request(
    scope_asset_ids: tuple[int, ...],
    prepared: PreparedAssetSeriesSet,
    *,
    analytic_codes: tuple[str, ...] = ("asset_set_risk_return",),
) -> RiskQueryRequest:
    """One ASSET_SET query over the window the prepared set actually covers.

    A query must carry at least one analytic, so the default names one. It is only
    load-bearing for ``RiskService.execute``; ``_build_context`` never looks at the
    list, which is why the context helper below leaves it alone.
    """
    return RiskQueryRequest(
        scope=AssetSetRiskScope(kind=RiskScopeKind.ASSET_SET, asset_ids=list(scope_asset_ids)),
        date_range=prepared.requested_range,
        target_currency="EUR",
        mode=RiskMode.HISTORICAL,
        analytics=[
            RiskAnalyticRequest(
                instance_id=f"instance-{code}",
                analytic_code=code,
                parameters=ASSET_SET_PARAMETERS[code],
            )
            for code in analytic_codes
        ],
    )


def asset_set_context(
    returns_by_asset: dict[int, list[float]],
    *,
    scope_asset_ids: tuple[int, ...] | None = None,
    prepared: PreparedAssetSeriesSet | None = None,
) -> RiskExecutionContext:
    """Build the context through ``RiskService._build_context``, not by hand.

    The context is the whole subject of clause ⓪, so fabricating one would let the
    tests assume exactly what they are supposed to observe. This goes through the
    service's own builder with the scope inputs ``_load_scope_inputs`` returns for an
    ``AssetSetRiskScope`` — no weights, no values, no portfolio report — which is why
    ``primary_returns`` comes back empty here rather than by decree.

    ``db=None`` is safe because nothing on this path touches the session: the
    asset-set branch of ``_load_scope_inputs`` is pure, and ``_build_context`` is a
    pure function of its three arguments.
    """
    prepared = prepared if prepared is not None else make_prepared_set(returns_by_asset)
    scope_asset_ids = scope_asset_ids if scope_asset_ids is not None else tuple(returns_by_asset)
    return RiskService(db=None)._build_context(
        request=asset_set_request(scope_asset_ids, prepared),
        scope_inputs=_ScopeInputs(
            requested_asset_ids=scope_asset_ids,
            weights={},
            asset_values={},
            cash_weight=0,
            scope_value=None,
            portfolio_report=None,
            data_quality=DataQualityReport(),
            warnings=(),
        ),
        prepared=prepared,
    )


def price_result(asset_id: int, prices_by_date: dict[date, str]) -> FAPriceQueryResult:
    """A fresh, already-converted daily price series for one asset."""
    return FAPriceQueryResult(
        asset_id=asset_id,
        prices=[
            FAPricePoint(
                date=point_date,
                close=Decimal(close),
                currency="EUR",
                source_plugin_key="fixture",
            )
            for point_date, close in sorted(prices_by_date.items())
        ],
    )


# ---------------------------------------------------------------------------
# Clause ⓪ — one request, one preparation.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_one_request_prepares_the_asset_series_exactly_once_for_all_five_codes(monkeypatch):
    """The five-code design does not fragment the service's one-preparation rule.

    ⚠️ READ THE LABEL BEFORE READING THE ASSERTION. This test says nothing about
    whether the plugins compute well, and it is not evidence that any number below
    is right. It proves one thing: a single ``RiskQueryRequest`` carrying all five
    asset-set analytics still results in exactly **one** call to
    ``_prepare_asset_series``. That property belongs to ``RiskService.execute``,
    which prepares once before the per-analytic loop; splitting one comparison
    surface across five codes is precisely the change that could have broken it, so
    it is pinned at the level where the breakage would appear.

    The consequence a consumer can verify without access to any of this is asserted
    beside it: ``n_observations``, ``analyzed_range`` and ``annualization_factor``
    are **identical** across the five results. They can only be identical because
    the five measurements share one joint calendar. Five requests would each have
    intersected their own, and the five metadata blocks would have drifted apart
    while every individual payload still looked impeccable.
    """
    prepared = make_prepared_set(
        {
            CHOPPY_ASSET_ID: CHOPPY,
            STEADY_ASSET_ID: STEADY,
            REFERENCE_ASSET_ID: REFERENCE,
        }
    )
    scope_asset_ids = (CHOPPY_ASSET_ID, STEADY_ASSET_ID)
    request = asset_set_request(
        scope_asset_ids,
        prepared,
        analytic_codes=(
            "asset_set_kpi",
            "asset_set_var",
            "asset_set_drawdown",
            "asset_set_risk_return",
            "asset_set_comparison",
        ),
    )

    service = RiskService(db=None)
    preparation_calls: list[dict] = []

    async def counting_prepare(**kwargs):
        preparation_calls.append(kwargs)
        return prepared

    async def existing_asset_ids(asset_ids):
        # Pure stand-in for the only other DB read on this path. It answers "these
        # all exist", which is the case the test is about; the asset-not-found path
        # is a different question and has its own gate.
        return set(asset_ids)

    monkeypatch.setattr(service, "_prepare_asset_series", counting_prepare)
    monkeypatch.setattr(service, "_existing_asset_ids", existing_asset_ids)

    response = await service.execute(user_id=1, request=request)

    assert len(preparation_calls) == 1
    # One preparation *covering everything the request needs* — including the
    # comparison reference, which is not a scope member. A second load for the
    # benchmark would still have counted as "prepared once" while putting the
    # reference on a calendar of its own.
    assert preparation_calls[0]["asset_ids"] == (CHOPPY_ASSET_ID, STEADY_ASSET_ID, REFERENCE_ASSET_ID)

    assert [item.analytic_code for item in response.items] == [analytic.analytic_code for analytic in request.analytics]
    assert [item.error for item in response.items] == [None] * len(request.analytics)
    assert [item.output.kind for item in response.items] == [
        RiskOutputKind.KPI_SET,
        RiskOutputKind.VAR_CVAR_SET,
        RiskOutputKind.DRAWDOWN_SET,
        RiskOutputKind.RISK_RETURN_SET,
        RiskOutputKind.COMPARISON_SET,
    ]

    metadata = [item.metadata for item in response.items]
    assert {item.n_observations for item in metadata} == {prepared.n_observations}
    assert {item.annualization_factor for item in metadata} == {prepared.annualization_factor}
    assert {(item.analyzed_range.start, item.analyzed_range.end) for item in metadata} == {
        (prepared.joint_return_dates[0], prepared.joint_return_dates[-1]),
    }


def test_the_joint_calendar_is_the_intersection_and_not_each_asset_own_history():
    """The mechanism clause ⓪ rests on, observed on raw inputs of different length.

    Two assets with different raw histories — one quotes every day, the other is
    missing a single mid-window day — come out of preparation with the *same* number
    of return points. The missing day is dropped for **everybody**, so the asset that
    did quote on it has its neighbouring return measured across the gap exactly as
    its neighbour does.

    That is what makes per-asset rows in one payload comparable, and it is also why
    ``n_observations`` travels once in the metadata instead of once per row: within
    one prepared set it is a constant, and publishing it per asset would suggest the
    values could differ.
    """
    days = [BASELINE + timedelta(days=index) for index in range(26)]
    withheld = days[13]
    complete = price_result(CHOPPY_ASSET_ID, {day: str(100 + index) for index, day in enumerate(days)})
    gapped = price_result(STEADY_ASSET_ID, {day: str(200 + index) for index, day in enumerate(days) if day != withheld})

    prepared = prepare_asset_series_set(
        [complete, gapped],
        requested_range=DateRangeModel(start=days[1], end=days[-1]),
        target_currency="EUR",
    )

    assert len(complete.prices) == 26
    assert len(gapped.prices) == 25
    assert withheld not in prepared.joint_valuation_dates
    assert prepared.data_quality.incomplete_valuation_dates == [withheld]
    # One calendar, one count, for every series in the set.
    assert prepared.n_observations == 24
    assert {len(item.returns.points) for item in prepared.series} == {prepared.n_observations}
    assert all([point.date for point in item.returns.points] == prepared.joint_return_dates for item in prepared.series)
    # The asset that *did* quote on the withheld day does not get a private return
    # for it: both series step across the gap from the same previous valuation.
    # Found by date rather than by index — the gap moves the positions.
    crossings = [next(point for point in item.returns.points if point.date == days[14]) for item in prepared.series]
    assert len(crossings) == len(prepared.series)
    assert {point.previous_valuation_date for point in crossings} == {days[12]}
    assert all(withheld not in [point.date for point in item.returns.points] for item in prepared.series)

    # And the analytics inherit it: the window the payload reports is the joint one.
    context = asset_set_context({}, scope_asset_ids=(CHOPPY_ASSET_ID, STEADY_ASSET_ID), prepared=prepared)
    output = AssetSetDrawdownAnalytic().compute(AssetSetDrawdownParams(), context).output
    assert output.available_start == prepared.joint_return_dates[0]
    assert output.available_end == prepared.joint_return_dates[-1]


def test_an_asset_set_context_carries_no_aggregate_series_of_its_own():
    """The premise every asset-set plugin is written against, stated once.

    ``_build_context`` fills ``primary_returns`` from a portfolio's TWRR curve, from
    a weighted backtest, or from the single asset of an ``asset`` scope. A weightless
    selection is none of those, so the field is empty — not zero-length by accident
    but because there is nothing to put in it. Every helper in
    ``analytic_helpers`` that these five plugins use exists to read the prepared set
    instead, and this is the fact that makes that necessary.
    """
    context = asset_set_context({CHOPPY_ASSET_ID: CHOPPY, STEADY_ASSET_ID: STEADY})

    assert context.scope_kind == RiskScopeKind.ASSET_SET
    assert context.primary_returns == ()
    assert context.primary_return_dates == ()
    assert context.primary_baseline_date is None
    assert context.n_observations == 0
    assert context.weights == {}
    # What is populated is the shared material.
    assert context.scope_asset_ids == (CHOPPY_ASSET_ID, STEADY_ASSET_ID)
    assert context.prepared_series is not None
    assert context.prepared_series.n_observations == OBSERVATIONS
    assert context.annualization_factor == context.prepared_series.annualization_factor


def test_asset_set_family_is_gated_on_the_prepared_set_not_on_the_absent_primary_series():
    """The history gate must count what these analytics actually consume.

    ``_available_observations`` decides what ``min_observations`` is compared
    against. Left on the default branch it returns ``context.n_observations``, which
    on an asset-set scope is **structurally zero** — see the test above — so every
    one of these plugins would be refused for insufficient history before its
    ``compute`` ran, on every request, with any data. That is not a data-driven
    refusal; it is a gate measuring the absence of a series nobody asked for.

    The assertion is scoped to this family on purpose: other analytics advertise the
    asset-set scope too, and what they should be counted on is their own mandate's
    question.
    """
    context = asset_set_context(
        {
            CHOPPY_ASSET_ID: CHOPPY,
            STEADY_ASSET_ID: STEADY,
            REFERENCE_ASSET_ID: REFERENCE,
        },
        scope_asset_ids=(CHOPPY_ASSET_ID, STEADY_ASSET_ID),
    )
    assert context.prepared_series is not None
    assert context.n_observations == 0

    for analytic_class in ASSET_SET_ANALYTIC_CLASSES:
        code = analytic_class.analytic_code
        plan = _AnalyticPlan(
            request=RiskAnalyticRequest(instance_id=f"instance-{code}", analytic_code=code, parameters=ASSET_SET_PARAMETERS[code]),
            analytic_class=analytic_class,
            analytic=analytic_class(),
            params=analytic_class.validate_params(ASSET_SET_PARAMETERS[code]),
        )
        available = RiskService._available_observations(plan, context)
        assert available == context.prepared_series.n_observations, code
        assert available >= analytic_class.min_observations, code


# ---------------------------------------------------------------------------
# Clause ① — no fabricated set-level aggregate.
# ---------------------------------------------------------------------------


def test_asset_set_risk_return_measures_each_asset_on_its_own_series():
    """(a) The happy path: one point per asset, on the convention the axes assume.

    The expectations are computed with ``statistics`` rather than with the product's
    own metric functions, so this pins the *convention* and not merely the call:
    volatility is the ddof=1 sample deviation scaled by the square root of the
    observed factor, and the expected return is the **arithmetic** mean scaled by the
    factor. Together they are what makes the slope from a risk-free intercept
    identically the Sharpe ratio — the geometry the singular analytic already ships,
    kept here so the two payloads cannot be read on axes that mean different things.
    """
    context = asset_set_context({CHOPPY_ASSET_ID: CHOPPY, STEADY_ASSET_ID: STEADY})
    factor = context.annualization_factor
    assert factor is not None

    output = AssetSetRiskReturnAnalytic().compute(AssetSetRiskReturnParams(), context).output

    assert [item.asset_id for item in output.items] == [CHOPPY_ASSET_ID, STEADY_ASSET_ID]
    by_asset = {item.asset_id: item for item in output.items}
    for asset_id, returns in ((CHOPPY_ASSET_ID, CHOPPY), (STEADY_ASSET_ID, STEADY)):
        # Derived from the series defined at the top of this file, not a product constant.
        assert by_asset[asset_id].volatility == pytest.approx(statistics.stdev(returns) * math.sqrt(factor), rel=1e-9)
        assert by_asset[asset_id].expected_annual_return == pytest.approx(statistics.fmean(returns) * factor, rel=1e-9)
    # Two different series must not land on the same point, or the assertions above
    # would hold for a plugin that measured one asset and copied the row.
    assert by_asset[CHOPPY_ASSET_ID].volatility != pytest.approx(by_asset[STEADY_ASSET_ID].volatility, rel=1e-6)


def test_asset_set_risk_return_publishes_one_item_per_scope_asset_and_no_set_level_key():
    """(a, continued) One item per usable scope asset, and nothing beside the items.

    The reference asset sits in the prepared set — a comparison in the same request
    puts it there — but it is not part of the selection, so it gets no point. What
    the payload contains is exactly two keys: the discriminator and the list.
    """
    context = asset_set_context(
        {
            CHOPPY_ASSET_ID: CHOPPY,
            STEADY_ASSET_ID: STEADY,
            REFERENCE_ASSET_ID: REFERENCE,
        },
        scope_asset_ids=(CHOPPY_ASSET_ID, STEADY_ASSET_ID),
    )

    output = AssetSetRiskReturnAnalytic().compute(AssetSetRiskReturnParams(), context).output

    assert [item.asset_id for item in output.items] == list(context.scope_asset_ids)
    assert REFERENCE_ASSET_ID not in {item.asset_id for item in output.items}
    assert set(output.model_dump()) == {"kind", "items"}


def test_asset_set_return_output_has_no_field_for_a_set_level_aggregate():
    """(b) Structural absence — true today, and true for a reason that expires.

    A selection has no weights, so it has no whole: no portfolio volatility, no
    portfolio expected return, no cash residual, and no per-item weight. The renderer
    draws the Capital Market Line only when the payload yields a portfolio point, so
    the absence of these fields is what makes the "paid well for the risk" judgement
    impossible rather than merely disabled.

    The singular model is asserted to *have* the same names, which is what keeps this
    test from passing vacuously: a typo in one of the absent names would otherwise
    satisfy it forever. What it cannot do is survive someone adding the field — it
    would simply start passing for a different reason, which is why the test below
    exists.
    """
    absent_on_a_weightless_scope = {"portfolio_volatility", "portfolio_expected_annual_return", "cash_weight"}

    assert absent_on_a_weightless_scope.isdisjoint(RiskAssetSetReturnOutput.model_fields)
    assert "weight" not in RiskAssetSetReturnItem.model_fields
    # The same names are real, and carry meaning, on the scope that has a composition.
    assert absent_on_a_weightless_scope <= set(RiskReturnOutput.model_fields)
    assert "weight" in RiskReturnItem.model_fields


def test_asset_set_return_output_actively_refuses_a_fabricated_portfolio_point():
    """(c) 🔴 The one that goes red at the exact moment the absence stops holding.

    The test above passes because the field is missing. It would keep passing the day
    somebody adds ``portfolio_volatility`` "for convenience" — computed, say, from an
    equal-weighted average — because the assertion it makes would simply become a
    statement about a different model. This one fails at that moment: ``StrictModel``
    is ``extra="forbid"``, so supplying the field today is a ``ValidationError``, and
    the only way to make this construction succeed is to declare the field. The
    fabricated aggregate is therefore not merely absent but *unexpressible*, and
    making it expressible again requires an edit that trips this assertion.

    Why it matters that the defence lives in the shape: an equal-weighted point would
    restore the Capital Market Line **through the data**, invisible to any renderer
    test — because the renderer would be doing exactly its job.
    """
    item = RiskAssetSetReturnItem(asset_id=CHOPPY_ASSET_ID, volatility=0.2, expected_annual_return=0.1)

    with pytest.raises(ValidationError) as exc_info:
        RiskAssetSetReturnOutput(items=[item], portfolio_volatility=0.1)
    assert "portfolio_volatility" in str(exc_info.value)

    with pytest.raises(ValidationError):
        RiskAssetSetReturnOutput(items=[item], portfolio_expected_annual_return=0.1)
    with pytest.raises(ValidationError):
        RiskAssetSetReturnOutput(items=[item], cash_weight=0.0)
    # The same refusal one level down, where a weight would let a caller rebuild the
    # aggregate itself from the items.
    with pytest.raises(ValidationError):
        RiskAssetSetReturnItem(asset_id=CHOPPY_ASSET_ID, volatility=0.2, expected_annual_return=0.1, weight=0.5)


def test_singular_risk_return_stays_pinned_to_portfolio_and_current_composition():
    """The mirror image of clause ①: the other half of the pair must not widen.

    Capabilities are two independent class-level tuples and every consumer reads them
    as a **cross product**. Adding ``asset_set`` here would advertise four pairs, and
    adding ``historical`` would advertise four more; the dangerous corner is
    ``portfolio`` x ``historical``, where the context *does* carry weights. The plugin
    would therefore not fail — it would return numbers: per-asset points measured
    against a portfolio's own TWRR curve, a chart nobody requested, advertised by the
    catalogue rather than asked for by any surface.

    Two codes turn that rectangle into two points. This assertion is the second
    corner of the same decision the asset-set family is the first corner of, which is
    why it is pinned here as well as beside its own plugin: widening either class
    silently invalidates the justification of the other.
    """
    assert AssetRiskReturnAnalytic.supported_scopes == (RiskScopeKind.PORTFOLIO,)
    assert AssetRiskReturnAnalytic.supported_modes == (RiskMode.CURRENT_COMPOSITION,)
    assert AssetSetRiskReturnAnalytic.supported_scopes == (RiskScopeKind.ASSET_SET,)
    assert AssetSetRiskReturnAnalytic.supported_modes == (RiskMode.HISTORICAL,)
    # The two codes are disjoint in both dimensions, so no request can reach both.
    assert set(AssetRiskReturnAnalytic.supported_scopes).isdisjoint(AssetSetRiskReturnAnalytic.supported_scopes)
    assert set(AssetRiskReturnAnalytic.supported_modes).isdisjoint(AssetSetRiskReturnAnalytic.supported_modes)


# ---------------------------------------------------------------------------
# The catalogue-wide invariant.
# ---------------------------------------------------------------------------


def test_every_advertised_scope_and_mode_pair_survives_the_service_compatibility_gate():
    """No plugin may advertise a combination the service would refuse as incompatible.

    The catalogue a consumer reads is ``RiskCatalogDefinition`` — published by
    ``catalog_definition()`` and served to the frontend, which builds its chart
    pickers from it. The gate the service applies is two lines at the top of
    ``RiskService.execute``, and it reads the **class attributes** of whatever
    ``RiskAnalyticRegistry.get_plugin(analytic_code)`` returns. This test walks every
    advertised ``(scope, mode)`` pair of the published catalogue and checks the gate
    would let it through, so the two sides cannot drift: a definition built from a
    filtered list, an overridden ``catalog_definition``, or a published code that no
    longer resolves back to its own class would all surface here as a pair the
    catalogue offers and the service answers ``INCOMPATIBLE_SCOPE`` /
    ``INCOMPATIBLE_MODE`` for.

    ⚠️ SCOPE, PRECISELY. This is a **declaration** check, not an execution. A pair
    that is compatible but yields ``INSUFFICIENT_HISTORY``, ``DATA_UNAVAILABLE`` or
    any other data-driven unavailability is *not* a catalogue defect — that is a
    different gate talking, about a particular request's data, and conflating the two
    would make this invariant fail for reasons that have nothing to do with what the
    catalogue promises.

    Every offender is collected before failing, so the report is a table rather than
    whichever plugin happens to be first alphabetically.
    """
    offenders: list[tuple[str, str, str, str]] = []
    checked_pairs = 0
    definitions = RiskAnalyticRegistry.list_definitions()
    for definition in definitions:
        analytic_class = RiskAnalyticRegistry.get_plugin(definition.analytic_code)
        if analytic_class is None:
            offenders.append((definition.analytic_code, "-", "-", "published code does not resolve to a plugin"))
            continue
        if analytic_class.analytic_code != definition.analytic_code:
            # The catalogue would send the frontend to a code the registry hands to
            # somebody else, and every pair below would be checked against the wrong
            # class — so this is reported once and the pairs are skipped.
            offenders.append((definition.analytic_code, "-", "-", f"registry key resolves to '{analytic_class.analytic_code}'"))
            continue
        for scope in definition.supported_scopes:
            for mode in definition.supported_modes:
                checked_pairs += 1
                if scope not in analytic_class.supported_scopes:
                    offenders.append((definition.analytic_code, scope.value, mode.value, RiskErrorCode.INCOMPATIBLE_SCOPE.value))
                if mode not in analytic_class.supported_modes:
                    offenders.append((definition.analytic_code, scope.value, mode.value, RiskErrorCode.INCOMPATIBLE_MODE.value))

    # The diagnostic first: an offender short-circuits its plugin's pairs, so the
    # barrier below would otherwise fail first and hide the table.
    assert offenders == [], "advertised pairs the service would refuse:\n" + "\n".join(f"  {code:24} {scope:12} {mode:20} {verdict}" for code, scope, mode, verdict in offenders)

    # The presence barrier: an empty catalogue, or one that stopped advertising
    # pairs, would satisfy every assertion above by having nothing to check.
    assert checked_pairs == sum(len(definition.supported_scopes) * len(definition.supported_modes) for definition in definitions)
    assert checked_pairs > len(ASSET_SET_ANALYTIC_CLASSES)
    assert {analytic_class.analytic_code for analytic_class in ASSET_SET_ANALYTIC_CLASSES} <= {definition.analytic_code for definition in definitions}


def test_asset_set_catalog_definitions_advertise_exactly_one_scope_and_one_mode():
    """Each code of this family is a point in the capability plane, not a rectangle.

    One scope and one mode is what makes the cross product harmless: there is no
    combination any of these five offers that none of them has ever run.
    """
    for analytic_class in ASSET_SET_ANALYTIC_CLASSES:
        definition = analytic_class.catalog_definition()
        assert definition.supported_scopes == [RiskScopeKind.ASSET_SET], definition.analytic_code
        assert definition.supported_modes == [RiskMode.HISTORICAL], definition.analytic_code
        assert definition.analytic_code == analytic_class.analytic_code
        assert definition.output_kind == analytic_class.output_kind
        assert definition.min_observations == analytic_class.min_observations
        assert definition.algorithm_version == analytic_class.algorithm_version


# ---------------------------------------------------------------------------
# Per-plugin behaviour.
# ---------------------------------------------------------------------------


def test_asset_set_kpi_publishes_one_row_per_asset_and_declares_every_omission():
    """A zero is a measurement; an undefined ratio must not be able to look like one.

    The flat asset has genuinely zero volatility — that zero is published, because it
    was measured. Its Sharpe and Sortino are ``None``, because dividing by that zero
    measures nothing, and a ``0.0`` there would read as "computed, and it is nil".
    Its worst realization is ``None`` too: every observation gained, so there is no
    worst loss, and a ``0`` would claim a loss that never happened.

    Each warning names the asset it is about, and names *only* that one — the
    neighbouring asset in the same payload keeps its defined values, which is what
    makes the warnings usable at all on a selection of eighty.
    """
    context = asset_set_context(
        {CHOPPY_ASSET_ID: CHOPPY, FLAT_GAINER_ASSET_ID: FLAT_GAINER},
        scope_asset_ids=(CHOPPY_ASSET_ID, FLAT_GAINER_ASSET_ID),
    )

    computation = AssetSetKpiAnalytic().compute(AssetSetKpiParams(), context)
    output = computation.output
    by_asset = {item.asset_id: item for item in output.items}

    assert [item.asset_id for item in output.items] == [CHOPPY_ASSET_ID, FLAT_GAINER_ASSET_ID]

    measured = by_asset[CHOPPY_ASSET_ID]
    assert measured.volatility > 0
    assert measured.sharpe is not None
    assert measured.sortino is not None
    # Derived from CHOPPY as defined above: the worst day is the smallest return,
    # and it is dated. `min`/`index` are plain Python, so this does not restate the
    # implementation it is checking.
    assert measured.worst_realization == pytest.approx(min(CHOPPY), rel=1e-12)
    assert measured.worst_realization_date == context.prepared_series.joint_return_dates[CHOPPY.index(min(CHOPPY))]
    assert measured.max_drawdown < 0
    assert measured.conditional_drawdown_at_risk <= measured.drawdown_at_risk <= 0
    assert measured.ulcer_index > 0

    undefined = by_asset[FLAT_GAINER_ASSET_ID]
    assert undefined.volatility == 0.0
    assert undefined.sharpe is None
    assert undefined.sortino is None
    assert undefined.worst_realization is None
    assert undefined.worst_realization_date is None

    warnings_by_code = {warning.code: warning for warning in computation.warnings}
    assert set(warnings_by_code) == {"sharpe_undefined", "sortino_undefined", "worst_realization_undefined"}
    for warning in warnings_by_code.values():
        assert warning.details["asset_ids"] == [FLAT_GAINER_ASSET_ID]


def test_asset_set_var_refuses_the_whole_request_when_the_horizon_eats_the_history():
    """The horizon shortfall is set-level, and a dropped row would hide it.

    Compounding to a multi-day horizon costs ``horizon_days - 1`` observations, so a
    window that clears the minimum on raw returns can fall short once compounded.
    Every asset shares the joint calendar, so the shortfall is identical for all of
    them: there is no selection where the horizon leaves one asset measurable and
    another not. The refusal therefore names the request, and the contrast case shows
    what the alternative would have looked like — the same request one day shorter
    returns a row for **every** scope asset, never a partial table.
    """
    context = asset_set_context({CHOPPY_ASSET_ID: CHOPPY, STEADY_ASSET_ID: STEADY})
    analytic = AssetSetVarAnalytic()
    # OBSERVATIONS - horizon + 1 falls one short of the declared minimum.
    too_long = OBSERVATIONS - analytic.min_observations + 2

    with pytest.raises(RiskUnavailableError) as exc_info:
        analytic.compute(AssetSetVarParams(horizon_days=too_long), context)

    assert exc_info.value.code == RiskErrorCode.INSUFFICIENT_HISTORY
    assert exc_info.value.details["horizon_days"] == too_long
    assert exc_info.value.details["observations"] == OBSERVATIONS - too_long + 1
    assert exc_info.value.details["required"] == analytic.min_observations

    longest_usable = analytic.compute(AssetSetVarParams(horizon_days=too_long - 1), context).output
    assert [item.asset_id for item in longest_usable.items] == list(context.scope_asset_ids)
    # One number for the set rather than a set-of-one across the rows: the
    # compounded count cannot differ between assets on a shared joint calendar.
    assert longest_usable.observations == analytic.min_observations


def test_asset_set_var_uses_the_coherent_tail_and_not_the_plug_in_mean():
    """The estimator is the Acerbi-Tasche one, so a figure here means what it means elsewhere.

    The tail is recomputed from the fixture with plain Python: with ``T`` observations
    and a nominal tail of ``m = (1 - confidence) * T`` observations, VaR is the
    ``ceil(m)``-th worst loss and CVaR counts the boundary observation for the
    *fraction* of it that falls inside the tail. The naive alternative — the mean of
    the worst ``ceil(m)`` losses — is computed alongside and asserted to be a
    different number, because a test that only checked ``cvar >= var`` would accept
    it, and it understates the tail.
    """
    context = asset_set_context({CHOPPY_ASSET_ID: CHOPPY, STEADY_ASSET_ID: STEADY})
    confidence_level = 0.95

    output = AssetSetVarAnalytic().compute(AssetSetVarParams(confidence_level=confidence_level, horizon_days=1), context).output
    item = next(item for item in output.items if item.asset_id == CHOPPY_ASSET_ID)

    losses = sorted((max(-value, 0.0) for value in CHOPPY), reverse=True)
    nominal_tail = (1.0 - confidence_level) * len(losses)
    whole = math.floor(nominal_tail)
    expected_var = losses[math.ceil(nominal_tail) - 1]
    expected_cvar = (math.fsum(losses[:whole]) + (nominal_tail - whole) * losses[whole]) / nominal_tail
    plug_in_cvar = statistics.fmean(losses[: math.ceil(nominal_tail)])

    # The fixture really has downside; a VaR of 0 here would mean the series never
    # lost and the assertions below would be about the floor, not about the tail.
    assert expected_var > 0
    # Stated once for the set, not once per row: one joint calendar compounded to
    # one horizon gives every asset the same count.
    assert output.observations == OBSERVATIONS
    assert not hasattr(item, "observations")
    assert item.value_at_risk == pytest.approx(expected_var, rel=1e-9)
    assert item.conditional_value_at_risk == pytest.approx(expected_cvar, rel=1e-9)
    assert item.conditional_value_at_risk >= item.value_at_risk
    assert item.conditional_value_at_risk != pytest.approx(plug_in_cvar, rel=1e-6)


def test_asset_set_drawdown_states_one_window_once_and_one_episode_per_asset():
    """The window is set-level; the episode, and what it still owes, is per asset.

    Two assets fell over the *same* days — that is the entire reason they can be put
    in one table — so ``available_start`` / ``available_end`` sit on the output and
    not on every row. What differs per asset is the episode: one has climbed back
    through its old peak and stands on it, the other is still under water. The
    asymmetry that makes losses worth reporting separately is checked where it is
    published: recovering a fall of ``d`` requires a rise of ``-d / (1 + d)``.
    """
    context = asset_set_context(
        {STILL_UNDERWATER_ASSET_ID: STILL_UNDERWATER, RECOVERED_ASSET_ID: RECOVERED},
        scope_asset_ids=(STILL_UNDERWATER_ASSET_ID, RECOVERED_ASSET_ID),
    )
    prepared = context.prepared_series
    assert prepared is not None

    computation = AssetSetDrawdownAnalytic().compute(AssetSetDrawdownParams(), context)
    output = computation.output
    by_asset = {item.asset_id: item for item in output.items}

    assert output.available_start == prepared.joint_return_dates[0]
    assert output.available_end == prepared.joint_return_dates[-1]
    assert output.return_basis == RiskReturnBasis.PRICE_ONLY
    assert computation.return_basis == RiskReturnBasis.PRICE_ONLY
    assert [item.asset_id for item in output.items] == list(context.scope_asset_ids)

    open_episode = by_asset[STILL_UNDERWATER_ASSET_ID]
    assert open_episode.maximum_drawdown_recovery_status == RiskDrawdownRecoveryStatus.OPEN
    assert open_episode.maximum_drawdown_recovery_date is None
    assert open_episode.maximum_drawdown < 0
    assert open_episode.current_drawdown < 0
    assert open_episode.remaining_to_peak_ratio == pytest.approx(-open_episode.current_drawdown / (1.0 + open_episode.current_drawdown), rel=1e-12)
    # Every date the episode names sits inside the window the set declares.
    assert BASELINE <= open_episode.maximum_drawdown_peak_date <= output.available_end
    assert open_episode.maximum_drawdown_peak_date <= open_episode.maximum_drawdown_trough_date <= output.available_end

    recovered = by_asset[RECOVERED_ASSET_ID]
    assert recovered.maximum_drawdown_recovery_status == RiskDrawdownRecoveryStatus.RECOVERED
    assert recovered.maximum_drawdown_recovery_date is not None
    assert recovered.maximum_drawdown_recovery_date >= recovered.maximum_drawdown_trough_date
    assert recovered.maximum_drawdown_recovered_ratio == pytest.approx(1.0, abs=1e-12)
    # It ended on its peak, so it owes nothing — and a zero here *is* a measurement.
    assert recovered.current_drawdown == pytest.approx(0.0, abs=1e-12)
    assert recovered.remaining_to_peak_ratio == pytest.approx(0.0, abs=1e-12)


def test_asset_set_comparison_keeps_the_reference_out_of_the_measured():
    """The yardstick cannot also be one of the measured, at three independent levels.

    The reference is prepared inside the same request as the selection, so its own
    coordinates are measured on the same joint calendar as every item — which is what
    lets a scatter place the benchmark beside the holdings. But it is not a subject:
    the plugin refuses a selection that contains it, and the output model refuses the
    payload even if a future caller assembled one by hand.
    """
    context = asset_set_context(
        {
            CHOPPY_ASSET_ID: CHOPPY,
            STEADY_ASSET_ID: STEADY,
            REFERENCE_ASSET_ID: REFERENCE,
        },
        scope_asset_ids=(CHOPPY_ASSET_ID, STEADY_ASSET_ID),
    )
    factor = context.annualization_factor
    assert factor is not None

    computation = AssetSetComparisonAnalytic().compute(AssetSetComparisonParams(comparison_asset_id=REFERENCE_ASSET_ID), context)
    output = computation.output

    assert output.comparison_asset_id == REFERENCE_ASSET_ID
    assert [item.asset_id for item in output.items] == list(context.scope_asset_ids)
    assert REFERENCE_ASSET_ID not in {item.asset_id for item in output.items}
    assert output.observations == OBSERVATIONS
    # The reference's own pair, on the same window and the same convention as the items.
    assert output.comparison_volatility == pytest.approx(statistics.stdev(REFERENCE) * math.sqrt(factor), rel=1e-9)
    assert output.comparison_expected_annual_return == pytest.approx(statistics.fmean(REFERENCE) * factor, rel=1e-9)
    assert all(item.beta is not None for item in output.items)

    # Level two: the same reference inside the selection is refused by the plugin.
    overlapping = asset_set_context(
        {
            CHOPPY_ASSET_ID: CHOPPY,
            STEADY_ASSET_ID: STEADY,
            REFERENCE_ASSET_ID: REFERENCE,
        },
        scope_asset_ids=(CHOPPY_ASSET_ID, STEADY_ASSET_ID, REFERENCE_ASSET_ID),
    )
    with pytest.raises(RiskUnavailableError) as exc_info:
        AssetSetComparisonAnalytic().compute(AssetSetComparisonParams(comparison_asset_id=REFERENCE_ASSET_ID), overlapping)
    assert exc_info.value.code == RiskErrorCode.INVALID_PARAMETERS
    assert exc_info.value.details["comparison_asset_id"] == REFERENCE_ASSET_ID

    # Level three: even hand-assembled, the payload cannot carry the contradiction.
    with pytest.raises(ValidationError):
        RiskAssetSetComparisonOutput(
            comparison_asset_id=REFERENCE_ASSET_ID,
            observations=OBSERVATIONS,
            items=[
                RiskAssetSetComparisonItem(
                    asset_id=REFERENCE_ASSET_ID,
                    active_return=0.0,
                    tracking_error=0.0,
                    information_ratio=None,
                    correlation=1.0,
                    beta=1.0,
                )
            ],
        )


def test_asset_set_comparison_reports_an_undefined_beta_as_undefined():
    """Zero would be a claim; ``None`` is the absence of one.

    Beta divides by the reference's variance and correlation divides by both, so a
    flat benchmark leaves them undefined. Publishing ``0`` there would read as
    "measured, and they are unrelated" — a much stronger statement than the data
    supports, and one a scatter would happily draw.
    """
    context = asset_set_context(
        {
            CHOPPY_ASSET_ID: CHOPPY,
            STEADY_ASSET_ID: STEADY,
            FLAT_GAINER_ASSET_ID: FLAT_GAINER,
        },
        scope_asset_ids=(CHOPPY_ASSET_ID, STEADY_ASSET_ID),
    )

    computation = AssetSetComparisonAnalytic().compute(AssetSetComparisonParams(comparison_asset_id=FLAT_GAINER_ASSET_ID), context)
    output = computation.output

    assert [item.beta for item in output.items] == [None, None]
    assert [item.correlation for item in output.items] == [None, None]
    # The measurable ones are still measured — the refusal is per figure, not per row.
    assert all(item.tracking_error > 0 for item in output.items)

    warnings_by_code = {warning.code: warning for warning in computation.warnings}
    assert set(warnings_by_code) == {"comparison_beta_undefined", "comparison_correlation_undefined"}
    for warning in warnings_by_code.values():
        assert warning.details["asset_ids"] == list(context.scope_asset_ids)


# ---------------------------------------------------------------------------
# Serialization.
# ---------------------------------------------------------------------------


def test_asset_set_outputs_round_trip_through_the_discriminated_union():
    """Five new ``RiskOutputKind`` values, five classes the union resolves back to.

    A kind that fails to discriminate does not raise anywhere near the plugin: the
    response simply validates into the wrong member, or fails at the API boundary
    with a message about a model nobody was writing.
    """
    context = asset_set_context(
        {
            CHOPPY_ASSET_ID: CHOPPY,
            STEADY_ASSET_ID: STEADY,
            REFERENCE_ASSET_ID: REFERENCE,
        },
        scope_asset_ids=(CHOPPY_ASSET_ID, STEADY_ASSET_ID),
    )
    outputs = [
        AssetSetKpiAnalytic().compute(AssetSetKpiParams(), context).output,
        AssetSetVarAnalytic().compute(AssetSetVarParams(), context).output,
        AssetSetDrawdownAnalytic().compute(AssetSetDrawdownParams(), context).output,
        AssetSetRiskReturnAnalytic().compute(AssetSetRiskReturnParams(), context).output,
        AssetSetComparisonAnalytic().compute(AssetSetComparisonParams(comparison_asset_id=REFERENCE_ASSET_ID), context).output,
    ]
    expected_classes = {
        RiskOutputKind.KPI_SET: RiskAssetSetKpiOutput,
        RiskOutputKind.VAR_CVAR_SET: RiskAssetSetVarCvarOutput,
        RiskOutputKind.DRAWDOWN_SET: RiskAssetSetDrawdownOutput,
        RiskOutputKind.RISK_RETURN_SET: RiskAssetSetReturnOutput,
        RiskOutputKind.COMPARISON_SET: RiskAssetSetComparisonOutput,
    }

    assert [output.kind for output in outputs] == [analytic_class.output_kind for analytic_class in ASSET_SET_ANALYTIC_CLASSES]
    assert set(expected_classes) == {analytic_class.output_kind for analytic_class in ASSET_SET_ANALYTIC_CLASSES}

    for output in outputs:
        payload = output.model_dump(mode="json")
        restored = TypeAdapter(RiskAnalyticOutput).validate_python(payload)
        assert isinstance(restored, expected_classes[output.kind]), payload["kind"]
        assert restored.model_dump(mode="json") == payload
        assert [item.asset_id for item in restored.items] == [item.asset_id for item in output.items]
