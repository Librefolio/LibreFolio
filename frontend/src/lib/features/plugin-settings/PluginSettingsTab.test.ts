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
 *   - the import sources (`brim`, W-BS) are a family like the other two, shown after them: one group with its own title
 *     (`FAMILY_TITLE_KEYS.brim`), icon and forms when the answer holds a brim plugin, no group, title or icon when it does not;
 *   - the tools (`tool`, X5-4b) are a family too, the last: after `brim`, with their own title (`FAMILY_TITLE_KEYS.tool`),
 *     icon and forms; no group, title or icon when the answer holds none;
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
import {tick} from 'svelte';

const fake = vi.hoisted(() => ({
    /** `key`, or `key {name=value, …}` when handed values, so that what the tab hands a form (a group's label) is readable. */
    translate(key: string, options?: {values?: Record<string, unknown>}): string {
        const values = options?.values ?? {};
        const shown = Object.keys(values)
            .sort()
            .map((name) => `${name}=${String(values[name])}`);
        return shown.length > 0 ? `${key} {${shown.join(', ')}}` : key;
    },
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
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: readable(fake.translate)};
});
vi.mock('$lib/stores/app/notify.svelte', () => ({notify: fake.notify}));
// The page the tab is open on, held by the test, and the navigation it asks for (S2c: ?family= and ?q=)
const pageStore = await vi.hoisted(async () => {
    const {writable: hoistedWritable} = await import('svelte/store');
    return hoistedWritable({url: new URL('http://librefolio.test/settings/plugins')});
});
const goto = vi.hoisted(() => vi.fn(async () => undefined));
vi.mock('$app/stores', () => ({page: {subscribe: pageStore.subscribe}}));
vi.mock('$app/navigation', () => ({goto}));

import PluginSettingsTab from './PluginSettingsTab.svelte';
import type {PluginSettingsEntry, SettingField, SettingsFamily} from './pluginSettingsApi';
import {FAMILY_TITLE_KEYS, groupFormId} from './pluginSettingsForm';

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
        missing_key: null,
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
    return {family, plugin_code: code, plugin_name: code, icon_url: null, configured: false, fields: [nickname()], groups: [], used_by: [], name_key: null, ...over};
}

const JUSTETF = plugin('asset', 'justetf');
const BORSA = plugin('asset', 'borsa_italiana', {configured: true});
const ECB = plugin('fx', 'ecb', {configured: true});
const MOCKFX = plugin('fx', 'mockfx');
const IMPORTER = plugin('brim', 'broker_x', {configured: true});
const TOOL = plugin('tool', 'fx_converter', {configured: true});

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
    for (const mock of Object.values(fake)) if (typeof mock === 'function' && 'mockReset' in mock) mock.mockReset();
    goto.mockClear();
    pageStore.set({url: new URL('http://librefolio.test/settings/plugins')});
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

// =====================================================================================================================
describe('PluginSettingsTab — the import sources (brim)', () => {
    it('PST-10: a brim plugin gets a group of its own, after the other two, with its form, its title and its icon', async () => {
        fake.fetchAll.mockResolvedValueOnce([IMPORTER, ECB, JUSTETF]);

        render(PluginSettingsTab);

        await loaded();
        expect(groups(), 'the price sources, the exchange-rate sources, then the import sources').toEqual([
            {family: 'asset', plugins: ['justetf']},
            {family: 'fx', plugins: ['ecb']},
            {family: 'brim', plugins: ['broker_x']},
        ]);
        const section = familySection('brim');
        const title = within(section).getByRole('heading', {level: 3});
        const [icon] = within(section).getAllByTestId('plugin-settings-family-icon');
        expect(within(section).getAllByTestId('plugin-settings-family-icon'), 'brim: one icon').toHaveLength(1);
        expect(title, 'the icon is in the title').toContainElement(icon);
        expect(icon).toHaveAttribute('aria-hidden', 'true');
        expect(textAround(title, icon), 'the icon first, then the title of the family').toEqual({before: '', after: FAMILY_TITLE_KEYS.brim});
        expect(FAMILY_TITLE_KEYS.brim).toBe('pluginSettings.families.brim');
    });

    it('PST-11: the import sources draw an icon of their own', async () => {
        fake.fetchAll.mockResolvedValueOnce([JUSTETF, ECB, IMPORTER]);

        render(PluginSettingsTab);

        await loaded();
        const drawing = (family: SettingsFamily) => within(familySection(family)).getByTestId('plugin-settings-family-icon').innerHTML;
        expect(drawing('brim'), 'premise: the icon draws something').not.toBe('');
        expect(drawing('brim')).not.toBe(drawing('asset'));
        expect(drawing('brim')).not.toBe(drawing('fx'));
    });

    it('PST-12: with no brim plugin in the answer there is no brim group, title or icon (the catalogue holds none until a plugin declares a setting)', async () => {
        fake.fetchAll.mockResolvedValueOnce([ECB, JUSTETF, MOCKFX, BORSA]);

        render(PluginSettingsTab);

        await loaded();
        expect(groups().map((group) => group.family)).toEqual(['asset', 'fx']);
        expect(screen.queryAllByTestId('plugin-settings-family').filter((section) => section.getAttribute('data-family') === 'brim')).toEqual([]);
        expect(screen.queryByText('pluginSettings.families.brim')).toBeNull();
        expect(screen.getAllByTestId('plugin-settings-family-icon'), 'one icon for each of the two families shown').toHaveLength(2);
    });

    it('PST-13: an answer with brim plugins only shows the brim group alone', async () => {
        fake.fetchAll.mockResolvedValueOnce([IMPORTER, plugin('brim', 'broker_y')]);

        render(PluginSettingsTab);

        await loaded();
        expect(groups()).toEqual([{family: 'brim', plugins: ['broker_x', 'broker_y']}]);
        expect(screen.queryByTestId('plugin-settings-empty'), 'a brim plugin is an entry like another: the tab is not empty').toBeNull();
    });
});

// =====================================================================================================================
describe('PluginSettingsTab — the tools (tool)', () => {
    it('PST-14: a tool plugin gets a group of its own, after the other three, with its form, its title and its icon', async () => {
        fake.fetchAll.mockResolvedValueOnce([TOOL, IMPORTER, ECB, JUSTETF]);

        render(PluginSettingsTab);

        await loaded();
        expect(groups(), 'the price sources, the exchange-rate sources, the import sources, then the tools').toEqual([
            {family: 'asset', plugins: ['justetf']},
            {family: 'fx', plugins: ['ecb']},
            {family: 'brim', plugins: ['broker_x']},
            {family: 'tool', plugins: ['fx_converter']},
        ]);
        const section = familySection('tool');
        const title = within(section).getByRole('heading', {level: 3});
        const icons = within(section).getAllByTestId('plugin-settings-family-icon');
        expect(icons, 'tool: one icon').toHaveLength(1);
        expect(title, 'the icon is in the title').toContainElement(icons[0]!);
        expect(icons[0]).toHaveAttribute('aria-hidden', 'true');
        expect(textAround(title, icons[0]!), 'the icon first, then the title of the family').toEqual({before: '', after: FAMILY_TITLE_KEYS.tool});
        expect(FAMILY_TITLE_KEYS.tool).toBe('pluginSettings.families.tool');
        expect(within(section).getByTestId('plugin-settings-form-fx_converter'), 'the form of the entry, with the neutral icon: a tool has no icon_url').toHaveAttribute('data-family', 'tool');
        expect(within(section).getByTestId('plugin-settings-plugin-icon-fallback')).toBeInTheDocument();
    });

    it('PST-15: the tools draw an icon of their own, none of the other three’s', async () => {
        fake.fetchAll.mockResolvedValueOnce([JUSTETF, ECB, IMPORTER, TOOL]);

        render(PluginSettingsTab);

        await loaded();
        const drawing = (family: SettingsFamily) => within(familySection(family)).getByTestId('plugin-settings-family-icon').innerHTML;
        expect(drawing('tool'), 'premise: the icon draws something').not.toBe('');
        for (const other of ['asset', 'fx', 'brim'] as const) expect(drawing('tool'), `not the ${other} icon`).not.toBe(drawing(other));
    });

    it('PST-16: with no tool plugin in the answer there is no tool group, title or icon', async () => {
        fake.fetchAll.mockResolvedValueOnce([ECB, JUSTETF, IMPORTER]);

        render(PluginSettingsTab);

        await loaded();
        expect(groups().map((group) => group.family)).toEqual(['asset', 'fx', 'brim']);
        expect(screen.queryAllByTestId('plugin-settings-family').filter((section) => section.getAttribute('data-family') === 'tool')).toEqual([]);
        expect(screen.queryByText('pluginSettings.families.tool')).toBeNull();
        expect(screen.getAllByTestId('plugin-settings-family-icon'), 'one icon for each of the three families shown').toHaveLength(3);
    });

    it('PST-17: an answer with tool plugins only shows the tool group alone, the tab not empty', async () => {
        fake.fetchAll.mockResolvedValueOnce([TOOL, plugin('tool', 'compound_growth')]);

        render(PluginSettingsTab);

        await loaded();
        expect(groups()).toEqual([{family: 'tool', plugins: ['fx_converter', 'compound_growth']}]);
        expect(screen.queryByTestId('plugin-settings-empty')).toBeNull();
    });

    it('PST-18: a save in a tool’s form is written with the family tool, and the tab shows the fresh state in place of the old one', async () => {
        const fresh: PluginSettingsEntry = {...TOOL, fields: [{...nickname(), value: 'someone', is_set: true, source: 'db'}]};
        fake.fetchAll.mockResolvedValueOnce([ECB, TOOL]);
        fake.save.mockResolvedValueOnce({kind: 'saved'});
        fake.fetchEntry.mockResolvedValueOnce(fresh);

        render(PluginSettingsTab);

        await loaded();
        const toolForm = form('fx_converter');
        await fireEvent.input(within(toolForm).getByTestId('plugin-setting-input'), {target: {value: 'someone'}});
        await fireEvent.click(within(toolForm).getByTestId('plugin-settings-save'));

        await waitFor(() => expect(fake.fetchEntry).toHaveBeenCalledWith('tool', 'fx_converter'));
        expect(fake.save.mock.calls).toStrictEqual([[[{family: 'tool', plugin_code: 'fx_converter', field_key: 'nickname', scope: 'user', value: 'someone'}]]]);
        expect(groups(), 'the other plugins untouched, the tool still in its group').toEqual([
            {family: 'fx', plugins: ['ecb']},
            {family: 'tool', plugins: ['fx_converter']},
        ]);
    });
});

// =====================================================================================================================
// Shared settings groups (project 76, lot G3, contract D): the groups are a section of their own, after the other
// families; a plugin's «open group» button brings the group's form into view and moves the focus to its heading.
describe('PluginSettingsTab — shared settings groups (G3)', () => {
    /** A group entry as the API lists it: system fields only, its users named. */
    function sharedGroup(name: string, label: string, over: Partial<PluginSettingsEntry> = {}): PluginSettingsEntry {
        return plugin('group', name, {plugin_name: label, fields: [{...nickname(), key: 'account_token', scope: 'system'}], used_by: [{family: 'asset', plugin_code: 'justetf', plugin_name: 'justETF'}], groups: [], name_key: null, ...over} as Partial<PluginSettingsEntry>);
    }
    const ALPHA = sharedGroup('alpha', 'Alpha keys');
    const BETA = sharedGroup('beta', 'Beta keys');
    const reader = (...names: string[]) => plugin('asset', 'justetf', {groups: names} as Partial<PluginSettingsEntry>);

    const scrolled = vi.fn();
    beforeEach(() => {
        scrolled.mockReset();
        Element.prototype.scrollIntoView = scrolled;
    });
    afterEach(() => {
        delete (Element.prototype as {scrollIntoView?: unknown}).scrollIntoView;
    });

    /** The group's form, and the element the tab anchors it at. */
    const anchor = (name: string) => document.getElementById(groupFormId(name));
    /** A menu entry. 81 U37: «All» lists the plugins only, so a shared group is read under «Shared». */
    const category = (key: string) => screen.getByTestId(`plugin-settings-category-${key}`);

    it('PST-19: the groups are not in «All»: they stand alone under «Shared» (81 U37), family group, titled by its key, one form per group in the answer’s order, whatever the order of the answer', async () => {
        fake.fetchAll.mockResolvedValueOnce([BETA, TOOL, ALPHA, JUSTETF, ECB]);

        render(PluginSettingsTab);

        await loaded();
        expect(groups(), '«All» lists the plugins, each in its family, and no shared group (81 U37)').toEqual([
            {family: 'asset', plugins: ['justetf']},
            {family: 'fx', plugins: ['ecb']},
            {family: 'tool', plugins: ['fx_converter']},
        ]);
        await fireEvent.click(category('group'));
        expect(groups(), 'under «Shared» the groups stand alone, one form per group in the answer’s order').toEqual([{family: 'group', plugins: ['beta', 'alpha']}]);
        expect(familySection('group').querySelector('h3'), 'its title is the family’s key').toHaveTextContent(FAMILY_TITLE_KEYS.group);
        expect(form('alpha')).toHaveAttribute('data-family', 'group');
        expect(within(familySection('group')).getAllByTestId('plugin-settings-family-icon')).toHaveLength(1);
    });

    it('PST-20: with no group in the answer there is no group section, title or icon; with groups only, the section stands alone', async () => {
        fake.fetchAll.mockResolvedValueOnce([JUSTETF]);
        const {unmount} = render(PluginSettingsTab);
        await loaded();
        expect(screen.queryAllByTestId('plugin-settings-family').map((section) => section.getAttribute('data-family'))).toEqual(['asset']);
        expect(screen.queryByText(FAMILY_TITLE_KEYS.group)).toBeNull();
        unmount();

        fake.fetchAll.mockResolvedValueOnce([ALPHA]);
        render(PluginSettingsTab);
        await loaded();
        expect(groups(), '«All» is the plugins: with groups only it lists nothing (81 U37)').toEqual([]);
        await fireEvent.click(category('group'));
        expect(groups()).toEqual([{family: 'group', plugins: ['alpha']}]);
        expect(screen.queryByTestId('plugin-settings-empty')).toBeNull();
    });

    it('PST-21: each group’s form is reachable at the element id plugin-settings-group-<name>, which holds that form and no other', async () => {
        fake.fetchAll.mockResolvedValueOnce([ALPHA, BETA, JUSTETF]);

        render(PluginSettingsTab);

        await loaded();
        await fireEvent.click(category('group'));
        for (const [name, other] of [
            ['alpha', 'beta'],
            ['beta', 'alpha'],
        ] as const) {
            const target = anchor(name);
            expect(target, `an element with the id of ${name}`).not.toBeNull();
            expect(target!.contains(form(name)), `${name}: the anchor holds its form`).toBe(true);
            expect(target!.contains(form(other)), `${name}: and not ${other}’s`).toBe(false);
        }
        expect(anchor('justetf'), 'only groups are anchored').toBeNull();
    });

    it('PST-22: a plugin’s form gets the labels of the groups the tab lists: its «in group» row names the group by the group’s own name', async () => {
        fake.fetchAll.mockResolvedValueOnce([reader('alpha', 'beta'), ALPHA, BETA]);

        render(PluginSettingsTab);

        await loaded();
        const rows = within(form('justetf')).getAllByTestId('plugin-settings-in-group');
        expect(rows.map((row) => row.getAttribute('data-group'))).toEqual(['alpha', 'beta']);
        expect(rows[0].textContent).toContain('group=Alpha keys');
        expect(rows[1].textContent).toContain('group=Beta keys');
    });

    it('PST-23: «open» on a group’s row brings that group’s form into view and moves the focus to its heading — the other group untouched', async () => {
        fake.fetchAll.mockResolvedValueOnce([reader('alpha', 'beta'), ALPHA, BETA]);
        render(PluginSettingsTab);
        await loaded();

        const row = within(form('justetf'))
            .getAllByTestId('plugin-settings-in-group')
            .find((element) => element.getAttribute('data-group') === 'beta')!;
        await fireEvent.click(within(row).getByTestId('plugin-settings-open-group'));

        await waitFor(() => expect(scrolled).toHaveBeenCalled());
        const target = anchor('beta')!;
        expect(
            (scrolled.mock.contexts as Element[]).every((element) => target.contains(element)),
            'only beta’s form is scrolled to',
        ).toBe(true);
        const heading = within(form('beta')).getByRole('heading', {level: 4});
        await waitFor(() => expect(document.activeElement).toBe(heading));
    });

    it('PST-24: a group the tab does not list gets no «open» button: the row says the group, the button is not there', async () => {
        fake.fetchAll.mockResolvedValueOnce([reader('alpha', 'hidden'), ALPHA]);

        render(PluginSettingsTab);

        await loaded();
        const rows = within(form('justetf')).getAllByTestId('plugin-settings-in-group');
        expect(rows.map((row) => row.getAttribute('data-group'))).toEqual(['alpha', 'hidden']);
        const opens = rows.map((row) => within(row).queryAllByTestId('plugin-settings-open-group').length);
        expect(opens, 'alpha: one button; hidden: none').toEqual([1, 0]);
    });

    it('PST-27: a reader of a group that owns a call count (a call_usage of its own) says its calls count there, with «open»; a reader of a group without one does not (project 76, U5)', async () => {
        const usage = {family: 'group', plugin_code: 'alpha', windows: [{window: 'day' as const, count: 3, limit: null, resets_at: '2026-11-19T00:00:00Z', full: false}]};
        fake.fetchAll.mockResolvedValueOnce([reader('alpha', 'beta'), sharedGroup('alpha', 'Alpha keys', {call_usage: usage}), BETA]);

        render(PluginSettingsTab);

        await loaded();
        const rows = within(form('justetf')).getAllByTestId('plugin-settings-calls-on-group');
        expect(
            rows.map((row) => row.getAttribute('data-group')),
            'alpha owns a count, beta does not',
        ).toEqual(['alpha']);
        expect(rows[0].textContent).toContain('pluginSettings.group.countsOn {group=Alpha keys}');
        await fireEvent.click(within(rows[0]).getByTestId('plugin-settings-calls-open-group'));
        await waitFor(() => expect(scrolled).toHaveBeenCalled());
        expect((scrolled.mock.contexts as Element[]).every((element) => anchor('alpha')!.contains(element))).toBe(true);
    });

    it('PST-26: a save in a group’s form reads again the plugins that read it: a reader unconfigured for want of the group’s key turns configured, without reloading the page', async () => {
        const waiting = {...reader('alpha'), configured: false};
        const freshGroup: PluginSettingsEntry = {...ALPHA, configured: true, fields: [{...nickname(), key: 'account_token', scope: 'system', value: 'someone', is_set: true, source: 'db'}]};
        fake.fetchAll.mockResolvedValueOnce([waiting, ALPHA]);
        fake.save.mockResolvedValueOnce({kind: 'saved'});
        fake.fetchEntry.mockImplementation(async (family: string, code: string) => (family === 'group' ? freshGroup : code === 'justetf' ? {...waiting, configured: true} : null));
        render(PluginSettingsTab);
        await loaded();
        expect(form('justetf'), 'barrier: the reader waits for the group').toHaveAttribute('data-configured', 'false');

        // The group's form is under «Shared» (81 U37); the reader's, under «All»: the reader is read again without a reload.
        await fireEvent.click(category('group'));
        await fireEvent.input(within(form('alpha')).getByTestId('plugin-setting-input'), {target: {value: 'someone'}});
        await fireEvent.click(within(form('alpha')).getByTestId('plugin-settings-save'));

        await waitFor(() => expect(fake.fetchEntry).toHaveBeenCalledWith('asset', 'justetf'));
        await fireEvent.click(category('all'));
        await waitFor(() => expect(form('justetf')).toHaveAttribute('data-configured', 'true'));
        expect(fake.fetchAll, 'no reload of the whole catalogue').toHaveBeenCalledTimes(1);
        fake.fetchEntry.mockReset();
    });

    it('PST-25: a save in a group’s form is written with the family group, and the tab shows the fresh state in place of the old one', async () => {
        const fresh: PluginSettingsEntry = {...ALPHA, configured: true, fields: [{...nickname(), key: 'account_token', scope: 'system', value: 'someone', is_set: true, source: 'db'}]};
        fake.fetchAll.mockResolvedValueOnce([JUSTETF, ALPHA]);
        fake.save.mockResolvedValueOnce({kind: 'saved'});
        fake.fetchEntry.mockResolvedValueOnce(fresh);
        render(PluginSettingsTab);
        await loaded();

        await fireEvent.click(category('group'));
        const alpha = form('alpha');
        await fireEvent.input(within(alpha).getByTestId('plugin-setting-input'), {target: {value: 'someone'}});
        await fireEvent.click(within(alpha).getByTestId('plugin-settings-save'));

        await waitFor(() => expect(fake.fetchEntry).toHaveBeenCalledWith('group', 'alpha'));
        expect(fake.save.mock.calls).toStrictEqual([[[{family: 'group', plugin_code: 'alpha', field_key: 'account_token', scope: 'system', value: 'someone'}]]]);
        await waitFor(() => expect(form('alpha')).toHaveAttribute('data-configured', 'true'));
        expect(groups()).toEqual([{family: 'group', plugins: ['alpha']}]);
        await fireEvent.click(category('all'));
        expect(groups(), 'the plugin untouched').toEqual([{family: 'asset', plugins: ['justetf']}]);
    });
});

// =====================================================================================================================
// The menu (project 76, S1b; mock S0 approved by the developer on 19/11): «All», «To configure» and the families, with
// counts and a dot, in the sidebar and in the phone dropdown (the shared SettingsCategoryNav, prefix plugin-settings).
describe('PluginSettingsTab — the menu (76 S1b)', () => {
    const SHARED = plugin('group', 'coingecko', {plugin_name: 'CoinGecko', fields: [{...nickname(), key: 'api_key', scope: 'system'}], used_by: [{family: 'asset', plugin_code: 'justetf', plugin_name: 'justETF'}]} as Partial<PluginSettingsEntry>);
    const READER = plugin('asset', 'justetf', {groups: ['coingecko']} as Partial<PluginSettingsEntry>);
    const ANSWER = () => [READER, BORSA, ECB, MOCKFX, SHARED];
    const sidebarItem = (key: string) => screen.getByTestId(`plugin-settings-category-${key}`);

    const scrolled = vi.fn();
    beforeEach(() => {
        scrolled.mockReset();
        Element.prototype.scrollIntoView = scrolled;
    });
    afterEach(() => {
        delete (Element.prototype as {scrollIntoView?: unknown}).scrollIntoView;
    });

    it('PST-28: lists «All» (the plugins, not the groups), «To configure» and each family present, with their counts and a dot where something is to configure; «All» selected', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        const nav = within(tab()).getByRole('navigation');
        expect(
            within(nav)
                .getAllByRole('button')
                .map((button) => [button.getAttribute('data-testid'), button.getAttribute('data-count'), button.getAttribute('aria-pressed')]),
        ).toEqual([
            ['plugin-settings-category-all', '4', 'true'],
            ['plugin-settings-category-unconfigured', '3', 'false'],
            ['plugin-settings-category-asset', '2', 'false'],
            ['plugin-settings-category-fx', '2', 'false'],
            ['plugin-settings-category-group', '1', 'false'],
        ]);
        expect(within(sidebarItem('asset')).getByTestId('plugin-settings-category-dot')).toBeInTheDocument();
        expect(within(sidebarItem('all')).queryByTestId('plugin-settings-category-dot')).toBeNull();
        expect(sidebarItem('asset')).toHaveTextContent('pluginSettings.menu.asset');
        expect(groups(), '«All»: every plugin once, in its family; the shared group is under «Shared» (81 U37)').toEqual([
            {family: 'asset', plugins: ['justetf', 'borsa_italiana']},
            {family: 'fx', plugins: ['ecb', 'mockfx']},
        ]);
    });

    it('PST-29: a family shows its section alone; «All» brings every plugin’s section back (not the shared groups)', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        await fireEvent.click(sidebarItem('fx'));
        expect(groups()).toEqual([{family: 'fx', plugins: ['ecb', 'mockfx']}]);
        expect(sidebarItem('fx')).toHaveAttribute('aria-pressed', 'true');

        await fireEvent.click(sidebarItem('all'));
        expect(groups().map((group) => group.family)).toEqual(['asset', 'fx']);
    });

    it('PST-30: «To configure» shows the entries not configured, under their families', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        await fireEvent.click(sidebarItem('unconfigured'));
        expect(groups()).toEqual([
            {family: 'asset', plugins: ['justetf']},
            {family: 'fx', plugins: ['mockfx']},
            {family: 'group', plugins: ['coingecko']},
        ]);
    });

    it('PST-31: «open» on a group while a family hides it shows the group first, then brings its form into view', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();
        await fireEvent.click(sidebarItem('asset'));
        expect(document.getElementById(groupFormId('coingecko')), 'premise: the filter hides the group').toBeNull();

        await fireEvent.click(within(form('justetf')).getByTestId('plugin-settings-open-group'));

        await waitFor(() => expect(scrolled).toHaveBeenCalled());
        expect(sidebarItem('group')).toHaveAttribute('aria-pressed', 'true');
        expect(document.getElementById(groupFormId('coingecko'))).not.toBeNull();
        await waitFor(() => expect(document.activeElement).toBe(within(form('coingecko')).getByRole('heading', {level: 4})));
    });

    it('U37-1: «All» lists each plugin once, in its family, and not the shared group the plugins read: the group is under «Shared» and reached from the reader’s row', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        expect(
            screen.queryAllByTestId('plugin-settings-family').map((section) => section.getAttribute('data-family')),
            'no «Shared» section in «All»',
        ).not.toContain('group');
        expect(document.getElementById(groupFormId('coingecko')), 'the group’s form is not in «All»').toBeNull();
        // The plugin that reads it still says so, and takes the reader there.
        expect(within(form('justetf')).getByTestId('plugin-settings-in-group')).toHaveAttribute('data-group', 'coingecko');
        await fireEvent.click(within(form('justetf')).getByTestId('plugin-settings-open-group'));
        await waitFor(() => expect(sidebarItem('group')).toHaveAttribute('aria-pressed', 'true'));
        expect(document.getElementById(groupFormId('coingecko'))).not.toBeNull();
    });

    it('U37-2: a search that finds only a shared group offers «Shared»; taking it shows the group and keeps the search', async () => {
        const onlyGroup = plugin('group', 'alpha', {plugin_name: 'Zebrakey settings', fields: [{...nickname(), key: 'account_token', scope: 'system'}], used_by: [], groups: [], name_key: null} as Partial<PluginSettingsEntry>);
        fake.fetchAll.mockResolvedValueOnce([READER, ECB, onlyGroup]);
        render(PluginSettingsTab);
        await loaded();

        await fireEvent.input(screen.getByTestId('plugin-settings-search'), {target: {value: 'zebrakey'}});

        expect(screen.getByTestId('plugin-settings-no-matches'), '«All» has no card for it').toBeInTheDocument();
        const shared = screen.getByTestId('plugin-settings-search-shared');
        await fireEvent.click(shared);
        await waitFor(() => expect(sidebarItem('group')).toHaveAttribute('aria-pressed', 'true'));
        expect(groups()).toEqual([{family: 'group', plugins: ['alpha']}]);
        expect(screen.getByTestId('plugin-settings-search')).toHaveValue('zebrakey');
    });

    it('U37-3: a search that finds plugins as well as a group lists the plugins and offers no «Shared» link', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        await fireEvent.input(screen.getByTestId('plugin-settings-search'), {target: {value: 'justetf'}});

        expect(groups().flatMap((group) => group.plugins)).toContain('justetf');
        expect(screen.queryByTestId('plugin-settings-search-shared')).toBeNull();
    });

    it('PST-32: «To configure» stays chosen when its last entry is configured, with 0 and a line that says so', async () => {
        const onlyOne = plugin('fx', 'mockfx');
        fake.fetchAll.mockResolvedValueOnce([BORSA, onlyOne]);
        fake.save.mockResolvedValueOnce({kind: 'saved'});
        fake.fetchEntry.mockResolvedValueOnce(plugin('fx', 'mockfx', {configured: true, fields: [{...nickname(), value: 'someone', is_set: true, source: 'db'}]}));
        render(PluginSettingsTab);
        await loaded();
        await fireEvent.click(sidebarItem('unconfigured'));

        await fireEvent.input(within(form('mockfx')).getByTestId('plugin-setting-input'), {target: {value: 'someone'}});
        await fireEvent.click(within(form('mockfx')).getByTestId('plugin-settings-save'));

        await waitFor(() => expect(sidebarItem('unconfigured')).toHaveAttribute('data-count', '0'));
        expect(sidebarItem('unconfigured')).toHaveAttribute('aria-pressed', 'true');
        expect(groups()).toEqual([]);
        expect(screen.getByTestId('plugin-settings-nothing-unconfigured')).toHaveTextContent('pluginSettings.menu.nothingUnconfigured');
    });

    it('PST-33: the phone dropdown offers the same entries, and a choice filters the page', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        await fireEvent.click(screen.getByTestId('plugin-settings-mobile-category-trigger'));
        const menu = screen.getByTestId('plugin-settings-mobile-category-menu');
        expect(
            within(menu)
                .getAllByRole('button')
                .map((button) => button.getAttribute('data-testid')),
        ).toEqual(['plugin-settings-mobile-category-all', 'plugin-settings-mobile-category-unconfigured', 'plugin-settings-mobile-category-asset', 'plugin-settings-mobile-category-fx', 'plugin-settings-mobile-category-group']);
        await fireEvent.click(screen.getByTestId('plugin-settings-mobile-category-group'));
        expect(groups()).toEqual([{family: 'group', plugins: ['coingecko']}]);
        expect(screen.getByTestId('plugin-settings-mobile-category-trigger')).toHaveTextContent('pluginSettings.menu.group');
    });
});

// =====================================================================================================================
// The search (project 76, S2b; the developer's rules of 19/11): exact words, all in the same card, names of the fields
// and descriptions, never the numbers; the menu's counts follow it, its entries stay (with 0).
describe('PluginSettingsTab — the search (76 S2b)', () => {
    const SNB = plugin('fx', 'snb', {plugin_name: 'Swiss National Bank', configured: true, description: 'Swiss National Bank — monthly averages.'} as Partial<PluginSettingsEntry>);
    const ANSWER = () => [JUSTETF, BORSA, ECB, SNB];
    const search = () => screen.getByTestId('plugin-settings-search');
    const sidebarItem = (key: string) => screen.getByTestId(`plugin-settings-category-${key}`);
    const type = async (text: string) => fireEvent.input(search(), {target: {value: text}});

    it('PST-34: shows the cards whose texts hold every word; the counts follow, the entries stay with 0', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        await type('swiss monthly');
        expect(groups()).toEqual([{family: 'fx', plugins: ['snb']}]);
        expect(['all', 'asset', 'fx'].map((key) => sidebarItem(key).getAttribute('data-count'))).toEqual(['1', '0', '1']);

        await type('');
        expect(groups().map((group) => group.plugins.length)).toEqual([2, 2]);
        expect(sidebarItem('all')).toHaveAttribute('data-count', '4');
    });

    it('PST-35: nothing matches anywhere: the empty state names the search, no section is drawn', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        await type('kraken');
        expect(groups()).toEqual([]);
        expect(screen.getByTestId('plugin-settings-no-matches')).toHaveTextContent('pluginSettings.search.noMatchAll {query=kraken}');
        expect(screen.queryByTestId('plugin-settings-search-all')).toBeNull();
    });

    it('PST-36: within a family with matches elsewhere, a link searches every family', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();
        await fireEvent.click(sidebarItem('asset'));

        await type('swiss');
        expect(groups()).toEqual([]);
        expect(screen.getByTestId('plugin-settings-no-matches')).toHaveTextContent('pluginSettings.search.noMatchFamily {family=pluginSettings.menu.asset, query=swiss}');
        await fireEvent.click(screen.getByTestId('plugin-settings-search-all'));
        expect(sidebarItem('all')).toHaveAttribute('aria-pressed', 'true');
        expect(groups()).toEqual([{family: 'fx', plugins: ['snb']}]);
        expect(search(), 'the search stays').toHaveValue('swiss');
    });

    it('PST-37: the search box is labelled and keeps its text across a choice of the menu', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        expect(search()).toHaveAttribute('placeholder', 'pluginSettings.search.placeholder');
        expect(search()).toHaveAttribute('aria-label', 'pluginSettings.search.placeholder');
        await type('bank');
        await fireEvent.click(sidebarItem('fx'));
        expect(search()).toHaveValue('bank');
        expect(groups()).toEqual([{family: 'fx', plugins: ['snb']}]);
    });
});

// =====================================================================================================================
// The address (project 76, S2c): the menu's choice and the search are read from ?family= and ?q=, and written there —
// a choice as a new step of the history, the search in place while typing.
describe('PluginSettingsTab — the address (76 S2c)', () => {
    const SNB = plugin('fx', 'snb', {plugin_name: 'Swiss National Bank', configured: true, description: 'Swiss National Bank.'} as Partial<PluginSettingsEntry>);
    const ANSWER = () => [JUSTETF, BORSA, ECB, SNB];
    const search = () => screen.getByTestId('plugin-settings-search');
    const sidebarItem = (key: string) => screen.getByTestId(`plugin-settings-category-${key}`);
    const at = (query: string) => pageStore.set({url: new URL(`http://librefolio.test/settings/plugins${query}`)});

    it('PST-38: opens on the family and the search the address names', async () => {
        at('?family=fx&q=swiss');
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        expect(sidebarItem('fx')).toHaveAttribute('aria-pressed', 'true');
        expect(search()).toHaveValue('swiss');
        expect(groups()).toEqual([{family: 'fx', plugins: ['snb']}]);
        expect(goto, 'reading the address writes nothing').not.toHaveBeenCalled();
    });

    it('PST-39: a choice of the menu is a new step of the history; typing replaces the address in place', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        await fireEvent.click(sidebarItem('asset'));
        expect(goto).toHaveBeenLastCalledWith('/settings/plugins?family=asset', expect.objectContaining({replaceState: false, noScroll: true, keepFocus: true}));
        await fireEvent.input(search(), {target: {value: 'borsa'}});
        expect(goto).toHaveBeenLastCalledWith('/settings/plugins?family=asset&q=borsa', expect.objectContaining({replaceState: true, noScroll: true, keepFocus: true}));
    });

    it('PST-40: Back or Forward (the address changes under the page) brings the choice and the search with it', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        at('?family=fx');
        await waitFor(() => expect(sidebarItem('fx')).toHaveAttribute('aria-pressed', 'true'));
        at('?q=borsa');
        await waitFor(() => expect(sidebarItem('all')).toHaveAttribute('aria-pressed', 'true'));
        expect(search()).toHaveValue('borsa');
        expect(groups()).toEqual([{family: 'asset', plugins: ['borsa_italiana']}]);
    });

    it('PST-42: typing fast, the address of an earlier keystroke arriving late does not take back what was typed since', async () => {
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();

        await fireEvent.input(search(), {target: {value: 'bo'}});
        await fireEvent.input(search(), {target: {value: 'bor'}});
        // The navigation of «bo» lands now: it is the page's own echo, not a new address
        at('?q=bo');
        await tick();
        expect(search()).toHaveValue('bor');
        at('?q=bor');
        await tick();
        expect(search()).toHaveValue('bor');
        // A real change of address afterwards is read as before
        at('?q=ecb');
        await waitFor(() => expect(search()).toHaveValue('ecb'));
    });

    it('PST-41: a family the menu does not know opens «All»', async () => {
        at('?family=crypto');
        fake.fetchAll.mockResolvedValueOnce(ANSWER());
        render(PluginSettingsTab);
        await loaded();
        expect(sidebarItem('all')).toHaveAttribute('aria-pressed', 'true');
    });
});
