// @vitest-environment jsdom
/**
 * PluginSettingsModal — «Configure»: one plugin's settings over the dialog that asked for them (workstream X, lot
 * CP11b; plan 03 §4.4).
 *
 * The contract under test:
 *   - props `{open, family, pluginCode, pluginName?, zIndex? = 80, onClose, onSaved?}`; root `plugin-settings-modal`
 *     (ModalBase, a dialog), drawn only while open, at layer 80 unless told otherwise — above the asset dialog (50) and
 *     its prompts (70);
 *   - every opening reads the plugin's state afresh (`fetchPluginEntry(family, pluginCode)`), and nothing is read while
 *     closed; the dialog's content publishes `data-busy` (with `aria-busy`) true while that read is in flight, and
 *     shows the form of the entry once it is in (`plugin-settings-form-{code}`), `plugin-settings-none` when the plugin
 *     declares no settings, `plugin-settings-load-error` (role alert) when the read fails;
 *   - only the latest read writes: an answer to an opening that was closed since never replaces the answer to a newer
 *     opening;
 *   - the title names the plugin: `pluginName` while its state loads, the entry's own name once it is in, the code
 *     when there is neither;
 *   - a save in the form shows the fresh state and hands it to `onSaved`; `plugin-settings-modal-close` and Escape ask
 *     `onClose`.
 *
 * Mocks, all owned here: `./pluginSettingsApi` (`fetchPluginEntry` and `savePluginSettings` are fakes the test answers,
 * deferred where "in flight" or "which answer lands last" is the subject; the narrowing stays real); `$lib/i18n` (only
 * `_`, answering `key {name=value}`: the title is read as the key and the name the dialog chose); and
 * `$lib/stores/app/notify.svelte` (a spy). The form is the real one, pinned by `PluginSettingsForm.component.test.ts`.
 *
 * Every wait is on a state, or on a deferred the test settles: a component that awaited a deferred before the test
 * did has run its continuation by the time the test's own `await` resumes.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

const fake = vi.hoisted(() => ({
    /** `key`, or `key {name=value, …}` when handed values. */
    translate(key: string, options?: {values?: Record<string, unknown>}): string {
        const values = options?.values ?? {};
        const shown = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return shown.length > 0 ? `${key} {${shown.join(', ')}}` : key;
    },
    fetchEntry: vi.fn(),
    save: vi.fn(),
    notify: vi.fn(),
}));

vi.mock('./pluginSettingsApi', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./pluginSettingsApi')>()),
    fetchPluginEntry: fake.fetchEntry,
    savePluginSettings: fake.save,
}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: readable(fake.translate)};
});
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: fake.notify}));

import PluginSettingsModal from './PluginSettingsModal.svelte';
import type {PluginSettingsEntry, SettingField, SettingsFamily} from './pluginSettingsApi';

// --- Fixtures --------------------------------------------------------------------------------------------------------

/** A user text field, editable, nothing in force. */
function nickname(): SettingField {
    return {
        key: 'nickname',
        type: 'string',
        scope: 'user',
        secret: false,
        required: true,
        label: 'Nickname',
        description: '',
        label_key: null,
        description_key: null,
        options: [],
        min_length: null,
        max_length: null,
        minimum: null,
        maximum: null,
        default: null,
        value: null,
        is_set: false,
        source: 'none',
        locked: false,
        env_variable: null,
        editable: true,
        problem: null,
        updated_at: null,
    };
}

function justetf(configured: boolean): PluginSettingsEntry {
    return {family: 'asset', plugin_code: 'justetf', plugin_name: 'justETF', icon_url: null, configured, fields: [nickname()]};
}

// --- Helpers ---------------------------------------------------------------------------------------------------------

interface ModalProps {
    open: boolean;
    family: SettingsFamily;
    pluginCode: string;
    pluginName?: string;
    zIndex?: number;
}

function mount(props: Partial<ModalProps> = {}) {
    const onClose = vi.fn();
    const onSaved = vi.fn();
    const utils = render(PluginSettingsModal, {props: {open: true, family: 'asset', pluginCode: 'justetf', onClose, onSaved, ...props}});
    return {...utils, onClose, onSaved};
}

const modal = () => screen.getByTestId('plugin-settings-modal');
const queryModal = () => screen.queryByTestId('plugin-settings-modal');
/** The dialog's content: it publishes the plugin it is about and whether its read is in flight. */
const content = () => modal().querySelector<HTMLElement>('[data-plugin]');
const title = () => (within(modal()).getByRole('heading', {level: 2}).textContent ?? '').trim();

/** A promise this test settles by hand, so that "in flight" is a state it controls. */
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((done, fail) => {
        resolve = done;
        reject = fail;
    });
    return {promise, resolve, reject};
}

async function loaded(): Promise<void> {
    await waitFor(() => expect(content()).toHaveAttribute('data-busy', 'false'));
}

// --- Lifecycle -------------------------------------------------------------------------------------------------------

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    fake.fetchEntry.mockReset();
    fake.save.mockReset();
    fake.notify.mockReset();
});

afterEach(() => {
    cleanup();
});

// =====================================================================================================================
describe('PluginSettingsModal — every opening reads the plugin afresh', () => {
    it('PSM-01: closed, it draws nothing and reads nothing; opened, it reads that plugin once, busy until the answer is in, then shows its form', async () => {
        const read = deferred<PluginSettingsEntry | null>();
        fake.fetchEntry.mockReturnValueOnce(read.promise);
        const {rerender} = mount({open: false});
        expect(queryModal()).toBeNull();

        await rerender({open: true});

        expect(modal()).toBeVisible();
        expect(modal()).toHaveAttribute('role', 'dialog');
        expect(fake.fetchEntry.mock.calls, 'one read, for that plugin of that family: none while it was closed').toEqual([['asset', 'justetf']]);
        expect(content()).toHaveAttribute('data-plugin', 'justetf');
        expect(content()).toHaveAttribute('data-busy', 'true');
        expect(content()).toHaveAttribute('aria-busy', 'true');
        expect(within(modal()).queryByTestId('plugin-settings-form-justetf')).toBeNull();
        expect(within(modal()).queryByTestId('plugin-settings-none'), 'not read yet is not «no settings»').toBeNull();
        expect(within(modal()).queryByTestId('plugin-settings-load-error')).toBeNull();

        read.resolve(justetf(false));

        await loaded();
        expect(within(modal()).getByTestId('plugin-settings-form-justetf')).toHaveAttribute('data-configured', 'false');
    });

    it('PSM-02: a re-opening reads again, shows nothing of the previous answer while it reads, then the new state', async () => {
        const second = deferred<PluginSettingsEntry | null>();
        fake.fetchEntry.mockResolvedValueOnce(justetf(false)).mockReturnValueOnce(second.promise);
        const {rerender} = mount();
        await loaded();
        expect(within(modal()).getByTestId('plugin-settings-form-justetf'), 'premise').toHaveAttribute('data-configured', 'false');

        await rerender({open: false});
        await waitFor(() => expect(queryModal()).toBeNull());
        expect(fake.fetchEntry, 'closing reads nothing').toHaveBeenCalledTimes(1);
        await rerender({open: true});

        expect(fake.fetchEntry).toHaveBeenCalledTimes(2);
        expect(fake.fetchEntry).toHaveBeenLastCalledWith('asset', 'justetf');
        expect(content()).toHaveAttribute('data-busy', 'true');
        expect(within(modal()).queryByTestId('plugin-settings-form-justetf'), 'the previous answer is not shown as the current one').toBeNull();

        second.resolve(justetf(true));

        await loaded();
        expect(within(modal()).getByTestId('plugin-settings-form-justetf')).toHaveAttribute('data-configured', 'true');
    });

    it('PSM-03: an answer to an opening closed since never replaces the answer to the newer opening', async () => {
        const first = deferred<PluginSettingsEntry | null>();
        const second = deferred<PluginSettingsEntry | null>();
        fake.fetchEntry.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
        const {rerender} = mount();
        await rerender({open: false});
        await waitFor(() => expect(queryModal()).toBeNull());
        await rerender({open: true});
        expect(fake.fetchEntry, 'premise: two openings, two reads').toHaveBeenCalledTimes(2);

        second.resolve(justetf(true));
        await loaded();
        expect(within(modal()).getByTestId('plugin-settings-form-justetf')).toHaveAttribute('data-configured', 'true');

        // The older answer lands last. The dialog awaited it before this test did, so its continuation has run by the
        // time this `await` resumes; flushSync then draws whatever it wrote.
        first.resolve(justetf(false));
        await first.promise;
        flushSync();

        expect(within(modal()).getByTestId('plugin-settings-form-justetf'), 'the newer answer stays').toHaveAttribute('data-configured', 'true');
        expect(content()).toHaveAttribute('data-busy', 'false');
    });

    it('PSM-04: a plugin that declares no settings says so', async () => {
        fake.fetchEntry.mockResolvedValueOnce(null);

        mount();

        await loaded();
        expect(within(modal()).getByTestId('plugin-settings-none')).toBeInTheDocument();
        expect(within(modal()).queryByTestId('plugin-settings-load-error')).toBeNull();
        expect(within(modal()).queryAllByTestId(/^plugin-settings-form-/)).toEqual([]);
    });

    it('PSM-05: a read that fails shows the load error, alone', async () => {
        fake.fetchEntry.mockRejectedValueOnce(new Error('settings unavailable'));

        mount();

        await loaded();
        expect(within(modal()).getByTestId('plugin-settings-load-error')).toHaveAttribute('role', 'alert');
        expect(within(modal()).queryByTestId('plugin-settings-none')).toBeNull();
        expect(within(modal()).queryAllByTestId(/^plugin-settings-form-/)).toEqual([]);
    });
});

// =====================================================================================================================
describe('PluginSettingsModal — its frame', () => {
    it('PSM-06: the title names the plugin it was given while its state loads, then the plugin’s own name; the code when it has neither', async () => {
        const read = deferred<PluginSettingsEntry | null>();
        fake.fetchEntry.mockReturnValueOnce(read.promise).mockResolvedValueOnce(null);
        mount({pluginName: 'justETF (from the list)'});

        expect(title()).toBe('pluginSettings.modal.title {plugin=justETF (from the list)}');
        read.resolve(justetf(true));
        await loaded();
        expect(title()).toBe('pluginSettings.modal.title {plugin=justETF}');

        cleanup();
        mount({pluginCode: 'mockfx', family: 'fx'});
        await loaded();
        expect(fake.fetchEntry).toHaveBeenLastCalledWith('fx', 'mockfx');
        expect(title(), 'no name given, none read').toBe('pluginSettings.modal.title {plugin=mockfx}');
    });

    it('PSM-07: sits at layer 80 unless told otherwise', async () => {
        fake.fetchEntry.mockResolvedValue(null);

        mount();
        expect(modal().style.zIndex).toBe('80');
        await loaded();

        cleanup();
        mount({zIndex: 95});
        expect(modal().style.zIndex).toBe('95');
        await loaded();
    });

    it('PSM-08: the close button and Escape ask onClose, and nothing is saved on the way', async () => {
        fake.fetchEntry.mockResolvedValueOnce(justetf(false));
        const {onClose, onSaved} = mount();
        await loaded();

        await fireEvent.click(within(modal()).getByTestId('plugin-settings-modal-close'));
        expect(onClose).toHaveBeenCalledTimes(1);

        await fireEvent.keyDown(modal(), {key: 'Escape'});
        expect(onClose).toHaveBeenCalledTimes(2);
        expect(onSaved).not.toHaveBeenCalled();
        expect(fake.save).not.toHaveBeenCalled();
    });

    it('PSM-09: a save in the form shows the fresh state and hands it to onSaved, and the dialog stays open', async () => {
        const fresh: PluginSettingsEntry = {...justetf(true), fields: [{...nickname(), value: 'someone', is_set: true, source: 'db'}]};
        fake.fetchEntry.mockResolvedValueOnce(justetf(false)).mockResolvedValueOnce(fresh);
        fake.save.mockResolvedValueOnce({kind: 'saved'});
        const {onClose, onSaved} = mount();
        await loaded();

        const form = within(modal()).getByTestId('plugin-settings-form-justetf');
        await fireEvent.input(within(form).getByTestId('plugin-setting-input'), {target: {value: 'someone'}});
        await fireEvent.click(within(form).getByTestId('plugin-settings-save'));

        await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1));
        expect(onSaved).toHaveBeenCalledWith(fresh);
        await waitFor(() => expect(within(modal()).getByTestId('plugin-settings-form-justetf')).toHaveAttribute('data-configured', 'true'));
        expect(fake.save.mock.calls).toStrictEqual([[[{family: 'asset', plugin_code: 'justetf', field_key: 'nickname', scope: 'user', value: 'someone'}]]]);
        expect(onClose, 'a save does not close the dialog').not.toHaveBeenCalled();
    });
});
