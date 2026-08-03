import {browser} from '$app/environment';
import {schemas} from '$lib/api';
import {getClientSessionUserId, registerClientSessionReset} from '$lib/stores/app/clientSession';
import {z} from 'zod';

import {findCompatibleAiExportSelection, selectionsForDomain, type AiExportCatalogCompatibilityResult} from './catalog/compatibility';
import {isAiExportAnalysisId, isAiExportDatasetId, type AiExportDomain, type AiExportSelectionId, type AiExportSelectionKind} from './catalog/shared';
import {AI_EXPORT_DEFAULT_PERIOD, AI_EXPORT_PERIOD_PRESETS, AI_EXPORT_PERIOD_UNITS, normalizeAiExportPeriod, normalizeAiExportUserNotes, type AiExportOptionsSelection} from './aiExportOptions';
import type {AiExportResponseLanguageDisplayName} from './templates/promptRenderer';

export const AI_EXPORT_MEMORY_VERSION = 2 as const;

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
    readonly storage?: AiExportMemoryStorage;
}

interface SaveAiExportMemoryInput {
    readonly memoryKey: AiExportMemoryKey;
    readonly options: AiExportOptionsSelection;
    readonly userNotesDraft?: string;
    readonly copyAnywayFingerprint?: string;
    readonly storage?: AiExportMemoryStorage;
}

const storedMemorySchema = z
    .object({
        version: z.literal(AI_EXPORT_MEMORY_VERSION),
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

function storageFor(storage: AiExportMemoryStorage | undefined): AiExportMemoryStorage | undefined {
    if (storage) return storage;
    return browser ? localStorage : undefined;
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

function isStoredApplicable(stored: StoredAiExportMemory, input: LoadAiExportMemoryInput): stored is StoredAiExportMemory & {selectionId: AiExportSelectionId} {
    if (!isSelectionId(stored.selectionId)) return false;
    const selection = findCompatibleAiExportSelection(input.compatibility, stored.selectionKind, stored.selectionId);
    return selection?.domain === input.domain && selection.supportedDetailLevels.includes(stored.detailLevel);
}

function hydrate(stored: StoredAiExportMemory & {selectionId: AiExportSelectionId}, responseLanguage: AiExportResponseLanguageDisplayName): AiExportMemoryState {
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

function discard(key: string, storage: AiExportMemoryStorage | undefined): void {
    memoryCache.delete(key);
    try {
        storage?.removeItem(key);
    } catch {
        // Restricted storage: cache removal is still effective for this SPA session.
    }
}

export function loadAiExportMemory(input: LoadAiExportMemoryInput): AiExportMemoryState {
    const fallback = fallbackState(input);
    if (input.compatibility.selections.length === 0) return fallback;
    const userId = getClientSessionUserId();
    if (!userId) return fallback;
    const key = buildAiExportMemoryStorageKey(userId, input.memoryKey);
    const storage = storageFor(input.storage);
    const cached = memoryCache.get(key);
    if (cached) return isStoredApplicable(cached, input) ? hydrate(cached, input.responseLanguage) : fallback;

    let raw: string | null;
    try {
        raw = storage?.getItem(key) ?? null;
    } catch {
        return fallback;
    }
    if (raw === null) return fallback;
    let parsed: unknown;
    try {
        parsed = JSON.parse(raw);
    } catch {
        discard(key, storage);
        return fallback;
    }
    const validated = storedMemorySchema.safeParse(parsed);
    if (!validated.success || !isStoredApplicable(validated.data, input)) {
        discard(key, storage);
        return fallback;
    }
    memoryCache.set(key, validated.data);
    return hydrate(validated.data, input.responseLanguage);
}

export function saveAiExportMemory(input: SaveAiExportMemoryInput): void {
    const userId = getClientSessionUserId();
    if (!userId) return;
    const key = buildAiExportMemoryStorageKey(userId, input.memoryKey);
    const storage = storageFor(input.storage);
    let previous = memoryCache.get(key);
    if (!previous) {
        try {
            const raw = storage?.getItem(key);
            if (raw) {
                const parsed = storedMemorySchema.safeParse(JSON.parse(raw));
                if (parsed.success) previous = parsed.data;
            }
        } catch {
            // Invalid or restricted storage is replaced by the current valid draft.
        }
    }
    const notes = input.userNotesDraft !== undefined ? input.userNotesDraft : input.options.selectionKind === 'analysis' ? (normalizeAiExportUserNotes(input.options.selectionKind, input.options.userNotes) ?? '') : (previous?.notes ?? '');
    const stored = storedMemorySchema.parse({
        version: AI_EXPORT_MEMORY_VERSION,
        selectionKind: input.options.selectionKind,
        selectionId: input.options.selectionId,
        detailLevel: input.options.detailLevel,
        period: normalizeAiExportPeriod(input.options.period),
        notes,
        copyAnywayFingerprint: input.copyAnywayFingerprint,
    });
    memoryCache.set(key, stored);
    try {
        storage?.setItem(key, JSON.stringify(stored));
    } catch {
        // In-memory state remains available for this SPA session.
    }
}

registerClientSessionReset('aiExportMemory', clearAiExportMemoryCache);
