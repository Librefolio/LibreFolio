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
 *      neither can measure against an id nobody confirmed. (Pinned for the check against
 *      the asset list; the wait for a verdict, round four, is not pinned here — see below.)
 *
 * Fourth round (06/10/2026), stage 2: the picker moves onto F's shared asset picker panel
 * (`AssetPickerPanel mode="single"`, which keeps `SearchSelect`'s test ids, so every case
 * above reads the ids it always read) and learns the engine's eligibility — D371 for the
 * lab, D378 for every page:
 *
 *  11. **What stays as it was is pinned as well**: each section in `assetSelectOrder`'s
 *      order (active first, then by name) whatever order the cache holds — the panel never
 *      sorts, so the picker must — the section titles' test ids, and `${testid}-load-error`.
 *  12. **Where the verdicts come from**, published as `data-eligibility` on the root:
 *      - `verdicts` given (the lab's way): used as they are, nothing asked — `given`;
 *      - a `period` and a `currency` and no verdicts: one `queryEligibility` 300 ms after
 *        mounting, about the catalogue it offers (the current choice included, what the page
 *        measures left out), worded by `describeEligibility` — `pending` while it waits,
 *        then `ready`; a rejected request reads `failed`, rules nothing out and is logged; a
 *        new period or currency asks again after the same debounce, an answer to an older
 *        question is ignored, and a remount on the same question is answered by the store's
 *        cache, not by the engine; a `null` — the store's word for an answer it discarded,
 *        its cache emptied while the question was in flight — is no answer: still `pending`,
 *        the same question again after the same debounce, settled by the next answer;
 *      - neither: nothing asked, nothing ruled out — `none`, as before.
 *  13. **A ruled-out asset is listed apart and never chosen**: in `${testid}-blocked`, titled
 *      by `risk.benchmark.blocked`, disabled, with the engine's codes in `data-reasons`. A
 *      warning leaves an asset selectable, with the panel's ⚠; no verdict means selectable.
 *  14. **A current choice the engine rules out is `blocked`** (D378): `value` keeps the id,
 *      the trigger still shows it, the blocked section marks it current, and the shared store
 *      keeps it — `resolveRiskBenchmark()` still reads it `set`, never `blocked`. With given
 *      verdicts the state follows the map at once; with a period a stored choice stays
 *      `pending` until its verdict for that period and currency is in — a `null` from the
 *      store is not one — and again after a new period; a failed request makes it `set`,
 *      because a failure locks nothing. Never `set` on the way to `blocked`: a page
 *      compares only on `set`, and would have asked once. Choosing an asset that can be
 *      chosen is `set`, as always.
 *
 * Not pinned, on purpose: whether `onchange` also fires when the mount-time resolution
 * lands (the contract does not say), what the trigger says while the state is `pending`
 * beyond showing no asset, and clearing — the picker has no control that empties a
 * choice, so there is nothing for a reader to press. From round four: what `value`,
 * `data-benchmark-id` and the trigger hold while a confirmed choice waits for its verdict
 * (rule 10 speaks of the list's check), and a choice made while the verdicts are still on
 * their way.
 *
 * Observed only through what a page can see: `data-testid`s, the bound `value` (held in
 * a `$state` behind a getter/setter, as a parent's `bind:value` would hold it), the
 * `onchange` payload, the shared store and its storage key — and, from round four, the
 * question the picker puts to the store and what reaches the engine. Asset names are this
 * file's own fixture and the placeholder is a prop it passes in; the sentences that matter
 * are resolved from the shipped catalogue through the same `$_` the component uses, so no
 * translated text is written down here.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import {tick} from 'svelte';
import {get} from 'svelte/store';

// The shared `$app/environment` mock reports `browser: false`, which turns every storage
// path of the benchmark store into a no-op — and "the choice reaches the shared key" is
// half of what this file pins. Same override as `riskBenchmarkStore.test.ts`, with every
// export spelled out because the component tree imports more of this module than the
// store does.
vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));

/**
 * This jsdom build exposes no `localStorage` at all (see `DataTable.test.ts`), and the
 * shared key is half of what this file pins: a Map-backed stand-in, as in
 * `riskBenchmarkStore.test.ts`, fresh for every case (`beforeEach`). Installed here too,
 * before anything is imported: with `browser: true` above, a module that reads storage
 * while it loads — the language store the shared asset panel imports does — would
 * otherwise throw before any case runs, and fail the whole file for a reason that is the
 * harness's, not the picker's.
 */
const storage = vi.hoisted(() => {
    function install(): void {
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
    }
    install();
    return {install};
});

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
        // A fresh array each call, as the real store re-derives one: whoever orders it — in
        // place, as `AssetSelect` did, or through `assetSelectOrder` — leaves the cache as it was.
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

/**
 * Round four. The eligibility engine, owned by this file: the generated client's call,
 * answered per case (`engineAnswers`, `engineHolds`). The rest of `$lib/api` is the real one.
 */
const engine = vi.hoisted(() => ({api: vi.fn()}));

vi.mock('$lib/api', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/api')>();
    return {...actual, zodiosApi: {...actual.zodiosApi, asset_eligibility_api_v1_risk_eligibility_post: engine.api}};
});

/** The panel's currency menu puts flags beside the codes, from the currency cache: kept empty, and off the network. */
vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    ensureCurrenciesLoaded: vi.fn(async () => {}),
}));

/**
 * The real risk store, with a spy on `queryEligibility`: the question the picker puts to the
 * store, between it and the engine above. Through to the real function, so its cache is the
 * one a remount meets. Until stage 2 lands the store has no such export, and the spy says so
 * if anything calls it.
 */
vi.mock('$lib/stores/risk/riskStore.svelte', async (importOriginal) => {
    const actual = await importOriginal<Record<string, unknown>>();
    return {
        ...actual,
        queryEligibility: vi.fn((...args: unknown[]) => {
            if (typeof actual.queryEligibility !== 'function') throw new Error('riskStore exports no queryEligibility: stage 2 has not landed');
            return (actual.queryEligibility as (...forwarded: unknown[]) => unknown)(...args);
        }),
    };
});

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {reactiveBox} from '$test/runes.svelte';
import {schemas} from '$lib/api';
import {dayFormatter, describeEligibility, mergeEligibilityAnswers, type AssetEligibilityItem, type EligibilityVerdicts} from '$lib/components/risk/eligibility';
import {assetSelectOrder, type PickerVerdict} from '$lib/components/ui/select/assetPicker';
import {_} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import {transitionClientSession} from '$lib/stores/app/clientSession';
import {ensureAssetsLoaded} from '$lib/stores/reference/assetStore';
import {resolveRiskBenchmark, riskBenchmark} from '$lib/stores/risk/riskBenchmarkStore.svelte';
import * as riskStore from '$lib/stores/risk/riskStore.svelte';
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

// ─── Fixture, round four: the engine's eligibility ──────────────────────────────────────────

const ALL_IDS = FIXTURE.map((asset) => asset.id).sort((left, right) => left - right);
/** The title of the section of ruled-out assets: a new key, which the product ships in four catalogues. */
const BLOCKED_KEY = 'risk.benchmark.blocked';
/** Two windows a page can be on, and its target currency. */
const P1 = {start: '2025-01-01', end: '2025-12-31'};
const P2 = {start: '2025-04-01', end: '2025-12-31'};
const CURRENCY = 'EUR';
/** A translation key that reached the screen untranslated: `scope.key`, no space anywhere. */
const RAW_KEY = /^[\w-]+(\.[\w-]+)+$/;

type EngineVerdict = Pick<AssetEligibilityItem, 'level' | 'reasons'>;
const ADMITTED: EngineVerdict = {level: 'eligible', reasons: []};
/** Ruled out for two reasons whose sentences carry no date: worded alike whatever the reader's locale does to days. */
const NO_PRICES: EngineVerdict = {level: 'ineligible', reasons: ['no_prices', 'missing_fx']};
const LATE_START: EngineVerdict = {level: 'warning', reasons: ['starts_late']};

/** The engine's view of the fixture for a page's period: BOREALIS has no prices in it, DUNE starts late, the rest are admitted. */
function engineView(assetId: number): EngineVerdict {
    if (assetId === BOREALIS.id) return NO_PRICES;
    if (assetId === DUNE.id) return LATE_START;
    return ADMITTED;
}

/** Texts the lab hands in with its verdicts: this file's own strings, compared as given. */
const GIVEN_TEXTS = {blocked: ['probe-blocked: no prices in the lab period'], warning: ['probe-warning: first quote after the start']};
const RULED_OUT: PickerVerdict = {level: 'ineligible', codes: ['no_prices'], texts: GIVEN_TEXTS.blocked};
const ADMITTED_VERDICT: PickerVerdict = {level: 'eligible', codes: [], texts: []};

/** The lab's way: verdicts already worded. BOREALIS ruled out, DUNE warned about, COBALT and EMBER without a verdict. */
function givenVerdicts(): Map<number, PickerVerdict> {
    return new Map<number, PickerVerdict>([
        [AURORA.id, ADMITTED_VERDICT],
        [BOREALIS.id, RULED_OUT],
        [DUNE.id, {level: 'warning', codes: ['starts_late'], texts: GIVEN_TEXTS.warning}],
    ]);
}

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

/** The resolution state the picker publishes (third round), and `blocked` (fourth round, D378). */
type BenchmarkState = 'none' | 'pending' | 'set' | 'unknown' | 'blocked';

type Period = {start: string; end: string};

/** The parent's state: what `bind:value`, `bind:state` and the page's own props would hold. */
interface ParentState {
    value: number | null;
    measured: number[];
    state: BenchmarkState;
    /** Round four: verdicts already worded (the lab's way)… */
    verdicts?: ReadonlyMap<number, PickerVerdict>;
    /** …or the page's window and target currency, which make the picker ask the engine. */
    period?: Period;
    currency?: string;
}

interface MountOptions {
    measured?: number[];
    testid?: string;
    hint?: string;
    verdicts?: ReadonlyMap<number, PickerVerdict>;
    period?: Period;
    currency?: string;
}

interface Mounted {
    /** The parent's state: what `bind:value`, `bind:state` and the page's props would hold. */
    box: ParentState;
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
 * runs; so does `hint`, which becomes `measuredHint` when given. Round four's `verdicts`,
 * `period` and `currency` are read from the parent's state the same way, and only when
 * given: a picker mounted without them has neither, which is a case of its own.
 *
 * The parent's `state` starts at `'none'`, as a page's `$state('none')` would, and not
 * `undefined`: binding `undefined` to a prop that declares a fallback is a Svelte error
 * (`props_invalid_value`), so a picker written `state = $bindable('none')` would refuse
 * to mount for a reason that is the harness's, not the picker's.
 */
function mount(options: MountOptions = {}): Mounted {
    const box = reactiveBox<ParentState>({value: null, measured: options.measured ?? [], state: 'none', verdicts: options.verdicts, period: options.period, currency: options.currency});
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
    for (const key of ['verdicts', 'period', 'currency'] as const) {
        if (options[key] !== undefined) Object.defineProperty(props, key, {enumerable: true, configurable: true, get: () => box[key]});
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

/** Open the list and wait for it to fill: the picker may still be loading its catalogue from the cache. */
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
 * Choose by typing and Enter. The picker keeps its search box live while its list may still
 * read "loading", and Enter picks from what the search shows — the one way a reader can beat
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

// ─── Helpers, round four ────────────────────────────────────────────────────────────────────

type QueryEligibility = (assetIds: readonly number[], period: Period, currency: string) => Promise<EligibilityVerdicts | null>;

/**
 * The question the picker puts to the store, through the spy installed above. Read through
 * the namespace: the export does not exist before stage 2, and a named import would fail the
 * type check instead of the cases that are about it.
 */
function eligibilitySpy(): Mock<QueryEligibility> {
    return (riskStore as unknown as {queryEligibility: Mock<QueryEligibility>}).queryEligibility;
}

/** Each question the picker asked the store: the ids (once each, sorted), the period and the currency. */
function questions(): Array<{ids: number[]; period: unknown; currency: unknown}> {
    return eligibilitySpy().mock.calls.map(([ids, period, currency]) => ({ids: [...new Set(ids)].sort((left, right) => left - right), period, currency}));
}

interface EligibilityBody {
    asset_ids: number[];
    date_range: {start: string; end?: string | null};
    target_currency: string;
}

/** The engine's answer to one request: a verdict for exactly the ids asked, through the generated schema the client validates against. */
function engineAnswer(assetIds: readonly number[], verdictFor: (assetId: number) => EngineVerdict = engineView) {
    return schemas.RiskEligibilityResponse.parse({
        items: assetIds.map((assetId) => {
            const verdict = verdictFor(assetId);
            // An asset with no quote in the period has no first or last one to report either.
            const quoted = !(verdict.reasons ?? []).includes('no_prices');
            return {
                asset_id: assetId,
                level: verdict.level,
                reasons: [...(verdict.reasons ?? [])],
                first_quote: quoted ? '2025-02-03' : null,
                last_quote: quoted ? '2025-12-30' : null,
                quotes_in_period: quoted ? 220 : 0,
            };
        }),
        min_quotes: 20,
        stale_days: 7,
    });
}

/** The engine answers every request at once. */
function engineAnswers(verdictFor: (assetId: number) => EngineVerdict = engineView): void {
    engine.api.mockImplementation(async (body: EligibilityBody) => engineAnswer(body.asset_ids, verdictFor));
}

interface HeldRequest {
    body: EligibilityBody;
    answer: (verdictFor?: (assetId: number) => EngineVerdict) => void;
}

/** The engine keeps every request until the case answers it, so "while it asks" is a state, not a race. */
function engineHolds(): HeldRequest[] {
    const held: HeldRequest[] = [];
    engine.api.mockImplementation(
        (body: EligibilityBody) =>
            new Promise((resolve) => {
                held.push({body, answer: (verdictFor = engineView) => resolve(engineAnswer(body.asset_ids, verdictFor))});
            }),
    );
    return held;
}

/**
 * The sentences the reader must find for `assetId`, worded by `describeEligibility` from the
 * engine's answer through the `$_` the component uses. The reasons in this fixture carry no
 * date, so the formatter's locale cannot change a sentence.
 */
function engineSentences(assetId: number): string[] {
    const verdicts = mergeEligibilityAnswers([engineAnswer([assetId])]);
    const item = verdicts.items.get(assetId);
    if (!item) throw new Error(`the fixture engine gave #${assetId} no verdict`);
    const translate = (key: string, options?: {values?: Record<string, string | number>}): string => get(_)(key, options);
    return [...describeEligibility(item, verdicts, CURRENCY, translate, dayFormatter('en')).texts];
}

/**
 * The picker's clock, faked: the debounce is 300 ms of it, so "not yet" and "now" are facts
 * and not bets on the machine. `Date` with it, for the panel's guard against reopening within
 * 200 ms of a close. With it on, nothing may `waitFor`: that would wait on this clock.
 */
function fakeClock(): void {
    vi.useFakeTimers({toFake: ['setTimeout', 'clearTimeout', 'Date']});
}

/** Every promise the picker started has answered and the DOM has caught up, with no time passing. */
async function settle(): Promise<void> {
    for (let round = 0; round < 3; round += 1) {
        await vi.advanceTimersByTimeAsync(0);
        await tick();
    }
}

/** `ms` of the picker's clock go by, then everything settles. */
async function elapse(ms: number): Promise<void> {
    await vi.advanceTimersByTimeAsync(ms);
    await settle();
}

/** Open the list with the clock faked: one click on a closed picker, then the list as it stands. */
async function openNow(m: Mounted): Promise<HTMLElement> {
    await fireEvent.click(m.trigger);
    return within(m.root).getByRole('listbox');
}

/** The section of ruled-out assets, inside this picker. */
function blockedSection(m: Mounted): HTMLElement {
    return within(m.root).getByTestId(`${m.testid}-blocked`);
}

function optionOf(container: HTMLElement, assetId: number): HTMLElement {
    return within(container).getByTestId(`search-select-option-${assetId}`);
}

/** `risk.benchmark.blocked` as the component resolves it. */
function blockedTitle(): string {
    return get(_)(BLOCKED_KEY);
}

/** The bound prop and the root attribute say the same thing. */
function expectPublished(m: Mounted, state: BenchmarkState, message?: string): void {
    expect(control(m), message).toHaveAttribute('data-benchmark-state', state);
    expect(m.box.state, message).toBe(state);
}

beforeAll(async () => {
    await setupI18n('en');
});

afterEach(() => {
    vi.useRealTimers();
});

beforeEach(() => {
    // A fresh stand-in for every case (see `storage` above).
    storage.install();
    cache.entries = FIXTURE.map((asset) => ({...asset}));
    cache.gate = null;
    cache.failure = null;
    resolveSpy().mockClear();
    vi.mocked(ensureAssetsLoaded).mockClear();
    // Round four: an engine that answers at once unless a case says otherwise, a spy with no
    // history, and a store that remembers no answer a neighbouring case got.
    engine.api.mockReset();
    engineAnswers();
    eligibilitySpy().mockClear();
    riskStore.invalidateRisk();
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

// ═══ Fourth round (06/10/2026), stage 2: on the shared panel, with the engine's eligibility ══
//
// `BenchmarkSelect` mounts F's `AssetPickerPanel` (`mode="single"`) in place of `AssetSelect`,
// and D378 makes the one picker the same on every page: the assets the engine cannot measure in
// the page's period are listed apart, read-only, with the engine's reasons; a stored benchmark it
// cannot measure is kept but published `blocked`, and pages compare only on `set`. The verdicts
// come from the page (`verdicts`, the lab's way) or from the engine, through the store's
// `queryEligibility`, when the page hands in a `period` and a `currency`. Cases with a debounce
// run on a faked clock (`fakeClock`), where nothing may `waitFor`.

// ─── 9. The harness, round four ─────────────────────────────────────────────────────────────

describe('BenchmarkSelect — the harness, round four', () => {
    it('owns an engine view and given verdicts where every rule has something to act on', () => {
        // A ruled-out benchmark beside an admitted one: the «Benchmark» section loses one and keeps one.
        expect([AURORA.is_benchmark, BOREALIS.is_benchmark]).toEqual([true, true]);
        expect(engineView(BOREALIS.id).level).toBe('ineligible');
        expect(engineView(AURORA.id).level).toBe('eligible');
        expect(engineView(DUNE.id).level, 'a warning, which must leave its asset selectable').toBe('warning');
        // The lab's verdicts rule out the same benchmark and leave two assets with none.
        expect(givenVerdicts().get(BOREALIS.id)?.level).toBe('ineligible');
        expect(FIXTURE.filter((asset) => !givenVerdicts().has(asset.id)).map((asset) => asset.id)).toEqual([COBALT.id, EMBER.id]);
        expect(P1).not.toEqual(P2);
    });

    it('words the ruled-out benchmark in sentences from the shipped catalogue, one per reason, never a key', () => {
        const sentences = engineSentences(BOREALIS.id);
        expect(sentences).toHaveLength((NO_PRICES.reasons ?? []).length);
        for (const sentence of sentences) expect(sentence).not.toMatch(RAW_KEY);
    });
});

// ─── 10. What stays as it was ───────────────────────────────────────────────────────────────

describe('BenchmarkSelect — on the shared panel, what stays as it was', () => {
    it('orders each section as AssetSelect did — active assets first, then by name — whatever order the cache holds', async () => {
        // The panel shows the order it is given and never sorts: the picker must.
        /** Inactive, and first by name: only "active first" puts it after DUNE. */
        const AMBER = {id: 204, display_name: 'Amber Retired Fund', currency: 'EUR', asset_type: 'FUND', active: false, is_benchmark: false, tx_count_own: 0};
        cache.entries = [DUNE, EMBER, BOREALIS, AMBER, COBALT, AURORA].map((asset) => ({...asset}));
        returningReader(null);
        const m = mount();
        await resolutionSettled();

        const rows = rowsOf(await openList(m));

        // The order written out below is assetSelectOrder's, section by section.
        expect(assetSelectOrder([BOREALIS, AURORA]).map((asset) => asset.id)).toEqual([AURORA.id, BOREALIS.id]);
        expect(assetSelectOrder([DUNE, EMBER, AMBER, COBALT]).map((asset) => asset.id)).toEqual([COBALT.id, DUNE.id, AMBER.id, EMBER.id]);
        expect(rows).toEqual(['title', AURORA.id, BOREALIS.id, 'title', COBALT.id, DUNE.id, AMBER.id, EMBER.id]);
    });

    it('titles the benchmarks and the rest with the section test ids it has always had', async () => {
        returningReader(null);
        const m = mount();
        await resolutionSettled();

        const listbox = await openList(m);

        const titles = Array.from(listbox.querySelectorAll<HTMLElement>('[data-testid^="search-select-header-"]')).map((title) => title.getAttribute('data-testid'));
        expect(titles).toEqual(['search-select-header-__section:benchmark', 'search-select-header-__section:__rest']);
    });

    it('says under `${testid}-load-error`, inside its root, that the asset list could not be loaded', async () => {
        cache.entries = [];
        cache.failure = new Error('synthetic: asset list unreachable');
        returningReader(null);
        const m = mount({testid: ASSET_PAGE_TESTID});

        const message = await screen.findByTestId(`${ASSET_PAGE_TESTID}-load-error`);
        expect(control(m)).toContainElement(message);
    });
});

// ─── 11. The title of the section apart ─────────────────────────────────────────────────────

describe('BenchmarkSelect — the title of the section of ruled-out assets', () => {
    it.each(Object.keys(CATALOGUES) as (keyof typeof CATALOGUES)[])(`ships ${BLOCKED_KEY} in %s.json`, (locale) => {
        const sentence = at(CATALOGUES[locale], BLOCKED_KEY);
        expect(typeof sentence, `${BLOCKED_KEY} is missing from ${locale}.json: the assets the engine rules out would sit under no title`).toBe('string');
        expect(normalize(sentence as string)).not.toBe('');
    });

    it(`resolves ${BLOCKED_KEY} through the $_ the component uses`, () => {
        // svelte-i18n echoes a missing id back: the section would be titled with its own key.
        expect(blockedTitle(), `${BLOCKED_KEY} does not resolve: the catalogue is not loaded or the key is missing`).not.toBe(BLOCKED_KEY);
    });
});

// ─── 12. Where the verdicts come from ───────────────────────────────────────────────────────

describe('BenchmarkSelect — where the verdicts come from', () => {
    beforeEach(() => {
        fakeClock();
    });

    it('asks nothing and rules nothing out with neither verdicts nor a period: data-eligibility="none"', async () => {
        returningReader(null);
        const m = mount();
        await settle();
        await elapse(1_000);

        expect(control(m), 'the root does not say where its verdicts come from').toHaveAttribute('data-eligibility', 'none');
        expect(eligibilitySpy(), 'a picker with no period asked the store').not.toHaveBeenCalled();
        expect(engine.api).not.toHaveBeenCalled();
        const listbox = await openNow(m);
        expect(new Set(offeredIds(listbox))).toEqual(new Set(ALL_IDS));
        for (const id of ALL_IDS) expect(optionOf(listbox, id)).toBeEnabled();
        expect(within(m.root).queryByTestId(`${m.testid}-blocked`)).toBeNull();
    });

    it.each<[string, Pick<MountOptions, 'period' | 'currency'>]>([
        ['alone', {}],
        ['beside a period and a currency', {period: P1, currency: CURRENCY}],
    ])('takes the verdicts it is given as they are, %s, and asks nothing: data-eligibility="given"', async (_label, extra) => {
        returningReader(null);
        const m = mount({verdicts: givenVerdicts(), ...extra});
        await settle();
        await elapse(1_000);

        expect(control(m), 'the root does not say its verdicts were given').toHaveAttribute('data-eligibility', 'given');
        expect(eligibilitySpy(), 'the picker asked the store although the page handed it verdicts').not.toHaveBeenCalled();
        expect(engine.api, 'the engine was asked although the page handed the picker its verdicts').not.toHaveBeenCalled();
    });

    it('lists a ruled-out asset apart, under its title, disabled and with its reasons; a warning or no verdict stays selectable', async () => {
        returningReader(null);
        const m = mount({verdicts: givenVerdicts()});
        await settle();

        const listbox = await openNow(m);
        const blocked = blockedSection(m);
        expect(
            within(blocked)
                .queryAllByTestId(/^search-select-option-\d+$/)
                .map(idOf),
            'the section apart lists what the verdicts rule out, and only that',
        ).toEqual([BOREALIS.id]);
        const borealis = optionOf(blocked, BOREALIS.id);
        expect(borealis).toBeDisabled();
        expect(borealis).toHaveAttribute('data-level', 'ineligible');
        expect(borealis).toHaveAttribute('data-reasons', 'no_prices');
        for (const text of GIVEN_TEXTS.blocked) expect(borealis, 'the given verdict is not shown as given').toHaveTextContent(text);
        expect(blockedTitle(), `${BLOCKED_KEY} does not resolve`).not.toBe(BLOCKED_KEY);
        expect(blocked, `the section apart is not titled by ${BLOCKED_KEY}`).toHaveAccessibleName(blockedTitle());

        for (const id of [AURORA.id, DUNE.id, COBALT.id, EMBER.id]) {
            const option = optionOf(listbox, id);
            expect(blocked, `#${id} is listed apart`).not.toContainElement(option);
            expect(option, `#${id} cannot be chosen`).toBeEnabled();
        }
        expect(within(optionOf(listbox, DUNE.id)).getByTestId(`${m.testid}-warning-${DUNE.id}`), 'a warned asset does not carry the panel’s ⚠').toBeInTheDocument();
    });

    it('refuses a ruled-out asset, and takes a warned one', async () => {
        const reader = returningReader(null);
        const m = mount({verdicts: givenVerdicts()});
        await settle();

        await openNow(m);
        await fireEvent.click(optionOf(blockedSection(m), BOREALIS.id));
        expect(m.onchange, 'a ruled-out asset was chosen').not.toHaveBeenCalled();
        expect(riskBenchmark.assetId).toBeNull();
        expectPublished(m, 'none');

        // A refused click leaves the list open: the warned asset is chosen from the same list.
        await fireEvent.click(optionOf(m.root, DUNE.id));
        expect(m.onchange).toHaveBeenCalledExactlyOnceWith(DUNE.id);
        expectPublished(m, 'set');
        expect(localStorage.getItem(keyFor(reader))).toBe(String(DUNE.id));
    });

    it('asks the store once, 300 ms after mounting, about the catalogue it offers, with the page’s period and currency', async () => {
        returningReader(null);
        mount({period: P1, currency: CURRENCY, measured: [DUNE.id]});
        await settle();

        await elapse(299);
        expect(eligibilitySpy(), 'the question left before the 300 ms debounce was over').not.toHaveBeenCalled();
        await elapse(1);
        expect(eligibilitySpy(), 'no queryEligibility 300 ms after mounting with a period and a currency').toHaveBeenCalledTimes(1);
        expect(questions()[0], 'not the question of the catalogue on offer, for the page’s period and currency').toEqual({ids: [AURORA.id, BOREALIS.id, COBALT.id, EMBER.id], period: P1, currency: CURRENCY});
        expect(engine.api, 'the question did not reach the engine through the store').toHaveBeenCalledTimes(1);

        await elapse(1_000);
        expect(eligibilitySpy(), 'the picker asked again with nothing changed').toHaveBeenCalledTimes(1);
    });

    it('puts the current choice in its question even when the page measures it, and leaves the other measured assets out', async () => {
        returningReader(AURORA.id);
        mount({period: P1, currency: CURRENCY, measured: [AURORA.id, DUNE.id]});
        await settle();
        await elapse(300);

        expect(eligibilitySpy(), 'no queryEligibility 300 ms after mounting with a period and a currency').toHaveBeenCalled();
        expect(questions().at(-1)?.ids, 'the question must judge the current choice, and nothing else the page measures').toEqual([AURORA.id, BOREALIS.id, COBALT.id, EMBER.id]);
    });

    it('publishes data-eligibility pending while it waits out the debounce and while it asks, then ready', async () => {
        const held = engineHolds();
        returningReader(null);
        const m = mount({period: P1, currency: CURRENCY});
        await settle();

        expect(control(m), 'waiting out the debounce is waiting').toHaveAttribute('data-eligibility', 'pending');
        await elapse(300);
        expect(held, 'premise: the question reached the engine').toHaveLength(1);
        expect(control(m), 'a question in flight is waiting').toHaveAttribute('data-eligibility', 'pending');

        held[0].answer();
        await settle();
        expect(control(m)).toHaveAttribute('data-eligibility', 'ready');
    });

    it('words the engine’s verdicts with describeEligibility: a ruled-out asset apart in the reader’s sentences, a late starter selectable with ⚠', async () => {
        returningReader(null);
        const m = mount({period: P1, currency: CURRENCY});
        await settle();
        await elapse(300);
        expect(engine.api, 'premise: the engine was asked').toHaveBeenCalledTimes(1);

        const listbox = await openNow(m);
        const blocked = blockedSection(m);
        const borealis = optionOf(blocked, BOREALIS.id);
        expect(borealis).toBeDisabled();
        expect(borealis).toHaveAttribute('data-level', 'ineligible');
        expect(borealis, 'the engine’s codes are not on the row').toHaveAttribute('data-reasons', (NO_PRICES.reasons ?? []).join(' '));
        for (const sentence of engineSentences(BOREALIS.id)) expect(borealis, 'a reason is not worded by describeEligibility').toHaveTextContent(sentence);
        expect(blocked).toHaveAccessibleName(blockedTitle());

        const dune = optionOf(listbox, DUNE.id);
        expect(blocked).not.toContainElement(dune);
        expect(dune).toBeEnabled();
        expect(dune).toHaveAttribute('data-level', 'warning');
        expect(within(dune).getByTestId(`${m.testid}-warning-${DUNE.id}`)).toBeInTheDocument();
        for (const id of [AURORA.id, COBALT.id, EMBER.id]) expect(optionOf(listbox, id)).toBeEnabled();
    });

    it('reads a failed request as failed: nothing ruled out, everything selectable, and the failure logged', async () => {
        const failure = new Error('synthetic: eligibility engine unreachable');
        engine.api.mockRejectedValue(failure);
        const errors = vi.spyOn(console, 'error').mockImplementation(() => {});
        try {
            returningReader(null);
            const m = mount({period: P1, currency: CURRENCY});
            await settle();
            await elapse(300);

            expect(engine.api, 'premise: the engine was asked').toHaveBeenCalled();
            expect(control(m)).toHaveAttribute('data-eligibility', 'failed');
            const logged = errors.mock.calls.some((args) => args.some((arg) => arg === failure || (typeof arg === 'string' && arg.includes(failure.message))));
            expect(logged, 'the failure was swallowed: no console.error carries it').toBe(true);
            const listbox = await openNow(m);
            expect(within(m.root).queryByTestId(`${m.testid}-blocked`), 'a failure ruled something out').toBeNull();
            for (const id of ALL_IDS) expect(optionOf(listbox, id)).toBeEnabled();
        } finally {
            errors.mockRestore();
        }
    });

    it('asks again, after the same debounce, when the page moves its period or changes its currency', async () => {
        returningReader(null);
        const m = mount({period: P1, currency: CURRENCY});
        await settle();
        await elapse(300);
        expect(eligibilitySpy(), 'premise: the first question left').toHaveBeenCalledTimes(1);

        m.box.period = P2;
        await settle();
        await elapse(299);
        expect(eligibilitySpy(), 'a new period asked before the debounce was over').toHaveBeenCalledTimes(1);
        await elapse(1);
        expect(eligibilitySpy(), 'a new period asked nothing').toHaveBeenCalledTimes(2);
        expect(questions()[1]).toEqual({ids: ALL_IDS, period: P2, currency: CURRENCY});

        m.box.currency = 'USD';
        await settle();
        await elapse(300);
        expect(eligibilitySpy(), 'a new currency asked nothing').toHaveBeenCalledTimes(3);
        expect(questions()[2]).toEqual({ids: ALL_IDS, period: P2, currency: 'USD'});
    });

    it.each(['after', 'before'] as const)('ignores the answer to an older question landing %s the answer to the newer one', async (order) => {
        const held = engineHolds();
        returningReader(null);
        const m = mount({period: P1, currency: CURRENCY});
        await settle();
        await elapse(300);
        m.box.period = P2;
        await settle();
        await elapse(300);
        expect(
            held.map((request) => request.body.date_range.start),
            'premise: one question per period reached the engine',
        ).toEqual([P1.start, P2.start]);

        // Under P1 the engine rules BOREALIS out; under P2 it admits every asset.
        const older = () => held[0].answer(engineView);
        const newer = () => held[1].answer(() => ADMITTED);
        if (order === 'after') {
            newer();
            await settle();
            older();
        } else {
            older();
            await settle();
            expect(control(m), 'the answer to the older question was taken for the current one').toHaveAttribute('data-eligibility', 'pending');
            newer();
        }
        await settle();

        expect(control(m)).toHaveAttribute('data-eligibility', 'ready');
        const listbox = await openNow(m);
        expect(within(m.root).queryByTestId(`${m.testid}-blocked`), 'the verdict of a superseded question is on screen').toBeNull();
        expect(optionOf(listbox, BOREALIS.id)).toBeEnabled();
    });

    it('asks the engine no second time when remounted on the same question: the store’s cache answers', async () => {
        returningReader(null);
        const first = mount({period: P1, currency: CURRENCY});
        await settle();
        await elapse(300);
        expect(control(first), 'premise: the first picker got its answer').toHaveAttribute('data-eligibility', 'ready');
        expect(engine.api).toHaveBeenCalledTimes(1);
        first.unmount();

        const second = mount({period: P1, currency: CURRENCY});
        await settle();
        await elapse(300);

        expect(control(second)).toHaveAttribute('data-eligibility', 'ready');
        expect(engine.api, 'the remounted picker sent the same question to the engine again').toHaveBeenCalledTimes(1);
        await openNow(second);
        expect(optionOf(blockedSection(second), BOREALIS.id), 'the cached answer did not reach the remounted picker').toBeDisabled();
    });
});

// ─── 13. A current choice the engine rules out (D378) ───────────────────────────────────────

describe('BenchmarkSelect — a current choice the engine rules out (D378)', () => {
    /**
     * All D378 keeps of a blocked choice: the id wherever a page reads it, and the stored
     * choice untouched. No `waitFor` inside: the faked-clock cases call it too.
     */
    async function expectBlockedButKept(m: Mounted, reader: string, asset: FixtureAsset): Promise<void> {
        expectPublished(m, 'blocked', `the engine rules ${asset.display_name} out, and it is the current choice`);
        expect(m.box.value, 'a blocked choice lost its value').toBe(asset.id);
        expect(control(m)).toHaveAttribute('data-benchmark-id', String(asset.id));
        expect(m.trigger, 'a blocked choice is no longer the one shown').toHaveTextContent(asset.display_name);
        expect(riskBenchmark.assetId, 'the picker cleared the shared choice').toBe(asset.id);
        expect(localStorage.getItem(keyFor(reader)), 'the picker cleared the stored key').toBe(String(asset.id));
        // The store knows nothing of verdicts: it reads the stored choice as set, never blocked.
        await expect(resolveRiskBenchmark()).resolves.toEqual({state: 'set', assetId: asset.id});
    }

    it('publishes blocked for a stored choice the given verdicts rule out, and keeps it: value, trigger, store, and current in the section apart', async () => {
        const reader = returningReader(BOREALIS.id);
        const m = mount({verdicts: givenVerdicts()});
        await resolutionSettled();
        await waitFor(() => expectPublished(m, 'blocked', 'the given verdicts rule the stored choice out'));

        await expectBlockedButKept(m, reader, BOREALIS);
        expect(transitions(m.states), 'blocked as soon as the verdicts say so — never set on the way, which a page comparing on set would have acted on').toEqual(['pending', 'blocked']);

        const listbox = await openList(m);
        const borealis = optionOf(blockedSection(m), BOREALIS.id);
        expect(borealis, 'the section apart does not mark the current choice').toHaveAttribute('aria-selected', 'true');
        expect(borealis).toBeDisabled();
        expect(within(listbox).getAllByTestId(`search-select-option-${BOREALIS.id}`), 'listed once').toHaveLength(1);
    });

    it('follows the given verdicts: blocked as soon as they rule the current choice out, set again once they no longer do', async () => {
        returningReader(AURORA.id);
        const m = mount({verdicts: new Map<number, PickerVerdict>()});
        await resolutionSettled();
        await waitFor(() => expectPublished(m, 'set', 'no verdict on the choice: nothing to block'));

        m.box.verdicts = new Map([[AURORA.id, RULED_OUT]]);
        await waitFor(() => expectPublished(m, 'blocked', 'the verdicts now rule the current choice out'));
        expect(m.box.value).toBe(AURORA.id);

        m.box.verdicts = new Map([[AURORA.id, ADMITTED_VERDICT]]);
        await waitFor(() => expectPublished(m, 'set', 'the verdicts admit the current choice again'));
        expect(transitions(m.states)).toEqual(['pending', 'set', 'blocked', 'set']);
        expect(riskBenchmark.assetId).toBe(AURORA.id);
    });

    it('keeps set a stored choice the given verdicts only warn about', async () => {
        returningReader(DUNE.id);
        const m = mount({verdicts: givenVerdicts()});
        await resolutionSettled();

        await waitFor(() => expectPublished(m, 'set'));
        expect(m.box.value).toBe(DUNE.id);
        expect(transitions(m.states)).toEqual(['pending', 'set']);
    });

    it('with a period, keeps a stored choice pending until its verdict for that period is in, then set', async () => {
        fakeClock();
        const held = engineHolds();
        returningReader(AURORA.id);
        const m = mount({period: P1, currency: CURRENCY});
        await settle();

        expectPublished(m, 'pending', 'the list confirmed the stored benchmark, but its verdict for the period is not in');
        await elapse(300);
        expect(held, 'premise: the question reached the engine').toHaveLength(1);
        expectPublished(m, 'pending', 'the question that judges the stored benchmark is in flight');

        held[0].answer();
        await settle();
        expectPublished(m, 'set');
        expect(m.box.value).toBe(AURORA.id);
        expect(control(m)).toHaveAttribute('data-benchmark-id', String(AURORA.id));
        expect(transitions(m.states)).toEqual(['pending', 'set']);
    });

    it('with a period, makes a stored choice the engine rules out blocked once its verdict is in, and keeps it', async () => {
        fakeClock();
        const held = engineHolds();
        const reader = returningReader(BOREALIS.id);
        const m = mount({period: P1, currency: CURRENCY});
        await settle();
        await elapse(300);
        expect(held, 'premise: the question reached the engine').toHaveLength(1);
        expect(held[0].body.asset_ids, 'the question left out the stored choice it has to judge').toContain(BOREALIS.id);
        expectPublished(m, 'pending');

        held[0].answer();
        await settle();

        await expectBlockedButKept(m, reader, BOREALIS);
        expect(transitions(m.states), 'never set on the way: a page comparing on set would have asked once').toEqual(['pending', 'blocked']);
        await openNow(m);
        expect(optionOf(blockedSection(m), BOREALIS.id), 'the section apart does not mark the current choice').toHaveAttribute('aria-selected', 'true');
    });

    it('goes back to pending when the page moves its period, until the verdict for the new one is in', async () => {
        fakeClock();
        const held = engineHolds();
        returningReader(BOREALIS.id);
        const m = mount({period: P1, currency: CURRENCY});
        await settle();
        await elapse(300);
        expect(held, 'premise: the question reached the engine').toHaveLength(1);
        held[0].answer(() => ADMITTED);
        await settle();
        expectPublished(m, 'set', 'premise: the engine admits the stored benchmark under P1');

        m.box.period = P2;
        await settle();
        expectPublished(m, 'pending', 'a new period: the verdict in hand is for the old one');
        await elapse(300);
        expect(held, 'premise: the new period was asked about').toHaveLength(2);
        expectPublished(m, 'pending', 'the question about the new period is in flight');

        // Under P2 the engine rules BOREALIS out.
        held[1].answer();
        await settle();
        expectPublished(m, 'blocked');
        expect(transitions(m.states)).toEqual(['pending', 'set', 'pending', 'blocked']);
        expect(riskBenchmark.assetId).toBe(BOREALIS.id);
    });

    it('takes a null from the store for no answer: pending still, the same question again after the same debounce, settled by the next answer', async () => {
        fakeClock();
        // `null` is the store's word for an answer it discarded, its cache emptied while the question
        // was in flight (a sync, a session change). Stood in for once: every later question goes
        // through to the real store and this file's engine, which rules BOREALIS out under P1.
        eligibilitySpy().mockResolvedValueOnce(null);
        try {
            const reader = returningReader(BOREALIS.id);
            const m = mount({period: P1, currency: CURRENCY});
            await settle();
            await elapse(300);

            // Positive control: the first question left, and what came back was that null, not a verdict.
            expect(eligibilitySpy(), 'premise: the first question left after the debounce').toHaveBeenCalledTimes(1);
            expect(eligibilitySpy().mock.settledResults[0], 'premise: the first question was answered null').toEqual({type: 'fulfilled', value: null});
            expect(engine.api, 'premise: the null stood in for the engine, which nothing reached').not.toHaveBeenCalled();
            expect(control(m), 'a null was taken for the verdicts').toHaveAttribute('data-eligibility', 'pending');
            expectPublished(m, 'pending', 'a null is no verdict on the stored choice, and a page compares on set');

            await elapse(299);
            expect(eligibilitySpy(), 'asked again before the debounce was over').toHaveBeenCalledTimes(1);
            await elapse(1);
            expect(eligibilitySpy(), 'a null was not asked again: the picker waits for an answer nobody will give').toHaveBeenCalledTimes(2);
            expect(questions()[0]).toEqual({ids: ALL_IDS, period: P1, currency: CURRENCY});
            expect(questions()[1], 'the second question is not the first one asked again').toEqual(questions()[0]);
            expect(engine.api, 'the second question did not reach the engine through the store').toHaveBeenCalledTimes(1);

            // Settled by the second answer: ready, and the stored choice blocked — never set on the way.
            expect(control(m)).toHaveAttribute('data-eligibility', 'ready');
            await expectBlockedButKept(m, reader, BOREALIS);
            expect(transitions(m.states), 'set on the way to blocked: a page comparing on set would have asked once').toEqual(['pending', 'blocked']);
            await openNow(m);
            const borealis = optionOf(blockedSection(m), BOREALIS.id);
            expect(borealis, 'the second answer’s verdict is not on the list').toBeDisabled();
            expect(borealis).toHaveAttribute('data-reasons', (NO_PRICES.reasons ?? []).join(' '));
            expect(borealis).toHaveAttribute('aria-selected', 'true');

            await elapse(1_000);
            expect(eligibilitySpy(), 'an answer did not end the asking').toHaveBeenCalledTimes(2);
        } finally {
            // Spent by the first question, unless the case failed before it: never left for a neighbour.
            eligibilitySpy().mockReset();
        }
    });

    it('makes a stored choice set when the eligibility request fails: a failure locks nothing', async () => {
        fakeClock();
        engine.api.mockRejectedValue(new Error('synthetic: eligibility engine unreachable'));
        const errors = vi.spyOn(console, 'error').mockImplementation(() => {});
        try {
            returningReader(BOREALIS.id);
            const m = mount({period: P1, currency: CURRENCY});
            await settle();
            await elapse(300);

            expect(control(m), 'premise: the request failed').toHaveAttribute('data-eligibility', 'failed');
            expectPublished(m, 'set');
            expect(m.box.value).toBe(BOREALIS.id);
            expect(transitions(m.states)).toEqual(['pending', 'set']);
        } finally {
            errors.mockRestore();
        }
    });

    it('keeps a stored id the list does not hold unknown under a period: there is no verdict to wait for', async () => {
        fakeClock();
        const reader = returningReader(GONE_ID);
        const m = mount({period: P1, currency: CURRENCY});
        await settle();
        await elapse(300);

        expectPublished(m, 'unknown');
        expect(m.box.value).toBeNull();
        expect(localStorage.getItem(keyFor(reader))).toBe(String(GONE_ID));
    });

    it('turns blocked into set when the reader chooses an asset that can be chosen — store, state and value before onchange', async () => {
        const reader = returningReader(BOREALIS.id);
        const m = mount({verdicts: givenVerdicts()});
        await resolutionSettled();
        await waitFor(() => expectPublished(m, 'blocked', 'premise: the stored choice is ruled out'));
        m.onchange.mockClear();
        const heard: Array<{next: number | null; state: BenchmarkState; store: number | null; value: number | null}> = [];
        m.onchange.mockImplementation((next) => {
            heard.push({next, state: m.box.state, store: riskBenchmark.assetId, value: m.box.value});
        });

        // DUNE carries a warning: selectable all the same.
        await choose(m, DUNE);

        expect(m.onchange).toHaveBeenCalledExactlyOnceWith(DUNE.id);
        expect(heard[0], 'inside onchange the state, the store and value must already hold the choice').toEqual({next: DUNE.id, state: 'set', store: DUNE.id, value: DUNE.id});
        expectPublished(m, 'set');
        expect(control(m)).toHaveAttribute('data-benchmark-id', String(DUNE.id));
        expect(localStorage.getItem(keyFor(reader))).toBe(String(DUNE.id));
    });
});
