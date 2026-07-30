import type {AiExportCatalogCompatibilityResult} from '../catalog/compatibility';
import {aiExportSelectionKey, isAiExportAnalysisId, type AiExportAnalysisCatalogEntry, type AiExportCompatibleSelection, type AiExportDatasetCatalogEntry, type AiExportSnapshotResponse} from '../catalog/shared';
import {renderFencedSection, serializeYaml} from '../serialization';
import {findAiExportResponseContract} from './responseContracts';
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

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

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
    if (!selectionMatches || snapshot.meta.schema_version !== 1 || snapshot.meta.catalog_version !== 1) {
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

function renderSnapshotMetadata(snapshot: AiExportSnapshotResponse): string {
    return renderFencedSection({
        heading: 'Snapshot Metadata and Dataset Manifest',
        language: 'yaml',
        content: serializeYaml(
            copiedValue({
                selection: snapshot.selection,
                detail_level: snapshot.detail_level,
                target: snapshot.target,
                meta: snapshot.meta,
                dataset_manifest: snapshot.dataset_manifest,
                analysis_contract: snapshot.analysis_contract,
                ...(snapshot.technical_sampling ? {technical_sampling: snapshot.technical_sampling} : {}),
                ...(snapshot.event_selection ? {event_selection: snapshot.event_selection} : {}),
                stats: snapshot.stats,
            }),
        ),
    });
}

function renderSnapshotData(snapshot: AiExportSnapshotResponse): string {
    return renderFencedSection({
        heading: 'Snapshot Data',
        language: 'yaml',
        content: serializeYaml(
            copiedValue({
                sections: snapshot.sections,
            }),
        ),
    });
}

function renderAdditionalData(input: RenderAiExportPromptInput): string {
    const included = new Set(input.snapshot.dataset_manifest.map((entry) => entry.dataset_id));
    const available = input.compatibility.catalog.datasets.filter((dataset) => dataset.domain === input.snapshot.domain && !included.has(dataset.id));
    const translate = input.translate ?? ((key: string) => key);
    const lines = ['## Additional LibreFolio Data', '', 'Do not assume absent data. If useful, ask the user to export one of these separate datasets:'];
    if (available.length === 0) lines.push('', '- None');
    else {
        for (const dataset of available) {
            const label = translate(dataset.display_i18n_key);
            const description = translate(dataset.description_i18n_key);
            lines.push(`- \`${dataset.id}\` — ${label}: ${description}`);
        }
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

export function renderAiExportPrompt(input: RenderAiExportPromptInput): RenderedAiExportPrompt {
    const catalogSelection = input.compatibility.byKey.get(aiExportSelectionKey(input.selection.kind, input.selection.id));
    if (input.compatibility.status !== 'compatible' || !catalogSelection || catalogSelection.version !== input.selection.version) {
        throw new AiExportPromptRenderError('incompatible_selection', 'AI Export selection is not compatible');
    }
    validateSnapshot(input);
    if (!isTrustedResponseLanguage(input.responseLanguage)) {
        throw new AiExportPromptRenderError('unsupported_response_language', `Unsupported response language: ${input.responseLanguage}`);
    }

    const sections: string[] = [];
    if (input.selection.kind === 'analysis') {
        const entry = input.selection.entry as AiExportAnalysisCatalogEntry;
        const notes = input.userNotes?.trim() ?? '';
        if (notes && !entry.supports_user_notes) {
            throw new AiExportPromptRenderError('unsupported_user_notes', `Analysis ${entry.id} does not support user notes`);
        }
        sections.push(renderAnalysisObjective(entry));
        sections.push(renderVerificationInstructions());
        sections.push(renderResponseContract(entry));
        sections.push(renderSnapshotMetadata(input.snapshot));
        sections.push(renderSnapshotData(input.snapshot));
        sections.push(renderAdditionalData(input));
        sections.push(renderDomainNotes(input.snapshot));
        if (notes) sections.push(renderUserNotes(notes));
        sections.push(`## Response Language\n\nPlease provide your answer in: ${input.responseLanguage}.`);
    } else {
        sections.push(renderSnapshotMetadata(input.snapshot));
        sections.push(renderSnapshotData(input.snapshot));
    }

    const prompt = sections.join('\n\n');
    return {
        prompt,
        mode: input.selection.kind === 'dataset' ? 'data_only' : 'full_prompt',
        stats: calculateAiExportPromptStats(prompt, input.snapshot.stats),
    };
}

export function calculateAiExportPromptStats(prompt: string, snapshotBackendStats: AiExportSnapshotResponse['stats']): AiExportPromptStats {
    return {
        finalPrompt: {
            characterCountUtf16CodeUnits: prompt.length,
            estimatedTokens: Math.ceil(prompt.length / 4),
            estimationMethod: 'ceil_utf16_code_units_div_4_v1',
        },
        snapshotBackendStats,
    };
}

export function isDatasetCatalogEntry(entry: AiExportDatasetCatalogEntry | AiExportAnalysisCatalogEntry): entry is AiExportDatasetCatalogEntry {
    return entry.kind === 'dataset';
}
