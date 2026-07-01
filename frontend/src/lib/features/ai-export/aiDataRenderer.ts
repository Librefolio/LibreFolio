/**
 * AI Data Renderer — produces the Data Only export as Markdown + YAML.
 *
 * Same structured data as the full prompt but without AI instructions,
 * methodology explanations, or analysis requests.
 */

import type {AiPortfolioExport, AiTechnicalAsset} from './types';

export function renderDataOnly(data: AiPortfolioExport): string {
	const sections: string[] = [];

	sections.push('# LibreFolio Portfolio Data Export\n');

	sections.push('```yaml');
	sections.push(toYaml({metadata: data.metadata}));
	sections.push('```\n');

	sections.push('```yaml');
	sections.push(toYaml({portfolio_snapshot: data.portfolio_snapshot}));
	sections.push('```\n');

	sections.push('```yaml');
	sections.push(toYaml({current_allocation: data.current_allocation}));
	sections.push('```\n');

	if (data.positions.length > 0) {
		sections.push('```yaml');
		sections.push(toYaml({positions: data.positions}));
		sections.push('```\n');
	}

	if (data.broker_summary.length > 0) {
		sections.push('```yaml');
		sections.push(toYaml({broker_summary: data.broker_summary}));
		sections.push('```\n');
	}

	if (data.technical_context.length > 0) {
		for (const asset of data.technical_context) {
			sections.push(renderTechnicalAsset(asset));
		}
	}

	const allEvents = data.technical_context.flatMap((a) => a.events);
	if (allEvents.length > 0) {
		sections.push('```yaml');
		sections.push(toYaml({technical_events: allEvents}));
		sections.push('```\n');
	}

	if (data.technical_context_unavailable.length > 0) {
		sections.push('```yaml');
		sections.push(toYaml({technical_context_unavailable: data.technical_context_unavailable}));
		sections.push('```\n');
	}

	const hasQuality =
		data.data_quality.missing_price_assets.length > 0 || data.data_quality.stale_prices.length > 0 || data.data_quality.warnings.length > 0;
	if (hasQuality) {
		sections.push('```yaml');
		sections.push(toYaml({data_quality: data.data_quality}));
		sections.push('```\n');
	}

	return sections.join('\n');
}

// ─── Technical asset rendering ───────────────────────────────────────────────

function renderTechnicalAsset(asset: AiTechnicalAsset): string {
	const lines: string[] = [];
	const label = asset.metadata.symbol ?? asset.metadata.asset;

	lines.push(`### ${label}\n`);
	lines.push('```yaml');
	lines.push(toYaml(asset.metadata));
	lines.push('```\n');

	if (asset.series.length > 0) {
		const cols = ['Date', 'Close', 'Return %', 'RSI14', 'MACD Hist', 'EMA20', 'EMA50', 'EMA200'];
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

// ─── YAML serializer (shared with prompt renderer) ──────────────────────────

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
