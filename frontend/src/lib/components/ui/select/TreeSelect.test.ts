// @vitest-environment jsdom
/**
 * TreeSelect — what the generic two-level select does that the signals picker never did (T3).
 *
 * The mechanics that moved verbatim out of `charts/SignalTreeSelect.svelte` by decision D-K1
 * (search across both levels, the keyboard model, outside click, flat mode, the clear button) are
 * pinned by `charts/SignalTreeSelect.test.ts`, which now runs through the thin adapter over this
 * component. This file covers only the four axes that became props, and nothing the other file
 * already says:
 *
 *   - `inline` groups: items at the root, no group row, always on screen, walked by the keyboard;
 *   - `showSelected` + `selectedItem`: a form field shows its value, an action picker never does;
 *   - `defaultExpanded`: 'first' (skipping inline groups), 'selected', 'none';
 *   - `testIdPrefix`, the `item` / `groupLabel` snippets, `searchPlaceholder`, `noMatchesText`.
 *
 * Plus one axis that is no prop: **no deferred work survives destroy** (K step 16, round 1). Opening, a
 * printable key on the closed trigger, typing, the clear button and the keyboard each defer a step with
 * `setTimeout(0)`; a picker unmounted with one still pending must cancel it, or the callback runs once
 * jsdom is gone — `document is not defined`, an unhandled error under a green suite. The scroll to the
 * active row must find it inside the dropdown, never through the global `document`. That block runs on
 * fake timers, as `ui/feedback/Tooltip.test.ts` does.
 *
 * ## Snippets come from `createRawSnippet`, not from a harness component
 *
 * One file, as in `ui/display/RiskMetricCard.test.ts`. A raw snippet renders once and does not
 * follow later changes of its argument — the reason `SyncModalBase.test.ts` needs a harness — but
 * here that never matters: a row is keyed on its value and keeps the same item for as long as it
 * is mounted, and the trigger's content is asserted only right after its branch has (re)mounted,
 * at mount or once a selection has closed the dropdown. A value that changes under a closed trigger
 * is pinned in `AssetTypeSelect.test.ts`, with the compiled snippets of production.
 *
 * ## The bound value is reactive
 *
 * `value` is bound through an accessor pair, which is what a parent's `bind:value` compiles to. A
 * real parent keeps the value in `$state`; a plain object behind the accessors would not be
 * tracked, and a form field that shows its value would keep showing the old one — a harness
 * artefact that looks like a product bug. `reactiveBox` gives the accessors a `$state` to read
 * (`DateRangePicker.test.ts` solves the same problem with `createSubscriber`).
 *
 * Never a CSS class, never a translated string: placeholder, search placeholder, empty-state text
 * and every label are strings this file owns. Opening defers "first entry active, then focus the
 * search box" with `setTimeout(0)`; focus is the observable end of that step, so every test waits
 * for it — on the fake clock of the last block, by draining the clock — before reading the highlight
 * or touching the keyboard.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {createRawSnippet, type Snippet} from 'svelte';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {reactiveBox} from '$test/runes.svelte';
import TreeSelect from './TreeSelect.svelte';
import type {TreeSelectGroup, TreeSelectItem} from './treeSelect';

const TEST_ID = 'probe-picker';
const PREFIX = 'probe-tree';
const PLACEHOLDER = 'Pick a probe';
const SEARCH_PLACEHOLDER = 'Find a probe';
const NO_MATCHES = 'Nothing probes like that';

/**
 * The shape `buildAssetTypeTree()` produces for asset types: root runs around families.
 *
 *     run-1 (inline)   a1 a2
 *     alpha            b1 b2
 *     run-2 (inline)   c1
 *     beta             d1 d2
 *
 * Load-bearing details (change them and the tests below stop meaning anything):
 * - the first group is inline, so 'first' has to skip it to reach alpha;
 * - the inline groups carry a label and a subtitle, which must never reach the screen;
 * - 'shared' matches a2 (inline) and d2 (in beta, collapsed at open), nothing else;
 * - no label or subtitle holds a digit, so a group row's text minus its label is its count.
 */
const GROUPS: TreeSelectGroup[] = [
    {
        key: 'run-1',
        label: 'Run one',
        subtitle: 'First inline run',
        inline: true,
        items: [
            {value: 'a1', searchText: 'a1 apple'},
            {value: 'a2', searchText: 'a2 apricot shared'},
        ],
    },
    {
        key: 'alpha',
        label: 'Alpha family',
        subtitle: 'Alpha subtitle',
        icon: '/probe/alpha.png',
        items: [
            {value: 'b1', searchText: 'b1 banana'},
            {value: 'b2', searchText: 'b2 blueberry'},
        ],
    },
    {key: 'run-2', label: 'Run two', subtitle: 'Second inline run', inline: true, items: [{value: 'c1', searchText: 'c1 cherry'}]},
    {
        key: 'beta',
        label: 'Beta family',
        subtitle: 'Beta subtitle',
        icon: '/probe/beta.png',
        items: [
            {value: 'd1', searchText: 'd1 date'},
            {value: 'd2', searchText: 'd2 durian shared'},
        ],
    },
];

/** Row content, tagged so a test tells the snippet's output from the component's own markup. */
const itemSnippet = createRawSnippet<[TreeSelectItem]>((item) => ({
    render: () => `<span data-testid="probe-item" data-value="${item().value}">item ${item().value}</span>`,
}));

/** Group row content: the group's key, its icon and its label, all handed in by the component. */
const groupLabelSnippet = createRawSnippet<[TreeSelectGroup]>((group) => ({
    render: () => `<span data-testid="probe-group-label" data-key="${group().key}"><img src="${group().icon ?? ''}" alt="" />${group().label}</span>`,
}));

/** Trigger content for the selected item. */
const selectedSnippet = createRawSnippet<[TreeSelectItem]>((item) => ({
    render: () => `<span data-testid="probe-selected" data-value="${item().value}">chosen ${item().value}</span>`,
}));

interface MountOptions {
    value?: string;
    groups?: TreeSelectGroup[];
    showSelected?: boolean;
    selectedItem?: Snippet<[TreeSelectItem]>;
    groupLabel?: Snippet<[TreeSelectGroup]>;
    defaultExpanded?: 'first' | 'selected' | 'none';
    /** Passing `undefined` explicitly exercises the component's own default. */
    testIdPrefix?: string;
    searchPlaceholder?: string;
    noMatchesText?: string;
}

function mount({value = '', ...props}: MountOptions = {}) {
    const onchange = vi.fn();
    // The parent's `$state` behind `bind:value`: the component writes it through the setter below.
    const bound = reactiveBox({value});
    const {unmount} = render(TreeSelect, {
        groups: GROUPS,
        placeholder: PLACEHOLDER,
        testId: TEST_ID,
        testIdPrefix: PREFIX,
        item: itemSnippet,
        ...props,
        onchange,
        get value() {
            return bound.value;
        },
        set value(next: string) {
            bound.value = next;
        },
    });
    return {onchange, bound, unmount, trigger: screen.getByTestId(`${TEST_ID}-button`)};
}

/** The component's own root: rows are looked up inside it. */
function root(): HTMLElement {
    return screen.getByTestId(TEST_ID);
}

function group(key: string): HTMLElement {
    return within(root()).getByTestId(`${PREFIX}-group-${key}`);
}

function queryGroup(key: string): HTMLElement | null {
    return within(root()).queryByTestId(`${PREFIX}-group-${key}`);
}

function option(value: string): HTMLElement {
    return within(root()).getByTestId(`${PREFIX}-option-${value}`);
}

function queryOption(value: string): HTMLElement | null {
    return within(root()).queryByTestId(`${PREFIX}-option-${value}`);
}

/** A row by the tail of its test id: `option-a1`, `group-alpha`. */
function row(id: string): HTMLElement {
    return within(root()).getByTestId(`${PREFIX}-${id}`);
}

/** Every rendered row, group rows included, as test-id tails in screen order. */
function rowOrder(): string[] {
    return within(root())
        .queryAllByTestId(new RegExp(`^${PREFIX}-(option|group)-`))
        .map((element) => (element.getAttribute('data-testid') ?? '').slice(PREFIX.length + 1));
}

/** The search box held by the open trigger. */
function searchBox(trigger: HTMLElement): HTMLInputElement {
    const input = trigger.querySelector('input');
    if (!input) throw new Error('the trigger holds no search box: the dropdown is not open');
    return input;
}

/** Opens with a click, then waits for the deferred step to end: focus lands right after "first entry active". */
async function openByClick(trigger: HTMLElement): Promise<HTMLInputElement> {
    await fireEvent.click(trigger);
    const input = searchBox(trigger);
    await waitFor(() => expect(input).toHaveFocus());
    return input;
}

/** The highlight, read as assistive tech reads it: both combobox ends point at the row, the only one `aria-selected`. */
function expectActive(trigger: HTMLElement, element: HTMLElement) {
    expect(element.id).not.toBe('');
    expect(trigger).toHaveAttribute('aria-activedescendant', element.id);
    expect(searchBox(trigger)).toHaveAttribute('aria-activedescendant', element.id);
    const highlighted = root().querySelectorAll('[aria-selected="true"]');
    expect(highlighted).toHaveLength(1);
    expect(highlighted[0]).toBe(element);
}

describe('TreeSelect — beyond the signals picker', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    describe('inline groups', () => {
        it('put their items at the root of the tree: no group row, no label, nothing to open', async () => {
            const {trigger} = mount();
            await openByClick(trigger);

            const tree = within(root()).getByRole('tree');
            expect(queryGroup('run-1')).toBeNull();
            expect(queryGroup('run-2')).toBeNull();
            // An inline group's label and subtitle are the caller's bookkeeping, never the user's.
            for (const text of ['Run one', 'First inline run', 'Run two', 'Second inline run']) {
                expect(tree).not.toHaveTextContent(text);
            }
            // Root-level treeitems: no `role="group"` between them and the tree.
            for (const value of ['a1', 'a2', 'c1']) {
                expect(option(value)).toBeVisible();
                expect(option(value)).toHaveAttribute('role', 'treeitem');
                expect(option(value).closest('[role="group"]'), `${value} sits in an inline group and must be a root-level treeitem`).toBeNull();
            }
            // A family's items, by contrast, live in the group its row opens.
            expect(option('b1').closest('[role="group"]')).not.toBeNull();
            // Groups keep the order they were given, whether inline or not.
            expect(rowOrder()).toEqual(['option-a1', 'option-a2', 'group-alpha', 'option-b1', 'option-b2', 'option-c1', 'group-beta']);
        });

        it('stay on screen while the families around them open and close', async () => {
            const {trigger} = mount();
            await openByClick(trigger);

            await fireEvent.click(group('alpha'));
            await fireEvent.click(group('beta'));
            expect(rowOrder()).toEqual(['option-a1', 'option-a2', 'group-alpha', 'option-c1', 'group-beta', 'option-d1', 'option-d2']);

            await fireEvent.click(group('beta'));
            expect(rowOrder()).toEqual(['option-a1', 'option-a2', 'group-alpha', 'option-c1', 'group-beta']);
        });

        it('are walked by the keyboard in screen order, between group rows and expanded items, and Enter picks one', async () => {
            const {trigger, onchange, bound} = mount();
            const input = await openByClick(trigger);

            // Entries of this open: a1 a2 [alpha] b1 b2 c1 [beta]. The first stop is an inline row, not a group row.
            expectActive(trigger, option('a1'));
            for (const id of ['option-a2', 'group-alpha', 'option-b1', 'option-b2', 'option-c1', 'group-beta']) {
                await fireEvent.keyDown(input, {key: 'ArrowDown'});
                expectActive(trigger, row(id));
            }

            // Expanding beta from the keyboard slots its items in after its row.
            await fireEvent.keyDown(input, {key: 'ArrowRight'});
            expect(group('beta')).toHaveAttribute('aria-expanded', 'true');
            await fireEvent.keyDown(input, {key: 'End'});
            expectActive(trigger, option('d2'));
            await fireEvent.keyDown(input, {key: 'Home'});
            expectActive(trigger, option('a1'));

            // Back up from the end to the inline row between the two families, and pick it.
            await fireEvent.keyDown(input, {key: 'End'});
            for (const id of ['option-d1', 'group-beta', 'option-c1']) {
                await fireEvent.keyDown(input, {key: 'ArrowUp'});
                expectActive(trigger, row(id));
            }
            await fireEvent.keyDown(input, {key: 'Enter'});

            expect(onchange).toHaveBeenCalledExactlyOnceWith('c1');
            expect(bound.value).toBe('c1');
            expect(trigger).toHaveAttribute('aria-expanded', 'false');
        });

        it('are filtered like any other row while searching', async () => {
            const {trigger} = mount({defaultExpanded: 'none'});
            const input = await openByClick(trigger);

            await fireEvent.input(input, {target: {value: 'shared'}});

            // a2 survives in its inline run, d2 in beta (shown expanded, as every matching family is);
            // alpha and the second run hold no match and go, rows and all.
            expect(rowOrder()).toEqual(['option-a2', 'group-beta', 'option-d2']);
            expect(group('beta')).toHaveAttribute('aria-expanded', 'true');
        });
    });

    describe('showSelected — a form field shows its value', () => {
        it('shows the selected item on the closed trigger, drawn by the selectedItem snippet', () => {
            const {trigger} = mount({value: 'b2', showSelected: true, selectedItem: selectedSnippet});

            expect(within(trigger).getByTestId('probe-selected')).toHaveAttribute('data-value', 'b2');
            expect(trigger).not.toHaveTextContent(PLACEHOLDER);
            // The trigger draws the value with its own snippet, never with the row snippet.
            expect(within(trigger).queryByTestId('probe-item')).toBeNull();
        });

        it.each([
            {label: 'empty', value: ''},
            {label: 'not a row of the tree', value: 'zz-unknown'},
        ])('falls back to the placeholder when the value is $label', ({value}) => {
            const {trigger} = mount({value, showSelected: true, selectedItem: selectedSnippet});

            expect(trigger).toHaveTextContent(PLACEHOLDER);
            expect(within(trigger).queryByTestId('probe-selected')).toBeNull();
        });

        it('stays an action picker by default: without showSelected the value never reaches the trigger', () => {
            const {trigger} = mount({value: 'b2', selectedItem: selectedSnippet});

            expect(trigger).toHaveTextContent(PLACEHOLDER);
            expect(within(trigger).queryByTestId('probe-selected')).toBeNull();
        });

        it('opens with the highlight on the selected row and, once another is chosen, shows that one', async () => {
            const {trigger, onchange, bound} = mount({value: 'c1', showSelected: true, selectedItem: selectedSnippet, defaultExpanded: 'none'});
            await openByClick(trigger);

            // Entries: a1 a2 [alpha] c1 [beta] — the highlight skips the first entry for the value,
            // so Enter would confirm the current choice instead of replacing it with the first row.
            expectActive(trigger, option('c1'));
            // While open the trigger is a search box: the selected content steps aside.
            expect(within(trigger).queryByTestId('probe-selected')).toBeNull();

            await fireEvent.click(group('beta'));
            await fireEvent.click(option('d1'));

            expect(onchange).toHaveBeenCalledExactlyOnceWith('d1');
            expect(bound.value).toBe('d1');
            expect(trigger).toHaveAttribute('aria-expanded', 'false');
            expect(within(trigger).getByTestId('probe-selected')).toHaveAttribute('data-value', 'd1');
        });
    });

    describe('defaultExpanded', () => {
        it("'first', the default, opens the first collapsible group, skipping the inline run in front of it", async () => {
            const {trigger} = mount();
            await openByClick(trigger);

            expect(group('alpha')).toHaveAttribute('aria-expanded', 'true');
            expect(option('b1')).toBeVisible();
            expect(group('beta')).toHaveAttribute('aria-expanded', 'false');
            expect(queryOption('d1')).toBeNull();
            expectActive(trigger, option('a1'));
        });

        it("'first' over inline groups only opens nothing, and every row is still there", async () => {
            const {trigger} = mount({groups: GROUPS.filter((candidate) => candidate.inline)});
            await openByClick(trigger);

            expect(rowOrder()).toEqual(['option-a1', 'option-a2', 'option-c1']);
            expectActive(trigger, option('a1'));
        });

        it("'selected' opens the group that holds the value, and again on every open", async () => {
            const {trigger} = mount({value: 'd2', defaultExpanded: 'selected'});
            const input = await openByClick(trigger);

            expect(group('beta')).toHaveAttribute('aria-expanded', 'true');
            expect(option('d2')).toBeVisible();
            expect(group('alpha')).toHaveAttribute('aria-expanded', 'false');

            // Collapsed by hand and reopened: the family of the value opens by itself once more.
            await fireEvent.click(group('beta'));
            expect(queryOption('d2')).toBeNull();
            await fireEvent.keyDown(input, {key: 'Escape'});
            expect(trigger).toHaveAttribute('aria-expanded', 'false');
            await openByClick(trigger);
            expect(group('beta')).toHaveAttribute('aria-expanded', 'true');
            expect(option('d2')).toBeVisible();
        });

        it.each([
            {label: 'sits in an inline group', value: 'c1'},
            {label: 'is empty', value: ''},
            {label: 'is not a row of the tree', value: 'zz-unknown'},
        ])("'selected' opens nothing when the value $label", async ({value}) => {
            const {trigger} = mount({value, defaultExpanded: 'selected'});
            await openByClick(trigger);

            expect(group('alpha')).toHaveAttribute('aria-expanded', 'false');
            expect(group('beta')).toHaveAttribute('aria-expanded', 'false');
            expect(rowOrder()).toEqual(['option-a1', 'option-a2', 'group-alpha', 'option-c1', 'group-beta']);
        });

        it("'none' opens nothing: the inline rows are all that shows", async () => {
            const {trigger} = mount({defaultExpanded: 'none'});
            await openByClick(trigger);

            expect(group('alpha')).toHaveAttribute('aria-expanded', 'false');
            expect(group('beta')).toHaveAttribute('aria-expanded', 'false');
            expect(rowOrder()).toEqual(['option-a1', 'option-a2', 'group-alpha', 'option-c1', 'group-beta']);
            expectActive(trigger, option('a1'));
        });
    });

    describe('test ids', () => {
        it.each([
            {label: 'its default prefix', testIdPrefix: undefined, expected: 'tree-select'},
            {label: 'the prefix it is given', testIdPrefix: 'probe-tree', expected: 'probe-tree'},
        ])('names every row after $label', async ({testIdPrefix, expected}) => {
            const {trigger} = mount({testIdPrefix});
            await openByClick(trigger);

            const rows = within(root()).queryAllByTestId(/-(option|group)-/);
            expect(rows.length, 'the open tree rendered no row at all').toBeGreaterThan(0);
            expect(rows.map((element) => element.getAttribute('data-testid')).filter((id) => !id?.startsWith(`${expected}-`))).toEqual([]);
            expect(within(root()).getByTestId(`${expected}-option-a1`)).toBeVisible();
            expect(within(root()).getByTestId(`${expected}-group-alpha`)).toHaveAttribute('aria-expanded', 'true');
        });
    });

    describe('content snippets', () => {
        it('renders every row through the item snippet, handed that very row', async () => {
            const {trigger} = mount();
            await openByClick(trigger);
            await fireEvent.click(group('beta'));

            const rows = within(root()).getAllByTestId(new RegExp(`^${PREFIX}-option-`));
            expect(rows.length, 'the open tree rendered no row at all').toBeGreaterThan(0);
            const mismatched = rows.filter((element) => {
                const probes = within(element).queryAllByTestId('probe-item');
                return probes.length !== 1 || element.getAttribute('data-testid') !== `${PREFIX}-option-${probes[0].getAttribute('data-value')}`;
            });
            expect(mismatched.map((element) => element.getAttribute('data-testid'))).toEqual([]);
        });

        it('draws a group row with the groupLabel snippet, keeping its own chevron and item count', async () => {
            const {trigger} = mount({groupLabel: groupLabelSnippet});
            await openByClick(trigger);

            const alpha = group('alpha');
            const label = within(alpha).getByTestId('probe-group-label');
            expect(label).toHaveAttribute('data-key', 'alpha');
            // The group object reaches the snippet whole, `icon` included — the default row has no use for it.
            expect(label.querySelector('img')).toHaveAttribute('src', '/probe/alpha.png');
            // The snippet replaces the default label and subtitle...
            expect(alpha).not.toHaveTextContent('Alpha subtitle');
            // ...and leaves the chevron and the count badge to the component.
            expect(alpha.querySelector('svg')).not.toBeNull();
            expect((alpha.textContent ?? '').replace(label.textContent ?? '', '').trim()).toBe('2');
        });

        it('without a groupLabel snippet prints label and subtitle, and ignores the group icon', async () => {
            const {trigger} = mount();
            await openByClick(trigger);

            const alpha = group('alpha');
            expect(alpha).toHaveTextContent('Alpha family');
            expect(alpha).toHaveTextContent('Alpha subtitle');
            expect(alpha.querySelector('img')).toBeNull();
        });
    });

    describe("the caller's texts", () => {
        it('uses the search placeholder and the empty-state text it is given', async () => {
            const {trigger, onchange} = mount({searchPlaceholder: SEARCH_PLACEHOLDER, noMatchesText: NO_MATCHES});
            const input = await openByClick(trigger);

            expect(input).toHaveAttribute('placeholder', SEARCH_PLACEHOLDER);

            await fireEvent.input(input, {target: {value: 'zz-no-match'}});

            const tree = within(root()).getByRole('tree');
            expect(tree).toHaveTextContent(NO_MATCHES);
            expect(within(tree).queryAllByRole('treeitem')).toHaveLength(0);
            expect(onchange).not.toHaveBeenCalled();
        });
    });
});

/** A path that defers work, armed through the interaction a user performs. */
interface DeferringPath {
    label: string;
    /** Brings the picker to where the path starts, running every step deferred on the way there. */
    prepare?: (trigger: HTMLElement) => Promise<unknown>;
    /** The interaction that defers, and nothing after it: the case destroys the picker at once. */
    arm: (trigger: HTMLElement) => Promise<unknown>;
}

/**
 * Each case arms the deferred work of one path, proves it is on the clock, unmounts the picker at once and counts
 * what is left. `prepare` drains the clock behind it, so what `arm` leaves there is that path's own work and nothing
 * the way there scheduled: a deferral left uncancelled turns red only the rows that arm it. The chain that was caught
 * throwing after teardown — open → `setTimeout` → active row → `setTimeout` → `document.getElementById` — is covered
 * link by link: the click row, the arrow-key row (the same scroll deferral) and the scroll case for the lookup.
 *
 * Every timer a row leaves must be the picker's own. jsdom queues a `selectionchange` on the same faked clock whenever
 * focus moves into the search box (`focus()` collapses the document selection; measured), and no teardown of the
 * picker can cancel that. So the open step always runs to its end before a row arms its deferral, and the clear
 * button is clicked without being focused first: the search box never has a focus to take back.
 *
 * No `waitFor` in this block: its polling runs on the faked clock. A deferred step is run by draining the clock.
 */
describe('TreeSelect — no deferred work survives destroy (K step 16, round 1)', () => {
    beforeAll(async () => {
        await setupI18n();
    });

    // Installed before the render: the handlers resolve `setTimeout` from the global when they run, so the fake
    // clock must be in place before the interaction that arms them — otherwise they land on the real one, where
    // `vi.getTimerCount()` cannot see them and where they can fire after the file's jsdom is gone.
    beforeEach(() => {
        vi.useFakeTimers();
    });

    // A case that failed before its `unmount()` leaves a picker mounted: unmount it while the clock that issued its
    // handles is still installed, then restore the real one — whatever is left on the fake clock is discarded with
    // it and can never fire. Then put back what the scroll case spied on.
    afterEach(() => {
        cleanup();
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    /** Opens with a click and runs the open step, with the scroll it defers: focus in the search box is its end. */
    async function openSettled(trigger: HTMLElement): Promise<HTMLInputElement> {
        await fireEvent.click(trigger);
        await vi.runAllTimersAsync();
        const input = searchBox(trigger);
        expect(input, 'the open step must have run').toHaveFocus();
        return input;
    }

    const PATHS: DeferringPath[] = [
        {label: 'a click opens it', arm: (trigger) => fireEvent.click(trigger)},
        // Two deferrals: the open step, and the key becoming the query.
        {label: 'a printable key opens it', arm: (trigger) => fireEvent.keyDown(trigger, {key: 's'})},
        {label: 'typing in the search box', prepare: openSettled, arm: (trigger) => fireEvent.input(searchBox(trigger), {target: {value: 'shared'}})},
        {
            label: 'the clear button empties the query',
            prepare: async (trigger) => {
                await fireEvent.input(await openSettled(trigger), {target: {value: 'shared'}});
                await vi.runAllTimersAsync();
            },
            // The only button the open trigger holds; its name is a translated string.
            arm: (trigger) => fireEvent.click(within(trigger).getByRole('button')),
        },
        {label: 'an arrow key moves the highlight', prepare: openSettled, arm: (trigger) => fireEvent.keyDown(searchBox(trigger), {key: 'ArrowDown'})},
    ];

    it.each(PATHS)('leaves no timer behind when unmounted right after $label', async ({prepare, arm}) => {
        const {trigger, unmount} = mount();
        await prepare?.(trigger);
        expect(vi.getTimerCount(), 'the way to the path must leave nothing pending').toBe(0);

        await arm(trigger);
        // Positive control: the path has work on the clock, so the zero below is about it.
        expect(vi.getTimerCount(), 'the path must defer work').toBeGreaterThan(0);

        unmount();
        expect(vi.getTimerCount(), 'deferred callbacks still pending after unmount').toBe(0);
    });

    it('scrolls the active row into view from inside the dropdown, never through the global document', async () => {
        const {trigger} = mount();
        const scrollIntoView = vi.spyOn(Element.prototype, 'scrollIntoView');
        const getElementById = vi.spyOn(document, 'getElementById');

        const input = await openSettled(trigger);
        await fireEvent.keyDown(input, {key: 'ArrowDown'});
        await vi.runAllTimersAsync();
        // Read here: what follows queries the DOM through testing-library, and only the component's lookups count.
        const globalLookups = getElementById.mock.calls.map(([id]) => id);

        // The dropdown is the tree the combobox says it controls.
        const tree = within(root()).getByRole('tree');
        expect(trigger).toHaveAttribute('aria-controls', tree.id);
        // a1 is the first entry of the open; ArrowDown moves the highlight to a2.
        const active = option('a2');
        expect(input).toHaveAttribute('aria-activedescendant', active.id);
        expect(tree).toContainElement(active);
        // The last scroll goes to the active row, aligned so that a row already in view leaves the list still.
        expect(scrollIntoView).toHaveBeenLastCalledWith({block: 'nearest'});
        expect(scrollIntoView.mock.contexts.at(-1), 'the last scroll must go to the active row').toBe(active);
        expect(globalLookups, 'the active row was looked up through the global document').toEqual([]);
    });
});
