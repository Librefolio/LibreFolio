// @vitest-environment node
/**
 * transactions.wacPreview.effect — the label of a `split_rescale` row, in the four languages (W6-1; Vitest, node).
 *
 * Why. The catalogue build fills a missing it, fr or es entry from English, so a forgotten translation would never show in the app nor in a
 * catalogue test: this file reads the SOURCES, `lib/i18n/transactions/<lang>.json`, directly, never the generated catalogue (same reader as
 * `transactionsEntryModeKeys.test.ts`).
 *
 * Contract. The backend preview sends `effect` in {add, add_zero_cost, reduce, split_rescale}; the effect column of the qualifying table
 * prints `transactions.wacPreview.effect.<key>` for each:
 *   - `splitRescale` exists, non-empty, in the four languages, and in it, fr and es differs from the English text (a copy of English is an
 *     untranslated key) and from the language's own `addZeroCost` («Dilution»): a distinct label;
 *   - `addAtWac` — the label of an effect the backend never sends — is gone from the four sources;
 *   - the three live keys `add`, `reduce`, `addZeroCost` are still there.
 *
 * Control. The reader is proven on a key that exists today (`transactions.wacPreview.effect.addZeroCost`): found, non-empty, in the four
 * languages; an invented key is reported missing — a reader that finds nothing would pass the «gone» check below.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit` (action `core-unit`).
 */
import {readFileSync} from 'node:fs';
import {describe, expect, it} from 'vitest';

const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;
type Lang = (typeof LANGUAGES)[number];
const TRANSLATIONS: readonly Lang[] = ['it', 'fr', 'es'];
const PREFIX = 'transactions.wacPreview.effect.';

/** `lib/i18n/transactions/<lang>.json`, read from disk, never through the generated catalogue (which fills gaps from English). */
function transactionsSource(lang: Lang): unknown {
    return JSON.parse(readFileSync(new URL(`./transactions/${lang}.json`, import.meta.url), 'utf8'));
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

/** The text of `transactions.wacPreview.effect.<name>` in one language's source, or `undefined`. */
function effectText(lang: Lang, name: string): string | undefined {
    const value = valueAt(transactionsSource(lang), PREFIX + name);
    return typeof value === 'string' ? value : undefined;
}

describe('transactions.wacPreview.effect — the split_rescale label, in the four languages (W6-1)', () => {
    it('Control: the reader finds addZeroCost in the four sources, and an invented key is reported missing', () => {
        for (const lang of LANGUAGES) expect(effectText(lang, 'addZeroCost')?.trim().length ?? 0, `Control: addZeroCost is a non-empty string in ${lang}.json`).toBeGreaterThan(0);
        expect(effectText('en', 'noSuchKey'), 'Control: an invented key is reported missing').toBeUndefined();
    });

    for (const lang of LANGUAGES) {
        describe(lang, () => {
            it.each(['splitRescale', 'add', 'reduce', 'addZeroCost'])('%s exists and is not empty', (name) => {
                expect(effectText(lang, name)?.trim().length ?? 0, `${PREFIX}${name} in transactions/${lang}.json`).toBeGreaterThan(0);
            });

            it('splitRescale is a label of its own — not the addZeroCost one', () => {
                const split = effectText(lang, 'splitRescale');
                expect(split, `splitRescale exists in ${lang}`).toBeDefined();
                expect(split, `splitRescale (${lang}) is the addZeroCost label`).not.toBe(effectText(lang, 'addZeroCost'));
            });

            it('addAtWac, the label of an effect the backend never sends, is gone from the source', () => {
                expect(effectText(lang, 'addAtWac'), `${PREFIX}addAtWac is still in transactions/${lang}.json`).toBeUndefined();
            });
        });
    }

    for (const lang of TRANSLATIONS) {
        it(`${lang}: splitRescale differs from the English text (a copy of English is an untranslated key)`, () => {
            const text = effectText(lang, 'splitRescale');
            expect(text, `splitRescale exists in ${lang}`).toBeDefined();
            expect(text, `splitRescale in ${lang} is the English text`).not.toBe(effectText('en', 'splitRescale'));
        });
    }
});
