/**
 * AI Export Builder — main orchestrator.
 *
 * Fetches portfolio report data (with contribution + breakdown), merges with
 * asset store and technical signals to produce the AiPortfolioExport model.
 */

import {zodiosApi} from '$lib/api';
import {getAssetInfo, ensureAssetsLoaded, getAllAssets} from '$lib/stores/reference/assetStore';
import {buildTechnicalContext, type TechnicalExportInput} from './technical/technicalExportBuilder';
import {getResponseLanguage} from './templates/languageMap';
import type {
	AiPortfolioExport,
	AiPortfolioSnapshot,
	AiPosition,
	AiAllocation,
	AiAllocationItem,
	AiBrokerSummary,
	AiDataQuality,
	AiMethodology,
	AiMetadata,
} from './types';

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
	const positions = buildPositions(summary, contribution, missingAssetIds);
	const allocation = buildAllocation(summary, positions);
	const brokerSummary = buildBrokerSummary(summary, positions);

	// Build technical context for eligible assets
	const technicalInputs = buildTechnicalInputs(positions, missingAssetIds, options);
	const technical = await buildTechnicalContext(technicalInputs);

	return {
		metadata: aiMetadata,
		methodology,
		portfolio_snapshot: snapshot,
		current_allocation: allocation,
		positions,
		broker_summary: brokerSummary,
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

function buildMethodology(): AiMethodology {
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
		allocation_basis: 'market_value_excluding_cash',
		metric_definitions: {
			nav: 'Total portfolio value: market_value + cash',
			total_pnl: 'NAV minus total invested capital (lifetime)',
			period_pnl: 'NAV change minus net cash flows in selected period',
			deposited_capital: 'Total deposits minus total withdrawals (net external capital)',
			unrealized_pnl: 'Current market value minus cost basis of open positions',
			twrr_percent: 'Time-Weighted Rate of Return (eliminates cash flow timing effect)',
			mwrr_annualized_percent: 'Money-Weighted Rate of Return (XIRR), annualized',
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
		deposited_capital: parseCurrency(summary.net_deposited_capital),
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

function buildPositions(
	summary: Record<string, any> | null,
	contribution: Record<string, any> | null,
	missingPriceAssetIds: Set<number>,
): AiPosition[] {
	const holdings: any[] = summary?.holdings ?? [];
	if (holdings.length === 0) return [];

	// Index contribution positions by (asset_id, broker_id) for merging
	const contribMap = new Map<string, any>();
	const contribPositions: any[] = contribution?.positions ?? [];
	for (const cp of contribPositions) {
		const key = `${cp.asset_id}|${cp.broker_id}`;
		contribMap.set(key, cp);
	}

	const positions: AiPosition[] = [];
	for (const h of holdings) {
		const assetInfo = getAssetInfo(h.asset_id);
		const currency = assetInfo?.currency ?? '';
		const contribKey = `${h.asset_id}|${h.broker_id}`;
		const cp = contribMap.get(contribKey);
		const qty = parseNum(h.quantity) ?? 0;

		// Skip closed positions that had no activity in the period
		if (qty === 0 && !cp) continue;

		const wac = parseNum(h.wac_per_unit);
		const costBasis = wac != null && qty > 0 ? Math.round(wac * qty * 100) / 100 : undefined;
		const isMissingPrice = missingPriceAssetIds.has(h.asset_id);

		positions.push(
			stripUndefined({
				broker: h.broker_name ?? `Broker #${h.broker_id}`,
				name: h.asset_name,
				symbol: h.asset_ticker ?? undefined,
				asset_type: h.asset_type,
				currency,
				quantity: qty,
				market_value: parseCurrency(h.current_value),
				nav_weight_percent: parseNum(h.nav_weight_percent),
				wac,
				cost_basis: costBasis,
				unrealized_pnl: parseCurrency(h.gain_loss),
				unrealized_pnl_percent: ratioToPct(h.gain_loss_percent),
				is_open: qty > 0 ? true : false,
				valuation_source: isMissingPrice ? 'LAST_BUY_PRICE_OR_MISSING' : undefined,
				// Period contribution
				period_pnl: parseNum(cp?.period_pnl),
				period_pnl_percent: ratioToPct(cp?.period_pnl_percent),
				period_unrealized_delta: parseNum(cp?.period_unrealized_delta),
				period_realized: parseNum(cp?.period_realized_gain_loss),
				period_income: parseNum(cp?.period_income),
				period_fees_taxes: parseNum(cp?.period_fees_taxes),
				is_fully_sold: cp?.is_fully_sold === true ? true : undefined,
			}) as AiPosition,
		);
	}

	// Sort by NAV weight descending
	positions.sort((a, b) => (b.nav_weight_percent ?? 0) - (a.nav_weight_percent ?? 0));

	return positions;
}

// ─── Allocation ──────────────────────────────────────────────────────────────

function buildAllocation(summary: Record<string, any> | null, positions: AiPosition[]): AiAllocation {
	const byType = ensureAllocSums100(mapAllocation(summary?.allocation_by_type));
	const bySector = ensureAllocSums100(mapAllocation(summary?.allocation_by_sector));
	const byGeo = ensureAllocSums100(mapAllocation(summary?.allocation_by_geography));

	// Compute by_currency from positions + assetStore
	const currencyWeights = new Map<string, number>();
	for (const p of positions) {
		if (p.currency && p.nav_weight_percent != null) {
			currencyWeights.set(p.currency, (currencyWeights.get(p.currency) ?? 0) + p.nav_weight_percent);
		}
	}
	const byCurrency: AiAllocationItem[] = Array.from(currencyWeights.entries())
		.map(([name, percent]) => ({name, percent: Math.round(percent * 100) / 100}))
		.sort((a, b) => b.percent - a.percent);

	// Compute by_broker from positions
	const brokerWeights = new Map<string, number>();
	for (const p of positions) {
		if (p.nav_weight_percent != null) {
			brokerWeights.set(p.broker, (brokerWeights.get(p.broker) ?? 0) + p.nav_weight_percent);
		}
	}
	const byBroker: AiAllocationItem[] = Array.from(brokerWeights.entries())
		.map(([name, percent]) => ({name, percent: Math.round(percent * 100) / 100}))
		.sort((a, b) => b.percent - a.percent);

	// by_asset from positions (only open)
	const byAsset: AiAllocationItem[] = positions
		.filter((p) => p.is_open && p.nav_weight_percent != null && p.nav_weight_percent > 0)
		.map((p) => ({name: p.symbol ?? p.name, percent: p.nav_weight_percent!}));

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

/** If allocation doesn't sum to ~100%, add an 'Other / Unallocated' entry */
function ensureAllocSums100(items: AiAllocationItem[]): AiAllocationItem[] {
	if (items.length === 0) return items;
	const total = items.reduce((s, i) => s + i.percent, 0);
	const gap = Math.round((100 - total) * 100) / 100;
	if (Math.abs(gap) > 0.5) {
		return [...items, {name: 'Other / Unallocated', percent: gap}];
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
			const mainType = exposure
				? Array.from(exposure.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'Mixed'
				: 'Unknown';

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
		const mainType = exposure
			? Array.from(exposure.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] ?? 'Mixed'
			: 'Unknown';
		return {broker: name, main_exposure: mainType};
	});
}

// ─── Data Quality ────────────────────────────────────────────────────────────

interface InternalDataQuality extends AiDataQuality {
	missing_price_assets_ids?: number[];
}

function buildDataQuality(
	dq: Record<string, any> | null,
	summary: Record<string, any> | null,
): InternalDataQuality {
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

function buildTechnicalInputs(
	positions: AiPosition[],
	missingAssetIds: Set<number>,
	options: AiExportOptions,
): TechnicalExportInput[] {
	// Deduplicate by asset_id (positions may have same asset across brokers)
	const seen = new Set<number>();
	const inputs: TechnicalExportInput[] = [];

	const allAssets = getAllAssets();

	for (const p of positions) {
		// Find asset_id from asset store
		const assetInfo = allAssets.find((a) => a.display_name === p.name);
		if (!assetInfo) continue;
		if (seen.has(assetInfo.id)) continue;
		if (missingAssetIds.has(assetInfo.id)) continue;
		seen.add(assetInfo.id);

		inputs.push({
			assetId: assetInfo.id,
			assetName: p.name,
			assetTicker: p.symbol,
			currency: p.currency,
			endDate: options.dateTo ?? new Date().toISOString().slice(0, 10),
			targetCurrency: options.targetCurrency,
		});
	}

	return inputs;
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
