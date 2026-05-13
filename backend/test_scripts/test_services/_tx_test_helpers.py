"""
Test helpers that adapt `TransactionService.execute_batch` to the legacy
create_bulk / update_bulk / delete_bulk interface used extensively in existing
service-level tests.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import List, Optional

from backend.app.schemas.transactions import TXCreateItem, TXUpdateItem
from backend.app.services.transaction_service import TransactionService


async def create_bulk(
    service: TransactionService,
    items: List[TXCreateItem],
    user_id: Optional[int] = None,
) -> SimpleNamespace:
    """Wrap execute_batch for create-only calls, returning legacy-compatible response."""
    raw = [item.model_dump(mode="json") for item in items]
    resp = await service.execute_batch(
        creates_raw=raw,
        updates_raw=[],
        deletes=[],
        user_id=user_id,
        commit=True,
    )

    # Build per-index result map from resp.results
    result_by_idx = {}
    for r in resp.results or []:
        result_by_idx[r.index] = r

    # Build per-index issue map
    issue_by_idx = {}
    for iss in resp.issues:
        if iss.operation == "create":
            issue_by_idx.setdefault(iss.index, iss)

    legacy_results = []
    for idx, item_orig in enumerate(items):
        r = result_by_idx.get(idx)
        iss = issue_by_idx.get(idx)
        if r and r.status == "success" and not resp.issues:
            legacy_results.append(
                SimpleNamespace(
                    success=True,
                    status="success",
                    transaction_id=r.id,
                    link_uuid=r.link_uuid,
                    error=None,
                )
            )
        elif iss:
            legacy_results.append(
                SimpleNamespace(
                    success=False,
                    status="failed",
                    transaction_id=None,
                    link_uuid=item_orig.link_uuid,
                    error=iss.error,
                )
            )
        elif r:
            legacy_results.append(
                SimpleNamespace(
                    success=False,
                    status="simulated",
                    transaction_id=r.id,
                    link_uuid=r.link_uuid,
                    error=None,
                )
            )
        else:
            legacy_results.append(
                SimpleNamespace(
                    success=False,
                    status="not_attempted",
                    transaction_id=None,
                    link_uuid=getattr(item_orig, "link_uuid", None),
                    error=None,
                )
            )

    return SimpleNamespace(
        success_count=sum(1 for r in legacy_results if r.success),
        results=legacy_results,
        errors=[iss.error for iss in resp.issues],
        rolled_back=bool(resp.issues),
    )


async def update_bulk(
    service: TransactionService,
    items: List[TXUpdateItem],
    user_id: Optional[int] = None,
) -> SimpleNamespace:
    """Wrap execute_batch for update-only calls, returning legacy-compatible response."""
    raw = [item.model_dump(mode="json") for item in items]
    resp = await service.execute_batch(
        creates_raw=[],
        updates_raw=raw,
        deletes=[],
        user_id=user_id,
        commit=True,
    )

    result_by_idx = {}
    for r in resp.results or []:
        result_by_idx[r.index] = r

    issue_by_idx = {}
    for iss in resp.issues:
        if iss.operation == "update":
            issue_by_idx.setdefault(iss.index, iss)

    legacy_results = []
    for idx, item_orig in enumerate(items):
        r = result_by_idx.get(idx)
        iss = issue_by_idx.get(idx)
        if r and r.status == "success" and not resp.issues:
            legacy_results.append(
                SimpleNamespace(
                    id=r.id or item_orig.id,
                    success=True,
                    status="success",
                    error=None,
                )
            )
        elif iss:
            legacy_results.append(
                SimpleNamespace(
                    id=item_orig.id,
                    success=False,
                    status="failed",
                    error=iss.error,
                )
            )
        elif r:
            legacy_results.append(
                SimpleNamespace(
                    id=r.id or item_orig.id,
                    success=False,
                    status="simulated",
                    error=None,
                )
            )
        else:
            legacy_results.append(
                SimpleNamespace(
                    id=item_orig.id,
                    success=False,
                    status="not_attempted",
                    error=None,
                )
            )

    return SimpleNamespace(
        success_count=sum(1 for r in legacy_results if r.success),
        results=legacy_results,
        errors=[iss.error for iss in resp.issues],
        rolled_back=bool(resp.issues),
    )


async def delete_bulk(
    service: TransactionService,
    ids: List[int],
    user_id: Optional[int] = None,
) -> SimpleNamespace:
    """Wrap execute_batch for delete-only calls, returning legacy-compatible response."""
    resp = await service.execute_batch(
        creates_raw=[],
        updates_raw=[],
        deletes=ids,
        user_id=user_id,
        commit=True,
    )

    result_by_idx = {}
    for r in resp.results or []:
        result_by_idx[r.index] = r

    issue_by_idx = {}
    for iss in resp.issues:
        if iss.operation == "delete":
            issue_by_idx.setdefault(iss.index, iss)

    legacy_results = []
    for idx, tx_id in enumerate(ids):
        r = result_by_idx.get(idx)
        iss = issue_by_idx.get(idx)
        if r and r.status == "success" and not resp.issues:
            legacy_results.append(
                SimpleNamespace(
                    id=r.id or tx_id,
                    success=True,
                    deleted_count=1,
                    status="success",
                    message=None,
                )
            )
        elif iss:
            legacy_results.append(
                SimpleNamespace(
                    id=tx_id,
                    success=False,
                    deleted_count=0,
                    status="failed",
                    message=iss.error,
                )
            )
        else:
            legacy_results.append(
                SimpleNamespace(
                    id=tx_id,
                    success=False,
                    deleted_count=0,
                    status="not_attempted",
                    message=None,
                )
            )

    success_count = sum(1 for r in legacy_results if r.success)
    return SimpleNamespace(
        success_count=success_count,
        total_deleted=success_count,
        results=legacy_results,
        errors=[iss.error for iss in resp.issues],
        rolled_back=bool(resp.issues),
    )
