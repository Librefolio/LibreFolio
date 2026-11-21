// @vitest-environment jsdom
/**
 * PositionsTable (F3a of project 67, step 5, the Rebalancer): an Asset's positions under its card, Broker by Broker.
 *
 * One row per position, in the project's `DataTable`. The quantity is the user's to change: an edit reaches the draft and
 * the row's badge turns from «copied» to «modified». The units in custody are personal: masked in privacy mode, and the
 * cell follows the switch both ways. A shared account also shows the user's share. Driven through test ids; nothing
 * reads translated text.
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
import {PlannerDraft, type DraftPosition} from '../draft.svelte';
import {fractionToPercent} from '$lib/utils/core/exactDecimal';
import {formatPlannerPercentUnits, formatPlannerQuantity} from '../format';
import PositionsTable from './PositionsTable.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

const ASSET = 'asset:11';

function position(broker: number, custody: string, share: string, quantity: string, accessRole: string | null = 'OWNER'): DraftPosition {
    return {
        key: `holding:asset:11:broker:${broker}`,
        assetKey: ASSET,
        brokerKey: `broker:${broker}`,
        sourceBrokerId: broker,
        brokerName: `Broker ${broker}`,
        brokerIconUrl: null,
        custody,
        ownershipShare: share,
        accessRole,
        quantity,
        copiedQuantity: quantity,
        stamp: {copyId: 'copy:1', provenanceId: 'source:portfolio-ledger'},
        enteredAt: '2026-11-14T10:00:00.000Z',
    };
}

function mount(): PlannerDraft {
    const draft = new PlannerDraft('EUR', 'proportional');
    draft.data.positions.push(position(7, '1234', '1', '1234'), position(8, '12', '0.5', '6', 'EDITOR'), {...position(9, '3', '1', '3'), assetKey: 'asset:99'});
    render(PositionsTable, {draft, assetKey: ASSET, assetLabel: 'Apple'});
    flushSync();
    return draft;
}

const cells = () => screen.getAllByTestId('pac-planner-position-quantity-cell');
const cell = (broker: number) => cells().find((item) => item.getAttribute('data-position-key') === `holding:asset:11:broker:${broker}`) as HTMLElement;

describe('PositionsTable', () => {
    it("lists the Asset's positions only, one row per Broker", () => {
        mount();

        expect(screen.getByTestId('pac-planner-positions').getAttribute('data-asset-key')).toBe(ASSET);
        expect(cells().map((item) => item.getAttribute('data-position-key'))).toEqual(['holding:asset:11:broker:7', 'holding:asset:11:broker:8']);
        expect((within(cell(8)).getByTestId('pac-planner-position-quantity') as HTMLInputElement).value).toBe('6');
        expect(within(cell(8)).getByTestId('pac-planner-position-origin').getAttribute('data-modified')).toBe('false');
    });

    it('an edited quantity reaches the draft and reads modified', async () => {
        const draft = mount();

        await fireEvent.input(within(cell(8)).getByTestId('pac-planner-position-quantity'), {target: {value: '4'}});
        flushSync();

        expect(draft.positionsOf(ASSET).find((item) => item.sourceBrokerId === 8)?.quantity).toBe('4');
        expect(within(cell(8)).getByTestId('pac-planner-position-origin').getAttribute('data-modified')).toBe('true');
        expect(within(cell(7)).getByTestId('pac-planner-position-origin').getAttribute('data-modified')).toBe('false');
    });

    it('the quantities are masked in privacy mode, the field included, both ways', async () => {
        mount();
        const table = screen.getByTestId('pac-planner-positions');
        const shown = formatPlannerQuantity('1234');
        expect(table.textContent).toContain(shown);

        setPrivacyEnabled(true);
        flushSync();
        await tick();
        expect(table.textContent).toContain(PRIVACY_PLACEHOLDER);
        expect(table.textContent).not.toContain(shown);
        // The quantity field is a quantity in clear: it gives way to the masked text (an input's value is not textContent).
        expect(screen.queryAllByTestId('pac-planner-position-quantity')).toHaveLength(0);
        expect(within(cell(7)).getByTestId('pac-planner-position-quantity-masked').textContent).toContain(PRIVACY_PLACEHOLDER);

        setPrivacyEnabled(false);
        flushSync();
        await tick();
        expect(table.textContent).toContain(shown);
        expect((within(cell(7)).getByTestId('pac-planner-position-quantity') as HTMLInputElement).value).toBe('1234');
    });

    it("a shared account shows the user's share as the broker page's badge: its percentage and its role; a whole one shows none", () => {
        mount();
        // R1-D of project 67 (the developer, 20/11: «la quota del conto come badge con la corona e la percentuale,
        // similmente a come avviene in broker detail»).
        const badges = screen.getAllByTestId('pac-planner-position-quota');
        expect(badges.map((badge) => badge.getAttribute('data-position-key'))).toEqual(['holding:asset:11:broker:8']);
        expect(badges[0].getAttribute('data-role')).toBe('EDITOR');
        expect(badges[0].textContent).toContain(formatPlannerPercentUnits(fractionToPercent('0.5')));
        expect(badges[0].querySelector('svg')).not.toBeNull();
        // The custody column says the units only: the share is the badge's.
        const custody = screen.getAllByText(formatPlannerQuantity('12'), {exact: false});
        expect(custody.every((node) => !node.textContent?.includes(formatPlannerPercentUnits(fractionToPercent('0.5'))))).toBe(true);
    });

    it('a share with no role shows its percentage alone, never a crown', () => {
        const draft = new PlannerDraft('EUR', 'proportional');
        draft.data.positions.push(position(8, '12', '0.5', '6', null));
        render(PositionsTable, {draft, assetKey: ASSET, assetLabel: 'Apple'});
        flushSync();
        const badge = screen.getByTestId('pac-planner-position-quota');
        expect(badge.hasAttribute('data-role')).toBe(false);
        expect(badge.textContent).toContain(formatPlannerPercentUnits(fractionToPercent('0.5')));
        expect(badge.querySelector('svg')).toBeNull();
    });

    it('nothing is shown for an Asset without positions', () => {
        const draft = new PlannerDraft('EUR', 'proportional');
        render(PositionsTable, {draft, assetKey: ASSET, assetLabel: 'Apple'});
        flushSync();
        expect(screen.queryByTestId('pac-planner-positions')).toBeNull();
    });
});
