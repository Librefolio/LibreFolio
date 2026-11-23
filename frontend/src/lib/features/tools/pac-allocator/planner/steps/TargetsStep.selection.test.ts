// @vitest-environment jsdom
/**
 * The targets table on the selection panel (plan 77, SEL-D3). The step's head holds the intro, then the table's selection
 * bar, then the step's own buttons («Balance all», «Copy current distribution», …): the table draws the head and hands
 * it the bar, as the sections of SEL-D2 do. «Balance the selected rows to 100%» acts on the ticked rows that have a
 * target, with their number (a PAC cash row is not counted); every row ticked balances as «Balance all». With the total
 * already at 100 % there is nothing to balance, so it is not offered (Q-SEL-17). It is off, and says why, with a target
 * that is not a number, or when the rows not ticked add up to 100 % or more. Mounted below a Tool wrapper in miniature
 * (`../../__tests__/ProfileHarness.svelte`); driven through test ids, never through translated text.
 */
import {flushSync} from 'svelte';
import {get} from 'svelte/store';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {t} from '$lib/i18n';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PlannerDraft, type DraftAsset} from '../draft.svelte';
import {PlannerPreview, type PreviewReady} from '../preview.svelte';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE} from '../profile';
import TargetsStep from './TargetsStep.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

function asset(key: string, name: string): DraftAsset {
    return {
        key,
        origin: 'manual',
        sourceAssetId: null,
        name,
        ticker: '',
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
}

/** Three Assets of the PAC with the given targets, in this order. */
function mount(targets: [string, string, string]): PlannerDraft {
    const draft = new PlannerDraft('EUR', 'proportional', PAC_PLANNER_PROFILE);
    ['a', 'b', 'c'].forEach((id, index) => {
        draft.addAsset(asset(`asset:${id}`, `ETF ${id}`));
        draft.data.targets[`asset:${id}`] = targets[index];
    });
    render(ProfileHarness, {props: {profile: PAC_PLANNER_PROFILE, child: TargetsStep, childProps: {draft, accountGeneration: 0}}});
    flushSync();
    return draft;
}

/** A ready preview where the cash without an entry (`other_cash`) is worth something today: never a row (TL-2). */
function otherCashWorthToday(): PlannerPreview {
    const preview = new PlannerPreview({call: vi.fn(), blocked: () => false});
    preview.state = 'ready';
    preview.numbers = otherCashWorth('50');
    return preview;
}

/** The preview's figures with the cash without an entry worth `amount` today. */
function otherCashWorth(amount: string): PreviewReady {
    const money = {value: {kind: 'finite_decimal' as const, value: amount}, currency: 'EUR'};
    return {
        operation: 'preview',
        result_state: 'preview_ready',
        availability: 'ready',
        valuation_currency: 'EUR',
        total: money,
        issues: [],
        limit_problems: [],
        items: [{kind: 'other_cash', value: money, weight: {kind: 'finite_decimal', value: '0.1'}}],
    };
}

const tick = (key: string) => fireEvent.click(screen.getByTestId(`dt-row-checkbox-${key}`));
/** -1 when `a` comes before `b` in the document. */
const order = (a: Element, b: Element) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1);

describe('the targets table on the selection panel (77 SEL-D3)', () => {
    it('ticked rows put the bar in the step head, before «Balance all»; the action takes them with their number', async () => {
        const draft = mount(['50', '30', '0']);
        await tick('asset:a');
        await tick('asset:b');

        const step = screen.getByTestId('pac-planner-targets');
        const bar = within(step).getByTestId('selection-toolbar');
        expect(bar).toHaveAttribute('data-in-head', 'true');
        expect(order(within(step).getByTestId('pac-planner-targets-intro'), bar)).toBe(-1);
        expect(order(bar, within(step).getByTestId('pac-planner-targets-balance-all'))).toBe(-1);
        // One bar only: the table has none of its own above the rows
        expect(within(step).getAllByTestId('selection-toolbar')).toHaveLength(1);
        expect(within(bar).getByTestId('toolbar-action-balance-selected-count').textContent?.trim()).toBe('2');

        // 20 % missing: the two ticked rows grow, keeping their ratio (50:30), and the total is 100
        await fireEvent.click(within(bar).getByTestId('toolbar-action-balance-selected'));
        expect(draft.data.targets['asset:a']).toBe('62.5');
        expect(draft.data.targets['asset:b']).toBe('37.5');
        expect(draft.data.targets['asset:c']).toBe('0');
        await waitFor(() => expect(within(step).queryByTestId('selection-toolbar')).toBeNull());
    });

    it('with every row ticked the action is offered, and balances as «Balance all» does', async () => {
        const draft = mount(['50', '30', '0']);
        for (const id of ['a', 'b', 'c']) await tick(`asset:${id}`);
        const bar = screen.getByTestId('selection-toolbar');
        const action = within(bar).getByTestId('toolbar-action-balance-selected');
        expect(action).not.toHaveAttribute('aria-disabled');
        expect(within(bar).getByTestId('toolbar-action-balance-selected-count').textContent?.trim()).toBe('3');
        await fireEvent.click(action);
        expect(['a', 'b', 'c'].map((id) => draft.data.targets[`asset:${id}`])).toEqual(['62.5', '37.5', '0']);
    });

    it('a row with no target of its own (a PAC cash row) is not counted, and alone gets no action', async () => {
        const draft = new PlannerDraft('EUR', 'proportional', PAC_PLANNER_PROFILE);
        const broker = draft.addManualBroker('Broker probe');
        draft.addAsset(asset('asset:a', 'ETF a'));
        draft.data.targets['asset:a'] = '50';
        const entry = draft.addCashEntry(broker.key, 'EUR');
        render(ProfileHarness, {props: {profile: PAC_PLANNER_PROFILE, child: TargetsStep, childProps: {draft, accountGeneration: 0}}});
        flushSync();

        await tick(entry.key);
        expect(within(screen.getByTestId('selection-toolbar')).queryByTestId('toolbar-action-balance-selected')).toBeNull();
        await tick('asset:a');
        const bar = screen.getByTestId('selection-toolbar');
        expect(within(bar).getByTestId('toolbar-action-balance-selected-count').textContent?.trim()).toBe('1');
    });

    it('the Rebalancer has no row to tick for the cash without an entry, whatever it is worth today (TL-2)', () => {
        const draft = new PlannerDraft('EUR', 'proportional', REBALANCER_PLANNER_PROFILE);
        draft.addManualBroker('Broker probe');
        draft.addManualAccount({name: 'Bank probe', currency: 'CHF', available: '100', selected: '50'});
        draft.addAsset(asset('asset:a', 'ETF a'));
        draft.data.targets['asset:a'] = '50';
        render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: TargetsStep, childProps: {draft, accountGeneration: 0, preview: otherCashWorthToday()}}});
        flushSync();
        expect(screen.queryByTestId('dt-row-checkbox-other-cash')).toBeNull();
        expect(screen.getByTestId('dt-row-checkbox-asset:a')).toBeInTheDocument();
    });

    it('with the total at 100 % there is nothing to balance: the action is not offered', async () => {
        mount(['50', '50', '0']);
        await tick('asset:a');
        const bar = screen.getByTestId('selection-toolbar');
        expect(within(bar).queryByTestId('toolbar-action-balance-selected')).toBeNull();
    });

    it('with a target that is not a number the action is off, and its reason opens on focus', async () => {
        mount(['50', 'abc', '0']);
        await tick('asset:a');
        const action = within(screen.getByTestId('selection-toolbar')).getByTestId('toolbar-action-balance-selected');
        expect(action).toHaveAttribute('aria-disabled', 'true');
        action.focus();
        const tip = await screen.findByTestId('tooltip-content');
        expect(tip.textContent?.trim()).toBe(get(t)('tools.pacAllocator.planner.targets.balanceNotNumber'));
    });

    it('with the rows not ticked at exactly 100 % the balancing would only empty the ticked ones: off, with the same reason', async () => {
        const draft = mount(['60', '40', '10']);
        await tick('asset:c');
        const action = within(screen.getByTestId('selection-toolbar')).getByTestId('toolbar-action-balance-selected');
        expect(action).toHaveAttribute('aria-disabled', 'true');
        await fireEvent.click(action);
        expect(draft.data.targets['asset:c'], 'an action that is off changes nothing').toBe('10');
        action.focus();
        const tip = await screen.findByTestId('tooltip-content');
        expect(tip.textContent?.trim()).toBe(get(t)('tools.pacAllocator.planner.targets.balanceNoRoom'));
    });

    it('with the rows not ticked already above 100 % the ticked ones have no room: the action is off, and says why', async () => {
        mount(['80', '40', '0']);
        await tick('asset:c');
        const action = within(screen.getByTestId('selection-toolbar')).getByTestId('toolbar-action-balance-selected');
        expect(action).toHaveAttribute('aria-disabled', 'true');
        action.focus();
        const tip = await screen.findByTestId('tooltip-content');
        expect(tip.textContent?.trim()).toBe(get(t)('tools.pacAllocator.planner.targets.balanceNoRoom'));
    });
});

describe('the row menu of a target (77 SEL-M)', () => {
    async function openRowMenu(key: string): Promise<HTMLElement> {
        const kebab = screen.getByTestId(`row-actions-${key}`);
        // jsdom has no layout: a menu anchored on a ⋮ of no size closes at once
        vi.spyOn(kebab, 'getBoundingClientRect').mockReturnValue(new DOMRect(10, 10, 24, 24));
        await fireEvent.click(kebab);
        return screen.findByTestId('context-menu');
    }

    it('at a total of 100 % «Balance to 100%» is not offered: an Asset row has no other action, so no ⋮ either', async () => {
        mount(['50', '50', '0']);
        expect(screen.queryByTestId('row-actions-asset:a')).toBeNull();
        expect(screen.queryByTestId('pac-planner-target-balance')).toBeNull();
    });

    it('with a target that is not a number «Balance to 100%» is offered: the field counts 0, in the total as here', async () => {
        const draft = mount(['50', 'abc', '0']);
        const menu = await openRowMenu('asset:a');
        const balance = within(menu).getByTestId('pac-planner-target-balance');
        expect(balance).not.toHaveAttribute('aria-disabled');
        await fireEvent.click(balance);
        expect(draft.data.targets['asset:a']).toBe('100');
    });
});
