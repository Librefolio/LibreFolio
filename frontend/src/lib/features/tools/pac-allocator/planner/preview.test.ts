// @vitest-environment jsdom
/**
 * The scenario preview (F3a of project 67, step 8; N1, contract §11; Vitest + jsdom, fake clock, fake call).
 *
 * Subject. Before the calculation the numbers come from the backend: the service's `preview` operation reads the same
 * request as `plan` (`buildRequest(draft, now, {operation: 'preview'})`, even incomplete) and answers the total, today's
 * items and the λ of the fidelity levels. `PlannerPreview`:
 *   - calls it once, a delay after the last change, with the latest draft's request;
 *   - while it waits, keeps the previous numbers, marked stale;
 *   - drops an answer older than the latest asked;
 *   - on a failure (the network, a `needs_input` answer, a draft it cannot send) drops the numbers and keeps the reason;
 *   - never runs during a calculation (one batch per user: the run would get a 429);
 *   - turns the euros typed for «Custom» into the draft's λ on a current answer's total (`acceptableCost.ts`, R1-F (b) of
 *     project 67): at once, with no call, when the numbers are current; on the next answer when they are stale;
 *   - is keyed on the draft without its fidelity, and sends «Balanced»: a level chosen or a figure typed asks nothing.
 * The call is a fake; nothing talks to a server.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {PlannerDraft, type DraftAsset} from './draft.svelte';
import {defaultPolicy} from './policies';
import {PlannerPreview, PREVIEW_DELAY_MS, type PreviewAnswer} from './preview.svelte';
import {REBALANCER_PLANNER_PROFILE} from './profile';

const AS_OF = '2026-11-14';
type Call = (request: Record<string, unknown>, signal: AbortSignal) => Promise<PreviewAnswer>;

function draftOf(): PlannerDraft {
    const draft = new PlannerDraft('EUR', defaultPolicy(REBALANCER_PLANNER_PROFILE), REBALANCER_PLANNER_PROFILE);
    draft.data.asOf = AS_OF;
    draft.addManualBroker('Broker probe');
    draft.addManualAccount({name: 'Bank probe', currency: 'EUR', available: '100', selected: '50'});
    const asset: DraftAsset = {
        key: 'asset:probe',
        origin: 'manual',
        sourceAssetId: null,
        name: 'ETF probe',
        ticker: '',
        assetClass: 'etf',
        iconUrl: null,
        active: true,
        price: {amount: '10', currency: 'EUR', quoteBaseQuantity: '1', referenceDate: AS_OF},
        priceManual: false,
        copiedPrice: null,
        priceStamp: null,
        priceSource: null,
        exposures: [],
        copiedExposures: null,
        exposureStamp: null,
        enteredAt: `${AS_OF}T10:00:00.000Z`,
    };
    draft.addAsset(asset);
    // An incomplete target (40 %): the preview still counts.
    draft.data.targets[asset.key] = '40';
    return draft;
}

function ready(total: string, extra: Record<string, unknown> = {}): PreviewAnswer {
    return {kind: 'answer', result: {operation: 'preview', result_state: 'preview_ready', availability: 'ready', valuation_currency: 'EUR', total: {value: {kind: 'finite_decimal', value: total}, currency: 'EUR'}, issues: [], limit_problems: [], items: [], ...extra}};
}

/** A call whose answers the test releases one by one, in any order. */
function controlled() {
    const pending: {request: Record<string, unknown>; resolve: (answer: PreviewAnswer) => void; reject: (error: unknown) => void}[] = [];
    const call: Call = (request) => new Promise((resolve, reject) => pending.push({request, resolve, reject}));
    return {call: vi.fn(call), pending};
}

beforeEach(() => {
    vi.useFakeTimers();
});

afterEach(() => {
    vi.useRealTimers();
});

describe('PlannerPreview', () => {
    it('preview is called once after the delay that follows the last change', async () => {
        const draft = draftOf();
        const {call, pending} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});

        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS / 2);
        draft.data.targets['asset:probe'] = '50';
        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS / 2);
        draft.data.targets['asset:probe'] = '60';
        preview.schedule(draft);
        expect(call).not.toHaveBeenCalled();
        vi.advanceTimersByTime(PREVIEW_DELAY_MS);

        expect(call).toHaveBeenCalledOnce();
        const request = pending[0].request;
        expect(request.operation).toBe('preview');
        expect((request.target_weights as {asset_id?: string; weight: string}[]).find((entry) => entry.asset_id === 'asset:probe')?.weight).toBe('0.6');
        expect(preview.state).toBe('waiting');
        preview.dispose();
    });

    it('while waiting the previous numbers stay, marked as stale', async () => {
        const draft = draftOf();
        const {call, pending} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});
        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS);
        pending[0].resolve(ready('150'));
        await vi.runAllTimersAsync();
        expect(preview.state).toBe('ready');
        expect(preview.numbers?.total.value).toEqual({kind: 'finite_decimal', value: '150'});
        expect(preview.stale).toBe(false);

        draft.data.targets['asset:probe'] = '70';
        preview.schedule(draft);
        expect(preview.stale).toBe(true);
        expect(preview.numbers?.total.value).toEqual({kind: 'finite_decimal', value: '150'});
        vi.advanceTimersByTime(PREVIEW_DELAY_MS);
        expect(preview.stale).toBe(true);
        pending[1].resolve(ready('155'));
        await vi.runAllTimersAsync();
        expect([preview.stale, preview.numbers?.total.value]).toEqual([false, {kind: 'finite_decimal', value: '155'}]);
        preview.dispose();
    });

    it('a change while a preview is on its way waits for it, then sends the latest draft once', async () => {
        // One batch per user: a second call while the first runs would be refused (429), so it is never sent.
        const draft = draftOf();
        const {call, pending} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});
        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS);
        draft.data.targets['asset:probe'] = '70';
        preview.schedule(draft);
        draft.data.targets['asset:probe'] = '80';
        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS * 3);
        expect(call).toHaveBeenCalledOnce();

        pending[0].resolve(ready('100'));
        await vi.runAllTimersAsync();
        expect(call).toHaveBeenCalledTimes(2);
        expect((pending[1].request.target_weights as {asset_id?: string; weight: string}[]).find((entry) => entry.asset_id === 'asset:probe')?.weight).toBe('0.8');
        // The first answer is shown, stale, until the second lands.
        expect([preview.stale, preview.numbers?.total.value]).toEqual([true, {kind: 'finite_decimal', value: '100'}]);
        pending[1].resolve(ready('200'));
        await vi.runAllTimersAsync();
        expect([preview.state, preview.numbers?.total.value]).toEqual(['ready', {kind: 'finite_decimal', value: '200'}]);
        preview.dispose();
    });

    it('an answer that lands while a newer change waits for its pause stays waiting, never ready or error', async () => {
        // Found in G5: the answer of an older draft, landing in the pause after the last change, showed `ready` (or `error`)
        // and not stale, so the screen, and a shot waiting for `ready`, took old numbers for current ones.
        const draft = draftOf();
        const {call, pending} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});
        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS);
        draft.data.targets['asset:probe'] = '70';
        preview.schedule(draft);
        pending[0].resolve(ready('100'));
        await vi.advanceTimersByTimeAsync(0);
        expect([preview.state, preview.stale, preview.numbers?.total.value]).toEqual(['waiting', true, {kind: 'finite_decimal', value: '100'}]);

        draft.data.targets['asset:probe'] = '80';
        preview.schedule(draft);
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS);
        expect(call).toHaveBeenCalledTimes(2);
        draft.data.targets['asset:probe'] = '90';
        preview.schedule(draft);
        pending[1].resolve({kind: 'answer', result: {operation: 'preview', result_state: 'preview_needs_input', issues: [{code: 'allocation.fx_rate_missing'}]}});
        await vi.advanceTimersByTimeAsync(0);
        expect([preview.state, preview.numbers, preview.reason]).toEqual(['waiting', null, 'allocation.fx_rate_missing']);

        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS);
        expect(call).toHaveBeenCalledTimes(3);
        pending[2].resolve(ready('300'));
        await vi.advanceTimersByTimeAsync(0);
        expect([preview.state, preview.stale, preview.numbers?.total.value]).toEqual(['ready', false, {kind: 'finite_decimal', value: '300'}]);
        preview.dispose();
    });

    it('the latest draft goes once, even when a change arms the pause while another waits in the queue', async () => {
        const draft = draftOf();
        const {call, pending} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});
        preview.schedule(draft);
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS);
        draft.data.targets['asset:probe'] = '70';
        preview.schedule(draft);
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS);
        draft.data.targets['asset:probe'] = '80';
        preview.schedule(draft);
        pending[0].resolve(ready('100'));
        await vi.advanceTimersByTimeAsync(0);
        expect(call).toHaveBeenCalledTimes(2);
        expect((pending[1].request.target_weights as {asset_id?: string; weight: string}[]).find((entry) => entry.asset_id === 'asset:probe')?.weight).toBe('0.8');

        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS * 2);
        pending[1].resolve(ready('200'));
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS * 2);
        expect(call).toHaveBeenCalledTimes(2);
        expect([preview.state, preview.numbers?.total.value]).toEqual(['ready', {kind: 'finite_decimal', value: '200'}]);
        preview.dispose();
    });

    it('a failed preview drops the numbers and keeps the reason', async () => {
        const draft = draftOf();
        const {call, pending} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});
        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS);
        pending[0].resolve(ready('150'));
        await vi.runAllTimersAsync();

        // A needs_input answer: no number, its issue's code is the reason.
        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS);
        pending[1].resolve({kind: 'answer', result: {operation: 'preview', result_state: 'preview_needs_input', availability: 'needs_input', issues: [{code: 'allocation.missing_price'}]}});
        await vi.runAllTimersAsync();
        expect([preview.state, preview.numbers, preview.reason]).toEqual(['error', null, 'allocation.missing_price']);

        // The network: the same.
        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS);
        pending[2].reject(new Error('network probe'));
        await vi.runAllTimersAsync();
        expect([preview.state, preview.numbers, preview.reason]).toEqual(['error', null, 'unavailable']);

        // A draft the request cannot carry yet (a step that is not a number): no call, the reason says so.
        draft.data.brokers[0].modes[0].step = 'abc';
        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS);
        expect(call).toHaveBeenCalledTimes(3);
        expect([preview.state, preview.numbers, preview.reason]).toEqual(['error', null, 'incomplete']);
        preview.dispose();
    });

    it('no preview runs during a calculation; it runs once the calculation is over', async () => {
        const draft = draftOf();
        const {call} = controlled();
        let calculating = true;
        const preview = new PlannerPreview({call, blocked: () => calculating});

        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS * 3);
        expect(call).not.toHaveBeenCalled();

        calculating = false;
        vi.advanceTimersByTime(PREVIEW_DELAY_MS);
        expect(call).toHaveBeenCalledOnce();
        preview.dispose();
    });

    /** A ready answer on `total` with the λ of the three levels, as the Rebalancer's preview gives them. */
    function levels(total: string): PreviewAnswer {
        return ready(total, {fidelity_level_weights: {cost_aware: {kind: 'finite_decimal', value: '0.25'}, balanced: {kind: 'finite_decimal', value: '1'}, faithful: {kind: 'finite_decimal', value: '4'}}});
    }

    it('the preview is keyed on the draft without its fidelity: a level chosen or a figure typed asks nothing (R1-F b)', () => {
        const draft = draftOf();
        const key = draft.previewFingerprint;
        const fingerprint = draft.fingerprint;
        draft.data.fidelity = {kind: 'custom', lambda: '0.6'};
        // The plan's fingerprint moves (a result on another λ is stale); the preview's key does not.
        expect(draft.fingerprint).not.toBe(fingerprint);
        expect(draft.previewFingerprint).toBe(key);
        draft.data.fidelity = {kind: 'target_first'};
        expect(draft.previewFingerprint).toBe(key);
        draft.data.targets['asset:probe'] = '50';
        expect(draft.previewFingerprint).not.toBe(key);
    });

    it('the preview request carries «Balanced» whatever the fidelity, and never the euros (R1-F b)', async () => {
        const draft = draftOf();
        draft.data.fidelity = {kind: 'custom', lambda: '0.6'};
        const {call, pending} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});
        preview.schedule(draft);
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS);
        expect(pending[0].request.target_fidelity).toEqual({kind: 'level', level: 'balanced'});
        expect(pending[0].request).not.toHaveProperty('custom_reference_amount');
        preview.dispose();
    });

    it('euros typed on current numbers become the draft λ at once, with no call (R1-F b, «istantaneo»)', async () => {
        const draft = draftOf();
        const {call, pending} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});
        preview.schedule(draft);
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS);
        pending[0].resolve(levels('20000'));
        await vi.advanceTimersByTimeAsync(0);
        expect(preview.state).toBe('ready');

        // As the step does: «Custom» with no λ, then the figure.
        draft.data.fidelity = {kind: 'custom', lambda: ''};
        preview.setCustomEuros(draft, '60');
        // 60·20 000/(2·1 000²) = 0.6, on the spot.
        expect(draft.data.fidelity).toEqual({kind: 'custom', lambda: '0.6'});
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS * 2);
        expect(call).toHaveBeenCalledTimes(1);
        expect([preview.state, preview.stale]).toEqual(['ready', false]);
        preview.dispose();
    });

    it('euros typed while the numbers are stale become λ on the next answer, on its total', async () => {
        const draft = draftOf();
        const {call, pending} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});
        preview.schedule(draft);
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS);
        pending[0].resolve(levels('20000'));
        await vi.advanceTimersByTimeAsync(0);

        // A new total is on its way: the figure waits for it, never converted on the old one.
        draft.data.targets['asset:probe'] = '50';
        preview.schedule(draft);
        draft.data.fidelity = {kind: 'custom', lambda: ''};
        preview.setCustomEuros(draft, '60');
        expect(draft.data.fidelity).toEqual({kind: 'custom', lambda: ''});
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS);
        pending[1].resolve(levels('10000'));
        await vi.advanceTimersByTimeAsync(0);
        // 60·10 000/(2·500²) = 1.2.
        expect(draft.data.fidelity).toEqual({kind: 'custom', lambda: '1.2'});
        expect(call).toHaveBeenCalledTimes(2);
        preview.dispose();
    });

    it('the figure still typed wins: newer euros replace the waiting ones, a cleared field withdraws them (10b)', async () => {
        const draft = draftOf();
        const {pending, call} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});
        preview.schedule(draft);
        draft.data.fidelity = {kind: 'custom', lambda: ''};
        preview.setCustomEuros(draft, '60');
        preview.setCustomEuros(draft, '600');
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS);
        pending[0].resolve(levels('20000'));
        await vi.advanceTimersByTimeAsync(0);
        expect(draft.data.fidelity).toEqual({kind: 'custom', lambda: '6'});

        draft.data.targets['asset:probe'] = '50';
        preview.schedule(draft);
        draft.data.fidelity = {kind: 'custom', lambda: ''};
        preview.setCustomEuros(draft, '70');
        preview.setCustomEuros(draft, '');
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS);
        pending[1].resolve(levels('20000'));
        await vi.advanceTimersByTimeAsync(0);
        expect(draft.data.fidelity).toEqual({kind: 'custom', lambda: ''});
        preview.dispose();
    });

    it('a λ never overwrites a choice the user changed meanwhile', async () => {
        const draft = draftOf();
        draft.data.fidelity = {kind: 'custom', lambda: ''};
        const {call, pending} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});
        preview.schedule(draft);
        preview.setCustomEuros(draft, '60');
        await vi.advanceTimersByTimeAsync(PREVIEW_DELAY_MS);

        draft.data.fidelity = {kind: 'level', level: 'balanced'};
        pending[0].resolve(levels('20000'));
        await vi.runAllTimersAsync();

        expect(draft.data.fidelity).toEqual({kind: 'level', level: 'balanced'});
        preview.dispose();
    });

    it('a calculation can wait for the preview in flight to finish (one batch per user)', async () => {
        const draft = draftOf();
        const {call, pending} = controlled();
        const preview = new PlannerPreview({call, blocked: () => false});
        await preview.settled();
        expect(preview.busy).toBe(false);

        preview.schedule(draft);
        vi.advanceTimersByTime(PREVIEW_DELAY_MS);
        expect(preview.busy).toBe(true);
        let done = false;
        void preview.settled().then(() => (done = true));
        await vi.runAllTimersAsync();
        expect(done).toBe(false);

        pending[0].resolve(ready('150'));
        await vi.runAllTimersAsync();
        expect([done, preview.busy]).toEqual([true, false]);
        preview.dispose();
    });
});
