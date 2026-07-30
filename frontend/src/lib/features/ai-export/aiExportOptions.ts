import type {AiExportCatalogCompatibilityResult} from './catalog/compatibility';
import {findCompatibleAiExportSelection, selectionsForDomain} from './catalog/compatibility';
import type {AiExportDetailLevel, AiExportDomain, AiExportSelectionId, AiExportSelectionKind} from './catalog/shared';
import type {AiExportPromptStats, AiExportResponseLanguageDisplayName} from './templates/promptRenderer';

export const AI_EXPORT_TOKEN_WARNING_THRESHOLD = 8_000;
export const AI_EXPORT_TOKEN_LARGE_THRESHOLD = 16_000;
export const AI_EXPORT_PERIOD_PRESETS = ['3m', '6m', '1y', 'custom'] as const;
export const AI_EXPORT_PERIOD_UNITS = ['days', 'weeks', 'months', 'years'] as const;

export type AiExportTokenSeverity = 'normal' | 'warning' | 'large';
export type AiExportPeriodPreset = (typeof AI_EXPORT_PERIOD_PRESETS)[number];
export type AiExportPeriodUnit = (typeof AI_EXPORT_PERIOD_UNITS)[number];

export interface AiExportPeriodSelection {
    readonly preset: AiExportPeriodPreset;
    readonly customAmount: number;
    readonly customUnit: AiExportPeriodUnit;
}

export const AI_EXPORT_DEFAULT_PERIOD = {
    preset: '3m',
    customAmount: 3,
    customUnit: 'months',
} as const satisfies AiExportPeriodSelection;

export interface AiExportOptionsSelection {
    readonly selectionKind: AiExportSelectionKind;
    readonly selectionId: AiExportSelectionId;
    readonly detailLevel: AiExportDetailLevel;
    readonly period: AiExportPeriodSelection;
    readonly responseLanguage: AiExportResponseLanguageDisplayName;
    readonly userNotes?: string;
}

export interface AiExportResolvedPeriod {
    readonly start: string;
    readonly end: string;
}

export interface AiExportStatsContextFingerprintInput {
    readonly contextKey: string;
    readonly snapshotAsOf: string;
    readonly targetCurrency: string;
}

export interface AiExportOptionsPanelLabels {
    readonly categoryLabel: string;
    readonly categoryLabels: Readonly<Record<AiExportSelectionKind, string>>;
    readonly selectionLabel: string;
    readonly selectionLabels: Readonly<Record<string, string>>;
    readonly selectionDescriptions: Readonly<Record<string, string>>;
    readonly detailLevelLabel: string;
    readonly detailLevelHelp: Readonly<Record<AiExportDetailLevel, string>>;
    readonly detailLevelLabels: Readonly<Record<AiExportDetailLevel, string>>;
    readonly periodLabel: string;
    readonly periodHelp: string;
    readonly periodPresetLabels: Readonly<Record<AiExportPeriodPreset, string>>;
    readonly periodUnitLabels: Readonly<Record<AiExportPeriodUnit, string>>;
    readonly periodUnitShortLabels: Readonly<Record<AiExportPeriodUnit, string>>;
    readonly userNotesLabel: string;
    readonly userNotesPlaceholder: string;
    readonly payloadStatsLabel: string;
    readonly backendEstimatedTokensLabel: string;
    readonly finalEstimatedTokensLabel: string;
    readonly tokenSeverityLabels: Readonly<Record<AiExportTokenSeverity, string>>;
    readonly prepareLabel: string;
    readonly preparingLabel: string;
    readonly copyAnywayLabel: string;
    readonly useCompactLabel: string;
}

export function estimateAiExportTokenSeverity(finalEstimatedTokens: number): AiExportTokenSeverity {
    if (finalEstimatedTokens >= AI_EXPORT_TOKEN_LARGE_THRESHOLD) return 'large';
    if (finalEstimatedTokens >= AI_EXPORT_TOKEN_WARNING_THRESHOLD) return 'warning';
    return 'normal';
}

export function normalizeAiExportPeriod(selection: AiExportPeriodSelection | undefined): AiExportPeriodSelection {
    const preset = selection && AI_EXPORT_PERIOD_PRESETS.includes(selection.preset) ? selection.preset : AI_EXPORT_DEFAULT_PERIOD.preset;
    const customUnit = selection && AI_EXPORT_PERIOD_UNITS.includes(selection.customUnit) ? selection.customUnit : AI_EXPORT_DEFAULT_PERIOD.customUnit;
    const customAmount = selection && Number.isFinite(selection.customAmount) ? Math.max(1, Math.floor(selection.customAmount)) : AI_EXPORT_DEFAULT_PERIOD.customAmount;
    return {preset, customAmount, customUnit};
}

function parseIsoDate(value: string): Date {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
    if (!match) throw new TypeError('AI Export snapshot date must use YYYY-MM-DD');
    const parsed = new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
    if (parsed.toISOString().slice(0, 10) !== value) throw new TypeError('AI Export snapshot date is invalid');
    return parsed;
}

function subtractMonths(end: Date, months: number): Date {
    const monthIndex = end.getUTCFullYear() * 12 + end.getUTCMonth() - months;
    const year = Math.floor(monthIndex / 12);
    const month = ((monthIndex % 12) + 12) % 12;
    const lastDay = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
    return new Date(Date.UTC(year, month, Math.min(end.getUTCDate(), lastDay)));
}

export function resolveAiExportPeriod(snapshotAsOf: string, selection: AiExportPeriodSelection | undefined): AiExportResolvedPeriod {
    const normalized = normalizeAiExportPeriod(selection);
    const end = parseIsoDate(snapshotAsOf);
    let start: Date;
    if (normalized.preset === '3m') start = subtractMonths(end, 3);
    else if (normalized.preset === '6m') start = subtractMonths(end, 6);
    else if (normalized.preset === '1y') start = subtractMonths(end, 12);
    else if (normalized.customUnit === 'months') start = subtractMonths(end, normalized.customAmount);
    else if (normalized.customUnit === 'years') start = subtractMonths(end, normalized.customAmount * 12);
    else {
        start = new Date(end);
        start.setUTCDate(start.getUTCDate() - normalized.customAmount * (normalized.customUnit === 'weeks' ? 7 : 1));
    }
    return {start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10)};
}

export function normalizeAiExportUserNotes(kind: AiExportSelectionKind, userNotes: string | undefined): string | undefined {
    const normalized = userNotes?.trim();
    return kind === 'analysis' && normalized ? normalized : undefined;
}

export function aiExportOptionsFingerprint(options: AiExportOptionsSelection): string {
    const period = normalizeAiExportPeriod(options.period);
    return JSON.stringify([
        'ai-export-options-v3',
        options.selectionKind,
        options.selectionId,
        options.detailLevel,
        period.preset,
        period.preset === 'custom' ? period.customAmount : null,
        period.preset === 'custom' ? period.customUnit : null,
        options.responseLanguage,
        normalizeAiExportUserNotes(options.selectionKind, options.userNotes) ?? null,
    ]);
}

export function areAiExportOptionsEqual(left: AiExportOptionsSelection, right: AiExportOptionsSelection): boolean {
    const leftPeriod = normalizeAiExportPeriod(left.period);
    const rightPeriod = normalizeAiExportPeriod(right.period);
    return (
        left.selectionKind === right.selectionKind &&
        left.selectionId === right.selectionId &&
        left.detailLevel === right.detailLevel &&
        leftPeriod.preset === rightPeriod.preset &&
        leftPeriod.customAmount === rightPeriod.customAmount &&
        leftPeriod.customUnit === rightPeriod.customUnit &&
        left.responseLanguage === right.responseLanguage &&
        normalizeAiExportUserNotes(left.selectionKind, left.userNotes) === normalizeAiExportUserNotes(right.selectionKind, right.userNotes)
    );
}

export function reconcileAiExportOptions(compatibility: AiExportCatalogCompatibilityResult, domain: AiExportDomain, options: AiExportOptionsSelection): AiExportOptionsSelection {
    const current = findCompatibleAiExportSelection(compatibility, options.selectionKind, options.selectionId);
    const fallback = selectionsForDomain(compatibility, domain, 'analysis')[0] ?? selectionsForDomain(compatibility, domain, 'dataset')[0];
    const selection = current?.domain === domain ? current : fallback;
    if (!selection) return options;
    const detailLevel = selection.supportedDetailLevels.includes(options.detailLevel) ? options.detailLevel : selection.supportedDetailLevels.includes('standard') ? 'standard' : selection.supportedDetailLevels[0];
    return {
        ...options,
        selectionKind: selection.kind,
        selectionId: selection.id,
        detailLevel,
        userNotes: normalizeAiExportUserNotes(selection.kind, options.userNotes),
        period: normalizeAiExportPeriod(options.period),
    };
}

export function aiExportStatsContextFingerprint(context: AiExportStatsContextFingerprintInput): string {
    return JSON.stringify(['ai-export-stats-context-v2', context.contextKey, context.snapshotAsOf, context.targetCurrency]);
}

export function isAiExportStatsRequestCurrent(requestGeneration: number, requestContextFingerprint: string, currentGeneration: number, currentContextFingerprint: string): boolean {
    return requestGeneration === currentGeneration && requestContextFingerprint === currentContextFingerprint;
}

export function getMatchingAiExportStats(lastStats: AiExportPromptStats | undefined, lastStatsFingerprint: string | undefined, currentFingerprint: string): AiExportPromptStats | undefined {
    return lastStatsFingerprint === currentFingerprint ? lastStats : undefined;
}
