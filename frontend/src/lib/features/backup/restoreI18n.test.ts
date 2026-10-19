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
import {ERROR_KEYS} from './restoreText';

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
    ['a warning of the check', ['rows_changed', 'foreign_key_violations', 'foreign_key_violations_added', 'control_totals_changed', 'control_totals_unreadable', 'non_iso_currencies']],
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
            // B-35: the archive's declared total, unpacked, above the instance's cap (checked before the free space).
            'unpacked_too_large',
            'no_space',
            'stage_failed',
            'database_damaged',
            'database_foreign_objects',
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
            // B-31: a confirmation, a cancellation or a restart the server could not carry out.
            'restore_confirm_failed',
            'restore_cancel_failed',
            'restore_restart_failed',
            // B-32: a state of the restore the server cannot read.
            'restore_state_unreadable',
            // B-35: the restore limit of the instance cannot be read, so no check starts.
            'backup_restore_unavailable',
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

// =====================================================================================================================
// B4 — the keys of the «secure» backup (B4 brief §7; written red first)
// =====================================================================================================================

/*
 * Every key B4 adds is a message of the four catalogues (`frontend/src/lib/i18n/backup/{en,it,fr,es}.json`, built into
 * the catalogues read here), naming the same placeholders in each. The names are this file's choice, made beside the
 * keys of today — `backup.download.phase.<phase>` and `backup.restore.phase.<phase>` as the phase maps of the two cards
 * build them, `backup.download.errors.<code>` and `backup.restore.errors.<code>` as their error maps do — and they are
 * the names the component tests of B4 read (BackupDownloadCard.test.ts, RestoreCard.test.ts,
 * RestoreReportModal.test.ts). The two lines of the report name one placeholder, `{count}`, the number they show.
 *
 * Red today: none of these keys exists. Two guards, green today: the download card and restoreText.ts — which holds
 * the restore's error keys, outside the sources scanned above — name no key missing from the four catalogues, so a
 * key B4 adds there and this list forgot is caught too.
 */

const B4_KEYS: Array<[string, string[]]> = [
    ['the two modes of the download card, and what each one means (decision 39)', ['backup.download.mode.clear', 'backup.download.mode.clearDescription', 'backup.download.mode.secure', 'backup.download.mode.secureDescription']],
    ['the password of a secure archive, asked twice', ['backup.download.password.label', 'backup.download.password.confirmLabel', 'backup.download.password.mismatch']],
    ['the phase that encrypts the archive', ['backup.download.phase.encrypting']],
    ['a password the server refuses for an archive', ['backup.download.errors.password_too_weak']],
    ['the password of an envelope to restore', ['backup.restore.password.label', 'backup.restore.password.submit', 'backup.restore.password.cancel']],
    ['the phase that decrypts the envelope on the server', ['backup.restore.phase.decrypting']],
    ['the refusals of an envelope', ['backup.restore.errors.wrong_password', 'backup.restore.errors.password_required', 'backup.restore.errors.envelope_damaged', 'backup.restore.errors.envelope_unsupported']],
    ['the plugin secrets of the checked copy', ['backup.restore.report.secretsRekeyed', 'backup.restore.report.secretsUnreadable']],
];

/** The two lines of the report and the one placeholder each names: the count it shows. */
const B4_COUNTED = ['backup.restore.report.secretsRekeyed', 'backup.restore.report.secretsUnreadable'];

/** The sources B4 adds keys to that the scan above does not read, and the names of events they hold: dotted like keys, and not keys. */
const B4_SOURCES = ['BackupDownloadCard.svelte', 'restoreText.ts'];
const DOWNLOAD_EVENT_NAMES = new Set(['backup.created', 'backup.failed', 'backup.delete.failed', 'backup.deleted', 'backup.download.started']);

describe('B4 — the keys of the secure backup', () => {
    it.each(B4_KEYS.flatMap(([what, keys]) => keys.map((key): [string, string] => [what, key])))('%s: %s is a message of the four catalogues, with the same placeholders in each', (_what, key) => {
        expectMessage(key);
    });

    it.each(B4_COUNTED)('%s names one placeholder, {count}, in the four catalogues', (key) => {
        expectMessage(key);

        expect(placeholdersOf(messageOf(en, key) as string)).toEqual(['count']);
    });

    it.each(B4_SOURCES)('%s: every key it names is a message of the four catalogues, with the same placeholders in each (green today: the guard)', (file) => {
        const keys = namedKeys(source(file)).keys.filter((key) => !DOWNLOAD_EVENT_NAMES.has(key));

        for (const key of keys) {
            if (isGroup(messageOf(en, key))) expectGroup(key);
            else expectMessage(key);
        }
    });

    it.each<[string, string]>([
        ['BackupDownloadCard.svelte', 'backup.download.phase.preparing'],
        ['restoreText.ts', 'backup.restore.errors.unexpected'],
    ])('positive control: the scan finds in %s a key of today, %s', (file, key) => {
        expect(namedKeys(source(file)).keys).toContain(key);
    });
});

// =====================================================================================================================
// B-28 — a database holding objects LibreFolio never creates is refused (written red first)
// =====================================================================================================================

/*
 * The check refuses an archive whose database holds triggers, views or other schema objects LibreFolio never creates:
 * `database_foreign_objects` (B-28 brief §1, §3), worded by restoreText.ts with `backup.restore.errors.<code>`, as every
 * error of the check. The lists above are written out, not derived from the generated `RestoreErrorCode`: the key is
 * required here by name. Red today: it does not exist.
 */
describe('B-28 — the refusal of a database holding objects LibreFolio never creates', () => {
    it('backup.restore.errors.database_foreign_objects is a message of the four catalogues, with the same placeholders in each', () => {
        expectMessage('backup.restore.errors.database_foreign_objects');
    });
});

// =====================================================================================================================
// B-16 — the hint of a server that never stops (written red first)
// =====================================================================================================================

/*
 * RestartOverlay.svelte words the hint `restart-not-stopped` by `backup.restore.restart.notStopped` (B-16 brief §2,
 * §3): a message of the four catalogues, naming no placeholder. Once the overlay names it, the scan of the restore
 * modules above requires it too. Red today: it does not exist.
 */
describe('B-16 — the hint of a server that never stops', () => {
    it('backup.restore.restart.notStopped is a message of the four catalogues, naming no placeholder', () => {
        expectMessage('backup.restore.restart.notStopped');

        expect(placeholdersOf(messageOf(en, 'backup.restore.restart.notStopped') as string)).toEqual([]);
    });
});

// =====================================================================================================================
// B-32 — a state of the restore the server cannot read (written red first)
// =====================================================================================================================

/*
 * `GET /backup/restore/status` answers 500 `restore_state_unreadable` when the server cannot read the state of the
 * restore (B-32 §3). restoreText.ts words it by `backup.restore.errors.restore_state_unreadable` (§4): a message of the
 * four catalogues naming no placeholder, as the English one of the contract names none. The code is also in the list
 * of the requests' errors above. Red today: neither the entry of `ERROR_KEYS` nor the key exists.
 */
describe('B-32 — a state of the restore the server cannot read', () => {
    it('ERROR_KEYS.restore_state_unreadable is backup.restore.errors.restore_state_unreadable, a message of the four catalogues naming no placeholder', () => {
        expect(ERROR_KEYS.restore_state_unreadable, 'restoreText.ts words the code').toBe('backup.restore.errors.restore_state_unreadable');

        expectMessage('backup.restore.errors.restore_state_unreadable');
        expect(placeholdersOf(messageOf(en, 'backup.restore.errors.restore_state_unreadable') as string)).toEqual([]);
    });
});

// =====================================================================================================================
// B-35 — an archive too large once unpacked; a restore limit the server cannot read (written red first)
// =====================================================================================================================

/*
 * The check refuses an archive whose declared total, unpacked, is above the instance's cap: `unpacked_too_large`, an
 * error of the check (B-35 §2). `POST /backup/restore/stage` answers 503 `backup_restore_unavailable` when that cap
 * cannot be read (§3). restoreText.ts words each by `backup.restore.errors.<code>` (§4): a message of the four
 * catalogues naming no placeholder, as the English ones of the contract name none. Both codes are also in the lists
 * above. Red today: neither the entries of `ERROR_KEYS` nor the keys exist.
 */
describe('B-35 — an archive too large once unpacked; a restore limit the server cannot read', () => {
    it.each(['unpacked_too_large', 'backup_restore_unavailable'])('ERROR_KEYS.%s is backup.restore.errors.<code>, a message of the four catalogues naming no placeholder', (code) => {
        const key = `backup.restore.errors.${code}`;
        expect(ERROR_KEYS[code], 'restoreText.ts words the code').toBe(key);

        expectMessage(key);
        expect(placeholdersOf(messageOf(en, key) as string)).toEqual([]);
    });
});

// =====================================================================================================================
// B-15 — a proxy's refusal of the archive (written red first)
// =====================================================================================================================

/*
 * A 413 the upload of an archive gets with no LibreFolio code comes from a proxy in front of LibreFolio (nginx's
 * `client_max_body_size`, Fly, a CDN), whose refusal LibreFolio's log knows nothing of: the page reads it as
 * `proxy_too_large` (B-15), worded by restoreText.ts with `backup.restore.errors.proxy_too_large`. A message of the four
 * catalogues naming no placeholder, as the English one of the contract names none: the proxy's limit is not known
 * (`errorLimitMb` null), so a `{limit}` would have nothing to show, in the card or in its toast. Once the entry exists,
 * the scan of restoreText.ts above (B4's guard) requires its key too; this case requires the entry itself, by name.
 * Red today: neither the entry of `ERROR_KEYS` nor the key exists.
 */
describe('B-15 — a proxy refused the archive', () => {
    it('ERROR_KEYS.proxy_too_large is backup.restore.errors.proxy_too_large, a message of the four catalogues naming no placeholder', () => {
        expect(ERROR_KEYS.proxy_too_large, 'restoreText.ts words the code').toBe('backup.restore.errors.proxy_too_large');

        expectMessage('backup.restore.errors.proxy_too_large');
        expect(placeholdersOf(messageOf(en, 'backup.restore.errors.proxy_too_large') as string)).toEqual([]);
    });
});
