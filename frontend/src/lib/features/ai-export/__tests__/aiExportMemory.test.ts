import {beforeEach, describe, expect, it} from 'vitest';

import {transitionClientSession} from '$lib/stores/app/clientSession';

import {AI_EXPORT_MEMORY_TTL_MS, clearAiExportMemoryCache, loadAiExportMemory, saveAiExportMemory} from '../aiExportMemory';
import {emptyAiExportCompatibility} from '../catalog/compatibility';
import {compatibilityFixture} from './runtimeFixtures';

beforeEach(() => {
    transitionClientSession(null);
    clearAiExportMemoryCache();
    transitionClientSession('user-1');
});

describe('AI Export memory', () => {
    it('stores selection, detail, period, notes, and warning override inside the TTL', () => {
        const options = {
            selectionKind: 'analysis' as const,
            selectionId: 'asset.position_review' as const,
            detailLevel: 'full' as const,
            period: {preset: 'custom' as const, customAmount: 9, customUnit: 'weeks' as const},
            responseLanguage: 'Italian' as const,
            userNotes: 'Recovery focus',
        };
        saveAiExportMemory({memoryKey: 'asset:7', options, copyAnywayFingerprint: 'fp-1', now: 1_000});

        const loaded = loadAiExportMemory({
            memoryKey: 'asset:7',
            domain: 'asset',
            compatibility: compatibilityFixture(),
            responseLanguage: 'French',
            defaultSelectionId: 'asset.market_analysis',
            now: 1_000 + AI_EXPORT_MEMORY_TTL_MS - 1,
        });

        expect(loaded.options).toMatchObject({...options, responseLanguage: 'French'});
        expect(loaded.userNotesDraft).toBe('Recovery focus');
        expect(loaded.copyAnywayFingerprint).toBe('fp-1');
    });

    it('expires every draft parameter after ten minutes and reopens with defaults', () => {
        saveAiExportMemory({
            memoryKey: 'portfolio',
            options: {
                selectionKind: 'analysis',
                selectionId: 'portfolio.rebalancing',
                detailLevel: 'full',
                period: {preset: '1y', customAmount: 3, customUnit: 'months'},
                responseLanguage: 'English',
                userNotes: 'Do not survive expiry',
            },
            copyAnywayFingerprint: 'expired-fingerprint',
            now: 5_000,
        });

        const loaded = loadAiExportMemory({
            memoryKey: 'portfolio',
            domain: 'portfolio',
            compatibility: compatibilityFixture(),
            responseLanguage: 'Italian',
            defaultSelectionId: 'portfolio.pac_planning',
            now: 5_000 + AI_EXPORT_MEMORY_TTL_MS,
        });

        expect(loaded.options).toMatchObject({
            selectionKind: 'analysis',
            selectionId: 'portfolio.pac_planning',
            detailLevel: 'standard',
            period: {preset: '3m'},
            responseLanguage: 'Italian',
        });
        expect(loaded.userNotesDraft).toBe('');
        expect(loaded.copyAnywayFingerprint).toBeUndefined();
    });

    it('clears all drafts across logout and the next login, including the same account', () => {
        saveAiExportMemory({
            memoryKey: 'portfolio',
            options: {
                selectionKind: 'analysis',
                selectionId: 'portfolio.rebalancing',
                detailLevel: 'full',
                period: {preset: '1y', customAmount: 3, customUnit: 'months'},
                responseLanguage: 'English',
                userNotes: 'Previous login',
            },
            now: 2_000,
        });

        transitionClientSession(null);
        transitionClientSession('user-1');

        const loaded = loadAiExportMemory({
            memoryKey: 'portfolio',
            domain: 'portfolio',
            compatibility: compatibilityFixture(),
            responseLanguage: 'English',
            defaultSelectionId: 'portfolio.pac_planning',
            now: 2_001,
        });

        expect(loaded.options.selectionId).toBe('portfolio.pac_planning');
        expect(loaded.options.detailLevel).toBe('standard');
        expect(loaded.userNotesDraft).toBe('');
    });

    it('keeps contexts isolated and preserves hidden Analysis notes only within the active login', () => {
        const hiddenNote = 'Analysis-only allocation constraints';
        saveAiExportMemory({
            memoryKey: 'portfolio',
            options: {
                selectionKind: 'analysis',
                selectionId: 'portfolio.rebalancing',
                detailLevel: 'standard',
                period: {preset: '3m', customAmount: 3, customUnit: 'months'},
                responseLanguage: 'English',
                userNotes: hiddenNote,
            },
            now: 3_000,
        });
        saveAiExportMemory({
            memoryKey: 'portfolio',
            options: {
                selectionKind: 'dataset',
                selectionId: 'portfolio.overview_and_history',
                detailLevel: 'compact',
                period: {preset: '3m', customAmount: 3, customUnit: 'months'},
                responseLanguage: 'English',
            },
            now: 3_001,
        });
        saveAiExportMemory({
            memoryKey: 'asset:7',
            options: {
                selectionKind: 'analysis',
                selectionId: 'asset.position_review',
                detailLevel: 'full',
                period: {preset: '1y', customAmount: 3, customUnit: 'months'},
                responseLanguage: 'English',
                userNotes: 'Asset-only note',
            },
            now: 3_001,
        });

        const portfolio = loadAiExportMemory({
            memoryKey: 'portfolio',
            domain: 'portfolio',
            compatibility: compatibilityFixture(),
            responseLanguage: 'English',
            defaultSelectionId: 'portfolio.pac_planning',
            now: 3_002,
        });
        const asset = loadAiExportMemory({
            memoryKey: 'asset:7',
            domain: 'asset',
            compatibility: compatibilityFixture(),
            responseLanguage: 'English',
            defaultSelectionId: 'asset.market_analysis',
            now: 3_002,
        });

        expect(portfolio.options).toMatchObject({
            selectionKind: 'dataset',
            selectionId: 'portfolio.overview_and_history',
            detailLevel: 'compact',
        });
        expect(portfolio.options.userNotes).toBeUndefined();
        expect(portfolio.userNotesDraft).toBe(hiddenNote);
        expect(asset.options.selectionId).toBe('asset.position_review');
        expect(asset.userNotesDraft).toBe('Asset-only note');
    });

    it('waits for async catalog hydration without discarding an unexpired in-memory draft', () => {
        saveAiExportMemory({
            memoryKey: 'portfolio',
            options: {
                selectionKind: 'analysis',
                selectionId: 'portfolio.rebalancing',
                detailLevel: 'full',
                period: {preset: '1y', customAmount: 3, customUnit: 'months'},
                responseLanguage: 'English',
                userNotes: 'Keep until the catalog resolves',
            },
            now: 4_000,
        });

        const pendingCatalog = loadAiExportMemory({
            memoryKey: 'portfolio',
            domain: 'portfolio',
            compatibility: emptyAiExportCompatibility(),
            responseLanguage: 'English',
            defaultSelectionId: 'portfolio.pac_planning',
            now: 4_001,
        });
        const hydratedCatalog = loadAiExportMemory({
            memoryKey: 'portfolio',
            domain: 'portfolio',
            compatibility: compatibilityFixture(),
            responseLanguage: 'English',
            defaultSelectionId: 'portfolio.pac_planning',
            now: 4_002,
        });

        expect(pendingCatalog.options.selectionId).toBe('portfolio.pac_planning');
        expect(hydratedCatalog.options.selectionId).toBe('portfolio.rebalancing');
        expect(hydratedCatalog.userNotesDraft).toBe('Keep until the catalog resolves');
    });
});
