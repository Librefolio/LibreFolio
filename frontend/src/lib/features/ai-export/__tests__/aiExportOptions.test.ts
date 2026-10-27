import {describe, expect, it} from 'vitest';

import {aiExportOptionsFingerprint, areAiExportOptionsEqual, estimateAiExportTokenSeverity, formatAiExportByteSize, formatAiExportTokenCount, normalizeAiExportPeriod, reconcileAiExportOptions, resolveAiExportPeriod} from '../aiExportOptions';
import {compatibilityFixture} from './runtimeFixtures';

describe('AI Export options', () => {
    it('resolves 3M/6M/1Y/custom periods with explicit start and end', () => {
        expect(resolveAiExportPeriod('2026-03-31', {preset: '3m', customAmount: 3, customUnit: 'months'})).toEqual({start: '2025-12-31', end: '2026-03-31'});
        expect(resolveAiExportPeriod('2026-03-31', {preset: '6m', customAmount: 3, customUnit: 'months'})).toEqual({start: '2025-09-30', end: '2026-03-31'});
        expect(resolveAiExportPeriod('2026-03-31', {preset: '1y', customAmount: 3, customUnit: 'months'})).toEqual({start: '2025-03-31', end: '2026-03-31'});
        expect(resolveAiExportPeriod('2026-03-31', {preset: 'custom', customAmount: 14, customUnit: 'days'})).toEqual({start: '2026-03-17', end: '2026-03-31'});
    });

    it('normalizes invalid custom values and classifies token severity', () => {
        expect(normalizeAiExportPeriod({preset: 'custom', customAmount: 0, customUnit: 'weeks'})).toMatchObject({customAmount: 1});
        expect(estimateAiExportTokenSeverity(20_000)).toBe('normal');
        expect(estimateAiExportTokenSeverity(20_001)).toBe('warning');
        expect(estimateAiExportTokenSeverity(59_999)).toBe('warning');
        expect(estimateAiExportTokenSeverity(60_000)).toBe('large');
    });

    it('formats tokens and bytes with localized two-decimal compact units', () => {
        expect(formatAiExportTokenCount(32_426, 'it', 'token')).toBe('32,43 k token');
        expect(formatAiExportTokenCount(999, 'en', 'tokens')).toBe('999.00 tokens');
        expect(formatAiExportTokenCount(1_250_000, 'fr', 'jetons')).toBe('1,25 M jetons');
        expect(formatAiExportByteSize(1_536, 'it')).toBe('1,50 KB');
        expect(formatAiExportByteSize(2_621_440, 'en')).toBe('2.50 MB');
    });

    it('reconciles stale selections against the real catalog', () => {
        const options = reconcileAiExportOptions(compatibilityFixture(), 'asset', {
            selectionKind: 'analysis',
            selectionId: 'portfolio.pac_planning',
            detailLevel: 'standard',
            period: {preset: '3m', customAmount: 3, customUnit: 'months'},
            responseLanguage: 'English',
        });
        expect(options.selectionId.startsWith('asset.')).toBe(true);
    });

    it('fingerprints every payload-changing option', () => {
        const base = {
            selectionKind: 'analysis' as const,
            selectionId: 'portfolio.pac_planning' as const,
            detailLevel: 'standard' as const,
            period: {preset: '3m' as const, customAmount: 3, customUnit: 'months' as const},
            responseLanguage: 'English' as const,
        };
        expect(aiExportOptionsFingerprint(base)).not.toBe(aiExportOptionsFingerprint({...base, detailLevel: 'compact'}));
        expect(aiExportOptionsFingerprint(base)).not.toBe(aiExportOptionsFingerprint({...base, userNotes: 'note'}));
    });

    it('excludes hidden Analysis notes from Dataset fingerprints', () => {
        const dataset = {
            selectionKind: 'dataset' as const,
            selectionId: 'portfolio.overview_and_history' as const,
            detailLevel: 'standard' as const,
            period: {preset: '3m' as const, customAmount: 3, customUnit: 'months' as const},
            responseLanguage: 'English' as const,
        };

        expect(aiExportOptionsFingerprint({...dataset, userNotes: 'hidden note'})).toBe(aiExportOptionsFingerprint(dataset));
    });

    it('recognizes no-op draft feedback without hiding stored custom period changes', () => {
        const base = {
            selectionKind: 'analysis' as const,
            selectionId: 'portfolio.pac_planning' as const,
            detailLevel: 'standard' as const,
            period: {preset: '3m' as const, customAmount: 3, customUnit: 'months' as const},
            responseLanguage: 'English' as const,
            userNotes: ' focus ',
        };

        expect(areAiExportOptionsEqual(base, {...base, period: {...base.period}, userNotes: 'focus'})).toBe(true);
        expect(areAiExportOptionsEqual(base, {...base, period: {...base.period, customAmount: 6}})).toBe(false);
    });
});

// D-P4: a snapshot date typed in the year 24 or 1 must stay there. `Date.UTC(24, …)` reads the year as 1924: the snapshot was
// refused as «invalid», and a period that falls before the year 100 came out a century later.
describe('AI Export period with a year before 100', () => {
    it('resolves a period that ends in the year 24 in the year 24', () => {
        expect(resolveAiExportPeriod('0024-03-31', {preset: '3m', customAmount: 3, customUnit: 'months'})).toEqual({start: '0023-12-31', end: '0024-03-31'});
        expect(resolveAiExportPeriod('0024-03-31', {preset: 'custom', customAmount: 14, customUnit: 'days'})).toEqual({start: '0024-03-17', end: '0024-03-31'});
    });

    it('resolves the first year', () => {
        expect(resolveAiExportPeriod('0001-03-31', {preset: '3m', customAmount: 3, customUnit: 'months'})).toEqual({start: '0000-12-31', end: '0001-03-31'});
    });

    it('goes back across the year 100 without landing in the 1900s', () => {
        expect(resolveAiExportPeriod('0100-01-31', {preset: '3m', customAmount: 3, customUnit: 'months'})).toEqual({start: '0099-10-31', end: '0100-01-31'});
        expect(resolveAiExportPeriod('0100-03-31', {preset: '1y', customAmount: 3, customUnit: 'months'})).toEqual({start: '0099-03-31', end: '0100-03-31'});
    });

    it('still refuses a date that does not exist', () => {
        expect(() => resolveAiExportPeriod('0024-02-30', {preset: '3m', customAmount: 3, customUnit: 'months'})).toThrow(TypeError);
    });
});
