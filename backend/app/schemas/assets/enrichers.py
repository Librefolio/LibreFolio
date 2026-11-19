"""The enrichers of an asset (FA, plan 68 §3.1, B3): the bindings, their last reads, the installed enrichers.

- ``FAEnricherBinding``: how one enricher names one asset, the object stored under its code in
  ``asset_enrichers.config``: ``identifier_type`` and ``identifier``, plus the free keys that only that plugin reads
  (Borsa Italiana's ``mic`` and ``platform``).
- ``FAAssetEnrichers``: an asset's ``config`` (code → binding; **the order of the keys is the priority**, kept as sent)
  and ``state`` (code → its last read and outcome, written only by the reads).
- ``FAEnricherInfo`` and ``FAEnrichersCatalogue``: what ``GET /assets/enrichers`` answers.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.db.models import AssetType
from backend.app.schemas.common import StrictModel

#: An enricher code: the key of a binding in ``config``.
ENRICHER_CODE = re.compile(r"[a-z][a-z0-9_]{0,63}")


def check_enricher_codes(bindings: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The bindings, refused when a key is not an enricher code. A code not installed is accepted: a binding to an
    enricher turned off or removed stays on the asset (plan B2)."""
    if bindings is not None:
        wrong = [code for code in bindings if not ENRICHER_CODE.fullmatch(code)]
        if wrong:
            raise ValueError(f"not enricher codes: {', '.join(sorted(wrong))}")
    return bindings


class FAEnricherBinding(BaseModel):
    """How one enricher names one asset. Free keys besides the two below belong to that plugin and are kept as sent."""

    model_config = ConfigDict(extra="allow")

    identifier_type: str = Field(..., min_length=1, max_length=32, description="The type of the identifier (ISIN, TICKER, LEI…)")
    identifier: str = Field(..., min_length=1, max_length=256, description="How the enricher names the asset")


class FAAssetEnrichers(StrictModel):
    """An asset's enrichers: the bindings in their order (the priority) and what each one last read."""

    config: Dict[str, FAEnricherBinding] = Field(default_factory=dict, description="Enricher code → binding; the order of the keys is the priority")
    state: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Enricher code → its last read and outcome")
    updated_at: Optional[datetime] = Field(None, description="Last change of the row")


class FAEnricherInfo(StrictModel):
    """One installed enricher and what it declares (plan §3.3)."""

    code: str
    name: str
    icon: Optional[str] = None
    help_url: Optional[str] = None
    terms: str = Field(..., description="The class of the source's terms of use: open, price_source, self_hosted, personal_file")
    accepted_identifier_types: List[str]
    params_schema: List[Dict[str, Any]] = Field(default_factory=list)
    supports_search: bool = False
    voices: Dict[AssetType, List[str]] = Field(default_factory=dict, description="Per asset type, the voices it can fill")
    default_priority: Dict[AssetType, Optional[int]] = Field(..., description="Per asset type, its degree (lower first); null for a type it does not cover")
    configured: bool = Field(True, description="False when a required setting of the enricher has no value: every read, test and search would answer NOT_CONFIGURED (plan 68, B2; the rule of plan 76, N1). The enrichers' window draws it off, with «Configure»")
    missing_settings: List[str] = Field(default_factory=list, description="The settings to set, as the NOT_CONFIGURED refusal names them: in the managed profile a field an environment variable locks is never named (decision N2)")


class FAEnrichersCatalogue(StrictModel):
    """``GET /assets/enrichers``: the installed enrichers, and per asset type their default order."""

    enrichers: List[FAEnricherInfo]
    default_order: Dict[AssetType, List[str]] = Field(..., description="Per asset type, the codes of the enrichers that cover it: by degree, then by code")


class FAEnricherRecognizeRequest(StrictModel):
    """``POST /assets/enrichers/recognize``: «recognize» in cascade from the identifiers known (plan B4), also before
    the asset exists."""

    asset_type: AssetType = Field(..., description="The asset's type: only the enrichers that cover it are asked")
    identifiers: Dict[str, str] = Field(..., min_length=1, description="Type → value of the identifiers known (ISIN, LEI, TICKER…)")
    price_provider_code: Optional[str] = Field(None, description="The asset's price provider: at equal degree its enricher comes first in the order")
    codes: Optional[List[str]] = Field(None, description="Only these enrichers; all installed when absent")


class FAEnricherRecognition(StrictModel):
    """What one enricher answered for one binding."""

    code: str
    identifier_type: str
    identifier: str
    status: str = Field(..., description="found, not_found, conflict (it names an identifier different from one already known), error")
    name: Optional[str] = None
    page_url: Optional[str] = None
    identifiers: Dict[str, str] = Field(default_factory=dict, description="The other identifiers it knows")
    conflicts: Dict[str, str] = Field(default_factory=dict, description="On a conflict: type → the value it named")
    error: Optional[str] = None


class FAEnricherSearchResult(StrictModel):
    """One result of an enricher's search: what fills a binding."""

    name: str
    binding: FAEnricherBinding
    asset_type: Optional[AssetType] = None
    page_url: Optional[str] = None


class FAEnricherTestRequest(StrictModel):
    """``POST /assets/enrichers/{code}/test``: «recognize» one binding, as the E7 window's «test» does."""

    binding: FAEnricherBinding
