/**
 * Domain copies for the PAC planner (C1).
 *
 * One client for `POST /portfolio/allocation-source`, plus 1:1 mappers from
 * the response rows to draft facts. No sums, no conversions and no provider
 * refresh: `/assets/prices/current` can write OHLC and is never called here.
 * A 403 or 404 reaches the user as an explicit error, never as a Broker or an
 * Asset silently dropped.
 */
import {isAxiosError} from 'axios';
import {zodiosApi} from '$lib/api';
import {safeToolTransportError} from '$lib/features/tools/client';
import {ToolClientError, assertToolAccount, runToolSessionTask} from '$lib/features/tools/contracts';

export type SourceSection = 'assets' | 'brokers' | 'holdings' | 'cash_balances' | 'prices' | 'classifications' | 'wac_contexts' | 'fx_quotes' | 'current_distribution';
export type SourceDomain = 'portfolio' | 'market_data' | 'broker' | 'fx' | 'wac';
export type ExposureDimension = 'asset_type' | 'sector' | 'geography';

export interface SourceQuery {
    asOf: string;
    targetCurrency: string;
    sections: readonly SourceSection[];
    brokerIds: readonly number[];
    /** `null` reads the held Assets; a list reads exactly those. */
    assetIds: readonly number[] | null;
    fxPairs: readonly string[];
}

export interface SourceProvenance {
    provenance_id: string;
    domain: SourceDomain;
    source_ref: string;
    source_label: string | null;
    captured_at: string;
}

export interface SourceAsset {
    asset_id: string;
    source_asset_id: number;
    name: string;
    ticker: string | null;
    asset_class: string;
    icon_url: string | null;
    active: boolean;
    provenance_id: string;
}

export interface SourceBroker {
    broker_id: string;
    source_broker_id: number;
    name: string;
    icon_url: string | null;
    access_role: string;
    ownership_share: string;
    observed_currencies: string[];
    active: boolean;
    execution_profile_status: string;
    provenance_id: string;
}

/**
 * Which Asset is held at which Broker. Identifiers only: the picker of the
 * user's own Assets needs no quantity, so none crosses into the planner.
 */
export interface SourceHolding {
    holding_id: string;
    asset_id: string;
    broker_id: string;
    provenance_id: string;
}

export interface SourceCash {
    cash_id: string;
    broker_id: string;
    currency: string;
    custody_amount: string;
    ownership_share: string;
    economic_amount: string;
    provenance_id: string;
}

export interface SourcePrice {
    price_id: string;
    asset_id: string;
    amount: string | null;
    currency: string | null;
    quote_base_quantity: string | null;
    reference_date: string | null;
    source: string | null;
    days_before_requested: number | null;
    provenance_id: string;
}

export interface SourceClassification {
    classification_id: string;
    asset_id: string;
    dimension: ExposureDimension;
    category_id: string | null;
    label: string | null;
    weight: string | null;
    provenance_id: string;
}

export interface SourceFxQuote {
    fx_quote_id: string;
    pair: string;
    rate: string | null;
    reference_date: string | null;
    source: string | null;
    days_before_requested: number | null;
    provenance_id: string;
}

export interface SourceCurrentWeight {
    weight_id: string;
    asset_id: string;
    held: boolean;
    weight: string | null;
    valuation_source: 'MARKET_PRICE' | 'LAST_TRADE_PRICE' | 'MISSING' | null;
    valuation_reference_date: string | null;
    valuation_days_before_requested: number | null;
    valuation_stale: boolean;
}

export interface SourceCurrentDistribution {
    status: 'complete' | 'incomplete' | 'no_holdings';
    weight_quantum: string;
    as_of: string;
    provenance_id: string;
    rows: SourceCurrentWeight[];
}

export type SourceIssuePath = {kind: 'root'} | {kind: 'section'; section: string} | {kind: 'entity'; section: string; entity_kind: string; entity_id: string} | {kind: 'field'; section: string; entity_kind: string; entity_id: string; field: string};

export type SourceIssueParam =
    | {kind: 'text'; name: string; value: string}
    | {kind: 'integer'; name: string; value: number}
    | {kind: 'money'; name: string; amount: string; currency: string}
    | {kind: 'date'; name: string; value: string}
    | {kind: 'entity_ref'; name: string; entity_kind: string; entity_id: string};

export interface SourceIssue {
    code: string;
    kind: 'missing' | 'invalid' | 'unsupported' | 'info';
    severity: 'error' | 'warning' | 'info';
    path: SourceIssuePath;
    params: SourceIssueParam[];
}

export interface PlannerSource {
    asOf: string;
    targetCurrency: string;
    generatedAt: string;
    provenance: SourceProvenance[];
    assets: SourceAsset[];
    brokers: SourceBroker[];
    holdings: SourceHolding[];
    cash: SourceCash[];
    prices: SourcePrice[];
    classifications: SourceClassification[];
    fxQuotes: SourceFxQuote[];
    currentDistribution: SourceCurrentDistribution | null;
    issues: SourceIssue[];
}

export type PlannerSourceErrorCode = 'broker_forbidden' | 'asset_not_found';

/** An explicit refusal of the domain API, shown to the user as such. */
export class PlannerSourceError extends Error {
    constructor(readonly code: PlannerSourceErrorCode) {
        super(code);
        this.name = 'PlannerSourceError';
    }
}

// The generated TS types widen nullable fields to `X | null | Array<X | null>`;
// the runtime Zod schema is `X | null`. These guards keep the runtime truth.
function text(value: unknown): string | null {
    return typeof value === 'string' ? value : null;
}

function integer(value: unknown): number | null {
    return typeof value === 'number' && Number.isInteger(value) ? value : null;
}

function refusal(error: unknown): PlannerSourceErrorCode | null {
    if (!isAxiosError<unknown>(error)) return null;
    const status = error.response?.status;
    const data = error.response?.data;
    const detail = data && typeof data === 'object' && 'detail' in data ? (data as {detail: unknown}).detail : null;
    const code = detail && typeof detail === 'object' && 'code' in detail ? (detail as {code: unknown}).code : null;
    if (status === 403 && code === 'portfolio_planner_source_broker_forbidden') return 'broker_forbidden';
    if (status === 404 && code === 'portfolio_planner_source_asset_not_found') return 'asset_not_found';
    return null;
}

type RawResponse = Awaited<ReturnType<typeof zodiosApi.get_portfolio_allocation_source_api_v1_portfolio_allocation_source_post>>;

function mapResponse(raw: RawResponse): PlannerSource {
    const distribution = raw.current_distribution;
    return {
        asOf: raw.snapshot.as_of,
        targetCurrency: raw.snapshot.target_currency,
        generatedAt: raw.snapshot.generated_at,
        provenance: raw.provenance.map((row) => ({
            provenance_id: row.provenance_id,
            domain: row.domain,
            source_ref: row.source_ref,
            source_label: text(row.source_label),
            captured_at: row.captured_at,
        })),
        assets: raw.assets.map((row) => ({
            asset_id: row.asset_id,
            source_asset_id: row.source_asset_id,
            name: row.name,
            ticker: text(row.ticker),
            asset_class: row.asset_class,
            icon_url: text(row.icon_url),
            active: row.active,
            provenance_id: row.provenance_id,
        })),
        brokers: raw.brokers.map((row) => ({
            broker_id: row.broker_id,
            source_broker_id: row.source_broker_id,
            name: row.name,
            icon_url: text(row.icon_url),
            access_role: row.access_role,
            ownership_share: row.ownership_share,
            observed_currencies: [...row.observed_currencies],
            active: row.active,
            execution_profile_status: row.execution_profile_status,
            provenance_id: row.provenance_id,
        })),
        holdings: raw.holdings.map((row) => ({
            holding_id: row.holding_id,
            asset_id: row.asset_id,
            broker_id: row.broker_id,
            provenance_id: row.provenance_id,
        })),
        cash: raw.cash_balances.map((row) => ({
            cash_id: row.cash_id,
            broker_id: row.broker_id,
            currency: row.currency,
            custody_amount: row.custody_amount,
            ownership_share: row.ownership_share,
            economic_amount: row.economic_amount,
            provenance_id: row.provenance_id,
        })),
        prices: raw.prices.map((row) => ({
            price_id: row.price_id,
            asset_id: row.asset_id,
            amount: text(row.amount),
            currency: text(row.currency),
            quote_base_quantity: text(row.quote_base_quantity),
            reference_date: text(row.reference_date),
            source: text(row.source),
            days_before_requested: integer(row.days_before_requested),
            provenance_id: row.provenance_id,
        })),
        classifications: raw.classifications.map((row) => ({
            classification_id: row.classification_id,
            asset_id: row.asset_id,
            dimension: row.dimension,
            category_id: text(row.category_id),
            label: text(row.label),
            weight: text(row.weight),
            provenance_id: row.provenance_id,
        })),
        fxQuotes: raw.fx_quotes.map((row) => ({
            fx_quote_id: row.fx_quote_id,
            pair: row.pair,
            rate: text(row.rate),
            reference_date: text(row.reference_date),
            source: text(row.source),
            days_before_requested: integer(row.days_before_requested),
            provenance_id: row.provenance_id,
        })),
        currentDistribution:
            distribution && !Array.isArray(distribution)
                ? {
                      status: distribution.status,
                      weight_quantum: distribution.weight_quantum,
                      as_of: distribution.as_of,
                      provenance_id: distribution.provenance_id,
                      rows: distribution.rows.map((row) => ({
                          weight_id: row.weight_id,
                          asset_id: row.asset_id,
                          held: row.held,
                          weight: text(row.weight),
                          valuation_source: row.valuation_source === 'MARKET_PRICE' || row.valuation_source === 'LAST_TRADE_PRICE' || row.valuation_source === 'MISSING' ? row.valuation_source : null,
                          valuation_reference_date: text(row.valuation_reference_date),
                          valuation_days_before_requested: integer(row.valuation_days_before_requested),
                          valuation_stale: row.valuation_stale,
                      })),
                  }
                : null,
        issues: raw.issues.map((issue) => ({
            code: issue.code,
            kind: issue.kind,
            severity: issue.severity,
            path: issue.path as SourceIssuePath,
            params: issue.params.map((param) => ({...param}) as SourceIssueParam),
        })),
    };
}

/** Reads one immutable domain snapshot. Every call is an explicit user action. */
export async function fetchPlannerSource(query: SourceQuery, accountGeneration: number, signal?: AbortSignal): Promise<PlannerSource> {
    try {
        return await runToolSessionTask(
            accountGeneration,
            async (requestSignal) => {
                const response = await zodiosApi.get_portfolio_allocation_source_api_v1_portfolio_allocation_source_post(
                    {
                        as_of: query.asOf,
                        target_currency: query.targetCurrency,
                        requested_sections: [...query.sections],
                        broker_ids: [...query.brokerIds],
                        asset_ids: query.assetIds === null ? null : [...query.assetIds],
                        fx_pairs: [...query.fxPairs],
                    },
                    {signal: requestSignal},
                );
                return mapResponse(response);
            },
            signal,
        );
    } catch (error) {
        const code = refusal(error);
        if (code) {
            assertToolAccount(accountGeneration);
            throw new PlannerSourceError(code);
        }
        throw safeToolTransportError(error, accountGeneration);
    }
}

export function isPlannerSourceError(error: unknown): error is PlannerSourceError {
    return error instanceof PlannerSourceError;
}

export function isStoppedWait(error: unknown): boolean {
    return error instanceof ToolClientError && error.code === 'waiting_stopped';
}

// ---------------------------------------------------------------------------
// Planner identifiers (N24/N25)
// ---------------------------------------------------------------------------

const PLANNER_ID = /^[A-Za-z0-9][A-Za-z0-9._:@/-]*$/;
const KEPT = /[A-Za-z0-9.:@/-]/;
const ENCODED_PREFIX = 'enc:';

/**
 * Injective mapping of a domain identifier into the planner identifier
 * alphabet. Valid identifiers pass unchanged; any other text (a sector such as
 * "Health Care", a source reference with `+`) becomes `enc:` plus its bytes,
 * with `_` as the escape. Returns `null` when the result exceeds `maxLength`.
 */
export function toPlannerId(raw: string, maxLength = 128): string | null {
    if (PLANNER_ID.test(raw) && !raw.startsWith(ENCODED_PREFIX) && raw.length <= maxLength) return raw;
    let encoded = ENCODED_PREFIX;
    for (const char of raw) {
        if (KEPT.test(char)) {
            encoded += char;
            continue;
        }
        for (const byte of new TextEncoder().encode(char)) encoded += '_' + byte.toString(16).padStart(2, '0');
    }
    return encoded.length <= maxLength ? encoded : null;
}

/**
 * The planner accepts UTC timestamps with `Z` only and compares them in time
 * order (N25). Every timestamp goes through one form — millisecond `Z` — so
 * `.123Z` and `.123456Z` can never be compared as text. `null` = unparseable.
 */
export function toPlannerTimestamp(value: string): string | null {
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
}

/** Canonical FX pair key (`AAA/BBB`, A < B), the form the planner and the source both use. */
export function canonicalPair(left: string, right: string): string {
    return left < right ? [left, right].join('/') : [right, left].join('/');
}
