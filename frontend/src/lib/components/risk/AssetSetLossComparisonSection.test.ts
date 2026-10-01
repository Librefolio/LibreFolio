// @vitest-environment jsdom
/**
 * AssetSetLossComparisonSection — component test (Vitest + jsdom).
 *
 * The worst-fall cell carries a sub-line with the episode's duration, formatted through
 * `risk.assetSet.levels.l1.lastedDays`. That key shipped as `lasted {{days}} d` — i18next syntax in
 * an ICU catalogue — and svelte-i18n does not fail on it: `$_()` catches the parse error, logs
 * `[svelte-i18n] Message "…" has syntax error: MALFORMED_ARGUMENT` on `console.warn`, and returns
 * the raw template. The E2E asserted `data-measured`, which was true; nothing read the number.
 *
 * So this file reads it: the **digits** of the duration the payload carries, in every shipped
 * locale, never the words around them. It deliberately does not compare against `$_()` of the same
 * key, the way `L4Replay.test.ts` checks its audit sentence: a formatter that cannot parse the
 * message returns the same raw template on both sides and agrees with itself. And it watches the
 * console, because the log line is the only place the runtime admits the failure.
 *
 * **The barrier sits on the cells, not the rows.** `buildAssetSetHurtRows` builds a row for every
 * selected asset whatever the payloads say; a payload `riskOutput` rejects leaves that row's cells
 * null, and a null worst fall hides the sub-line altogether. "No complaint on the console" is then
 * true about a message nobody formatted. Every assertion therefore stands first on
 * `data-measured="true"` and on the sub-line being in the DOM.
 *
 * ⚠️ Every figure below was **invented while writing this file**: nothing was read off a running
 * backend, and nothing here may be described as measured. The payloads are shaped to be
 * *emittable* — they satisfy the zod schemas `assetSetLevels.ts` parses with and the pydantic
 * validators in `backend/app/schemas/risk.py` that would have produced them: CVaR ≥ VaR, and the
 * episode contract (a negative maximum with ordered peak/trough dates and a recovered ratio; a
 * recovery date only on `recovered`). Dates agree with durations the way `metrics.py` counts them,
 * so the arithmetic can be checked instead of trusted. `metadata` and `data_quality` are omitted
 * although an `ok` result carries both: this component reads neither — the same stated shortcut as
 * `assetSetLevels.test.ts`.
 *
 * ── The DataTable redesign (F, L1°, approved by the developer on 2026-09-30) ─────────────────────
 *
 * The hand-written `<table>` becomes the project's `DataTable`. What the cases below pin of it, and
 * why each part is a contract rather than a detail:
 *
 *  - **the rows are the selection, in its order, all of them** — `tbody tr[data-row-id]`, never
 *    pre-sorted, because the component's own docblock makes the columns sortable *by the reader*
 *    and never ordered by the system; and never paged, because a row on page two reads as an asset
 *    that was not selected, which is the claim the level exists to avoid;
 *  - **a column sorts by the figure it draws.** A loss is drawn negative, so ascending puts the
 *    largest loss first; the rise to peak is drawn positive, so ascending puts the smallest first;
 *    a blank is not a zero and goes last both ways; the third press gives the selection its order
 *    back. The name sorts without its emoji (`plainName`), ties by id, like the matrix's "by name";
 *  - **the headers explain, they do not link.** Each value column's help is the tooltip of its own
 *    title (`headerTooltip` with no URL), so no ⓘ and no anchor: the documentation is the section
 *    frame's manual icon, outside this component;
 *  - **the asset cell is the Assets list's**: the type icon `assetIcons` gives, and the name in the
 *    marquee's marker span on one line — as text, never as markup.
 *
 * The figures the sort cases read are invented like the rest, and chosen so that for every column
 * the ascending order, the descending one and the selection's own are three different orders: a
 * press that did nothing, or a clear that did not clear, cannot pass.
 *
 * **Two ways to find a row, on purpose.** The duration, console and value-cell cases describe
 * behaviour the redesign does not change, so they find a row by the asset id it carries
 * (`[data-asset-id]`, up to its `tr`), whichever element carries it; the DataTable cases find it by
 * `data-row-id`, which is theirs to pin.
 *
 * **The help keys are read twice.** The tooltip cases compare against `$_()` of the same key,
 * because their question is *which* key a column shows. A key missing from the catalogue would come
 * back as itself on both sides and agree with itself, so the catalogues are also read directly,
 * locale by locale — the move `assetSetI18n.test.ts` makes for ICU syntax.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import {get} from 'svelte/store';
import type {z} from 'zod';

import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {OVERFLOW_MARQUEE_SELECTOR} from '$lib/actions/scrollOnOverflow';
import type {schemas} from '$lib/api';
import {_, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import AssetSetLossComparisonSection from './AssetSetLossComparisonSection.svelte';

type VarCvarOutput = z.infer<typeof schemas.RiskAssetSetVarCvarOutput>;
type DrawdownOutput = z.infer<typeof schemas.RiskAssetSetDrawdownOutput>;
type DrawdownItem = DrawdownOutput['items'][number];

// Invented: a window, two assets and their names.
const WINDOW_START = '2022-01-03';
const WINDOW_END = '2024-12-31';
const OPEN_ASSET = 7;
const RECOVERED_ASSET = 9;
const SELECTION = [OPEN_ASSET, RECOVERED_ASSET];
const LABELS: ReadonlyMap<number, string> = new Map([
    [OPEN_ASSET, 'Invented holding A'],
    [RECOVERED_ASSET, 'Invented holding B'],
]);
/**
 * Invented. The panel resolves each icon as `icon_url || getAssetTypeIconUrl(asset_type)`; this
 * component draws whatever it is handed. One asset has an icon and one has none, so both branches
 * of the asset cell are on screen in every mount.
 */
const ICONS: ReadonlyMap<number, string> = new Map([[OPEN_ASSET, '/icons/asset-types/etf.png']]);

/**
 * Invented. Peak 2023-10-20, trough 2024-04-19, still open on the window's last day, so its
 * duration runs peak → last day: 72 days to the end of 2023 plus 366 in leap 2024 = 438. The
 * current drawdown shares that peak and that count. Fell 45% (1 → 0.55), has won back a fifth of
 * the fall (0.55 + 0.2 × 0.45 = 0.64), so it sits 36% below the peak and needs 0.36 / 0.64 = 56.25%.
 */
const OPEN_EPISODE: DrawdownItem = {
    asset_id: OPEN_ASSET,
    current_drawdown: -0.36,
    current_peak_date: '2023-10-20',
    current_drawdown_duration_days: 438,
    maximum_drawdown: -0.45,
    maximum_drawdown_peak_date: '2023-10-20',
    maximum_drawdown_trough_date: '2024-04-19',
    maximum_drawdown_recovery_status: 'open',
    maximum_drawdown_duration_days: 438,
    maximum_drawdown_recovered_ratio: 0.2,
    remaining_to_peak_ratio: 0.5625,
};

/**
 * Invented. Peak 2022-03-29, trough 2022-10-12, back at the peak on 2023-05-02, so its duration
 * runs peak → recovery: 365 + 34 = 399 days. At a new high on the window's last day, which makes
 * the current drawdown a real zero dated that day.
 */
const RECOVERED_EPISODE: DrawdownItem = {
    asset_id: RECOVERED_ASSET,
    current_drawdown: 0,
    current_peak_date: WINDOW_END,
    current_drawdown_duration_days: 0,
    maximum_drawdown: -0.32,
    maximum_drawdown_peak_date: '2022-03-29',
    maximum_drawdown_trough_date: '2022-10-12',
    maximum_drawdown_recovery_status: 'recovered',
    maximum_drawdown_recovery_date: '2023-05-02',
    maximum_drawdown_duration_days: 399,
    maximum_drawdown_recovered_ratio: 1,
    remaining_to_peak_ratio: 0,
};

/** What each row must show, read off the fixture itself so the two can never drift apart. */
const EPISODES = [OPEN_EPISODE, RECOVERED_EPISODE].map((item) => ({assetId: item.asset_id, status: item.maximum_drawdown_recovery_status, days: item.maximum_drawdown_duration_days}));

function ok(instanceId: string, analyticCode: string, output: VarCvarOutput | DrawdownOutput): RiskAnalyticResult {
    return {instance_id: instanceId, analytic_code: analyticCode, status: 'ok', output};
}

// Invented tails. 752 daily observations; a 30-day month is 21 of them, and compounding over 21 consumes 20, hence 732.
const DAILY_VAR = ok('invented-daily-var', 'asset_set_var', {
    kind: 'var_cvar_set',
    confidence_level: 0.95,
    horizon_days: 1,
    horizon_observations: 1,
    observations: 752,
    items: [
        {asset_id: OPEN_ASSET, value_at_risk: 0.031, conditional_value_at_risk: 0.046},
        {asset_id: RECOVERED_ASSET, value_at_risk: 0.012, conditional_value_at_risk: 0.019},
    ],
});
const MONTHLY_VAR = ok('invented-monthly-var', 'asset_set_var', {
    kind: 'var_cvar_set',
    confidence_level: 0.95,
    horizon_days: 30,
    horizon_observations: 21,
    observations: 732,
    items: [
        {asset_id: OPEN_ASSET, value_at_risk: 0.118, conditional_value_at_risk: 0.171},
        {asset_id: RECOVERED_ASSET, value_at_risk: 0.047, conditional_value_at_risk: 0.069},
    ],
});
// Listed against the selection's order, so a row can only find its episode by `asset_id`.
const DRAWDOWN = ok('invented-drawdown', 'asset_set_drawdown', {
    kind: 'drawdown_set',
    available_start: WINDOW_START,
    available_end: WINDOW_END,
    calculation_basis: 'price_only_close',
    return_basis: 'price_only',
    items: [RECOVERED_EPISODE, OPEN_EPISODE],
});

function mount(): void {
    render(AssetSetLossComparisonSection, {props: {assetIds: SELECTION, assetLabels: LABELS, assetIcons: ICONS, dailyVar: DAILY_VAR, monthlyVar: MONTHLY_VAR, drawdown: DRAWDOWN, loading: false}});
}

function normalize(text: string | null): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/**
 * An asset's row, found by the asset id it carries — whichever element carries it — and walked up
 * to its `tr`. The cases that use it describe behaviour the DataTable redesign leaves alone, so they
 * must not care whether the id sits on the row or on the asset's own cell; the DataTable structure
 * is pinned by cases of its own, through `data-row-id`.
 */
function rowOf(assetId: number): HTMLElement {
    const carriers = screen.getByTestId('risk-asset-set-l1-table').querySelectorAll<HTMLElement>(`[data-asset-id="${assetId}"]`);
    const rows = [...new Set([...carriers].map((carrier) => carrier.closest('tr')))].filter((row): row is HTMLTableRowElement => row !== null);
    expect(rows, `asset ${assetId} has no row of its own`).toHaveLength(1);
    return rows[0];
}

/** The presence barrier: the episode parsed, belongs to this row, and its sub-line was rendered. */
function durationSubLine({assetId, status}: (typeof EPISODES)[number]): HTMLElement {
    const cell = within(rowOf(assetId)).getByTestId('risk-asset-set-l1-worstFall');
    expect(cell, `asset ${assetId}: the drawdown payload did not survive riskOutput(…, schemas.RiskAssetSetDrawdownOutput) — the cell is a dash and no message was formatted`).toHaveAttribute('data-measured', 'true');
    expect(cell, `asset ${assetId}: the worst-fall cell is not showing this asset's own episode`).toHaveAttribute('data-recovery', status);
    return within(cell).getByTestId('risk-asset-set-l1-worstFall-days');
}

let consoleWarn: MockInstance<Console['warn']>;
let consoleError: MockInstance<Console['error']>;

beforeEach(() => {
    // Pass-through spies: they record, and an unrelated warning still reaches the run's output.
    consoleWarn = vi.spyOn(console, 'warn');
    consoleError = vi.spyOn(console, 'error');
});

afterEach(() => {
    consoleWarn.mockRestore();
    consoleError.mockRestore();
});

/** svelte-i18n logs the id in the first argument and the parser's verdict in the second: join them. */
function i18nComplaints(): string[] {
    const lines = [...consoleWarn.mock.calls.map((args) => `console.warn: ${args.map(String).join(' ')}`), ...consoleError.mock.calls.map((args) => `console.error: ${args.map(String).join(' ')}`)];
    return lines.filter((line) => line.includes('[svelte-i18n]') || line.includes('MALFORMED_ARGUMENT'));
}

describe('AssetSetLossComparisonSection — the harness itself', () => {
    beforeAll(async () => {
        await setupI18n('en');
    });

    it('every fixture survives the parsers the component reads it through', () => {
        mount();

        expect(screen.getByTestId('risk-asset-set-l1-table')).toHaveAttribute('data-row-count', String(SELECTION.length));
        for (const assetId of SELECTION) {
            const row = rowOf(assetId);
            for (const column of ['badDay', 'badMonth', 'worstFall', 'currentFall', 'toPeak']) {
                expect(within(row).getByTestId(`risk-asset-set-l1-${column}`), `asset ${assetId}: ${column} is a dash — its fixture was rejected by a schema, not measured`).toHaveAttribute('data-measured', 'true');
            }
        }
    });

    it('the console watch catches what svelte-i18n emits for a message it cannot parse', () => {
        consoleWarn.mockImplementation(() => {}); // deliberate: kept out of the run's output
        const rendered = get(_)('test.invented.malformed', {default: 'lasted {{days}} d', values: {days: OPEN_EPISODE.maximum_drawdown_duration_days}});

        // Logged and returned raw rather than thrown — the behaviour that let the defect ship.
        expect(rendered).toBe('lasted {{days}} d');
        expect(i18nComplaints()).toContainEqual(expect.stringContaining('MALFORMED_ARGUMENT'));
    });
});

describe.each([...SUPPORTED_LOCALES])('AssetSetLossComparisonSection — the worst-fall duration, in %s', (locale) => {
    beforeAll(async () => {
        await setupI18n(locale);
    });

    it('prints the number of days each worst fall lasted', () => {
        mount();

        for (const episode of EPISODES) {
            const text = normalize(durationSubLine(episode).textContent);
            expect(text.match(/\d+/g) ?? [], `asset ${episode.assetId}: the sub-line reads ${JSON.stringify(text)} — the ${episode.days} days in the payload never reached the screen`).toContain(String(episode.days));
        }
    });

    it('formats the sub-line without svelte-i18n reporting a broken message', () => {
        mount();

        // Barrier: the message was formatted with a value, so a quiet console means it parsed — not that it never ran.
        for (const episode of EPISODES) durationSubLine(episode);
        expect(i18nComplaints(), `${locale}: svelte-i18n could not format a message while the section rendered`).toEqual([]);
    });
});

// ═══════════════════════════════════════════════════════════════════════════════════════════════
// The DataTable redesign
// ═══════════════════════════════════════════════════════════════════════════════════════════════

/** The five value columns, in the order that carries the argument: a day, a month, the window, today, the way back. */
const VALUE_COLUMNS = ['badDay', 'badMonth', 'worstFall', 'currentFall', 'toPeak'] as const;
type ValueColumn = (typeof VALUE_COLUMNS)[number];
/** Every column, the asset first. */
const COLUMNS = ['name', ...VALUE_COLUMNS] as const;

/** The key a value column's help is worded from: the tooltip of its own title. */
function helpKey(column: ValueColumn): string {
    return `risk.assetSet.levels.l1.columnHelp.${column}`;
}

/** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/**
 * The sort fixture. Invented, like everything in this file.
 *
 * Four assets, one of them measured by no analytic: the state the backend leaves when it cannot
 * prepare an asset's series and excludes it from every result of the request. The figures are
 * chosen so that, for each column, ascending, descending and the selection's own order are three
 * different orders — see `LOSS_SORTS` — and the names so that the selection is not alphabetical
 * either: a table that sorted by anything on opening would not draw `SORT_SELECTION`.
 */
const SORT_UNMEASURED = 62;
const SORT_SELECTION: number[] = [SORT_UNMEASURED, 64, 61, 63];
const SORT_LABELS: ReadonlyMap<number, string> = new Map([
    [61, 'Invented holding C'],
    [62, 'Invented holding D'],
    [63, 'Invented holding A'],
    [64, 'Invented holding B'],
]);
const SORT_ICONS: ReadonlyMap<number, string> = new Map([
    [61, '/icons/asset-types/stock.png'],
    [63, '/icons/asset-types/bond.png'],
]);

// Invented tails, CVaR ≥ VaR; the one-day and the one-month orders differ on purpose.
const SORT_DAILY_VAR = ok('invented-sort-daily-var', 'asset_set_var', {
    kind: 'var_cvar_set',
    confidence_level: 0.95,
    horizon_days: 1,
    horizon_observations: 1,
    observations: 752,
    items: [
        {asset_id: 61, value_at_risk: 0.007, conditional_value_at_risk: 0.01},
        {asset_id: 63, value_at_risk: 0.034, conditional_value_at_risk: 0.05},
        {asset_id: 64, value_at_risk: 0.021, conditional_value_at_risk: 0.03},
    ],
});
const SORT_MONTHLY_VAR = ok('invented-sort-monthly-var', 'asset_set_var', {
    kind: 'var_cvar_set',
    confidence_level: 0.95,
    horizon_days: 30,
    horizon_observations: 21,
    observations: 732,
    items: [
        {asset_id: 61, value_at_risk: 0.083, conditional_value_at_risk: 0.12},
        {asset_id: 63, value_at_risk: 0.049, conditional_value_at_risk: 0.07},
        {asset_id: 64, value_at_risk: 0.14, conditional_value_at_risk: 0.2},
    ],
});

/**
 * Invented. Peak 2024-01-02, still open on the window's last day, so its duration runs peak → last
 * day: 29 days left of January, then 29 + 31 + 30 + 31 + 30 + 31 + 31 + 30 + 31 + 30 + 31 in leap
 * 2024 = 364. The current drawdown shares that peak and that count. Fell 45% (1 → 0.55) and is back
 * at 0.95: it has won back 0.40 / 0.45 of the fall and needs 0.05 / 0.95 to close it.
 */
const SORT_DEEP_OPEN: DrawdownItem = {
    asset_id: 61,
    current_drawdown: -0.05,
    current_peak_date: '2024-01-02',
    current_drawdown_duration_days: 364,
    maximum_drawdown: -0.45,
    maximum_drawdown_peak_date: '2024-01-02',
    maximum_drawdown_trough_date: '2024-05-31',
    maximum_drawdown_recovery_status: 'open',
    maximum_drawdown_duration_days: 364,
    maximum_drawdown_recovered_ratio: 0.4 / 0.45,
    remaining_to_peak_ratio: 0.05 / 0.95,
};

/**
 * Invented. Peak 2023-09-01, still open: 121 days to the end of 2023 plus 366 in leap 2024 = 487.
 * Fell 30% (1 → 0.70) and is at 0.75: it has won back 0.05 / 0.30 of the fall, sits 25% below the
 * peak and needs 0.25 / 0.75.
 */
const SORT_MIDDLE_OPEN: DrawdownItem = {
    asset_id: 63,
    current_drawdown: -0.25,
    current_peak_date: '2023-09-01',
    current_drawdown_duration_days: 487,
    maximum_drawdown: -0.3,
    maximum_drawdown_peak_date: '2023-09-01',
    maximum_drawdown_trough_date: '2024-03-01',
    maximum_drawdown_recovery_status: 'open',
    maximum_drawdown_duration_days: 487,
    maximum_drawdown_recovered_ratio: 0.05 / 0.3,
    remaining_to_peak_ratio: 0.25 / 0.75,
};

/**
 * Invented. Peak 2022-06-01, trough 2022-07-15, back at the peak on 2022-10-03, so its duration runs
 * peak → recovery: 29 + 31 + 31 + 30 + 3 = 124 days. At a new high on the window's last day, which
 * makes the current drawdown a real zero dated that day.
 */
const SORT_SHALLOW_RECOVERED: DrawdownItem = {
    asset_id: 64,
    current_drawdown: 0,
    current_peak_date: WINDOW_END,
    current_drawdown_duration_days: 0,
    maximum_drawdown: -0.12,
    maximum_drawdown_peak_date: '2022-06-01',
    maximum_drawdown_trough_date: '2022-07-15',
    maximum_drawdown_recovery_status: 'recovered',
    maximum_drawdown_recovery_date: '2022-10-03',
    maximum_drawdown_duration_days: 124,
    maximum_drawdown_recovered_ratio: 1,
    remaining_to_peak_ratio: 0,
};

// Listed against the selection's order, so a row can only find its episode by `asset_id`.
const SORT_DRAWDOWN = ok('invented-sort-drawdown', 'asset_set_drawdown', {
    kind: 'drawdown_set',
    available_start: WINDOW_START,
    available_end: WINDOW_END,
    calculation_basis: 'price_only_close',
    return_basis: 'price_only',
    items: [SORT_SHALLOW_RECOVERED, SORT_DEEP_OPEN, SORT_MIDDLE_OPEN],
});

/**
 * What each measured cell of the sort fixture draws, read off the figures above by hand. The two
 * zeros of asset 64 (current fall, rise to peak) are measured and left out on purpose: how the sign
 * of a zero is drawn is not this redesign's decision.
 */
const SORT_DRAWN: ReadonlyMap<number, Partial<Record<ValueColumn, string>>> = new Map<number, Partial<Record<ValueColumn, string>>>([
    [61, {badDay: '\u22121.0%', badMonth: '\u221212.0%', worstFall: '\u221245.0%', currentFall: '\u22125.0%', toPeak: '+5.3%'}],
    [63, {badDay: '\u22125.0%', badMonth: '\u22127.0%', worstFall: '\u221230.0%', currentFall: '\u221225.0%', toPeak: '+33.3%'}],
    [64, {badDay: '\u22123.0%', badMonth: '\u221220.0%', worstFall: '\u221212.0%'}],
]);
const SORT_RECOVERY: ReadonlyMap<number, string> = new Map([
    [61, 'open'],
    [63, 'open'],
    [64, 'recovered'],
]);

/**
 * The orders the four loss columns must take, written out by hand from the figures drawn:
 *   bad day      61 −1.0   63 −5.0   64 −3.0
 *   bad month    61 −12.0  63 −7.0   64 −20.0
 *   worst fall   61 −45.0  63 −30.0  64 −12.0
 *   below peak   61 −5.0   63 −25.0  64 −0.0
 * and 62 blank everywhere. Ascending is the most negative first — the largest loss.
 */
const LOSS_SORTS = [
    {column: 'badDay', ascending: [63, 64, 61, SORT_UNMEASURED], descending: [61, 64, 63, SORT_UNMEASURED]},
    {column: 'badMonth', ascending: [64, 61, 63, SORT_UNMEASURED], descending: [63, 61, 64, SORT_UNMEASURED]},
    {column: 'worstFall', ascending: [61, 63, 64, SORT_UNMEASURED], descending: [64, 63, 61, SORT_UNMEASURED]},
    {column: 'currentFall', ascending: [63, 61, 64, SORT_UNMEASURED], descending: [64, 61, 63, SORT_UNMEASURED]},
] as const;

/** The rise to peak, drawn positive: 61 +5.3, 63 +33.3, 64 +0.0, 62 blank. Ascending is the smallest rise first. */
const TO_PEAK_ASCENDING = [64, 61, 63, SORT_UNMEASURED];
const TO_PEAK_DESCENDING = [63, 61, 64, SORT_UNMEASURED];

/**
 * The name fixture. Invented names, decorated the way real ones are (a flag, a marker in front).
 *
 * Chosen so that each wrong way to sort gives a different, wrong order: a collator reading the raw
 * name files every emoji ahead of every letter, a code-point comparison files them after every
 * letter, and a stable sort without the id tie-break keeps 🇪🇺 Alpha ahead of Alpha, because the
 * selection lists it first.
 */
const NAMES = [
    {assetId: 75, label: '🇪🇺 Alpha', plain: 'Alpha'},
    {assetId: 72, label: 'Gamma', plain: 'Gamma'},
    {assetId: 71, label: '🇪🇺 Zeta', plain: 'Zeta'},
    {assetId: 74, label: 'Alpha', plain: 'Alpha'},
    {assetId: 73, label: '👑 Beta', plain: 'Beta'},
];
const NAME_SELECTION = NAMES.map(({assetId}) => assetId);
const NAME_LABELS: ReadonlyMap<number, string> = new Map(NAMES.map(({assetId, label}): [number, string] => [assetId, label]));
const PLAIN_NAMES: ReadonlyMap<number, string> = new Map(NAMES.map(({assetId, plain}): [number, string] => [assetId, plain]));
/** Alpha (74) before 🇪🇺 Alpha (75): the same name without its emoji, and the lower id first. */
const NAME_ASCENDING = [74, 75, 73, 72, 71];

/** More assets than DataTable's default page holds (10), in an order no column would produce. */
const WIDE_SELECTION = [...Array(12).keys()].map((index) => 112 - index);
const WIDE_LABELS: ReadonlyMap<number, string> = new Map(WIDE_SELECTION.map((assetId): [number, string] => [assetId, `Invented holding ${assetId}`]));

/** Names a provider or a user could type, each of which is markup if it reaches `{@html}` unescaped. */
const MARKUP_NAMES = [
    {assetId: 81, label: '<b>Bold</b>', forbidden: 'b'},
    {assetId: 82, label: '<img src=x onerror=alert(1)>', forbidden: 'img'},
    // Not markup, but an entity escaped twice would print `&amp;` in the middle of a real name.
    {assetId: 83, label: 'SPDR® S&P 500® ETF', forbidden: null},
] as const;
const MARKUP_ICONS: ReadonlyMap<number, string> = new Map([
    [81, '/icons/asset-types/stock.png'],
    [83, '/icons/asset-types/etf.png'],
]);

interface MountProps {
    assetIds: number[];
    assetLabels: ReadonlyMap<number, string>;
    assetIcons: ReadonlyMap<number, string>;
    dailyVar?: RiskAnalyticResult | null;
    monthlyVar?: RiskAnalyticResult | null;
    drawdown?: RiskAnalyticResult | null;
}

function mountWith({assetIds, assetLabels, assetIcons, dailyVar = null, monthlyVar = null, drawdown = null}: MountProps): void {
    render(AssetSetLossComparisonSection, {props: {assetIds, assetLabels, assetIcons, dailyVar, monthlyVar, drawdown, loading: false}});
}

function mountSortFixture(): void {
    mountWith({assetIds: SORT_SELECTION, assetLabels: SORT_LABELS, assetIcons: SORT_ICONS, dailyVar: SORT_DAILY_VAR, monthlyVar: SORT_MONTHLY_VAR, drawdown: SORT_DRAWDOWN});
}

/** The wrapper the level publishes its row count on; the DataTable sits inside it. */
function l1Table(): HTMLElement {
    return screen.getByTestId('risk-asset-set-l1-table');
}

/** The asset ids of the drawn rows, top to bottom, as DataTable publishes them. */
function drawnOrder(): number[] {
    return [...l1Table().querySelectorAll<HTMLElement>('tbody tr[data-row-id]')].map((row) => Number(row.dataset.rowId));
}

/** One asset's DataTable row, by the id DataTable writes on it. */
function rowById(assetId: number): HTMLElement {
    const rows = l1Table().querySelectorAll<HTMLElement>(`tbody tr[data-row-id="${assetId}"]`);
    expect(rows, `asset ${assetId}: no DataTable row of its own — tbody tr[data-row-id="${assetId}"]`).toHaveLength(1);
    return rows[0];
}

/** The column ids of the header row, left to right. */
function headerOrder(): string[] {
    return [...l1Table().querySelectorAll<HTMLElement>('thead th[data-testid^="dt-header-"]')].map((header) => (header.dataset.testid ?? '').replace('dt-header-', ''));
}

/** One asset's name cell: the icon and the name, carrying the asset's id. */
function nameCell(assetId: number): HTMLElement {
    const cells = l1Table().querySelectorAll<HTMLElement>(`[data-testid="risk-asset-set-l1-name"][data-asset-id="${assetId}"]`);
    expect(cells, `asset ${assetId}: no name cell of its own — [data-testid="risk-asset-set-l1-name"][data-asset-id="${assetId}"]`).toHaveLength(1);
    return cells[0];
}

/**
 * The span holding the name, found by the marker the marquee itself attaches by
 * (`attachOverflowMarqueeToDescendants` scans for it): a functional hook, not a style.
 */
function marqueeOf(cell: HTMLElement): HTMLElement {
    const spans = [...cell.querySelectorAll<HTMLElement>(OVERFLOW_MARQUEE_SELECTOR)];
    expect(spans, 'the name must sit in exactly one marquee span, or it wraps instead of scrolling').toHaveLength(1);
    expect(spans[0].tagName).toBe('SPAN');
    return spans[0];
}

/** What a value cell draws as its figure, the worst fall's duration sub-line set aside. */
function figureText(cell: HTMLElement): string {
    const copy = cell.cloneNode(true) as HTMLElement;
    copy.querySelectorAll('[data-testid="risk-asset-set-l1-worstFall-days"]').forEach((node) => node.remove());
    return normalize(copy.textContent);
}

/** That figure as the signed number it reads as, or null for the blank. */
function drawnFigure(cell: HTMLElement): number | null {
    const text = figureText(cell);
    if (text === '\u2014') return null;
    const match = /^([\u2212+]?)(\d+(?:\.\d+)?)%$/.exec(text);
    if (!match) throw new Error(`a value cell draws ${JSON.stringify(text)}: neither a percentage nor the blank`);
    return match[1] === '\u2212' ? -Number(match[2]) : Number(match[2]);
}

/**
 * The drawn column read top to bottom: its figures in the stated direction, the blanks after them.
 *
 * Independent of the orders written out by hand in `LOSS_SORTS`: it reads the screen, so it is the
 * rule itself — "sorted by the figure as drawn" — rather than one instance of it.
 */
function expectSortedAsDrawn(column: ValueColumn, direction: 'asc' | 'desc'): void {
    const figures = drawnOrder().map((assetId) => drawnFigure(within(rowById(assetId)).getByTestId(`risk-asset-set-l1-${column}`)));
    const measured = figures.filter((figure): figure is number => figure !== null);
    expect(figures.slice(measured.length), `${column} ${direction}: a blank is drawn above a figure — an unmeasured asset goes last whichever way the column points`).toEqual(figures.slice(measured.length).map(() => null));
    expect(measured, `${column} ${direction}: the column is not in the order of the figures it draws`).toEqual([...measured].sort((left, right) => (direction === 'asc' ? left - right : right - left)));
}

/** Press a column's title once, and read where the header says the sort now stands. */
async function press(column: string, expected: 'asc' | 'desc' | 'none'): Promise<void> {
    await fireEvent.click(screen.getByTestId(`dt-sort-${column}`));
    expect(screen.getByTestId(`dt-header-${column}`), `${column}: one more press must leave the header at ${expected}`).toHaveAttribute('data-sort', expected);
}

/**
 * DataTable keeps widths and order in `localStorage`. Stubbed per case — as
 * `DataTableHeaderTooltip.test.ts` does — so no case inherits another's layout, and so the keys the
 * table reads can be seen.
 */
const storage = new Map<string, string>();
const storageReads: string[] = [];

function dataTableHarness(): void {
    beforeAll(async () => {
        await setupI18n('en');
    });

    beforeEach(() => {
        storage.clear();
        storageReads.length = 0;
        vi.stubGlobal('localStorage', {
            getItem: (key: string) => {
                storageReads.push(key);
                return storage.get(key) ?? null;
            },
            setItem: (key: string, value: string) => void storage.set(key, value),
            removeItem: (key: string) => void storage.delete(key),
        });
    });

    afterEach(() => {
        cleanup();
        vi.unstubAllGlobals();
    });
}

describe('AssetSetLossComparisonSection — the table is the project DataTable', () => {
    dataTableHarness();

    it('draws the selection in its own order under the six columns, nothing sorted and every column sortable', () => {
        mountSortFixture();
        const table = l1Table();

        expect(table.querySelector('table'), 'risk-asset-set-l1-table must wrap the DataTable, not be the table itself').not.toBeNull();
        expect(table).toHaveAttribute('data-row-count', String(SORT_SELECTION.length));
        expect(headerOrder(), "the header row is not DataTable's, or not the six columns in the order that carries the argument").toEqual([...COLUMNS]);
        expect(drawnOrder(), "the rows must open in the selection's own order: the reader sorts, the system never ranks").toEqual(SORT_SELECTION);

        for (const column of COLUMNS) {
            expect(screen.getByTestId(`dt-header-${column}`), `${column} opens sorted`).toHaveAttribute('data-sort', 'none');
            expect(screen.getByTestId(`dt-sort-${column}`), `${column} cannot be sorted`).toBeEnabled();
        }

        // Each row holds its own asset's cells, one of each.
        for (const assetId of SORT_SELECTION) {
            const row = rowById(assetId);
            expect(
                within(row)
                    .getAllByTestId('risk-asset-set-l1-name')
                    .map((cell) => cell.dataset.assetId),
                `asset ${assetId}: the row's name cell must carry the row's asset`,
            ).toEqual([String(assetId)]);
            for (const column of VALUE_COLUMNS) expect(within(row).getAllByTestId(`risk-asset-set-l1-${column}`), `asset ${assetId}: ${column}`).toHaveLength(1);
        }
    });

    it('draws every selected asset however many there are, with no pagination and no selection, filter or action chrome', async () => {
        mountWith({assetIds: WIDE_SELECTION, assetLabels: WIDE_LABELS, assetIcons: new Map()});

        expect(drawnOrder(), `${WIDE_SELECTION.length} assets selected and DataTable's default page holds 10: a row on page two reads as an asset nobody selected`).toEqual(WIDE_SELECTION);
        expect(screen.getByTestId('risk-asset-set-l1-table')).toHaveAttribute('data-row-count', String(WIDE_SELECTION.length));
        expect(screen.queryByTestId('data-table-pagination')).toBeNull();
        expect(screen.queryByTestId('dt-select-all'), 'a comparison selects nothing').toBeNull();
        expect(document.querySelectorAll('[data-testid^="dt-row-checkbox-"]')).toHaveLength(0);
        expect(document.querySelectorAll('[data-testid^="col-filter-trigger-"]'), 'no column filters: the selection is the filter').toHaveLength(0);
        expect(document.querySelectorAll('[data-testid^="row-actions-"]'), 'no row actions').toHaveLength(0);

        // Nor by a click: L3°'s rows select because L3° has a scatter to link a row to; L1° has no chart.
        await fireEvent.click(rowById(WIDE_SELECTION[0]));
        expect(rowById(WIDE_SELECTION[0]), 'a click selected an L1° row: this table has no chart for a selection to point at').toHaveAttribute('data-selected', 'false');
    });

    it('keeps its layout under its own storage key', () => {
        mountSortFixture();

        expect(
            storageReads.filter((key) => key.includes('dataTable_risk-asset-set-l1_')),
            'DataTable read no preference under storageKey "risk-asset-set-l1": the level would share its widths and order with another table',
        ).not.toEqual([]);
    });
});

describe('AssetSetLossComparisonSection — the headers explain, they do not link', () => {
    dataTableHarness();

    it('has no anchor, no info icon and no documentation link in its header row', () => {
        mountSortFixture();

        // Presence first: the header row is DataTable's and holds all six titles, so the absences
        // below are about a header that exists.
        expect(headerOrder(), "the header row is not DataTable's: its six titles must be there before their links can be absent").toEqual([...COLUMNS]);
        const headerRow = l1Table().querySelector('thead tr');
        expect(headerRow).not.toBeNull();
        expect(headerRow?.querySelectorAll('a'), "a link in the header row: the documentation is the frame's manual, the header only explains").toHaveLength(0);
        expect(document.querySelectorAll('[data-testid^="dt-header-tooltip-"]'), 'an ⓘ beside a title: DataTable draws one only for a tooltip with a URL, and these have none').toHaveLength(0);
        expect(document.querySelectorAll('[data-testid^="risk-asset-set-l1-docs-"]'), 'the per-column documentation links are gone').toHaveLength(0);
    });

    it.each(VALUE_COLUMNS)('%s: its title reveals the help worded from its own columnHelp key', async (column) => {
        mountSortFixture();

        // Revealed the way `DataTableHeaderTooltip.test.ts` reveals a sortable title's tooltip: a
        // press pins it open. The press also sorts, which is not this case's subject.
        await fireEvent.click(screen.getByTestId(`dt-sort-${column}`));
        const help = await screen.findByRole('tooltip');

        expect(normalize(help.textContent), `${column}: the tooltip is not the message of ${helpKey(column)}`).toBe(normalize(get(_)(helpKey(column))));
    });

    it('name: the same press on its title reveals nothing — the one column without help', async () => {
        mountSortFixture();

        // Positive control: on this very mount, the press does reveal a value column's help.
        await fireEvent.click(screen.getByTestId('dt-sort-badDay'));
        const help = await screen.findByRole('tooltip');
        await waitFor(() => expect(help).toHaveAttribute('data-dismissable', 'true'));
        await fireEvent.click(document.body);
        await waitFor(() => expect(screen.queryByRole('tooltip')).toBeNull());

        await fireEvent.click(screen.getByTestId('dt-sort-name'));
        // The press landed — the column sorted — so the absence below is about a press that happened.
        expect(screen.getByTestId('dt-header-name')).toHaveAttribute('data-sort', 'asc');
        expect(screen.queryByRole('tooltip'), 'the asset column has no help of its own to show').toBeNull();
    });
});

describe("AssetSetLossComparisonSection — every value column's help is in every catalogue", () => {
    it.each([...SUPPORTED_LOCALES])('%s.json', (locale) => {
        const catalogue = CATALOGUES[locale];

        // Barrier: the walk reaches the level — the titles the help belongs to are read from the same subtree.
        for (const column of VALUE_COLUMNS) {
            expect(typeof at(catalogue, `risk.assetSet.levels.l1.columns.${column}`), `${locale}.json: the walk never reached risk.assetSet.levels.l1.columns.${column}`).toBe('string');
        }

        const missing = VALUE_COLUMNS.map(helpKey).filter((key) => {
            const message = at(catalogue, key);
            return typeof message !== 'string' || message.trim() === '';
        });
        expect(missing, `${locale}.json: these tooltips would print their own key`).toEqual([]);
    });
});

describe('AssetSetLossComparisonSection — the asset cell', () => {
    dataTableHarness();

    it('draws the icon assetIcons gives an asset, and the name alone for an asset it gives none', () => {
        mount();

        const withIcon = nameCell(OPEN_ASSET);
        const icons = within(withIcon).getAllByTestId('risk-asset-set-l1-icon');
        expect(icons, 'one icon, beside the name').toHaveLength(1);
        expect(icons[0].tagName).toBe('IMG');
        expect(icons[0].getAttribute('src'), 'the icon must be the one the map gives this asset').toBe(ICONS.get(OPEN_ASSET));

        const withoutIcon = nameCell(RECOVERED_ASSET);
        expect(within(withoutIcon).queryByTestId('risk-asset-set-l1-icon'), 'no icon in the map, no icon drawn').toBeNull();
        expect(withoutIcon.querySelectorAll('img'), 'no stand-in image either').toHaveLength(0);
        expect(normalize(marqueeOf(withoutIcon).textContent), 'the name stays when the icon is missing').toBe(LABELS.get(RECOVERED_ASSET));
    });

    it('holds each name in the marquee span of its own cell', () => {
        mount();

        for (const assetId of SELECTION) {
            expect(normalize(marqueeOf(nameCell(assetId)).textContent), `asset ${assetId}`).toBe(LABELS.get(assetId));
        }
    });

    it.each(MARKUP_NAMES)('draws $label as text, never as markup', ({assetId, label, forbidden}) => {
        mountWith({assetIds: MARKUP_NAMES.map((entry) => entry.assetId), assetLabels: new Map(MARKUP_NAMES.map((entry): [number, string] => [entry.assetId, entry.label])), assetIcons: MARKUP_ICONS});

        const cell = nameCell(assetId);
        expect(normalize(marqueeOf(cell).textContent), 'the name must reach the screen character for character').toBe(label);
        if (forbidden !== null) {
            const smuggled = [...cell.querySelectorAll(forbidden)].filter((node) => node.getAttribute('data-testid') !== 'risk-asset-set-l1-icon');
            expect(smuggled, `the name became a <${forbidden}> element`).toHaveLength(0);
        }
    });
});

describe('AssetSetLossComparisonSection — the value cells keep their contract', () => {
    dataTableHarness();

    it('draws a loss with U+2212, the rise with +, and a dash marked unmeasured where nothing was measured', () => {
        mountSortFixture();

        for (const [assetId, drawn] of SORT_DRAWN) {
            const row = rowOf(assetId);
            for (const column of VALUE_COLUMNS) {
                const cell = within(row).getByTestId(`risk-asset-set-l1-${column}`);
                expect(cell, `asset ${assetId}: ${column} is not measured — its fixture was rejected by a schema`).toHaveAttribute('data-measured', 'true');
                const figure = drawn[column];
                if (figure !== undefined) expect(figureText(cell), `asset ${assetId}: ${column}`).toBe(figure);
            }
            expect(within(row).getByTestId('risk-asset-set-l1-worstFall'), `asset ${assetId}: the worst fall's recovery state`).toHaveAttribute('data-recovery', SORT_RECOVERY.get(assetId));
        }

        const blank = rowOf(SORT_UNMEASURED);
        for (const column of VALUE_COLUMNS) {
            const cell = within(blank).getByTestId(`risk-asset-set-l1-${column}`);
            expect(cell, `${column}: an unmeasured asset must say so, never print a figure`).toHaveAttribute('data-measured', 'false');
            expect(figureText(cell), `${column}: the blank is an em-dash, not a zero`).toBe('\u2014');
        }
        expect(within(blank).getByTestId('risk-asset-set-l1-worstFall')).toHaveAttribute('data-recovery', '');
        expect(within(blank).queryByTestId('risk-asset-set-l1-worstFall-days'), 'no duration for a fall nobody measured').toBeNull();
    });
});

describe('AssetSetLossComparisonSection — a column sorts by the figure it draws', () => {
    dataTableHarness();

    it.each(LOSS_SORTS)('$column: ascending puts the largest loss first, descending the smallest, the blank last both ways, and the third press restores the selection', async ({column, ascending, descending}) => {
        mountSortFixture();
        expect(drawnOrder(), 'the rows must open in the selection order').toEqual(SORT_SELECTION);

        await press(column, 'asc');
        expect(drawnOrder(), `${column} ascending: the largest loss — the most negative figure — first, the blank last`).toEqual(ascending);
        expectSortedAsDrawn(column, 'asc');

        await press(column, 'desc');
        expect(drawnOrder(), `${column} descending: the smallest loss first, the blank still last`).toEqual(descending);
        expectSortedAsDrawn(column, 'desc');

        await press(column, 'none');
        expect(drawnOrder(), `${column}: the third press must give the rows back in the selection's order`).toEqual(SORT_SELECTION);
    });

    it('toPeak: the rise is drawn positive, so ascending puts the smallest first; the blank is last both ways', async () => {
        mountSortFixture();
        expect(drawnOrder()).toEqual(SORT_SELECTION);

        await press('toPeak', 'asc');
        expect(drawnOrder(), 'toPeak ascending: the smallest rise first — it is a gain, not a loss').toEqual(TO_PEAK_ASCENDING);
        expectSortedAsDrawn('toPeak', 'asc');

        await press('toPeak', 'desc');
        expect(drawnOrder(), 'toPeak descending: the largest rise first, the blank still last').toEqual(TO_PEAK_DESCENDING);
        expectSortedAsDrawn('toPeak', 'desc');

        await press('toPeak', 'none');
        expect(drawnOrder()).toEqual(SORT_SELECTION);
    });

    it('name: sorts by the name without its emoji, ties broken by id, and the third press restores the selection', async () => {
        mountWith({assetIds: NAME_SELECTION, assetLabels: NAME_LABELS, assetIcons: new Map()});
        expect(drawnOrder()).toEqual(NAME_SELECTION);

        await press('name', 'asc');
        expect(drawnOrder(), 'ascending by the name without its emoji — a flag files under its name, not ahead of every letter — and Alpha (74) before 🇪🇺 Alpha (75), the lower id first').toEqual(NAME_ASCENDING);

        // Descending is read as names: which of the two Alphas comes first is the tie-break's
        // direction, and the contract says "ties by id" without naming one for this side.
        await press('name', 'desc');
        expect(
            drawnOrder().map((assetId) => PLAIN_NAMES.get(assetId)),
            'descending by the name without its emoji',
        ).toEqual(['Zeta', 'Gamma', 'Beta', 'Alpha', 'Alpha']);

        await press('name', 'none');
        expect(drawnOrder(), "the third press must give the rows back in the selection's order").toEqual(NAME_SELECTION);
    });
});
