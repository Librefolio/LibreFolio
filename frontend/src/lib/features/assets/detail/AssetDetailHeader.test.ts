// @vitest-environment jsdom
/**
 * AssetDetailHeader — the header of the asset detail page (project 71, block 1).
 *
 * The nav inside it (AssetBrowseNav) stays `pending` here: `$navigating` is null and no afterNavigate
 * callback runs, so it renders no buttons and fetches nothing. Nothing reads translated text: the
 * labels are only required non-empty and not a raw key.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

const mocks = await vi.hoisted(async () => {
    const {writable} = await import('svelte/store');
    return {
        goto: vi.fn(() => Promise.resolve()),
        afterNavigate: vi.fn(),
        listAssets: vi.fn(() => Promise.resolve([])),
        page: writable<Record<string, unknown>>({url: new URL('http://librefolio.test/assets/7'), params: {id: '7'}, route: {id: '/(app)/assets/[id]'}}),
        navigating: writable<Record<string, unknown> | null>(null),
    };
});

vi.mock('$app/navigation', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$app/navigation')>()),
    goto: mocks.goto,
    afterNavigate: mocks.afterNavigate,
}));
vi.mock('$app/stores', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$app/stores')>()),
    page: mocks.page,
    navigating: mocks.navigating,
}));
vi.mock('$lib/api', () => ({
    zodiosApi: {list_assets_api_v1_assets_query_get: mocks.listAssets},
    ApiError: class ApiError extends Error {},
}));

import {cleanup, render, screen, setupI18n} from '$test/component';
import {guideAnchors} from '$lib/features/onboarding/guideAnchors.svelte';
import type {AssetDetail} from '$lib/types';
import AssetDetailHeader from './AssetDetailHeader.svelte';

const TX_HREF = '/transactions?asset_id=7';

function info(overrides: Record<string, unknown> = {}): AssetDetail {
    return {id: 7, display_name: 'Synthetic asset', asset_type: 'STOCK', currency: 'EUR', active: true, tx_count: 29, provider_code: null, icon_url: null, ...overrides} as unknown as AssetDetail;
}

function mount(assetInfo: AssetDetail | null) {
    return render(AssetDetailHeader, {
        assetId: 7,
        assetInfo,
        loading: false,
        currencyFlag: '🇪🇺',
        providerIconUrl: null,
        assetProviderName: 'Synthetic provider',
        userUrl: null,
        providerExternalUrl: null,
        transactionsHref: TX_HREF,
        liveUpdatesState: 'running',
    });
}

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
});

describe('AssetDetailHeader — transactions badge', () => {
    it('H-01 is a link to the filtered list with an icon and the count', () => {
        mount(info({tx_count: 29}));
        const link = screen.getByTestId('asset-detail-transactions-link');
        expect(link.tagName).toBe('A');
        expect(link).toHaveAttribute('href', TX_HREF);
        expect(link.querySelector('svg')).not.toBeNull();
        expect(screen.getByTestId('asset-detail-transactions-count')).toHaveTextContent('29');
    });

    it('H-02 is absent with no transactions', () => {
        mount(info({tx_count: 0}));
        expect(screen.queryByTestId('asset-detail-transactions-link')).toBeNull();
        cleanup();
        mount(info({tx_count: undefined}));
        expect(screen.queryByTestId('asset-detail-transactions-link')).toBeNull();
    });
});

describe('AssetDetailHeader — guide anchor and back button', () => {
    it('H-03 the guide anchor is the header root', () => {
        mount(info());
        expect(guideAnchors.get('asset.detail.header')).toBe(screen.getByTestId('asset-detail-header'));
    });

    it('H-04 the back button has an accessible name that is not a raw key', () => {
        mount(info());
        const label = screen.getByTestId('asset-detail-back-btn').getAttribute('aria-label') ?? '';
        expect(label.trim()).not.toBe('');
        expect(label.startsWith('assetDetail.')).toBe(false);
    });
});
