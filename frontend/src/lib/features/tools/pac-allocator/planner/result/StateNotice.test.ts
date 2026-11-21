// @vitest-environment jsdom
/**
 * StateNotice — the rounding top-ups a published plan carries (Vitest + jsdom).
 *
 * Subject. Since QX1-b the backend publishes SCIP's plan even when the exact Decimal replay
 * leaves a cash pool (broker × currency) a few minor units short: the result then carries one
 * top-up per such pool in `primary_solution.rounding_top_ups` — "to execute the plan you need
 * this much more on that broker/currency". StateNotice renders them after its state chain, as a
 * block of its own (`pac-planner-top-up`, `role="status"`): one `pac-planner-top-up-row` per
 * top-up, in wire order, naming its pool in `data-broker` / `data-currency`. The amount is wealth,
 * so it goes through the planner's personal formatter and masks with privacy on. A replay
 * rejection no longer reaches the UI as `ready_no_incumbent`, so the "replay rejected" notice
 * keyed on `ready_no_incumbent` + `completed` has no state left to describe.
 *
 * Expectations. The amount a row must show is the planner adapter's own output
 * (`formatPlannerMoneyPlain` with the catalogue digits), computed here with privacy off and
 * checked once against the digits put in; the broker is the stub's name. Nothing here reads
 * translated text: the sentence around those values belongs to the catalogue.
 *
 * Results. Minimal objects cast to `PlannerReadyResult`: `result_state`, `stop_reason`,
 * `solver_evidence.stages`, `primary_solution.rounding_top_ups`, and exactly what the branch
 * each case renders reads (the no-op's selected funding, the infeasible proof source and
 * reachable funding, the request's order routes).
 *
 * Absence. Every "no block" assertion follows a presence barrier: the state notice the same
 * mount renders, so an absent block cannot mean an absent component.
 *
 * Storage. The shared `$app/environment` mock reports `browser: false`, so `setPrivacyEnabled`
 * moves the in-memory rune and never touches `localStorage`.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';
import {t} from 'svelte-i18n';

// The formatter reads the currency catalogue store, which imports the API client. Nothing here
// loads the catalogue: every call resolves to nothing, and each comparison runs the formatter on
// both sides against the same, unloaded store.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
}));

import {cleanup, render, screen, setupI18n, within} from '$test/component';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import {catalogCurrencyDigits, formatPlannerMoneyPlain} from '../format';
import type {PlannerReadyResult} from '../types';
import type {LimitedEntry, ResultNames} from './model';
import StateNotice from './StateNotice.svelte';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {REBALANCER_PLANNER_PROFILE} from '../profile';

const STATES = 'tools.pacAllocator.planner.result.states';

const digits = catalogCurrencyDigits([
    {currency: 'EUR', minor_unit: '0.01'},
    {currency: 'JPY', minor_unit: '1'},
]);

const BROKER_NAMES: Record<string, string> = {'broker-one': 'Broker One probe', 'broker-two': 'Broker Two probe'};
const names: ResultNames = {
    asset: (id) => `Asset ${id}`,
    ticker: () => null,
    broker: (id) => BROKER_NAMES[id] ?? id,
};

interface TopUp {
    broker_id: string;
    currency: string;
    amount: string;
    rounded_postings: number;
    valuation_amount: {value: {kind: 'finite_decimal'; value: string}; currency: string};
}

function topUp(broker_id: string, currency: string, amount: string, valuation: string, rounded_postings = 1): TopUp {
    return {broker_id, currency, amount, rounded_postings, valuation_amount: {value: {kind: 'finite_decimal', value: valuation}, currency: 'EUR'}};
}

const ONE_CENT = topUp('broker-one', 'EUR', '0.01', '0.01');
/** Listed first on the wire although its broker sorts second: the rows must keep the wire order. */
const ONE_YEN = topUp('broker-two', 'JPY', '1', '0.006');

function money(value: string) {
    return {value: {kind: 'finite_decimal', value}, currency: 'EUR'};
}

function incumbent(stop_reason: 'completed' | 'time_limit', rounding_top_ups: TopUp[]): PlannerReadyResult {
    const stages = stop_reason === 'completed' ? [{status: 'finished'}] : [{status: 'finished'}, {status: 'unfinished'}];
    return {result_state: 'ready_incumbent', stop_reason, solver_evidence: {stages}, primary_solution: {rounding_top_ups}} as unknown as PlannerReadyResult;
}

function noOp(): PlannerReadyResult {
    return {
        result_state: 'ready_no_op',
        stop_reason: 'completed',
        solver_evidence: {stages: [{status: 'finished'}]},
        primary_solution: {accounting: {selected_funding: money('5.00')}, rounding_top_ups: []},
    } as unknown as PlannerReadyResult;
}

function noIncumbent(stop_reason: 'time_limit' | 'completed' = 'time_limit'): PlannerReadyResult {
    const status = stop_reason === 'completed' ? 'finished' : 'unfinished';
    return {result_state: 'ready_no_incumbent', stop_reason, solver_evidence: {stages: [{status}]}} as unknown as PlannerReadyResult;
}

function infeasible(): PlannerReadyResult {
    return {
        result_state: 'ready_infeasible',
        stop_reason: 'completed',
        solver_evidence: {stages: [{status: 'infeasible'}]},
        proof: {kind: 'infeasibility_proven', proof_source: 'solver_status'},
        scenario_basis: {reachable_funding: money('100.00')},
    } as unknown as PlannerReadyResult;
}

/** What a row must show for `row`, with privacy as it currently is. */
function amountOf(row: TopUp): string {
    return formatPlannerMoneyPlain(row.amount, row.currency, {digits});
}

async function mount(result: PlannerReadyResult, limits: LimitedEntry[] = [], ongoto = vi.fn()): Promise<void> {
    render(StateNotice, {result, names, digits, limits, ongoto, onedit: vi.fn()});
    flushSync();
    await tick();
}

async function setPrivacy(value: boolean): Promise<void> {
    setPrivacyEnabled(value);
    flushSync();
    await tick();
}

function topUpRows(): HTMLElement[] {
    return within(screen.getByTestId('pac-planner-top-up')).getAllByTestId('pac-planner-top-up-row');
}

function stateNotice(state: string): HTMLElement {
    const notice = screen.getByTestId('pac-planner-state');
    expect(notice, `barrier: the ${state} notice is rendered`).toHaveAttribute('data-state', state);
    return notice;
}

beforeAll(async () => {
    await setupI18n();
    setPrivacyEnabled(false);
    // The expectation is the formatter's own output: check once that it carries the digits put in,
    // or "the row shows the amount" would compare like with like.
    expect(amountOf(ONE_CENT).replace(/\D/g, '')).toBe('001');
    expect(amountOf(ONE_YEN).replace(/\D/g, '')).toBe('1');
});

afterEach(() => {
    // Module-level flag: a leftover `true` would mount the next notice masked.
    setPrivacyEnabled(false);
    cleanup();
});

describe('StateNotice rounding top-ups', () => {
    it('a completed plan with one top-up names its pool and the amount to add, as a status', async () => {
        await mount(incumbent('completed', [ONE_CENT]));

        const block = screen.getByTestId('pac-planner-top-up');
        expect(block).toHaveAttribute('role', 'status');
        const [row, ...others] = topUpRows();
        expect(others, 'one top-up, one row').toHaveLength(0);
        expect(row).toHaveAttribute('data-broker', 'broker-one');
        expect(row).toHaveAttribute('data-currency', 'EUR');
        expect(row.textContent).toContain(amountOf(ONE_CENT));
        expect(row.textContent).toContain(BROKER_NAMES['broker-one']);
    });

    it('two top-ups are two rows, in wire order, each with its own currency digits', async () => {
        await mount(incumbent('completed', [ONE_YEN, ONE_CENT]));

        const rows = topUpRows();
        expect(rows.map((row) => [row.dataset.broker, row.dataset.currency])).toEqual([
            ['broker-two', 'JPY'],
            ['broker-one', 'EUR'],
        ]);
        expect(rows[0].textContent).toContain(amountOf(ONE_YEN));
        expect(rows[0].textContent).toContain(BROKER_NAMES['broker-two']);
        expect(rows[1].textContent).toContain(amountOf(ONE_CENT));
        expect(rows[1].textContent).toContain(BROKER_NAMES['broker-one']);
    });

    it('an empty top-up list renders no block, whatever notice the state shows', async () => {
        await mount(noOp());
        stateNotice('no_op');
        expect(screen.queryByTestId('pac-planner-top-up')).toBeNull();
        cleanup();

        await mount(incumbent('time_limit', []));
        stateNotice('limit');
        expect(screen.queryByTestId('pac-planner-top-up')).toBeNull();
    });

    it('with privacy on the pool stays named and the amount is masked', async () => {
        const clear = amountOf(ONE_CENT);
        await setPrivacy(true);
        expect(isPrivacyEnabled(), 'control: the flag').toBe(true);
        const masked = amountOf(ONE_CENT);
        expect(masked, 'control: a fresh personal call through the same formatter masks').toContain(PRIVACY_PLACEHOLDER);
        expect(masked, 'control: and drops the clear amount').not.toBe(clear);

        await mount(incumbent('completed', [ONE_CENT]));

        const [row] = topUpRows();
        expect(row).toHaveAttribute('data-broker', 'broker-one');
        expect(row.textContent).toContain(BROKER_NAMES['broker-one']);
        expect(row.textContent).not.toContain(clear);
        expect(row.textContent).toContain(masked);
    });

    it('a limit stop shows both its notice and the top-up of the plan it published', async () => {
        await mount(incumbent('time_limit', [ONE_CENT]));

        expect(stateNotice('limit')).toHaveAttribute('data-stop', 'time_limit');
        const [row] = topUpRows();
        expect(row).toHaveAttribute('data-broker', 'broker-one');
    });

    it('lot ZB: a completed search with no plan says the search ended, not that a limit stopped it', async () => {
        // The surface is frozen (plannerSurface.gate): no new test id. The rendered sentence is checked against the
        // catalogue's own value of each key, so nothing here depends on its wording.
        const ended = get(t)(`${STATES}.noIncumbent.completedBody`);
        const limited = get(t)(`${STATES}.noIncumbent.body`);
        const tips = get(t)(`${STATES}.noIncumbent.tips`);

        await mount(noIncumbent('time_limit'));
        let notice = stateNotice('no_incumbent');
        expect(notice.textContent).toContain(limited);
        expect(notice.textContent).toContain(tips);
        expect(notice.textContent).not.toContain(ended);
        cleanup();

        await mount(noIncumbent('completed'));
        notice = stateNotice('no_incumbent');
        expect(notice).toHaveAttribute('data-stop', 'completed');
        expect(notice.textContent).toContain(ended);
        expect(notice.textContent).not.toContain(limited);
        expect(notice.textContent).not.toContain(tips);
    });

    it('a result without a plan renders no top-up block and does not crash', async () => {
        await mount(noIncumbent());
        expect(stateNotice('no_incumbent')).toHaveAttribute('data-stop', 'time_limit');
        expect(screen.queryByTestId('pac-planner-top-up')).toBeNull();
        cleanup();

        await mount(infeasible());
        stateNotice('infeasible');
        expect(screen.queryByTestId('pac-planner-top-up')).toBeNull();
    });
});

describe('StateNotice infeasible state (M19, §10.2)', () => {
    it('lists the reachable liquidity only: no route is named as a hard minimum any more', async () => {
        await mount(infeasible());

        stateNotice('infeasible');
        const constraints = within(screen.getByTestId('pac-planner-state-constraints')).getAllByTestId('pac-planner-state-constraint');
        expect(constraints.map((row) => row.getAttribute('data-kind'))).toEqual(['reachable_funding']);
    });
});

/*
 * F2 of project 67 (M20, U6): without limits «do nothing» is always a plan, so `ready_infeasible` with a limit in the
 * request means the limits rule every plan out. The notice then lists every entry with a limit, read from the resolved
 * request, each with its own «Go to» the Targets step. Without limits the generic message of today stays; a search that
 * ran out of time (`ready_no_incumbent`) is not a proof, and never shows this banner.
 */
const LIMIT_MAX: LimitedEntry = {kind: 'asset', id: 'msft', brokerId: null, currency: null, minimum: null, maximum: {kind: 'amount', amount: {amount: '1000', currency: 'EUR'}}};
const LIMIT_MIN: LimitedEntry = {kind: 'asset', id: 'bond', brokerId: null, currency: null, minimum: {kind: 'share', share: '0.35'}, maximum: null};

function limitRows(): HTMLElement[] {
    return within(screen.getByTestId('pac-planner-state-limits')).getAllByTestId('pac-planner-state-limit');
}

describe('StateNotice limits banner (F2, M20)', () => {
    it('infeasible with limits lists every limited entry and links to Targets', async () => {
        const ongoto = vi.fn();
        await mount(infeasible(), [LIMIT_MAX, LIMIT_MIN], ongoto);

        expect(stateNotice('infeasible')).toHaveAttribute('data-limits', 'true');
        const rows = limitRows();
        expect(rows.map((row) => [row.getAttribute('data-kind'), row.getAttribute('data-entity')])).toEqual([
            ['asset', 'msft'],
            ['asset', 'bond'],
        ]);
        expect(rows[0]).toHaveTextContent(formatPlannerMoneyPlain('1000', 'EUR', {digits}));
        expect(rows[0].querySelector('[data-side="maximum"]')).not.toBeNull();
        expect(rows[1].querySelector('[data-side="minimum"]')).not.toBeNull();
        // The generic list of today is not shown beside the banner.
        expect(screen.queryByTestId('pac-planner-state-constraints')).toBeNull();

        within(rows[1]).getByTestId('pac-planner-state-limit-goto').click();
        expect(ongoto).toHaveBeenCalledWith('targets');
    });

    it('masks an amount limit with privacy on, and keeps a share visible', async () => {
        await mount(infeasible(), [LIMIT_MAX, LIMIT_MIN]);
        await setPrivacy(true);

        const [amountRow, shareRow] = limitRows();
        expect(amountRow).toHaveTextContent(PRIVACY_PLACEHOLDER);
        expect(amountRow).not.toHaveTextContent('1,000');
        expect(shareRow).not.toHaveTextContent(PRIVACY_PLACEHOLDER);
        expect(isPrivacyEnabled()).toBe(true);
    });

    it('infeasible without limits shows the generic message', async () => {
        await mount(infeasible(), []);

        expect(stateNotice('infeasible')).toHaveAttribute('data-limits', 'false');
        expect(screen.queryByTestId('pac-planner-state-limits')).toBeNull();
        expect(screen.getByTestId('pac-planner-state-constraints')).toBeInTheDocument();
    });

    it('no incumbent never shows the limits banner', async () => {
        await mount(noIncumbent(), [LIMIT_MAX]);

        stateNotice('no_incumbent');
        expect(screen.queryByTestId('pac-planner-state-limits')).toBeNull();
    });
});

/**
 * F4a of project 67, step 7: the «limited» notice says why the search stopped, from the published stages and notes.
 *
 * - **The Rebalancer, its objective closed, a tie-break stopped** (the engine's G5 answer has this shape): the score is
 *   proven, only an equally good plan may differ; the notice says so (`data-scope="tie_break"`) and counts no stage.
 * - **The Rebalancer, its objective stopped:** the search notice, counting its objectives only (the tie-breaks apart).
 * - **A numerical error** (`allocation.solver_numerical_error`, lot SE): named as the cause (`data-cause`), in both Tools.
 * - **The PAC** counts every stage, as before.
 */
function limitedResult(stages: {objective_code: string; status: string}[], issues: {code: string}[] = [], proof: object = {kind: 'optimal_proven'}): PlannerReadyResult {
    return {result_state: 'ready_incumbent', stop_reason: 'time_limit', issues, proof, solver_evidence: {stages}, primary_solution: {rounding_top_ups: []}} as unknown as PlannerReadyResult;
}

async function mountRebalancer(result: PlannerReadyResult): Promise<void> {
    render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: StateNotice, childProps: {result, names, digits, limits: [], ongoto: vi.fn(), onedit: vi.fn()}}});
    flushSync();
    await tick();
}

const SCORE_CLOSED = [
    {objective_code: 'plan_score', status: 'finished'},
    {objective_code: 'operation_count', status: 'unfinished'},
    {objective_code: 'route_priority', status: 'unfinished'},
];
const DISTANCE_STOPPED = [
    {objective_code: 'target_distance', status: 'finished'},
    {objective_code: 'wealth_loss', status: 'unfinished'},
    {objective_code: 'operation_count', status: 'unfinished'},
    {objective_code: 'route_priority', status: 'unfinished'},
];
const counts = (notice: HTMLElement) => {
    const line = notice.querySelector('[data-finished]');
    return line ? [line.getAttribute('data-finished'), line.getAttribute('data-unfinished')] : null;
};

describe('the «limited» notice says why the search stopped (F4a step 7)', () => {
    it('Rebalancer: the score closed and a tie-break stopped', async () => {
        await mountRebalancer(limitedResult(SCORE_CLOSED));
        const notice = screen.getByTestId('rebalancer-planner-state');
        expect(notice).toHaveAttribute('data-state', 'limit');
        expect(notice).toHaveAttribute('data-scope', 'tie_break');
        expect(counts(notice)).toBeNull();
    });

    it('Rebalancer: the score closed but its proof not confirmed (lot SEEDS): never «proven»', async () => {
        await mountRebalancer(limitedResult(SCORE_CLOSED, [], {kind: 'not_proven', reason_code: 'allocation.proof_not_confirmed'}));
        const notice = screen.getByTestId('rebalancer-planner-state');
        expect(notice).toHaveAttribute('data-scope', 'search');
        expect(counts(notice)).toEqual(['1', '0']);
    });

    it('Rebalancer: an objective stopped: the search, counting the objectives only', async () => {
        await mountRebalancer(limitedResult(DISTANCE_STOPPED));
        const notice = screen.getByTestId('rebalancer-planner-state');
        expect(notice).toHaveAttribute('data-scope', 'search');
        expect(counts(notice)).toEqual(['1', '1']);
    });

    it('a numerical error is named as the cause, in both Tools', async () => {
        const error = [{code: 'allocation.solver_numerical_error'}];
        await mountRebalancer(limitedResult(SCORE_CLOSED, error));
        expect(screen.getByTestId('rebalancer-planner-state')).toHaveAttribute('data-cause', 'solver_error');
        cleanup();
        await mount(limitedResult(SCORE_CLOSED, error));
        expect(screen.getByTestId('pac-planner-state')).toHaveAttribute('data-cause', 'solver_error');
    });

    it('the PAC counts every stage, and the clock is the cause', async () => {
        await mount(limitedResult(SCORE_CLOSED));
        const notice = screen.getByTestId('pac-planner-state');
        expect(notice).toHaveAttribute('data-scope', 'search');
        expect(notice).toHaveAttribute('data-cause', 'time_limit');
        expect(counts(notice)).toEqual(['1', '2']);
    });
});
