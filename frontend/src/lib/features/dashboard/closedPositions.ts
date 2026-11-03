/**
 * The positions closed inside the period that the Portfolio table lists as sold out (T1, Y6-7).
 *
 * The engine says how each closed position closed (`closed_by`, MF-CB) and, for a transfer, where the units went
 * (`closed_to_broker_id`). A position closed by a transfer to a broker that is in the report and still holds the asset has
 * moved, not left: listing it as sold out in italics beside the destination's full row would say the opposite. Every other
 * closure stays listed — a sale, an adjustment, a closure the engine does not name, and a transfer whose destination is
 * not among the holdings on screen (not selected, unknown or sold since): there the units did leave this view.
 *
 * The decision reads only the holdings on screen, so it follows the broker filter by itself.
 */

/**
 * A contribution row as far as this decision reads it. The generated client types the two closure fields as a value or a
 * list of values (its shape for every optional nullable field), so they are read as what they are on the wire: a string and
 * a number, anything else counting as absent.
 */
export interface ClosedPositionLike {
    asset_id: number;
    broker_id?: number | null;
    is_fully_sold?: boolean;
    closed_by?: unknown;
    closed_to_broker_id?: unknown;
}

export interface HeldPositionLike {
    asset_id: number;
    /** A broker id, read as a number when it is one (see `ClosedPositionLike`). */
    broker_id?: unknown;
}

/** The closed positions to list, in the order given. */
export function closedPositionsToList<T extends ClosedPositionLike>(positions: readonly T[], holdings: readonly HeldPositionLike[]): T[] {
    const held = new Set(holdings.map((holding) => `${holding.asset_id}:${typeof holding.broker_id === 'number' ? holding.broker_id : ''}`));
    return positions.filter((position) => {
        if (!position.is_fully_sold) return false;
        const movedTo = position.closed_by === 'TRANSFER' && typeof position.closed_to_broker_id === 'number' ? position.closed_to_broker_id : null;
        if (movedTo === null || movedTo === (position.broker_id ?? null)) return true;
        return !held.has(`${position.asset_id}:${movedTo}`);
    });
}
