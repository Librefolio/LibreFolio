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

import {cleanup, render, screen, setupI18n} from '$test/component';
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
});

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
});
