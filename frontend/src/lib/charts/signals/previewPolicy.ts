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
}

function belongsToInstance(signal: RenderedSignal, instanceId: string): boolean {
    return signal.id === instanceId || signal.id.startsWith(`${instanceId}:`);
}

export function resolveSignalPreview(options: ResolveSignalPreviewOptions): SignalPreviewResolution {
    const definitionsByType = new Map(options.definitions.map((definition) => [definition.type, definition]));
    const signals: RenderedSignal[] = [];
    let hasBackendConfig = false;
    let hasBackendPreview = false;

    for (const config of options.configs) {
        const definition = definitionsByType.get(config.signalType);
        if (!definition) continue;

        if (definition.source === 'backend') {
            hasBackendConfig = true;
            if (options.mode === 'pair') {
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

    return {
        signals,
        backendState: options.mode === 'global' ? 'real-target-required' : hasBackendPreview ? 'apply-required' : 'unavailable',
    };
}
