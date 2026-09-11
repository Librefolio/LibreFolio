import {zodiosApi} from '$lib/api';
import {safeToolTransportError} from '$lib/features/tools/client';
import {ToolClientError, runToolSessionTask} from '$lib/features/tools/contracts';

export interface PacAllocationSourceQuote {
    rawPrice: string | null;
    currency: string;
    quoteBaseQuantity: number;
    referenceDate: string | null;
    source: string | null;
    daysBeforeRequested: number | null;
}

export interface PacAllocationSourceContext {
    contextKey: string;
    brokerId: number;
    brokerName: string;
    ownershipSharePercent: string;
    custodyQuantity: string;
}

export interface PacAllocationSourceAsset {
    assetId: number;
    instrumentKey: string;
    name: string;
    ticker: string | null;
    assetType: string;
    iconUrl: string | null;
    quote: PacAllocationSourceQuote;
    contexts: readonly PacAllocationSourceContext[];
}

export interface PacAllocationSource {
    generatedAt: string;
    asOfDate: string;
    assets: readonly PacAllocationSourceAsset[];
}

function record(value: unknown): Record<string, unknown> {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) {
        throw new ToolClientError('protocol', 'invalid_response');
    }
    return value as Record<string, unknown>;
}

function stringValue(value: unknown): string {
    if (typeof value !== 'string') throw new ToolClientError('protocol', 'invalid_response');
    return value;
}

function optionalString(value: unknown): string | null {
    if (value === null || value === undefined) return null;
    return stringValue(value);
}

function numberValue(value: unknown): number {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new ToolClientError('protocol', 'invalid_response');
    }
    return value;
}

function optionalNumber(value: unknown): number | null {
    if (value === null || value === undefined) return null;
    return numberValue(value);
}

function arrayValue(value: unknown): readonly unknown[] {
    if (value === undefined) return [];
    if (!Array.isArray(value)) throw new ToolClientError('protocol', 'invalid_response');
    return value;
}

function normalizeSource(value: unknown): PacAllocationSource {
    const source = record(value);
    return {
        generatedAt: stringValue(source.generated_at),
        asOfDate: stringValue(source.as_of_date),
        assets: arrayValue(source.assets).map((assetValue): PacAllocationSourceAsset => {
            const asset = record(assetValue);
            const quote = record(asset.quote);
            return {
                assetId: numberValue(asset.asset_id),
                instrumentKey: stringValue(asset.instrument_key),
                name: stringValue(asset.name),
                ticker: optionalString(asset.ticker),
                assetType: stringValue(asset.asset_type),
                iconUrl: optionalString(asset.icon_url),
                quote: {
                    rawPrice: optionalString(quote.raw_price),
                    currency: stringValue(quote.currency),
                    quoteBaseQuantity: numberValue(quote.quote_base_quantity),
                    referenceDate: optionalString(quote.reference_date),
                    source: optionalString(quote.source),
                    daysBeforeRequested: optionalNumber(quote.days_before_requested),
                },
                contexts: arrayValue(asset.contexts).map((contextValue): PacAllocationSourceContext => {
                    const context = record(contextValue);
                    return {
                        contextKey: stringValue(context.context_key),
                        brokerId: numberValue(context.broker_id),
                        brokerName: stringValue(context.broker_name),
                        ownershipSharePercent: stringValue(context.ownership_share_percent),
                        custodyQuantity: stringValue(context.custody_quantity),
                    };
                }),
            };
        }),
    };
}

export async function fetchPacAllocationSource(asOfDate: string, accountGeneration: number, signal?: AbortSignal): Promise<PacAllocationSource> {
    try {
        return await runToolSessionTask(
            accountGeneration,
            async (requestSignal) => {
                const response = await zodiosApi.get_portfolio_report_api_v1_portfolio_report_post(
                    {
                        include_summary: false,
                        include_history: false,
                        include_allocation_history: false,
                        include_positions_contribution: false,
                        include_breakdown: false,
                        allocation_source: {as_of_date: asOfDate},
                    },
                    {signal: requestSignal},
                );
                return normalizeSource(response.allocation_source);
            },
            signal,
        );
    } catch (error) {
        throw safeToolTransportError(error, accountGeneration);
    }
}
