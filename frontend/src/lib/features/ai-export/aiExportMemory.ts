import {browser} from '$app/environment';
import {schemas} from '$lib/api';
import {getClientSessionUserId, registerClientSessionReset} from '$lib/stores/app/clientSession';
import {z} from 'zod';

import type {AiExportHiddenAnalysisTasks, AiExportOptionsSelection} from './aiExportOptions';
import {getAiExportSnapshotTask} from './aiExportOptions';
import {AI_EXPORT_RENDER_MODES, type AiExportDetailLevel, type AiExportRenderMode, type AiExportTask, type AiExportTaskDefinition} from './catalog/shared';
import type {AiExportResponseLanguageDisplayName} from './templates/promptRenderer';

export const AI_EXPORT_MEMORY_VERSION = 1 as const;

export type AiExportMemoryKey = 'portfolio' | `broker:${number}` | `asset:${number}` | `fx:${string}`;

export type AiExportMemoryStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

export interface AiExportMemoryDefaults {
    readonly task: AiExportTask;
    readonly detailLevel: AiExportDetailLevel;
    readonly renderMode: AiExportRenderMode;
    readonly userNotes?: string;
}

interface LoadAiExportMemoryInput {
    readonly memoryKey: AiExportMemoryKey;
    readonly defaults: AiExportMemoryDefaults;
    readonly responseLanguage: AiExportResponseLanguageDisplayName;
    readonly taskDefinitions: readonly AiExportTaskDefinition[];
    readonly hiddenAnalysisTasks?: AiExportHiddenAnalysisTasks;
    readonly storage?: AiExportMemoryStorage;
}

interface SaveAiExportMemoryInput {
    readonly memoryKey: AiExportMemoryKey;
    readonly options: AiExportOptionsSelection;
    readonly userNotesDraft: string;
    readonly taskDefinitions: readonly AiExportTaskDefinition[];
    readonly hiddenAnalysisTasks?: AiExportHiddenAnalysisTasks;
    readonly storage?: AiExportMemoryStorage;
}

const storedMemorySchema = z
    .object({
        version: z.literal(AI_EXPORT_MEMORY_VERSION),
        task: schemas.AiExportTask,
        detailLevel: schemas.AiExportDetailLevel,
        renderMode: z.enum(AI_EXPORT_RENDER_MODES),
        notes: z.string(),
    })
    .strict();

type StoredAiExportMemory = z.infer<typeof storedMemorySchema>;

const memoryCache = new Map<string, StoredAiExportMemory>();

export function buildAiExportMemoryStorageKey(userId: string, memoryKey: AiExportMemoryKey): string {
    return `lf_${userId}_ai_export_v${AI_EXPORT_MEMORY_VERSION}_${encodeURIComponent(memoryKey)}`;
}

export function clearAiExportMemoryCache(): void {
    memoryCache.clear();
}

function getStorage(storage: AiExportMemoryStorage | undefined): AiExportMemoryStorage | undefined {
    if (storage) return storage;
    if (!browser) return undefined;
    return localStorage;
}

function defaultOptions(defaults: AiExportMemoryDefaults, responseLanguage: AiExportResponseLanguageDisplayName, taskDefinitions: readonly AiExportTaskDefinition[], hiddenAnalysisTasks: AiExportHiddenAnalysisTasks): AiExportOptionsSelection {
    const domain = taskDefinitions[0]?.domain;
    const snapshotTask = domain ? getAiExportSnapshotTask(domain) : undefined;
    const requestedDefinition = taskDefinitions.find((definition) => definition.backendTask === defaults.task);
    const fallbackDefinition =
        defaults.renderMode === 'data_only'
            ? taskDefinitions.find((definition) => definition.backendTask === snapshotTask)
            : requestedDefinition && !hiddenAnalysisTasks.includes(requestedDefinition.id)
              ? requestedDefinition
              : taskDefinitions.find((definition) => !hiddenAnalysisTasks.includes(definition.id));

    return {
        task: fallbackDefinition?.id ?? defaults.task,
        detailLevel: fallbackDefinition?.supportedDetailLevels.includes(defaults.detailLevel) ? defaults.detailLevel : (fallbackDefinition?.defaultDetailLevel ?? defaults.detailLevel),
        renderMode: defaults.renderMode,
        responseLanguage,
        userNotes: defaults.userNotes ?? '',
        webResearch: false,
    };
}

function isStoredMemoryApplicable(stored: StoredAiExportMemory, taskDefinitions: readonly AiExportTaskDefinition[], hiddenAnalysisTasks: AiExportHiddenAnalysisTasks): boolean {
    const definition = taskDefinitions.find((candidate) => candidate.backendTask === stored.task);
    if (!definition || !definition.supportedDetailLevels.includes(stored.detailLevel) || !definition.renderModes.includes(stored.renderMode)) return false;
    if (stored.renderMode === 'full_prompt' && hiddenAnalysisTasks.includes(definition.id)) return false;
    return stored.renderMode !== 'data_only' || stored.task === getAiExportSnapshotTask(definition.domain);
}

function hydrateStoredMemory(stored: StoredAiExportMemory, responseLanguage: AiExportResponseLanguageDisplayName): AiExportOptionsSelection {
    return {
        task: stored.task,
        detailLevel: stored.detailLevel,
        renderMode: stored.renderMode,
        responseLanguage,
        userNotes: stored.notes,
        webResearch: false,
    };
}

function discardStoredMemory(storageKey: string, storage: AiExportMemoryStorage | undefined): void {
    memoryCache.delete(storageKey);
    try {
        storage?.removeItem(storageKey);
    } catch {
        // Storage can be unavailable in private/restricted browser contexts.
    }
}

export function loadAiExportMemory(input: LoadAiExportMemoryInput): AiExportOptionsSelection {
    const hiddenAnalysisTasks = input.hiddenAnalysisTasks ?? [];
    const fallback = defaultOptions(input.defaults, input.responseLanguage, input.taskDefinitions, hiddenAnalysisTasks);
    const userId = getClientSessionUserId();
    if (!userId) return fallback;

    const storageKey = buildAiExportMemoryStorageKey(userId, input.memoryKey);
    const cached = memoryCache.get(storageKey);
    if (cached) {
        if (isStoredMemoryApplicable(cached, input.taskDefinitions, hiddenAnalysisTasks)) return hydrateStoredMemory(cached, input.responseLanguage);
        discardStoredMemory(storageKey, getStorage(input.storage));
        return fallback;
    }

    const storage = getStorage(input.storage);
    let raw: string | null = null;
    try {
        raw = storage?.getItem(storageKey) ?? null;
    } catch {
        return fallback;
    }
    if (raw === null) return fallback;

    let parsed: unknown;
    try {
        parsed = JSON.parse(raw);
    } catch {
        discardStoredMemory(storageKey, storage);
        return fallback;
    }

    const result = storedMemorySchema.safeParse(parsed);
    if (!result.success || !isStoredMemoryApplicable(result.data, input.taskDefinitions, hiddenAnalysisTasks)) {
        discardStoredMemory(storageKey, storage);
        return fallback;
    }

    memoryCache.set(storageKey, result.data);
    return hydrateStoredMemory(result.data, input.responseLanguage);
}

export function saveAiExportMemory(input: SaveAiExportMemoryInput): void {
    const userId = getClientSessionUserId();
    if (!userId) return;

    const stored = storedMemorySchema.safeParse({
        version: AI_EXPORT_MEMORY_VERSION,
        task: input.options.task,
        detailLevel: input.options.detailLevel,
        renderMode: input.options.renderMode,
        notes: input.userNotesDraft,
    });
    if (!stored.success || !isStoredMemoryApplicable(stored.data, input.taskDefinitions, input.hiddenAnalysisTasks ?? [])) return;

    const storageKey = buildAiExportMemoryStorageKey(userId, input.memoryKey);
    memoryCache.set(storageKey, stored.data);
    try {
        getStorage(input.storage)?.setItem(storageKey, JSON.stringify(stored.data));
    } catch {
        // In-memory draft remains available for this SPA session.
    }
}

registerClientSessionReset('aiExportMemory', clearAiExportMemoryCache);
