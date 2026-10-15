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
import {ANSWER_TIMEOUT, isRecord, ISO_DAY, type Json, jsonOf, parkPointer, RISK_QUERY, type RiskItem, riskItemsOf} from './galleryRiskLab';

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

/** The time the crisis menu has to offer the crisis, and then again to highlight it: the old single wait's budget, each. */
const CRISIS_MENU_TIMEOUT = 20_000;

/** How many lines of the crisis menu's record a failure quotes: the last ones, where it went wrong. */
const CRISIS_MENU_QUOTED = 6;

/**
 * The crisis menu at one instant, read in one pass so its parts agree. Every option is named by the value its id ends in
 * (`<listbox>-option-<encodeURIComponent(value)>`, SimpleSelect.svelte, `getOptionId`): `__empty__` is «No preset».
 */
interface CrisisMenuState {
    /** The trigger says the menu is open (`aria-expanded`). */
    open: boolean;
    /** The open menu's options, in order; none while it is closed — SimpleSelect renders them only open. */
    options: string[];
    /** Those of them that are disabled: no key lands on one (optionFilter.ts, `stepSelectable`). */
    disabled: string[];
    /** The option the trigger names in `aria-activedescendant`, '' when it names none. */
    highlighted: string;
    /** The option the pointer is over, by the browser's own hover state — the one `mouseenter` follows — '' when none of the menu's. */
    hovered: string;
    /** What the pointer is over: the nearest test id, else the tag, else `nothing`. */
    pointer: string;
}

/** One line of the record: a step, what the menu showed after it, and how many times in a row that step showed it. */
interface CrisisMenuLine {
    step: 'read' | 'ArrowDown' | 'ArrowUp';
    shown: string;
    times: number;
}

/** What was read off the crisis menu while a crisis was chosen: what a failure names, instead of a cause guessed. */
interface CrisisMenuRecord {
    /** The crisis, by the value its option's id ends in. */
    wanted: string;
    lines: CrisisMenuLine[];
    last: CrisisMenuState | null;
}

/**
 * Read the crisis menu through the combobox's own contract — the trigger's `aria-expanded`, `aria-controls` (its listbox's
 * id) and `aria-activedescendant`, and the ids SimpleSelect gives the options of that listbox — never through a label. The
 * pointer is read off the browser's hover state, which is what moves the highlight, rather than off a position assumed.
 */
async function readCrisisMenu(trigger: Locator): Promise<CrisisMenuState> {
    return trigger.evaluate((element): CrisisMenuState => {
        const listboxId = element.getAttribute('aria-controls') ?? '';
        const prefix = `${listboxId}-option-`;
        const valueOf = (id: string): string => (id.startsWith(prefix) ? id.slice(prefix.length) : id);
        const listbox = listboxId === '' ? null : document.getElementById(listboxId);
        const options = listbox === null ? [] : Array.from(listbox.querySelectorAll('[role="option"]'));
        const hovers = document.querySelectorAll(':hover');
        const under = hovers.length > 0 ? hovers[hovers.length - 1] : null;
        const hoveredOption = under?.closest('[role="option"]') ?? null;
        return {
            open: element.getAttribute('aria-expanded') === 'true',
            options: options.map((option) => valueOf(option.id)),
            disabled: options.filter((option) => option.hasAttribute('disabled') || option.getAttribute('aria-disabled') === 'true').map((option) => valueOf(option.id)),
            highlighted: valueOf(element.getAttribute('aria-activedescendant') ?? ''),
            hovered: hoveredOption !== null && options.includes(hoveredOption) ? valueOf(hoveredOption.id) : '',
            pointer: under === null ? 'nothing' : (under.closest('[data-testid]')?.getAttribute('data-testid') ?? under.tagName.toLowerCase()),
        };
    });
}

/** Where `value` sits among the open menu's options, as `i/n`, or null when the menu does not hold it. */
function placeInCrisisMenu(state: CrisisMenuState, value: string): string | null {
    const index = value === '' ? -1 : state.options.indexOf(value);
    return index < 0 ? null : `${index + 1}/${state.options.length}`;
}

/** A state as a line of the record: open or closed, the highlighted option, the crisis and what the pointer is over. */
function describeCrisisMenu(state: CrisisMenuState, wanted: string): string {
    const pointer = state.hovered === '' ? state.pointer : `option ${placeInCrisisMenu(state, state.hovered)} ${state.hovered}`;
    if (!state.open) return `closed · pointer on ${pointer}`;
    const highlighted = state.highlighted === '' ? 'none' : `${placeInCrisisMenu(state, state.highlighted) ?? 'outside the menu:'} ${state.highlighted}`;
    const crisis = `${placeInCrisisMenu(state, wanted) ?? 'absent'}${state.disabled.includes(wanted) ? ' (disabled)' : ''}`;
    return `open · highlight ${highlighted} · crisis ${crisis} · pointer on ${pointer}`;
}

/**
 * Write into the record what the menu showed after `step`. A read that shows what the last line shows adds nothing, and a
 * key that shows what the same key showed last counts on that line: a highlight no key moves reads `ArrowDown ×212 → …`.
 */
function recordCrisisMenu(record: CrisisMenuRecord, step: CrisisMenuLine['step'], state: CrisisMenuState): void {
    record.last = state;
    const shown = describeCrisisMenu(state, record.wanted);
    const line = record.lines.at(-1);
    if (line?.shown === shown && step === 'read') return;
    if (line?.shown === shown && line.step === step) {
        line.times += 1;
        return;
    }
    record.lines.push({step, shown, times: 1});
}

/** The crisis is the highlighted option of the open menu: Enter chooses it. */
function crisisHighlighted(state: CrisisMenuState, wanted: string): boolean {
    return state.open && state.highlighted === wanted && state.options.includes(wanted);
}

/**
 * The key that moves the highlight one option nearer the crisis, whichever side of it the highlight is on — ↓ also opens a
 * closed menu, on the option chosen now — or null when no key would: the crisis is highlighted, or not in the menu.
 */
function keyTowardCrisis(state: CrisisMenuState, wanted: string): 'ArrowDown' | 'ArrowUp' | null {
    if (!state.open) return 'ArrowDown';
    const target = state.options.indexOf(wanted);
    const from = state.highlighted === '' ? -1 : state.options.indexOf(state.highlighted);
    if (target < 0 || from === target) return null;
    return from < target ? 'ArrowDown' : 'ArrowUp';
}

/** What the last state read says went wrong, in one sentence. Only the wait for the crisis to be offered blames the catalogue. */
function crisisMenuVerdict(record: CrisisMenuRecord, phase: 'offered' | 'highlighted'): string {
    const state = record.last;
    if (state === null) return 'the menu was never read';
    if (!state.open) return 'the menu is closed';
    const crisis = placeInCrisisMenu(state, record.wanted);
    if (crisis === null) {
        return phase === 'offered' ? `the open menu holds ${state.options.length} option(s), none of them the crisis: the scenario catalogue did not reach the replay box` : `the crisis left the open menu, which holds ${state.options.length} option(s)`;
    }
    if (state.disabled.includes(record.wanted)) return `the crisis is option ${crisis}, disabled: no key lands on it`;
    const highlighted = placeInCrisisMenu(state, state.highlighted);
    if (highlighted === null) return `no option is highlighted; the crisis is option ${crisis}`;
    const where = `option ${highlighted} ${state.highlighted}${state.hovered === state.highlighted ? ', under the pointer' : ''}`;
    const line = record.lines.at(-1);
    if (line !== undefined && line.step !== 'read' && line.times > 1) return `the highlight is stuck on ${where} (${line.step} ×${line.times} moved nothing); the crisis is option ${crisis}`;
    return `the highlight is on ${where}; the crisis is option ${crisis}`;
}

/** The failure of a choice: what the menu never did, why by its last state, its options, and the last lines of the record. */
function crisisMenuFailure(record: CrisisMenuRecord, scenarioId: string, phase: 'offered' | 'highlighted', cause?: unknown): Error {
    const lines = record.lines.slice(-CRISIS_MENU_QUOTED).map((line) => `    ${line.step}${line.times > 1 ? ` ×${line.times}` : ''} → ${line.shown}`);
    if (record.lines.length > CRISIS_MENU_QUOTED) lines.unshift(`    … ${record.lines.length - CRISIS_MENU_QUOTED} earlier line(s)`);
    const last = record.last;
    const options = last?.open ? `\n  the open menu's options, by the value their ids end in: ${last.options.join(' · ') || 'none'}` : '';
    const message = `the crisis menu never ${phase} "${scenarioId}": ${crisisMenuVerdict(record, phase)}${options}\n  what it showed, oldest first (step → state):\n${lines.join('\n')}`;
    return cause === undefined ? new Error(message) : new Error(message, {cause});
}

/**
 * Choose `scenarioId` in the replay box's crisis menu, as a keyboard does. The menu's options carry no test id (L4Replay
 * gives SimpleSelect no `optionTestId`) and their labels are translated, so the choice never goes through a label but
 * through the combobox's own contract: the trigger names its listbox in `aria-controls` and the highlighted option in
 * `aria-activedescendant`; each option's id is `<listbox>-option-<encodeURIComponent(value)>`; ↓ opens the menu on the
 * option chosen now; ↓ and ↑ move the highlight one option at a time, stopping at either end — never wrapping round
 * (optionFilter.ts, `stepSelectable`); Enter chooses the highlighted option.
 *
 * The menu fills once the scenario catalogue, asked when What if…? first opens, is in; until then it holds «No preset»
 * alone. So the crisis is first awaited among the open menu's options — the one wait about the catalogue, and the only
 * failure that blames it — and only then walked to.
 *
 * The keys are not all that moves the highlight, and the walk is built for the two other writers:
 * - the pointer (H1). Each option takes the highlight on `mouseenter`, and Chromium sends the boundary events of a pointer
 *   that does not move when content appears under it. The menu is `position: fixed` and opens above the trigger when less
 *   than 200 px are left below it (`dropdownPosition="auto"`): over the head of the box and the Add: row, around where the
 *   click that added the box left the pointer. An option hovered below the crisis took the highlight where ↓ alone could
 *   never bring it back: the likeliest reading of the 20 s reds of 14/10/2026, desktop only (where the menu opens is the
 *   layout's call), two runs in three. So the pointer is parked first ({@link parkPointer}), where the menu never
 *   reaches, and the walk goes both ways.
 * - the menu itself (H2). SimpleSelect puts the highlight back on the chosen option whenever its options, its value or its
 *   open state change, and its options are derived (the catalogue, the language): a change mid-walk sends the highlight
 *   back to «No preset».
 * So each step reads where the highlight and the crisis are, presses ↓ or ↑ toward the crisis and reads again, until the
 * trigger names the crisis, wherever the highlight was moved in between. Every state read is recorded, and a failure
 * names the last ones — open or closed, the highlighted option as i/n, the crisis, the option under the pointer — rather
 * than a cause guessed. After Enter the menu is closed. The choice itself is proved by the caller: the period the crisis
 * sets, then the replay the box asks, which {@link injectCrisisReplay} answers only over the crisis's own dates.
 */
export async function chooseReplayPreset(replay: Locator, scenarioId: string): Promise<void> {
    const trigger = replay.getByTestId('risk-replay-preset-button');
    const record: CrisisMenuRecord = {wanted: encodeURIComponent(scenarioId), lines: [], last: null};
    const look = async (step: CrisisMenuLine['step']): Promise<CrisisMenuState> => {
        const state = await readCrisisMenu(trigger);
        recordCrisisMenu(record, step, state);
        return state;
    };
    const press = async (key: 'ArrowDown' | 'ArrowUp'): Promise<CrisisMenuState> => {
        await trigger.press(key);
        return look(key);
    };
    await expect(trigger).toBeEnabled();
    // H1: parked before the menu opens, the pointer never lies under it, so no option takes the highlight by being hovered.
    await parkPointer(replay.page());

    // The crisis among the open menu's options: the scenario catalogue has reached the box. ↓ opens a closed menu and
    // moves nothing else; an open one is only read, until the catalogue fills it.
    const notOffered = await expect
        .poll(
            async () => {
                const state = await look('read');
                return (state.open ? state : await press('ArrowDown')).options.includes(record.wanted);
            },
            {message: `the crisis menu offers "${scenarioId}"`, timeout: CRISIS_MENU_TIMEOUT, intervals: [50]},
        )
        .toBe(true)
        .then(
            () => null,
            (error: unknown) => error,
        );
    if (notOffered !== null) throw crisisMenuFailure(record, scenarioId, 'offered', notOffered);
    if (record.last?.disabled.includes(record.wanted)) throw crisisMenuFailure(record, scenarioId, 'highlighted');

    // The walk: one key toward the crisis, from wherever the highlight stands, then read again — until the trigger names it.
    const notHighlighted = await expect
        .poll(
            async () => {
                const state = await look('read');
                const key = keyTowardCrisis(state, record.wanted);
                return crisisHighlighted(key === null ? state : await press(key), record.wanted);
            },
            {message: `the crisis menu highlights "${scenarioId}"`, timeout: CRISIS_MENU_TIMEOUT, intervals: [50]},
        )
        .toBe(true)
        .then(
            () => null,
            (error: unknown) => error,
        );
    if (notHighlighted !== null) throw crisisMenuFailure(record, scenarioId, 'highlighted', notHighlighted);

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
