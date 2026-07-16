/**
 * AI Prompt Renderer — composes any instruction-bearing catalog prompt as
 * Markdown + YAML, using the per-prompt PromptDefinition (which sections to
 * include) and PromptTemplateContent (role/task text). "Portfolio Snapshot"
 * has no instructions at all and is rendered by aiDataRenderer.ts instead.
 */

import type {AiPortfolioExport, AiTechnicalAsset} from './types';
import {PROMPT_WEB_RESEARCH, PROMPT_TECHNICAL_DISCLAIMER, PROMPT_INVESTOR_ASSUMPTIONS_NOTE, buildResponseLanguageLine} from './templates/promptTemplate';
import {PROMPT_CONCISE_RESPONSE, PROMPT_ASSET_NAMING} from './templates/responseStyleTemplate';
import {PROMPT_TEMPLATES} from './templates/promptTemplates';
import {getPromptDefinition, type PromptId} from './promptCatalog';
import {toYaml, fmt} from './yamlSerializer';

/** Prompts whose task text already embeds its own web-research instructions — the generic note would be redundant */
const EMBEDS_OWN_WEB_RESEARCH: PromptId[] = ['pac_planning', 'market_trend'];

export function renderPrompt(data: AiPortfolioExport, promptId: Exclude<PromptId, 'snapshot'>): string {
    const def = getPromptDefinition(promptId);
    const template = PROMPT_TEMPLATES[promptId];
    const sections: string[] = [];

    sections.push(`# LibreFolio Portfolio AI Export — ${template.title}\n`);
    sections.push(template.role + '\n');
    sections.push(PROMPT_CONCISE_RESPONSE + '\n');
    sections.push(PROMPT_ASSET_NAMING + '\n');
    if (!EMBEDS_OWN_WEB_RESEARCH.includes(promptId)) {
        sections.push(PROMPT_WEB_RESEARCH + '\n');
    }

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

    // Allocation — skipped for prompts that don't need it (e.g. market trend)
    if (def.sections.allocation) {
        sections.push('## Current Allocation\n');
        sections.push('```yaml');
        sections.push(toYaml(data.current_allocation));
        sections.push('```\n');
    }

    // Positions
    if (data.positions.length > 0) {
        sections.push('## Positions\n');
        sections.push('```yaml');
        sections.push(toYaml({positions: data.positions}));
        sections.push('```\n');
    }

    // Broker Summary
    if (def.sections.broker_summary && data.broker_summary.length > 0) {
        sections.push('## Broker Summary\n');
        sections.push('```yaml');
        sections.push(toYaml({broker_summary: data.broker_summary}));
        sections.push('```\n');
    }

    // PAC Context — skipped whenever its fixed "avoid_sale_suggestions: true" framing
    // would contradict this prompt's own instructions (e.g. rebalancing may suggest selling)
    if (def.sections.pac_context) {
        sections.push('## PAC Context\n');
        sections.push('```yaml');
        sections.push(toYaml({pac_context: data.pac_context}));
        sections.push('```\n');
    }

    // Investor Assumptions
    sections.push('## Investor Assumptions\n');
    sections.push(PROMPT_INVESTOR_ASSUMPTIONS_NOTE + '\n');
    sections.push('```yaml');
    sections.push(toYaml({investor_assumptions: data.investor_assumptions}));
    sections.push('```\n');

    // Technical Summary (compact overview — always shown when present)
    if (data.technical_summary.length > 0) {
        sections.push('## Technical Summary\n');
        sections.push('```yaml');
        sections.push(toYaml({technical_summary: data.technical_summary}));
        sections.push('```\n');
    }

    // Technical Context — full per-day series/events only for prompts that need
    // that granularity (e.g. market trend); others rely on Technical Summary alone.
    if (def.sections.technicalDetail === 'full') {
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
    }

    // Unavailable assets
    if (data.technical_context_unavailable.length > 0) {
        sections.push('## Technical Context Unavailable\n');
        sections.push('```yaml');
        sections.push(toYaml({technical_context_unavailable: data.technical_context_unavailable}));
        sections.push('```\n');
    }

    // Data Quality
    const hasQualityIssues = data.data_quality.missing_price_assets.length > 0 || data.data_quality.stale_prices.length > 0 || data.data_quality.warnings.length > 0;
    if (hasQualityIssues) {
        sections.push('## Data Quality Notes\n');
        sections.push('```yaml');
        sections.push(toYaml(data.data_quality));
        sections.push('```\n');
    }

    // Analysis Request (prompt-specific task text)
    sections.push('## Requested Analysis\n');
    sections.push(template.task + '\n');
    sections.push(buildResponseLanguageLine(data.metadata.response_language));

    return sections.join('\n');
}

// ─── Technical asset rendering ───────────────────────────────────────────────

function renderTechnicalAsset(asset: AiTechnicalAsset): string {
    const lines: string[] = [];
    const label = asset.metadata.asset;

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
            const row = [p.date, fmt(p.close), fmt(p.return_from_base_pct), p.rsi14 != null ? fmt(p.rsi14) : '—', p.macd_hist != null ? fmt(p.macd_hist) : '—', p.ema20 != null ? fmt(p.ema20) : '—', p.ema50 != null ? fmt(p.ema50) : '—', p.ema200 != null ? fmt(p.ema200) : '—'];
            lines.push('| ' + row.join(' | ') + ' |');
        }
        lines.push('');
    }

    return lines.join('\n');
}
