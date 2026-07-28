import {schemas} from '$lib/api';
import type {z} from 'zod';

export type AiExportDomain = z.infer<typeof schemas.AiExportDomain>;
export type AiExportTask = z.infer<typeof schemas.AiExportTask>;
export type AiExportDetailLevel = z.infer<typeof schemas.AiExportDetailLevel>;
export type AiExportBackendCatalogEntry = z.infer<typeof schemas.AiExportCatalogEntry>;
export type AiExportBackendCatalogResponse = z.infer<typeof schemas.AiExportCatalogResponse>;

type AiExportTaskByDomain = {
    portfolio: z.infer<typeof schemas.AiExportPortfolioTask>;
    asset: z.infer<typeof schemas.AiExportAssetTask>;
    fx: z.infer<typeof schemas.AiExportFxTask>;
    broker: z.infer<typeof schemas.AiExportBrokerTask>;
};

export type AiExportTaskForDomain<D extends AiExportDomain> = AiExportTaskByDomain[D];
export type AiExportRenderMode = 'data_only' | 'full_prompt';

export const AI_EXPORT_CATALOG_SCHEMA_VERSION = 1;
export const AI_EXPORT_SNAPSHOT_SCHEMA_VERSION = 1;
export const AI_EXPORT_PROFILE_VERSION = 1;
export const AI_EXPORT_FRONTEND_RESPONSE_CONTRACT_VERSION = 1;
export const AI_EXPORT_DETAIL_LEVELS = ['compact', 'standard', 'full'] as const satisfies readonly AiExportDetailLevel[];
export const AI_EXPORT_DEFAULT_DETAIL_LEVEL = 'standard' satisfies AiExportDetailLevel;
export const AI_EXPORT_RENDER_MODES = ['data_only', 'full_prompt'] as const satisfies readonly AiExportRenderMode[];
export const AI_EXPORT_DOMAIN_ORDER = ['portfolio', 'asset', 'fx', 'broker'] as const satisfies readonly AiExportDomain[];
export const AI_EXPORT_TASK_ICON_NAMES = ['Activity', 'ArrowLeftRight', 'Briefcase', 'CalendarClock', 'Camera', 'ChartColumn', 'ChartNoAxesCombined', 'Clock', 'Coins', 'FileText', 'Landmark', 'Layers', 'PieChart', 'PiggyBank', 'Receipt', 'Scale', 'TrendingUp'] as const;
export type AiExportTaskIconName = (typeof AI_EXPORT_TASK_ICON_NAMES)[number];

export interface AiExportExpectedProfile {
    readonly profileId: string;
    readonly profileVersion: typeof AI_EXPORT_PROFILE_VERSION;
}

export type AiExportExpectedProfiles = Readonly<Record<AiExportDetailLevel, AiExportExpectedProfile>>;

export interface AiExportFrontendResponseContract {
    readonly id: string;
    readonly version: number;
}

export interface AiExportTaskDefinition<D extends AiExportDomain = AiExportDomain> {
    readonly id: AiExportTaskForDomain<D>;
    readonly domain: D;
    readonly backendTask: AiExportTaskForDomain<D>;
    readonly labelKey: string;
    readonly descriptionKey: string;
    readonly icon: AiExportTaskIconName;
    readonly supportedDetailLevels: typeof AI_EXPORT_DETAIL_LEVELS;
    readonly defaultDetailLevel: typeof AI_EXPORT_DEFAULT_DETAIL_LEVEL;
    readonly expectedProfiles: AiExportExpectedProfiles;
    readonly frontendResponseContract: AiExportFrontendResponseContract;
    readonly supportsUserNotes: boolean;
    readonly supportsWebResearch: boolean;
    readonly renderModes: typeof AI_EXPORT_RENDER_MODES;
    readonly instructionTemplateId: string;
    readonly responseContractTemplateId: string;
}

interface AiExportTaskDefinitionInput<D extends AiExportDomain> {
    readonly domain: D;
    readonly backendTask: AiExportTaskForDomain<D>;
    readonly icon: AiExportTaskIconName;
    readonly supportsUserNotes: boolean;
    readonly supportsWebResearch: boolean;
    readonly frontendResponseContractVersion?: number;
}

export function defineAiExportTask<const D extends AiExportDomain>(input: AiExportTaskDefinitionInput<D>): AiExportTaskDefinition<D> {
    const taskPath = `${input.domain}.${input.backendTask}`;
    const frontendResponseContractVersion = input.frontendResponseContractVersion ?? AI_EXPORT_FRONTEND_RESPONSE_CONTRACT_VERSION;

    return {
        id: input.backendTask,
        domain: input.domain,
        backendTask: input.backendTask,
        labelKey: `aiExport.catalog.${taskPath}.label`,
        descriptionKey: `aiExport.catalog.${taskPath}.description`,
        icon: input.icon,
        supportedDetailLevels: AI_EXPORT_DETAIL_LEVELS,
        defaultDetailLevel: AI_EXPORT_DEFAULT_DETAIL_LEVEL,
        expectedProfiles: {
            compact: {
                profileId: `${taskPath}.compact`,
                profileVersion: AI_EXPORT_PROFILE_VERSION,
            },
            standard: {
                profileId: `${taskPath}.standard`,
                profileVersion: AI_EXPORT_PROFILE_VERSION,
            },
            full: {
                profileId: `${taskPath}.full`,
                profileVersion: AI_EXPORT_PROFILE_VERSION,
            },
        },
        frontendResponseContract: {
            id: taskPath,
            version: frontendResponseContractVersion,
        },
        supportsUserNotes: input.supportsUserNotes,
        supportsWebResearch: input.supportsWebResearch,
        renderModes: AI_EXPORT_RENDER_MODES,
        instructionTemplateId: `aiExport.instructions.${taskPath}.v1`,
        responseContractTemplateId: `aiExport.responseContracts.${taskPath}.v${frontendResponseContractVersion}`,
    };
}

export interface AiExportLocalCatalogChoice {
    readonly key: string;
    readonly taskId: AiExportTask;
    readonly domain: AiExportDomain;
    readonly backendTask: AiExportTask;
    readonly detailLevel: AiExportDetailLevel;
    readonly profileId: string;
    readonly profileVersion: typeof AI_EXPORT_PROFILE_VERSION;
    readonly frontendResponseContractId: string;
    readonly frontendResponseContractVersion: number;
    readonly supportsUserNotes: boolean;
    readonly supportsWebResearch: boolean;
}

export function aiExportCatalogTupleKey(domain: AiExportDomain, backendTask: AiExportTask, detailLevel: AiExportDetailLevel): string {
    return `${domain}:${backendTask}:${detailLevel}`;
}

export function expandAiExportTaskDefinitions(taskDefinitions: readonly AiExportTaskDefinition[]): readonly AiExportLocalCatalogChoice[] {
    return taskDefinitions.flatMap((taskDefinition) =>
        taskDefinition.supportedDetailLevels.map((detailLevel): AiExportLocalCatalogChoice => {
            const expectedProfile = taskDefinition.expectedProfiles[detailLevel];

            return {
                key: aiExportCatalogTupleKey(taskDefinition.domain, taskDefinition.backendTask, detailLevel),
                taskId: taskDefinition.id,
                domain: taskDefinition.domain,
                backendTask: taskDefinition.backendTask,
                detailLevel,
                profileId: expectedProfile.profileId,
                profileVersion: expectedProfile.profileVersion,
                frontendResponseContractId: taskDefinition.frontendResponseContract.id,
                frontendResponseContractVersion: taskDefinition.frontendResponseContract.version,
                supportsUserNotes: taskDefinition.supportsUserNotes,
                supportsWebResearch: taskDefinition.supportsWebResearch,
            };
        }),
    );
}
