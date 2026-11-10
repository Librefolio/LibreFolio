// @vitest-environment jsdom
/**
 * AllocationPanel.negativeCash.test.ts — decision 49 (workstream Y, lot Y10, backlog 54-1 and Y-6): the «now» pie of an
 * overdrawn portfolio, and what the panel hands the pie.
 *
 * ## The subject
 *
 * The `summary` block of `POST /portfolio/report` carries `allocation_by_type` and `allocation_by_sector` with the cash as a signed `Liquidity`
 * row — `AllocationItem{name, value, amount, emoji}`, `value` a share of the NET total (`build_allocation_current`,
 * `derived_views.py`) — so an overdrawn broker gives `Liquidity` a negative `value` and `amount`, and positive shares
 * adding up to more than 100. Decision 49 (approved by the developer), on the pie's side:
 *
 * - the pie keeps only the positive shares — `toAllocEntries` drops `value <= 0`, the pie filters `> 0` — and that STAYS;
 * - a note, test id `allocation-negative-cash-note` («Negative cash: −X», proposed key `dashboard.allocationNegativeCash`,
 *   not yet in the catalogue), shows the backend's `Liquidity.amount` as the app's currency formatter writes it —
 *   `formatCurrencyAmountPlain`, the one every amount of the dashboard goes through — and so masked under privacy, the
 *   minus left outside the mask (D8, `maskable`);
 * - no note without negative cash;
 * - Y-6: the entries handed to the pie carry no `emoji` field — the pie stopped reading it after DV.
 *
 * The amount is the backend's: the test feeds it, and expects it back formatted. No arithmetic on it anywhere.
 *
 * ## How it is read
 *
 * - The pie is the real `AllocationPieChart`, wrapped: the panel mounts it through a function that keeps the props it is
 *   handed and calls the real component with them. What the panel hands the pie is read off those props, and a note the
 *   pie itself would render is in the DOM all the same.
 * - The note by its test id. Its text is compared, whitespace runs collapsed and a typographic minus read as the ASCII
 *   one, with the formatter's own output for the same amount and currency, computed in the test as the flag stands —
 *   never a locale string written down. The sentence around the amount is not under test: its wording is not settled.
 *
 * ## What is replaced, and why
 *
 * - `echarts`: a recorder, jsdom having no canvas. The pie draws into it; its first draw is the barrier before a note is
 *   looked for — present or absent.
 * - `$lib/api`: the history chart's reference data, answered with empty lists (`AllocationPanel.test.ts`).
 * - `getCurrencyInfo`: EUR with its symbol and flag, as `GET /currencies` describes it, so the formatted amount carries
 *   every part the formatter can emit (`OtherPeriodEffectsTable.test.ts`).
 * - `localStorage`: a Map emptied before each case, holding the view and the tab the case mounts on — on Node 26 the
 *   global is undefined (`AllocationPanel.test.ts`).
 *
 * Privacy is module-level state: `setPrivacyEnabled` moves the in-memory flag (`$app/environment` reports
 * `browser: false`), and every case puts it back off.
 *
 * ## What is red today
 *
 * The note does not exist, so every note case is red but the absence guard; and `toAllocEntries` writes `emoji` into
 * every entry (Y-6). Green today, and must stay green: only positive entries reach the pie; no note without negative cash.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in, the currency the mock describes and the props of every pie the panel mounts. Hoisted: the mock
 * factories below read them.
 */
const {chartInstances, echartsModule, EUR_INFO, pieMounts} = vi.hoisted(() => {
    interface FakeChart {
        setOptionCalls: unknown[];
        setOption: (option: unknown) => void;
        getOption: () => Record<string, unknown>;
        getDom: () => unknown;
        getWidth: () => number;
        getHeight: () => number;
        on: () => void;
        off: () => void;
        dispatchAction: () => void;
        resize: () => void;
        clear: () => void;
        isDisposed: () => boolean;
        dispose: () => void;
    }

    const chartInstances: FakeChart[] = [];

    function createFakeChart(dom: unknown): FakeChart {
        let disposed = false;
        const chart: FakeChart = {
            setOptionCalls: [],
            setOption: (option) => void chart.setOptionCalls.push(option),
            getOption: () => ({}),
            getDom: () => dom,
            getWidth: () => 0,
            getHeight: () => 0,
            on: () => {},
            off: () => {},
            dispatchAction: () => {},
            resize: () => {},
            clear: () => {},
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
        chartInstances.push(chart);
        return chart;
    }

    return {
        chartInstances,
        echartsModule: {
            init: (dom: unknown) => createFakeChart(dom),
            format: {getTextRect: (text: string) => ({x: 0, y: 0, width: text.length * 7, height: 14})},
        },
        /** EUR as `GET /currencies` describes it. Shared by the mock and the expectations, so the two cannot drift apart. */
        EUR_INFO: {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [] as string[], country_names: [] as string[]},
        /** The props object of every AllocationPieChart the panel mounted, in mount order. */
        pieMounts: [] as Array<Record<string, unknown>>,
    };
});

vi.mock('echarts', () => echartsModule);

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => ({items: []}));
            },
        },
    ),
}));

vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    getCurrencyInfo: (code: string) => (code === EUR_INFO.code ? EUR_INFO : {code, name: code, symbol: code, flag_emoji: '🏳️', country_codes: [], country_names: []}),
}));

/**
 * The real pie, mounted as the panel mounts it, its props kept. A Svelte 5 component is a function of an anchor and a
 * props object — the panel calls `AllocationPieChart(anchor, {get data() {…}, …})` — so the wrapper records the object,
 * whose getters read the panel's state at the time of the read, and hands it on untouched.
 */
vi.mock('$lib/components/charts/AllocationPieChart.svelte', async (importOriginal) => {
    const original = await importOriginal<typeof import('$lib/components/charts/AllocationPieChart.svelte')>();
    const RealPie = original.default as unknown as (anchor: unknown, props: Record<string, unknown>) => unknown;
    function RecordedPie(anchor: unknown, props: Record<string, unknown>): unknown {
        pieMounts.push(props);
        return RealPie(anchor, props);
    }
    return {...original, default: RecordedPie};
});

const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => void storage.set(key, value),
    removeItem: (key: string) => void storage.delete(key),
});

import {flushSync, tick} from 'svelte';
import {render, screen, setupI18n, waitFor} from '$test/component';
import {getUserStorageKey} from '$lib/utils/storage';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import type {PortfolioSummary} from '$lib/stores/portfolio/portfolioStore.svelte';
import AllocationPanel from './AllocationPanel.svelte';

// =============================================================================
// Fixtures — the backend's numbers, as the `summary` block of `POST /portfolio/report` carries them
// =============================================================================

/** One `AllocationItem` as the backend serialises it: share and amount are decimal strings, `emoji` a string or null. */
interface Item {
    name: string;
    value: string;
    amount: string;
    emoji: string | null;
}

const item = (name: string, value: string, amount: string, emoji: string | null = null): Item => ({name, value, amount, emoji});

/** The part of a summary the panel reads: its three allocation lists. */
interface Allocation {
    allocation_by_type: Item[];
    allocation_by_sector: Item[];
    allocation_by_geography: Item[];
}

/** The overdrawn broker's cash, as the backend sends it in its `Liquidity` rows. */
const NEGATIVE_CASH = '-2000.00';

/**
 * An overdrawn portfolio: positions 12 000, cash −2 000, net worth 10 000. The shares are on the net total, so by type
 * and by sector the positives add up to 120 and `Liquidity` is −20; geography never holds the cash, so its shares are on
 * the positions alone. Sorted as the backend sorts them, by amount, the cash last. The type rows carry `emoji: null`,
 * the sector rows the sector's emoji, as `_alloc` writes them.
 */
const OVERDRAWN: Allocation = {
    allocation_by_type: [item('STOCK', '70.00', '7000.00'), item('ETF', '50.00', '5000.00'), item('Liquidity', '-20.00', NEGATIVE_CASH)],
    allocation_by_sector: [item('Technology', '70.00', '7000.00', '💻'), item('Financials', '50.00', '5000.00', '🏦'), item('Liquidity', '-20.00', NEGATIVE_CASH, '💰')],
    allocation_by_geography: [item('USA', '58.33', '7000.00'), item('ITA', '41.67', '5000.00')],
};

/** A funded portfolio: `typeRows` by type — the pie under test — and one-row sector and geography lists. */
function funded(typeRows: Item[]): Allocation {
    return {allocation_by_type: typeRows, allocation_by_sector: [item('Technology', '100.00', '10000.00', '💻')], allocation_by_geography: [item('USA', '100.00', '9000.00')]};
}

/** Portfolios without negative cash: positive, zero, or no `Liquidity` row at all. */
const NO_NEGATIVE_CASH = [
    {title: 'positive cash', allocation: funded([item('STOCK', '60.00', '6000.00'), item('ETF', '30.00', '3000.00'), item('Liquidity', '10.00', '1000.00')])},
    {title: 'zero cash', allocation: funded([item('STOCK', '60.00', '6000.00'), item('ETF', '40.00', '4000.00'), item('Liquidity', '0.00', '0.00')])},
    {title: 'no cash row', allocation: funded([item('STOCK', '60.00', '6000.00'), item('ETF', '40.00', '4000.00')])},
];

/** The two dimensions the pie draws, each with the list of the overdrawn portfolio it is handed. */
const TABS = [
    {tab: 'type' as const, items: OVERDRAWN.allocation_by_type},
    {tab: 'sector' as const, items: OVERDRAWN.allocation_by_sector},
];

type Tab = (typeof TABS)[number]['tab'];

const NOTE_TESTID = 'allocation-negative-cash-note';

// =============================================================================
// Mounting and reading
// =============================================================================

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    storage.clear();
    pieMounts.length = 0;
    chartInstances.length = 0;
});

afterEach(() => {
    // Module-level flag shared by every case of the file: a leftover `true` would mount the next panel masked.
    setPrivacyEnabled(false);
});

/** Mounts the panel on the «now» view and `tab`, as a user who left it there finds it (storage keys of the panel itself). */
function mountPanel(allocation: Allocation, tab: Tab = 'type'): void {
    storage.set(getUserStorageKey('dashboard-allocation-view'), 'now');
    storage.set(getUserStorageKey('dashboard-allocation-tab'), tab);
    render(AllocationPanel, {
        summary: allocation as unknown as PortfolioSummary,
        loading: false,
        displayCurrency: EUR_INFO.code,
        brokerIds: undefined,
        currentLanguage: 'en',
        allocationHistory: null,
        onRequestAllocationHistory: vi.fn(async () => {}),
    });
}

/** The props of the pie the panel mounted last, checked to be the pie of `tab`: the type pie is the one given `mode: 'type'`. */
function pieOf(tab: Tab): Record<string, unknown> {
    const props = pieMounts.at(-1);
    if (!props) throw new Error('the panel mounted no AllocationPieChart');
    expect(props.mode ?? 'sector', `the pie mounted last is not the ${tab} pie`).toBe(tab);
    return props;
}

/** The entries the panel handed the pie of `tab`. */
function pieEntries(tab: Tab): Array<Record<string, unknown>> {
    const data = pieOf(tab).data;
    if (!Array.isArray(data)) throw new Error(`the ${tab} pie was handed no list of entries`);
    return data as Array<Record<string, unknown>>;
}

/** The positive rows of `items` as the pie must receive them: the name, the share and the amount, parsed as the panel parses them. */
function positiveEntries(items: readonly Item[]): Array<{name: string; value: number; amount: number}> {
    return items.filter(({value}) => parseFloat(value) > 0).map(({name, value, amount}) => ({name, value: parseFloat(value), amount: parseFloat(amount)}));
}

/** Barrier: the pie has drawn, so the «now» view — where a note would sit — has rendered and run its effects. */
async function pieDrawn(): Promise<void> {
    await waitFor(() =>
        expect(
            chartInstances.some(({setOptionCalls}) => setOptionCalls.length > 0),
            'the pie never drew',
        ).toBe(true),
    );
}

/** Text as a user reads it: whitespace runs (no-break ones included) as one space, a typographic minus as the ASCII one. */
function readable(text: string | null | undefined): string {
    return (text ?? '')
        .replace(/\u2212/g, '-')
        .replace(/\s+/g, ' ')
        .trim();
}

/** The note's text, once the pie has drawn. Fails when the panel renders no note. */
async function noteText(): Promise<string> {
    await pieDrawn();
    const note = screen.queryByTestId(NOTE_TESTID);
    expect(note, `the panel renders no ${NOTE_TESTID}`).not.toBeNull();
    return readable(note?.textContent);
}

/** The backend's cash as the app's currency formatter writes it right now: clear or masked, as the privacy flag stands. */
const formattedCash = (): string => readable(formatCurrencyAmountPlain(parseFloat(NEGATIVE_CASH), EUR_INFO.code));

/** The digits of the cash as the formatter writes them unmasked — the same `toLocaleString` call it makes: what masking must hide. */
const cashMagnitude = (): string => Math.abs(parseFloat(NEGATIVE_CASH)).toLocaleString(uiLocale(), {minimumFractionDigits: 2, maximumFractionDigits: 2});

/** Sets the privacy flag, then flushes: synchronously, and once more through the microtask the app itself waits on. */
async function setPrivacy(value: boolean): Promise<void> {
    setPrivacyEnabled(value);
    flushSync();
    await tick();
}

function escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// =============================================================================
// Decision 49 and Y-6 — what the panel hands the pie
// =============================================================================

describe('AllocationPanel — what the panel hands the pie of an overdrawn portfolio (decision 49, Y-6)', () => {
    it.each(TABS)('$tab: only the positive shares reach the pie, the negative Liquidity stays out (green today, must stay green)', ({tab, items}) => {
        // CONTRACT: decision 49 keeps the pie to the positive shares — an arc cannot be negative; the cash goes to the
        // note instead. Guards `toAllocEntries`, which drops `value <= 0`, against a fix that lets the cash through.
        // GREEN TODAY.
        expect(
            items.some(({name, value}) => name === 'Liquidity' && parseFloat(value) < 0),
            'fixture: the negative cash is in the list',
        ).toBe(true);

        mountPanel(OVERDRAWN, tab);

        expect(pieEntries(tab).map(({name, value, amount}) => ({name, value, amount}))).toEqual(positiveEntries(items));
    });

    it.each(TABS)('$tab: no entry handed to the pie carries an emoji key (Y-6)', ({tab}) => {
        // CONTRACT: Y-6 — after DV the pie reads no `emoji` (sector emoji come from the sector store, type icons from
        // K's taxonomy), so the panel stops writing a field nobody reads. RED TODAY: `toAllocEntries` writes
        // `emoji: i?.emoji ?? null` into every entry — the key is there even when the backend sends null.
        mountPanel(OVERDRAWN, tab);
        const entries = pieEntries(tab);
        expect(entries.length, 'barrier: the pie was handed entries').toBeGreaterThan(0);

        expect(
            entries.filter((entry) => 'emoji' in entry).map(({name}) => name),
            'entries carrying an emoji key',
        ).toEqual([]);
    });
});

// =============================================================================
// Decision 49 — the negative cash note
// =============================================================================

describe('AllocationPanel — the negative cash note under the pie (decision 49)', () => {
    it('shows the backend’s Liquidity amount, −2000, as the app’s currency formatter writes it', async () => {
        // CONTRACT: decision 49 — the overdraft the pie cannot draw is stated in `allocation-negative-cash-note`, with
        // the backend's `Liquidity.amount` written by the dashboard's currency formatter, sign included. RED TODAY: the
        // panel renders no such element; `toAllocEntries` drops the negative row and nothing takes its place.
        expect(isPrivacyEnabled(), 'precondition: privacy off').toBe(false);
        const expected = formattedCash();
        // Controls: the expectation is the clear, signed amount in EUR — the sign, the digits, the currency.
        expect(expected, 'control: the formatter signs the negative amount and writes its digits').toMatch(/^-\d/);
        expect(expected, 'control: the formatter writes the magnitude').toContain(cashMagnitude());
        expect(expected, 'control: the formatter names the currency').toContain(EUR_INFO.code);

        mountPanel(OVERDRAWN);

        expect(await noteText()).toContain(expected);
    });

    it('masks the amount under privacy, the minus left outside the mask (D8)', async () => {
        // CONTRACT: decision 49 + D8 — the note's amount is personal money, so privacy replaces its digits with the
        // placeholder and keeps the sign in front of it: «−•••», currency kept. RED TODAY: there is no note.
        setPrivacyEnabled(true);
        const masked = formattedCash();
        // Controls: the formatter masks — no digit left — and keeps the sign outside the placeholder, as D8 rules.
        expect(masked, 'control: no digit survives the formatter’s mask').not.toMatch(/\d/);
        expect(masked, 'control: D8, the sign outside the placeholder').toMatch(new RegExp(`^-${escapeRegExp(PRIVACY_PLACEHOLDER)}`));

        mountPanel(OVERDRAWN);
        const text = await noteText();

        expect(text).toContain(masked);
        expect(text, 'the magnitude, as the formatter writes it').not.toContain(cashMagnitude());
        expect(text, 'the backend’s raw amount').not.toContain(NEGATIVE_CASH.replace(/^-/, ''));
    });

    it('follows the privacy toggle in place, both ways', async () => {
        // CONTRACT: the note reacts to the privacy toggle like every amount of the dashboard — a formatter call frozen
        // at mount would keep the digits on screen after the toggle (R20). RED TODAY: there is no note.
        mountPanel(OVERDRAWN);
        const clear = formattedCash();
        expect(await noteText(), 'mounted, privacy off').toContain(clear);

        await setPrivacy(true);
        const masked = formattedCash();
        expect(masked, 'control: the flag moved the formatter').not.toBe(clear);
        expect(await noteText(), 'privacy turned on').toContain(masked);
        expect(await noteText(), 'privacy turned on: the clear amount is gone').not.toContain(clear);

        await setPrivacy(false);
        expect(await noteText(), 'privacy turned off again').toContain(clear);
    });

    it.each(NO_NEGATIVE_CASH)('$title: no note (green today, must stay green)', async ({allocation}) => {
        // CONTRACT: decision 49 — the note states an overdraft; a portfolio whose cash is positive, zero or absent has
        // none to state. GREEN TODAY: there is no note at all.
        mountPanel(allocation);
        // Presence barrier: the pie is mounted, handed the positive entries, and has drawn — the view the note would
        // sit in is on screen and settled, so its absence is not a matter of time.
        expect(pieEntries('type').map(({name, value, amount}) => ({name, value, amount}))).toEqual(positiveEntries(allocation.allocation_by_type));
        await pieDrawn();

        expect(screen.queryByTestId(NOTE_TESTID)).toBeNull();
    });
});
