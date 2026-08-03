import type {AiExportCatalogCompatibilityResult} from '../catalog/compatibility';
import {AI_EXPORT_PAGE_FEATURE_LABEL_KEYS, AI_EXPORT_PAGE_LABEL_KEYS, AI_EXPORT_SCHEMA_VERSION, aiExportSelectionKey, isAiExportAnalysisId, type AiExportAnalysisCatalogEntry, type AiExportCompatibleSelection, type AiExportDatasetCatalogEntry, type AiExportSnapshotResponse} from '../catalog/shared';
import {renderFencedSection, serializeYaml} from '../serialization';
import {findAiExportResponseContract} from './responseContracts';
import {renderSnapshotDataText, type RenderedSnapshotDataText, type SnapshotFormatDiagnostics, type SnapshotSignalMetric} from './snapshotDataRenderer';
import {AI_EXPORT_DOMAIN_NOTES, AI_EXPORT_SHARED_VERIFICATION_INSTRUCTIONS, findAiExportAnalysisInstruction} from './sharedInstructions';

export const AI_EXPORT_RESPONSE_LANGUAGE_DISPLAY_NAMES = ['English', 'Italian', 'French', 'Spanish'] as const;
export type AiExportResponseLanguageDisplayName = (typeof AI_EXPORT_RESPONSE_LANGUAGE_DISPLAY_NAMES)[number];

export type AiExportPromptRenderErrorCode = 'incompatible_selection' | 'incompatible_snapshot' | 'unsupported_user_notes' | 'unsupported_response_language';

export class AiExportPromptRenderError extends Error {
    constructor(
        readonly code: AiExportPromptRenderErrorCode,
        message: string,
    ) {
        super(message);
        this.name = 'AiExportPromptRenderError';
    }
}

export interface RenderAiExportPromptInput {
    readonly selection: AiExportCompatibleSelection;
    readonly compatibility: AiExportCatalogCompatibilityResult;
    readonly snapshot: AiExportSnapshotResponse;
    readonly responseLanguage: AiExportResponseLanguageDisplayName;
    readonly userNotes?: string;
    readonly translate?: (key: string) => string;
}

export interface AiExportFinalPromptStats {
    readonly characterCountUtf16CodeUnits: number;
    readonly byteCountUtf8: number;
    readonly estimatedTokens: number;
    readonly estimationMethod: 'ceil_utf16_code_units_div_4_v1';
}

export interface AiExportPromptStats {
    readonly finalPrompt: AiExportFinalPromptStats;
    readonly snapshotBackendStats: AiExportSnapshotResponse['stats'];
}

export interface RenderedAiExportPrompt {
    readonly prompt: string;
    readonly mode: 'data_only' | 'full_prompt';
    readonly stats: AiExportPromptStats;
}

export type AiExportPromptSectionId = 'analysis_objective' | 'shared_verification_instructions' | 'response_contract' | 'snapshot_metadata' | 'snapshot_data' | 'additional_librefolio_data' | 'domain_notes' | 'user_notes' | 'response_language';

export interface AiExportPromptDiagnosticTextBlock {
    readonly id: string;
    readonly content: string;
}

export interface AiExportPromptDiagnostics {
    readonly rendered: RenderedAiExportPrompt;
    readonly sectionSeparator: '\n\n';
    readonly sections: readonly AiExportPromptDiagnosticTextBlock[];
    readonly snapshotMetadataFields: readonly AiExportPromptDiagnosticTextBlock[];
    readonly snapshotDataComponents: readonly AiExportPromptDiagnosticTextBlock[];
    readonly snapshotDataWrapper: string;
    readonly snapshotDataFormatPreamble: string;
    readonly snapshotDataEntityDirectory: string;
    readonly snapshotSignalMetrics: readonly SnapshotSignalMetric[];
    readonly snapshotFormatDiagnostics: SnapshotFormatDiagnostics;
}

interface PromptSectionSource {
    readonly id: AiExportPromptSectionId;
    readonly content: string;
}

interface SerializedDiagnosticValue {
    readonly content: string;
    readonly blocks: readonly AiExportPromptDiagnosticTextBlock[];
    readonly wrapper: string;
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const SECTION_SEPARATOR = '\n\n';

function slashDate(value: string): string {
    return ISO_DATE.test(value) ? value.replaceAll('-', '/') : value;
}

function copiedValue(value: unknown): unknown {
    if (typeof value === 'string') return slashDate(value);
    if (Array.isArray(value)) return value.map(copiedValue);
    if (value !== null && typeof value === 'object') {
        return Object.fromEntries(Object.entries(value).map(([key, nested]) => [key, copiedValue(nested)]));
    }
    return value;
}

function validateSnapshot(input: RenderAiExportPromptInput): void {
    const {selection, snapshot} = input;
    const selectionMatches = snapshot.domain === selection.domain && snapshot.selection.kind === selection.kind && snapshot.selection.id === selection.id && snapshot.selection.version === selection.version && selection.supportedDetailLevels.includes(snapshot.detail_level);
    if (!selectionMatches || snapshot.meta.schema_version !== AI_EXPORT_SCHEMA_VERSION || snapshot.meta.catalog_version !== input.compatibility.catalog.catalog_version) {
        throw new AiExportPromptRenderError('incompatible_snapshot', 'Snapshot identity does not match the selected catalog entry');
    }
    if (selection.kind === 'analysis') {
        const entry = selection.entry as AiExportAnalysisCatalogEntry;
        const contract = snapshot.analysis_contract;
        if (
            !contract ||
            contract.instruction_template_id !== entry.instruction_template_id ||
            contract.instruction_template_version !== entry.instruction_template_version ||
            contract.response_contract_id !== entry.response_contract_id ||
            contract.response_contract_version !== entry.response_contract_version
        ) {
            throw new AiExportPromptRenderError('incompatible_snapshot', 'Snapshot analysis contract does not match the catalog');
        }
    } else if (snapshot.analysis_contract !== null && snapshot.analysis_contract !== undefined) {
        throw new AiExportPromptRenderError('incompatible_snapshot', 'Dataset snapshot must not include an analysis contract');
    }
}

function renderAnalysisObjective(entry: AiExportAnalysisCatalogEntry): string {
    if (!isAiExportAnalysisId(entry.id)) throw new AiExportPromptRenderError('incompatible_selection', `Unknown analysis id: ${entry.id}`);
    const template = findAiExportAnalysisInstruction(entry.id);
    return ['## Analysis Objective', '', template.objective, '', ...template.steps.map((step, index) => `${index + 1}. ${step}`)].join('\n');
}

function renderVerificationInstructions(): string {
    return `## Shared Verification Instructions\n\n${AI_EXPORT_SHARED_VERIFICATION_INSTRUCTIONS}`;
}

function renderResponseContract(entry: AiExportAnalysisCatalogEntry): string {
    if (!isAiExportAnalysisId(entry.id)) throw new AiExportPromptRenderError('incompatible_selection', `Unknown analysis id: ${entry.id}`);
    const contract = findAiExportResponseContract(entry.id);
    const lines = ['## Response Contract', '', `Contract: ${contract.id} v${contract.version}`, '', 'Use these sections in this exact order:'];
    for (const [index, contractSection] of contract.sections.entries()) {
        lines.push(`${index + 1}. **${contractSection.title}**`);
        for (const requirement of contractSection.requirements) lines.push(`   - ${requirement}`);
    }
    return lines.join('\n');
}

function requiredDirectoryRef(index: number, prefix: 'A' | 'B', target: string): string {
    if (index < 0) {
        throw new AiExportPromptRenderError('incompatible_snapshot', `Entity directory does not resolve ${target}`);
    }
    return `${prefix}${index + 1}`;
}

function publicPercent(ratio: number): string {
    return `${Math.round(ratio * 1_000_000) / 10_000}%`;
}

function snapshotMetadataValue(snapshot: AiExportSnapshotResponse): Record<string, unknown> {
    const technicalSampling = snapshot.technical_sampling
        ? {
              detail_level: snapshot.technical_sampling.detail_level,
              ...(snapshot.technical_sampling.price_policy ? {price_bucket_count: snapshot.technical_sampling.price_policy.bucket_count} : {}),
              indicator_history_row_limit: snapshot.technical_sampling.indicator_history_row_limit,
          }
        : undefined;
    const snapshotTarget = snapshot.target;
    const historyCoverage = snapshot.meta.history_coverage
        ? (({coverage_ratio, ...coverage}) => ({
              ...coverage,
              coverage_percent: publicPercent(coverage_ratio),
          }))(snapshot.meta.history_coverage)
        : undefined;
    const target =
        snapshotTarget.kind === 'asset'
            ? {
                  kind: 'asset',
                  asset_ref: requiredDirectoryRef(
                      snapshot.entity_directory.assets.findIndex((asset) => asset.asset_id === snapshotTarget.asset_id),
                      'A',
                      `asset ${snapshotTarget.asset_id}`,
                  ),
              }
            : snapshotTarget.kind === 'broker'
              ? {
                    kind: 'broker',
                    broker_ref: requiredDirectoryRef(
                        snapshot.entity_directory.brokers.findIndex((broker) => broker.broker_id === snapshotTarget.broker_id),
                        'B',
                        `broker ${snapshotTarget.broker_id}`,
                    ),
                }
              : snapshotTarget.kind === 'fx_pair'
                ? {
                      kind: 'fx_pair',
                      fx_ref: 'F1',
                      display_name: `${snapshotTarget.base_currency}/${snapshotTarget.quote_currency}`,
                  }
                : {kind: 'portfolio'};
    return copiedValue({
        selection: {
            kind: snapshot.selection.kind,
            id: snapshot.selection.id,
        },
        detail_level: snapshot.detail_level,
        target,
        snapshot: {
            snapshot_as_of: snapshot.meta.snapshot_as_of,
            exported_period: snapshot.meta.exported_period,
            target_currency: snapshot.meta.target_currency,
            ...(snapshot.meta.calculation_range ? {calculation_range: snapshot.meta.calculation_range} : {}),
            ...(historyCoverage ? {history_coverage: historyCoverage} : {}),
        },
        dataset_manifest: snapshot.dataset_manifest.map((entry) => ({
            dataset_id: entry.dataset_id,
            role: entry.role,
        })),
        ...(technicalSampling ? {technical_sampling: technicalSampling} : {}),
        ...(snapshot.event_selection ? {event_selection: snapshot.event_selection} : {}),
    }) as Record<string, unknown>;
}

function serializeObjectBlocks(value: Record<string, unknown>): SerializedDiagnosticValue {
    const content = serializeYaml(value);
    const blocks = Object.keys(value)
        .sort()
        .map((key) => ({
            id: key,
            content: serializeYaml({[key]: value[key]}),
        }));
    if (blocks.map((block) => block.content).join('') !== content) {
        throw new Error('AI Export metadata diagnostic blocks do not reconcile with rendered YAML');
    }
    return {content, blocks, wrapper: ''};
}

function renderSnapshotDataBlocks(snapshot: AiExportSnapshotResponse): RenderedSnapshotDataText {
    const sections = copiedValue(snapshot.sections);
    return renderSnapshotDataText(sections, copiedValue(snapshot.target), copiedValue(snapshot.entity_directory), copiedValue(snapshot.technical_sampling));
}

function renderSnapshotMetadata(snapshot: AiExportSnapshotResponse, diagnostics: boolean): {content: string; blocks: readonly AiExportPromptDiagnosticTextBlock[]} {
    const serialized = diagnostics ? serializeObjectBlocks(snapshotMetadataValue(snapshot)) : {content: serializeYaml(snapshotMetadataValue(snapshot)), blocks: []};
    return {
        content: renderFencedSection({
            heading: 'Snapshot Metadata and Dataset Manifest',
            language: 'yaml',
            content: serialized.content,
        }),
        blocks: serialized.blocks,
    };
}

function renderSnapshotData(
    snapshot: AiExportSnapshotResponse,
    diagnostics: boolean,
): {
    content: string;
    blocks: readonly AiExportPromptDiagnosticTextBlock[];
    wrapper: string;
    formatPreamble: string;
    entityDirectory: string;
    signalMetrics: readonly SnapshotSignalMetric[];
    formatDiagnostics: SnapshotFormatDiagnostics;
} {
    const serialized = renderSnapshotDataBlocks(snapshot);
    return {
        content: renderFencedSection({
            heading: 'Snapshot Data',
            language: 'text',
            content: serialized.content,
        }),
        blocks: diagnostics ? serialized.blocks : [],
        wrapper: diagnostics ? serialized.wrapper : '',
        formatPreamble: diagnostics ? serialized.formatPreamble : '',
        entityDirectory: diagnostics ? serialized.entityDirectory : '',
        signalMetrics: diagnostics ? serialized.signalMetrics : [],
        formatDiagnostics: serialized.formatDiagnostics,
    };
}

function renderAdditionalData(input: RenderAiExportPromptInput): string {
    if (input.selection.kind !== 'analysis' || input.selection.entry.kind !== 'analysis') {
        throw new AiExportPromptRenderError('incompatible_selection', 'Additional LibreFolio data guidance requires an analysis selection');
    }
    const included = new Set(input.snapshot.dataset_manifest.map((entry) => entry.dataset_id));
    const translate = input.translate ?? ((key: string) => key);
    const suggestions = (input.selection.entry.additional_export_suggestions ?? []).filter((suggestion) => !included.has(suggestion.dataset_id));
    const lines = [`## ${translate('aiExport.additionalData.heading')}`, '', translate('aiExport.additionalData.intro')];
    if (suggestions.length === 0) {
        lines.push('', `- ${translate('aiExport.additionalData.none')}`);
        return lines.join('\n');
    }
    for (const suggestion of suggestions) {
        const dataset = input.compatibility.catalog.datasets.find((entry) => entry.id === suggestion.dataset_id);
        if (!dataset || dataset.domain !== input.snapshot.domain) {
            throw new AiExportPromptRenderError('incompatible_selection', `Additional export suggestion does not resolve a same-domain dataset: ${suggestion.dataset_id}`);
        }
        const pageCode = dataset.applicable_pages[0];
        const pageLabelKey = pageCode ? AI_EXPORT_PAGE_LABEL_KEYS[pageCode] : undefined;
        const featureLabelKey = pageCode ? AI_EXPORT_PAGE_FEATURE_LABEL_KEYS[pageCode] : undefined;
        if (!pageLabelKey || !featureLabelKey) {
            throw new AiExportPromptRenderError('incompatible_selection', `Unknown AI Export page code for ${dataset.id}: ${pageCode ?? 'missing'}`);
        }
        const label = translate(dataset.display_i18n_key);
        const period = translate(`aiExport.additionalData.period.${suggestion.recommended_period}`);
        const detail = translate(`aiExport.details.${suggestion.recommended_detail}`);
        const necessity = translate(`aiExport.additionalData.necessity.${suggestion.necessity}`);
        lines.push(
            '',
            `### ${label}`,
            '',
            `- **${translate('aiExport.additionalData.what')}**: ${translate(dataset.description_i18n_key)}`,
            `- **${translate('aiExport.additionalData.why')}**: ${translate(suggestion.reason_i18n_key)}`,
            `- **${translate('aiExport.additionalData.necessityLabel')}**: ${necessity}`,
            `- **${translate('aiExport.additionalData.path')}**:`,
            `  1. ${translate('aiExport.additionalData.steps.openLibreFolio')}`,
            `  2. ${translate('aiExport.additionalData.steps.page')}: "${translate(pageLabelKey)}"`,
            `  3. ${translate('aiExport.additionalData.steps.feature')}: "${translate(featureLabelKey)}"`,
            `  4. ${translate('aiExport.additionalData.steps.exportType')}: "${translate('aiExport.exportData')}"`,
            `  5. ${translate('aiExport.additionalData.steps.dataset')}: "${label}"`,
            `  6. ${translate('aiExport.additionalData.steps.period')}: "${period}"`,
            `  7. ${translate('aiExport.additionalData.steps.detail')}: "${detail}"`,
            `- **${translate('aiExport.additionalData.recommended')}**: ${period}; ${detail}`,
            `- **${translate('aiExport.additionalData.technicalReference')}**: \`${dataset.id}\``,
        );
    }
    return lines.join('\n');
}

function renderDomainNotes(snapshot: AiExportSnapshotResponse): string {
    return renderFencedSection({
        heading: 'Domain Notes',
        language: 'yaml',
        content: serializeYaml({domain_notes: AI_EXPORT_DOMAIN_NOTES[snapshot.domain]}),
    });
}

function renderUserNotes(notes: string): string {
    return renderFencedSection({
        heading: 'User Notes',
        language: 'yaml',
        content: serializeYaml({user_notes: notes}),
    });
}

function isTrustedResponseLanguage(value: string): value is AiExportResponseLanguageDisplayName {
    return AI_EXPORT_RESPONSE_LANGUAGE_DISPLAY_NAMES.some((language) => language === value);
}

function buildAiExportPrompt(input: RenderAiExportPromptInput, diagnostics: boolean): AiExportPromptDiagnostics {
    const catalogSelection = input.compatibility.byKey.get(aiExportSelectionKey(input.selection.kind, input.selection.id));
    if (input.compatibility.status !== 'compatible' || !catalogSelection || catalogSelection.version !== input.selection.version) {
        throw new AiExportPromptRenderError('incompatible_selection', 'AI Export selection is not compatible');
    }
    validateSnapshot(input);
    if (!isTrustedResponseLanguage(input.responseLanguage)) {
        throw new AiExportPromptRenderError('unsupported_response_language', `Unsupported response language: ${input.responseLanguage}`);
    }

    const sections: PromptSectionSource[] = [];
    const snapshotMetadata = renderSnapshotMetadata(input.snapshot, diagnostics);
    const snapshotData = renderSnapshotData(input.snapshot, diagnostics);
    if (input.selection.kind === 'analysis') {
        const entry = input.selection.entry as AiExportAnalysisCatalogEntry;
        const notes = input.userNotes?.trim() ?? '';
        if (notes && !entry.supports_user_notes) {
            throw new AiExportPromptRenderError('unsupported_user_notes', `Analysis ${entry.id} does not support user notes`);
        }
        sections.push({id: 'analysis_objective', content: renderAnalysisObjective(entry)});
        sections.push({id: 'shared_verification_instructions', content: renderVerificationInstructions()});
        sections.push({id: 'response_contract', content: renderResponseContract(entry)});
        sections.push({id: 'snapshot_metadata', content: snapshotMetadata.content});
        sections.push({id: 'snapshot_data', content: snapshotData.content});
        sections.push({id: 'additional_librefolio_data', content: renderAdditionalData(input)});
        sections.push({id: 'domain_notes', content: renderDomainNotes(input.snapshot)});
        if (notes) sections.push({id: 'user_notes', content: renderUserNotes(notes)});
        sections.push({
            id: 'response_language',
            content: `## Response Language\n\nPlease provide your answer in: ${input.responseLanguage}.`,
        });
    } else {
        sections.push({id: 'snapshot_metadata', content: snapshotMetadata.content});
        sections.push({id: 'snapshot_data', content: snapshotData.content});
    }

    const prompt = sections.map((section) => section.content).join(SECTION_SEPARATOR);
    const rendered: RenderedAiExportPrompt = {
        prompt,
        mode: input.selection.kind === 'dataset' ? 'data_only' : 'full_prompt',
        stats: calculateAiExportPromptStats(prompt, input.snapshot.stats),
    };
    return {
        rendered,
        sectionSeparator: SECTION_SEPARATOR,
        sections,
        snapshotMetadataFields: snapshotMetadata.blocks,
        snapshotDataComponents: snapshotData.blocks,
        snapshotDataWrapper: snapshotData.wrapper,
        snapshotDataFormatPreamble: snapshotData.formatPreamble,
        snapshotDataEntityDirectory: snapshotData.entityDirectory,
        snapshotSignalMetrics: snapshotData.signalMetrics,
        snapshotFormatDiagnostics: snapshotData.formatDiagnostics,
    };
}

export function renderAiExportPrompt(input: RenderAiExportPromptInput): RenderedAiExportPrompt {
    return buildAiExportPrompt(input, false).rendered;
}

export function renderAiExportPromptDiagnostics(input: RenderAiExportPromptInput): AiExportPromptDiagnostics {
    return buildAiExportPrompt(input, true);
}

export function calculateAiExportPromptStats(prompt: string, snapshotBackendStats: AiExportSnapshotResponse['stats']): AiExportPromptStats {
    return {
        finalPrompt: {
            characterCountUtf16CodeUnits: prompt.length,
            byteCountUtf8: new TextEncoder().encode(prompt).length,
            estimatedTokens: Math.ceil(prompt.length / 4),
            estimationMethod: 'ceil_utf16_code_units_div_4_v1',
        },
        snapshotBackendStats,
    };
}

export function isDatasetCatalogEntry(entry: AiExportDatasetCatalogEntry | AiExportAnalysisCatalogEntry): entry is AiExportDatasetCatalogEntry {
    return entry.kind === 'dataset';
}
