// @vitest-environment node
/**
 * csvImport — the status words of the CSV editor bar and of the import modal footer, in the four languages (W6-3; Vitest, node).
 *
 * Why. «valid row(s)», «N error(s)» and «duplicate <label>s» were English written in the components. The catalogue build fills a
 * missing it, fr or es entry from English, so a forgotten translation would never show in the app nor in a catalogue test: this
 * file reads the SOURCES, `lib/i18n/base/<lang>.json`, directly, never the generated catalogue (same reader idea as
 * `transactionsEntryModeKeys.test.ts`).
 *
 * Contract.
 *   - `csvImport.statusValidRows` and `csvImport.statusErrors` exist, non-empty, in the four languages; each is an ICU plural on
 *     `count` (singular and plural read differently once the number is taken out — «# valid row» / «# valid rows»);
 *   - `csvImport.statusDuplicates` exists in the four languages and carries `{label}` (the identity column label, shown as is);
 *   - `csvImport.duplicatesShort` (the modal footer's «Duplicates») exists, non-empty, in the four languages;
 *   - in it, fr and es each text differs from the English one (a copy of English is an untranslated key).
 *
 * Control. The reader is proven on a key that exists today (`csvImport.noValidRows`): found, non-empty, in the four languages; an
 * invented key is reported missing. The plural reader is proven on a message written here, where one and many differ.
 *
 * Registered in `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit` (action `core-unit`).
 */
import {readFileSync} from 'node:fs';
import {getMessageFormatter} from 'svelte-i18n';
import {describe, expect, it} from 'vitest';

const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;
type Lang = (typeof LANGUAGES)[number];
const TRANSLATIONS: readonly Lang[] = ['it', 'fr', 'es'];
const PREFIX = 'csvImport.';
const NEW_KEYS = ['statusValidRows', 'statusErrors', 'statusDuplicates', 'duplicatesShort'] as const;
const PLURALS = ['statusValidRows', 'statusErrors'] as const;

/** `lib/i18n/base/<lang>.json`, read from disk, never through the generated catalogue (which fills gaps from English). */
function baseSource(lang: Lang): unknown {
    return JSON.parse(readFileSync(new URL(`./base/${lang}.json`, import.meta.url), 'utf8'));
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

/** The text of `csvImport.<name>` in one language's source, or `undefined`. */
function csvText(lang: Lang, name: string): string | undefined {
    const value = valueAt(baseSource(lang), PREFIX + name);
    return typeof value === 'string' ? value : undefined;
}

/** `message` formatted by the runtime's own formatter for `lang`. */
function render(message: string, lang: Lang, values: Record<string, string | number>): string {
    return String(getMessageFormatter(message, lang).format(values));
}

/** The message for `count` with the number itself taken out: what is left is the wording of the plural form. */
function wording(message: string, lang: Lang, count: number): string {
    return render(message, lang, {count}).replaceAll(String(count), '#');
}

describe('csvImport — status words of the CSV editor bar and the import footer, in the four languages (W6-3)', () => {
    it('Control: the reader finds noValidRows in the four sources, an invented key is reported missing, the plural reader tells one from many', () => {
        for (const lang of LANGUAGES) expect(csvText(lang, 'noValidRows')?.trim().length ?? 0, `Control: noValidRows is a non-empty string in ${lang}.json`).toBeGreaterThan(0);
        expect(csvText('en', 'noSuchKey'), 'Control: an invented key is reported missing').toBeUndefined();
        const sample = '{count, plural, one {# thing} other {# things}}';
        expect(wording(sample, 'en', 1), 'Control: one').toBe('# thing');
        expect(wording(sample, 'en', 5), 'Control: many').toBe('# things');
    });

    for (const lang of LANGUAGES) {
        describe(lang, () => {
            it.each(NEW_KEYS)('%s exists and is not empty', (name) => {
                expect(csvText(lang, name)?.trim().length ?? 0, `${PREFIX}${name} in base/${lang}.json`).toBeGreaterThan(0);
            });

            it.each(PLURALS)('%s is a plural on count: one and many read differently', (name) => {
                const message = csvText(lang, name);
                expect(message, `${PREFIX}${name} exists in ${lang}`).toBeDefined();
                expect(message ?? '', `${name} (${lang}) is an ICU plural`).toMatch(/\{count\s*,\s*plural\s*,/);
                expect(wording(message ?? '', lang, 1), `${name} (${lang}): the singular reads like the plural`).not.toBe(wording(message ?? '', lang, 5));
            });

            it('statusDuplicates carries {label}, and shows it as given', () => {
                const message = csvText(lang, 'statusDuplicates');
                expect(message ?? '', 'statusDuplicates').toContain('{label}');
                expect(render(message ?? '', lang, {label: 'ISIN'}), 'the label is shown as is').toContain('ISIN');
            });
        });
    }

    for (const lang of TRANSLATIONS) {
        it(`${lang}: the four texts differ from the English ones (a copy of English is an untranslated key)`, () => {
            for (const name of NEW_KEYS) {
                const text = csvText(lang, name);
                expect(text, `${name} exists in ${lang}`).toBeDefined();
                expect(text, `${name} in ${lang} is the English text`).not.toBe(csvText('en', name));
            }
        });
    }
});
