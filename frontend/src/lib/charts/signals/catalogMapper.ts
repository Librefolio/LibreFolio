import type {BackendSignalCatalogDefinition} from './backendTypes';
import type {SignalAggregationProfile, SignalColorRole, SignalDefinition, SignalDomain, SignalIndicatorGroup, SignalInputField, SignalVisualComponent, SignalVisualPartition, SignalVisualStyle} from './ChartSignal';
import {mapSignalParamsSchema} from './schemaMapper';
import {defaultSignalVisualStyle} from './signalVisualStyle';

export function signalCodeToType(signalCode: string): string {
    return signalCode.trim().toLowerCase().replaceAll('_', '-');
}

function optionalString(value: unknown): string | undefined {
    if (typeof value === 'string') return value;
    if (!Array.isArray(value)) return undefined;
    return value.find((item): item is string => typeof item === 'string') ?? undefined;
}

function firstRecord(value: unknown): Record<string, unknown> | undefined {
    if (value && typeof value === 'object' && !Array.isArray(value)) return value as Record<string, unknown>;
    if (!Array.isArray(value)) return undefined;
    return value.find((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item));
}

function optionalNumber(value: unknown): number | undefined {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (!Array.isArray(value)) return undefined;
    return value.find((item): item is number => typeof item === 'number' && Number.isFinite(item));
}

function recordList(value: unknown): Record<string, unknown>[] {
    if (!Array.isArray(value)) return [];
    return value.flatMap((item) => {
        if (Array.isArray(item)) return item.filter((nested): nested is Record<string, unknown> => Boolean(nested) && typeof nested === 'object' && !Array.isArray(nested));
        return item && typeof item === 'object' ? [item as Record<string, unknown>] : [];
    });
}

function visualStyle(value: unknown): SignalVisualStyle {
    const record = firstRecord(value);
    if (!record) return defaultSignalVisualStyle();
    const colorRole = optionalString(record.color_role);
    const lineType = optionalString(record.line_pattern ?? record.pattern);
    return {
        colorRole: (colorRole === 'secondary' || colorRole === 'positive' || colorRole === 'negative' || colorRole === 'neutral' || colorRole === 'accent' ? colorRole : 'primary') satisfies SignalColorRole,
        lineType: lineType === 'solid' || lineType === 'dashed' || lineType === 'dotted' ? lineType : undefined,
        lineWidthDelta: typeof record.width_delta === 'number' ? record.width_delta : 0,
        opacity: typeof record.opacity === 'number' ? record.opacity : 1,
        fillOpacity: typeof record.fill_opacity === 'number' ? record.fill_opacity : 0.2,
    };
}

function aggregationProfile(value: unknown): SignalAggregationProfile {
    if (value === 'last_with_range' || value === 'first_with_range' || value === 'min_with_range' || value === 'max_with_range' || value === 'band_envelope' || value === 'events_verbatim') return value;
    throw new Error(`Unsupported or missing signal aggregation profile '${String(value)}'`);
}

function indicatorGroup(value: string): SignalIndicatorGroup {
    if (value === 'trend' || value === 'momentum' || value === 'volatility' || value === 'volume' || value === 'risk') return value;
    throw new Error(`Unsupported signal category '${value}'`);
}

function inputPriceFields(values: string[]): SignalInputField[] {
    return values.map((value) => {
        if (value === 'open' || value === 'high' || value === 'low' || value === 'close' || value === 'volume') return value;
        throw new Error(`Unsupported signal input field '${value}'`);
    });
}

function outputFullyPartitioned(output: BackendSignalCatalogDefinition['output_specs'][number]): boolean {
    const regions = recordList(output.default_value_regions)
        .map((region) => ({
            lower: optionalNumber(region.lower),
            upper: optionalNumber(region.upper),
            includeLower: region.include_lower !== false,
            includeUpper: region.include_upper === true,
        }))
        .sort((left, right) => (left.lower ?? Number.NEGATIVE_INFINITY) - (right.lower ?? Number.NEGATIVE_INFINITY));
    if (regions.length === 0 || regions[0].lower !== undefined || regions.at(-1)?.upper !== undefined) return false;

    for (let index = 1; index < regions.length; index++) {
        const previous = regions[index - 1];
        const current = regions[index];
        if (previous.upper === undefined || current.lower === undefined || previous.upper < current.lower) return false;
        if (previous.upper === current.lower && !previous.includeUpper && !current.includeLower) return false;
    }
    return true;
}

function visualComponents(catalog: BackendSignalCatalogDefinition): SignalVisualComponent[] {
    return catalog.output_specs.map((output) => ({
        key: output.key,
        labelKey: output.label_key,
        descriptionKey: optionalString(output.description_key),
        kind: output.kind,
        aggregationProfile: aggregationProfile(output.aggregation_profile),
        style: visualStyle(output.style),
        fullyPartitioned: outputFullyPartitioned(output),
    }));
}

function visualPartitions(catalog: BackendSignalCatalogDefinition): SignalVisualPartition[] {
    return catalog.output_specs.flatMap((output) =>
        recordList(output.default_value_regions).flatMap((region) => {
            const styleRecord = firstRecord(region.line_style);
            if (!styleRecord) return [];
            return [
                {
                    key: `${output.key}:${String(region.key ?? 'region')}`,
                    labelKey: String(region.label_key ?? ''),
                    descriptionKey: optionalString(region.description_key),
                    semantic: String(region.semantic ?? ''),
                    style: visualStyle(styleRecord),
                },
            ];
        }),
    );
}

export function mapBackendSignalDefinition(catalog: BackendSignalCatalogDefinition): SignalDefinition {
    const compatibleDomains = catalog.compatible_domains.filter((domain): domain is SignalDomain => domain === 'asset' || domain === 'fx');
    if (compatibleDomains.length !== catalog.compatible_domains.length) {
        throw new Error(`Signal '${catalog.signal_code}' contains an unsupported domain`);
    }

    const components = visualComponents(catalog);
    const partitions = visualPartitions(catalog);
    return {
        type: signalCodeToType(catalog.signal_code),
        displayName: catalog.signal_code,
        displayNameKey: catalog.display_name_key,
        descriptionKey: catalog.description_key,
        icon: catalog.icon,
        category: 'indicator',
        paramDescriptors: mapSignalParamsSchema(catalog.params_schema, catalog.default_params ?? {}),
        docsPath: optionalString(catalog.docs_path),
        source: 'backend',
        backendSignalCode: catalog.signal_code,
        indicatorGroup: indicatorGroup(catalog.category),
        inputPriceFields: inputPriceFields(catalog.input_requirements.price_fields ?? []),
        compatibleDomains,
        visualComponents: components,
        visualPartitions: partitions,
        paramsSchema: catalog.params_schema,
        defaultParams: catalog.default_params ?? {},
    };
}

export function mergeSignalDefinitions(remoteCatalog: BackendSignalCatalogDefinition[], localDefinitions: SignalDefinition[], domain: SignalDomain): SignalDefinition[] {
    const definitions = [...remoteCatalog.map(mapBackendSignalDefinition), ...localDefinitions.filter((definition) => definition.compatibleDomains?.includes(domain) ?? true)];
    const seen = new Set<string>();

    for (const definition of definitions) {
        if (seen.has(definition.type)) {
            throw new Error(`Duplicate signal definition '${definition.type}'`);
        }
        seen.add(definition.type);
    }

    return definitions;
}
