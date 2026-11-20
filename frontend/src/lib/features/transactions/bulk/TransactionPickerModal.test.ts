// @vitest-environment jsdom
/**
 * TransactionPickerModal — the optional props of lot F4 (project 66). RED FIRST: `rows`, `title`, `filterLabel`,
 * `addLabel`, `maxSelect` and `zIndex` do not exist yet; the last test guards the behaviour without them.
 *
 * Handles: the rows by `tr[data-row-id="tx-<id>"]`, a row's checkbox by `dt-row-checkbox-tx-<id>`, the picker's own
 * `tx-picker-modal`, `tx-picker-filter-label`, `tx-picker-add`. No translated text is asserted: the labels the test
 * passes are unique markers.
 *
 * Doubt: `filterLabel` is assumed to render BOTH strings in the DOM (short below `sm`, long from `sm`, by responsive
 * classes), so the test reads the element's text content. If the component renders only one, adapt the assertion.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (property === 'list_currencies_api_v1_utilities_currencies_get') {
                    return vi.fn(async () => ({items: [{code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []}]}));
                }
                if (property === 'list_assets_api_v1_assets_query_get') return vi.fn(async () => []);
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import {ensureCurrenciesLoaded} from '$lib/stores/reference/currencyStore';
import {mergeBrokers, resetBrokerStore} from '$lib/stores/reference/brokerStore';
import {txStoreSetAll} from '$lib/features/transactions/txStore.svelte';
import type {TXReadItem} from '../types';
import TransactionPickerModal from './TransactionPickerModal.svelte';

const OWNED = {id: 61, name: 'F4 picker broker', portal_url: 'https://picker.example.com', icon_url: null, default_import_plugin: null, user_role: 'OWNER'};
const base = {asset_id: null, quantity: '0', asset_event_id: null, tags: [], description: null, broker_id: OWNED.id, date: '2026-03-10', related_transaction_id: null};

const FEE_A: TXReadItem = {...base, id: 9101, type: 'FEE', cash: {code: 'EUR', amount: '-1.00'}};
const FEE_B: TXReadItem = {...base, id: 9102, type: 'FEE', cash: {code: 'EUR', amount: '-2.00'}};
const STORE_DEPOSIT: TXReadItem = {...base, id: 9103, type: 'DEPOSIT', cash: {code: 'EUR', amount: '50.00'}};
const FX_GIVER: TXReadItem = {...base, id: 9104, type: 'FX_CONVERSION', cash: {code: 'EUR', amount: '-100.00'}, related_transaction_id: 9105};
const FX_RECEIVER: TXReadItem = {...base, id: 9105, type: 'FX_CONVERSION', cash: {code: 'EUR', amount: '109.00'}, related_transaction_id: 9104};

const rowOf = (id: number) => document.querySelector(`tr[data-row-id="tx-${id}"]`);
const checkbox = (id: number) => screen.getByTestId(`dt-row-checkbox-tx-${id}`);

function mount(props: Record<string, unknown> = {}) {
    const onAdd = vi.fn();
    const onClose = vi.fn();
    render(TransactionPickerModal, {open: true, excludeIds: new Set<number>(), onAdd, onClose, ...props});
    return {onAdd, onClose};
}

beforeAll(async () => {
    await setupI18n();
    await ensureCurrenciesLoaded();
});

beforeEach(() => {
    mergeBrokers([{...OWNED}]);
    txStoreSetAll([STORE_DEPOSIT, FX_GIVER, FX_RECEIVER], []);
});

afterEach(() => {
    cleanup();
    resetBrokerStore();
    txStoreSetAll([], []);
});

describe('TransactionPickerModal — rows', () => {
    it('lists the given rows and not the store rows', async () => {
        mount({rows: [FEE_A, FEE_B]});
        await screen.findByTestId(`dt-row-checkbox-tx-${FEE_A.id}`);
        expect(rowOf(FEE_A.id)).not.toBeNull();
        expect(rowOf(FEE_B.id)).not.toBeNull();
        expect(rowOf(STORE_DEPOSIT.id)).toBeNull();
    });

    it('still filters the given rows by excludeIds', async () => {
        mount({rows: [FEE_A, FEE_B], excludeIds: new Set([FEE_B.id])});
        await screen.findByTestId(`dt-row-checkbox-tx-${FEE_A.id}`);
        expect(rowOf(FEE_B.id)).toBeNull();
    });
});

describe('TransactionPickerModal — labels and layer', () => {
    it('title replaces the header text', async () => {
        mount({rows: [FEE_A], title: 'F4-TITLE-MARKER'});
        await screen.findByTestId('tx-picker-content');
        expect(screen.getByTestId('tx-picker-content').textContent).toContain('F4-TITLE-MARKER');
    });

    it('filterLabel publishes the short and the long text in tx-picker-filter-label', async () => {
        mount({rows: [FEE_A], filterLabel: {short: 'F4-SHORT', long: 'F4-LONG-LABEL'}});
        const label = await screen.findByTestId('tx-picker-filter-label');
        expect(label.textContent).toContain('F4-SHORT');
        expect(label.textContent).toContain('F4-LONG-LABEL');
    });

    it('addLabel replaces the Add button text with the selected count', async () => {
        mount({rows: [FEE_A, FEE_B], addLabel: (n: number) => `F4-ADD-${n}`});
        await fireEvent.click(await screen.findByTestId(`dt-row-checkbox-tx-${FEE_A.id}`));
        const add = screen.getByTestId('tx-picker-add');
        expect(add.textContent).toContain('F4-ADD-1');
        expect(add.getAttribute('title')).toBe('F4-ADD-1');
    });

    it('zIndex reaches the modal layer', async () => {
        mount({rows: [FEE_A], zIndex: 90});
        const modal = await screen.findByTestId('tx-picker-modal');
        expect(modal.style.zIndex).toBe('90');
    });
});

describe('TransactionPickerModal — selection', () => {
    it('maxSelect 1 enables Add only with exactly one row selected', async () => {
        mount({rows: [FEE_A, FEE_B], maxSelect: 1});
        const add = await screen.findByTestId('tx-picker-add');
        expect(add).toBeDisabled();
        await fireEvent.click(checkbox(FEE_A.id));
        expect(add).toBeEnabled();
        await fireEvent.click(checkbox(FEE_B.id));
        expect(add).toBeDisabled();
        await fireEvent.click(checkbox(FEE_B.id));
        expect(add).toBeEnabled();
    });

    it('Add hands onAdd exactly the selected rows', async () => {
        const {onAdd} = mount({rows: [FEE_A, FEE_B]});
        await fireEvent.click(await screen.findByTestId(`dt-row-checkbox-tx-${FEE_A.id}`));
        await fireEvent.click(screen.getByTestId('tx-picker-add'));
        expect(onAdd).toHaveBeenCalledTimes(1);
        expect(onAdd.mock.calls[0][0].map((r: TXReadItem) => r.id)).toEqual([FEE_A.id]);
    });

    it('with rows, a paired row never auto-adds its partner', async () => {
        const {onAdd} = mount({rows: [FX_GIVER]});
        await fireEvent.click(await screen.findByTestId(`dt-row-checkbox-tx-${FX_GIVER.id}`));
        await fireEvent.click(screen.getByTestId('tx-picker-add'));
        expect(onAdd.mock.calls[0][0].map((r: TXReadItem) => r.id)).toEqual([FX_GIVER.id]);
    });
});

describe('TransactionPickerModal — without the new props', () => {
    it('lists the store rows, has no filter label, and auto-adds the partner of a pair', async () => {
        const {onAdd} = mount();
        await screen.findByTestId(`dt-row-checkbox-tx-${STORE_DEPOSIT.id}`);
        expect(rowOf(FEE_A.id)).toBeNull();
        expect(screen.queryByTestId('tx-picker-filter-label')).toBeNull();
        await fireEvent.click(checkbox(FX_GIVER.id));
        await fireEvent.click(screen.getByTestId('tx-picker-add'));
        expect(onAdd.mock.calls[0][0].map((r: TXReadItem) => r.id).sort()).toEqual([FX_GIVER.id, FX_RECEIVER.id]);
    });
});
