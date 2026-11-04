// @vitest-environment jsdom
/**
 * RestoreReportModal — what a restore of the checked archive would do, and the typed confirmation (component test,
 * Vitest + jsdom; workstream B, lot B5b). Written red first against `b5b-contract.md` §0.4 (the confirmation word, P8),
 * §3 (the sections, P11) and §2b: the component does not exist yet.
 *
 * The contract under test:
 *   - the root `restore-report`; one test id per section: `restore-report-migrations` (each revision and message of an
 *     upgrade), `restore-report-tables` (only the tables whose rows changed), `restore-report-totals` with `data-status`
 *     (`same`, `changed`, `absent`, `other_version`, `unreadable`) and, for `changed`, one line per difference given,
 *     `restore-report-admins` (each administrator of the backup), `restore-report-links` (one notice, P11),
 *     `restore-report-warnings` (only with warnings), `restore-report-blocker` (only with the blocker);
 *   - L3 (workstream B, lot L3 CP1): `restore-report-warnings` lists every warning but `credentials_from_backup`
 *     (which every report ends with: `backup.restore.report.signInAgain` already says it, under the administrators)
 *     and `confirming_account_not_in_backup`, and is absent when no other warning is left; the second code draws
 *     `restore-report-own-account` instead (`role="alert"`, the danger roles, `backup.restore.report.ownAccountMissing`),
 *     absent without the code, never blocking the confirmation;
 *   - P11: one notice about the links, `restore-report-links`, worded by `backup.restore.report.linksExpired`, and
 *     nothing about accounts waiting for an email verification — no test id, no key;
 *   - the word (§0.4): picked once when the modal opens, `pickConfirmationWord(confirmationWords(<backup.restore.confirm
 *     .words>), random)`, so `words[Math.floor(random() × n)]` of the words that can be typed, the translated
 *     `backup.restore.confirm.word` when none can; shown in `restore-confirm-word`, `select-none`; typing does not pick
 *     again;
 *   - the field `restore-confirm-input`: `paste` and `drop` prevented, and `beforeinput` with `insertFromPaste`,
 *     `insertFromPasteAsQuotation` or `insertFromDrop` prevented; typing works (`insertText`, `deleteContentBackward`);
 *   - `restore-confirm` disabled until `confirmationMatches(typed, word)` (trimmed, case-insensitive) and the report is
 *     restorable; disabled whatever is typed with the blocker `no_administrator`, even if a report said restorable;
 *     disabled, like `restore-drop`, while `busy`; `onConfirm()` once on a click, `onDrop()` once on `restore-drop`.
 *
 * Props, the choice of this file where §3 names none: `open`, `report`, `busy`, `random` (§0.4), `onConfirm`, `onDrop`
 * and `onClose` (never pinned). A controlled modal: it confirms nothing itself, it calls back.
 *
 * The seams. `$lib/i18n` is a translator the test holds: it answers the word list and the fallback word the case set,
 * renders every other key as itself (with its values, when it has any), and records every key it is asked, so a case
 * can prove a key was — or was not — asked, never reading a sentence. `$lib/api` is a client that throws on any request:
 * the modal sends nothing. The words of the cases are this file's own, never the catalogue's.
 *
 * Additions to §3 this file pins, each one attribute or test id: a line of the ledger totals is
 * `restore-report-totals-line` with `data-kind` (§3 names the lines but gives them no handle). The names of the tables
 * are the raw table names of the report, read as the values the case passed in.
 *
 * The component is loaded through `import.meta.glob` in a hook: while it does not exist, every case fails on its own and
 * names it.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import type {Component} from 'svelte';
import type {z} from 'zod';
import type {schemas} from '$lib/api';
import {cleanup, fireEvent, render, screen, waitFor, within} from '$test/component';

const i18n = vi.hoisted(() => ({
    /** Every key the translator was asked, in order. */
    asked: [] as string[],
    /** What `backup.restore.confirm.words` answers. */
    words: 'garden ribbon violet window',
    /** What `backup.restore.confirm.word` answers: the fallback of an empty list. */
    fallback: 'meadow',
}));

vi.mock('$lib/i18n', () => {
    const translate = (key: string, options?: {values?: Record<string, unknown>}) => {
        i18n.asked.push(key);
        if (key === 'backup.restore.confirm.words') return i18n.words;
        if (key === 'backup.restore.confirm.word') return i18n.fallback;
        return options?.values ? `${key} ${JSON.stringify(options.values)}` : key;
    };
    const translator = readable(translate);
    return {
        _: translator,
        t: translator,
        locale: writable('en'),
        date: readable((value: unknown) => String(value)),
        time: readable((value: unknown) => String(value)),
        number: readable((value: unknown) => String(value)),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it', 'fr', 'es'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano', fr: 'Français', es: 'Español'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT', fr: 'FR', es: 'ES'},
        LANGUAGE_OPTIONS: [{code: 'en', name: 'English', flag: 'EN'}],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

// The modal sends nothing: any request would come through this client, and fails the case instead of leaving the page.
vi.mock('$lib/api', () => {
    const zodiosApi = new Proxy(
        {},
        {
            get: (_target, alias) =>
                typeof alias !== 'string' || alias === 'then'
                    ? undefined
                    : () => {
                          throw new Error(`RestoreReportModal.test: a request went through zodiosApi.${alias}`);
                      },
        },
    );
    return {zodiosApi, schemas: {}, axiosInstance: {}, ApiError: class ApiError extends Error {}};
});

type GeneratedStageReport = z.infer<typeof schemas.RestoreStageReport>;
/** L3: the two warnings of the accounts, written out until the client is generated again. */
type Warning = GeneratedStageReport['warnings'][number] | 'credentials_from_backup' | 'confirming_account_not_in_backup' | 'users_over_limit';
type RestoreStageReport = Omit<GeneratedStageReport, 'warnings'> & {warnings: Warning[]};
type Difference = RestoreStageReport['control_totals_differences'][number];

// --- The component ----------------------------------------------------------------------------------------------------

const MODAL_MODULES = import.meta.glob<{default: Component<Record<string, unknown>>}>('./RestoreReportModal.svelte');

let loaded: Component<Record<string, unknown>> | {error: unknown} | undefined;

beforeAll(async () => {
    try {
        const load = MODAL_MODULES['./RestoreReportModal.svelte'];
        if (!load) throw new Error('src/lib/features/backup/RestoreReportModal.svelte does not exist yet: the report of a checked archive has no modal (B5b contract §3)');
        loaded = (await load()).default;
    } catch (error) {
        loaded = {error};
    }
}, 60_000);

function modal(): Component<Record<string, unknown>> {
    if (loaded === undefined) throw new Error('RestoreReportModal was never loaded: its beforeAll did not run');
    if (typeof loaded === 'object' && 'error' in loaded) {
        const {error} = loaded;
        throw new Error(error instanceof Error ? error.message : String(error), {cause: error});
    }
    return loaded;
}

// --- Fixtures ---------------------------------------------------------------------------------------------------------

const MIB = 1024 * 1024;

const CASH_LINE: Difference = {kind: 'cash', broker_id: 7, currency: 'EUR', asset_id: null, before: '1000.00', after: '1250.50'};
const QUANTITY_LINE: Difference = {kind: 'quantity', broker_id: 7, currency: null, asset_id: 34, before: '10', after: '12'};

/** B4 (§5): what a report says of the archive's encryption and of the plugin secrets. Written out until the client is generated again. */
type ReportB4Fields = {encrypted: boolean; secrets_unreadable: {system: number; user: number}; secrets_rekeyed: number};

/** L3: the warning every report ends with, as the server sends it now. */
const CREDENTIALS = 'credentials_from_backup';
/** L3: the administrator confirming is not among the backup's administrators. */
const OWN_ACCOUNT = 'confirming_account_not_in_backup';

/**
 * An upgrade: two migrations, two tables changed and one not, the totals changed, two administrators, two warnings
 * shown, and `credentials_from_backup` last, as the server sends it in every report (L3).
 */
function report(overrides: Partial<RestoreStageReport & ReportB4Fields> = {}): RestoreStageReport & ReportB4Fields {
    return {
        backup_created_at: '2026-10-15T12:00:00Z',
        backup_app_version: '0.8.2',
        backup_origin: 'ui',
        backup_revision: 'a1b2c3d4e5f6',
        app_version: '0.9.0',
        head_revision: 'f6e5d4c3b2a1',
        action: 'upgrade',
        migrations: [
            {revision: 'b7c8d9e0f1a2', message: 'add broker report sets'},
            {revision: 'f6e5d4c3b2a1', message: 'add the restore state'},
        ],
        post_migration_fixes: ['recomputed_cash_balances'],
        tables: {
            price_history: {before: 1200, after: 1260},
            fx_rate: {before: null, after: 40},
            broker_user_access: {before: 3, after: 3},
        },
        foreign_key_violations_before: 0,
        foreign_key_violations_after: 0,
        files: 12,
        files_size: 3 * MIB,
        database_size: 8 * MIB,
        instance_key_included: true,
        administrators: ['giulia.bianchi', 'operator7'],
        warnings: ['rows_changed', 'control_totals_changed', CREDENTIALS],
        blockers: [],
        control_totals: 'changed',
        control_totals_differences: [CASH_LINE, QUANTITY_LINE],
        control_totals_differences_count: 2,
        restorable: true,
        expires_at: '2026-10-16T12:00:00Z',
        encrypted: false,
        secrets_unreadable: {system: 0, user: 0},
        secrets_rekeyed: 0,
        ...overrides,
    };
}

/** The modal open on `answer`, with the callbacks as spies; `random` picks the third of four words unless told otherwise. */
function mount(answer: RestoreStageReport = report(), props: Record<string, unknown> = {}) {
    const onConfirm = vi.fn();
    const onDrop = vi.fn();
    const onClose = vi.fn();
    const random = vi.fn(() => 0.5);
    const view = render(modal(), {props: {open: true, report: answer, busy: false, random, onConfirm, onDrop, onClose, ...props}});
    return {...view, onConfirm, onDrop, onClose, random};
}

const section = (testId: string) => within(screen.getByTestId('restore-report')).getByTestId(testId);
const confirmButton = () => screen.getByTestId('restore-confirm');
const field = () => screen.getByTestId('restore-confirm-input');

async function type(text: string): Promise<void> {
    await fireEvent.input(field(), {target: {value: text}});
}

beforeEach(() => {
    i18n.asked.length = 0;
    i18n.words = 'garden ribbon violet window';
    i18n.fallback = 'meadow';
});

afterEach(() => {
    cleanup();
});

// =====================================================================================================================
describe('RestoreReportModal — the sections', () => {
    it('a full report: every section by its test id, the confirmation, and no blocker', () => {
        mount();

        const root = screen.getByTestId('restore-report');
        for (const testId of ['restore-report-migrations', 'restore-report-tables', 'restore-report-totals', 'restore-report-admins', 'restore-report-links', 'restore-report-warnings', 'restore-confirm-word', 'restore-confirm-input', 'restore-confirm', 'restore-drop']) {
            expect(within(root).getByTestId(testId), `${testId} is missing from the report`).toBeInTheDocument();
        }
        expect(within(root).queryByTestId('restore-report-blocker'), 'a report without a blocker shows one').toBeNull();
    });

    it('the migrations of an upgrade: each revision and its message', () => {
        mount();

        const migrations = section('restore-report-migrations');
        for (const {revision, message} of report().migrations) {
            expect(migrations).toHaveTextContent(revision);
            expect(migrations).toHaveTextContent(message);
        }
    });

    it('the tables: only those whose rows changed', () => {
        mount();

        const tables = section('restore-report-tables');
        expect(tables).toHaveTextContent('price_history');
        expect(tables, 'a table that the backup did not have is a change').toHaveTextContent('fx_rate');
        expect(tables, 'a table whose rows did not change is listed').not.toHaveTextContent('broker_user_access');
    });

    it.each<[RestoreStageReport['control_totals'], Partial<RestoreStageReport>]>([
        ['same', {control_totals: 'same', control_totals_differences: [], control_totals_differences_count: 0, warnings: [CREDENTIALS]}],
        ['absent', {control_totals: 'absent', control_totals_differences: [], control_totals_differences_count: 0, warnings: [CREDENTIALS]}],
        ['other_version', {control_totals: 'other_version', control_totals_differences: [], control_totals_differences_count: 0, warnings: [CREDENTIALS]}],
        ['unreadable', {control_totals: 'unreadable', control_totals_differences: [], control_totals_differences_count: 0, warnings: ['control_totals_unreadable', CREDENTIALS]}],
    ])('the ledger totals %s: data-status, and no difference line', (status, overrides) => {
        mount(report(overrides));

        const totals = section('restore-report-totals');
        expect(totals).toHaveAttribute('data-status', status);
        expect(within(totals).queryAllByTestId('restore-report-totals-line')).toHaveLength(0);
    });

    it('the ledger totals changed: data-status changed, and one line per difference given, in order, with its kind', () => {
        mount();

        const totals = section('restore-report-totals');
        expect(totals).toHaveAttribute('data-status', 'changed');
        const lines = within(totals).getAllByTestId('restore-report-totals-line');
        expect(lines.map((line) => line.getAttribute('data-kind'))).toEqual(['cash', 'quantity']);
    });

    it('the administrators of the backup: each one named', () => {
        mount();

        const admins = section('restore-report-admins');
        expect(admins).toHaveTextContent('giulia.bianchi');
        expect(admins).toHaveTextContent('operator7');
    });

    it('P11: one notice about the links, and nothing about accounts waiting for an email verification', () => {
        mount();

        const root = screen.getByTestId('restore-report');
        const notices = within(root).getAllByTestId('restore-report-links');
        expect(notices, 'one notice about the links, nothing more').toHaveLength(1);
        expect(notices[0]).toHaveTextContent('backup.restore.report.linksExpired');
        expect(i18n.asked).toContain('backup.restore.report.linksExpired');
        const verificationIds = [...root.querySelectorAll('[data-testid]')].map((element) => element.getAttribute('data-testid') ?? '').filter((testId) => /verif/i.test(testId));
        expect(verificationIds, 'an element about accounts waiting for a verification').toEqual([]);
        expect(
            i18n.asked.filter((key) => /verif/i.test(key)),
            'a key about accounts waiting for a verification',
        ).toEqual([]);
    });

    it('the warnings: shown with the warnings, absent without (L3: credentials_from_backup alone is none)', () => {
        const withWarnings = mount();
        expect(section('restore-report-warnings')).toBeInTheDocument();
        withWarnings.unmount();

        mount(report({warnings: [CREDENTIALS]}));
        expect(within(screen.getByTestId('restore-report')).queryByTestId('restore-report-warnings')).toBeNull();
    });
});

// =====================================================================================================================
describe('RestoreReportModal — the word to type (§0.4)', () => {
    it('picked once when the modal opens, from backup.restore.confirm.words, and shown in restore-confirm-word (select-none); typing does not pick again', async () => {
        const {random} = mount();

        const word = screen.getByTestId('restore-confirm-word');
        expect(word).toHaveTextContent(/^\s*violet\s*$/);
        expect(word, 'the word must not be selectable, so it cannot be copied').toHaveClass('select-none');
        expect(i18n.asked).toContain('backup.restore.confirm.words');
        expect(random).toHaveBeenCalledTimes(1);

        await type('vio');
        await type('viol');

        expect(random, 'typing picked another word').toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('restore-confirm-word')).toHaveTextContent(/^\s*violet\s*$/);
    });

    it.each<[number, string]>([
        [0, 'garden'],
        [0.25, 'ribbon'],
        [0.999, 'window'],
    ])('random() = %s: the word is %s', (value, expected) => {
        mount(report(), {random: () => value});

        expect(screen.getByTestId('restore-confirm-word')).toHaveTextContent(new RegExp(`^\\s*${expected}\\s*$`));
    });

    it('only the words that can be typed are picked from', () => {
        i18n.words = 'Garden apple jardín violet backgrounds';

        mount(report(), {random: () => 0.999});

        expect(screen.getByTestId('restore-confirm-word')).toHaveTextContent(/^\s*violet\s*$/);
    });

    it('a list with no word that can be typed: the translated backup.restore.confirm.word', () => {
        i18n.words = 'Garden apple';

        mount();

        expect(screen.getByTestId('restore-confirm-word')).toHaveTextContent(/^\s*meadow\s*$/);
    });
});

describe('RestoreReportModal — the field: typed, never pasted (§0.4)', () => {
    function beforeInput(inputType: string): Event {
        const event = new InputEvent('beforeinput', {inputType, bubbles: true, cancelable: true});
        // An older jsdom drops inputType from the init: the property is what the field reads.
        if (event.inputType !== inputType) Object.defineProperty(event, 'inputType', {value: inputType});
        return event;
    }

    it.each<[string, () => Event]>([
        ['paste', () => new Event('paste', {bubbles: true, cancelable: true})],
        ['drop', () => new Event('drop', {bubbles: true, cancelable: true})],
        ['beforeinput insertFromPaste', () => beforeInput('insertFromPaste')],
        ['beforeinput insertFromPasteAsQuotation', () => beforeInput('insertFromPasteAsQuotation')],
        ['beforeinput insertFromDrop', () => beforeInput('insertFromDrop')],
    ])('%s is prevented', (_case, make) => {
        mount();
        const event = make();

        field().dispatchEvent(event);

        expect(event.defaultPrevented, 'the word could be pasted instead of typed').toBe(true);
    });

    it.each(['insertText', 'deleteContentBackward'])('beforeinput %s is not prevented: typing works', (inputType) => {
        mount();
        const event = beforeInput(inputType);

        field().dispatchEvent(event);

        expect(event.defaultPrevented).toBe(false);
    });
});

describe('RestoreReportModal — confirm and drop', () => {
    it('confirm disabled until the word is typed, then onConfirm() once on a click', async () => {
        const {onConfirm, onDrop} = mount();
        expect(confirmButton(), 'nothing typed yet').toBeDisabled();

        await type('garden');
        expect(confirmButton(), 'another word of the list').toBeDisabled();

        await type('violet');
        expect(confirmButton()).toBeEnabled();

        await fireEvent.click(confirmButton());

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onDrop).not.toHaveBeenCalled();
    });

    it.each(['  violet ', 'VIOLET', 'Violet', '\tviolet\n'])('typed %j: the word, trimmed and in any case — confirm enabled', async (typed) => {
        mount();

        await type(typed);

        expect(confirmButton()).toBeEnabled();
    });

    it.each(['', '   ', 'violets', 'violét', 'vio let', 'viole'])('typed %j: not the word — confirm disabled', async (typed) => {
        mount();

        await type(typed);

        expect(confirmButton()).toBeDisabled();
    });

    it('an archive that cannot be restored: confirm disabled whatever is typed', async () => {
        mount(report({restorable: false}));

        await type('violet');

        expect(confirmButton()).toBeDisabled();
    });

    it.each<[string, boolean]>([
        ['not restorable, as the server says it', false],
        ['even if a report said restorable', true],
    ])('the blocker no_administrator (%s): restore-report-blocker, confirm disabled whatever is typed', async (_case, restorable) => {
        const {onConfirm} = mount(report({blockers: ['no_administrator'], administrators: [], restorable}));

        expect(section('restore-report-blocker')).toBeInTheDocument();
        await type('violet');

        expect(confirmButton()).toBeDisabled();
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('busy (the confirmation is out): confirm and drop disabled, even with the word typed', async () => {
        const view = mount();
        await type('violet');
        expect(confirmButton(), 'precondition: the word matches').toBeEnabled();

        await view.rerender({open: true, report: report(), busy: true, random: view.random, onConfirm: view.onConfirm, onDrop: view.onDrop, onClose: view.onClose});

        expect(confirmButton()).toBeDisabled();
        expect(screen.getByTestId('restore-drop')).toBeDisabled();
    });

    it('drop: onDrop() once on a click, never onConfirm()', async () => {
        const {onConfirm, onDrop} = mount();

        await fireEvent.click(screen.getByTestId('restore-drop'));

        expect(onDrop).toHaveBeenCalledTimes(1);
        expect(onConfirm).not.toHaveBeenCalled();
    });
});

// =====================================================================================================================
// B4 — the plugin secrets of the checked copy (B4 brief §5, §7; written red first)
// =====================================================================================================================

/*
 * The contract: the report says how many plugin secrets of the copy were re-encrypted with this instance's key
 * (`secrets_rekeyed`, from an archive that carried its key) and how many cannot be read with it
 * (`secrets_unreadable.system` + `.user`). The modal draws `restore-report-secrets-rekeyed` when `secrets_rekeyed > 0`
 * and `restore-report-secrets-unreadable` when the two unreadable counts add up to more than 0, each with `data-count`;
 * neither line otherwise.
 *
 * Choices of this file where the contract is silent, each one place to change: the lines are worded by
 * `backup.restore.report.secretsRekeyed` and `backup.restore.report.secretsUnreadable`, given the count they show as
 * `{count}` (the translator of this file prints the values it is given after the key).
 *
 * Red today: the modal knows neither count, so it draws neither line. The cases of a count of 0 are green today (the
 * guards of «absent at 0»), with the links notice as their presence barrier.
 */

/** The values a line was worded with: the translator renders `key {"name":value}`. */
function valuesOf(line: HTMLElement, key: string): Record<string, unknown> {
    const text = line.textContent ?? '';
    const at = text.indexOf(`${key} {`);
    expect(at, `the line is not worded by ${key} with its values: ${JSON.stringify(text)}`).toBeGreaterThanOrEqual(0);
    const json = text.slice(at + key.length + 1);
    return JSON.parse(json.slice(0, json.lastIndexOf('}') + 1)) as Record<string, unknown>;
}

describe('B4 — RestoreReportModal: the plugin secrets of the checked copy', () => {
    const root = () => screen.getByTestId('restore-report');

    it('secrets_rekeyed 3: restore-report-secrets-rekeyed with data-count 3, worded by backup.restore.report.secretsRekeyed with the count', () => {
        mount(report({secrets_rekeyed: 3}));

        const line = within(root()).getByTestId('restore-report-secrets-rekeyed');
        expect(line).toHaveAttribute('data-count', '3');
        expect(valuesOf(line, 'backup.restore.report.secretsRekeyed')).toMatchObject({count: 3});
    });

    it.each<[string, {system: number; user: number}, number]>([
        ['of the system and of the users', {system: 2, user: 3}, 5],
        ['of the system only', {system: 1, user: 0}, 1],
        ['of the users only', {system: 0, user: 4}, 4],
    ])('secrets unreadable %s: restore-report-secrets-unreadable with data-count the sum, worded by backup.restore.report.secretsUnreadable with it', (_case, unreadable, total) => {
        mount(report({secrets_unreadable: unreadable}));

        const line = within(root()).getByTestId('restore-report-secrets-unreadable');
        expect(line).toHaveAttribute('data-count', String(total));
        expect(valuesOf(line, 'backup.restore.report.secretsUnreadable')).toMatchObject({count: total});
    });

    it('both counts at once: the two lines, each with its own count', () => {
        mount(report({secrets_rekeyed: 6, secrets_unreadable: {system: 1, user: 1}}));

        expect(within(root()).getByTestId('restore-report-secrets-rekeyed')).toHaveAttribute('data-count', '6');
        expect(within(root()).getByTestId('restore-report-secrets-unreadable')).toHaveAttribute('data-count', '2');
    });

    it('no secret re-encrypted and none unreadable: neither line (green today: the guard)', () => {
        mount(report({secrets_rekeyed: 0, secrets_unreadable: {system: 0, user: 0}}));

        // The presence barrier: the report drew its sections.
        expect(within(root()).getByTestId('restore-report-links')).toBeInTheDocument();
        expect(within(root()).queryByTestId('restore-report-secrets-rekeyed')).toBeNull();
        expect(within(root()).queryByTestId('restore-report-secrets-unreadable')).toBeNull();
    });
});

// =====================================================================================================================
// L3 CP1 — the warnings of the accounts (workstream B, lot L3; written red first)
// =====================================================================================================================

/*
 * The contract: every report the server sends ends with the warning `credentials_from_backup` (after the restart, the
 * accounts and passwords are the backup's). `backup.restore.report.signInAgain`, under the administrators, already
 * says it: the yellow box `restore-report-warnings` does not list it, and is not drawn when it is the only warning.
 *
 * `confirming_account_not_in_backup`: the administrator reading the report is not among the backup's administrators,
 * so after the restart this account cannot sign in. Not a line of the yellow box: a strong alert of its own,
 * `restore-report-own-account`, `role="alert"`, in the danger roles (`bg-lf-danger-soft`), worded by
 * `backup.restore.report.ownAccountMissing`. Absent without the code. It does not block: a restorable report with no
 * blocker can still be confirmed.
 *
 * Red today: the box lists both codes (as the `unknown` warning) and nothing draws the alert. The case «absent without
 * the code» is green today: the guard.
 */

describe('L3 — RestoreReportModal: the warnings of the accounts', () => {
    const root = () => screen.getByTestId('restore-report');
    const listed = () =>
        within(section('restore-report-warnings'))
            .getAllByTestId('restore-report-warning')
            .map((line) => line.getAttribute('data-warning'));

    it('credentials_from_backup is not a line of the yellow box: the other warnings are, in order', () => {
        mount();

        expect(listed()).toEqual(['rows_changed', 'control_totals_changed']);
        expect(root().querySelector(`[data-warning="${CREDENTIALS}"]`), 'credentials_from_backup drawn as a warning').toBeNull();
        expect(i18n.asked, 'a warning shown as the unknown fallback').not.toContain('backup.restore.report.warning.unknown');
    });

    it('credentials_from_backup the only warning: no yellow box, and the administrators still say to sign in again', () => {
        mount(report({warnings: [CREDENTIALS]}));

        // The presence barrier: the section that already says it is drawn.
        expect(within(root()).getByTestId('restore-report-admins')).toHaveTextContent('backup.restore.report.signInAgain');
        expect(within(root()).queryByTestId('restore-report-warnings')).toBeNull();
    });

    it('confirming_account_not_in_backup: restore-report-own-account, role alert, the danger roles, worded by backup.restore.report.ownAccountMissing', () => {
        mount(report({warnings: ['rows_changed', OWN_ACCOUNT, CREDENTIALS]}));

        const alert = within(root()).getByTestId('restore-report-own-account');
        expect(alert).toHaveAttribute('role', 'alert');
        expect(alert.className, 'the alert is not drawn in the danger roles').toContain('bg-lf-danger-soft');
        expect(alert).toHaveTextContent('backup.restore.report.ownAccountMissing');
        expect(i18n.asked).toContain('backup.restore.report.ownAccountMissing');
    });

    it('confirming_account_not_in_backup is not a line of the yellow box', () => {
        mount(report({warnings: ['rows_changed', OWN_ACCOUNT, CREDENTIALS]}));

        expect(within(root()).getByTestId('restore-report-own-account')).toBeInTheDocument();
        expect(listed()).toEqual(['rows_changed']);
        expect(root().querySelector(`[data-warning="${OWN_ACCOUNT}"]`), 'confirming_account_not_in_backup drawn as a warning').toBeNull();
    });

    it('confirming_account_not_in_backup and credentials_from_backup only: the alert, and no yellow box', () => {
        mount(report({warnings: [OWN_ACCOUNT, CREDENTIALS]}));

        expect(within(root()).getByTestId('restore-report-own-account')).toBeInTheDocument();
        expect(within(root()).queryByTestId('restore-report-warnings')).toBeNull();
    });

    it('without the code: no restore-report-own-account (green today: the guard)', () => {
        mount();

        // The presence barrier: the report drew its sections, the yellow box included.
        expect(within(root()).getByTestId('restore-report-warnings')).toBeInTheDocument();
        expect(within(root()).queryByTestId('restore-report-own-account')).toBeNull();
        expect(i18n.asked).not.toContain('backup.restore.report.ownAccountMissing');
    });

    it('confirming_account_not_in_backup does not block: a restorable report with no blocker is confirmed with the word', async () => {
        const {onConfirm} = mount(report({warnings: [OWN_ACCOUNT, CREDENTIALS], restorable: true, blockers: []}));
        expect(within(root()).getByTestId('restore-report-own-account'), 'precondition: the alert is drawn').toBeInTheDocument();
        expect(within(root()).queryByTestId('restore-report-blocker')).toBeNull();

        expect(field()).toBeEnabled();
        await type('violet');
        expect(confirmButton()).toBeEnabled();
        await fireEvent.click(confirmButton());

        expect(onConfirm).toHaveBeenCalledTimes(1);
    });
});

// =====================================================================================================================
// B5-1b — the owner's choice when confirming a restore (interface B-b51 §8; written red first)
// =====================================================================================================================

/*
 * The contract: `onConfirm: (ownerUserId: number | null) => void`.
 *   - `report.owner_choice` null or absent: as today, the word typed then `restore-confirm` → `onConfirm(null)`, and no
 *     `owner-choice-modal`;
 *   - present: `restore-confirm` (same word rule) does not call `onConfirm`: it opens `OwnerChoiceModal`
 *     (`owner-choice-modal`) with `ownerEmail = owner_choice.owner_email` and as `users` only the candidate whose
 *     `user_id === forced_user_id` when that is not null, otherwise the candidates with `administrator === true`, each
 *     mapped `{id: user_id, username, email: email ?? '', is_superuser, is_active}`; `busy` passed through. Its confirm
 *     closes it and calls `onConfirm(id)` once; its cancel closes it, confirms nothing, and leaves the report open with
 *     the word typed.
 *
 * OwnerChoiceModal.svelte is workstream A's (its real component since the merge): it is driven only through
 * A's handles — `owner-choice-option` with `data-user-id` and `data-selected` (a click selects), `owner-choice-confirm`,
 * `owner-choice-cancel`, and `data-locked` on `owner-choice-modal` (the owner's address is one of the users': only that
 * one can be chosen). `ownerEmail` and the mapped `email` are seen through `data-locked`, which A's modal derives from
 * them; nothing reads its text or its classes.
 *
 * Choice of this file where §8 is silent: the users keep the order of `owner_choice.candidates`. A candidate that is
 * neither an administrator nor the owner's address cannot come from the server (the check selects only those), but one
 * is in the fixture to pin the filter `administrator === true` on its own.
 *
 * Red today: the modal calls `onConfirm()` with no argument and knows no `owner_choice`, so no owner modal ever opens.
 * The guards (green today): a report the word does not unlock opens nothing.
 */

/** The generated type also admits an array (an artefact of the OpenAPI union): the object is the contract. */
type OwnerChoice = Exclude<NonNullable<GeneratedStageReport['owner_choice']>, unknown[]>;
type OwnerCandidate = OwnerChoice['candidates'][number];

const OWNER_EMAIL = 'owner@example.org';

const ADMIN_GIULIA: OwnerCandidate = {user_id: 3, username: 'giulia.bianchi', email: 'giulia@example.org', owner_email: false, administrator: true, is_superuser: true, is_active: true};
/** An administrator without an address: mapped with `email: ''`. */
const ADMIN_NO_EMAIL: OwnerCandidate = {user_id: 7, username: 'operator7', email: null, owner_email: false, administrator: true, is_superuser: true, is_active: true};
/** Neither an administrator nor the owner's address (see the docblock): never offered. */
const NOT_OFFERED: OwnerCandidate = {user_id: 5, username: 'former.admin', email: 'former@example.org', owner_email: false, administrator: false, is_superuser: true, is_active: false};
/** The account whose address is the owner's, in another case: the forced choice. */
const OWNER_ACCOUNT: OwnerCandidate = {user_id: 9, username: 'owner.mailbox', email: 'Owner@Example.org', owner_email: true, administrator: false, is_superuser: false, is_active: true};

function ownerChoice(overrides: Partial<OwnerChoice> = {}): OwnerChoice {
    return {required: true, owner_email: OWNER_EMAIL, forced_user_id: null, candidates: [ADMIN_GIULIA, NOT_OFFERED, ADMIN_NO_EMAIL], ...overrides};
}

const forcedChoice = () => ownerChoice({forced_user_id: OWNER_ACCOUNT.user_id, candidates: [ADMIN_GIULIA, OWNER_ACCOUNT, ADMIN_NO_EMAIL]});

const ownerModal = () => screen.getByTestId('owner-choice-modal');
const offered = () =>
    within(ownerModal())
        .getAllByTestId('owner-choice-option')
        .map((option) => Number(option.getAttribute('data-user-id')));
const option = (userId: number) => {
    const found = within(ownerModal())
        .getAllByTestId('owner-choice-option')
        .filter((element) => element.getAttribute('data-user-id') === String(userId));
    expect(found, `no owner-choice-option for the user ${userId}`).toHaveLength(1);
    return found[0];
};

/** The word typed and `restore-confirm` clicked. */
async function typeAndConfirm(): Promise<void> {
    await type('violet');
    expect(confirmButton(), 'precondition: the word unlocks the confirmation').toBeEnabled();
    await fireEvent.click(confirmButton());
}

/** The report of `choice`, the word typed and confirmed: the owner modal open. */
async function ownerModalOpen(choice: OwnerChoice = ownerChoice(), props: Record<string, unknown> = {}) {
    const view = mount(report({owner_choice: choice}), props);
    await typeAndConfirm();
    expect(screen.getByTestId('owner-choice-modal'), 'precondition: the owner modal is open').toBeInTheDocument();
    return view;
}

describe('B5-1b — RestoreReportModal: no owner to choose (self-hosted)', () => {
    it.each<[string, Partial<RestoreStageReport>]>([
        ['owner_choice absent', {}],
        ['owner_choice null', {owner_choice: null}],
    ])('%s: the word typed, restore-confirm → onConfirm(null) once, and no owner modal', async (_case, overrides) => {
        const {onConfirm} = mount(report(overrides));

        await typeAndConfirm();

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm, 'a confirmation without an owner names none: null').toHaveBeenCalledWith(null);
        expect(screen.queryByTestId('owner-choice-modal')).toBeNull();
    });

    it('owner_choice absent: Enter in the field confirms with onConfirm(null)', async () => {
        const {onConfirm} = mount();
        await type('violet');

        await fireEvent.keyDown(field(), {key: 'Enter'});

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith(null);
    });
});

describe('B5-1b — RestoreReportModal: the owner to choose (managed)', () => {
    it('restore-confirm with the word typed does not confirm: it opens owner-choice-modal', async () => {
        const {onConfirm} = mount(report({owner_choice: ownerChoice()}));

        await typeAndConfirm();

        expect(onConfirm, 'the restore was confirmed before the owner was chosen').not.toHaveBeenCalled();
        expect(screen.getByTestId('owner-choice-modal')).toBeInTheDocument();
        expect(screen.getByTestId('restore-report'), 'the report stays under the owner modal').toBeInTheDocument();
    });

    it('Enter in the field does not confirm either: it opens owner-choice-modal', async () => {
        const {onConfirm} = mount(report({owner_choice: ownerChoice()}));
        await type('violet');

        await fireEvent.keyDown(field(), {key: 'Enter'});

        expect(onConfirm).not.toHaveBeenCalled();
        expect(screen.getByTestId('owner-choice-modal')).toBeInTheDocument();
    });

    it.each<[string, Partial<RestoreStageReport & ReportB4Fields>, string]>([
        ['nothing typed', {}, ''],
        ['another word typed', {}, 'garden'],
        ['an archive that cannot be restored', {restorable: false}, 'violet'],
    ])('the word rule still holds — %s: restore-confirm disabled, no owner modal (green today: the guard)', async (_case, overrides, typed) => {
        const {onConfirm} = mount(report({owner_choice: ownerChoice(), ...overrides}));
        await type(typed);

        expect(confirmButton()).toBeDisabled();
        await fireEvent.click(confirmButton());
        await fireEvent.keyDown(field(), {key: 'Enter'});

        expect(screen.queryByTestId('owner-choice-modal')).toBeNull();
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it.each<[string, () => OwnerChoice]>([
        ['an owner to choose among administrators', () => ownerChoice()],
        ['the owner account forced (a plain user holding the owner address, no active administrator)', () => forcedChoice()],
    ])('the blocker no_administrator with an owner choice (%s): the blocker is shown, the word cannot be typed, nothing confirms and no owner modal opens (B5-1g: green today, a guard)', async (_case, choice) => {
        const {onConfirm} = mount(report({blockers: ['no_administrator'], administrators: [], restorable: false, owner_choice: choice()}));

        expect(section('restore-report-blocker')).toBeInTheDocument();
        expect(field(), 'the field is closed while the archive cannot be restored').toBeDisabled();
        await type('violet');
        expect(confirmButton()).toBeDisabled();
        await fireEvent.click(confirmButton());
        await fireEvent.keyDown(field(), {key: 'Enter'});

        expect(screen.queryByTestId('owner-choice-modal'), 'the owner is never asked for an archive that cannot be restored').toBeNull();
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('forced_user_id null: the users are the administrators among the candidates, in their order — nothing locked', async () => {
        await ownerModalOpen();

        expect(offered(), 'the users offered as the owner').toEqual([ADMIN_GIULIA.user_id, ADMIN_NO_EMAIL.user_id]);
        expect(ownerModal(), 'no user has the owner address: nothing is forced').toHaveAttribute('data-locked', 'false');
    });

    it('forced_user_id set: only that candidate, mapped with its address — locked on it, selected', async () => {
        await ownerModalOpen(forcedChoice());

        expect(offered(), 'a forced owner leaves no other choice').toEqual([OWNER_ACCOUNT.user_id]);
        expect(ownerModal(), 'ownerEmail and the candidate email reached the modal: it locks on the owner address').toHaveAttribute('data-locked', 'true');
        expect(option(OWNER_ACCOUNT.user_id)).toHaveAttribute('data-selected', 'true');
    });

    it('an administrator chosen, then owner-choice-confirm: the owner modal closes and onConfirm(id) is called once', async () => {
        const {onConfirm} = await ownerModalOpen();

        await fireEvent.click(option(ADMIN_NO_EMAIL.user_id));
        expect(option(ADMIN_NO_EMAIL.user_id), 'precondition: the click selected it').toHaveAttribute('data-selected', 'true');
        await fireEvent.click(within(ownerModal()).getByTestId('owner-choice-confirm'));

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith(ADMIN_NO_EMAIL.user_id);
        await waitFor(() => expect(screen.queryByTestId('owner-choice-modal')).toBeNull());
    });

    it('the forced owner, owner-choice-confirm: onConfirm(forced_user_id) once', async () => {
        const {onConfirm} = await ownerModalOpen(forcedChoice());

        await fireEvent.click(within(ownerModal()).getByTestId('owner-choice-confirm'));

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith(OWNER_ACCOUNT.user_id);
        await waitFor(() => expect(screen.queryByTestId('owner-choice-modal')).toBeNull());
    });

    it('owner-choice-cancel: the owner modal closes, nothing confirmed, the report still open with the word typed — and confirm opens it again', async () => {
        const {onConfirm, onClose} = await ownerModalOpen();

        await fireEvent.click(within(ownerModal()).getByTestId('owner-choice-cancel'));

        await waitFor(() => expect(screen.queryByTestId('owner-choice-modal')).toBeNull());
        expect(onConfirm).not.toHaveBeenCalled();
        expect(onClose, 'cancelling the owner closed the report').not.toHaveBeenCalled();
        expect(screen.getByTestId('restore-report')).toBeInTheDocument();
        expect(field(), 'the word typed was lost').toHaveValue('violet');
        expect(confirmButton()).toBeEnabled();

        await fireEvent.click(confirmButton());

        expect(screen.getByTestId('owner-choice-modal'), 'confirm again: the owner modal again').toBeInTheDocument();
        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('busy is passed through: while the confirmation is out, owner-choice-confirm is disabled', async () => {
        const view = await ownerModalOpen(forcedChoice());
        const answer = report({owner_choice: forcedChoice()});
        expect(within(ownerModal()).getByTestId('owner-choice-confirm'), 'precondition: the forced owner can be confirmed').toBeEnabled();

        await view.rerender({open: true, report: answer, busy: true, random: view.random, onConfirm: view.onConfirm, onDrop: view.onDrop, onClose: view.onClose});

        expect(within(ownerModal()).getByTestId('owner-choice-confirm')).toBeDisabled();
    });
});

// =====================================================================================================================
// B5-1k2 — a backup with more active accounts than the instance accepts: a notice before the confirmation, no refusal
// =====================================================================================================================

/*
 * The contract (`B-5-1k2-contratto.md`, «Frontend»):
 *   - `RestoreReportModal` draws a notice of its own, `restore-users-over-limit`, when `report.users_over_limit > 0`, worded by
 *     `backup.restore.report.usersOverLimit` with the values `{active, limit}` (from `users_active` and `users_limit`). Absent
 *     otherwise: the fields missing (a report of before the client was generated), 0, or no limit;
 *   - the code `users_over_limit` of `warnings` is not a line of the warnings box (`WARNINGS_SHOWN_APART`);
 *   - the confirmation does not change: the word typed → the owner's choice, if the report has one → `onConfirm(ownerUserId)`.
 *     No step more, no second argument.
 *
 * The translator of this file renders a key as itself followed by its values as JSON, so the values are read, never a
 * sentence. Red today: the notice does not exist, and the code, unknown to `WARNINGS_SHOWN_APART`, is drawn as a line of
 * the warnings box under the unknown fallback.
 */

type UsersFields = {users_active: number; users_limit: number | null; users_over_limit: number};

const OVER_LIMIT: UsersFields = {users_active: 5, users_limit: 3, users_over_limit: 2};
const USERS_OVER_LIMIT = 'users_over_limit';
const USERS_KEY = 'backup.restore.report.usersOverLimit';

const noticeOf = () => screen.queryByTestId('restore-users-over-limit');

/** The values the translator was given for the notice: `key {json}` → the json. */
function noticeValues(): unknown {
    const notice = screen.getByTestId('restore-users-over-limit');
    const text = (notice.textContent ?? '').trim();
    expect(text, 'the notice is worded by backup.restore.report.usersOverLimit').toContain(USERS_KEY);
    return JSON.parse(text.slice(text.indexOf('{', text.indexOf(USERS_KEY))));
}

const overLimit = (extra: Partial<RestoreStageReport & ReportB4Fields> = {}, fields: Partial<UsersFields> = {}) => report({...OVER_LIMIT, ...fields, warnings: [USERS_OVER_LIMIT, CREDENTIALS], ...extra} as Partial<RestoreStageReport & ReportB4Fields>);

describe('B5-1k2 — RestoreReportModal: the notice of too many accounts', () => {
    it('users_over_limit > 0: restore-users-over-limit, worded by backup.restore.report.usersOverLimit with {active, limit}', () => {
        mount(overLimit());

        expect(noticeOf(), 'the notice is not drawn').toBeInTheDocument();
        expect(noticeValues()).toEqual({active: 5, limit: 3});
        expect(i18n.asked).toContain(USERS_KEY);
    });

    it('the values follow the report: users_active and users_limit, not users_over_limit', () => {
        mount(overLimit({}, {users_active: 12, users_limit: 10, users_over_limit: 2}));

        expect(noticeValues()).toEqual({active: 12, limit: 10});
    });

    it.each<[string, () => RestoreStageReport]>([
        ['the fields absent (a report of before)', () => report()],
        ['users_over_limit 0 (at the limit)', () => report({users_active: 3, users_limit: 3, users_over_limit: 0} as Partial<RestoreStageReport & ReportB4Fields>)],
        ['no limit (null)', () => report({users_active: 9, users_limit: null, users_over_limit: 0} as Partial<RestoreStageReport & ReportB4Fields>)],
    ])('%s: no notice', (_case, answer) => {
        // The presence barrier: the same modal does draw the notice over the limit.
        const control = mount(overLimit());
        expect(noticeOf(), 'barrier: the notice is drawn over the limit').toBeInTheDocument();
        control.unmount();
        i18n.asked.length = 0; // the barrier asked the key; only what the next mount asks counts

        mount(answer());

        expect(noticeOf()).toBeNull();
        expect(i18n.asked, 'a key asked for a notice that is not drawn').not.toContain(USERS_KEY);
    });

    it('the code is not a line of the warnings box: alone it draws no box; with another warning the box lists the other only', () => {
        const alone = mount(overLimit());
        expect(noticeOf(), 'barrier: the notice is drawn').toBeInTheDocument();
        expect(within(screen.getByTestId('restore-report')).queryByTestId('restore-report-warnings'), 'a box for a warning drawn apart').toBeNull();
        alone.unmount();

        mount(overLimit({warnings: ['rows_changed', USERS_OVER_LIMIT, CREDENTIALS]}));

        const box = within(screen.getByTestId('restore-report')).getByTestId('restore-report-warnings');
        expect(
            within(box)
                .getAllByTestId('restore-report-warning')
                .map((line) => line.getAttribute('data-warning')),
        ).toEqual(['rows_changed']);
        expect(screen.getByTestId('restore-report').querySelector(`[data-warning="${USERS_OVER_LIMIT}"]`)).toBeNull();
        expect(i18n.asked, 'the code was drawn as the unknown warning').not.toContain('backup.restore.report.warning.unknown');
    });
});

describe('B5-1k2 — RestoreReportModal: the confirmation is the one of before', () => {
    it('no owner to choose: the word typed, restore-confirm → onConfirm(null) once, with no argument more, and no step in between', async () => {
        const {onConfirm} = mount(overLimit());
        expect(noticeOf(), 'barrier: the notice is drawn').toBeInTheDocument();

        await typeAndConfirm();

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith(null);
        expect(screen.queryByTestId('owner-choice-modal')).toBeNull();
        expect(screen.queryByTestId('restore-trim-modal')).toBeNull();
    });

    it('Enter in the field confirms as before', async () => {
        const {onConfirm} = mount(overLimit());
        await type('violet');
        expect(noticeOf(), 'barrier: the notice is drawn').toBeInTheDocument();

        await fireEvent.keyDown(field(), {key: 'Enter'});

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith(null);
    });

    it('the word rule is untouched: nothing typed, or another word, keeps restore-confirm disabled whatever the notice says', async () => {
        const {onConfirm} = mount(overLimit());
        expect(noticeOf(), 'barrier: the notice is drawn').toBeInTheDocument();

        expect(confirmButton()).toBeDisabled();
        await type('garden');
        expect(confirmButton()).toBeDisabled();
        await fireEvent.click(confirmButton());

        expect(onConfirm).not.toHaveBeenCalled();
    });

    it('with an owner to choose (managed): the word typed opens the owner modal, its confirm calls onConfirm(id) once', async () => {
        const {onConfirm} = mount(overLimit({owner_choice: ownerChoice()}));
        expect(noticeOf(), 'barrier: the notice is drawn').toBeInTheDocument();

        await typeAndConfirm();

        expect(onConfirm, 'confirmed before the owner was chosen').not.toHaveBeenCalled();
        expect(screen.getByTestId('owner-choice-modal')).toBeInTheDocument();
        expect(screen.queryByTestId('restore-trim-modal')).toBeNull();
        await fireEvent.click(option(ADMIN_NO_EMAIL.user_id));
        await fireEvent.click(within(ownerModal()).getByTestId('owner-choice-confirm'));

        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onConfirm).toHaveBeenCalledWith(ADMIN_NO_EMAIL.user_id);
    });
});
