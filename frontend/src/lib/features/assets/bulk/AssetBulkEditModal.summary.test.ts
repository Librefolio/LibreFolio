// @vitest-environment jsdom
/**
 * AssetBulkEditModal — step 2 «Summary» and the save (Vitest + jsdom). Lane 65, lot F5.
 *
 * `POST /assets/validate` and `PATCH /assets` are simulated; no assertion reads a translated text (test ids and `data-*`).
 *
 * Contract.
 * - «Continue» runs the check by itself and moves to the summary, also when the answer holds a block (then «Save» is
 *   off); when the call fails it stays on the fields with the failure banner.
 * - The summary has one row per changing asset (the assets of the payload), a cell per touched field marked
 *   `data-unchanged` where the asset already has the value, the numbers, and the rows of warned assets amber / blocked red.
 * - «Back» returns to the fields with the draft as it was.
 * - «Save N assets» sends the same payload to `PATCH /assets`: `committed=true` calls `onsaved` once with the ids and
 *   the fields; `committed=false` stays on the summary with the red banner and the issues (nothing saved, `onsaved`
 *   never called); a failed call shows the banner too and the button stays usable for a retry.
 * - While the call is open `data-saving` is true and every button that could change something is off.
 * - «Remove from the edit» on the summary re-checks the rest by itself, so «Save» is never on over a stale answer;
 *   when nothing is left to change the modal goes back to the fields.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';

vi.mock('$lib/api', async () => {
    const {schemas} = await import('$lib/api/generated');
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, schemas, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

import {zodiosApi} from '$lib/api';
import AssetBulkEditModal from './AssetBulkEditModal.svelte';
import type {BulkAsset} from './assetBulkEdit';

const validate = () => vi.mocked(zodiosApi.validate_assets_patch_api_v1_assets_validate_post as never) as ReturnType<typeof vi.fn>;
const patch = () => vi.mocked(zodiosApi.patch_assets_bulk_api_v1_assets_patch as never) as ReturnType<typeof vi.fn>;

function asset(id: number, over: Partial<BulkAsset> = {}): BulkAsset {
    return {id, display_name: `Summary asset ${id}`, asset_type: 'ETF', active: true, is_benchmark: false, quote_base_quantity: 1, icon_url: null, user_url: null, ...over};
}

// Asset 2 is already a benchmark: its benchmark cell is «already», its type cell changes.
const SELECTION: BulkAsset[] = [asset(1), asset(2, {is_benchmark: true}), asset(3, {asset_type: 'ETF_STOCK', is_benchmark: true})];

const answer = (over: Record<string, unknown> = {}) => ({results: [], success_count: 0, errors: [], committed: false, issues: [], warnings: [], ...over});
const issue = (code: string, assetId: number, index: number, over: Record<string, unknown> = {}) => ({asset_id: assetId, index, code, message: `English ${code}`, params: null, field: null, ...over});

function mount(over: Record<string, unknown> = {}) {
    const onsaved = vi.fn();
    const onclose = vi.fn();
    const view = render(AssetBulkEditModal, {open: true, assets: SELECTION, onsaved, onclose, ...over});
    return {onsaved, onclose, ...view};
}

const root = () => screen.getByTestId('asset-bulk-edit');
const saveBtn = () => screen.getByTestId('asset-bulk-save') as HTMLButtonElement;

async function chooseType(type: string) {
    const field = screen.getByTestId('asset-bulk-type');
    await fireEvent.click(within(field).getByTestId('asset-bulk-type-button'));
    await fireEvent.click(within(field).getByTestId(`asset-type-tree-option-${type}`));
}

/** Benchmark Yes + type STOCK for all, then «Continue»: the summary. */
async function toSummary(over: Record<string, unknown> = {}) {
    const view = mount(over);
    await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
    await chooseType('STOCK');
    await fireEvent.click(screen.getByTestId('asset-bulk-continue'));
    await waitFor(() => expect(root()).toHaveAttribute('data-step', 'summary'));
    return view;
}

const EXPECTED_ITEMS = [
    {asset_id: 1, asset_type: 'STOCK', is_benchmark: true},
    {asset_id: 2, asset_type: 'STOCK'},
    {asset_id: 3, asset_type: 'STOCK'},
];

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    validate().mockReset();
    validate().mockResolvedValue(answer());
    patch().mockReset();
    patch().mockResolvedValue(answer({committed: true}));
});

describe('«Continue»', () => {
    it('runs the check by itself and moves to the summary', async () => {
        await toSummary();
        expect(validate()).toHaveBeenCalledTimes(1);
        expect(validate().mock.calls[0][0]).toEqual(EXPECTED_ITEMS);
        expect(screen.getByTestId('asset-bulk-step-summary')).toHaveAttribute('data-active', 'true');
        expect(saveBtn()).toBeEnabled();
    });

    it('moves on even with a block, and then «Save» is off', async () => {
        validate().mockResolvedValue(answer({issues: [issue('indexWithTransactions', 1, 0, {field: 'asset_type', params: {tx_count: 4}})]}));
        await toSummary();
        expect(screen.getByTestId('asset-bulk-block-indexWithTransactions')).toBeInTheDocument();
        expect(saveBtn()).toBeDisabled();
    });

    it('stays on the fields, with the failure banner, when the check cannot run', async () => {
        validate().mockRejectedValue(new Error('boom'));
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        await fireEvent.click(screen.getByTestId('asset-bulk-continue'));
        await waitFor(() => expect(root()).toHaveAttribute('data-verify', 'failed'));
        expect(root()).toHaveAttribute('data-step', 'fields');
        expect(screen.getByTestId('asset-bulk-verify-failed')).toBeInTheDocument();
    });
});

describe('the summary', () => {
    it('has a row per changing asset, with «already» marked where the value is there', async () => {
        await toSummary();
        const summary = screen.getByTestId('asset-bulk-summary');
        expect(summary).toHaveAttribute('data-changing', '3');
        expect(summary).toHaveAttribute('data-selected', '3');
        const rows = screen.getAllByTestId('asset-bulk-summary-row');
        expect(rows.map((r) => r.getAttribute('data-asset-id'))).toEqual(['1', '2', '3']);
        const cells = (row: HTMLElement) =>
            within(row)
                .getAllByTestId('asset-bulk-summary-cell')
                .map((c) => [c.getAttribute('data-field'), c.getAttribute('data-unchanged')]);
        expect(cells(rows[0])).toEqual([
            ['asset_type', 'false'],
            ['is_benchmark', 'false'],
        ]);
        expect(cells(rows[1])).toEqual([
            ['asset_type', 'false'],
            ['is_benchmark', 'true'],
        ]);
        expect(cells(rows[2])).toEqual([
            ['asset_type', 'false'],
            ['is_benchmark', 'true'],
        ]);
    });

    it('says, per touched field, how many assets change', async () => {
        await toSummary();
        expect(screen.getByTestId('asset-bulk-summary-field-asset_type')).toHaveAttribute('data-changing', '3');
        expect(screen.getByTestId('asset-bulk-summary-field-is_benchmark')).toHaveAttribute('data-changing', '1');
    });

    it('leaves out an asset that has every chosen value', async () => {
        mount({assets: [asset(1), asset(2, {is_benchmark: true})]});
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        await fireEvent.click(screen.getByTestId('asset-bulk-continue'));
        await waitFor(() => expect(root()).toHaveAttribute('data-step', 'summary'));
        expect(screen.getAllByTestId('asset-bulk-summary-row').map((r) => r.getAttribute('data-asset-id'))).toEqual(['1']);
        expect(saveBtn()).toBeEnabled();
    });

    it('draws a warned asset amber and a blocked one red', async () => {
        validate().mockResolvedValue(
            answer({
                issues: [issue('indexWithTransactions', 1, 0, {field: 'asset_type', params: {tx_count: 4}})],
                warnings: [issue('assetFamilyChange', 2, 1, {field: 'asset_type', params: {from: 'ETF', to: 'STOCK'}})],
            }),
        );
        await toSummary();
        const state = (id: number) =>
            screen
                .getAllByTestId('asset-bulk-summary-row')
                .find((r) => r.getAttribute('data-asset-id') === String(id))!
                .getAttribute('data-state');
        expect(state(1)).toBe('blocked');
        expect(state(2)).toBe('warning');
        expect(state(3)).toBe('ok');
    });

    it('«Back» returns to the fields with the draft as it was', async () => {
        await toSummary();
        await fireEvent.click(screen.getByTestId('asset-bulk-back'));
        expect(root()).toHaveAttribute('data-step', 'fields');
        expect(screen.getByTestId('asset-bulk-is_benchmark')).toHaveAttribute('data-state', 'yes');
        expect(screen.getByTestId('asset-bulk-field-asset_type')).toHaveAttribute('data-modified', 'true');
    });
});

describe('«Save»', () => {
    it('sends the payload to PATCH once and reports the save', async () => {
        const {onsaved} = await toSummary();
        await fireEvent.click(saveBtn());

        await waitFor(() => expect(onsaved).toHaveBeenCalledTimes(1));
        expect(patch()).toHaveBeenCalledTimes(1);
        expect(patch().mock.calls[0][0]).toEqual(EXPECTED_ITEMS);
        expect(onsaved.mock.calls[0][0]).toEqual({ids: [1, 2, 3], fields: ['asset_type', 'is_benchmark'], count: 3});
    });

    it('publishes «saving» and keeps the buttons off while the call is open', async () => {
        let resolve: (value: unknown) => void = () => {};
        patch().mockReturnValue(new Promise((r) => (resolve = r)));
        const {onsaved} = await toSummary();
        await fireEvent.click(saveBtn());

        expect(root()).toHaveAttribute('data-saving', 'true');
        expect(saveBtn()).toBeDisabled();
        expect(screen.getByTestId('asset-bulk-back')).toBeDisabled();
        await fireEvent.click(saveBtn());
        expect(patch()).toHaveBeenCalledTimes(1);

        resolve(answer({committed: true}));
        await waitFor(() => expect(onsaved).toHaveBeenCalledTimes(1));
    });

    it('committed=false keeps the summary with the red banner and the issues, and saves nothing', async () => {
        patch().mockResolvedValue(answer({committed: false, issues: [issue('assetNotFound', 2, 1)]}));
        const {onsaved} = await toSummary();
        await fireEvent.click(saveBtn());

        await waitFor(() => expect(screen.getByTestId('asset-bulk-save-failed')).toBeInTheDocument());
        expect(root()).toHaveAttribute('data-step', 'summary');
        expect(root()).toHaveAttribute('data-saving', 'false');
        expect(onsaved).not.toHaveBeenCalled();
        expect(screen.getByTestId('asset-bulk-block-assetNotFound')).toBeInTheDocument();
        expect(saveBtn()).toBeDisabled();
    });

    it('«Remove from the edit» of the culprit re-checks the rest, clears the banner and turns «Save» on', async () => {
        patch().mockResolvedValue(answer({committed: false, issues: [issue('assetNotFound', 2, 1)]}));
        const {onsaved} = await toSummary();
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(screen.getByTestId('asset-bulk-block-assetNotFound')).toBeInTheDocument());

        await fireEvent.click(screen.getByTestId('asset-bulk-block-assetNotFound-remove'));

        await waitFor(() => expect(validate()).toHaveBeenCalledTimes(2));
        expect(validate().mock.calls[1][0]).toEqual([
            {asset_id: 1, asset_type: 'STOCK', is_benchmark: true},
            {asset_id: 3, asset_type: 'STOCK'},
        ]);
        await waitFor(() => expect(saveBtn()).toBeEnabled());
        expect(screen.queryByTestId('asset-bulk-save-failed')).toBeNull();
        expect(root()).toHaveAttribute('data-step', 'summary');
        expect(screen.getAllByTestId('asset-bulk-summary-row').map((r) => r.getAttribute('data-asset-id'))).toEqual(['1', '3']);

        patch().mockResolvedValue(answer({committed: true}));
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(onsaved).toHaveBeenCalledTimes(1));
        expect(onsaved.mock.calls[0][0].ids).toEqual([1, 3]);
    });

    it('a failed call shows the banner and the button stays usable for a retry', async () => {
        patch().mockRejectedValueOnce(new Error('boom'));
        const {onsaved} = await toSummary();
        await fireEvent.click(saveBtn());

        await waitFor(() => expect(screen.getByTestId('asset-bulk-save-failed')).toBeInTheDocument());
        expect(saveBtn()).toBeEnabled();
        await fireEvent.click(saveBtn());
        await waitFor(() => expect(onsaved).toHaveBeenCalledTimes(1));
    });
});

describe('removing the last changing asset on the summary', () => {
    it('goes back to the fields', async () => {
        validate().mockResolvedValue(answer({warnings: [issue('assetFamilyChange', 1, 0, {field: 'asset_type', params: {from: 'ETF', to: 'STOCK'}})]}));
        mount({assets: [asset(1)]});
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        await fireEvent.click(screen.getByTestId('asset-bulk-continue'));
        await waitFor(() => expect(root()).toHaveAttribute('data-step', 'summary'));

        await fireEvent.click(screen.getByTestId('asset-bulk-warning-assetFamilyChange-remove'));

        expect(root()).toHaveAttribute('data-step', 'fields');
        expect(root()).toHaveAttribute('data-selected', '0');
    });
});
