/**
 * restoreI18n — every key the restore modules use is in the four catalogues (workstream B, lot B5b). Written red first
 * against `b5b-contract.md` §0, §3 and §5: the modules and their keys do not exist yet.
 *
 * The contract under test:
 *   - every key the four new modules name (restoreFlow.svelte.ts, RestoreCard.svelte, RestoreReportModal.svelte,
 *     RestartOverlay.svelte) is a message in the four catalogues, naming the same placeholders in each; a key the code
 *     builds from a prefix (`'backup.restore.errors.' + code`, `` `backup.restore.errors.${code}` ``) names a group
 *     that holds the same messages in the four; and the scan is not vacuous: it finds the keys §0 and §3 fix where they
 *     must be named;
 *   - the keys §0 and §3 fix: `backup.restore.confirm.words` gives at least 30 words in each language, each
 *     `^[a-z]{6,10}$`, separated by spaces, no duplicate (§0.4); `backup.restore.confirm.word`, the fallback of an empty
 *     list, is one such word; `backup.restore.report.linksExpired`, the one notice about links (P11), names no
 *     placeholder; `backup.restore.waiting.<waiting>` exists for the four waiting reasons, `instance_blocked` included
 *     (§0.5);
 *   - every code §5 lists has its message — a key of `backup.restore` ending with the code, the same keys in the four
 *     catalogues: the warnings of the check, the blocker, the rollback reasons, the phases of the check, the statuses of
 *     the ledger totals, the check's `RestoreErrorCode` list and the codes of the requests;
 *   - the success texts §0.6 removed (`last.committed`, `restart.restored*`, `restart.signIn`) are named by no module and
 *     held by no catalogue.
 *
 * How the keys are found: a quoted dotted name whose first segment is a namespace of the catalogue is a key, or a prefix
 * when it ends with a dot; the head of a template literal before `${` is a prefix. The names of the events
 * (`backup.restore.uploaded`, …) look like keys and are set aside. The scan reads the source as text, so it also counts
 * a key named in a comment — a key a comment names must exist too.
 *
 * The catalogues are the generated ones (`$lib/i18n/<lang>.json`), built from their sources (`lib/i18n/backup/*.json`)
 * before every Vitest run, as in `emailText.test.ts`: a case reads the presence of a key and the placeholders it names,
 * never its wording — except the words of the confirmation, whose form is the contract (§0.4).
 *
 * Node environment: nothing here renders.
 */
import {readFileSync} from 'node:fs';
import {describe, expect, it} from 'vitest';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};
const LANGUAGES = Object.keys(CATALOGUES);
const NAMESPACES = new Set(Object.keys(en));

const SOURCES = ['restoreFlow.svelte.ts', 'RestoreCard.svelte', 'RestoreReportModal.svelte', 'RestartOverlay.svelte'];

/** The names of the events of §2b: dotted like keys, and not keys. */
const EVENT_NAMES = new Set(['backup.restore.uploaded', 'backup.restore.staged', 'backup.restore.confirmed', 'backup.restore.cancelled', 'backup.restore.restart.requested', 'backup.restore.failed', 'backup.restore.restored', 'backup.restore.rolled_back']);

/** The success texts §0.6 removed. */
const REMOVED = /^backup\.restore\.(?:last\.committed|restart\.restored|restart\.signIn)/;

/** The waiting reasons of §0.5. */
const WAITINGS = ['backup_running', 'other_data_directory', 'server_running', 'instance_blocked'];

/** A word of the confirmation (§0.4). */
const WORD = /^[a-z]{6,10}$/;

/** The source of one of the new modules, or a failure that names it. */
function source(file: string): string {
    try {
        return readFileSync(new URL(`./${file}`, import.meta.url), 'utf8');
    } catch (error) {
        throw new Error(`src/lib/features/backup/${file} does not exist yet, or cannot be read (B5b contract §3): ${error instanceof Error ? error.message : String(error)}`);
    }
}

/** A quoted dotted name: a key (`'backup.restore.title'`), or a prefix when it ends with a dot. */
const QUOTED = /(['"`])([A-Za-z][\w-]*(?:\.[\w-]+)+\.?)\1/g;
/** The head of a template literal that builds a key: `` `backup.restore.errors.${code}` ``. */
const TEMPLATE_HEAD = /`([A-Za-z][\w-]*(?:\.[\w-]+)*\.)\$\{/g;

/** The keys a source names, and the prefixes it builds keys from. */
function namedKeys(text: string): {keys: string[]; prefixes: string[]} {
    const keys = new Set<string>();
    const prefixes = new Set<string>();
    for (const [, , name] of text.matchAll(QUOTED)) {
        if (!NAMESPACES.has(name.split('.')[0]) || EVENT_NAMES.has(name)) continue;
        if (name.endsWith('.')) prefixes.add(name.slice(0, -1));
        else keys.add(name);
    }
    for (const [, head] of text.matchAll(TEMPLATE_HEAD)) {
        if (NAMESPACES.has(head.split('.')[0])) prefixes.add(head.slice(0, -1));
    }
    return {keys: [...keys].sort(), prefixes: [...prefixes].sort()};
}

/** The node at a dotted path of a catalogue, or undefined. */
function messageOf(catalogue: unknown, key: string): unknown {
    let node = catalogue;
    for (const part of key.split('.')) node = node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined;
    return node;
}

const isGroup = (node: unknown): node is Record<string, unknown> => node !== null && typeof node === 'object';

/** The leaves below a node, as dotted paths that start with `prefix`. */
function leaves(node: unknown, prefix: string): string[] {
    if (!isGroup(node)) return [prefix];
    return Object.entries(node).flatMap(([name, child]) => leaves(child, `${prefix}.${name}`));
}

/** The ICU arguments a message names: `limit` for «larger than {limit} MB». */
function placeholdersOf(message: string): string[] {
    return [...new Set([...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1]))].sort();
}

/** `key` is a message in the four catalogues, naming the same placeholders in each. */
function expectMessage(key: string): void {
    let english: string[] | undefined;
    for (const language of LANGUAGES) {
        const message = messageOf(CATALOGUES[language], key);
        expect(typeof message, `${language}: ${key} is not a message of the catalogue`).toBe('string');
        const named = placeholdersOf(message as string);
        english ??= named;
        expect(named, `${language}: ${key} names other placeholders than in en`).toEqual(english);
    }
}

/** `prefix` is a group holding the same messages in the four catalogues, each named the same way. */
function expectGroup(prefix: string): void {
    const english = messageOf(en, prefix);
    expect(isGroup(english), `en: ${prefix} is not a group of messages`).toBe(true);
    const paths = leaves(english, prefix).sort();
    for (const language of LANGUAGES.slice(1)) {
        const group = messageOf(CATALOGUES[language], prefix);
        expect(isGroup(group), `${language}: ${prefix} is not a group of messages`).toBe(true);
        const found = leaves(group, prefix).sort();
        expect(found, `${language}: ${prefix} holds other messages than in en`).toEqual(paths);
    }
    for (const path of paths) expectMessage(path);
}

/** Every key of `backup.restore` in a catalogue. */
function restoreKeys(catalogue: unknown): string[] {
    const restore = messageOf(catalogue, 'backup.restore');
    return isGroup(restore) ? leaves(restore, 'backup.restore') : [];
}

// =====================================================================================================================
describe('the keys the restore modules name', () => {
    it.each(SOURCES)('%s: every key it names is a message of the four catalogues, with the same placeholders in each', (file) => {
        const {keys} = namedKeys(source(file));

        for (const key of keys) {
            if (isGroup(messageOf(en, key))) expectGroup(key);
            else expectMessage(key);
        }
    });

    it.each(SOURCES)('%s: every key it builds from a prefix names a group with the same messages in the four catalogues', (file) => {
        const {prefixes} = namedKeys(source(file));

        for (const prefix of prefixes) expectGroup(prefix);
    });

    it.each<[string, string[]]>([
        ['restoreFlow.svelte.ts', ['backup.restore.confirm.word']],
        ['RestoreReportModal.svelte', ['backup.restore.confirm.words', 'backup.restore.report.linksExpired']],
    ])('positive control: the scan finds in %s the keys §0 and §3 fix', (file, expected) => {
        const {keys} = namedKeys(source(file));

        for (const key of expected) expect(keys, `${file} does not name ${key}`).toContain(key);
    });

    it.each(['RestoreCard.svelte', 'RestartOverlay.svelte'])('positive control: the scan finds keys of backup.restore in %s', (file) => {
        const {keys, prefixes} = namedKeys(source(file));
        const restore = [...keys, ...prefixes].filter((name) => name.startsWith('backup.restore'));

        expect(restore.length, `the scan found no key of backup.restore in ${file}: it reads the wrong file, or misses its form`).toBeGreaterThan(0);
    });

    it.each(SOURCES)('%s names none of the success texts §0.6 removed', (file) => {
        const {keys, prefixes} = namedKeys(source(file));
        const removed = [...keys, ...prefixes].filter((name) => REMOVED.test(name));

        expect(removed).toEqual([]);
    });

    it.each(LANGUAGES)('%s: the catalogue holds none of the success texts §0.6 removed', (language) => {
        const removed = restoreKeys(CATALOGUES[language]).filter((key) => REMOVED.test(key));

        expect(removed).toEqual([]);
    });
});

describe('the keys §0 and §3 fix', () => {
    it.each(LANGUAGES)('%s: backup.restore.confirm.words gives at least 30 words, each ^[a-z]{6,10}$, separated by spaces, no duplicate (§0.4)', (language) => {
        const text = messageOf(CATALOGUES[language], 'backup.restore.confirm.words');
        expect(typeof text, `${language}: backup.restore.confirm.words is not a message`).toBe('string');
        const words = (text as string).split(' ').filter((word) => word !== '');
        const untypable = words.filter((word) => !WORD.test(word));

        expect(untypable, `${language}: words that cannot be typed as they are`).toEqual([]);
        expect(words.length, `${language}: fewer than 30 words`).toBeGreaterThanOrEqual(30);
        expect(new Set(words).size, `${language}: a word comes twice`).toBe(words.length);
    });

    it.each(LANGUAGES)('%s: backup.restore.confirm.word, the fallback of an empty list, is one such word (§0.4)', (language) => {
        const word = messageOf(CATALOGUES[language], 'backup.restore.confirm.word');

        expect(typeof word, `${language}: backup.restore.confirm.word is not a message`).toBe('string');
        expect(word as string).toMatch(WORD);
    });

    it('backup.restore.report.linksExpired, the one notice about links (P11): a message of the four catalogues, with no placeholder', () => {
        expectMessage('backup.restore.report.linksExpired');

        expect(placeholdersOf(messageOf(en, 'backup.restore.report.linksExpired') as string)).toEqual([]);
    });

    it.each(WAITINGS)('backup.restore.waiting.%s: a message of the four catalogues (§0.5)', (waiting) => {
        expectMessage(`backup.restore.waiting.${waiting}`);
    });
});

// =====================================================================================================================
/** The codes §5 lists, each needing a message, by what they name. */
const CODE_LISTS: Array<[string, string[]]> = [
    ['a warning of the check', ['rows_changed', 'foreign_key_violations', 'foreign_key_violations_added', 'control_totals_changed', 'control_totals_unreadable']],
    ['the blocker', ['no_administrator']],
    ['a rollback reason', ['first_start_failed', 'swap_interrupted', 'swap_failed', 'stage_missing']],
    ['a phase of the check', ['checking', 'unpacking', 'upgrading', 'verifying']],
    ['a status of the ledger totals', ['same', 'changed', 'absent', 'other_version', 'unreadable']],
    [
        'an error of the check',
        [
            'not_a_backup',
            'archive_unreadable',
            'archive_damaged',
            'manifest_newer_format',
            'manifest_invalid',
            'manifest_unreadable',
            'manifest_too_large',
            'too_many_entries',
            'duplicate_entry',
            'unexpected_entry',
            'not_a_file',
            'encrypted_entry',
            'unsupported_entry',
            'checksum_mismatch',
            'missing_entry',
            'no_space',
            'stage_failed',
            'database_damaged',
            'manifest_mismatch',
            'head_unknown',
            'revision_missing',
            'revision_unknown',
            'upgrade_failed',
            'post_migration_failed',
            'restore_interrupted',
            'restore_folder_unusable',
        ],
    ],
    [
        'an error of a request',
        [
            'backup_upload_empty',
            'backup_upload_incomplete',
            'backup_too_large',
            'backup_no_space',
            'backup_upload_unavailable',
            'backup_upload_failed',
            'backup_upload_not_found',
            'restore_busy',
            'restore_stage_running',
            'restore_stage_not_found',
            'restore_stage_expired',
            'restore_stage_outdated',
            'restore_not_restorable',
            'restore_already_pending',
            'restore_not_pending',
            'restore_pending',
            'network',
            'unexpected',
        ],
    ],
];

const CODES = CODE_LISTS.flatMap(([what, codes]) => codes.map((code): [string, string] => [what, code]));

describe('every code §5 lists has its message', () => {
    it.each(CODES)('%s, %s: a key of backup.restore ending with it, the same in the four catalogues', (_what, code) => {
        const english = restoreKeys(en).filter((key) => key.endsWith(`.${code}`));
        expect(english, `en: no key of backup.restore ends with .${code}`).not.toEqual([]);

        for (const language of LANGUAGES.slice(1)) {
            const keys = new Set(restoreKeys(CATALOGUES[language]));
            const missing = english.filter((key) => !keys.has(key));
            expect(missing, `${language}: the messages of ${code} that en has`).toEqual([]);
        }
    });
});
