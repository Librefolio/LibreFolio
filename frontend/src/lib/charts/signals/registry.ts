/**
 * Signal Registry — Maps signalType strings to constructors.
 * Provides factory functions for creating, deserializing, and querying signals.
 *
 * To add a new signal type:
 * 1. Create the class extending ChartSignal
 * 2. Add an entry to SIGNAL_REGISTRY below
 * 3. Done — the UI automatically picks it up via getRegisteredSignalTypes()
 */

import {
    ChartSignal,
    type SignalConfig,
    type SignalStyle,
    DEFAULT_SIGNAL_COLORS,
} from './ChartSignal';
import {FxPairSignal} from './FxPairSignal';
import {LinearSignal} from './LinearSignal';
import {CompoundSignal} from './CompoundSignal';
import {SineSignal} from './SineSignal';
import {EmaSignal} from './EmaSignal';
import {MacdSignal} from './MacdSignal';
import {RsiSignal} from './RsiSignal';
import {BollingerSignal} from './BollingerSignal';

// Re-export for convenience
export type {SignalConfig, SignalStyle};

// ═══════════════════════════════════════════════════════════════════════════════
// REGISTRY MAP: signalType → constructor
// ═══════════════════════════════════════════════════════════════════════════════

// Use `as unknown as typeof ChartSignal` because TS doesn't allow direct
// assignment of concrete subclass constructors to an abstract constructor type.
type SignalConstructor = typeof ChartSignal;

const SIGNAL_REGISTRY = new Map<string, SignalConstructor>([
    [FxPairSignal.signalType, FxPairSignal as unknown as SignalConstructor],
    [LinearSignal.signalType, LinearSignal as unknown as SignalConstructor],
    [CompoundSignal.signalType, CompoundSignal as unknown as SignalConstructor],
    [SineSignal.signalType, SineSignal as unknown as SignalConstructor],
    [EmaSignal.signalType, EmaSignal as unknown as SignalConstructor],
    [MacdSignal.signalType, MacdSignal as unknown as SignalConstructor],
    [RsiSignal.signalType, RsiSignal as unknown as SignalConstructor],
    [BollingerSignal.signalType, BollingerSignal as unknown as SignalConstructor],
]);

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC API
// ═══════════════════════════════════════════════════════════════════════════════

import type {SignalParamDescriptor} from './ChartSignal';

export interface SignalTypeInfo {
    type: string;
    displayName: string;
    icon: string;
    category: 'indicator' | 'comparison' | 'benchmark';
    paramDescriptors: SignalParamDescriptor[];
}

/** All registered signal types (for "Add signal" dropdown in ChartSettingsModal). */
export function getRegisteredSignalTypes(): SignalTypeInfo[] {
    return [...SIGNAL_REGISTRY.values()].map(Cls => ({
        type: Cls.signalType,
        displayName: Cls.displayName,
        icon: Cls.icon,
        category: Cls.category,
        paramDescriptors: Cls.paramDescriptors,
    }));
}

/**
 * Create a NEW signal instance with default params and next color from palette.
 * Returns null if signalType is not registered.
 */
export function createSignal(signalType: string, existingCount: number): ChartSignal | null {
    const Cls = SIGNAL_REGISTRY.get(signalType);
    if (!Cls) return null;

    const id = crypto.randomUUID();
    const style: SignalStyle = {
        color: DEFAULT_SIGNAL_COLORS[existingCount % DEFAULT_SIGNAL_COLORS.length],
        lineWidth: 2,
        lineType: 'dashed',
        markerStart: null,
        markerEnd: null,
    };

    const params: Record<string, unknown> = {};
    for (const desc of Cls.paramDescriptors) {
        params[desc.key] = desc.default;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return new (Cls as any)(id, style, params);
}

/**
 * Recreate a signal instance from a serialized config.
 * Returns null if signalType is not registered.
 */
export function signalFromConfig(config: SignalConfig): ChartSignal | null {
    const Cls = SIGNAL_REGISTRY.get(config.signalType);
    if (!Cls) return null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return new (Cls as any)(config.id, config.style, config.params);
}


