/**
 * Asset AI Export Clipboard — builds the single-asset export and copies it to
 * the clipboard. Entry point for the Asset Detail page's Signals panel button.
 */

import {buildAssetAiExport, type AssetExportInput, type AssetExportOptions} from './assetExportBuilder';
import {renderAssetSnapshot, renderAssetClassify} from './assetPromptRenderer';
import {getAssetPromptDefinition, type AssetPromptId} from './assetPromptCatalog';
import {writeExportToClipboard, type ToastFn} from '$lib/utils/clipboard';

export type {ToastFn};

/**
 * Build the single-asset AI export for the given catalog prompt and copy it
 * to the clipboard.
 */
export async function copyAssetAiExport(promptId: AssetPromptId, input: AssetExportInput, options: AssetExportOptions, toast: ToastFn, t: (key: string, opts?: {values?: Record<string, any>}) => string): Promise<void> {
    try {
        const exportData = await buildAssetAiExport(input, options);
        const def = getAssetPromptDefinition(promptId);
        const text = def.hasInstructions ? renderAssetClassify(exportData) : renderAssetSnapshot(exportData);
        const label = t(def.labelKey);

        await writeExportToClipboard(text, toast, t('dashboard.aiExportCopiedGeneric', {values: {label}}));
    } catch (err) {
        console.error('Asset AI export failed:', err);
        toast.error(t('dashboard.aiExportFailed'));
    }
}
