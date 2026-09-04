/**
 * assetIdentifiers.ts — the rules that decide whether an identifier raises a question.
 *
 * ## Why this is a module and not three closures in the import wizard
 *
 * Two beta-test findings were pure logic mistakes buried inside the wizard, where nothing could
 * reach them:
 *
 * - the prompt kept reappearing on assets whose *alternate* list already held the very ISIN it
 *   was offering, because only `identifier_isin` was ever compared;
 * - an asset with an empty ISIN column was reported as a conflict, because `'' !== null`.
 *
 * Both are one-line answers to a question that deserves a name. Pulling them out makes them
 * testable, and makes the invariant they enforce explicit rather than incidental.
 *
 * ## The invariant
 *
 * `identifier_isin` holds the **quoted** code — the only one a price provider can index, since a
 * price *is* the last trade. Everything else lives in `identifier_other`, where it no longer
 * quotes but still **recognises**: an Italian retail bond bought at issue carries a non-tradeable
 * "CUM" ISIN, and any future import quoting it must still find the same asset.
 *
 * So an identifier already stored among the alternates is not a gap to be filled again — it is a
 * deliberate statement, and asking about it a second time is noise.
 */

export type IdentifierField = 'identifier_isin' | 'identifier_ticker';

export interface IdentifierPending {
    field: IdentifierField;
    /**
     * The codes the report carried that the asset does not already know, trimmed and
     * deduplicated. More than one is normal once import assets are unified: a BTP group holds
     * both the CUM code and the quoted one.
     */
    extracted: string[];
    /** The code already on the asset, or null when it holds none of that type. */
    existing: string | null;
}

/** A blank column is not a value: the DB stores `''` where a code was never filled in. */
export function normIdentifier(value: unknown): string | null {
    const text = typeof value === 'string' ? value.trim() : '';
    return text === '' ? null : text;
}

/** Case-insensitive membership in a soft-identifier list. */
export function otherContains(list: unknown, value: string): boolean {
    const needle = (value ?? '').trim().toUpperCase();
    if (needle === '') return false;
    return Array.isArray(list) && list.some((entry) => typeof entry === 'string' && entry.trim().toUpperCase() === needle);
}

/**
 * Decide whether the report's codes raise a question at all.
 *
 * A code raises none when the asset already carries it — as the primary *or* among its
 * alternates. What is left over is the decision actually owed, with `existing` normalised so a
 * blank column never reads as a clash.
 *
 * Several codes are answered in **one** question, not in a queue: a group holding two ISINs plus
 * the one already stored is a single "which of these three leads?", and asking it three times
 * would invite three inconsistent answers.
 */
export function pendingIdentifier(extractedRaw: unknown, existingRaw: unknown, other: unknown, field: IdentifierField): IdentifierPending | null {
    const candidates = Array.isArray(extractedRaw) ? extractedRaw : [extractedRaw];
    const existing = normIdentifier(existingRaw);
    const extracted: string[] = [];
    for (const candidate of candidates) {
        const value = normIdentifier(candidate);
        if (!value) continue;
        if (existing && existing.toUpperCase() === value.toUpperCase()) continue;
        if (otherContains(other, value)) continue;
        if (otherContains(extracted, value)) continue;
        extracted.push(value);
    }
    if (extracted.length === 0) return null;
    return {field, extracted, existing};
}

/**
 * Does the pending decision actually need the user to *choose*, or only to agree?
 *
 * One unknown code on an asset that holds none is not a choice — it is a confirmation, and
 * dressing it up as an election is how the old modal ended up saying "replace?" over an empty
 * column. Two or more candidates is a genuine election.
 */
export function needsPrimaryChoice(pending: IdentifierPending): boolean {
    return pending.existing !== null || pending.extracted.length > 1;
}

/**
 * Union of a soft-identifier list with new entries, preserving order and existing casing.
 *
 * The PATCH replaces `identifier_other` wholesale, so the caller has to send the complete set —
 * appending blindly would duplicate, and rebuilding from scratch would drop what the user typed
 * by hand.
 */
export function mergeOther(current: readonly string[], additions: readonly (string | null | undefined)[]): string[] {
    const merged = [...current];
    for (const candidate of additions) {
        const value = normIdentifier(candidate);
        if (value && !otherContains(merged, value)) merged.push(value);
    }
    return merged;
}

/**
 * Split a settled decision into what goes where: the elected code leads, every other candidate
 * is demoted to the alternates. Nothing is discarded — that is the whole point.
 */
export function demotedValues(primary: string, candidates: readonly (string | null | undefined)[]): string[] {
    const lead = primary.trim().toUpperCase();
    const out: string[] = [];
    for (const candidate of candidates) {
        const value = normIdentifier(candidate);
        if (value && value.toUpperCase() !== lead && !otherContains(out, value)) out.push(value);
    }
    return out;
}
