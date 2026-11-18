"""Serializable quantitative simulation boundary and production engine."""

from backend.app.services.risk.quant.engine import (
    MAX_HISTORY_CELLS,
    MAX_STOCHASTIC_CELLS,
    MIN_SIMULATION_PATHS,
    SimulationResourceLimitError,
    clear_simulation_cache,
    fit_path_count,
    history_observation_cap,
    run_simulation,
    validate_resource_budget,
)
from backend.app.services.risk.quant.estimation import (
    GbmParameterEstimates,
    align_simple_returns,
    estimate_drift_uncertainty,
    estimate_gbm_parameters,
)
from backend.app.services.risk.quant.models import (
    MAX_HISTORY_OBSERVATIONS,
    MAX_SIMULATION_ASSETS,
    MAX_SOBOL_DIMENSION,
    SimulationEngineRequest,
    SimulationEngineResult,
    historical_returns_digest,
    simulation_cache_key,
)
from backend.app.services.risk.quant.resampling import (
    resolve_block_length,
    resolve_regime_days,
    run_block_bootstrap,
)

__all__ = [
    "MAX_HISTORY_CELLS",
    "MAX_HISTORY_OBSERVATIONS",
    "MAX_SIMULATION_ASSETS",
    "MAX_SOBOL_DIMENSION",
    "MAX_STOCHASTIC_CELLS",
    "MIN_SIMULATION_PATHS",
    "GbmParameterEstimates",
    "SimulationEngineRequest",
    "SimulationEngineResult",
    "SimulationResourceLimitError",
    "align_simple_returns",
    "clear_simulation_cache",
    "estimate_drift_uncertainty",
    "estimate_gbm_parameters",
    "fit_path_count",
    "historical_returns_digest",
    "history_observation_cap",
    "resolve_block_length",
    "resolve_regime_days",
    "run_block_bootstrap",
    "run_simulation",
    "simulation_cache_key",
    "validate_resource_budget",
]
