// @vitest-environment jsdom
/**
 * AssetPickerPanel — the reusable picker of **portfolio assets**, and the pure helpers it stands on.
 *
 * Not to be confused with `ui/media/AssetPickerModal.svelte`, which picks an image *file* (a URL, an
 * upload, a file already on the server). This panel picks instruments out of the user's asset
 * catalogue: the ones a portfolio holds, or could hold.
 *
 * Stage 1 extracts it from the Asset Global lab into `ui/select/`, in two modes, and each mode is a
 * promise made to code that exists today:
 *
 *  - `mode="multi"` is the lab's «+», `risk/LabAssetPicker.svelte`. The lab keeps a thin wrapper and
 *    must behave exactly as before, so the cases below restate today's behaviour under generic test
 *    ids: every one is `${testId}-…`.
 *  - `mode="single"` is a drop-in for `SearchSelect`, and for what `AssetSelect` adds to it: the same
 *    test ids, the same search (`filterOptions`), the same keyboard (`stepSelectable`), plus Risk's
 *    verdicts. A ruled-out asset is listed, disabled, in `${testId}-blocked`, and the current value is
 *    never dropped from the trigger, whatever hides it from the list.
 *
 * The five helpers that leave `risk/assetSetSelection.ts` with the picker (`applyFilters`,
 * `foldForSearch`, `pickerRows`, `toggleVisibleRows`, `visibleRowsAllChecked`) bring their tests
 * along, unchanged in substance. `ui/select` imports nothing from `components/risk/`, and the last
 * block gates it.
 *
 * Conventions, the suite's own:
 *
 *  - Fixtures are invented, and every string a test asserts on is one it handed in: names, tickers,
 *    labels, the placeholder, the verdicts' texts. What the panel translates itself («Add {count}»,
 *    its two empty states) is read for its number, or compared with itself, never with a literal.
 *  - No class is a selector. Three are read on purpose, because the contract names them: the value
 *    line's `truncate` span, its icon's `w-4 h-4`, and the trigger's height class, which must not
 *    change when a value arrives. `AssetSelect`'s trigger stacked a second line under the name, and
 *    the field grew with it.
 *  - Lookups are scoped to this instance: `search-select-option-*` is shared by every SearchSelect on
 *    a page.
 *  - The lab's «+» comes in as a raw snippet (`createRawSnippet`), and the bound value as accessors
 *    over a `reactiveBox`, for the reasons `TreeSelect.test.ts` gives.
 */
import {beforeAll, describe, expect, expectTypeOf, it, vi} from 'vitest';
import {createRawSnippet} from 'svelte';
import {readdirSync, readFileSync} from 'node:fs';
import {dirname, join, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {reactiveBox} from '$test/runes.svelte';
import type {EligibilityView} from '$lib/components/risk/eligibility';
import type {AssetInfo} from '$lib/stores/reference/assetStore';
import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';
import AssetPickerPanel from './AssetPickerPanel.svelte';
import {applyFilters, assetSearchText, assetSelectOrder, dropdownPlacement, foldForSearch, pickerRows, toggleVisibleRows, visibleRowsAllChecked, type PickerAsset, type PickerSection, type PickerVerdict, type SelectionFilters} from './assetPicker';
import {filterOptions} from './optionFilter';

/**
 * The filter menus may put a flag beside each currency, and flags live in the currency cache. The
 * cache stays empty here (every code falls back to itself) and nothing reaches the network.
 */
vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    ensureCurrenciesLoaded: vi.fn(async () => {}),
}));

beforeAll(async () => {
    await setupI18n();
});

// ─── Shared fixtures and readers ─────────────────────────────────────────────────────────────

/** An asset as the panel reads it. Every field is spelled out, so a fixture shows what it has and what it lacks. */
function asset(id: number, name: string, overrides: Partial<PickerAsset> = {}): PickerAsset {
    return {id, display_name: name, currency: 'EUR', asset_type: 'ETF', icon_url: null, active: true, identifier_isin: null, identifier_ticker: null, identifier_other: null, ...overrides};
}

const ids = (rows: readonly {id: number}[]): number[] => rows.map((row) => row.id);

/** Text as a reader meets it: whitespace collapsed. */
const textOf = (element: Element): string => (element.textContent ?? '').replace(/\s+/g, ' ').trim();

/** The asset id a row's test id ends on. */
const idOf = (element: Element): number => Number((element.getAttribute('data-testid') ?? '').replace(/^.*-/, ''));

/** Disabled as a control (`disabled`) or as an ARIA option (`aria-disabled`): either way the user cannot take it. */
const isDisabled = (element: Element): boolean => element.hasAttribute('disabled') || element.getAttribute('aria-disabled') === 'true';

/** A translation key that reached the screen untranslated: `scope.key`, no space anywhere. */
const RAW_KEY = /^[\w-]+(\.[\w-]+)+$/;

/** Two sentences per verdict, none of them with a digit: a digit in a row can only be one the panel added. */
const WARN_TEXTS = ['probe-warning: a thin price history', 'probe-warning: a gap in the period'];
const BLOCK_TEXTS = ['probe-blocked: no prices in the period', 'probe-blocked: prices too old'];

const ELIGIBLE: PickerVerdict = {level: 'eligible', codes: [], texts: []};

/** The section title of the blocked assets, and the note a full selection shows: the caller's words, handed in. */
const BLOCKED_LABEL = 'probe: cannot take part';
const FULL_LABEL = 'probe: no room left';

// ─── assetPicker.ts: the helpers that moved out of risk/assetSetSelection.ts ─────────────────

/** The fields `applyFilters` reads, and an id to name a row by. Structural: risk's `SelectableAsset` stays in risk. */
interface FilterRow {
    id: number;
    asset_type?: string | null;
    currency: string;
}

function filterRow(id: number, overrides: Partial<FilterRow> = {}): FilterRow {
    return {id, asset_type: 'ETF', currency: 'EUR', ...overrides};
}

describe('applyFilters', () => {
    /** The filter row with no criterion set, as it opens. */
    const EMPTY_FILTERS: SelectionFilters = {types: [], currencies: []};
    const assets = [filterRow(1, {asset_type: 'ETF', currency: 'EUR'}), filterRow(2, {asset_type: 'STOCK', currency: 'USD'}), filterRow(3, {asset_type: 'ETF', currency: 'USD'}), filterRow(4, {asset_type: null, currency: 'EUR'})];

    it('shows everything when no criterion is set', () => {
        // An empty filter row is unconstrained, not empty. A page that opens
        // blank makes the user guess what they did wrong.
        expect(ids(applyFilters(assets, EMPTY_FILTERS))).toEqual(ids(assets));
    });

    it('narrows by type', () => {
        expect(ids(applyFilters(assets, {types: ['ETF'], currencies: []}))).toEqual([1, 3]);
    });

    it('narrows by currency', () => {
        expect(ids(applyFilters(assets, {types: [], currencies: ['USD']}))).toEqual([2, 3]);
    });

    it('accepts several values for one criterion', () => {
        expect(ids(applyFilters(assets, {types: ['ETF', 'STOCK'], currencies: []}))).toEqual([1, 2, 3]);
    });

    it('composes type and currency with AND', () => {
        expect(ids(applyFilters(assets, {types: ['ETF'], currencies: ['USD']}))).toEqual([3]);
    });

    it('matches an asset with no type under OTHER', () => {
        expect(ids(applyFilters(assets, {types: ['OTHER'], currencies: []}))).toEqual([4]);
        const untyped: FilterRow[] = [{id: 9, currency: 'EUR'}];
        expect(ids(applyFilters(untyped, {types: ['OTHER'], currencies: []}))).toEqual([9]);
    });

    it('matches an asset whose type is an empty string under OTHER', () => {
        // `||`, not `??`: an empty string is as unclassified as a null one, and
        // under `??` the asset would match no criterion at all — it would
        // vanish the moment any type filter was switched on, unreachable.
        const blank = [filterRow(9, {asset_type: ''})];
        expect(ids(applyFilters(blank, {types: ['OTHER'], currencies: []}))).toEqual([9]);
        expect(ids(applyFilters(blank, EMPTY_FILTERS))).toEqual([9]);
    });

    it('returns nothing when a criterion that was really set matches nothing', () => {
        expect(applyFilters(assets, {types: ['CRYPTO'], currencies: []})).toEqual([]);
    });

    it('leaves the catalogue it was given untouched', () => {
        const original = [...assets];
        const filtered = applyFilters(assets, {types: ['ETF'], currencies: []});
        expect(assets).toEqual(original);
        expect(filtered).not.toBe(assets);
    });
});

describe('foldForSearch', () => {
    it('drops accents and case, so "societe" finds "Société"', () => {
        expect(foldForSearch('Société Générale')).toBe('societe generale');
        expect(foldForSearch('ÉCLAIR À LA CRÈME')).toBe('eclair a la creme');
    });

    it('folds an accent typed as a separate mark exactly like a precomposed one', () => {
        // "é" arrives as one code point or as "e" + COMBINING ACUTE ACCENT, depending on where the text came from.
        expect(foldForSearch('Soci\u00E9t\u00E9')).toBe('societe');
        expect(foldForSearch('Socie\u0301te\u0301')).toBe('societe');
    });

    it('leaves digits, spaces and punctuation as they are', () => {
        expect(foldForSearch('S&P 500 — ETF (Acc)')).toBe('s&p 500 — etf (acc)');
    });
});

describe('pickerRows', () => {
    interface Row {
        id: number;
        name: string;
        currency: string;
    }

    // Not in id order, so "the order the caller passed" cannot pass for "sorted".
    const rows: Row[] = [
        {id: 4, name: 'iShares Core MSCI World', currency: 'USD'},
        {id: 2, name: 'Société Générale', currency: 'EUR'},
        {id: 7, name: 'Vanguard FTSE All-World ETF', currency: 'USD'},
        {id: 1, name: 'Amundi MSCI World ETF', currency: 'EUR'},
    ];
    const found = (selected: readonly number[], query: string): number[] => pickerRows(rows, selected, query, (row) => `${row.name} ${row.currency}`).map((row) => row.id);

    it('lists every candidate, in the order given, when the query is empty or blank', () => {
        expect(found([], '')).toEqual([4, 2, 7, 1]);
        expect(found([], '   ')).toEqual([4, 2, 7, 1]);
    });

    it('leaves out the assets already selected, even when they match', () => {
        expect(found([2, 7], '')).toEqual([4, 1]);
        expect(found([7], 'vanguard')).toEqual([]);
    });

    it('keeps a row only when every word of the query is in its text, in any order', () => {
        // "etf usd" finds the ETF quoted in dollars whichever way its name is written;
        // either word alone also brings the euro ETF, or the dollar fund that is no ETF.
        expect(found([], 'etf usd')).toEqual([7]);
        expect(found([], 'usd etf')).toEqual([7]);
        expect(found([], 'etf')).toEqual([7, 1]);
        expect(found([], 'usd')).toEqual([4, 7]);
        expect(found([], 'msci crypto')).toEqual([]);
    });

    it('matches regardless of accents and case, on either side', () => {
        expect(found([], 'SOCIETE')).toEqual([2]);
        expect(found([], 'générale')).toEqual([2]);
    });
});

describe('toggleVisibleRows and visibleRowsAllChecked', () => {
    // `room` is how many assets the selection can still take; the rows checked in
    // the picker, shown or not, spend it.

    it('checks the visible rows not checked yet, in the order shown', () => {
        expect(visibleRowsAllChecked([], [3, 1, 2], 10)).toBe(false);
        expect(toggleVisibleRows([], [3, 1, 2], 10)).toEqual([3, 1, 2]);
    });

    it('checks no more rows than the selection has room for', () => {
        const checked = toggleVisibleRows([], [1, 2, 3, 4, 5], 3);
        expect(checked).toEqual([1, 2, 3]);
        // Nothing left it could check: the switch now offers to uncheck.
        expect(visibleRowsAllChecked(checked, [1, 2, 3, 4, 5], 3)).toBe(true);
    });

    it('counts a row checked under another query against the room, and keeps it', () => {
        // 9 was checked under an earlier search: it is not shown, and it takes a place.
        expect(toggleVisibleRows([9], [1, 2, 3], 3)).toEqual([9, 1, 2]);
    });

    it('unchecks the visible rows once every one is checked, and only those', () => {
        expect(visibleRowsAllChecked([9, 1, 2], [1, 2], 10)).toBe(true);
        expect(toggleVisibleRows([9, 1, 2], [1, 2], 10)).toEqual([9]);
    });

    it('unchecks instead of checking when no room is left', () => {
        // One visible row checked, two not, and no room for them: the switch clears the one.
        expect(visibleRowsAllChecked([9, 1], [1, 2, 3], 2)).toBe(true);
        expect(toggleVisibleRows([9, 1], [1, 2, 3], 2)).toEqual([9]);
        // With no room at all and nothing checked it has nothing to do — the picker disables it then.
        expect(visibleRowsAllChecked([], [1, 2, 3], 0)).toBe(true);
        expect(toggleVisibleRows([], [1, 2, 3], 0)).toEqual([]);
    });

    it('offers nothing to uncheck when no row is visible', () => {
        expect(visibleRowsAllChecked([9], [], 10)).toBe(false);
        expect(toggleVisibleRows([9], [], 10)).toEqual([9]);
    });

    it('says it would uncheck exactly when the switch unchecks, in every state', () => {
        // `visibleRowsAllChecked` is the label and `toggleVisibleRows` the action:
        // if they ever disagreed, the switch would say one thing and do another.
        const visible = [1, 2, 3];
        const states = [[], [1], [1, 2], [1, 2, 3], [9], [9, 1], [9, 1, 2, 3]];
        for (const checked of states) {
            for (const room of [0, 1, 2, 3, 4, 10]) {
                const unchecks = !toggleVisibleRows(checked, visible, room).some((id) => visible.includes(id));
                expect(visibleRowsAllChecked(checked, visible, room), `checked [${checked.join(', ')}], room ${room}`).toBe(unchecks);
            }
        }
    });

    it('hands back a new list and leaves the one it was given alone', () => {
        // The picker assigns the result to its state: a list changed in place would not re-render.
        const checked = [9, 1];
        for (const room of [10, 2]) {
            expect(toggleVisibleRows(checked, [1, 2, 3], room), `room ${room}`).not.toBe(checked);
        }
        expect(checked).toEqual([9, 1]);
    });
});

// ─── assetPicker.ts: what single mode brings from AssetSelect and SearchSelect ───────────────

describe('assetSearchText', () => {
    it('joins the ISIN, the ticker and the other codes, in that order, with spaces', () => {
        const probe = asset(1, 'Probe World', {identifier_isin: 'IE00PROBE001', identifier_ticker: 'PRW', identifier_other: ['PRWD', 'PRWC']});
        expect(assetSearchText(probe)).toBe('IE00PROBE001 PRW PRWD PRWC');
    });

    it('skips the codes an asset does not have, empty ones included', () => {
        expect(assetSearchText(asset(1, 'Probe World', {identifier_ticker: 'PRW'}))).toBe('PRW');
        expect(assetSearchText(asset(1, 'Probe World', {identifier_isin: 'IE00PROBE001', identifier_ticker: '', identifier_other: ['', 'PRWC']}))).toBe('IE00PROBE001 PRWC');
        expect(assetSearchText(asset(1, 'Probe World'))).toBe('');
    });

    it('never carries the name, the currency or the type (P3/A6)', () => {
        // Shared by hundreds of rows, a currency or a type would make "eur" or "etf" match the whole list.
        const text = assetSearchText(asset(1, 'Euro Stoxx Tracker', {currency: 'EUR', asset_type: 'ETF', identifier_ticker: 'PRW'}));
        expect(text).toBe('PRW');
        expect(text.toLowerCase()).not.toMatch(/eur|etf|stoxx/);
    });
});

describe('assetSelectOrder', () => {
    /**
     * AssetSelect's comparator (`AssetSelect.svelte:98-101`), copied: active first, then
     * `display_name.localeCompare(other)` with no locale, so the runtime's own collation decides.
     *
     * The names are chosen so that collation cannot vary with that runtime: every one is capitalised
     * (a POSIX collation sorts every capital before every lower-case letter), and they differ on the
     * first letter, where the only accent is É, an E in every Latin collation. A bare code-unit
     * `sort()` still files it after Z, which is what keeps this from passing for a naive comparison.
     */
    it('puts the active assets first, each group in the order of a locale-less localeCompare', () => {
        const unordered = [asset(1, 'Zeta Fund'), asset(2, 'Cobalt Growth', {active: false}), asset(3, 'Évian Water'), asset(4, 'Banana Republic'), asset(5, 'Aardvark Legacy', {active: false}), asset(6, 'Delta Income')];
        const activeNames = ['Banana Republic', 'Delta Income', 'Évian Water', 'Zeta Fund'];
        const localeless = (names: readonly string[]): string[] => [...names].sort((left, right) => left.localeCompare(right));

        // Premises: the order expected below is the one this runtime's locale-less localeCompare gives, and not a code-unit sort's.
        expect(localeless(['Zeta Fund', 'Évian Water', 'Banana Republic', 'Delta Income']), 'premise: what localeCompare with no locale gives').toEqual(activeNames);
        expect(localeless(['Cobalt Growth', 'Aardvark Legacy']), 'premise: the inactive pair').toEqual(['Aardvark Legacy', 'Cobalt Growth']);
        expect([...activeNames].sort(), 'premise: a code-unit sort files É after Z').not.toEqual(activeNames);

        expect(ids(assetSelectOrder(unordered))).toEqual([4, 6, 3, 1, 5, 2]);
    });

    it('hands back a new array and leaves the one it was given alone', () => {
        const given = [asset(1, 'Zeta Fund'), asset(2, 'Alpha Fund')];
        const before = [...given];
        const ordered = assetSelectOrder(given);
        expect(ids(ordered)).toEqual([2, 1]);
        expect(ordered).not.toBe(given);
        expect(given).toEqual(before);
    });
});

describe('dropdownPlacement', () => {
    const AUTO = {position: 'auto', minWidth: 280} as const;
    const DESKTOP = {width: 1280, height: 800};
    /** A trigger 36 px tall whose top edge sits at `top`. */
    const at = (top: number, left = 40, width = 320) => ({top, bottom: top + 36, left, width});

    it('opens below a trigger with room under it, no taller than that room', () => {
        const placement = dropdownPlacement(at(100), DESKTOP, AUTO);
        expect(placement.side).toBe('bottom');
        expect(placement.maxHeight).toBeGreaterThan(0);
        expect(placement.maxHeight).toBeLessThanOrEqual(DESKTOP.height - 136);
    });

    it('opens above a trigger near the bottom edge, no taller than the room above', () => {
        const placement = dropdownPlacement(at(700), DESKTOP, AUTO);
        expect(placement.side).toBe('top');
        expect(placement.maxHeight).toBeGreaterThan(0);
        expect(placement.maxHeight).toBeLessThanOrEqual(700);
    });

    it('prefers below whenever the room there is enough, even with more above', () => {
        // 1000 px above, 964 below: far more than a list needs, on either side.
        expect(dropdownPlacement(at(1000), {width: 1280, height: 2000}, AUTO).side).toBe('bottom');
    });

    it('prefers below on a tie', () => {
        // 382 px above, 382 below.
        expect(dropdownPlacement({top: 382, bottom: 418, left: 40, width: 320}, DESKTOP, AUTO).side).toBe('bottom');
    });

    it('honours an explicit side, whatever the room', () => {
        expect(dropdownPlacement(at(100), DESKTOP, {position: 'top', minWidth: 280}).side).toBe('top');
        expect(dropdownPlacement(at(700), DESKTOP, {position: 'bottom', minWidth: 280}).side).toBe('bottom');
    });

    it('is as wide as the trigger, and never narrower than minWidth', () => {
        expect(dropdownPlacement(at(100, 40, 200), DESKTOP, AUTO).width).toBe(280);
        expect(dropdownPlacement(at(100, 40, 400), DESKTOP, AUTO).width).toBe(400);
    });

    it('is never wider than the viewport less 16 px', () => {
        expect(dropdownPlacement(at(100, 10, 200), {width: 250, height: 800}, AUTO).width).toBe(234);
        expect(dropdownPlacement(at(100, 0, 600), {width: 375, height: 800}, AUTO).width).toBe(359);
    });

    it('starts at the trigger’s left edge when it fits there', () => {
        expect(dropdownPlacement(at(100, 40, 320), DESKTOP, AUTO).left).toBe(40);
    });

    it('slides left to keep 8 px from the right edge', () => {
        // 1100 + 320 would cross 1280: 1280 - 320 - 8.
        expect(dropdownPlacement(at(100, 1100, 320), DESKTOP, AUTO).left).toBe(952);
    });

    it('keeps 8 px from the left edge, a trigger scrolled half out of view included', () => {
        expect(dropdownPlacement(at(100, 2, 320), DESKTOP, AUTO).left).toBe(8);
        expect(dropdownPlacement(at(100, -30, 320), DESKTOP, AUTO).left).toBe(8);
    });

    it('fits a phone: a narrow trigger opens at minWidth, pulled back inside the screen', () => {
        // 375 px wide; a 120 px trigger at 200: 280 wide, at 375 - 280 - 8.
        expect(dropdownPlacement(at(100, 200, 120), {width: 375, height: 667}, AUTO)).toMatchObject({width: 280, left: 87});
    });

    it('keeps 8 px from both edges on any screen', () => {
        for (const viewportWidth of [250, 320, 375, 768, 1280]) {
            for (const left of [-50, 0, 8, 100, 300, 1000]) {
                for (const width of [100, 280, 400]) {
                    const placement = dropdownPlacement(at(100, left, width), {width: viewportWidth, height: 800}, AUTO);
                    const where = `viewport ${viewportWidth}, trigger at ${left}, ${width} wide`;
                    expect(placement.left, where).toBeGreaterThanOrEqual(8);
                    expect(placement.left + placement.width, where).toBeLessThanOrEqual(viewportWidth - 8);
                }
            }
        }
    });
});

/**
 * Compile-time pins. `expectTypeOf` does nothing at run time: `npm run check` (svelte-check) is
 * what fails on them. The one import from `components/risk/` in this folder lives here, type-only,
 * in a test: it is the contract the panel must meet without importing it.
 */
describe('the exported types', () => {
    it('publishes a verdict shaped as risk’s worded one, so the lab hands its map over as it is', () => {
        expectTypeOf<PickerVerdict>().toEqualTypeOf<{level: 'eligible' | 'warning' | 'ineligible'; codes: readonly string[]; texts: readonly string[]}>();
        expectTypeOf<EligibilityView>().toExtend<PickerVerdict>();
    });

    it('takes the lab’s assets and the asset store’s as they are', () => {
        expectTypeOf<{id: number; display_name: string; currency: string}>().toExtend<PickerAsset>();
        expectTypeOf<AssetInfo>().toExtend<PickerAsset>();
    });

    it('takes sections shaped as AssetSelect’s', () => {
        expectTypeOf<{key: string; label: string; match: (asset: PickerAsset) => boolean}>().toExtend<PickerSection>();
    });
});

// ─── The filter menus, as both modes carry them ──────────────────────────────────────────────

type FilterKind = 'type' | 'currency';

/** Open one filter menu of a panel — asked, never toggled blind — and end on its list being drawn. */
async function openFilterMenu(scope: HTMLElement, prefix: string, kind: FilterKind): Promise<HTMLElement> {
    const menu = `${prefix}-filter-${kind}-panel`;
    if (!within(scope).queryByTestId(menu)) await fireEvent.click(within(scope).getByTestId(`${prefix}-filter-${kind}-button`));
    return within(scope).getByTestId(menu);
}

/** A menu's options by value: what carries a pressed state. The menu's button, panel and "clear" share the prefix and carry none. */
function menuOptions(menu: HTMLElement, prefix: string, kind: FilterKind): Map<string, HTMLElement> {
    const stem = `${prefix}-filter-${kind}-`;
    const options = [...menu.querySelectorAll<HTMLElement>(`[data-testid^="${stem}"][aria-pressed]`)];
    return new Map(options.map((option): [string, HTMLElement] => [(option.getAttribute('data-testid') ?? '').slice(stem.length), option]));
}

/** What each value of a menu counts: the number its option ends on. */
function menuCounts(menu: HTMLElement, prefix: string, kind: FilterKind): Record<string, number> {
    const counts: Record<string, number> = {};
    for (const [value, option] of menuOptions(menu, prefix, kind)) {
        const count = textOf(option).match(/(\d+)$/);
        if (!count) throw new Error(`${prefix}-filter-${kind}-${value} shows no count`);
        counts[value] = Number(count[1]);
    }
    return counts;
}

/** Switch one value of a filter on or off, and end on its option reporting the new state. */
async function toggleFilter(scope: HTMLElement, prefix: string, kind: FilterKind, value: string): Promise<void> {
    const menu = await openFilterMenu(scope, prefix, kind);
    const option = within(menu).getByTestId(`${prefix}-filter-${kind}-${value}`);
    const wasOn = option.getAttribute('aria-pressed') === 'true';
    await fireEvent.click(option);
    expect(option).toHaveAttribute('aria-pressed', wasOn ? 'false' : 'true');
}

// ─── mode="multi": the lab's «+» ─────────────────────────────────────────────────────────────

const MULTI = 'probe-add';
const PLUS = 'probe-plus';

const ZEPHYR = asset(14, 'Zephyr Global Equity', {asset_type: 'STOCK', currency: 'USD'});
const AURORA = asset(11, 'Aurora Bond Ladder', {asset_type: 'BOND', currency: 'EUR'});
const MERIDIAN = asset(16, 'Meridian Value Fund', {asset_type: 'ETF', currency: 'EUR'});
const BOREALIS = asset(12, 'Borealis Tech', {asset_type: 'STOCK', currency: 'CHF'});
const COTE = asset(15, 'Côte Trésor', {asset_type: null, currency: 'EUR'});
const ASHEN = asset(17, 'Ashen Mining', {asset_type: 'STOCK', currency: 'CHF'});
const HALCYON = asset(13, 'Halcyon Income', {asset_type: 'ETF', currency: 'USD'});

/** The caller's order: neither by name nor by id, so "kept as given" cannot pass for "sorted". */
const CATALOGUE = [ZEPHYR, AURORA, MERIDIAN, BOREALIS, COTE, ASHEN, HALCYON];

/** AURORA (11) has no verdict: an asset the engine was never asked about is selectable. */
const MULTI_VERDICTS = new Map<number, PickerVerdict>([
    [14, ELIGIBLE],
    [16, {level: 'warning', codes: ['THIN_HISTORY', 'PERIOD_GAP'], texts: WARN_TEXTS}],
    [12, {level: 'ineligible', codes: ['NO_PRICES', 'STALE_PRICES'], texts: BLOCK_TEXTS}],
    [15, ELIGIBLE],
    [17, {level: 'ineligible', codes: ['NO_PRICES'], texts: ['probe-blocked: nothing to measure']}],
    [13, ELIGIBLE],
]);

/** The lab's own search text, less its translated type label. MERIDIAN alone answers to "quillwort". */
const SEARCH_TEXT = (candidate: PickerAsset): string => `${candidate.display_name} ${candidate.currency}${candidate.id === 16 ? ' quillwort' : ''}`;

/** The lab's «+», as a caller hands it in: a button that opens and closes the panel through the `toggle` it is given. */
const plusTrigger = createRawSnippet<[{toggle: () => void}]>((popover) => ({
    render: () => `<button type="button" data-testid="${PLUS}">+</button>`,
    setup: (button) => {
        const press = (): void => popover().toggle();
        button.addEventListener('click', press);
        return () => button.removeEventListener('click', press);
    },
}));

interface MultiMount {
    assets?: PickerAsset[];
    selected?: number[];
    room?: number;
    verdicts?: Map<number, PickerVerdict>;
    searchText?: (candidate: PickerAsset) => string;
}

function mountMulti(options: MultiMount = {}) {
    const onadd = vi.fn();
    render(AssetPickerPanel, {
        mode: 'multi',
        assets: CATALOGUE,
        selected: [],
        room: 10,
        verdicts: MULTI_VERDICTS,
        blockedLabel: BLOCKED_LABEL,
        fullLabel: FULL_LABEL,
        trigger: plusTrigger,
        testId: MULTI,
        ...options,
        onadd,
    });
    return {onadd};
}

/** Open the «+» — asked, never toggled blind — and end on its panel. */
async function openMulti(): Promise<HTMLElement> {
    if (!screen.queryByTestId(`${MULTI}-panel`)) await fireEvent.click(screen.getByTestId(PLUS));
    return screen.getByTestId(`${MULTI}-panel`);
}

/** Close it through the same «+», and end on the panel being gone. */
async function closeMulti(): Promise<void> {
    if (screen.queryByTestId(`${MULTI}-panel`)) await fireEvent.click(screen.getByTestId(PLUS));
    expect(screen.queryByTestId(`${MULTI}-panel`)).toBeNull();
}

const MULTI_ROW = new RegExp(`^${MULTI}-option-\\d+$`);
const multiSearch = (panel: HTMLElement): HTMLInputElement => within(panel).getByTestId(`${MULTI}-search`) as HTMLInputElement;
const multiRow = (panel: HTMLElement, id: number): HTMLElement => within(panel).getByTestId(`${MULTI}-option-${id}`);
const multiConfirm = (panel: HTMLElement): HTMLElement => within(panel).getByTestId(`${MULTI}-confirm`);
const multiSwitch = (panel: HTMLElement): HTMLElement => within(panel).getByTestId(`${MULTI}-toggle-visible`);
const multiEmpty = (panel: HTMLElement): HTMLElement | null => within(panel).queryByTestId(`${MULTI}-empty`);

/** The rows that can be checked, in screen order: every row outside the blocked section. */
function listedRows(panel: HTMLElement): HTMLElement[] {
    const blocked = within(panel).queryByTestId(`${MULTI}-blocked`);
    return within(panel)
        .queryAllByTestId(MULTI_ROW)
        .filter((row) => !blocked?.contains(row));
}

const listedIds = (panel: HTMLElement): number[] => listedRows(panel).map(idOf);
const checkedIds = (panel: HTMLElement): number[] =>
    listedRows(panel)
        .filter((row) => row.getAttribute('aria-selected') === 'true')
        .map(idOf);
const enabledIds = (panel: HTMLElement): number[] =>
    listedRows(panel)
        .filter((row) => !isDisabled(row))
        .map(idOf);

function blockedIds(panel: HTMLElement): number[] {
    const blocked = within(panel).queryByTestId(`${MULTI}-blocked`);
    return blocked ? within(blocked).queryAllByTestId(MULTI_ROW).map(idOf) : [];
}

/** The number «Add {count}» carries, whatever language the words around it are in. */
function confirmCount(panel: HTMLElement): number {
    const count = textOf(multiConfirm(panel)).match(/\d+/);
    if (!count) throw new Error('the confirm button shows no count');
    return Number(count[0]);
}

/**
 * Bring the pointer onto `target`, coming from `row`: every element in between is entered too.
 * `mouseenter` does not bubble, so a hover listener on a wrapper of the target (`Tooltip` keeps its
 * own on the icon's parent) hears it only when it is aimed at it.
 */
async function pointAt(target: HTMLElement, row: HTMLElement): Promise<void> {
    const path: HTMLElement[] = [];
    for (let node: HTMLElement | null = target; node && node !== row; node = node.parentElement) path.unshift(node);
    for (const node of path) await fireEvent.mouseEnter(node);
}

describe('AssetPickerPanel, mode="multi": the lab’s «+»', () => {
    it('names every part after its testId, and mounts the panel only while open', async () => {
        mountMulti();
        expect(screen.queryByTestId(`${MULTI}-panel`)).toBeNull();

        const panel = await openMulti();
        for (const part of ['search', 'toggle-visible', 'confirm', 'blocked']) expect(within(panel).getByTestId(`${MULTI}-${part}`)).toBeInTheDocument();
        const filters = within(panel).getByTestId(`${MULTI}-filters`);
        for (const kind of ['type', 'currency']) expect(filters).toContainElement(within(panel).getByTestId(`${MULTI}-filter-${kind}-button`));
        expect(within(panel).queryByTestId(`${MULTI}-filters-clear`), 'no filter is on yet').toBeNull();
        expect(multiEmpty(panel), 'the list is not empty').toBeNull();

        await toggleFilter(panel, MULTI, 'type', 'ETF');
        expect(filters).toContainElement(within(panel).getByTestId(`${MULTI}-filters-clear`));
        const strays = (): string[] => [...panel.querySelectorAll('[data-testid]')].map((element) => element.getAttribute('data-testid') ?? '').filter((testId) => !testId.startsWith(`${MULTI}-`));
        // A leftover `risk-…` id would leak the lab into every other caller of the panel.
        expect(strays(), 'with the type menu open').toEqual([]);
        await openFilterMenu(panel, MULTI, 'currency');
        expect(strays(), 'with the currency menu open').toEqual([]);
    });

    it('puts the focus in the search on opening', async () => {
        mountMulti();
        const panel = await openMulti();
        await waitFor(() => expect(multiSearch(panel)).toHaveFocus());
    });

    it('lists the rows in the order given, never sorted, and publishes each verdict', async () => {
        mountMulti();
        const panel = await openMulti();

        expect(listedIds(panel)).toEqual([14, 11, 16, 15, 13]);
        expect(blockedIds(panel)).toEqual([12, 17]);

        const published = (id: number) => [multiRow(panel, id).getAttribute('data-level'), multiRow(panel, id).getAttribute('data-reasons')];
        expect(published(14)).toEqual(['eligible', '']);
        expect(published(11), 'no verdict, as today').toEqual(['unknown', '']);
        expect(published(16)).toEqual(['warning', 'THIN_HISTORY PERIOD_GAP']);
        expect(published(12)).toEqual(['ineligible', 'NO_PRICES STALE_PRICES']);
        for (const id of listedIds(panel)) expect(multiRow(panel, id)).toHaveAttribute('aria-selected', 'false');
    });

    it('leaves the selected assets out, the parked ruled-out ones included, even when they match', async () => {
        mountMulti({selected: [13, 11, 17], searchText: SEARCH_TEXT});
        const panel = await openMulti();

        expect(listedIds(panel)).toEqual([14, 16, 15]);
        expect(blockedIds(panel)).toEqual([12]);

        await fireEvent.input(multiSearch(panel), {target: {value: 'halcyon'}});
        expect(listedIds(panel)).toEqual([]);
        expect(multiEmpty(panel)).not.toBeNull();
    });

    it('treats every asset as selectable when no verdict is given', async () => {
        mountMulti({verdicts: undefined});
        const panel = await openMulti();

        expect(within(panel).queryByTestId(`${MULTI}-blocked`)).toBeNull();
        expect(listedIds(panel)).toEqual(ids(CATALOGUE));
        for (const id of ids(CATALOGUE)) expect(multiRow(panel, id)).toHaveAttribute('data-level', 'unknown');
    });

    it('marks a warning row with ⚠ and its texts, and still lets it be checked', async () => {
        mountMulti();
        const panel = await openMulti();
        const meridian = multiRow(panel, 16);

        const warning = within(meridian).getByTestId(`${MULTI}-warning-16`);
        expect(
            within(panel)
                .queryAllByTestId(new RegExp(`^${MULTI}-warning-\\d+$`))
                .map(idOf),
            'only the warning row',
        ).toEqual([16]);

        // The texts are the hover's: wherever they are drawn, the pointer on the ⚠ brings them on screen.
        await pointAt(warning, meridian);
        for (const text of WARN_TEXTS) await waitFor(() => expect(document.body).toHaveTextContent(text), {timeout: 2_000});

        await fireEvent.click(meridian);
        expect(meridian).toHaveAttribute('aria-selected', 'true');
    });

    it('lists the ruled-out assets read-only, with their reasons, under the caller’s label', async () => {
        const {onadd} = mountMulti();
        const panel = await openMulti();
        const blocked = within(panel).getByTestId(`${MULTI}-blocked`);
        const borealis = within(blocked).getByTestId(`${MULTI}-option-12`);

        for (const text of BLOCK_TEXTS) expect(borealis).toHaveTextContent(text);
        expect(panel).toHaveTextContent(BLOCKED_LABEL);

        await fireEvent.click(borealis);
        expect(borealis).not.toHaveAttribute('aria-selected', 'true');
        expect(multiConfirm(panel)).toBeDisabled();

        // "Select visible" never reaches them either: five rows checked, five counted.
        await fireEvent.click(multiSwitch(panel));
        expect(checkedIds(panel)).toEqual([14, 11, 16, 15, 13]);
        expect(confirmCount(panel)).toBe(5);
        for (const row of within(within(panel).getByTestId(`${MULTI}-blocked`)).getAllByTestId(MULTI_ROW)) expect(row).not.toHaveAttribute('aria-selected', 'true');

        // With no ruled-out asset in view, neither the section nor its label.
        await toggleFilter(panel, MULTI, 'type', 'ETF');
        expect(within(panel).queryByTestId(`${MULTI}-blocked`)).toBeNull();
        expect(panel).not.toHaveTextContent(BLOCKED_LABEL);
        expect(onadd).not.toHaveBeenCalled();
    });

    it('offers every value of the whole catalogue, counting what each would still add', async () => {
        // HALCYON (ETF, USD) and AURORA (the only BOND) are in already; BOREALIS and ASHEN (the only CHF) are ruled out.
        mountMulti({selected: [13, 11]});
        const panel = await openMulti();
        const counts = async (kind: FilterKind) => menuCounts(await openFilterMenu(panel, MULTI, kind), MULTI, kind);

        expect(await counts('type')).toEqual({BOND: 0, ETF: 1, OTHER: 1, STOCK: 1});
        expect(await counts('currency')).toEqual({CHF: 0, EUR: 2, USD: 1});

        // A value switched on narrows the rows, never the menus nor their counts.
        await toggleFilter(panel, MULTI, 'type', 'ETF');
        expect(listedIds(panel)).toEqual([16]);
        expect(await counts('type')).toEqual({BOND: 0, ETF: 1, OTHER: 1, STOCK: 1});
        expect(await counts('currency')).toEqual({CHF: 0, EUR: 2, USD: 1});
    });

    it('narrows by any value of one filter, and by both filters together', async () => {
        mountMulti();
        const panel = await openMulti();

        await toggleFilter(panel, MULTI, 'type', 'ETF');
        expect(listedIds(panel)).toEqual([16, 13]);
        await toggleFilter(panel, MULTI, 'type', 'BOND');
        expect(listedIds(panel)).toEqual([11, 16, 13]);
        await toggleFilter(panel, MULTI, 'currency', 'USD');
        expect(listedIds(panel)).toEqual([13]);

        await toggleFilter(panel, MULTI, 'type', 'ETF');
        await toggleFilter(panel, MULTI, 'type', 'BOND');
        expect(listedIds(panel), 'USD alone').toEqual([14, 13]);

        await toggleFilter(panel, MULTI, 'currency', 'USD');
        await toggleFilter(panel, MULTI, 'type', 'OTHER');
        expect(listedIds(panel), 'the untyped asset').toEqual([15]);
    });

    it('offers "clear filters" only while a filter is on, and clears them all', async () => {
        mountMulti();
        const panel = await openMulti();
        const clear = () => within(panel).queryByTestId(`${MULTI}-filters-clear`);
        expect(clear(), 'nothing to clear yet').toBeNull();

        await toggleFilter(panel, MULTI, 'type', 'ETF');
        await toggleFilter(panel, MULTI, 'currency', 'USD');
        expect(listedIds(panel)).toEqual([13]);

        await fireEvent.click(within(panel).getByTestId(`${MULTI}-filters-clear`));
        expect(clear()).toBeNull();
        expect(listedIds(panel)).toEqual([14, 11, 16, 15, 13]);
        for (const kind of ['type', 'currency'] as const) {
            for (const option of menuOptions(await openFilterMenu(panel, MULTI, kind), MULTI, kind).values()) expect(option).toHaveAttribute('aria-pressed', 'false');
        }
    });

    it('opens on an empty search with nothing checked every time, and keeps the filters', async () => {
        mountMulti({searchText: SEARCH_TEXT});
        let panel = await openMulti();
        await toggleFilter(panel, MULTI, 'currency', 'EUR');
        expect(listedIds(panel)).toEqual([11, 16, 15]);
        await fireEvent.input(multiSearch(panel), {target: {value: 'meridian'}});
        expect(listedIds(panel)).toEqual([16]);
        await fireEvent.click(multiRow(panel, 16));
        expect(checkedIds(panel)).toEqual([16]);

        await closeMulti();
        panel = await openMulti();

        await waitFor(() => expect(multiSearch(panel)).toHaveValue(''));
        expect(checkedIds(panel)).toEqual([]);
        expect(multiConfirm(panel)).toBeDisabled();
        expect(listedIds(panel), 'EUR is still on').toEqual([11, 16, 15]);
        expect(menuOptions(await openFilterMenu(panel, MULTI, 'currency'), MULTI, 'currency').get('EUR')).toHaveAttribute('aria-pressed', 'true');
        expect(within(panel).getByTestId(`${MULTI}-filters-clear`)).toBeInTheDocument();
    });

    it('searches every word of the query, in any order, accents aside, through the caller’s searchText', async () => {
        mountMulti({searchText: SEARCH_TEXT});
        const panel = await openMulti();
        const search = async (query: string) => {
            await fireEvent.input(multiSearch(panel), {target: {value: query}});
            return [listedIds(panel), blockedIds(panel)];
        };

        expect(await search('quillwort'), 'only the searchText knows it').toEqual([[16], []]);
        expect(await search('fund eur')).toEqual([[16], []]);
        expect(await search('eur fund')).toEqual([[16], []]);
        expect(await search('tresor')).toEqual([[15], []]);
        expect(await search('CÔTE')).toEqual([[15], []]);
        // The blocked section is searched too, and a list holding only it is not empty.
        expect(await search('tech')).toEqual([[], [12]]);
        expect(multiEmpty(panel)).toBeNull();
    });

    it('checks the visible rows only up to the room left, and disables the rows beyond it', async () => {
        mountMulti({room: 2});
        const panel = await openMulti();
        const selectLabel = textOf(multiSwitch(panel));
        expect(panel).not.toHaveTextContent(FULL_LABEL);

        await fireEvent.click(multiSwitch(panel));
        expect(checkedIds(panel)).toEqual([14, 11]);
        expect(enabledIds(panel), 'only the checked rows stay clickable').toEqual([14, 11]);
        expect(confirmCount(panel)).toBe(2);
        expect(panel).toHaveTextContent(FULL_LABEL);
        expect(textOf(multiSwitch(panel)), 'the switch now says it unchecks').not.toBe(selectLabel);

        await fireEvent.click(multiRow(panel, 13));
        expect(checkedIds(panel), 'a row beyond the room is refused').toEqual([14, 11]);

        // No room left: the switch unchecks what it shows.
        await fireEvent.click(multiSwitch(panel));
        expect(checkedIds(panel)).toEqual([]);
        expect(enabledIds(panel)).toEqual([14, 11, 16, 15, 13]);
        expect(panel).not.toHaveTextContent(FULL_LABEL);
        expect(textOf(multiSwitch(panel))).toBe(selectLabel);
    });

    it('adds the checked assets on «Add {count}», in the order they were checked, and closes', async () => {
        const {onadd} = mountMulti();
        const panel = await openMulti();
        expect(multiConfirm(panel)).toBeDisabled();

        await fireEvent.click(multiRow(panel, 16));
        await fireEvent.click(multiRow(panel, 14));
        expect(multiConfirm(panel)).toBeEnabled();
        expect(confirmCount(panel)).toBe(2);
        await fireEvent.click(multiRow(panel, 16));
        expect(confirmCount(panel)).toBe(1);
        await fireEvent.click(multiRow(panel, 15));

        await fireEvent.click(multiConfirm(panel));
        expect(onadd).toHaveBeenCalledExactlyOnceWith([14, 15]);
        expect(screen.queryByTestId(`${MULTI}-panel`)).toBeNull();
    });

    it('confirms on Enter in the search, and does nothing on Enter with nothing checked', async () => {
        const {onadd} = mountMulti();
        const panel = await openMulti();

        await fireEvent.keyDown(multiSearch(panel), {key: 'Enter'});
        expect(onadd).not.toHaveBeenCalled();
        expect(screen.getByTestId(`${MULTI}-panel`)).toBeInTheDocument();

        await fireEvent.click(multiRow(panel, 13));
        await fireEvent.keyDown(multiSearch(panel), {key: 'Enter'});
        expect(onadd).toHaveBeenCalledExactlyOnceWith([13]);
        expect(screen.queryByTestId(`${MULTI}-panel`)).toBeNull();
    });

    it('says why the list is empty, in one of two ways: no results while searching or filtering, everything selected otherwise', async () => {
        mountMulti({selected: ids(CATALOGUE), searchText: SEARCH_TEXT});
        const panel = await openMulti();
        const emptyText = (): string => textOf(within(panel).getByTestId(`${MULTI}-empty`));

        const allIn = emptyText();
        await fireEvent.input(multiSearch(panel), {target: {value: 'halcyon'}});
        const noMatch = emptyText();
        expect(noMatch, 'a search that found nothing is not "everything is selected"').not.toBe(allIn);

        await fireEvent.input(multiSearch(panel), {target: {value: ''}});
        expect(emptyText()).toBe(allIn);
        await toggleFilter(panel, MULTI, 'type', 'ETF');
        expect(emptyText(), 'a filter answers like a search').toBe(noMatch);

        for (const text of [allIn, noMatch]) {
            expect(text).not.toBe('');
            expect(text, 'a translation, not its key').not.toMatch(RAW_KEY);
        }
    });

    it('shows no amounts: a row carries a name, a type and a currency, and no number', async () => {
        mountMulti();
        const panel = await openMulti();
        const rows = within(panel).getAllByTestId(MULTI_ROW);

        expect(rows).toHaveLength(CATALOGUE.length);
        for (const row of rows) expect(textOf(row), row.getAttribute('data-testid') ?? '').not.toMatch(/\d/);
    });
});

// ─── mode="single": SearchSelect's drop-in ───────────────────────────────────────────────────

const SINGLE = 'probe-pick';
const PLACEHOLDER = 'probe: choose an asset';
const REST_LABEL = 'Probe others';

const HARBOR = asset(21, 'Harbor Total Market', {identifier_ticker: 'HTM', identifier_isin: 'IE00HARBOR21', asset_type: 'ETF', currency: 'USD', icon_url: '/probe/icons/harbor.png'});
const TIDEWATER = asset(25, 'Tidewater Legacy', {identifier_ticker: 'TWL', asset_type: 'ETF', currency: 'USD', active: false});
const LUMEN = asset(22, 'Lumen Short Duration', {identifier_ticker: 'LSD', asset_type: 'BOND', currency: 'EUR'});
const QUARRY = asset(23, 'Quarry Resources', {identifier_ticker: 'QRY', asset_type: 'STOCK', currency: 'CHF'});
const SAFFRON = asset(24, 'Saffron Dividend', {asset_type: 'STOCK', currency: 'EUR'});
const UMBER = asset(26, 'Umber Fund', {identifier_ticker: 'UMB', asset_type: 'FUND', currency: 'EUR', active: undefined});

/** The caller's order, an inactive asset second: neither by name nor active-first. */
const SINGLE_ASSETS = [HARBOR, TIDEWATER, LUMEN, QUARRY, SAFFRON, UMBER];

/** LUMEN (22) carries a warning and QUARRY (23) is ruled out; SAFFRON and UMBER have no verdict. */
const SINGLE_VERDICTS = new Map<number, PickerVerdict>([
    [21, ELIGIBLE],
    [25, ELIGIBLE],
    [22, {level: 'warning', codes: ['THIN_HISTORY'], texts: [WARN_TEXTS[0]]}],
    [23, {level: 'ineligible', codes: ['NO_PRICES', 'STALE_PRICES'], texts: BLOCK_TEXTS}],
]);

const SECTIONS: PickerSection[] = [
    // Claims the ruled-out QUARRY too: a verdict outranks a section, so it still lands in the blocked section.
    {key: 'held', label: 'Probe held', match: (candidate) => [21, 22, 23].includes(candidate.id)},
    // Claims nothing: a section left empty prints no title.
    {key: 'never', label: 'Probe never', match: () => false},
    // Claims HARBOR too, after `held` did: the first section that accepts an asset keeps it.
    {key: 'bench', label: 'Probe benchmarks', match: (candidate) => [24, 21].includes(candidate.id)},
];

/** No ticker anywhere, so "bond" ranks the same whether an option's label is the name or `ticker · name`. */
const RANKED = [
    asset(31, 'Global Bond Fund'), // "bond" starts a word: rank 1
    asset(33, 'Vagabond Index'), // "bond" inside a word: rank 2
    asset(34, 'Treasury Ladder', {identifier_other: ['XBOND']}), // only its searchText says it: rank 3
    asset(32, 'Bondora Growth'), // the name starts with it: rank 0
    asset(35, 'Equity Income'), // no match
];

/** HARBOR is quoted in USD and is an ETF, LUMEN is a BOND in EUR: only names and codes may answer a query. */
const SEARCHABLE = [
    asset(41, 'Harbor Total Market', {identifier_ticker: 'HTM', identifier_isin: 'IE00HARBOR41', asset_type: 'ETF', currency: 'USD'}),
    asset(42, 'Lumen Short Duration', {identifier_ticker: 'LSD', identifier_other: ['LUMENCUM'], asset_type: 'BOND', currency: 'EUR'}),
    asset(43, 'USD Liquidity Reserve', {asset_type: 'LIQUIDITY', currency: 'EUR'}),
];

interface SingleMount {
    value?: number | null;
    assets?: PickerAsset[];
    verdicts?: Map<number, PickerVerdict>;
    sections?: PickerSection[];
    restLabel?: string;
    searchText?: (candidate: PickerAsset) => string;
    loading?: boolean;
    disabled?: boolean;
}

function mountSingle({value = null, ...options}: SingleMount = {}) {
    const onchange = vi.fn();
    // The parent's `$state` behind `bind:value`: the panel writes it through the setter below.
    const bound = reactiveBox<{value: number | null}>({value});
    const view = render(AssetPickerPanel, {
        mode: 'single',
        assets: SINGLE_ASSETS,
        verdicts: SINGLE_VERDICTS,
        blockedLabel: BLOCKED_LABEL,
        placeholder: PLACEHOLDER,
        testId: SINGLE,
        ...options,
        onchange,
        get value() {
            return bound.value;
        },
        set value(next: number | null) {
            bound.value = next;
        },
    });
    return {onchange, bound, unmount: view.unmount};
}

/** The one node carrying the test id: `getBy` throws on a second one, which is what keeps the wrapper honest. */
const singleRoot = (): HTMLElement => screen.getByTestId(SINGLE);
const singleTrigger = (): HTMLElement => within(singleRoot()).getByTestId(`${SINGLE}-trigger`);
const singleSearch = (): HTMLInputElement => within(singleRoot()).getByTestId(`${SINGLE}-search`) as HTMLInputElement;
const singleBlocked = (): HTMLElement => within(singleRoot()).getByTestId(`${SINGLE}-blocked`);
const choice = (id: number): HTMLElement => within(singleRoot()).getByTestId(`search-select-option-${id}`);
const queryChoice = (id: number): HTMLElement | null => within(singleRoot()).queryByTestId(`search-select-option-${id}`);
const CHOICE = /^search-select-option-\d+$/;
const SECTION_TITLE = /^search-select-header-__section:(held|never|bench|__rest)$/;

/** Open by a click — asked, never toggled blind — and end on the search being there. */
async function openSingle(): Promise<HTMLInputElement> {
    if (singleTrigger().getAttribute('aria-expanded') !== 'true') await fireEvent.click(singleTrigger());
    expect(singleTrigger()).toHaveAttribute('aria-expanded', 'true');
    return singleSearch();
}

function expectSingleClosed(): void {
    expect(singleTrigger()).toHaveAttribute('aria-expanded', 'false');
    expect(within(singleRoot()).queryByTestId(`${SINGLE}-search`)).toBeNull();
}

/** The list outside the blocked section, in screen order: `option-21`, `header-__section:held`. Titles this file did not define are not its business. */
function listOrder(): string[] {
    const blocked = within(singleRoot()).queryByTestId(`${SINGLE}-blocked`);
    return within(singleRoot())
        .queryAllByTestId(/^search-select-(option|header)-/)
        .filter((element) => !blocked?.contains(element))
        .map((element) => element.getAttribute('data-testid') ?? '')
        .filter((testId) => CHOICE.test(testId) || SECTION_TITLE.test(testId))
        .map((testId) => testId.replace('search-select-', ''));
}

/** The options outside the blocked section, in screen order. */
function optionIds(): number[] {
    const blocked = within(singleRoot()).queryByTestId(`${SINGLE}-blocked`);
    return within(singleRoot())
        .queryAllByTestId(CHOICE)
        .filter((option) => !blocked?.contains(option))
        .map(idOf);
}

/** Where the roving highlight is, read as data the way SearchSelect publishes it. */
const highlighted = (): number[] =>
    within(singleRoot())
        .queryAllByTestId(CHOICE)
        .filter((option) => option.getAttribute('data-highlighted') === 'true')
        .map(idOf);

const currentIds = (): number[] =>
    within(singleRoot())
        .queryAllByTestId(CHOICE)
        .filter((option) => option.getAttribute('aria-selected') === 'true')
        .map(idOf);

async function typeQuery(search: HTMLInputElement, query: string): Promise<number[]> {
    await fireEvent.input(search, {target: {value: query}});
    return optionIds();
}

/** The trigger's height classes, variants included (`h-9`, `min-h-9`, `sm:h-10`): compared, never required by name. */
const heightClasses = (element: Element): string[] => [...element.classList].filter((token) => /^(?:[\w-]+:)*(?:min-|max-)?h-/.test(token)).sort();

const BLOCK_TAGS = new Set(['ADDRESS', 'ARTICLE', 'ASIDE', 'BLOCKQUOTE', 'DD', 'DIV', 'DL', 'DT', 'FIGCAPTION', 'FIGURE', 'FOOTER', 'FORM', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'HEADER', 'LI', 'MAIN', 'NAV', 'OL', 'P', 'PRE', 'SECTION', 'TABLE', 'UL']);

/**
 * How many lines of text the trigger stacks, read from its structure: jsdom has no layout.
 *
 * A line is a box that starts a line of its own (a block element, a `block`-classed one, or a child of
 * a `flex-col`) and holds text that no smaller such box inside it holds. The trigger this guards
 * against stacked a ticker line over a "name · currency" line: two such boxes. A one-line trigger
 * keeps its spans in a single row: one box, or none at all.
 */
function lineCount(trigger: HTMLElement): number {
    const startsLine = (element: Element): boolean => BLOCK_TAGS.has(element.tagName) || element.classList.contains('block') || !!element.parentElement?.classList.contains('flex-col');
    const boxes = [...trigger.querySelectorAll('*')].filter((element) => startsLine(element) && textOf(element) !== '');
    return boxes.filter((box) => !boxes.some((other) => other !== box && box.contains(other))).length;
}

/** AssetSelect's own id for the badge, kept so the panel stays a drop-in for its trigger. */
const INACTIVE_BADGE = 'asset-select-selected-inactive-badge';

/** The value line: the trigger's one `truncate` element, a span. */
function valueLine(trigger: HTMLElement): HTMLElement {
    const lines = trigger.querySelectorAll<HTMLElement>('.truncate');
    expect(lines, 'one truncate element: the value line').toHaveLength(1);
    expect(lines[0].tagName).toBe('SPAN');
    return lines[0];
}

/**
 * The trigger's text outside the parts the contract names (the value line, the badge, the
 * placeholder): where a currency or a second line would show up.
 */
function textOutside(trigger: HTMLElement, named: readonly Element[]): string {
    const walker = document.createTreeWalker(trigger, NodeFilter.SHOW_TEXT);
    const loose: string[] = [];
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (!named.some((part) => part.contains(node))) loose.push(node.textContent ?? '');
    }
    return loose.join(' ').replace(/\s+/g, ' ').trim();
}

describe('AssetPickerPanel, mode="single": SearchSelect’s drop-in', () => {
    describe('test ids and opening', () => {
        it('carries SearchSelect’s test ids and ARIA, everything inside its own root', async () => {
            mountSingle({value: 21});
            const root = singleRoot();
            const trigger = singleTrigger();

            expect(trigger).toHaveAttribute('role', 'combobox');
            expect(trigger).toHaveAttribute('aria-haspopup', 'listbox');
            expect(trigger).toHaveAttribute('aria-expanded', 'false');
            expect(within(root).queryByTestId(`${SINGLE}-search`)).toBeNull();

            await fireEvent.click(trigger);
            expect(trigger).toHaveAttribute('aria-expanded', 'true');
            expect(root).toContainElement(singleSearch());
            // Nothing is portalled out: every option on the page is this root's, the blocked one included.
            const everywhere = screen.queryAllByTestId(CHOICE);
            expect(everywhere).toHaveLength(SINGLE_ASSETS.length);
            for (const option of everywhere) expect(root).toContainElement(option);
            expect(root).toContainElement(singleBlocked());
        });

        it('opens onto the first option it can land on, past a leading title, with the search focused', async () => {
            mountSingle({sections: SECTIONS, restLabel: REST_LABEL});
            const search = await openSingle();

            expect(highlighted()).toEqual([21]);
            await waitFor(() => expect(search).toHaveFocus());
        });

        it('lists the assets in the order given: the caller sorts, the panel never does', async () => {
            mountSingle();
            await openSingle();

            expect(optionIds()).toEqual([21, 25, 22, 24, 26]);
            expect(within(singleBlocked()).queryAllByTestId(CHOICE).map(idOf)).toEqual([23]);
        });
    });

    describe('choosing', () => {
        it('reports a click, writes the bound value, closes, and hands the focus back to the trigger', async () => {
            const {onchange, bound} = mountSingle();
            const search = await openSingle();
            await waitFor(() => expect(search).toHaveFocus());

            await fireEvent.click(choice(21));

            expect(onchange).toHaveBeenCalledExactlyOnceWith(21);
            expect(bound.value).toBe(21);
            expectSingleClosed();
            expect(singleTrigger()).toHaveFocus();
            expect(textOf(singleTrigger())).toBe('HTM · Harbor Total Market');
        });

        it('marks the current value, and nothing else, aria-selected', async () => {
            mountSingle({value: 22});
            await openSingle();

            expect(currentIds()).toEqual([22]);
        });

        it('follows a value its parent sets', async () => {
            const {bound} = mountSingle();
            expect(textOf(singleTrigger())).toBe(PLACEHOLDER);

            bound.value = 24;
            await waitFor(() => expect(textOf(singleTrigger())).toBe('Saffron Dividend'));
            bound.value = null;
            await waitFor(() => expect(textOf(singleTrigger())).toBe(PLACEHOLDER));
        });
    });

    describe('keyboard, as SearchSelect', () => {
        it.each(['Enter', ' ', 'ArrowDown'])('opens on %j pressed on the trigger', async (key) => {
            mountSingle();
            await fireEvent.keyDown(singleTrigger(), {key});

            expect(singleTrigger()).toHaveAttribute('aria-expanded', 'true');
            expect(singleSearch()).toBeInTheDocument();
        });

        it('opens on a printable key, and searches for it', async () => {
            mountSingle();
            await fireEvent.keyDown(singleTrigger(), {key: 'h'});

            expect(singleTrigger()).toHaveAttribute('aria-expanded', 'true');
            await waitFor(() => expect(singleSearch()).toHaveValue('h'));
            // A real query, not just a character in the box: TIDEWATER has no "h" anywhere.
            await waitFor(() => expect(queryChoice(25)).toBeNull());
            expect(queryChoice(21)).not.toBeNull();
        });

        it('steps the highlight over titles and blocked rows, stops at both ends, and chooses on Enter', async () => {
            const {onchange} = mountSingle({sections: SECTIONS, restLabel: REST_LABEL});
            const search = await openSingle();
            expect(listOrder(), 'premise: the list the walk crosses').toEqual(['header-__section:held', 'option-21', 'option-22', 'header-__section:bench', 'option-24', 'header-__section:__rest', 'option-25', 'option-26']);
            expect(highlighted()).toEqual([21]);

            const walk = async (key: 'ArrowDown' | 'ArrowUp', presses: number): Promise<number[][]> => {
                const stops: number[][] = [];
                for (let press = 0; press < presses; press++) {
                    await fireEvent.keyDown(search, {key});
                    stops.push(highlighted());
                }
                return stops;
            };

            // LUMEN carries a warning and is a stop; the titles are not; QUARRY, ruled out, sits after the end.
            expect(await walk('ArrowDown', 5)).toEqual([[22], [24], [25], [26], [26]]);
            expect(await walk('ArrowUp', 5)).toEqual([[25], [24], [22], [21], [21]]);
            expect(choice(23)).not.toHaveAttribute('data-highlighted', 'true');

            await walk('ArrowDown', 2);
            expect(highlighted()).toEqual([24]);
            await fireEvent.keyDown(search, {key: 'Enter'});
            expect(onchange).toHaveBeenCalledExactlyOnceWith(24);
            expectSingleClosed();
        });

        it('closes on Escape without choosing, and hands the focus back to the trigger', async () => {
            const {onchange} = mountSingle({value: 21});
            const search = await openSingle();
            await waitFor(() => expect(search).toHaveFocus());

            await fireEvent.keyDown(search, {key: 'Escape'});

            expectSingleClosed();
            expect(singleTrigger()).toHaveFocus();
            expect(onchange).not.toHaveBeenCalled();
            expect(textOf(singleTrigger())).toBe('HTM · Harbor Total Market');
        });
    });

    describe('verdicts', () => {
        it('lists a ruled-out asset as a disabled option of the blocked section, with its reasons, and refuses it', async () => {
            const {onchange} = mountSingle();
            await openSingle();
            const quarry = within(singleBlocked()).getByTestId('search-select-option-23');

            expect(isDisabled(quarry)).toBe(true);
            expect(quarry).toHaveAttribute('data-reasons', 'NO_PRICES STALE_PRICES');
            for (const text of BLOCK_TEXTS) expect(quarry).toHaveTextContent(text);
            expect(singleRoot()).toHaveTextContent(BLOCKED_LABEL);

            await fireEvent.click(quarry);
            expect(onchange).not.toHaveBeenCalled();
            expect(singleTrigger()).toHaveAttribute('aria-expanded', 'true');
        });

        it('keeps a warning asset selectable, marked ⚠', async () => {
            const {onchange} = mountSingle();
            await openSingle();
            const lumen = choice(22);

            expect(within(lumen).getByTestId(`${SINGLE}-warning-22`)).toBeInTheDocument();
            expect(within(choice(21)).queryByTestId(`${SINGLE}-warning-21`)).toBeNull();
            expect(isDisabled(lumen)).toBe(false);
            expect(singleBlocked()).not.toContainElement(lumen);

            await fireEvent.click(lumen);
            expect(onchange).toHaveBeenCalledExactlyOnceWith(22);
        });

        it('has no blocked section, and no blocked label, when nothing is ruled out', async () => {
            mountSingle({verdicts: new Map([[22, SINGLE_VERDICTS.get(22)!]])});
            await openSingle();

            expect(within(singleRoot()).queryByTestId(`${SINGLE}-blocked`)).toBeNull();
            expect(singleRoot()).not.toHaveTextContent(BLOCKED_LABEL);
            expect(optionIds()).toEqual([21, 25, 22, 23, 24, 26]);
        });
    });

    describe('the current value is never dropped', () => {
        it('shows a ruled-out current value on the trigger, and marks it current in the blocked section', async () => {
            mountSingle({value: 23});
            expect(textOf(singleTrigger())).toBe('QRY · Quarry Resources');

            await openSingle();
            const quarry = within(singleBlocked()).getByTestId('search-select-option-23');
            expect(quarry).toHaveAttribute('aria-selected', 'true');
            expect(isDisabled(quarry)).toBe(true);
            expect(within(singleRoot()).getAllByTestId('search-select-option-23'), 'listed once').toHaveLength(1);
        });

        it('keeps showing the current value on the trigger when a filter hides it from the list', async () => {
            mountSingle({value: 21});
            await openSingle();
            expect(choice(21)).toHaveAttribute('aria-selected', 'true');

            await toggleFilter(singleRoot(), SINGLE, 'type', 'STOCK');

            expect(queryChoice(21)).toBeNull();
            expect(queryChoice(24), 'the filter is live: SAFFRON is a STOCK').not.toBeNull();
            expect(singleTrigger()).toHaveAttribute('aria-expanded', 'true');
            expect(textOf(singleTrigger())).toBe('HTM · Harbor Total Market');
        });
    });

    describe('sections, as AssetSelect', () => {
        it('titles each section that holds an asset, gives each asset to the first section that takes it, and titles the rest', async () => {
            mountSingle({sections: SECTIONS, restLabel: REST_LABEL});
            await openSingle();

            expect(listOrder()).toEqual(['header-__section:held', 'option-21', 'option-22', 'header-__section:bench', 'option-24', 'header-__section:__rest', 'option-25', 'option-26']);
            expect(within(singleRoot()).getByTestId('search-select-header-__section:held')).toHaveTextContent('Probe held');
            expect(within(singleRoot()).getByTestId('search-select-header-__section:bench')).toHaveTextContent('Probe benchmarks');
            expect(within(singleRoot()).getByTestId('search-select-header-__section:__rest')).toHaveTextContent(REST_LABEL);
            expect(within(singleBlocked()).getByTestId('search-select-option-23'), 'a verdict outranks a section').toBeInTheDocument();
            expect(within(singleRoot()).getAllByTestId('search-select-option-23')).toHaveLength(1);
        });

        it('leaves the rest untitled without a restLabel', async () => {
            mountSingle({sections: SECTIONS});
            await openSingle();

            expect(listOrder()).toEqual(['header-__section:held', 'option-21', 'option-22', 'header-__section:bench', 'option-24', 'option-25', 'option-26']);
        });

        it('titles the rest only when a section above it was titled', async () => {
            mountSingle({sections: [SECTIONS[1]], restLabel: REST_LABEL});
            await openSingle();

            expect(listOrder(), 'one heading over the whole list would say nothing').toEqual(['option-21', 'option-25', 'option-22', 'option-24', 'option-26']);
        });

        it('drops a title once the search has emptied its section', async () => {
            mountSingle({sections: SECTIONS, restLabel: REST_LABEL});
            const search = await openSingle();
            await fireEvent.input(search, {target: {value: 'tidewater'}});

            expect(listOrder()).toEqual(['header-__section:__rest', 'option-25']);
        });
    });

    describe('search, as SearchSelect', () => {
        it('ranks the matches through filterOptions, not in the order given, and Enter takes the best', async () => {
            const {onchange} = mountSingle({assets: RANKED});
            const search = await openSingle();

            const asSearchSelect = filterOptions(
                RANKED.map((candidate) => ({value: String(candidate.id), label: candidate.display_name, searchText: assetSearchText(candidate)})),
                'bond',
            ).map((option) => Number(option.value));
            expect(asSearchSelect, 'premise: what SearchSelect ranks, and not the order given').toEqual([32, 31, 33, 34]);

            expect(await typeQuery(search, 'bond')).toEqual(asSearchSelect);
            await waitFor(() => expect(highlighted()).toEqual([32]));
            await fireEvent.keyDown(search, {key: 'Enter'});
            expect(onchange).toHaveBeenCalledExactlyOnceWith(32);
        });

        it('finds an asset by its codes, never by its currency or its type (P3/A6)', async () => {
            mountSingle({assets: SEARCHABLE});
            const search = await openSingle();

            expect(await typeQuery(search, 'lumencum'), 'an alternate code').toEqual([42]);
            expect(await typeQuery(search, 'htm'), 'a ticker').toEqual([41]);
            expect(await typeQuery(search, 'usd'), 'only the name that says it, not the asset quoted in it').toEqual([43]);
            expect(await typeQuery(search, 'eur'), 'two assets in EUR, neither named so').toEqual([]);
            expect(await typeQuery(search, 'etf'), 'an ETF not named so').toEqual([]);
            expect(await typeQuery(search, 'bond'), 'a BOND not named so').toEqual([]);
        });

        it('takes the caller’s searchText in place of the default', async () => {
            mountSingle({assets: SEARCHABLE, searchText: (candidate) => (candidate.id === 43 ? 'zebra' : '')});
            const search = await openSingle();

            expect(await typeQuery(search, 'zebra')).toEqual([43]);
            expect(await typeQuery(search, 'lumencum'), 'the default is gone, not merged').toEqual([]);
            expect(await typeQuery(search, 'harbor'), 'the name still answers').toEqual([41]);
        });
    });

    describe('unavailable states', () => {
        it('cannot be opened while disabled, by pointer or by keyboard', async () => {
            const {onchange} = mountSingle({disabled: true, value: 21});

            await fireEvent.click(singleTrigger());
            expectSingleClosed();
            for (const key of ['Enter', ' ', 'ArrowDown', 'h']) {
                await fireEvent.keyDown(singleTrigger(), {key});
                expectSingleClosed();
            }
            expect(onchange).not.toHaveBeenCalled();
            expect(textOf(singleTrigger())).toBe('HTM · Harbor Total Market');
        });

        it('shows a loading row instead of options while loading', async () => {
            mountSingle({loading: true});
            await openSingle();

            expect(within(singleRoot()).queryAllByTestId(CHOICE)).toHaveLength(0);
            expect(within(singleRoot()).queryByTestId(`${SINGLE}-blocked`)).toBeNull();
            expect(
                within(singleRoot())
                    .getAllByRole('listbox')
                    .some((listbox) => listbox.getAttribute('aria-busy') === 'true'),
            ).toBe(true);
        });
    });

    /**
     * The final markup is the compact item AssetSelect is landing: one line, a `w-4 h-4` icon when
     * the asset has one, then one `truncate` span holding `ticker · name`, then AssetSelect's own
     * inactive badge. No currency, no second line. Without a value, a plain span holds the placeholder.
     */
    describe('the trigger', () => {
        it('keeps the same height class and a single line, with a value and without', async () => {
            mountSingle();
            const empty = singleTrigger();
            const height = heightClasses(empty);
            expect(height, 'the trigger sets its height with a class').not.toEqual([]);
            expect(lineCount(empty)).toBeLessThanOrEqual(1);
            expect(empty.querySelector('svg'), 'the chevron').not.toBeNull();

            await openSingle();
            await fireEvent.click(choice(21));

            const filled = singleTrigger();
            expect(textOf(filled), 'premise: the value is on the trigger now').toBe('HTM · Harbor Total Market');
            expect(heightClasses(filled)).toEqual(height);
            expect(lineCount(filled)).toBeLessThanOrEqual(1);
            expect(filled.querySelector('svg'), 'the chevron').not.toBeNull();
        });

        it('shows the placeholder in a plain span, and nothing else, without a value', () => {
            mountSingle();
            const trigger = singleTrigger();
            const placeholder = within(trigger).getByText(PLACEHOLDER);

            expect(placeholder.tagName).toBe('SPAN');
            expect(placeholder.children, 'plain: text and nothing else').toHaveLength(0);
            expect(textOutside(trigger, [placeholder])).toBe('');
            expect(trigger.querySelector('img'), 'no value, no icon').toBeNull();
            expect(within(trigger).queryByTestId(INACTIVE_BADGE)).toBeNull();
        });

        it('shows the value as one truncate span, ticker first, after a w-4 h-4 icon, with no currency', () => {
            mountSingle({value: 21});
            const trigger = singleTrigger();
            const line = valueLine(trigger);

            expect(textOf(line)).toBe('HTM · Harbor Total Market');
            const icons = trigger.querySelectorAll('img');
            expect(icons).toHaveLength(1);
            expect(icons[0]).toHaveAttribute('src', '/probe/icons/harbor.png');
            expect(icons[0]).toHaveClass('w-4', 'h-4');
            expect(icons[0].compareDocumentPosition(line) & Node.DOCUMENT_POSITION_FOLLOWING, 'the icon goes before the value line').not.toBe(0);
            // HARBOR is quoted in USD: nothing but the value line may carry text, and that line does not name it.
            expect(textOutside(trigger, [line])).toBe('');
            expect(textOf(trigger)).not.toContain('USD');
            expect(lineCount(trigger)).toBeLessThanOrEqual(1);
            expect(within(trigger).queryByTestId(INACTIVE_BADGE)).toBeNull();
        });

        it('shows the bare name without a ticker, after its type’s icon when it has none of its own', () => {
            mountSingle({value: 24});
            const trigger = singleTrigger();
            const line = valueLine(trigger);

            expect(textOf(line)).toBe('Saffron Dividend');
            const icon = trigger.querySelector('img');
            expect(icon).toHaveAttribute('src', getAssetTypeIconUrl('STOCK'));
            expect(icon).toHaveClass('w-4', 'h-4');
            expect(textOutside(trigger, [line])).toBe('');
        });

        it('shows no icon for an asset with neither an icon nor a type', () => {
            const bare = asset(27, 'Bare Holding', {identifier_ticker: 'BRH', asset_type: null});
            mountSingle({assets: [...SINGLE_ASSETS, bare], value: 27});
            const trigger = singleTrigger();

            expect(textOf(valueLine(trigger))).toBe('BRH · Bare Holding');
            expect(trigger.querySelector('img')).toBeNull();
        });

        it('adds asset-select-selected-inactive-badge when active is false, and only then', () => {
            const inactive = mountSingle({value: 25});
            const trigger = singleTrigger();
            const badge = within(trigger).getByTestId(INACTIVE_BADGE);
            const line = valueLine(trigger);

            expect(textOf(line), 'the badge sits beside the value line, not in it').toBe('TWL · Tidewater Legacy');
            expect(textOf(badge), 'the badge says something').not.toBe('');
            expect(textOutside(trigger, [line, badge])).toBe('');
            expect(lineCount(trigger), 'the badge stays on the line').toBeLessThanOrEqual(1);
            inactive.unmount();

            // HARBOR is active; UMBER carries no `active` at all, which is not inactive.
            for (const [value, shown] of [
                [21, 'HTM · Harbor Total Market'],
                [26, 'UMB · Umber Fund'],
            ] as const) {
                const view = mountSingle({value});
                expect(textOf(valueLine(singleTrigger())), `asset ${value}`).toBe(shown);
                expect(within(singleTrigger()).queryByTestId(INACTIVE_BADGE), `asset ${value}`).toBeNull();
                view.unmount();
            }
        });
    });
});

// ─── The boundary: ui/select imports nothing from components/risk/ ──────────────────────────

describe('the ui/select boundary', () => {
    /** This folder, from the test's own location: the gate does not depend on where vitest was started. */
    const HERE = dirname(fileURLToPath(import.meta.url));
    const RISK = resolve(HERE, '../../risk');
    /** The files stage 1 adds here. Moved out of `components/risk/`, they are the likeliest to keep a risk import. */
    const STAGE_ONE = ['AssetPickerPanel.svelte', 'SelectPopover.svelte', 'CheckMenu.svelte', 'assetPicker.ts'];

    /** Every module a source names: imports and re-exports, side-effect imports, dynamic imports. */
    function specifiers(source: string): string[] {
        const named = [...source.matchAll(/\bfrom\s*(['"])([^'"\n]+)\1/g)].map((match) => match[2]);
        const bare = [...source.matchAll(/\bimport\s*\(?\s*(['"])([^'"\n]+)\1/g)].map((match) => match[2]);
        return [...named, ...bare];
    }

    /** Whether a specifier written in a file of this folder lands in `components/risk/`. */
    function reachesRisk(specifier: string): boolean {
        if (specifier.startsWith('$lib/')) return /^\$lib\/components\/risk(\/|$)/.test(specifier);
        if (!specifier.startsWith('.')) return false;
        const target = resolve(HERE, specifier);
        return target === RISK || target.startsWith(RISK + sep);
    }

    /** The production sources of this folder: every module but the tests. */
    const productionFiles = (): string[] => readdirSync(HERE).filter((name) => /\.(ts|svelte)$/.test(name) && !name.endsWith('.test.ts'));

    it('sees what it gates: the stage-one files, and an import it knows is there', () => {
        const files = productionFiles();
        for (const name of STAGE_ONE) expect(files, `${name} is read by the gate`).toContain(name);
        expect(specifiers(readFileSync(join(HERE, 'SearchSelect.svelte'), 'utf8'))).toContain('./optionFilter');
    });

    it('recognises a risk import in every form it can take', () => {
        const source = ["import {x} from '../../risk/eligibility';", 'import type {Y} from "$lib/components/risk/eligibility";', "export {z} from './z';", "import './side-effect';", "const lazy = () => import('../../risk/lazy');"].join('\n');
        expect(specifiers(source)).toEqual(['../../risk/eligibility', '$lib/components/risk/eligibility', './z', './side-effect', '../../risk/lazy']);
        expect(specifiers(source).filter(reachesRisk)).toEqual(['../../risk/eligibility', '$lib/components/risk/eligibility', '../../risk/lazy']);
        expect(reachesRisk('../../risk/LabPopover.svelte')).toBe(true);
        expect(reachesRisk('$lib/components/riskless/probe')).toBe(false);
        expect(reachesRisk('$lib/components/ui/select/types')).toBe(false);
    });

    it('imports nothing from components/risk/', () => {
        const offenders = productionFiles().flatMap((name) =>
            specifiers(readFileSync(join(HERE, name), 'utf8'))
                .filter(reachesRisk)
                .map((specifier) => `${name} → ${specifier}`),
        );
        expect(offenders).toEqual([]);
    });
});
