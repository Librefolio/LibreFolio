import type {BackendSignalRequest} from './backendTypes';
import type {SignalConfig, SignalDefinition} from './ChartSignal';

export interface BackendSignalRequestPlan {
    requests: BackendSignalRequest[];
    backendConfigs: SignalConfig[];
    localConfigs: SignalConfig[];
    unavailableConfigs: SignalConfig[];
    instanceAliases: Map<string, string[]>;
}

function backendParams(params: Record<string, unknown>): Record<string, unknown> {
    return Object.fromEntries(Object.entries(params).filter(([key]) => !key.startsWith('_')));
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

        backendConfigs.push(config);
        const params = backendParams(config.params);
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
