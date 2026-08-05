import type {AiExportSnapshotRequestInput, AiExportSnapshotTransport} from './aiExportClient';
import {fetchAiExportSnapshot} from './aiExportClient';
import {findCompatibleAiExportSelection, type AiExportCatalogCompatibilityResult} from './catalog/compatibility';
import {AI_EXPORT_CATALOG_VERSION, type AiExportCompatibleSelection, type AiExportDomain, type AiExportSnapshotResponse} from './catalog/shared';
import {aiExportOptionsFingerprint, normalizeAiExportUserNotes, resolveAiExportPeriod, type AiExportOptionsSelection} from './aiExportOptions';
import {renderAiExportPrompt, type AiExportPromptStats, type RenderedAiExportPrompt} from './templates/promptRenderer';

export interface AiExportPortfolioContext {
    readonly domain: 'portfolio';
    readonly snapshotAsOf: string;
    readonly targetCurrency: string;
    readonly brokerIds?: readonly number[];
}

export interface AiExportBrokerContext {
    readonly domain: 'broker';
    readonly snapshotAsOf: string;
    readonly targetCurrency: string;
    readonly brokerId: number;
}

export interface AiExportAssetContext {
    readonly domain: 'asset';
    readonly snapshotAsOf: string;
    readonly targetCurrency: string;
    readonly assetId: number;
    readonly brokerIds?: readonly number[];
}

export interface AiExportFxContext {
    readonly domain: 'fx';
    readonly snapshotAsOf: string;
    readonly targetCurrency: string;
    readonly baseCurrency: string;
    readonly quoteCurrency: string;
    readonly brokerIds?: readonly number[];
}

export type AiExportRequestContext = AiExportPortfolioContext | AiExportBrokerContext | AiExportAssetContext | AiExportFxContext;

export interface PrepareAiExportInput {
    readonly context: AiExportRequestContext;
    readonly options: AiExportOptionsSelection;
    readonly compatibility: AiExportCatalogCompatibilityResult;
    readonly translate?: (key: string) => string;
}

export interface PreparedAiExport {
    readonly selection: AiExportCompatibleSelection;
    readonly request: AiExportSnapshotRequestInput;
    readonly snapshot: AiExportSnapshotResponse;
    readonly renderedPrompt: RenderedAiExportPrompt;
    readonly prompt: string;
    readonly stats: AiExportPromptStats;
    readonly options: AiExportOptionsSelection;
    readonly optionsFingerprint: string;
}

export type AiExportClipboardWriter = (text: string) => void | Promise<void>;

export interface PrepareAiExportDependencies {
    readonly transport?: AiExportSnapshotTransport;
}

export class AiExportChoiceUnavailableError extends Error {
    readonly kind = 'choice_unavailable';

    constructor(
        readonly domain: AiExportDomain,
        readonly selectionId: string,
    ) {
        super(`AI Export choice unavailable: ${domain}.${selectionId}`);
        this.name = 'AiExportChoiceUnavailableError';
    }
}

export class AiExportClipboardUnavailableError extends Error {
    readonly kind = 'clipboard_unavailable';

    constructor(message = 'Clipboard writing is unavailable', options?: ErrorOptions) {
        super(message, options);
        this.name = 'AiExportClipboardUnavailableError';
    }
}

function selectionPayload(selection: AiExportCompatibleSelection): AiExportSnapshotRequestInput['selection'] {
    if (selection.kind === 'dataset') return {kind: 'dataset', id: selection.id, version: selection.version};
    if (selection.entry.kind !== 'analysis') throw new Error(`Analysis selection '${selection.id}' has invalid catalog metadata`);
    return {
        kind: 'analysis',
        id: selection.id,
        version: selection.version,
        instruction_template_id: selection.entry.instruction_template_id,
        instruction_template_version: selection.entry.instruction_template_version,
        response_contract_id: selection.entry.response_contract_id,
        response_contract_version: selection.entry.response_contract_version,
    };
}

function brokerIds(values: readonly number[] | undefined): number[] | undefined {
    return values?.length ? [...new Set(values)].sort((left, right) => left - right) : undefined;
}

export function buildAiExportSnapshotRequest(context: AiExportRequestContext, options: AiExportOptionsSelection, selection: AiExportCompatibleSelection): AiExportSnapshotRequestInput {
    const common = {
        selection: selectionPayload(selection),
        detail_level: options.detailLevel,
        period: resolveAiExportPeriod(context.snapshotAsOf, options.period),
        target_currency: context.targetCurrency,
        expected_catalog_version: AI_EXPORT_CATALOG_VERSION,
    } as const;
    if (context.domain === 'portfolio') return {domain: 'portfolio', ...common, broker_ids: brokerIds(context.brokerIds)};
    if (context.domain === 'broker') return {domain: 'broker', ...common, broker_id: context.brokerId};
    if (context.domain === 'asset') return {domain: 'asset', ...common, asset_id: context.assetId, broker_ids: brokerIds(context.brokerIds)};
    return {
        domain: 'fx',
        ...common,
        base_currency: context.baseCurrency,
        quote_currency: context.quoteCurrency,
        broker_ids: brokerIds(context.brokerIds),
    };
}

export async function prepareAiExport(input: PrepareAiExportInput, dependencies: PrepareAiExportDependencies = {}): Promise<PreparedAiExport> {
    const selection = findCompatibleAiExportSelection(input.compatibility, input.options.selectionKind, input.options.selectionId);
    if (!selection || selection.domain !== input.context.domain || !selection.supportedDetailLevels.includes(input.options.detailLevel)) {
        throw new AiExportChoiceUnavailableError(input.context.domain, input.options.selectionId);
    }
    const options: AiExportOptionsSelection = {
        ...input.options,
        userNotes: normalizeAiExportUserNotes(selection.kind, input.options.userNotes),
    };
    const request = buildAiExportSnapshotRequest(input.context, options, selection);
    const snapshot = await fetchAiExportSnapshot(request, selection, dependencies.transport);
    const renderedPrompt = renderAiExportPrompt({
        selection,
        compatibility: input.compatibility,
        snapshot,
        responseLanguage: options.responseLanguage,
        userNotes: options.userNotes,
        translate: input.translate,
    });
    return {
        selection,
        request,
        snapshot,
        renderedPrompt,
        prompt: renderedPrompt.prompt,
        stats: renderedPrompt.stats,
        options,
        optionsFingerprint: aiExportOptionsFingerprint(options),
    };
}

export async function defaultAiExportClipboardWriter(text: string): Promise<void> {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText && (typeof window === 'undefined' || window.isSecureContext !== false)) {
        try {
            await navigator.clipboard.writeText(text);
        } catch (error) {
            throw new AiExportClipboardUnavailableError('Clipboard permission denied', {cause: error});
        }
        return;
    }
    if (typeof document === 'undefined' || typeof document.execCommand !== 'function') throw new AiExportClipboardUnavailableError();
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    try {
        textarea.focus();
        textarea.select();
        if (!document.execCommand('copy')) throw new AiExportClipboardUnavailableError('Clipboard fallback failed');
    } finally {
        textarea.remove();
    }
}

export async function writePreparedAiExport(result: Pick<PreparedAiExport, 'prompt'>, writer: AiExportClipboardWriter = defaultAiExportClipboardWriter): Promise<void> {
    await writer(result.prompt);
}

export async function copyAiExport(input: PrepareAiExportInput, dependencies: PrepareAiExportDependencies & {writer?: AiExportClipboardWriter} = {}): Promise<PreparedAiExport> {
    const result = await prepareAiExport(input, dependencies);
    await writePreparedAiExport(result, dependencies.writer);
    return result;
}
