"""
Date sentinel resolution utility.

Resolves "min" / "max" sentinel values in OpenDateRangeModel to concrete dates
by querying the user's accessible transaction history.

Usage:
    resolved = await resolve_date_sentinels(date_range, user_id, session)
"""

from datetime import date as date_type

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import BrokerUserAccess, Transaction
from backend.app.schemas.common import OpenDateRangeModel


async def resolve_date_sentinels(
    date_range: OpenDateRangeModel | None,
    user_id: int,
    session: AsyncSession,
    *,
    broker_ids: list[int] | None = None,
) -> OpenDateRangeModel | None:
    """Resolve "min"/"max" sentinels to real dates.

    If date_range is None or has no sentinels, returns it unchanged.
    Resolution queries the Transaction table scoped to the user's
    accessible brokers (via BrokerUserAccess).

    Args:
        date_range: The OpenDateRangeModel (may contain "min"/"max" strings).
        user_id: Current user's ID.
        session: Async SQLAlchemy session.
        broker_ids: Optional broker filter (restricts which transactions to consider).

    Returns:
        A new OpenDateRangeModel with concrete dates, or None.
    """
    if date_range is None:
        return None

    if not date_range.has_sentinels():
        return date_range

    # Get user's accessible broker IDs
    accessible_brokers_stmt = select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id)
    if broker_ids:
        accessible_brokers_stmt = accessible_brokers_stmt.where(BrokerUserAccess.broker_id.in_(broker_ids))

    # Query min/max transaction dates for accessible brokers
    stmt = select(
        func.min(Transaction.date).label("min_date"),
        func.max(Transaction.date).label("max_date"),
    ).where(Transaction.broker_id.in_(accessible_brokers_stmt))

    result = await session.execute(stmt)
    row = result.one_or_none()

    min_date: date_type | None = row.min_date if row else None
    max_date: date_type | None = row.max_date if row else None

    # Resolve sentinels
    resolved_start = date_range.start
    resolved_end = date_range.end

    if resolved_start == "min":
        resolved_start = min_date
    if resolved_end == "max":
        resolved_end = max_date or date_type.today()

    return OpenDateRangeModel(start=resolved_start, end=resolved_end)
