/**
 * Chart Signals Library — Barrel export.
 *
 * Provides chart overlay signals: real data (FxPairSignal) and
 * synthetic benchmarks (LinearSignal, CompoundSignal).
 *
 * Usage:
 *   import { createSignal, signalFromConfig, getRegisteredSignalTypes } from '$lib/charts/signals';
 *   import type { SignalConfig, RenderedSignal } from '$lib/charts/signals';
 */

// Base class & types
export {
    ChartSignal,
    DEFAULT_SIGNAL_COLORS,
    type MarkerType,
    type SignalParamDescriptor,
    type SignalStyle,
    type SignalConfig,
    type RenderedSignal,
} from './ChartSignal';

// Concrete signal classes
export {FxPairSignal} from './FxPairSignal';
export {LinearSignal} from './LinearSignal';
export {CompoundSignal} from './CompoundSignal';
export {SineSignal} from './SineSignal';
export {EmaSignal} from './EmaSignal';
export {MacdSignal} from './MacdSignal';
export {RsiSignal} from './RsiSignal';
export {BollingerSignal} from './BollingerSignal';

// Registry & factory
export {
    getRegisteredSignalTypes,
    createSignal,
    signalFromConfig,
    type SignalTypeInfo,
} from './registry';

