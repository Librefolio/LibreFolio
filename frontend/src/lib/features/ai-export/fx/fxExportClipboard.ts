/**
 * FX AI Export Clipboard — builds the single-pair export and copies it to the
 * clipboard. Entry point for the FX Detail page's Signals panel button.
 */

import {writeExportToClipboard, type ToastFn} from '$lib/utils/clipboard';
import {buildFxAiExport, type FxExportInput, type FxExportOptions} from './fxExportBuilder';
import {getFxPromptDefinition, type FxPromptId} from './fxPromptCatalog';
import {renderFxSnapshot, renderFxTrend} from './fxPromptRenderer';

export type {ToastFn};

/**
 * Build the single-pair AI export for the given catalog prompt and copy it to
 * the clipboard.
 */
export async function copyFxAiExport(promptId: FxPromptId, input: FxExportInput, options: FxExportOptions, toast: ToastFn, t: (key: string, opts?: {values?: Record<string, any>}) => string): Promise<void> {
    try {
        const exportData = await buildFxAiExport(input, options);
        const def = getFxPromptDefinition(promptId);
        const text = def.hasInstructions ? renderFxTrend(exportData) : renderFxSnapshot(exportData);
        const label = t(def.labelKey);

        await writeExportToClipboard(text, toast, t('dashboard.aiExportCopiedGeneric', {values: {label}}));
    } catch (err) {
        console.error('FX AI export failed:', err);
        toast.error(t('dashboard.aiExportFailed'));
    }
}
