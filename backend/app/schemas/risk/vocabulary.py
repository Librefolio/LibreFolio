"""Risk vocabulary: the enums every risk request, result and output speaks in (modes, scopes, output kinds, statuses, error codes, stress and simulation methods, eligibility)."""

from __future__ import annotations

from enum import StrEnum


class RiskDataFrequency(StrEnum):
    """Mathematical sampling frequency supported by Release 2."""

    DAILY = "daily"


class RiskMode(StrEnum):
    """Portfolio semantics used by a risk calculation."""

    HISTORICAL = "historical"
    CURRENT_COMPOSITION = "current_composition"


class RiskCompositionPolicy(StrEnum):
    """Weight-evolution policy supported for current composition."""

    CURRENT_BUY_AND_HOLD = "current_buy_and_hold"


class RiskReturnBasis(StrEnum):
    """Financial series consumed by a risk result."""

    PRICE_ONLY = "price_only"
    TWRR = "twrr"
    CURRENT_COMPOSITION_BACKTEST = "current_composition_backtest"


class RiskScopeKind(StrEnum):
    """Domain scope resolved before risk analytics execute."""

    ASSET = "asset"
    ASSET_SET = "asset_set"
    PORTFOLIO = "portfolio"


class RiskOutputKind(StrEnum):
    """Serializable output family advertised by the risk catalog."""

    KPI = "kpi"
    MATRIX = "matrix"
    CONTRIBUTION = "contribution"
    STRESS = "stress"
    COMPARISON = "comparison"
    VAR_CVAR = "var_cvar"
    SIMULATION = "simulation"
    OPTIMIZATION = "optimization"
    DRAWDOWN = "drawdown"
    RISK_RETURN = "risk_return"
    # The weightless multi-asset family, for the ASSET_SET scope. Each one is a
    # *list* of per-asset measurements carrying no set-level aggregate, because a
    # selection of assets has no weights and therefore nothing to aggregate into.
    # They are separate kinds rather than optional fields on the four singular
    # ones above: widening those would have meant making required scalars
    # optional, and an optional field is exactly the mechanism by which a
    # fabricated number becomes expressible. See RiskAssetSetReturnOutput.
    KPI_SET = "kpi_set"
    VAR_CVAR_SET = "var_cvar_set"
    DRAWDOWN_SET = "drawdown_set"
    RISK_RETURN_SET = "risk_return_set"
    COMPARISON_SET = "comparison_set"


class RiskDrawdownRecoveryStatus(StrEnum):
    """Recovery lifecycle of the maximum drawdown episode."""

    NO_DRAWDOWN = "no_drawdown"
    RECOVERED = "recovered"
    OPEN = "open"


class RiskResultStatus(StrEnum):
    """Per-analytic bulk execution status."""

    OK = "ok"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class RiskValueStatus(StrEnum):
    """Status for values that can be undefined independently."""

    OK = "ok"
    INSUFFICIENT = "insufficient"
    UNDEFINED = "undefined"


class RiskErrorCode(StrEnum):
    """Stable machine-readable failures for one analytic result."""

    ANALYTIC_NOT_FOUND = "analytic_not_found"
    INCOMPATIBLE_SCOPE = "incompatible_scope"
    INCOMPATIBLE_MODE = "incompatible_mode"
    INVALID_PARAMETERS = "invalid_parameters"
    INSUFFICIENT_HISTORY = "insufficient_history"
    UNDEFINED_METRIC = "undefined_metric"
    DATA_UNAVAILABLE = "data_unavailable"
    INVALID_COVARIANCE = "invalid_covariance"
    RESOURCE_LIMIT = "resource_limit"
    WORKER_BUSY = "worker_busy"
    EXECUTION_TIMEOUT = "execution_timeout"
    OPTIMIZATION_INFEASIBLE = "optimization_infeasible"
    EXECUTION_FAILED = "execution_failed"


class RiskStressMethod(StrEnum):
    """Deterministic stress methods shipped in Step 4."""

    HYPOTHETICAL = "hypothetical"
    HISTORICAL_REPLAY = "historical_replay"


class RiskStressApplicationRule(StrEnum):
    """Rule that selected one effective shock for an exposure bucket."""

    DIRECT = "direct"
    COUNTRY = "country"
    GEOGRAPHY_GROUP = "geography_group"
    OTHER = "other"
    MISSING_METADATA_OTHER = "missing_metadata_other"
    UNCONFIGURED_ZERO = "unconfigured_zero"


class RiskHistoricalReplayExclusionTreatment(StrEnum):
    """Effective handling of one excluded replay asset."""

    OMITTED_FROM_REPLAY = "omitted_from_replay"
    ZERO_RETURN_RESIDUAL = "zero_return_residual"


class RiskHistoricalReplayExclusionReason(StrEnum):
    """Why one asset takes no part in a historical replay.

    The user excludes an asset by hand; the engine excludes, on its own, every asset whose quotes do
    not cover the replay window at both ends within the project's staleness threshold. At the start
    a late listing and a gap in an older history are told apart, because the sentence differs; at
    the end they are not, because the facts stop at the window end.
    """

    MANUAL_EXCLUSION = "manual_exclusion"
    NO_PRICES_IN_WINDOW = "no_prices_in_window"
    STARTS_AFTER_WINDOW_START = "starts_after_window_start"
    STALE_AT_WINDOW_START = "stale_at_window_start"
    STALE_AT_WINDOW_END = "stale_at_window_end"
    MISSING_FX = "missing_fx"


class RiskSimulationProcess(StrEnum):
    """Stochastic or resampling process available to simulation."""

    BLOCK_BOOTSTRAP = "block_bootstrap"
    GBM = "gbm"


class RiskSimulationRegime(StrEnum):
    """Prescribed market regime overlaid on a resampled simulation.

    A regime is *declared*, never estimated from the data: every non-NONE
    value applies a stated transformation whose hypothesis must be shown to the
    user next to the choice that selects it.

    No backticks here, and that is load-bearing rather than a style choice.
    This docstring is the OpenAPI description of a NAMED enum, so the client
    generator emits it inside a JavaScript template literal, as an argument to
    the describe() call on the generated Zod enum. A backtick inside such a
    literal terminates the string, and the file then stops compiling at a point
    far from this line. Object schemas escape this because their descriptions
    become JSDoc comments instead; an enum is the one shape where the text lands
    in executable position.
    """

    NONE = "none"
    CALM = "calm"
    PROLONGED_CRISIS = "prolonged_crisis"
    SHOCK_RECOVERY = "shock_recovery"


class RiskSamplingStrategy(StrEnum):
    """Sampling strategy used for stochastic simulation."""

    MC = "mc"
    QMC = "qmc"


class RiskOptimizationStrategy(StrEnum):
    """Mean-variance strategies exposed by portfolio optimization."""

    MIN_RISK = "min_risk"
    MAX_SHARPE = "max_sharpe"
    RISK_PARITY = "risk_parity"


class RiskCovarianceEstimator(StrEnum):
    """Riskfolio covariance estimators approved for production."""

    HISTORICAL = "historical"
    LEDOIT_WOLF = "ledoit_wolf"
    OAS = "oas"


class RiskOptimizationSolver(StrEnum):
    """Open-source solvers accepted by the optimization worker."""

    CLARABEL = "clarabel"
    SCS = "scs"


class RiskSimulationDriftEstimator(StrEnum):
    """Drift estimator disclosed by simulation results."""

    HISTORICAL_LOG_MLE = "historical_log_mle"
    EMPIRICAL_RESAMPLED = "empirical_resampled"


class RiskSimulationCovarianceEstimator(StrEnum):
    """Covariance estimator disclosed by simulation results."""

    SAMPLE_LOG_RETURNS = "sample_log_returns"
    NOT_ESTIMATED_JOINT_RESAMPLING = "not_estimated_joint_resampling"


class RiskEligibilityLevel(StrEnum):
    """Whether an asset can be selected for a risk analysis of a period."""

    ELIGIBLE = "eligible"
    WARNING = "warning"
    INELIGIBLE = "ineligible"


class RiskEligibilityReason(StrEnum):
    """Why an asset is ineligible (the first four) or eligible with a warning (the last two).

    `no_price_history` (never quoted) is told apart from `no_prices` (no quote in the period, some
    elsewhere), because only the second can be mended by choosing another period.
    """

    NO_PRICE_HISTORY = "no_price_history"
    NO_PRICES = "no_prices"
    TOO_FEW_QUOTES = "too_few_quotes"
    MISSING_FX = "missing_fx"
    STARTS_LATE = "starts_late"
    STALE_AT_END = "stale_at_end"
