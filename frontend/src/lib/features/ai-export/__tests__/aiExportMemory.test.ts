import {beforeEach, describe, expect, it} from 'vitest';

import {getClientSessionUserId, transitionClientSession} from '$lib/stores/app/clientSession';

import {clearAiExportMemoryCache, buildAiExportMemoryStorageKey, loadAiExportMemory, saveAiExportMemory, type AiExportMemoryDefaults, type AiExportMemoryKey} from '../aiExportMemory';
import {AI_EXPORT_DEFAULT_TECHNICAL_WINDOW, type AiExportHiddenAnalysisTasks, type AiExportOptionsSelection} from '../aiExportOptions';
import {ASSET_AI_EXPORT_TASKS} from '../catalog/assetTasks';
import {BROKER_AI_EXPORT_TASKS} from '../catalog/brokerTasks';
import {FX_AI_EXPORT_TASKS} from '../catalog/fxTasks';
import {PORTFOLIO_AI_EXPORT_TASKS} from '../catalog/portfolioTasks';
import type {AiExportTask, AiExportTaskDefinition} from '../catalog/shared';
import type {AiExportResponseLanguageDisplayName} from '../templates/promptRenderer';

class MemoryStorage implements Storage {
    private readonly values = new Map<string, string>();

    get length(): number {
        return this.values.size;
    }

    clear(): void {
        this.values.clear();
    }

    getItem(key: string): string | null {
        return this.values.get(key) ?? null;
    }

    key(index: number): string | null {
        return Array.from(this.values.keys())[index] ?? null;
    }

    removeItem(key: string): void {
        this.values.delete(key);
    }

    setItem(key: string, value: string): void {
        this.values.set(key, value);
    }
}

interface MemoryScenario {
    readonly key: AiExportMemoryKey;
    readonly definitions: readonly AiExportTaskDefinition[];
    readonly defaults: AiExportMemoryDefaults;
    readonly options: AiExportOptionsSelection;
    readonly userNotesDraft: string;
    readonly hiddenAnalysisTasks?: AiExportHiddenAnalysisTasks;
    readonly expectedDefaultTask?: AiExportTask;
}

let storage: MemoryStorage;
let userSequence = 0;

function transitionToUser(userId: string): void {
    transitionClientSession(null);
    transitionClientSession(userId);
}

function loadScenario(scenario: MemoryScenario, responseLanguage: AiExportResponseLanguageDisplayName = 'English'): AiExportOptionsSelection {
    return loadAiExportMemory({
        memoryKey: scenario.key,
        defaults: scenario.defaults,
        responseLanguage,
        taskDefinitions: scenario.definitions,
        hiddenAnalysisTasks: scenario.hiddenAnalysisTasks,
        storage,
    });
}

function saveScenario(scenario: MemoryScenario): void {
    saveAiExportMemory({
        memoryKey: scenario.key,
        options: scenario.options,
        userNotesDraft: scenario.userNotesDraft,
        taskDefinitions: scenario.definitions,
        hiddenAnalysisTasks: scenario.hiddenAnalysisTasks,
        storage,
    });
}

const scenarios: readonly MemoryScenario[] = [
    {
        key: 'portfolio',
        definitions: PORTFOLIO_AI_EXPORT_TASKS,
        defaults: {task: 'pac_planning', detailLevel: 'standard', renderMode: 'full_prompt', technicalWindow: AI_EXPORT_DEFAULT_TECHNICAL_WINDOW},
        options: {
            task: 'rebalancing',
            detailLevel: 'full',
            renderMode: 'full_prompt',
            responseLanguage: 'English',
            userNotes: 'Portfolio draft',
            webResearch: false,
            technicalWindow: {preset: '6m', customAmount: 3, customUnit: 'months'},
        },
        userNotesDraft: 'Portfolio draft',
    },
    {
        key: 'broker:17',
        definitions: BROKER_AI_EXPORT_TASKS,
        defaults: {task: 'broker_review', detailLevel: 'standard', renderMode: 'full_prompt', technicalWindow: AI_EXPORT_DEFAULT_TECHNICAL_WINDOW},
        options: {
            task: 'broker_cost_efficiency',
            detailLevel: 'compact',
            renderMode: 'full_prompt',
            responseLanguage: 'English',
            userNotes: 'Broker draft',
            webResearch: false,
            technicalWindow: AI_EXPORT_DEFAULT_TECHNICAL_WINDOW,
        },
        userNotesDraft: 'Broker draft',
    },
    {
        key: 'asset:23',
        definitions: ASSET_AI_EXPORT_TASKS,
        defaults: {task: 'asset_snapshot', detailLevel: 'standard', renderMode: 'full_prompt', technicalWindow: AI_EXPORT_DEFAULT_TECHNICAL_WINDOW},
        options: {
            task: 'asset_snapshot',
            detailLevel: 'compact',
            renderMode: 'data_only',
            responseLanguage: 'English',
            userNotes: undefined,
            webResearch: false,
            technicalWindow: {preset: '1y', customAmount: 3, customUnit: 'months'},
        },
        userNotesDraft: 'Hidden Snapshot draft',
        hiddenAnalysisTasks: ['asset_snapshot', 'asset_pac_timing_context'],
        expectedDefaultTask: 'asset_trend_analysis',
    },
    {
        key: 'fx:EUR-USD',
        definitions: FX_AI_EXPORT_TASKS,
        defaults: {task: 'fx_trend_review', detailLevel: 'standard', renderMode: 'full_prompt', technicalWindow: AI_EXPORT_DEFAULT_TECHNICAL_WINDOW},
        options: {
            task: 'fx_conversion_timing_context',
            detailLevel: 'full',
            renderMode: 'full_prompt',
            responseLanguage: 'English',
            userNotes: 'FX draft',
            webResearch: false,
            technicalWindow: {preset: 'custom', customAmount: 8, customUnit: 'weeks'},
        },
        userNotesDraft: 'FX draft',
    },
];

describe('AI Export memory', () => {
    beforeEach(() => {
        storage = new MemoryStorage();
        clearAiExportMemoryCache();
        transitionToUser(`memory-test-${++userSequence}`);
    });

    it('isolates all supported page contexts per authenticated user', () => {
        const userA = getClientSessionUserId();
        if (!userA) throw new Error('Expected authenticated test user');

        for (const scenario of scenarios) saveScenario(scenario);
        for (const scenario of scenarios) expect(loadScenario(scenario)).toEqual({...scenario.options, userNotes: scenario.userNotesDraft, webResearch: false});

        transitionToUser(`${userA}-other`);
        for (const scenario of scenarios) {
            expect(loadScenario(scenario)).toEqual({
                ...scenario.defaults,
                task: scenario.expectedDefaultTask ?? scenario.defaults.task,
                responseLanguage: 'English',
                userNotes: '',
                webResearch: false,
            });
        }

        transitionToUser(userA);
        for (const scenario of scenarios) expect(loadScenario(scenario)).toEqual({...scenario.options, userNotes: scenario.userNotesDraft, webResearch: false});
    });

    it('restores persisted storage after module memory is cleared', () => {
        const scenario = scenarios[0];
        saveScenario(scenario);

        clearAiExportMemoryCache();

        expect(loadScenario(scenario)).toEqual({...scenario.options, userNotes: scenario.userNotesDraft, webResearch: false});
    });

    it('rejects malformed, extra, unknown, and cross-domain stored values', () => {
        const scenario = scenarios[0];
        const userId = getClientSessionUserId();
        if (!userId) throw new Error('Expected authenticated test user');
        const storageKey = buildAiExportMemoryStorageKey(userId, scenario.key);
        const malformedValues = [
            '{not-json',
            JSON.stringify({version: 1, task: 'not_a_task', detailLevel: 'standard', renderMode: 'full_prompt', notes: ''}),
            JSON.stringify({version: 1, task: 'pac_planning', detailLevel: 'unknown', renderMode: 'full_prompt', notes: ''}),
            JSON.stringify({version: 1, task: 'pac_planning', detailLevel: 'standard', renderMode: 'unknown', notes: ''}),
            JSON.stringify({version: 1, task: 'asset_snapshot', detailLevel: 'standard', renderMode: 'full_prompt', notes: ''}),
            JSON.stringify({version: 1, task: 'pac_planning', detailLevel: 'standard', renderMode: 'full_prompt', notes: '', extra: true}),
        ];

        for (const raw of malformedValues) {
            storage.setItem(storageKey, raw);
            clearAiExportMemoryCache();

            expect(loadScenario(scenario)).toEqual({...scenario.defaults, responseLanguage: 'English', userNotes: '', webResearch: false});
            expect(storage.getItem(storageKey)).toBeNull();
        }
    });

    it('restores Snapshot and analysis render modes exactly', () => {
        const snapshotScenario = scenarios[2];
        saveScenario(snapshotScenario);
        clearAiExportMemoryCache();
        expect(loadScenario(snapshotScenario)).toMatchObject({
            task: 'asset_snapshot',
            detailLevel: 'compact',
            renderMode: 'data_only',
            userNotes: 'Hidden Snapshot draft',
        });

        const analysisScenario: MemoryScenario = {
            ...snapshotScenario,
            options: {
                task: 'asset_trend_analysis',
                detailLevel: 'full',
                renderMode: 'full_prompt',
                responseLanguage: 'English',
                userNotes: 'Analysis draft',
                webResearch: false,
                technicalWindow: {preset: 'custom', customAmount: 18, customUnit: 'months'},
            },
            userNotesDraft: 'Analysis draft',
        };
        saveScenario(analysisScenario);
        clearAiExportMemoryCache();
        expect(loadScenario(analysisScenario)).toMatchObject({
            task: 'asset_trend_analysis',
            detailLevel: 'full',
            renderMode: 'full_prompt',
            userNotes: 'Analysis draft',
        });
    });

    it('rejects a previously saved hidden analysis and falls back to the first visible analysis', () => {
        const scenario = scenarios[2];
        const userId = getClientSessionUserId();
        if (!userId) throw new Error('Expected authenticated test user');
        const storageKey = buildAiExportMemoryStorageKey(userId, scenario.key);
        storage.setItem(
            storageKey,
            JSON.stringify({
                version: 1,
                task: 'asset_pac_timing_context',
                detailLevel: 'full',
                renderMode: 'full_prompt',
                notes: 'Legacy hidden draft',
            }),
        );

        expect(
            loadAiExportMemory({
                memoryKey: scenario.key,
                defaults: {task: 'asset_snapshot', detailLevel: 'standard', renderMode: 'full_prompt'},
                responseLanguage: 'English',
                taskDefinitions: scenario.definitions,
                hiddenAnalysisTasks: scenario.hiddenAnalysisTasks,
                storage,
            }),
        ).toEqual({
            task: 'asset_trend_analysis',
            detailLevel: 'standard',
            renderMode: 'full_prompt',
            responseLanguage: 'English',
            userNotes: '',
            webResearch: false,
            technicalWindow: AI_EXPORT_DEFAULT_TECHNICAL_WINDOW,
        });
        expect(storage.getItem(storageKey)).toBeNull();
    });

    it('keeps late old-context saves isolated from the newly active key', () => {
        const oldScenario: MemoryScenario = {
            ...scenarios[2],
            options: {
                task: 'asset_trend_analysis',
                detailLevel: 'full',
                renderMode: 'full_prompt',
                responseLanguage: 'English',
                userNotes: 'Old asset draft',
                webResearch: false,
                technicalWindow: {preset: '6m', customAmount: 3, customUnit: 'months'},
            },
            userNotesDraft: 'Old asset draft',
        };
        const newScenario: MemoryScenario = {
            ...oldScenario,
            key: 'asset:24',
            options: {
                ...oldScenario.options,
                detailLevel: 'compact',
                userNotes: 'New asset draft',
            },
            userNotesDraft: 'New asset draft',
        };
        saveScenario(newScenario);

        saveScenario({
            ...oldScenario,
            options: {...oldScenario.options, userNotes: 'Late old asset draft'},
            userNotesDraft: 'Late old asset draft',
        });

        expect(loadScenario(newScenario)).toMatchObject({
            detailLevel: 'compact',
            userNotes: 'New asset draft',
        });
        expect(loadScenario(oldScenario)).toMatchObject({
            detailLevel: 'full',
            userNotes: 'Late old asset draft',
        });
    });

    it('always overwrites response language from the current locale and disables web research', () => {
        const scenario: MemoryScenario = {
            ...scenarios[3],
            options: {
                ...scenarios[3].options,
                responseLanguage: 'English',
                webResearch: true,
            },
        };
        saveScenario(scenario);
        clearAiExportMemoryCache();

        expect(loadScenario(scenario, 'Italian')).toMatchObject({
            responseLanguage: 'Italian',
            webResearch: false,
        });
    });
});
