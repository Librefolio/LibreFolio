import {describe, expect, it} from 'vitest';

import {AssetComparisonSignal} from '../AssetComparisonSignal';
import {DEFAULT_SIGNAL_COLORS, type SignalDefinition} from '../ChartSignal';
import {LinearSignal} from '../LinearSignal';
import {createSignal, createSignalConfig, getLocalSignalDefinitions, signalFromConfig} from '../registry';

/**
 * Registry behaviour: instance creation, default params, and palette assignment.
 *
 * `localSignalRegression.test.ts` already pins *which* signals are registered.
 * This file pins what the registry *does* with them — the part every "add a
 * signal" click goes through and that no test reached before.
 *
 * The palette is a fixed constant of the product, so the expected colours below
 * are stated as literals. They were derived independently from the hue circle
 * (blue ≈ 217°, amber ≈ 38°, violet ≈ 258°, pink ≈ 330°, cyan ≈ 189°, lime ≈ 84°),
 * never by running the picker and copying its answer.
 */

const [BLUE, AMBER, VIOLET, PINK, CYAN, LIME] = DEFAULT_SIGNAL_COLORS;

function definitionFor(type: string): SignalDefinition {
    const definition = getLocalSignalDefinitions().find((candidate) => candidate.type === type);
    if (!definition) throw new Error(`local definition '${type}' is missing`);
    return definition;
}

describe('registry — palette assignment', () => {
    it('cycles the palette by position when nothing is in use yet', () => {
        // existingCount indexes the palette directly; 7 wraps onto the second entry.
        expect(createSignal('linear', 0)?.style.color).toBe(BLUE);
        expect(createSignal('linear', 2)?.style.color).toBe(VIOLET);
        expect(createSignal('linear', 6)?.style.color).toBe(BLUE);
        expect(createSignal('linear', 7)?.style.color).toBe(AMBER);
    });

    it('answers a used colour with its hue opposite, not with the next palette slot', () => {
        // Amber sits ~180° from blue on the hue circle — the farthest the palette
        // can get. The "next slot" answer would have been amber for blue too, so
        // the second case is the one that separates the two rules: with amber
        // taken the pick jumps *back* to blue instead of forward to violet.
        expect(createSignal('linear', 0, [BLUE])?.style.color).toBe(AMBER);
        expect(createSignal('linear', 0, [AMBER])?.style.color).toBe(BLUE);
    });

    it('maximises the smallest distance when several colours are taken', () => {
        // blue+amber leave violet(41°), pink(67°), cyan(28°), lime(46°) as the
        // minimum distances — pink is the widest gap, and it is neither the next
        // free slot nor the opposite of either used colour.
        expect(createSignal('linear', 0, [BLUE, AMBER])?.style.color).toBe(PINK);
        expect(createSignal('linear', 0, [BLUE, AMBER, PINK])?.style.color).toBe(LIME);
    });

    it('treats an achromatic colour as hue zero', () => {
        // Grey has no hue; the formula collapses it to 0° (the red end), so the
        // farthest palette entry is cyan.
        expect(createSignal('linear', 0, ['#808080'])?.style.color).toBe(CYAN);
    });

    it('reuses the first palette entry once every colour is taken', () => {
        // Every candidate scores a minimum distance of 0, and the picker keeps the
        // first strict improvement over -1. Six signals in, colours start repeating.
        expect(createSignal('linear', 0, [...DEFAULT_SIGNAL_COLORS])?.style.color).toBe(BLUE);
    });

    it('ignores existingCount as soon as a used colour is supplied', () => {
        // The two rules are exclusive: a non-empty usedColors list wins outright.
        expect(createSignal('linear', 3, [BLUE])?.style.color).toBe(AMBER);
    });
});

describe('registry — createSignal', () => {
    it('returns null for a type the registry does not know', () => {
        expect(createSignal('ema', 0)).toBeNull();
    });

    it('builds an instance seeded with every declared default param', () => {
        const signal = createSignal('sine', 0);

        // Defaults come from the class descriptors: amplitude 15, period 45, offset 0.
        expect(signal).toBeInstanceOf(Object);
        expect(signal?.params).toEqual({amplitude: 15, period: 45, offset: 0});
        expect(signal?.getLabel()).toBe('Sine ±15% / 45d');
    });

    it('gives benchmarks a dashed line and comparisons a solid one', () => {
        expect(createSignal('linear', 0)?.style.lineType).toBe('dashed');
        expect(createSignal('compound', 0)?.style.lineType).toBe('dashed');
        expect(createSignal('sine', 0)?.style.lineType).toBe('dashed');
        expect(createSignal('fx-pair', 0)?.style.lineType).toBe('solid');
        expect(createSignal('asset-comparison', 0)?.style.lineType).toBe('solid');
    });

    it('draws asset comparison thicker than every other local signal', () => {
        expect(createSignal('asset-comparison', 0)?.style.lineWidth).toBe(2);
        expect(createSignal('fx-pair', 0)?.style.lineWidth).toBe(1);
        expect(createSignal('linear', 0)?.style.lineWidth).toBe(1);
    });

    it('leaves both endpoint markers off and gives each instance its own id', () => {
        const first = createSignal('linear', 0);
        const second = createSignal('linear', 1);

        expect(first?.style.markerStart).toBeNull();
        expect(first?.style.markerEnd).toBeNull();
        expect(first?.id).not.toBe(second?.id);
        expect(first?.id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
    });
});

describe('registry — createSignalConfig', () => {
    it('routes a local definition through its class, keeping the class defaults', () => {
        const config = createSignalConfig(definitionFor('asset-comparison'), 0);

        // lineWidth 2 is only reachable via AssetComparisonSignal's own rule; the
        // generic fallback below hands out 1 for everything.
        expect(config.signalType).toBe('asset-comparison');
        expect(config.style.lineWidth).toBe(2);
        expect(config.params).toEqual({assetId: ''});
    });

    it('drops the transient _resolvedData key when serialising a local signal', () => {
        const config = createSignalConfig(definitionFor('fx-pair'), 0);

        expect(config.params).toEqual({pairSlug: ''});
        expect(config.params).not.toHaveProperty('_resolvedData');
    });

    it('falls back to the generic shape when a local definition has no class', () => {
        const orphan: SignalDefinition = {
            ...definitionFor('asset-comparison'),
            type: 'asset-comparison-v2',
        };
        const config = createSignalConfig(orphan, 0);

        // Same source and same descriptors, but no constructor behind the type:
        // the config still comes out usable, on the generic width instead of 2.
        expect(config.signalType).toBe('asset-comparison-v2');
        expect(config.style.lineWidth).toBe(1);
        expect(config.params).toEqual({assetId: ''});
    });

    it('picks the line pattern from the category on the generic path', () => {
        const base = definitionFor('linear');
        const patternFor = (category: SignalDefinition['category']) => createSignalConfig({...base, type: `probe-${category}`, source: 'backend', category}, 0).style.lineType;

        expect(patternFor('indicator')).toBe('dotted');
        expect(patternFor('benchmark')).toBe('dashed');
        expect(patternFor('comparison')).toBe('solid');
        expect(patternFor('measure')).toBe('solid');
    });

    it('omits params whose descriptor declares no default', () => {
        const definition: SignalDefinition = {
            ...definitionFor('linear'),
            type: 'probe-partial-defaults',
            source: 'backend',
            paramDescriptors: [
                {key: 'period', label: 'Period', type: 'number', default: 14},
                {key: 'source', label: 'Source', type: 'string', default: undefined},
            ],
        };

        expect(createSignalConfig(definition, 0).params).toEqual({period: 14});
    });

    it('honours the palette rules on the generic path too', () => {
        const definition: SignalDefinition = {...definitionFor('linear'), type: 'probe-colour', source: 'backend'};

        expect(createSignalConfig(definition, 1).style.color).toBe(AMBER);
        expect(createSignalConfig(definition, 0, [BLUE]).style.color).toBe(AMBER);
    });
});

describe('registry — signalFromConfig', () => {
    it('rebuilds the declared class and preserves id, style and params', () => {
        const created = createSignal('linear', 0);
        const restored = signalFromConfig(created!.toConfig());

        expect(restored).toBeInstanceOf(LinearSignal);
        expect(restored?.id).toBe(created!.id);
        expect(restored?.params).toEqual({annualRate: 2, offset: 0});
        expect(restored?.style).toEqual(created!.style);
    });

    it('restores an asset comparison without its injected runtime data', () => {
        const signal = new AssetComparisonSignal('asset-7', {color: BLUE, lineWidth: 2, lineType: 'solid', markerStart: null, markerEnd: null}, {assetId: '7', _assetDisplayName: 'Acme', _resolvedData: [{date: '2026-01-01', value: 10}]});
        const restored = signalFromConfig(signal.toConfig());

        expect(restored).toBeInstanceOf(AssetComparisonSignal);
        expect(restored?.params).toEqual({assetId: '7', _assetDisplayName: 'Acme'});
        expect(restored?.getLabel()).toBe('Acme');
    });
});
