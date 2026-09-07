/**
 * Which rows the duplicate re-check may ask about, and in what shape.
 *
 * Extracted from `ImportWizardModal.refreshDuplicateReport` because the decision is a
 * pure one — it depends only on the rows, on what the user resolved, and on the type
 * rules — while the surrounding function is network and component state.
 */

import {isFakeAssetId} from '$lib/utils/brim/isFakeAssetId';

/** Minimal view of a row: everything else the wizard carries is irrelevant here. */
export interface RecheckCandidate<T = unknown> {
    /** Stable identity of the row in the wizard, echoed back on the result. */
    index: number;
    /** The transaction payload as it currently stands, corrections included. */
    tx: T;
}

export interface RecheckAsk<T = unknown> {
    /** The original row, so the verdict can be attributed back to it. */
    row: RecheckCandidate<T>;
    /** The payload actually sent: a copy, with fake asset ids substituted. */
    clone: T;
}

/** How a transaction type treats its instrument field. */
export type AssetFieldMode = 'required' | 'optional' | 'forbidden' | string;

/**
 * Build the list of rows to submit to `POST /brokers/import/duplicates`.
 *
 * Two things happen here, and both are load-bearing:
 *
 * 1. **Fake ids are substituted.** A row parsed from a report points at a placeholder
 *    instrument until the user resolves it; the database knows nothing of those ids.
 * 2. **Rows whose instrument is still unresolved are dropped** — but only when their
 *    type *requires* one. The endpoint validates the payload as real transactions, so a
 *    BUY with a null asset is refused with a 422, and a single such row used to fail the
 *    whole re-check and leave the wizard showing the pre-correction verdict. A row with
 *    no instrument could not match anything anyway: there is nothing to key the
 *    comparison on. A DEPOSIT or a FEE, whose type does not require an instrument, is
 *    kept — dropping those would empty the payload of a cash-only file.
 *
 * @param rows Candidate rows, in wizard order.
 * @param resolvedByFakeId Mapping from placeholder id to the instrument the user picked.
 * @param assetFieldOf How a given type treats its instrument field.
 * @returns The rows to ask about, paired with the payload sent for each.
 */
export function buildDuplicateRecheckPayload<T extends {asset_id?: unknown; type?: unknown}>(rows: ReadonlyArray<RecheckCandidate<T>>, resolvedByFakeId: ReadonlyMap<number, number>, assetFieldOf: (type: string) => AssetFieldMode): RecheckAsk<T>[] {
    return rows
        .map((row) => {
            const clone = {...row.tx} as T & {asset_id?: number | null};
            // A row can carry a paired instrument (two-sided transfers); only a plain id
            // can be a placeholder, and only a plain id is what the endpoint compares on.
            const aid = typeof clone.asset_id === 'number' ? clone.asset_id : null;
            if (aid !== null && isFakeAssetId(aid)) {
                clone.asset_id = resolvedByFakeId.get(aid) ?? null;
            }
            return {row, clone: clone as T};
        })
        .filter(({clone}) => {
            const aid = (clone as {asset_id?: unknown}).asset_id;
            if (aid !== null && aid !== undefined) return true;
            return assetFieldOf(String((clone as {type?: unknown}).type ?? '')) !== 'required';
        });
}
