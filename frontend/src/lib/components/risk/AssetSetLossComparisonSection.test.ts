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
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import {get} from 'svelte/store';
import type {z} from 'zod';

import {render, screen, setupI18n, within} from '$test/component';
import type {schemas} from '$lib/api';
import {_, SUPPORTED_LOCALES} from '$lib/i18n';
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

// Invented tails. 752 daily observations; compounding to 21 days consumes 20 of them, hence 732.
const DAILY_VAR = ok('invented-daily-var', 'asset_set_var', {
    kind: 'var_cvar_set',
    confidence_level: 0.95,
    horizon_days: 1,
    observations: 752,
    items: [
        {asset_id: OPEN_ASSET, value_at_risk: 0.031, conditional_value_at_risk: 0.046},
        {asset_id: RECOVERED_ASSET, value_at_risk: 0.012, conditional_value_at_risk: 0.019},
    ],
});
const MONTHLY_VAR = ok('invented-monthly-var', 'asset_set_var', {
    kind: 'var_cvar_set',
    confidence_level: 0.95,
    horizon_days: 21,
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
    render(AssetSetLossComparisonSection, {props: {assetIds: SELECTION, assetLabels: LABELS, dailyVar: DAILY_VAR, monthlyVar: MONTHLY_VAR, drawdown: DRAWDOWN, loading: false}});
}

function normalize(text: string | null): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

function rowOf(assetId: number): HTMLElement {
    const rows = screen.getAllByTestId('risk-asset-set-l1-row').filter((row) => row.dataset.assetId === String(assetId));
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
