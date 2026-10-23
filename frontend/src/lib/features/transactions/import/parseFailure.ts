/**
 * What the import wizard shows when the server refuses a parse or a file preview, in the UI language (C-70b).
 *
 * The API answers those with `400 {detail: {...}}`, an object the wizard translates instead of an English sentence:
 *
 * - `{code: 'parse_failed', message, plugin_code, plugin_name, reason: {code, message, context}}`: the plugin could not
 *   read the file. The frame is `importWizard.parseFailed` with the plugin and the reason; the reason is the plugin's
 *   refusal as `resolveParseRefusalMessage` shows it (`importWizard.parseRefusal.<code>` with the context, else the plugin's
 *   own sentence). Nothing to say about the reason at all gives `importWizard.parseFailedNoReason`.
 * - `{code: 'preview_unsupported' | 'preview_unreadable', message}`: `importWizard.previewFailed.<code>`, else `message`.
 * - anything else: `extractErrorMessage`, as before.
 *
 * Pure: the wizard passes `$t`.
 */
import {extractErrorMessage} from '$lib/utils/trySave';
import {brimPluginName} from '$lib/utils/brim/pluginText';
import {resolveParseRefusalMessage} from './defaultPluginCheck';

type TranslateFn = (key: string, opts?: {values?: Record<string, any>}) => string;

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** The error of a failed parse or preview, shown in the UI language; any other error as `extractErrorMessage` says it. */
export function resolveParseFailureMessage(error: unknown, t: TranslateFn, fallback?: string): string {
    const detail = (error as {response?: {data?: {detail?: unknown}}} | null | undefined)?.response?.data?.detail;
    if (isRecord(detail)) {
        if (detail.code === 'parse_failed') return parseFailedMessage(detail, t);
        if (detail.code === 'preview_unsupported' || detail.code === 'preview_unreadable') {
            const key = `importWizard.previewFailed.${detail.code}`;
            const translated = t(key, {values: {}});
            if (translated !== key) return translated;
            if (typeof detail.message === 'string' && detail.message) return detail.message;
        }
    }
    return extractErrorMessage(error, fallback);
}

function parseFailedMessage(detail: Record<string, unknown>, t: TranslateFn): string {
    const reason = isRecord(detail.reason) ? detail.reason : {};
    const code = typeof reason.code === 'string' && reason.code ? reason.code : null;
    const text = typeof reason.message === 'string' ? reason.message : '';
    const context = isRecord(reason.context) ? reason.context : null;
    const shownReason = code || text.trim() ? resolveParseRefusalMessage({code, message: text, context}, t) : '';
    if (!shownReason.trim()) return t('importWizard.parseFailedNoReason', {values: {}});
    const pluginCode = typeof detail.plugin_code === 'string' ? detail.plugin_code : '';
    const pluginName = typeof detail.plugin_name === 'string' && detail.plugin_name ? detail.plugin_name : null;
    return t('importWizard.parseFailed', {values: {plugin_name: brimPluginName({code: pluginCode, name: pluginName}, t), reason: shownReason}});
}
