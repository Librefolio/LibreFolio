/**
 * signHintColor.ts — Shared sign-rule coloring logic for numeric inputs.
 *
 * Computes whether a numeric value conforms to the backend sign rule
 * AFTER auto-flip (e.g., 'negative' rule + positive input = OK because
 * the system auto-negates on save).
 *
 * Used by: CompactCashCell (cash), TransactionFormModal (quantity).
 * Purely visual guidance — never blocks input.
 */

export type SignRule = 'positive' | 'negative' | 'nonzero' | 'zero' | 'any' | 'free' | 'optional' | string;

export interface SignHintResult {
	ok: boolean;
	bad: boolean;
}

/**
 * Given a numeric value and a backend sign rule, determine whether the
 * value is conformant (ok=green) or violating (bad=red).
 *
 * Logic accounts for auto-flip: when rule is 'negative', user enters
 * positive (system negates on save), so positive → ok, negative → bad.
 */
export function computeSignHint(value: number, rule: SignRule): SignHintResult {
	if (Number.isNaN(value)) return {ok: false, bad: false};

	switch (rule) {
		case 'positive':
			return {ok: value > 0, bad: value < 0};
		case 'negative':
			// Auto-flip active: user enters positive (green), negative is wrong (red)
			return {ok: value > 0, bad: value < 0};
		case 'nonzero':
			return {ok: value !== 0, bad: value === 0};
		case 'zero':
			return {ok: value === 0, bad: value !== 0};
		default:
			// 'any', 'free', 'optional', or unknown — no coloring
			return {ok: false, bad: false};
	}
}

