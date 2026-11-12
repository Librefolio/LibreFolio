// @vitest-environment jsdom
/**
 * AssetBulkEditModal — «Verify now» (Vitest + jsdom). Lane 65, lot F4.
 *
 * `POST /assets/validate` is simulated (`zodiosApi.validate_assets_patch_api_v1_assets_validate_post`); no assertion reads
 * a translated text — banners, rows, chips and counts are found by test id and `data-*`.
 *
 * Contract.
 * - «Verify now» is off until the draft would change an asset; it sends the payload of the draft (`buildBulkPatch`) and
 *   publishes `data-verify` (`idle`, `running`, `done`, `failed`).
 * - An answer with no problem shows nothing at all.
 * - Blocks come before warnings, each group by code with a row per asset; the block on the type puts the chip
 *   «blocked» and the line «Not allowed for N of M» on that field, and `data-blocked` on the root counts the groups.
 * - «Remove from the edit» takes the group's assets out of this edit (the selection count drops, later payloads leave
 *   them out) and discards the answer; «That's fine» hides the warnings for good, blocks stay.
 * - Any change of the draft discards the answer; an answer that comes back after the draft changed is dropped.
 * - A failed call shows a banner and `data-verify="failed"`, and the button can be pressed again.
 * - «Continue» tells whether the warnings were accepted.
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

function asset(id: number, over: Partial<BulkAsset> = {}): BulkAsset {
    return {id, display_name: `Verify asset ${id}`, asset_type: 'ETF', active: true, is_benchmark: false, quote_base_quantity: 1, icon_url: null, user_url: null, ...over};
}

const SELECTION: BulkAsset[] = [asset(1), asset(2), asset(3, {asset_type: 'CROWDFUND_REAL_ESTATE'})];

const answer = (over: Record<string, unknown> = {}) => ({results: [], success_count: 0, errors: [], committed: false, issues: [], warnings: [], ...over});
const issue = (code: string, assetId: number, index: number, over: Record<string, unknown> = {}) => ({asset_id: assetId, index, code, message: `English ${code}`, params: null, field: null, ...over});

function mount(over: Record<string, unknown> = {}) {
    const oncontinue = vi.fn();
    const view = render(AssetBulkEditModal, {open: true, assets: SELECTION, oncontinue, onclose: vi.fn(), ...over});
    return {oncontinue, ...view};
}

const root = () => screen.getByTestId('asset-bulk-edit');
const verifyBtn = () => screen.getByTestId('asset-bulk-verify') as HTMLButtonElement;
const banners = () => screen.getByTestId('asset-bulk-verify-banners');

async function chooseType(type: string) {
    const field = screen.getByTestId('asset-bulk-type');
    await fireEvent.click(within(field).getByTestId('asset-bulk-type-button'));
    await fireEvent.click(within(field).getByTestId(`asset-type-tree-option-${type}`));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    validate().mockReset();
    validate().mockResolvedValue(answer());
});

describe('«Verify now»', () => {
    it('is off until the draft would change an asset', async () => {
        mount();
        expect(verifyBtn()).toBeDisabled();
        expect(root()).toHaveAttribute('data-verify', 'idle');
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        expect(verifyBtn()).toBeEnabled();
    });

    it('sends the payload of the draft, shows nothing when the answer has no problem, and says it is done', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        await fireEvent.click(verifyBtn());

        await waitFor(() => expect(root()).toHaveAttribute('data-verify', 'done'));
        expect(validate()).toHaveBeenCalledTimes(1);
        expect(validate().mock.calls[0][0]).toEqual([
            {asset_id: 1, is_benchmark: true},
            {asset_id: 2, is_benchmark: true},
            {asset_id: 3, is_benchmark: true},
        ]);
        expect(banners().children).toHaveLength(0);
    });

    it('publishes «running» and keeps the button off while the call is open', async () => {
        let resolve: (value: unknown) => void = () => {};
        validate().mockReturnValue(new Promise((r) => (resolve = r)));
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        await fireEvent.click(verifyBtn());

        expect(root()).toHaveAttribute('data-verify', 'running');
        expect(verifyBtn()).toBeDisabled();
        expect(screen.getByTestId('asset-bulk-verifying')).toBeInTheDocument();
        await fireEvent.click(verifyBtn());
        expect(validate()).toHaveBeenCalledTimes(1);

        resolve(answer());
        await waitFor(() => expect(root()).toHaveAttribute('data-verify', 'done'));
    });
});

describe('blocks and warnings', () => {
    const indexBlocked = answer({
        issues: [issue('indexWithTransactions', 1, 0, {field: 'asset_type', params: {tx_count: 12}}), issue('indexWithTransactions', 2, 1, {field: 'asset_type', params: {tx_count: 8}})],
        warnings: [issue('assetFamilyChange', 3, 2, {field: 'asset_type', params: {from: 'CROWDFUND_REAL_ESTATE', to: 'INDEX'}})],
    });

    async function verifyIndex() {
        validate().mockResolvedValue(indexBlocked);
        const view = mount();
        await chooseType('INDEX');
        await fireEvent.click(verifyBtn());
        await waitFor(() => expect(root()).toHaveAttribute('data-verify', 'done'));
        return view;
    }

    it('shows the block first, with a row per asset, then the warning', async () => {
        await verifyIndex();
        const block = screen.getByTestId('asset-bulk-block-indexWithTransactions');
        const warning = screen.getByTestId('asset-bulk-warning-assetFamilyChange');
        expect(block.compareDocumentPosition(warning) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
        const rows = within(screen.getByTestId('asset-bulk-block-indexWithTransactions-rows')).getAllByRole('listitem');
        expect(rows.map((r) => r.getAttribute('data-asset-id'))).toEqual(['1', '2']);
        expect(rows[0].textContent).toContain('12');
        expect(within(screen.getByTestId('asset-bulk-warning-assetFamilyChange-rows')).getAllByRole('listitem')).toHaveLength(1);
        expect(root()).toHaveAttribute('data-blocked', '1');
    });

    it('marks the blocked field with its chip and its line, and nothing else', async () => {
        await verifyIndex();
        expect(screen.getByTestId('asset-bulk-asset_type-blocked')).toBeInTheDocument();
        expect(screen.getByTestId('asset-bulk-asset_type-blocked-line')).toHaveAttribute('data-blocked', '2');
        expect(screen.getByTestId('asset-bulk-field-asset_type')).toHaveAttribute('data-blocked', '2');
        expect(screen.queryByTestId('asset-bulk-active-blocked')).toBeNull();
    });

    it('«Remove from the edit» of the block takes its assets out, discards the answer and the next payload leaves them out', async () => {
        await verifyIndex();
        await fireEvent.click(screen.getByTestId('asset-bulk-block-indexWithTransactions-remove'));

        expect(root()).toHaveAttribute('data-selected', '1');
        expect(root()).toHaveAttribute('data-verify', 'idle');
        expect(screen.queryByTestId('asset-bulk-block-indexWithTransactions')).toBeNull();
        expect(screen.queryByTestId('asset-bulk-asset_type-blocked')).toBeNull();

        validate().mockResolvedValue(answer());
        await fireEvent.click(verifyBtn());
        await waitFor(() => expect(validate()).toHaveBeenCalledTimes(2));
        expect(validate().mock.calls[1][0]).toEqual([{asset_id: 3, asset_type: 'INDEX'}]);
    });

    it("«That's fine» hides the warnings for good; the block stays", async () => {
        await verifyIndex();
        await fireEvent.click(screen.getByTestId('asset-bulk-warning-assetFamilyChange-ok'));
        expect(screen.queryByTestId('asset-bulk-warning-assetFamilyChange')).toBeNull();
        expect(screen.getByTestId('asset-bulk-block-indexWithTransactions')).toBeInTheDocument();
    });

    it('a warning alone: «Remove from the edit» takes that asset out', async () => {
        validate().mockResolvedValue(answer({warnings: [issue('assetFamilyChange', 3, 2, {field: 'asset_type', params: {from: 'CROWDFUND_REAL_ESTATE', to: 'ETF_STOCK'}})]}));
        mount();
        await chooseType('STOCK');
        await fireEvent.click(verifyBtn());
        await waitFor(() => expect(screen.getByTestId('asset-bulk-warning-assetFamilyChange')).toBeInTheDocument());
        expect(root()).toHaveAttribute('data-blocked', '0');

        await fireEvent.click(screen.getByTestId('asset-bulk-warning-assetFamilyChange-remove'));
        expect(root()).toHaveAttribute('data-selected', '2');
        expect(screen.queryByTestId('asset-bulk-warning-assetFamilyChange')).toBeNull();
    });

    it('any change of the draft discards the answer', async () => {
        await verifyIndex();
        await fireEvent.click(screen.getByTestId('asset-bulk-active-no'));
        expect(root()).toHaveAttribute('data-verify', 'idle');
        expect(screen.queryByTestId('asset-bulk-block-indexWithTransactions')).toBeNull();
        expect(screen.queryByTestId('asset-bulk-asset_type-blocked')).toBeNull();
    });

    it('an answer that arrives after the draft changed is dropped', async () => {
        let resolve: (value: unknown) => void = () => {};
        validate().mockReturnValue(new Promise((r) => (resolve = r)));
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        await fireEvent.click(verifyBtn());
        expect(root()).toHaveAttribute('data-verify', 'running');

        await fireEvent.click(screen.getByTestId('asset-bulk-active-no'));
        resolve(indexBlocked);
        await Promise.resolve();
        await Promise.resolve();

        expect(root()).toHaveAttribute('data-verify', 'idle');
        expect(screen.queryByTestId('asset-bulk-block-indexWithTransactions')).toBeNull();
    });

    it('«Continue» says whether the warnings were accepted', async () => {
        const {oncontinue} = await verifyIndex();
        await fireEvent.click(screen.getByTestId('asset-bulk-block-indexWithTransactions-remove'));
        validate().mockResolvedValue(answer({warnings: [issue('assetFamilyChange', 3, 0, {field: 'asset_type', params: {from: 'CROWDFUND_REAL_ESTATE', to: 'INDEX'}})]}));
        await fireEvent.click(verifyBtn());
        await waitFor(() => expect(screen.getByTestId('asset-bulk-warning-assetFamilyChange')).toBeInTheDocument());
        await fireEvent.click(screen.getByTestId('asset-bulk-warning-assetFamilyChange-ok'));
        await fireEvent.click(screen.getByTestId('asset-bulk-continue'));
        expect(oncontinue.mock.calls[0][0].warningsAccepted).toBe(true);
    });
});

describe('a check that fails', () => {
    it('shows a banner, says «failed», and the button can be pressed again', async () => {
        validate().mockRejectedValueOnce(new Error('boom'));
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        await fireEvent.click(verifyBtn());

        await waitFor(() => expect(root()).toHaveAttribute('data-verify', 'failed'));
        expect(screen.getByTestId('asset-bulk-verify-failed')).toBeInTheDocument();
        expect(verifyBtn()).toBeEnabled();

        validate().mockResolvedValue(answer());
        await fireEvent.click(verifyBtn());
        await waitFor(() => expect(root()).toHaveAttribute('data-verify', 'done'));
        expect(screen.queryByTestId('asset-bulk-verify-failed')).toBeNull();
    });
});
