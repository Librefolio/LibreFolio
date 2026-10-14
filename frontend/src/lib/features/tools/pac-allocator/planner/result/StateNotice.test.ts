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
 * Results. Minimal objects cast to `PacReadyResult`: `result_state`, `stop_reason`,
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
import type {PacReadyResult, PacResolvedRequest} from '../types';
import type {ResultNames} from './model';
import StateNotice from './StateNotice.svelte';

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
/** No route with a required minimum: the infeasible notice lists the reachable funding only. */
const request = {order_routes: []} as unknown as PacResolvedRequest;

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

function incumbent(stop_reason: 'completed' | 'time_limit', rounding_top_ups: TopUp[]): PacReadyResult {
    const stages = stop_reason === 'completed' ? [{status: 'finished'}] : [{status: 'finished'}, {status: 'unfinished'}];
    return {result_state: 'ready_incumbent', stop_reason, solver_evidence: {stages}, primary_solution: {rounding_top_ups}} as unknown as PacReadyResult;
}

function noOp(): PacReadyResult {
    return {
        result_state: 'ready_no_op',
        stop_reason: 'completed',
        solver_evidence: {stages: [{status: 'finished'}]},
        primary_solution: {accounting: {selected_funding: money('5.00')}, rounding_top_ups: []},
    } as unknown as PacReadyResult;
}

function noIncumbent(): PacReadyResult {
    return {result_state: 'ready_no_incumbent', stop_reason: 'time_limit', solver_evidence: {stages: [{status: 'unfinished'}]}} as unknown as PacReadyResult;
}

function infeasible(): PacReadyResult {
    return {
        result_state: 'ready_infeasible',
        stop_reason: 'completed',
        solver_evidence: {stages: [{status: 'infeasible'}]},
        proof: {kind: 'infeasibility_proven', proof_source: 'solver_status'},
        scenario_basis: {reachable_funding: money('100.00')},
    } as unknown as PacReadyResult;
}

/** What a row must show for `row`, with privacy as it currently is. */
function amountOf(row: TopUp): string {
    return formatPlannerMoneyPlain(row.amount, row.currency, {digits});
}

async function mount(result: PacReadyResult): Promise<void> {
    render(StateNotice, {result, request, names, digits, ongoto: vi.fn(), onedit: vi.fn()});
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
