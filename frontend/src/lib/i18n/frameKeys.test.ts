// @vitest-environment node
/**
 * The frame texts of the app shell, in the catalogues (workstream H, checkpoint 1, lot TC-5).
 *
 * Why. The (app) layout's «Checking authentication...» and the sidebar's close / collapse / expand names were English text
 * written in the markup. The cure moves them to the catalogue under `nav.checkingAuthentication`, `nav.closeSidebar`,
 * `nav.expandSidebar` and `nav.collapseSidebar`. The catalogue build fills a missing it, fr or es entry from English, so a
 * forgotten translation would never show in the app nor in a test of the built catalogue: this file reads the SOURCES,
 * `lib/i18n/<folder>/<lang>.json` (the base and the subsystem folders), directly, and finds each key in exactly one folder.
 *
 * Contract. Each of the four keys is a non-empty string in the sources of en, it, fr and es; it, fr and es are not a copy of the
 * English text; none holds an ICU placeholder (the texts take no parameter).
 *
 * Source guard. `routes/(app)/+layout.svelte` no longer writes «Checking authentication» in its markup: the loading panel
 * (`app-auth-checking`) shows `$_('nav.checkingAuthentication')`.
 *
 * Control. The reader is proven on the neighbour that exists today, `nav.toggleMenu`: found in the four sources, and different
 * from English in it, fr and es; an invented key is reported missing.
 *
 * Red today: the four keys are in none of the sources, and the layout still writes the English sentence.
 */
import {existsSync, readFileSync, readdirSync} from 'node:fs';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';

const LANGUAGES = ['en', 'it', 'fr', 'es'] as const;
type Lang = (typeof LANGUAGES)[number];
const TRANSLATIONS: readonly Lang[] = ['it', 'fr', 'es'];
const KEYS = ['nav.checkingAuthentication', 'nav.closeSidebar', 'nav.expandSidebar', 'nav.collapseSidebar'] as const;

const I18N_DIR = fileURLToPath(new URL('.', import.meta.url));
const LAYOUT = fileURLToPath(new URL('../../routes/(app)/+layout.svelte', import.meta.url));

/** The source folders: every subfolder of `lib/i18n` that holds an `en.json`. */
function sourceFolders(): string[] {
    return readdirSync(I18N_DIR, {withFileTypes: true})
        .filter((entry) => entry.isDirectory() && existsSync(join(I18N_DIR, entry.name, 'en.json')))
        .map((entry) => entry.name);
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

/** Every string found for `key` in the sources of `lang`, one per folder that holds it. */
function found(lang: Lang, key: string): string[] {
    return sourceFolders().flatMap((folder) => {
        const file = join(I18N_DIR, folder, `${lang}.json`);
        if (!existsSync(file)) return [];
        const value = valueAt(JSON.parse(readFileSync(file, 'utf8')), key);
        return typeof value === 'string' ? [value] : [];
    });
}

describe('frame texts of the app shell — the catalogue sources (TC-5)', () => {
    it('Control: the reader finds nav.toggleMenu in the four sources, it, fr and es differ from English, and an invented key is missing', () => {
        for (const lang of LANGUAGES) expect(found(lang, 'nav.toggleMenu'), `Control: nav.toggleMenu is a string in the ${lang} sources`).toHaveLength(1);
        for (const lang of TRANSLATIONS) expect(found(lang, 'nav.toggleMenu')[0], `Control: the ${lang} text of nav.toggleMenu is not the English one`).not.toBe(found('en', 'nav.toggleMenu')[0]);
        expect(found('en', 'nav.noSuchFrameKey'), 'Control: an invented key is reported missing').toEqual([]);
    });

    for (const key of KEYS) {
        for (const lang of LANGUAGES) {
            it(`${key} exists once in the ${lang} sources, as a non-empty text without placeholders`, () => {
                const texts = found(lang, key);

                expect(texts, `${key} is in exactly one ${lang} source folder`).toHaveLength(1);
                expect(texts[0].trim().length, `${key} in ${lang} is not empty`).toBeGreaterThan(0);
                expect(texts[0], `${key} in ${lang} takes no parameter`).not.toMatch(/[{}]/);
            });
        }
        for (const lang of TRANSLATIONS) {
            it(`${key} in ${lang} is translated, not a copy of the English text`, () => {
                const [english] = found('en', key);
                const [translated] = found(lang, key);

                expect(english, `barrier: ${key} exists in English`).toBeTypeOf('string');
                expect(translated, `${key} in ${lang} differs from English`).toBeTypeOf('string');
                expect(translated).not.toBe(english);
            });
        }
    }

    it('the (app) layout no longer writes «Checking authentication» in its markup, and its loading panel asks for nav.checkingAuthentication', () => {
        const source = readFileSync(LAYOUT, 'utf8');
        // presence barrier: the loading panel the sentence belongs to is still in the layout
        expect(source, 'barrier: the layout still draws its app-auth-checking panel').toContain('data-testid="app-auth-checking"');

        expect(source, 'the English sentence is gone from the layout').not.toMatch(/Checking authentication/i);
        expect(source, 'the panel reads the catalogue').toContain('nav.checkingAuthentication');
    });
});
