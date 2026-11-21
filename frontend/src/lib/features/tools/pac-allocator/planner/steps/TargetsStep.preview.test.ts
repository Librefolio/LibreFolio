// @vitest-environment jsdom
/**
 * The Targets step reads the preview (F3a of project 67, step 9a; N1, U5, M17).
 *
 * The numbers before the calculation are the backend's (`PlannerPreview`): the Rebalancer's intro names the total that
 * enters the plan, the «Now» column shows each row's weight today, and the limits note names the total a percentage refers
 * to (the PAC's too). While the preview waits the figures stay, marked stale; after a failure they are gone and a line
 * says why. The total is the user's money: masked in privacy mode. Mounted below a Tool wrapper in miniature; the preview
 * is a real `PlannerPreview` whose state the test sets; nothing reads translated text (figures are compared with the
 * planner's own formatters).
 */
import {flushSync, tick} from 'svelte';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PlannerDraft, type DraftAsset} from '../draft.svelte';
import {formatExactMoneyPlain, formatExactPercent} from '../format';
import {PlannerPreview, type PreviewReady} from '../preview.svelte';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE, type PlannerProfile} from '../profile';
import TargetsStep from './TargetsStep.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
    vi.restoreAllMocks();
});

/** jsdom has no media queries: answer the table's phone breakpoint (768 px) as a phone does. */
function asPhone(): void {
    vi.spyOn(window, 'matchMedia').mockImplementation((query: string) => ({matches: query.includes('max-width: 768px'), media: query, onchange: null, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}, dispatchEvent: () => false}) as MediaQueryList);
}

const TOTAL = {value: {kind: 'finite_decimal' as const, value: '12345.67'}, currency: 'EUR'};

function scenario(profile: PlannerProfile) {
    const draft = new PlannerDraft('EUR', 'proportional', profile);
    const broker = draft.addManualBroker('Broker probe');
    const asset: DraftAsset = {
        key: 'asset:probe',
        origin: 'manual',
        sourceAssetId: null,
        name: 'ETF probe',
        ticker: 'PRB',
        assetClass: 'etf',
        iconUrl: null,
        active: true,
        price: {amount: '10', currency: 'EUR', quoteBaseQuantity: '1', referenceDate: '2026-11-14'},
        priceManual: false,
        copiedPrice: null,
        priceStamp: null,
        priceSource: null,
        exposures: [],
        copiedExposures: null,
        exposureStamp: null,
        enteredAt: '2026-11-14T10:00:00Z',
    };
    draft.addAsset(asset);
    draft.data.targets[asset.key] = '90';
    return {draft, brokerKey: broker.key};
}

function ready(brokerKey: string): PreviewReady {
    return {
        operation: 'preview',
        result_state: 'preview_ready',
        availability: 'ready',
        valuation_currency: 'EUR',
        total: TOTAL,
        issues: [],
        limit_problems: [],
        items: [
            {kind: 'asset', asset_id: 'asset:probe', value: TOTAL, weight: {kind: 'finite_decimal', value: '0.42'}},
            {kind: 'cash', broker_id: brokerKey, currency: 'EUR', value: TOTAL, weight: {kind: 'finite_decimal', value: '0.06'}},
            {kind: 'other_cash', value: TOTAL, weight: {kind: 'finite_decimal', value: '0.12'}},
        ],
    };
}

function previewWith(state: PlannerPreview['state'], numbers: PreviewReady | null, reason: string | null = null): PlannerPreview {
    const preview = new PlannerPreview({call: vi.fn(), blocked: () => false});
    preview.state = state;
    preview.numbers = numbers;
    preview.reason = reason;
    return preview;
}

function mount(profile: PlannerProfile | null, draft: PlannerDraft, preview: PlannerPreview | null): void {
    render(ProfileHarness, {props: {profile, child: TargetsStep, childProps: {draft, accountGeneration: 0, preview}}});
    flushSync();
}

describe('the Targets step and the preview', () => {
    it('the Now column and the step total come from preview', () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        const entry = draft.addCashEntry(brokerKey, 'EUR');
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));

        expect(screen.getByTestId('rebalancer-planner-targets-intro').textContent).toContain(formatExactMoneyPlain(TOTAL));
        const now = screen.getAllByTestId('rebalancer-planner-target-now');
        expect(now.map((cell) => [cell.getAttribute('data-asset-key'), cell.textContent?.trim()])).toEqual([
            ['asset:probe', formatExactPercent({kind: 'finite_decimal', value: '0.42'}, 1)],
            [entry.key, formatExactPercent({kind: 'finite_decimal', value: '0.06'}, 1)],
        ]);
        expect(screen.getByTestId('rebalancer-planner-targets').getAttribute('data-preview')).toBe('ready');
    });

    it('stale numbers stay, marked; a failed preview removes them and says why', () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('waiting', ready(brokerKey)));
        expect(screen.getByTestId('rebalancer-planner-targets').getAttribute('data-stale')).toBe('true');
        expect(screen.getByTestId('rebalancer-planner-targets-intro').textContent).toContain(formatExactMoneyPlain(TOTAL));
        cleanup();

        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('error', null, 'unavailable'));
        expect(screen.getByTestId('rebalancer-planner-targets-intro').textContent).not.toContain(formatExactMoneyPlain(TOTAL));
        expect(screen.getAllByTestId('rebalancer-planner-target-now').every((cell) => cell.textContent?.trim() === '')).toBe(true);
        expect(screen.getByTestId('rebalancer-planner-targets-preview-reason').getAttribute('data-reason')).toBe('unavailable');
    });

    it('the limits hint shows the preview total, PAC included', () => {
        const {draft} = scenario(PAC_PLANNER_PROFILE);
        mount(null, draft, previewWith('ready', {...ready('none'), items: undefined}));
        expect(screen.getByTestId('pac-planner-targets-limits-note').textContent).toContain(formatExactMoneyPlain(TOTAL));
        // The PAC has no «Now» column.
        expect(screen.queryAllByTestId('pac-planner-target-now')).toHaveLength(0);
        cleanup();

        mount(null, draft, null);
        expect(screen.getByTestId('pac-planner-targets-limits-note').textContent).not.toContain(formatExactMoneyPlain(TOTAL));
    });

    it('the total is masked in privacy mode, both ways', async () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
        const shown = formatExactMoneyPlain(TOTAL);

        setPrivacyEnabled(true);
        flushSync();
        await tick();
        expect(screen.getByTestId('rebalancer-planner-targets-intro').textContent).toContain(PRIVACY_PLACEHOLDER);
        expect(screen.getByTestId('rebalancer-planner-targets-intro').textContent).not.toContain(shown);

        setPrivacyEnabled(false);
        flushSync();
        await tick();
        expect(screen.getByTestId('rebalancer-planner-targets-intro').textContent).toContain(shown);
    });

    it('the PAC limits note masks the total in privacy mode, both ways', async () => {
        const {draft} = scenario(PAC_PLANNER_PROFILE);
        mount(null, draft, previewWith('ready', {...ready('none'), items: undefined}));
        const note = () => screen.getByTestId('pac-planner-targets-limits-note').textContent;
        const shown = formatExactMoneyPlain(TOTAL);

        setPrivacyEnabled(true);
        flushSync();
        await tick();
        expect(note()).toContain(PRIVACY_PLACEHOLDER);
        expect(note()).not.toContain(shown);

        setPrivacyEnabled(false);
        flushSync();
        await tick();
        expect(note()).toContain(shown);
    });

    it('«Other cash» shows its own weight today, from the preview (G5-2)', () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        draft.addCashEntry(brokerKey, 'EUR');
        // A manual account: cash without a target of its own, so the «Other cash» row is there.
        draft.addManualAccount({name: 'Bank probe', currency: 'EUR', available: '100', selected: '50'});
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));

        const other = screen.getAllByTestId('rebalancer-planner-target-now').find((cell) => cell.getAttribute('data-asset-key') === 'other-cash');
        expect(other?.textContent?.trim()).toBe(formatExactPercent({kind: 'finite_decimal', value: '0.12'}, 1));
    });

    describe('«Other cash» only when it is worth more than 0 today (R1-C of project 67, approved 19/11)', () => {
        /** The last preview with «Other cash» worth `amount` today. */
        function withOther(brokerKey: string, amount: string): PreviewReady {
            const numbers = ready(brokerKey);
            return {...numbers, items: numbers.items!.map((item) => (item.kind === 'other_cash' ? {...item, value: {value: {kind: 'finite_decimal' as const, value: amount}, currency: 'EUR'}} : item))};
        }
        /** Cash without a target of its own: the draft has «Other cash»; whether it shows is the preview's to say. */
        function withLooseCash() {
            const made = scenario(REBALANCER_PLANNER_PROFILE);
            made.draft.addManualAccount({name: 'Bank probe', currency: 'EUR', available: '100', selected: '50'});
            return made;
        }
        const row = () => screen.queryByTestId('rebalancer-planner-target-other-cash');

        it('no row before a preview has said what it is worth', () => {
            const {draft} = withLooseCash();
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('waiting', null));
            expect(screen.getByTestId('rebalancer-planner-targets').getAttribute('data-preview')).toBe('waiting');
            expect(row()).toBeNull();
        });

        it('no row when it is worth 0 today', () => {
            const {draft, brokerKey} = withLooseCash();
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', withOther(brokerKey, '0')));
            expect(screen.getByTestId('rebalancer-planner-targets').getAttribute('data-preview')).toBe('ready');
            expect(row()).toBeNull();
        });

        it('the row when it is worth more than 0 today', () => {
            const {draft, brokerKey} = withLooseCash();
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', withOther(brokerKey, '0.01')));
            expect(row()).not.toBeNull();
        });

        it('an exact ratio is read by its sign too: worth a third of a cent, the row is there', () => {
            const {draft, brokerKey} = withLooseCash();
            const numbers = ready(brokerKey);
            const third = {kind: 'exact_ratio' as const, numerator: '1', denominator: '300', display_decimal: '0.003333', display_scale: 6, display_authority: 'non_authoritative' as const};
            const withRatio: PreviewReady = {...numbers, items: numbers.items!.map((item) => (item.kind === 'other_cash' ? {...item, value: {value: third, currency: 'EUR'}} : item))};
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', withRatio));
            expect(row()).not.toBeNull();
        });

        it('a stale preview keeps its answer until the next one: the row stays, or stays out', () => {
            const {draft, brokerKey} = withLooseCash();
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('waiting', withOther(brokerKey, '50')));
            expect(screen.getByTestId('rebalancer-planner-targets').getAttribute('data-stale')).toBe('true');
            expect(row()).not.toBeNull();
            cleanup();
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('waiting', withOther(brokerKey, '0')));
            expect(row()).toBeNull();
        });

        it('a preview worth more than 0 adds no row when no cash is outside the entries', () => {
            const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
            draft.addCashEntry(brokerKey, 'EUR');
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
            expect(row()).toBeNull();
        });
    });

    it('a contribution alone is «Other cash» too: the row is there with its weight (G5-2)', () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        const contribution = draft.addContribution('EUR', 'Salary probe');
        draft.contribution(contribution.key)!.amount = '300';
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));

        const other = screen.getAllByTestId('rebalancer-planner-target-now').find((cell) => cell.getAttribute('data-asset-key') === 'other-cash');
        expect(other?.textContent?.trim()).toBe(formatExactPercent({kind: 'finite_decimal', value: '0.12'}, 1));
    });

    it('on a phone, where «Now» starts hidden, each name carries its weight today under it (G5-1)', async () => {
        asPhone();
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        const entry = draft.addCashEntry(brokerKey, 'EUR');
        draft.addManualAccount({name: 'Bank probe', currency: 'EUR', available: '100', selected: '50'});
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));

        expect(screen.queryAllByTestId('rebalancer-planner-target-now')).toHaveLength(0);
        const lines = screen.getAllByTestId('rebalancer-planner-target-now-line').map((line) => [line.getAttribute('data-asset-key'), line.textContent ?? '']);
        expect(lines.map(([key]) => key)).toEqual(['asset:probe', entry.key, 'other-cash']);
        const percent = (value: string) => formatExactPercent({kind: 'finite_decimal', value}, 1);
        expect(lines.map(([, text], index) => (text ?? '').includes(percent(['0.42', '0.06', '0.12'][index])))).toEqual([true, true, true]);

        // «Columns» brings the column back: the lines go, the cells show the weights.
        await fireEvent.click(within(screen.getByTestId('rebalancer-planner-targets-columns')).getByTestId('column-visibility-toggle'));
        await fireEvent.click(await screen.findByTestId('column-visibility-item-now'));
        flushSync();
        expect(screen.queryAllByTestId('rebalancer-planner-target-now-line')).toHaveLength(0);
        expect(screen.getAllByTestId('rebalancer-planner-target-now').map((cell) => cell.getAttribute('data-asset-key'))).toEqual(['asset:probe', entry.key, 'other-cash']);
        cleanup();

        // On a wide screen the column shows it: no line under the names.
        vi.restoreAllMocks();
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
        expect(screen.queryAllByTestId('rebalancer-planner-target-now-line')).toHaveLength(0);
    });

    describe('the limits the backend checks are said in this step, from the preview (R1-E of project 67)', () => {
        // «Ho messo un minimo che era più di tutto il capitale disponibile, mi aspettavo già in 6 un banner» (§2 n. 2).
        /** One of the preview's cross checks of the limits, on `assetKey`'s target entry (contract 2.0.0, a field path). */
        function limitProblem(code: string, assetKey: string, field: 'minimum' | 'maximum' = 'minimum') {
            return {code, severity: 'error', kind: 'invalid', path: {kind: 'field', section: 'targets', entity_kind: 'asset', entity_id: assetKey, field}, message_key: code, params: []} as unknown as PreviewReady['limit_problems'][number];
        }
        const box = (prefix: string) => screen.queryByTestId(`${prefix}-targets-limits-problems`);
        const lines = (prefix: string, key: string) => screen.queryAllByTestId(`${prefix}-targets-limits-problem`).filter((line) => line.getAttribute('data-key') === key);

        it('PAC: a minimum above the money the plan invests shows in the step, and stays while the preview is stale', () => {
            const {draft} = scenario(PAC_PLANNER_PROFILE);
            draft.setLimit('asset:probe', 'minimum', '20000');
            const numbers = {...ready('none'), items: undefined, limit_problems: [limitProblem('allocation.bounds_min_sum_exceeds_reference', 'asset:probe')]};
            mount(null, draft, previewWith('ready', numbers));
            const [line] = lines('pac-planner', 'bounds_min_sum_exceeds_reference');
            expect(line?.textContent).toContain('ETF probe');
            cleanup();

            mount(null, draft, previewWith('waiting', numbers));
            expect(lines('pac-planner', 'bounds_min_sum_exceeds_reference')).toHaveLength(1);
            cleanup();

            // A failed preview has no numbers: nothing of it is said.
            mount(null, draft, previewWith('error', null, 'unavailable'));
            expect(box('pac-planner')).toBeNull();
        });

        it('Rebalancer: a maximum below what is held today names its entry', () => {
            const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
            draft.setLimit('asset:probe', 'maximum', '1');
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', {...ready(brokerKey), limit_problems: [limitProblem('allocation.bound_max_below_current', 'asset:probe', 'maximum')]}));
            const [line] = lines('rebalancer-planner', 'bound_max_below_current');
            expect(line?.getAttribute('data-asset-key')).toBe('asset:probe');
            expect(line?.textContent).toContain('ETF probe');
        });

        it('a problem the page already says is not said twice', () => {
            const {draft} = scenario(PAC_PLANNER_PROFILE);
            draft.setLimit('asset:probe', 'minimum', '2000');
            draft.setLimit('asset:probe', 'maximum', '1000');
            mount(null, draft, previewWith('ready', {...ready('none'), items: undefined, limit_problems: [limitProblem('allocation.bound_min_above_max', 'asset:probe')]}));
            expect(lines('pac-planner', 'limitMinAboveMax')).toHaveLength(1);
            expect(lines('pac-planner', 'bound_min_above_max')).toHaveLength(0);
        });

        describe('a cash entry, named on the wire «<broker>:CURRENCY»', () => {
            /** The same cross check on the cash entry of `brokerKey` in EUR. */
            function onCash(code: string, brokerKey: string) {
                const problem = limitProblem(code, '');
                return {...problem, path: {kind: 'field', section: 'targets', entity_kind: 'cash', entity_id: `${brokerKey}:EUR`, field: 'minimum'}} as unknown as PreviewReady['limit_problems'][number];
            }

            it('is named by its Broker and currency, on its own row', () => {
                const {draft, brokerKey} = scenario(PAC_PLANNER_PROFILE);
                const entry = draft.addCashEntry(brokerKey, 'EUR');
                draft.setLimit(entry.key, 'minimum', '600');
                draft.setLimit(entry.key, 'maximum', '10%');
                mount(null, draft, previewWith('ready', {...ready(brokerKey), items: undefined, limit_problems: [onCash('allocation.bound_min_above_max', brokerKey), onCash('allocation.bounds_min_sum_exceeds_reference', brokerKey)]}));
                const [conflict] = lines('pac-planner', 'bound_min_above_max');
                expect(conflict?.getAttribute('data-asset-key')).toBe(entry.key);
                expect(conflict?.textContent).toContain('Broker probe · EUR');
                expect(lines('pac-planner', 'bounds_min_sum_exceeds_reference')[0]?.textContent).toContain('Broker probe · EUR');
            });

            it('its minimum above the maximum in the same form is said once, by the page', () => {
                const {draft, brokerKey} = scenario(PAC_PLANNER_PROFILE);
                const entry = draft.addCashEntry(brokerKey, 'EUR');
                draft.setLimit(entry.key, 'minimum', '2000');
                draft.setLimit(entry.key, 'maximum', '1000');
                mount(null, draft, previewWith('ready', {...ready(brokerKey), items: undefined, limit_problems: [onCash('allocation.bound_min_above_max', brokerKey)]}));
                expect(lines('pac-planner', 'limitMinAboveMax')).toHaveLength(1);
                expect(lines('pac-planner', 'bound_min_above_max')).toHaveLength(0);
            });
        });
    });
});
