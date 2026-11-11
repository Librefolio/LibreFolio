"""Signal annotations: the line-crossover and threshold-crossing requests and the annotation they produce."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Dict, Literal, Optional, Union

from pydantic import Field, FiniteFloat, JsonValue, field_validator, model_validator

from backend.app.schemas.signals.base import _KEY_PATTERN, SignalModel, _inject_discriminator
from backend.app.schemas.signals.inputs import SignalValueSource
from backend.app.schemas.signals.vocabulary import SignalAnnotationDirection, SignalAnnotationSampling, SignalThresholdDirection
from backend.app.utils.json_utils import ensure_json_safe


class SignalAnnotationRequestBase(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    attach_to_instance_id: str = Field(..., min_length=1, max_length=128)
    observed_only: bool = False
    epsilon: FiniteFloat = Field(
        0.0,
        ge=0,
        description="Absolute numerical tolerance for equality/crossover detection.",
    )
    relative_epsilon: FiniteFloat = Field(
        0.0,
        ge=0,
        description="Scale-aware tolerance multiplied by max(abs(left), abs(right)).",
    )
    min_gap_days: int = Field(0, ge=0)
    limit: Optional[int] = Field(None, ge=1)
    sampling: SignalAnnotationSampling = SignalAnnotationSampling.RECENT


class SignalLineCrossoverRequest(SignalAnnotationRequestBase):
    kind: Literal["line_crossover"] = Field(json_schema_extra={"enum": ["line_crossover"]})
    left: SignalValueSource
    right: SignalValueSource

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(
            value,
            kind="line_crossover",
        )


class SignalThresholdCrossingRequest(SignalAnnotationRequestBase):
    kind: Literal["threshold_crossing"] = Field(json_schema_extra={"enum": ["threshold_crossing"]})
    source: SignalValueSource
    threshold: FiniteFloat
    direction: SignalThresholdDirection = SignalThresholdDirection.BOTH

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(
            value,
            kind="threshold_crossing",
        )


SignalAnnotationRequest = Annotated[
    Union[SignalLineCrossoverRequest, SignalThresholdCrossingRequest],
    Field(discriminator="kind"),
]


class SignalAnnotation(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    annotation_type: str = Field(..., min_length=1)
    date: date
    direction: Optional[SignalAnnotationDirection] = None
    values: Dict[str, FiniteFloat] = Field(..., min_length=1)
    metadata: Dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value: Any) -> Any:
        return ensure_json_safe(value, "metadata")
