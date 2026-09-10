import {Calculator, ChartLine, ChartPie, Scale, Wrench} from 'lucide-svelte';
import type {Readable} from 'svelte/store';
import {SUPPORTED_LOCALES, type t} from '$lib/i18n';
import {ToolClientError, type ToolCompatibilityCode, type ToolDescriptor} from './contracts';
import type {ToolRendererUnavailableCode} from './registry';

type Translator = typeof t extends Readable<infer Formatter> ? Formatter : never;

export interface ToolMessage {
    key: string;
    fallback: string;
}

export type ToolUnavailableReason = ToolCompatibilityCode | ToolRendererUnavailableCode;

const icons = new Map<string, typeof Wrench>([
    ['calculator', Calculator],
    ['chart_line', ChartLine],
    ['chart_pie', ChartPie],
    ['scale', Scale],
    ['wrench', Wrench],
]);

export function toolIcon(iconKey: string): typeof Wrench {
    return icons.get(iconKey) ?? Wrench;
}

function metadataText(key: string | null, fallback: string, translate: Translator): string {
    if (!key || !/^[a-zA-Z][a-zA-Z0-9_-]*(?:\.[a-zA-Z0-9_-]+)+$/.test(key)) return fallback;
    const missing = '[tool metadata translation unavailable]';
    // Backend fallback text is plain text, never an ICU message or HTML template.
    const localized = translate(key, {default: missing});
    return localized === missing || localized === key ? fallback : localized;
}

export function toolName(descriptor: ToolDescriptor, translate: Translator): string {
    return metadataText(descriptor.name_i18n_key, descriptor.name, translate);
}

export function toolDescription(descriptor: ToolDescriptor, translate: Translator): string {
    return metadataText(descriptor.description_i18n_key, descriptor.description, translate);
}

export function toolDocumentationPath(descriptor: ToolDescriptor): string | null {
    const path = descriptor.documentation.path;
    if (!/^[A-Za-z0-9_-]+(?:\/[A-Za-z0-9_-]+)*\/?$/.test(path) || path.startsWith('mkdocs/') || SUPPORTED_LOCALES.some((locale) => path.startsWith(`${locale}/`))) {
        return null;
    }
    return path;
}

export function toolRoute(descriptor: ToolDescriptor): string {
    return `/tools/${encodeURIComponent(descriptor.tool_code)}`;
}

export function unavailableMessage(reason: ToolUnavailableReason): ToolMessage {
    switch (reason) {
        case 'tool_not_installed':
            return {key: 'tools.availability.notInstalled', fallback: 'This tool is not listed in the current backend catalogue.'};
        case 'tool_unavailable':
            return {key: 'tools.availability.backendUnavailable', fallback: 'This tool is unavailable on the backend. No calculation has been started.'};
        case 'renderer_missing':
            return {
                key: 'tools.availability.rendererMissing',
                fallback: 'The backend tool is installed, but its interface is not included in this frontend build. No calculation has been started.',
            };
        case 'renderer_registration_invalid':
        case 'renderer_collision':
            return {
                key: 'tools.availability.rendererInvalid',
                fallback: 'The compiled interface registration is invalid or duplicated. No calculation has been started.',
            };
        default:
            return {key: 'tools.availability.incompatible', fallback: 'This tool requires a compatible frontend build. No calculation has been started.'};
    }
}

export function toolViewError(error: unknown): ToolClientError {
    return error instanceof ToolClientError ? error : new ToolClientError('internal', 'unexpected_ui_error');
}

export function toolErrorMessage(error: ToolClientError): ToolMessage {
    switch (error.code) {
        case 'renderer_load_failed':
            return {key: 'tools.errors.componentLoad', fallback: 'The tool interface could not be loaded.'};
        case 'renderer_mount_failed':
            return {key: 'tools.errors.componentMount', fallback: 'The tool interface could not be opened.'};
        case 'renderer_unmount_failed':
            return {key: 'tools.errors.cleanup', fallback: 'The tool view was removed, but its cleanup reported an error.'};
        case 'session_changed':
            return {key: 'tools.errors.sessionChanged', fallback: 'The account changed. Previous tool data was cleared.'};
        case 'waiting_stopped':
            return {key: 'tools.errors.stopped', fallback: 'Waiting stopped. This does not confirm cancellation on the server.'};
    }
    switch (error.kind) {
        case 'authentication':
            return {key: 'tools.authRequired', fallback: 'Sign in to use tools.'};
        case 'network':
            return {key: 'tools.errors.network', fallback: 'The tool service could not be reached. Check your connection and retry explicitly.'};
        case 'timeout':
            return {key: 'tools.errors.timeout', fallback: 'The tool request timed out. No result has been accepted and nothing was retried automatically.'};
        case 'http':
            return {key: 'tools.errors.requestRejected', fallback: 'The server rejected the tool request.'};
        case 'validation':
            return {key: 'tools.errors.requestInvalid', fallback: 'The tool request failed local structural validation.'};
        case 'protocol':
            return {key: 'tools.errors.protocol', fallback: 'The server response did not match the expected tool contract.'};
        case 'compatibility':
            return {key: 'tools.errors.mismatch', fallback: 'Tool metadata no longer matches this frontend. Reload explicitly to obtain updated metadata.'};
        default:
            return {key: 'tools.errors.internal', fallback: 'An unexpected tool interface error occurred.'};
    }
}
