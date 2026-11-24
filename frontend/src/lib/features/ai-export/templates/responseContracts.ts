import type {AiExportAnalysisId} from '../catalog/shared';

export interface AiExportResponseContractSection {
    readonly title: string;
    readonly requirements: readonly string[];
}

interface AiExportResponseContractIdentity {
    readonly id: string;
    readonly version: 1;
    readonly analysisId: AiExportAnalysisId;
}

/** Today's shape: the sections the answer must follow, in order. */
export interface AiExportSectionsResponseContract extends AiExportResponseContractIdentity {
    readonly shape: 'sections';
    readonly sections: readonly AiExportResponseContractSection[];
}

/**
 * The new shape (plan 78, L1): no sections any more. The contract keeps its identity (the backend handshake protects it)
 * and carries the analysis's usual follow-up questions, which «How to Answer» offers at the end of the first reply.
 */
export interface AiExportFollowUpsResponseContract extends AiExportResponseContractIdentity {
    readonly shape: 'follow_ups';
    readonly followUps: string;
}

export type AiExportResponseContractTemplate = AiExportSectionsResponseContract | AiExportFollowUpsResponseContract;

function section(title: string, ...requirements: readonly string[]): AiExportResponseContractSection {
    return {title, requirements};
}

function contract(analysisId: AiExportAnalysisId, sections: readonly AiExportResponseContractSection[]): AiExportSectionsResponseContract {
    return {id: `${analysisId}.response`, version: 1, analysisId, shape: 'sections', sections};
}

function followUps(analysisId: AiExportAnalysisId, line: string): AiExportFollowUpsResponseContract {
    return {id: `${analysisId}.response`, version: 1, analysisId, shape: 'follow_ups', followUps: line};
}

/** The market-driver analyses' usual follow-ups: version 7 of `78_aiExportPrompts/bozze-AIX.md`, copied as written. */
const PERFORMANCE_MARKET_DRIVER_FOLLOW_UPS =
    "Usual follow-ups for this analysis: the secondary causes with their evidence; the earlier episodes of the same move; what remains unexplained, holding by holding; the detail of one holding; the sources one by one with their quality; how the period's result splits into realised and unrealised, income and new money.";

/** Protection Strategies' usual follow-ups (78 L8a): version 6 of `78_aiExportPrompts/bozze-AIX.md`, copied as written. */
const PROTECTION_STRATEGIES_FOLLOW_UPS =
    "Usual follow-ups for this analysis: the risk measures holding by holding; the hedging instruments the user's brokers offer, with the capital each needs and its costs; what a hedge of a given size would cost and avoid here; what funding a hedge by selling holdings really amounts to; the tax side of each option under the user's regime; the signals to watch so as to decide earlier next time; the detail of one holding.";

const facts = section('Key Facts', 'Cite only the supplied facts your conclusions rely on, briefly, with their units, currencies, signs, dates, periods, scope, coverage, and data-quality limits where they matter. Do not restate or summarize the rest of the Snapshot Data.');
const evidence = section('Evidence and Interpretation', 'Connect conclusions to supplied evidence. Separate observation, calculation, interpretation, assumption, and uncertainty; never invent missing evidence.');
const limits = section('Assumptions, Limits, and Questions', 'List material data gaps, assumptions, unresolved user inputs, and interpretation limits. Ask only questions that could change the result.');
const scenarioThesis = section(
    'Scenario Thesis',
    'This section is mandatory for this task. Give every material scenario an explicit conditional thesis with horizon, supplied evidence, assumptions, expected mechanism, trade-offs, trigger conditions, invalidation conditions, and missing user decisions.',
    'Keep theses conditional. Do not present a forecast, promise, recommendation, legal conclusion, or automatic action.',
);
const externalContext = section(
    'External Context',
    'When external research is used, keep it separate from LibreFolio facts and provide publisher, title, URL, publication date, access date, source type, and source-quality assessment.',
    'If web access is unavailable, state that clearly and never fabricate a citation, date, URL, or current event.',
);
const drawdownContext = section(
    'Drawdown Context',
    'Use only supplied current and maximum peak-relative drawdown, episode dates, recovery status, recovered or remaining-to-peak percentages, duration, calculation basis, coverage, and data-quality status.',
    'Never infer a missing Risk metric from Drawdown. Drawdown is historical and not by itself a forecast, buy/sell signal, volatility measure, Sharpe ratio, VaR, or broader Risk metric.',
);

const fiscalSections = [
    section(
        'User Tax-Loss Inventory',
        'Before proposing any strategy, ask for country of tax residence or jurisdiction when absent, tax regime, account or wrapper type, and the official tax-loss inventory or equivalent statement, such as the Italian "cassetto fiscale".',
        'For each legal category or bucket, request original amount, remaining usable amount, amount already used or reserved, recognition or origin date, expiry date, eligible gain categories, offset order and limits, source document, and document date.',
        'Ask whether balances span multiple brokers or accounts and whether they can legally be pooled or transferred. Mark these answers indispensable; treat execution preferences as optional refinements.',
    ),
    section(
        'Economic FIFO Candidate Map',
        'Present supplied acquisition and closure chronology, open and partial lots, residual quantity and cost, current value, realized and unrealized economic gain or loss, income, recorded fees and taxes, age, currency, valuation source, shorts or transfers, and coverage.',
        'Group candidate lots by economic gain or loss and relevant date, but never label a lot legally offsettable until the user-supplied jurisdiction and tax rules support that conclusion.',
    ),
    section(
        'Legal Offset Eligibility Boundary',
        'Separate LibreFolio economic FIFO evidence from legal basis rules, eligible gain/loss categories, matching elections, wash-sale or anti-avoidance rules, exemptions, withholding, reporting, and timing.',
        'Identify every eligibility question that remains unresolved. Do not state a definitive tax liability, deductible loss, optimized sale, or legal compliance conclusion.',
    ),
    section(
        'Expiry and Decision Timeline',
        'Order user-supplied tax-loss buckets by expiry and show which dates create genuine decision windows.',
        'Estimate gains needed for an offset only when amount, legal category, eligibility, and remaining usable balance are supplied. Otherwise present formulas and conditional examples without inventing values.',
    ),
    scenarioThesis,
    section(
        'Conditional Offset Strategies',
        'Compare taking no tax-driven action, realizing legally eligible gains before expiry, staged realization aligned with rebalancing, and loss harvesting only when relevant to the stated objective and applicable rules.',
        'For each path show economic amount, expiry window, fees, market exposure changed or preserved, concentration, liquidity, replacement risk, holding-period constraints, wash-sale or anti-abuse uncertainty, and user decisions.',
        'Never recommend a transaction solely for tax reasons and never issue an automatic trade instruction.',
    ),
] as const;

export const AI_EXPORT_RESPONSE_CONTRACTS: Readonly<Record<AiExportAnalysisId, AiExportResponseContractTemplate>> = {
    'portfolio.pac_planning': contract('portfolio.pac_planning', [
        facts,
        section(
            'Decision Inputs Still Needed',
            'Ask only for missing inputs that materially distinguish plausible PAC scenarios: immediate and recurring capital, cadence, liquidity reserve, objective, horizon, targets or tolerances, risk and drawdown tolerance, exclusions, usable brokers, tradable minimums, whether sales are allowed, and tax or cost constraints.',
            'Separate indispensable answers from optional refinements. Never ask for facts already supplied or infer user preferences from portfolio measurements.',
        ),
        section(
            'PAC Timing Gate',
            'Compare immediate and staged deployment.',
            'Include conditional waiting only when supplied evidence shows a broad, persistent decline across the portfolio, not isolated Asset weakness or a single indicator. State the evidence, horizon, trigger, and invalidation conditions.',
            'Ask which timing preference the user wants before choosing a concrete path: immediate, staged, or—only when the gate is met—conditional waiting.',
        ),
        scenarioThesis,
        section('PAC Scenarios', 'Present two or three conditional recurring-contribution scenarios when feasible, including allocation logic, cadence, liquidity protection, concentration effects, operational feasibility, and trade-offs.'),
        drawdownContext,
        evidence,
        limits,
    ]),
    'portfolio.rebalancing': contract('portfolio.rebalancing', [
        facts,
        section('Targets and Measured Gaps', 'Quantify drift only against user-supplied targets, tolerance bands, exclusions, or priorities. Identify missing targets rather than inventing them.'),
        section('Uniform Asset Comparison', 'Compare supplied Assets on consistent allocation, performance, trend, momentum, volatility, drawdown, event, and coverage fields. Do not turn one indicator into a standalone trade signal.'),
        section('Economic Lots, Costs, and Tax Boundary', 'Keep measured economic FIFO and recorded costs separate from execution assumptions and jurisdiction-specific legal tax treatment.'),
        scenarioThesis,
        section('Rebalancing Pathways', 'Compare cash-flow-only, one-time trade, and mixed pathways. State expected allocation effect, turnover, concentration, liquidity, economic lot implications, assumptions, and user decisions without issuing orders.'),
        drawdownContext,
        evidence,
        limits,
    ]),
    'portfolio.performance_market_drivers': followUps('portfolio.performance_market_drivers', PERFORMANCE_MARKET_DRIVER_FOLLOW_UPS),
    'portfolio.fiscal_lots': contract('portfolio.fiscal_lots', [facts, ...fiscalSections, limits]),
    'portfolio.protection_strategies': followUps('portfolio.protection_strategies', PROTECTION_STRATEGIES_FOLLOW_UPS),
    'broker.review': contract('broker.review', [
        facts,
        section('Holdings, Cash, and Concentration', 'Describe only the selected broker scope. Separate position, asset type, sector, geography, currency, and cash dimensions and disclose coverage gaps.'),
        section('Performance, Flows, Income, and Costs', 'Keep performance methodologies, external flows, income, fees, taxes, ratios, and reconciliation distinct.'),
        section('Economic FIFO and Market Context', 'Present FIFO as economic evidence and compact per-Asset market context as secondary historical evidence. Do not infer full histories or legal tax treatment.'),
        evidence,
        drawdownContext,
        limits,
    ]),
    'broker.performance_market_drivers': followUps('broker.performance_market_drivers', PERFORMANCE_MARKET_DRIVER_FOLLOW_UPS),
    'broker.fiscal_lots': contract('broker.fiscal_lots', [facts, ...fiscalSections, limits]),
    'asset.position_review': contract('asset.position_review', [
        facts,
        section(
            'Cost, Value, and P&L',
            'Keep quantity, broker distribution, valuation source, current value, cost basis, realized and unrealized P&L, income, combined period fees/taxes, cumulative lot-allocated fees and taxes, and performance distinct.',
            'Respect supplied zero semantics. Do not interpret excluded Broker-level unallocated costs as zero or as allocated to this Asset.',
        ),
        section('Economic Lots and Legal Boundary', 'Use supplied lots only as economic FIFO evidence. Distinguish lot-allocated costs from Broker-level unallocated costs. Do not infer jurisdiction-specific legal tax treatment or a definitive taxable result.'),
        section('Portfolio Role and Concentration', 'Use the supplied portfolio-role weight basis and broker scope; do not recompute another denominator or infer missing look-through exposure.'),
        section('Focused Market Context', 'Use supplied trend, momentum, volatility, drawdown, limited history, and recent events without reconstructing a complete Asset Market Analysis.'),
        drawdownContext,
        section('Conditional Position Considerations', 'If alternatives are compared, apply the shared Scenario Thesis rule and keep goals, horizon, liquidity, risk tolerance, tax treatment, and execution constraints explicit.'),
        limits,
    ]),
    'asset.market_analysis': contract('asset.market_analysis', [
        facts,
        section('Price, Return, and Coverage', 'State current observation, requested and available periods, OHLC or return evidence, extrema and dates, coverage, source, staleness, and data-quality status.'),
        section('Trend, Momentum, Volatility, and Drawdown', 'Separate short-, medium-, and long-horizon evidence and preserve dated states, transitions, extrema, and drawdown semantics.'),
        section('Technical and Market Events', 'List material dated transitions and distinguish observed events from interpretation. Technical evidence is historical, not predictive.'),
        externalContext,
        evidence,
        limits,
    ]),
    'fx.pair_analysis': contract('fx.pair_analysis', [
        facts,
        section('Rate Direction and Coverage', 'Use quote currency per one unit of base currency. State current rate, source, conversion provenance, requested and available periods, extrema dates, returns, volatility, coverage, and staleness.'),
        section('Trend, Momentum, Volatility, and Events', 'Separate short-, medium-, and long-horizon evidence and preserve quote-per-base direction. Never invert the pair silently.'),
        externalContext,
        evidence,
        limits,
    ]),
    'fx.exposure_impact': contract('fx.exposure_impact', [
        facts,
        section('Direct Exposure Links', 'Separate cash, trading-currency, and valuation-currency links and preserve supplied valuation and conversion provenance.'),
        section('Conditional Directional Impact', 'Describe how base appreciation or depreciation could affect the supplied direct links. Keep rate, return, volatility, trend, event, and coverage evidence distinct from scenario assumptions.'),
        section('No Look-Through Inference', 'Do not infer issuer revenue, supply-chain, domicile, hedging, or other economic exposure that the snapshot does not contain.'),
        section('Exposure Scenarios', 'If multiple future FX paths are compared, apply the shared Scenario Thesis rule and state horizon, triggers, invalidation conditions, concentration, and missing links.'),
        externalContext,
        limits,
    ]),
};

export function findAiExportResponseContract(analysisId: AiExportAnalysisId): AiExportResponseContractTemplate {
    return AI_EXPORT_RESPONSE_CONTRACTS[analysisId];
}
