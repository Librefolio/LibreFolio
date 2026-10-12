"""Income eligibility of FIFO fragments: the quantity a lot held on the record date of an income event."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Sequence

from backend.app.services.financial_math.fifo.models import FragmentInterval


def eligible_income_quantity(
    fragments: Sequence[FragmentInterval],
    broker_id: int,
    cutoff: date,
) -> Decimal:
    """Return LONG quantity attributable to a paying broker at end of ``cutoff``.

    Broker-custodied fragments count for their broker. In-transit fragments
    count for their source broker, never the destination before arrival.
    This is the canonical D-1 eligibility seam shared by FIFO allocation and
    transaction-ledger Yield on Cost.
    """
    total = Decimal("0")
    for fragment in fragments:
        if fragment.direction != "LONG":
            continue
        if not (fragment.start_date <= cutoff and (fragment.end_date is None or cutoff < fragment.end_date)):
            continue
        if fragment.custody_type == "BROKER" and fragment.broker_id == broker_id:
            total += fragment.quantity
        elif fragment.custody_type == "IN_TRANSIT" and fragment.source_broker_id == broker_id:
            total += fragment.quantity
    return total
