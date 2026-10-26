// @vitest-environment node
/**
 * instance.checks.instanceKey — the messages of the security check of the instance key (lot H5-7, decision D6; Vitest, node).
 *
 * Why. The check (`backend/app/services/platform/instance_key_check.py`, `check_instance_key`) answers `ok`, or `error` when the
 * instance key is not the one the data were saved with, and the Security tab renders its i18n key
 * `instance.checks.instanceKey.<state>`. The catalogue build fills a missing it, fr or es entry from English, so a forgotten
 * translation would never show in the app nor in a catalogue test: this file reads the SOURCES, `lib/i18n/instance/<lang>.json`,
 * directly.
 *
 * Contract. `ok` (it exists today, as the key file check's «usable» text, and stays) and `mismatch` exist, non-empty strings, in each
 * of en, it, fr and es; `mismatch` has no parameter (the check's detail is empty), so no ICU placeholder; and the it, fr and es text of
 * `mismatch` differs from the English one (a copy of English is an untranslated key). The text of `mismatch` says neither a key nor a
 * check value: it is a sentence, so it holds no 64-character hexadecimal run.
 *
 * Control. The reader is proven on the neighbour that exists today, `instance.checks.pluginSecrets.ok`: found, non-empty, in the four
 * languages, and different from English in it, fr and es: a reader that finds nothing fails there, and the «differs» check is shown able
 * to differ.
 *
 * Red today: `instance.checks.instanceKey.mismatch` is in none of the four sources. Registered in
 * `scripts/test_runner/_frontend_utility.py`, in the Vitest list of `front_utility_unit` (action `core-unit`).
 */
import {readFileSync} from 'node:fs';
import {describe, expect, it} from 'vitest';

const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;
type Lang = (typeof LANGUAGES)[number];
const TRANSLATIONS: readonly Lang[] = ['it', 'fr', 'es'];
const OK = 'instance.checks.instanceKey.ok';
const MISMATCH = 'instance.checks.instanceKey.mismatch';

/** `lib/i18n/instance/<lang>.json`, read from disk, never through the generated catalogue (which fills gaps from English). */
function instanceSource(lang: Lang): unknown {
    return JSON.parse(readFileSync(new URL(`./instance/${lang}.json`, import.meta.url), 'utf8'));
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

/** The text of a key in one language's source, or `undefined`. */
function text(lang: Lang, key: string): string | undefined {
    const value = valueAt(instanceSource(lang), key);
    return typeof value === 'string' ? value : undefined;
}

describe('instance.checks.instanceKey — the instance key check, in the four languages (H5-7)', () => {
    it('Control: the reader finds instance.checks.pluginSecrets.ok in the four sources, and it, fr and es differ from English', () => {
        for (const lang of LANGUAGES) expect(text(lang, 'instance.checks.pluginSecrets.ok')?.length ?? 0, `Control: pluginSecrets.ok is a non-empty string in ${lang}.json`).toBeGreaterThan(0);
        for (const lang of TRANSLATIONS) expect(text(lang, 'instance.checks.pluginSecrets.ok'), `Control: the ${lang} text of pluginSecrets.ok is not the English one`).not.toBe(text('en', 'instance.checks.pluginSecrets.ok'));
        expect(text('en', 'instance.checks.noSuchKey.ok'), 'Control: an invented key is reported missing').toBeUndefined();
    });

    for (const lang of LANGUAGES) {
        it(`${lang}: ok and mismatch exist, non-empty, in instance/${lang}.json`, () => {
            const found = [OK, MISMATCH].map((key) => [key, text(lang, key)] as const);
            expect(
                found.filter(([, value]) => value === undefined || value.trim() === '').map(([key]) => key),
                `instance/${lang}.json must hold a non-empty text for each state of the check`,
            ).toEqual([]);
        });

        // red until H5-7: the key is in no source
        it(`${lang}: the mismatch message carries no ICU placeholder and no key-like run — the check has no detail`, () => {
            const written = text(lang, MISMATCH);
            // Barrier: the text exists, so «no placeholder» is a fact about a text, not about nothing
            expect(typeof written === 'string' && written.length > 0, `instance/${lang}.json holds ${MISMATCH}`).toBe(true);
            expect(/[{}]/.test(written ?? ''), 'the message has no parameter').toBe(false);
            expect(/[0-9a-f]{64}/i.test(written ?? ''), 'the message holds no 64-character hexadecimal run').toBe(false);
        });
    }

    // red until H5-7: the key is in no source
    it('mismatch: the it, fr and es texts differ from the English one', () => {
        const english = text('en', MISMATCH);
        expect(english?.length ?? 0, `Barrier: instance/en.json holds ${MISMATCH}`).toBeGreaterThan(0);
        const untranslated = TRANSLATIONS.filter((lang) => text(lang, MISMATCH) === undefined || text(lang, MISMATCH) === english);
        expect(untranslated, `${MISMATCH} in these languages is missing or a copy of the English text`).toEqual([]);
    });
});
