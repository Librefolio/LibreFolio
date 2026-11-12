// @vitest-environment jsdom
/**
 * AssetBulkEditModal — component test (Vitest + jsdom). Lane 65, lot F3, step «Campi».
 *
 * What it pins (no assertion reads a translated text; the figures come from `data-*` attributes and test ids):
 * - at rest: the three zones, the selected assets, «Continue» off, nothing marked modified, `data-step="fields"`;
 * - a three-state control (`leave`, `yes`, `no`) publishes `data-state`, a touched field takes its chip and its Undo,
 *   and Undo puts it back to «leave»; the header's Undo-all clears every field;
 * - «Continue» turns on only when saving would change at least one asset: choosing a value every asset already has
 *   leaves it off (the impact line says 0 change);
 * - the unit: a value that is not a whole number from 1 shows the error and keeps «Continue» off, even when another
 *   field would turn it on; a valid one goes out in the payload;
 * - the type is chosen through the same two-level select as the single modal;
 * - «Continue» hands the draft and the items (only the fields that change for each asset) to `oncontinue`;
 * - a new opening starts clean.
 * Responsive layout is not checked here (jsdom has no layout): the E2E at 375 px does it (lot E1).
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import AssetBulkEditModal from './AssetBulkEditModal.svelte';
import type {BulkAsset} from './assetBulkEdit';

beforeAll(async () => {
    await setupI18n();
});

function asset(id: number, over: Partial<BulkAsset> = {}): BulkAsset {
    return {id, display_name: `Bulk asset ${id}`, asset_type: 'ETF', active: true, is_benchmark: false, quote_base_quantity: 1, icon_url: null, user_url: null, ...over};
}

const SELECTION: BulkAsset[] = [asset(1), asset(2, {is_benchmark: true}), asset(3, {asset_type: 'ETF_STOCK'}), asset(4, {asset_type: 'CROWDFUND_REAL_ESTATE'}), asset(5, {active: false})];

function mount(over: Record<string, unknown> = {}) {
    const oncontinue = vi.fn();
    const onclose = vi.fn();
    const view = render(AssetBulkEditModal, {open: true, assets: SELECTION, oncontinue, onclose, ...over});
    return {oncontinue, onclose, ...view};
}

const root = () => screen.getByTestId('asset-bulk-edit');
const cont = () => screen.getByTestId('asset-bulk-continue') as HTMLButtonElement;

describe('AssetBulkEditModal — at rest', () => {
    it('shows the three zones in order, the selection, and nothing modified', () => {
        mount();
        expect(root()).toHaveAttribute('data-step', 'fields');
        expect(root()).toHaveAttribute('data-modified', '0');
        expect(root()).toHaveAttribute('data-selected', '5');
        const zones = ['asset-bulk-zone-details', 'asset-bulk-zone-classification', 'asset-bulk-zone-price'].map((id) => screen.getByTestId(id));
        for (let i = 1; i < zones.length; i++) expect(zones[i - 1].compareDocumentPosition(zones[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
        expect(screen.getAllByTestId('asset-bulk-selected-chip')).toHaveLength(4);
        expect(screen.queryByTestId('asset-bulk-reset-all')).toBeNull();
        expect(cont()).toBeDisabled();
    });

    it('lists the current types with their counts, most frequent first', () => {
        mount();
        const badges = screen.getAllByTestId('asset-bulk-now-type');
        expect(badges.map((b) => b.getAttribute('data-asset-type'))).toEqual(['ETF', 'ETF_STOCK', 'CROWDFUND_REAL_ESTATE']);
        expect(badges[0].textContent).toContain('×3');
    });

    it('«Show all» opens the whole selection', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-selected-toggle'));
        expect(screen.getAllByTestId('asset-bulk-selected-chip')).toHaveLength(5);
        expect(screen.queryByTestId('asset-bulk-selected-more')).toBeNull();
    });

    it('every field starts on «leave»', () => {
        mount();
        expect(screen.getByTestId('asset-bulk-active')).toHaveAttribute('data-state', 'leave');
        expect(screen.getByTestId('asset-bulk-is_benchmark')).toHaveAttribute('data-state', 'leave');
    });
});

describe('AssetBulkEditModal — the three-state controls', () => {
    it('a choice publishes its state, the field its chip and its Undo, and the header its Undo-all', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        expect(screen.getByTestId('asset-bulk-is_benchmark')).toHaveAttribute('data-state', 'yes');
        expect(screen.getByTestId('asset-bulk-is_benchmark-yes')).toHaveAttribute('aria-checked', 'true');
        expect(screen.getByTestId('asset-bulk-field-is_benchmark')).toHaveAttribute('data-modified', 'true');
        expect(screen.getByTestId('asset-bulk-is_benchmark-chip')).toBeInTheDocument();
        expect(screen.getByTestId('asset-bulk-reset-is_benchmark')).toBeInTheDocument();
        expect(screen.getByTestId('asset-bulk-reset-all')).toBeInTheDocument();
        expect(root()).toHaveAttribute('data-modified', '1');
    });

    it('the impact line counts the assets that change and the ones that already have the value', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        const line = screen.getByTestId('asset-bulk-is_benchmark-impact');
        expect(line).toHaveAttribute('data-changing', '4');
        expect(line).toHaveAttribute('data-total', '5');
    });

    it('Undo of the field puts it back to «leave» and removes its chip', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-active-no'));
        await fireEvent.click(screen.getByTestId('asset-bulk-reset-active'));
        expect(screen.getByTestId('asset-bulk-active')).toHaveAttribute('data-state', 'leave');
        expect(screen.queryByTestId('asset-bulk-active-chip')).toBeNull();
        expect(root()).toHaveAttribute('data-modified', '0');
    });

    it('Undo-all clears every field', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-active-no'));
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        await fireEvent.input(screen.getByTestId('asset-bulk-user-url'), {target: {value: 'https://example.org/x'}});
        expect(root()).toHaveAttribute('data-modified', '3');

        await fireEvent.click(screen.getByTestId('asset-bulk-reset-all'));

        expect(root()).toHaveAttribute('data-modified', '0');
        expect(screen.getByTestId('asset-bulk-active')).toHaveAttribute('data-state', 'leave');
        expect((screen.getByTestId('asset-bulk-user-url') as HTMLInputElement).value).toBe('');
        expect(cont()).toBeDisabled();
    });
});

describe('AssetBulkEditModal — «Continue»', () => {
    it('stays off when every asset already has the chosen value', async () => {
        mount({assets: [asset(1), asset(2)]});
        await fireEvent.click(screen.getByTestId('asset-bulk-active-yes'));
        expect(screen.getByTestId('asset-bulk-active-chip')).toBeInTheDocument();
        expect(screen.getByTestId('asset-bulk-active-impact')).toHaveAttribute('data-changing', '0');
        expect(cont()).toBeDisabled();
    });

    it('turns on as soon as one asset would change', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        expect(cont()).toBeEnabled();
    });

    it('a URL of blanks is «leave as is»', async () => {
        mount();
        await fireEvent.input(screen.getByTestId('asset-bulk-user-url'), {target: {value: '   '}});
        expect(cont()).toBeDisabled();
        expect(root()).toHaveAttribute('data-modified', '0');
    });

    it('hands the draft and only the changing fields of each asset to oncontinue', async () => {
        const {oncontinue} = mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        await fireEvent.click(screen.getByTestId('asset-bulk-active-yes'));
        await fireEvent.click(cont());

        expect(oncontinue).toHaveBeenCalledTimes(1);
        const {draft, items} = oncontinue.mock.calls[0][0];
        expect(draft).toMatchObject({active: true, is_benchmark: true});
        // asset 2 is already a benchmark and asset 5 is the only inactive one: each item carries only its own changes.
        expect(items).toEqual([
            {asset_id: 1, is_benchmark: true},
            {asset_id: 3, is_benchmark: true},
            {asset_id: 4, is_benchmark: true},
            {asset_id: 5, active: true, is_benchmark: true},
        ]);
    });
});

describe('AssetBulkEditModal — units per single price', () => {
    it.each(['0', '-2', '2.5', 'abc'])('"%s" shows the error and keeps «Continue» off even with another field touched', async (typed) => {
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        expect(cont()).toBeEnabled();

        await fireEvent.input(screen.getByTestId('asset-bulk-quote-base'), {target: {value: typed}});

        expect(screen.getByTestId('asset-bulk-quote-base-error')).toBeInTheDocument();
        expect(cont()).toBeDisabled();
        expect(screen.getByTestId('asset-bulk-quote-base')).toHaveAttribute('aria-invalid', 'true');
    });

    it('a valid unit goes out in the payload, and clearing the field removes the error', async () => {
        const {oncontinue} = mount({assets: [asset(1), asset(2)]});
        await fireEvent.input(screen.getByTestId('asset-bulk-quote-base'), {target: {value: '0'}});
        expect(screen.getByTestId('asset-bulk-quote-base-error')).toBeInTheDocument();

        await fireEvent.input(screen.getByTestId('asset-bulk-quote-base'), {target: {value: '100'}});
        expect(screen.queryByTestId('asset-bulk-quote-base-error')).toBeNull();
        await fireEvent.click(cont());

        expect(oncontinue.mock.calls[0][0].items).toEqual([
            {asset_id: 1, quote_base_quantity: 100},
            {asset_id: 2, quote_base_quantity: 100},
        ]);
    });
});

describe('AssetBulkEditModal — the type', () => {
    it('is chosen through the two-level select, and Undo puts it back', async () => {
        const {oncontinue} = mount();
        const field = screen.getByTestId('asset-bulk-type');
        await fireEvent.click(within(field).getByTestId('asset-bulk-type-button'));
        await fireEvent.click(within(field).getByTestId('asset-type-tree-option-BOND'));

        expect(screen.getByTestId('asset-bulk-field-asset_type')).toHaveAttribute('data-modified', 'true');
        expect(screen.getByTestId('asset-bulk-asset_type-impact')).toHaveAttribute('data-changing', '5');
        await fireEvent.click(cont());
        expect(oncontinue.mock.calls[0][0].items).toEqual(SELECTION.map((a) => ({asset_id: a.id, asset_type: 'BOND'})));
    });

    it('Undo of the type clears the choice', async () => {
        mount();
        const field = screen.getByTestId('asset-bulk-type');
        await fireEvent.click(within(field).getByTestId('asset-bulk-type-button'));
        await fireEvent.click(within(field).getByTestId('asset-type-tree-option-STOCK'));
        await fireEvent.click(screen.getByTestId('asset-bulk-reset-asset_type'));
        expect(screen.getByTestId('asset-bulk-field-asset_type')).toHaveAttribute('data-modified', 'false');
        expect(cont()).toBeDisabled();
    });
});

describe('AssetBulkEditModal — closing and reopening', () => {
    it('Cancel and the close button ask the owner to close', async () => {
        const {onclose} = mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-cancel'));
        await fireEvent.click(screen.getByTestId('asset-bulk-close'));
        expect(onclose).toHaveBeenCalledTimes(2);
    });

    it('a new opening starts clean', async () => {
        const {rerender} = mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-active-no'));
        expect(root()).toHaveAttribute('data-modified', '1');

        await rerender({open: false, assets: SELECTION});
        await rerender({open: true, assets: SELECTION});

        expect(screen.getByTestId('asset-bulk-active')).toHaveAttribute('data-state', 'leave');
        expect(root()).toHaveAttribute('data-modified', '0');
    });
});
