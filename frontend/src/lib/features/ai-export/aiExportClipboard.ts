/**
 * AI Export Clipboard — handles building the export and copying to clipboard.
 *
 * Entry point for dashboard/broker-detail UI: call copyAiExport() with the
 * chosen catalog prompt id and parameters.
 */

import {buildAiExport, type AiExportOptions} from './aiExportBuilder';
import {renderPrompt} from './aiPromptRenderer';
import {renderDataOnly} from './aiDataRenderer';
import {getPromptDefinition, type PromptId} from './promptCatalog';
import {writeExportToClipboard, type ToastFn} from '$lib/utils/clipboard';

export type {ToastFn};

/**
 * Build the AI export for the given catalog prompt and copy it to the clipboard.
 *
 * @param promptId Catalog entry id (see promptCatalog.ts) — 'snapshot' has no instructions, the rest do.
 * @param options   Export options (brokerIds, dates, currency, locale)
 * @param toast     Toast notification functions
 * @param t         i18n translation function
 */
export async function copyAiExport(promptId: PromptId, options: AiExportOptions, toast: ToastFn, t: (key: string, opts?: {values?: Record<string, any>}) => string): Promise<void> {
    try {
        const exportData = await buildAiExport(options);

        // Check for empty portfolio
        if (exportData.positions.length === 0 && exportData.portfolio_snapshot.nav == null) {
            toast.warning(t('dashboard.aiExportEmpty'));
            return;
        }

        const def = getPromptDefinition(promptId);
        const text = def.hasInstructions ? renderPrompt(exportData, promptId as Exclude<PromptId, 'snapshot'>) : renderDataOnly(exportData);
        const label = t(def.labelKey);

        await writeExportToClipboard(text, toast, t('dashboard.aiExportCopiedGeneric', {values: {label}}));
    } catch (err) {
        console.error('AI export failed:', err);
        toast.error(t('dashboard.aiExportFailed'));
    }
}
