/**
 * AI Export Clipboard — handles building the export and copying to clipboard.
 *
 * Entry point for dashboard UI: call copyAiExport() with mode and parameters.
 */

import {buildAiExport, type AiExportOptions} from './aiExportBuilder';
import {renderFullPrompt} from './aiPromptRenderer';
import {renderDataOnly} from './aiDataRenderer';

/** Toast callback type — wired to toastStore by caller */
export type ToastFn = {
	success: (msg: string) => void;
	error: (msg: string) => void;
	warning: (msg: string) => void;
};

const PROMPT_SIZE_WARNING_THRESHOLD = 50_000;

/**
 * Build the AI export and copy to clipboard.
 *
 * @param mode    'full' for full AI prompt, 'data-only' for portfolio data only
 * @param options Export options (brokerIds, dates, currency, locale)
 * @param toast   Toast notification functions
 * @param t       i18n translation function
 */
export async function copyAiExport(
	mode: 'full' | 'data-only',
	options: AiExportOptions,
	toast: ToastFn,
	t: (key: string) => string,
): Promise<void> {
	try {
		const exportData = await buildAiExport(options);

		// Check for empty portfolio
		if (exportData.positions.length === 0 && exportData.portfolio_snapshot.nav == null) {
			toast.warning(t('dashboard.aiExportEmpty'));
			return;
		}

		const text = mode === 'full' ? renderFullPrompt(exportData) : renderDataOnly(exportData);

		await navigator.clipboard.writeText(text);

		// Show appropriate feedback
		if (text.length > PROMPT_SIZE_WARNING_THRESHOLD) {
			const sizeKb = Math.round(text.length / 1000);
			const msg = mode === 'full' ? t('dashboard.aiExportCopied') : t('dashboard.aiExportCopiedData');
			toast.warning(`${msg} (${sizeKb}K chars)`);
		} else {
			const msg = mode === 'full' ? t('dashboard.aiExportCopied') : t('dashboard.aiExportCopiedData');
			toast.success(msg);
		}
	} catch (err) {
		console.error('AI export failed:', err);
		toast.error(t('dashboard.aiExportFailed'));
	}
}
