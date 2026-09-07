/**
 * Pure field helpers extracted from `TransactionFormModal.svelte`.
 *
 * These are input→output functions with no component state: issue de-duplication and the
 * sign-rule presentation (marker glyph + hint i18n key). The component keeps a thin
 * `signHintText` wrapper that feeds `signHintKey` through `$t`, so the markup is unchanged.
 */
import type {SignRule} from '$lib/stores/transactions/transactionTypeStore';
import type {ValidationIssue} from '$lib/components/transactions/types';

/**
 * Collapse repeated validation issues to the first occurrence, keyed by `code` (falling back
 * to the raw `error` string when a code is absent). The user sees each distinct problem once.
 */
export function deduplicateIssues(raw: ValidationIssue[]): ValidationIssue[] {
    const seen = new Set<string>();
    return raw.filter((iss) => {
        const key = iss.code ?? iss.error;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

/** Short marker glyph shown beside a field whose value is sign-constrained (empty when unconstrained). */
export function signLabel(sign: SignRule): string {
    switch (sign) {
        case 'positive':
            return '(+)';
        case 'negative':
            return '(−)';
        case 'nonzero':
            return '(≠0)';
        default:
            return '';
    }
}

/**
 * i18n key for the hint text below a sign-constrained field, or `null` when the rule needs no
 * hint. Kept separate from the translation so it can be asserted without touching translated
 * strings; the component renders `$t(signHintKey(sign) ?? '')`.
 */
export function signHintKey(sign: SignRule): string | null {
    switch (sign) {
        case 'positive':
            return 'transactions.form.hintSignPositive';
        case 'negative':
            return 'transactions.form.hintSignNegative';
        case 'zero':
            return 'transactions.form.hintSignZero';
        case 'nonzero':
            return 'transactions.form.hintSignNonzero';
        default:
            return null;
    }
}
