// @vitest-environment jsdom
/**
 * SearchSelect — component test (Vitest + jsdom).
 *
 * SearchSelect is the select every other select in the app is built on, so a
 * regression here is a regression everywhere. Through the UI it only ever appears
 * fully populated inside some feature modal, which means an E2E can prove it opens
 * and picks a value but never that it filters, that the keyboard steps over a
 * section title, that the "create new" footer carries the typed query, or that a
 * disabled row refuses selection — all of which depend on an option list the test
 * must own. Those are the subject.
 *
 * The contract is `onchange(value)` plus the two-way `value`; every test asserts on
 * that payload or on a `data-*` the component publishes, never on a Tailwind class
 * or a translated string. The one product affordance that is *only* a class — the
 * roving highlight — is read through `data-highlighted`, added for exactly this
 * (the accessibility twin of SimpleSelect's `aria-activedescendant`).
 *
 * Option lookups are scoped to this instance's dropdown on purpose: the option
 * testid is `search-select-option-{value}`, shared by every SearchSelect on the
 * page, so an unscoped query would fish from a neighbour's list the moment two are
 * mounted. `within(dropdown(...))` is the closing barrier.
 *
 * The last block is `AssetSelect`'s, which has no test file of its own: what it
 * hands this trigger through the `selectedItem` snippet. A compact trigger grew
 * taller once an asset was chosen — a 28px icon box and a second, smaller line under
 * the name — so the chosen asset reads as one line there, with the dropdown's
 * `w-4 h-4` icon and the trigger's own text size, and the full-size trigger keeps its
 * box. jsdom lays nothing out, so the size utilities themselves are the subject, read
 * off the elements found by structure; the asset cache is this file's own fixture,
 * mocked for the whole file and read by that block alone (SearchSelect never reads it).
 */
import {describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {SelectOption} from './types';
import SearchSelect from './SearchSelect.svelte';

/** The asset cache `AssetSelect` reads, owned by the last block: one active asset with an icon of its own, a ticker and a currency. */
const CACHED_ASSET = vi.hoisted(() => ({
    id: 4242,
    display_name: 'Invented Holding Plc',
    identifier_ticker: 'INVH',
    currency: 'EUR',
    asset_type: 'STOCK',
    icon_url: 'https://cdn.test/invh.png',
    active: true,
}));

vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/reference/assetStore')>();
    const {readable} = await import('svelte/store');
    return {
        ...actual,
        assetStoreVersion: readable(0),
        ensureAssetsLoaded: vi.fn(() => Promise.resolve()),
        // A fresh array each call, as the real store re-derives one: `AssetSelect` sorts it in place.
        getAllAssets: vi.fn(() => [{...CACHED_ASSET}]),
    };
});

import AssetSelect from './AssetSelect.svelte';

/**
 * A list bracketed by section headers, with one disabled row, so the awkward
 * positions all exist: a header first, a header between two sections, a header
 * last, and a disabled option that the keyboard and the mouse must both refuse.
 */
const OPTS: SelectOption[] = [
    {value: '__sec:major', label: 'Major', header: true},
    {value: 'EUR', label: 'Euro', icon: '🇪🇺'},
    {value: 'USD', label: 'US Dollar', icon: '🇺🇸'},
    {value: 'GBP', label: 'British Pound', disabled: true},
    {value: '__sec:other', label: 'Other', header: true},
    {value: 'JPY', label: 'Japanese Yen', searchText: 'nippon yen'},
    {value: '__sec:trailing', label: 'Trailing', header: true},
];

function mount(props: Partial<ComponentProps<typeof SearchSelect>> = {}) {
    const onchange = vi.fn();
    const utils = render(SearchSelect, {value: '', options: OPTS, testId: 'ccy', ...props, onchange});
    const trigger = screen.getByTestId('ccy-trigger');
    return {onchange, trigger, ...utils};
}

/** The open dropdown panel, scoped to this instance — the barrier against the shared option prefix. */
function dropdown(): HTMLElement {
    // The listbox is the stable inner landmark; the panel is its parent and also holds
    // the (non-inline) search box and the create-new footer, which sit outside the listbox.
    return screen.getByRole('listbox').parentElement as HTMLElement;
}

/** An option button for a value this test put in the list, scoped to the open dropdown. */
function option(value: string): HTMLElement {
    return within(dropdown()).getByTestId(`search-select-option-${value}`);
}

/** Asserts which option the roving highlight points at, read as data rather than a CSS class. */
function expectHighlighted(value: string) {
    expect(option(value)).toHaveAttribute('data-highlighted', 'true');
}

async function open(trigger: HTMLElement) {
    await fireEvent.click(trigger);
    await waitFor(() => expect(screen.queryByRole('listbox')).not.toBeNull());
}

describe('SearchSelect', () => {
    describe('selection', () => {
        it('reports the chosen value, closes, and shows it on the trigger', async () => {
            await setupI18n();
            const {onchange, trigger} = mount({value: 'EUR'});
            await open(trigger);

            await fireEvent.click(option('USD'));

            expect(onchange).toHaveBeenCalledExactlyOnceWith('USD');
            expect(trigger).toHaveAttribute('aria-expanded', 'false');
            expect(screen.queryByRole('listbox')).toBeNull();
            // The trigger now renders the new selection's value (a prop, not a translation).
            expect(trigger).toHaveTextContent('USD');
        });

        it('refuses a disabled option and stays open', async () => {
            await setupI18n();
            const {onchange, trigger} = mount({value: 'EUR'});
            await open(trigger);

            expect(option('GBP')).toBeDisabled();
            await fireEvent.click(option('GBP'));

            expect(onchange).not.toHaveBeenCalled();
            expect(screen.getByRole('listbox')).toBeInTheDocument();
        });

        it('will not leave the highlight on a disabled row under the pointer', async () => {
            await setupI18n();
            const {trigger} = mount({value: 'EUR'});
            await open(trigger);

            await fireEvent.mouseEnter(option('USD'));
            expectHighlighted('USD');

            // GBP is disabled; hovering it moves the raw index there, but the reset
            // effect refuses a non-selectable highlight and pulls it back.
            await fireEvent.mouseEnter(option('GBP'));
            await waitFor(() => expect(option('GBP')).toHaveAttribute('data-highlighted', 'false'));
        });
    });

    describe('search', () => {
        it('narrows the list to what matches, across value, label and searchText', async () => {
            await setupI18n();
            const {trigger} = mount();
            await open(trigger);
            const search = screen.getByTestId('ccy-search');

            // 'nippon' is only in JPY's searchText — proof the search reaches past value+label.
            await fireEvent.input(search, {target: {value: 'nippon'}});
            expect(within(dropdown()).getByTestId('search-select-option-JPY')).toBeInTheDocument();
            expect(within(dropdown()).queryByTestId('search-select-option-EUR')).toBeNull();
        });

        it('drops a section header once its section is emptied by the query', async () => {
            await setupI18n();
            const {trigger} = mount();
            await open(trigger);
            const search = screen.getByTestId('ccy-search');

            // 'euro' keeps only EUR, under the 'Major' header; the 'Other' and 'Trailing'
            // headers now stand over nothing and must be dropped.
            await fireEvent.input(search, {target: {value: 'euro'}});
            expect(within(dropdown()).getByTestId('search-select-header-__sec:major')).toBeInTheDocument();
            expect(within(dropdown()).queryByTestId('search-select-header-__sec:other')).toBeNull();
            expect(within(dropdown()).queryByTestId('search-select-header-__sec:trailing')).toBeNull();
        });

        it('shows an empty state, with no options, when nothing matches', async () => {
            await setupI18n();
            const {trigger} = mount();
            await open(trigger);
            await fireEvent.input(screen.getByTestId('ccy-search'), {target: {value: 'zzz-no-such'}});

            // The listbox is still there (so the user sees *why*), but it holds no options.
            expect(screen.getByRole('listbox')).toBeInTheDocument();
            expect(within(dropdown()).queryAllByTestId(/^search-select-option-/)).toHaveLength(0);
        });

        it('clears the query with the inline clear button, restoring the full list', async () => {
            await setupI18n();
            const {trigger} = mount();
            await open(trigger);
            const search = screen.getByTestId('ccy-search') as HTMLInputElement;
            await fireEvent.input(search, {target: {value: 'euro'}});
            expect(within(dropdown()).queryByTestId('search-select-option-USD')).toBeNull();

            // The clear button only exists while there is a query to clear.
            await fireEvent.click(within(dropdown()).getByTestId('ccy-search-clear'));

            await waitFor(() => expect(within(dropdown()).getByTestId('search-select-option-USD')).toBeInTheDocument());
            expect(search.value).toBe('');
        });
    });

    /**
     * R13: typing "CSV" into the import-plugin picker left the highlight — the row Enter picks — on
     * whatever it had been on, far from the one match whose *name* says CSV. A query change is a
     * new question, so its answer starts at the top: the highlight on the first row the user can
     * land on, and the list scrolled back to show it.
     */
    describe('query change', () => {
        /**
         * Every "… one" row matches "one" the same way — a word start in its label — so whatever the
         * ranking does they keep this order, and the top row after typing is `alpha`: that isolates
         * the reset from the ordering. The leading header makes "top" mean the first row the user
         * can land on, not index 0.
         */
        const ROWS: SelectOption[] = [
            {value: '__sec:all', label: 'All', header: true},
            {value: 'alpha', label: 'Alpha one'},
            {value: 'beta', label: 'Beta one'},
            {value: 'gamma', label: 'Gamma one'},
            {value: 'delta', label: 'Delta two'},
        ];

        it('moves the highlight to the top row on every query change, even off a row the pointer chose', async () => {
            await setupI18n();
            const {trigger} = mount({options: ROWS});
            await open(trigger);
            const search = screen.getByTestId('ccy-search');

            await fireEvent.mouseEnter(option('gamma'));
            expectHighlighted('gamma');

            // 'one' keeps gamma at the very index the pointer left the highlight on, so nothing but
            // a reset on the query change can take it away.
            await fireEvent.input(search, {target: {value: 'one'}});
            await waitFor(() => expectHighlighted('alpha'));
            expect(option('gamma')).toHaveAttribute('data-highlighted', 'false');

            // Every change, not only the first — 'on' keeps the very same rows.
            await fireEvent.mouseEnter(option('beta'));
            expectHighlighted('beta');
            await fireEvent.input(search, {target: {value: 'on'}});
            await waitFor(() => expectHighlighted('alpha'));
        });

        it('lands the highlight on the best-ranked row, so Enter picks it (R13)', async () => {
            await setupI18n();
            // The import picker in miniature: every description says CSV, one name does, and that
            // one is not first in source order — which is how "CSV" + Enter used to pick Avanza.
            const plugins: SelectOption[] = [
                {value: 'broker_avanza', label: 'Avanza', searchText: 'Import transactions from Avanza CSV export.'},
                {value: 'broker_bitvavo', label: 'Bitvavo', searchText: 'Import transactions from Bitvavo CSV export.'},
                {value: 'broker_generic_csv', label: 'Generic CSV', searchText: 'Import transactions from a generic CSV file.'},
                {value: 'broker_xtb', label: 'XTB', searchText: 'Import transactions from XTB CSV export.'},
            ];
            // Enter advances focus through a deferred timer that reads containerRef (see the keyboard
            // block): fake timers let it run while the component is still mounted.
            vi.useFakeTimers();
            try {
                const {onchange, trigger} = mount({options: plugins});
                await fireEvent.click(trigger);
                const search = screen.getByTestId('ccy-search');
                expectHighlighted('broker_avanza');

                await fireEvent.input(search, {target: {value: 'CSV'}});
                await vi.advanceTimersByTimeAsync(30); // fake time: runs whatever the reset defers before the read
                expectHighlighted('broker_generic_csv');

                await fireEvent.keyDown(search, {key: 'Enter'});
                expect(onchange).toHaveBeenCalledExactlyOnceWith('broker_generic_csv');
                await vi.advanceTimersByTimeAsync(30); // drain the advance-focus timer while mounted
            } finally {
                vi.useRealTimers();
            }
        });

        it('scrolls the list back to the top when the query changes', async () => {
            await setupI18n();
            const {trigger} = mount({options: ROWS});
            await open(trigger);

            // jsdom has no layout, so it keeps whatever scrollTop it is given instead of clamping it —
            // the only reason a reset is observable here at all. Proven before it is relied upon.
            screen.getByRole('listbox').scrollTop = 120;
            expect(screen.getByRole('listbox').scrollTop).toBe(120);

            await fireEvent.input(screen.getByTestId('ccy-search'), {target: {value: 'one'}});

            // Re-queried on purpose: a list re-created at the top would be as good as one scrolled back.
            await waitFor(() => expect(screen.getByRole('listbox').scrollTop).toBe(0));
        });

        it('counts clearing the query as a change too: highlight on the top row, list at the top', async () => {
            await setupI18n();
            const {trigger} = mount({options: ROWS});
            await open(trigger);
            await fireEvent.input(screen.getByTestId('ccy-search'), {target: {value: 'one'}});
            await fireEvent.mouseEnter(option('gamma'));
            expectHighlighted('gamma');
            screen.getByRole('listbox').scrollTop = 80;
            expect(screen.getByRole('listbox').scrollTop).toBe(80);

            // The clear button assigns the query without an input event: the reset must follow the
            // query itself, not the keystrokes that usually change it.
            await fireEvent.click(within(dropdown()).getByTestId('ccy-search-clear'));

            await waitFor(() => expectHighlighted('alpha'));
            await waitFor(() => expect(screen.getByRole('listbox').scrollTop).toBe(0));
        });
    });

    describe('keyboard', () => {
        it('opens on the keys that should open it', async () => {
            await setupI18n();
            for (const key of ['Enter', ' ', 'ArrowDown']) {
                const {trigger, unmount} = mount();
                expect(trigger).toHaveAttribute('aria-expanded', 'false');
                await fireEvent.keyDown(trigger, {key});
                await waitFor(() => expect(trigger, `key ${key} should open`).toHaveAttribute('aria-expanded', 'true'));
                unmount();
            }
        });

        it('opens onto the first selectable option, stepping over a leading header', async () => {
            await setupI18n();
            const {trigger} = mount();
            await open(trigger);
            // '__sec:major' leads the list but is a header; the highlight starts on EUR.
            expectHighlighted('EUR');
        });

        it('steps over header and disabled rows with the arrow keys, and chooses on Enter', async () => {
            await setupI18n();
            // Enter-select advances focus through a deferred timer that reads containerRef; fake
            // timers let it run while the component is still mounted, instead of firing detached
            // after teardown. open() is fake-timer-safe: the listbox mounts on the click's microtask.
            vi.useFakeTimers();
            try {
                const {onchange, trigger} = mount();
                await fireEvent.click(trigger);
                const search = screen.getByTestId('ccy-search');
                expectHighlighted('EUR');

                await fireEvent.keyDown(search, {key: 'ArrowDown'});
                expectHighlighted('USD');

                // GBP is disabled and '__sec:other' is a header: one press clears both and lands on JPY.
                await fireEvent.keyDown(search, {key: 'ArrowDown'});
                expectHighlighted('JPY');

                await fireEvent.keyDown(search, {key: 'Enter'});
                expect(onchange).toHaveBeenCalledExactlyOnceWith('JPY');
                await vi.advanceTimersByTimeAsync(30); // drain the advance-focus timer while mounted
            } finally {
                vi.useRealTimers();
            }
        });

        it('holds at the top rather than wrapping past the leading header', async () => {
            await setupI18n();
            const {trigger} = mount();
            await open(trigger);
            const search = screen.getByTestId('ccy-search');
            expectHighlighted('EUR');

            // Above EUR there is only a header — nowhere legal to go, so it holds.
            await fireEvent.keyDown(search, {key: 'ArrowUp'});
            expectHighlighted('EUR');
        });

        it('closes on Escape without choosing anything', async () => {
            await setupI18n();
            const {onchange, trigger} = mount();
            await open(trigger);

            await fireEvent.keyDown(screen.getByTestId('ccy-search'), {key: 'Escape'});

            await waitFor(() => expect(trigger).toHaveAttribute('aria-expanded', 'false'));
            expect(onchange).not.toHaveBeenCalled();
        });

        it('opens and seeds the search from a printable key pressed on the trigger', async () => {
            await setupI18n();
            vi.useFakeTimers();
            try {
                const {trigger} = mount();
                await fireEvent.keyDown(trigger, {key: 'u'});
                // The key press opens the dropdown and, after the mount defer, seeds the query.
                await vi.advanceTimersByTimeAsync(30);
                expect(trigger).toHaveAttribute('aria-expanded', 'true');
                const search = screen.getByTestId('ccy-search') as HTMLInputElement;
                expect(search.value).toBe('u');
            } finally {
                vi.useRealTimers();
            }
        });
    });

    describe('unavailable states', () => {
        it('cannot be opened while disabled', async () => {
            await setupI18n();
            const {onchange, trigger} = mount({disabled: true});
            await fireEvent.click(trigger);
            await fireEvent.keyDown(trigger, {key: 'ArrowDown'});

            expect(trigger).toHaveAttribute('aria-expanded', 'false');
            expect(screen.queryByRole('listbox')).toBeNull();
            expect(onchange).not.toHaveBeenCalled();
        });

        it('announces a loading list as busy and shows no options', async () => {
            await setupI18n();
            const {trigger} = mount({loading: true});
            await open(trigger);

            const listbox = screen.getByRole('listbox');
            expect(listbox).toHaveAttribute('aria-busy', 'true');
            expect(within(dropdown()).queryAllByTestId(/^search-select-option-/)).toHaveLength(0);
        });
    });

    describe('closing', () => {
        it('closes on a click outside its own container', async () => {
            await setupI18n();
            const {trigger} = mount();
            await open(trigger);

            // The close-on-outside listener is a capturing mousedown on the document.
            await fireEvent.mouseDown(document.body);

            await waitFor(() => expect(trigger).toHaveAttribute('aria-expanded', 'false'));
        });
    });

    describe('section headers', () => {
        it('renders a header as furniture, never as a clickable option', async () => {
            await setupI18n();
            const {onchange, trigger} = mount();
            await open(trigger);

            expect(within(dropdown()).getByTestId('search-select-header-__sec:major')).toBeInTheDocument();
            expect(within(dropdown()).queryByTestId('search-select-option-__sec:major')).toBeNull();

            // A trailing header standing over nothing is dropped even with no query.
            expect(within(dropdown()).queryByTestId('search-select-header-__sec:trailing')).toBeNull();
            expect(onchange).not.toHaveBeenCalled();
        });
    });

    describe('icons', () => {
        it('renders a URL icon as an <img> and an emoji icon as text', async () => {
            await setupI18n();
            const opts: SelectOption[] = [
                {value: 'URL', label: 'Has image', icon: '/icons/url.png'},
                {value: 'EMO', label: 'Has emoji', icon: '🚀'},
            ];
            const {trigger} = mount({options: opts});
            await open(trigger);

            // The URL is rendered as an image (alt is empty by design), not leaked as a text node.
            const urlOpt = option('URL');
            expect(urlOpt.querySelector('img')).not.toBeNull();
            expect(urlOpt.querySelector('img')!.getAttribute('src')).toBe('/icons/url.png');

            // The emoji stays a text node — no <img> for it.
            const emoOpt = option('EMO');
            expect(emoOpt.querySelector('img')).toBeNull();
            expect(emoOpt).toHaveTextContent('🚀');
        });

        it('shows the selected option’s URL icon on the closed trigger', async () => {
            await setupI18n();
            const opts: SelectOption[] = [{value: 'AAPL', label: 'Apple Inc', icon: 'https://cdn.test/aapl.png'}];
            const {trigger} = mount({options: opts, value: 'AAPL'});

            // Trigger stays closed; the selected value's image icon renders in it.
            const img = trigger.querySelector('img');
            expect(img).not.toBeNull();
            expect(img!.getAttribute('src')).toBe('https://cdn.test/aapl.png');
        });
    });

    describe('create-new footer', () => {
        it('offers the footer only when both a label and a handler are given, and hands it the typed query', async () => {
            await setupI18n();
            const onCreateNew = vi.fn();
            // createLabelFor formats the footer from the query; it is our function, not a
            // translation, so its output is fair to assert on.
            const {trigger} = mount({
                createLabel: 'Create',
                createLabelFor: (q: string) => `make:${q}`,
                onCreateNew,
            });
            await open(trigger);

            const footer = within(dropdown()).getByTestId('search-select-create-new');
            expect(footer).toBeInTheDocument();

            await fireEvent.input(screen.getByTestId('ccy-search'), {target: {value: 'BTP 28'}});
            expect(within(dropdown()).getByTestId('search-select-create-new')).toHaveTextContent('make:BTP 28');

            await fireEvent.click(within(dropdown()).getByTestId('search-select-create-new'));
            expect(onCreateNew).toHaveBeenCalledExactlyOnceWith('BTP 28');
        });

        it('shows no footer when no create handler is wired', async () => {
            await setupI18n();
            const {trigger} = mount();
            await open(trigger);
            expect(within(dropdown()).queryByTestId('search-select-create-new')).toBeNull();
        });
    });

    describe('inline search', () => {
        it('puts the search box inside the trigger when inlineSearch is set', async () => {
            await setupI18n();
            const {trigger} = mount({inlineSearch: true});
            await open(trigger);

            // In inline mode the search input lives in the trigger itself…
            const search = within(trigger).getByTestId('ccy-search');
            expect(search).toBeInTheDocument();
            // …and there is no separate search field in the dropdown body.
            expect(within(dropdown()).queryByTestId('ccy-search')).toBeNull();
        });
    });
});

// =============================================================================
// AssetSelect — the chosen asset on the trigger
// =============================================================================

/** A Tailwind font-size utility — a step of the scale or an arbitrary size, never a colour such as `text-gray-500`. */
const FONT_SIZE = /^text-(xs|sm|base|lg|[2-9]?xl|\[[^\]]+\])$/;

/** An element as its tag and utilities, for a red that says what is on screen. */
function described(element: Element): string {
    return [element.tagName.toLowerCase(), ...element.classList].join('.');
}

/** Every element at or under `root`. */
function selfAndBelow(root: Element): Element[] {
    return [root, ...root.querySelectorAll('*')];
}

/** The size an element's text is drawn at, as the utilities say it: its own, else its nearest ancestor's, up to `top` included. */
function fontSizeOf(element: Element, top: Element): string | null {
    for (let node: Element | null = element; node; node = node.parentElement) {
        const size = [...node.classList].find((token) => FONT_SIZE.test(token));
        if (size) return size;
        if (node === top) break;
    }
    return null;
}

/**
 * Text stacked on lines of its own: an element holding two or more `div`/`p` children that carry
 * text, unless it lays them out side by side (`flex` without `flex-col`). Today's selected item has
 * one: the name above, the label and the currency below.
 */
function stackedLines(root: Element): string[] {
    return selfAndBelow(root)
        .filter((parent) => {
            if (parent.classList.contains('flex') && !parent.classList.contains('flex-col')) return false;
            const lines = [...parent.children].filter((child) => (child.tagName === 'DIV' || child.tagName === 'P') && (child.textContent ?? '').trim() !== '');
            return lines.length > 1;
        })
        .map(described);
}

/** The elements that write the chosen asset's name — its ticker or its display name — in text of their own. */
function nameHolders(root: Element): Element[] {
    const names = [CACHED_ASSET.identifier_ticker, CACHED_ASSET.display_name];
    return selfAndBelow(root).filter((element) => [...element.childNodes].some((node) => node.nodeType === Node.TEXT_NODE && names.some((name) => (node.textContent ?? '').includes(name))));
}

/** `AssetSelect` mounted on the cached asset, and its trigger once the chosen asset is drawn on it. */
async function mountAssetSelect(compact: boolean): Promise<{trigger: HTMLElement; icon: HTMLImageElement}> {
    render(AssetSelect, {value: CACHED_ASSET.id, compact, testid: 'chosen-asset'});
    const trigger = screen.getByTestId('chosen-asset-trigger');
    // The barrier: the chosen asset's own icon is on the trigger, so the selected item has been drawn.
    const icon = await waitFor(() => {
        const found = trigger.querySelector<HTMLImageElement>(`img[src="${CACHED_ASSET.icon_url}"]`);
        expect(found, 'the chosen asset is not drawn on the trigger: the selected item never rendered').not.toBeNull();
        return found as HTMLImageElement;
    });
    return {trigger, icon};
}

describe('AssetSelect — the chosen asset on the trigger', () => {
    it("compact: one line, with the dropdown's w-4 h-4 icon and the trigger's text size, and no icon box", async () => {
        await setupI18n();
        const {trigger, icon} = await mountAssetSelect(true);
        const triggerSize = fontSizeOf(trigger, trigger);
        expect(triggerSize, 'premise: the compact trigger states a text size of its own').not.toBeNull();
        const names = nameHolders(trigger);
        expect(names.length, 'premise: the chosen asset is named on the trigger').toBeGreaterThan(0);

        expect(
            selfAndBelow(trigger)
                .filter((element) => element.classList.contains('w-7') || element.classList.contains('h-7'))
                .map(described),
            'the compact trigger still draws the chosen asset in the 28px icon box, taller than the line it sits on',
        ).toEqual([]);
        expect([...icon.classList], "the chosen asset's icon is not the dropdown's w-4 h-4 one").toEqual(expect.arrayContaining(['w-4', 'h-4']));
        expect(stackedLines(trigger), 'the chosen asset takes two lines on a compact trigger, so the trigger grows once a value is chosen').toEqual([]);
        expect(
            names.map((holder) => `${described(holder)}: ${fontSizeOf(holder, trigger)}`),
            "the chosen asset is not written at the trigger's text size",
        ).toEqual(names.map((holder) => `${described(holder)}: ${triggerSize}`));
    });

    it('full size: the chosen asset keeps its icon box and its two lines', async () => {
        await setupI18n();
        const {trigger, icon} = await mountAssetSelect(false);

        expect([...(icon.parentElement as HTMLElement).classList], 'the full-size trigger lost the icon box around the chosen asset').toEqual(expect.arrayContaining(['w-7', 'h-7']));
        expect(stackedLines(trigger), 'the full-size trigger no longer writes the name above the label and the currency').toHaveLength(1);
    });
});
