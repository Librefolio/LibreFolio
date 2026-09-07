import type {BackendSignalResult} from './backendTypes';
import type {SignalConfig} from './ChartSignal';
import type {BackendSignalRequestPlan} from './requestBuilder';

export type SignalInstanceStatus = BackendSignalResult['status'] | 'local' | 'missing';

export interface SignalInstanceResult {
    config: SignalConfig;
    source: 'local' | 'backend' | 'unavailable';
    status: SignalInstanceStatus;
    result: BackendSignalResult | null;
    error: string | null;
}

function backendResultByInstance(plan: BackendSignalRequestPlan, results: BackendSignalResult[]): Map<string, BackendSignalResult> {
    const returnedByCanonicalId = new Map(results.map((result) => [result.instance_id, result]));
    const byInstance = new Map<string, BackendSignalResult>();

    for (const [canonicalId, aliases] of plan.instanceAliases) {
        const result = returnedByCanonicalId.get(canonicalId);
        if (!result) continue;
        for (const alias of aliases) {
            byInstance.set(alias, result);
        }
    }

    return byInstance;
}

export function mapSignalInstanceResults(configs: SignalConfig[], plan: BackendSignalRequestPlan, results: BackendSignalResult[]): SignalInstanceResult[] {
    const localIds = new Set(plan.localConfigs.map((config) => config.id));
    const unavailableIds = new Set(plan.unavailableConfigs.map((config) => config.id));
    const resultByInstance = backendResultByInstance(plan, results);

    return configs.map((config) => {
        if (localIds.has(config.id)) {
            return {
                config,
                source: 'local',
                status: 'local',
                result: null,
                error: null,
            };
        }

        if (unavailableIds.has(config.id)) {
            return {
                config,
                source: 'unavailable',
                status: 'missing',
                result: null,
                error: `Signal definition '${config.signalType}' is unavailable`,
            };
        }

        const result = resultByInstance.get(config.id);
        if (!result) {
            return {
                config,
                source: 'backend',
                status: 'missing',
                result: null,
                error: `Backend result for '${config.id}' is missing`,
            };
        }

        const resultError = Array.isArray(result.error) ? result.error.find((error) => error !== null)?.message : result.error?.message;
        return {
            config,
            source: 'backend',
            status: result.status,
            result,
            error: resultError ?? null,
        };
    });
}

export class SignalResultState {
    private requestVersion = 0;
    private current: SignalInstanceResult[] = [];

    beginRequest(): number {
        this.requestVersion += 1;
        return this.requestVersion;
    }

    apply(requestVersion: number, results: SignalInstanceResult[]): boolean {
        if (requestVersion !== this.requestVersion) return false;
        this.current = results;
        return true;
    }

    values(): SignalInstanceResult[] {
        return this.current;
    }
}
