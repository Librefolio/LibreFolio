/**
 * FX-pair AI export prompt catalog (FX Detail page — Signals panel).
 * Mirrors the shape of the asset-level catalog (see ../asset/assetPromptCatalog.ts)
 * but scoped to just 2 entries for a single FX pair.
 */

import type {ComponentType} from 'svelte';
import {Camera, TrendingUp} from 'lucide-svelte';

export type FxPromptId = 'fx_snapshot' | 'fx_trend';

export interface FxPromptDefinition {
    id: FxPromptId;
    labelKey: string;
    descriptionKey: string;
    /** false only for 'fx_snapshot' — pure data, no role/task/web-research instructions */
    hasInstructions: boolean;
    /** Dropdown icon — distinguishes entries at a glance; see AiExportMenu.svelte */
    icon: ComponentType;
}

export const FX_PROMPT_CATALOG: FxPromptDefinition[] = [
    {
        id: 'fx_snapshot',
        labelKey: 'fxDetail.aiExportMenu.fx_snapshot.label',
        descriptionKey: 'fxDetail.aiExportMenu.fx_snapshot.description',
        hasInstructions: false,
        icon: Camera,
    },
    {
        id: 'fx_trend',
        labelKey: 'fxDetail.aiExportMenu.fx_trend.label',
        descriptionKey: 'fxDetail.aiExportMenu.fx_trend.description',
        hasInstructions: true,
        icon: TrendingUp,
    },
];

export function getFxPromptDefinition(id: FxPromptId): FxPromptDefinition {
    const def = FX_PROMPT_CATALOG.find((p) => p.id === id);
    if (!def) throw new Error(`Unknown FX AI export prompt id: ${id}`);
    return def;
}
