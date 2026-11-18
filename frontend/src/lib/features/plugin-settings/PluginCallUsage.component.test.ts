// @vitest-environment jsdom
/**
 * PluginCallUsage — the «Calls» block of a plugin's card, drawn inside the real `PluginSettingsForm` (project 76, lot U5;
 * mock section 2). Named `.component.test.ts` beside `callUsage.test.ts` (the rules without the DOM): the two names
 * differ by more than their case.
 *
 * The contract under test:
 *   - the block `plugin-settings-calls` (`data-managed`) comes after the plugin's own fields and before Discard / Save,
 *     and only on a card with a limit field or a usage block; the five limit fields are never drawn as generic fields;
 *   - one box `plugin-settings-calls-window` per window, in window order, publishing `data-window`, `data-state`
 *     (`open`, `full`, `stopped`, `invalid`), `data-full`, `data-control` (`input`, `locked`, `text`, `hidden`),
 *     `data-count`, `data-limit` and `data-edit`; its count (`plugin-settings-calls-count`), its limit
 *     (`plugin-settings-calls-limit`) or «no limit» (`plugin-settings-calls-no-limit`) for a reader;
 *   - an administrator types each limit (`plugin-settings-calls-input`, empty: no limit, «No limit» as placeholder): the
 *     limit saves with the card (`savePluginSettings`, one item per edit, a number as a number; emptying a saved value
 *     clears it); a problem and a refusal show in the box;
 *   - a full window's note (`plugin-settings-calls-full`, `data-window`, `data-kind` full / stopped / managed), the locks
 *     (`plugin-settings-calls-lock-note`), an invalid variable (`plugin-settings-calls-invalid-note`, administrators
 *     only), «only an administrator» (`plugin-settings-calls-admin-only`), the group's note
 *     (`plugin-settings-calls-group-note`) and the UTC note (`plugin-settings-calls-utc`);
 *   - an invalid limit variable puts the red message at the top of the card (`plugin-settings-invalid-env`, `data-case`);
 *   - a plugin whose calls count on a group the page names in `countGroups` has the row `plugin-settings-calls-on-group`
 *     with «Open» (`plugin-settings-calls-open-group`) when the group can be brought into view.
 *
 * Mocks, as in `PluginSettingsForm.component.test.ts`: `./pluginSettingsApi` (`savePluginSettings`, `fetchPluginEntry`
 * fakes), `$lib/i18n` (`_` answers `key {name=value, …}`: assertions name keys and values, never a catalogue's
 * sentence), `$lib/stores/app/notify.svelte` (a spy). Dates and numbers are expected through the same helpers the block
 * uses (`resumeAt`, `formatCount`) with the interface locale: the test pins which values the block chose.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

const fake = vi.hoisted(() => ({
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
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: fake.notify}));

import PluginSettingsForm from './PluginSettingsForm.svelte';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatCount, resumeAt} from './callUsage';
import type {CallUsage, CallWindow, CallWindowName, PluginSettingsEntry, SettingField} from './pluginSettingsApi';

// --- Fixtures --------------------------------------------------------------------------------------------------------

const WINDOWS: CallWindowName[] = ['minute', 'hour', 'day', 'week', 'month'];
const LATE = '2026-11-18T23:30:00Z';

function field(over: Partial<SettingField> & Pick<SettingField, 'key'>): SettingField {
    return {
        type: 'integer',
        scope: 'system',
        secret: false,
        required: false,
        label: over.key,
        description: '',
        label_key: null,
        description_key: null,
        missing_key: null,
        options: [],
        min_length: null,
        max_length: null,
        minimum: 0,
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

const limit = (window: CallWindowName, over: Partial<SettingField> = {}) => field({key: `call_limit_${window}`, label: `Calls per ${window}`, ...over});
/** The five limits as an administrator reads them, none set. */
const LIMITS = WINDOWS.map((window) => limit(window));
/** The five as another user reads them: instance fields, read-only. */
const MEMBER_LIMITS = LIMITS.map((candidate) => ({...candidate, editable: false}));
const CURRENCY = field({key: 'preferred_currency', type: 'select', scope: 'user', label: 'Preferred currency', options: [{value: 'all', label: 'All', label_key: null}], default: 'all', value: 'all', source: 'default'});

function usage(over: Partial<Record<CallWindowName, Partial<CallWindow>>> = {}): CallUsage {
    const counts: Record<CallWindowName, number> = {minute: 2, hour: 31, day: 412, week: 2960, month: 11840};
    return {family: 'asset', plugin_code: 'justetf', windows: WINDOWS.map((window) => ({window, count: counts[window], limit: null, resets_at: LATE, full: false, ...over[window]}))};
}

function entry(over: Partial<PluginSettingsEntry> = {}): PluginSettingsEntry {
    return {family: 'asset', plugin_code: 'justetf', plugin_name: 'justETF', icon_url: null, configured: true, fields: [CURRENCY, ...LIMITS], groups: [], used_by: [], name_key: null, call_usage: usage(), ...over};
}

/** `fields` with the window's limit replaced. */
function withLimit(fields: SettingField[], window: CallWindowName, over: Partial<SettingField>): SettingField[] {
    return fields.map((candidate) => (candidate.key === `call_limit_${window}` ? {...candidate, ...over} : candidate));
}

// --- Helpers ---------------------------------------------------------------------------------------------------------

function mount(theEntry: PluginSettingsEntry, extra: Record<string, unknown> = {}) {
    const onsaved = vi.fn();
    const utils = render(PluginSettingsForm, {props: {entry: theEntry, onsaved, ...extra}});
    return {...utils, onsaved};
}

const card = (code = 'justetf') => screen.getByTestId(`plugin-settings-form-${code}`);
const block = () => screen.getByTestId('plugin-settings-calls');
const boxes = () => within(block()).getAllByTestId('plugin-settings-calls-window');
const boxOf = (window: CallWindowName) => boxes().find((candidate) => candidate.getAttribute('data-window') === window) as HTMLElement;
const inBox = (window: CallWindowName, testId: string) => within(boxOf(window)).queryByTestId(testId);
const notes = (testId: string) => within(block()).queryAllByTestId(testId);
const noteOf = (testId: string, window: CallWindowName) => notes(testId).find((note) => note.getAttribute('data-window') === window);

function text(element: Element | null | undefined): string {
    return (element?.textContent ?? '').replace(/\s+/g, ' ').trim();
}

/** What the block shows for a number or a moment, in the interface's locale: the values it hands the translator. */
const count = (value: number) => formatCount(value, uiLocale());
const when = (iso: string) => resumeAt(iso, uiLocale());

beforeAll(async () => {
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

describe('PluginCallUsage — where the block is', () => {
    it('CU-1: after the plugin’s own fields and before Discard / Save; the limits are never generic fields', () => {
        mount(entry());

        const own = within(card()).getByTestId('plugin-setting-preferred_currency');
        const save = within(card()).getByTestId('plugin-settings-save');
        expect(own.compareDocumentPosition(block()) & Node.DOCUMENT_POSITION_FOLLOWING, 'the block follows the own fields').toBeTruthy();
        expect(block().compareDocumentPosition(save) & Node.DOCUMENT_POSITION_FOLLOWING, 'Save follows the block').toBeTruthy();
        for (const window of WINDOWS) expect(within(card()).queryByTestId(`plugin-setting-call_limit_${window}`), `call_limit_${window} is not a generic field`).toBeNull();
        expect(text(within(block()).getByRole('heading'))).toBe('pluginSettings.calls.title');
    });

    it('CU-2: a card with neither a limit field nor a usage block has no block; one with only the limits has the block alone, with Save', () => {
        const {unmount} = mount(entry({fields: [CURRENCY], call_usage: undefined}));
        expect(screen.queryByTestId('plugin-settings-calls')).toBeNull();
        unmount();

        mount(entry({fields: LIMITS}));
        expect(boxes()).toHaveLength(5);
        expect(within(card()).queryAllByTestId(/^plugin-setting-/)).toEqual([]);
        expect(within(card()).getByTestId('plugin-settings-save')).toBeDisabled();
    });
});

describe('PluginCallUsage — the boxes', () => {
    it('CU-3: no limit (administrator): five boxes in window order, each count, an empty input with «No limit», no note but the UTC one', () => {
        mount(entry());

        expect(boxes().map((box) => box.getAttribute('data-window'))).toEqual(WINDOWS);
        expect(boxes().map((box) => box.getAttribute('data-state'))).toEqual(['open', 'open', 'open', 'open', 'open']);
        expect(boxes().map((box) => box.getAttribute('data-control'))).toEqual(['input', 'input', 'input', 'input', 'input']);
        expect(boxes().map((box) => box.getAttribute('data-count'))).toEqual(['2', '31', '412', '2960', '11840']);
        expect(text(inBox('month', 'plugin-settings-calls-count'))).toBe(count(11840));
        const input = inBox('day', 'plugin-settings-calls-input') as HTMLInputElement;
        expect(input.value).toBe('');
        expect(input.placeholder).toBe('pluginSettings.calls.noLimit');
        expect(input).toHaveAccessibleName('pluginSettings.calls.limitOf {window=pluginSettings.calls.window.day}');
        expect(inBox('day', 'plugin-settings-calls-limit')).toBeNull();
        expect(notes('plugin-settings-calls-full')).toEqual([]);
        expect(notes('plugin-settings-calls-admin-only')).toEqual([]);
        expect(notes('plugin-settings-calls-utc')).toHaveLength(1);
        expect(block()).toHaveAttribute('data-managed', 'false');
    });

    it('CU-4: a limit: «count / limit», the input holding it', () => {
        mount(entry({fields: withLimit([CURRENCY, ...LIMITS], 'day', {value: 2000, is_set: true, source: 'db'}), call_usage: usage({day: {limit: 2000}})}));

        expect(boxOf('day')).toHaveAttribute('data-limit', '2000');
        expect(text(inBox('day', 'plugin-settings-calls-limit'))).toBe(`/ ${count(2000)}`);
        expect((inBox('day', 'plugin-settings-calls-input') as HTMLInputElement).value).toBe('2000');
    });

    it('CU-5: read-only for another user: text, «no limit» beside a count without one, and «only an administrator»', () => {
        mount(entry({fields: withLimit([CURRENCY, ...MEMBER_LIMITS], 'month', {value: 50000, is_set: true, source: 'db'}), call_usage: usage({month: {limit: 50000}})}));

        expect(within(block()).queryAllByTestId('plugin-settings-calls-input')).toEqual([]);
        expect(boxes().map((box) => box.getAttribute('data-control'))).toEqual(['text', 'text', 'text', 'text', 'text']);
        expect(text(inBox('day', 'plugin-settings-calls-no-limit'))).toBe('pluginSettings.calls.noLimitInline');
        expect(inBox('month', 'plugin-settings-calls-no-limit')).toBeNull();
        expect(text(inBox('month', 'plugin-settings-calls-limit'))).toBe(`/ ${count(50000)}`);
        expect(notes('plugin-settings-calls-admin-only').map(text)).toEqual(['pluginSettings.calls.adminOnly']);
    });
});

describe('PluginCallUsage — full and stopped windows', () => {
    it('CU-6: a full day: the box full, its note with the count, the limit, the date and the time of UTC', () => {
        mount(entry({fields: withLimit([CURRENCY, ...LIMITS], 'day', {value: 2000, is_set: true, source: 'db'}), call_usage: usage({day: {count: 2000, limit: 2000, full: true}})}));

        expect(boxOf('day')).toHaveAttribute('data-full', 'true');
        expect(boxOf('day')).toHaveAttribute('data-state', 'full');
        const note = noteOf('plugin-settings-calls-full', 'day');
        expect(note).toHaveAttribute('data-kind', 'full');
        const {date, time} = when(LATE);
        expect(text(note)).toBe(`pluginSettings.calls.full.day {count=${count(2000)}, date=${date}, limit=${count(2000)}, time=${time}}`);
        expect(notes('plugin-settings-calls-full'), 'one note: only the day is full').toHaveLength(1);
    });

    it('CU-7: a full minute: the time only', () => {
        mount(entry({fields: withLimit([CURRENCY, ...LIMITS], 'minute', {value: 30, is_set: true, source: 'db'}), call_usage: usage({minute: {count: 30, limit: 30, full: true}})}));

        expect(text(noteOf('plugin-settings-calls-full', 'minute'))).toBe(`pluginSettings.calls.full.minute {count=30, limit=30, time=${when(LATE).time}}`);
    });

    it('CU-8: a limit of 0: «stopped», never «resumes»', () => {
        mount(entry({fields: withLimit([CURRENCY, ...LIMITS], 'day', {value: 0, is_set: true, source: 'db'}), call_usage: usage({day: {count: 0, limit: 0, full: true}})}));

        expect(boxOf('day')).toHaveAttribute('data-state', 'stopped');
        expect(boxOf('day')).toHaveAttribute('data-full', 'true');
        const note = noteOf('plugin-settings-calls-full', 'day');
        expect(note).toHaveAttribute('data-kind', 'stopped');
        expect(text(note)).toBe('pluginSettings.calls.stopped.day');
    });
});

describe('PluginCallUsage — limits a server variable sets', () => {
    const lockedMonth = (variable: string | null) => withLimit([CURRENCY, ...LIMITS], 'month', {value: 50000, is_set: true, source: 'env', locked: true, editable: false, env_variable: variable});

    it('CU-9: named for an administrator: the value with a lock, no input, «Month — Set by the server variable …» under the grid', () => {
        mount(entry({fields: lockedMonth('LIBREFOLIO_PLUGIN_ASSET_JUSTETF_CALL_LIMIT_MONTH'), call_usage: usage({month: {limit: 50000}})}));

        expect(boxOf('month')).toHaveAttribute('data-control', 'locked');
        expect(inBox('month', 'plugin-settings-calls-input')).toBeNull();
        expect(text(inBox('month', 'plugin-settings-calls-locked'))).toBe(count(50000));
        expect(text(noteOf('plugin-settings-calls-lock-note', 'month'))).toBe('pluginSettings.calls.window.month — pluginSettings.field.lockedBy {variable=LIBREFOLIO_PLUGIN_ASSET_JUSTETF_CALL_LIMIT_MONTH}');
        expect(notes('plugin-settings-calls-lock-note')).toHaveLength(1);
        expect(notes('plugin-settings-calls-admin-only'), 'a lock is not «only an administrator»').toEqual([]);
    });

    it('CU-10: not named (the server gives the name to administrators only): «Month — Set by the server»', () => {
        mount(entry({fields: lockedMonth(null), call_usage: usage({month: {limit: 50000}})}));

        expect(text(noteOf('plugin-settings-calls-lock-note', 'month'))).toBe('pluginSettings.calls.window.month — pluginSettings.field.locked');
    });
});

describe('PluginCallUsage — the managed profile', () => {
    it('CU-11: every limit hidden: counts only, never «No limit», no input, no Save; a full month says when it resumes, no number', () => {
        mount(entry({plugin_code: 'yfinance', plugin_name: 'Yahoo Finance', fields: [], call_usage: usage({month: {count: 10000, full: true}})}), {});

        const yahoo = card('yfinance');
        expect(block()).toHaveAttribute('data-managed', 'true');
        expect(boxes().map((box) => box.getAttribute('data-control'))).toEqual(['hidden', 'hidden', 'hidden', 'hidden', 'hidden']);
        expect(within(block()).queryAllByTestId('plugin-settings-calls-no-limit')).toEqual([]);
        expect(within(block()).queryAllByTestId('plugin-settings-calls-limit')).toEqual([]);
        expect(within(block()).queryAllByTestId('plugin-settings-calls-input')).toEqual([]);
        expect(within(yahoo).queryByTestId('plugin-settings-save')).toBeNull();
        expect(notes('plugin-settings-calls-admin-only')).toEqual([]);
        const note = noteOf('plugin-settings-calls-full', 'month');
        expect(note).toHaveAttribute('data-kind', 'managed');
        const {date, time} = when(LATE);
        expect(text(note)).toBe(`pluginSettings.calls.managedFull {date=${date}, time=${time}}`);
        expect(within(yahoo).queryByTestId('plugin-settings-invalid-env'), 'configured: no message on top').toBeNull();
    });

    it('CU-12: not configured with nothing shown to fix: the managed text on top, naming no variable', () => {
        mount(entry({plugin_code: 'yfinance', plugin_name: 'Yahoo Finance', configured: false, fields: [], call_usage: usage()}));

        const top = within(card('yfinance')).getByTestId('plugin-settings-invalid-env');
        expect(top).toHaveAttribute('data-case', 'managed');
        expect(text(top)).toBe('pluginSettings.notConfigured.managed {provider=Yahoo Finance}');
    });
});

describe('PluginCallUsage — an invalid limit variable', () => {
    const VARIABLE = 'LIBREFOLIO_PLUGIN_ASSET_YFINANCE_CALL_LIMIT_DAY';
    const invalidDay = (fields: SettingField[], variable: string | null) => withLimit(fields, 'day', {source: 'env', is_set: true, locked: true, editable: false, problem: 'invalid_env', env_variable: variable});
    const yahoo = (fields: SettingField[]) => entry({plugin_code: 'yfinance', plugin_name: 'Yahoo Finance', configured: false, fields, call_usage: usage()});

    it('CU-13: an administrator: the message on top with the variable and the provider; the day red, «invalid value»; the variable under the grid', () => {
        mount(yahoo(invalidDay(LIMITS, VARIABLE)));

        const top = within(card('yfinance')).getByTestId('plugin-settings-invalid-env');
        expect(top).toHaveAttribute('data-case', 'invalidLimitAdmin');
        expect(top).toHaveAttribute('role', 'alert');
        expect(text(top)).toBe(`pluginSettings.notConfigured.invalidLimitAdmin {provider=Yahoo Finance, variable=${VARIABLE}}`);
        expect(boxOf('day')).toHaveAttribute('data-state', 'invalid');
        expect(boxOf('day')).toHaveAttribute('data-full', 'false');
        expect(text(inBox('day', 'plugin-settings-calls-invalid'))).toBe('pluginSettings.calls.invalid');
        expect(inBox('day', 'plugin-settings-calls-no-limit')).toBeNull();
        expect(text(noteOf('plugin-settings-calls-invalid-note', 'day'))).toBe(`pluginSettings.calls.window.day — pluginSettings.calls.invalidBy {variable=${VARIABLE}}`);
        expect(notes('plugin-settings-calls-lock-note'), 'an invalid variable is not a lock note').toEqual([]);
        expect(screen.queryByTestId('provider-configure'), 'no «Configure»').toBeNull();
    });

    it('CU-14: another user: «stopped, tell the administrator» on top, «invalid value» in the box, no variable anywhere', () => {
        mount(yahoo(invalidDay(MEMBER_LIMITS, null)));

        const top = within(card('yfinance')).getByTestId('plugin-settings-invalid-env');
        expect(top).toHaveAttribute('data-case', 'invalidMember');
        expect(text(top)).toBe('pluginSettings.notConfigured.invalidMember {provider=Yahoo Finance}');
        expect(boxOf('day')).toHaveAttribute('data-state', 'invalid');
        expect(text(inBox('day', 'plugin-settings-calls-invalid'))).toBe('pluginSettings.calls.invalid');
        expect(notes('plugin-settings-calls-invalid-note')).toEqual([]);
        expect(text(card('yfinance'))).not.toContain('LIBREFOLIO_');
    });
});

describe('PluginCallUsage — a limit saves with the card', () => {
    it('CU-15: typed: the box’s edit; Save writes it as a number, an instance item, then reads the plugin again', async () => {
        fake.save.mockResolvedValueOnce({kind: 'saved'});
        fake.fetchEntry.mockResolvedValueOnce(entry());
        const {onsaved} = mount(entry());

        await fireEvent.input(inBox('day', 'plugin-settings-calls-input') as HTMLElement, {target: {value: '2000'}});
        expect(boxOf('day')).toHaveAttribute('data-edit', 'text');
        await fireEvent.click(within(card()).getByTestId('plugin-settings-save'));

        await waitFor(() => expect(onsaved).toHaveBeenCalledTimes(1));
        expect(fake.save).toHaveBeenCalledWith([{family: 'asset', plugin_code: 'justetf', field_key: 'call_limit_day', scope: 'system', value: 2000}]);
        expect(fake.fetchEntry).toHaveBeenCalledWith('asset', 'justetf');
    });

    it('CU-16: a saved limit emptied: no limit, written as a clear', async () => {
        fake.save.mockResolvedValueOnce({kind: 'saved'});
        fake.fetchEntry.mockResolvedValueOnce(entry());
        const {onsaved} = mount(entry({fields: withLimit([CURRENCY, ...LIMITS], 'week', {value: 9000, is_set: true, source: 'db'}), call_usage: usage({week: {limit: 9000}})}));

        await fireEvent.input(inBox('week', 'plugin-settings-calls-input') as HTMLElement, {target: {value: ''}});
        expect(boxOf('week')).toHaveAttribute('data-edit', 'clear');
        await fireEvent.click(within(card()).getByTestId('plugin-settings-save'));

        await waitFor(() => expect(onsaved).toHaveBeenCalledTimes(1));
        expect(fake.save).toHaveBeenCalledWith([{family: 'asset', plugin_code: 'justetf', field_key: 'call_limit_week', scope: 'system', clear: true}]);
    });

    it('CU-17: a value below 0 is a problem in its box, and Save waits; a refusal shows in its box', async () => {
        const {unmount} = mount(entry());
        await fireEvent.input(inBox('hour', 'plugin-settings-calls-input') as HTMLElement, {target: {value: '-1'}});
        expect(inBox('hour', 'plugin-setting-problem')).toHaveAttribute('data-code', 'below');
        expect(within(card()).getByTestId('plugin-settings-save')).toBeDisabled();
        unmount();

        fake.save.mockResolvedValueOnce({kind: 'refused', results: [{field_key: 'call_limit_hour', success: false, error_code: 'INVALID_VALUE'}]});
        mount(entry());
        await fireEvent.input(inBox('hour', 'plugin-settings-calls-input') as HTMLElement, {target: {value: '5'}});
        await fireEvent.click(within(card()).getByTestId('plugin-settings-save'));
        await waitFor(() => expect(inBox('hour', 'plugin-setting-refusal')).toHaveAttribute('data-code', 'INVALID_VALUE'));
    });
});

describe('PluginCallUsage — shared groups', () => {
    const reader = () => entry({plugin_code: 'coingecko_price', plugin_name: 'CoinGecko', fields: [], groups: ['coingecko'], call_usage: undefined});

    it('CU-18: a reader of a group that owns the count: «its calls count on …» with Open, which brings the group into view', async () => {
        const onopengroup = vi.fn();
        mount(reader(), {countGroups: ['coingecko'], groupNames: {coingecko: 'CoinGecko account'}, onopengroup});

        const row = within(card('coingecko_price')).getByTestId('plugin-settings-calls-on-group');
        expect(row).toHaveAttribute('data-group', 'coingecko');
        expect(text(row)).toContain('pluginSettings.group.countsOn {group=CoinGecko account}');
        await fireEvent.click(within(row).getByTestId('plugin-settings-calls-open-group'));
        expect(onopengroup).toHaveBeenCalledWith('coingecko');
        expect(screen.queryByTestId('plugin-settings-calls'), 'the reader has no block of its own').toBeNull();
    });

    it('CU-19: no row when the page names no counting group; no Open when the group cannot be brought into view', () => {
        const {unmount} = mount(reader(), {onopengroup: vi.fn()});
        expect(screen.queryByTestId('plugin-settings-calls-on-group')).toBeNull();
        unmount();

        mount(reader(), {countGroups: ['coingecko'], onopengroup: vi.fn(), openableGroups: []});
        expect(screen.getByTestId('plugin-settings-calls-on-group')).toBeInTheDocument();
        expect(screen.queryByTestId('plugin-settings-calls-open-group')).toBeNull();
    });

    it('CU-20: CoinGecko’s group has its note (A8) in its block; another card has none', () => {
        const {unmount} = mount(entry({family: 'group', plugin_code: 'coingecko', plugin_name: 'CoinGecko', fields: LIMITS, call_usage: {...usage(), family: 'group', plugin_code: 'coingecko'}}));
        expect(notes('plugin-settings-calls-group-note').map(text)).toEqual(['pluginSettings.group.coingecko.callsNote']);
        unmount();

        mount(entry());
        expect(notes('plugin-settings-calls-group-note')).toEqual([]);
    });
});
