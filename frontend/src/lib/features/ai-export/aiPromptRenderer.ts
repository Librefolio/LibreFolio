/**
 * AI Prompt Renderer — produces the Full AI Prompt as Markdown + YAML.
 */

import type {AiPortfolioExport, AiTechnicalAsset} from './types';
import {
	PROMPT_ROLE,
	PROMPT_WEB_RESEARCH,
	PROMPT_TECHNICAL_DISCLAIMER,
	PROMPT_INVESTOR_ASSUMPTIONS_NOTE,
	PROMPT_ANALYSIS_REQUEST,
	buildResponseLanguageLine,
} from './templates/promptTemplate';

export function renderFullPrompt(data: AiPortfolioExport): string {
	const sections: string[] = [];

	sections.push('# LibreFolio Portfolio AI Export\n');
	sections.push(PROMPT_ROLE + '\n');
	sections.push(PROMPT_WEB_RESEARCH + '\n');

	// Methodology
	sections.push('## Methodology\n');
	sections.push('```yaml');
	sections.push(toYaml(data.methodology));
	sections.push('```\n');

	// Export Metadata (right after Methodology)
	sections.push('## Export Metadata\n');
	sections.push('```yaml');
	sections.push(toYaml(data.metadata));
	sections.push('```\n');

	// Portfolio Snapshot
	sections.push('## Portfolio Snapshot\n');
	sections.push('```yaml');
	sections.push(toYaml(data.portfolio_snapshot));
	sections.push('```\n');

	// Allocation
	sections.push('## Current Allocation\n');
	sections.push('```yaml');
	sections.push(toYaml(data.current_allocation));
	sections.push('```\n');

	// Positions
	if (data.positions.length > 0) {
		sections.push('## Positions\n');
		sections.push('```yaml');
		sections.push(toYaml({positions: data.positions}));
		sections.push('```\n');
	}

	// Broker Summary
	if (data.broker_summary.length > 0) {
		sections.push('## Broker Summary\n');
		sections.push('```yaml');
		sections.push(toYaml({broker_summary: data.broker_summary}));
		sections.push('```\n');
	}

	// PAC Context
	sections.push('## PAC Context\n');
	sections.push('```yaml');
	sections.push(toYaml({pac_context: data.pac_context}));
	sections.push('```\n');

	// Investor Assumptions
	sections.push('## Investor Assumptions\n');
	sections.push(PROMPT_INVESTOR_ASSUMPTIONS_NOTE + '\n');
	sections.push('```yaml');
	sections.push(toYaml({investor_assumptions: data.investor_assumptions}));
	sections.push('```\n');

	// Technical Summary (compact overview before full tables)
	if (data.technical_summary.length > 0) {
		sections.push('## Technical Summary\n');
		sections.push('```yaml');
		sections.push(toYaml({technical_summary: data.technical_summary}));
		sections.push('```\n');
	}

	// Technical Context
	if (data.technical_context.length > 0) {
		sections.push('## Technical Series Detail\n');
		sections.push(PROMPT_TECHNICAL_DISCLAIMER + '\n');

		for (const asset of data.technical_context) {
			sections.push(renderTechnicalAsset(asset));
		}
	}

	// Technical events (all assets merged)
	const allEvents = data.technical_context.flatMap((a) => a.events);
	if (allEvents.length > 0) {
		sections.push('## Technical Events\n');
		sections.push('```yaml');
		sections.push(toYaml({technical_events: allEvents}));
		sections.push('```\n');
	}

	// Unavailable assets
	if (data.technical_context_unavailable.length > 0) {
		sections.push('## Technical Context Unavailable\n');
		sections.push('```yaml');
		sections.push(toYaml({technical_context_unavailable: data.technical_context_unavailable}));
		sections.push('```\n');
	}

	// Data Quality
	const hasQualityIssues =
		data.data_quality.missing_price_assets.length > 0 || data.data_quality.stale_prices.length > 0 || data.data_quality.warnings.length > 0;
	if (hasQualityIssues) {
		sections.push('## Data Quality Notes\n');
		sections.push('```yaml');
		sections.push(toYaml(data.data_quality));
		sections.push('```\n');
	}

	// Analysis Request
	sections.push('## Requested Analysis\n');
	sections.push(PROMPT_ANALYSIS_REQUEST + '\n');
	sections.push(buildResponseLanguageLine(data.metadata.response_language));

	return sections.join('\n');
}

// ─── Technical asset rendering ───────────────────────────────────────────────

function renderTechnicalAsset(asset: AiTechnicalAsset): string {
	const lines: string[] = [];
	const label = asset.metadata.symbol ?? asset.metadata.asset;

	lines.push(`### Technical Series — ${label}\n`);
	lines.push('```yaml');
	lines.push(toYaml(asset.metadata));
	lines.push('```\n');

	if (asset.series.length > 0) {
		// Markdown table
		const cols = ['Date', 'Close', 'Return from 3M base %', 'RSI14', 'MACD Hist', 'EMA20', 'EMA50', 'EMA200'];
		lines.push('| ' + cols.join(' | ') + ' |');
		lines.push('|' + cols.map(() => '---:').join('|') + '|');

		for (const p of asset.series) {
			const row = [
				p.date,
				fmt(p.close),
				fmt(p.return_from_base_pct),
				p.rsi14 != null ? fmt(p.rsi14) : '—',
				p.macd_hist != null ? fmt(p.macd_hist) : '—',
				p.ema20 != null ? fmt(p.ema20) : '—',
				p.ema50 != null ? fmt(p.ema50) : '—',
				p.ema200 != null ? fmt(p.ema200) : '—',
			];
			lines.push('| ' + row.join(' | ') + ' |');
		}
		lines.push('');
	}

	return lines.join('\n');
}

// ─── YAML serializer (minimal, no dependency) ───────────────────────────────

function toYaml(obj: unknown, indent = 0): string {
	const pad = '  '.repeat(indent);

	if (obj === null || obj === undefined) return `${pad}null`;
	if (typeof obj === 'boolean') return `${pad}${obj}`;
	if (typeof obj === 'number') return `${pad}${fmt(obj)}`;
	if (typeof obj === 'string') {
		if (obj.includes('\n') || obj.includes(':') || obj.includes('#') || obj.startsWith('"')) {
			return `${pad}"${obj.replace(/"/g, '\\"')}"`;
		}
		return `${pad}${obj}`;
	}

	if (Array.isArray(obj)) {
		if (obj.length === 0) return `${pad}[]`;
		// Primitive arrays inline
		if (obj.every((v) => typeof v === 'string' || typeof v === 'number')) {
			return `${pad}[${obj.map((v) => (typeof v === 'string' ? `"${v}"` : fmt(v as number))).join(', ')}]`;
		}
		return obj.map((item) => `${pad}- ${toYaml(item, indent + 1).trimStart()}`).join('\n');
	}

	if (typeof obj === 'object') {
		const entries = Object.entries(obj).filter(([, v]) => v !== undefined && v !== null);
		if (entries.length === 0) return `${pad}{}`;
		return entries
			.map(([k, v]) => {
				const valStr = toYaml(v, indent + 1);
				if (typeof v === 'object' && !Array.isArray(v)) {
					return `${pad}${k}:\n${valStr}`;
				}
				if (Array.isArray(v) && v.length > 0 && typeof v[0] === 'object') {
					return `${pad}${k}:\n${valStr}`;
				}
				return `${pad}${k}: ${valStr.trimStart()}`;
			})
			.join('\n');
	}

	return `${pad}${String(obj)}`;
}

function fmt(n: number): string {
	return Number.isInteger(n) ? String(n) : n.toFixed(2);
}
