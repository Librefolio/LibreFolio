/**
 * storageI18n — every key the storage bar of the Files page names is in the four catalogues (lot FB-29, written red
 * first against `B6r-fb29-interface.md` §5).
 *
 * The contract under test:
 *   - the keys of §5 — `storage.title`, `storage.parts.{database,uploads,brokerReports,backups,dataOther,disk,free}`,
 *     `storage.summary.{limit,volume,data}`, `storage.overLimit`, `storage.limit.{label,hint,locked,save,saved}`,
 *     `storage.limit.errors.{invalid,forbidden,locked,network,unexpected}`, `storage.errors.load` and `storage.retry` —
 *     are non-empty messages in `en`, `it`, `fr` and `es`;
 *   - each key names the same placeholders in the four languages (a message with a `{used}` in English and none in French
 *     would print the braces, or drop the number);
 *   - the summaries carry the numbers they are about: `limit` the used size and the limit, `volume` the size of
 *     LibreFolio’s files and the size of the disk, `data` the size of the data folder — the placeholder names the
 *     component fills in (`used`, `limit`, `total`);
 *   - the keys the component chooses by value exist for EVERY value its code can produce: the seven parts the legend
 *     names, the five codes `storageLimitSaveCode` answers, the three summaries one per mode.
 *
 * The catalogues are the generated ones (`$lib/i18n/<lang>.json`), built from their sources before every Vitest run: a
 * case reads the presence of a key and the placeholders it names, never its wording.
 *
 * Node environment: nothing here renders.
 */
import {describe, expect, it} from 'vitest';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};
const LANGUAGES = Object.keys(CATALOGUES);

/** The message at a dotted path, or `undefined` when the path leads nowhere or to a group. */
function message(catalogue: unknown, key: string): string | undefined {
    let node: unknown = catalogue;
    for (const part of key.split('.')) {
        if (node === null || typeof node !== 'object' || !(part in (node as Record<string, unknown>))) return undefined;
        node = (node as Record<string, unknown>)[part];
    }
    return typeof node === 'string' ? node : undefined;
}

/** The names a message fills in: `{count}` → `count`, sorted, once each. */
function placeholders(text: string): string[] {
    return [...new Set([...text.matchAll(/\{(\w+)/g)].map((match) => match[1]))].sort();
}

const PARTS = ['database', 'uploads', 'brokerReports', 'backups', 'dataOther', 'disk', 'free'];
const LIMIT_ERRORS = ['invalid', 'forbidden', 'locked', 'network', 'unexpected'];

const STORAGE_KEYS = [
    'storage.title',
    'storage.overLimit',
    'storage.retry',
    'storage.errors.load',
    ...PARTS.map((part) => `storage.parts.${part}`),
    ...['limit', 'volume', 'data'].map((mode) => `storage.summary.${mode}`),
    ...['label', 'hint', 'locked', 'save', 'saved'].map((name) => `storage.limit.${name}`),
    ...LIMIT_ERRORS.map((code) => `storage.limit.errors.${code}`),
];

describe('FB-29 — the keys of the storage bar', () => {
    it.each(LANGUAGES)('%s: every key of §5 is a non-empty message', (language) => {
        const missing = STORAGE_KEYS.filter((key) => (message(CATALOGUES[language], key) ?? '').trim() === '');

        expect(missing, `keys missing, or empty, in ${language}.json`).toEqual([]);
    });

    it('each key names the same placeholders in the four languages', () => {
        const mismatched = STORAGE_KEYS.filter((key) => {
            const names = LANGUAGES.map((language) => placeholders(message(CATALOGUES[language], key) ?? '').join(','));
            return new Set(names).size > 1;
        });

        expect(mismatched, 'keys whose placeholders differ between languages').toEqual([]);
    });

    it.each<[string, string[]]>([
        ['storage.summary.limit', ['limit', 'used']],
        ['storage.summary.volume', ['total', 'used']],
        ['storage.summary.data', ['used']],
    ])('%s carries the numbers it is about: %j', (key, names) => {
        for (const language of LANGUAGES) expect(placeholders(message(CATALOGUES[language], key) ?? ''), `${key} in ${language}`).toEqual(names);
    });

    it('the labels, the legend and the errors carry no placeholder: the component fills none in', () => {
        const withPlaceholders = STORAGE_KEYS.filter((key) => !key.startsWith('storage.summary.')).filter((key) => LANGUAGES.some((language) => placeholders(message(CATALOGUES[language], key) ?? '').length > 0));

        expect(withPlaceholders).toEqual([]);
    });

    it('the sentences are translated, not copied (each is a sentence, bar words that are one in all)', () => {
        const untranslated = ['storage.overLimit', 'storage.limit.hint', 'storage.limit.locked', 'storage.limit.errors.locked', 'storage.limit.errors.invalid', 'storage.errors.load'].filter((key) => {
            const texts = new Set(LANGUAGES.map((language) => message(CATALOGUES[language], key)));
            return texts.size === 1;
        });

        expect(untranslated).toEqual([]);
    });
});
