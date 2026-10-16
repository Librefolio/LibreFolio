// @vitest-environment jsdom
/**
 * PluginSettingsTab — Settings › Plugins (workstream X, lot CP11b; plan 03 §4.4, decisions D-X13 to D-X15).
 *
 * The contract under test:
 *   - on mount the tab reads every plugin's settings once, unfiltered (`fetchPluginSettings()`); its root
 *     `plugin-settings-tab` publishes `data-busy` (with `aria-busy`) true while that read is in flight, and shows no
 *     group, no empty state and no error meanwhile;
 *   - the entries are grouped by family, one `plugin-settings-family` (`data-family`) per family: the price sources
 *     (`asset`) before the exchange-rate sources (`fx`) whatever the order of the answer, each family in the answer's
 *     order, a family without entries left out; one form `plugin-settings-form-{code}` per entry, inside its family;
 *   - each family's title (`h3`) starts with the family's icon, `plugin-settings-family-icon` (`aria-hidden`): one per
 *     family shown, each its own, none for a family left out. Which icon is which is pinned by
 *     `pluginSettingsForm.test.ts` (`FAMILY_ICONS`);
 *   - an answer with no entry shows `plugin-settings-empty`, a read that fails `plugin-settings-load-error` (role
 *     alert), each alone;
 *   - a save in a form hands the plugin's fresh state back, and the tab shows it in place of the old one, the other
 *     plugins untouched.
 *
 * Not pinned: «an older read never replaces a newer one» (the generation counter of `load()`). The tab reads once, on
 * mount, and offers no way to read again: two reads never overlap through its surface. `PluginSettingsModal.test.ts`
 * pins the same rule where a second read can be started (a re-opening).
 *
 * Mocks, all owned here: `./pluginSettingsApi` (`fetchPluginSettings`, `savePluginSettings`, `fetchPluginEntry` are
 * fakes the test answers, deferred where "in flight" is the subject; the narrowing stays real); `$lib/i18n` (only `_`,
 * answering a key with itself); `$lib/stores/app/notify.svelte` (a spy). The forms are the real ones: what the tab
 * hands them is observed as they draw it, and their own contract is pinned by `PluginSettingsForm.component.test.ts`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

const fake = vi.hoisted(() => ({
    fetchAll: vi.fn(),
    save: vi.fn(),
    fetchEntry: vi.fn(),
    notify: vi.fn(),
}));

vi.mock('./pluginSettingsApi', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./pluginSettingsApi')>()),
    fetchPluginSettings: fake.fetchAll,
    savePluginSettings: fake.save,
    fetchPluginEntry: fake.fetchEntry,
}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: readable((key: string) => key)};
});
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: fake.notify}));

import PluginSettingsTab from './PluginSettingsTab.svelte';
import type {PluginSettingsEntry, SettingField, SettingsFamily} from './pluginSettingsApi';
import {FAMILY_TITLE_KEYS} from './pluginSettingsForm';

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

function plugin(family: SettingsFamily, code: string, over: Partial<PluginSettingsEntry> = {}): PluginSettingsEntry {
    return {family, plugin_code: code, plugin_name: code, icon_url: null, configured: false, fields: [nickname()], ...over};
}

const JUSTETF = plugin('asset', 'justetf');
const BORSA = plugin('asset', 'borsa_italiana', {configured: true});
const ECB = plugin('fx', 'ecb', {configured: true});
const MOCKFX = plugin('fx', 'mockfx');

// --- Helpers ---------------------------------------------------------------------------------------------------------

const tab = () => screen.getByTestId('plugin-settings-tab');
const form = (code: string) => screen.getByTestId(`plugin-settings-form-${code}`);

/** The section of `family`, found by what it publishes: never by its place on the page. */
function familySection(family: SettingsFamily): HTMLElement {
    const section = screen.queryAllByTestId('plugin-settings-family').find((element) => element.getAttribute('data-family') === family);
    if (!section) throw new Error(`no plugin-settings-family for ${family}`);
    return section;
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

/** The groups, top to bottom: each family with the codes of its forms, in order. */
function groups(): Array<{family: string | null; plugins: string[]}> {
    return screen.queryAllByTestId('plugin-settings-family').map((group) => ({
        family: group.getAttribute('data-family'),
        plugins: within(group)
            .queryAllByTestId(/^plugin-settings-form-/)
            .map((element) => (element.getAttribute('data-testid') ?? '').replace(/^plugin-settings-form-/, '')),
    }));
}

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
    await waitFor(() => expect(tab()).toHaveAttribute('data-busy', 'false'));
}

// --- Lifecycle -------------------------------------------------------------------------------------------------------

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    for (const mock of Object.values(fake)) mock.mockReset();
});

afterEach(() => {
    cleanup();
});

// =====================================================================================================================
describe('PluginSettingsTab — the read', () => {
    it('PST-01: reads every plugin once on mount, unfiltered, and is busy until the answer is in — no group, no empty state, no error meanwhile', async () => {
        const read = deferred<PluginSettingsEntry[]>();
        fake.fetchAll.mockReturnValueOnce(read.promise);

        render(PluginSettingsTab);

        expect(tab()).toHaveAttribute('data-busy', 'true');
        expect(tab()).toHaveAttribute('aria-busy', 'true');
        expect(screen.queryAllByTestId('plugin-settings-family')).toEqual([]);
        expect(screen.queryByTestId('plugin-settings-empty'), 'not loaded is not empty').toBeNull();
        expect(screen.queryByTestId('plugin-settings-load-error')).toBeNull();
        expect(fake.fetchAll).toHaveBeenCalledTimes(1);
        const [filter] = fake.fetchAll.mock.calls[0] as [unknown?];
        expect(filter ?? {}, 'no filter: every plugin the API lists').toEqual({});

        read.resolve([JUSTETF]);

        await loaded();
        expect(tab()).toHaveAttribute('aria-busy', 'false');
        expect(groups()).toEqual([{family: 'asset', plugins: ['justetf']}]);
        expect(fake.fetchAll, 'one read').toHaveBeenCalledTimes(1);
    });

    it('PST-02: groups the price sources before the exchange-rate sources, each family in the order of the answer', async () => {
        fake.fetchAll.mockResolvedValueOnce([ECB, JUSTETF, MOCKFX, BORSA]);

        render(PluginSettingsTab);

        await loaded();
        expect(groups()).toEqual([
            {family: 'asset', plugins: ['justetf', 'borsa_italiana']},
            {family: 'fx', plugins: ['ecb', 'mockfx']},
        ]);
        expect(form('borsa_italiana'), 'each form draws its own entry').toHaveAttribute('data-configured', 'true');
        expect(form('justetf')).toHaveAttribute('data-configured', 'false');
    });

    it('PST-03: leaves out a family without entries', async () => {
        fake.fetchAll.mockResolvedValueOnce([MOCKFX, ECB]);

        render(PluginSettingsTab);

        await loaded();
        expect(groups()).toEqual([{family: 'fx', plugins: ['mockfx', 'ecb']}]);
    });

    it('PST-04: an answer without plugins shows the empty state, alone', async () => {
        fake.fetchAll.mockResolvedValueOnce([]);

        render(PluginSettingsTab);

        await loaded();
        expect(screen.getByTestId('plugin-settings-empty')).toBeInTheDocument();
        expect(screen.queryAllByTestId('plugin-settings-family')).toEqual([]);
        expect(screen.queryByTestId('plugin-settings-load-error')).toBeNull();
    });

    it('PST-05: a read that fails shows the load error, alone', async () => {
        const read = deferred<PluginSettingsEntry[]>();
        fake.fetchAll.mockReturnValueOnce(read.promise);
        render(PluginSettingsTab);
        expect(tab(), 'premise: the read is in flight').toHaveAttribute('data-busy', 'true');

        read.reject(new Error('settings unavailable'));

        await loaded();
        expect(screen.getByTestId('plugin-settings-load-error')).toHaveAttribute('role', 'alert');
        expect(screen.queryByTestId('plugin-settings-empty'), 'a failure is not an empty list').toBeNull();
        expect(screen.queryAllByTestId('plugin-settings-family')).toEqual([]);
    });
});

// =====================================================================================================================
describe('PluginSettingsTab — a save', () => {
    it('PST-06: a form that saved shows the plugin’s fresh state in place of the old one, the other plugins untouched', async () => {
        fake.fetchAll.mockResolvedValueOnce([JUSTETF, BORSA, MOCKFX]);
        fake.save.mockResolvedValueOnce({kind: 'saved'});
        fake.fetchEntry.mockResolvedValueOnce(plugin('asset', 'justetf', {configured: true, fields: [{...nickname(), value: 'someone', is_set: true, source: 'db'}]}));
        render(PluginSettingsTab);
        await loaded();
        expect(form('justetf'), 'premise').toHaveAttribute('data-configured', 'false');

        await fireEvent.input(within(form('justetf')).getByTestId('plugin-setting-input'), {target: {value: 'someone'}});
        await fireEvent.click(within(form('justetf')).getByTestId('plugin-settings-save'));

        await waitFor(() => expect(form('justetf')).toHaveAttribute('data-configured', 'true'));
        expect(fake.fetchEntry).toHaveBeenCalledWith('asset', 'justetf');
        expect(within(form('justetf')).getByTestId('plugin-setting-nickname'), 'the saved value is the one in force now').toHaveAttribute('data-source', 'db');
        expect(within(form('justetf')).getByTestId('plugin-setting-input')).toHaveValue('someone');
        expect(form('borsa_italiana')).toHaveAttribute('data-configured', 'true');
        expect(form('mockfx')).toHaveAttribute('data-configured', 'false');
        expect(groups(), 'in its place').toEqual([
            {family: 'asset', plugins: ['justetf', 'borsa_italiana']},
            {family: 'fx', plugins: ['mockfx']},
        ]);
        expect(fake.fetchAll, 'the tab reads nothing else again').toHaveBeenCalledTimes(1);
    });
});

// =====================================================================================================================
describe('PluginSettingsTab — the family icons', () => {
    it('PST-07: each family’s title starts with its icon: one per family, inside its h3, before the title, hidden from assistive technology', async () => {
        fake.fetchAll.mockResolvedValueOnce([ECB, JUSTETF, MOCKFX, BORSA]);

        render(PluginSettingsTab);

        await loaded();
        expect(
            groups().map((group) => group.family),
            'premise: both families are shown',
        ).toEqual(['asset', 'fx']);
        for (const family of ['asset', 'fx'] as const) {
            const section = familySection(family);
            const icons = within(section).getAllByTestId('plugin-settings-family-icon');
            expect(icons, `${family}: one icon`).toHaveLength(1);
            const [icon] = icons;
            const title = within(section).getByRole('heading', {level: 3});
            expect(title, `${family}: the icon is in the title`).toContainElement(icon);
            expect(icon, `${family}: a decoration, which assistive technology skips`).toHaveAttribute('aria-hidden', 'true');
            expect(textAround(title, icon), `${family}: the icon first, then the title`).toEqual({before: '', after: FAMILY_TITLE_KEYS[family]});
        }
    });

    it('PST-08: each family draws its own icon: the price sources’ and the exchange-rate sources’ differ', async () => {
        fake.fetchAll.mockResolvedValueOnce([JUSTETF, ECB]);

        render(PluginSettingsTab);

        await loaded();
        const drawing = (family: SettingsFamily) => within(familySection(family)).getByTestId('plugin-settings-family-icon').innerHTML;
        expect(drawing('asset'), 'premise: the icon draws something').not.toBe('');
        expect(drawing('asset')).not.toBe(drawing('fx'));
    });

    it.each<[string, PluginSettingsEntry[], SettingsFamily]>([
        ['only exchange-rate sources: no price-source icon', [MOCKFX, ECB], 'fx'],
        ['only price sources: no exchange-rate icon', [BORSA, JUSTETF], 'asset'],
    ])('PST-09: a family left out has no icon either — %s', async (_label, answer, shown) => {
        fake.fetchAll.mockResolvedValueOnce(answer);

        render(PluginSettingsTab);

        await loaded();
        expect(
            screen.getAllByTestId('plugin-settings-family-icon').map((icon) => icon.closest('[data-testid="plugin-settings-family"]')?.getAttribute('data-family')),
            'every icon on the tab, by the family whose title it starts',
        ).toEqual([shown]);
    });
});
