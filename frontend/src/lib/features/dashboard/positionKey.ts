/**
 * makePositionKey — the composite key that identifies a holding line.
 *
 * A position is identified by its asset together with the broker that holds it;
 * a `null` broker (an aggregate / broker-less holding) collapses to `0` so the
 * key is always a stable string. The dashboard's contribution and exposure
 * tables both build lookup maps on this key, and the map only works if the two
 * sides agree on the format down to the character — which is exactly why the
 * builder must live in one place rather than be re-typed per table.
 */
export function makePositionKey(assetId: number, brokerId: number | null): string {
    return `${assetId}-${brokerId ?? 0}`;
}
