import type {AiExportBackendExportStats, AiExportSnapshotResponse} from '../aiExportClient';
import type {AiExportCatalogCompatibilityChoice} from '../catalog/compatibility';
import type {AiExportRenderMode, AiExportTaskDefinition} from '../catalog/shared';
import {renderFencedSection, serializeYaml} from '../serialization';
import {findAiExportResponseContract, type AiExportResponseContractTemplate} from './responseContracts';
import {AI_EXPORT_OPTIONAL_WEB_RESEARCH_INSTRUCTION, AI_EXPORT_SHARED_MANDATORY_INSTRUCTIONS, findAiExportTaskInstruction, type AiExportTaskInstructionTemplate} from './sharedInstructions';

export const AI_EXPORT_RESPONSE_LANGUAGE_DISPLAY_NAMES = ['English', 'Italian', 'French', 'Spanish'] as const;
export type AiExportResponseLanguageDisplayName = (typeof AI_EXPORT_RESPONSE_LANGUAGE_DISPLAY_NAMES)[number];

export type AiExportPromptRenderErrorCode = 'incompatible_catalog_choice' | 'incompatible_contract' | 'unsupported_user_notes' | 'unsupported_web_research' | 'unsupported_response_language';

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
    readonly taskDefinition: AiExportTaskDefinition;
    readonly compatibleChoice: AiExportCatalogCompatibilityChoice;
    readonly snapshot: AiExportSnapshotResponse;
    readonly renderMode: AiExportRenderMode;
    readonly responseLanguage: AiExportResponseLanguageDisplayName;
    readonly userNotes?: string;
    readonly webResearch?: boolean;
}

export interface AiExportFinalPromptStats {
    /**
     * JavaScript string.length: deterministic UTF-16 code units, not Unicode code points.
     */
    readonly characterCountUtf16CodeUnits: number;
    readonly estimatedTokens: number;
    readonly estimationMethod: 'ceil_utf16_code_units_div_4_v1';
}

export interface AiExportPromptStats {
    readonly finalPrompt: AiExportFinalPromptStats;
    readonly snapshotBackendStats: AiExportBackendExportStats;
}

export interface RenderedAiExportPrompt {
    readonly prompt: string;
    readonly stats: AiExportPromptStats;
}

export function renderAiExportPrompt(input: RenderAiExportPromptInput): RenderedAiExportPrompt {
    const {instructionTemplate, responseContract} = validateRenderContract(input);
    const notesPresent = input.renderMode === 'full_prompt' && input.userNotes !== undefined && input.userNotes.trim().length > 0;
    const webResearch = input.webResearch ?? false;

    if (notesPresent && !input.taskDefinition.supportsUserNotes) {
        throw new AiExportPromptRenderError('unsupported_user_notes', `Task ${input.taskDefinition.domain}.${input.taskDefinition.backendTask} does not support user notes`);
    }
    if (webResearch && !input.taskDefinition.supportsWebResearch) {
        throw new AiExportPromptRenderError('unsupported_web_research', `Task ${input.taskDefinition.domain}.${input.taskDefinition.backendTask} does not support web research`);
    }
    if (!isTrustedResponseLanguage(input.responseLanguage)) {
        throw new AiExportPromptRenderError('unsupported_response_language', `Unsupported response language display name: ${input.responseLanguage}`);
    }

    const sections: string[] = [];
    if (input.renderMode === 'full_prompt') {
        sections.push(renderTaskInstructions(instructionTemplate, webResearch));
        sections.push(renderResponseContract(responseContract));
    }

    sections.push(
        renderFencedSection({
            heading: 'Snapshot Data',
            language: 'yaml',
            content: serializeYaml(buildSnapshotData(input.snapshot)),
        }),
    );

    if (input.snapshot.domain_notes !== undefined && input.snapshot.domain_notes.length > 0) {
        sections.push(
            renderFencedSection({
                heading: 'Domain Notes and Descriptions',
                language: 'yaml',
                content: serializeYaml({domain_notes: input.snapshot.domain_notes}),
            }),
        );
    }

    if (notesPresent) {
        sections.push(
            renderFencedSection({
                heading: 'Optional User Notes',
                language: 'yaml',
                content: serializeYaml({user_notes: input.userNotes}),
            }),
        );
    }

    if (input.renderMode === 'full_prompt') {
        sections.push(`## Response Language\n\nPlease provide your answer in: ${input.responseLanguage}.`);
    }

    const prompt = sections.join('\n\n');
    return {
        prompt,
        stats: calculateAiExportPromptStats(prompt, input.snapshot.export_stats),
    };
}

export function calculateAiExportPromptStats(prompt: string, snapshotBackendStats: AiExportBackendExportStats): AiExportPromptStats {
    const characterCountUtf16CodeUnits = prompt.length;
    return {
        finalPrompt: {
            characterCountUtf16CodeUnits,
            estimatedTokens: Math.ceil(characterCountUtf16CodeUnits / 4),
            estimationMethod: 'ceil_utf16_code_units_div_4_v1',
        },
        snapshotBackendStats,
    };
}

function validateRenderContract(input: RenderAiExportPromptInput): {
    readonly instructionTemplate: AiExportTaskInstructionTemplate;
    readonly responseContract: AiExportResponseContractTemplate;
} {
    if (input.compatibleChoice.status !== 'compatible' || input.compatibleChoice.reasonCode !== null || input.compatibleChoice.backendEntry === undefined) {
        throw new AiExportPromptRenderError('incompatible_catalog_choice', 'AI Export catalog choice is not compatible');
    }

    const instructionTemplate = findAiExportTaskInstruction(input.taskDefinition.domain, input.taskDefinition.backendTask);
    const responseContract = findAiExportResponseContract(input.taskDefinition.domain, input.taskDefinition.backendTask);
    const expectedProfile = input.taskDefinition.expectedProfiles[input.compatibleChoice.detailLevel];
    const backendEntry = input.compatibleChoice.backendEntry;

    const compatible =
        instructionTemplate !== undefined &&
        responseContract !== undefined &&
        input.taskDefinition.instructionTemplateId === instructionTemplate.id &&
        input.taskDefinition.responseContractTemplateId === responseContract.templateId &&
        input.taskDefinition.frontendResponseContract.id === responseContract.contractId &&
        input.taskDefinition.frontendResponseContract.version === responseContract.version &&
        input.taskDefinition.renderModes.includes(input.renderMode) &&
        input.taskDefinition.domain === input.compatibleChoice.domain &&
        input.taskDefinition.backendTask === input.compatibleChoice.backendTask &&
        input.taskDefinition.backendTask === input.compatibleChoice.taskId &&
        input.taskDefinition.supportsUserNotes === input.compatibleChoice.supportsUserNotes &&
        input.taskDefinition.supportsWebResearch === input.compatibleChoice.supportsWebResearch &&
        expectedProfile.profileId === input.compatibleChoice.profileId &&
        expectedProfile.profileVersion === input.compatibleChoice.profileVersion &&
        responseContract.contractId === input.compatibleChoice.frontendResponseContractId &&
        responseContract.version === input.compatibleChoice.frontendResponseContractVersion &&
        backendEntry.domain === input.compatibleChoice.domain &&
        backendEntry.task === input.compatibleChoice.backendTask &&
        backendEntry.detail_level === input.compatibleChoice.detailLevel &&
        backendEntry.profile_id === input.compatibleChoice.profileId &&
        backendEntry.profile_version === input.compatibleChoice.profileVersion &&
        backendEntry.frontend_response_contract_id === input.compatibleChoice.frontendResponseContractId &&
        backendEntry.frontend_response_contract_version === input.compatibleChoice.frontendResponseContractVersion &&
        input.snapshot.domain === input.taskDefinition.domain &&
        input.snapshot.task === input.taskDefinition.backendTask &&
        input.snapshot.detail_level === input.compatibleChoice.detailLevel &&
        input.snapshot.meta.profile_id === input.compatibleChoice.profileId &&
        input.snapshot.meta.profile_version === input.compatibleChoice.profileVersion &&
        input.snapshot.meta.frontend_response_contract_id === responseContract.contractId &&
        input.snapshot.meta.frontend_response_contract_version === responseContract.version;

    if (!compatible || instructionTemplate === undefined || responseContract === undefined) {
        throw new AiExportPromptRenderError('incompatible_contract', 'Task, catalog choice, snapshot, and local prompt contract do not match');
    }

    return {instructionTemplate, responseContract};
}

function renderTaskInstructions(template: AiExportTaskInstructionTemplate, webResearch: boolean): string {
    const lines = ['## Task Instructions', '', AI_EXPORT_SHARED_MANDATORY_INSTRUCTIONS, '', `Objective: ${template.objective}`, '', ...template.steps.map((step, index) => `${index + 1}. ${step}`)];

    if (webResearch) {
        lines.push('', AI_EXPORT_OPTIONAL_WEB_RESEARCH_INSTRUCTION);
    }

    return lines.join('\n');
}

function renderResponseContract(template: AiExportResponseContractTemplate): string {
    const lines = ['## Response Contract', '', `Contract: ${template.contractId} v${template.version}`, '', 'Use these sections in this exact order:'];

    for (const [index, contractSection] of template.sections.entries()) {
        lines.push(`${index + 1}. **${contractSection.title}**`);
        for (const requirement of contractSection.requirements) {
            lines.push(`   - ${requirement}`);
        }
    }

    return lines.join('\n');
}

function buildSnapshotData(snapshot: AiExportSnapshotResponse): object {
    return {
        snapshot: {
            domain: snapshot.domain,
            task: snapshot.task,
            detail_level: snapshot.detail_level,
        },
        meta: snapshot.meta,
        methodology: snapshot.methodology,
        facts: snapshot.facts,
        ...(snapshot.states !== undefined ? {states: snapshot.states} : {}),
        ...(snapshot.technical !== undefined ? {technical: snapshot.technical} : {}),
        ...(snapshot.events !== undefined ? {events: snapshot.events} : {}),
        ...(snapshot.coverage !== undefined ? {coverage: snapshot.coverage} : {}),
        ...(snapshot.semantics !== undefined ? {semantics: snapshot.semantics} : {}),
        export_stats: snapshot.export_stats,
    };
}

function isTrustedResponseLanguage(value: string): value is AiExportResponseLanguageDisplayName {
    return AI_EXPORT_RESPONSE_LANGUAGE_DISPLAY_NAMES.some((language) => language === value);
}
