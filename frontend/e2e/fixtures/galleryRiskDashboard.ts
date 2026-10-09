/**
 * Gallery, the Dashboard's Risk tab — the four blocks of user/dashboard/risk.md, one shot each.
 *
 * The tab measures the gallery database's own portfolio — the admin's, every broker it owns — over the Dashboard's period
 * and currency: live answers, never the frozen report the other Dashboard shots are served (its broker ids are not the
 * database's). This module holds what those shots stand on beyond group 4's (galleryRiskLab.ts): the benchmark, the
 * waits for what no attribute publishes — a figure that counts up, a chart redrawn by a later answer — the record of what
 * each frame holds, and the one question answered over another window than it asked.
 *
 * On the desktop each block's shot gets a screen as tall as the whole block — the simulation shot's rule (coordinator's
 * decision, provisional; gallery.spec.ts, `fitScreenToRiskBlock`) — and a resize can redraw a chart: {@link canvasStill}
 * waits it out on the pixels and on the charts' render counters.
 *
 * ## Read-only
 *
 * The benchmark L3 compares against lives in the browser, under the user's key (`lf_<user>_risk_benchmark_asset`,
 * riskBenchmarkStore.svelte.ts), as do the What if…? tools left open (`lf_<user>_risk.l4.openTools`, L4WhatIf.svelte).
 * Each test writes them into its own browser context before every page load ({@link seedDashboardBenchmark},
 * `forgetWhatIfTools`) and removes what it wrote at its end ({@link forgetDashboardRiskMemory}): nothing reaches the
 * database. Nor does the risk engine write: a risk query — the deepest-fall question below included — only reads.
 *
 * ## What is injected, and why
 *
 * `dashboard/risk-whatif` ({@link injectCrisisReplay}): the page wants the Historical replay box after a crisis was
 * replayed — the crisis in Preset, its period, the total sentence and the table of what each holding contributed. The
 * built-in crises (2007–2009, 2020, 2022) lie years before the gallery's prices, which cover about the last year
 * (populate_mock_data.py, `_seed_market_start_date`): replayed for real, every holding is left out and the box says there
 * was nothing left to replay — no total, no table. No crisis lies inside the seeded year, so no real replay shows one.
 *
 * So the replay the box asks — the crisis chosen in the menu, over the crisis's own dates — is answered with the engine's
 * answer to the same question over another window: the portfolio's deepest fall in the page's period, from its peak to
 * its trough, as the engine itself measures it for the same scope, period and currency (`drawdown_summary`, the fall
 * L1's «The worst fall» card reports). Only the request's replay window changes. The answer is delivered as the engine
 * wrote it — every row, weight, return, amount and the total, the holdings it left out and why — and it still names the
 * window it was computed over (`replay_range`, `analyzed_range`), which nothing on the page reads. What the shot shows
 * that is not real: the crisis's name and dates above figures from another stretch of the gallery's synthetic prices,
 * the one where the portfolio fell the most. The page validates the answer with its generated Zod schemas, as any other.
 */

import type {APIResponse, Route} from '@playwright/test';
import {expect, type Locator, type Page} from './playwright';
import {ANSWER_TIMEOUT, isRecord, ISO_DAY, type Json, jsonOf, RISK_QUERY, type RiskItem, riskItemsOf} from './galleryRiskLab';

/**
 * The benchmark of `dashboard/risk-paid`. The page advises a tracker of a broad world index, and the seed prices this
 * index over the whole period, built from the held equities' own days (populate_mock_data.py,
 * `_populate_benchmark_indices`), so the engine lets it be measured. Nobody holds it, so the table adds it as a row of its
 * own, under the Portfolio's.
 */
export const DASHBOARD_BENCHMARK_NAME = 'MSCI World Index';

/** The crisis of `dashboard/risk-whatif`: the one the theory page asks about — «what would 2008 do to me?». */
export const CRISIS_PRESET_ID = 'global_financial_crisis';

/** The id of the one seeded asset named `displayName`, found by name — never assumed from the populate order. */
export async function assetIdNamed(page: Page, displayName: string): Promise<number> {
    const response = await page.request.get('/api/v1/assets/query');
    expect(response.ok(), `GET /api/v1/assets/query answered HTTP ${response.status()}`).toBe(true);
    const assets = (await response.json()) as Array<{id: number; display_name: string}>;
    const matches = assets.filter((asset) => asset.display_name === displayName);
    if (matches.length !== 1) throw new Error(`Asset "${displayName}" found ${matches.length} times, expected once. Check populate_mock_data.py seeding.`);
    return matches[0].id;
}

// ---------------------------------------------------------------------------
// Read-only: the browser's own memory
// ---------------------------------------------------------------------------

function benchmarkKey(userId: number): string {
    return `lf_${userId}_risk_benchmark_asset`;
}

function openToolsKey(userId: number): string {
    return `lf_${userId}_risk.l4.openTools`;
}

/**
 * Write the benchmark L3 compares against before every page load (`null` forgets it). An init script runs ahead of the app
 * on each navigation, so every combination opens on this choice, whatever the previous one left; the choice is the
 * browser's, never the database's (riskBenchmarkStore.svelte.ts).
 */
export async function seedDashboardBenchmark(page: Page, userId: number, benchmarkId: number | null): Promise<void> {
    await page.addInitScript(
        ({key, value}) => {
            try {
                if (value === null) window.localStorage.removeItem(key);
                else window.localStorage.setItem(key, String(value));
            } catch {
                /* storage disabled: the picker opens on no benchmark, and the assertions say so */
            }
        },
        {key: benchmarkKey(userId), value: benchmarkId},
    );
}

/**
 * Remove, now, what a test wrote into the browser's memory of the Risk tab — the benchmark and the What if…? tools left
 * open — and end on both being gone. Called at the end of a test: the browser context goes with it anyway, so nothing
 * would outlive the test even without this, but whoever writes cleans up.
 */
export async function forgetDashboardRiskMemory(page: Page, userId: number): Promise<void> {
    const left = await page.evaluate(
        (keys) => {
            for (const key of keys) window.localStorage.removeItem(key);
            return keys.filter((key) => window.localStorage.getItem(key) !== null);
        },
        [benchmarkKey(userId), openToolsKey(userId)],
    );
    expect(left, 'the Risk tab memory written by the test is still in the browser').toEqual([]);
}

// ---------------------------------------------------------------------------
// The crisis
// ---------------------------------------------------------------------------

export interface CrisisPreset {
    id: string;
    /** The crisis's own dates, as the catalogue sets them and the box asks them. */
    start: string;
    end: string;
}

/** A historical crisis of the scenario catalogue, with the dates it sets: read from the catalogue the page reads, never copied here. */
export async function historicalReplayPreset(page: Page, scenarioId: string): Promise<CrisisPreset> {
    const response = await page.request.get('/api/v1/risk/scenario-catalog');
    expect(response.ok(), `GET /api/v1/risk/scenario-catalog answered HTTP ${response.status()}`).toBe(true);
    const body: unknown = await response.json();
    const entries = isRecord(body) && Array.isArray(body.items) ? body.items : [];
    const scenario = entries.map((entry) => (isRecord(entry) ? entry.scenario : null)).find((candidate) => isRecord(candidate) && candidate.kind === 'historical_replay' && candidate.id === scenarioId);
    const defaults = isRecord(scenario) && isRecord(scenario.defaults) ? scenario.defaults : null;
    const start = defaults?.start;
    const end = defaults?.end;
    if (typeof start !== 'string' || typeof end !== 'string' || !ISO_DAY.test(start) || !ISO_DAY.test(end)) throw new Error(`the scenario catalogue offers no historical replay "${scenarioId}" with both of its dates`);
    return {id: scenarioId, start, end};
}

/**
 * Choose `scenarioId` in the replay box's crisis menu, as a keyboard does. The menu's options carry no test id (L4Replay
 * gives SimpleSelect no `optionTestId`) and their labels are translated, so the choice goes through the combobox's own
 * contract: ↓ opens it on the option chosen now, each ↓ moves the highlight, the trigger names the highlighted option in
 * `aria-activedescendant` — an id ending in the option's value — and Enter chooses it. The menu fills once the scenario
 * catalogue, asked when What if…? first opens, is in; until then it holds «No preset» alone and ↓ moves nothing, so the
 * loop goes on until the crisis is highlighted, or fails naming it. The choice itself is proved by the replay the box
 * asks next: {@link injectCrisisReplay} answers only the crisis's own dates.
 */
export async function chooseReplayPreset(replay: Locator, scenarioId: string): Promise<void> {
    const trigger = replay.getByTestId('risk-replay-preset-button');
    const wanted = `-option-${encodeURIComponent(scenarioId)}`;
    const highlighted = async (): Promise<boolean> => ((await trigger.getAttribute('aria-activedescendant')) ?? '').endsWith(wanted);
    await expect(trigger).toBeEnabled();
    await expect
        .poll(
            async () => {
                if ((await trigger.getAttribute('aria-expanded')) !== 'true' || !(await highlighted())) await trigger.press('ArrowDown');
                return highlighted();
            },
            {message: `the crisis menu never highlighted "${scenarioId}": the scenario catalogue did not reach the replay box`, timeout: 20_000, intervals: [50]},
        )
        .toBe(true);
    await trigger.press('Enter');
    await expect(trigger, 'the crisis menu stayed open').toHaveAttribute('aria-expanded', 'false');
}

interface ReplayWindow {
    start: string;
    end: string;
}

export interface CrisisReplayInjection {
    /** Crisis replays answered with the engine's answer over the deepest fall. */
    edited: number;
    /** The rows of the last such answer: one per holding replayed. */
    rows: number;
    /** The window the last answer was computed over: the portfolio's deepest fall in the page's period. */
    fall: ReplayWindow | null;
    /** The last answer's total, as a fraction. */
    total: number | null;
    /** Crisis replays that went through unedited, or could not be answered, and why. */
    problems: string[];
}

interface ReplayQuestion {
    body: Json;
    analytic: Json;
    parameters: Json;
}

/** The Dashboard asking a historical replay over exactly the crisis's dates, or null when the route carries another question. */
function crisisReplayQuestion(route: Route, crisis: CrisisPreset): ReplayQuestion | null {
    let body: unknown = null;
    try {
        body = route.request().postDataJSON();
    } catch {
        return null;
    }
    if (!isRecord(body) || !isRecord(body.scope) || body.scope.kind !== 'portfolio' || !Array.isArray(body.analytics) || body.analytics.length !== 1) return null;
    const analytic: unknown = body.analytics[0];
    if (!isRecord(analytic) || analytic.analytic_code !== 'stress' || !isRecord(analytic.parameters)) return null;
    const parameters = analytic.parameters;
    const range = parameters.replay_range;
    if (parameters.method !== 'historical_replay' || !isRecord(range)) return null;
    const end = typeof range.end === 'string' && range.end !== '' ? range.end : range.start;
    return range.start === crisis.start && end === crisis.end ? {body, analytic, parameters} : null;
}

/**
 * The portfolio's deepest fall over the question's own scope, period and currency, from its peak to its trough, as the
 * engine measures it (`drawdown_summary`, historical — the only mode it is offered in), or why there is none to use.
 */
async function deepestFall(page: Page, question: Json): Promise<ReplayWindow | string> {
    const response = await page.request.post('/api/v1/risk/query', {
        data: {
            scope: question.scope,
            date_range: question.date_range,
            target_currency: question.target_currency,
            mode: 'historical',
            analytics: [{instance_id: 'gallery-deepest-fall', analytic_code: 'drawdown_summary', parameters: {}}],
        },
        timeout: ANSWER_TIMEOUT,
    });
    const item = riskItemsOf(await jsonOf(response))?.[0];
    if (!response.ok() || !item || (item.status !== 'ok' && item.status !== 'partial')) return `the deepest-fall question answered HTTP ${response.status()} (${item?.status ?? 'no result'})`;
    const output = isRecord(item.output) ? item.output : {};
    const peak = output.maximum_drawdown_peak_date;
    const trough = output.maximum_drawdown_trough_date;
    if (typeof peak !== 'string' || typeof trough !== 'string' || !ISO_DAY.test(peak) || !ISO_DAY.test(trough) || peak >= trough) {
        return `the portfolio has no fall in the page's period to stand in for the crisis (peak ${String(peak)}, trough ${String(trough)})`;
    }
    return {start: peak, end: trough};
}

/** Why the engine's answer over the fall cannot stand in for the crisis's, or null when it can. */
function fallAnswerProblem(response: APIResponse, item: RiskItem | undefined): string | null {
    if (!response.ok()) return `answered HTTP ${response.status()}`;
    if (!item) return 'answered without a result';
    if (item.status !== 'ok' && item.status !== 'partial') return `came back ${item.status}`;
    const output = item.output;
    if (!isRecord(output) || output.kind !== 'stress' || !Array.isArray(output.impacts) || output.impacts.length === 0) return 'carries no row';
    if (typeof output.portfolio_return !== 'number') return 'carries no total';
    // A common period would be offered with the fall's own dates, under the crisis's name: the shot would show the stand-in.
    const audit = isRecord(item.metadata) ? item.metadata.historical_replay_audit : null;
    if (isRecord(audit) && audit.suggested_range != null) return "offers a common period, whose dates would show under the crisis's";
    return null;
}

/**
 * `dashboard/risk-whatif`: answer the Dashboard's replay of `crisis`, over the crisis's own dates, with the engine's answer
 * to the same question over the portfolio's deepest fall in the page's period. The fall is asked once per question
 * (scope, period, currency — the same on every load of a test); the replay request is sent as the page wrote it with
 * its replay window alone moved, and the answer is delivered unedited. Any other request goes on to the backend. A
 * crisis replay that cannot be answered so is recorded in `problems` and goes to the engine as asked — every holding left
 * out — so the test fails on the record, not on a shot. Install before the replay runs.
 */
export async function injectCrisisReplay(page: Page, crisis: CrisisPreset): Promise<CrisisReplayInjection> {
    const log: CrisisReplayInjection = {edited: 0, rows: 0, fall: null, total: null, problems: []};
    const falls = new Map<string, Promise<ReplayWindow | string>>();
    await page.route(RISK_QUERY, async (route) => {
        const question = crisisReplayQuestion(route, crisis);
        if (question === null) return route.fallback();
        try {
            const key = JSON.stringify([question.body.scope, question.body.date_range, question.body.target_currency]);
            let fall = falls.get(key);
            if (!fall) {
                fall = deepestFall(page, question.body);
                falls.set(key, fall);
            }
            const window = await fall;
            if (typeof window === 'string') {
                log.problems.push(`${window}: the crisis replay went to the engine as asked`);
                return route.fallback();
            }
            const asked: Json = {...question.body, analytics: [{...question.analytic, parameters: {...question.parameters, replay_range: window}}]};
            // The body changes length: the header that described the old one is left for the new one to set.
            const headers = Object.fromEntries(Object.entries(route.request().headers()).filter(([name]) => name.toLowerCase() !== 'content-length'));
            const response = await route.fetch({postData: JSON.stringify(asked), headers, timeout: ANSWER_TIMEOUT});
            const item = riskItemsOf(await jsonOf(response))?.[0];
            const problem = fallAnswerProblem(response, item);
            if (problem !== null || !item || !isRecord(item.output)) {
                log.problems.push(`the replay over the deepest fall (${window.start}…${window.end}) ${problem ?? 'carries no output'}: delivered as the engine answered`);
                return route.fulfill({response});
            }
            log.edited += 1;
            log.rows = Array.isArray(item.output.impacts) ? item.output.impacts.length : 0;
            log.fall = window;
            log.total = typeof item.output.portfolio_return === 'number' ? item.output.portfolio_return : null;
            await route.fulfill({response});
        } catch (error) {
            log.problems.push(`the crisis replay could not be answered over the deepest fall: ${error instanceof Error ? error.message : String(error)}`);
            await route.abort().catch(() => undefined);
        }
    });
    return log;
}

// ---------------------------------------------------------------------------
// What no attribute publishes
// ---------------------------------------------------------------------------

/**
 * Every chart inside `scope` has stopped: two readings in a row agree on its pixels and on its finished render passes
 * (`data-chart-renders`, chartReady.ts). ECharts draws into a canvas and animates every redraw for up to 800 ms
 * (echartsAnimationConfig.ts), on no animation the gallery can pause; and `data-chart-ready` turns true on the first
 * finished drawing and stays true through every later one, so a chart redrawn by a later answer — L3's benchmark diamond
 * comes after the holdings' dots — or by a resize of the screen passes it mid-animation. The shot takes the pixels, so
 * the pixels are read; the counters add that no render pass ended between the two readings. A scope with no chart is
 * still at once.
 */
export async function canvasStill(scope: Locator, what: string): Promise<void> {
    let previous: string | null = null;
    await expect
        .poll(
            async () => {
                const now = await scope.evaluate((root) => {
                    const canvases = Array.from(root.querySelectorAll('canvas'));
                    let hash = 0;
                    for (const canvas of canvases) {
                        const pixels = canvas.width > 0 && canvas.height > 0 ? canvas.toDataURL() : '';
                        for (let index = 0; index < pixels.length; index += 1) hash = (Math.imul(hash, 31) + pixels.charCodeAt(index)) | 0;
                    }
                    const passes = Array.from(root.querySelectorAll('[data-chart-renders]'), (chart) => chart.getAttribute('data-chart-renders') ?? '').join(',');
                    return `${canvases.length}:${hash}:${passes}`;
                });
                const still = now === previous;
                previous = now;
                return still;
            },
            {message: `${what} is still drawing`, timeout: 15_000, intervals: [150, 250]},
        )
        .toBe(true);
}

/** Longer than any count-up: `TweenedValue` runs 900 ms at most (TweenedValue.svelte; RiskMetricCard asks 700). */
const TWEEN_QUIET_MS = 1_000;

/**
 * The text of `scope` has not changed for {@link TWEEN_QUIET_MS}, measured on the page's own clock — the one a count-up
 * runs on. A figure that counts up (`TweenedValue`, svelte/motion: from 0 on its first display, as L2's three cards do on
 * a fresh load) runs on no animation the gallery can pause and publishes no end. A count-up still running changes its
 * figure at least once over its whole length, so text that stood still for longer than that holds no count-up.
 */
export async function textStill(scope: Locator, what: string): Promise<void> {
    await expect
        .poll(
            () =>
                scope.evaluate(
                    (root, quietMs) =>
                        new Promise<boolean>((resolve) => {
                            let text = root.textContent;
                            const started = performance.now();
                            let since = started;
                            const step = (now: number): void => {
                                const current = root.textContent;
                                if (current !== text) {
                                    text = current;
                                    since = now;
                                }
                                if (now - since >= quietMs) resolve(true);
                                else if (now - started >= 3 * quietMs) resolve(false);
                                else requestAnimationFrame(step);
                            };
                            requestAnimationFrame(step);
                        }),
                    TWEEN_QUIET_MS,
                ),
            {message: `${what} is still counting up`, timeout: 20_000},
        )
        .toBe(true);
}

// ---------------------------------------------------------------------------
// What a frame holds
// ---------------------------------------------------------------------------

const FRAME_MARKS = {whole: '✓', partly: '◐', out: '✗', absent: '–'} as const;

/**
 * Where each named part of a shot lies on the screen — whole ✓, partly ◐, out ✗, or not on the page – — as one line for
 * the run's log: the record of what each image holds, per project and language, beyond the parts a test asserts in frame.
 * Each part is one element (a test id), so a part that matches several fails here, loudly.
 */
export async function framedParts(page: Page, parts: Readonly<Record<string, Locator>>): Promise<string> {
    const viewport = page.viewportSize();
    if (!viewport) throw new Error('the page has no viewport');
    const entries: string[] = [];
    for (const [name, part] of Object.entries(parts)) {
        let place: keyof typeof FRAME_MARKS = 'absent';
        if ((await part.count()) > 0) {
            const box = await part.boundingBox();
            if (box === null || box.y + box.height <= 0 || box.y >= viewport.height) place = 'out';
            else if (box.y >= -0.5 && box.y + box.height <= viewport.height + 0.5) place = 'whole';
            else place = 'partly';
        }
        entries.push(`${name} ${FRAME_MARKS[place]}`);
    }
    return entries.join(' · ');
}
