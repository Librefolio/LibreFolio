import type {BackendSignalRequest} from './backendTypes';
import type {SignalConfig, SignalDefinition} from './ChartSignal';
import {annualRiskFreeRate} from '$lib/features/risk/riskFreeRate';
import {riskFreeRate} from '$lib/features/risk/riskFreeRateStore.svelte';

export interface BackendSignalRequestPlan {
    requests: BackendSignalRequest[];
    backendConfigs: SignalConfig[];
    localConfigs: SignalConfig[];
    unavailableConfigs: SignalConfig[];
    instanceAliases: Map<string, string[]>;
}

/**
 * The parameters sent to the backend: the config's own, without the private ones (`_…`), and every parameter the
 * catalog binds to the reader's risk-free rate (`x-control: "risk_free_rate"`, RN-21) set from the one shared value —
 * a value the chart once saved there is left in the config and no longer read (the consultant, 17/11/2026).
 */
function backendParams(params: Record<string, unknown>, definition: SignalDefinition): Record<string, unknown> {
    const sent = Object.fromEntries(Object.entries(params).filter(([key]) => !key.startsWith('_')));
    for (const descriptor of definition.paramDescriptors) {
        if (descriptor.control === 'risk_free_rate') sent[descriptor.key] = annualRiskFreeRate(riskFreeRate.percent);
    }
    return sent;
}

/**
 * Whether one of these signals reads the reader's risk-free rate (a parameter bound to it, RN-21): a chart that shows one
 * asks again when the rate changes («A»), one that shows none has nothing to ask.
 */
export function readsRiskFreeRate(configs: readonly SignalConfig[], definitions: readonly SignalDefinition[]): boolean {
    const definitionsByType = new Map(definitions.map((definition) => [definition.type, definition]));
    return configs.some((config) => definitionsByType.get(config.signalType)?.paramDescriptors.some((descriptor) => descriptor.control === 'risk_free_rate') === true);
}

function stableJson(value: unknown): string {
    if (Array.isArray(value)) {
        return `[${value.map(stableJson).join(',')}]`;
    }
    if (value !== null && typeof value === 'object') {
        return `{${Object.entries(value)
            .sort(([left], [right]) => left.localeCompare(right))
            .map(([key, nested]) => `${JSON.stringify(key)}:${stableJson(nested)}`)
            .join(',')}}`;
    }
    return JSON.stringify(value);
}

function hasRequiredParams(config: SignalConfig, definition: SignalDefinition): boolean {
    return definition.paramDescriptors
        .filter((descriptor) => descriptor.required)
        .every((descriptor) => {
            const value = config.params[descriptor.key];
            return value !== undefined && value !== null && value !== '';
        });
}

export function buildBackendSignalRequestPlan(configs: SignalConfig[], definitions: SignalDefinition[]): BackendSignalRequestPlan {
    const definitionsByType = new Map(definitions.map((definition) => [definition.type, definition]));
    const requests: BackendSignalRequest[] = [];
    const backendConfigs: SignalConfig[] = [];
    const localConfigs: SignalConfig[] = [];
    const unavailableConfigs: SignalConfig[] = [];
    const instanceAliases = new Map<string, string[]>();
    const canonicalByRequestKey = new Map<string, string>();

    for (const config of configs) {
        const definition = definitionsByType.get(config.signalType);
        if (!definition) {
            unavailableConfigs.push(config);
            continue;
        }
        if (definition.source === 'local') {
            localConfigs.push(config);
            continue;
        }
        if (!definition.backendSignalCode) {
            unavailableConfigs.push(config);
            continue;
        }
        if (!hasRequiredParams(config, definition)) {
            unavailableConfigs.push(config);
            continue;
        }

        backendConfigs.push(config);
        const params = backendParams(config.params, definition);
        const requestKey = `${definition.backendSignalCode}:${stableJson(params)}`;
        const canonicalInstanceId = canonicalByRequestKey.get(requestKey);

        if (canonicalInstanceId) {
            instanceAliases.get(canonicalInstanceId)?.push(config.id);
            continue;
        }

        canonicalByRequestKey.set(requestKey, config.id);
        instanceAliases.set(config.id, [config.id]);
        requests.push({
            instance_id: config.id,
            signal_code: definition.backendSignalCode,
            params,
        });
    }

    return {
        requests,
        backendConfigs,
        localConfigs,
        unavailableConfigs,
        instanceAliases,
    };
}
