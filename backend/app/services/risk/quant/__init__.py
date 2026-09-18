"""Serializable quantitative simulation boundary and production engine."""

from backend.app.services.risk.quant.engine import (
    MAX_HISTORY_CELLS,
    SimulationResourceLimitError,
    clear_simulation_cache,
    run_simulation,
    validate_resource_budget,
)
from backend.app.services.risk.quant.estimation import (
    GbmParameterEstimates,
    align_simple_returns,
    estimate_gbm_parameters,
)
from backend.app.services.risk.quant.models import (
    MAX_HISTORY_OBSERVATIONS,
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
    "MAX_SOBOL_DIMENSION",
    "GbmParameterEstimates",
    "SimulationEngineRequest",
    "SimulationEngineResult",
    "SimulationResourceLimitError",
    "align_simple_returns",
    "clear_simulation_cache",
    "estimate_gbm_parameters",
    "historical_returns_digest",
    "resolve_block_length",
    "resolve_regime_days",
    "run_block_bootstrap",
    "run_simulation",
    "simulation_cache_key",
    "validate_resource_budget",
]
