/**
 * Signal Registry — Maps signalType strings to constructors.
 * Provides factory functions for creating, deserializing, and querying signals.
 *
 * To add a new signal type:
 * 1. Create the class extending ChartSignal
 * 2. Add an entry to SIGNAL_REGISTRY below
 * 3. Done — the UI automatically picks it up via getRegisteredSignalTypes()
 */

import type {SignalParamDescriptor} from './ChartSignal';
import {ChartSignal, DEFAULT_SIGNAL_COLORS, type SignalConfig, type SignalStyle} from './ChartSignal';
import {generateUUID} from '$lib/utils/uuid';
import {FxPairSignal} from './FxPairSignal';
import {AssetComparisonSignal} from './AssetComparisonSignal';
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
    [AssetComparisonSignal.signalType, AssetComparisonSignal as unknown as SignalConstructor],
    [LinearSignal.signalType, LinearSignal as unknown as SignalConstructor],
    [CompoundSignal.signalType, CompoundSignal as unknown as SignalConstructor],
    [SineSignal.signalType, SineSignal as unknown as SignalConstructor],
    [EmaSignal.signalType, EmaSignal as unknown as SignalConstructor],
    [MacdSignal.signalType, MacdSignal as unknown as SignalConstructor],
    [RsiSignal.signalType, RsiSignal as unknown as SignalConstructor],
    [BollingerSignal.signalType, BollingerSignal as unknown as SignalConstructor],
]);

// ═══════════════════════════════════════════════════════════════════════════════
// COLOR DISTANCE — Pick signal colors maximally distant from those already in use
// ═══════════════════════════════════════════════════════════════════════════════

/** Extract hue (0–360) from a hex color string like '#3b82f6'. */
function hexToHue(hex: string): number {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    const max = Math.max(r, g, b),
        min = Math.min(r, g, b),
        d = max - min;
    if (d === 0) return 0;
    let h: number;
    if (max === r) h = ((g - b) / d) % 6;
    else if (max === g) h = (b - r) / d + 2;
    else h = (r - g) / d + 4;
    return (h * 60 + 360) % 360;
}

/**
 * Pick the palette color with max minimum-distance (hue-based, circular)
 * from all colors already in use. Falls back to simple index if no
 * usedColors are provided.
 */
function pickBestColor(usedColors: string[]): string {
    if (!usedColors.length) return DEFAULT_SIGNAL_COLORS[0];
    const usedHues = usedColors.map(hexToHue);
    let bestColor = DEFAULT_SIGNAL_COLORS[0];
    let bestDist = -1;
    for (const c of DEFAULT_SIGNAL_COLORS) {
        const h = hexToHue(c);
        const minDist = Math.min(
            ...usedHues.map((uh) => {
                const d = Math.abs(h - uh);
                return Math.min(d, 360 - d); // circular hue distance
            }),
        );
        if (minDist > bestDist) {
            bestDist = minDist;
            bestColor = c;
        }
    }
    return bestColor;
}

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC API
// ═══════════════════════════════════════════════════════════════════════════════

export interface SignalTypeInfo {
    type: string;
    displayName: string;
    icon: string;
    category: 'indicator' | 'comparison' | 'benchmark' | 'measure';
    paramDescriptors: SignalParamDescriptor[];
    /** Path to MkDocs documentation section, e.g. 'financial-theory/technical-analysis/indicators/ema/' */
    docsPath?: string;
}

/** All registered signal types (for "Add signal" dropdown in ChartSettingsModal). */
export function getRegisteredSignalTypes(): SignalTypeInfo[] {
    return [...SIGNAL_REGISTRY.values()].map((Cls) => ({
        type: Cls.signalType,
        displayName: Cls.displayName,
        icon: Cls.icon,
        category: Cls.category,
        paramDescriptors: Cls.paramDescriptors,
        docsPath: Cls.docsPath,
    }));
}

/**
 * Create a NEW signal instance with default params and best color from palette.
 * Colors are chosen to maximize perceptual distance from already-used colors.
 * Returns null if signalType is not registered.
 */
export function createSignal(signalType: string, existingCount: number, usedColors: string[] = []): ChartSignal | null {
    const Cls = SIGNAL_REGISTRY.get(signalType);
    if (!Cls) return null;

    const id = generateUUID();
    // Line width: indicator=1, benchmark=1, fx-pair=1, asset-comparison=2
    const defaultWidth = Cls.category === 'indicator' ? 1 : Cls.category === 'benchmark' ? 1 : Cls.signalType === 'fx-pair' ? 1 : 2; // asset-comparison
    // Line type: indicator=dotted, benchmark=dashed, comparison=solid, MACD=solid
    const defaultLineType: 'solid' | 'dashed' | 'dotted' = Cls.signalType === 'macd' ? 'solid' : Cls.category === 'indicator' ? 'dotted' : Cls.category === 'benchmark' ? 'dashed' : 'solid'; // comparison
    const color = usedColors.length > 0 ? pickBestColor(usedColors) : DEFAULT_SIGNAL_COLORS[existingCount % DEFAULT_SIGNAL_COLORS.length];
    const style: SignalStyle = {
        color,
        lineWidth: defaultWidth,
        lineType: defaultLineType,
        markerStart: null,
        markerEnd: null,
    };

    const params: Record<string, unknown> = {};
    for (const desc of Cls.paramDescriptors) {
        params[desc.key] = desc.default;
    }

    // MACD composite: set signal-line defaults so they match renderMulti() and the UI
    if (Cls.signalType === 'macd') {
        params._signalColor = style.color; // same color as primary
        params._signalLineWidth = 1; // thinner than MACD line
        params._signalLineType = 'dashed'; // dashed to distinguish
        params._signalMarkerStart = null;
        params._signalMarkerEnd = null;
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
