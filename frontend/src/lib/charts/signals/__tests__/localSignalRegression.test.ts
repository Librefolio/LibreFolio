import {describe, expect, it} from 'vitest';

import {AssetComparisonSignal} from '../AssetComparisonSignal';
import {FxPairSignal} from '../FxPairSignal';
import {LinearSignal} from '../LinearSignal';
import {MeasureSignal} from '../MeasureSignal';
import {getLocalSignalDefinitions} from '../registry';
import type {SignalStyle} from '../ChartSignal';

const style: SignalStyle = {
    color: '#3b82f6',
    lineWidth: 1,
    lineType: 'solid',
    markerStart: null,
    markerEnd: null,
};

const baseData = [
    {date: '2026-07-22', value: 100},
    {date: '2026-07-23', value: 110},
];

describe('local signal regression', () => {
    it('keeps only comparison and benchmark definitions in the local catalog', () => {
        expect(getLocalSignalDefinitions().map((definition) => definition.type)).toEqual(['fx-pair', 'asset-comparison', 'linear', 'compound', 'sine']);
    });

    it('keeps synthetic benchmark rendering local', () => {
        const signal = new LinearSignal('linear-1', style, {annualRate: 10, offset: 0});
        expect(signal.renderMulti(baseData, 'absolute')[0].data).toHaveLength(2);
    });

    it('keeps FX and Asset comparison rendering from injected data', () => {
        const fx = new FxPairSignal('fx-1', style, {
            pairSlug: 'EUR-USD',
            _resolvedData: baseData.map((point) => ({...point, value: point.value / 100})),
        });
        const asset = new AssetComparisonSignal('asset-1', style, {
            assetId: '42',
            _resolvedData: baseData,
        });

        const fxValues = fx.renderMulti(baseData, 'percentage')[0].data.map((point) => point.value);
        const assetValues = asset.renderMulti(baseData, 'percentage')[0].data.map((point) => point.value);
        expect(fxValues[0]).toBe(0);
        expect(fxValues[1]).toBeCloseTo(10);
        expect(assetValues[0]).toBe(0);
        expect(assetValues[1]).toBeCloseTo(10);
    });

    it('keeps Measure outside the registry and computes its result', () => {
        const measure = new MeasureSignal('measure-1', MeasureSignal.getDefaultStyle(), {
            startDate: '2026-07-22',
            endDate: '2026-07-23',
        });

        expect(measure.getMeasurement(baseData)).toMatchObject({
            deltaAbs: 10,
            deltaPct: 10,
            days: 1,
        });
        expect(getLocalSignalDefinitions().some((definition) => definition.type === 'measure')).toBe(false);
    });
});
