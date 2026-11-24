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
import {get} from 'svelte/store';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {t} from '$lib/i18n';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PlannerDraft, type DraftAsset} from '../draft.svelte';
import {formatExactMoneyPlain, formatExactPercent, formatPlannerMoneyPlain, formatPlannerPercentUnits} from '../format';
import {PlannerPreview, type PreviewReady} from '../preview.svelte';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE, type PlannerProfile} from '../profile';
import {STEP_TITLE_CONTEXT, StepTitleSlot} from '../shell/stepTitle.svelte';
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

    describe('the cash without a target of its own is never a row (TL-2 of project 67, the testlist of 21/11)', () => {
        /** The last preview with the backend's `other_cash` worth `amount` today. */
        function withOther(brokerKey: string, amount: string): PreviewReady {
            const numbers = ready(brokerKey);
            return {...numbers, items: numbers.items!.map((item) => (item.kind === 'other_cash' ? {...item, value: {value: {kind: 'finite_decimal' as const, value: amount}, currency: 'EUR'}} : item))};
        }
        const keys = () => screen.getAllByTestId('rebalancer-planner-target-now').map((cell) => cell.getAttribute('data-asset-key'));

        it('cash outside the entries, worth more than 0 today: no row, and the plan is the same', () => {
            const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
            draft.addManualAccount({name: 'Bank probe', currency: 'EUR', available: '100', selected: '50'});
            const fingerprint = draft.fingerprint;
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', withOther(brokerKey, '50')));
            expect(keys()).toEqual(['asset:probe']);
            expect(screen.queryByTestId('dt-row-checkbox-other-cash')).toBeNull();
            expect(draft.fingerprint).toBe(fingerprint);
        });

        it('a contribution alone, worth more than 0 today: no row either; stale or not', () => {
            const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
            const contribution = draft.addContribution('EUR', 'Salary probe');
            draft.contribution(contribution.key)!.amount = '300';
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
            expect(keys()).toEqual(['asset:probe']);
            cleanup();
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('waiting', ready(brokerKey)));
            expect(keys()).toEqual(['asset:probe']);
        });
    });

    describe('«Distribution» with two bars in the Rebalancer, on one scale (TL-2)', () => {
        const bars = (testid: string) => Object.fromEntries(screen.getAllByTestId(testid).map((bar) => [bar.getAttribute('data-asset-key'), bar.getAttribute('data-width')]));

        it('the grey bar is the weight today, the coloured one the target: 50 % and 42 % today on a scale of 50', () => {
            const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
            const entry = draft.addCashEntry(brokerKey, 'EUR');
            draft.data.targets['asset:probe'] = '50';
            draft.data.targets[entry.key] = '10';
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
            // Targets 50 and 10 %, today 42 and 6 %: the widest, 50, fills the column.
            expect(bars('rebalancer-planner-target-bar')).toEqual({'asset:probe': '100.00%', [entry.key]: '20.00%'});
            expect(bars('rebalancer-planner-target-bar-now')).toEqual({'asset:probe': '84.00%', [entry.key]: '12.00%'});
        });

        it('a weight today above every target sets the scale', () => {
            const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
            draft.data.targets['asset:probe'] = '21';
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
            expect(bars('rebalancer-planner-target-bar')).toEqual({'asset:probe': '50.00%'});
            expect(bars('rebalancer-planner-target-bar-now')).toEqual({'asset:probe': '100.00%'});
        });

        it('a stale preview mutes the grey bar, a current one does not', () => {
            const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
            const muted = () => screen.getByTestId('rebalancer-planner-target-bar-now').firstElementChild?.classList.contains('opacity-50');
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('waiting', ready(brokerKey)));
            expect(muted()).toBe(true);
            cleanup();
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
            expect(muted()).toBe(false);
        });

        it('without a preview the grey bar is empty, the target is drawn', () => {
            const {draft} = scenario(REBALANCER_PLANNER_PROFILE);
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('waiting', null));
            expect(bars('rebalancer-planner-target-bar')).toEqual({'asset:probe': '100.00%'});
            expect(bars('rebalancer-planner-target-bar-now')).toEqual({'asset:probe': '0.00%'});
            expect(screen.getByTestId('rebalancer-planner-target-bar-now').getAttribute('data-known')).toBe('false');
        });

        it('the columns: Entry, Distribution, Now, Target %, Limits — «Now» beside the target', () => {
            const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
            mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
            const order = screen.getAllByTestId(/^dt-header-/).map((header) => header.getAttribute('data-testid')!.replace('dt-header-', ''));
            expect(order.filter((id) => ['asset', 'bar', 'now', 'target', 'limits'].includes(id))).toEqual(['asset', 'bar', 'now', 'target', 'limits']);
        });

        it('the PAC keeps one bar and its columns: no «Now»', () => {
            const {draft, brokerKey} = scenario(PAC_PLANNER_PROFILE);
            mount(null, draft, previewWith('ready', ready(brokerKey)));
            expect(screen.queryAllByTestId('pac-planner-target-bar-now')).toHaveLength(0);
            expect(bars('pac-planner-target-bar')).toEqual({'asset:probe': '100.00%'});
            const order = screen.getAllByTestId(/^dt-header-/).map((header) => header.getAttribute('data-testid')!.replace('dt-header-', ''));
            expect(order.filter((id) => ['asset', 'bar', 'now', 'target', 'limits'].includes(id))).toEqual(['asset', 'bar', 'target', 'limits']);
        });
    });

    it('on a phone, where «Now» starts hidden, each name carries its weight today under it (G5-1)', async () => {
        asPhone();
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        const entry = draft.addCashEntry(brokerKey, 'EUR');
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));

        expect(screen.queryAllByTestId('rebalancer-planner-target-now')).toHaveLength(0);
        const lines = screen.getAllByTestId('rebalancer-planner-target-now-line').map((line) => [line.getAttribute('data-asset-key'), line.textContent ?? '']);
        expect(lines.map(([key]) => key)).toEqual(['asset:probe', entry.key]);
        const percent = (value: string) => formatExactPercent({kind: 'finite_decimal', value}, 1);
        expect(lines.map(([, text], index) => (text ?? '').includes(percent(['0.42', '0.06'][index])))).toEqual([true, true]);

        // «Columns» brings the column back: the lines go, the cells show the weights.
        await fireEvent.click(within(screen.getByTestId('rebalancer-planner-targets-columns')).getByTestId('column-visibility-toggle'));
        await fireEvent.click(await screen.findByTestId('column-visibility-item-now'));
        flushSync();
        expect(screen.queryAllByTestId('rebalancer-planner-target-now-line')).toHaveLength(0);
        expect(screen.getAllByTestId('rebalancer-planner-target-now').map((cell) => cell.getAttribute('data-asset-key'))).toEqual(['asset:probe', entry.key]);
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

describe('the head (TL-3 of project 67, the testlist of 21/11): the limits note above the table, no «?» beside the buttons, the columns on the title row', () => {
    const PAC = 'tools.pacAllocator.planner.targets';
    const REB = 'tools.portfolioRebalancer.planner.targets';
    const TOOLS = [
        {profile: PAC_PLANNER_PROFILE, prefix: 'pac-planner', base: PAC, mountAs: null},
        {profile: REBALANCER_PLANNER_PROFILE, prefix: 'rebalancer-planner', base: REB, mountAs: REBALANCER_PLANNER_PROFILE},
    ] as const;
    const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    it('the note comes before the table: a title and four lines, the percent line with each Tool’s own figure', () => {
        for (const tool of TOOLS) {
            const {draft, brokerKey} = scenario(tool.profile);
            mount(tool.mountAs, draft, previewWith('ready', ready(brokerKey)));
            const note = screen.getByTestId(`${tool.prefix}-targets-limits-note`);
            const table = screen.getByTestId(`${tool.prefix}-targets-table`).querySelector('table') as HTMLTableElement;
            expect(note.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
            expect(note.querySelectorAll('li')).toHaveLength(4);
            expect(screen.getByTestId(`${tool.prefix}-targets-limits-percent`).textContent?.trim()).toBe(get(t)(`${tool.base}.limitsGuide.percentTotal`, {values: {total: formatExactMoneyPlain(TOTAL)}}));
            cleanup();

            // Before any preview the line has no figure.
            mount(tool.mountAs, draft, null);
            expect(screen.getByTestId(`${tool.prefix}-targets-limits-percent`).textContent?.trim()).toBe(get(t)(`${tool.base}.limitsGuide.percent`));
            cleanup();
        }
    });

    it('no «?» beside a button: the help is its description, and its tooltip once the pointer rests on it', async () => {
        for (const tool of TOOLS) {
            const {draft, brokerKey} = scenario(tool.profile);
            mount(tool.mountAs, draft, previewWith('ready', ready(brokerKey)));
            expect(screen.queryByTestId(`${tool.prefix}-distribution-help`)).toBeNull();
            const help = {
                [`${tool.prefix}-distribution-open`]: [get(t)(`${PAC}.copyDistribution`), get(t)(`${PAC}.copyHelp`)],
                [`${tool.prefix}-cash-entry-add`]: [get(t)(`${REB}.addCash`), get(t)(`${tool.base}.addCashHelp`)],
            };
            for (const [id, [name, text]] of Object.entries(help)) {
                const button = screen.getByTestId(id);
                expect(button.getAttribute('aria-label')).toBe(name);
                expect(document.getElementById(button.getAttribute('aria-describedby') ?? '')?.textContent).toBe(text);
                // No «?» in the button's group any more.
                expect(button.parentElement?.parentElement?.querySelector('button[aria-label^="' + name + ':"]')).toBeNull();
            }
            const copy = screen.getByTestId(`${tool.prefix}-distribution-open`);
            await fireEvent.mouseEnter(copy.parentElement as HTMLElement);
            const tip = await screen.findByRole('tooltip', {}, {timeout: 2000});
            expect(tip.textContent).toContain(help[`${tool.prefix}-distribution-open`][0]);
            expect(tip.textContent).toContain(help[`${tool.prefix}-distribution-open`][1]);
            await fireEvent.mouseLeave(copy.parentElement as HTMLElement);
            cleanup();
        }
    });

    it.each([
        ['cash-entry-add', 'cash-entry-dialog'],
        ['distribution-open', 'distribution'],
    ])('a click on %s acts and pins no tooltip over its dialog', async (button, dialog) => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
        await fireEvent.click(screen.getByTestId(`rebalancer-planner-${button}`));
        expect(screen.getByTestId(`rebalancer-planner-${dialog}`)).toBeTruthy();
        await wait(50);
        expect(screen.queryByRole('tooltip')).toBeNull();
    });

    it('a finger gets no tooltip: the tap acts, and no tooltip opens over the dialog after it', async () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
        const button = screen.getByTestId('rebalancer-planner-cash-entry-add');
        const wrapper = button.parentElement as HTMLElement;
        await fireEvent.pointerOver(button, {pointerType: 'touch'});
        await fireEvent.pointerDown(button, {pointerType: 'touch'});
        await fireEvent.touchStart(button);
        await fireEvent.touchEnd(button);
        expect(screen.queryByRole('tooltip')).toBeNull();
        // The browser's mouse events after a tap.
        await fireEvent.mouseEnter(wrapper);
        await fireEvent.click(button);
        expect(screen.getByTestId('rebalancer-planner-cash-entry-dialog')).toBeTruthy();
        await wait(700);
        expect(screen.queryByRole('tooltip')).toBeNull();
    });

    it('the columns button goes on the shell’s title row while the step has a table, and only its own piece leaves with it', () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        const slot = new StepTitleSlot();
        const inShell = () => {
            render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: TargetsStep, childProps: {draft, accountGeneration: 0, preview: previewWith('ready', ready(brokerKey))}}, context: new Map([[STEP_TITLE_CONTEXT, slot]])});
            flushSync();
        };
        inShell();
        expect(slot.action).not.toBeNull();
        // Not in the head: the shell draws it.
        expect(screen.queryByTestId('rebalancer-planner-targets-columns')).toBeNull();
        cleanup();
        expect(slot.action).toBeNull();

        // Another step's piece, put while this one was still mounted, stays when this one goes.
        inShell();
        const other = (() => {}) as unknown as NonNullable<StepTitleSlot['action']>;
        slot.hold(other);
        flushSync();
        cleanup();
        expect(slot.action).toBe(other);
        slot.action = null;

        // Without an Asset there is no table, so no columns button.
        const empty = new PlannerDraft('EUR', 'proportional', REBALANCER_PLANNER_PROFILE);
        render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: TargetsStep, childProps: {draft: empty, accountGeneration: 0, preview: null}}, context: new Map([[STEP_TITLE_CONTEXT, slot]])});
        flushSync();
        expect(slot.action).toBeNull();
        cleanup();

        // Mounted alone (no shell), the head keeps it.
        mount(REBALANCER_PLANNER_PROFILE, draft, null);
        expect(screen.getByTestId('rebalancer-planner-targets-columns')).toBeTruthy();
    });
});

describe('the limits check at once (TL-4 of project 67, the testlist of 21/11, row 7)', () => {
    const SUM_CODE = 'allocation.bounds_min_sum_exceeds_reference';
    type AppEvents = {events: {name: string; detail?: Record<string, unknown>}[]};

    function sumProblem(entityId: string, minimums: string, reference: string): PreviewReady['limit_problems'][number] {
        return {
            code: SUM_CODE,
            path: {kind: 'field', section: 'targets', entity_kind: 'asset', entity_id: entityId, field: 'minimum'},
            params: [
                {kind: 'money', name: 'minimums', value: {amount: minimums, currency: 'EUR'}},
                {kind: 'money', name: 'reference', value: {amount: reference, currency: 'EUR'}},
            ],
        } as unknown as PreviewReady['limit_problems'][number];
    }

    function appeared(): {name: string; detail?: Record<string, unknown>}[] {
        return ((window as unknown as {__lf: AppEvents}).__lf.events ?? []).filter((event) => event.name === 'planner.limit-problem.appeared');
    }

    async function typeMinimum(prefix: string, text: string): Promise<void> {
        await fireEvent.input(screen.getAllByTestId(`${prefix}-limit-minimum`)[0], {target: {value: text}});
        flushSync();
    }

    it('a minimum alone above the total: its line and the red field at once, before any new preview; gone when cleared', async () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
        await typeMinimum('rebalancer-planner', '20000');

        const line = within(screen.getByTestId('rebalancer-planner-targets-limits-problems')).getByTestId('rebalancer-planner-targets-limits-problem');
        expect(line.getAttribute('data-key')).toBe('limitMinimumAboveTotal');
        expect(line.textContent).toContain(get(t)('tools.portfolioRebalancer.planner.problems.limitMinimumAboveTotal', {values: {reference: formatExactMoneyPlain(TOTAL)}}));
        expect(screen.getAllByTestId('rebalancer-planner-limit-minimum')[0].getAttribute('aria-invalid')).toBe('true');
        expect(screen.getAllByTestId('rebalancer-planner-limit')[0].getAttribute('data-above-total')).toBe('true');

        await typeMinimum('rebalancer-planner', '');
        expect(screen.queryByTestId('rebalancer-planner-targets-limits-problems')).toBeNull();
        expect(screen.getAllByTestId('rebalancer-planner-limit-minimum')[0].getAttribute('aria-invalid')).toBe('false');
    });

    it('the sum of the minimums says its two figures, each Tool with its own words; the summary row’s minimums turn red', () => {
        for (const [profile, prefix, key] of [
            [REBALANCER_PLANNER_PROFILE, 'rebalancer-planner', `tools.portfolioRebalancer.planner.issues.${SUM_CODE}`],
            [PAC_PLANNER_PROFILE, 'pac-planner', `tools.pacAllocator.planner.issues.${SUM_CODE}`],
        ] as const) {
            const {draft, brokerKey} = scenario(profile);
            draft.setLimit('asset:probe', 'minimum', '20000');
            mount(profile, draft, previewWith('ready', {...ready(brokerKey), limit_problems: [sumProblem('asset:probe', '20000', '12345.67')]}));
            const lines = screen.getAllByTestId(`${prefix}-targets-limits-problem`);
            // The page's own line gives way to the preview's, which names the Asset in the sum.
            expect(lines.map((line) => line.getAttribute('data-key'))).toEqual(['bounds_min_sum_exceeds_reference']);
            expect(lines[0].textContent).toContain(get(t)(key, {values: {minimums: formatExactMoneyPlain({value: {kind: 'finite_decimal', value: '20000'}, currency: 'EUR'}), reference: formatExactMoneyPlain(TOTAL)}}));
            expect(screen.getByTestId(`${prefix}-targets-limits-sum-minimum`).getAttribute('data-over')).toBe('true');
            expect(screen.getAllByTestId(`${prefix}-limit-minimum`)[0].getAttribute('aria-invalid')).toBe('true');
            cleanup();
        }
    });

    it('the summary row: the targets, the minimums and the maximums together; red only on the backend’s verdict (trapped cash)', () => {
        const {draft, brokerKey} = scenario(PAC_PLANNER_PROFILE);
        const cash = draft.addCashEntry(brokerKey, 'EUR');
        draft.setLimit('asset:probe', 'minimum', '10%');
        draft.setLimit(cash.key, 'minimum', '12000');
        draft.setLimit('asset:probe', 'maximum', '500');
        // 10% of 12 345,67 + 12 000 = 13 234,567: above the total, but the cash entry's minimum is honoured by cash that
        // reaches no buy, and the backend names no problem. The row says the sum, not red.
        mount(PAC_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
        const minimum = screen.getByTestId('pac-planner-targets-limits-sum-minimum');
        expect(minimum.getAttribute('data-over')).toBe('false');
        expect(minimum.textContent).toContain(formatPlannerMoneyPlain('13234.57', 'EUR', {approx: true}));
        expect(screen.getByTestId('pac-planner-targets-limits-sum-maximum').textContent).toContain(formatPlannerMoneyPlain('500', 'EUR'));
        expect(screen.getByTestId('pac-planner-targets-total').textContent).toBe(formatPlannerPercentUnits(draft.targetTotal));
        expect(screen.queryByTestId('pac-planner-targets-limits-problems')).toBeNull();
    });

    it('the summary row says the cash without an entry today (P-24): under «Now», under the names on a phone; never in the PAC', () => {
        const otherCash = formatExactPercent({kind: 'finite_decimal', value: '0.12'}, 1);
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
        const line = screen.getByTestId('rebalancer-planner-targets-now-other-cash');
        expect(line.textContent).toBe(get(t)('tools.portfolioRebalancer.planner.targets.nowOtherCash', {values: {weight: otherCash}}));
        expect(line.closest('[data-testid="dt-footer-now"]')).not.toBeNull();
        cleanup();

        asPhone();
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
        flushSync();
        expect(screen.getByTestId('rebalancer-planner-targets-now-other-cash').closest('[data-testid="dt-footer-asset"]')).not.toBeNull();
        cleanup();
        vi.restoreAllMocks();

        const none = ready(brokerKey);
        none.items = none.items?.map((item) => (item.kind === 'other_cash' ? {...item, weight: {kind: 'finite_decimal' as const, value: '0'}} : item));
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', none));
        expect(screen.queryByTestId('rebalancer-planner-targets-now-other-cash')).toBeNull();
        cleanup();

        const pac = scenario(PAC_PLANNER_PROFILE);
        mount(PAC_PLANNER_PROFILE, pac.draft, previewWith('ready', ready(pac.brokerKey)));
        expect(screen.queryByTestId('pac-planner-targets-now-other-cash')).toBeNull();
    });

    it('while a preview is on its way and limits are typed, the summary row says the check is coming', () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('waiting', ready(brokerKey)));
        expect(screen.queryByTestId('rebalancer-planner-targets-limits-checking')).toBeNull();
        cleanup();

        draft.setLimit('asset:probe', 'maximum', '500');
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('waiting', ready(brokerKey)));
        expect(screen.getByTestId('rebalancer-planner-targets-limits-checking')).toBeTruthy();
        cleanup();

        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
        expect(screen.queryByTestId('rebalancer-planner-targets-limits-checking')).toBeNull();
    });

    it('a toast once per problem: typed digit by digit, then named by the preview, it raises one; not for one already there', async () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        const preview = previewWith('ready', ready(brokerKey));
        mount(REBALANCER_PLANNER_PROFILE, draft, preview);
        const before = appeared().length;
        for (const text of ['2', '20', '200', '2000', '20000', '200000']) await typeMinimum('rebalancer-planner', text);
        expect(appeared().length).toBe(before + 1);
        expect(appeared().at(-1)?.detail).toEqual({tool: 'rebalancer', key: 'limitMinimumAboveTotal'});

        preview.numbers = {...ready(brokerKey), limit_problems: [sumProblem('asset:probe', '200000', '12345.67')]};
        flushSync();
        expect(screen.getAllByTestId('rebalancer-planner-targets-limits-problem').map((line) => line.getAttribute('data-key'))).toEqual(['bounds_min_sum_exceeds_reference']);
        expect(appeared().length).toBe(before + 1);

        // Gone, then back: a new toast.
        preview.numbers = ready(brokerKey);
        await typeMinimum('rebalancer-planner', '');
        await typeMinimum('rebalancer-planner', '30000');
        expect(appeared().length).toBe(before + 2);
        cleanup();

        // Back on the step with the problem already there: nothing.
        const again = appeared().length;
        mount(REBALANCER_PLANNER_PROFILE, draft, previewWith('ready', ready(brokerKey)));
        expect(screen.getByTestId('rebalancer-planner-targets-limits-problems')).toBeTruthy();
        expect(appeared().length).toBe(again);
    });
});
