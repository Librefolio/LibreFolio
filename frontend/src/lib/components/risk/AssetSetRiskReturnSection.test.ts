// @vitest-environment jsdom
/**
 * AssetSetRiskReturnSection — component test (Vitest + jsdom).
 *
 * L3° of Asset Global asks "what did each of these pay for its risk?" and answers with a scatter and a
 * table, one row per selected asset. The redesign approved by the developer on 2026-09-30 gives the
 * table the treatment L1° got the same day (`AssetSetLossComparisonSection.test.ts` is the model of
 * this file, and most of its reasoning carries over unchanged):
 *
 *  - **the project's `DataTable`**, inside `[data-testid="risk-asset-set-l3-table"]` (which keeps
 *    `data-row-count`): no checkbox column (a row is selected by a click on it — see the second review
 *    below), no row actions, no column filters, no pagination, sorting on, `storageKey`
 *    `risk-asset-set-l3`. Its instance is published through the bindable `tableRef`, for the column
 *    toggle the levels draw in the frame's header;
 *  - **the columns** `name`, `volatility`, `expectedReturn`, `sortino`, `sharpe`, plus `beta` and
 *    `correlation` only when `benchmarkApplies`; the rows open in the selection's own order, unsorted —
 *    the reader sorts, the system never ranks;
 *  - **a column sorts by the figure it draws, with its sign**: an average return of −1.2% sorts below
 *    one of +4.5%, and a blank is not a zero, so it goes last whichever way the column points; the third
 *    press gives the selection its order back. The name sorts like the matrix's "by name" — emoji
 *    ignored — ties by id;
 *  - **the headers explain, they do not link**: each value column's help is the tooltip of its own title,
 *    worded from `risk.assetSet.levels.l3.columnHelp.<col>`; the name has none; no anchor, no ⓘ;
 *  - **the asset cell is L1°'s** (the same shared helper), with L3° testids: the icon `assetIcons` gives,
 *    and the name — as text, never as markup — in the marquee's marker span;
 *  - **the value cells** publish `data-measured`: the volatility as a percentage, the average annual
 *    return with its sign (`+` or U+2212), the ratios as `formatRatio` prints them today, `—` when
 *    nothing was measured;
 *  - **the return is renamed** "average annual return", and since the developer's review of 06/10/2026
 *    its title is the short `risk.levels.l3.table.expectedReturnShort`: the full name,
 *    `risk.assetSet.levels.l3.expectedReturn`, is the column menu's `displayName` and the first line of
 *    the title's tooltip; the scatter's vertical axis is worded from a key of the lab's own,
 *    `risk.assetSet.levels.l3.axisReturn`, no longer from the portfolio L3's `risk.levels.l3.scatter.axisReturn`.
 *
 * What does not change, and is pinned here so the rewrite cannot lose it: the error, loading, discarded
 * and empty branches with their retry; the scatter block (`-risk-return`, `-scatter`, `-scatter-note`).
 * (`-blank-note` under the table was on this list until the third review below took it away.)
 * `risk-asset-set-l3-row` goes: rows are read from DataTable's `tr[data-row-id]`.
 *
 * **Written red first.** The cases about the DataTable, the cells, the tooltips, the axis key and the
 * catalogues describe the new contract and fail on the hand-written table they replace; the harness and
 * the unchanged branches pass on both. The catalogue cases stay red until the seven keys (six
 * `columnHelp`, one `axisReturn`) are added through the i18n tool.
 *
 * ── The second review (the developer, 2026-09-30, afternoon) ─────────────────────────────────────
 *
 *  - **the no-benchmark note goes** ("fuori luogo qui"): `risk-asset-set-l3-no-benchmark` is drawn in
 *    no state, with a benchmark or without — nor its sentence under another testid — and its key
 *    `risk.assetSet.levels.l3.noBenchmark` leaves the four catalogues. Beta and correlation still come
 *    only with a benchmark (the table cases above, unchanged);
 *  - **a click on a row selects it** — the table half of a selection L3° shares with its scatter.
 *    DataTable in single selection, so no checkbox column: a click selects the row, a second click on
 *    it clears it, a click on another row moves the selection there. One row at most, none on
 *    opening, read where DataTable publishes it — `data-selected` on `tr[data-row-id]`, never a class.
 *    The selection belongs to the asset, not to a position: a sort carries it with its row;
 *  - **the chart half** — the selection handed to the scatter as `selectedId` (`asset-<id>`, or `null`),
 *    a dot's `onpointclick('asset-<id>')` toggling that row through the table's instance — a second
 *    click on the selected dot clears it, as on its row — and the benchmark's dot, or a dot whose asset
 *    has no row, selecting nothing. Both are `ScatterChart` props; the cases read them off the stand-in,
 *    and the chart's own side of them (`data-selected-id`, a click coming back as the dot's id) is
 *    `ScatterChart.test.ts`'s.
 *
 * Red first again: the note cases on a table without a benchmark, the catalogue case for the note's key
 * and the selection cases fail on the section as it stands; the opening state (nothing selected), the
 * note's absence in every other state and everything above pass on both.
 *
 * ── The third review (the developer, 2026-10-01) ─────────────────────────────────────────────────
 *
 *  - **the dashes explain themselves, the fixed note goes**: `risk-asset-set-l3-blank-note` is drawn in
 *    no state, nor its sentence under another testid. Every unmeasured value cell (`data-measured=
 *    "false"`, the em dash) sits instead in the project's `Tooltip`, through DataTable's
 *    `HtmlCell.tooltip`, worded from the same key, `risk.assetSet.levels.blankNote`; a figure carries
 *    none — a property of the cell, not of the row. The trigger is found by what `Tooltip` draws
 *    (`role="button"`, `tabindex="0"`) between the figure and its own `td`, never by a class; opened,
 *    it is `[role="tooltip"][data-testid="tooltip-content"]`, portalled to `document.body`. A click on
 *    a dash opens it and does not reach the row — accepted, and deliberately not pinned; what is
 *    pinned is that a row made only of dashes is still selected by a click on its asset cell;
 *  - **the period the figures cover is stated**: under the table, before the scatter block, a note
 *    `risk-asset-set-l3-period` whose attributes are the contract — `data-start`, `data-end`,
 *    `data-days`, `data-narrowed` — read through `assetSetCalculationWindow` from the first of
 *    `[riskReturn, kpi, comparison]` whose metadata measured anything, against the toolbar's period,
 *    which the section now requires as `dateStart`/`dateEnd`. Its sentences are compared with `$_()`
 *    of `risk.assetSet.levels.l3.period.{window,narrowed,annualized}` with the dates as
 *    `dayFormatter($currentLanguage)` writes them, never read as prose. No qualifying metadata, no
 *    note; and none outside the table branch.
 *
 * Red first, a third time: the blank-note cases on the two tables, the wrapper cases and every period
 * case that expects a note fail on the section as it stands; the note's absence elsewhere, the period's
 * absence without metadata and the dash-row selection pass on both.
 *
 * ── The fourth review (the developer, 2026-10-01) ────────────────────────────────────────────────
 *
 *  - **the period's length in calendar units, and a line break**: the window sentence's message names
 *    `{length}` instead of a count of days, and the section words it as the span in calendar years,
 *    months and days — `calendarLength(start, end)`, pinned in `assetSetLevels.test.ts` — each non-zero
 *    part from its plural key, `risk.assetSet.levels.l3.period.{years,months,days}`, the parts joined by
 *    `Intl.ListFormat($currentLanguage, {style: 'long', type: 'conjunction'})`. `data-days` still
 *    publishes the count of days; the text no longer prints it. The note keeps its root and its
 *    attributes, and its text becomes two lines, in order: `risk-asset-set-l3-period-window` — the
 *    window sentence, then the narrowing one when narrowed — and `risk-asset-set-l3-period-annualized`,
 *    the annualisation sentence. That the two are drawn as blocks is a class, and is not asserted.
 *
 * Red first, a fourth time: every period case that reads the note's text fails on the section as it
 * stands — neither line is drawn, and the window sentence prints its raw template, the code still
 * handing `days` to a message that asks for `{length}`; the catalogue case, the attributes, the note's
 * place and its absence pass on both.
 *
 * ── D371 (the developer, 2026-10-05): the benchmark may be one of the selection ─────────────────
 *
 * «per le metriche che si calcolano con il benchmark e l'asset stesso è il benchmark, mettici un trattino
 * e un tooltip che spiega che non è applicabile perché sé stesso è già il benchmark». `asset_set_comparison`
 * 1.1.0 accepts a reference the reader also selected: it keeps its row, measured like the others, and is
 * left out of the comparison's `items` — its beta and correlation with itself would be 1 by construction.
 * So, on the reference's row (`isReference`, read from the parsed comparison):
 *
 *  - **its beta and correlation are the em dash** with `data-measured="false"` and `data-reference="true"`
 *    on the cell's span, in the project's Tooltip worded from `risk.assetSet.levels.l3.referenceItself` —
 *    not from the blank note. Every other dash keeps the blank note and carries no `data-reference`, and
 *    the reference's other four columns are measured like any row's;
 *  - **the scatter draws it once**: the points handed to `ScatterChart` are
 *    `buildAssetSetChartPoints(rows, benchmarkPoint)` — the reference's own row dot, `asset-<id>`, takes the
 *    role `benchmark` and no separate `benchmark` point is added, so a selection of the reference alone is
 *    one dot and no chart. A reference outside the selection is drawn as before, its own point last.
 *
 * Red first, a fifth time: the reference's two cells (no `data-reference`, the blank note's sentence) and
 * the scatter cases with the reference selected (a separate `benchmark` dot beside its row's) fail on the
 * section as it stands; the fixtures, the catalogues, the reference's measured columns, the other dashes
 * and a reference outside the selection pass on both. Not pinned, because the contract does not say it: what
 * a click on the selected reference's dot does — it is `asset-<id>` and its row exists, while the second
 * review's rule was that the benchmark's dot selects nothing.
 *
 * **The scatter is a stand-in.** `ScatterChart` belongs to another workstream and draws through
 * ECharts, whose canvas jsdom does not implement (see `SemiDonutChartStub.svelte`). It is replaced by a
 * function with a Svelte component's calling convention, which records the props this section hands it
 * and publishes its `testId` — the section's contract with the chart, observed from the section's side.
 * It also keeps the props object itself (`live`): the compiled section hands a reactive prop as a
 * getter, so reading `live.selectedId` after a click reads what the section hands the chart *now*,
 * with no re-mount. Nothing of the chart itself is tested here.
 *
 * **The help keys are read twice**, as in L1°: the tooltip and axis cases compare against `$_()` of the
 * same key, because their question is *which* key is shown; a key missing from the catalogue would come
 * back as itself on both sides and agree with itself, so the catalogues are also read directly.
 *
 * ⚠️ Every figure and name below was **invented while writing this file**: nothing was read off a
 * running backend. The payloads are shaped to be emittable — they satisfy the zod schemas
 * `assetSetLevels.ts` parses with (`buildAssetSetPaidRows`) and the pydantic models in
 * `backend/app/schemas/risk.py` that would have produced them: volatilities ≥ 0, falls ≤ 0, correlations
 * in [−1, 1], and a reference that is never one of the comparison's items — though since D371 it may be
 * one of the selection, as in the `REFERENCE_SELECTED` and `REFERENCE_ALONE` mounts. They are also
 * roughly coherent with each other, so a reader can check them rather than trust them: with the zero
 * risk-free rate the levels charge, Sharpe ≈ return ÷ volatility; beta ≈ correlation × volatility ÷ the
 * reference's 15%; the tracking error follows from the two volatilities and the correlation.
 * `data_quality` is omitted, as in the neighbouring files: the section does not read it. `metadata` is
 * omitted from the main fixtures too — so the cases that are not about the period draw no period note —
 * and the period cases attach a complete one (`windowMetadata`), proved by the harness to parse with
 * `schemas.RiskResultMetadata`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick, type ComponentProps} from 'svelte';
import {get} from 'svelte/store';
import type {z} from 'zod';

/**
 * Every mount of the stand-in scatter, with the props it was handed, read once at mount — and the props
 * object itself (`live`), whose getters stay current for as long as the section is mounted.
 *
 * Hoisted because `vi.mock` factories run before the imports; the stand-in has the calling convention
 * of a compiled Svelte 5 component — `(anchor, props)`, content inserted before the anchor — which is
 * all the section's compiled output asks of it.
 */
const scatter = vi.hoisted(() => {
    interface StandInProps {
        points: readonly {id: string; role?: string}[];
        labels: {volatility: string; return: string; capitalMarketLine: string};
        testId?: string;
        /** The linked selection's chart half, as `ScatterChart` takes it. */
        selectedId?: string | null;
        onpointclick?: (pointId: string) => void;
    }
    const mounts: {testId: string | undefined; labels: StandInProps['labels']; points: {id: string; role: string | undefined}[]; live: StandInProps}[] = [];
    function ScatterChartStandIn(anchor: ChildNode, props: StandInProps): void {
        mounts.push({testId: props.testId, labels: {...props.labels}, points: props.points.map(({id, role}) => ({id, role})), live: props});
        const stand = document.createElement('div');
        stand.setAttribute('data-testid', props.testId ?? 'risk-return-scatter');
        stand.setAttribute('data-point-count', String(props.points.length));
        anchor.before(stand);
    }
    return {mounts, ScatterChartStandIn};
});

vi.mock('$lib/components/charts/ScatterChart.svelte', () => ({default: scatter.ScatterChartStandIn}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {OVERFLOW_MARQUEE_SELECTOR} from '$lib/actions/scrollOnOverflow';
import {schemas} from '$lib/api';
import {_, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {currentLanguage} from '$lib/stores/app/language';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import AssetSetRiskReturnSection from './AssetSetRiskReturnSection.svelte';
import {buildAssetSetPaidRows, type CalendarLength} from './assetSetLevels';
import {dayFormatter} from './eligibility';

type ReturnOutput = z.infer<typeof schemas.RiskAssetSetReturnOutput>;
type KpiOutput = z.infer<typeof schemas.RiskAssetSetKpiOutput>;
type ComparisonOutput = z.infer<typeof schemas.RiskAssetSetComparisonOutput>;
type Metadata = z.infer<typeof schemas.RiskResultMetadata>;

function ok(instanceId: string, analyticCode: string, output: ReturnOutput | KpiOutput | ComparisonOutput): RiskAnalyticResult {
    return {instance_id: instanceId, analytic_code: analyticCode, status: 'ok', output};
}

// ═══════════════════════════════════════════════════════════════════════════════════════════════
// Fixtures — invented
// ═══════════════════════════════════════════════════════════════════════════════════════════════

/** The four value columns every table draws, in their order, and the two a benchmark adds. */
const BASE_VALUE_COLUMNS = ['volatility', 'expectedReturn', 'sortino', 'sharpe'] as const;
const BENCHMARK_COLUMNS = ['beta', 'correlation'] as const;
const VALUE_COLUMNS = [...BASE_VALUE_COLUMNS, ...BENCHMARK_COLUMNS] as const;
type ValueColumn = (typeof VALUE_COLUMNS)[number];

/**
 * The main fixture: five assets, one of them measured by no analytic — the state the backend leaves
 * when it cannot prepare an asset's series and excludes it from every result of the request. The
 * selection opens with that asset and is not alphabetical, so a table sorted by anything on opening
 * cannot draw `SELECTION`.
 */
const UNMEASURED = 62;
const SELECTION: number[] = [UNMEASURED, 65, 61, 64, 63];
const LABELS: ReadonlyMap<number, string> = new Map([
    [61, 'Invented holding C'],
    [62, 'Invented holding D'],
    [63, 'Invented holding A'],
    [64, 'Invented holding B'],
    [65, 'Invented holding E'],
]);
/**
 * Invented. The panel resolves each icon as `icon_url || getAssetTypeIconUrl(asset_type)`; this section
 * draws whatever it is handed. Three assets have one and two have none — the unmeasured one included —
 * so both branches of the asset cell are on screen in every mount.
 */
const ICONS: ReadonlyMap<number, string> = new Map([
    [61, '/icons/asset-types/stock.png'],
    [63, '/icons/asset-types/bond.png'],
    [65, '/icons/asset-types/etf.png'],
]);
/**
 * The shared reference: outside `SELECTION`, and never among the comparison's items, as
 * `validate_reference_is_not_a_subject` demands. Since D371 the reader may select it too — the
 * `REFERENCE_SELECTED` and `REFERENCE_ALONE` mounts do.
 */
const BENCHMARK_ID = 90;
const BENCHMARK_VOLATILITY = 0.15;
const BENCHMARK_RETURN = 0.058;

interface Measured {
    volatility: number;
    expectedReturn: number;
    sharpe: number;
    sortino: number;
    correlation: number;
    beta: number;
    /** Read by nothing here; required by the KPI contract. */
    maxDrawdown: number;
    maxDrawdownDays: number;
    /** Read by nothing here; required by the comparison contract. */
    activeReturn: number;
    trackingError: number;
    informationRatio: number;
}

/**
 * The measured four. Chosen so that, over the six value columns, **every ascending order is different
 * from every other** — a column that sorted by its neighbour's figure would draw the neighbour's order —
 * and none is the selection's. The returns cross zero, and their order by magnitude is not their order
 * by value, which is what the signed sort is about.
 */
const MEASURED: ReadonlyMap<number, Measured> = new Map([
    [61, {volatility: 0.18, expectedReturn: 0.045, sharpe: 0.25, sortino: 0.61, correlation: 0.4, beta: 0.48, maxDrawdown: -0.21, maxDrawdownDays: 140, activeReturn: -0.013, trackingError: 0.1825, informationRatio: -0.0712}],
    [63, {volatility: 0.09, expectedReturn: -0.012, sharpe: -0.13, sortino: -0.17, correlation: 0.88, beta: 0.53, maxDrawdown: -0.08, maxDrawdownDays: 61, activeReturn: -0.07, trackingError: 0.0827, informationRatio: -0.8464}],
    [64, {volatility: 0.31, expectedReturn: -0.034, sharpe: -0.11, sortino: -0.19, correlation: -0.11, beta: -0.23, maxDrawdown: -0.44, maxDrawdownDays: 388, activeReturn: -0.092, trackingError: 0.3589, informationRatio: -0.2563}],
    [65, {volatility: 0.26, expectedReturn: 0.091, sharpe: 0.35, sortino: 0.48, correlation: 0.36, beta: 0.62, maxDrawdown: -0.29, maxDrawdownDays: 203, activeReturn: 0.033, trackingError: 0.249, informationRatio: 0.1325}],
]);

/** Listed against the selection's order, so a row can only find its item by `asset_id`. */
const PAYLOAD_ORDER = [...MEASURED.keys()].sort((left, right) => right - left);

const RISK_RETURN = ok('invented-risk-return', 'asset_set_risk_return', {
    kind: 'risk_return_set',
    items: PAYLOAD_ORDER.map((assetId) => {
        const figures = MEASURED.get(assetId) as Measured;
        return {asset_id: assetId, volatility: figures.volatility, expected_annual_return: figures.expectedReturn};
    }),
});

const KPI = ok('invented-kpi', 'asset_set_kpi', {
    kind: 'kpi_set',
    drawdown_confidence_level: 0.95,
    items: PAYLOAD_ORDER.map((assetId) => {
        const figures = MEASURED.get(assetId) as Measured;
        // The same volatility as the risk/return point: both are measured on the one joint calendar.
        return {asset_id: assetId, volatility: figures.volatility, max_drawdown: figures.maxDrawdown, max_drawdown_duration_days: figures.maxDrawdownDays, sharpe: figures.sharpe, sortino: figures.sortino};
    }),
});

const COMPARISON = ok('invented-comparison', 'asset_set_comparison', {
    kind: 'comparison_set',
    comparison_asset_id: BENCHMARK_ID,
    observations: 752,
    comparison_volatility: BENCHMARK_VOLATILITY,
    comparison_expected_annual_return: BENCHMARK_RETURN,
    items: PAYLOAD_ORDER.map((assetId) => {
        const figures = MEASURED.get(assetId) as Measured;
        return {asset_id: assetId, active_return: figures.activeReturn, tracking_error: figures.trackingError, information_ratio: figures.informationRatio, correlation: figures.correlation, beta: figures.beta};
    }),
});

/** What each measured cell draws, read off the figures above by hand. */
const DRAWN: ReadonlyMap<number, Record<ValueColumn, string>> = new Map([
    [61, {volatility: '18.0%', expectedReturn: '+4.5%', sortino: '0.61', sharpe: '0.25', beta: '0.48', correlation: '0.40'}],
    [63, {volatility: '9.0%', expectedReturn: '\u22121.2%', sortino: '-0.17', sharpe: '-0.13', beta: '0.53', correlation: '0.88'}],
    [64, {volatility: '31.0%', expectedReturn: '\u22123.4%', sortino: '-0.19', sharpe: '-0.11', beta: '-0.23', correlation: '-0.11'}],
    [65, {volatility: '26.0%', expectedReturn: '+9.1%', sortino: '0.48', sharpe: '0.35', beta: '0.62', correlation: '0.36'}],
]);

/**
 * D371: the reader selected the reference too, mid-list — neither first nor last, so no position can stand
 * in for it. The comparison is `COMPARISON` itself: the backend leaves a selected reference out of `items`,
 * and the reference always took part in the selection's joint window, so selecting it moves no other figure
 * and its own coordinates are the comparison's. Its row is measured on them like any other: Sharpe ≈
 * 0.058 ÷ 0.15.
 */
const SELECTION_WITH_REFERENCE: number[] = [UNMEASURED, 65, BENCHMARK_ID, 61, 64, 63];
const REFERENCE_NAME = 'Invented reference R';
const LABELS_WITH_REFERENCE: ReadonlyMap<number, string> = new Map<number, string>([...LABELS, [BENCHMARK_ID, REFERENCE_NAME]]);
const REFERENCE_FIGURES = {volatility: BENCHMARK_VOLATILITY, expectedReturn: BENCHMARK_RETURN, sharpe: 0.39, sortino: 0.52, maxDrawdown: -0.19, maxDrawdownDays: 166};
/** What the reference's four measured cells draw, read off the figures above by hand. */
const REFERENCE_DRAWN: Record<(typeof BASE_VALUE_COLUMNS)[number], string> = {volatility: '15.0%', expectedReturn: '+5.8%', sortino: '0.52', sharpe: '0.39'};
const REFERENCE_RETURN_ITEM = {asset_id: BENCHMARK_ID, volatility: REFERENCE_FIGURES.volatility, expected_annual_return: REFERENCE_FIGURES.expectedReturn};
const REFERENCE_KPI_ITEM = {asset_id: BENCHMARK_ID, volatility: REFERENCE_FIGURES.volatility, max_drawdown: REFERENCE_FIGURES.maxDrawdown, max_drawdown_duration_days: REFERENCE_FIGURES.maxDrawdownDays, sharpe: REFERENCE_FIGURES.sharpe, sortino: REFERENCE_FIGURES.sortino};

/** The main payloads with the reference's own item first, as `PAYLOAD_ORDER` lists them: by id, descending. */
const RISK_RETURN_WITH_REFERENCE = ok('invented-risk-return-with-reference', 'asset_set_risk_return', {kind: 'risk_return_set', items: [REFERENCE_RETURN_ITEM, ...(RISK_RETURN.output as ReturnOutput).items]});
const KPI_WITH_REFERENCE = ok('invented-kpi-with-reference', 'asset_set_kpi', {kind: 'kpi_set', drawdown_confidence_level: 0.95, items: [REFERENCE_KPI_ITEM, ...(KPI.output as KpiOutput).items]});

/** The reference selected alone: the backend answers with not one item, and the reference's coordinates beside them. */
const RISK_RETURN_REFERENCE_ALONE = ok('invented-risk-return-reference-alone', 'asset_set_risk_return', {kind: 'risk_return_set', items: [REFERENCE_RETURN_ITEM]});
const KPI_REFERENCE_ALONE = ok('invented-kpi-reference-alone', 'asset_set_kpi', {kind: 'kpi_set', drawdown_confidence_level: 0.95, items: [REFERENCE_KPI_ITEM]});
const COMPARISON_REFERENCE_ALONE = ok('invented-comparison-reference-alone', 'asset_set_comparison', {
    kind: 'comparison_set',
    comparison_asset_id: BENCHMARK_ID,
    observations: 752,
    comparison_volatility: BENCHMARK_VOLATILITY,
    comparison_expected_annual_return: BENCHMARK_RETURN,
    items: [],
});

/**
 * The orders each column must take, written out by hand from the figures drawn:
 *   volatility   61 18.0   63 9.0     64 31.0    65 26.0
 *   return       61 +4.5   63 −1.2    64 −3.4    65 +9.1
 *   Sortino      61 0.61   63 −0.17   64 −0.19   65 0.48
 *   Sharpe       61 0.25   63 −0.13   64 −0.11   65 0.35
 *   beta         61 0.48   63 0.53    64 −0.23   65 0.62
 *   correlation  61 0.40   63 0.88    64 −0.11   65 0.36
 * and 62 blank everywhere, last both ways.
 */
const VALUE_SORTS = [
    {column: 'volatility', ascending: [63, 61, 65, 64, UNMEASURED], descending: [64, 65, 61, 63, UNMEASURED]},
    {column: 'expectedReturn', ascending: [64, 63, 61, 65, UNMEASURED], descending: [65, 61, 63, 64, UNMEASURED]},
    {column: 'sortino', ascending: [64, 63, 65, 61, UNMEASURED], descending: [61, 65, 63, 64, UNMEASURED]},
    {column: 'sharpe', ascending: [63, 64, 61, 65, UNMEASURED], descending: [65, 61, 64, 63, UNMEASURED]},
    {column: 'beta', ascending: [64, 61, 63, 65, UNMEASURED], descending: [65, 63, 61, 64, UNMEASURED]},
    {column: 'correlation', ascending: [64, 65, 61, 63, UNMEASURED], descending: [63, 61, 65, 64, UNMEASURED]},
] as const;

/**
 * The name fixture — L1°'s, for the same reasons. Invented names, decorated the way real ones are.
 * A collator reading the raw name files every emoji ahead of every letter, a code-point comparison
 * files them after every letter, and a stable sort without the id tie-break keeps 🇪🇺 Alpha ahead of
 * Alpha, because the selection lists it first: each wrong way gives a different, wrong order.
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

/**
 * The toolbar's period, which the section requires as `dateStart` and `dateEnd` (third review): a
 * year, Wednesday to Wednesday. Every mount below hands it, so no case leaves a required prop out.
 */
const SELECTED_START = '2025-10-01';
const SELECTED_END = '2026-09-30';

/**
 * A result's `metadata`, complete — `schemas.RiskResultMetadata` refuses less, and the harness proves
 * each of these parses — and filled the way the engine fills it for an asset set: the BASELINE PRICE,
 * the one the first return is measured from, is the day before the selection when every asset has
 * history before it (prices are carried over every calendar day), and the first complete date inside
 * it only when some asset has none; `analyzed_range` runs from the first RETURN date to the last one,
 * a return falling only on a day some asset is freshly quoted; `calendar_days` runs from the baseline
 * price date to the last return date. So the figures cover `end − calendar_days + 1` — the day after
 * the baseline price, the selection's first day whenever there is history before it — to `end`:
 * `calendar_days` days, both ends counted. The counts of returns are invented, of the order a joint
 * calendar of exchange-traded assets gives: about 252 a year.
 */
function windowMetadata(firstReturn: string, lastReturn: string, calendarDays: number, observations: number): Metadata {
    return {
        analyzed_range: {start: firstReturn, end: lastReturn},
        frequency: 'daily',
        n_observations: observations,
        calendar_days: calendarDays,
        // `observed_annualization`: n · 365 / calendar days, and nothing when nothing was observed.
        annualization_factor: observations > 0 && calendarDays > 0 ? (observations * 365) / calendarDays : null,
        coverage: 1,
        currency: 'EUR',
        scope: 'asset_set',
        return_basis: 'price_only',
        algorithm_version: 'invented-asset-set',
        computed_at: '2026-10-01T09:00:00+00:00',
    };
}

/** The same result, carrying the metadata the API sends beside its output. */
function withWindow(result: RiskAnalyticResult, metadata: Metadata): RiskAnalyticResult {
    return {...result, metadata};
}

/** A window, and what the period note must publish for it against `SELECTED_START`…`SELECTED_END` — `YEAR_AND_MORE` alone against a selection of its own. */
interface PeriodWindow {
    metadata: Metadata;
    start: string;
    end: string;
    days: number;
    narrowed: boolean;
    /**
     * `start`…`end` in calendar units, as `calendarLength` counts it (fourth review) — worked out here by
     * hand, with a calendar, so the note is not checked against the helper it is written with.
     */
    length: CalendarLength;
}

/** History before the selection: the baseline price on 30 September, the day before it opens, and 365 days from there to the last return — the selection's own year. Twelve months to 1 October: a year. */
const FULL_YEAR: PeriodWindow = {metadata: windowMetadata('2025-10-01', '2026-09-30', 365, 252), start: '2025-10-01', end: '2026-09-30', days: 365, narrowed: false, length: {years: 1, months: 0, days: 0}};
/** No history before Monday 6 October, the first common price: that is the baseline, so the figures open on the Tuesday — six days late, within the week's tolerance, so not narrowed. Eleven months to 7 September, and 24 days to 1 October. */
const SIX_DAYS_LATE: PeriodWindow = {metadata: windowMetadata('2025-10-07', '2026-09-30', 359, 248), start: '2025-10-07', end: '2026-09-30', days: 359, narrowed: false, length: {years: 0, months: 11, days: 24}};
/** No history before Thursday 15 January, the first common price: the figures open on the Friday, three and a half months in, and cover the last eight and a half. Eight months to 16 September, and 15 days to 1 October. */
const LATE_START: PeriodWindow = {metadata: windowMetadata('2026-01-16', '2026-09-30', 258, 178), start: '2026-01-16', end: '2026-09-30', days: 258, narrowed: true, length: {years: 0, months: 8, days: 15}};
/**
 * The one window here whose length has all three parts — so the one that tells `Intl.ListFormat` from
 * any plain join — and so the one mounted against a selection of its own, longer than a year: Monday
 * 28 July 2025 to Wednesday 30 September 2026, with history before it. The baseline is Sunday's price,
 * carried from the Friday, and 430 days run from there to the last return. Fourteen months to 28
 * September, and 3 days to 1 October: a year, two months and three days.
 */
const YEAR_AND_MORE: PeriodWindow = {metadata: windowMetadata('2025-07-28', '2026-09-30', 430, 297), start: '2025-07-28', end: '2026-09-30', days: 430, narrowed: false, length: {years: 1, months: 2, days: 3}};

/**
 * An analytic that measured nothing: unavailable, as an analytic without a single return is, and still
 * carrying its metadata — `RiskService._unavailable` may attach it, and `_metadata` zeroes
 * `calendar_days` whenever `n_observations` is 0. Its range is the one asked for: no window at all.
 */
function measuredNothing(instanceId: string, analyticCode: string): RiskAnalyticResult {
    return {instance_id: instanceId, analytic_code: analyticCode, status: 'unavailable', output: null, metadata: windowMetadata(SELECTED_START, SELECTED_END, 0, 0), error: {code: 'insufficient_history', message: 'invented: not one return in the window'}};
}

// ═══════════════════════════════════════════════════════════════════════════════════════════════
// Harness
// ═══════════════════════════════════════════════════════════════════════════════════════════════

interface MountProps {
    assetIds?: number[];
    assetLabels?: ReadonlyMap<number, string>;
    assetIcons?: ReadonlyMap<number, string>;
    riskReturn?: RiskAnalyticResult | null;
    kpi?: RiskAnalyticResult | null;
    comparison?: RiskAnalyticResult | null;
    benchmarkApplies?: boolean;
    /** The toolbar's period: required by the section, defaulted here to `SELECTED_START`…`SELECTED_END`. */
    dateStart?: string;
    dateEnd?: string;
    loading?: boolean;
    failed?: boolean;
    discarded?: boolean;
    onretry?: () => void;
}

/** The whole fixture, measured, with no benchmark — the page's ordinary state. */
const MAIN: MountProps = {assetIds: SELECTION, assetLabels: LABELS, assetIcons: ICONS, riskReturn: RISK_RETURN, kpi: KPI};
/** The same, with a benchmark that applies. */
const WITH_BENCHMARK: MountProps = {...MAIN, comparison: COMPARISON, benchmarkApplies: true};
/** D371: the reference selected mid-list beside the others, the benchmark applying — `COMPARISON` unchanged. */
const REFERENCE_SELECTED: MountProps = {assetIds: SELECTION_WITH_REFERENCE, assetLabels: LABELS_WITH_REFERENCE, assetIcons: ICONS, riskReturn: RISK_RETURN_WITH_REFERENCE, kpi: KPI_WITH_REFERENCE, comparison: COMPARISON, benchmarkApplies: true};
/** D371: the reference selected alone — one row, and nothing to compare it with. */
const REFERENCE_ALONE: MountProps = {assetIds: [BENCHMARK_ID], assetLabels: new Map([[BENCHMARK_ID, REFERENCE_NAME]]), riskReturn: RISK_RETURN_REFERENCE_ALONE, kpi: KPI_REFERENCE_ALONE, comparison: COMPARISON_REFERENCE_ALONE, benchmarkApplies: true};

function propsOf({assetIds = SELECTION, assetLabels = LABELS, assetIcons = new Map(), riskReturn = null, kpi = null, comparison = null, benchmarkApplies = false, dateStart = SELECTED_START, dateEnd = SELECTED_END, loading = false, failed = false, discarded = false, onretry}: MountProps) {
    return {assetIds, assetLabels, assetIcons, riskReturn, kpi, comparison, benchmarkApplies, dateStart, dateEnd, loading, failed, discarded, ...(onretry ? {onretry} : {})};
}

function mountWith(props: MountProps): void {
    render(AssetSetRiskReturnSection, {props: propsOf(props)});
}

/** The section's own props, so the bound `tableRef` is typed as the section declares it. */
type SectionProps = ComponentProps<typeof AssetSetRiskReturnSection>;

/**
 * Mount with `tableRef` bound, the way `bind:tableRef` binds it: through a setter on the props object,
 * which Svelte calls when the section writes its bindable prop. Returns where the value lands.
 */
function mountBinding(props: MountProps): {tableRef: SectionProps['tableRef']} {
    const bound: {tableRef: SectionProps['tableRef']} = {tableRef: undefined};
    render(AssetSetRiskReturnSection, {
        props: {
            ...propsOf(props),
            get tableRef() {
                return bound.tableRef;
            },
            set tableRef(value: SectionProps['tableRef']) {
                bound.tableRef = value;
            },
        },
    });
    return bound;
}

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** The wrapper the level publishes its row count on; the DataTable sits inside it. */
function l3Table(): HTMLElement {
    return screen.getByTestId('risk-asset-set-l3-table');
}

/** The asset ids of the drawn rows, top to bottom, as DataTable publishes them. */
function drawnOrder(): number[] {
    return [...l3Table().querySelectorAll<HTMLElement>('tbody tr[data-row-id]')].map((row) => Number(row.dataset.rowId));
}

/** One asset's DataTable row, by the id DataTable writes on it. */
function rowById(assetId: number): HTMLElement {
    const rows = l3Table().querySelectorAll<HTMLElement>(`tbody tr[data-row-id="${assetId}"]`);
    expect(rows, `asset ${assetId}: no DataTable row of its own — tbody tr[data-row-id="${assetId}"]`).toHaveLength(1);
    return rows[0];
}

/** The column ids of the header row, left to right. */
function headerOrder(): string[] {
    return [...l3Table().querySelectorAll<HTMLElement>('thead th[data-testid^="dt-header-"]')].map((header) => (header.dataset.testid ?? '').replace('dt-header-', ''));
}

/** One asset's value cell for a column: the element carrying the figure and `data-measured`. */
function cellOf(assetId: number, column: ValueColumn): HTMLElement {
    const cells = within(rowById(assetId)).getAllByTestId(`risk-asset-set-l3-${column}`);
    expect(cells, `asset ${assetId}: ${column} must be one cell`).toHaveLength(1);
    return cells[0];
}

/** One asset's name cell: the icon and the name, carrying the asset's id. */
function nameCell(assetId: number): HTMLElement {
    const cells = l3Table().querySelectorAll<HTMLElement>(`[data-testid="risk-asset-set-l3-name"][data-asset-id="${assetId}"]`);
    expect(cells, `asset ${assetId}: no name cell of its own — [data-testid="risk-asset-set-l3-name"][data-asset-id="${assetId}"]`).toHaveLength(1);
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

/** A value cell's figure as the signed number it reads as, or null for the blank. */
function drawnFigure(cell: HTMLElement): number | null {
    const text = normalize(cell.textContent);
    if (text === '\u2014') return null;
    // A percentage (signed or not), or a ratio as `formatRatio` prints it — with an ASCII hyphen today.
    const match = /^([\u2212+-]?)(\d+(?:\.\d+)?)%?$/.exec(text);
    if (!match) throw new Error(`a value cell draws ${JSON.stringify(text)}: neither a figure nor the blank`);
    return match[1] === '\u2212' || match[1] === '-' ? -Number(match[2]) : Number(match[2]);
}

/**
 * The drawn column read top to bottom: its figures in the stated direction, the blanks after them.
 *
 * Independent of the orders written out by hand in `VALUE_SORTS`: it reads the screen, so it is the
 * rule itself — "sorted by the figure as drawn, with its sign" — rather than one instance of it.
 */
function expectSortedAsDrawn(column: ValueColumn, direction: 'asc' | 'desc'): void {
    const figures = drawnOrder().map((assetId) => drawnFigure(cellOf(assetId, column)));
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
 * A click on one asset's row, where a pointer lands: on one of its cells — the volatility, a plain
 * figure — from which the click bubbles to the `tr` DataTable listens on.
 */
async function clickRow(assetId: number): Promise<void> {
    await fireEvent.click(cellOf(assetId, 'volatility'));
}

/**
 * The selection as every drawn row states it: `assetId` the one selected row, or `null` for none.
 *
 * Each row is read, not only the one expected: a second row left selected fails, and so does a row that
 * publishes no state at all — `data-selected` missing is not "not selected", it is a table that stopped
 * saying. Barrier first: an empty table would satisfy "no row selected" by having no rows.
 */
function expectSelected(assetId: number | null, why: string): void {
    const order = drawnOrder();
    expect(order.length, `${why}: the table has no rows to read a selection from`).toBeGreaterThan(0);
    if (assetId !== null) expect(order, `${why}: asset ${assetId} has no row`).toContain(assetId);
    for (const rowId of order) {
        expect(rowById(rowId), `${why} — asset ${rowId}'s row`).toHaveAttribute('data-selected', rowId === assetId ? 'true' : 'false');
    }
}

/** The key a value column's help is worded from: the tooltip of its own title. */
function helpKey(column: ValueColumn): string {
    return `risk.assetSet.levels.l3.columnHelp.${column}`;
}

/** The lab's own key for the scatter's vertical axis, and the portfolio L3's it replaces. */
const AXIS_RETURN_KEY = 'risk.assetSet.levels.l3.axisReturn';
const PORTFOLIO_AXIS_RETURN_KEY = 'risk.levels.l3.scatter.axisReturn';

/** The note that sent the reader to the Dashboard for a benchmark, and its key — both gone (second review). */
const NO_BENCHMARK_TESTID = 'risk-asset-set-l3-no-benchmark';
const NO_BENCHMARK_KEY = 'risk.assetSet.levels.l3.noBenchmark';

/** The fixed note under the table that said what a dash means — gone (third review) — and its key, now each dash's own explanation. */
const BLANK_NOTE_TESTID = 'risk-asset-set-l3-blank-note';
const BLANK_NOTE_KEY = 'risk.assetSet.levels.blankNote';

/** D371: what the reference's own beta and correlation dashes say instead — it is the benchmark itself. */
const REFERENCE_ITSELF_KEY = 'risk.assetSet.levels.l3.referenceItself';

/** The period note (third review), and the three keys its sentences are worded from. */
const PERIOD_TESTID = 'risk-asset-set-l3-period';
const PERIOD_WINDOW_KEY = 'risk.assetSet.levels.l3.period.window';
const PERIOD_NARROWED_KEY = 'risk.assetSet.levels.l3.period.narrowed';
const PERIOD_ANNUALIZED_KEY = 'risk.assetSet.levels.l3.period.annualized';

/** The note's two lines (fourth review): the period, then what the figures make of it. */
const PERIOD_WINDOW_LINE_TESTID = 'risk-asset-set-l3-period-window';
const PERIOD_ANNUALIZED_LINE_TESTID = 'risk-asset-set-l3-period-annualized';

/** The three plural keys the window's length is worded from, one per calendar unit; and the units, in the order the parts are read. */
const PERIOD_LENGTH_KEYS = {years: 'risk.assetSet.levels.l3.period.years', months: 'risk.assetSet.levels.l3.period.months', days: 'risk.assetSet.levels.l3.period.days'} as const;
const LENGTH_UNITS = ['years', 'months', 'days'] as const;

/**
 * The explanation wrapped around a value cell, or `null`: the trigger the project's `Tooltip` draws
 * (`role="button"`), looked for between the figure and its own `td` and never beyond it, so that a
 * role on the row could not pass for the cell's own.
 */
function explainerOf(cell: HTMLElement): HTMLElement | null {
    const td = cell.closest('td');
    const trigger = cell.closest<HTMLElement>('[role="button"]');
    return td !== null && trigger !== null && trigger !== td && td.contains(trigger) ? trigger : null;
}

/** Whether `first` comes before `second` in document order, `second` not inside it. */
function precedes(first: Node, second: Node): boolean {
    return !first.contains(second) && (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

/** Typed on the app's locale list, so a fifth locale without a catalogue here fails `front check`. */
const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** The stand-in scatter's mounts under the section's own testId. */
function scatterMounts(): (typeof scatter.mounts)[number][] {
    return scatter.mounts.filter((mount) => mount.testId === 'risk-asset-set-l3-scatter');
}

/**
 * DataTable keeps widths and order in `localStorage`. Stubbed per case — as
 * `DataTableHeaderTooltip.test.ts` does — so no case inherits another's layout, and so the keys the
 * table reads can be seen.
 */
const storage = new Map<string, string>();
const storageReads: string[] = [];

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    scatter.mounts.length = 0;
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

// ═══════════════════════════════════════════════════════════════════════════════════════════════
// The harness itself — true of the old table and the new one alike
// ═══════════════════════════════════════════════════════════════════════════════════════════════

describe('AssetSetRiskReturnSection — the harness itself', () => {
    it('every fixture survives the parsers the section reads it through', () => {
        const rows = buildAssetSetPaidRows(SELECTION, LABELS, RISK_RETURN, KPI, COMPARISON);

        expect(
            rows.map((row) => row.assetId),
            'one row per selected asset, in the selection order',
        ).toEqual(SELECTION);
        for (const row of rows) {
            const figures = MEASURED.get(row.assetId);
            if (figures === undefined) {
                expect([row.volatility, row.expectedReturn, row.sortino, row.sharpe, row.beta, row.correlation], `asset ${row.assetId} is measured by no payload and must stay blank`).toEqual([null, null, null, null, null, null]);
                continue;
            }
            expect({volatility: row.volatility, expectedReturn: row.expectedReturn, sortino: row.sortino, sharpe: row.sharpe, beta: row.beta, correlation: row.correlation}, `asset ${row.assetId}: a payload was rejected by its schema — riskOutput() returned null and the row is blank`).toEqual({
                volatility: figures.volatility,
                expectedReturn: figures.expectedReturn,
                sortino: figures.sortino,
                sharpe: figures.sharpe,
                beta: figures.beta,
                correlation: figures.correlation,
            });
        }
    });

    it('every metadata fixture is complete: it parses as the API would send it', () => {
        const fixtures = [FULL_YEAR, SIX_DAYS_LATE, LATE_START, YEAR_AND_MORE].map((period) => period.metadata);
        fixtures.push(measuredNothing('invented-nothing', 'asset_set_risk_return').metadata as Metadata);
        for (const metadata of fixtures) {
            const parsed = schemas.RiskResultMetadata.safeParse(metadata);
            expect(parsed.success, `${JSON.stringify(metadata.analyzed_range)}: ${parsed.success ? '' : parsed.error.message}`).toBe(true);
        }
    });

    it('the D371 fixtures parse too: the reference selected, measured like the others, and never among the compared', () => {
        const parsed = {
            riskReturnWithReference: schemas.RiskAssetSetReturnOutput.safeParse(RISK_RETURN_WITH_REFERENCE.output).success,
            kpiWithReference: schemas.RiskAssetSetKpiOutput.safeParse(KPI_WITH_REFERENCE.output).success,
            riskReturnAlone: schemas.RiskAssetSetReturnOutput.safeParse(RISK_RETURN_REFERENCE_ALONE.output).success,
            kpiAlone: schemas.RiskAssetSetKpiOutput.safeParse(KPI_REFERENCE_ALONE.output).success,
            comparisonAlone: schemas.RiskAssetSetComparisonOutput.safeParse(COMPARISON_REFERENCE_ALONE.output).success,
        };
        expect(parsed, 'a D371 payload is rejected by its schema: its cases would be red for the fixture, not the contract').toEqual({riskReturnWithReference: true, kpiWithReference: true, riskReturnAlone: true, kpiAlone: true, comparisonAlone: true});
        expect(SELECTION_WITH_REFERENCE, 'the reference is one of the selection').toContain(BENCHMARK_ID);
        const compared = (COMPARISON.output as ComparisonOutput).items.map((item) => item.asset_id);
        expect(compared, 'validate_reference_is_not_a_subject: the reference is never among the compared').not.toContain(BENCHMARK_ID);

        const rows = buildAssetSetPaidRows(SELECTION_WITH_REFERENCE, LABELS_WITH_REFERENCE, RISK_RETURN_WITH_REFERENCE, KPI_WITH_REFERENCE, COMPARISON);
        const figuresOf = (assetId: number) => {
            const row = rows.find((candidate) => candidate.assetId === assetId);
            return row && {volatility: row.volatility, expectedReturn: row.expectedReturn, sortino: row.sortino, sharpe: row.sharpe, beta: row.beta, correlation: row.correlation};
        };
        const referenceFigures = {volatility: REFERENCE_FIGURES.volatility, expectedReturn: REFERENCE_FIGURES.expectedReturn, sortino: REFERENCE_FIGURES.sortino, sharpe: REFERENCE_FIGURES.sharpe, beta: null, correlation: null};
        expect(figuresOf(BENCHMARK_ID), 'the reference is measured like the others, and compared with nothing').toEqual(referenceFigures);
        for (const [assetId, figures] of MEASURED) {
            const expected = {volatility: figures.volatility, expectedReturn: figures.expectedReturn, sortino: figures.sortino, sharpe: figures.sharpe, beta: figures.beta, correlation: figures.correlation};
            expect(figuresOf(assetId), `asset ${assetId}: selecting the reference moved its figures`).toEqual(expected);
        }
        expect(figuresOf(UNMEASURED), 'the unmeasured asset stays blank beside a selected reference').toEqual({volatility: null, expectedReturn: null, sortino: null, sharpe: null, beta: null, correlation: null});
    });

    it("the stand-in scatter is the one the section mounts: it receives the section's testId and one point per measured asset", () => {
        mountWith(MAIN);

        const mounts = scatterMounts();
        expect(mounts, 'the section did not mount the stand-in: the axis case below would read nothing').toHaveLength(1);
        expect(mounts[0].points, 'one point per asset measured on both axes').toHaveLength(MEASURED.size);
        expect(screen.getByTestId('risk-asset-set-l3-scatter'), 'the stand-in publishes the testId it was handed').toHaveAttribute('data-point-count', String(MEASURED.size));
    });

    it("the stand-in's live props follow the section after mount: a reactive prop is handed as a getter", async () => {
        // What the chart-half cases stand on, proved with a prop the selection does not touch:
        // they read `live.selectedId` after a click, which is only meaningful if the object the chart
        // was handed at mount answers with the section's current value, without a re-mount.
        const {rerender} = render(AssetSetRiskReturnSection, {props: propsOf(MAIN)});
        const [mount] = scatterMounts();
        expect(mount.live.points, 'at mount: one point per measured asset').toHaveLength(MEASURED.size);

        await rerender(propsOf(WITH_BENCHMARK));

        expect(scatterMounts(), 'the scatter was mounted again: the case below would read a fresh object, not a live one').toHaveLength(1);
        expect(
            mount.live.points.map((point) => point.id),
            'the props object handed at mount must answer with the points of now — the benchmark dot joined',
        ).toContain('benchmark');
        expect(mount.live.points).toHaveLength(MEASURED.size + 1);
    });
});

// ═══════════════════════════════════════════════════════════════════════════════════════════════
// The DataTable redesign
// ═══════════════════════════════════════════════════════════════════════════════════════════════

describe('AssetSetRiskReturnSection — the table is the project DataTable', () => {
    it('without a benchmark: the selection in its own order under five columns, nothing sorted and every column sortable', () => {
        mountWith(MAIN);
        const table = l3Table();

        expect(table.querySelector('table'), 'risk-asset-set-l3-table must wrap the DataTable, not be the table itself').not.toBeNull();
        expect(table).toHaveAttribute('data-row-count', String(SELECTION.length));
        expect(headerOrder(), "the header row is not DataTable's, or not the five columns in their order").toEqual(['name', ...BASE_VALUE_COLUMNS]);
        expect(drawnOrder(), "the rows must open in the selection's own order: the reader sorts, the system never ranks").toEqual(SELECTION);

        for (const column of ['name', ...BASE_VALUE_COLUMNS]) {
            expect(screen.getByTestId(`dt-header-${column}`), `${column} opens sorted`).toHaveAttribute('data-sort', 'none');
            expect(screen.getByTestId(`dt-sort-${column}`), `${column} cannot be sorted`).toBeEnabled();
            // A title that printed its own key would read "risk.…": worded, never read.
            const title = normalize(screen.getByTestId(`dt-sort-${column}`).textContent);
            expect(title, `${column}: the title is empty`).not.toBe('');
            expect(title, `${column}: the title prints a catalogue key instead of its message`).not.toMatch(/^[a-z]+(\.[A-Za-z0-9_]+)+$/);
        }

        // Each row holds its own asset's cells, one of each, and nothing of a benchmark.
        for (const assetId of SELECTION) {
            const row = rowById(assetId);
            expect(
                within(row)
                    .getAllByTestId('risk-asset-set-l3-name')
                    .map((cell) => cell.dataset.assetId),
                `asset ${assetId}: the row's name cell must carry the row's asset`,
            ).toEqual([String(assetId)]);
            for (const column of BASE_VALUE_COLUMNS) expect(within(row).getAllByTestId(`risk-asset-set-l3-${column}`), `asset ${assetId}: ${column}`).toHaveLength(1);
        }
        for (const column of BENCHMARK_COLUMNS) {
            expect(screen.queryByTestId(`dt-header-${column}`), `${column}: a column with no reference to measure against`).toBeNull();
            expect(screen.queryAllByTestId(`risk-asset-set-l3-${column}`), `${column}: cells with no reference to measure against`).toHaveLength(0);
        }
    });

    it('with a benchmark that applies: beta and correlation join, last, with a cell in every row', () => {
        mountWith(WITH_BENCHMARK);

        expect(headerOrder(), 'the two benchmark columns close the header, after the four every table has').toEqual(['name', ...VALUE_COLUMNS]);
        expect(drawnOrder()).toEqual(SELECTION);
        for (const column of BENCHMARK_COLUMNS) {
            expect(screen.getByTestId(`dt-header-${column}`)).toHaveAttribute('data-sort', 'none');
            for (const assetId of SELECTION) expect(within(rowById(assetId)).getAllByTestId(`risk-asset-set-l3-${column}`), `asset ${assetId}: ${column}`).toHaveLength(1);
        }
    });

    it('draws every selected asset however many there are, with no pagination and no checkbox, filter or action chrome', () => {
        mountWith({assetIds: WIDE_SELECTION, assetLabels: WIDE_LABELS});

        expect(drawnOrder(), `${WIDE_SELECTION.length} assets selected and DataTable's default page holds 10: a row on page two reads as an asset nobody selected`).toEqual(WIDE_SELECTION);
        expect(l3Table()).toHaveAttribute('data-row-count', String(WIDE_SELECTION.length));
        expect(screen.queryByTestId('data-table-pagination')).toBeNull();
        expect(screen.queryByTestId('dt-select-all'), 'a row is selected by a click on it, one at a time: no select-all').toBeNull();
        expect(document.querySelectorAll('[data-testid^="dt-row-checkbox-"]'), 'a row is selected by a click on it: no checkbox column').toHaveLength(0);
        expect(document.querySelectorAll('[data-testid^="col-filter-trigger-"]'), 'no column filters: the selection is the filter').toHaveLength(0);
        expect(document.querySelectorAll('[data-testid^="row-actions-"]'), 'no row actions').toHaveLength(0);
    });

    it('keeps its layout under its own storage key', () => {
        mountWith(MAIN);

        expect(
            storageReads.filter((key) => key.includes('dataTable_risk-asset-set-l3_')),
            'DataTable read no preference under storageKey "risk-asset-set-l3": the level would share its widths and order with another table',
        ).not.toEqual([]);
    });

    it('the rows are the only row markup: risk-asset-set-l3-row is gone', () => {
        mountWith(MAIN);

        // Presence first: the table is drawn with a row per asset, so the absence is about a table that exists.
        expect(drawnOrder()).toEqual(SELECTION);
        expect(screen.queryAllByTestId('risk-asset-set-l3-row'), 'the hand-written row testid survived the redesign: rows are read from tr[data-row-id]').toHaveLength(0);
    });

    it('binds tableRef to the DataTable it draws, which lists the columns for the toggle', () => {
        const bound = mountBinding(MAIN);

        const table = bound.tableRef as {getColumnsForVisibility?: () => {id: string; visible: boolean}[]} | undefined;
        expect(typeof table?.getColumnsForVisibility, 'tableRef is not the DataTable instance: the column toggle in the frame would have nothing to read').toBe('function');
        expect(
            table?.getColumnsForVisibility?.().map(({id, visible}) => `${id}:${visible}`),
            'the toggle must list the five columns of this table, all visible',
        ).toEqual(['name', ...BASE_VALUE_COLUMNS].map((id) => `${id}:true`));
    });

    it.each([
        {state: 'failed', props: {failed: true}, drawn: 'risk-asset-set-l3-error'},
        {state: 'loading with no figure', props: {loading: true}, drawn: 'risk-asset-set-l3-loading'},
        {state: 'discarded with no figure', props: {discarded: true}, drawn: 'risk-asset-set-l3-discarded'},
        {state: 'an empty selection', props: {assetIds: []}, drawn: 'risk-asset-set-l3-empty'},
    ])('$state: no table, so tableRef is never set', ({props, drawn}) => {
        const bound = mountBinding(props);

        // The state is on screen — the absence is about a table this state does not draw.
        expect(screen.getByTestId(drawn)).toBeInTheDocument();
        expect(screen.queryByTestId('risk-asset-set-l3-table')).toBeNull();
        expect(bound.tableRef ?? undefined, 'a table reference with no table: the toggle would open onto nothing').toBeUndefined();
    });
});

describe('AssetSetRiskReturnSection — the headers explain, they do not link', () => {
    it('has no anchor, no info icon and no documentation link in its header row', () => {
        mountWith(WITH_BENCHMARK);

        // Presence first: the header row is DataTable's and holds all seven titles, so the absences
        // below are about a header that exists.
        expect(headerOrder(), "the header row is not DataTable's: its titles must be there before their links can be absent").toEqual(['name', ...VALUE_COLUMNS]);
        const headerRow = l3Table().querySelector('thead tr');
        expect(headerRow).not.toBeNull();
        expect(headerRow?.querySelectorAll('a'), "a link in the header row: the documentation is the frame's manual, the header only explains").toHaveLength(0);
        expect(document.querySelectorAll('[data-testid^="dt-header-tooltip-"]'), 'an ⓘ beside a title: DataTable draws one only for a tooltip with a URL, and these have none').toHaveLength(0);
        expect(document.querySelectorAll('[data-testid^="risk-asset-set-l3-docs-"]'), 'no per-column documentation link').toHaveLength(0);
    });

    it.each(VALUE_COLUMNS)('%s: its title reveals the help worded from its own columnHelp key', async (column) => {
        mountWith(WITH_BENCHMARK);

        // Revealed the way `DataTableHeaderTooltip.test.ts` reveals a sortable title's tooltip: a
        // press pins it open. The press also sorts, which is not this case's subject.
        await fireEvent.click(screen.getByTestId(`dt-sort-${column}`));
        const help = await screen.findByRole('tooltip');

        if (column === 'expectedReturn') {
            // Its title is the short name since the developer's review of 06/10/2026, so its help opens
            // with the full one, on a line of its own, and then says how it is computed.
            const fullName = get(_)('risk.assetSet.levels.l3.expectedReturn');
            expect((help.textContent ?? '').split('\n')[0].trim(), 'expectedReturn: the tooltip does not open with the full name, on a line of its own').toBe(fullName);
            expect(normalize(help.textContent), `expectedReturn: the tooltip is not the full name followed by the message of ${helpKey(column)}`).toBe(normalize(get(_)('risk.levels.l3.table.namedHelp', {values: {name: fullName, help: get(_)(helpKey(column))}})));
            return;
        }
        expect(normalize(help.textContent), `${column}: the tooltip is not the message of ${helpKey(column)}`).toBe(normalize(get(_)(helpKey(column))));
    });

    it('name: the same press on its title reveals nothing — the one column without help', async () => {
        mountWith(WITH_BENCHMARK);

        // Positive control: on this very mount, the press does reveal a value column's help.
        await fireEvent.click(screen.getByTestId('dt-sort-expectedReturn'));
        const help = await screen.findByRole('tooltip');
        await waitFor(() => expect(help).toHaveAttribute('data-dismissable', 'true'));
        await fireEvent.click(document.body);
        await waitFor(() => expect(screen.queryByRole('tooltip')).toBeNull());

        await fireEvent.click(screen.getByTestId('dt-sort-name'));
        // The press landed — the column sorted — so the absence below is about a press that happened.
        expect(screen.getByTestId('dt-header-name')).toHaveAttribute('data-sort', 'asc');
        expect(screen.queryByRole('tooltip'), 'the asset column has no help of its own to show').toBeNull();
    });

    it('expectedReturn: its title is the short name, and the full name is the column menu’s and the tooltip’s first line', async () => {
        const bound = mountBinding(MAIN);
        const fullName = get(_)('risk.assetSet.levels.l3.expectedReturn');

        expect(normalize(screen.getByTestId('dt-sort-expectedReturn').textContent), 'the return column’s title must be the short name (the developer’s review of 06/10/2026)').toBe(normalize(get(_)('risk.levels.l3.table.expectedReturnShort')));

        const table = bound.tableRef as {getColumnsForVisibility?: () => {id: string; displayName?: string | (() => string)}[]} | undefined;
        const listed = table?.getColumnsForVisibility?.().find((column) => column.id === 'expectedReturn')?.displayName;
        expect(typeof listed === 'function' ? listed() : listed, 'the column menu must name the return in full').toBe(fullName);

        await fireEvent.click(screen.getByTestId('dt-sort-expectedReturn'));
        const help = await screen.findByRole('tooltip');
        expect((help.textContent ?? '').split('\n')[0].trim(), 'the title’s tooltip must open with the full name').toBe(fullName);
    });
});

describe("AssetSetRiskReturnSection — the catalogues: every column's help and the axis in each, the no-benchmark note in none", () => {
    const KEYS = [...VALUE_COLUMNS.map(helpKey), AXIS_RETURN_KEY];

    it.each([...SUPPORTED_LOCALES])('%s.json', (locale) => {
        const catalogue = CATALOGUES[locale];

        // Barrier: the walk reaches the level — the return column's title lives in the same subtree.
        expect(typeof at(catalogue, 'risk.assetSet.levels.l3.expectedReturn'), `${locale}.json: the walk never reached risk.assetSet.levels.l3`).toBe('string');

        const missing = KEYS.filter((key) => {
            const message = at(catalogue, key);
            return typeof message !== 'string' || message.trim() === '';
        });
        expect(missing, `${locale}.json: these tooltips, or the axis, would print their own key`).toEqual([]);
    });

    it.each([...SUPPORTED_LOCALES])('%s.json: the no-benchmark note has left it with the page', (locale) => {
        const catalogue = CATALOGUES[locale];

        // Barrier: the walk reaches the level the key lived in, so "absent" is about a subtree that exists.
        expect(typeof at(catalogue, 'risk.assetSet.levels.l3.expectedReturn'), `${locale}.json: the walk never reached risk.assetSet.levels.l3`).toBe('string');
        expect(at(catalogue, NO_BENCHMARK_KEY), `${locale}.json still carries ${NO_BENCHMARK_KEY}: the note left the page (second review), its message leaves the catalogue — through the i18n tool`).toBeUndefined();
    });
});

describe('AssetSetRiskReturnSection — the asset cell', () => {
    it('draws the icon assetIcons gives an asset, and the name alone for an asset it gives none', () => {
        mountWith(MAIN);

        for (const assetId of SELECTION) {
            const cell = nameCell(assetId);
            const url = ICONS.get(assetId);
            if (url === undefined) {
                expect(within(cell).queryByTestId('risk-asset-set-l3-icon'), `asset ${assetId}: no icon in the map, no icon drawn`).toBeNull();
                expect(cell.querySelectorAll('img'), `asset ${assetId}: no stand-in image either`).toHaveLength(0);
            } else {
                const icons = within(cell).getAllByTestId('risk-asset-set-l3-icon');
                expect(icons, `asset ${assetId}: one icon, beside the name`).toHaveLength(1);
                expect(icons[0].tagName).toBe('IMG');
                expect(icons[0].getAttribute('src'), `asset ${assetId}: the icon must be the one the map gives this asset`).toBe(url);
            }
        }
    });

    it('holds each name in the marquee span of its own cell', () => {
        mountWith(MAIN);

        for (const assetId of SELECTION) {
            expect(normalize(marqueeOf(nameCell(assetId)).textContent), `asset ${assetId}`).toBe(LABELS.get(assetId));
        }
    });

    it.each(MARKUP_NAMES)('draws $label as text, never as markup', ({assetId, label, forbidden}) => {
        mountWith({assetIds: MARKUP_NAMES.map((entry) => entry.assetId), assetLabels: new Map(MARKUP_NAMES.map((entry): [number, string] => [entry.assetId, entry.label])), assetIcons: MARKUP_ICONS});

        const cell = nameCell(assetId);
        expect(normalize(marqueeOf(cell).textContent), 'the name must reach the screen character for character').toBe(label);
        if (forbidden !== null) {
            const smuggled = [...cell.querySelectorAll(forbidden)].filter((node) => node.getAttribute('data-testid') !== 'risk-asset-set-l3-icon');
            expect(smuggled, `the name became a <${forbidden}> element`).toHaveLength(0);
        }
    });
});

describe('AssetSetRiskReturnSection — the value cells', () => {
    it('draws the volatility as a percentage, the return with its sign, the ratios as formatRatio does, and a dash marked unmeasured where nothing was measured', () => {
        mountWith(WITH_BENCHMARK);

        for (const [assetId, drawn] of DRAWN) {
            for (const column of VALUE_COLUMNS) {
                const cell = cellOf(assetId, column);
                expect(cell, `asset ${assetId}: ${column} is not measured — its fixture was rejected by a schema`).toHaveAttribute('data-measured', 'true');
                expect(normalize(cell.textContent), `asset ${assetId}: ${column}`).toBe(drawn[column]);
            }
        }

        for (const column of VALUE_COLUMNS) {
            const cell = cellOf(UNMEASURED, column);
            expect(cell, `${column}: an unmeasured asset must say so, never print a figure`).toHaveAttribute('data-measured', 'false');
            expect(normalize(cell.textContent), `${column}: the blank is an em-dash, not a zero`).toBe('\u2014');
        }
    });

    it('without a benchmark, the four cells of every table are the same figures', () => {
        mountWith(MAIN);

        for (const [assetId, drawn] of DRAWN) {
            for (const column of BASE_VALUE_COLUMNS) {
                expect(cellOf(assetId, column)).toHaveAttribute('data-measured', 'true');
                expect(normalize(cellOf(assetId, column).textContent), `asset ${assetId}: ${column}`).toBe(drawn[column]);
            }
        }
    });
});

describe('AssetSetRiskReturnSection — a column sorts by the figure it draws', () => {
    it.each(VALUE_SORTS)('$column: ascending, descending, the blank last both ways, and the third press restores the selection', async ({column, ascending, descending}) => {
        mountWith(WITH_BENCHMARK);
        expect(drawnOrder(), 'the rows must open in the selection order').toEqual(SELECTION);

        await press(column, 'asc');
        expect(drawnOrder(), `${column} ascending: the smallest figure first, with its sign, the blank last`).toEqual([...ascending]);
        expectSortedAsDrawn(column, 'asc');

        await press(column, 'desc');
        expect(drawnOrder(), `${column} descending: the largest figure first, the blank still last`).toEqual([...descending]);
        expectSortedAsDrawn(column, 'desc');

        await press(column, 'none');
        expect(drawnOrder(), `${column}: the third press must give the rows back in the selection's order`).toEqual(SELECTION);
    });

    it('expectedReturn: a loss sorts below a gain by its value with its sign, never by its size', async () => {
        mountWith(MAIN);

        await press('expectedReturn', 'asc');
        const order = drawnOrder();
        // 63 draws −1.2%, 61 draws +4.5%, 64 draws −3.4%: by size 63 would open the list.
        expect(order.indexOf(63), '−1.2% must come before +4.5% ascending').toBeLessThan(order.indexOf(61));
        expect(order.indexOf(64), '−3.4% must come before −1.2% ascending: sorted by the value drawn, not by its magnitude').toBeLessThan(order.indexOf(63));
        expect(order[order.length - 1], 'the blank is last').toBe(UNMEASURED);
    });

    it('name: sorts by the name without its emoji, ties broken by id, and the third press restores the selection', async () => {
        mountWith({assetIds: NAME_SELECTION, assetLabels: NAME_LABELS});
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

describe('AssetSetRiskReturnSection — the scatter', () => {
    it("labels its vertical axis with the lab's own key, risk.assetSet.levels.l3.axisReturn", () => {
        mountWith(MAIN);

        const mounts = scatterMounts();
        expect(mounts, 'barrier: four measured points draw the scatter').toHaveLength(1);
        // Compared with `$_()` of the key, because the question is which key: until the i18n step adds
        // it, both sides are the key itself, and the catalogue case above is the one that stays red.
        // The key it replaces is the portfolio L3's, which Dashboard and Broker Detail keep.
        expect(mounts[0].labels.return, `the vertical axis is not worded from ${AXIS_RETURN_KEY} (the old one was ${PORTFOLIO_AXIS_RETURN_KEY})`).toBe(get(_)(AXIS_RETURN_KEY));
    });

    it('is drawn with its note from two measured points up, one dot per asset and no aggregate', () => {
        mountWith(MAIN);

        const block = screen.getByTestId('risk-asset-set-l3-risk-return');
        expect(within(block).getByTestId('risk-asset-set-l3-scatter')).toBeInTheDocument();
        expect(normalize(within(block).getByTestId('risk-asset-set-l3-scatter-note').textContent), 'the note under the scatter is empty').not.toBe('');
        const [mount] = scatterMounts();
        expect(
            mount.points.every((point) => point.role === 'asset'),
            'a point that is not an asset: with no benchmark, anything else is an aggregate nobody measured',
        ).toBe(true);
    });

    it('adds the reference as a benchmark dot when a benchmark applies — never as a portfolio', () => {
        mountWith(WITH_BENCHMARK);

        const [mount] = scatterMounts();
        expect(mount.points, 'one dot per measured asset and one for the reference').toHaveLength(MEASURED.size + 1);
        expect(mount.points.filter((point) => point.role === 'benchmark').map((point) => point.id)).toEqual(['benchmark']);
        expect(
            mount.points.some((point) => point.role === 'portfolio'),
            "a portfolio dot would anchor the capital market line: the judgement this page's payload makes impossible",
        ).toBe(false);
    });

    it('is not drawn from a single point: one dot is a fact, not a comparison', () => {
        const single = ok('invented-single-point', 'asset_set_risk_return', {kind: 'risk_return_set', items: [{asset_id: 61, volatility: 0.18, expected_annual_return: 0.045}]});
        mountWith({...MAIN, riskReturn: single, kpi: null});

        // Barrier: the section rendered its body, a table — the absence is about the scatter alone.
        // (It stood on the blank note until the third review took the note away.)
        expect(l3Table()).toHaveAttribute('data-row-count', String(SELECTION.length));
        expect(screen.queryByTestId('risk-asset-set-l3-risk-return')).toBeNull();
        expect(scatterMounts()).toHaveLength(0);
    });
});

describe('AssetSetRiskReturnSection — the states the redesign leaves alone', () => {
    it('a failed wave: a sentence and a retry that asks again, and no table', async () => {
        const onretry = vi.fn();
        mountWith({...MAIN, riskReturn: null, kpi: null, failed: true, onretry});

        const block = screen.getByTestId('risk-asset-set-l3-error');
        const retry = within(block).getByTestId('risk-asset-set-l3-retry');
        expect(retry.tagName).toBe('BUTTON');
        const beside = block.cloneNode(true) as HTMLElement;
        beside.querySelectorAll('[data-testid="risk-asset-set-l3-retry"]').forEach((node) => node.remove());
        expect(normalize(beside.textContent), 'the error block offers a retry but no sentence saying what failed').not.toBe('');
        expect(screen.queryByTestId('risk-asset-set-l3-table')).toBeNull();

        await fireEvent.click(retry);
        expect(onretry).toHaveBeenCalledTimes(1);
    });

    it('loading with no figure: the skeleton, and no table', () => {
        mountWith({assetIds: SELECTION, assetLabels: LABELS, loading: true});

        expect(screen.getByTestId('risk-asset-set-l3-loading')).toBeInTheDocument();
        expect(screen.queryByTestId('risk-asset-set-l3-table')).toBeNull();
    });

    it('loading with figures: a refresh in flight keeps the table', () => {
        mountWith({...MAIN, loading: true});

        expect(screen.getByTestId('risk-asset-set-l3-table')).toHaveAttribute('data-row-count', String(SELECTION.length));
        expect(screen.queryByTestId('risk-asset-set-l3-loading')).toBeNull();
    });

    it('discarded with no figure: the retry and nothing else, and no table', async () => {
        const onretry = vi.fn();
        mountWith({assetIds: SELECTION, assetLabels: LABELS, discarded: true, onretry});

        const block = screen.getByTestId('risk-asset-set-l3-discarded');
        const retry = within(block).getByTestId('risk-asset-set-l3-retry');
        // Nothing else: the frame says the answer was lost (`answer_discarded`), once; the body offers the cure.
        const beside = block.cloneNode(true) as HTMLElement;
        beside.querySelectorAll('[data-testid="risk-asset-set-l3-retry"]').forEach((node) => node.remove());
        expect(normalize(beside.textContent), 'the discarded block carries a sentence of its own: the frame already says it').toBe('');
        expect(screen.queryByTestId('risk-asset-set-l3-table')).toBeNull();
        await fireEvent.click(retry);
        expect(onretry).toHaveBeenCalledTimes(1);
    });

    it('discarded with figures: the table stays', () => {
        mountWith({...MAIN, discarded: true});

        expect(screen.getByTestId('risk-asset-set-l3-table')).toHaveAttribute('data-row-count', String(SELECTION.length));
        expect(screen.queryByTestId('risk-asset-set-l3-discarded')).toBeNull();
    });

    it('an empty selection: the empty state, and no table', () => {
        mountWith({assetIds: [], assetLabels: new Map()});

        expect(screen.getByTestId('risk-asset-set-l3-empty')).toBeInTheDocument();
        expect(screen.queryByTestId('risk-asset-set-l3-table')).toBeNull();
    });

    // The case that pinned `-blank-note` under both tables here moved out with the note: the third
    // review takes the note away, and "the fixed blank note is gone, in every state" below says so.
});

// ═══════════════════════════════════════════════════════════════════════════════════════════════
// The second review (2026-09-30, afternoon)
// ═══════════════════════════════════════════════════════════════════════════════════════════════

describe('AssetSetRiskReturnSection — the no-benchmark note is gone, in every state', () => {
    /**
     * Each state with the element that proves its body is drawn: on the two tables that is the table
     * itself, in the very branch the note sat in — so "no note" is about a body that exists. (It was
     * the blank note until the third review took that note away too.)
     */
    it.each([
        {state: 'the table without a benchmark', props: MAIN, drawn: 'risk-asset-set-l3-table', benchmark: 'false'},
        {state: 'the table with a benchmark', props: WITH_BENCHMARK, drawn: 'risk-asset-set-l3-table', benchmark: 'true'},
        {state: 'failed', props: {failed: true}, drawn: 'risk-asset-set-l3-error', benchmark: 'false'},
        {state: 'loading with no figure', props: {loading: true}, drawn: 'risk-asset-set-l3-loading', benchmark: 'false'},
        {state: 'discarded with no figure', props: {discarded: true}, drawn: 'risk-asset-set-l3-discarded', benchmark: 'false'},
        {state: 'an empty selection', props: {assetIds: []}, drawn: 'risk-asset-set-l3-empty', benchmark: 'false'},
    ])('$state: no note, under its testid or any other', ({props, drawn, benchmark}) => {
        mountWith(props);

        const section = screen.getByTestId('risk-asset-set-l3');
        expect(section).toHaveAttribute('data-benchmark', benchmark);
        expect(screen.getByTestId(drawn), 'barrier: the state draws its own body').toBeInTheDocument();

        expect(screen.queryByTestId(NO_BENCHMARK_TESTID), 'the no-benchmark note is drawn: the developer took it out of this page ("fuori luogo qui")').toBeNull();
        // Nor its sentence under another name. Compared with `$_()` of the key, so no language is read;
        // once the key leaves the catalogues `$_()` answers the key itself — which is exactly what a
        // section still asking for it would print.
        const sentence = normalize(get(_)(NO_BENCHMARK_KEY));
        expect(sentence, 'premise: the key resolves to something to look for').not.toBe('');
        expect(normalize(section.textContent), 'the no-benchmark sentence is still in the section, under another testid').not.toContain(sentence);
    });
});

describe('AssetSetRiskReturnSection — a click on a row selects it, one row at a time', () => {
    it('opens with nothing selected, and every row says so', () => {
        mountWith(MAIN);

        expect(drawnOrder(), 'barrier: a row per selected asset').toEqual(SELECTION);
        expectSelected(null, 'nothing may be selected before the reader clicks');
    });

    it('a click on a row selects that row and no other, and adds no selection column', async () => {
        mountWith(MAIN);
        expectSelected(null, 'premise: nothing selected on opening');

        await clickRow(65);

        expectSelected(65, 'a click on a row must select it');
        // Single selection: the click is the whole interface — no checkbox column appeared to hold it.
        expect(headerOrder(), 'selecting a row changed the header: single selection draws no selection column').toEqual(['name', ...BASE_VALUE_COLUMNS]);
        expect(screen.queryByTestId('dt-select-all')).toBeNull();
        expect(document.querySelectorAll('[data-testid^="dt-row-checkbox-"]')).toHaveLength(0);
    });

    it('a second click on the selected row clears the selection', async () => {
        mountWith(MAIN);

        await clickRow(65);
        expectSelected(65, 'premise: the first click selects');

        await clickRow(65);
        expectSelected(null, 'a second click on the selected row must clear it');
    });

    it('a click on another row moves the selection there: one row at most', async () => {
        mountWith(MAIN);

        await clickRow(65);
        expectSelected(65, 'premise: the first click selects');

        await clickRow(61);
        expectSelected(61, 'the selection must move to the row clicked and leave the one before');

        await clickRow(63);
        expectSelected(63, 'and move again, still one row');
    });

    it('the selection belongs to the asset, not to a position: a sort carries it with its row', async () => {
        mountWith(MAIN);

        await clickRow(61);
        expectSelected(61, 'premise: the click selects');
        const opening = drawnOrder().indexOf(61);

        await press('volatility', 'asc');
        expect(drawnOrder().indexOf(61), 'premise: the sort must move the selected row, or a selection kept by position would pass').not.toBe(opening);
        expectSelected(61, 'the sort must carry the selection with its asset');
    });
});

/**
 * The chart half of the linked selection, read off the stand-in, which records the two props
 * `ScatterChart` takes for it: `selectedId`, what the section hands the chart to mark, and
 * `onpointclick`, which the section answers by toggling the dot's row through the table's instance —
 * so the table stays the one source, and a dot's click selects, moves and clears as a row's does.
 */
describe('AssetSetRiskReturnSection — the chart half of the selection', () => {
    /** What the section hands the one scatter it drew, as it stands now (the getters are live). */
    function handedToScatter(): (typeof scatter.mounts)[number]['live'] {
        const mounts = scatterMounts();
        expect(mounts, 'barrier: the section drew one scatter').toHaveLength(1);
        return mounts[0].live;
    }

    it('hands the scatter selectedId: null on opening, asset-<id> for the selected row, null once cleared', async () => {
        mountWith(MAIN);
        const handed = handedToScatter();
        expect('selectedId' in handed, 'the section hands the scatter no selectedId at all').toBe(true);
        expect(handed.selectedId, 'nothing selected on opening: the chart marks no dot').toBeNull();

        await clickRow(65);
        expect(handed.selectedId, "the selected row's dot").toBe('asset-65');

        await clickRow(61);
        expect(handed.selectedId, 'the chart follows the selection when it moves').toBe('asset-61');

        await clickRow(61);
        expect(handed.selectedId, 'a cleared selection marks no dot').toBeNull();
    });

    it("a click on an asset's dot selects that asset's row through the table, and a click on another dot moves it", async () => {
        mountWith(MAIN);
        const handed = handedToScatter();
        expect(typeof handed.onpointclick, 'the section hands the scatter no onpointclick').toBe('function');
        expectSelected(null, 'premise: nothing selected on opening');

        handed.onpointclick?.('asset-65');
        await tick();
        expectSelected(65, "a click on asset 65's dot must select its row");
        expect(handed.selectedId, 'the chart hears of it like any other selection').toBe('asset-65');

        handed.onpointclick?.('asset-61');
        await tick();
        expectSelected(61, 'a click on another dot must move the selection there');
        expect(handed.selectedId).toBe('asset-61');
    });

    it("a second click on the selected asset's dot clears the selection, as a second click on its row does", async () => {
        mountWith(MAIN);
        const handed = handedToScatter();
        expect(typeof handed.onpointclick, 'the section hands the scatter no onpointclick').toBe('function');
        expectSelected(null, 'premise: nothing selected on opening');

        handed.onpointclick?.('asset-65');
        await tick();
        // Barrier: the first click did select, so the clear below is the toggle, not a click that did nothing.
        expectSelected(65, "premise: a click on asset 65's dot selects its row");
        expect(handed.selectedId, 'premise: the chart marks the dot').toBe('asset-65');

        handed.onpointclick?.('asset-65');
        await tick();
        expectSelected(null, 'a second click on the selected dot must clear the selection, as a second click on its row does');
        expect(handed.selectedId, 'a cleared selection marks no dot').toBeNull();
    });

    it('a click on the benchmark dot changes nothing: a reference outside the selection has no row', async () => {
        mountWith(WITH_BENCHMARK);
        const handed = handedToScatter();
        expect(typeof handed.onpointclick, 'the section hands the scatter no onpointclick').toBe('function');
        expect(
            handed.points.some((point) => point.id === 'benchmark'),
            'premise: the reference is drawn as a dot',
        ).toBe(true);

        handed.onpointclick?.('benchmark');
        await tick();
        expectSelected(null, 'a click on the benchmark dot selected a row');
        expect(handed.selectedId).toBeNull();

        await clickRow(65);
        handed.onpointclick?.('benchmark');
        await tick();
        expectSelected(65, 'a click on the benchmark dot must leave the selection as it was');
        expect(handed.selectedId).toBe('asset-65');
    });

    it('a click on a dot whose asset has no row changes nothing: the section selects only what its table holds', async () => {
        mountWith(MAIN);
        const handed = handedToScatter();
        expect(typeof handed.onpointclick, 'the section hands the scatter no onpointclick').toBe('function');
        // Presence first, then the absence: the table is drawn with a row per selected asset, and the
        // reference's asset — outside this selection (D371 lets a reader select it) — is not among them.
        expect(drawnOrder(), 'premise: a row per selected asset').toEqual(SELECTION);
        expect(drawnOrder(), `premise: asset ${BENCHMARK_ID} has no row`).not.toContain(BENCHMARK_ID);

        handed.onpointclick?.(`asset-${BENCHMARK_ID}`);
        await tick();
        expectSelected(null, `a click on asset-${BENCHMARK_ID}, which has no row, selected one`);
        expect(handed.selectedId, 'the chart was handed a selection no row holds').toBeNull();

        await clickRow(65);
        handed.onpointclick?.(`asset-${BENCHMARK_ID}`);
        await tick();
        expectSelected(65, `a click on asset-${BENCHMARK_ID} must leave the selection as it was`);
        expect(handed.selectedId).toBe('asset-65');
    });
});

// ═══════════════════════════════════════════════════════════════════════════════════════════════
// The third review (2026-10-01): the dashes explain themselves, and the period is stated
// ═══════════════════════════════════════════════════════════════════════════════════════════════

describe('AssetSetRiskReturnSection — the fixed blank note is gone, in every state', () => {
    it.each([
        {state: 'the table without a benchmark', props: MAIN, drawn: 'risk-asset-set-l3-table'},
        {state: 'the table with a benchmark', props: WITH_BENCHMARK, drawn: 'risk-asset-set-l3-table'},
        {state: 'failed', props: {failed: true}, drawn: 'risk-asset-set-l3-error'},
        {state: 'loading with no figure', props: {loading: true}, drawn: 'risk-asset-set-l3-loading'},
        {state: 'discarded with no figure', props: {discarded: true}, drawn: 'risk-asset-set-l3-discarded'},
        {state: 'an empty selection', props: {assetIds: []}, drawn: 'risk-asset-set-l3-empty'},
    ])('$state: no note, under its testid or any other', ({props, drawn}) => {
        mountWith(props);

        expect(screen.getByTestId(drawn), 'barrier: the state draws its own body').toBeInTheDocument();
        expect(screen.queryByTestId(BLANK_NOTE_TESTID), 'the fixed note under the table is drawn: each dash explains itself now').toBeNull();
        // Nor its sentence under another name. Compared with `$_()` of the key, so no language is read;
        // a closed tooltip holds no text, so the dashes on the tables do not print it either.
        const sentence = normalize(get(_)(BLANK_NOTE_KEY));
        expect(sentence, 'premise: the key resolves to something to look for').not.toBe('');
        expect(normalize(screen.getByTestId('risk-asset-set-l3').textContent), "the note's sentence is still printed in the section, under another testid").not.toContain(sentence);
    });
});

describe('AssetSetRiskReturnSection — a dash explains itself', () => {
    it.each(VALUE_COLUMNS)('%s: the dash of an unmeasured asset opens the explanation the note used to give', async (column) => {
        mountWith(WITH_BENCHMARK);
        const cell = cellOf(UNMEASURED, column);
        expect(cell, 'premise: the asset is measured by no analytic').toHaveAttribute('data-measured', 'false');
        expect(normalize(cell.textContent), 'premise: the cell draws the em dash').toBe('\u2014');

        const trigger = explainerOf(cell);
        expect(trigger, `${column}: the dash is bare — it must sit in the project's Tooltip, as HtmlCell.tooltip draws it`).not.toBeNull();
        expect(trigger, 'the trigger is reachable from the keyboard').toHaveAttribute('tabindex', '0');
        expect(screen.queryByRole('tooltip'), 'premise: nothing is open before the click').toBeNull();

        // A click on the dash itself, where a pointer lands. That it does not also select the row is the
        // shared Tooltip's accepted side effect, and is deliberately asserted neither way.
        await fireEvent.click(cell);
        const help = await screen.findByRole('tooltip');
        expect(help).toHaveAttribute('data-testid', 'tooltip-content');
        const sentence = normalize(get(_)(BLANK_NOTE_KEY));
        expect(sentence, `premise: ${BLANK_NOTE_KEY} resolves to a message, not to itself`).not.toBe(BLANK_NOTE_KEY);
        expect(normalize(help.textContent), `${column}: the explanation is not the message of ${BLANK_NOTE_KEY}`).toBe(sentence);
    });

    /**
     * Every cell of a mount, figure or dash: a figure is bare, a dash is wrapped. Two fixtures, because a
     * wrapper decided per row would pass the first — whose blank row is blank throughout — and only the
     * second, where the measured rows mix both, tells a row's rule from a cell's.
     */
    const DASH_FIXTURES: {fixture: string; props: MountProps; columns: readonly ValueColumn[]; figures: number; dashes: number}[] = [
        {fixture: 'a blank row beside full ones', props: WITH_BENCHMARK, columns: VALUE_COLUMNS, figures: 24, dashes: 6},
        {fixture: 'points measured, ratios not', props: {assetIds: SELECTION, assetLabels: LABELS, assetIcons: ICONS, riskReturn: RISK_RETURN}, columns: BASE_VALUE_COLUMNS, figures: 8, dashes: 12},
    ];

    it.each(DASH_FIXTURES)('$fixture: only the dashes are wrapped, cell by cell', ({props, columns, figures, dashes}) => {
        mountWith(props);

        const cells = SELECTION.flatMap((assetId) => columns.map((column) => ({assetId, column, cell: cellOf(assetId, column)})));
        const measured = cells.filter(({cell}) => cell.getAttribute('data-measured') === 'true');
        const blank = cells.filter(({cell}) => cell.getAttribute('data-measured') === 'false');
        // Presence first: both kinds are on screen, so neither half below is about an empty set.
        expect({figures: measured.length, dashes: blank.length}, 'premise: the fixture draws its figures and its dashes').toEqual({figures, dashes});

        for (const {assetId, column, cell} of measured) expect(explainerOf(cell), `asset ${assetId}: ${column} is a figure, and is wrapped like a dash`).toBeNull();
        for (const {assetId, column, cell} of blank) expect(explainerOf(cell), `asset ${assetId}: ${column} is a dash with no explanation`).not.toBeNull();
    });

    it('a row made only of dashes is still selected by a click on its asset cell', async () => {
        mountWith(WITH_BENCHMARK);
        // Premise: the row has no figure to click — every value cell in it is a dash.
        for (const column of VALUE_COLUMNS) expect(cellOf(UNMEASURED, column), `premise: ${column} of asset ${UNMEASURED} is a dash`).toHaveAttribute('data-measured', 'false');
        expectSelected(null, 'premise: nothing selected on opening');

        await fireEvent.click(nameCell(UNMEASURED));
        expectSelected(UNMEASURED, 'a click on the asset cell of a row of dashes must select it: its dashes open their explanation, so the name is the way in');

        await fireEvent.click(nameCell(UNMEASURED));
        expectSelected(null, 'and a second click there clears it, as on any row');
    });
});

describe('AssetSetRiskReturnSection — the period the figures cover', () => {
    /** The note's contract — its four attributes — read as one object, so a red names every one that is off. */
    function periodOf(): Record<'start' | 'end' | 'days' | 'narrowed', string | undefined> {
        const note = screen.getByTestId(PERIOD_TESTID);
        return {start: note.dataset.start, end: note.dataset.end, days: note.dataset.days, narrowed: note.dataset.narrowed};
    }

    /** What the note must publish for a window. */
    function published(period: PeriodWindow): Record<'start' | 'end' | 'days' | 'narrowed', string> {
        return {start: period.start, end: period.end, days: String(period.days), narrowed: String(period.narrowed)};
    }

    /** The note's text, normalised. */
    function periodText(): string {
        return normalize(screen.getByTestId(PERIOD_TESTID).textContent);
    }

    /** The note's two lines (fourth review), each looked for inside the note: a line drawn anywhere else is not one of its lines. */
    function linesOf(): {windowLine: HTMLElement; annualizedLine: HTMLElement} {
        const note = screen.getByTestId(PERIOD_TESTID);
        return {windowLine: within(note).getByTestId(PERIOD_WINDOW_LINE_TESTID), annualizedLine: within(note).getByTestId(PERIOD_ANNUALIZED_LINE_TESTID)};
    }

    /** A window's length, part by part: each unit that is not zero, worded by its plural key — `$_()` of the catalogue, never prose written here. */
    function lengthPartsOf(period: PeriodWindow): string[] {
        return LENGTH_UNITS.filter((unit) => period.length[unit] > 0).map((unit) => get(_)(PERIOD_LENGTH_KEYS[unit], {values: {count: period.length[unit]}}));
    }

    /** Parts joined as `Intl.ListFormat` joins a list in `locale`: the reader's language, unless another is named. */
    function joined(parts: string[], locale: string = get(currentLanguage)): string {
        return new Intl.ListFormat(locale, {style: 'long', type: 'conjunction'}).format(parts);
    }

    /**
     * The note's three sentences, as `$_()` words them: the dates as `dayFormatter($currentLanguage)`
     * writes them, the length as its parts joined in the reader's language.
     */
    function sentencesFor(period: PeriodWindow): {window: string; narrowed: string; annualized: string} {
        const day = dayFormatter(get(currentLanguage));
        const sentences = {
            window: normalize(get(_)(PERIOD_WINDOW_KEY, {values: {start: day(period.start), end: day(period.end), length: joined(lengthPartsOf(period))}})),
            narrowed: normalize(get(_)(PERIOD_NARROWED_KEY, {values: {selectedStart: day(SELECTED_START), selectedEnd: day(SELECTED_END)}})),
            annualized: normalize(get(_)(PERIOD_ANNUALIZED_KEY)),
        };
        // A message not handed every value it names comes back as its raw template, on both sides alike:
        // that is how the narrowed case stayed green while the note printed `{start} – {end} ({length})`.
        // A sentence still holding a brace measures nothing.
        for (const [name, sentence] of Object.entries(sentences)) expect(sentence, `premise: the ${name} sentence resolves every value its message names`).not.toMatch(/[{}]/);
        return sentences;
    }

    // Read directly, because the cases below compare against `$_()` of the same keys: a key missing
    // from the catalogue would come back as itself on both sides and agree with itself.
    it.each([...SUPPORTED_LOCALES])("%s.json words the note's three sentences, and the three parts of its length", (locale) => {
        const catalogue = CATALOGUES[locale];

        // Barrier: the walk reaches the level.
        expect(typeof at(catalogue, 'risk.assetSet.levels.l3.expectedReturn'), `${locale}.json: the walk never reached risk.assetSet.levels.l3`).toBe('string');
        const missing = [PERIOD_WINDOW_KEY, PERIOD_NARROWED_KEY, PERIOD_ANNUALIZED_KEY, ...Object.values(PERIOD_LENGTH_KEYS)].filter((key) => {
            const message = at(catalogue, key);
            return typeof message !== 'string' || message.trim() === '';
        });
        expect(missing, `${locale}.json: the period note would print these keys`).toEqual([]);
        // The window is worded around its length now, no longer around a count of days (fourth review).
        expect(at(catalogue, PERIOD_WINDOW_KEY), `${locale}.json: ${PERIOD_WINDOW_KEY} must take the length`).toContain('{length}');
        expect(at(catalogue, PERIOD_WINDOW_KEY), `${locale}.json: ${PERIOD_WINDOW_KEY} still takes a count of days`).not.toContain('{days}');
        for (const key of Object.values(PERIOD_LENGTH_KEYS)) expect(at(catalogue, key), `${locale}.json: ${key} must be a plural on {count}`).toMatch(/^\{count, plural,/);
    });

    it('a window that is the selected period: its attributes, then two lines — the period with its length, what is annualised — and no narrowing', () => {
        mountWith({...MAIN, riskReturn: withWindow(RISK_RETURN, FULL_YEAR.metadata), kpi: withWindow(KPI, FULL_YEAR.metadata)});

        expect(periodOf(), 'the attributes are the contract: data-days still publishes the count of days').toEqual(published(FULL_YEAR));
        const {windowLine, annualizedLine} = linesOf();
        expect(precedes(windowLine, annualizedLine), 'the period is the first line and what the figures make of it the second — neither inside the other').toBe(true);
        expect(screen.getByTestId(PERIOD_TESTID).textContent?.replace(/\s+/g, ''), 'the note says nothing outside its two lines').toBe(`${windowLine.textContent}${annualizedLine.textContent}`.replace(/\s+/g, ''));

        const sentences = sentencesFor(FULL_YEAR);
        const windowText = normalize(windowLine.textContent);
        const day = dayFormatter(get(currentLanguage));
        expect(windowText, 'the first day, as dayFormatter writes it').toContain(day(FULL_YEAR.start));
        expect(windowText, 'the last day, as dayFormatter writes it').toContain(day(FULL_YEAR.end));
        expect(periodText(), 'an ISO day reached the screen: the dates are written for a reader').not.toContain(FULL_YEAR.start);
        expect(windowText, 'the length is no longer a count of days: 365 is not on the line').not.toContain(String(FULL_YEAR.days));
        expect(windowText, `a year is a single part, worded by ${PERIOD_LENGTH_KEYS.years} with count 1`).toContain(get(_)(PERIOD_LENGTH_KEYS.years, {values: {count: 1}}));
        for (const unit of ['months', 'days'] as const) expect(windowText, `a part that is zero is left out: no ${unit} at 0`).not.toContain(get(_)(PERIOD_LENGTH_KEYS[unit], {values: {count: 0}}));
        expect(windowText, `the period, as ${PERIOD_WINDOW_KEY} words it with its length`).toContain(sentences.window);
        expect(normalize(annualizedLine.textContent), `what the figures do with it, as ${PERIOD_ANNUALIZED_KEY} words it`).toContain(sentences.annualized);
        expect(windowText, 'the annualisation is on the second line only').not.toContain(sentences.annualized);
        expect(periodText(), 'a window that is the selected period is not narrower: no narrowing sentence').not.toContain(sentences.narrowed);
    });

    it('a window narrower than the selection: data-narrowed, and the selected period named on the first line, after the window', () => {
        mountWith({...MAIN, riskReturn: withWindow(RISK_RETURN, LATE_START.metadata), kpi: withWindow(KPI, LATE_START.metadata)});

        expect(periodOf(), 'the attributes are the contract').toEqual(published(LATE_START));
        const {windowLine, annualizedLine} = linesOf();
        expect(precedes(windowLine, annualizedLine), 'the period is the first line and what the figures make of it the second — neither inside the other').toBe(true);
        const sentences = sentencesFor(LATE_START);
        const windowText = normalize(windowLine.textContent);
        const annualizedText = normalize(annualizedLine.textContent);
        const day = dayFormatter(get(currentLanguage));
        expect(windowText, "the toolbar's first day, as dayFormatter writes it").toContain(day(SELECTED_START));
        expect(windowText, "the toolbar's last day, as dayFormatter writes it").toContain(day(SELECTED_END));
        expect(windowText, 'the length is no longer a count of days: 258 is not on the line').not.toContain(String(LATE_START.days));
        expect(windowText, `the period, as ${PERIOD_WINDOW_KEY} words it with its length: ${joined(lengthPartsOf(LATE_START))}`).toContain(sentences.window);
        expect(windowText, `how it falls short of the selection, as ${PERIOD_NARROWED_KEY} words it with the toolbar's dates — on the period's line`).toContain(sentences.narrowed);
        // The order a reader needs: the period, then how it differs from the one chosen — and, on a line of its own, what the figures make of it.
        expect(windowText.indexOf(sentences.window), 'the narrowing is read before the period it qualifies').toBeLessThan(windowText.indexOf(sentences.narrowed));
        expect(annualizedText, `what the figures do with it, as ${PERIOD_ANNUALIZED_KEY} words it`).toContain(sentences.annualized);
        expect(windowText, 'the annualisation is on the second line only').not.toContain(sentences.annualized);
        expect(annualizedText, 'the narrowing qualifies the period: it is not on the annualisation line').not.toContain(sentences.narrowed);
    });

    it("a window of a year, two months and three days: every part, joined as Intl.ListFormat joins a list in the reader's language", () => {
        mountWith({...MAIN, riskReturn: withWindow(RISK_RETURN, YEAR_AND_MORE.metadata), kpi: withWindow(KPI, YEAR_AND_MORE.metadata), dateStart: YEAR_AND_MORE.start, dateEnd: YEAR_AND_MORE.end});

        expect(periodOf(), 'the attributes are the contract').toEqual(published(YEAR_AND_MORE));
        const parts = lengthPartsOf(YEAR_AND_MORE);
        expect(parts, 'premise: three parts, one per unit — a list Intl.ListFormat words otherwise than a plain join').toHaveLength(3);
        const windowText = normalize(linesOf().windowLine.textContent);
        expect(windowText, `the length, its parts joined as Intl.ListFormat joins them: ${joined(parts)}`).toContain(joined(parts));
        expect(windowText, `the period, as ${PERIOD_WINDOW_KEY} words it with its length`).toContain(sentencesFor(YEAR_AND_MORE).window);
        expect(windowText, 'the length is no longer a count of days: 430 is not on the line').not.toContain(String(YEAR_AND_MORE.days));
    });

    it('sits after the table, outside it, and before the scatter block', () => {
        mountWith({...MAIN, riskReturn: withWindow(RISK_RETURN, FULL_YEAR.metadata), kpi: withWindow(KPI, FULL_YEAR.metadata)});

        const note = screen.getByTestId(PERIOD_TESTID);
        // Barrier: four measured points draw the scatter block, so "before it" is about a block that is there.
        const block = screen.getByTestId('risk-asset-set-l3-risk-return');
        expect(precedes(l3Table(), note), 'the note must come after the table, and not inside it').toBe(true);
        expect(precedes(note, block), 'the note must come before the scatter block, and not inside it').toBe(true);
    });

    /**
     * Read from the first of `[riskReturn, kpi, comparison]` whose metadata measured anything. In one
     * answer the three normally agree — the KPI and the risk/return share one joint calendar, and the
     * comparison's can only be narrower, since the reference's prices join it — so they differ here
     * only so the one read can be told apart.
     */
    const SOURCES: {sources: string; props: MountProps; read: PeriodWindow; from: string}[] = [
        {sources: 'all three carry metadata', props: {riskReturn: withWindow(RISK_RETURN, FULL_YEAR.metadata), kpi: withWindow(KPI, SIX_DAYS_LATE.metadata), comparison: withWindow(COMPARISON, LATE_START.metadata)}, read: FULL_YEAR, from: 'riskReturn'},
        {sources: 'riskReturn carries none', props: {riskReturn: RISK_RETURN, kpi: withWindow(KPI, SIX_DAYS_LATE.metadata), comparison: withWindow(COMPARISON, LATE_START.metadata)}, read: SIX_DAYS_LATE, from: 'kpi'},
        {sources: 'only the comparison answered', props: {riskReturn: null, kpi: null, comparison: withWindow(COMPARISON, LATE_START.metadata)}, read: LATE_START, from: 'comparison'},
    ];

    it.each(SOURCES)('$sources: the window is the one $from reports', ({props, read}) => {
        mountWith({...WITH_BENCHMARK, ...props});

        expect(l3Table(), 'barrier: the table is drawn').toHaveAttribute('data-row-count', String(SELECTION.length));
        expect(periodOf()).toEqual(published(read));
    });

    it.each([
        {why: 'no result carries metadata', props: MAIN},
        {why: 'none does with a benchmark either', props: WITH_BENCHMARK},
        {why: 'the metadata there measured nothing', props: {...MAIN, riskReturn: measuredNothing('invented-risk-return', 'asset_set_risk_return'), kpi: measuredNothing('invented-kpi', 'asset_set_kpi')}},
    ])('$why: the table, and no period note', ({props}) => {
        mountWith(props);

        expect(l3Table(), 'barrier: the table is drawn — the absence is about the note').toHaveAttribute('data-row-count', String(SELECTION.length));
        expect(screen.queryByTestId(PERIOD_TESTID), 'a period note with no window to state').toBeNull();
    });

    it.each([
        {state: 'failed', props: {...MAIN, riskReturn: withWindow(RISK_RETURN, FULL_YEAR.metadata), kpi: withWindow(KPI, FULL_YEAR.metadata), failed: true}, drawn: 'risk-asset-set-l3-error'},
        {state: 'an empty selection', props: {assetIds: [], assetLabels: new Map(), riskReturn: withWindow(RISK_RETURN, FULL_YEAR.metadata), kpi: withWindow(KPI, FULL_YEAR.metadata)}, drawn: 'risk-asset-set-l3-empty'},
    ])('$state: no period note outside the table branch, whatever the metadata says', ({props, drawn}) => {
        mountWith(props);

        expect(screen.getByTestId(drawn), 'barrier: the state draws its own body').toBeInTheDocument();
        expect(screen.queryByTestId('risk-asset-set-l3-table'), 'premise: this state draws no table').toBeNull();
        expect(screen.queryByTestId(PERIOD_TESTID), 'a period note beside no table').toBeNull();
    });

    it("writes the dates and the length in the reader's language: dayFormatter, the plural keys and Intl.ListFormat, all in $currentLanguage", async () => {
        await setupI18n('it');
        currentLanguage.set('it');
        try {
            mountWith({...MAIN, riskReturn: withWindow(RISK_RETURN, LATE_START.metadata), kpi: withWindow(KPI, LATE_START.metadata)});

            const italian = dayFormatter('it');
            expect(italian(LATE_START.start), 'premise: Italian writes the day otherwise than English').not.toBe(dayFormatter('en')(LATE_START.start));
            const windowText = normalize(linesOf().windowLine.textContent);
            for (const isoDay of [LATE_START.start, LATE_START.end, SELECTED_START, SELECTED_END]) {
                expect(windowText, `${isoDay} is not written as dayFormatter('it') writes it`).toContain(italian(isoDay));
            }
            const parts = lengthPartsOf(LATE_START);
            expect(joined(parts), 'premise: Italian joins the parts otherwise than English').not.toBe(joined(parts, 'en'));
            expect(windowText, `the length, its parts worded by the Italian catalogue and joined by Intl.ListFormat('it'): ${joined(parts)}`).toContain(joined(parts));
            expect(windowText, `the period, as ${PERIOD_WINDOW_KEY} words it in Italian`).toContain(sentencesFor(LATE_START).window);
        } finally {
            currentLanguage.set('en');
            await setupI18n('en');
        }
    });
});

// ═══════════════════════════════════════════════════════════════════════════════════════════════
// D371 (2026-10-05): the benchmark may be one of the selection
// ═══════════════════════════════════════════════════════════════════════════════════════════════

describe('AssetSetRiskReturnSection — a selected benchmark is not compared with itself (D371)', () => {
    /** The reference's two benchmark cells, in each mount that selects it: beside the others, and alone. */
    const REFERENCE_CELLS = [
        {fixture: 'selected mid-list', props: REFERENCE_SELECTED},
        {fixture: 'selected alone', props: REFERENCE_ALONE},
    ].flatMap(({fixture, props}) => BENCHMARK_COLUMNS.map((column) => ({fixture, props, column})));

    /** The dots the table can place — drawn rows whose volatility and average return are both measured — as `asset-<id>`, top to bottom. */
    function placeableDots(): string[] {
        const placeable = drawnOrder().filter((assetId) => cellOf(assetId, 'volatility').dataset.measured === 'true' && cellOf(assetId, 'expectedReturn').dataset.measured === 'true');
        return placeable.map((assetId) => `asset-${assetId}`);
    }

    it.each(REFERENCE_CELLS)('$fixture, $column: the em dash, marked data-reference="true" beside data-measured="false"', ({props, column}) => {
        mountWith(props);
        // Barrier: the reference has a row of its own, and the benchmark's columns are drawn in it.
        expect(drawnOrder(), `premise: asset ${BENCHMARK_ID} is selected and has a row`).toContain(BENCHMARK_ID);
        const cell = cellOf(BENCHMARK_ID, column);

        expect(cell, `${column}: the reference is not compared with itself, so nothing is measured`).toHaveAttribute('data-measured', 'false');
        expect(normalize(cell.textContent), `${column}: the blank is the em dash`).toBe('\u2014');
        expect(cell, `${column}: the reference's dash does not say it is the reference's`).toHaveAttribute('data-reference', 'true');
    });

    it.each(REFERENCE_CELLS)('$fixture, $column: the dash explains that the asset is the benchmark itself, not with the blank note', async ({props, column}) => {
        mountWith(props);
        const cell = cellOf(BENCHMARK_ID, column);
        expect(normalize(cell.textContent), 'premise: the cell draws the em dash').toBe('\u2014');
        const trigger = explainerOf(cell);
        expect(trigger, `${column}: the reference's dash is bare — it must sit in the project's Tooltip, as HtmlCell.tooltip draws it`).not.toBeNull();
        expect(trigger, 'the trigger is reachable from the keyboard').toHaveAttribute('tabindex', '0');
        expect(screen.queryByRole('tooltip'), 'premise: nothing is open before the click').toBeNull();

        const sentence = normalize(get(_)(REFERENCE_ITSELF_KEY));
        expect(sentence, `premise: ${REFERENCE_ITSELF_KEY} resolves to a message, not to itself`).not.toBe(REFERENCE_ITSELF_KEY);
        expect(sentence, `premise: ${REFERENCE_ITSELF_KEY} is not the blank note's sentence`).not.toBe(normalize(get(_)(BLANK_NOTE_KEY)));

        await fireEvent.click(cell);
        const help = await screen.findByRole('tooltip');
        expect(help).toHaveAttribute('data-testid', 'tooltip-content');
        expect(normalize(help.textContent), `${column}: the reference's dash is not explained with the message of ${REFERENCE_ITSELF_KEY}`).toBe(sentence);
    });

    it.each(BENCHMARK_COLUMNS)("%s: every other dash keeps the blank note's explanation, and no data-reference", async (column) => {
        mountWith(REFERENCE_SELECTED);
        // Barrier: the mount is the one that selects the reference — its row is drawn beside this one.
        expect(drawnOrder(), `premise: asset ${BENCHMARK_ID} is selected and has a row`).toContain(BENCHMARK_ID);
        const cell = cellOf(UNMEASURED, column);
        expect(cell, 'premise: the asset is measured by no analytic').toHaveAttribute('data-measured', 'false');
        expect(cell, `${column}: an unmeasured asset is not the reference`).not.toHaveAttribute('data-reference');

        await fireEvent.click(cell);
        const help = await screen.findByRole('tooltip');
        expect(normalize(help.textContent), `${column}: an unmeasured dash must keep the message of ${BLANK_NOTE_KEY}`).toBe(normalize(get(_)(BLANK_NOTE_KEY)));
    });

    it.each<{fixture: string; props: MountProps; marked: string[]}>([
        {fixture: 'the reference outside the selection', props: WITH_BENCHMARK, marked: []},
        {fixture: 'the reference selected mid-list', props: REFERENCE_SELECTED, marked: [`${BENCHMARK_ID}:beta=true`, `${BENCHMARK_ID}:correlation=true`]},
    ])("$fixture: data-reference marks the reference's beta and correlation, and no other value cell", ({props, marked}) => {
        mountWith(props);
        const cells = drawnOrder().flatMap((assetId) => VALUE_COLUMNS.map((column) => ({where: `${assetId}:${column}`, cell: cellOf(assetId, column)})));
        // Presence first: every selected asset draws its six cells, so "no other" is about cells that exist.
        expect(cells, 'premise: six value cells for every selected asset').toHaveLength((props.assetIds ?? SELECTION).length * VALUE_COLUMNS.length);
        const found = cells.filter(({cell}) => cell.hasAttribute('data-reference')).map(({where, cell}) => `${where}=${cell.getAttribute('data-reference')}`);

        expect(found, 'the value cells carrying data-reference, as asset:column=value').toEqual(marked);
    });

    it("the reference's own four columns are measured like any row's: its figures, bare and unmarked", () => {
        mountWith(REFERENCE_SELECTED);

        for (const column of BASE_VALUE_COLUMNS) {
            const cell = cellOf(BENCHMARK_ID, column);
            expect(cell, `${column}: the reference is measured like the others`).toHaveAttribute('data-measured', 'true');
            expect(normalize(cell.textContent), column).toBe(REFERENCE_DRAWN[column]);
            expect(explainerOf(cell), `${column}: a figure carries no explanation`).toBeNull();
            expect(cell, `${column}: only beta and correlation are the reference's to mark`).not.toHaveAttribute('data-reference');
        }
    });

    it.each([...SUPPORTED_LOCALES])("%s.json words the reference's explanation, a sentence of its own", (locale) => {
        const catalogue = CATALOGUES[locale];

        // Barrier: the walk reaches the level the key lives in.
        expect(typeof at(catalogue, 'risk.assetSet.levels.l3.expectedReturn'), `${locale}.json: the walk never reached risk.assetSet.levels.l3`).toBe('string');
        const message = at(catalogue, REFERENCE_ITSELF_KEY);
        expect(typeof message === 'string' && message.trim() !== '', `${locale}.json: ${REFERENCE_ITSELF_KEY} is missing or empty — the tooltip would print its key`).toBe(true);
        expect(message, `${locale}.json: the reference's explanation repeats the blank note`).not.toBe(at(catalogue, BLANK_NOTE_KEY));
    });

    it.each<{benchmark: string; props: MountProps; dots: (placeable: string[]) => string[]; benchmarkDot: string}>([
        {benchmark: 'outside the selection', props: WITH_BENCHMARK, dots: (placeable) => [...placeable, 'benchmark'], benchmarkDot: 'benchmark'},
        {benchmark: 'one of the selection', props: REFERENCE_SELECTED, dots: (placeable) => placeable, benchmarkDot: `asset-${BENCHMARK_ID}`},
    ])('a benchmark $benchmark: one dot per placeable row, and the reference once — as $benchmarkDot', ({props, dots, benchmarkDot}) => {
        mountWith(props);
        const placeable = placeableDots();
        // Barrier: the rows place a cloud, the reference's own row among it when it is selected.
        expect(placeable.length, 'premise: the table places at least two dots').toBeGreaterThan(1);
        const mounts = scatterMounts();
        expect(mounts, 'barrier: the section drew one scatter').toHaveLength(1);
        const ids = mounts[0].points.map((point) => point.id);
        const roles = mounts[0].points.map((point) => point.role);

        expect(ids, 'the dots handed to ScatterChart, in their order').toEqual(dots(placeable));
        expect(roles, `${benchmarkDot} is the one benchmark dot, every other dot an asset`).toEqual(ids.map((id) => (id === benchmarkDot ? 'benchmark' : 'asset')));
    });

    it('the reference selected alone draws no scatter: its one dot is a fact, not a comparison', () => {
        mountWith(REFERENCE_ALONE);

        // Barrier: the section drew its table, the reference's one row placeable — the absence is the scatter's alone.
        expect(l3Table()).toHaveAttribute('data-row-count', '1');
        expect(placeableDots(), 'premise: the reference can be placed').toEqual([`asset-${BENCHMARK_ID}`]);
        expect(scatterMounts(), 'a scatter was drawn: the reference counted twice, as its row and as its own point').toHaveLength(0);
        expect(screen.queryByTestId('risk-asset-set-l3-risk-return')).toBeNull();
    });
});
