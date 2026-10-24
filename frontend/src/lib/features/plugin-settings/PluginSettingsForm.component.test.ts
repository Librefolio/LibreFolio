// @vitest-environment jsdom
/**
 * PluginSettingsForm — one plugin's settings, as the caller may see and change them (workstream X, lot CP11b; plan 03
 * §4.4, D-X15).
 *
 * Named `.component.test.ts` because `PluginSettingsForm.test.ts` and `pluginSettingsForm.test.ts` (the rules without
 * the DOM) are one file on a case-insensitive file system — the precedent is `LinkShare.component.test.ts` beside
 * `linkShare.test.ts`.
 *
 * The contract under test:
 *   - the root `plugin-settings-form-{plugin_code}` publishes `data-configured`, and `data-busy` (with `aria-busy`)
 *     true from the click on Save until the plugin's state has been read again; `plugin-settings-status` says whether
 *     the plugin is configured (`data-configured`);
 *   - the heading (`h4`), which names the form (`aria-labelledby`), starts with the plugin's icon:
 *     `plugin-settings-plugin-icon`, an image of `icon_url`, decorative (`alt=""`) and fetched without a referrer;
 *     without an icon, or once that address has failed to load, the neutral `plugin-settings-plugin-icon-fallback`
 *     (`aria-hidden`), until the plugin publishes another address. Either way the form is named by the plugin's name
 *     alone;
 *   - one container `plugin-setting-{key}` per declared field, publishing `data-type`, `data-scope`, `data-source`,
 *     `data-editable`, `data-locked`, `data-problem` and `data-edit` (the kind of the field's unsaved edit, else
 *     empty), drawing one control by type: `plugin-setting-input` (a text, a number), `plugin-setting-select` (its
 *     options `plugin-setting-option-{value}`), `plugin-setting-toggle`, `plugin-setting-secret-input`;
 *   - a secret is write-only: unset, an input; set, «set on …» (`plugin-setting-secret-state`, `data-state`) with
 *     `plugin-setting-replace` (an empty input, and `plugin-setting-cancel-replace`, which drops what was typed) and
 *     `plugin-setting-clear` (`clearing`, `plugin-setting-undo`). What was typed is sent once, as `secret_value`, and
 *     forgotten: the input is empty after the save, and no event and no console line carries it, whatever the outcome;
 *   - a field the caller cannot change is read-only — its value (`plugin-setting-value`), a boolean as a disabled
 *     toggle, a secret as set or not set — with its reason (`plugin-setting-note`, `data-note`): `locked`, naming the
 *     variable only when the answer gives it, or `adminOnly`; the problems the server reports have their notes
 *     (`invalidEnv`, naming the variable when given, `invalidStored`, `unreadable`); with nothing editable there is
 *     neither Save nor Discard;
 *   - a saved value offers `plugin-setting-default` («Use the default»): the default shows, a `toDefault` note, Undo;
 *     Save writes `clear: true`. Emptying a saved text does the same;
 *   - a value the declared rules refuse shows `plugin-setting-problem` (`data-code`) on its field, and Save stays
 *     disabled until it is fixed;
 *   - Save hands the edits to `savePluginSettings`, one item per edit, in declaration order. Saved: the form empties,
 *     `pluginSettings.saved` is notified with the field names only and no toast, the plugin is read again and handed to
 *     `onsaved`. Refused: each refusal on its field (`plugin-setting-refusal`, `data-code`, role alert; a code this
 *     interface does not know worded as an invalid value) and `pluginSettings.save.refused` with a toast, the edits
 *     kept, editing a field taking its refusal down. Conflict: `pluginSettings.save.failed` (`reason: conflict`) with a
 *     toast, and the plugin read again for `onsaved`. Key unavailable, failed: `pluginSettings.save.failed` with its
 *     reason and a toast, the edits kept, nothing read again;
 *   - a field named like a property every object inherits (`constructor`, which the backend's key pattern allows) is a
 *     field like any other: no edit, no problem and no refusal it does not have, and its own when it has them; a secret
 *     one, unset, shows an empty input — never the text of what every object inherits — and sends exactly what was
 *     typed.
 *
 * Mocks, all owned here:
 *   - `./pluginSettingsApi`: `savePluginSettings` and `fetchPluginEntry` are fakes the test answers, with outcomes and
 *     entries already narrowed, as the real functions hand them over; deferreds where "in flight" is the subject. The
 *     narrowing stays real, and is pinned by `pluginSettingsApi.test.ts`;
 *   - `$lib/i18n`: only `_` is replaced (the rest stays real: the language store reads its constants), by a translator
 *     answering a key with itself, and `key {name=value}` when handed values: an assertion names the key and the
 *     values the form chose, never a sentence of a catalogue. A plugin's own keys answer the same way, untranslated, so
 *     its English text shows, as `translateOr` decides;
 *   - `$lib/utils/core/formatDateTime`: `⟨iso⟩`, so the date «set on» names is the one the entry carried;
 *   - `$lib/stores/app/notify.svelte`: a spy (the event, not the toast, is the contract).
 *
 * The rules themselves — what an edit is, what is wrong with one, the items of a write — are pinned without the DOM by
 * `pluginSettingsForm.test.ts`; here, that the form draws them and wires them. Every wait is on a state: `data-busy`,
 * `data-edit`, an element appearing, a deferred the test resolves. No clock. No image is fetched: jsdom loads none, so
 * an icon fails only when a test dispatches its `error`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {inspect} from 'node:util';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

const fake = vi.hoisted(() => ({
    /** `key`, or `key {name=value, …}` when handed values: what the form chose to say, in no language at all. */
    translate(key: string, options?: {values?: Record<string, unknown>}): string {
        const values = options?.values ?? {};
        const shown = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return shown.length > 0 ? `${key} {${shown.join(', ')}}` : key;
    },
    save: vi.fn(),
    fetchEntry: vi.fn(),
    notify: vi.fn(),
}));

vi.mock('./pluginSettingsApi', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./pluginSettingsApi')>()),
    savePluginSettings: fake.save,
    fetchPluginEntry: fake.fetchEntry,
}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: readable(fake.translate)};
});
vi.mock('$lib/utils/core/formatDateTime', () => ({formatDateTime: (value: string) => `⟨${value}⟩`}));
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: fake.notify}));

import PluginSettingsForm from './PluginSettingsForm.svelte';
import type {PluginSettingsEntry, SaveOutcome, SettingField} from './pluginSettingsApi';

// --- Fixtures --------------------------------------------------------------------------------------------------------

/** What the user types as a secret: it must reach the write, and nothing else. */
const SECRET = 'sk-live-5f3a9c0d1e2b';
const UPDATED_AT = '2026-10-15T10:00:00Z';

/** A field as `fieldOf` hands it over, every key present: an editable user text field, nothing in force. */
function field(over: Partial<SettingField> & Pick<SettingField, 'key'>): SettingField {
    return {
        type: 'string',
        scope: 'user',
        secret: false,
        required: false,
        label: over.key,
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
        ...over,
    };
}

function entry(fields: SettingField[], over: Partial<PluginSettingsEntry> = {}): PluginSettingsEntry {
    return {family: 'asset', plugin_code: 'mockprov', plugin_name: 'Mock provider', icon_url: null, configured: false, fields, ...over};
}

/** Icons the plugin may publish: a remote URL (a reserved domain, which never resolves) and a path of this instance. */
const ICON = 'https://icons.example/mockprov.png';
const OTHER_ICON = '/api/v1/uploads/plugin/asset/mockprov.svg';

/** A user choice at its default; the label of `us` has a key the translator does not know. */
const REGION = field({
    key: 'region',
    type: 'select',
    label: 'Region',
    options: [
        {value: 'eu', label: 'Europe', label_key: null},
        {value: 'us', label: 'United States', label_key: 'pluginSettings.asset.mockprov.option.region.us'},
    ],
    default: 'eu',
    value: 'eu',
    source: 'default',
});
const TOLERANCE = field({key: 'price_tolerance', type: 'number', scope: 'system', label: 'Price tolerance', minimum: 0, maximum: 10, default: 0.5, value: 0.5, source: 'default'});
const RETRIES = field({key: 'retries', type: 'integer', label: 'Retries', minimum: 1, maximum: 5, default: 3, value: 3, source: 'default'});
const VERBOSE = field({key: 'verbose', type: 'boolean', scope: 'system', label: 'Verbose', default: false, value: false, source: 'default'});
/** A saved user text, its default behind it. */
const NICKNAME = field({key: 'nickname', label: 'Nickname', max_length: 12, default: 'anon', value: 'mine', is_set: true, source: 'db'});
/** A user secret, not set. */
const API_KEY = field({key: 'api_key', secret: true, required: true, label: 'API key', min_length: 8});
/** The same secret, saved. */
const SAVED_KEY = field({...API_KEY, is_set: true, source: 'db', updated_at: UPDATED_AT});

/** Every control a field may draw: an editable field draws exactly one, by type. */
const CONTROLS = ['plugin-setting-input', 'plugin-setting-select', 'plugin-setting-toggle', 'plugin-setting-secret-input', 'plugin-setting-value'];
/** The controls that change a value. */
const EDIT_CONTROLS = ['plugin-setting-input', 'plugin-setting-select', 'plugin-setting-secret-input', 'plugin-setting-replace', 'plugin-setting-clear', 'plugin-setting-default'];
const CONSOLE_METHODS = ['log', 'info', 'warn', 'error', 'debug', 'trace'] as const;

// --- Helpers ---------------------------------------------------------------------------------------------------------

function mount(theEntry: PluginSettingsEntry) {
    const onsaved = vi.fn();
    const utils = render(PluginSettingsForm, {props: {entry: theEntry, onsaved}});
    return {...utils, onsaved};
}

const form = () => screen.getByTestId('plugin-settings-form-mockprov');
const setting = (key: string) => screen.getByTestId(`plugin-setting-${key}`);
const inSetting = (key: string, testId: string) => within(setting(key)).getByTestId(testId);
const queryInSetting = (key: string, testId: string) => within(setting(key)).queryByTestId(testId);
const notesOf = (key: string) =>
    within(setting(key))
        .queryAllByTestId('plugin-setting-note')
        .map((note) => note.getAttribute('data-note'));
const noteOf = (key: string, kind: string) =>
    within(setting(key))
        .getAllByTestId('plugin-setting-note')
        .find((note) => note.getAttribute('data-note') === kind);
const saveButton = () => screen.getByTestId('plugin-settings-save');
const discardButton = () => screen.getByTestId('plugin-settings-discard');
/** The form's title: the level-4 heading that names it. */
const heading = () => within(form()).getByRole('heading', {level: 4});
const pluginIcon = () => within(form()).queryByTestId('plugin-settings-plugin-icon');
const fallbackIcon = () => within(form()).queryByTestId('plugin-settings-plugin-icon-fallback');

function text(element: Element | undefined): string {
    return (element?.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** The text of `container` on either side of `element`, blanks collapsed: what is read before it, and after it. */
function textAround(container: Element, element: Element): {before: string; after: string} {
    const before = document.createRange();
    before.setStart(container, 0);
    before.setEndBefore(element);
    const after = document.createRange();
    after.setStartAfter(element);
    after.setEnd(container, container.childNodes.length);
    const read = (range: Range) => range.toString().replace(/\s+/g, ' ').trim();
    return {before: read(before), after: read(after)};
}

async function typeIn(key: string, value: string): Promise<void> {
    await fireEvent.input(inSetting(key, 'plugin-setting-input'), {target: {value}});
}

async function typeSecret(key: string, value: string): Promise<void> {
    await fireEvent.input(inSetting(key, 'plugin-setting-secret-input'), {target: {value}});
}

/** Types `value` where keystrokes land: after whatever the secret input already holds, which is then sent with it. */
async function typeSecretAfterItsContent(key: string, value: string): Promise<void> {
    const input = inSetting(key, 'plugin-setting-secret-input') as HTMLInputElement;
    await fireEvent.input(input, {target: {value: input.value + value}});
}

/** Opens the field's select and picks the option: its options are looked for inside the field, never elsewhere. */
async function choose(key: string, value: string): Promise<void> {
    await fireEvent.click(inSetting(key, 'plugin-setting-select-button'));
    await fireEvent.click(await within(setting(key)).findByTestId(`plugin-setting-option-${value}`));
}

async function pressSave(): Promise<void> {
    await fireEvent.click(saveButton());
}

/** The form is no longer busy: the write, and the read after it, are over. */
async function settled(): Promise<void> {
    await waitFor(() => expect(form()).toHaveAttribute('data-busy', 'false'));
}

interface Notified {
    name: string;
    detail?: Record<string, unknown>;
    toast?: {variant: string; message: string; duration?: number};
}

/** Every notification, or every one of `name`, in order. */
function notified(name?: string): Notified[] {
    return fake.notify.mock.calls.map(([options]) => options as Notified).filter((options) => name === undefined || options.name === name);
}

/** A promise this test settles by hand, so that "in flight" is a state it controls. */
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((done) => {
        resolve = done;
    });
    return {promise, resolve};
}

/** Every console call made while the spies watched, as text, objects and errors written out in full. */
function consoleText(spies: Array<{mock: {calls: unknown[][]}}>): string {
    return spies
        .flatMap((spy) => spy.mock.calls)
        .map((args) => inspect(args, {depth: null}))
        .join('\n');
}

// --- Lifecycle -------------------------------------------------------------------------------------------------------

beforeAll(async () => {
    // Only a component reading svelte-i18n's own stores would need it: `_` is mocked above.
    await setupI18n();
});

beforeEach(() => {
    fake.save.mockReset();
    fake.fetchEntry.mockReset();
    fake.notify.mockReset();
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

// =====================================================================================================================
describe('PluginSettingsForm — one control per field', () => {
    it('PSF-01: draws one control per declared field, by type, each container publishing its type, scope, source and state', async () => {
        mount(entry([REGION, TOLERANCE, RETRIES, VERBOSE, NICKNAME, API_KEY]));

        expect(form()).toHaveAttribute('data-configured', 'false');
        expect(form()).toHaveAttribute('data-busy', 'false');
        expect(form()).toHaveAttribute('aria-busy', 'false');
        expect(within(form()).getByTestId('plugin-settings-status')).toHaveAttribute('data-configured', 'false');

        const drawn: Array<[key: string, type: string, scope: string, source: string, control: string]> = [
            ['region', 'select', 'user', 'default', 'plugin-setting-select'],
            ['price_tolerance', 'number', 'system', 'default', 'plugin-setting-input'],
            ['retries', 'integer', 'user', 'default', 'plugin-setting-input'],
            ['verbose', 'boolean', 'system', 'default', 'plugin-setting-toggle'],
            ['nickname', 'string', 'user', 'db', 'plugin-setting-input'],
            ['api_key', 'string', 'user', 'none', 'plugin-setting-secret-input'],
        ];
        for (const [key, type, scope, source, control] of drawn) {
            const container = setting(key);
            expect(container, key).toHaveAttribute('data-type', type);
            expect(container, key).toHaveAttribute('data-scope', scope);
            expect(container, key).toHaveAttribute('data-source', source);
            expect(container, key).toHaveAttribute('data-editable', 'true');
            expect(container, key).toHaveAttribute('data-locked', 'false');
            expect(container, key).toHaveAttribute('data-problem', '');
            expect(container, key).toHaveAttribute('data-edit', '');
            expect(
                CONTROLS.filter((testId) => within(container).queryByTestId(testId) !== null),
                `${key} draws one control, its own`,
            ).toEqual([control]);
        }

        const tolerance = inSetting('price_tolerance', 'plugin-setting-input');
        expect(tolerance).toHaveAttribute('type', 'number');
        expect(tolerance).toHaveAttribute('step', 'any');
        expect(tolerance).toHaveAttribute('min', '0');
        expect(tolerance).toHaveAttribute('max', '10');
        expect(tolerance, 'the value in force').toHaveValue(0.5);
        const retries = inSetting('retries', 'plugin-setting-input');
        expect(retries).toHaveAttribute('type', 'number');
        expect(retries).toHaveAttribute('step', '1');
        expect(retries).toHaveValue(3);
        const nickname = inSetting('nickname', 'plugin-setting-input');
        expect(nickname).toHaveAttribute('type', 'text');
        expect(nickname).toHaveAttribute('maxlength', '12');
        expect(nickname).toHaveValue('mine');
        expect(inSetting('verbose', 'plugin-setting-toggle')).not.toBeChecked();
        const secret = inSetting('api_key', 'plugin-setting-secret-input');
        expect(secret).toHaveAttribute('type', 'password');
        expect(secret).toHaveAttribute('autocomplete', 'new-password');
        expect(secret).toHaveValue('');
        expect(queryInSetting('api_key', 'plugin-setting-secret-state'), 'a secret not set, one the caller may set: its input, nothing else').toBeNull();
        expect(saveButton(), 'nothing to save yet').toBeDisabled();
        expect(discardButton(), 'nothing to discard yet').toBeDisabled();

        await fireEvent.click(inSetting('region', 'plugin-setting-select-button'));
        expect(await within(setting('region')).findByTestId('plugin-setting-option-eu'), 'the option in force is the selected one').toHaveAttribute('aria-selected', 'true');
        expect(within(setting('region')).getByTestId('plugin-setting-option-us')).toHaveAttribute('aria-selected', 'false');
    });

    it('PSF-02: each control makes its edit, and Save writes one item per edit, in the order the plugin declares its fields', async () => {
        fake.save.mockResolvedValue({kind: 'saved'} satisfies SaveOutcome);
        fake.fetchEntry.mockResolvedValue(entry([REGION, TOLERANCE, RETRIES, VERBOSE, NICKNAME], {configured: true}));
        mount(entry([REGION, TOLERANCE, RETRIES, VERBOSE, NICKNAME]));

        // Made in the reverse order of the declaration, on purpose.
        await typeIn('nickname', 'someone');
        await fireEvent.click(inSetting('verbose', 'plugin-setting-toggle'));
        await typeIn('retries', '4');
        await typeIn('price_tolerance', '0.75');
        await choose('region', 'us');

        expect(setting('region')).toHaveAttribute('data-edit', 'value');
        expect(setting('price_tolerance')).toHaveAttribute('data-edit', 'text');
        expect(setting('retries')).toHaveAttribute('data-edit', 'text');
        expect(setting('verbose')).toHaveAttribute('data-edit', 'value');
        expect(setting('nickname')).toHaveAttribute('data-edit', 'text');
        expect(inSetting('verbose', 'plugin-setting-toggle')).toBeChecked();
        expect(saveButton()).toBeEnabled();
        expect(discardButton()).toBeEnabled();

        await pressSave();

        await waitFor(() => expect(fake.fetchEntry).toHaveBeenCalledTimes(1));
        await settled();
        expect(fake.save).toHaveBeenCalledTimes(1);
        expect(fake.save.mock.calls[0]).toStrictEqual([
            [
                {family: 'asset', plugin_code: 'mockprov', field_key: 'region', scope: 'user', value: 'us'},
                {family: 'asset', plugin_code: 'mockprov', field_key: 'price_tolerance', scope: 'system', value: 0.75},
                {family: 'asset', plugin_code: 'mockprov', field_key: 'retries', scope: 'user', value: 4},
                {family: 'asset', plugin_code: 'mockprov', field_key: 'verbose', scope: 'system', value: true},
                {family: 'asset', plugin_code: 'mockprov', field_key: 'nickname', scope: 'user', value: 'someone'},
            ],
        ]);
    });

    it('PSF-03: a field typed or chosen back to its value in force has no edit any more, and Save goes back to disabled', async () => {
        mount(entry([REGION, TOLERANCE, VERBOSE]));

        await typeIn('price_tolerance', '7');
        expect(setting('price_tolerance')).toHaveAttribute('data-edit', 'text');
        await typeIn('price_tolerance', '0.50');
        expect(setting('price_tolerance'), '0.50 says what 0.5 says').toHaveAttribute('data-edit', '');

        await choose('region', 'us');
        expect(setting('region')).toHaveAttribute('data-edit', 'value');
        await choose('region', 'eu');
        expect(setting('region')).toHaveAttribute('data-edit', '');

        await fireEvent.click(inSetting('verbose', 'plugin-setting-toggle'));
        expect(setting('verbose')).toHaveAttribute('data-edit', 'value');
        await fireEvent.click(inSetting('verbose', 'plugin-setting-toggle'));
        expect(setting('verbose')).toHaveAttribute('data-edit', '');

        expect(saveButton()).toBeDisabled();
        expect(fake.save).not.toHaveBeenCalled();
    });
});

// =====================================================================================================================
describe('PluginSettingsForm — a secret is write-only', () => {
    it('PSF-04: a secret not set: what is typed is sent once as secret_value, the input is empty after, and the event names the field only', async () => {
        const fresh = entry([SAVED_KEY], {configured: true});
        fake.save.mockResolvedValue({kind: 'saved'} satisfies SaveOutcome);
        fake.fetchEntry.mockResolvedValue(fresh);
        const {onsaved, rerender} = mount(entry([API_KEY]));

        await typeSecret('api_key', SECRET);
        expect(setting('api_key')).toHaveAttribute('data-edit', 'secret');
        expect(saveButton()).toBeEnabled();

        await pressSave();

        await waitFor(() => expect(onsaved).toHaveBeenCalledTimes(1));
        await settled();
        expect(onsaved, 'the plugin read again is handed over').toHaveBeenCalledWith(fresh);
        expect(fake.fetchEntry).toHaveBeenCalledWith('asset', 'mockprov');
        expect(fake.save).toHaveBeenCalledTimes(1);
        expect(fake.save.mock.calls[0]).toStrictEqual([[{family: 'asset', plugin_code: 'mockprov', field_key: 'api_key', scope: 'user', secret_value: SECRET}]]);
        expect(inSetting('api_key', 'plugin-setting-secret-input'), 'sent once, then forgotten').toHaveValue('');
        expect(setting('api_key')).toHaveAttribute('data-edit', '');
        expect(saveButton(), 'nothing left to save').toBeDisabled();
        expect(notified(), 'one event, naming the field, without a toast: the form shows the outcome').toStrictEqual([{name: 'pluginSettings.saved', detail: {family: 'asset', plugin_code: 'mockprov', fields: ['api_key']}}]);

        // What the parent does with the fresh state: the secret now reads as set.
        await rerender({entry: fresh});
        expect(within(form()).getByTestId('plugin-settings-status')).toHaveAttribute('data-configured', 'true');
        expect(inSetting('api_key', 'plugin-setting-secret-state')).toHaveAttribute('data-state', 'set');
        expect(queryInSetting('api_key', 'plugin-setting-secret-input')).toBeNull();
    });

    it.each<[string, SaveOutcome]>([
        ['saved', {kind: 'saved'}],
        ['refused', {kind: 'refused', results: [{field_key: 'api_key', success: false, error_code: 'INVALID_VALUE'}]}],
        ['in a conflict', {kind: 'conflict'}],
        ['without a usable key', {kind: 'keyUnavailable'}],
        ['failed', {kind: 'failed'}],
    ])('PSF-05: a typed secret reaches the write and nothing else — no event, no toast, no console line — when the write ends %s', async (_label, outcome) => {
        const spies = CONSOLE_METHODS.map((method) => vi.spyOn(console, method) as unknown as {mock: {calls: unknown[][]}});
        fake.save.mockResolvedValue(outcome);
        fake.fetchEntry.mockResolvedValue(entry([API_KEY, NICKNAME]));
        mount(entry([API_KEY, NICKNAME]));

        await typeSecret('api_key', SECRET);
        await typeIn('nickname', 'someone');
        await pressSave();

        await waitFor(() => expect(notified()).toHaveLength(1));
        await settled();
        expect(inspect(fake.save.mock.calls, {depth: null}), 'premise: the secret was handed to the write').toContain(SECRET);
        expect(notified()[0].detail?.fields, 'the event names the fields').toEqual(['api_key', 'nickname']);
        const events = inspect(fake.notify.mock.calls, {depth: null});
        expect(events, 'no event, no toast carries the secret').not.toContain(SECRET);
        expect(events, 'nor any other value: names only').not.toContain('someone');
        expect(consoleText(spies), 'no console line carries the secret').not.toContain(SECRET);
    });

    it('PSF-06: a saved secret says when it was set; Replace opens an empty input, Cancel closes it and drops what was typed', async () => {
        mount(entry([SAVED_KEY]));

        const state = inSetting('api_key', 'plugin-setting-secret-state');
        expect(state).toHaveAttribute('data-state', 'set');
        expect(text(state)).toBe(`pluginSettings.secret.setOn {date=⟨${UPDATED_AT}⟩}`);
        expect(queryInSetting('api_key', 'plugin-setting-secret-input'), 'the value never comes back: no input').toBeNull();
        expect(queryInSetting('api_key', 'plugin-setting-cancel-replace')).toBeNull();
        expect(discardButton()).toBeDisabled();

        await fireEvent.click(inSetting('api_key', 'plugin-setting-replace'));

        expect(inSetting('api_key', 'plugin-setting-secret-input')).toHaveValue('');
        expect(queryInSetting('api_key', 'plugin-setting-secret-state')).toBeNull();
        expect(queryInSetting('api_key', 'plugin-setting-replace')).toBeNull();
        expect(queryInSetting('api_key', 'plugin-setting-clear')).toBeNull();
        expect(saveButton(), 'nothing typed yet: nothing to save').toBeDisabled();
        expect(discardButton(), 'a replacement under way can be discarded').toBeEnabled();

        await typeSecret('api_key', SECRET);
        expect(setting('api_key')).toHaveAttribute('data-edit', 'secret');
        expect(saveButton()).toBeEnabled();

        await fireEvent.click(inSetting('api_key', 'plugin-setting-cancel-replace'));

        expect(queryInSetting('api_key', 'plugin-setting-secret-input')).toBeNull();
        expect(inSetting('api_key', 'plugin-setting-secret-state')).toHaveAttribute('data-state', 'set');
        expect(setting('api_key')).toHaveAttribute('data-edit', '');
        expect(saveButton()).toBeDisabled();
        expect(discardButton()).toBeDisabled();

        await fireEvent.click(inSetting('api_key', 'plugin-setting-replace'));
        expect(inSetting('api_key', 'plugin-setting-secret-input'), 'what was typed before Cancel is gone').toHaveValue('');
        expect(fake.save).not.toHaveBeenCalled();
    });

    it('PSF-07: a saved secret without a date reads as set', () => {
        mount(entry([field({...SAVED_KEY, updated_at: null})]));

        expect(text(inSetting('api_key', 'plugin-setting-secret-state'))).toBe('pluginSettings.secret.set');
    });

    it('PSF-08: Clear marks a saved secret to delete, Undo takes it back, and Save writes clear: true and nothing else', async () => {
        fake.save.mockResolvedValue({kind: 'saved'} satisfies SaveOutcome);
        fake.fetchEntry.mockResolvedValue(entry([API_KEY]));
        mount(entry([SAVED_KEY]));

        await fireEvent.click(inSetting('api_key', 'plugin-setting-clear'));

        expect(setting('api_key')).toHaveAttribute('data-edit', 'clear');
        expect(inSetting('api_key', 'plugin-setting-secret-state')).toHaveAttribute('data-state', 'clearing');
        expect(queryInSetting('api_key', 'plugin-setting-replace')).toBeNull();
        expect(queryInSetting('api_key', 'plugin-setting-clear')).toBeNull();
        expect(saveButton()).toBeEnabled();

        await fireEvent.click(inSetting('api_key', 'plugin-setting-undo'));

        expect(setting('api_key')).toHaveAttribute('data-edit', '');
        expect(inSetting('api_key', 'plugin-setting-secret-state')).toHaveAttribute('data-state', 'set');
        expect(saveButton()).toBeDisabled();

        await fireEvent.click(inSetting('api_key', 'plugin-setting-clear'));
        await pressSave();

        await waitFor(() => expect(fake.fetchEntry).toHaveBeenCalledTimes(1));
        await settled();
        expect(fake.save.mock.calls).toStrictEqual([[[{family: 'asset', plugin_code: 'mockprov', field_key: 'api_key', scope: 'user', clear: true}]]]);
    });
});

// =====================================================================================================================
describe('PluginSettingsForm — what the caller cannot change', () => {
    it.each([
        {who: 'an administrator, who is told the variable', variable: 'LIBREFOLIO_ASSET_MOCKPROV_REGION', note: 'pluginSettings.field.lockedBy {variable=LIBREFOLIO_ASSET_MOCKPROV_REGION}'},
        {who: 'a user, who is not', variable: null, note: 'pluginSettings.field.locked'},
    ])('PSF-09: a field a server variable sets is read-only for $who: its value in force, and the lock', ({variable, note}) => {
        mount(entry([field({...REGION, value: 'us', is_set: true, source: 'env', locked: true, editable: false, env_variable: variable}), NICKNAME]));

        const container = setting('region');
        expect(container).toHaveAttribute('data-editable', 'false');
        expect(container).toHaveAttribute('data-locked', 'true');
        expect(container).toHaveAttribute('data-source', 'env');
        expect(text(inSetting('region', 'plugin-setting-value')), 'the option’s English label: its key has no translation here').toBe('United States');
        expect(EDIT_CONTROLS.filter((testId) => within(container).queryByTestId(testId) !== null)).toEqual([]);
        expect(notesOf('region')).toEqual(['locked']);
        expect(text(noteOf('region', 'locked'))).toBe(note);
        if (variable === null) expect(container.textContent, 'no variable is named to someone not given it').not.toContain('LIBREFOLIO');
    });

    it('PSF-10: a secret a server variable sets reads as set, read-only, with the lock', () => {
        mount(entry([field({...API_KEY, scope: 'system', is_set: true, source: 'env', locked: true, editable: false, env_variable: 'LIBREFOLIO_ASSET_MOCKPROV_API_KEY'})]));

        expect(inSetting('api_key', 'plugin-setting-secret-state')).toHaveAttribute('data-state', 'env');
        expect(EDIT_CONTROLS.filter((testId) => queryInSetting('api_key', testId) !== null)).toEqual([]);
        expect(notesOf('api_key')).toEqual(['locked']);
    });

    it('PSF-11: an instance field is read-only for a user who is not an administrator: its value, a disabled toggle, a secret only set or not set — and no Save', () => {
        mount(
            entry([
                field({...TOLERANCE, editable: false}),
                field({...VERBOSE, value: true, is_set: true, source: 'db', editable: false}),
                field({key: 'endpoint', scope: 'system', editable: false}),
                field({key: 'system_key', secret: true, scope: 'system', is_set: true, source: 'db', editable: false}),
                field({key: 'other_key', secret: true, scope: 'system', editable: false}),
            ]),
        );

        expect(text(inSetting('price_tolerance', 'plugin-setting-value'))).toBe('0.5');
        expect(inSetting('verbose', 'plugin-setting-toggle')).toBeDisabled();
        expect(inSetting('verbose', 'plugin-setting-toggle')).toBeChecked();
        expect(text(inSetting('endpoint', 'plugin-setting-value')), 'no value').toBe('—');
        expect(inSetting('system_key', 'plugin-setting-secret-state')).toHaveAttribute('data-state', 'set');
        expect(text(inSetting('system_key', 'plugin-setting-secret-state'))).toBe('pluginSettings.secret.set');
        expect(inSetting('other_key', 'plugin-setting-secret-state')).toHaveAttribute('data-state', 'unset');
        for (const key of ['price_tolerance', 'verbose', 'endpoint', 'system_key', 'other_key']) {
            expect(setting(key), key).toHaveAttribute('data-editable', 'false');
            expect(setting(key), key).toHaveAttribute('data-locked', 'false');
            expect(notesOf(key), `${key} says why`).toEqual(['adminOnly']);
            expect(
                EDIT_CONTROLS.filter((testId) => queryInSetting(key, testId) !== null),
                `${key} offers nothing to change`,
            ).toEqual([]);
        }
        expect(screen.queryByTestId('plugin-settings-save'), 'nothing editable: no Save').toBeNull();
        expect(screen.queryByTestId('plugin-settings-discard'), 'nor Discard').toBeNull();
    });

    it.each<{label: string; over: Partial<SettingField>; notes: string[]; kind: string; note: string}>([
        {
            label: 'a server variable that is invalid, named for an administrator',
            over: {problem: 'invalid_env', locked: true, editable: false, env_variable: 'LIBREFOLIO_ASSET_MOCKPROV_PRICE_TOLERANCE'},
            notes: ['locked', 'invalidEnv'],
            kind: 'invalidEnv',
            note: 'pluginSettings.field.invalidEnvBy {variable=LIBREFOLIO_ASSET_MOCKPROV_PRICE_TOLERANCE}',
        },
        {label: 'a server variable that is invalid, not named for a user', over: {problem: 'invalid_env', locked: true, editable: false}, notes: ['locked', 'invalidEnv'], kind: 'invalidEnv', note: 'pluginSettings.field.invalidEnv'},
        {label: 'a saved value the field refuses now', over: {problem: 'invalid_stored'}, notes: ['invalidStored'], kind: 'invalidStored', note: 'pluginSettings.field.invalidStored'},
    ])('PSF-12: $label has its note', ({over, notes, kind, note}) => {
        mount(entry([field({...TOLERANCE, ...over})]));

        expect(setting('price_tolerance')).toHaveAttribute('data-problem', String(over.problem));
        expect(notesOf('price_tolerance')).toEqual(notes);
        expect(text(noteOf('price_tolerance', kind))).toBe(note);
    });

    it('PSF-13: a secret whose server variable is invalid shows no «set», only the lock and the problem', () => {
        mount(entry([field({...API_KEY, scope: 'system', is_set: true, source: 'env', locked: true, editable: false, problem: 'invalid_env', env_variable: 'LIBREFOLIO_ASSET_MOCKPROV_API_KEY'})]));

        expect(queryInSetting('api_key', 'plugin-setting-secret-state')).toBeNull();
        expect(notesOf('api_key')).toEqual(['locked', 'invalidEnv']);
        expect(queryInSetting('api_key', 'plugin-setting-secret-input')).toBeNull();
    });

    it('PSF-14: a saved secret this instance’s key cannot read says so, and offers an input to set it again', () => {
        mount(entry([field({...SAVED_KEY, problem: 'unreadable'})]));

        expect(setting('api_key')).toHaveAttribute('data-problem', 'unreadable');
        expect(notesOf('api_key')).toEqual(['unreadable']);
        expect(queryInSetting('api_key', 'plugin-setting-secret-state'), 'not «set»: it cannot be used').toBeNull();
        expect(inSetting('api_key', 'plugin-setting-secret-input')).toHaveValue('');
        expect(queryInSetting('api_key', 'plugin-setting-replace')).toBeNull();
        expect(queryInSetting('api_key', 'plugin-setting-clear')).toBeNull();
    });
});

// =====================================================================================================================
describe('PluginSettingsForm — back to the default', () => {
    it('PSF-15: a saved value offers «Use the default»: the default shows, Undo brings the saved value back, and Save writes clear: true', async () => {
        fake.save.mockResolvedValue({kind: 'saved'} satisfies SaveOutcome);
        fake.fetchEntry.mockResolvedValue(entry([field({...NICKNAME, value: 'anon', is_set: false, source: 'default'}), TOLERANCE]));
        mount(entry([NICKNAME, TOLERANCE]));

        expect(queryInSetting('price_tolerance', 'plugin-setting-default'), 'a value that is not saved has no default to go back to').toBeNull();

        await fireEvent.click(inSetting('nickname', 'plugin-setting-default'));

        expect(setting('nickname')).toHaveAttribute('data-edit', 'clear');
        expect(inSetting('nickname', 'plugin-setting-input'), 'the default shows').toHaveValue('anon');
        expect(notesOf('nickname')).toEqual(['toDefault']);
        expect(queryInSetting('nickname', 'plugin-setting-default')).toBeNull();

        await fireEvent.click(inSetting('nickname', 'plugin-setting-undo'));

        expect(setting('nickname')).toHaveAttribute('data-edit', '');
        expect(inSetting('nickname', 'plugin-setting-input')).toHaveValue('mine');
        expect(notesOf('nickname')).toEqual([]);

        await fireEvent.click(inSetting('nickname', 'plugin-setting-default'));
        await pressSave();

        await waitFor(() => expect(fake.fetchEntry).toHaveBeenCalledTimes(1));
        await settled();
        expect(fake.save.mock.calls).toStrictEqual([[[{family: 'asset', plugin_code: 'mockprov', field_key: 'nickname', scope: 'user', clear: true}]]]);
    });

    it('PSF-16: emptying a saved text deletes it as well: the same clear, with its note and Undo', async () => {
        mount(entry([NICKNAME]));

        await typeIn('nickname', '');

        expect(setting('nickname')).toHaveAttribute('data-edit', 'clear');
        expect(inSetting('nickname', 'plugin-setting-input'), 'what the user emptied stays empty').toHaveValue('');
        expect(notesOf('nickname')).toEqual(['toDefault']);
        expect(saveButton()).toBeEnabled();

        await fireEvent.click(inSetting('nickname', 'plugin-setting-undo'));
        expect(inSetting('nickname', 'plugin-setting-input')).toHaveValue('mine');
        expect(setting('nickname')).toHaveAttribute('data-edit', '');
    });
});

// =====================================================================================================================
describe('PluginSettingsForm — problems before the server’s', () => {
    it('PSF-17: a value the declared rules refuse is flagged on its field, and Save stays disabled until every field is fixed', async () => {
        mount(entry([TOLERANCE, RETRIES, NICKNAME]));

        await typeIn('price_tolerance', '11');

        const above = inSetting('price_tolerance', 'plugin-setting-problem');
        expect(above).toHaveAttribute('data-code', 'above');
        expect(text(above)).toBe('pluginSettings.problems.above {limit=10}');
        expect(inSetting('price_tolerance', 'plugin-setting-input')).toHaveAttribute('aria-invalid', 'true');
        expect(saveButton()).toBeDisabled();

        await typeIn('retries', '2.5');
        expect(inSetting('retries', 'plugin-setting-problem')).toHaveAttribute('data-code', 'integer');
        await typeIn('nickname', 'far too long a nickname');
        expect(inSetting('nickname', 'plugin-setting-problem')).toHaveAttribute('data-code', 'tooLong');
        expect(text(inSetting('nickname', 'plugin-setting-problem'))).toBe('pluginSettings.problems.tooLong {limit=12}');

        await typeIn('price_tolerance', '9.5');
        expect(queryInSetting('price_tolerance', 'plugin-setting-problem')).toBeNull();
        expect(inSetting('price_tolerance', 'plugin-setting-input')).not.toHaveAttribute('aria-invalid');
        expect(saveButton(), 'two fields still refused').toBeDisabled();

        await typeIn('retries', '2');
        await typeIn('nickname', 'someone');
        expect(within(form()).queryAllByTestId('plugin-setting-problem')).toEqual([]);
        expect(saveButton(), 'every field fixed').toBeEnabled();
        expect(fake.save).not.toHaveBeenCalled();
    });
});

// =====================================================================================================================
describe('PluginSettingsForm — how a write ends', () => {
    it('PSF-18: a refused write shows each refusal on its field, raises the refusal event with a toast, and keeps the edits', async () => {
        fake.save.mockResolvedValue({
            kind: 'refused',
            results: [
                {field_key: 'region', success: false, error_code: 'LOCKED_BY_ENV'},
                {field_key: 'price_tolerance', success: true, error_code: null},
                {field_key: 'nickname', success: false, error_code: 'A_CODE_FROM_A_NEWER_SERVER'},
            ],
        } satisfies SaveOutcome);
        const {onsaved} = mount(entry([REGION, TOLERANCE, NICKNAME]));
        await choose('region', 'us');
        await typeIn('price_tolerance', '2');
        await typeIn('nickname', 'someone');

        await pressSave();

        await waitFor(() => expect(notified('pluginSettings.save.refused')).toHaveLength(1));
        await settled();
        const regionRefusal = inSetting('region', 'plugin-setting-refusal');
        expect(regionRefusal).toHaveAttribute('data-code', 'LOCKED_BY_ENV');
        expect(regionRefusal).toHaveAttribute('role', 'alert');
        expect(text(regionRefusal)).toBe('pluginSettings.refusals.LOCKED_BY_ENV');
        const nicknameRefusal = inSetting('nickname', 'plugin-setting-refusal');
        expect(nicknameRefusal, 'the code as the server sent it').toHaveAttribute('data-code', 'A_CODE_FROM_A_NEWER_SERVER');
        expect(text(nicknameRefusal), 'worded as an invalid value').toBe('pluginSettings.refusals.INVALID_VALUE');
        expect(inSetting('nickname', 'plugin-setting-input')).toHaveAttribute('aria-invalid', 'true');
        expect(queryInSetting('price_tolerance', 'plugin-setting-refusal'), 'an accepted item is not refused').toBeNull();
        expect(notified()).toStrictEqual([
            {
                name: 'pluginSettings.save.refused',
                detail: {family: 'asset', plugin_code: 'mockprov', fields: ['region', 'price_tolerance', 'nickname'], refused: {region: 'LOCKED_BY_ENV', nickname: 'A_CODE_FROM_A_NEWER_SERVER'}},
                toast: {variant: 'error', message: 'pluginSettings.form.refused'},
            },
        ]);
        // Nothing was written: the edits stay to be corrected, and nothing is read again.
        expect(setting('nickname')).toHaveAttribute('data-edit', 'text');
        expect(setting('region')).toHaveAttribute('data-edit', 'value');
        expect(saveButton()).toBeEnabled();
        expect(fake.fetchEntry).not.toHaveBeenCalled();
        expect(onsaved).not.toHaveBeenCalled();

        await typeIn('nickname', 'someone else');

        expect(queryInSetting('nickname', 'plugin-setting-refusal'), 'editing a refused field takes its refusal down').toBeNull();
        expect(inSetting('region', 'plugin-setting-refusal'), 'and only its own').toHaveAttribute('data-code', 'LOCKED_BY_ENV');
    });

    it('PSF-19: a conflicting write raises the failure event with a toast, and reads the plugin again for onsaved', async () => {
        const fresh = entry([field({...NICKNAME, value: 'theirs'})], {configured: true});
        fake.save.mockResolvedValue({kind: 'conflict'} satisfies SaveOutcome);
        fake.fetchEntry.mockResolvedValue(fresh);
        const {onsaved} = mount(entry([NICKNAME]));
        await typeIn('nickname', 'someone');

        await pressSave();

        await waitFor(() => expect(onsaved).toHaveBeenCalledWith(fresh));
        await settled();
        expect(fake.fetchEntry).toHaveBeenCalledWith('asset', 'mockprov');
        expect(notified()).toStrictEqual([{name: 'pluginSettings.save.failed', detail: {family: 'asset', plugin_code: 'mockprov', fields: ['nickname'], reason: 'conflict'}, toast: {variant: 'error', message: 'pluginSettings.form.conflict'}}]);
    });

    it.each([
        {kind: 'keyUnavailable', message: 'pluginSettings.form.keyUnavailable'},
        {kind: 'failed', message: 'pluginSettings.form.saveFailed'},
    ] as const)('PSF-20: a write that ends $kind raises the failure event with its reason and a toast, keeps the edits, and reads nothing again', async ({kind, message}) => {
        fake.save.mockResolvedValue({kind} satisfies SaveOutcome);
        const {onsaved} = mount(entry([NICKNAME, SAVED_KEY]));
        await typeIn('nickname', 'someone');

        await pressSave();

        await waitFor(() => expect(notified()).toHaveLength(1));
        await settled();
        expect(notified()).toStrictEqual([{name: 'pluginSettings.save.failed', detail: {family: 'asset', plugin_code: 'mockprov', fields: ['nickname'], reason: kind}, toast: {variant: 'error', message}}]);
        expect(setting('nickname')).toHaveAttribute('data-edit', 'text');
        expect(saveButton(), 'the same edits can be sent again').toBeEnabled();
        expect(fake.fetchEntry).not.toHaveBeenCalled();
        expect(onsaved).not.toHaveBeenCalled();
    });

    it.each([
        {label: 'fails', answer: () => Promise.reject(new Error('read failed'))},
        {label: 'finds the plugin no more', answer: () => Promise.resolve(null)},
    ])('PSF-21: once saved, a read of the fresh state that $label hands nothing over, and the form is usable again', async ({answer}) => {
        fake.save.mockResolvedValue({kind: 'saved'} satisfies SaveOutcome);
        fake.fetchEntry.mockImplementation(answer);
        const {onsaved} = mount(entry([NICKNAME]));
        await typeIn('nickname', 'someone');

        await pressSave();

        await waitFor(() => expect(fake.fetchEntry).toHaveBeenCalledTimes(1));
        await settled();
        expect(onsaved).not.toHaveBeenCalled();
        expect(
            notified().map((event) => event.name),
            'the write is done either way',
        ).toEqual(['pluginSettings.saved']);
        expect(inSetting('nickname', 'plugin-setting-input')).toBeEnabled();
        expect(saveButton(), 'the form is empty again').toBeDisabled();
    });
});

// =====================================================================================================================
describe('PluginSettingsForm — busy, and Discard', () => {
    it('PSF-22: from Save until the plugin is read again the form is busy: data-busy and aria-busy true, every control disabled, a second Save starting nothing', async () => {
        const write = deferred<SaveOutcome>();
        const reread = deferred<PluginSettingsEntry | null>();
        const fresh = entry([REGION, TOLERANCE, VERBOSE, NICKNAME, API_KEY], {configured: true});
        fake.save.mockReturnValueOnce(write.promise);
        fake.fetchEntry.mockReturnValueOnce(reread.promise);
        const {onsaved} = mount(entry([REGION, TOLERANCE, VERBOSE, NICKNAME, API_KEY]));
        await typeIn('nickname', 'someone');

        await pressSave();

        expect(form()).toHaveAttribute('data-busy', 'true');
        expect(form()).toHaveAttribute('aria-busy', 'true');
        expect(saveButton()).toBeDisabled();
        expect(discardButton()).toBeDisabled();
        expect(inSetting('nickname', 'plugin-setting-input')).toBeDisabled();
        expect(inSetting('price_tolerance', 'plugin-setting-input')).toBeDisabled();
        expect(inSetting('verbose', 'plugin-setting-toggle')).toBeDisabled();
        expect(inSetting('region', 'plugin-setting-select-button')).toBeDisabled();
        expect(inSetting('api_key', 'plugin-setting-secret-input')).toBeDisabled();
        await fireEvent.click(saveButton());
        expect(fake.save, 'one write at a time').toHaveBeenCalledTimes(1);

        write.resolve({kind: 'saved'});
        await waitFor(() => expect(fake.fetchEntry).toHaveBeenCalledTimes(1));
        expect(form(), 'written, not read again yet: still busy').toHaveAttribute('data-busy', 'true');
        expect(onsaved).not.toHaveBeenCalled();

        reread.resolve(fresh);
        await settled();
        expect(form()).toHaveAttribute('aria-busy', 'false');
        expect(onsaved).toHaveBeenCalledWith(fresh);
        expect(inSetting('nickname', 'plugin-setting-input')).toBeEnabled();
    });

    it('PSF-23: Discard drops every edit and every replacement under way, and is offered only when there is something to drop', async () => {
        mount(entry([NICKNAME, SAVED_KEY]));
        expect(discardButton()).toBeDisabled();

        await typeIn('nickname', 'someone');
        await fireEvent.click(inSetting('api_key', 'plugin-setting-replace'));
        await typeSecret('api_key', SECRET);
        expect(discardButton()).toBeEnabled();

        await fireEvent.click(discardButton());

        expect(inSetting('nickname', 'plugin-setting-input')).toHaveValue('mine');
        expect(setting('nickname')).toHaveAttribute('data-edit', '');
        expect(queryInSetting('api_key', 'plugin-setting-secret-input')).toBeNull();
        expect(inSetting('api_key', 'plugin-setting-secret-state')).toHaveAttribute('data-state', 'set');
        expect(discardButton()).toBeDisabled();
        expect(saveButton()).toBeDisabled();
        expect(fake.save).not.toHaveBeenCalled();
    });
});

// =====================================================================================================================
describe('PluginSettingsForm — a field named like a property every object inherits', () => {
    it('PSF-24: a field named constructor draws with no edit, no problem and no refusal; typed, it is saved like any other, and refused on itself', async () => {
        const CONSTRUCTOR = field({key: 'constructor', label: 'Constructor', max_length: 5});
        fake.save.mockResolvedValueOnce({kind: 'refused', results: [{field_key: 'constructor', success: false, error_code: 'INVALID_VALUE'}]} satisfies SaveOutcome);
        mount(entry([CONSTRUCTOR, NICKNAME]));

        expect(setting('constructor')).toHaveAttribute('data-edit', '');
        expect(inSetting('constructor', 'plugin-setting-input')).toHaveValue('');
        expect(queryInSetting('constructor', 'plugin-setting-problem'), 'no problem it does not have').toBeNull();
        expect(queryInSetting('constructor', 'plugin-setting-refusal'), 'no refusal it was not given').toBeNull();
        expect(inSetting('constructor', 'plugin-setting-input')).not.toHaveAttribute('aria-invalid');
        expect(saveButton(), 'nothing to save').toBeDisabled();

        await typeIn('constructor', 'abc');

        expect(setting('constructor')).toHaveAttribute('data-edit', 'text');
        expect(saveButton()).toBeEnabled();

        await pressSave();

        await waitFor(() => expect(inSetting('constructor', 'plugin-setting-refusal')).toHaveAttribute('data-code', 'INVALID_VALUE'));
        await settled();
        expect(fake.save.mock.calls).toStrictEqual([[[{family: 'asset', plugin_code: 'mockprov', field_key: 'constructor', scope: 'user', value: 'abc'}]]]);
        expect(queryInSetting('nickname', 'plugin-setting-refusal'), 'the refusal is its own').toBeNull();

        await typeIn('constructor', 'abcdef');

        expect(queryInSetting('constructor', 'plugin-setting-refusal'), 'editing it takes its refusal down').toBeNull();
        expect(inSetting('constructor', 'plugin-setting-problem'), 'its declared rules apply').toHaveAttribute('data-code', 'tooLong');
    });

    it('PSF-25: a secret named constructor, unset and editable, shows an empty input; typed, it is a secret edit like any other, and Save sends exactly the text typed', async () => {
        const CONSTRUCTOR_KEY = field({key: 'constructor', secret: true, label: 'Constructor', min_length: 8});
        fake.save.mockResolvedValue({kind: 'saved'} satisfies SaveOutcome);
        fake.fetchEntry.mockResolvedValue(entry([field({...CONSTRUCTOR_KEY, is_set: true, source: 'db', updated_at: UPDATED_AT})], {configured: true}));
        mount(entry([CONSTRUCTOR_KEY]));

        expect(setting('constructor')).toHaveAttribute('data-edit', '');
        expect(inSetting('constructor', 'plugin-setting-secret-input'), 'nothing every object inherits shows as the secret').toHaveValue('');
        expect(queryInSetting('constructor', 'plugin-setting-secret-state'), 'unset and editable: the input, nothing else').toBeNull();
        expect(queryInSetting('constructor', 'plugin-setting-problem'), 'no problem it does not have').toBeNull();
        expect(saveButton(), 'nothing to save').toBeDisabled();

        await typeSecretAfterItsContent('constructor', SECRET);

        expect(setting('constructor')).toHaveAttribute('data-edit', 'secret');
        expect(inSetting('constructor', 'plugin-setting-secret-input')).toHaveValue(SECRET);
        expect(saveButton()).toBeEnabled();

        await pressSave();

        await waitFor(() => expect(fake.fetchEntry).toHaveBeenCalledTimes(1));
        await settled();
        expect(fake.save.mock.calls, 'exactly what was typed, nothing in front of it').toStrictEqual([[[{family: 'asset', plugin_code: 'mockprov', field_key: 'constructor', scope: 'user', secret_value: SECRET}]]]);
        expect(inSetting('constructor', 'plugin-setting-secret-input'), 'sent once, then forgotten: empty again').toHaveValue('');
        expect(setting('constructor')).toHaveAttribute('data-edit', '');
    });
});

// =====================================================================================================================
describe('PluginSettingsForm — the plugin’s icon', () => {
    it('PSF-26: a plugin with an icon shows it first in its heading: one image of that address, decorative, fetched without a referrer — and the form is still named by the plugin’s name alone', () => {
        mount(entry([NICKNAME], {icon_url: ICON}));

        const icons = within(form()).getAllByTestId('plugin-settings-plugin-icon');
        expect(icons, 'one icon').toHaveLength(1);
        const [icon] = icons;
        expect(icon).toBeInstanceOf(HTMLImageElement);
        expect(heading(), 'in the heading').toContainElement(icon);
        expect(icon).toHaveAttribute('src', ICON);
        expect(icon, 'the name beside it says what it shows: an alt text would say it twice').toHaveAttribute('alt', '');
        expect(icon, 'the icon’s host is not told which page asked for it').toHaveAttribute('referrerpolicy', 'no-referrer');
        expect(textAround(heading(), icon), 'the icon first, then the name').toEqual({before: '', after: 'Mock provider'});
        expect(fallbackIcon(), 'no neutral icon beside it').toBeNull();
        expect(form(), 'named by its heading: the plugin’s name, nothing of the icon').toHaveAccessibleName('Mock provider');
    });

    it('PSF-27: a plugin without an icon shows the neutral one in its place, hidden from assistive technology, and no image', () => {
        mount(entry([NICKNAME], {icon_url: null}));

        const fallback = within(form()).getByTestId('plugin-settings-plugin-icon-fallback');
        expect(fallback).toHaveAttribute('aria-hidden', 'true');
        expect(heading(), 'in the heading').toContainElement(fallback);
        expect(textAround(heading(), fallback), 'the neutral icon first, then the name').toEqual({before: '', after: 'Mock provider'});
        expect(pluginIcon()).toBeNull();
        expect(form().querySelector('img'), 'no image at all').toBeNull();
        expect(form()).toHaveAccessibleName('Mock provider');
    });

    it('PSF-28: an icon that fails to load gives way to the neutral one, still before the name', async () => {
        mount(entry([NICKNAME], {icon_url: ICON}));
        const icon = within(form()).getByTestId('plugin-settings-plugin-icon');
        expect(fallbackIcon(), 'premise: the image shows until it fails').toBeNull();

        await fireEvent.error(icon);

        expect(icon, 'the broken image is gone, not merely hidden').not.toBeInTheDocument();
        expect(pluginIcon()).toBeNull();
        const fallback = within(form()).getByTestId('plugin-settings-plugin-icon-fallback');
        expect(fallback).toHaveAttribute('aria-hidden', 'true');
        expect(textAround(heading(), fallback), 'the neutral icon first, then the name').toEqual({before: '', after: 'Mock provider'});
        expect(form()).toHaveAccessibleName('Mock provider');
    });

    it('PSF-29: an icon that failed is not tried again while the plugin publishes that address: its fresh state keeps the neutral one', async () => {
        const {rerender} = mount(entry([NICKNAME], {icon_url: ICON}));
        await fireEvent.error(within(form()).getByTestId('plugin-settings-plugin-icon'));
        expect(fallbackIcon(), 'premise: the icon failed').toBeInTheDocument();

        // What the parent hands over after a save: a new entry, the same address.
        await rerender({entry: entry([NICKNAME], {icon_url: ICON, configured: true})});

        expect(form(), 'premise: the fresh state is the one drawn').toHaveAttribute('data-configured', 'true');
        expect(pluginIcon(), 'the address that failed is not asked again').toBeNull();
        expect(fallbackIcon()).toBeInTheDocument();
    });

    it('PSF-30: after a failure, the next address the plugin publishes brings the image back, with that address', async () => {
        const {rerender} = mount(entry([NICKNAME], {icon_url: ICON}));
        await fireEvent.error(within(form()).getByTestId('plugin-settings-plugin-icon'));
        expect(fallbackIcon(), 'premise: the icon failed').toBeInTheDocument();

        await rerender({entry: entry([NICKNAME], {icon_url: OTHER_ICON})});

        expect(within(form()).getByTestId('plugin-settings-plugin-icon')).toHaveAttribute('src', OTHER_ICON);
        expect(fallbackIcon(), 'the neutral icon gives the place back').toBeNull();
    });
});

// =====================================================================================================================
describe('PluginSettingsForm — a tool plugin (family tool, X5-4b)', () => {
    const TOOL_USER = field({key: 'precision', type: 'integer', label: 'Precision', minimum: 0, maximum: 8, default: 2, value: 2, source: 'default'});
    const TOOL_SYSTEM = field({key: 'workers', type: 'integer', scope: 'system', label: 'Workers', minimum: 1, maximum: 8, default: 2, value: 2, source: 'default'});
    const tool = (fields: SettingField[]) => entry(fields, {family: 'tool', plugin_code: 'fx_converter', plugin_name: 'FX converter'});
    const toolForm = () => screen.getByTestId('plugin-settings-form-fx_converter');

    it('PSF-31: it publishes its family, shows the neutral icon (a tool has no icon_url), and a user field is editable by a non-admin', async () => {
        mount(tool([TOOL_USER, field({...TOOL_SYSTEM, editable: false})]));

        expect(toolForm()).toHaveAttribute('data-family', 'tool');
        expect(within(toolForm()).getByTestId('plugin-settings-plugin-icon-fallback')).toBeInTheDocument();
        expect(within(toolForm()).queryByTestId('plugin-settings-plugin-icon')).toBeNull();
        expect(setting('precision')).toHaveAttribute('data-editable', 'true');
        expect(setting('precision')).toHaveAttribute('data-scope', 'user');
        expect(inSetting('precision', 'plugin-setting-input')).toBeEnabled();
        expect(setting('workers'), 'a system field is the instance’s: read-only for a non-admin').toHaveAttribute('data-editable', 'false');
        expect(notesOf('workers')).toEqual(['adminOnly']);
        expect(EDIT_CONTROLS.filter((testId) => queryInSetting('workers', testId) !== null)).toEqual([]);
        expect(queryInSetting('precision', 'plugin-setting-secret-input'), 'a tool field is never secret').toBeNull();
    });

    it('PSF-32: a system field is editable by an administrator, and the write names the family tool, each field with its own scope', async () => {
        fake.save.mockResolvedValue({kind: 'saved'} satisfies SaveOutcome);
        fake.fetchEntry.mockResolvedValue(tool([field({...TOOL_USER, value: 6, is_set: true, source: 'db'}), field({...TOOL_SYSTEM, value: 4, is_set: true, source: 'db'})]));
        mount(tool([TOOL_USER, TOOL_SYSTEM]));

        await typeIn('precision', '6');
        await typeIn('workers', '4');
        await pressSave();

        await waitFor(() => expect(toolForm()).toHaveAttribute('data-busy', 'false'));
        await waitFor(() => expect(fake.fetchEntry).toHaveBeenCalled());
        expect(fake.save.mock.calls).toStrictEqual([
            [
                [
                    {family: 'tool', plugin_code: 'fx_converter', field_key: 'precision', scope: 'user', value: 6},
                    {family: 'tool', plugin_code: 'fx_converter', field_key: 'workers', scope: 'system', value: 4},
                ],
            ],
        ]);
        expect(fake.fetchEntry).toHaveBeenCalledWith('tool', 'fx_converter');
        expect(notified('pluginSettings.saved')).toStrictEqual([{name: 'pluginSettings.saved', detail: {family: 'tool', plugin_code: 'fx_converter', fields: ['precision', 'workers']}}]);
    });
});
