import {browser} from '$app/environment';
import {schemas} from '$lib/api';
import {getClientSessionUserId, registerClientSessionReset} from '$lib/stores/app/clientSession';
import {z} from 'zod';

import {findCompatibleAiExportSelection, selectionsForDomain, type AiExportCatalogCompatibilityResult} from './catalog/compatibility';
import {isAiExportAnalysisId, isAiExportDatasetId, type AiExportDomain, type AiExportSelectionId, type AiExportSelectionKind} from './catalog/shared';
import {AI_EXPORT_DEFAULT_PERIOD, AI_EXPORT_PERIOD_PRESETS, AI_EXPORT_PERIOD_UNITS, normalizeAiExportPeriod, normalizeAiExportUserNotes, type AiExportOptionsSelection} from './aiExportOptions';
import type {AiExportResponseLanguageDisplayName} from './templates/promptRenderer';

export const AI_EXPORT_MEMORY_TTL_MS = 10 * 60 * 1_000;

export type AiExportMemoryKey = 'portfolio' | `broker:${number}` | `asset:${number}` | `fx:${string}`;
export type AiExportMemoryStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

export interface AiExportMemoryState {
    readonly options: AiExportOptionsSelection;
    readonly userNotesDraft: string;
    readonly copyAnywayFingerprint?: string;
}

interface LoadAiExportMemoryInput {
    readonly memoryKey: AiExportMemoryKey;
    readonly domain: AiExportDomain;
    readonly compatibility: AiExportCatalogCompatibilityResult;
    readonly responseLanguage: AiExportResponseLanguageDisplayName;
    readonly defaultSelectionId: AiExportSelectionId;
    readonly now?: number;
    readonly storage?: AiExportMemoryStorage;
}

interface SaveAiExportMemoryInput {
    readonly memoryKey: AiExportMemoryKey;
    readonly options: AiExportOptionsSelection;
    readonly userNotesDraft?: string;
    readonly copyAnywayFingerprint?: string;
    readonly now?: number;
    readonly storage?: AiExportMemoryStorage;
}

const storedMemorySchema = z
    .object({
        selectionKind: z.enum(['dataset', 'analysis']),
        selectionId: z.string(),
        detailLevel: schemas.AiExportDetailLevel,
        period: z
            .object({
                preset: z.enum(AI_EXPORT_PERIOD_PRESETS),
                customAmount: z.number().int().positive(),
                customUnit: z.enum(AI_EXPORT_PERIOD_UNITS),
            })
            .strict(),
        notes: z.string(),
        copyAnywayFingerprint: z.string().optional(),
        savedAt: z.number().finite().nonnegative(),
    })
    .strict();

type StoredAiExportMemory = z.infer<typeof storedMemorySchema>;
type ApplicableStoredAiExportMemory = StoredAiExportMemory & {selectionId: AiExportSelectionId};

const memoryCache = new Map<string, StoredAiExportMemory>();

function buildCacheKey(userId: string, memoryKey: AiExportMemoryKey): string {
    return `lf_${userId}_ai_export_session_${encodeURIComponent(memoryKey)}`;
}

export function clearAiExportMemoryCache(): void {
    memoryCache.clear();
}

function clearAiExportMemoryState(): void {
    memoryCache.clear();
    if (!browser) return;
    try {
        for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
            const key = sessionStorage.key(index);
            if (key?.includes('_ai_export_session_')) sessionStorage.removeItem(key);
        }
        for (let index = localStorage.length - 1; index >= 0; index -= 1) {
            const key = localStorage.key(index);
            if (key?.includes('_ai_export_v2_') || key?.includes('_ai_export_v3_')) localStorage.removeItem(key);
        }
    } catch {
        // Restricted browser storage cannot retain a usable AI Export draft anyway.
    }
}

function storageFor(storage: AiExportMemoryStorage | undefined): AiExportMemoryStorage | undefined {
    if (storage) return storage;
    return browser ? sessionStorage : undefined;
}

function discard(key: string, storage: AiExportMemoryStorage | undefined): void {
    memoryCache.delete(key);
    try {
        storage?.removeItem(key);
    } catch {
        // In-memory removal still enforces expiry and session reset.
    }
}

function readStored(key: string, storage: AiExportMemoryStorage | undefined): StoredAiExportMemory | undefined {
    let raw: string | null;
    try {
        raw = storage?.getItem(key) ?? null;
    } catch {
        return undefined;
    }
    if (raw === null) return undefined;
    try {
        const parsed = storedMemorySchema.safeParse(JSON.parse(raw));
        if (parsed.success) return parsed.data;
    } catch {
        // Invalid JSON is discarded below.
    }
    discard(key, storage);
    return undefined;
}

function kindForId(id: AiExportSelectionId): AiExportSelectionKind {
    return isAiExportDatasetId(id) ? 'dataset' : 'analysis';
}

function isSelectionId(value: string): value is AiExportSelectionId {
    return isAiExportDatasetId(value) || isAiExportAnalysisId(value);
}

function fallbackState(input: LoadAiExportMemoryInput): AiExportMemoryState {
    const requestedKind = kindForId(input.defaultSelectionId);
    const requested = findCompatibleAiExportSelection(input.compatibility, requestedKind, input.defaultSelectionId);
    const selection = requested?.domain === input.domain ? requested : (selectionsForDomain(input.compatibility, input.domain, 'analysis')[0] ?? selectionsForDomain(input.compatibility, input.domain, 'dataset')[0]);
    if (!selection) {
        return {
            options: {
                selectionKind: requestedKind,
                selectionId: input.defaultSelectionId,
                detailLevel: 'standard',
                period: AI_EXPORT_DEFAULT_PERIOD,
                responseLanguage: input.responseLanguage,
            },
            userNotesDraft: '',
        };
    }
    return {
        options: {
            selectionKind: selection.kind,
            selectionId: selection.id,
            detailLevel: selection.supportedDetailLevels.includes('standard') ? 'standard' : selection.supportedDetailLevels[0],
            period: AI_EXPORT_DEFAULT_PERIOD,
            responseLanguage: input.responseLanguage,
        },
        userNotesDraft: '',
    };
}

function isStoredApplicable(stored: StoredAiExportMemory, input: LoadAiExportMemoryInput): stored is ApplicableStoredAiExportMemory {
    if (!isSelectionId(stored.selectionId)) return false;
    const selection = findCompatibleAiExportSelection(input.compatibility, stored.selectionKind, stored.selectionId);
    return selection?.domain === input.domain && selection.supportedDetailLevels.includes(stored.detailLevel);
}

function isExpired(stored: StoredAiExportMemory, now: number): boolean {
    return now - stored.savedAt >= AI_EXPORT_MEMORY_TTL_MS;
}

function hydrate(stored: ApplicableStoredAiExportMemory, responseLanguage: AiExportResponseLanguageDisplayName): AiExportMemoryState {
    return {
        options: {
            selectionKind: stored.selectionKind,
            selectionId: stored.selectionId,
            detailLevel: stored.detailLevel,
            period: normalizeAiExportPeriod(stored.period),
            responseLanguage,
            userNotes: normalizeAiExportUserNotes(stored.selectionKind, stored.notes),
        },
        userNotesDraft: stored.notes,
        copyAnywayFingerprint: stored.copyAnywayFingerprint,
    };
}

export function loadAiExportMemory(input: LoadAiExportMemoryInput): AiExportMemoryState {
    const fallback = fallbackState(input);
    if (input.compatibility.selections.length === 0) return fallback;
    const userId = getClientSessionUserId();
    if (!userId) return fallback;

    const key = buildCacheKey(userId, input.memoryKey);
    const storage = storageFor(input.storage);
    const stored = memoryCache.get(key) ?? readStored(key, storage);
    if (!stored) return fallback;
    if (isExpired(stored, input.now ?? Date.now()) || !isStoredApplicable(stored, input)) {
        discard(key, storage);
        return fallback;
    }
    memoryCache.set(key, stored);
    return hydrate(stored, input.responseLanguage);
}

export function saveAiExportMemory(input: SaveAiExportMemoryInput): void {
    const userId = getClientSessionUserId();
    if (!userId) return;

    const key = buildCacheKey(userId, input.memoryKey);
    const storage = storageFor(input.storage);
    const now = input.now ?? Date.now();
    const cached = memoryCache.get(key) ?? readStored(key, storage);
    const previous = cached && !isExpired(cached, now) ? cached : undefined;
    if (cached && !previous) discard(key, storage);
    const notes = input.userNotesDraft !== undefined ? input.userNotesDraft : input.options.selectionKind === 'analysis' ? (normalizeAiExportUserNotes(input.options.selectionKind, input.options.userNotes) ?? '') : (previous?.notes ?? '');

    const stored = storedMemorySchema.parse({
        selectionKind: input.options.selectionKind,
        selectionId: input.options.selectionId,
        detailLevel: input.options.detailLevel,
        period: normalizeAiExportPeriod(input.options.period),
        notes,
        copyAnywayFingerprint: input.copyAnywayFingerprint,
        savedAt: now,
    });
    memoryCache.set(key, stored);
    try {
        storage?.setItem(key, JSON.stringify(stored));
    } catch {
        // The in-memory cache still works for this SPA lifetime.
    }
}

registerClientSessionReset('aiExportMemory', clearAiExportMemoryState);
