"""Conditional simulation by historical resampling or correlated GBM."""

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
    RiskSimulationRegime,
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
    align_simple_returns,
    estimate_drift_uncertainty,
    estimate_gbm_parameters,
    historical_returns_digest,
    run_simulation,
)
from backend.app.services.risk.quant.spawn_worker import (
    SpawnWorkerQueueFullError,
    SpawnWorkerRemoteError,
    SpawnWorkerTimeoutError,
)

_DEFAULT_SEED = 123456


class SimulationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process: RiskSimulationProcess = RiskSimulationProcess.BLOCK_BOOTSTRAP
    regime: RiskSimulationRegime = RiskSimulationRegime.NONE
    sampling_method: RiskSamplingStrategy = RiskSamplingStrategy.MC
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
    random_seed: int | None = Field(None, ge=0, le=2**32 - 1)
    sobol_start_index: int | None = Field(None, ge=0, le=2**32 - 1)
    bootstrap_seed: int | None = Field(None, ge=0, le=2**32 - 1)
    block_length_days: int | None = Field(None, ge=1, le=5_000)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_contract(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        legacy_aliases = {"sampling", "paths", "seed"} & set(data)

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
        data.setdefault("process", cls._infer_process(data, sampling_value, bool(legacy_aliases)))
        process = data["process"]
        process_value = process.value if isinstance(process, RiskSimulationProcess) else process

        if process_value == RiskSimulationProcess.BLOCK_BOOTSTRAP.value:
            target = "bootstrap_seed"
        else:
            target = "sobol_start_index" if sampling_value == RiskSamplingStrategy.QMC.value else "random_seed"
        if "seed" in data:
            legacy_seed = data.pop("seed")
            if legacy_seed is not None:
                if target in data and data[target] != legacy_seed:
                    raise ValueError(f"seed conflicts with {target}")
                data.setdefault(target, legacy_seed)
        data.setdefault(target, _DEFAULT_SEED)
        return data

    @staticmethod
    def _infer_process(data: dict, sampling_value, from_legacy_payload: bool) -> str:
        """Keep every caller that predates the resampler on the parametric engine.

        Quasi-random sampling and both parametric seeds are meaningless for a
        resampler, so naming one identifies GBM unambiguously.

        A legacy alias identifies it just as surely. When ``sampling``,
        ``paths`` and ``seed`` were minted, GBM was the only engine, so a
        client still using those names also still renders the result under the
        old labels — a fixed "assumptions" line that describes a lognormal
        process. Answering it with resampled paths would put honest numbers
        under a caption that misdescribes them, which is worse than answering
        with the model its UI actually claims. New clients send the canonical
        field names and land on the new default.
        """
        if from_legacy_payload:
            return RiskSimulationProcess.GBM.value
        if sampling_value == RiskSamplingStrategy.QMC.value:
            return RiskSimulationProcess.GBM.value
        if data.get("random_seed") is not None or data.get("sobol_start_index") is not None:
            return RiskSimulationProcess.GBM.value
        return RiskSimulationProcess.BLOCK_BOOTSTRAP.value

    @model_validator(mode="after")
    def validate_engine_contract(self) -> SimulationParams:
        if self.process == RiskSimulationProcess.BLOCK_BOOTSTRAP:
            self._validate_bootstrap_params()
        else:
            self._validate_parametric_params()
        return self

    def _validate_bootstrap_params(self) -> None:
        if self.sampling_method != RiskSamplingStrategy.MC:
            raise ValueError("block bootstrap resampling is pseudo-random and requires mc sampling")
        if self.random_seed is not None or self.sobol_start_index is not None:
            raise ValueError("block bootstrap forbids random_seed and sobol_start_index")
        if self.bootstrap_seed is None:
            raise ValueError("block bootstrap requires bootstrap_seed")

    def _validate_parametric_params(self) -> None:
        if self.regime != RiskSimulationRegime.NONE:
            raise ValueError("prescribed regimes require the block bootstrap process")
        if self.bootstrap_seed is not None or self.block_length_days is not None:
            raise ValueError("bootstrap_seed and block_length_days are meaningful only for block bootstrap")
        if self.sampling_method == RiskSamplingStrategy.MC:
            if self.random_seed is None or self.sobol_start_index is not None:
                raise ValueError("MC simulation requires random_seed and forbids sobol_start_index")
            return
        if self.sobol_start_index is None or self.random_seed is not None:
            raise ValueError("QMC simulation requires sobol_start_index and forbids random_seed")
        if self.path_count & (self.path_count - 1):
            raise ValueError("QMC paths must be a power of two")


@register_plugin(RiskAnalyticRegistry)
class SimulationAnalytic(RiskAnalytic):
    analytic_code = "simulation"
    algorithm_version = "3.0.0-bootstrap-quantlib-1.43"
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

        if params.process == RiskSimulationProcess.BLOCK_BOOTSTRAP:
            engine_request, observations = self._build_bootstrap_request(
                params,
                returns_by_asset,
                asset_ids,
                weights,
                cash_weight,
            )
        else:
            engine_request, observations = self._build_parametric_request(
                params,
                returns_by_asset,
                weights,
                cash_weight,
                annualization_factor=context.annualization_factor,
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
            raise RiskUnavailableError(
                str(exc),
                code=self._remote_error_code(params, exc.remote_type),
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
        bootstrapped = params.process == RiskSimulationProcess.BLOCK_BOOTSTRAP
        drift_uncertainty = self._drift_uncertainty(
            returns_by_asset,
            asset_ids,
            weights,
            params.horizon_days,
        )
        return RiskComputation(
            output=RiskSimulationOutput(
                process=params.process,
                regime=params.regime,
                sampling_method=params.sampling_method,
                horizon_days=params.horizon_days,
                path_count=params.path_count,
                block_length_days=engine_result.block_length_days,
                regime_declared_days=engine_result.regime_declared_days,
                regime_applied_days=engine_result.regime_applied_days,
                drift_estimator=(RiskSimulationDriftEstimator.EMPIRICAL_RESAMPLED if bootstrapped else RiskSimulationDriftEstimator.HISTORICAL_LOG_MLE),
                covariance_estimator=(RiskSimulationCovarianceEstimator.NOT_ESTIMATED_JOINT_RESAMPLING if bootstrapped else RiskSimulationCovarianceEstimator.SAMPLE_LOG_RETURNS),
                aggregation_policy=(RiskCompositionPolicy.CURRENT_BUY_AND_HOLD),
                percentile_bands=bands,
                terminal_mean_return=(engine_result.terminal_mean_return),
                terminal_volatility=(engine_result.terminal_volatility),
                probability_of_loss=(engine_result.probability_of_loss),
                drift_uncertainty_factor=(drift_uncertainty[0] if drift_uncertainty else None),
                drift_uncertainty_observations=(drift_uncertainty[1] if drift_uncertainty else None),
            ),
            method=self._method_label(params),
            n_observations=observations,
            sampling_method=params.sampling_method,
            path_count=params.path_count,
            random_seed=params.random_seed,
            sobol_start_index=params.sobol_start_index,
            bootstrap_seed=params.bootstrap_seed,
        )

    @staticmethod
    def _remote_error_code(params: SimulationParams, remote_type: str) -> RiskErrorCode:
        """Name the failure the engine actually had.

        The parametric path rejects a covariance it cannot use. The bootstrap
        has no covariance to reject: a refusal there means the return history
        itself was unusable, and calling that "invalid covariance" would send
        the user looking for a matrix that was never built.
        """
        if not remote_type.endswith("ValueError"):
            return RiskErrorCode.EXECUTION_FAILED
        if params.process == RiskSimulationProcess.BLOCK_BOOTSTRAP:
            return RiskErrorCode.DATA_UNAVAILABLE
        return RiskErrorCode.INVALID_COVARIANCE

    @staticmethod
    def _method_label(params: SimulationParams) -> str:
        if params.process != RiskSimulationProcess.BLOCK_BOOTSTRAP:
            return "quantlib_geometric_brownian_motion_historical_log_mle_sample_covariance"
        if params.regime == RiskSimulationRegime.NONE:
            return "numpy_joint_block_bootstrap_empirical_resampling"
        return f"numpy_joint_block_bootstrap_prescribed_{params.regime.value}"

    @staticmethod
    def _drift_uncertainty(
        returns_by_asset,
        asset_ids,
        weights,
        horizon_days: int,
    ) -> tuple[float, int] | None:
        """Qualify the band with the drift's own standard error, or disclose nothing.

        Narrow on purpose: only the estimator's documented ValueError degrades to an
        absent disclosure, because by this point the engine has already run on these
        same returns. A broader catch would turn a coding fault into a missing field,
        which reads exactly like a simulation that had nothing to disclose.
        """
        try:
            return estimate_drift_uncertainty(
                returns_by_asset,
                asset_ids,
                weights,
                horizon_days=horizon_days,
            )
        except ValueError:
            return None

    @staticmethod
    def _build_bootstrap_request(
        params: SimulationParams,
        returns_by_asset,
        asset_ids,
        weights,
        cash_weight,
    ) -> tuple[SimulationEngineRequest, int]:
        """Carry the real history across the boundary, and nothing estimated."""
        matrix = align_simple_returns(returns_by_asset, asset_ids)
        request = SimulationEngineRequest(
            process=RiskSimulationProcess.BLOCK_BOOTSTRAP,
            regime=params.regime,
            sampling_method=RiskSamplingStrategy.MC,
            asset_ids=list(asset_ids),
            historical_returns=matrix.tolist(),
            historical_digest=historical_returns_digest(matrix),
            block_length_days=params.block_length_days,
            bootstrap_seed=params.bootstrap_seed,
            weights=weights,
            cash_weight=cash_weight,
            horizon_days=params.horizon_days,
            path_count=params.path_count,
        )
        return request, int(matrix.shape[0])

    @staticmethod
    def _build_parametric_request(
        params: SimulationParams,
        returns_by_asset,
        weights,
        cash_weight,
        *,
        annualization_factor: float,
    ) -> tuple[SimulationEngineRequest, int]:
        estimates = estimate_gbm_parameters(
            returns_by_asset,
            annualization_factor=annualization_factor,
        )
        request = SimulationEngineRequest(
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
        return request, estimates.observations
