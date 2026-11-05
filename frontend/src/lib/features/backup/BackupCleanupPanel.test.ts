// @vitest-environment jsdom
/**
 * BackupCleanupPanel — component test (Vitest + jsdom), lot FB-24, written red first against
 * `B6r-fb24-frontend-interface.md` §4.
 *
 * The two global settings that tell the server which backups to throw away on its own: `backup_cleanup_max_mb` (the
 * total size the archives may take) and `backup_cleanup_max_days` (how old one may get), 0 meaning «this rule is off».
 * They are GLOBAL settings, saved together by one request, from the Backup section of the Settings tab and of the Files
 * page.
 *
 * What this file pins:
 *   - the state on its root, `backup-cleanup`: `data-state` (`loading|idle|saving|saved|error`) and `data-error-code`
 *     (empty unless `error`); the values come from `getCleanupSettings()`;
 *   - the two integer fields `backup-cleanup-max-mb` and `backup-cleanup-max-days` (labelled `backup.cleanup.maxMb` and
 *     `backup.cleanup.maxDays`), and `backup-cleanup-save`, disabled while nothing differs from what the server holds,
 *     while a save is out, and while a value is not an integer ≥ 0 (empty, negative, decimal);
 *   - the save: `saveCleanupSettings({maxMb, maxDays})` once, the state `saving` meanwhile (no second request), then
 *     `saved` and `notify({name: 'backup.cleanup.saved', detail: {max_mb, max_days}})` — the structured half uses the
 *     API's own snake_case names; after it the panel holds the saved values as its baseline, so the button is off again;
 *   - the profile (`instanceConfig.config.profile`): on `managed` the MB field has `min=1` and the hint
 *     `backup.cleanup.hintManaged`; on the self-hosted `min=0` and `backup.cleanup.hintSelfhosted` (0 turns the rule
 *     off). The panel does not stop a 0 on `managed` by itself — the server refuses it with a 422 and that is what the
 *     user is told;
 *   - a refused save: `data-state="error"`, `data-error-code` on the root and on `backup-cleanup-error`, whose text is
 *     `backup.cleanup.errors.<invalid|forbidden|network|unexpected>` (`cleanupSaveCode`: 422, 403, no answer, anything
 *     else); no `backup.cleanup.saved`; the typed values stay, ready to be saved again;
 *   - the fixed line `backup-cleanup-latest-kept` (`backup.cleanup.latestKept`): the latest backup is always kept.
 *
 * The seams. `$lib/i18n` is an identity translator: assertions name keys. `./backupApi` keeps its real
 * `cleanupSaveCode` and swaps the two requests for `vi.fn`; `$lib/api` throws on any request. The instance
 * configuration is a fake with the real store's shape (enumerable getters over `$state`), its profile chosen per case.
 * The component is loaded inside each case, so that while it does not exist each case fails on its own.
 *
 * What it deliberately does not assert: how long `saved` stays on screen before `idle` (unspecified); what the panel
 * does when the first read of the settings fails (unspecified); the translated sentences; any CSS class.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {readable, writable} from 'svelte/store';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {cleanup, fireEvent, render, screen, waitFor} from '$test/component';

// --- Mocks ----------------------------------------------------------------------------------------------------------

vi.mock('$lib/i18n', () => {
    const identity = readable((key: string) => key);
    return {
        _: identity,
        t: identity,
        locale: writable('en'),
        date: readable((v: unknown) => String(v)),
        time: readable((v: unknown) => String(v)),
        number: readable((v: unknown) => String(v)),
        i18nLoading: readable(false),
        SUPPORTED_LOCALES: ['en', 'it'],
        DEFAULT_LOCALE: 'en',
        LOCALE_NAMES: {en: 'English', it: 'Italiano', fr: 'Français', es: 'Español'},
        LOCALE_FLAGS: {en: 'EN', it: 'IT'},
        LANGUAGE_OPTIONS: [{code: 'en', name: 'English', flag: 'EN'}],
        initI18n: () => undefined,
        saveLocalePreference: () => undefined,
    };
});

vi.mock('$lib/api', () => {
    const zodiosApi = new Proxy(
        {},
        {
            get: (_target, alias) =>
                typeof alias !== 'string' || alias === 'then'
                    ? undefined
                    : () => {
                          throw new Error(`BackupCleanupPanel.test: a request went through zodiosApi.${alias}`);
                      },
        },
    );
    return {zodiosApi, schemas: {}, axiosInstance: {}, ApiError: class ApiError extends Error {}};
});

vi.mock('./backupApi', async () => {
    const actual = await vi.importActual<typeof import('./backupApi')>('./backupApi');
    return {...actual, getCleanupSettings: vi.fn(), saveCleanupSettings: vi.fn()};
});

vi.mock('$lib/stores/app/notify.svelte', () => ({notify: vi.fn()}));

/** The public configuration of the instance, held by the test; getters over `$state`, as in the real store. */
const instance = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const SELFHOSTED: InstanceConfig = {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}};
    const MANAGED: InstanceConfig = {profile: 'managed', accounts: {registration_mode: 'open', registration_locked: false}};
    return {SELFHOSTED, MANAGED, box: reactiveBox<{config: InstanceConfig}>({config: SELFHOSTED})};
});
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: instance.SELFHOSTED,
    instanceConfig: {
        get config() {
            return instance.box.config;
        },
        get loaded() {
            return true;
        },
        get failed() {
            return false;
        },
        load: vi.fn(() => Promise.resolve()),
    },
}));

import {getCleanupSettings, saveCleanupSettings} from './backupApi';
import {notify} from '$lib/stores/app/notify.svelte';

// A literal path would fail the whole file at transform time while the module is missing; a variable path fails each case alone.
const MODULES = {panel: './BackupCleanupPanel.svelte'};
const loadPanel = async () => (await import(/* @vite-ignore */ MODULES.panel)).default;

// --- Fixtures & helpers ---------------------------------------------------------------------------------------------

const api = {
    read: vi.mocked(getCleanupSettings),
    save: vi.mocked(saveCleanupSettings),
};

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

/** A request the server answered with an error status: axios rejects with the response. */
function answered(status: number, data: unknown) {
    return {isAxiosError: true, name: 'AxiosError', message: `Request failed with status code ${status}`, response: {status, data}};
}
const noAnswer = () => ({isAxiosError: true, name: 'AxiosError', message: 'Network Error', code: 'ERR_NETWORK', response: undefined});

const panel = () => screen.getByTestId('backup-cleanup');
const saveButton = () => screen.getByTestId('backup-cleanup-save') as HTMLButtonElement;

/** The `<input>` of a field: the test id may sit on the input itself or on the wrapper around it. */
function field(testId: 'backup-cleanup-max-mb' | 'backup-cleanup-max-days'): HTMLInputElement {
    const element = screen.getByTestId(testId);
    const input = element instanceof HTMLInputElement ? element : element.querySelector('input');
    if (!input) throw new Error(`${testId} holds no input`);
    return input;
}

async function typeInto(testId: 'backup-cleanup-max-mb' | 'backup-cleanup-max-days', value: string) {
    await fireEvent.input(field(testId), {target: {value}});
}

/** What `notify()` recorded, in order; only the events called `name` when it is given. */
function events(name?: string) {
    return vi
        .mocked(notify)
        .mock.calls.map(([options]) => options)
        .filter((options) => name === undefined || options.name === name);
}

/** Mount the panel with the server holding `held`, and wait for the read to land. */
async function mountIdle(held = {maxMb: 250, maxDays: 30}) {
    api.read.mockResolvedValueOnce(held);
    const Panel = await loadPanel();
    const view = render(Panel);
    await waitFor(() => expect(panel()).toHaveAttribute('data-state', 'idle'));
    return view;
}

// The first import of the panel is slower than a case's own 5 s on a loaded machine. It is done once, here.
beforeAll(async () => {
    await loadPanel();
}, 120_000);

beforeEach(() => {
    api.read.mockReset();
    api.save.mockReset();
    vi.mocked(notify).mockReset();
    instance.box.config = instance.SELFHOSTED;
});

afterEach(() => {
    cleanup();
});

// =====================================================================================================================
describe('BackupCleanupPanel — reading', () => {
    it('loading: no value yet and nothing to save; idle with the values of the server once the read lands', async () => {
        const answer = deferred<{maxMb: number; maxDays: number}>();
        api.read.mockReturnValueOnce(answer.promise);
        const Panel = await loadPanel();
        render(Panel);

        expect(panel()).toHaveAttribute('data-state', 'loading');
        expect(saveButton()).toBeDisabled();
        expect(api.read).toHaveBeenCalledTimes(1);

        answer.resolve({maxMb: 250, maxDays: 30});
        await waitFor(() => expect(panel()).toHaveAttribute('data-state', 'idle'));

        expect(field('backup-cleanup-max-mb').value).toBe('250');
        expect(field('backup-cleanup-max-days').value).toBe('30');
        expect(panel()).toHaveAttribute('data-error-code', '');
        expect(saveButton()).toBeDisabled();
        expect(api.read).toHaveBeenCalledTimes(1);
        expect(api.save).not.toHaveBeenCalled();
    });

    it('names both fields and says the latest backup is always kept', async () => {
        await mountIdle();

        expect(panel()).toHaveTextContent('backup.cleanup.maxMb');
        expect(panel()).toHaveTextContent('backup.cleanup.maxDays');
        expect(screen.getByTestId('backup-cleanup-latest-kept')).toHaveTextContent('backup.cleanup.latestKept');
        expect(screen.queryByTestId('backup-cleanup-error')).toBeNull();
    });

    it('a rule that is off is shown as 0', async () => {
        await mountIdle({maxMb: 0, maxDays: 0});

        expect(field('backup-cleanup-max-mb').value).toBe('0');
        expect(field('backup-cleanup-max-days').value).toBe('0');
    });
});

// =====================================================================================================================
describe('BackupCleanupPanel — the profile of the instance', () => {
    it('self-hosted: the MB field accepts 0, and the hint says 0 turns the rule off', async () => {
        instance.box.config = instance.SELFHOSTED;
        await mountIdle({maxMb: 0, maxDays: 0});

        expect(field('backup-cleanup-max-mb')).toHaveAttribute('min', '0');
        expect(panel()).toHaveTextContent('backup.cleanup.hintSelfhosted');
        expect(panel()).not.toHaveTextContent('backup.cleanup.hintManaged');
    });

    it('managed: the MB field starts at 1, and the hint is the managed one', async () => {
        instance.box.config = instance.MANAGED;
        await mountIdle();

        expect(field('backup-cleanup-max-mb')).toHaveAttribute('min', '1');
        expect(panel()).toHaveTextContent('backup.cleanup.hintManaged');
        expect(panel()).not.toHaveTextContent('backup.cleanup.hintSelfhosted');
    });
});

// =====================================================================================================================
describe('BackupCleanupPanel — the save button', () => {
    it('is off while nothing differs from the server, on after a change, off again when the change is undone', async () => {
        await mountIdle();
        expect(saveButton()).toBeDisabled();

        await typeInto('backup-cleanup-max-mb', '500');
        expect(saveButton()).toBeEnabled();

        await typeInto('backup-cleanup-max-mb', '250');
        expect(saveButton()).toBeDisabled();

        await typeInto('backup-cleanup-max-days', '7');
        expect(saveButton()).toBeEnabled();
    });

    it.each<[string, string]>([
        ['an empty value', ''],
        ['a negative number', '-1'],
        ['a decimal number', '1.5'],
    ])('is off for %s in the MB field, though it differs from the server', async (_case, value) => {
        await mountIdle();

        await typeInto('backup-cleanup-max-mb', value);

        expect(saveButton()).toBeDisabled();
        await fireEvent.click(saveButton());
        expect(api.save).not.toHaveBeenCalled();
    });

    it.each<[string, string]>([
        ['an empty value', ''],
        ['a negative number', '-1'],
        ['a decimal number', '1.5'],
    ])('is off for %s in the days field, though it differs from the server', async (_case, value) => {
        await mountIdle();

        await typeInto('backup-cleanup-max-days', value);

        expect(saveButton()).toBeDisabled();
        await fireEvent.click(saveButton());
        expect(api.save).not.toHaveBeenCalled();
    });

    it('back to a valid value, it is on again', async () => {
        await mountIdle();
        await typeInto('backup-cleanup-max-days', '-1');
        expect(saveButton()).toBeDisabled();

        await typeInto('backup-cleanup-max-days', '14');

        expect(saveButton()).toBeEnabled();
    });
});

// =====================================================================================================================
describe('BackupCleanupPanel — saving', () => {
    it('one request with both values; saving meanwhile, no second request; then saved, notified, and nothing left to save', async () => {
        await mountIdle();
        const answer = deferred<void>();
        api.save.mockReturnValueOnce(answer.promise);
        await typeInto('backup-cleanup-max-mb', '500');
        await typeInto('backup-cleanup-max-days', '14');

        await fireEvent.click(saveButton());

        expect(api.save).toHaveBeenCalledTimes(1);
        expect(api.save).toHaveBeenCalledWith({maxMb: 500, maxDays: 14});
        await waitFor(() => expect(panel()).toHaveAttribute('data-state', 'saving'));
        expect(saveButton()).toBeDisabled();
        await fireEvent.click(saveButton());
        expect(api.save, 'a save in flight is not sent twice').toHaveBeenCalledTimes(1);
        expect(events('backup.cleanup.saved')).toEqual([]);

        answer.resolve();

        await waitFor(() => expect(panel()).toHaveAttribute('data-state', 'saved'));
        expect(panel()).toHaveAttribute('data-error-code', '');
        expect(events('backup.cleanup.saved')).toHaveLength(1);
        expect(events('backup.cleanup.saved')[0].detail).toEqual({max_mb: 500, max_days: 14});
        expect(field('backup-cleanup-max-mb').value).toBe('500');
        expect(field('backup-cleanup-max-days').value).toBe('14');
        expect(saveButton(), 'the saved values are the baseline: nothing differs').toBeDisabled();
        expect(screen.queryByTestId('backup-cleanup-error')).toBeNull();
    });

    it('turning a rule off is a save of 0, not of nothing', async () => {
        await mountIdle();
        api.save.mockResolvedValueOnce(undefined);
        await typeInto('backup-cleanup-max-days', '0');

        await fireEvent.click(saveButton());

        await waitFor(() => expect(api.save).toHaveBeenCalledWith({maxMb: 250, maxDays: 0}));
        await waitFor(() => expect(events('backup.cleanup.saved')).toHaveLength(1));
        expect(events('backup.cleanup.saved')[0].detail).toEqual({max_mb: 250, max_days: 0});
    });

    it('a new change after a save makes the button available again', async () => {
        await mountIdle();
        api.save.mockResolvedValueOnce(undefined);
        await typeInto('backup-cleanup-max-mb', '500');
        await fireEvent.click(saveButton());
        await waitFor(() => expect(events('backup.cleanup.saved')).toHaveLength(1));

        await typeInto('backup-cleanup-max-mb', '600');

        expect(saveButton()).toBeEnabled();
    });
});

// =====================================================================================================================
describe('BackupCleanupPanel — a refused save', () => {
    it.each<[string, string, () => unknown]>([
        ['a 422', 'invalid', () => answered(422, {detail: 'Invalid value for backup_cleanup_max_mb'})],
        ['a 403', 'forbidden', () => answered(403, {detail: 'Admin required'})],
        ['no answer', 'network', noAnswer],
        ['a 500', 'unexpected', () => answered(500, {detail: 'Internal Server Error'})],
    ])('%s: error %s on the root and on backup-cleanup-error, its sentence by key, nothing announced as saved, the values kept', async (_case, code, refused) => {
        await mountIdle();
        api.save.mockRejectedValueOnce(refused());
        await typeInto('backup-cleanup-max-mb', '500');

        await fireEvent.click(saveButton());

        await waitFor(() => expect(panel()).toHaveAttribute('data-state', 'error'));
        expect(panel()).toHaveAttribute('data-error-code', code);
        const error = screen.getByTestId('backup-cleanup-error');
        expect(error).toHaveAttribute('data-error-code', code);
        expect(error).toHaveTextContent(`backup.cleanup.errors.${code}`);
        expect(events('backup.cleanup.saved')).toEqual([]);
        expect(field('backup-cleanup-max-mb').value, 'what the user typed stays').toBe('500');
        expect(saveButton(), 'the value is still unsaved: it can be sent again').toBeEnabled();
    });

    it('managed: a 0 in the MB field is sent, the server refuses it with a 422, and the user is told it is invalid', async () => {
        instance.box.config = instance.MANAGED;
        await mountIdle();
        api.save.mockRejectedValueOnce(answered(422, {detail: 'Invalid value for backup_cleanup_max_mb'}));
        await typeInto('backup-cleanup-max-mb', '0');

        await fireEvent.click(saveButton());

        await waitFor(() => expect(api.save).toHaveBeenCalledWith({maxMb: 0, maxDays: 30}));
        await waitFor(() => expect(panel()).toHaveAttribute('data-error-code', 'invalid'));
        expect(screen.getByTestId('backup-cleanup-error')).toHaveTextContent('backup.cleanup.errors.invalid');
    });

    it('sent again after a refusal, it can succeed: the error is gone', async () => {
        await mountIdle();
        api.save.mockRejectedValueOnce(noAnswer());
        api.save.mockResolvedValueOnce(undefined);
        await typeInto('backup-cleanup-max-mb', '500');
        await fireEvent.click(saveButton());
        await waitFor(() => expect(panel()).toHaveAttribute('data-state', 'error'));

        await fireEvent.click(saveButton());

        await waitFor(() => expect(panel()).toHaveAttribute('data-state', 'saved'));
        expect(panel()).toHaveAttribute('data-error-code', '');
        expect(screen.queryByTestId('backup-cleanup-error')).toBeNull();
        expect(api.save).toHaveBeenCalledTimes(2);
        expect(events('backup.cleanup.saved')).toHaveLength(1);
    });
});

// =====================================================================================================================
// K-3 (developer, 05/11) — the clean-up is a panel that starts closed
// =====================================================================================================================
describe('BackupCleanupPanel — a panel that starts closed (K-3)', () => {
    it('is a closed fold named by the panel title, holding both fields and the save button; the state stays on the root', async () => {
        await mountIdle();

        const fold = screen.getByTestId('backup-cleanup-fold') as HTMLDetailsElement;
        expect(fold.open).toBe(false);
        expect(fold).toHaveAttribute('data-open', 'false');
        expect(screen.getByTestId('backup-cleanup-fold-toggle')).toHaveTextContent('backup.cleanup.title');
        expect(panel()).toContainElement(fold);
        for (const element of [field('backup-cleanup-max-mb'), field('backup-cleanup-max-days'), saveButton()]) expect(fold).toContainElement(element);
    });

    it('says, under the rules, when they apply: within the hour', async () => {
        await mountIdle();

        expect(screen.getByTestId('backup-cleanup-fold')).toContainElement(screen.getByTestId('backup-cleanup-timing'));
        expect(screen.getByTestId('backup-cleanup-timing')).toHaveTextContent('backup.cleanup.timing');
    });
});
