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
    sampling_method: RiskSamplingStrategy = Field(
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
    path_count: int = Field(
        8192,
        ge=256,
        le=100_000,
        json_schema_extra={
            "x-i18n-key": "risk.params.paths",
            "x-control-order": 4,
            "x-step": 256,
        },
    )
    random_seed: int | None = Field(
        None,
        ge=0,
        le=2**32 - 1,
        json_schema_extra={
            "x-i18n-key": "risk.params.randomSeed",
            "x-control-order": 5,
            "x-step": 1,
            "x-visible-when": {"sampling_method": "mc"},
        },
    )
    sobol_start_index: int | None = Field(
        None,
        ge=0,
        le=2**32 - 1,
        json_schema_extra={
            "x-i18n-key": "risk.params.sobolStartIndex",
            "x-control-order": 5,
            "x-step": 1,
            "x-visible-when": {"sampling_method": "qmc"},
        },
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_contract(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)

        for legacy, canonical in (
            ("sampling", "sampling_method"),
            ("paths", "path_count"),
        ):
            if legacy not in data:
                continue
            legacy_value = data.pop(legacy)
            if canonical in data and data[canonical] != legacy_value:
                raise ValueError(f"{legacy} conflicts with {canonical}")
            data.setdefault(canonical, legacy_value)

        sampling = data.get("sampling_method", RiskSamplingStrategy.MC)
        sampling_value = sampling.value if isinstance(sampling, RiskSamplingStrategy) else sampling
        target = "sobol_start_index" if sampling_value == RiskSamplingStrategy.QMC.value else "random_seed"
        if "seed" in data:
            legacy_seed = data.pop("seed")
            if legacy_seed is not None:
                if target in data and data[target] != legacy_seed:
                    raise ValueError(f"seed conflicts with {target}")
                data.setdefault(target, legacy_seed)
        data.setdefault(target, 123456)
        return data

    @model_validator(mode="after")
    def validate_sampling(self) -> SimulationParams:
        if self.sampling_method == RiskSamplingStrategy.MC:
            if self.random_seed is None or self.sobol_start_index is not None:
                raise ValueError("MC simulation requires random_seed and forbids sobol_start_index")
        elif self.sobol_start_index is None or self.random_seed is not None:
            raise ValueError("QMC simulation requires sobol_start_index and forbids random_seed")
        if self.sampling_method == RiskSamplingStrategy.QMC and self.path_count & (self.path_count - 1):
            raise ValueError("QMC paths must be a power of two")
        return self


@register_plugin(RiskAnalyticRegistry)
class SimulationAnalytic(RiskAnalytic):
    analytic_code = "simulation"
    algorithm_version = "2.1.0-quantlib-1.43"
    name_i18n_key = "risk.analytics.simulation.name"
    description_i18n_key = "risk.analytics.simulation.description"
    output_kind = RiskOutputKind.SIMULATION
    supported_scopes = (
        RiskScopeKind.ASSET,
        RiskScopeKind.PORTFOLIO,
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
            sampling_method=params.sampling_method,
            asset_ids=list(estimates.asset_ids),
            annual_drifts=list(estimates.annual_drifts),
            annual_covariance=[list(row) for row in estimates.annual_covariance],
            weights=weights,
            cash_weight=cash_weight,
            horizon_days=params.horizon_days,
            path_count=params.path_count,
            random_seed=params.random_seed,
            sobol_start_index=params.sobol_start_index,
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
                sampling_method=params.sampling_method,
                horizon_days=params.horizon_days,
                path_count=params.path_count,
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
            sampling_method=params.sampling_method,
            path_count=params.path_count,
            random_seed=params.random_seed,
            sobol_start_index=params.sobol_start_index,
        )
