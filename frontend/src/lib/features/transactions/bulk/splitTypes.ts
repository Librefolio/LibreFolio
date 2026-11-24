/**
 * The types the halves of a split pair take (66 C22d): one computation for the Bulk's Type cell, a half's Form, «Link»
 * (`bulkLinkSelection`), the issue rows and the local split of a new pair. The backend assigns the same types when it
 * splits a saved pair (`apply_splits`, `SPLIT_TYPE_MAP`), and checks the batch's rules on its final state (rule 7).
 */
import type {PendingOp} from './txBulkTypes';

/** Client mirror of the backend's `SPLIT_TYPE_MAP`: [sender, receiver]. */
export const SPLIT_TYPE_MAP: Readonly<Record<string, readonly [string, string]>> = {
    TRANSFER: ['ADJUSTMENT', 'ADJUSTMENT'],
    CASH_TRANSFER: ['WITHDRAWAL', 'DEPOSIT'],
    FX_CONVERSION: ['WITHDRAWAL', 'DEPOSIT'],
};

/** A queued split of a saved pair (`pendingSplits`): `originalType` is the pair's type before the split. */
export interface QueuedSplit {
    id_a: number;
    id_b: number;
    originalType: string;
}

/** The type one half of a pair of `originalType` takes when split: the sender (its quantity for a TRANSFER, its cash
 *  for the others, at or below zero) takes the first type, the receiver the second; `null` for a type that does not
 *  split. */
export function splitHalfType(originalType: string, fields: {quantity?: string | null; cash?: {amount: string} | null}): string | null {
    const types = SPLIT_TYPE_MAP[originalType];
    if (!types) return null;
    const sign = originalType === 'TRANSFER' ? Number(fields.quantity ?? 0) : Number(fields.cash?.amount ?? 0);
    return sign <= 0 ? types[0] : types[1];
}

/** The type `op` will have once the batch is saved: the type its queued split gives it, unless the user chose another
 *  one by hand (BUG-C4: `fields.type` changed from the pair's type); any other operation keeps `fields.type`. */
export function postSplitType(op: PendingOp, splits: readonly QueuedSplit[]): string {
    if (op.op !== 'edit') return op.fields.type;
    const split = splits.find((s) => s.id_a === op.txId || s.id_b === op.txId);
    if (!split || op.fields.type !== split.originalType) return op.fields.type;
    return splitHalfType(split.originalType, op.fields) ?? op.fields.type;
}

/** The type the update of a split half must carry (66 C22e), or `null` when it carries none. The backend splits first
 *  (`apply_splits`) and gives the half the type of its side as saved (`pair_sides`); the update runs after. So the
 *  update names a type only when the one the Bulk shows (`postSplitType`) differs from that: the user swapped it by
 *  hand. The side is read on the saved row, never on the draft: after a swap the draft's amount is a magnitude. */
export function splitTypeToSend(op: PendingOp, splits: readonly QueuedSplit[], saved: {quantity?: string | null; cash?: {amount: string} | null} | null): string | null {
    if (op.op !== 'edit' || !saved) return null;
    const split = splits.find((s) => s.id_a === op.txId || s.id_b === op.txId);
    if (!split) return null;
    const serverType = splitHalfType(split.originalType, saved);
    const finalType = postSplitType(op, splits);
    return serverType && finalType !== serverType ? finalType : null;
}
