import type {RenderedSignal, SignalConfig, SignalDefinition} from './ChartSignal';

export type BackendPreviewState = 'none' | 'real-target-required' | 'apply-required' | 'unavailable';

export interface SignalPreviewResolution {
    signals: RenderedSignal[];
    backendState: BackendPreviewState;
}

interface ResolveSignalPreviewOptions {
    configs: SignalConfig[];
    definitions: SignalDefinition[];
    mode: 'global' | 'pair';
    backendSignals: RenderedSignal[];
    renderLocal: (config: SignalConfig) => RenderedSignal[];
    /** Global mode only: backend signals are computed live on the synthetic preview data. */
    globalLivePreview?: boolean;
    /** Global-live only: the live backend compute failed. */
    backendError?: boolean;
}

function belongsToInstance(signal: RenderedSignal, instanceId: string): boolean {
    return signal.id === instanceId || signal.id.startsWith(`${instanceId}:`);
}

export function resolveSignalPreview(options: ResolveSignalPreviewOptions): SignalPreviewResolution {
    const definitionsByType = new Map(options.definitions.map((definition) => [definition.type, definition]));
    const signals: RenderedSignal[] = [];
    let hasBackendConfig = false;
    let hasBackendPreview = false;

    // Backend signals resolve against a rendered list both in pair mode (last
    // applied) and in global-live mode (computed on the synthetic curve).
    const matchBackend = options.mode === 'pair' || options.globalLivePreview === true;

    for (const config of options.configs) {
        const definition = definitionsByType.get(config.signalType);
        if (!definition) continue;

        if (definition.source === 'backend') {
            hasBackendConfig = true;
            if (matchBackend) {
                const matchingSignals = options.backendSignals.filter((signal) => belongsToInstance(signal, config.id));
                if (matchingSignals.length > 0) {
                    hasBackendPreview = true;
                    signals.push(...matchingSignals);
                }
            }
            continue;
        }

        signals.push(...options.renderLocal(config));
    }

    if (!hasBackendConfig) {
        return {
            signals,
            backendState: 'none',
        };
    }

    let backendState: BackendPreviewState;
    if (options.mode === 'pair') {
        backendState = hasBackendPreview ? 'apply-required' : 'unavailable';
    } else if (options.globalLivePreview === true) {
        // Live preview on synthetic data: render whatever came back; only warn
        // when the backend compute genuinely failed (transient loading = no banner).
        backendState = options.backendError === true ? 'unavailable' : 'none';
    } else {
        backendState = 'real-target-required';
    }

    return {
        signals,
        backendState,
    };
}
