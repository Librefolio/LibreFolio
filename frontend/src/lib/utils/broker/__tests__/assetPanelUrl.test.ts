import {describe, expect, it} from 'vitest';

import {buildAssetPanelUrl, getAssetPanelAssetId} from '../assetPanelUrl';

describe('assetPanelUrl', () => {
    describe('getAssetPanelAssetId', () => {
        it('returns asset id when asset query param exists', () => {
            const searchParams = new URLSearchParams('asset=42');

            expect(getAssetPanelAssetId(searchParams)).toBe(42);
        });

        it('returns undefined when asset query param is missing', () => {
            const searchParams = new URLSearchParams('tab=positions');

            expect(getAssetPanelAssetId(searchParams)).toBeUndefined();
        });
    });

    describe('buildAssetPanelUrl', () => {
        it('adds asset query param when missing', () => {
            const currentUrl = new URL('https://example.com/brokers/12?tab=positions');

            expect(buildAssetPanelUrl(currentUrl, 42)).toBe('/brokers/12?tab=positions&asset=42');
        });

        it('replaces existing asset query param', () => {
            const currentUrl = new URL('https://example.com/brokers/12?tab=positions&asset=10');

            expect(buildAssetPanelUrl(currentUrl, 42)).toBe('/brokers/12?tab=positions&asset=42');
        });

        it('removes asset query param when asset id is undefined', () => {
            const currentUrl = new URL('https://example.com/brokers/12?tab=positions&asset=42');

            expect(buildAssetPanelUrl(currentUrl, undefined)).toBe('/brokers/12?tab=positions');
        });

        it('preserves unrelated query params when removing asset query param', () => {
            const currentUrl = new URL('https://example.com/brokers/12?tab=positions&sort=name&asset=42&view=table');

            expect(buildAssetPanelUrl(currentUrl, null)).toBe('/brokers/12?tab=positions&sort=name&view=table');
        });
    });
});
