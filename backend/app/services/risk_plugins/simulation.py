"""Conditional correlated-GBM simulation for assets and current compositions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.risk import (
    RiskCompositionPolicy,
    RiskErrorCode,
    RiskMode,
    RiskOutputKind,
    RiskSamplingStrategy,
    RiskScopeKind,
    RiskSimulationBandPoint,
    RiskSimulationCovarianceEstimator,
    RiskSimulationDriftEstimator,
    RiskSimulationOutput,
    RiskSimulationProcess,
)
from backend.app.services.provider_registry import (
    RiskAnalyticRegistry,
    register_plugin,
)
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskUnavailableError,
)
from backend.app.services.risk.quant import (
    SimulationEngineRequest,
    SimulationResourceLimitError,
    estimate_gbm_parameters,
    run_simulation,
)
from backend.app.services.risk.quant.spawn_worker import (
    SpawnWorkerQueueFullError,
    SpawnWorkerRemoteError,
    SpawnWorkerTimeoutError,
)


class SimulationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process: RiskSimulationProcess = Field(
        RiskSimulationProcess.GBM,
        json_schema_extra={
            "x-i18n-key": "risk.params.process",
            "x-control-order": 1,
        },
    )
    sampling: RiskSamplingStrategy = Field(
        RiskSamplingStrategy.MC,
        json_schema_extra={
            "x-i18n-key": "risk.params.sampling",
            "x-control-order": 2,
        },
    )
    horizon_days: int = Field(
        365,
        ge=1,
        le=3650,
        json_schema_extra={
            "x-i18n-key": "risk.params.horizonDays",
            "x-control-order": 3,
            "x-step": 1,
            "x-suffix": "days",
        },
    )
    paths: int = Field(
        8192,
        ge=256,
        le=100_000,
        json_schema_extra={
            "x-i18n-key": "risk.params.paths",
            "x-control-order": 4,
            "x-step": 256,
        },
    )
    seed: int = Field(
        123456,
        ge=0,
        le=2**32 - 1,
        json_schema_extra={
            "x-i18n-key": "risk.params.seed",
            "x-control-order": 5,
            "x-step": 1,
        },
    )

    @model_validator(mode="after")
    def validate_sampling(self) -> SimulationParams:
        if self.sampling == RiskSamplingStrategy.QMC and self.paths & (self.paths - 1):
            raise ValueError("QMC paths must be a power of two")
        return self


@register_plugin(RiskAnalyticRegistry)
class SimulationAnalytic(RiskAnalytic):
    analytic_code = "simulation"
    algorithm_version = "2.0.0-quantlib-1.43"
    name_i18n_key = "risk.analytics.simulation.name"
    description_i18n_key = "risk.analytics.simulation.description"
    output_kind = RiskOutputKind.SIMULATION
    supported_scopes = (
        RiskScopeKind.ASSET,
        RiskScopeKind.PORTFOLIO,
        RiskScopeKind.BROKER,
    )
    supported_modes = (RiskMode.CURRENT_COMPOSITION,)
    params_model = SimulationParams
    min_observations = 30

    async def execute(self, params, context):
        prepared = context.prepared_series
        if prepared is None or context.annualization_factor is None:
            raise RiskUnavailableError(
                "Simulation requires prepared historical asset returns",
                code=RiskErrorCode.DATA_UNAVAILABLE,
            )
        asset_ids = context.scope_asset_ids
        if not asset_ids:
            raise RiskUnavailableError(
                "Simulation has no usable assets",
                code=RiskErrorCode.DATA_UNAVAILABLE,
            )
        prepared_by_asset = {item.returns.asset_id: item for item in prepared.series}
        returns_by_asset = {asset_id: [float(point.value) for point in prepared_by_asset[asset_id].returns.points] for asset_id in asset_ids}
        estimates = estimate_gbm_parameters(
            returns_by_asset,
            annualization_factor=(context.annualization_factor),
        )
        if context.scope_kind == RiskScopeKind.ASSET:
            weights = [1.0]
            cash_weight = 0.0
        else:
            weights = [
                context.weights.get(
                    asset_id,
                    0.0,
                )
                for asset_id in asset_ids
            ]
            cash_weight = context.cash_weight

        engine_request = SimulationEngineRequest(
            process=params.process,
            sampling=params.sampling,
            asset_ids=list(estimates.asset_ids),
            annual_drifts=list(estimates.annual_drifts),
            annual_covariance=[list(row) for row in estimates.annual_covariance],
            weights=weights,
            cash_weight=cash_weight,
            horizon_days=params.horizon_days,
            paths=params.paths,
            seed=params.seed,
        )
        try:
            engine_result, _cache_hit, _worker_result = await run_simulation(
                engine_request,
                algorithm_version=(f"{self.analytic_code}@" f"{self.algorithm_version}"),
            )
        except SimulationResourceLimitError as exc:
            raise RiskUnavailableError(
                str(exc),
                code=RiskErrorCode.INVALID_PARAMETERS,
                details={
                    "metric": exc.metric,
                    "actual": exc.actual,
                    "limit": exc.limit,
                },
            ) from exc
        except SpawnWorkerQueueFullError as exc:
            raise RiskUnavailableError(
                str(exc),
                code=RiskErrorCode.WORKER_BUSY,
            ) from exc
        except SpawnWorkerTimeoutError as exc:
            raise RiskUnavailableError(
                str(exc),
                code=RiskErrorCode.EXECUTION_TIMEOUT,
            ) from exc
        except SpawnWorkerRemoteError as exc:
            code = RiskErrorCode.INVALID_COVARIANCE if exc.remote_type.endswith("ValueError") else RiskErrorCode.EXECUTION_FAILED
            raise RiskUnavailableError(
                str(exc),
                code=code,
                details={"remote_type": exc.remote_type},
            ) from exc

        bands = [
            RiskSimulationBandPoint(
                day=day,
                p05=(engine_result.percentile_paths[0][day]),
                p50=(engine_result.percentile_paths[1][day]),
                p95=(engine_result.percentile_paths[2][day]),
            )
            for day in range(params.horizon_days + 1)
        ]
        return RiskComputation(
            output=RiskSimulationOutput(
                process=params.process,
                sampling=params.sampling,
                horizon_days=params.horizon_days,
                paths=params.paths,
                drift_estimator=(RiskSimulationDriftEstimator.HISTORICAL_LOG_MLE),
                covariance_estimator=(RiskSimulationCovarianceEstimator.SAMPLE_LOG_RETURNS),
                aggregation_policy=(RiskCompositionPolicy.CURRENT_BUY_AND_HOLD),
                percentile_bands=bands,
                terminal_mean_return=(engine_result.terminal_mean_return),
                terminal_volatility=(engine_result.terminal_volatility),
                probability_of_loss=(engine_result.probability_of_loss),
            ),
            method=("quantlib_geometric_brownian_motion_" "historical_log_mle_sample_covariance"),
            n_observations=estimates.observations,
            seed=params.seed,
        )
