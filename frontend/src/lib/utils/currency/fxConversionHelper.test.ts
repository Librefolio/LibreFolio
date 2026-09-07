import {describe, expect, it} from 'vitest';

import {buildFxTooltipData, buildFxTooltipHtml, computeFxConversionInfo} from './fxConversionHelper';

const t = (key: string) => key;

describe('fxConversionHelper', () => {
    it('builds no-market tooltip data when the FX point has a zero rate', () => {
        const info = computeFxConversionInfo(-100, 'USD', 90, 'EUR');

        if (!info) throw new Error('Expected non-null FX conversion info');
        const data = buildFxTooltipData(info, {
            date: '2024-01-01',
            rate: 0,
            backwardFillInfo: {actualRateDate: '2023-12-29', daysBack: 3},
        });

        expect(data).toMatchObject({
            impliedRate: 0.9,
            base: 'USD',
            quote: 'EUR',
            marketRate: null,
            marketDate: null,
            staleDays: null,
            spread: null,
        });
    });

    it('builds no-market tooltip data when the FX point has a null rate', () => {
        const info = computeFxConversionInfo(-100, 'USD', 90, 'EUR');

        if (!info) throw new Error('Expected non-null FX conversion info');
        const data = buildFxTooltipData(info, {
            date: '2024-01-01',
            rate: null,
            backwardFillInfo: {actualRateDate: '2023-12-29', daysBack: 3},
        });

        expect(data).toMatchObject({
            impliedRate: 0.9,
            base: 'USD',
            quote: 'EUR',
            marketRate: null,
            marketDate: null,
            staleDays: null,
            spread: null,
        });
    });

    it('renders the market-not-available branch when market rate is null', () => {
        const html = buildFxTooltipHtml(
            {
                impliedRate: 0.9,
                base: 'USD',
                quote: 'EUR',
                marketRate: null,
                marketDate: null,
                staleDays: null,
                spread: null,
            },
            t,
        );

        expect(html).toContain('transactions.fxInfo.marketNotAvailable');
        expect(html).not.toContain('transactions.fxInfo.marketRate');
    });
});
