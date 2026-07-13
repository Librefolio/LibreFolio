import {describe, expect, it} from 'vitest';

import {buildTabUrl, getOptionalTabParam, getResolvedTabParam} from '../tabUrl';

describe('tabUrl', () => {
    const validTabIds = ['panoramica', 'posizioni', 'transazioni'] as const;

    describe('getOptionalTabParam', () => {
        it('returns tab id when tab query param exists and is valid', () => {
            const searchParams = new URLSearchParams('tab=posizioni');

            expect(getOptionalTabParam(searchParams, validTabIds)).toBe('posizioni');
        });

        it('returns undefined when tab query param is missing', () => {
            const searchParams = new URLSearchParams('asset=42');

            expect(getOptionalTabParam(searchParams, validTabIds)).toBeUndefined();
        });

        it('returns undefined when tab query param is not recognized', () => {
            const searchParams = new URLSearchParams('tab=unknown');

            expect(getOptionalTabParam(searchParams, validTabIds)).toBeUndefined();
        });
    });

    describe('getResolvedTabParam', () => {
        it('falls back to default tab when tab query param is invalid', () => {
            const searchParams = new URLSearchParams('tab=unknown');

            expect(getResolvedTabParam(searchParams, validTabIds, 'panoramica')).toBe('panoramica');
        });
    });

    describe('buildTabUrl', () => {
        it('adds tab query param when missing', () => {
            const currentUrl = new URL('https://example.com/dashboard?asset=42');

            expect(buildTabUrl(currentUrl, 'posizioni')).toBe('/dashboard?asset=42&tab=posizioni');
        });

        it('replaces existing tab query param', () => {
            const currentUrl = new URL('https://example.com/dashboard?tab=panoramica&asset=42');

            expect(buildTabUrl(currentUrl, 'transazioni')).toBe('/dashboard?asset=42&tab=transazioni');
        });

        it('removes tab query param when tab id is undefined', () => {
            const currentUrl = new URL('https://example.com/dashboard?tab=panoramica&asset=42');

            expect(buildTabUrl(currentUrl, undefined)).toBe('/dashboard?asset=42');
        });
    });
});
