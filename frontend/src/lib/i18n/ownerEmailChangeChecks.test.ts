// @vitest-environment node
/**
 * auth.checks.ownerEmailChange — the three messages of the security check `accounts.owner_email_change`, in the four
 * languages (lot H5-4, A's request A5-1b; Vitest, node).
 *
 * Why. The check (`backend/app/services/accounts/checks.py`, `check_owner_email_change`) answers `ok`, `info` (pending: the
 * new address was sent a confirmation link) or `warning` (blocked: another account holds the new address), and the
 * Security tab renders its i18n key `auth.checks.ownerEmailChange.<state>`. The catalogue build fills a missing it, fr or
 * es entry from English, so a forgotten translation would never show in the app nor in a catalogue test: this file reads
 * the SOURCES, `lib/i18n/auth/<lang>.json`, directly.
 *
 * Contract. `ok`, `pending` and `blocked` exist, non-empty strings, in each of en, it, fr and es, in the `auth` source; the
 * messages have no parameter (the check's detail is empty), so no ICU placeholder; and the it, fr and es text of `pending`
 * and `blocked` differs from the English one (a copy of English is an untranslated key). `ok` is checked for presence only:
 * a state's text may legitimately read the same.
 *
 * Control. The reader is proven on the neighbour that exists today, `auth.checks.loginLimit.ok`: found, non-empty, in the
 * four languages, and different from English in it, fr and es: a reader that finds nothing fails there, and the «differs»
 * check is shown able to differ.
 *
 * Red today: the three keys are in none of the four sources. Registered in `scripts/test_runner/_frontend_utility.py`, in the
 * Vitest list of `front_utility_unit` (action `core-unit`), next to `importWizardAssetsCount.test.ts`.
 */
import {readFileSync} from 'node:fs';
import {describe, expect, it} from 'vitest';

const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;
type Lang = (typeof LANGUAGES)[number];
const TRANSLATIONS: readonly Lang[] = ['it', 'fr', 'es'];
const STATES = ['ok', 'pending', 'blocked'] as const;
const OWNER_CHANGE = 'auth.checks.ownerEmailChange';

/** `lib/i18n/auth/<lang>.json`, read from disk, never through the generated catalogue (which fills gaps from English). */
function authSource(lang: Lang): unknown {
    return JSON.parse(readFileSync(new URL(`./auth/${lang}.json`, import.meta.url), 'utf8'));
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
    const value = valueAt(authSource(lang), key);
    return typeof value === 'string' ? value : undefined;
}

describe('auth.checks.ownerEmailChange — the owner email change check, in the four languages (H5-4)', () => {
    it('Control: the reader finds auth.checks.loginLimit.ok in the four sources, and it, fr and es differ from English', () => {
        for (const lang of LANGUAGES) expect(text(lang, 'auth.checks.loginLimit.ok')?.length ?? 0, `Control: auth.checks.loginLimit.ok is a non-empty string in ${lang}.json`).toBeGreaterThan(0);
        for (const lang of TRANSLATIONS) expect(text(lang, 'auth.checks.loginLimit.ok'), `Control: the ${lang} text of loginLimit.ok is not the English one`).not.toBe(text('en', 'auth.checks.loginLimit.ok'));
        expect(text('en', 'auth.checks.noSuchKey.ok'), 'Control: an invented key is reported missing').toBeUndefined();
    });

    // red until H5-4: the keys are in no source
    for (const lang of LANGUAGES) {
        it(`${lang}: ok, pending and blocked exist, non-empty, in auth/${lang}.json`, () => {
            const found = STATES.map((state) => [state, text(lang, `${OWNER_CHANGE}.${state}`)] as const);
            expect(
                found.filter(([, value]) => value === undefined || value.trim() === '').map(([state]) => `${OWNER_CHANGE}.${state}`),
                `auth/${lang}.json must hold a non-empty text for each state of the check`,
            ).toEqual([]);
        });

        it(`${lang}: the messages carry no ICU placeholder — the check has no detail`, () => {
            const written = STATES.map((state) => text(lang, `${OWNER_CHANGE}.${state}`));
            // Barrier: the three texts exist, so «no placeholder» is a fact about texts, not about nothing
            expect(
                written.every((value) => typeof value === 'string' && value.length > 0),
                `auth/${lang}.json holds the three texts of ${OWNER_CHANGE}`,
            ).toBe(true);
            expect(
                written.filter((value) => /[{}]/.test(value ?? '')),
                'no message of the check has a parameter',
            ).toEqual([]);
        });
    }

    // red until H5-4: the keys are in no source
    for (const state of ['pending', 'blocked'] as const) {
        it(`${state}: the it, fr and es texts differ from the English one`, () => {
            const english = text('en', `${OWNER_CHANGE}.${state}`);
            expect(english?.length ?? 0, `Barrier: auth/en.json holds ${OWNER_CHANGE}.${state}`).toBeGreaterThan(0);
            const untranslated = TRANSLATIONS.filter((lang) => text(lang, `${OWNER_CHANGE}.${state}`) === undefined || text(lang, `${OWNER_CHANGE}.${state}`) === english);
            expect(untranslated, `${OWNER_CHANGE}.${state} in these languages is missing or a copy of the English text`).toEqual([]);
        });
    }
});
