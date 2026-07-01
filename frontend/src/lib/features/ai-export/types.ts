/**
 * AI Portfolio Export — Type definitions.
 *
 * Internal model for the AI export feature. Built from portfolio report data +
 * frontend-computed technical signals. Rendered to Markdown+YAML for clipboard.
 */

// ─── Root ────────────────────────────────────────────────────────────────────

export interface AiPortfolioExport {
	metadata: AiMetadata;
	methodology: AiMethodology;
	portfolio_snapshot: AiPortfolioSnapshot;
	current_allocation: AiAllocation;
	positions: AiPosition[];
	broker_summary: AiBrokerSummary[];
	technical_context: AiTechnicalAsset[];
	technical_context_unavailable: AiTechnicalUnavailable[];
	data_quality: AiDataQuality;
}

// ─── Metadata ────────────────────────────────────────────────────────────────

export interface AiMetadata {
	generated_at: string;
	base_currency: string;
	selected_range: {from: string; to: string};
	response_language: string;
	export_purpose: string;
}

// ─── Methodology ─────────────────────────────────────────────────────────────

export interface AiMethodology {
	portfolio_style: string;
	valuation_policy: {
		primary: string;
		fallback: string;
		missing_policy: string;
	};
	wac_policy: {
		used_for: string[];
		not_used_as_price: boolean;
	};
	technical_indicators_policy: {
		purpose: string;
		not_trading_signals: boolean;
	};
	allocation_basis: string;
	metric_definitions: Record<string, string>;
}

// ─── Portfolio Snapshot ──────────────────────────────────────────────────────

export interface AiPortfolioSnapshot {
	nav?: number;
	market_value?: number;
	cash?: number;
	book_value?: number;
	deposited_capital?: number;
	total_pnl?: number;
	total_pnl_percent?: number;
	unrealized_pnl?: number;
	period_pnl?: number;
	twrr_percent?: number;
	mwrr_annualized_percent?: number;
	simple_roi_percent?: number;
}

// ─── Positions ───────────────────────────────────────────────────────────────

export interface AiPosition {
	broker: string;
	name: string;
	symbol?: string;
	asset_type: string;
	currency: string;
	quantity: number;
	market_value?: number;
	nav_weight_percent?: number;
	wac?: number;
	cost_basis?: number;
	unrealized_pnl?: number;
	unrealized_pnl_percent?: number;
	is_open: boolean;
	/** Only set for assets flagged as missing in data_quality */
	valuation_source?: string;
	/** Period contribution fields (from positions_contribution) */
	period_pnl?: number;
	period_pnl_percent?: number;
	period_unrealized_delta?: number;
	period_realized?: number;
	period_income?: number;
	period_fees_taxes?: number;
	is_fully_sold?: boolean;
}

// ─── Allocation ──────────────────────────────────────────────────────────────

export interface AiAllocationItem {
	name: string;
	percent: number;
}

export interface AiAllocation {
	by_asset: AiAllocationItem[];
	by_asset_type: AiAllocationItem[];
	by_sector: AiAllocationItem[];
	by_geography: AiAllocationItem[];
	by_currency: AiAllocationItem[];
	by_broker: AiAllocationItem[];
}

// ─── Broker Summary ─────────────────────────────────────────────────────────

export interface AiBrokerSummary {
	broker: string;
	nav_weight_percent?: number;
	cash?: number;
	main_exposure: string;
}

// ─── Technical Context ───────────────────────────────────────────────────────

export interface AiTechnicalMetadata {
	asset: string;
	symbol?: string;
	technical_window: string;
	technical_window_start: string;
	normalized_return_base_date: string;
	normalized_return_base_price: number;
	technical_window_complete: boolean;
	normalized_return_base_reason?: string;
	comparability_note?: string;
}

export interface AiTechnicalSeriesPoint {
	date: string;
	close: number;
	return_from_base_pct: number;
	rsi14?: number;
	macd_hist?: number;
	ema20?: number;
	ema50?: number;
	ema200?: number;
}

export interface AiTechnicalEvent {
	asset: string;
	date: string;
	event: string;
	details?: Record<string, number | string>;
}

export interface AiTechnicalAsset {
	metadata: AiTechnicalMetadata;
	series: AiTechnicalSeriesPoint[];
	events: AiTechnicalEvent[];
}

export interface AiTechnicalUnavailable {
	asset: string;
	reason: string;
}

// ─── Data Quality ────────────────────────────────────────────────────────────

export interface AiDataQuality {
	missing_price_assets: string[];
	stale_prices: string[];
	warnings: string[];
}
