"""Signal schema base: the strict model, the decimal and text types, the shared patterns and validators."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from pydantic import AfterValidator, Field

from backend.app.schemas.common import StrictModel

_SIGNAL_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


_KEY_PATTERN = r"^[a-z][a-z0-9_.-]*$"


_SEMANTIC_ID_PATTERN = r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$"


_PRESCRIPTIVE_WORD_PATTERN = re.compile(
    r"(?<![A-Za-z])(?:buy|buys|buying|bought|sell|sells|selling|sold)(?![A-Za-z])",
    re.IGNORECASE,
)


def _finite_decimal(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("signal numeric values must be finite")
    return value


def _semantic_description(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("semantic_description must not be empty")
    if _PRESCRIPTIVE_WORD_PATTERN.search(normalized):
        raise ValueError("semantic_description must be neutral and non-prescriptive")
    return normalized


SignalDecimal = Annotated[Decimal, AfterValidator(_finite_decimal)]


SignalSemanticId = Annotated[str, Field(min_length=1, max_length=128, pattern=_SEMANTIC_ID_PATTERN)]


SignalSemanticDescription = Annotated[str, Field(min_length=1, max_length=300), AfterValidator(_semantic_description)]


NonNegativeInt = Annotated[int, Field(ge=0)]


def _ensure_unique(values: list[Any], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must not contain duplicates")


def _ensure_strictly_increasing(dates: list[date], label: str) -> None:
    if any(current >= following for current, following in zip(dates, dates[1:], strict=False)):
        raise ValueError(f"{label} dates must be strictly increasing and unique")


def _inject_discriminator(
    value: Any,
    *,
    kind: str,
) -> Any:
    if isinstance(value, dict) and "kind" not in value:
        return {
            **value,
            "kind": kind,
        }
    return value


class SignalModel(StrictModel):
    """Base for the signal payloads.

    Same story as ``AiExportModel``: it existed to carry
    ``ConfigDict(extra="forbid")``, which :class:`StrictModel` now provides. Kept
    as the family's named base.
    """
