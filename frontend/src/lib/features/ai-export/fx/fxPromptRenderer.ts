/**
 * FX-pair AI export renderer — two variants sharing the same underlying
 * AiFxExport data: "FX Snapshot" (data only) and "Explain Rate Trend"
 * (adds role/task + web-research request).
 */

import type {AiTechnicalAsset} from '../types';
import {PROMPT_TECHNICAL_DISCLAIMER, PROMPT_WEB_RESEARCH, buildResponseLanguageLine} from '../templates/promptTemplate';
import {PROMPT_CONCISE_RESPONSE} from '../templates/responseStyleTemplate';
import {fmt, toYaml} from '../yamlSerializer';
import type {AiFxExport} from './fxTypes';

const TREND_ROLE = `You are a neutral FX analysis assistant.
The user wants a neutral explanation of why this specific currency pair is currently moving in its present direction, combining the data below with your own research.`;

const TREND_TASK = `Please:

1. If you have web access, research this currency pair's current drivers: interest rate differentials, central bank / monetary policy signals, recent macro data, and any relevant geopolitical or risk-sentiment events. If you do not have web access, state it and rely only on the data below.
2. Cross-reference what you find with the metrics below: current spot snapshot in both directions and the technical posture in the canonical base→quote direction.
3. Explain neutrally WHY the rate appears to be moving in its current direction. This is not a trading recommendation or forecast.
4. If technical data is unavailable, or if your web/data access is insufficient to support a confident explanation, say so explicitly rather than guessing.
5. Separate observed facts from interpretation, and distinguish data-based observations from research-based context.`;

export function renderFxSnapshot(data: AiFxExport): string {
    const sections: string[] = [];

    sections.push('# LibreFolio FX AI Export — Snapshot\n');
    sections.push('```yaml');
    sections.push(toYaml({methodology: data.methodology}));
    sections.push('```\n');
    sections.push('```yaml');
    sections.push(toYaml({metadata: data.metadata}));
    sections.push('```\n');
    sections.push('```yaml');
    sections.push(toYaml({identity: data.identity}));
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

export function renderFxTrend(data: AiFxExport): string {
    const sections: string[] = [];

    sections.push('# LibreFolio FX AI Export — Explain Rate Trend\n');
    sections.push(TREND_ROLE + '\n');
    sections.push(PROMPT_CONCISE_RESPONSE + '\n');
    sections.push(PROMPT_WEB_RESEARCH + '\n');

    sections.push('## Methodology\n');
    sections.push('```yaml');
    sections.push(toYaml(data.methodology));
    sections.push('```\n');

    sections.push('## Export Metadata\n');
    sections.push('```yaml');
    sections.push(toYaml(data.metadata));
    sections.push('```\n');

    sections.push('## FX Identity\n');
    sections.push('```yaml');
    sections.push(toYaml(data.identity));
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

    if (data.data_quality.stale_rate) {
        sections.push('## Data Quality Notes\n');
        sections.push('```yaml');
        sections.push(toYaml(data.data_quality));
        sections.push('```\n');
    }

    sections.push('## Requested Analysis\n');
    sections.push(TREND_TASK + '\n');
    sections.push(buildResponseLanguageLine(data.metadata.response_language));

    return sections.join('\n');
}

function renderTechnicalAsset(asset: AiTechnicalAsset): string {
    const lines: string[] = [];

    lines.push('```yaml');
    lines.push(toYaml(asset.metadata));
    lines.push('```\n');

    if (asset.series.length > 0) {
        const cols = ['Date', 'Close', 'Return from 3M base %', 'MACD Hist', 'EMA20', 'EMA50', 'EMA200'];
        lines.push('| ' + cols.join(' | ') + ' |');
        lines.push('|' + cols.map(() => '---:').join('|') + '|');

        for (const p of asset.series) {
            const row = [p.date, fmt(p.close), fmt(p.return_from_base_pct), p.macd_hist != null ? fmt(p.macd_hist) : '—', p.ema20 != null ? fmt(p.ema20) : '—', p.ema50 != null ? fmt(p.ema50) : '—', p.ema200 != null ? fmt(p.ema200) : '—'];
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
