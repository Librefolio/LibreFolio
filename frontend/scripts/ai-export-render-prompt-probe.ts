import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';

import {schemas} from '$lib/api';
import {buildAiExportSnapshotRequest, type AiExportRequestContext} from '$lib/features/ai-export/aiExportClipboard';
import {AI_EXPORT_DETAIL_LEVELS, normalizeAiExportSnapshotResponse, type AiExportCompatibleSelection, type AiExportDetailLevel} from '$lib/features/ai-export/catalog/shared';
import {reconcileAiExportCatalog, type AiExportCatalogCompatibilityResult} from '$lib/features/ai-export/catalog/compatibility';
import {AI_EXPORT_PERIOD_PRESETS, AI_EXPORT_PERIOD_UNITS, type AiExportOptionsSelection, type AiExportPeriodPreset, type AiExportPeriodSelection, type AiExportPeriodUnit} from '$lib/features/ai-export/aiExportOptions';
import {serializeYaml} from '$lib/features/ai-export/serialization';
import {AI_EXPORT_RESPONSE_LANGUAGE_DISPLAY_NAMES, renderAiExportPrompt, renderAiExportPromptDiagnostics, type AiExportPromptDiagnosticTextBlock, type AiExportResponseLanguageDisplayName} from '$lib/features/ai-export/templates/promptRenderer';

type ProbeAction = 'prepare' | 'render';
type ProbeMode = 'data' | 'analysis';
type ProbeLocale = 'en' | 'it' | 'fr' | 'es';

interface ProbeMessage {
    readonly request_id: string;
    readonly action: ProbeAction;
    readonly catalog: unknown;
    readonly selection_kind: 'dataset' | 'analysis';
    readonly selection_id: string;
    readonly context?: unknown;
    readonly detail_level?: unknown;
    readonly period?: unknown;
    readonly response_language?: unknown;
    readonly locale?: unknown;
    readonly user_notes?: unknown;
    readonly snapshot?: unknown;
    readonly legacy_technical_sampling?: unknown;
}

interface TextMeasurement {
    readonly unicode_characters: number;
    readonly utf16_code_units: number;
    readonly utf8_bytes: number;
    readonly lines: number;
    readonly words: number;
}

interface MeasuredBlock extends TextMeasurement {
    readonly id: string;
}

interface ComponentMeasurement extends MeasuredBlock {
    readonly category: string;
    readonly dataset_ids: readonly string[];
    readonly attributed_dataset_id: string;
}

interface DatasetMeasurement extends TextMeasurement {
    readonly dataset_id: string;
    readonly component_ids: readonly string[];
}

const encoder = new TextEncoder();
const localeCache = new Map<ProbeLocale, Record<string, unknown>>();

function isRecord(value: unknown): value is Record<string, unknown> {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function requireRecord(value: unknown, label: string): Record<string, unknown> {
    if (!isRecord(value)) throw new TypeError(`${label} must be an object`);
    return value;
}

function requireString(value: unknown, label: string): string {
    if (typeof value !== 'string' || value.length === 0) throw new TypeError(`${label} must be a non-empty string`);
    return value;
}

function optionalString(value: unknown, label: string): string | undefined {
    if (value === undefined || value === null || value === '') return undefined;
    return requireString(value, label);
}

function requireInteger(value: unknown, label: string): number {
    if (typeof value !== 'number' || !Number.isInteger(value)) throw new TypeError(`${label} must be an integer`);
    return value;
}

function optionalIntegerArray(value: unknown, label: string): readonly number[] | undefined {
    if (value === undefined || value === null) return undefined;
    if (!Array.isArray(value)) throw new TypeError(`${label} must be an array`);
    return value.map((item, index) => requireInteger(item, `${label}[${index}]`));
}

function parseContext(value: unknown): AiExportRequestContext {
    const context = requireRecord(value, 'context');
    const domain = requireString(context.domain, 'context.domain');
    const snapshotAsOf = requireString(context.snapshotAsOf, 'context.snapshotAsOf');
    const targetCurrency = requireString(context.targetCurrency, 'context.targetCurrency');
    if (domain === 'portfolio') {
        return {
            domain,
            snapshotAsOf,
            targetCurrency,
            brokerIds: optionalIntegerArray(context.brokerIds, 'context.brokerIds'),
        };
    }
    if (domain === 'broker') {
        return {
            domain,
            snapshotAsOf,
            targetCurrency,
            brokerId: requireInteger(context.brokerId, 'context.brokerId'),
        };
    }
    if (domain === 'asset') {
        return {
            domain,
            snapshotAsOf,
            targetCurrency,
            assetId: requireInteger(context.assetId, 'context.assetId'),
            brokerIds: optionalIntegerArray(context.brokerIds, 'context.brokerIds'),
        };
    }
    if (domain === 'fx') {
        return {
            domain,
            snapshotAsOf,
            targetCurrency,
            baseCurrency: requireString(context.baseCurrency, 'context.baseCurrency'),
            quoteCurrency: requireString(context.quoteCurrency, 'context.quoteCurrency'),
            brokerIds: optionalIntegerArray(context.brokerIds, 'context.brokerIds'),
        };
    }
    throw new TypeError(`unsupported context.domain: ${domain}`);
}

function parseDetailLevel(value: unknown): AiExportDetailLevel {
    if (!isDetailLevel(value)) {
        throw new TypeError(`unsupported detail_level: ${String(value)}`);
    }
    return value;
}

function isDetailLevel(value: unknown): value is AiExportDetailLevel {
    return typeof value === 'string' && AI_EXPORT_DETAIL_LEVELS.some((detail) => detail === value);
}

function isPeriodPreset(value: unknown): value is AiExportPeriodPreset {
    return typeof value === 'string' && AI_EXPORT_PERIOD_PRESETS.some((preset) => preset === value);
}

function isPeriodUnit(value: unknown): value is AiExportPeriodUnit {
    return typeof value === 'string' && AI_EXPORT_PERIOD_UNITS.some((unit) => unit === value);
}

function parsePeriod(value: unknown): AiExportPeriodSelection {
    const period = requireRecord(value, 'period');
    const preset = period.preset;
    const customUnit = period.customUnit;
    if (!isPeriodPreset(preset)) {
        throw new TypeError(`unsupported period.preset: ${String(preset)}`);
    }
    if (!isPeriodUnit(customUnit)) {
        throw new TypeError(`unsupported period.customUnit: ${String(customUnit)}`);
    }
    return {
        preset,
        customAmount: requireInteger(period.customAmount, 'period.customAmount'),
        customUnit,
    };
}

function parseResponseLanguage(value: unknown): AiExportResponseLanguageDisplayName {
    if (!isResponseLanguage(value)) {
        throw new TypeError(`unsupported response_language: ${String(value)}`);
    }
    return value;
}

function isResponseLanguage(value: unknown): value is AiExportResponseLanguageDisplayName {
    return typeof value === 'string' && AI_EXPORT_RESPONSE_LANGUAGE_DISPLAY_NAMES.some((language) => language === value);
}

function parseLocale(value: unknown): ProbeLocale {
    if (value === 'en' || value === 'it' || value === 'fr' || value === 'es') return value;
    throw new TypeError(`unsupported locale: ${String(value)}`);
}

function loadLocale(locale: ProbeLocale): Record<string, unknown> {
    const cached = localeCache.get(locale);
    if (cached) return cached;
    const frontendRoot = process.env.LIBREFOLIO_FRONTEND_ROOT || process.cwd();
    const parsed = JSON.parse(readFileSync(resolve(frontendRoot, 'src', 'lib', 'i18n', `${locale}.json`), 'utf8')) as unknown;
    const translations = requireRecord(parsed, `locale ${locale}`);
    localeCache.set(locale, translations);
    return translations;
}

export function probeTranslation(locale: ProbeLocale): (key: string) => string {
    const translations = loadLocale(locale);
    return (key: string): string => {
        let current: unknown = translations;
        for (const segment of key.split('.')) {
            if (!isRecord(current) || !(segment in current)) return key;
            current = current[segment];
        }
        return typeof current === 'string' ? current : key;
    };
}

function compatibility(message: ProbeMessage): AiExportCatalogCompatibilityResult {
    const catalog = schemas.AiExportCatalogResponse.parse(message.catalog);
    const result = reconcileAiExportCatalog(catalog);
    if (result.status !== 'compatible') {
        throw new Error(`frontend catalog compatibility failed: ${result.reasonCodes.join(',') || 'unknown'}`);
    }
    return result;
}

function selection(result: AiExportCatalogCompatibilityResult, message: ProbeMessage): AiExportCompatibleSelection {
    const selected = result.selections.find((item) => item.kind === message.selection_kind && item.id === message.selection_id);
    if (!selected) throw new Error(`selection is not compatible with the frontend catalog: ${message.selection_kind}:${message.selection_id}`);
    return selected;
}

function measureText(content: string): TextMeasurement {
    const trimmed = content.trim();
    return {
        unicode_characters: Array.from(content).length,
        utf16_code_units: content.length,
        utf8_bytes: encoder.encode(content).length,
        lines: content.length === 0 ? 0 : content.split('\n').length,
        words: trimmed.length === 0 ? 0 : trimmed.split(/\s+/u).length,
    };
}

function measureBlock(block: AiExportPromptDiagnosticTextBlock): MeasuredBlock {
    return {
        id: block.id,
        ...measureText(block.content),
    };
}

function componentCategory(componentId: string): string {
    if (componentId.includes('technical_prices') || componentId.includes('ohlc_returns') || componentId.includes('rate_ohlc')) return 'technical_prices';
    if (componentId.includes('technical_indicators') || componentId.endsWith('.indicators') || componentId.includes('returns_volatility')) return 'technical_indicators';
    if (componentId.includes('technical_events') || componentId.includes('states_events')) return 'technical_events';
    if (componentId.includes('technical_breadth')) return 'technical_breadth';
    if (componentId.includes('position') || componentId.includes('allocation') || componentId.includes('concentration')) return 'holdings_allocation';
    if (componentId.includes('performance') || componentId.includes('flow') || componentId.includes('income') || componentId.includes('reconciliation')) return 'performance_flows';
    if (componentId.includes('transaction')) return 'transactions';
    if (componentId.includes('fifo') || componentId.includes('lot')) return 'fifo_lots';
    if (componentId.includes('fee') || componentId.includes('tax') || componentId.includes('cost')) return 'costs_taxes';
    if (componentId.startsWith('fx.') || componentId.includes('currency')) return 'fx';
    if (componentId.includes('summary') || componentId.includes('overview') || componentId.includes('provenance')) return 'financial_overview';
    return 'other';
}

function measureComponents(
    blocks: readonly AiExportPromptDiagnosticTextBlock[],
    result: AiExportCatalogCompatibilityResult,
    snapshot: ReturnType<typeof normalizeAiExportSnapshotResponse>,
): {
    components: readonly ComponentMeasurement[];
    datasets: readonly DatasetMeasurement[];
} {
    const datasetsById = new Map(result.catalog.datasets.map((entry) => [entry.id, entry]));
    const manifestOrder = snapshot.dataset_manifest.map((entry) => entry.dataset_id);
    const components = blocks.map((block) => {
        const datasetIds = manifestOrder.filter((datasetId) => {
            const dataset = datasetsById.get(datasetId);
            return dataset ? [...dataset.required_component_ids, ...dataset.optional_component_ids].includes(block.id) : false;
        });
        const attributedDatasetId = datasetIds[0] ?? '__unattributed__';
        return {
            ...measureBlock(block),
            category: componentCategory(block.id),
            dataset_ids: datasetIds,
            attributed_dataset_id: attributedDatasetId,
        };
    });

    const datasets = manifestOrder.map((datasetId) => {
        const attributed = components.filter((component) => component.attributed_dataset_id === datasetId);
        return {
            dataset_id: datasetId,
            component_ids: attributed.map((component) => component.id),
            unicode_characters: attributed.reduce((total, component) => total + component.unicode_characters, 0),
            utf16_code_units: attributed.reduce((total, component) => total + component.utf16_code_units, 0),
            utf8_bytes: attributed.reduce((total, component) => total + component.utf8_bytes, 0),
            lines: attributed.reduce((total, component) => total + component.lines, 0),
            words: attributed.reduce((total, component) => total + component.words, 0),
        };
    });
    const unattributed = components.filter((component) => component.attributed_dataset_id === '__unattributed__');
    if (unattributed.length > 0) {
        datasets.push({
            dataset_id: '__unattributed__',
            component_ids: unattributed.map((component) => component.id),
            unicode_characters: unattributed.reduce((total, component) => total + component.unicode_characters, 0),
            utf16_code_units: unattributed.reduce((total, component) => total + component.utf16_code_units, 0),
            utf8_bytes: unattributed.reduce((total, component) => total + component.utf8_bytes, 0),
            lines: unattributed.reduce((total, component) => total + component.lines, 0),
            words: unattributed.reduce((total, component) => total + component.words, 0),
        });
    }
    return {components, datasets};
}

function subtractMeasurements(total: TextMeasurement, parts: readonly TextMeasurement[]): TextMeasurement {
    return {
        unicode_characters: total.unicode_characters - parts.reduce((sum, part) => sum + part.unicode_characters, 0),
        utf16_code_units: total.utf16_code_units - parts.reduce((sum, part) => sum + part.utf16_code_units, 0),
        utf8_bytes: total.utf8_bytes - parts.reduce((sum, part) => sum + part.utf8_bytes, 0),
        lines: total.lines - parts.reduce((sum, part) => sum + Math.max(0, part.lines - 1), 0),
        words: total.words - parts.reduce((sum, part) => sum + part.words, 0),
    };
}

function measureManifestImpact(prompt: string, currentBlock: AiExportPromptDiagnosticTextBlock | undefined, legacyValue: unknown): Record<string, unknown> | null {
    if (!currentBlock || !isRecord(legacyValue)) return null;
    const occurrences = prompt.split(currentBlock.content).length - 1;
    if (occurrences !== 1) throw new Error(`technical sampling block occurs ${occurrences} times in the rendered prompt`);
    const legacyBlock = serializeYaml({technical_sampling: legacyValue});
    const legacyPrompt = prompt.replace(currentBlock.content, legacyBlock);
    const beforeManifest = measureText(legacyBlock);
    const afterManifest = measureText(currentBlock.content);
    const beforePrompt = measureText(legacyPrompt);
    const afterPrompt = measureText(prompt);
    return {
        method: 'exact_official_yaml_field_substitution_v1',
        manifest_before: beforeManifest,
        manifest_after: afterManifest,
        prompt_before: beforePrompt,
        prompt_after: afterPrompt,
        saved_unicode_characters: beforePrompt.unicode_characters - afterPrompt.unicode_characters,
        saved_utf8_bytes: beforePrompt.utf8_bytes - afterPrompt.utf8_bytes,
        saved_estimated_token_equivalent_chars_div_4: (beforePrompt.unicode_characters - afterPrompt.unicode_characters) / 4,
    };
}

function probeMode(kind: 'dataset' | 'analysis'): ProbeMode {
    return kind === 'dataset' ? 'data' : 'analysis';
}

function prepare(message: ProbeMessage): Record<string, unknown> {
    const reconciled = compatibility(message);
    const selected = selection(reconciled, message);
    const options: AiExportOptionsSelection = {
        selectionKind: selected.kind,
        selectionId: selected.id,
        detailLevel: parseDetailLevel(message.detail_level),
        period: parsePeriod(message.period),
        responseLanguage: parseResponseLanguage(message.response_language),
        userNotes: optionalString(message.user_notes, 'user_notes'),
    };
    const request = buildAiExportSnapshotRequest(parseContext(message.context), options, selected);
    return {
        request_id: message.request_id,
        action: 'prepare',
        ok: true,
        mode: probeMode(selected.kind),
        compatibility: {
            status: reconciled.status,
            dataset_count: reconciled.catalog.datasets.length,
            analysis_count: reconciled.catalog.analyses.length,
            selection_count: reconciled.selections.length,
            reason_codes: reconciled.reasonCodes,
        },
        request,
    };
}

function render(message: ProbeMessage): Record<string, unknown> {
    const reconciled = compatibility(message);
    const selected = selection(reconciled, message);
    const snapshot = normalizeAiExportSnapshotResponse(schemas.AiExportSnapshotResponse.parse(message.snapshot));
    const input = {
        selection: selected,
        compatibility: reconciled,
        snapshot,
        responseLanguage: parseResponseLanguage(message.response_language),
        userNotes: optionalString(message.user_notes, 'user_notes'),
        translate: probeTranslation(parseLocale(message.locale)),
    } as const;
    const uiRendered = renderAiExportPrompt(input);
    const diagnostics = renderAiExportPromptDiagnostics(input);
    if (uiRendered.prompt !== diagnostics.rendered.prompt) throw new Error('AI Export UI and probe renderer output differ');
    const promptMeasurement = measureText(uiRendered.prompt);
    const sections = diagnostics.sections.map(measureBlock);
    const separatorCount = Math.max(0, sections.length - 1);
    const separators = measureText(diagnostics.sectionSeparator.repeat(separatorCount));
    const metadataFields = diagnostics.snapshotMetadataFields.map(measureBlock);
    const snapshotDataSection = sections.find((section) => section.id === 'snapshot_data');
    const snapshotMetadataSection = sections.find((section) => section.id === 'snapshot_metadata');
    if (!snapshotDataSection || !snapshotMetadataSection) throw new Error('rendered prompt is missing required snapshot sections');

    const {components, datasets} = measureComponents(diagnostics.snapshotDataComponents, reconciled, snapshot);
    const snapshotDataWrapper = subtractMeasurements(snapshotDataSection, components);
    const snapshotMetadataWrapper = subtractMeasurements(snapshotMetadataSection, metadataFields);
    const technicalSampling = diagnostics.snapshotMetadataFields.find((block) => block.id === 'technical_sampling')?.content ?? '';
    const technicalSamplingBlock = diagnostics.snapshotMetadataFields.find((block) => block.id === 'technical_sampling');
    const reconciledCharacters = sections.reduce((total, section) => total + section.unicode_characters, 0) + separators.unicode_characters;
    const reconciledBytes = sections.reduce((total, section) => total + section.utf8_bytes, 0) + separators.utf8_bytes;

    return {
        request_id: message.request_id,
        action: 'render',
        ok: true,
        mode: probeMode(selected.kind),
        prompt: uiRendered.prompt,
        frontend_stats: uiRendered.stats,
        renderer_equivalence: {
            ui_function: 'renderAiExportPrompt',
            diagnostic_function: 'renderAiExportPromptDiagnostics',
            exact_string_match: true,
            utf8_bytes_match: measureText(uiRendered.prompt).utf8_bytes === measureText(diagnostics.rendered.prompt).utf8_bytes,
        },
        prompt_measurement: promptMeasurement,
        breakdown: {
            sections,
            separators: {
                count: separatorCount,
                ...separators,
            },
            snapshot_metadata_fields: metadataFields,
            snapshot_metadata_wrapper: snapshotMetadataWrapper,
            snapshot_data_format_preamble: measureText(diagnostics.snapshotDataFormatPreamble),
            entity_directory: measureText(diagnostics.snapshotDataEntityDirectory),
            snapshot_data_components: components,
            snapshot_data_datasets: datasets,
            snapshot_data_wrapper: snapshotDataWrapper,
            signal_metrics: diagnostics.snapshotSignalMetrics,
            format_diagnostics: diagnostics.snapshotFormatDiagnostics,
            reconciliation: {
                unicode_characters_match: reconciledCharacters === promptMeasurement.unicode_characters,
                utf8_bytes_match: reconciledBytes === promptMeasurement.utf8_bytes,
                reconciled_unicode_characters: reconciledCharacters,
                reconciled_utf8_bytes: reconciledBytes,
            },
        },
        manifest_checks: {
            has_technical_sampling: technicalSampling.length > 0,
            implementation_parameter_lines: technicalSampling.match(/^\s*[pmk]:/gmu)?.length ?? 0,
            has_detail_level: /^\s*detail_level:/mu.test(technicalSampling),
            has_price_bucket_count: /^\s*price_bucket_count:/mu.test(technicalSampling),
            has_instance_temporal_class: diagnostics.rendered.prompt.includes('|instance_id|temporal_class|bucket_count'),
            has_instance_bucket_count: diagnostics.rendered.prompt.includes('|instance_id|temporal_class|bucket_count'),
        },
        manifest_impact: measureManifestImpact(uiRendered.prompt, technicalSamplingBlock, message.legacy_technical_sampling),
    };
}

export async function handleProbeMessage(raw: unknown): Promise<Record<string, unknown>> {
    const message = requireRecord(raw, 'probe message');
    const parsed: ProbeMessage = {
        request_id: requireString(message.request_id, 'request_id'),
        action:
            message.action === 'prepare' || message.action === 'render'
                ? message.action
                : (() => {
                      throw new TypeError(`unsupported action: ${String(message.action)}`);
                  })(),
        catalog: message.catalog,
        selection_kind:
            message.selection_kind === 'dataset' || message.selection_kind === 'analysis'
                ? message.selection_kind
                : (() => {
                      throw new TypeError(`unsupported selection_kind: ${String(message.selection_kind)}`);
                  })(),
        selection_id: requireString(message.selection_id, 'selection_id'),
        context: message.context,
        detail_level: message.detail_level,
        period: message.period,
        response_language: message.response_language,
        locale: message.locale,
        user_notes: message.user_notes,
        snapshot: message.snapshot,
        legacy_technical_sampling: message.legacy_technical_sampling,
    };
    return parsed.action === 'prepare' ? prepare(parsed) : render(parsed);
}
