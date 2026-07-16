/**
 * Portfolio-level AI export prompt catalog — one entry per analysis "activity"
 * instead of a single all-in-one prompt. Drives both the dropdown UI (dashboard,
 * broker detail) and the renderer (which sections to include, how much
 * technical detail, and which instructions to append).
 *
 * Order matters: it's the display order in the UI, from most reusable/general
 * (Portfolio Snapshot) to most specific, with "Describe Portfolio" deliberately
 * last — it's the most likely to just restate what the dashboard already shows.
 */

export type PromptId = 'snapshot' | 'pac_planning' | 'rebalancing' | 'market_trend' | 'income_review' | 'describe_portfolio';

export interface PromptSections {
    /** current_allocation block */
    allocation: boolean;
    broker_summary: boolean;
    /** pac_context block — excluded whenever its fixed "avoid_sale_suggestions: true" framing would contradict the prompt's own instructions (e.g. rebalancing, which may suggest selling) */
    pac_context: boolean;
    /** 'full' = technical_context (complete sampled series + events), 'summary' = technical_summary only (compact, one line per asset) */
    technicalDetail: 'full' | 'summary';
}

export interface PromptDefinition {
    id: PromptId;
    labelKey: string;
    descriptionKey: string;
    /** false only for 'snapshot' — pure data, no role/task text, no web-research/analysis instructions */
    hasInstructions: boolean;
    sections: PromptSections;
}

export const PORTFOLIO_PROMPT_CATALOG: PromptDefinition[] = [
    {
        id: 'snapshot',
        labelKey: 'dashboard.aiExportMenu.snapshot.label',
        descriptionKey: 'dashboard.aiExportMenu.snapshot.description',
        hasInstructions: false,
        sections: {allocation: true, broker_summary: true, pac_context: true, technicalDetail: 'full'},
    },
    {
        id: 'pac_planning',
        labelKey: 'dashboard.aiExportMenu.pac_planning.label',
        descriptionKey: 'dashboard.aiExportMenu.pac_planning.description',
        hasInstructions: true,
        sections: {allocation: true, broker_summary: false, pac_context: true, technicalDetail: 'summary'},
    },
    {
        id: 'rebalancing',
        labelKey: 'dashboard.aiExportMenu.rebalancing.label',
        descriptionKey: 'dashboard.aiExportMenu.rebalancing.description',
        hasInstructions: true,
        sections: {allocation: true, broker_summary: true, pac_context: false, technicalDetail: 'summary'},
    },
    {
        id: 'market_trend',
        labelKey: 'dashboard.aiExportMenu.market_trend.label',
        descriptionKey: 'dashboard.aiExportMenu.market_trend.description',
        hasInstructions: true,
        sections: {allocation: false, broker_summary: false, pac_context: false, technicalDetail: 'full'},
    },
    {
        id: 'income_review',
        labelKey: 'dashboard.aiExportMenu.income_review.label',
        descriptionKey: 'dashboard.aiExportMenu.income_review.description',
        hasInstructions: true,
        sections: {allocation: true, broker_summary: false, pac_context: false, technicalDetail: 'summary'},
    },
    {
        id: 'describe_portfolio',
        labelKey: 'dashboard.aiExportMenu.describe_portfolio.label',
        descriptionKey: 'dashboard.aiExportMenu.describe_portfolio.description',
        hasInstructions: true,
        sections: {allocation: true, broker_summary: true, pac_context: true, technicalDetail: 'summary'},
    },
];

export function getPromptDefinition(id: PromptId): PromptDefinition {
    const def = PORTFOLIO_PROMPT_CATALOG.find((p) => p.id === id);
    if (!def) throw new Error(`Unknown AI export prompt id: ${id}`);
    return def;
}
