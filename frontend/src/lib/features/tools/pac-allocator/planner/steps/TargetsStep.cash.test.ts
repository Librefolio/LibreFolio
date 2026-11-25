// @vitest-environment jsdom
/**
 * The targets table with cash entries (F3a of project 67, step 7; M3, M12, mockup screen 5).
 *
 * Under the Rebalancer's profile the targets table holds the Assets and the cash entries in one `DataTable`: «Add a cash
 * entry» offers the scenario's Broker × currency pairs; a cash row has the cash icon (the Broker's logo with the currency's
 * circle), a target and the limits of F2, and the total counts it. The cash without a target of its own has no row (TL-2):
 * the plan counts it, the table does not show it. Under the PAC's profile none of this exists in F3a. Mounted below a Tool wrapper in miniature
 * (`../../__tests__/ProfileHarness.svelte`); driven through test ids.
 */
import {flushSync, tick} from 'svelte';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PlannerDraft, cashEntryKey, type DraftAsset} from '../draft.svelte';
import {PlannerPreview, type PreviewReady} from '../preview.svelte';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE, type PlannerProfile} from '../profile';
import TargetsStep from './TargetsStep.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

/** An operative Broker buying in EUR, a manual account holding CHF, one Asset at 90 %. */
function scenario(profile: PlannerProfile) {
    const draft = new PlannerDraft('EUR', 'proportional', profile);
    const broker = draft.addManualBroker('Broker probe');
    draft.addManualAccount({name: 'Bank probe', currency: 'CHF', available: '100', selected: '50'});
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

function mount(profile: PlannerProfile | null, draft: PlannerDraft, preview: PlannerPreview | null = null): void {
    render(ProfileHarness, {props: {profile, child: TargetsStep, childProps: {draft, accountGeneration: 0, preview}}});
    flushSync();
}

/** A ready preview where the cash without an entry (`other_cash`) is worth something today. */
function otherCashWorthToday(): PlannerPreview {
    const money = {value: {kind: 'finite_decimal' as const, value: '50'}, currency: 'EUR'};
    const numbers: PreviewReady = {
        operation: 'preview',
        result_state: 'preview_ready',
        availability: 'ready',
        valuation_currency: 'EUR',
        total: money,
        issues: [],
        limit_problems: [],
        items: [{kind: 'other_cash', value: money, weight: {kind: 'finite_decimal', value: '0.1'}}],
    };
    const preview = new PlannerPreview({call: vi.fn(), blocked: () => false});
    preview.state = 'ready';
    preview.numbers = numbers;
    return preview;
}

describe('the targets table and the cash entries', () => {
    it('the Rebalancer adds a cash entry as a row with a target, counted in the total', async () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        mount(REBALANCER_PLANNER_PROFILE, draft);

        await fireEvent.click(screen.getByTestId('rebalancer-planner-cash-entry-add'));
        const dialog = screen.getByTestId('rebalancer-planner-cash-entry-dialog');
        expect(
            within(dialog)
                .getAllByTestId('rebalancer-planner-cash-entry-choice')
                .map((choice) => choice.getAttribute('data-currency')),
        ).toEqual(['EUR', 'CHF']);
        const eur = within(dialog)
            .getAllByTestId('rebalancer-planner-cash-entry-choice')
            .find((choice) => choice.getAttribute('data-currency') === 'EUR') as HTMLElement;
        await fireEvent.click(eur);
        flushSync();
        await tick();

        expect(draft.data.cashEntries.map((entry) => entry.key)).toEqual([cashEntryKey(brokerKey, 'EUR')]);
        expect(screen.queryByTestId('rebalancer-planner-cash-entry-dialog')).toBeNull();
        const inputs = screen.getAllByTestId('rebalancer-planner-target-input');
        expect(inputs).toHaveLength(2);
        await fireEvent.input(inputs[1], {target: {value: '10'}});
        flushSync();

        expect(draft.data.targets[cashEntryKey(brokerKey, 'EUR')]).toBe('10');
        expect(screen.getByTestId('rebalancer-planner-targets-control').getAttribute('data-state')).toBe('balanced');
        // The cash row has the limits of F2, under the entry's key.
        expect(screen.getAllByTestId('rebalancer-planner-limit').map((cell) => cell.getAttribute('data-asset-key'))).toEqual(['asset:probe', cashEntryKey(brokerKey, 'EUR')]);
    });

    it('a cash row is removed from its row action', async () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        const entry = draft.addCashEntry(brokerKey, 'EUR');
        draft.data.targets[entry.key] = '10';
        mount(REBALANCER_PLANNER_PROFILE, draft);

        // Only the cash row's menu offers the removal. jsdom has no layout: the menu closes on an anchor of no size.
        const kebab = screen.getByTestId(`row-actions-${entry.key}`);
        vi.spyOn(kebab, 'getBoundingClientRect').mockReturnValue(new DOMRect(10, 10, 24, 24));
        await fireEvent.click(kebab);
        flushSync();
        await fireEvent.click(await screen.findByTestId('rebalancer-planner-cash-entry-remove'));
        flushSync();

        expect(draft.data.cashEntries).toEqual([]);
        expect(draft.data.targets).not.toHaveProperty(entry.key);
        expect(screen.getAllByTestId('rebalancer-planner-target-input')).toHaveLength(1);
    });

    it('a right click on a cash row opens its menu on a desktop, and a target field keeps the browser menu (81 U15)', async () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        const entry = draft.addCashEntry(brokerKey, 'EUR');
        draft.data.targets[entry.key] = '10';
        mount(REBALANCER_PLANNER_PROFILE, draft);

        const input = screen.getAllByTestId('rebalancer-planner-target-input')[1];
        expect(await fireEvent.contextMenu(input)).toBe(true);
        expect(screen.queryByTestId('context-menu')).toBeNull();

        const row = document.querySelector(`tr[data-row-id="${entry.key}"]`) as HTMLElement;
        expect(await fireEvent.contextMenu(row)).toBe(false);
        const menu = screen.getByTestId('context-menu');
        expect(within(menu).getByTestId('rebalancer-planner-cash-entry-remove')).toBeTruthy();
    });

    it('cash with no entry, worth something today, has no row: the plan counts it, the table does not show it (TL-2)', () => {
        const {draft} = scenario(REBALANCER_PLANNER_PROFILE);
        mount(REBALANCER_PLANNER_PROFILE, draft, otherCashWorthToday());

        expect(screen.queryByTestId('dt-row-checkbox-other-cash')).toBeNull();
        // The Asset alone: one target field, one limits cell, one row.
        expect(screen.getAllByTestId('rebalancer-planner-target-input')).toHaveLength(1);
        expect(screen.getAllByTestId('rebalancer-planner-limit')).toHaveLength(1);
        expect(screen.getAllByTestId('rebalancer-planner-target-bar')).toHaveLength(1);
    });

    it('the PAC adds cash rows with limits only: no target, outside the total (step 14, U8)', async () => {
        const {draft, brokerKey} = scenario(PAC_PLANNER_PROFILE);
        mount(null, draft);

        await fireEvent.click(screen.getByTestId('pac-planner-cash-entry-add'));
        const dialog = screen.getByTestId('pac-planner-cash-entry-dialog');
        const eur = within(dialog)
            .getAllByTestId('pac-planner-cash-entry-choice')
            .find((choice) => choice.getAttribute('data-currency') === 'EUR') as HTMLElement;
        await fireEvent.click(eur);
        flushSync();
        await tick();

        const key = cashEntryKey(brokerKey, 'EUR');
        expect(draft.data.cashEntries.map((entry) => entry.key)).toEqual([key]);
        // The row has its limits and no target field; the total stays the Assets'.
        expect(screen.getAllByTestId('pac-planner-limit').map((cell) => cell.getAttribute('data-asset-key'))).toContain(key);
        expect(screen.getAllByTestId('pac-planner-target').map((cell) => cell.getAttribute('data-asset-key'))).toEqual(['asset:probe']);
        expect(draft.targetTotal).toBe('90');
    });
});
