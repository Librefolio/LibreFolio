// @vitest-environment jsdom
/**
 * AssetSetMoveComparisonSection — component test (Vitest + jsdom), RN-19.
 *
 * «How did each one move?» is the positive twin of the loss table (developer's decision of 12/11/2026): the same
 * project `DataTable`, the selection's rows in their own order, each value column as wide as its title and explained in
 * the tooltip of that title, a dash that says why it is a dash. What this file pins of it:
 *
 *  - **the columns fixed on 12/11**, in the order that carries the argument — the best day, the best 30 days, the
 *    largest rally, gains against losses, the positive days, the semi-deviation — and four **hidden** until the reader
 *    asks for them: the two of Q21 c (the average up and down day, the longest positive streak) and, the consultant's
 *    answer of 17/11, «below the peak, on average» (ADD) and «extreme days» (the kurtosis over the bell curve's);
 *  - **each figure from the answer that measures it**: the KPI instance of L1°'s wave for the day-level measures, the
 *    monthly VaR's best window for the best 30 days, the drawdown's largest rally — with the dates under the figure;
 *  - **a blank says why**: the backend's warning that names the asset (no gaining day, no losing day, no day below
 *    the target) on that cell; the table's blank note on any other dash;
 *  - **the states** (loading, failed, discarded, empty) under their own test ids, the twin's;
 *  - **the sizes** the twin's rule gives: every visible value column opens exactly as wide as its title, per locale.
 *
 * ⚠️ Every figure below is invented while writing this file, shaped to satisfy the zod schemas the builder parses with
 * (`assetSetLevels.ts`): nothing was read off a running backend.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import {get} from 'svelte/store';

import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {_, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import type {RiskAnalyticResult} from '$lib/features/risk/riskStore.svelte';
import {formatDay, formatDayRange} from '$lib/utils/core/formatAxisDate';
import {ASSET_SET_MONTHLY_VAR_INSTANCE, ASSET_SET_MOVE_KPI_INSTANCE} from './riskAnalysisHelpers';
import {headerWidth, measureHeaderTitle} from './riskReturnLevel';
import AssetSetMoveComparisonSection from './AssetSetMoveComparisonSection.svelte';

type Payload = Record<string, unknown>;

const VISIBLE_COLUMNS = ['bestDay', 'bestMonth', 'rally', 'omega', 'positiveShare', 'downsideDeviation'] as const;
const HIDDEN_COLUMNS = ['meanUpDown', 'streak', 'averageDrawdown', 'extremeDays'] as const;
const ALL_COLUMNS = [...VISIBLE_COLUMNS, ...HIDDEN_COLUMNS] as const;
type MoveColumn = (typeof ALL_COLUMNS)[number];

const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};
const BLANK_NOTE_KEY = 'risk.assetSet.levels.blankNote';

// Invented: three assets — one measured in full, one that never gained a day, one nobody measured.
const RISER = 21;
const FALLER = 22;
const UNMEASURED = 23;
const SELECTION = [UNMEASURED, RISER, FALLER];
const LABELS: ReadonlyMap<number, string> = new Map([
    [RISER, 'Invented riser'],
    [FALLER, 'Invented faller'],
    [UNMEASURED, 'Invented stranger'],
]);

const RISER_KPI: Payload = {
    asset_id: RISER,
    volatility: 0.19,
    max_drawdown: -0.18,
    max_drawdown_duration_days: 288,
    sharpe: 0.62,
    sortino: 0.81,
    best_realization: 0.052,
    best_realization_date: '2024-05-12',
    positive_observation_share: 0.53,
    mean_positive_return: 0.013,
    mean_negative_return: -0.012,
    longest_positive_run_observations: 8,
    longest_positive_run_start_date: '2024-03-04',
    longest_positive_run_end_date: '2024-03-13',
    omega_ratio: 1.22,
    downside_deviation: 0.196,
    extreme_day_ratio: 2.4,
};

/** Fell every day: no gaining day, so no best day, no average up day, no streak — and the backend names it for each. */
const FALLER_KPI: Payload = {
    ...RISER_KPI,
    asset_id: FALLER,
    best_realization: null,
    best_realization_date: null,
    positive_observation_share: 0,
    mean_positive_return: null,
    longest_positive_run_observations: null,
    longest_positive_run_start_date: null,
    longest_positive_run_end_date: null,
    omega_ratio: 0,
};

function result(analyticCode: string, instanceId: string, output: Payload, warnings: Payload[] = []): RiskAnalyticResult {
    return {analytic_code: analyticCode, instance_id: instanceId, status: 'ok', output, warnings} as unknown as RiskAnalyticResult;
}

const KPI = result('asset_set_kpi', ASSET_SET_MOVE_KPI_INSTANCE, {kind: 'kpi_set', drawdown_confidence_level: 0.95, items: [RISER_KPI, FALLER_KPI]}, [
    {code: 'best_realization_undefined', message: 'x', degrades_result: false, message_i18n_key: 'risk.warnings.best_realization_undefined_assets', details: {asset_ids: [FALLER]}},
]);

const MONTHLY_VAR = result('asset_set_var', ASSET_SET_MONTHLY_VAR_INSTANCE, {
    kind: 'var_cvar_set',
    confidence_level: 0.95,
    horizon_days: 30,
    horizon_observations: 21,
    observations: 482,
    items: [
        {asset_id: RISER, value_at_risk: 0.04, conditional_value_at_risk: 0.05, best_horizon: {compounded_return: 0.183, start_date: '2024-04-21', end_date: '2024-05-20'}},
        // A best 30 days that still lost: a figure, drawn with the minus.
        {asset_id: FALLER, value_at_risk: 0.09, conditional_value_at_risk: 0.11, best_horizon: {compounded_return: -0.021, start_date: '2024-06-03', end_date: '2024-07-02'}},
    ],
});

const DRAWDOWN = result('asset_set_drawdown', 'base-historical-asset_set_drawdown', {
    kind: 'drawdown_set',
    available_start: '2023-01-02',
    available_end: '2025-01-31',
    calculation_basis: 'price_only_close',
    return_basis: 'price_only',
    items: [
        {
            asset_id: RISER,
            current_drawdown: 0,
            current_peak_date: '2025-01-31',
            current_drawdown_duration_days: 0,
            maximum_drawdown: -0.18,
            maximum_drawdown_peak_date: '2023-08-01',
            maximum_drawdown_trough_date: '2023-10-27',
            maximum_drawdown_recovery_status: 'recovered',
            maximum_drawdown_recovery_date: '2024-05-15',
            maximum_drawdown_duration_days: 288,
            maximum_drawdown_recovered_ratio: 1,
            remaining_to_peak_ratio: 0,
            largest_rally: 0.384,
            largest_rally_start_date: '2024-04-21',
            largest_rally_end_date: '2024-09-02',
            largest_rally_duration_days: 134,
            average_drawdown: -0.031,
        },
    ],
});

interface MountProps {
    assetIds?: number[];
    kpi?: RiskAnalyticResult | null;
    monthlyVar?: RiskAnalyticResult | null;
    drawdown?: RiskAnalyticResult | null;
    loading?: boolean;
    failed?: boolean;
    discarded?: boolean;
}

function mount({assetIds = SELECTION, kpi = KPI, monthlyVar = MONTHLY_VAR, drawdown = DRAWDOWN, loading = false, failed = false, discarded = false}: MountProps = {}): void {
    render(AssetSetMoveComparisonSection, {props: {assetIds, assetLabels: LABELS, assetIcons: new Map(), kpi, monthlyVar, drawdown, loading, failed, discarded}});
}

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

function moveTable(): HTMLElement {
    return screen.getByTestId('risk-asset-set-move-table');
}

function drawnOrder(): number[] {
    return [...moveTable().querySelectorAll<HTMLElement>('tbody tr[data-row-id]')].map((row) => Number(row.dataset.rowId));
}

function rowById(assetId: number): HTMLElement {
    const rows = moveTable().querySelectorAll<HTMLElement>(`tbody tr[data-row-id="${assetId}"]`);
    expect(rows, `asset ${assetId}: no DataTable row of its own`).toHaveLength(1);
    return rows[0];
}

function headerOrder(): string[] {
    return [...moveTable().querySelectorAll<HTMLElement>('thead th[data-testid^="dt-header-"]')].map((header) => (header.dataset.testid ?? '').replace('dt-header-', ''));
}

function cellOf(assetId: number, column: MoveColumn): HTMLElement {
    return within(rowById(assetId)).getByTestId(`risk-asset-set-move-${column}`);
}

/** The figure a cell draws, its date line set aside. */
function figureText(cell: HTMLElement): string {
    const copy = cell.cloneNode(true) as HTMLElement;
    copy.querySelectorAll('[data-testid$="-detail"]').forEach((node) => node.remove());
    return normalize(copy.textContent);
}

function detailText(cell: HTMLElement): string {
    return normalize(cell.querySelector('[data-testid$="-detail"]')?.textContent);
}

/** The project's Tooltip around a dash: a `role="button"` trigger between the figure and its own `td`, never beyond. */
function explainerOf(cell: HTMLElement): HTMLElement | null {
    const td = cell.closest('td');
    const trigger = cell.closest<HTMLElement>('[role="button"]');
    return td !== null && trigger !== null && trigger !== td && td.contains(trigger) ? trigger : null;
}

const storage = new Map<string, string>();
const storageReads: string[] = [];

function dataTableHarness(locale: SupportedLocale = 'en'): void {
    beforeAll(async () => {
        await setupI18n(locale);
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

describe('AssetSetMoveComparisonSection — the table', () => {
    dataTableHarness();

    it('draws the selection in its own order under the six columns of 12/11, the other four hidden', () => {
        mount();

        expect(moveTable().querySelector('table'), 'the wrapper holds the DataTable').not.toBeNull();
        expect(moveTable()).toHaveAttribute('data-row-count', String(SELECTION.length));
        expect(headerOrder()).toEqual(['name', ...VISIBLE_COLUMNS]);
        expect(drawnOrder(), "the reader sorts, the system never ranks: the selection's own order").toEqual(SELECTION);
        for (const column of VISIBLE_COLUMNS) expect(screen.getByTestId(`dt-header-${column}`)).toHaveAttribute('data-sort', 'none');
        for (const column of HIDDEN_COLUMNS) expect(screen.queryByTestId(`dt-header-${column}`), `${column} starts hidden, a click away in the column toggle`).toBeNull();
    });

    it('keeps its layout under its own storage key', () => {
        mount();

        expect(
            storageReads.filter((key) => key.includes('dataTable_risk-asset-set-move_')),
            'no preference read under "risk-asset-set-move": it would share the loss table\'s widths',
        ).not.toEqual([]);
    });
});

describe('AssetSetMoveComparisonSection — each figure from the answer that measures it', () => {
    dataTableHarness();

    it('draws the best day, the best 30 days and the largest rally with their dates, and the shape of the days', () => {
        mount();

        const t = get(_);
        const drawn = Object.fromEntries(VISIBLE_COLUMNS.map((column) => [column, {figure: figureText(cellOf(RISER, column)), detail: detailText(cellOf(RISER, column))}]));
        expect(drawn).toEqual({
            bestDay: {figure: '+5.2%', detail: normalize(formatDay('2024-05-12'))},
            bestMonth: {figure: '+18.3%', detail: normalize(formatDayRange('2024-04-21', '2024-05-20'))},
            rally: {figure: '+38.4%', detail: normalize(`${formatDayRange('2024-04-21', '2024-09-02')} · ${t('risk.assetSet.levels.l1.lastedDays', {values: {days: 134}})}`)},
            omega: {figure: normalize(t('risk.assetSet.levels.move.times', {values: {value: '1.22'}})), detail: ''},
            positiveShare: {figure: '53.0%', detail: ''},
            downsideDeviation: {figure: '19.6%', detail: ''},
        });
        for (const column of VISIBLE_COLUMNS) expect(cellOf(RISER, column), column).toHaveAttribute('data-measured', 'true');
    });

    it('draws a best 30 days that lost with U+2212, a figure and never a blank', () => {
        mount();

        expect(cellOf(FALLER, 'bestMonth')).toHaveAttribute('data-measured', 'true');
        expect(figureText(cellOf(FALLER, 'bestMonth'))).toBe('−2.1%');
    });

    it('draws a dash marked unmeasured in every column of an asset nobody measured', () => {
        mount();

        for (const column of VISIBLE_COLUMNS) {
            expect(cellOf(UNMEASURED, column), column).toHaveAttribute('data-measured', 'false');
            expect(figureText(cellOf(UNMEASURED, column)), `${column}: the blank is an em dash, not a zero`).toBe('—');
        }
    });
});

describe('AssetSetMoveComparisonSection — the four hidden columns, once the reader shows them', () => {
    dataTableHarness();

    it('draws the average day, the streak, below the peak on average and the extreme days from the same answers', () => {
        // What the column toggle stores: the reader's overrides, under the table's own key.
        storage.set('lf_anon_dataTable_risk-asset-set-move_columnVisibilityOverrides', JSON.stringify(Object.fromEntries(HIDDEN_COLUMNS.map((column) => [column, true]))));
        mount();

        const t = get(_);
        expect(headerOrder()).toEqual(['name', ...VISIBLE_COLUMNS, ...HIDDEN_COLUMNS]);
        const drawn = Object.fromEntries(HIDDEN_COLUMNS.map((column) => [column, {figure: figureText(cellOf(RISER, column)), detail: detailText(cellOf(RISER, column))}]));
        expect(drawn).toEqual({
            meanUpDown: {figure: '+1.3% · \u22121.2%', detail: ''},
            streak: {figure: normalize(t('risk.assetSet.levels.move.days', {values: {days: 8}})), detail: normalize(formatDayRange('2024-03-04', '2024-03-13'))},
            averageDrawdown: {figure: '\u22123.1%', detail: ''},
            extremeDays: {figure: normalize(t('risk.assetSet.levels.move.times', {values: {value: '2.4'}})), detail: ''},
        });
        // The faller has no drawdown in the answer: its average below the peak is a dash, not a zero.
        expect(cellOf(FALLER, 'averageDrawdown')).toHaveAttribute('data-measured', 'false');
    });

    it('draws a zero as a plain 0.0%, neither a gain nor a loss: no rise at all, never below the peak', () => {
        storage.set('lf_anon_dataTable_risk-asset-set-move_columnVisibilityOverrides', JSON.stringify({averageDrawdown: true}));
        const neverMoved = {
            asset_id: RISER,
            current_drawdown: 0,
            current_peak_date: '2025-01-31',
            current_drawdown_duration_days: 0,
            maximum_drawdown: 0,
            maximum_drawdown_recovery_status: 'no_drawdown',
            maximum_drawdown_duration_days: 0,
            remaining_to_peak_ratio: 0,
            largest_rally: 0,
            largest_rally_duration_days: 0,
            average_drawdown: 0,
        };
        mount({drawdown: result('asset_set_drawdown', 'base-historical-asset_set_drawdown', {kind: 'drawdown_set', available_start: '2023-01-02', available_end: '2025-01-31', calculation_basis: 'price_only_close', return_basis: 'price_only', items: [neverMoved]})});

        for (const column of ['rally', 'averageDrawdown'] as const) {
            const cell = cellOf(RISER, column);
            expect(cell, `${column}: a zero is measured`).toHaveAttribute('data-measured', 'true');
            expect({figure: figureText(cell), detail: detailText(cell)}, `${column}: a zero has no sign and no dates`).toEqual({figure: '0.0%', detail: ''});
        }
    });

    it('says why half of the average day is a dash: the faller never gained, so its up half is blank and its down half drawn', async () => {
        storage.set('lf_anon_dataTable_risk-asset-set-move_columnVisibilityOverrides', JSON.stringify({meanUpDown: true}));
        mount();

        const cell = cellOf(FALLER, 'meanUpDown');
        expect(cell, 'premise: the down half is a figure, so the cell is measured').toHaveAttribute('data-measured', 'true');
        expect(figureText(cell)).toBe('\u2014 · \u22121.2%');
        expect(explainerOf(cell), 'a half dash with no explanation').not.toBeNull();
        await fireEvent.click(cell);
        const help = await screen.findByRole('tooltip');
        expect(normalize(help.textContent)).toBe(normalize(get(_)('risk.warnings.best_realization_undefined')));
        // Both halves drawn: nothing to explain.
        expect(explainerOf(cellOf(RISER, 'meanUpDown'))).toBeNull();
    });
});

describe('AssetSetMoveComparisonSection — a dash says why', () => {
    dataTableHarness();

    it('opens the backend’s reason on the cell of the asset its warning names', async () => {
        mount();
        const cell = cellOf(FALLER, 'bestDay');
        expect(cell, 'premise: the faller has no best day').toHaveAttribute('data-measured', 'false');

        const trigger = explainerOf(cell);
        expect(trigger, 'the dash sits in the project Tooltip').not.toBeNull();
        await fireEvent.click(cell);
        const help = await screen.findByRole('tooltip');
        const reason = normalize(get(_)('risk.warnings.best_realization_undefined'));
        expect(reason, 'premise: the reason key resolves').not.toBe('risk.warnings.best_realization_undefined');
        expect(normalize(help.textContent)).toBe(reason);
    });

    it('opens the table’s blank note on a dash no warning explains', async () => {
        mount();

        await fireEvent.click(cellOf(UNMEASURED, 'omega'));
        const help = await screen.findByRole('tooltip');
        expect(normalize(help.textContent)).toBe(normalize(get(_)(BLANK_NOTE_KEY)));
    });

    it('wraps only the dashes, cell by cell', () => {
        mount();

        for (const assetId of SELECTION) {
            for (const column of VISIBLE_COLUMNS) {
                const cell = cellOf(assetId, column);
                const measured = cell.getAttribute('data-measured') === 'true';
                expect(explainerOf(cell) === null, `asset ${assetId}: ${column} ${measured ? 'is a figure and is wrapped' : 'is a dash with no explanation'}`).toBe(measured);
            }
        }
    });
});

describe('AssetSetMoveComparisonSection — the headers explain', () => {
    dataTableHarness();

    it.each(VISIBLE_COLUMNS)('%s: its title reveals the help of its own columnHelp key', async (column) => {
        mount();

        await fireEvent.click(screen.getByTestId(`dt-sort-${column}`));
        const help = await screen.findByRole('tooltip');
        expect(normalize(help.textContent)).toBe(normalize(get(_)(`risk.assetSet.levels.move.columnHelp.${column}`)));
    });
});

describe('AssetSetMoveComparisonSection — the states', () => {
    dataTableHarness();

    it.each([
        {state: 'loading, nothing measured yet', props: {loading: true, kpi: null, monthlyVar: null, drawdown: null}, testId: 'risk-asset-set-move-loading'},
        {state: 'failed', props: {failed: true}, testId: 'risk-asset-set-move-error'},
        {state: 'discarded, nothing measured', props: {discarded: true, kpi: null, monthlyVar: null, drawdown: null}, testId: 'risk-asset-set-move-discarded'},
        {state: 'no asset selected', props: {assetIds: []}, testId: 'risk-asset-set-move-empty'},
    ])('$state: draws $testId and no table', ({props, testId}) => {
        mount(props);

        expect(screen.getByTestId(testId)).toBeInTheDocument();
        expect(screen.queryByTestId('risk-asset-set-move-table')).toBeNull();
    });

    it('keeps the figures on screen while a new answer loads', () => {
        mount({loading: true});

        expect(moveTable()).toHaveAttribute('data-row-count', String(SELECTION.length));
        expect(screen.queryByTestId('risk-asset-set-move-loading')).toBeNull();
    });
});

describe.each([...SUPPORTED_LOCALES])('AssetSetMoveComparisonSection — in %s', (locale) => {
    dataTableHarness(locale);

    let consoleWarn: MockInstance<Console['warn']>;
    beforeEach(() => {
        consoleWarn = vi.spyOn(console, 'warn');
    });
    afterEach(() => consoleWarn.mockRestore());

    it('opens every visible value column exactly as wide as its own title', () => {
        mount();

        const expected: Record<string, string> = {};
        const drawn: Record<string, string> = {};
        for (const column of VISIBLE_COLUMNS) {
            const key = `risk.assetSet.levels.move.columns.${column}`;
            const title = get(_)(key);
            expect(title, `premise: ${key} is ${locale}.json's own message`).toBe(at(CATALOGUES[locale], key));
            const width = headerWidth(title, measureHeaderTitle);
            expected[column] = `${width}px/${width}px`;
            const header = screen.getByTestId(`dt-header-${column}`);
            drawn[column] = `${header.style.width}/${header.style.minWidth}`;
        }
        expect(drawn).toEqual(expected);
    });

    it('has a title and a help for every column, hidden ones included, and formats its own messages without a complaint', () => {
        const catalogue = CATALOGUES[locale];
        const missing = ALL_COLUMNS.flatMap((column) => [`risk.assetSet.levels.move.columns.${column}`, `risk.assetSet.levels.move.columnHelp.${column}`]).filter((key) => {
            const message = at(catalogue, key);
            return typeof message !== 'string' || message.trim() === '';
        });
        expect(missing, `${locale}.json: these would print their own key`).toEqual([]);

        const days = get(_)('risk.assetSet.levels.move.days', {values: {days: 8}});
        const times = get(_)('risk.assetSet.levels.move.times', {values: {value: '1.22'}});
        expect(days.match(/\d+/g)).toContain('8');
        expect(times).toContain('1.22');
        const complaints = consoleWarn.mock.calls.map((args) => args.map(String).join(' ')).filter((line) => line.includes('[svelte-i18n]'));
        expect(complaints).toEqual([]);
    });
});
