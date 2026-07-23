import type {BackendSignalCatalogDefinition} from './backendTypes';
import type {SignalDefinition, SignalDomain, SignalIndicatorGroup, SignalInputField} from './ChartSignal';
import {mapSignalParamsSchema} from './schemaMapper';

export function signalCodeToType(signalCode: string): string {
    return signalCode.trim().toLowerCase().replaceAll('_', '-');
}

function optionalString(value: unknown): string | undefined {
    return typeof value === 'string' ? value : undefined;
}

function indicatorGroup(value: string): SignalIndicatorGroup {
    if (value === 'trend' || value === 'momentum' || value === 'volatility' || value === 'volume') return value;
    throw new Error(`Unsupported signal category '${value}'`);
}

function inputPriceFields(values: string[]): SignalInputField[] {
    return values.map((value) => {
        if (value === 'open' || value === 'high' || value === 'low' || value === 'close' || value === 'volume') return value;
        throw new Error(`Unsupported signal input field '${value}'`);
    });
}

export function mapBackendSignalDefinition(catalog: BackendSignalCatalogDefinition): SignalDefinition {
    const compatibleDomains = catalog.compatible_domains.filter((domain): domain is SignalDomain => domain === 'asset' || domain === 'fx');
    if (compatibleDomains.length !== catalog.compatible_domains.length) {
        throw new Error(`Signal '${catalog.signal_code}' contains an unsupported domain`);
    }

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
