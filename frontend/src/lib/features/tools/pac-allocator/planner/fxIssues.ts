/**
 * What the last read of LibreFolio's stored FX rates said about each pair (X-R45b): a saved rate skipped for an older
 * one, or none usable. Kept per draft and outside its data, so nothing here is saved or compared. Every read writes it
 * for the pairs it read, at the same time as their rate: the FX step's own read (`FxRateReader`) and the re-read before
 * «Calcola» (`refreshCopiedFacts`). So a pair's card never shows what another read said than the one of its rate.
 */
import {SvelteMap} from 'svelte/reactivity';
import type {PlannerDraft} from './draft.svelte';
import type {SourceIssue} from './source';

/** «No stored rate»: the card says it on its own (`notStored`), so it is not repeated among the pair's issues. */
const SAVED_FX_MISSING = 'allocation.saved_fx_missing';

const memories = new WeakMap<PlannerDraft, SvelteMap<string, SourceIssue[]>>();

function memoryOf(draft: PlannerDraft): SvelteMap<string, SourceIssue[]> {
    let memory = memories.get(draft);
    if (!memory) {
        memory = new SvelteMap();
        memories.set(draft, memory);
    }
    return memory;
}

/** The issues of a read about one pair: those of its FX quote (`fx:<pair>:<date>:<source>`), but «missing». */
function pairIssues(issues: readonly SourceIssue[], pair: string): SourceIssue[] {
    return issues.filter((issue) => issue.code !== SAVED_FX_MISSING && 'entity_kind' in issue.path && issue.path.entity_kind === 'fx_quote' && issue.path.entity_id.split(':')[1] === pair);
}

/** What the last read said about the pair. */
export function fxPairIssues(draft: PlannerDraft, pair: string): SourceIssue[] {
    return memoryOf(draft).get(pair) ?? [];
}

/** A read of `pairs` starts: what an older read said about them no longer holds. */
export function forgetFxPairIssues(draft: PlannerDraft, pairs: readonly string[]): void {
    const memory = memoryOf(draft);
    for (const pair of pairs) memory.delete(pair);
}

/** A read of `pairs` ended: what it said about each replaces what was kept, and a pair it said nothing about is cleared. */
export function rememberFxPairIssues(draft: PlannerDraft, pairs: readonly string[], issues: readonly SourceIssue[]): void {
    const memory = memoryOf(draft);
    for (const pair of pairs) {
        const about = pairIssues(issues, pair);
        if (about.length > 0) memory.set(pair, about);
        else memory.delete(pair);
    }
}
