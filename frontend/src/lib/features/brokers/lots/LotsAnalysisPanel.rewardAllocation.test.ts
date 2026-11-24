// @vitest-environment jsdom
/**
 * LotsAnalysisPanel — the «spread rewards across lots» switch (project 79, STK-3; Vitest + jsdom).
 *
 * The contract. The header shows `lots-reward-allocation-toggle` only when the scope has a reward (a `lot_events` row of
 * kind REWARD or REWARD_MERGE, or an `income_events` row of type REWARD), or while the switch is on. It publishes its
 * state (`aria-pressed`, `data-state` OWN_LOT | MERGED). On, the main and the selection requests carry
 * `reward_allocation: 'MERGED'`; off, the field is absent, so the usual request and its cache key stay as they were.
 * Switching FIFO/LIFO while it is on keeps MERGED; another asset, or the panel opened again, starts at OWN_LOT.
 *
 * The harness. The store is replaced by a double that answers every question from `answerFor(body)` and never holds a
 * cached answer (`peekLotsAnalysis` → null), so every load is a request this test can read. The children that draw
 * (charts, table, modal, banners, dialog, docs link) are no-op components: they have their own specs, and none of them
 * owns the switch. `waitForStableRect` never settles, so the panel never scrolls (jsdom has no layout). Nothing
 * translated is asserted: the switch is read by its test id and its published state.
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

function props(assetId: number = ASSET, open = true) {
    return {open, assetId, brokerIds: [1], brokers: [], currency: 'EUR', onClose: () => {}};
}

/** The panel with the answer applied: its block's method is published on the panel and the loading state is gone. */
async function renderApplied() {
    const view = render(LotsAnalysisPanel, {props: props()});
    await waitFor(() => expect(screen.getByTestId('lots-analysis-panel')).toHaveAttribute('data-matching-method', 'FIFO'));
    await waitFor(() => expect(screen.queryByTestId('lots-analysis-panel-loading')).toBeNull());
    return view;
}

/** Turns the switch on and waits for the MERGED main answer to be asked. */
async function switchOn() {
    const before = bodies().length;
    await fireEvent.click(screen.getByTestId('lots-reward-allocation-toggle'));
    await waitFor(() =>
        expect(
            bodies()
                .slice(before)
                .some((body) => isMain(body) && body.reward_allocation === 'MERGED'),
        ).toBe(true),
    );
    await waitFor(() => expect(screen.getByTestId('lots-reward-allocation-toggle')).toHaveAttribute('data-state', 'MERGED'));
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

describe('LotsAnalysisPanel — the «spread rewards across lots» switch (STK-3)', () => {
    it('is not drawn when the scope has no reward', async () => {
        await renderApplied();
        // Presence barrier: the header is there, with the method selector beside where the switch would be
        expect(screen.getByTestId('lots-method-FIFO')).toBeVisible();
        expect(screen.queryByTestId('lots-reward-allocation-toggle')).toBeNull();
        expect(
            bodies()
                .filter(isMain)
                .every((body) => !('reward_allocation' in body)),
        ).toBe(true);
    });

    it('is drawn, off, when a lot opened by a reward is in the scope; the usual request carries no reward_allocation', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        await renderApplied();
        const toggle = await screen.findByTestId('lots-reward-allocation-toggle');
        expect(toggle).toHaveAttribute('data-state', 'OWN_LOT');
        expect(toggle).toHaveAttribute('aria-pressed', 'false');
        const [main] = bodies().filter(isMain);
        expect('reward_allocation' in main, 'the OWN_LOT request carries the field: its cache key changed').toBe(false);
    });

    it('is drawn when the only trace of a reward is its income event', async () => {
        scope.income = [{type: 'REWARD', date: '2024-03-01', amount: '10', lot_ids: [1]}];
        await renderApplied();
        expect(await screen.findByTestId('lots-reward-allocation-toggle')).toHaveAttribute('data-state', 'OWN_LOT');
    });

    it('pressed, asks the main and the selection analyses again with reward_allocation MERGED', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        await renderApplied();
        await screen.findByTestId('lots-reward-allocation-toggle');
        const before = bodies().length;

        await switchOn();
        const toggle = screen.getByTestId('lots-reward-allocation-toggle');
        expect(toggle).toHaveAttribute('aria-pressed', 'true');
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

    it('stays drawn while on, even when the MERGED answer holds no reward row', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        scope.mergedEvents = [BUY_ROW];
        await renderApplied();
        await screen.findByTestId('lots-reward-allocation-toggle');
        // The MERGED main answer is held until the panel is seen waiting for it: until then the OWN_LOT rows (with their
        // REWARD) are still on screen and would keep the switch drawn by themselves
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
        // The MERGED answer is on screen, with no reward row: only the switch being on keeps it drawn
        expect(screen.getByTestId('lots-reward-allocation-toggle')).toHaveAttribute('data-state', 'MERGED');
        expect(screen.getByTestId('lots-reward-allocation-toggle')).toHaveAttribute('aria-pressed', 'true');
    });

    it('pressed again, asks the usual question with no reward_allocation', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        await renderApplied();
        await screen.findByTestId('lots-reward-allocation-toggle');
        await switchOn();
        const before = bodies().length;

        await fireEvent.click(screen.getByTestId('lots-reward-allocation-toggle'));
        await waitFor(() => expect(bodies().slice(before).some(isMain)).toBe(true));
        expect(
            bodies()
                .slice(before)
                .filter(isMain)
                .every((body) => !('reward_allocation' in body)),
        ).toBe(true);
        expect(screen.getByTestId('lots-reward-allocation-toggle')).toHaveAttribute('data-state', 'OWN_LOT');
    });

    it('keeps MERGED when the method switches from FIFO to LIFO', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        await renderApplied();
        await screen.findByTestId('lots-reward-allocation-toggle');
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
        expect(screen.getByTestId('lots-reward-allocation-toggle')).toHaveAttribute('data-state', 'MERGED');
    });

    it('starts at OWN_LOT again on another asset', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        const view = await renderApplied();
        await screen.findByTestId('lots-reward-allocation-toggle');
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
        await waitFor(() => expect(screen.getByTestId('lots-reward-allocation-toggle')).toHaveAttribute('data-state', 'OWN_LOT'));
    });

    it('starts at OWN_LOT again when the panel is opened again', async () => {
        scope.events = [BUY_ROW, REWARD_ROW];
        const view = await renderApplied();
        await screen.findByTestId('lots-reward-allocation-toggle');
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
        await waitFor(() => expect(screen.getByTestId('lots-reward-allocation-toggle')).toHaveAttribute('data-state', 'OWN_LOT'));
    });
});
