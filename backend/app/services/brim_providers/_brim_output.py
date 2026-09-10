"""Shared helpers for schema-aware BRIM parse output."""

from __future__ import annotations

from typing import Dict, Sequence

from backend.app.schemas.brim import BRIMAssetNotice, BRIMExtractedAssetInfo
from backend.app.services.brim_providers import _brim_io as io


def attach_maturity_notices(
    transactions: Sequence[object],
    extracted_assets: Dict[int, BRIMExtractedAssetInfo],
    *,
    reason: str,
) -> None:
    """Attach a provider-localized maturity advisory to affected assets."""
    for asset_id, indexes in io.detect_maturity_hits(transactions).items():
        info = extracted_assets.get(asset_id)
        if info is not None:
            info.notices.append(
                BRIMAssetNotice(
                    kind=io.MATURITY_NOTICE_KIND,
                    reason=reason,
                    transaction_indexes=indexes,
                )
            )
