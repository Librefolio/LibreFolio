/**
 * Single-asset AI export renderer — two variants sharing the same underlying
 * AiAssetExport data: "Asset Snapshot" (data only, mirrors the portfolio-level
 * Snapshot) and "Classify Asset Status" (adds role/task + web-research request).
 */

import type {AiAssetExport} from './assetTypes';
import type {AiTechnicalAsset} from '../types';
import {toYaml, fmt} from '../yamlSerializer';
import {PROMPT_TECHNICAL_DISCLAIMER, PROMPT_WEB_RESEARCH, buildResponseLanguageLine} from '../templates/promptTemplate';
import {PROMPT_CONCISE_RESPONSE, PROMPT_ASSET_NAMING} from '../templates/responseStyleTemplate';

const CLASSIFY_ROLE = `You are a neutral asset analysis assistant.
The user wants a neutral classification of this single asset's current status, combining the data below with your own research.`;

const CLASSIFY_TASK = `Please:

1. If you have web access, research this asset: recent news, fundamentals, sector/peer context, and any notable recent developments. If you do not have web access, state it and rely only on the data below.
2. Cross-reference what you find with the metrics below: price trend and technical posture ("technical"), and — if held — portfolio weight and contribution ("holding").
3. Present a neutral classification of the asset's current status (e.g. strengths, risks, and points to monitor) — not a buy/sell recommendation.
4. If technical or holding data is unavailable, say so explicitly rather than guessing.
5. Ask clarifying questions if the user's goal for this asset (e.g. core holding vs. speculative, planning to add to or reduce it) would change your assessment.`;

export function renderAssetSnapshot(data: AiAssetExport): string {
    const sections: string[] = [];

    sections.push('# LibreFolio Asset AI Export — Snapshot\n');
    sections.push('```yaml');
    sections.push(toYaml({methodology: data.methodology}));
    sections.push('```\n');
    sections.push('```yaml');
    sections.push(toYaml({metadata: data.metadata}));
    sections.push('```\n');
    sections.push('```yaml');
    sections.push(toYaml({identity: data.identity}));
    sections.push('```\n');
    sections.push('```yaml');
    sections.push(toYaml({holding: data.holding}));
    sections.push('```\n');

    if (data.technical) {
        sections.push(renderTechnicalAsset(data.technical));
    } else if (data.technical_unavailable_reason) {
        sections.push('```yaml');
        sections.push(toYaml({technical_unavailable_reason: data.technical_unavailable_reason}));
        sections.push('```\n');
    }

    sections.push('```yaml');
    sections.push(toYaml({data_quality: data.data_quality}));
    sections.push('```\n');

    return sections.join('\n');
}

export function renderAssetClassify(data: AiAssetExport): string {
    const sections: string[] = [];

    sections.push('# LibreFolio Asset AI Export — Classify Asset Status\n');
    sections.push(CLASSIFY_ROLE + '\n');
    sections.push(PROMPT_CONCISE_RESPONSE + '\n');
    sections.push(PROMPT_ASSET_NAMING + '\n');
    sections.push(PROMPT_WEB_RESEARCH + '\n');

    sections.push('## Methodology\n');
    sections.push('```yaml');
    sections.push(toYaml(data.methodology));
    sections.push('```\n');

    sections.push('## Export Metadata\n');
    sections.push('```yaml');
    sections.push(toYaml(data.metadata));
    sections.push('```\n');

    sections.push('## Asset Identity\n');
    sections.push('```yaml');
    sections.push(toYaml(data.identity));
    sections.push('```\n');

    sections.push('## Portfolio Holding\n');
    sections.push('```yaml');
    sections.push(toYaml({holding: data.holding}));
    sections.push('```\n');

    if (data.technical) {
        sections.push('## Technical Context\n');
        sections.push(PROMPT_TECHNICAL_DISCLAIMER + '\n');
        sections.push(renderTechnicalAsset(data.technical));
    } else if (data.technical_unavailable_reason) {
        sections.push('## Technical Context Unavailable\n');
        sections.push('```yaml');
        sections.push(toYaml({reason: data.technical_unavailable_reason}));
        sections.push('```\n');
    }

    if (data.data_quality.missing_price || data.data_quality.stale_price) {
        sections.push('## Data Quality Notes\n');
        sections.push('```yaml');
        sections.push(toYaml(data.data_quality));
        sections.push('```\n');
    }

    sections.push('## Requested Analysis\n');
    sections.push(CLASSIFY_TASK + '\n');
    sections.push(buildResponseLanguageLine(data.metadata.response_language));

    return sections.join('\n');
}

// ─── Technical asset rendering (metadata + series table + events) ──────────

function renderTechnicalAsset(asset: AiTechnicalAsset): string {
    const lines: string[] = [];

    lines.push('```yaml');
    lines.push(toYaml(asset.metadata));
    lines.push('```\n');

    if (asset.series.length > 0) {
        const cols = ['Date', 'Close', 'Return from 3M base %', 'RSI14', 'MACD Hist', 'EMA20', 'EMA50', 'EMA200'];
        lines.push('| ' + cols.join(' | ') + ' |');
        lines.push('|' + cols.map(() => '---:').join('|') + '|');

        for (const p of asset.series) {
            const row = [p.date, fmt(p.close), fmt(p.return_from_base_pct), p.rsi14 != null ? fmt(p.rsi14) : '—', p.macd_hist != null ? fmt(p.macd_hist) : '—', p.ema20 != null ? fmt(p.ema20) : '—', p.ema50 != null ? fmt(p.ema50) : '—', p.ema200 != null ? fmt(p.ema200) : '—'];
            lines.push('| ' + row.join(' | ') + ' |');
        }
        lines.push('');
    }

    if (asset.events.length > 0) {
        lines.push('```yaml');
        lines.push(toYaml({technical_events: asset.events}));
        lines.push('```\n');
    }

    return lines.join('\n');
}
