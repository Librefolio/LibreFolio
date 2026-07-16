/**
 * Asset-level AI export prompt catalog (Asset Detail page — Signals panel).
 * Mirrors the shape of the portfolio-level catalog (see ../promptCatalog.ts)
 * but scoped to just 2 entries for a single asset.
 */

export type AssetPromptId = 'asset_snapshot' | 'asset_classify';

export interface AssetPromptDefinition {
    id: AssetPromptId;
    labelKey: string;
    descriptionKey: string;
    /** false only for 'asset_snapshot' — pure data, no role/task/web-research instructions */
    hasInstructions: boolean;
}

export const ASSET_PROMPT_CATALOG: AssetPromptDefinition[] = [
    {
        id: 'asset_snapshot',
        labelKey: 'assetDetail.aiExportMenu.asset_snapshot.label',
        descriptionKey: 'assetDetail.aiExportMenu.asset_snapshot.description',
        hasInstructions: false,
    },
    {
        id: 'asset_classify',
        labelKey: 'assetDetail.aiExportMenu.asset_classify.label',
        descriptionKey: 'assetDetail.aiExportMenu.asset_classify.description',
        hasInstructions: true,
    },
];

export function getAssetPromptDefinition(id: AssetPromptId): AssetPromptDefinition {
    const def = ASSET_PROMPT_CATALOG.find((p) => p.id === id);
    if (!def) throw new Error(`Unknown asset AI export prompt id: ${id}`);
    return def;
}
