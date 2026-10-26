"""Cross-record checks of ``TransactionService``: event links, cost basis requirement, linked-pair rules."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AssetEvent, Transaction, TransactionType
from backend.app.schemas.transactions.batch import TXValidationCode
from backend.app.schemas.transactions.type_metadata import cost_basis_required


class TransactionValidationMixin:
    """Cross-record checks: the link to an asset event, the rows that need a cost basis, the rules of a linked pair.

    Mixed into ``TransactionService`` (``transaction_service.py``), which provides ``session``.
    """

    session: AsyncSession

    # =========================================================================
    # CROSS-RECORD VALIDATION HELPERS
    # =========================================================================

    async def _validate_asset_event_link(self, asset_event_id: int, expected_asset_id: int) -> None:
        """Verify the referenced AssetEvent exists and belongs to expected_asset_id."""
        event = await self.session.get(AssetEvent, asset_event_id)
        if event is None:
            raise ValueError(f"asset_event_id={asset_event_id} not found")
        if event.asset_id != expected_asset_id:
            raise ValueError(f"asset_event_id={asset_event_id} belongs to asset {event.asset_id}, not {expected_asset_id}")

    @staticmethod
    def _requires_cost_basis(tx: Transaction) -> bool:
        """True if this Transaction's type and quantity require ``cost_basis_override``: the rule of ``TX_TYPE_METADATA``."""
        return cost_basis_required(tx.type, tx.quantity)

    @staticmethod
    def _validate_linked_pair(a: Transaction, b: Transaction) -> Optional[tuple[str, str, dict]]:
        """
        Validate semantic coherence of a linked pair (Block H.1).

        Rules:
        - Both items must share the same `type` (no mixing e.g. TRANSFER + SELL).
        - Two ADJUSTMENTs cannot be linked (the developer's decision, 22/10/2026: protect the entry of data): a move of units
          between brokers is a TRANSFER. Pairs of ADJUSTMENTs already stored are never judged or changed.
        - TRANSFER requires distinct brokers (same-broker TRANSFER is a no-op), one
          asset, and exactly opposite quantities: what leaves one broker arrives at
          the other, no unit is created or lost.
        - FX_CONVERSION requires both legs on one broker (a multi-currency account): ``broker_id`` is ``equal`` in
          ``TX_TYPE_METADATA``, as the form, the promotion and the imports write it (W-B17).
        - CASH_TRANSFER requires distinct brokers (same-broker is a no-op).

        Returns None when the pair is valid, otherwise a tuple of
        (error_message, code, params).
        """
        if a.type != b.type:
            return (
                f"linked pair must share the same type (got {a.type.value} + {b.type.value})",
                "pairTypeMismatch",
                {"typeA": a.type.value, "typeB": b.type.value},
            )
        if a.type == TransactionType.ADJUSTMENT:
            return (
                "two Adjustments cannot be linked: use an Asset Transfer to move units between brokers",
                "pairAdjustmentNotAllowed",
                {"type": a.type.value},
            )
        if a.type == TransactionType.TRANSFER and a.broker_id == b.broker_id:
            return (
                f"TRANSFER requires distinct brokers (both on broker {a.broker_id})",
                "pairSameBroker",
                {"brokerId": a.broker_id},
            )
        if a.type == TransactionType.TRANSFER and a.asset_id != b.asset_id:
            return (
                f"TRANSFER pair must move one asset (got assets {a.asset_id} and {b.asset_id})",
                "pairAssetMismatch",
                {"assetA": a.asset_id, "assetB": b.asset_id},
            )
        if a.type == TransactionType.TRANSFER and (a.quantity is None or b.quantity is None or a.quantity != -b.quantity):
            return (
                f"TRANSFER pair must move the same quantity out and in (got {a.quantity} and {b.quantity})",
                "pairQuantityMismatch",
                {"qtyA": str(a.quantity), "qtyB": str(b.quantity)},
            )
        if a.type == TransactionType.CASH_TRANSFER and a.broker_id == b.broker_id:
            return (
                f"CASH_TRANSFER requires distinct brokers (both on broker {a.broker_id})",
                "pairSameBroker",
                {"brokerId": a.broker_id},
            )
        if a.type == TransactionType.FX_CONVERSION and a.broker_id != b.broker_id:
            return (
                f"FX_CONVERSION requires both legs on one broker (got brokers {a.broker_id} and {b.broker_id})",
                "pairBrokerMismatch",
                {"brokerA": a.broker_id, "brokerB": b.broker_id},
            )
        return None

    @staticmethod
    def _pair_order_warning(a: Transaction, b: Transaction) -> Optional[tuple[str, str, dict]]:
        """A linked TRANSFER or CASH_TRANSFER whose arrival is dated before its departure (B2).

        A remark, never a refusal and never a correction: the pair is saved as sent. The departure is the leg that gives
        (a negative quantity, or a negative amount for cash), the arrival the one that receives. Equal dates are in order,
        and so is every other type of pair.

        Returns None when the pair is in order, otherwise (message, code, params).
        """
        if a.type != b.type or a.type not in (TransactionType.TRANSFER, TransactionType.CASH_TRANSFER):
            return None
        key = "quantity" if a.type == TransactionType.TRANSFER else "amount"
        value_a, value_b = getattr(a, key), getattr(b, key)
        if value_a is None or value_b is None or value_a == value_b:
            return None
        departure, arrival = (a, b) if value_a < value_b else (b, a)
        if arrival.date >= departure.date:
            return None
        return (
            f"the arrival ({arrival.date.isoformat()}) is dated before the departure ({departure.date.isoformat()})",
            TXValidationCode.PAIR_ARRIVAL_BEFORE_DEPARTURE.value,
            {"departureDate": departure.date.isoformat(), "arrivalDate": arrival.date.isoformat()},
        )

    @staticmethod
    def _validate_pair_description_tags(a: Transaction, b: Transaction) -> Optional[tuple[str, str, dict]]:
        """Validate that a linked pair has identical description and tags.

        Returns None when consistent, otherwise (error_message, code, params).
        """
        # Normalize None to "" for comparison
        desc_a = a.description or ""
        desc_b = b.description or ""
        if desc_a != desc_b:
            return (
                "Linked pair must have identical description",
                "pairDescriptionMismatch",
                {"descA": desc_a[:50], "descB": desc_b[:50]},
            )
        # Tags are stored as CSV strings; normalize None to ""
        tags_a = a.tags or ""
        tags_b = b.tags or ""
        if tags_a != tags_b:
            return (
                "Linked pair must have identical tags",
                "pairTagsMismatch",
                {"tagsA": tags_a, "tagsB": tags_b},
            )
        return None
