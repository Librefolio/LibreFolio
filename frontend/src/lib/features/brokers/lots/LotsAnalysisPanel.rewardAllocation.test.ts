// @vitest-environment jsdom
/**
 * LotsAnalysisPanel — the «rewards spread across lots» selector (project 79, STK-3 / P-27; Vitest + jsdom).
 *
 * The contract. The header shows `lots-reward-allocation-selector` (a group of two options, `lots-reward-allocation-OWN_LOT`
 * and `lots-reward-allocation-MERGED`) only when the scope has a reward (a `lot_events` row of kind REWARD or
 * REWARD_MERGE, or an `income_events` row of type REWARD), or while MERGED is chosen. The group publishes the choice
 * (`data-state` OWN_LOT | MERGED), each option its own `aria-pressed`. On MERGED, the main and the selection requests
 * carry `reward_allocation: 'MERGED'`; on OWN_LOT the field is absent, so the usual request and its cache key stay as
 * they were. Choosing the option already chosen asks nothing. Switching FIFO/LIFO keeps MERGED; another asset, another
 * broker set, or the panel opened again starts at OWN_LOT (the same broker set in another order is the same scope).
 *
 * The harness. The store is replaced by a double that answers every question from `answerFor(body)` and never holds a
 * cached answer (`peekLotsAnalysis` → null), so every load is a request this test can read. The children that draw
 * (charts, table, modal, banners, dialog, docs link) are no-op components: they have their own specs, and none of them
 * owns the selector. `waitForStableRect` never settles, so the panel never scrolls (jsdom has no layout). Nothing
 * translated is asserted: the selector is read by its test ids and its published state.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';

const mocks = vi.hoisted(() => ({
    noop: () => {},
    fetchLotsAnalysis: vi.fn(),
}));

vi.mock('./lotsAnalysisStore.svelte', () => ({
    fetchLotsAnalysis: mocks.fetchLotsAnalysis,
    peekLotsAnalysis: () => null,
    methodAnalysis: (response: {methods?: Record<string, unknown>}, method: string) => response.methods?.[method] ?? null,
}));
vi.mock('./waitForStableRect', () => ({waitForStableRect: () => new Promise(() => {})}));
vi.mock('./LotGanttChart.svelte', () => ({default: mocks.noop}));
vi.mock('./LotWacPriceChart.svelte', () => ({default: mocks.noop}));
vi.mock('./UnifiedLotsTable.svelte', () => ({default: mocks.noop}));
vi.mock('./LotCustodyModal.svelte', () => ({default: mocks.noop}));
vi.mock('./LotComparisonChart.svelte', () => ({default: mocks.noop}));
vi.mock('./LotDataQualityBanner.svelte', () => ({default: mocks.noop}));
vi.mock('./LotAnalysisFailedNotice.svelte', () => ({default: mocks.noop}));
vi.mock('$lib/features/portfolio-view/BannerFxPairDialog.svelte', () => ({default: mocks.noop}));
vi.mock('$lib/components/ui/DocsLink.svelte', () => ({default: mocks.noop}));

import LotsAnalysisPanel from './LotsAnalysisPanel.svelte';

interface Body {
    asset_id: number;
    requested_analyses: readonly string[];
    matching_methods: readonly string[];
    broker_ids?: number[];
    selected_lot_ids?: number[];
    reward_allocation?: string;
}

type EventRow = {lot_id: number; kind: string; transaction_id: number; date: string; quantity: string};
type IncomeRow = {type: string; date: string; amount: string; lot_ids: number[]};

const ASSET = 6;
const OTHER_ASSET = 7;
const BUY_ROW: EventRow = {lot_id: 1, kind: 'BUY', transaction_id: 1, date: '2024-01-10', quantity: '500'};
const REWARD_ROW: EventRow = {lot_id: 3, kind: 'REWARD', transaction_id: 3, date: '2024-03-01', quantity: '20'};
const MERGE_ROW: EventRow = {lot_id: 1, kind: 'REWARD_MERGE', transaction_id: 3, date: '2024-03-01', quantity: '20'};

/** What the scope holds for the next answers: the event rows and income rows of every method block. */
let scope: {events: EventRow[]; mergedEvents: EventRow[]; income: IncomeRow[]};

function lot(lotId: number) {
    return {lot_id: lotId, opening_date: '2024-01-10', opening_transaction_id: lotId, open_quantity: '500', original_quantity: '500', states: ['OPEN']};
}

function block(body: Body) {
    const main = body.requested_analyses.includes('LOT_SUMMARY');
    const events = body.reward_allocation === 'MERGED' ? scope.mergedEvents : scope.events;
    return main ? {calculation_status: 'COMPLETE', lots: [lot(1)], gantt_segments: [], lot_events: events, income_events: scope.income, data_quality: {issues: []}} : {calculation_status: 'COMPLETE', value_history: [], return_history: []};
}

function answerFor(body: Body) {
    return {
        asset_id: body.asset_id,
        target_currency: 'EUR',
        quote_base_quantity: 1,
        calculation_metadata: {computed_date_from: '2024-01-10', computed_date_to: '2024-03-20', reward_allocation: body.reward_allocation ?? 'OWN_LOT'},
        range: null,
        market_price_history: [],
        broker_wac_history: [],
        cumulative_wac_history: [],
        methods: Object.fromEntries(body.matching_methods.map((method) => [method, block(body)])),
    };
}

function bodies(): Body[] {
    return mocks.fetchLotsAnalysis.mock.calls.map((call) => call[0] as Body);
}

const isMain = (body: Body) => body.requested_analyses.includes('LOT_SUMMARY');

/** The last main question asked: what is on screen once the answers settle (an earlier one is superseded). */
function lastMain(): Body {
    const mains = bodies().filter(isMain);
    expect(mains.length, 'no main question was asked').toBeGreaterThan(0);
    return mains[mains.length - 1];
}
const isSelection = (body: Body) => body.requested_analyses.includes('VALUE_HISTORY');

function props(assetId: number = ASSET, open = true, brokerIds: number[] = [1]) {
    return {open, assetId, brokerIds, brokers: [], currency: 'EUR', onClose: () => {}};
}

const SELECTOR = 'lots-reward-allocation-selector';
const OWN_LOT = 'lots-reward-allocation-OWN_LOT';
const MERGED = 'lots-reward-allocation-MERGED';

/** The selector shows `allocation`: its group publishes it, and only that option is pressed. */
function expectAllocation(allocation: 'OWN_LOT' | 'MERGED') {
    expect(screen.getByTestId(SELECTOR)).toHaveAttribute('data-state', allocation);
    expect(screen.getByTestId(OWN_LOT)).toHaveAttribute('aria-pressed', String(allocation === 'OWN_LOT'));
    expect(screen.getByTestId(MERGED)).toHaveAttribute('aria-pressed', String(allocation === 'MERGED'));
}

/** The panel with the answer applied: its block's method is published on the panel and the loading state is gone. */
async function renderApplied(brokerIds: number[] = [1]) {
    const view = render(LotsAnalysisPanel, {props: props(ASSET, true, brokerIds)});
    await waitFor(() => expect(screen.getByTestId('lots-analysis-panel')).toHaveAttribute('data-matching-method', 'FIFO'));
    await waitFor(() => expect(screen.queryByTestId('lots-analysis-panel-loading')).toBeNull());
    return view;
}

/** Chooses MERGED and waits for the MERGED main answer to be asked. */
async function switchOn() {
    const before = bodies().length;
    await fireEvent.click(screen.getByTestId(MERGED));
    await waitFor(() =>
        expect(
            bodies()
                .slice(before)
                .some((body) => isMain(body) && body.reward_allocation === 'MERGED'),
        ).toBe(true),
    );
    await waitFor(() => expect(screen.getByTestId(SELECTOR)).toHaveAttribute('data-state', 'MERGED'));
}

/** MERGED chosen and settled: both MERGED questions asked and answered, nothing loading. A later slice holds only what follows. */
async function switchOnSettled() {
    const before = bodies().length;
    await switchOn();
    await waitFor(() =>
        expect(
            bodies()
                .slice(before)
                .some((body) => isSelection(body) && body.reward_allocation === 'MERGED'),
        ).toBe(true),
    );
    await waitFor(() => expect(screen.queryByTestId('lots-analysis-panel-loading')).toBeNull());
}

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    scope = {events: [BUY_ROW], mergedEvents: [BUY_ROW, MERGE_ROW], income: []};
    mocks.fetchLotsAnalysis.mockReset();
    mocks.fetchLotsAnalysis.mockImplementation(async (body: Body) => answerFor(body));
});

afterEach(() => {
    cleanup();
});

describe('LotsAnalysisPanel — the «rewards spread across lots» selector (STK-3, P-27)', () => {
    it('is not drawn when the scope has no reward', async () => {
        await renderApplied();
        // Presence barrier: the header is there, with the method selector beside where the reward selector would be
        expect(screen.getByTestId('lots-method-FIFO')).toBeVisible();
        expect(screen.queryByTestId(SELECTOR)).toBeNull();
        expect(
            bodies()
                .filter(isMain)
                .every((body) => !('reward_allocation' in body)),
        ).toBe(true);
    });

    it('is drawn, on OWN_LOT, when a lot opened by a reward is in the scope; the usual request carries no reward_allocation', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        await renderApplied();
        expect(await screen.findByTestId(SELECTOR)).toHaveAttribute('role', 'group');
        expectAllocation('OWN_LOT');
        const [main] = bodies().filter(isMain);
        expect('reward_allocation' in main, 'the OWN_LOT request carries the field: its cache key changed').toBe(false);
    });

    it('is drawn when the only trace of a reward is its income event', async () => {
        scope.income = [{type: 'REWARD', date: '2024-03-01', amount: '10', lot_ids: [1]}];
        await renderApplied();
        await screen.findByTestId(SELECTOR);
        expectAllocation('OWN_LOT');
    });

    it('on MERGED, asks the main and the selection analyses again with reward_allocation MERGED', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        await renderApplied();
        await screen.findByTestId(SELECTOR);
        const before = bodies().length;

        await switchOn();
        expectAllocation('MERGED');
        await waitFor(() =>
            expect(
                bodies()
                    .slice(before)
                    .some((body) => isSelection(body) && body.reward_allocation === 'MERGED'),
            ).toBe(true),
        );
        const main = bodies().slice(before).find(isMain)!;
        expect(main.matching_methods).toEqual(['FIFO', 'LIFO']);
    });

    it('stays drawn while on MERGED, even when the MERGED answer holds no reward row', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        scope.mergedEvents = [BUY_ROW];
        await renderApplied();
        await screen.findByTestId(SELECTOR);
        // The MERGED main answer is held until the panel is seen waiting for it: until then the OWN_LOT rows (with their
        // REWARD) are still on screen and would keep the selector drawn by themselves
        let release!: () => void;
        const held = new Promise<void>((resolve) => {
            release = resolve;
        });
        mocks.fetchLotsAnalysis.mockImplementation(async (body: Body) => {
            if (isMain(body) && body.reward_allocation === 'MERGED') await held;
            return answerFor(body);
        });

        await switchOn();
        await waitFor(() => expect(screen.getByTestId('lots-analysis-panel-loading')).toBeInTheDocument());
        release();
        await waitFor(() => expect(screen.queryByTestId('lots-analysis-panel-loading')).toBeNull());
        // The MERGED answer is on screen, with no reward row: only MERGED being chosen keeps the selector drawn
        expectAllocation('MERGED');
    });

    it('back on OWN_LOT, asks the usual question with no reward_allocation', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        await renderApplied();
        await screen.findByTestId(SELECTOR);
        await switchOn();
        const before = bodies().length;

        await fireEvent.click(screen.getByTestId(OWN_LOT));
        await waitFor(() => expect(bodies().slice(before).some(isMain)).toBe(true));
        expect(
            bodies()
                .slice(before)
                .filter(isMain)
                .every((body) => !('reward_allocation' in body)),
        ).toBe(true);
        expectAllocation('OWN_LOT');
    });

    it('choosing the option already chosen asks nothing (OWN_LOT, then MERGED)', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        await renderApplied();
        await screen.findByTestId(SELECTOR);

        // OWN_LOT on OWN_LOT. Barrier: MERGED is chosen next, so a usual question sent by the no-op click would sit in
        // the slice before the MERGED ones
        let before = bodies().length;
        await fireEvent.click(screen.getByTestId(OWN_LOT));
        expectAllocation('OWN_LOT');
        await switchOnSettled();
        const afterOwnLot = bodies().slice(before);
        expect(
            afterOwnLot.every((body) => body.reward_allocation === 'MERGED'),
            JSON.stringify(afterOwnLot),
        ).toBe(true);

        // MERGED on MERGED. Barrier: OWN_LOT is chosen next, so a MERGED question sent by the no-op click would show up
        before = bodies().length;
        await fireEvent.click(screen.getByTestId(MERGED));
        expectAllocation('MERGED');
        await fireEvent.click(screen.getByTestId(OWN_LOT));
        await waitFor(() =>
            expect(
                bodies()
                    .slice(before)
                    .some((body) => isMain(body) && !('reward_allocation' in body)),
            ).toBe(true),
        );
        const afterMerged = bodies().slice(before);
        expect(
            afterMerged.every((body) => !('reward_allocation' in body)),
            JSON.stringify(afterMerged),
        ).toBe(true);
        expectAllocation('OWN_LOT');
    });

    it('keeps MERGED when the method switches from FIFO to LIFO', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        await renderApplied();
        await screen.findByTestId(SELECTOR);
        await switchOn();
        const before = bodies().length;

        await fireEvent.click(screen.getByTestId('lots-method-LIFO'));
        await waitFor(() => expect(screen.getByTestId('lots-analysis-panel')).toHaveAttribute('data-matching-method', 'LIFO'));
        // The LIFO selection is asked for the method on screen, still MERGED
        await waitFor(() =>
            expect(
                bodies()
                    .slice(before)
                    .some((body) => isSelection(body) && body.matching_methods[0] === 'LIFO'),
            ).toBe(true),
        );
        const asked = bodies().slice(before);
        expect(
            asked.every((body) => body.reward_allocation === 'MERGED'),
            JSON.stringify(asked),
        ).toBe(true);
        expectAllocation('MERGED');
    });

    it('starts at OWN_LOT again on another asset', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        const view = await renderApplied();
        await screen.findByTestId(SELECTOR);
        await switchOn();
        const before = bodies().length;

        await view.rerender(props(OTHER_ASSET));
        // The reset effect is declared before the loads: the new asset is never asked in MERGED, not even once
        await waitFor(() =>
            expect(
                bodies()
                    .slice(before)
                    .some((body) => isMain(body) && body.asset_id === OTHER_ASSET && !('reward_allocation' in body)),
            ).toBe(true),
        );
        expect(lastMain(), 'the last main question is not the usual one').not.toHaveProperty('reward_allocation');
        expect(lastMain().asset_id).toBe(OTHER_ASSET);
        expect(
            bodies()
                .filter((body) => body.asset_id === OTHER_ASSET)
                .every((body) => !('reward_allocation' in body)),
            'a MERGED question went out for the new asset',
        ).toBe(true);
        await waitFor(() => expect(screen.getByTestId(SELECTOR)).toHaveAttribute('data-state', 'OWN_LOT'));
        expectAllocation('OWN_LOT');
    });

    it('starts at OWN_LOT again on another broker set; the first question for it carries no reward_allocation', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        const view = await renderApplied([1]);
        await screen.findByTestId(SELECTOR);
        await switchOnSettled();
        const before = bodies().length;

        await view.rerender(props(ASSET, true, [2]));
        await waitFor(() =>
            expect(
                bodies()
                    .slice(before)
                    .some((body) => isMain(body) && JSON.stringify(body.broker_ids) === '[2]'),
            ).toBe(true),
        );
        // The reset effect is declared before the loads: nothing asked for the new broker set is MERGED, not even once
        const asked = bodies().slice(before);
        expect(asked[0].broker_ids, 'the first question after the change is not for the new broker set').toEqual([2]);
        expect(
            asked.every((body) => !('reward_allocation' in body)),
            `a MERGED question went out for the new broker set: ${JSON.stringify(asked)}`,
        ).toBe(true);
        expect(lastMain(), 'the last main question is not the usual one').not.toHaveProperty('reward_allocation');
        await waitFor(() => expect(screen.getByTestId(SELECTOR)).toHaveAttribute('data-state', 'OWN_LOT'));
        expectAllocation('OWN_LOT');
    });

    it('keeps MERGED when the same broker set comes back in another order: no reset, nothing asked without MERGED', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        const view = await renderApplied([1, 2]);
        await screen.findByTestId(SELECTOR);
        await switchOnSettled();
        const before = bodies().length;

        await view.rerender(props(ASSET, true, [2, 1]));
        // Barrier: a LIFO click asks the LIFO selection; whatever the reorder sent goes out before it
        await fireEvent.click(screen.getByTestId('lots-method-LIFO'));
        await waitFor(() =>
            expect(
                bodies()
                    .slice(before)
                    .some((body) => isSelection(body) && body.matching_methods[0] === 'LIFO'),
            ).toBe(true),
        );
        await waitFor(() => expect(screen.queryByTestId('lots-analysis-panel-loading')).toBeNull());
        const asked = bodies().slice(before);
        expect(
            asked.every((body) => body.reward_allocation === 'MERGED'),
            `the reorder reset the choice: ${JSON.stringify(asked)}`,
        ).toBe(true);
        // Not asserted: that the reorder asks nothing. The load effects track the `brokerIds` array itself, so a new array
        // in another order asks main and selection again (MERGED, as checked above); only the reset normalises the order.
        expectAllocation('MERGED');
    });

    it('is hidden once another broker set answers with no reward (MERGED was reset)', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        const view = await renderApplied([1]);
        await screen.findByTestId(SELECTOR);
        await switchOnSettled();

        // Broker 2 holds no reward, in either allocation. Its main answer is held until the panel is seen waiting for it,
        // so the absence below is read on broker 2's answer, not on a header still showing broker 1's rows
        let release!: () => void;
        const held = new Promise<void>((resolve) => {
            release = resolve;
        });
        mocks.fetchLotsAnalysis.mockImplementation(async (body: Body) => {
            if (!body.broker_ids?.includes(2)) return answerFor(body);
            if (isMain(body)) await held;
            const answer = answerFor(body);
            for (const method of Object.values(answer.methods) as {lot_events?: EventRow[]; income_events?: IncomeRow[]}[]) {
                if (method.lot_events) method.lot_events = [BUY_ROW];
                if (method.income_events) method.income_events = [];
            }
            return answer;
        });
        const before = bodies().length;

        await view.rerender(props(ASSET, true, [2]));
        await waitFor(() => expect(screen.getByTestId('lots-analysis-panel-loading')).toBeInTheDocument());
        release();
        await waitFor(() => expect(screen.queryByTestId('lots-analysis-panel-loading')).toBeNull());
        // Presence barrier: broker 2's answer is applied and the header is there
        expect(
            bodies()
                .slice(before)
                .some((body) => isMain(body) && JSON.stringify(body.broker_ids) === '[2]' && !('reward_allocation' in body)),
        ).toBe(true);
        await waitFor(() => expect(screen.getByTestId('lots-analysis-panel')).toHaveAttribute('data-matching-method', 'FIFO'));
        expect(screen.getByTestId('lots-method-FIFO')).toBeVisible();
        expect(screen.queryByTestId(SELECTOR)).toBeNull();
    });

    it('starts at OWN_LOT again when the panel is opened again', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        const view = await renderApplied();
        await screen.findByTestId(SELECTOR);
        await switchOn();

        await view.rerender(props(ASSET, false));
        await waitFor(() => expect(screen.queryByTestId('lots-analysis-panel')).toBeNull());
        const before = bodies().length;
        await view.rerender(props(ASSET, true));
        await waitFor(() =>
            expect(
                bodies()
                    .slice(before)
                    .some((body) => isMain(body) && !('reward_allocation' in body)),
            ).toBe(true),
        );
        expect(lastMain(), 'the last main question is not the usual one').not.toHaveProperty('reward_allocation');
        await waitFor(() => expect(screen.getByTestId(SELECTOR)).toHaveAttribute('data-state', 'OWN_LOT'));
        expectAllocation('OWN_LOT');
    });
});
