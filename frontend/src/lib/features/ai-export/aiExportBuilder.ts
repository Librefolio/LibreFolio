/**
 * AI Export Builder — main orchestrator.
 *
 * Fetches portfolio report data (with contribution + breakdown), merges with
 * asset store and technical signals to produce the AiPortfolioExport model.
 */

import {zodiosApi} from '$lib/api';
import {ensureAssetPriceRangeLoaded} from '$lib/stores/assetPriceStoreRegistry';
import {getAssetInfo, ensureAssetsLoaded} from '$lib/stores/reference/assetStore';
import {buildTechnicalContext, type TechnicalExportInput} from './technical/technicalExportBuilder';
import {getResponseLanguage} from './templates/languageMap';
import {compactGeography, compactSector} from './allocationCompaction';
import {buildAssetIdentifiers, disambiguateAssetName, findCollidingAssetIds} from './assetLabel';
import type {AiPortfolioExport, AiPortfolioSnapshot, AiPosition, AiAllocation, AiAllocationItem, AiBrokerSummary, AiDataQuality, AiMethodology, AiMetadata, AiPacContext, AiInvestorAssumptions, AiTechnicalSummaryItem} from './types';

/** Position enriched with the internal asset id — used only to reliably link
 *  technical data back to the right asset; never part of the exported YAML. */
interface InternalPosition extends AiPosition {
    _assetId: number;
}

/** Country/sector entries below this percent are grouped into a minor bucket. */
const ALLOCATION_COMPACTION_THRESHOLD = 1;

// ─── Options ─────────────────────────────────────────────────────────────────

export interface AiExportOptions {
    brokerIds?: number[];
    dateFrom?: string;
    dateTo?: string;
    targetCurrency: string;
    locale: string;
}

// ─── Main Builder ────────────────────────────────────────────────────────────

export async function buildAiExport(options: AiExportOptions): Promise<AiPortfolioExport> {
    // Ensure asset store is loaded for currency/type lookups
    await ensureAssetsLoaded();

    // Fetch full report with contribution + breakdown
    const report = await zodiosApi.get_portfolio_report_api_v1_portfolio_report_post({
        include_summary: true,
        include_history: false,
        include_allocation_history: false,
        include_positions_contribution: true,
        include_breakdown: true,
        ...(options.brokerIds && options.brokerIds.length > 0 ? {broker_ids: options.brokerIds} : {}),
        ...(options.dateFrom || options.dateTo
            ? {
                  date_range: {
                      ...(options.dateFrom ? {start: options.dateFrom} : {}),
                      ...(options.dateTo ? {end: options.dateTo} : {}),
                  },
              }
            : {}),
        target_currency: options.targetCurrency,
    });

    const summary = report.summary as Record<string, any> | null;
    const contribution = report.positions_contribution as Record<string, any> | null;
    const dataQuality = report.data_quality as Record<string, any> | null;
    const metadata = report.metadata as Record<string, any>;

    // Build sections
    const aiMetadata = buildMetadata(metadata, options);
    const methodology = buildMethodology();
    const snapshot = buildSnapshot(summary);
    const quality = buildDataQuality(dataQuality, summary);
    const missingAssetIds = new Set((quality.missing_price_assets_ids ?? []) as number[]);
    const internalPositions = buildPositions(summary, contribution);
    const allocation = buildAllocation(summary, internalPositions);
    const brokerSummary = buildBrokerSummary(summary, internalPositions);

    // Build technical context for eligible assets (uses the internal asset id
    // directly — never re-derives it by matching on the, possibly disambiguated, name)
    const technicalInputs = buildTechnicalInputs(internalPositions, missingAssetIds, options);
    const technical = await buildTechnicalContext(technicalInputs);

    // Build technical summary from computed assets
    const technicalSummary = buildTechnicalSummary(technical.assets, internalPositions);

    // Strip the internal-only asset id before exporting — it's a linking key, not export data.
    const positions: AiPosition[] = internalPositions.map(({_assetId, ...rest}) => rest);

    return {
        metadata: aiMetadata,
        methodology,
        portfolio_snapshot: snapshot,
        current_allocation: allocation,
        positions,
        broker_summary: brokerSummary,
        pac_context: buildPacContext(options),
        investor_assumptions: buildInvestorAssumptions(),
        technical_summary: technicalSummary,
        technical_context: technical.assets,
        technical_context_unavailable: technical.unavailable,
        data_quality: {
            missing_price_assets: quality.missing_price_assets,
            stale_prices: quality.stale_prices,
            warnings: quality.warnings,
        },
    };
}

// ─── Metadata ────────────────────────────────────────────────────────────────

function buildMetadata(meta: Record<string, any>, options: AiExportOptions): AiMetadata {
    return {
        generated_at: new Date().toISOString(),
        base_currency: options.targetCurrency,
        selected_range: {
            from: options.dateFrom ?? meta.computed_date_from ?? '',
            to: options.dateTo ?? meta.computed_date_to ?? '',
        },
        response_language: getResponseLanguage(options.locale),
        export_purpose: 'monthly PAC long-term allocation support',
    };
}

// ─── Methodology ─────────────────────────────────────────────────────────────

export function buildMethodology(): AiMethodology {
    return {
        portfolio_style: 'long_term_monthly_accumulation',
        valuation_policy: {
            primary: 'market_price',
            fallback: 'last_visible_buy_price',
            missing_policy: 'flag_or_omit',
        },
        wac_policy: {
            used_for: ['cost_basis', 'unrealized_pnl', 'realized_pnl'],
            not_used_as_price: true,
        },
        technical_indicators_policy: {
            purpose: 'descriptive_context_only',
            not_trading_signals: true,
        },
        technical_context_policy: {
            technical_window: '3M',
            technical_window_is_independent_from_selected_portfolio_range: true,
            technical_indicators_are_context_only: true,
        },
        allocation_basis: 'nav_including_cash',
        allocation_basis_exceptions: {
            by_geography: 'invested_market_value_excluding_cash_rescaled_to_100 — backend does not classify cash geographically, so country/continent percentages are rescaled to sum to ~100% of invested market value only (excluding cash), not of NAV like the other allocation sections',
        },
        allocation_compaction_policy: {
            geography: {
                country_threshold_percent: ALLOCATION_COMPACTION_THRESHOLD,
                below_threshold_grouping: 'continent',
                keep_unknown_separate: true,
                includes_liquidity: false,
            },
            sector: {
                sector_threshold_percent: ALLOCATION_COMPACTION_THRESHOLD,
                below_threshold_grouping: 'minor_sectors',
                keep_unknown_separate: true,
                includes_liquidity: true,
            },
        },
        metric_definitions: {
            nav: 'Total portfolio value: market_value + cash',
            total_invested: 'Lifetime net external capital: sum(deposits) - sum(withdrawals)',
            total_pnl: 'NAV minus total_invested (lifetime gain/loss)',
            period_pnl: 'NAV change minus net external flows within selected period',
            period_nav_start: 'NAV at the start of the selected period',
            period_net_deposits: 'Deposits minus withdrawals within selected period only',
            unrealized_pnl: 'Current market value minus cost basis of open positions',
            twrr_percent: 'Time-Weighted Return (eliminates cash flow timing effect)',
            mwrr_annualized_percent: 'Money-Weighted Return (XIRR), annualized',
            simple_roi_percent: 'Simple ROI for the selected period, computed as period_pnl divided by the capital base for the period (approximately period_nav_start + period_net_deposits); treat as an approximation, not an exact reproducible formula from the other exported fields.',
            position_period_pnl_percent: 'Position-level period gain/loss percentage (field: period_pnl_percent on each position), computed as period_pnl / |start_value| for the selected period; it is not the same as the technical price return_3m_percent shown in Technical Summary/Series.',
        },
    };
}

// ─── Portfolio Snapshot ──────────────────────────────────────────────────────

function buildSnapshot(summary: Record<string, any> | null): AiPortfolioSnapshot {
    if (!summary) return {};

    return stripUndefined({
        nav: parseCurrency(summary.net_worth),
        market_value: parseCurrency(summary.market_value),
        cash: parseCurrency(summary.cash_total),
        book_value: parseCurrency(summary.book_value),
        total_invested: parseCurrency(summary.total_invested),
        period_nav_start: parseCurrency(summary.period_nav_start),
        period_net_deposits: parseCurrency(summary.net_deposited_capital),
        total_pnl: parseCurrency(summary.total_gain_loss),
        total_pnl_percent: ratioToPct(summary.total_gain_loss_percent),
        unrealized_pnl: parseCurrency(summary.unrealized_gain_loss),
        period_pnl: parseCurrency(summary.period_pnl),
        twrr_percent: ratioToPct(summary.twrr_percent),
        mwrr_annualized_percent: ratioToPct(summary.mwrr_annualized_percent),
        simple_roi_percent: ratioToPct(summary.simple_roi_percent),
    }) as AiPortfolioSnapshot;
}

// ─── Positions ───────────────────────────────────────────────────────────────

function buildPositions(summary: Record<string, any> | null, contribution: Record<string, any> | null): InternalPosition[] {
    const holdings: any[] = summary?.holdings ?? [];
    if (holdings.length === 0) return [];

    // Index contribution positions by (asset_id, broker_id) for merging
    const contribMap = new Map<string, any>();
    const contribPositions: any[] = contribution?.positions ?? [];
    for (const cp of contribPositions) {
        const key = `${cp.asset_id}|${cp.broker_id}`;
        contribMap.set(key, cp);
    }

    // Two *different* assets sharing the exact same display name are rare but
    // must never collapse into one ambiguous label — see disambiguateAssetName().
    const collidingAssetIds = findCollidingAssetIds(holdings.map((h) => ({asset_id: h.asset_id, asset_name: h.asset_name})));

    const positions: InternalPosition[] = [];
    for (const h of holdings) {
        const assetInfo = getAssetInfo(h.asset_id);
        const currency = assetInfo?.currency ?? '';
        const contribKey = `${h.asset_id}|${h.broker_id}`;
        const cp = contribMap.get(contribKey);
        const qty = parseNum(h.quantity) ?? 0;

        // Skip closed positions entirely — not relevant for PAC advice
        if (qty <= 0.0001) continue;

        const wac = parseNum(h.wac_per_unit);
        const costBasis = wac != null && qty > 0 ? Math.round(wac * qty * 100) / 100 : undefined;
        const name = collidingAssetIds.has(h.asset_id) ? disambiguateAssetName(h.asset_name, {assetType: h.asset_type, currency, broker: h.broker_name}) : h.asset_name;

        positions.push(
            stripUndefined({
                _assetId: h.asset_id,
                broker: h.broker_name ?? `Broker #${h.broker_id}`,
                name,
                identifiers: buildAssetIdentifiers(assetInfo),
                asset_type: h.asset_type,
                currency,
                quantity: qty,
                market_value: parseCurrency(h.current_value),
                nav_weight_percent: parseNum(h.nav_weight_percent),
                wac,
                cost_basis: costBasis,
                unrealized_pnl: parseCurrency(h.gain_loss),
                unrealized_pnl_percent: ratioToPct(h.gain_loss_percent),
                // Period contribution
                period_pnl: parseNum(cp?.period_pnl),
                period_pnl_percent: ratioToPct(cp?.period_pnl_percent),
                period_unrealized_delta: parseNum(cp?.period_unrealized_delta),
                period_realized: parseNum(cp?.period_realized_gain_loss),
                period_income: parseNum(cp?.period_income),
                period_fees_taxes: parseNum(cp?.period_fees_taxes),
                is_fully_sold: cp?.is_fully_sold === true ? true : undefined,
            }) as InternalPosition,
        );
    }

    // Sort by NAV weight descending
    positions.sort((a, b) => (b.nav_weight_percent ?? 0) - (a.nav_weight_percent ?? 0));

    return positions;
}

// ─── Allocation ──────────────────────────────────────────────────────────────

function buildAllocation(summary: Record<string, any> | null, positions: AiPosition[]): AiAllocation {
    const byType = ensureAllocSums100(mapAllocation(summary?.allocation_by_type));
    const bySectorRaw = mapAllocation(summary?.allocation_by_sector);
    const bySector = ensureAllocSums100(compactSector(bySectorRaw, ALLOCATION_COMPACTION_THRESHOLD));

    const navValue = parseCurrency(summary?.net_worth) ?? 0;
    const cashTotal = parseCurrency(summary?.cash_total) ?? 0;
    const cashPercentOfNav = navValue > 0 ? Math.round((cashTotal / navValue) * 10000) / 100 : 0;

    // Geography: backend excludes cash from this dimension (unlike type/sector, which
    // include a "Liquidity" bucket). Kept on its own market_value_excluding_cash basis —
    // no rescale, no Liquidity line added, so country percentages stay as reported.
    const byGeoRaw = mapAllocation(summary?.allocation_by_geography);
    const byGeo = ensureAllocSums100(compactGeography(byGeoRaw, ALLOCATION_COMPACTION_THRESHOLD));

    // Compute by_currency from positions, then add cash by currency (nav_including_cash basis)
    const currencyWeights = new Map<string, number>();
    for (const p of positions) {
        if (p.currency && p.nav_weight_percent != null) {
            currencyWeights.set(p.currency, (currencyWeights.get(p.currency) ?? 0) + p.nav_weight_percent);
        }
    }
    const cashBalances: any[] = summary?.cash_balances ?? [];
    for (const cb of cashBalances) {
        const amount = parseCurrency(cb);
        if (amount == null || navValue <= 0) continue;
        const pct = Math.round((amount / navValue) * 10000) / 100;
        if (pct <= 0) continue;
        currencyWeights.set(cb.code, (currencyWeights.get(cb.code) ?? 0) + pct);
    }
    const byCurrency: AiAllocationItem[] = Array.from(currencyWeights.entries())
        .map(([name, percent]) => ({name, percent: Math.round(percent * 100) / 100}))
        .sort((a, b) => b.percent - a.percent);

    // Compute by_broker from positions, then add cash per broker (nav_including_cash basis)
    const brokerWeights = new Map<string, number>();
    for (const p of positions) {
        if (p.nav_weight_percent != null) {
            brokerWeights.set(p.broker, (brokerWeights.get(p.broker) ?? 0) + p.nav_weight_percent);
        }
    }
    const byBrokerRaw: any[] = summary?.by_broker ?? [];
    for (const b of byBrokerRaw) {
        const cash = parseCurrency(b.cash_total);
        if (cash == null || navValue <= 0) continue;
        const pct = Math.round((cash / navValue) * 10000) / 100;
        if (pct <= 0) continue;
        brokerWeights.set(b.broker_name, (brokerWeights.get(b.broker_name) ?? 0) + pct);
    }
    const byBroker: AiAllocationItem[] = Array.from(brokerWeights.entries())
        .map(([name, percent]) => ({name, percent: Math.round(percent * 100) / 100}))
        .sort((a, b) => b.percent - a.percent);

    // by_asset from positions, plus a single Cash / Liquidity entry (nav_including_cash basis)
    const byAsset: AiAllocationItem[] = positions.filter((p) => p.nav_weight_percent != null && p.nav_weight_percent > 0).map((p) => ({name: p.name, percent: p.nav_weight_percent!}));
    if (cashPercentOfNav > 0) {
        byAsset.push({name: 'Cash / Liquidity', percent: cashPercentOfNav});
    }
    byAsset.sort((a, b) => b.percent - a.percent);

    return {
        by_asset: byAsset,
        by_asset_type: byType,
        by_sector: bySector,
        by_geography: byGeo,
        by_currency: byCurrency,
        by_broker: byBroker,
    };
}

function mapAllocation(items: any[] | undefined): AiAllocationItem[] {
    if (!items || !Array.isArray(items)) return [];
    return items
        .filter((i) => i.name && i.value != null)
        .map((i) => ({name: i.name, percent: Math.round(parseFloat(i.value) * 100) / 100}))
        .sort((a, b) => b.percent - a.percent);
}

/**
 * If allocation doesn't sum to ~100%, add an 'Other / Unallocated' entry.
 * Never emits a negative-percent bucket — if the section already exceeds 100%
 * beyond tolerance (e.g. rounding or double-counting upstream), the excess is
 * logged as a warning and silently omitted rather than exported as confusing
 * negative data.
 */
function ensureAllocSums100(items: AiAllocationItem[]): AiAllocationItem[] {
    if (items.length === 0) return items;
    const total = items.reduce((s, i) => s + i.percent, 0);
    const gap = Math.round((100 - total) * 100) / 100;
    const TOLERANCE = 0.5;

    if (gap > TOLERANCE) {
        return [...items, {name: 'Other / Unallocated', percent: gap}];
    }
    if (gap < -TOLERANCE) {
        console.warn(`[ai-export] allocation section exceeds 100% by ${Math.abs(gap)}pp — omitting negative residual bucket`);
    }
    return items;
}

// ─── Broker Summary ─────────────────────────────────────────────────────────

function buildBrokerSummary(summary: Record<string, any> | null, positions: AiPosition[]): AiBrokerSummary[] {
    const byBroker: any[] = summary?.by_broker ?? [];

    // Derive main exposure per broker from positions
    const brokerExposure = new Map<string, Map<string, number>>();
    for (const p of positions) {
        if (!brokerExposure.has(p.broker)) brokerExposure.set(p.broker, new Map());
        const typeMap = brokerExposure.get(p.broker)!;
        typeMap.set(p.asset_type, (typeMap.get(p.asset_type) ?? 0) + (p.nav_weight_percent ?? 0));
    }

    if (byBroker.length > 0) {
        return byBroker.map((b) => {
            const navWeight = parseCurrency(b.net_worth);
            const totalNav = parseCurrency(summary?.net_worth) ?? 1;
            const exposure = brokerExposure.get(b.broker_name);
            const mainType = exposure ? (Array.from(exposure.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'Mixed') : 'Unknown';

            return stripUndefined({
                broker: b.broker_name,
                nav_weight_percent: navWeight != null && totalNav > 0 ? Math.round((navWeight / totalNav) * 10000) / 100 : undefined,
                cash: parseCurrency(b.cash_total),
                main_exposure: mainType,
            }) as AiBrokerSummary;
        });
    }

    // Fallback: derive from positions
    const brokerNames = [...new Set(positions.map((p) => p.broker))];
    return brokerNames.map((name) => {
        const exposure = brokerExposure.get(name);
        const mainType = exposure ? (Array.from(exposure.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'Mixed') : 'Unknown';
        return {broker: name, main_exposure: mainType};
    });
}

// ─── Data Quality ────────────────────────────────────────────────────────────

interface InternalDataQuality extends AiDataQuality {
    missing_price_assets_ids?: number[];
}

function buildDataQuality(dq: Record<string, any> | null, summary: Record<string, any> | null): InternalDataQuality {
    const missingPrices: string[] = [];
    const missingIds: number[] = [];
    const stale: string[] = [];
    const warnings: string[] = [];

    // From data_quality
    if (dq) {
        for (const mp of dq.missing_price_assets ?? []) {
            missingPrices.push(`${mp.name ?? mp.symbol ?? 'Asset #' + mp.asset_id} (${mp.broker_name})`);
            missingIds.push(mp.asset_id);
        }
        for (const sp of dq.stale_prices ?? []) {
            stale.push(`${sp.name ?? sp.symbol ?? 'Asset #' + sp.asset_id}: price is ${sp.stale_days ?? '?'} days old`);
        }
        for (const w of dq.warnings ?? []) {
            warnings.push(typeof w === 'string' ? w : JSON.stringify(w));
        }
        for (const issue of dq.issues ?? []) {
            if (typeof issue === 'object' && issue.message) {
                warnings.push(issue.message);
            }
        }
    }

    // From summary
    if (summary) {
        for (const mp of summary.missing_price_assets ?? []) {
            if (!missingIds.includes(mp.asset_id)) {
                missingPrices.push(`${mp.name ?? mp.symbol ?? 'Asset #' + mp.asset_id} (${mp.broker_name})`);
                missingIds.push(mp.asset_id);
            }
        }
    }

    return {
        missing_price_assets: missingPrices,
        missing_price_assets_ids: missingIds,
        stale_prices: stale,
        warnings,
    };
}

// ─── Technical inputs ────────────────────────────────────────────────────────

function buildTechnicalInputs(positions: InternalPosition[], missingAssetIds: Set<number>, options: AiExportOptions): TechnicalExportInput[] {
    // Deduplicate by asset_id (positions may have same asset across brokers).
    // Uses the internal asset id directly — no more fragile matching by name,
    // which would silently drop/mismatch technical data for disambiguated names.
    const seen = new Set<number>();
    const inputs: TechnicalExportInput[] = [];

    for (const p of positions) {
        if (seen.has(p._assetId)) continue;
        if (missingAssetIds.has(p._assetId)) continue;
        seen.add(p._assetId);

        inputs.push({
            assetName: p.name,
            identifiers: p.identifiers,
            loadPrices: (loadStart, endDate) =>
                ensureAssetPriceRangeLoaded(p._assetId, p.currency, loadStart, endDate, {
                    targetCurrency: options.targetCurrency,
                }).then((prices) => prices.map((price) => ({date: price.date, value: price.close, backwardFillInfo: price.backwardFillInfo}))),
            endDate: options.dateTo ?? new Date().toISOString().slice(0, 10),
        });
    }

    return inputs;
}

// ─── PAC Context ─────────────────────────────────────────────────────────────

function buildPacContext(options: AiExportOptions): AiPacContext {
    return {
        monthly_pac_amount: 'unavailable',
        monthly_pac_currency: options.targetCurrency,
        preferred_action: 'allocate_new_capital',
        avoid_sale_suggestions: true,
        allow_new_assets: 'unknown',
    };
}

// ─── Investor Assumptions ────────────────────────────────────────────────────

function buildInvestorAssumptions(): AiInvestorAssumptions {
    return {
        risk_tolerance: 'unavailable',
        investment_horizon: 'unavailable',
        target_allocation: 'unavailable',
    };
}

// ─── Technical Summary ───────────────────────────────────────────────────────

function buildTechnicalSummary(assets: import('./types').AiTechnicalAsset[], positions: AiPosition[]): AiTechnicalSummaryItem[] {
    // Build NAV weight lookup by asset name (already unique — see disambiguateAssetName)
    const weightMap = new Map<string, number>();
    for (const p of positions) {
        weightMap.set(p.name, (weightMap.get(p.name) ?? 0) + (p.nav_weight_percent ?? 0));
    }

    return assets
        .map((a) => {
            const lastPoint = a.series.length > 0 ? a.series[a.series.length - 1] : null;
            const label = a.metadata.asset;
            const lastClose = lastPoint?.close ?? 0;

            return stripUndefined({
                asset: a.metadata.asset,
                identifiers: a.metadata.identifiers,
                nav_weight_percent: weightMap.get(label),
                return_3m_percent: lastPoint?.return_from_base_pct ?? 0,
                latest_rsi14: lastPoint?.rsi14,
                latest_macd_histogram: lastPoint?.macd_hist,
                price_vs_ema20_percent: lastPoint?.ema20 && lastClose > 0 ? Math.round(((lastClose - lastPoint.ema20) / lastPoint.ema20) * 10000) / 100 : undefined,
                price_vs_ema50_percent: lastPoint?.ema50 && lastClose > 0 ? Math.round(((lastClose - lastPoint.ema50) / lastPoint.ema50) * 10000) / 100 : undefined,
                price_vs_ema200_percent: lastPoint?.ema200 && lastClose > 0 ? Math.round(((lastClose - lastPoint.ema200) / lastPoint.ema200) * 10000) / 100 : undefined,
            }) as AiTechnicalSummaryItem;
        })
        .sort((a, b) => (b.nav_weight_percent ?? 0) - (a.nav_weight_percent ?? 0));
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Parse a Currency object {code, amount} to number, or a SafeDecimal string */
function parseCurrency(val: any): number | undefined {
    if (val == null) return undefined;
    if (typeof val === 'number') return val;
    if (typeof val === 'string') {
        const n = parseFloat(val);
        return Number.isNaN(n) ? undefined : n;
    }
    if (typeof val === 'object' && val.amount != null) {
        const n = parseFloat(val.amount);
        return Number.isNaN(n) ? undefined : n;
    }
    return undefined;
}

function parseNum(val: any): number | undefined {
    if (val == null) return undefined;
    if (typeof val === 'number') return val;
    const n = parseFloat(String(val));
    return Number.isNaN(n) ? undefined : n;
}

/** Convert backend ratio (0.17) to human-readable percentage points (17.0) */
function ratioToPct(val: any): number | undefined {
    const n = parseNum(val);
    if (n == null) return undefined;
    return Math.round(n * 10000) / 100;
}

/** Remove undefined values from an object */
function stripUndefined<T extends Record<string, any>>(obj: T): T {
    const result = {} as T;
    for (const [k, v] of Object.entries(obj)) {
        if (v !== undefined) (result as any)[k] = v;
    }
    return result;
}
