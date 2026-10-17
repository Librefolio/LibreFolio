"""
MF-D2 (workstream MF, lot D, part 2): a total loss keeps its AI Export drawdown section, and the per-asset drawdown
snapshot reads its returns the way the Risk series does.

Module under test: ``backend/app/services/ai_export/components/drawdown_context.py``.

Context (CP-13a): ``risk/metrics.py::drawdown_episodes`` answers ``remaining_to_peak_ratio=None`` for a total loss — a
drawdown of exactly -1.0 in floating point, from which no finite gain climbs back — and the drawdown analytics add the
non-degrading warning ``total_loss_no_recovery`` (``risk_plugins/drawdown_summary/plugin.py``). Before MF-D2 every
successful AI Export drawdown section required the gain, so a total loss raised a ValidationError instead of building a
section.

The contract (developer decision via the coordinator, agreed with J):

1. ``DrawdownContextPayload`` (``ok``/``partial``): ``remaining_to_peak_ratio`` may be None **only** when
   ``current_drawdown_ratio <= -1``; anywhere else it stays required. ``_success_payload`` builds a total-loss Risk
   result, keeps every other metric verbatim and carries the warning in ``warnings``.
2. ``PortfolioAssetDrawdownRow``: the same rule.
3. The return path: ``_observed_price_points`` keeps the Decimal closes and ``_asset_drawdown_row`` computes each return
   with ``financial_math.returns.float_price_return``, the function ``market_series.prepare_asset_series_set``
   uses, so the row's drawdown is ``drawdown_episodes`` over exactly the returns the Risk series carries. Before MF-D2
   the closes became floats first and the return was ``float(end) / float(start) - 1``: another number on
   high-precision closes.
4. The four drawdown components move 1 → 2, on the real spec and on the frozen catalog placeholder together (also pinned
   in ``test_ai_export_dataset_analysis_catalogs.py``, beside the other bumps).
5. A fall the episode maths refuses fails that asset's row, not the section. A single fall whose float return is already
   -1.0 (``1000000 → 0.00000000001``, a return of ``1e-17 - 1``) takes the float wealth to 0.0, and ``drawdown_episodes``
   raises ``ValueError`` ("drawdown values must be finite and positive") before any gain is asked for. The row is then
   ``failed`` with ``reason_code="risk_execution_error"``, no metrics, its ``n_observations``, and the error is logged
   with its ``asset_id`` — Risk's rule for an undeclared failure (``risk/service.py``): reported as ours, logged, never a
   verdict on the data. The other assets of the snapshot keep their rows. Before, the ``ValueError`` escaped
   ``_asset_drawdown_row`` and took the whole ``portfolio.asset_drawdown_snapshot`` build with it.

The total-loss fixture is the one CP-13a verified (``test_risk_metrics.py``, ``test_risk_analytics.py``): two falls of
99.99999999 % — closes ``1 → 1E-10 → 1E-20`` — leave about 1e-20 of the value, still positive for the underwater curve,
and a drawdown of exactly -1.0. The deep fall of point 5 is the other side of that line: the same -100 % reached in one
step, which the float wealth cannot represent.

``float_price_return`` is read as an attribute of ``returns`` while each test runs, never imported at module level, so
the file collects without MF-D1 too. The other names it imports exist on HEAD (b05b80201).

Pure: no database, no server, no network.
"""

from __future__ import annotations

import math
import sys
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import backend.app.services.ai_export.components.drawdown_context as drawdown_module
from backend.app.schemas.portfolio import DataQualityReport
from backend.app.schemas.prices import FAPricePoint, FAPriceQueryResult
from backend.app.schemas.risk import (
    RiskAnalyticResult,
    RiskDrawdownOutput,
    RiskDrawdownRecoveryStatus,
    RiskResultStatus,
    RiskReturnBasis,
    RiskWarning,
)
from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.drawdown_context import (
    REASON_RISK_ERROR,
    DrawdownContextPayload,
    DrawdownContextStatus,
    PortfolioAssetDrawdownRow,
    PortfolioAssetDrawdownSnapshotPayload,
    _asset_drawdown_row,
    _build_portfolio_asset_drawdown_snapshot,
    _observed_price_points,
    _success_payload,
)
from backend.app.services.ai_export.components.resources import PriceResultsResource
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, Domain
from backend.app.services.ai_export.dependencies import BuildContext, build_bucket_plan_for_scope
from backend.app.services.financial_math import returns as fm_returns
from backend.app.services.financial_math.returns import required_recovery_return
from backend.app.services.risk.metrics import drawdown_episodes, underwater_drawdown, wealth_index

PERIOD_START = date(2024, 1, 1)
PERIOD_END = date(2024, 12, 31)

# The total loss: one open episode from its peak at the period start down to nothing.
TOTAL_LOSS_PEAK = date(2024, 3, 1)
TOTAL_LOSS_TROUGH = date(2024, 9, 2)
TOTAL_LOSS_OPEN_DAYS = (PERIOD_END - TOTAL_LOSS_PEAK).days

# What the drawdown analytics publish beside a total loss: informative, never degrading.
TOTAL_LOSS_WARNING = RiskWarning(
    code="total_loss_no_recovery",
    message_i18n_key="risk.warnings.total_loss_no_recovery",
    message="The value fell to zero: no gain can bring it back to its peak, so the recovery needed is not shown.",
    degrades_result=False,
)

# The CP-13a total loss as closes: two falls of 99.99999999 %.
TOTAL_LOSS_CLOSES = (
    (PERIOD_START, Decimal("1")),
    (date(2024, 6, 3), Decimal("1E-10")),
    (PERIOD_END, Decimal("1E-20")),
)

# High-precision closes on which the float quotient and the Decimal return differ: the return path shows in the result.
HIGH_PRECISION_CLOSES = (
    (PERIOD_START, Decimal("101.37")),
    (date(2024, 3, 1), Decimal("99.993")),
    (date(2024, 5, 2), Decimal("100.0001")),
    (date(2024, 7, 1), Decimal("97.4321")),
    (date(2024, 9, 2), Decimal("98.76543")),
    (PERIOD_END, Decimal("96.0007")),
)

# One fall of everything but 1e-17 of the price: its float return is exactly -1.0, so the float wealth reaches 0.0.
DEEP_FALL_CLOSES = (
    (PERIOD_START, Decimal("1000000")),
    (PERIOD_END, Decimal("0.00000000001")),
)

# An ordinary open drawdown (100 → 80 → 90), the asset that must keep its row beside the deep fall.
ORDINARY_CLOSES = (
    (PERIOD_START, Decimal("100")),
    (date(2024, 6, 3), Decimal("80")),
    (PERIOD_END, Decimal("90")),
)

# The metrics a row without a result never carries (the row validator's list).
ROW_METRIC_FIELDS = (
    "calculation_basis",
    "calculation_currency",
    "data_quality_status",
    "current_drawdown_ratio",
    "maximum_drawdown_ratio",
    "maximum_drawdown_recovery_status",
    "remaining_to_peak_ratio",
    "available_start",
    "available_end",
)

# Short of a total loss, the gain stays required. The float just above -1 has a finite (huge) gain: the bound is exact.
SHORT_OF_A_TOTAL_LOSS = [
    pytest.param(-0.5, id="half-lost"),
    pytest.param(math.nextafter(-1.0, 0.0), id="the-float-just-above-minus-one"),
]


# =============================================================================
# Builders
# =============================================================================


def _portfolio_scope() -> BuildScope:
    return BuildScope(
        request_id="req-portfolio-drawdown-total-loss",
        user_id=42,
        domain=Domain.PORTFOLIO,
        detail_level=DetailLevel.STANDARD,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        target_currency="EUR",
    )


def _total_loss_output() -> RiskDrawdownOutput:
    """A ``drawdown_summary`` output after a total loss, shaped as the analytic publishes it (CP-13a)."""
    return RiskDrawdownOutput(
        current_drawdown=-1.0,
        current_peak_date=TOTAL_LOSS_PEAK,
        current_drawdown_duration_days=TOTAL_LOSS_OPEN_DAYS,
        maximum_drawdown=-1.0,
        maximum_drawdown_peak_date=TOTAL_LOSS_PEAK,
        maximum_drawdown_trough_date=TOTAL_LOSS_TROUGH,
        maximum_drawdown_recovery_status=RiskDrawdownRecoveryStatus.OPEN,
        maximum_drawdown_recovery_date=None,
        maximum_drawdown_duration_days=TOTAL_LOSS_OPEN_DAYS,
        maximum_drawdown_recovered_ratio=0.0,
        maximum_drawdown_trough_to_peak_ratio=None,
        remaining_to_peak_ratio=None,
        available_start=PERIOD_START,
        available_end=PERIOD_END,
        n_observations=250,
        coverage=0.95,
        calculation_basis="price_only_close",
        return_basis=RiskReturnBasis.PRICE_ONLY,
    )


def _risk_result(output: RiskDrawdownOutput, *, warnings: list[RiskWarning], status: RiskResultStatus) -> RiskAnalyticResult:
    # As ``_ok_result`` in test_ai_export_components_drawdown_context.py: model_construct skips the
    # success-requires-metadata validator; the component reads only status/output/data_quality/warnings/error.
    return RiskAnalyticResult.model_construct(
        instance_id="ai_export_drawdown_context",
        analytic_code="drawdown_summary",
        status=status,
        output=output,
        metadata=None,
        data_quality=DataQualityReport(),
        warnings=list(warnings),
        error=None,
    )


def _open_episode_payload_fields(current_drawdown_ratio: float, remaining_to_peak_ratio: float | None) -> dict:
    """A successful ``DrawdownContextPayload``: one open episode, as deep now as at its trough."""
    return {
        "status": DrawdownContextStatus.OK,
        "calculation_basis": "price_only_close",
        "return_basis": "price_only",
        "calculation_currency": "EUR",
        "data_quality_status": "ok",
        "current_drawdown_ratio": current_drawdown_ratio,
        "current_peak_date": TOTAL_LOSS_PEAK,
        "current_drawdown_duration_days": TOTAL_LOSS_OPEN_DAYS,
        "maximum_drawdown_ratio": current_drawdown_ratio,
        "maximum_drawdown_peak_date": TOTAL_LOSS_PEAK,
        "maximum_drawdown_trough_date": TOTAL_LOSS_TROUGH,
        "maximum_drawdown_recovery_status": "open",
        "maximum_drawdown_duration_days": TOTAL_LOSS_OPEN_DAYS,
        "maximum_drawdown_recovered_ratio": 0.0,
        "remaining_to_peak_ratio": remaining_to_peak_ratio,
        "available_start": PERIOD_START,
        "available_end": PERIOD_END,
        "n_observations": 250,
        "coverage_ratio": 0.95,
    }


def _open_row_fields(current_drawdown_ratio: float, remaining_to_peak_ratio: float | None) -> dict:
    """An available ``PortfolioAssetDrawdownRow``: one open episode, as deep now as at its trough."""
    return {
        "asset_id": 7,
        "status": DrawdownContextStatus.OK,
        "calculation_basis": "observed_native_price_only_close",
        "calculation_currency": "EUR",
        "data_quality_status": "ok",
        "current_drawdown_ratio": current_drawdown_ratio,
        "maximum_drawdown_ratio": current_drawdown_ratio,
        "maximum_drawdown_recovery_status": "open",
        "remaining_to_peak_ratio": remaining_to_peak_ratio,
        "available_start": date(2024, 6, 3),
        "available_end": PERIOD_END,
        "n_observations": 3,
        "coverage_ratio": 1.0,
    }


def _price_result(closes: tuple[tuple[date, Decimal], ...], *, asset_id: int = 7) -> FAPriceQueryResult:
    """Observed prices as the price service returns them: one currency, no backward fill."""
    return FAPriceQueryResult(asset_id=asset_id, prices=[FAPricePoint(date=point_date, close=close, currency="EUR") for point_date, close in closes])


def _house_returns(closes) -> list[float]:
    return [fm_returns.float_price_return(previous, current) for (_, previous), (_, current) in zip(closes, closes[1:], strict=False)]


def _house_drawdown(closes):
    dates = tuple(point_date for point_date, _ in closes)
    return drawdown_episodes(_house_returns(closes), dates=dates[1:], baseline_date=dates[0])


class _ExceptionLog:
    """Stands in for ``drawdown_context.logger``: records each ``exception`` call with the exception being handled."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict, type[BaseException] | None]] = []

    def exception(self, event: str, **fields) -> None:
        # ``logger.exception`` attaches the exception being handled: it is only meaningful inside the ``except``.
        self.calls.append((event, fields, sys.exc_info()[0]))


@pytest.fixture
def exception_log(monkeypatch) -> _ExceptionLog:
    """The module's logger, recorded instead of written: the deep-fall tests stay quiet and the log call is observable.

    ``raising=False``: before the deep-fall rule the module has no ``logger`` at all, and the red to read there is the
    ``ValueError`` that escapes the row, not a missing attribute.
    """
    log = _ExceptionLog()
    monkeypatch.setattr(drawdown_module, "logger", log, raising=False)
    return log


# =============================================================================
# 1. DrawdownContextPayload: a total loss builds, without its gain
# =============================================================================


class TestDrawdownContextPayloadTotalLoss:
    @pytest.mark.parametrize("status", [RiskResultStatus.OK, RiskResultStatus.PARTIAL])
    def test_success_payload_keeps_a_total_loss_without_a_gain(self, status):
        """RED before MF-D2: ``remaining_to_peak_ratio`` was a required success field, so this raised a ValidationError."""
        output = _total_loss_output()

        payload = _success_payload(_risk_result(output, warnings=[TOTAL_LOSS_WARNING], status=status), calculation_currency="EUR")

        assert payload.status == DrawdownContextStatus(status.value)
        assert payload.reason_code is None
        assert payload.message is None
        # The one field a total loss cannot have.
        assert payload.remaining_to_peak_ratio is None
        # Everything else is the Risk output's, verbatim.
        assert payload.current_drawdown_ratio == -1.0
        assert payload.maximum_drawdown_ratio == -1.0
        assert payload.current_peak_date == output.current_peak_date
        assert payload.current_drawdown_duration_days == output.current_drawdown_duration_days
        assert payload.maximum_drawdown_peak_date == output.maximum_drawdown_peak_date
        assert payload.maximum_drawdown_trough_date == output.maximum_drawdown_trough_date
        assert payload.maximum_drawdown_recovery_status == RiskDrawdownRecoveryStatus.OPEN.value
        assert payload.maximum_drawdown_recovery_date is None
        assert payload.maximum_drawdown_duration_days == output.maximum_drawdown_duration_days
        assert payload.maximum_drawdown_recovered_ratio == 0.0
        assert payload.available_start == output.available_start
        assert payload.available_end == output.available_end
        assert payload.n_observations == output.n_observations
        assert payload.coverage_ratio == output.coverage
        assert payload.calculation_basis == "price_only_close"
        assert payload.return_basis == "price_only"
        assert payload.calculation_currency == "EUR"
        assert payload.data_quality_status == DataQualityReport().data_quality_status.value
        # The warning travels with the section, in the component's "code: message" form.
        assert payload.warnings == (f"total_loss_no_recovery: {TOTAL_LOSS_WARNING.message}",)

    def test_a_total_loss_payload_carries_an_explicit_null_on_the_wire(self):
        payload = _success_payload(_risk_result(_total_loss_output(), warnings=[TOTAL_LOSS_WARNING], status=RiskResultStatus.OK), calculation_currency="EUR")

        wire = payload.model_dump(mode="json")

        # A key with null, never a missing key: the renderer prints it as the literal null.
        assert "remaining_to_peak_ratio" in wire
        assert wire["remaining_to_peak_ratio"] is None
        assert wire["current_drawdown_ratio"] == -1.0
        # And what is serialized validates back.
        assert DrawdownContextPayload.model_validate(wire) == payload

    @pytest.mark.parametrize("current_drawdown_ratio", SHORT_OF_A_TOTAL_LOSS)
    def test_the_gain_stays_required_short_of_a_total_loss(self, current_drawdown_ratio):
        """GREEN before and after MF-D2: the exemption is for a total loss only."""
        # Control: with its gain, the same payload builds — what is refused below is the missing gain, nothing else.
        DrawdownContextPayload(**_open_episode_payload_fields(current_drawdown_ratio, required_recovery_return(current_drawdown_ratio)))

        with pytest.raises(ValidationError, match="remaining_to_peak_ratio"):
            DrawdownContextPayload(**_open_episode_payload_fields(current_drawdown_ratio, None))


# =============================================================================
# 2. PortfolioAssetDrawdownRow: the same rule
# =============================================================================


class TestAssetDrawdownRowTotalLoss:
    def test_the_fixture_is_a_total_loss_in_floating_point(self):
        """GREEN with MF-D1 (independent of MF-D2): the precondition, verified rather than assumed."""
        house_returns = _house_returns(TOTAL_LOSS_CLOSES)
        wealth = wealth_index(house_returns)

        # About 1e-20 of the value is left: still positive, so the underwater curve accepts it ...
        assert 0.0 < wealth[-1] < 1e-15
        # ... and 1e-20 / 1 - 1 rounds to exactly -1.0, the drawdown no finite gain recovers.
        assert underwater_drawdown(wealth)[-1] == -1.0
        assert drawdown_episodes(house_returns, dates=tuple(point_date for point_date, _ in TOTAL_LOSS_CLOSES[1:]), baseline_date=PERIOD_START).remaining_to_peak_ratio is None

    def test_asset_row_keeps_a_total_loss_without_a_gain(self):
        """RED before MF-D2: ``remaining_to_peak_ratio`` was a required metric of an available row."""
        row = _asset_drawdown_row(asset_id=7, points=TOTAL_LOSS_CLOSES, scope=_portfolio_scope(), calculation_currency="EUR")

        assert row.status == DrawdownContextStatus.OK
        assert row.reason_code is None
        assert row.current_drawdown_ratio == -1.0
        assert row.remaining_to_peak_ratio is None
        # Every other metric is there.
        assert row.maximum_drawdown_ratio == -1.0
        assert row.maximum_drawdown_recovery_status == "open"
        assert row.calculation_basis == "observed_native_price_only_close"
        assert row.calculation_currency == "EUR"
        assert row.data_quality_status == "ok"
        assert row.available_start == date(2024, 6, 3)
        assert row.available_end == PERIOD_END
        assert row.n_observations == 3
        assert row.coverage_ratio == 1.0
        # The row goes into the snapshot, and its null reaches the wire as a null.
        wire = PortfolioAssetDrawdownSnapshotPayload(rows=(row,)).model_dump(mode="json")
        (wire_row,) = wire["rows"]
        assert "remaining_to_peak_ratio" in wire_row
        assert wire_row["remaining_to_peak_ratio"] is None

    @pytest.mark.parametrize("current_drawdown_ratio", SHORT_OF_A_TOTAL_LOSS)
    def test_the_row_gain_stays_required_short_of_a_total_loss(self, current_drawdown_ratio):
        """GREEN before and after MF-D2: the exemption is for a total loss only."""
        # Control: with its gain, the same row builds.
        PortfolioAssetDrawdownRow(**_open_row_fields(current_drawdown_ratio, required_recovery_return(current_drawdown_ratio)))

        with pytest.raises(ValidationError):
            PortfolioAssetDrawdownRow(**_open_row_fields(current_drawdown_ratio, None))


# =============================================================================
# 2b. A fall the episode maths refuses: that asset's row fails, the snapshot stands
# =============================================================================


class TestAssetDrawdownRowDeepFall:
    def test_the_fixture_takes_the_float_wealth_to_zero(self):
        """GREEN with MF-D1 (independent of the rule): the precondition, verified rather than assumed."""
        house_returns = _house_returns(DEEP_FALL_CLOSES)

        # 1E-11 / 1E6 - 1 is -0.99999999999999999 in Decimal, exactly -1.0 as a float ...
        assert house_returns == [-1.0]
        # ... so the wealth is 0.0, which the underwater curve refuses: the episode maths raise before any gain.
        assert wealth_index(house_returns) == [1.0, 0.0]
        with pytest.raises(ValueError, match="finite and positive"):
            drawdown_episodes(house_returns, dates=(PERIOD_END,), baseline_date=PERIOD_START)

    def test_a_deep_fall_fails_its_row_without_metrics(self, exception_log):
        """RED before the rule: ``ValueError: drawdown values must be finite and positive`` escaped the row."""
        row = _asset_drawdown_row(asset_id=7, points=DEEP_FALL_CLOSES, scope=_portfolio_scope(), calculation_currency="EUR")

        # Reported as ours — the computation failed — never as a verdict on the data (unavailable).
        assert row.status == DrawdownContextStatus.FAILED
        assert row.reason_code == REASON_RISK_ERROR == "risk_execution_error"
        assert row.n_observations == len(DEEP_FALL_CLOSES)
        assert {name: getattr(row, name) for name in ROW_METRIC_FIELDS} == dict.fromkeys(ROW_METRIC_FIELDS)
        # The coverage default every row without a result carries.
        assert row.coverage_ratio == 0
        # A failed row is a valid row of the snapshot, on the wire too.
        wire = PortfolioAssetDrawdownSnapshotPayload(rows=(row,)).model_dump(mode="json")
        assert PortfolioAssetDrawdownSnapshotPayload.model_validate(wire).rows == (row,)

    def test_the_deep_fall_is_logged_with_its_asset(self, exception_log):
        """RED before the rule: the same ``ValueError`` escaped before anything was logged."""
        _asset_drawdown_row(asset_id=7, points=DEEP_FALL_CLOSES, scope=_portfolio_scope(), calculation_currency="EUR")

        assert len(exception_log.calls) == 1, exception_log.calls
        _event, fields, handled = exception_log.calls[0]
        assert fields.get("asset_id") == 7
        # Logged while the episode maths' ValueError is being handled: the traceback goes with the record.
        assert handled is ValueError

        # Control: an ordinary row logs nothing.
        _asset_drawdown_row(asset_id=8, points=ORDINARY_CLOSES, scope=_portfolio_scope(), calculation_currency="EUR")
        assert len(exception_log.calls) == 1, exception_log.calls

    @pytest.mark.asyncio
    async def test_the_snapshot_keeps_the_other_assets_beside_a_failed_row(self, monkeypatch, exception_log):
        """RED before the rule: the deep fall's ``ValueError`` escaped the builder, and the whole section was lost.

        Through ``_build_portfolio_asset_drawdown_snapshot`` itself. Its one I/O collaborator,
        ``load_technical_universe_bundle``, is doubled where the module reads it: the universe is this test's two
        assets and their prices, so no report, no price load, no session. The deep fall comes first, so a failure that
        stopped the loop would also lose the row after it.
        """
        scope = _portfolio_scope()
        context = BuildContext(build_component_registry(), request_id=scope.request_id, scope=scope, bucket_plan=build_bucket_plan_for_scope(scope))
        universe = SimpleNamespace(
            asset_ids=(7, 8),
            price_results=PriceResultsResource.from_results([_price_result(DEEP_FALL_CLOSES, asset_id=7), _price_result(ORDINARY_CLOSES, asset_id=8)]),
        )
        asked: list[BuildContext] = []

        async def _universe(build_context, **_resource_keys):
            asked.append(build_context)
            return universe

        monkeypatch.setattr(drawdown_module, "load_technical_universe_bundle", _universe)

        payload = await _build_portfolio_asset_drawdown_snapshot(context, {})

        assert asked == [context]
        rows = {row.asset_id: row for row in payload.rows}
        assert set(rows) == {7, 8}
        deep_fall, ordinary = rows[7], rows[8]
        # The deep fall: its own row, failed, without metrics.
        assert deep_fall.status == DrawdownContextStatus.FAILED
        assert deep_fall.reason_code == REASON_RISK_ERROR
        assert deep_fall.current_drawdown_ratio is None
        # The ordinary asset: untouched by its neighbour, every metric the house computes.
        expected = _house_drawdown(ORDINARY_CLOSES)
        assert ordinary.status == DrawdownContextStatus.OK
        assert ordinary.reason_code is None
        assert ordinary.current_drawdown_ratio == expected.current_drawdown
        assert ordinary.maximum_drawdown_ratio == expected.maximum_drawdown
        assert ordinary.remaining_to_peak_ratio == expected.remaining_to_peak_ratio
        assert ordinary.maximum_drawdown_recovery_status == "open"
        assert ordinary.n_observations == len(ORDINARY_CLOSES)
        # One log record, for the asset that failed.
        assert [fields.get("asset_id") for _event, fields, _handled in exception_log.calls] == [7]


# =============================================================================
# 3. The return path: the Risk series' own
# =============================================================================


class TestAssetDrawdownRowReturnPath:
    def test_observed_price_points_keep_the_decimal_closes(self):
        """RED before MF-D2: ``_observed_price_points`` turned every close into a float."""
        points = _observed_price_points(_price_result(HIGH_PRECISION_CLOSES), start=PERIOD_START, end=PERIOD_END)

        assert [type(close) for _, close in points] == [Decimal] * len(HIGH_PRECISION_CLOSES)
        # The closes themselves, not a float that compares close to them: Decimal("101.37") != 101.37 exactly.
        assert points == HIGH_PRECISION_CLOSES

    def test_the_fixture_tells_the_two_return_paths_apart(self):
        """GREEN with MF-D1 (independent of MF-D2): on these closes the float quotient gives another drawdown."""
        dates = tuple(point_date for point_date, _ in HIGH_PRECISION_CLOSES)
        house = drawdown_episodes(_house_returns(HIGH_PRECISION_CLOSES), dates=dates[1:], baseline_date=dates[0])
        floats = [float(close) for _, close in HIGH_PRECISION_CLOSES]
        naive = drawdown_episodes([current / previous - 1 for previous, current in zip(floats, floats[1:], strict=False)], dates=dates[1:], baseline_date=dates[0])

        # A drawdown, open, and different under the two paths: the equality in the next test has teeth.
        assert house.current_drawdown < 0
        assert house.maximum_drawdown_recovery_status == "open"
        assert naive.current_drawdown != house.current_drawdown
        assert naive.maximum_drawdown != house.maximum_drawdown

    def test_asset_row_drawdown_is_the_drawdown_of_the_series_returns(self):
        """RED before MF-D2, by value: the row's float-quotient returns gave a drawdown some ulps away from the house's.

        Through ``_observed_price_points`` and ``_asset_drawdown_row`` as ``_build_portfolio_asset_drawdown_snapshot``
        composes them: the row must equal ``drawdown_episodes`` over ``float_price_return`` of the same closes, the
        returns ``market_series`` gives the Risk ``drawdown_summary``. Exact equality, no tolerance.
        """
        scope = _portfolio_scope()
        points = _observed_price_points(_price_result(HIGH_PRECISION_CLOSES), start=scope.period_start, end=scope.period_end)
        row = _asset_drawdown_row(asset_id=7, points=points, scope=scope, calculation_currency="EUR")

        dates = tuple(point_date for point_date, _ in HIGH_PRECISION_CLOSES)
        expected = drawdown_episodes(_house_returns(HIGH_PRECISION_CLOSES), dates=dates[1:], baseline_date=dates[0])

        assert row.status == DrawdownContextStatus.OK
        assert row.current_drawdown_ratio == expected.current_drawdown
        assert row.maximum_drawdown_ratio == expected.maximum_drawdown
        assert row.remaining_to_peak_ratio == expected.remaining_to_peak_ratio
        assert row.maximum_drawdown_recovery_status == expected.maximum_drawdown_recovery_status


# =============================================================================
# 4. Versions: 1 → 2 on the real spec and on the frozen placeholder together
# =============================================================================


class TestDrawdownComponentVersion:
    """MF-D2 lets a total loss keep its section with ``remaining_to_peak_ratio`` null: the builder and the payload
    contract change, so the four drawdown components move from version 1 to 2 — on the real spec and on the frozen
    catalog placeholder together — with the same payload shape (schema_version 1). The catalog is imported in the test
    rather than at module level, so a parity failure on import reds these tests only.

    Before MF-D2: 1 on both sides."""

    @pytest.mark.parametrize(
        ("component_id", "real"),
        [
            pytest.param("portfolio.drawdown_summary", drawdown_module.PORTFOLIO_DRAWDOWN_SUMMARY_COMPONENT, id="portfolio-drawdown-summary"),
            pytest.param("portfolio.asset_drawdown_snapshot", drawdown_module.PORTFOLIO_ASSET_DRAWDOWN_SNAPSHOT_COMPONENT, id="portfolio-asset-drawdown-snapshot"),
            pytest.param("broker.drawdown_summary", drawdown_module.BROKER_DRAWDOWN_SUMMARY_COMPONENT, id="broker-drawdown-summary"),
            pytest.param("asset.drawdown_summary", drawdown_module.ASSET_DRAWDOWN_SUMMARY_COMPONENT, id="asset-drawdown-summary"),
        ],
    )
    def test_drawdown_component_version_in_spec_and_placeholder(self, component_id, real):
        from backend.app.services.ai_export.components import catalog  # noqa: PLC0415 — test-local: a real/placeholder parity failure on import must red these tests only

        placeholder = next(spec for spec in catalog.ALL_FOUNDATION_COMPONENTS if spec.component_id == component_id)
        assert real.component_id == component_id
        assert (real.version, placeholder.version, real.schema_version) == (2, 2, 1)
