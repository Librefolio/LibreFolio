/**
 * backupListI18n — every key the list of kept backups and the clean-up settings name is in the four catalogues (lot
 * FB-24, written red first against `B6r-fb24-frontend-interface.md` §7).
 *
 * The contract under test:
 *   - the keys of §7 — `backup.list.*` (title, description, show, hide, empty, the five column names (the sixth of §7, `columns.actions`, is not in the catalogues the lot delivered: the actions column has no header text), the retry button, the four origins, the
 *     three kinds, the three row actions, the delete confirmation, the SHA-copied toast, the same-disk warning, the read
 *     error), `backup.cleanup.*` (title, description, the two field labels, the two hints, save, saved, the
 *     «latest backup is always kept» line and the four save errors that `cleanupSaveCode` can answer) and
 *     `uploads.backups` (the label of the Files page tab) — are non-empty messages in `en`, `it`, `fr` and `es`;
 *   - each key names the same placeholders in the four languages (a message with a `{count}` in English and none in French
 *     would print the braces, or drop the number);
 *   - the keys the components choose by value exist for EVERY value their code can produce: the four origins the server
 *     lists, the three kinds `backupKind` answers, the four codes `cleanupSaveCode` answers;
 *   - `backup.download.retention`, which the card keeps using, is still a message in the four (its wording changes — the
 *     archive stays on the server until the user deletes it — and wording is not asserted here).
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

const LIST_KEYS = [
    'backup.list.title',
    'backup.list.description',
    'backup.list.show',
    'backup.list.hide',
    'backup.list.empty',
    'backup.list.deleteConfirm',
    'backup.list.sha.copied',
    'backup.list.sameDisk',
    'backup.list.errors.load',
    'backup.list.retry',
    ...['date', 'origin', 'kind', 'size', 'sha256'].map((column) => `backup.list.columns.${column}`),
    ...['ui', 'cli', 'pre-restore', 'panel'].map((origin) => `backup.list.origin.${origin}`),
    ...['clear', 'password', 'sealed'].map((kind) => `backup.list.kind.${kind}`),
    ...['download', 'delete', 'copySha'].map((action) => `backup.list.actions.${action}`),
];

const CLEANUP_KEYS = [
    'backup.cleanup.title',
    'backup.cleanup.description',
    'backup.cleanup.maxMb',
    'backup.cleanup.maxDays',
    'backup.cleanup.hintSelfhosted',
    'backup.cleanup.hintManaged',
    'backup.cleanup.save',
    'backup.cleanup.saved',
    'backup.cleanup.latestKept',
    ...['invalid', 'forbidden', 'network', 'unexpected'].map((code) => `backup.cleanup.errors.${code}`),
];

const OTHER_KEYS = ['uploads.backups', 'backup.download.retention'];

const ALL_KEYS = [...LIST_KEYS, ...CLEANUP_KEYS, ...OTHER_KEYS];

describe('FB-24 — the keys of the list of kept backups and of the clean-up settings', () => {
    it.each(LANGUAGES)('%s: every key of §7 is a non-empty message', (language) => {
        const missing = ALL_KEYS.filter((key) => (message(CATALOGUES[language], key) ?? '').trim() === '');

        expect(missing, `keys missing, or empty, in ${language}.json`).toEqual([]);
    });

    it('each key names the same placeholders in the four languages', () => {
        const mismatched = ALL_KEYS.filter((key) => {
            const names = LANGUAGES.map((language) => placeholders(message(CATALOGUES[language], key) ?? '').join(','));
            return new Set(names).size > 1;
        });

        expect(mismatched, 'keys whose placeholders differ between languages').toEqual([]);
    });

    it('the keys are not the same sentence in all four languages by accident of a copy (each is translated, bar words that are one in all)', () => {
        // Sentences only: a one-word label (a column named SHA-256) may legitimately be identical in every language.
        const untranslated = ['backup.list.sameDisk', 'backup.list.description', 'backup.cleanup.description', 'backup.cleanup.latestKept'].filter((key) => {
            const texts = new Set(LANGUAGES.map((language) => message(CATALOGUES[language], key)));
            return texts.size === 1;
        });

        expect(untranslated).toEqual([]);
    });
});
