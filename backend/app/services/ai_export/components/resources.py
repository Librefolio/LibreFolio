"""Shared typed resource contracts for AI Export domain component builders."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from types import MappingProxyType

from backend.app.schemas.portfolio import LotsAnalysisResponse, PortfolioReportResponse
from backend.app.schemas.prices import FAPriceQueryResult
from backend.app.services.ai_export.components.types import ResourceKey


@dataclass(frozen=True, slots=True)
class PriceResultsResource:
    """Bulk Asset price results indexed by asset ID without losing typed rows."""

    results: tuple[FAPriceQueryResult, ...]
    by_asset_id: Mapping[int, FAPriceQueryResult]

    @classmethod
    def from_results(cls, values: Sequence[FAPriceQueryResult]) -> PriceResultsResource:
        results = tuple(values)
        if any(not isinstance(value, FAPriceQueryResult) for value in results):
            raise TypeError("price results must contain FAPriceQueryResult values")
        by_asset_id = {result.asset_id: result for result in results}
        if len(by_asset_id) != len(results):
            raise ValueError("price results must contain unique asset IDs")
        return cls(results=results, by_asset_id=MappingProxyType(by_asset_id))


@dataclass(frozen=True, slots=True)
class LotsResultsResource:
    """LotsAnalysisService responses indexed by asset ID."""

    by_asset_id: Mapping[int, LotsAnalysisResponse]

    @classmethod
    def from_mapping(cls, values: Mapping[int, LotsAnalysisResponse]) -> LotsResultsResource:
        normalized: dict[int, LotsAnalysisResponse] = {}
        for asset_id, response in values.items():
            if isinstance(asset_id, bool) or not isinstance(asset_id, int) or asset_id < 1:
                raise ValueError("lots result asset IDs must be positive integers")
            if not isinstance(response, LotsAnalysisResponse):
                raise TypeError("lots results must contain LotsAnalysisResponse values")
            if response.asset_id != asset_id:
                raise ValueError("lots result mapping key must match response.asset_id")
            normalized[asset_id] = response
        return cls(by_asset_id=MappingProxyType(normalized))


@dataclass(frozen=True, slots=True)
class FxRateObservation:
    """One authoritative daily FX observation with effective-date provenance."""

    requested_date: date
    actual_date: date
    rate: Decimal
    backward_filled: bool

    def __post_init__(self) -> None:
        if type(self.requested_date) is not date or type(self.actual_date) is not date:
            raise TypeError("FX observation dates must be datetime.date values")
        if self.actual_date > self.requested_date:
            raise ValueError("actual_date must not be after requested_date")
        if not isinstance(self.rate, Decimal):
            raise TypeError("rate must be a Decimal")
        if not self.rate.is_finite() or self.rate <= 0:
            raise ValueError("rate must be finite and positive")


@dataclass(frozen=True, slots=True)
class FxRateSeriesResource:
    """Chronological, unique FX observations for one requested pair."""

    observations: tuple[FxRateObservation, ...]

    @classmethod
    def from_observations(cls, values: Sequence[FxRateObservation]) -> FxRateSeriesResource:
        observations = tuple(values)
        if any(not isinstance(value, FxRateObservation) for value in observations):
            raise TypeError("FX rate series must contain FxRateObservation values")
        dates = [value.requested_date for value in observations]
        if any(current >= following for current, following in zip(dates, dates[1:], strict=False)):
            raise ValueError("FX rate observations must be strictly increasing and unique")
        return cls(observations=observations)


PORTFOLIO_REPORT_RESOURCE = ResourceKey("portfolio.report", PortfolioReportResponse)
BROKER_REPORT_RESOURCE = ResourceKey("broker.report", PortfolioReportResponse)

PORTFOLIO_PRICE_RESULTS_RESOURCE = ResourceKey("portfolio.price_results", PriceResultsResource)
BROKER_PRICE_RESULTS_RESOURCE = ResourceKey("broker.price_results", PriceResultsResource)
ASSET_PRICE_RESULTS_RESOURCE = ResourceKey("asset.price_results", PriceResultsResource)

PORTFOLIO_LOTS_RESULTS_RESOURCE = ResourceKey("portfolio.lots_results", LotsResultsResource)
BROKER_LOTS_RESULTS_RESOURCE = ResourceKey("broker.lots_results", LotsResultsResource)
ASSET_LOTS_RESULTS_RESOURCE = ResourceKey("asset.lots_results", LotsResultsResource)

FX_RATE_SERIES_RESOURCE = ResourceKey("fx.rate_series", FxRateSeriesResource)


__all__ = [
    "ASSET_LOTS_RESULTS_RESOURCE",
    "ASSET_PRICE_RESULTS_RESOURCE",
    "BROKER_LOTS_RESULTS_RESOURCE",
    "BROKER_PRICE_RESULTS_RESOURCE",
    "BROKER_REPORT_RESOURCE",
    "FX_RATE_SERIES_RESOURCE",
    "PORTFOLIO_LOTS_RESULTS_RESOURCE",
    "PORTFOLIO_PRICE_RESULTS_RESOURCE",
    "PORTFOLIO_REPORT_RESOURCE",
    "FxRateObservation",
    "FxRateSeriesResource",
    "LotsResultsResource",
    "PriceResultsResource",
]
