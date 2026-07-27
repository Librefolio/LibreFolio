import {
    AiExportContractMismatchError,
    canonicalizeAiExportSnapshotRequest,
    fetchAiExportSnapshot,
    type AiExportAssetSnapshotRequestInput,
    type AiExportAssetSnapshotResponse,
    type AiExportBackendExportStats,
    type AiExportBrokerSnapshotRequestInput,
    type AiExportBrokerSnapshotResponse,
    type AiExportFxSnapshotRequestInput,
    type AiExportFxSnapshotResponse,
    type AiExportPortfolioSnapshotRequestInput,
    type AiExportPortfolioSnapshotResponse,
    type AiExportSnapshotRequestInput,
    type AiExportSnapshotResponse,
} from './aiExportClient';
import {AI_EXPORT_TASK_CATALOG, aiExportCatalogLoader, type AiExportCatalogCompatibilityChoice, type AiExportCatalogCompatibilityResult} from './catalog/compatibility';
import type {AiExportDetailLevel, AiExportDomain, AiExportRenderMode, AiExportTask, AiExportTaskDefinition, AiExportTaskForDomain} from './catalog/shared';
import {aiExportOptionsFingerprint, findAiExportCatalogChoice, isAiExportCompatibleChoice, normalizeAiExportUserNotes, normalizeAiExportWebResearch} from './aiExportOptions';
import {renderAiExportPrompt, type AiExportFinalPromptStats, type AiExportPromptStats, type AiExportResponseLanguageDisplayName, type RenderAiExportPromptInput, type RenderedAiExportPrompt} from './templates/promptRenderer';

export type AiExportNonEmptyBrokerIds = readonly [number, ...number[]];

export interface AiExportV2DateRange {
    readonly start: string;
    readonly end?: string | null;
}

export interface AiExportV2CommonRequestContext {
    readonly dateRange: AiExportV2DateRange;
    readonly targetCurrency: string;
}

export interface AiExportPortfolioRequestContext extends AiExportV2CommonRequestContext {
    readonly domain: 'portfolio';
    readonly brokerIds?: AiExportNonEmptyBrokerIds;
}

export interface AiExportBrokerRequestContext extends AiExportV2CommonRequestContext {
    readonly domain: 'broker';
    readonly brokerId: number;
}

export interface AiExportAssetRequestContext extends AiExportV2CommonRequestContext {
    readonly domain: 'asset';
    readonly assetId: number;
    readonly brokerIds?: AiExportNonEmptyBrokerIds;
}

export interface AiExportFxRequestContext extends AiExportV2CommonRequestContext {
    readonly domain: 'fx';
    readonly baseCurrency: string;
    readonly quoteCurrency: string;
    readonly brokerIds?: AiExportNonEmptyBrokerIds;
}

export type AiExportV2RequestContext = AiExportPortfolioRequestContext | AiExportBrokerRequestContext | AiExportAssetRequestContext | AiExportFxRequestContext;

type AiExportSnapshotForDomain<D extends AiExportDomain> = D extends 'portfolio' ? AiExportPortfolioSnapshotResponse : D extends 'asset' ? AiExportAssetSnapshotResponse : D extends 'fx' ? AiExportFxSnapshotResponse : AiExportBrokerSnapshotResponse;

interface CopyAiExportV2InputForContext<C extends AiExportV2RequestContext> {
    readonly context: C;
    readonly task: AiExportTaskForDomain<C['domain']>;
    readonly detailLevel: AiExportDetailLevel;
    readonly renderMode: AiExportRenderMode;
    readonly responseLanguage: AiExportResponseLanguageDisplayName;
    readonly userNotes?: string;
    readonly webResearch?: boolean;
    readonly compatibility?: AiExportCatalogCompatibilityResult;
}

export type CopyAiExportV2Input<C extends AiExportV2RequestContext = AiExportV2RequestContext> = C extends AiExportV2RequestContext ? CopyAiExportV2InputForContext<C> : never;

export interface CopyAiExportV2Result<C extends AiExportV2RequestContext = AiExportV2RequestContext> {
    readonly snapshot: AiExportSnapshotForDomain<C['domain']>;
    readonly renderedPrompt: RenderedAiExportPrompt;
    readonly prompt: string;
    readonly stats: AiExportPromptStats;
    readonly backendStats: AiExportBackendExportStats;
    readonly finalStats: AiExportFinalPromptStats;
    readonly task: AiExportTaskForDomain<C['domain']>;
    readonly detailLevel: AiExportDetailLevel;
    readonly renderMode: AiExportRenderMode;
    readonly optionsFingerprint: string;
}

export type AiExportV2SnapshotFetcher = (request: AiExportSnapshotRequestInput, expectedChoice: AiExportCatalogCompatibilityChoice) => Promise<AiExportSnapshotResponse>;
export type AiExportV2PromptRenderer = (input: RenderAiExportPromptInput) => RenderedAiExportPrompt;
export type AiExportV2ClipboardWriter = (text: string) => void | Promise<void>;

export interface PrepareAiExportV2Dependencies {
    readonly loadCatalogCompatibility?: () => Promise<AiExportCatalogCompatibilityResult>;
    readonly fetchSnapshot?: AiExportV2SnapshotFetcher;
    readonly renderPrompt?: AiExportV2PromptRenderer;
}

export interface CopyAiExportV2Dependencies extends PrepareAiExportV2Dependencies {
    readonly writeClipboard?: AiExportV2ClipboardWriter;
}

export type AiExportChoiceUnavailableReason = 'task_unavailable' | 'detail_unavailable' | 'catalog_choice_missing' | 'catalog_choice_incompatible';

export class AiExportChoiceUnavailableError extends Error {
    readonly kind = 'choice_unavailable';

    constructor(
        readonly domain: AiExportDomain,
        readonly task: AiExportTask,
        readonly detailLevel: AiExportDetailLevel,
        readonly reason: AiExportChoiceUnavailableReason,
        readonly compatibilityReasonCode: AiExportCatalogCompatibilityChoice['reasonCode'] = null,
    ) {
        super(`AI Export choice unavailable: ${domain}.${task}.${detailLevel} (${reason})`);
        this.name = 'AiExportChoiceUnavailableError';
    }
}

export class AiExportClipboardUnavailableError extends Error {
    readonly kind = 'clipboard_unavailable';

    constructor(message = 'Clipboard writing is unavailable') {
        super(message);
        this.name = 'AiExportClipboardUnavailableError';
    }
}

export async function defaultAiExportV2ClipboardWriter(text: string): Promise<void> {
    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText && (typeof window === 'undefined' || window.isSecureContext !== false)) {
        await navigator.clipboard.writeText(text);
        return;
    }

    if (typeof document === 'undefined' || typeof document.execCommand !== 'function') {
        throw new AiExportClipboardUnavailableError();
    }

    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);

    try {
        textarea.focus();
        textarea.select();
        if (!document.execCommand('copy')) {
            throw new AiExportClipboardUnavailableError('Clipboard fallback failed');
        }
    } finally {
        textarea.remove();
    }
}

export async function prepareAiExportV2(input: CopyAiExportV2Input, dependencies: PrepareAiExportV2Dependencies = {}): Promise<CopyAiExportV2Result> {
    const taskDefinition = findTaskDefinition(input.context.domain, input.task);
    if (!taskDefinition) {
        throw new AiExportChoiceUnavailableError(input.context.domain, input.task, input.detailLevel, 'task_unavailable');
    }
    if (!taskDefinition.supportedDetailLevels.includes(input.detailLevel)) {
        throw new AiExportChoiceUnavailableError(input.context.domain, input.task, input.detailLevel, 'detail_unavailable');
    }

    const compatibility = input.compatibility ?? (await (dependencies.loadCatalogCompatibility ?? (() => aiExportCatalogLoader.load()))());
    const catalogChoice = findAiExportCatalogChoice(compatibility, input.context.domain, input.task, input.detailLevel);
    if (!catalogChoice) {
        throw new AiExportChoiceUnavailableError(input.context.domain, input.task, input.detailLevel, 'catalog_choice_missing');
    }
    if (!isAiExportCompatibleChoice(catalogChoice)) {
        throw new AiExportChoiceUnavailableError(input.context.domain, input.task, input.detailLevel, 'catalog_choice_incompatible', catalogChoice.reasonCode);
    }

    const request = buildCanonicalSnapshotRequest(input);
    const fetchSnapshot = dependencies.fetchSnapshot ?? ((snapshotRequest, expectedChoice) => fetchAiExportSnapshot(snapshotRequest, expectedChoice));
    const snapshot = await fetchSnapshot(request, catalogChoice);
    assertAiExportSnapshotDomain(input.context.domain, snapshot);

    const userNotes = normalizeAiExportUserNotes(input.renderMode, input.userNotes);
    const webResearch = normalizeAiExportWebResearch(taskDefinition, input.renderMode, input.webResearch);
    const renderPrompt = dependencies.renderPrompt ?? renderAiExportPrompt;
    const renderedPrompt = renderPrompt({
        taskDefinition,
        compatibleChoice: catalogChoice,
        snapshot,
        renderMode: input.renderMode,
        responseLanguage: input.responseLanguage,
        userNotes,
        webResearch,
    });

    return {
        snapshot,
        renderedPrompt,
        prompt: renderedPrompt.prompt,
        stats: renderedPrompt.stats,
        backendStats: renderedPrompt.stats.snapshotBackendStats,
        finalStats: renderedPrompt.stats.finalPrompt,
        task: input.task,
        detailLevel: input.detailLevel,
        renderMode: input.renderMode,
        optionsFingerprint: aiExportOptionsFingerprint({
            task: input.task,
            detailLevel: input.detailLevel,
            renderMode: input.renderMode,
            responseLanguage: input.responseLanguage,
            userNotes,
            webResearch,
        }),
    };
}

export async function writePreparedAiExportV2(result: Pick<CopyAiExportV2Result, 'prompt'>, writer: AiExportV2ClipboardWriter = defaultAiExportV2ClipboardWriter): Promise<void> {
    await writer(result.prompt);
}

export async function copyAiExportV2(input: CopyAiExportV2Input, dependencies: CopyAiExportV2Dependencies = {}): Promise<CopyAiExportV2Result> {
    const {writeClipboard, ...prepareDependencies} = dependencies;
    if (writeClipboard) {
        const result = await prepareAiExportV2(input, prepareDependencies);
        await writePreparedAiExportV2(result, writeClipboard);
        return result;
    }

    const modernClipboard = getModernAiExportV2Clipboard();
    if (!modernClipboard) {
        const result = await prepareAiExportV2(input, prepareDependencies);
        await writePreparedAiExportV2(result);
        return result;
    }

    const preparation = prepareAiExportV2(input, prepareDependencies);
    const promptBlob = preparation.then((result) => new Blob([result.prompt], {type: 'text/plain'}));
    const clipboardWrite = modernClipboard.clipboard.write([
        new modernClipboard.ClipboardItemConstructor({
            'text/plain': promptBlob,
        }),
    ]);
    const [result] = await Promise.all([preparation, clipboardWrite]);
    return result;
}

function getModernAiExportV2Clipboard():
    | {
          readonly clipboard: Clipboard;
          readonly ClipboardItemConstructor: typeof ClipboardItem;
      }
    | undefined {
    if (typeof navigator === 'undefined' || typeof ClipboardItem === 'undefined' || typeof Blob === 'undefined' || typeof navigator.clipboard?.write !== 'function') {
        return undefined;
    }
    return {
        clipboard: navigator.clipboard,
        ClipboardItemConstructor: ClipboardItem,
    };
}

function findTaskDefinition(domain: AiExportDomain, task: AiExportTask): AiExportTaskDefinition | undefined {
    return AI_EXPORT_TASK_CATALOG.find((definition) => definition.domain === domain && definition.backendTask === task);
}

type CopyAiExportV2InputForDomain<D extends AiExportDomain> = Extract<CopyAiExportV2Input, {readonly context: {readonly domain: D}}>;

function isCopyAiExportV2InputForDomain<D extends AiExportDomain>(input: CopyAiExportV2Input, domain: D): input is CopyAiExportV2InputForDomain<D> {
    return input.context.domain === domain;
}

function buildCanonicalSnapshotRequest(input: CopyAiExportV2Input): AiExportSnapshotRequestInput {
    const dateRange = {
        start: input.context.dateRange.start,
        end: input.context.dateRange.end,
    };

    if (isCopyAiExportV2InputForDomain(input, 'portfolio')) {
        const request: AiExportPortfolioSnapshotRequestInput = {
            domain: 'portfolio',
            task: input.task,
            detail_level: input.detailLevel,
            date_range: dateRange,
            target_currency: input.context.targetCurrency,
            broker_ids: cloneBrokerIds(input.context.brokerIds),
        };
        return canonicalizeAiExportSnapshotRequest(request);
    }
    if (isCopyAiExportV2InputForDomain(input, 'asset')) {
        const request: AiExportAssetSnapshotRequestInput = {
            domain: 'asset',
            task: input.task,
            detail_level: input.detailLevel,
            date_range: dateRange,
            target_currency: input.context.targetCurrency,
            asset_id: input.context.assetId,
            broker_ids: cloneBrokerIds(input.context.brokerIds),
        };
        return canonicalizeAiExportSnapshotRequest(request);
    }
    if (isCopyAiExportV2InputForDomain(input, 'fx')) {
        const request: AiExportFxSnapshotRequestInput = {
            domain: 'fx',
            task: input.task,
            detail_level: input.detailLevel,
            date_range: dateRange,
            target_currency: input.context.targetCurrency,
            base_currency: input.context.baseCurrency,
            quote_currency: input.context.quoteCurrency,
            broker_ids: cloneBrokerIds(input.context.brokerIds),
        };
        return canonicalizeAiExportSnapshotRequest(request);
    }

    const request: AiExportBrokerSnapshotRequestInput = {
        domain: 'broker',
        task: input.task,
        detail_level: input.detailLevel,
        date_range: dateRange,
        target_currency: input.context.targetCurrency,
        broker_id: input.context.brokerId,
    };
    return canonicalizeAiExportSnapshotRequest(request);
}

function assertAiExportSnapshotDomain<D extends AiExportDomain>(domain: D, snapshot: AiExportSnapshotResponse): asserts snapshot is AiExportSnapshotForDomain<D> {
    if (snapshot.domain !== domain) {
        throw new AiExportContractMismatchError([
            {
                field: 'response.domain',
                expected: domain,
                actual: snapshot.domain,
            },
        ]);
    }
}

function cloneBrokerIds(brokerIds: AiExportNonEmptyBrokerIds | undefined): number[] | undefined {
    return brokerIds ? [...brokerIds] : undefined;
}
