import type {AiExportCatalogCompatibilityResult} from '../catalog/compatibility';
import {AI_EXPORT_PAGE_FEATURE_LABEL_KEYS, AI_EXPORT_PAGE_LABEL_KEYS, AI_EXPORT_SCHEMA_VERSION, aiExportSelectionKey, isAiExportAnalysisId, type AiExportAnalysisCatalogEntry, type AiExportCompatibleSelection, type AiExportSnapshotResponse} from '../catalog/shared';
import {renderFencedSection, serializeYaml} from '../serialization';
import {findAiExportResponseContract, type AiExportFollowUpsResponseContract, type AiExportSectionsResponseContract} from './responseContracts';
import {renderSnapshotDataText, type RenderedSnapshotDataText, type SnapshotFormatDiagnostics, type SnapshotSignalMetric} from './snapshotDataRenderer';
import {AI_EXPORT_TOOL_GUIDES, AI_EXPORT_TOOLS_NAV_KEY} from './toolGuides';
import {
    AI_EXPORT_ANSWER_FOCUS_INSTRUCTIONS,
    AI_EXPORT_DATA_RECEIVED_KEY,
    AI_EXPORT_DOMAIN_NOTES,
    AI_EXPORT_EXPORT_SCOPE_INSTRUCTIONS,
    AI_EXPORT_GROUND_RULES,
    AI_EXPORT_HOW_TO_ANSWER,
    AI_EXPORT_SHARED_VERIFICATION_INSTRUCTIONS,
    AI_EXPORT_USER_QUESTION_INTRO,
    aiExportReplyInstructions,
    findAiExportAnalysisInstruction,
    type AiExportSectionsInstructionTemplate,
    type AiExportTaskInstructionTemplate,
} from './sharedInstructions';

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
    /** The interface's translation; `values` fill a message's `{name}` placeholders (78 L4a: the tool's labels). */
    readonly translate?: AiExportPromptTranslate;
}

export type AiExportPromptTranslate = (key: string, values?: Readonly<Record<string, string>>) => string;

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

export type AiExportPromptSectionId =
    | 'export_scope'
    | 'librefolio_tool'
    | 'analysis_objective'
    | 'shared_verification_instructions'
    | 'response_contract'
    | 'task'
    | 'rules_of_reasoning'
    | 'how_to_answer'
    | 'ground_rules'
    | 'snapshot_metadata'
    | 'snapshot_data'
    | 'additional_librefolio_data'
    | 'domain_notes'
    | 'user_question'
    | 'answer_focus'
    | 'legal_notice'
    | 'response_language'
    | 'reply_instructions';

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

type AnalysisTemplates =
    | {readonly shape: 'sections'; readonly instruction: AiExportSectionsInstructionTemplate; readonly contract: AiExportSectionsResponseContract}
    | {readonly shape: 'task'; readonly instruction: AiExportTaskInstructionTemplate; readonly contract: AiExportFollowUpsResponseContract};

/** The analysis's two templates, of one shape (plan 78, L1): a new-shape task with an old-shape contract, or the reverse, fails closed. */
function analysisTemplates(entry: AiExportAnalysisCatalogEntry): AnalysisTemplates {
    if (!isAiExportAnalysisId(entry.id)) throw new AiExportPromptRenderError('incompatible_selection', `Unknown analysis id: ${entry.id}`);
    const instruction = findAiExportAnalysisInstruction(entry.id);
    const contract = findAiExportResponseContract(entry.id);
    if (instruction.shape === 'sections' && contract.shape === 'sections') return {shape: 'sections', instruction, contract};
    if (instruction.shape === 'task' && contract.shape === 'follow_ups') return {shape: 'task', instruction, contract};
    throw new AiExportPromptRenderError('incompatible_selection', `Analysis ${entry.id} mixes the two template shapes`);
}

function renderAnalysisObjective(template: AiExportSectionsInstructionTemplate): string {
    return ['## Analysis Objective', '', template.objective, '', ...template.steps.map((step, index) => `${index + 1}. ${step}`)].join('\n');
}

/** The new shape's own instructions (78 L1): «Your Task», then «Rules of Reasoning» closed by the usual follow-ups. */
function renderTask(template: AiExportTaskInstructionTemplate): string {
    return `## Your Task\n\n${template.task}`;
}

function renderRulesOfReasoning(template: AiExportTaskInstructionTemplate, contract: AiExportFollowUpsResponseContract): string {
    return ['## Rules of Reasoning', '', ...template.rules.map((rule) => `- ${rule}`), '', contract.followUps].join('\n');
}

function renderVerificationInstructions(): string {
    return `## Shared Verification Instructions\n\n${AI_EXPORT_SHARED_VERIFICATION_INSTRUCTIONS}`;
}

function renderResponseContract(contract: AiExportSectionsResponseContract): string {
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

/**
 * «Calcolalo in LibreFolio» (78 L4a): for each tool the analysis suggests, where to find it and what to enter, step by
 * step. Every label of the tool is the tool's own i18n key, quoted; the AI Export writes only the sentences around them.
 * Null when the analysis suggests no tool.
 */
/** The way to the tool, the first points of the list: open LibreFolio, the sidebar's Tools, the tool's card. */
const TOOL_PATH_STEPS = 3;

function renderLibreFolioTool(entry: AiExportAnalysisCatalogEntry, translate: AiExportPromptTranslate = (key) => key): string | null {
    const tools = entry.suggested_tools ?? [];
    if (tools.length === 0) return null;
    const lines = [`## ${translate('aiExport.tool.heading')}`, '', translate('aiExport.tool.intro')];
    for (const {tool_code: toolCode} of tools) {
        const guide = AI_EXPORT_TOOL_GUIDES[toolCode];
        if (!guide) throw new AiExportPromptRenderError('incompatible_selection', `Unknown suggested tool: ${toolCode}`);
        const name = translate(guide.nameKey);
        lines.push(
            '',
            `### ${name}`,
            '',
            `- **${translate('aiExport.tool.when')}**: ${translate(guide.whenKey)}`,
            // 78 L4b: one numbered list, the way to the tool as its first three points (two lists lost the way in the trials)
            `- **${translate('aiExport.tool.inputs')}**:`,
            `  1. ${translate('aiExport.additionalData.steps.openLibreFolio')}`,
            `  2. ${translate('aiExport.tool.steps.sidebar')}: "${translate(AI_EXPORT_TOOLS_NAV_KEY)}"`,
            `  3. ${translate('aiExport.tool.steps.card')}: "${name}"`,
            ...guide.steps.map((step, index) => {
                const values = Object.fromEntries(Object.entries(step.values ?? {}).map(([placeholder, key]) => [placeholder, `"${translate(key)}"`]));
                return `  ${index + TOOL_PATH_STEPS + 1}. "${translate(step.labelKey)}": ${translate(step.explanationKey, values)}`;
            }),
            `- **${translate('aiExport.tool.returns')}**: ${translate(guide.returnsKey)}`,
        );
    }
    return lines.join('\n');
}

function renderAdditionalData(input: RenderAiExportPromptInput): string {
    if (input.selection.kind !== 'analysis' || input.selection.entry.kind !== 'analysis') {
        throw new AiExportPromptRenderError('incompatible_selection', 'Additional LibreFolio data guidance requires an analysis selection');
    }
    // 78 L10b: a dataset the user cannot select (it reads brokers, and the user owns none) is never suggested.
    const included = new Set([...input.snapshot.dataset_manifest.map((entry) => entry.dataset_id), ...(input.snapshot.unavailable_dataset_ids ?? [])]);
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

/**
 * The user's question (78 L1, both shapes since 78 L2), the thing to answer, safely serialized under a trusted sentence that
 * keeps it from changing the rules. The new shape puts it last, before the response language; the old shape keeps it
 * before its trusted closing.
 */
function renderUserQuestion(question: string): string {
    const heading = '## User Question\n\n';
    const fenced = renderFencedSection({heading: 'User Question', language: 'yaml', content: serializeYaml({user_question: question})});
    return `${heading}${AI_EXPORT_USER_QUESTION_INTRO}\n\n${fenced.slice(heading.length)}`;
}

/**
 * «Export Scope» (78 L10): a filtered Portfolio export that leaves out a broker the user owns says so at the top of the
 * prompt. The fixed sentence is local; the included and the excluded brokers' names (the user's own text, D12 (b)) come
 * from the snapshot and are serialized safely under it. Null when the snapshot carries no scope fact: the prompt is then exactly
 * what it was before L10.
 */
function renderExportScope(snapshot: AiExportSnapshotResponse): string | null {
    const scope = snapshot.export_scope;
    if (scope === null || scope === undefined) return null;
    const includedBrokers = scope.included_broker_ids.map((brokerId) => {
        const entry = snapshot.entity_directory.brokers.find((broker) => broker.broker_id === brokerId);
        if (!entry) throw new AiExportPromptRenderError('incompatible_snapshot', `Entity directory does not resolve broker ${brokerId}`);
        return entry.display_name;
    });
    const heading = '## Export Scope\n\n';
    const fenced = renderFencedSection({
        heading: 'Export Scope',
        language: 'yaml',
        // Two safe serializations, included first as the sentence reads them: one serializeYaml sorts its keys
        content: serializeYaml({included_brokers: includedBrokers}) + serializeYaml({excluded_brokers: scope.excluded_brokers.map((broker) => broker.display_name)}),
    });
    return `${heading}${AI_EXPORT_EXPORT_SCOPE_INSTRUCTIONS}\n\n${fenced.slice(heading.length)}`;
}

/**
 * The instance's legal notice (F09, workstream A), in the interface language: local, allow-listed copy under its own
 * heading — never a fenced data block, never a URL or anything the instance or the snapshot provides — so the UI and
 * the probe, which translate from the same catalogue, render the same bytes.
 */
function renderLegalNotice(input: RenderAiExportPromptInput): string {
    const translate = input.translate ?? ((key: string) => key);
    return [`## ${translate('legal.title')}`, '', translate('legal.disclaimer')].join('\n');
}

/** Request Analysis' closing instruction (E-24): answer the question from the data, never restate the data. Fixed English. */
function renderAnswerFocus(): string {
    return `## Answer Focus\n\n${AI_EXPORT_ANSWER_FOCUS_INSTRUCTIONS}`;
}

/**
 * Export Data's last word (E-24): data only, already seen in LibreFolio, so the assistant answers only a question the
 * user adds, and otherwise replies with the catalogue's sentence (`AI_EXPORT_DATA_RECEIVED_KEY`), in the interface
 * language through the caller's `translate`, as the legal notice. Fixed English around that one sentence.
 */
function renderReplyInstructions(input: RenderAiExportPromptInput): string {
    const translate = input.translate ?? ((key: string) => key);
    return `## Reply Instructions\n\n${aiExportReplyInstructions(translate(AI_EXPORT_DATA_RECEIVED_KEY))}`;
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
    // 78 L10: a filtered Portfolio export opens every prompt, analysis or Export Data, with the brokers it covers
    const exportScope = renderExportScope(input.snapshot);
    if (exportScope !== null) sections.push({id: 'export_scope', content: exportScope});
    const snapshotMetadata = renderSnapshotMetadata(input.snapshot, diagnostics);
    const snapshotData = renderSnapshotData(input.snapshot, diagnostics);
    if (input.selection.kind === 'analysis') {
        const entry = input.selection.entry as AiExportAnalysisCatalogEntry;
        const notes = input.userNotes?.trim() ?? '';
        if (notes && !entry.supports_user_notes) {
            throw new AiExportPromptRenderError('unsupported_user_notes', `Analysis ${entry.id} does not support user notes`);
        }
        const templates = analysisTemplates(entry);
        const language = {id: 'response_language' as const, content: `## Response Language\n\nPlease provide your answer in: ${input.responseLanguage}.`};
        if (templates.shape === 'task') {
            // The new shape (78 L1): the analysis's task and rules, the two shared blocks, the data, the legal notice, then
            // the user's question, the thing to answer, and the response language, the prompt's last word
            sections.push({id: 'task', content: renderTask(templates.instruction)});
            sections.push({id: 'rules_of_reasoning', content: renderRulesOfReasoning(templates.instruction, templates.contract)});
            sections.push({id: 'how_to_answer', content: `## How to Answer\n\n${AI_EXPORT_HOW_TO_ANSWER}`});
            sections.push({id: 'ground_rules', content: `## Ground Rules\n\n${AI_EXPORT_GROUND_RULES}`});
            sections.push({id: 'snapshot_metadata', content: snapshotMetadata.content});
            sections.push({id: 'snapshot_data', content: snapshotData.content});
            sections.push({id: 'additional_librefolio_data', content: renderAdditionalData(input)});
            // 78 L4a: «Calcolalo in LibreFolio», the tool the analysis sends the user to, after the data it suggests
            const tool = renderLibreFolioTool(entry, input.translate);
            if (tool !== null) sections.push({id: 'librefolio_tool', content: tool});
            sections.push({id: 'domain_notes', content: renderDomainNotes(input.snapshot)});
            sections.push({id: 'legal_notice', content: renderLegalNotice(input)});
            if (notes) sections.push({id: 'user_question', content: renderUserQuestion(notes)});
            sections.push(language);
        } else {
            sections.push({id: 'analysis_objective', content: renderAnalysisObjective(templates.instruction)});
            sections.push({id: 'shared_verification_instructions', content: renderVerificationInstructions()});
            sections.push({id: 'response_contract', content: renderResponseContract(templates.contract)});
            sections.push({id: 'snapshot_metadata', content: snapshotMetadata.content});
            sections.push({id: 'snapshot_data', content: snapshotData.content});
            sections.push({id: 'additional_librefolio_data', content: renderAdditionalData(input)});
            sections.push({id: 'domain_notes', content: renderDomainNotes(input.snapshot)});
            // 78 L2: the old shape's user text is the User Question too, under its sentence, but it keeps its place before
            // the trusted closing (Answer Focus, legal notice, language): «the question last» is proven on the new shape only
            if (notes) sections.push({id: 'user_question', content: renderUserQuestion(notes)});
            // The trusted closing, after the untrusted user question: the answer focus (E-24), the legal notice, then the response
            // language, the prompt's last word (J, A9)
            sections.push({id: 'answer_focus', content: renderAnswerFocus()});
            sections.push({id: 'legal_notice', content: renderLegalNotice(input)});
            sections.push(language);
        }
    } else {
        sections.push({id: 'snapshot_metadata', content: snapshotMetadata.content});
        sections.push({id: 'snapshot_data', content: snapshotData.content});
        sections.push({id: 'legal_notice', content: renderLegalNotice(input)});
        // Export Data's last word: how to reply, never a restatement of the data (E-24)
        sections.push({id: 'reply_instructions', content: renderReplyInstructions(input)});
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
