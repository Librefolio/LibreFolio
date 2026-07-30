import {describe, expect, it} from 'vitest';

import {aiExportOptionsFingerprint, areAiExportOptionsEqual, estimateAiExportTokenSeverity, normalizeAiExportPeriod, reconcileAiExportOptions, resolveAiExportPeriod} from '../aiExportOptions';
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
        expect(estimateAiExportTokenSeverity(7_999)).toBe('normal');
        expect(estimateAiExportTokenSeverity(8_000)).toBe('warning');
        expect(estimateAiExportTokenSeverity(16_000)).toBe('large');
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
