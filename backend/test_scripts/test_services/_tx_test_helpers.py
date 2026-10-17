"""
Test helpers that adapt `TransactionService.execute_batch` to the legacy
create_bulk / update_bulk / delete_bulk interface used extensively in existing
service-level tests.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import SimpleNamespace
from typing import List, Optional

from backend.app.schemas.transactions.batch import TXBatchResponse, TXValidationIssue
from backend.app.schemas.transactions.transactions import TXCreateItem, TXUpdateItem
from backend.app.services.transactions.transaction_service import TransactionService

# =============================================================================
# R13-SEC7-3 — A SPY ON WHAT A SERVICE HANDS THE BATCH
# =============================================================================

#: A raw decimal at least this long reached the batch expanded (``format(v, "f")``): the short form (``str(v)``) of
#: every value the R13-SEC7-3 tests send is a dozen characters.
RAW_DECIMAL_MAX_CHARS = 64
#: The decimal fields of a raw create, as paths into its dict.
RAW_DECIMAL_PATHS = (("quantity",), ("cash", "amount"), ("cost_basis_override", "amount"))


@dataclass
class BatchCall:
    """One call of ``TransactionService.execute_batch`` the spy saw: the raw creates it received, and the real batch's
    response when the spy handed them on (None when it did not)."""

    creates_raw: list
    response: Optional[TXBatchResponse] = None


def raw_decimals(creates_raw: list) -> list[tuple[int, str, str]]:
    """Every decimal value of the raw creates as ``(create index, dotted path, the value as a string)``."""
    found: list[tuple[int, str, str]] = []
    for index, raw in enumerate(creates_raw):
        for path in RAW_DECIMAL_PATHS:
            value = raw
            for key in path:
                value = value.get(key) if isinstance(value, dict) else None
            if value is not None:
                found.append((index, ".".join(path), value if isinstance(value, str) else str(value)))
    return found


def expanded_raw_decimals(call: BatchCall) -> list[tuple[int, str, int, str]]:
    """The raw decimals of ``call`` at least ``RAW_DECIMAL_MAX_CHARS`` long, as ``(index, path, length, first 16
    characters)``: what a failure message may print, never the value itself."""
    return [(index, path, len(raw), raw[:16]) for index, path, raw in raw_decimals(call.creates_raw) if len(raw) >= RAW_DECIMAL_MAX_CHARS]


def spy_on_execute_batch(monkeypatch) -> list[BatchCall]:
    """Replace ``TransactionService.execute_batch`` with a spy for the rest of the test; the list of its calls.

    Each call records its ``creates_raw``. When every raw decimal is short the real batch runs, and its response is
    recorded; an expanded value is never handed on — the red is the expansion itself, not what the batch would make of
    megabytes — and the spy answers a refusal of its own instead.
    """
    original = TransactionService.execute_batch
    signature = inspect.signature(original)
    calls: list[BatchCall] = []

    async def spy(self, *args, **kwargs):
        arguments = signature.bind(self, *args, **kwargs).arguments
        call = BatchCall(creates_raw=list(arguments.get("creates_raw") or []))
        calls.append(call)
        if expanded_raw_decimals(call):
            return TXBatchResponse(committed=False, issues=[TXValidationIssue(operation="create", index=-1, error="R13-SEC7-3 spy: an expanded value reached execute_batch, not handed on")], results=[], success_count=0)
        call.response = await original(self, *args, **kwargs)
        return call.response

    monkeypatch.setattr(TransactionService, "execute_batch", spy)
    return calls


async def create_bulk(
    service: TransactionService,
    items: List[TXCreateItem],
    user_id: Optional[int] = None,
) -> SimpleNamespace:
    """Wrap execute_batch for create-only calls, returning legacy-compatible response."""
    # model_dump → raw dict: execute_batch(creates_raw=...) re-validates per-row
    # inside try/except, collecting ALL errors instead of failing on the first.
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
                    transaction_id=r.ids[0] if r.ids else None,
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
                    transaction_id=r.ids[0] if r.ids else None,
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
    # model_dump → raw dict: same rationale as create_bulk (batch error collection).
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
                    id=(r.ids[0] if r.ids else None) or item_orig.id,
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
                    id=(r.ids[0] if r.ids else None) or item_orig.id,
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
                    id=(r.ids[0] if r.ids else None) or tx_id,
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
