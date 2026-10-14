/**
 * providerComparisonQueue — when the provider comparison may open, and with which rows.
 *
 * A provider search selection in `AssetModal` can raise two questions about the same identifier:
 * the primary-identifier chooser opens synchronously ("the report says X, the provider says Y:
 * which one leads?"), and the metadata comparison arrives a moment later from the probe and asks
 * it again as an `identifier_*` row. Opened as they arrive, the second modal lands on top of the
 * first and repeats its question (R18).
 *
 * The rule, as the developer stated it: while the chooser is open the comparison stays loaded but
 * waits; once the chooser is answered, the row asking the same thing goes away; if nothing is
 * left, the comparison does not open at all. The same pruning applies when the user answers
 * *before* the probe returns, because a question already answered must not be asked again.
 *
 * Extracted out of the component so the decision is testable without mounting the modal: the
 * component only reports what is open and whether its provider context is still current.
 *
 * @module components/assets/providerComparisonQueue
 */
import type {DiffItem} from './ProviderComparisonModal.svelte';

/** One identifier question the chooser put to the user, in the comparison's own terms. */
export interface IdentifierQuestion {
    /** Comparison field the question corresponds to, e.g. `identifier_isin`. */
    field: string;
    /** Every code the chooser offered, trimmed and upper-cased. */
    candidates: readonly string[];
}

export type ComparisonDecision = {kind: 'open'; differences: DiffItem[]} | {kind: 'hold'; differences: DiffItem[]} | {kind: 'drop'};

function normalise(value: unknown): string {
    return String(value ?? '')
        .trim()
        .toUpperCase();
}

/** The question the chooser asks for `idType`, over the codes it offered. */
export function identifierQuestion(idType: string, candidates: readonly string[]): IdentifierQuestion {
    const seen = new Set<string>();
    const normalised: string[] = [];
    for (const candidate of candidates) {
        const value = normalise(candidate);
        if (value === '' || seen.has(value)) continue;
        seen.add(value);
        normalised.push(value);
    }
    return {field: `identifier_${idType.toLowerCase()}`, candidates: normalised};
}

/**
 * True when a comparison row asks what the chooser asks.
 *
 * Only identifier rows can: the chooser elects identifiers, so a name or a distribution is never
 * its question, whatever the question object says. And the same field is not enough: a provider
 * value the chooser never offered is a new question and has to reach the user.
 */
export function asksSameQuestion(diff: DiffItem, question: IdentifierQuestion): boolean {
    return diff.field.startsWith('identifier_') && diff.field === question.field && question.candidates.includes(normalise(diff.providerValue));
}

/** The rows no question has already covered, in their original order. */
export function pruneAnsweredRows(differences: readonly DiffItem[], questions: readonly IdentifierQuestion[]): DiffItem[] {
    return differences.filter((diff) => !questions.some((question) => asksSameQuestion(diff, question)));
}

/**
 * What to do with a comparison born from a search selection.
 *
 * - `drop` when its provider context is stale, or when every row was already answered;
 * - `hold` while a prompt of the same selection is still open — it opens once the prompt settles;
 * - `open` otherwise, with the answered rows removed.
 */
export function decideComparison(input: {differences: readonly DiffItem[]; questions: readonly IdentifierQuestion[]; promptOpen: boolean; current: boolean}): ComparisonDecision {
    if (!input.current) return {kind: 'drop'};
    const differences = pruneAnsweredRows(input.differences, input.questions);
    if (differences.length === 0) return {kind: 'drop'};
    return input.promptOpen ? {kind: 'hold', differences} : {kind: 'open', differences};
}
