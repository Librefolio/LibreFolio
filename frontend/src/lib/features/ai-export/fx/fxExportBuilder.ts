/**
 * FX-pair AI export builder.
 *
 * Reuses the same technical context builder and generic methodology section as
 * the asset/portfolio exports, but scoped to one FX pair with canonical
 * base→quote rates, both directions pre-computed, and no RSI.
 */

import {ensureFxRangeLoaded, type FxDataPoint} from '$lib/stores/fxStoreRegistry';
import {buildMethodology} from '../aiExportBuilder';
import {buildTechnicalContext} from '../technical/technicalExportBuilder';
import {getResponseLanguage} from '../templates/languageMap';
import type {AiFxExport} from './fxTypes';

export interface FxExportInput {
    base: string;
    quote: string;
    slug: string;
    latestPoint: FxDataPoint;
}

export interface FxExportOptions {
    locale: string;
}

export async function buildFxAiExport(input: FxExportInput, options: FxExportOptions): Promise<AiFxExport> {
    const rateBaseToQuote = input.latestPoint.rate;
    const rateQuoteToBase = rateBaseToQuote !== 0 ? 1 / rateBaseToQuote : rateBaseToQuote;
    const endDate = input.latestPoint.date;

    const technicalResult = await buildTechnicalContext([
        {
            assetName: `${input.base}/${input.quote}`,
            endDate,
            loadPrices: (loadStart, technicalEndDate) =>
                ensureFxRangeLoaded(input.slug, loadStart, technicalEndDate).then((points) =>
                    points.map((p) => ({
                        date: p.date,
                        value: p.rate,
                        backwardFillInfo: p.backwardFillInfo,
                    })),
                ),
            computeRsi: false,
        },
    ]);

    return {
        metadata: {
            generated_at: new Date().toISOString(),
            response_language: getResponseLanguage(options.locale),
            export_purpose: 'single FX pair rate snapshot and trend explanation',
        },
        methodology: buildMethodology(),
        identity: {
            base: input.base,
            quote: input.quote,
            rate_base_to_quote: rateBaseToQuote,
            rate_quote_to_base: rateQuoteToBase,
            rate_date: input.latestPoint.date,
        },
        technical: technicalResult.assets[0] ?? null,
        technical_unavailable_reason: technicalResult.assets.length === 0 ? technicalResult.unavailable[0]?.reason : undefined,
        data_quality: {
            stale_rate: input.latestPoint.backwardFillInfo != null,
        },
    };
}
