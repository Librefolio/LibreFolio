// @vitest-environment jsdom
/**
 * BenchmarkSelect — the one benchmark picker every Risk surface mounts (Vitest + jsdom).
 *
 * Developer decision, 01/10/2026: wherever a page measures against a benchmark — the
 * Dashboard and Broker L3, the Asset Global lab, the asset page's Risk tab — there is a
 * picker, it opens on the current benchmark, and it is empty only when nothing is set.
 * The three surfaces mount this one component so the rule cannot diverge. What is
 * pinned, rule by rule:
 *
 *   1. **It opens on the shared choice.** On mount it asks `resolveRiskBenchmark()` and
 *      hands the answer to `value`. Nothing stored → the placeholder and null. A stored
 *      id it cannot confirm — a deleted asset, or a list that did not load — reads as
 *      `unknown`: the placeholder and null, and the store is left exactly as it was.
 *   2. **Only what the page measures leaves the list** (`measuredAssetIds`) — never the
 *      current choice, which stays listed and selectable. Held assets, plain assets and
 *      inactive ones are all offered: there is no holdings concept here at all.
 *   3. **A measured current choice is still shown**, never swapped for the placeholder,
 *      with `${testid}-measured` worded by `risk.benchmark.measuredHere`. Presence,
 *      absence and the key are pinned; layout and icon are not.
 *   4. **Choosing is choosing for every page.** The shared store (memory and the
 *      user-scoped key) is written first, then `value`, then `onchange(next)`.
 *   5. **A late check never overwrites a choice made while it was running.**
 *   6. **Benchmarks first**, under a title of their own, the rest under another — the
 *      structure `SignalAssetParamControl` gives the same list.
 *
 * Second round, the approved visual design (01/10/2026):
 *
 *   7. **The root publishes the state** a page reads: `${testid}-control` carries
 *      `data-benchmark-id` (the resolved value, `''` when there is none) and
 *      `data-measured` (`'true'` | `'false'`).
 *   8. **The ⚠ is an image a keyboard can reach, not a button** — `tabindex="0"`,
 *      `role="img"` — and its `aria-label` is the hint: `risk.benchmark.measuredHere` by
 *      default, or exactly the page's own `measuredHint`, which then replaces the default
 *      wherever the warning speaks.
 *
 * Third round, the resolution state (01/10/2026):
 *
 *   9. **The picker says how far it got**: a `$bindable` `state` — `'none' | 'pending' |
 *      'set' | 'unknown'` — published as `data-benchmark-state` on the root. `none` at
 *      once when nothing is stored; `pending` from the first instant an id is stored and
 *      until its check settles, then `set` or `unknown`. A reader's choice is `set` before
 *      anyone hears of it, and a late check overwrites none of it.
 *  10. **An unconfirmed id is never published.** While the state is `pending`, `value`
 *      stays null, `data-benchmark-id` is `''` and the trigger shows no asset — even for
 *      an id the list goes on to confirm, which arrives with `set` and not before. So a
 *      page that waits for `set` and a page that reads `value` cannot disagree, and
 *      neither can measure against an id nobody confirmed.
 *
 * Not pinned, on purpose: whether `onchange` also fires when the mount-time resolution
 * lands (the contract does not say), what the trigger says while the state is `pending`
 * beyond showing no asset, and clearing — `AssetSelect` has no control that empties a
 * choice, so there is nothing for a reader to press.
 *
 * Observed only through what a page can see: `data-testid`s, the bound `value` (held in
 * a `$state` behind a getter/setter, as a parent's `bind:value` would hold it), the
 * `onchange` payload, the shared store and its storage key. Asset names are this file's
 * own fixture and the placeholder is a prop it passes in; the one sentence that matters
 * is resolved from the shipped catalogue through the same `$_` the component uses, so no
 * translated text is written down here.
 */
import {beforeAll, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import {tick} from 'svelte';
import {get} from 'svelte/store';

// The shared `$app/environment` mock reports `browser: false`, which turns every storage
// path of the benchmark store into a no-op — and "the choice reaches the shared key" is
// half of what this file pins. Same override as `riskBenchmarkStore.test.ts`, with every
// export spelled out because the component tree imports more of this module than the
// store does.
vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

/**
 * The asset cache, owned by this file: the list it holds, a gate on
 * `ensureAssetsLoaded()` that the race cases hold open, and a failure it can answer with
 * instead. The list is in the cache from the start — a warm cache with a refresh in
 * flight — which is what lets a reader find an asset while the stored benchmark is still
 * being confirmed.
 */
const cache = vi.hoisted(() => ({
    entries: [] as Array<Record<string, unknown> & {id: number}>,
    gate: null as Promise<void> | null,
    failure: null as Error | null,
}));

vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/reference/assetStore')>();
    const {readable} = await import('svelte/store');
    return {
        ...actual,
        assetStoreVersion: readable(0),
        // A fresh rejection per call, so no rejected promise is ever left unobserved.
        ensureAssetsLoaded: vi.fn(() => (cache.failure ? Promise.reject(cache.failure) : (cache.gate ?? Promise.resolve()))),
        getAssetInfo: vi.fn((id: number) => cache.entries.find((asset) => asset.id === id) ?? null),
        // A fresh array each call, as the real store re-derives one: `AssetSelect` sorts it in place.
        getAllAssets: vi.fn(() => cache.entries.map((asset) => ({...asset}))),
    };
});

// The real store and the real resolution, with a spy in between. It adds two things and
// changes none: proof that the picker asks the one shared primitive rather than carrying a
// copy of the rule, and a barrier — "every resolution it started has answered" — for the
// cases where nothing else on screen moves when it does.
vi.mock('$lib/stores/risk/riskBenchmarkStore.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/risk/riskBenchmarkStore.svelte')>();
    return {
        ...actual,
        resolveRiskBenchmark: vi.fn(() => actual.resolveRiskBenchmark()),
    };
});

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {reactiveBox} from '$test/runes.svelte';
import {_} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import {transitionClientSession} from '$lib/stores/app/clientSession';
import {ensureAssetsLoaded} from '$lib/stores/reference/assetStore';
import {resolveRiskBenchmark, riskBenchmark} from '$lib/stores/risk/riskBenchmarkStore.svelte';
import BenchmarkSelect from './BenchmarkSelect.svelte';

// ─── Fixture ────────────────────────────────────────────────────────────────────────────────

/** Two flagged benchmarks. */
const AURORA = {id: 101, display_name: 'Aurora World Index', currency: 'USD', asset_type: 'INDEX', active: true, is_benchmark: true, tx_count_own: 0};
const BOREALIS = {id: 102, display_name: 'Borealis Bond Index', currency: 'EUR', asset_type: 'INDEX', active: true, is_benchmark: true, tx_count_own: 0};
/** Held by the reader: a benchmark candidate like any other (01/10/2026). */
const COBALT = {id: 201, display_name: 'Cobalt Held Equity', currency: 'EUR', asset_type: 'STOCK', active: true, is_benchmark: false, tx_count_own: 4};
const DUNE = {id: 202, display_name: 'Dune Plain Equity', currency: 'USD', asset_type: 'STOCK', active: true, is_benchmark: false, tx_count_own: 0};
/** Inactive and held: still on offer, since only what the page measures leaves the list. */
const EMBER = {id: 203, display_name: 'Ember Matured Note', currency: 'EUR', asset_type: 'BOND', active: false, is_benchmark: false, tx_count_own: 2};

const FIXTURE = [AURORA, BOREALIS, COBALT, DUNE, EMBER];
type FixtureAsset = (typeof FIXTURE)[number];
const BENCHMARK_IDS = FIXTURE.filter((asset) => asset.is_benchmark).map((asset) => asset.id);
const OTHER_IDS = FIXTURE.filter((asset) => !asset.is_benchmark).map((asset) => asset.id);
/** A stored id whose asset no longer exists. */
const GONE_ID = 999;

const PLACEHOLDER = 'Synthetic benchmark placeholder';
const DEFAULT_TESTID = 'risk-benchmark-select';
/** The asset page's id for the picker: `${testid}-measured` is pinned as a composition, not a literal. */
const ASSET_PAGE_TESTID = 'risk-comparison-asset-select';
const MEASURED_KEY = 'risk.benchmark.measuredHere';
const CATALOGUES = {en, it: itCatalogue, fr, es};
/** A page's own, already-translated wording for the warning (`measuredHint`): this file's string, never a catalogue's. */
const HINT = 'Synthetic page hint: the lab already compares this asset';

// ─── Helpers ────────────────────────────────────────────────────────────────────────────────

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/**
 * What the measured-here marker must say, as normalised fragments of the shipped sentence.
 *
 * Resolved through the same `$_` the component uses. A sentence that interpolates (the
 * asset's name, say) is compared by its literal fragments instead, so the wording is
 * pinned without this file guessing the values the component passes in.
 */
function expectedWording(): string[] {
    const raw = at(en, MEASURED_KEY);
    if (typeof raw !== 'string') throw new Error(`${MEASURED_KEY} is missing from en.json: the marker has no sentence to carry`);
    if (raw.includes('{'))
        return raw
            .split(/\{[^{}]*\}/)
            .map(normalize)
            .filter(Boolean);
    return [normalize(get(_)(MEASURED_KEY))];
}

/**
 * Everything the marker says to a reader: its text, the accessible names and descriptions
 * on it and inside it, and — if the sentence is not among them — the tooltip it opens.
 * `Tooltip.svelte` renders its sentence only while open, so a marker built on it is opened
 * the way a reader opens it rather than failed for a layout choice this file does not pin.
 */
async function wordingOf(marker: HTMLElement): Promise<string> {
    const parts: string[] = [marker.textContent ?? ''];
    for (const element of [marker, ...Array.from(marker.querySelectorAll<HTMLElement>('*'))]) {
        for (const attribute of ['title', 'aria-label', 'aria-description']) {
            const value = element.getAttribute(attribute);
            if (value) parts.push(value);
        }
        for (const attribute of ['aria-labelledby', 'aria-describedby']) {
            for (const id of (element.getAttribute(attribute) ?? '').split(/\s+/).filter(Boolean)) {
                parts.push(document.getElementById(id)?.textContent ?? '');
            }
        }
    }
    const inline = normalize(parts.join(' '));
    if (expectedWording().every((fragment) => inline.includes(fragment))) return inline;
    await fireEvent.click(marker);
    const tooltips = Array.from(document.querySelectorAll('[role="tooltip"]')).map((tooltip) => tooltip.textContent ?? '');
    return normalize([inline, ...tooltips].join(' '));
}

/** The default hint, exactly as the component words it: `$_('risk.benchmark.measuredHere')`, no values. */
function defaultHint(): string {
    return normalize(get(_)(MEASURED_KEY));
}

/**
 * Every tooltip the warning opens when a reader clicks it — none, if it opens none. The
 * click always happens; what is asserted afterwards is that whatever opened says the hint.
 */
async function tooltipsOpenedBy(marker: HTMLElement): Promise<string[]> {
    await fireEvent.click(marker);
    return Array.from(document.querySelectorAll('[role="tooltip"]')).map((tooltip) => normalize(tooltip.textContent));
}

/** Everything the warning says without being opened: its text, and the names and descriptions on it and in it. */
function inlineWordingOf(marker: HTMLElement): string {
    const parts: string[] = [marker.textContent ?? ''];
    for (const element of [marker, ...Array.from(marker.querySelectorAll<HTMLElement>('*'))]) {
        for (const attribute of ['title', 'aria-label', 'aria-description']) parts.push(element.getAttribute(attribute) ?? '');
        for (const attribute of ['aria-labelledby', 'aria-describedby']) {
            for (const id of (element.getAttribute(attribute) ?? '').split(/\s+/).filter(Boolean)) parts.push(document.getElementById(id)?.textContent ?? '');
        }
    }
    return normalize(parts.join(' '));
}

let accountSeq = 0;

/** The key `riskBenchmarkStore` keeps one reader's choice under. */
function keyFor(account: string): string {
    return `lf_${account}_risk_benchmark_asset`;
}

/**
 * A reader arriving with `stored` already in storage from an earlier visit, or nothing.
 *
 * Seeded *before* the account becomes current: the store re-reads storage when the
 * resolved account changes, and that is the only moment it does, so a fresh account per
 * test is the store's own re-hydration trigger rather than a back door.
 */
function returningReader(stored: number | null): string {
    const account = `benchmark-select-u${++accountSeq}`;
    if (stored !== null) localStorage.setItem(keyFor(account), String(stored));
    transitionClientSession(account);
    return account;
}

/** The resolution state the picker publishes (third round). */
type BenchmarkState = 'none' | 'pending' | 'set' | 'unknown';

interface Mounted {
    /** The parent's state: what `bind:value`, `bind:state` and the page's measured ids would hold. */
    box: {value: number | null; measured: number[]; state: BenchmarkState};
    /** Every write the component made to `value`, with the shared store as it stood at that instant. */
    writes: Array<{value: number | null; storeAtWrite: number | null}>;
    /** Every state the component wrote, in order. */
    states: BenchmarkState[];
    onchange: Mock<(next: number | null) => void>;
    testid: string;
    root: HTMLElement;
    trigger: HTMLElement;
    unmount: () => void;
}

/**
 * Mount the picker as a page would: `value` and `state` bound to the parent's `$state`,
 * the measured ids read from it too, so a page that changes what it measures is a plain
 * assignment. `measured` left undefined passes no prop at all, so the default is what
 * runs; so does `hint`, which becomes `measuredHint` when given.
 *
 * The parent's `state` starts at `'none'`, as a page's `$state('none')` would, and not
 * `undefined`: binding `undefined` to a prop that declares a fallback is a Svelte error
 * (`props_invalid_value`), so a picker written `state = $bindable('none')` would refuse
 * to mount for a reason that is the harness's, not the picker's.
 */
function mount(options: {measured?: number[]; testid?: string; hint?: string} = {}): Mounted {
    const box = reactiveBox<{value: number | null; measured: number[]; state: BenchmarkState}>({value: null, measured: options.measured ?? [], state: 'none'});
    const writes: Mounted['writes'] = [];
    const states: BenchmarkState[] = [];
    const onchange = vi.fn<(next: number | null) => void>();
    const props: Record<string, unknown> = {placeholder: PLACEHOLDER, onchange};
    if (options.testid !== undefined) props.testid = options.testid;
    if (options.hint !== undefined) props.measuredHint = options.hint;
    Object.defineProperty(props, 'value', {
        enumerable: true,
        configurable: true,
        get: () => box.value,
        set: (next: number | null) => {
            writes.push({value: next, storeAtWrite: riskBenchmark.assetId});
            box.value = next;
        },
    });
    Object.defineProperty(props, 'state', {
        enumerable: true,
        configurable: true,
        get: () => box.state,
        set: (next: BenchmarkState) => {
            states.push(next);
            box.state = next;
        },
    });
    if (options.measured !== undefined) {
        Object.defineProperty(props, 'measuredAssetIds', {enumerable: true, configurable: true, get: () => box.measured});
    }
    const view = render(BenchmarkSelect, props);
    const testid = options.testid ?? DEFAULT_TESTID;
    return {box, writes, states, onchange, testid, root: screen.getByTestId(testid), trigger: screen.getByTestId(`${testid}-trigger`), unmount: view.unmount};
}

/** The sequence of states, with a state written twice in a row counted once. */
function transitions(states: BenchmarkState[]): BenchmarkState[] {
    return states.filter((state, index) => index === 0 || state !== states[index - 1]);
}

const resolveSpy = () => vi.mocked(resolveRiskBenchmark);

/**
 * The picker's root, `${testid}-control`, where pages read its state. Looked up when a
 * case asks for it rather than at mount, so a root that is missing fails the cases about
 * the root and not every other one.
 */
function control(m: Mounted): HTMLElement {
    return screen.getByTestId(`${m.testid}-control`);
}

/** Every `resolveRiskBenchmark()` the picker started has answered, and the DOM has caught up. */
async function resolutionSettled(): Promise<void> {
    await waitFor(() => expect(resolveSpy(), 'the picker never asked resolveRiskBenchmark() for the shared choice').toHaveBeenCalled());
    await Promise.allSettled(resolveSpy().mock.results.map((result) => result.value));
    await tick();
}

/** Open the list and wait for it to fill: `AssetSelect` shows "loading" until its cache call settles. */
async function openList(m: Mounted): Promise<HTMLElement> {
    await fireEvent.click(m.trigger);
    const listbox = await within(m.root).findByRole('listbox');
    await waitFor(() => expect(within(listbox).queryAllByTestId(/^search-select-option-\d+$/).length, 'the list never filled').toBeGreaterThan(0));
    return listbox;
}

function idOf(element: HTMLElement): number {
    return Number((element.getAttribute('data-testid') ?? '').replace('search-select-option-', ''));
}

/** The asset ids the open list offers. */
function offeredIds(listbox: HTMLElement): number[] {
    return within(listbox)
        .queryAllByTestId(/^search-select-option-\d+$/)
        .map(idOf);
}

/** The open list in screen order: a section title is `'title'`, an option its asset id. */
function rowsOf(listbox: HTMLElement): Array<'title' | number> {
    return Array.from(listbox.querySelectorAll<HTMLElement>('[data-testid^="search-select-header-"], [data-testid^="search-select-option-"]')).map((row) => ((row.getAttribute('data-testid') ?? '').startsWith('search-select-header-') ? 'title' : idOf(row)));
}

async function choose(m: Mounted, asset: FixtureAsset): Promise<void> {
    const listbox = await openList(m);
    await fireEvent.click(within(listbox).getByTestId(`search-select-option-${asset.id}`));
}

/**
 * Choose by typing and Enter. `SearchSelect` keeps its search box live while the list reads
 * "loading", and Enter picks from what the search shows — the one way a reader can beat
 * the mount-time check to a choice, which is the case the race tests exist for.
 */
async function chooseByTyping(m: Mounted, query: string): Promise<void> {
    expect(m.trigger, 'the picker is locked while the stored benchmark is checked: a reader cannot choose').toHaveAttribute('aria-disabled', 'false');
    await fireEvent.click(m.trigger);
    const search = within(m.root).getByTestId(`${m.testid}-search`);
    await fireEvent.input(search, {target: {value: query}});
    await fireEvent.keyDown(search, {key: 'Enter'});
}

function expectNoAssetOn(trigger: HTMLElement): void {
    for (const asset of FIXTURE) expect(trigger, `the picker shows ${asset.display_name} although nothing is chosen`).not.toHaveTextContent(asset.display_name);
}

function deferred(): {promise: Promise<void>; resolve: () => void} {
    let resolve!: () => void;
    const promise = new Promise<void>((settle) => {
        resolve = () => settle();
    });
    return {promise, resolve};
}

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    // This jsdom build exposes no `localStorage` at all (see `DataTable.test.ts`), and the
    // shared key is half of what this file pins: same Map-backed stand-in as
    // `riskBenchmarkStore.test.ts`, fresh for every case.
    const backing = new Map<string, string>();
    Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        writable: true,
        value: {
            getItem: (key: string) => backing.get(key) ?? null,
            setItem: (key: string, value: string) => void backing.set(key, String(value)),
            removeItem: (key: string) => void backing.delete(key),
            clear: () => backing.clear(),
            key: (index: number) => [...backing.keys()][index] ?? null,
            get length() {
                return backing.size;
            },
        },
    });
    cache.entries = FIXTURE.map((asset) => ({...asset}));
    cache.gate = null;
    cache.failure = null;
    resolveSpy().mockClear();
    vi.mocked(ensureAssetsLoaded).mockClear();
});

// ─── The harness itself ─────────────────────────────────────────────────────────────────────

describe('BenchmarkSelect — the harness itself', () => {
    it.each(Object.keys(CATALOGUES) as (keyof typeof CATALOGUES)[])(`ships ${MEASURED_KEY} in %s.json`, (locale) => {
        const sentence = at(CATALOGUES[locale], MEASURED_KEY);
        expect(typeof sentence, `${MEASURED_KEY} is missing from ${locale}.json`).toBe('string');
        expect(normalize(sentence as string)).not.toBe('');
    });

    it('resolves the measured-here sentence through the $_ the component uses', () => {
        // svelte-i18n echoes a missing id back; were that the case the marker would echo it
        // too, and "the marker carries the sentence" would compare the key with itself.
        expect(get(_)(MEASURED_KEY), `${MEASURED_KEY} does not resolve: the catalogue is not loaded or the key is missing`).not.toBe(MEASURED_KEY);
    });

    it('owns a fixture where every rule has something to act on', () => {
        expect(BENCHMARK_IDS.length, 'two benchmarks: one can be measured while the other stays on offer').toBeGreaterThanOrEqual(2);
        expect(OTHER_IDS.length).toBeGreaterThanOrEqual(2);
        expect(
            FIXTURE.some((asset) => !asset.is_benchmark && asset.tx_count_own > 0),
            'a held asset, to prove holdings filter nothing',
        ).toBe(true);
        expect(
            FIXTURE.some((asset) => !asset.active),
            'an inactive asset, to prove only measured assets leave the list',
        ).toBe(true);
        expect(new Set(FIXTURE.map((asset) => asset.id)).size).toBe(FIXTURE.length);
        expect(FIXTURE.map((asset) => asset.id)).not.toContain(GONE_ID);
        // The race cases choose by typing: each query must reach exactly one asset, by name only.
        for (const query of ['Dune', 'Cobalt']) {
            expect(FIXTURE.filter((asset) => asset.display_name.includes(query) || String(asset.id).includes(query))).toHaveLength(1);
        }
    });
});

// ─── 1. It opens on the shared choice ───────────────────────────────────────────────────────

describe('BenchmarkSelect — it opens on the shared choice', () => {
    it('shows the stored benchmark, not the placeholder, hands it to value and leaves the store as it was', async () => {
        const reader = returningReader(BOREALIS.id);
        const m = mount();

        await waitFor(() => expect(m.box.value, 'value never received the stored benchmark').toBe(BOREALIS.id));
        await resolutionSettled();

        expect(m.trigger).toHaveTextContent(BOREALIS.display_name);
        expect(m.trigger).not.toHaveTextContent(PLACEHOLDER);
        expect(riskBenchmark.assetId).toBe(BOREALIS.id);
        expect(localStorage.getItem(keyFor(reader))).toBe(String(BOREALIS.id));
    });

    it('shows the placeholder and leaves value null when nothing is stored', async () => {
        const reader = returningReader(null);
        const m = mount();

        await resolutionSettled();

        expect(m.trigger).toHaveTextContent(PLACEHOLDER);
        expectNoAssetOn(m.trigger);
        expect(m.box.value).toBeNull();
        expect(
            m.writes.filter((write) => write.value !== null),
            'value was given a benchmark nobody chose',
        ).toEqual([]);
        expect(localStorage.getItem(keyFor(reader))).toBeNull();
    });

    it('treats a stored id it cannot confirm as unknown: placeholder and null, with the store left as it was', async () => {
        const reader = returningReader(GONE_ID);
        expect(localStorage.getItem(keyFor(reader)), 'precondition: the unconfirmable id is stored').toBe(String(GONE_ID));
        const m = mount();

        await resolutionSettled();

        expect(m.trigger).toHaveTextContent(PLACEHOLDER);
        expectNoAssetOn(m.trigger);
        expect(m.box.value).toBeNull();
        expect(
            m.writes.filter((write) => write.value !== null),
            'value was given an id nobody could confirm',
        ).toEqual([]);
        expect(control(m)).toHaveAttribute('data-benchmark-id', '');
        expect(control(m)).toHaveAttribute('data-benchmark-state', 'unknown');
        // A deleted asset and a list that did not load look the same from here, and SQLite
        // may reuse the id: neither is a reason to destroy what the reader stored.
        expect(riskBenchmark.assetId, 'the picker cleared the stored id').toBe(GONE_ID);
        expect(localStorage.getItem(keyFor(reader)), 'the picker cleared the stored key').toBe(String(GONE_ID));
    });
});

// ─── 2. What the list offers ────────────────────────────────────────────────────────────────

describe('BenchmarkSelect — what the list offers', () => {
    it('leaves out only what the page measures: benchmarks, held and inactive assets all stay on offer', async () => {
        returningReader(null);
        const m = mount({measured: [BOREALIS.id, DUNE.id]});
        await resolutionSettled();

        const listbox = await openList(m);

        expect(new Set(offeredIds(listbox))).toEqual(new Set([AURORA.id, COBALT.id, EMBER.id]));
    });

    it('offers everything when the page measures nothing', async () => {
        returningReader(null);
        const m = mount();
        await resolutionSettled();

        const listbox = await openList(m);

        expect(new Set(offeredIds(listbox))).toEqual(new Set(FIXTURE.map((asset) => asset.id)));
    });

    it('keeps the current choice listed and selectable even when the page measures it', async () => {
        returningReader(BOREALIS.id);
        const m = mount({measured: [BOREALIS.id, DUNE.id]});
        await waitFor(() => expect(m.box.value).toBe(BOREALIS.id));

        const listbox = await openList(m);

        expect(new Set(offeredIds(listbox))).toEqual(new Set([AURORA.id, BOREALIS.id, COBALT.id, EMBER.id]));
        expect(within(listbox).getByTestId(`search-select-option-${BOREALIS.id}`)).toBeEnabled();
    });

    it('lists the benchmarks first, under a title of their own, and the rest under another', async () => {
        returningReader(null);
        const m = mount();
        await resolutionSettled();

        const rows = rowsOf(await openList(m));
        const restTitle = rows.indexOf('title', 1);

        expect(rows[0], 'the list does not open on the benchmarks title').toBe('title');
        expect(restTitle, 'nothing separates the benchmarks from the rest').toBeGreaterThan(1);
        expect(new Set(rows.slice(1, restTitle))).toEqual(new Set(BENCHMARK_IDS));
        expect(new Set(rows.slice(restTitle + 1))).toEqual(new Set(OTHER_IDS));
        expect(rows.filter((row) => row === 'title')).toHaveLength(2);
    });
});

// ─── 3. A current choice the page itself measures ───────────────────────────────────────────

describe('BenchmarkSelect — a current choice the page itself measures', () => {
    it('is still shown, never swapped for the placeholder, and says it cannot be used here', async () => {
        returningReader(AURORA.id);
        const m = mount({measured: [AURORA.id], testid: ASSET_PAGE_TESTID});

        await waitFor(() => expect(m.box.value, 'value must still carry the measured choice').toBe(AURORA.id));
        expect(m.trigger).toHaveTextContent(AURORA.display_name);
        expect(m.trigger).not.toHaveTextContent(PLACEHOLDER);

        const marker = await screen.findByTestId(`${ASSET_PAGE_TESTID}-measured`);
        const wording = await wordingOf(marker);
        for (const fragment of expectedWording()) {
            expect(wording, `the marker does not carry ${MEASURED_KEY} in its text, its accessible name or its tooltip`).toContain(fragment);
        }
    });

    it('shows no marker when the current choice is not measured here', async () => {
        returningReader(AURORA.id);
        const m = mount({measured: [DUNE.id], testid: ASSET_PAGE_TESTID});

        await waitFor(() => expect(m.box.value).toBe(AURORA.id));
        await resolutionSettled();
        // Presence barrier: the choice is on screen, so the marker has had every chance to be.
        expect(m.trigger).toHaveTextContent(AURORA.display_name);

        expect(screen.queryByTestId(`${ASSET_PAGE_TESTID}-measured`)).toBeNull();
    });

    it('shows no marker when nothing is chosen', async () => {
        returningReader(null);
        const m = mount({measured: [AURORA.id], testid: ASSET_PAGE_TESTID});

        await resolutionSettled();
        expect(m.trigger).toHaveTextContent(PLACEHOLDER);

        expect(screen.queryByTestId(`${ASSET_PAGE_TESTID}-measured`)).toBeNull();
    });

    it('drops the marker as soon as the reader chooses something the page does not measure', async () => {
        returningReader(AURORA.id);
        const m = mount({measured: [AURORA.id], testid: ASSET_PAGE_TESTID});
        await screen.findByTestId(`${ASSET_PAGE_TESTID}-measured`);

        await choose(m, BOREALIS);

        await waitFor(() => expect(m.trigger).toHaveTextContent(BOREALIS.display_name));
        expect(screen.queryByTestId(`${ASSET_PAGE_TESTID}-measured`)).toBeNull();
    });

    it('follows the page when what it measures changes after mount', async () => {
        // The lab's selection moves under a mounted picker; the asset page's never does.
        returningReader(AURORA.id);
        const m = mount({measured: [], testid: ASSET_PAGE_TESTID});
        await waitFor(() => expect(m.box.value).toBe(AURORA.id));
        await resolutionSettled();
        expect(screen.queryByTestId(`${ASSET_PAGE_TESTID}-measured`)).toBeNull();

        m.box.measured = [AURORA.id, DUNE.id];
        await tick();

        expect(await screen.findByTestId(`${ASSET_PAGE_TESTID}-measured`)).toBeInTheDocument();
        expect(m.trigger).toHaveTextContent(AURORA.display_name);
        const listbox = await openList(m);
        expect(new Set(offeredIds(listbox))).toEqual(new Set([AURORA.id, BOREALIS.id, COBALT.id, EMBER.id]));
    });
});

// ─── 4. Choosing ────────────────────────────────────────────────────────────────────────────

describe('BenchmarkSelect — choosing', () => {
    it('writes the shared store before anyone hears of the choice', async () => {
        const reader = returningReader(AURORA.id);
        const m = mount();
        await waitFor(() => expect(m.box.value).toBe(AURORA.id));
        await resolutionSettled();
        // Whatever the mount did with onchange is not this test's subject; the choice is.
        m.onchange.mockClear();
        const heard: Array<{next: number | null; state: BenchmarkState; store: number | null; key: string | null; value: number | null}> = [];
        m.onchange.mockImplementation((next) => {
            heard.push({next, state: m.box.state, store: riskBenchmark.assetId, key: localStorage.getItem(keyFor(reader)), value: m.box.value});
        });

        await choose(m, DUNE);

        expect(m.onchange).toHaveBeenCalledExactlyOnceWith(DUNE.id);
        expect(heard[0], 'inside onchange the state, the store, its key and value must already hold the choice').toEqual({next: DUNE.id, state: 'set', store: DUNE.id, key: String(DUNE.id), value: DUNE.id});
        expect(riskBenchmark.assetId).toBe(DUNE.id);
        expect(localStorage.getItem(keyFor(reader))).toBe(String(DUNE.id));
        expect(m.box.value).toBe(DUNE.id);
        expect(m.trigger).toHaveTextContent(DUNE.display_name);
    });

    it('sets value only once the store already holds the choice', async () => {
        returningReader(AURORA.id);
        const m = mount();
        await waitFor(() => expect(m.box.value).toBe(AURORA.id));

        await choose(m, DUNE);

        const write = m.writes.find((candidate) => candidate.value === DUNE.id);
        if (!write) throw new Error('value never received the choice');
        expect(write.storeAtWrite, 'value moved before the shared store did').toBe(DUNE.id);
    });

    it('is the choice the next picker opens on, wherever it is mounted', async () => {
        returningReader(AURORA.id);
        const first = mount();
        await waitFor(() => expect(first.box.value).toBe(AURORA.id));
        await choose(first, COBALT);
        await waitFor(() => expect(first.box.value).toBe(COBALT.id));
        first.unmount();

        // Another surface, measuring something else: the Dashboard after the asset page, say.
        const second = mount({measured: [DUNE.id], testid: 'risk-l3-benchmark-select'});

        await waitFor(() => expect(second.box.value).toBe(COBALT.id));
        expect(second.trigger).toHaveTextContent(COBALT.display_name);
    });
});

// ─── 5. A choice made while the stored one is still being checked ───────────────────────────

describe('BenchmarkSelect — a choice made while the stored one is still being checked', () => {
    /**
     * Holds `ensureAssetsLoaded()` open, mounts, and reports whether the mount-time
     * resolution has answered — the barrier that makes these cases about a race at all.
     */
    async function mountWhileChecking(stored: number): Promise<{reader: string; m: Mounted; gate: {resolve: () => void}; answered: () => boolean}> {
        const gate = deferred();
        cache.gate = gate.promise;
        const reader = returningReader(stored);
        const m = mount();
        await waitFor(() => expect(resolveSpy(), 'the picker never asked resolveRiskBenchmark() for the shared choice').toHaveBeenCalled());
        let done = false;
        void Promise.resolve(resolveSpy().mock.results[0]?.value).finally(() => {
            done = true;
        });
        return {reader, m, gate, answered: () => done};
    }

    function expectChoiceHeld(m: Mounted, reader: string, asset: FixtureAsset): void {
        expect(m.box.value, 'the late check overwrote value').toBe(asset.id);
        expect(m.box.state, 'the late check overwrote the state').toBe('set');
        expect(m.trigger).toHaveTextContent(asset.display_name);
        expect(riskBenchmark.assetId, 'the late check overwrote the shared choice').toBe(asset.id);
        expect(localStorage.getItem(keyFor(reader)), 'the late check overwrote the stored choice').toBe(String(asset.id));
        expect(m.onchange, 'the page was last told about something other than the choice').toHaveBeenLastCalledWith(asset.id);
    }

    it("keeps the reader's choice when the late check confirms the stored benchmark", async () => {
        const {reader, m, gate, answered} = await mountWhileChecking(AURORA.id);

        await chooseByTyping(m, 'Dune');
        await waitFor(() => expect(m.onchange).toHaveBeenCalledWith(DUNE.id));
        expect(answered(), 'the check answered before the asset list was in: the race this case exists for never happened').toBe(false);

        gate.resolve();
        await resolutionSettled();

        expectChoiceHeld(m, reader, DUNE);
    });

    it("keeps the reader's choice when the late check finds the stored benchmark gone", async () => {
        const {reader, m, gate, answered} = await mountWhileChecking(GONE_ID);

        await chooseByTyping(m, 'Dune');
        await waitFor(() => expect(m.onchange).toHaveBeenCalledWith(DUNE.id));
        expect(answered(), 'the check answered before the asset list was in: the race this case exists for never happened').toBe(false);

        gate.resolve();
        await resolutionSettled();

        // Clearing the dead id must not clear what replaced it while the check was running.
        expectChoiceHeld(m, reader, DUNE);
    });
});

// ═══ Second round (01/10/2026): the approved visual design ═════════════════════════════════
//
// The root publishes the picker's state, so a page — and its E2E — reads attributes rather
// than an icon or a label: `${testid}-control` carries `data-benchmark-id` (the resolved
// value, '' when there is none) and `data-measured` ('true' | 'false'). The ⚠ is not a
// button: a keyboard can reach it (`tabindex="0"`), it is an image (`role="img"`), and its
// `aria-label` is the hint — `risk.benchmark.measuredHere` by default, or exactly the page's
// own already-translated `measuredHint`, which then replaces the default everywhere the
// warning speaks. Semantics are pinned; the icon and its colours are not.

// ─── 6. What it publishes on its root ───────────────────────────────────────────────────────

describe('BenchmarkSelect — what it publishes on its root', () => {
    it('wraps the picker in `${testid}-control`, publishing the resolved id and that it is not measured', async () => {
        returningReader(BOREALIS.id);
        const m = mount();
        await waitFor(() => expect(m.box.value).toBe(BOREALIS.id));
        await resolutionSettled();

        const root = control(m);
        expect(root, 'the picker must sit inside the root that publishes its state').toContainElement(m.root);
        expect(root).toHaveAttribute('data-benchmark-id', String(BOREALIS.id));
        expect(root).toHaveAttribute('data-measured', 'false');
    });

    it('publishes an empty id when nothing is stored', async () => {
        returningReader(null);
        const m = mount();
        await resolutionSettled();

        expect(control(m)).toHaveAttribute('data-benchmark-id', '');
        expect(control(m)).toHaveAttribute('data-measured', 'false');
    });

    it('publishes an empty id for a stored id it cannot confirm — the unconfirmed id is never published', async () => {
        const reader = returningReader(GONE_ID);
        const m = mount();
        await resolutionSettled();

        expect(control(m)).toHaveAttribute('data-benchmark-id', '');
        expect(control(m)).toHaveAttribute('data-measured', 'false');
        expect(localStorage.getItem(keyFor(reader)), 'publishing nothing is not clearing: the stored key must stay').toBe(String(GONE_ID));
    });

    it('publishes data-measured="true" when the page measures the current choice, with the warning inside the root', async () => {
        returningReader(AURORA.id);
        const m = mount({measured: [AURORA.id], testid: ASSET_PAGE_TESTID});
        const marker = await screen.findByTestId(`${ASSET_PAGE_TESTID}-measured`);

        // The asset page's root keeps the id it has today with SignalAssetParamControl.
        const root = screen.getByTestId('risk-comparison-asset-select-control');
        expect(root).toBe(control(m));
        expect(root).toHaveAttribute('data-benchmark-id', String(AURORA.id));
        expect(root).toHaveAttribute('data-measured', 'true');
        expect(root).toContainElement(marker);
    });

    it('moves both attributes with what the page measures and with what the reader chooses', async () => {
        returningReader(AURORA.id);
        const m = mount({measured: [], testid: ASSET_PAGE_TESTID});
        await waitFor(() => expect(control(m)).toHaveAttribute('data-benchmark-id', String(AURORA.id)));
        expect(control(m)).toHaveAttribute('data-measured', 'false');

        // The lab puts the benchmark into its own selection…
        m.box.measured = [AURORA.id];
        await tick();
        await waitFor(() => expect(control(m)).toHaveAttribute('data-measured', 'true'));

        // …and the reader answers by choosing something the page does not measure.
        await choose(m, BOREALIS);
        await waitFor(() => expect(control(m)).toHaveAttribute('data-benchmark-id', String(BOREALIS.id)));
        expect(control(m)).toHaveAttribute('data-measured', 'false');
    });

    it("publishes the reader's choice, not the late check's", async () => {
        const gate = deferred();
        cache.gate = gate.promise;
        returningReader(AURORA.id);
        const m = mount();
        await waitFor(() => expect(resolveSpy()).toHaveBeenCalled());
        let answered = false;
        void Promise.resolve(resolveSpy().mock.results[0]?.value).finally(() => {
            answered = true;
        });

        await chooseByTyping(m, 'Dune');
        await waitFor(() => expect(m.onchange).toHaveBeenCalledWith(DUNE.id));
        expect(answered, 'the check answered before the asset list was in: the race this case exists for never happened').toBe(false);
        gate.resolve();
        await resolutionSettled();

        expect(control(m)).toHaveAttribute('data-benchmark-id', String(DUNE.id));
        expect(control(m)).toHaveAttribute('data-benchmark-state', 'set');
    });
});

// ─── 7. The warning: an image a keyboard can reach, worded by the hint ──────────────────────

describe('BenchmarkSelect — the warning reads as an image worded by its hint', () => {
    it('ships a default hint that is a plain sentence, and a page hint that is not it', () => {
        // The default is compared as `$_(key)` with no values, which is only what renders
        // if the sentence takes none; and "the page hint replaces it" would be vacuous if
        // either string contained the other.
        const raw = at(en, MEASURED_KEY);
        expect(typeof raw, `${MEASURED_KEY} is missing from en.json`).toBe('string');
        expect(raw as string, `${MEASURED_KEY} takes arguments, so $_(key) alone is not what renders`).not.toContain('{');
        expect(defaultHint()).not.toContain(HINT);
        expect(HINT).not.toContain(defaultHint());
    });

    it('is not a button: focusable, an image, named by the default sentence', async () => {
        returningReader(AURORA.id);
        mount({measured: [AURORA.id], testid: ASSET_PAGE_TESTID});
        const marker = await screen.findByTestId(`${ASSET_PAGE_TESTID}-measured`);

        expect(marker.tagName, 'the warning is a button: it would read as an action that does something').not.toBe('BUTTON');
        expect(marker).toHaveAttribute('role', 'img');
        expect(marker).toHaveAttribute('tabindex', '0');
        // svelte-i18n echoes a missing key back, on both sides of the comparison below.
        expect(defaultHint(), `${MEASURED_KEY} does not resolve: the label would match a key with itself`).not.toBe(MEASURED_KEY);
        expect(marker).toHaveAttribute('aria-label', defaultHint());
        for (const tooltip of await tooltipsOpenedBy(marker)) {
            expect(tooltip, 'the warning opens a tooltip that says something else').toBe(defaultHint());
        }
    });

    it('words itself with measuredHint exactly when the page gives one, and the default never shows', async () => {
        returningReader(AURORA.id);
        mount({measured: [AURORA.id], testid: ASSET_PAGE_TESTID, hint: HINT});
        const marker = await screen.findByTestId(`${ASSET_PAGE_TESTID}-measured`);

        expect(marker).toHaveAttribute('role', 'img');
        expect(marker).toHaveAttribute('tabindex', '0');
        expect(marker).toHaveAttribute('aria-label', HINT);
        const tooltips = await tooltipsOpenedBy(marker);
        for (const tooltip of tooltips) {
            expect(tooltip, 'the warning opens a tooltip that is not the page hint').toBe(normalize(HINT));
        }
        expect([inlineWordingOf(marker), ...tooltips].join(' '), 'the default sentence still shows beside the page hint').not.toContain(defaultHint());
    });
});

// ═══ Third round (01/10/2026): the resolution state ═════════════════════════════════════════
//
// An id that cannot be confirmed is no longer cleared — `ensureLoaded()` resolves even when
// the load fails, so "gone" and "not loaded" look alike, and SQLite may reuse a deleted id —
// so the picker says how far it got instead: `state`, bindable, published as
// `data-benchmark-state` on the root. `none` at once when nothing is stored; `pending` from
// the first instant an id is stored until its check settles; then `set` or `unknown`.

// ─── 8. The resolution state ────────────────────────────────────────────────────────────────

describe('BenchmarkSelect — the resolution state it publishes', () => {
    /** Hold `ensureAssetsLoaded()` open, so the check of a stored id cannot settle until released. */
    function holdTheList(): {resolve: () => void} {
        const gate = deferred();
        cache.gate = gate.promise;
        return gate;
    }

    /** The bound prop and the root attribute say the same thing. */
    function expectState(m: Mounted, state: BenchmarkState, message?: string): void {
        expect(control(m), message).toHaveAttribute('data-benchmark-state', state);
        expect(m.box.state, message).toBe(state);
    }

    it('is none straight away when nothing is stored, and never pending', async () => {
        returningReader(null);
        const m = mount();

        // `render()` flushes before returning: this is the first thing a page can read.
        expectState(m, 'none', 'nothing is stored: there is nothing to wait for');
        await resolutionSettled();

        expectState(m, 'none');
        expect(m.states, 'pending is for a stored id whose check has not settled, and nothing was stored').not.toContain('pending');
    });

    it('goes pending → set for a stored id the list confirms', async () => {
        const list = holdTheList();
        returningReader(BOREALIS.id);
        const m = mount();

        expectState(m, 'pending', 'an id is stored and its check has not settled: the first word is pending, never none');
        await tick();
        expectState(m, 'pending', 'pending gave way while the asset list was still held');

        list.resolve();
        await resolutionSettled();

        expectState(m, 'set');
        expect(transitions(m.states)).toEqual(['pending', 'set']);
        expect(control(m)).toHaveAttribute('data-benchmark-id', String(BOREALIS.id));
        expect(m.box.value).toBe(BOREALIS.id);
    });

    it('publishes no id while pending, even one the list goes on to confirm: value null, data-benchmark-id empty, no asset on the trigger', async () => {
        // Rule 10. A page that measures only once the state is `set` and a page that reads
        // `value` agree only because nothing is handed out while the check runs. BOREALIS is
        // in the list, so the check will confirm it: what is pinned is the window, not a
        // refusal — the id arrives, with `set` and not before.
        const list = holdTheList();
        returningReader(BOREALIS.id);
        const m = mount();

        /** Every channel a page reads the choice through, still empty. */
        function expectNothingPublished(moment: string): void {
            expect(m.box.value, `${moment}: value holds an id the list has not confirmed`).toBeNull();
            expect(control(m), `${moment}: the root publishes an id the list has not confirmed`).toHaveAttribute('data-benchmark-id', '');
            expect(
                m.writes.filter((write) => write.value !== null),
                `${moment}: value was handed an id the list has not confirmed, if only for an instant`,
            ).toEqual([]);
            expectNoAssetOn(m.trigger);
        }

        // `render()` flushes before returning: this is the first thing a page can read.
        expectState(m, 'pending', 'an id is stored and its check has not settled: the window this case is about');
        expectNothingPublished('at mount');

        await tick();
        expect(resolveSpy(), 'the check never started: there was no window to hold open').toHaveBeenCalled();
        expectState(m, 'pending', 'pending gave way while the asset list was still held');
        expectNothingPublished('a tick later, with the check under way');

        list.resolve();
        await resolutionSettled();

        // The presence barrier for every absence above: the same id reaches the same
        // channels as soon as the list confirms it.
        expectState(m, 'set');
        expect(m.box.value).toBe(BOREALIS.id);
        expect(control(m)).toHaveAttribute('data-benchmark-id', String(BOREALIS.id));
        expect(m.trigger).toHaveTextContent(BOREALIS.display_name);
    });

    it('goes pending → unknown for a stored id the list does not hold, and leaves it stored', async () => {
        const list = holdTheList();
        const reader = returningReader(GONE_ID);
        const m = mount();

        expectState(m, 'pending', 'an id is stored and its check has not settled: the first word is pending, never none');
        await tick();
        expectState(m, 'pending', 'pending gave way while the asset list was still held');

        list.resolve();
        await resolutionSettled();

        expectState(m, 'unknown');
        expect(transitions(m.states)).toEqual(['pending', 'unknown']);
        expect(control(m)).toHaveAttribute('data-benchmark-id', '');
        expect(m.box.value).toBeNull();
        expect(m.trigger).toHaveTextContent(PLACEHOLDER);
        expect(riskBenchmark.assetId, 'unknown is a reading, not a verdict: the stored id must stay').toBe(GONE_ID);
        expect(localStorage.getItem(keyFor(reader))).toBe(String(GONE_ID));
    });

    it('reads a failed asset-list load as unknown, and keeps the stored id', async () => {
        // The list never arrived: the cache knows nothing, and the load rejects for the
        // picker's own list too — the case where "gone" and "not loaded" cannot be told apart.
        cache.entries = [];
        cache.failure = new Error('synthetic: asset list unreachable');
        const reader = returningReader(BOREALIS.id);
        const m = mount();

        await resolutionSettled();

        expectState(m, 'unknown');
        expect(control(m)).toHaveAttribute('data-benchmark-id', '');
        expect(m.box.value).toBeNull();
        expect(riskBenchmark.assetId, 'a failed request cost the reader their stored choice').toBe(BOREALIS.id);
        expect(localStorage.getItem(keyFor(reader))).toBe(String(BOREALIS.id));
    });

    it('turns a choice made from unknown into set — state, store and value — before onchange hears of it', async () => {
        const reader = returningReader(GONE_ID);
        const m = mount();
        await resolutionSettled();
        expectState(m, 'unknown');
        m.onchange.mockClear();
        const heard: Array<{next: number | null; state: BenchmarkState; store: number | null; value: number | null}> = [];
        m.onchange.mockImplementation((next) => {
            heard.push({next, state: m.box.state, store: riskBenchmark.assetId, value: m.box.value});
        });

        await choose(m, DUNE);

        expect(m.onchange).toHaveBeenCalledExactlyOnceWith(DUNE.id);
        expect(heard[0], 'inside onchange the state, the store and value must already hold the choice').toEqual({next: DUNE.id, state: 'set', store: DUNE.id, value: DUNE.id});
        expectState(m, 'set');
        expect(control(m)).toHaveAttribute('data-benchmark-id', String(DUNE.id));
        expect(localStorage.getItem(keyFor(reader))).toBe(String(DUNE.id));
    });

    it('keeps a choice made while pending as set when the late check answers unknown', async () => {
        // The race of section 5, read through the state: the late `unknown` must not
        // overwrite the choice's `set`, nor the id the root publishes.
        const list = holdTheList();
        const reader = returningReader(GONE_ID);
        const m = mount();
        expectState(m, 'pending');

        await chooseByTyping(m, 'Dune');
        await waitFor(() => expect(m.onchange).toHaveBeenCalledWith(DUNE.id));
        expectState(m, 'set', 'a choice is set at once, even while the stored id is still being checked');

        list.resolve();
        await resolutionSettled();

        expectState(m, 'set', 'the late check overwrote the state of a choice made after it began');
        expect(control(m)).toHaveAttribute('data-benchmark-id', String(DUNE.id));
        expect(m.box.value).toBe(DUNE.id);
        expect(riskBenchmark.assetId).toBe(DUNE.id);
        expect(localStorage.getItem(keyFor(reader))).toBe(String(DUNE.id));
    });
});
