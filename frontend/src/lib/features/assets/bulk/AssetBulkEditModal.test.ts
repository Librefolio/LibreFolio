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
 * - «Continue» checks the payload (only the fields that change for each asset) through `POST /assets/validate` and moves to
 *   the summary (`data-step`); the summary has its own test file;
 * - a new opening starts clean.
 * Responsive layout is not checked here (jsdom has no layout): the E2E at 375 px does it (lot E1).
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';
import {_} from '$lib/i18n';
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

vi.mock('$lib/components/ui/media/ImagePickerWrapper.svelte', async () => ({default: (await import('$test/ImagePickerStub.svelte')).default}));

import {zodiosApi} from '$lib/api';
import AssetBulkEditModal from './AssetBulkEditModal.svelte';
import type {BulkAsset} from './assetBulkEdit';

const validate = () => vi.mocked(zodiosApi.validate_assets_patch_api_v1_assets_validate_post as never) as ReturnType<typeof vi.fn>;
const patch = () => vi.mocked(zodiosApi.patch_assets_bulk_api_v1_assets_patch as never) as ReturnType<typeof vi.fn>;
const answer = (over: Record<string, unknown> = {}) => ({results: [], success_count: 0, errors: [], committed: false, issues: [], warnings: [], ...over});

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    validate().mockReset();
    validate().mockResolvedValue(answer());
    patch().mockReset();
    patch().mockResolvedValue(answer({committed: true}));
});

function asset(id: number, over: Partial<BulkAsset> = {}): BulkAsset {
    return {id, display_name: `Bulk asset ${id}`, asset_type: 'ETF', active: true, is_benchmark: false, quote_base_quantity: 1, icon_url: null, user_url: null, ...over};
}

const SELECTION: BulkAsset[] = [asset(1), asset(2, {is_benchmark: true}), asset(3, {asset_type: 'ETF_STOCK'}), asset(4, {asset_type: 'CROWDFUND_REAL_ESTATE'}), asset(5, {active: false})];

function mount(over: Record<string, unknown> = {}) {
    const onsaved = vi.fn();
    const onclose = vi.fn();
    const view = render(AssetBulkEditModal, {open: true, assets: SELECTION, onsaved, onclose, ...over});
    return {onsaved, onclose, ...view};
}

const root = () => screen.getByTestId('asset-bulk-edit');
const cont = () => screen.getByTestId('asset-bulk-continue') as HTMLButtonElement;

describe('AssetBulkEditModal — at rest', () => {
    it('shows the two zones in order (details and classification, then price and status), the selection, and nothing modified', () => {
        mount();
        expect(root()).toHaveAttribute('data-step', 'fields');
        expect(root()).toHaveAttribute('data-modified', '0');
        expect(root()).toHaveAttribute('data-selected', '5');
        const zones = ['asset-bulk-zone-details', 'asset-bulk-zone-price'].map((id) => screen.getByTestId(id));
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

    // 81 U45: «Leave as is» was too long for a segment of a three-state control (it read «Leave a…»): the segment says the state, one
    // short word (the SEL consultant: «Unchanged»), while the long sentence stays on the placeholders of the text fields.
    it('the «leave» segment of Active and Benchmark says «Unchanged», not the long sentence the text fields keep as their placeholder', () => {
        mount();
        const t = get(_);
        for (const field of ['active', 'is_benchmark']) {
            const segment = screen.getByTestId(`asset-bulk-${field}-leave`);
            expect(segment.textContent?.trim(), `${field}: the segment`).toBe(t('assets.bulkEdit.triLeave'));
            expect(segment.textContent?.trim(), `${field}: not the long sentence`).not.toBe(t('assets.bulkEdit.leave'));
        }
        expect(t('assets.bulkEdit.triLeave').length, 'the short word is short').toBeLessThanOrEqual(11);
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

    it('checks only the changing fields of each asset and moves to the summary', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-is_benchmark-yes'));
        await fireEvent.click(screen.getByTestId('asset-bulk-active-yes'));
        await fireEvent.click(cont());

        await waitFor(() => expect(root()).toHaveAttribute('data-step', 'summary'));
        expect(validate()).toHaveBeenCalledTimes(1);
        // asset 2 is already a benchmark and asset 5 is the only inactive one: each item carries only its own changes.
        expect(validate().mock.calls[0][0]).toEqual([
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
        mount({assets: [asset(1), asset(2)]});
        await fireEvent.input(screen.getByTestId('asset-bulk-quote-base'), {target: {value: '0'}});
        expect(screen.getByTestId('asset-bulk-quote-base-error')).toBeInTheDocument();

        await fireEvent.input(screen.getByTestId('asset-bulk-quote-base'), {target: {value: '100'}});
        expect(screen.queryByTestId('asset-bulk-quote-base-error')).toBeNull();
        await fireEvent.click(cont());

        await waitFor(() => expect(validate()).toHaveBeenCalledTimes(1));
        expect(validate().mock.calls[0][0]).toEqual([
            {asset_id: 1, quote_base_quantity: 100},
            {asset_id: 2, quote_base_quantity: 100},
        ]);
    });
});

describe('AssetBulkEditModal — the type', () => {
    it('is chosen through the two-level select, and Undo puts it back', async () => {
        mount();
        const field = screen.getByTestId('asset-bulk-type');
        await fireEvent.click(within(field).getByTestId('asset-bulk-type-button'));
        await fireEvent.click(within(field).getByTestId('asset-type-tree-option-BOND'));

        expect(screen.getByTestId('asset-bulk-field-asset_type')).toHaveAttribute('data-modified', 'true');
        expect(screen.getByTestId('asset-bulk-asset_type-impact')).toHaveAttribute('data-changing', '5');
        await fireEvent.click(cont());
        await waitFor(() => expect(validate()).toHaveBeenCalledTimes(1));
        expect(validate().mock.calls[0][0]).toEqual(SELECTION.map((a) => ({asset_id: a.id, asset_type: 'BOND'})));
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

describe('AssetBulkEditModal — the type placeholder', () => {
    // The text is read back from the catalogue, never written here.
    const triggerText = () => screen.getByTestId('asset-bulk-type-button').textContent ?? '';

    it('says «Leave as is» alone when every asset has the same type', () => {
        mount({assets: [asset(1), asset(2)]});
        expect(triggerText()).toContain(get(_)('assets.bulkEdit.leave'));
        expect(triggerText()).not.toContain(get(_)('assets.bulkEdit.leaveDifferent'));
    });

    it('adds «different values» when the types differ', () => {
        mount();
        expect(triggerText()).toContain(get(_)('assets.bulkEdit.leaveDifferent'));
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

describe('the chosen icon', () => {
    it('shows no file name or URL under the icon once it is chosen (U2)', async () => {
        mount();
        await fireEvent.click(screen.getByTestId('asset-bulk-icon-pick'));
        await fireEvent.click(screen.getByTestId('stub-icon-pick'));
        expect(screen.getByTestId('asset-bulk-field-icon_url')).toHaveAttribute('data-modified', 'true');
        expect(screen.queryByTestId('asset-bulk-icon-file')).toBeNull();
    });
});

describe('removing the icon and the personal URL (U7)', () => {
    const HOLDERS = [asset(1, {icon_url: 'https://example.test/1.png', user_url: 'https://example.test/u1'}), asset(2), asset(3, {icon_url: 'https://example.test/3.png'})];

    it('offers «Remove» only for what at least one selected asset holds', () => {
        mount({assets: [asset(1), asset(2)]});
        expect(screen.queryByTestId('asset-bulk-icon-remove')).toBeNull();
        expect(screen.queryByTestId('asset-bulk-user-url-remove')).toBeNull();
    });

    it('«Remove icon» is a choice of its own: chip, Undo, «Continue» on, and a null only for the assets that have an icon', async () => {
        mount({assets: HOLDERS});
        expect(screen.queryByTestId('asset-bulk-user-url-remove')).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('asset-bulk-icon-remove'));

        expect(screen.getByTestId('asset-bulk-icon-remove')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('asset-bulk-field-icon_url')).toHaveAttribute('data-modified', 'true');
        expect(screen.getByTestId('asset-bulk-icon_url-chip')).toBeInTheDocument();
        expect(screen.getByTestId('asset-bulk-icon_url-impact')).toHaveAttribute('data-changing', '2');
        expect(cont()).toBeEnabled();

        await fireEvent.click(screen.getByTestId('asset-bulk-verify'));
        await waitFor(() => expect(validate()).toHaveBeenCalledTimes(1));
        expect(validate().mock.calls[0][0]).toEqual([
            {asset_id: 1, icon_url: null},
            {asset_id: 3, icon_url: null},
        ]);
    });

    it('«Remove URL» turns the field off while it stands, and Undo gives it back', async () => {
        mount({assets: HOLDERS});
        await fireEvent.click(screen.getByTestId('asset-bulk-user-url-remove'));
        expect(screen.getByTestId('asset-bulk-user-url')).toBeDisabled();
        expect(screen.getByTestId('asset-bulk-field-user_url')).toHaveAttribute('data-modified', 'true');
        expect(root()).toHaveAttribute('data-modified', '1');

        await fireEvent.click(screen.getByTestId('asset-bulk-reset-user_url'));
        expect(screen.getByTestId('asset-bulk-user-url')).toBeEnabled();
        expect(screen.getByTestId('asset-bulk-user-url-remove')).toHaveAttribute('aria-pressed', 'false');
        expect(screen.getByTestId('asset-bulk-field-user_url')).toHaveAttribute('data-modified', 'false');
        expect(cont()).toBeDisabled();
    });

    it('choosing an icon after «Remove icon» takes the removal back, and the other way round', async () => {
        mount({assets: HOLDERS});
        await fireEvent.click(screen.getByTestId('asset-bulk-icon-remove'));
        await fireEvent.click(screen.getByTestId('asset-bulk-icon-pick'));
        await fireEvent.click(screen.getByTestId('stub-icon-pick'));
        expect(screen.getByTestId('asset-bulk-icon-remove')).toHaveAttribute('aria-pressed', 'false');

        await fireEvent.click(screen.getByTestId('asset-bulk-icon-remove'));
        expect(screen.getByTestId('asset-bulk-icon-remove')).toHaveAttribute('aria-pressed', 'true');
        await fireEvent.click(screen.getByTestId('asset-bulk-verify'));
        await waitFor(() => expect(validate()).toHaveBeenCalledTimes(1));
        // The removal is what goes out, never the chosen icon as well.
        expect(validate().mock.calls[0][0]).toEqual([
            {asset_id: 1, icon_url: null},
            {asset_id: 3, icon_url: null},
        ]);
    });

    it('«Undo all» takes both removals back', async () => {
        mount({assets: HOLDERS});
        await fireEvent.click(screen.getByTestId('asset-bulk-icon-remove'));
        await fireEvent.click(screen.getByTestId('asset-bulk-user-url-remove'));
        expect(root()).toHaveAttribute('data-modified', '2');
        await fireEvent.click(screen.getByTestId('asset-bulk-reset-all'));
        expect(root()).toHaveAttribute('data-modified', '0');
        expect(screen.getByTestId('asset-bulk-icon-remove')).toHaveAttribute('aria-pressed', 'false');
    });
});

describe('the scrolling body (U5)', () => {
    it('scrolls without a visible scrollbar: the shared utility, still reachable and focusable by keyboard', () => {
        mount();
        const body = screen.getByTestId('asset-bulk-body');
        // `overflow-y-auto` keeps the scroll (wheel, touch, keyboard); `scrollbar-hidden` (app.css) only hides the bar.
        expect(body).toHaveClass('overflow-y-auto');
        expect(body).toHaveClass('scrollbar-hidden');
        // A scrollable area a keyboard user can reach: a region, named by the title, in the tab order.
        expect(body).toHaveAttribute('tabindex', '0');
        expect(body).toHaveAttribute('role', 'region');
        expect(body).toHaveAttribute('aria-labelledby', 'asset-bulk-edit-title');
    });
});
