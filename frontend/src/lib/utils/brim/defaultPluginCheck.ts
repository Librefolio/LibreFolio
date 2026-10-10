/**
 * Does an uploaded file fit its broker's default import plugin — and where does it belong if not?
 *
 * A broker that sets a default import plugin says what its files are. Scalable Capital's two
 * accounts, for example, are two brokers whose default plugins refuse each other's export. The
 * upload answers with the plugins that read the file (`compatible_plugins`): when the broker's
 * default one is missing, the file was probably assigned to the wrong broker, and the brokers whose
 * default plugin reads it are where it belongs. Without this check the wizard silently picks the
 * first compatible plugin (`pickBestPlugin`) and imports the file into the wrong broker.
 *
 * Pure: the wizard asks the default plugin *why* it refuses the file separately
 * (`GET /brokers/import/files/{file_id}/plugin-check`) and translates the answer with
 * `resolveParseRefusalMessage`.
 */
import {brimPluginName} from './pluginText';

/** The broker fields the check reads. */
export interface MismatchBroker {
    id: number;
    name: string;
    default_import_plugin?: string | null;
}

/** A broker whose default import plugin reads the file. */
export interface MismatchTarget {
    id: number;
    name: string;
    pluginCode: string;
}

export interface DefaultPluginMismatch {
    /** The broker the file was uploaded to. */
    brokerId: number;
    /** Its default import plugin, which does not read the file. */
    defaultPlugin: string;
    /** The plugins that read the file, as detected at upload: best match first. */
    readers: string[];
    /** The other brokers whose default plugin reads the file, best plugin first, then in the order of `brokers`. */
    targets: MismatchTarget[];
}

export interface MismatchOptions {
    /** Report-set plugins: a file one of them reads is read through its set, whatever the broker's default plugin, so it is never questioned. */
    reportSetPlugins?: ReadonlySet<string>;
    /** Fallback plugins (the generic CSV): a broker using one by default is proposed only when no broker uses a specific plugin that reads the file. */
    fallbackPlugins?: ReadonlySet<string>;
}

/**
 * The mismatch between a file and its broker's default import plugin, or `null` when there is none
 * to report: the broker has no default plugin, its default plugin reads the file, or a report-set
 * plugin reads it.
 *
 * `compatiblePlugins` is the upload's list, sorted best match first: the targets follow that order.
 */
export function findDefaultPluginMismatch(compatiblePlugins: readonly string[] | null | undefined, brokerId: number, brokers: readonly MismatchBroker[], options: MismatchOptions = {}): DefaultPluginMismatch | null {
    const defaultPlugin = brokers.find((b) => b.id === brokerId)?.default_import_plugin ?? '';
    if (!defaultPlugin) return null;
    const readers = [...(compatiblePlugins ?? [])];
    if (readers.includes(defaultPlugin)) return null;
    if (readers.some((code) => options.reportSetPlugins?.has(code))) return null;
    const candidates = brokers
        .filter((b) => b.id !== brokerId && !!b.default_import_plugin && readers.includes(b.default_import_plugin))
        .map((b) => ({id: b.id, name: b.name, pluginCode: b.default_import_plugin as string}))
        .sort((a, b) => readers.indexOf(a.pluginCode) - readers.indexOf(b.pluginCode));
    const isFallback = (target: MismatchTarget) => options.fallbackPlugins?.has(target.pluginCode) ?? false;
    const targets = candidates.some((target) => !isFallback(target)) ? candidates.filter((target) => !isFallback(target)) : candidates;
    return {brokerId, defaultPlugin, readers, targets};
}

/** A plugin's refusal as the API returns it (`BRIMRefusal`). */
export interface ParseRefusal {
    code?: string | null;
    message: string;
    context?: Record<string, unknown> | null;
}

type TranslateFn = (key: string, opts?: {values?: Record<string, any>}) => string;

/**
 * A plugin's refusal in the UI language: `importWizard.parseRefusal.<code>` with the refusal's
 * `context` as values, as the notices do (`resolveBrimNoticeMessage`). Without a code, or without a
 * translation, the plugin's own English sentence — written lowercase and without a final period, to
 * complete the parse error — is shown as a sentence.
 */
export function resolveParseRefusalMessage(refusal: ParseRefusal, t: TranslateFn): string {
    if (refusal.code) {
        const key = `importWizard.parseRefusal.${refusal.code}`;
        const translated = t(key, {values: refusalValues(refusal.context, t)});
        if (translated !== key) return translated;
    }
    const message = refusal.message.trim();
    if (!message) return message;
    const sentence = message.charAt(0).toUpperCase() + message.slice(1);
    return /[.!?]$/.test(sentence) ? sentence : `${sentence}.`;
}

/** A refusal's context as message values: a plugin it names by `plugin_code` gets its `plugin_name` in the UI language. */
function refusalValues(context: Record<string, unknown> | null | undefined, t: TranslateFn): Record<string, unknown> {
    const values: Record<string, unknown> = {...(context ?? {})};
    if (typeof values.plugin_code === 'string') {
        values.plugin_name = brimPluginName({code: values.plugin_code, name: typeof values.plugin_name === 'string' ? values.plugin_name : null}, t);
    }
    return values;
}
