import {beforeEach, describe, expect, it} from 'vitest';

import {transitionClientSession} from '$lib/stores/app/clientSession';

import {buildAiExportMemoryStorageKey, clearAiExportMemoryCache, loadAiExportMemory, saveAiExportMemory} from '../aiExportMemory';
import {compatibilityFixture} from './runtimeFixtures';

class MemoryStorage implements Storage {
    private readonly values = new Map<string, string>();
    get length() {
        return this.values.size;
    }
    clear() {
        this.values.clear();
    }
    getItem(key: string) {
        return this.values.get(key) ?? null;
    }
    key(index: number) {
        return [...this.values.keys()][index] ?? null;
    }
    removeItem(key: string) {
        this.values.delete(key);
    }
    setItem(key: string, value: string) {
        this.values.set(key, value);
    }
}

let storage: MemoryStorage;

beforeEach(() => {
    storage = new MemoryStorage();
    clearAiExportMemoryCache();
    transitionClientSession(null);
    transitionClientSession('user-1');
});

describe('AI Export memory', () => {
    it('stores selection, detail, period, notes, and warning override per entity', () => {
        const options = {
            selectionKind: 'analysis' as const,
            selectionId: 'asset.drawdown_recovery' as const,
            detailLevel: 'full' as const,
            period: {preset: 'custom' as const, customAmount: 9, customUnit: 'weeks' as const},
            responseLanguage: 'Italian' as const,
            userNotes: 'Recovery focus',
        };
        saveAiExportMemory({memoryKey: 'asset:7', options, copyAnywayFingerprint: 'fp-1', storage});

        const loaded = loadAiExportMemory({
            memoryKey: 'asset:7',
            domain: 'asset',
            compatibility: compatibilityFixture(),
            responseLanguage: 'French',
            defaultSelectionId: 'asset.trend_analysis',
            storage,
        });

        expect(loaded.options).toMatchObject({...options, responseLanguage: 'French'});
        expect(loaded.copyAnywayFingerprint).toBe('fp-1');
    });

    it('ignores old memory schema versions', () => {
        const key = buildAiExportMemoryStorageKey('user-1', 'portfolio');
        storage.setItem(key, JSON.stringify({version: 1, task: 'pac_planning'}));

        const loaded = loadAiExportMemory({
            memoryKey: 'portfolio',
            domain: 'portfolio',
            compatibility: compatibilityFixture(),
            responseLanguage: 'English',
            defaultSelectionId: 'portfolio.pac_planning',
            storage,
        });

        expect(loaded.options.selectionId).toBe('portfolio.pac_planning');
        expect(storage.getItem(key)).toBeNull();
    });
});
