/**
 * Promote suggestions that join a new row of the bulk editor to a saved transaction.
 *
 * The editor already pairs two new rows (both sides imported together) and two saved rows. A side
 * imported now whose other side was saved earlier — Scalable Capital's overnight account imported a
 * month after the broker account — needs the third case. So the database search
 * (`POST /transactions/promote-suggest`) is asked for the new rows too, under a negative id, and the
 * banner pairs a new row with a saved one once both are in the editor; the 💡 button adds the saved
 * side when it is not there yet.
 */

/**
 * The id a new row is asked under: negative, so it never collides with a transaction id. The backend
 * keeps the input ids out of the candidates only when they are positive, i.e. real transactions.
 */
export function newRowSuggestId(createdSeq: number): number {
    return -(createdSeq + 1);
}

/** A new row paired with a saved one, and the type the pair would become. */
export interface MixedPromotePair {
    newTempId: string;
    savedTempId: string;
    targetType: string;
}

export interface MixedPairingRules<R> {
    /** The editor's row id. */
    keyOf: (row: R) => string;
    /** Whole days between the two rows' dates. */
    daysBetween: (a: R, b: R) => number;
    /** The widest gap, in days, between the two sides of a pair. */
    maxDeltaDays: number;
    /** The pair's target type when the two rows promote, or null. */
    match: (newRow: R, savedRow: R) => string | null;
}

/** Every (new, saved) pair that promotes within the date window, in the order of `newRows`, then of `savedRows`. */
export function mixedPromotePairs<R>(newRows: readonly R[], savedRows: readonly R[], rules: MixedPairingRules<R>): MixedPromotePair[] {
    const pairs: MixedPromotePair[] = [];
    for (const newRow of newRows) {
        for (const savedRow of savedRows) {
            if (rules.daysBetween(newRow, savedRow) > rules.maxDeltaDays) continue;
            const targetType = rules.match(newRow, savedRow);
            if (targetType) pairs.push({newTempId: rules.keyOf(newRow), savedTempId: rules.keyOf(savedRow), targetType});
        }
    }
    return pairs;
}

/** A saved transaction the database search proposes as the other side of a row. */
export interface SuggestCandidate {
    id: number;
    broker_id: number;
    date: string;
    type: string;
}

/** The candidates of one asked row that are not in the editor yet: what the 💡 button offers to add. */
export interface ImportableSuggestion {
    /** The id the row was asked under: the transaction id of a saved row, `newRowSuggestId` of a new one. */
    key: number;
    tempId: string;
    candidates: SuggestCandidate[];
}

/**
 * The database search's answer, reduced to the candidates the editor does not hold yet, per asked row
 * still in the editor. `tempIdOfKey` maps an asked id back to its row (undefined: the row is gone).
 */
export function importableSuggestions(results: ReadonlyMap<number, readonly SuggestCandidate[]>, tempIdOfKey: (key: number) => string | undefined, idsInEditor: ReadonlySet<number>): ImportableSuggestion[] {
    const importable: ImportableSuggestion[] = [];
    for (const [key, candidates] of results) {
        const tempId = tempIdOfKey(key);
        if (tempId === undefined) continue;
        const missing = candidates.filter((candidate) => !idsInEditor.has(candidate.id));
        if (missing.length > 0) importable.push({key, tempId, candidates: missing});
    }
    return importable;
}
