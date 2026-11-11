// @vitest-environment node
/**
 * transactions.form — the sign hints and the «Total / Unit price» keys of the transaction form, in the four languages (FB-16; Vitest, node).
 *
 * Why. The catalogue build fills a missing it, fr or es entry from English, so a forgotten translation would never show in the app nor in a
 * catalogue test: this file reads the SOURCES, `lib/features/transactions/i18n/<lang>.json`, directly, never the generated catalogue (the equivalent of
 * `scripts.i18n_catalog.load_catalog(lang, fallback=False)` the backend tests use).
 *
 * Contract (developer decision of 28/10/2026).
 *   - The sign hints (`hintSignPositive`, `hintSignNegative`, `hintSignZero`, `hintSignNonzero`) say only WHAT TO ENTER, never what the form
 *     does afterwards: each exists, non-empty, in each language, and none says «negated», «inverted» or «auto» (`negat`, `invert`, `invers`,
 *     `auto-`, in any of the four languages: «invertito», "inversé", "invertido", "auto-negated");
 *   - `unitPriceHint` (the old second input's note) is gone from the source;
 *   - `entryModeAmount` (the «Total» button), `entryModeUnitPrice`, `entryDerivedTotal` and `entryDerivedUnit` exist, non-empty, in the four
 *     languages; the two derived texts carry the `{value}` placeholder, and `entryDerivedUnit` also carries `{base}` (the quote base: «per unit»
 *     / «per N units»). The it, fr and es text of the derived ones differs from the English one (a copy of English is an untranslated key).
 *
 * Control. The reader is proven on a key that exists today and has not changed (`transactions.form.hintSignZero`): found, non-empty, in the four
 * languages; an invented key is reported missing — a reader that finds nothing would pass every «absent» check below.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit` (action `core-unit`).
 */
import {readFileSync} from 'node:fs';
import {describe, expect, it} from 'vitest';

const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;
type Lang = (typeof LANGUAGES)[number];
const TRANSLATIONS: readonly Lang[] = ['it', 'fr', 'es'];
const PREFIX = 'transactions.form.';
const SIGN_HINTS = ['hintSignPositive', 'hintSignNegative', 'hintSignZero', 'hintSignNonzero'] as const;
/** What a hint must not say: it describes what happens after the save, not what to enter. */
const AFTERWARDS = /negat|invert|invers|auto-/i;

/** `lib/features/transactions/i18n/<lang>.json`, read from disk, never through the generated catalogue (which fills gaps from English). */
function transactionsSource(lang: Lang): unknown {
    return JSON.parse(readFileSync(new URL(`../features/transactions/i18n/${lang}.json`, import.meta.url), 'utf8'));
}

/** The value at a dotted key of a nested source; `undefined` when any step is missing or not an object. */
function valueAt(source: unknown, key: string): unknown {
    let current: unknown = source;
    for (const step of key.split('.')) {
        if (typeof current !== 'object' || current === null || !Object.hasOwn(current, step)) return undefined;
        current = (current as Record<string, unknown>)[step];
    }
    return current;
}

/** The text of `transactions.form.<name>` in one language's source, or `undefined`. */
function formText(lang: Lang, name: string): string | undefined {
    const value = valueAt(transactionsSource(lang), PREFIX + name);
    return typeof value === 'string' ? value : undefined;
}

describe('transactions.form — sign hints and «Total / Unit price» keys, in the four languages (FB-16)', () => {
    it('Control: the reader finds hintSignZero in the four sources, and an invented key is reported missing', () => {
        for (const lang of LANGUAGES) expect(formText(lang, 'hintSignZero')?.trim().length ?? 0, `Control: hintSignZero is a non-empty string in ${lang}.json`).toBeGreaterThan(0);
        expect(formText('en', 'noSuchKey'), 'Control: an invented key is reported missing').toBeUndefined();
    });

    for (const lang of LANGUAGES) {
        describe(lang, () => {
            it.each(SIGN_HINTS)('%s exists, is not empty, and says what to enter — not what the form does after', (name) => {
                const text = formText(lang, name);
                expect(text?.trim().length ?? 0, `${name} in transactions/${lang}.json`).toBeGreaterThan(0);
                expect(text, `${name} (${lang}) describes a later step: ${text}`).not.toMatch(AFTERWARDS);
            });

            it('unitPriceHint, the note of the second input that is gone, is not in the source', () => {
                expect(formText(lang, 'unitPriceHint'), `transactions.form.unitPriceHint is still in transactions/${lang}.json`).toBeUndefined();
            });

            it.each(['entryModeAmount', 'entryModeUnitPrice', 'entryDerivedTotal', 'entryDerivedUnit'])('%s exists and is not empty', (name) => {
                expect(formText(lang, name)?.trim().length ?? 0, `${name} in transactions/${lang}.json`).toBeGreaterThan(0);
            });

            it('entryDerivedTotal carries {value}; entryDerivedUnit carries {value} and {base} (the quote base)', () => {
                expect(formText(lang, 'entryDerivedTotal') ?? '', 'entryDerivedTotal').toContain('{value}');
                expect(formText(lang, 'entryDerivedUnit') ?? '', 'entryDerivedUnit').toContain('{value}');
                expect(formText(lang, 'entryDerivedUnit') ?? '', 'entryDerivedUnit').toContain('{base');
            });
        });
    }

    for (const lang of TRANSLATIONS) {
        it(`${lang}: the two derived texts differ from the English ones (a copy of English is an untranslated key)`, () => {
            for (const name of ['entryDerivedTotal', 'entryDerivedUnit']) {
                const text = formText(lang, name);
                expect(text, `${name} exists in ${lang}`).toBeDefined();
                expect(text, `${name} in ${lang} is the English text`).not.toBe(formText('en', name));
            }
        });
    }
});
