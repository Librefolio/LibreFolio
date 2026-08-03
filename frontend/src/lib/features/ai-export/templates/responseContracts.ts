import type {AiExportAnalysisId} from '../catalog/shared';

export interface AiExportResponseContractSection {
    readonly title: string;
    readonly requirements: readonly string[];
}

export interface AiExportResponseContractTemplate {
    readonly id: string;
    readonly version: 2;
    readonly analysisId: AiExportAnalysisId;
    readonly sections: readonly AiExportResponseContractSection[];
}

function section(title: string, ...requirements: readonly string[]): AiExportResponseContractSection {
    return {title, requirements};
}

function contract(analysisId: AiExportAnalysisId, sections: readonly AiExportResponseContractSection[]): AiExportResponseContractTemplate {
    return {id: `${analysisId}.response`, version: 2, analysisId, sections};
}

const facts = section('LibreFolio Facts', 'State the relevant supplied facts, units, currencies, signs, periods, and scope.');
const evidence = section('Evidence and Interpretation', 'Connect conclusions to supplied data and dated technical buckets without inventing missing evidence.');
const external = section('External Context', 'When web access was used, cite source and dates and keep external facts separate from LibreFolio facts.');
const limits = section('Assumptions, Limits, and Questions', 'List data gaps, assumptions, unresolved user inputs, and interpretation limits.');
const drawdownContext = section(
    'Drawdown Context',
    'Only when a drawdown context section is supplied, use its deterministic current and maximum peak-relative drawdown ratios, episode peak/trough/recovery dates, recovery status, recovered/remaining-to-peak percentages, duration, calculation basis, data-quality status, and coverage exactly as given.',
    'Never infer volatility, Sharpe, VaR, or any broader Risk metric it does not contain, and treat an unavailable or failed drawdown status as simply missing rather than approximating it.',
    'Drawdown is historical, not predictive, and is never by itself a buy/sell signal.',
);

export const AI_EXPORT_RESPONSE_CONTRACTS: Readonly<Record<AiExportAnalysisId, AiExportResponseContractTemplate>> = {
    'portfolio.pac_planning': contract('portfolio.pac_planning', [
        facts,
        section(
            'Decision Inputs Still Needed',
            'Use Snapshot Data and User Notes first. Ask only about missing inputs that materially distinguish plausible PAC scenarios; never ask for facts already supplied and never invent an answer.',
            'Group only the questions actually needed under capital and cadence, goals and horizon, risk preferences, and operational constraints. Mark each asked question as indispensable or optional refinement; if no indispensable question remains, do not manufacture a questionnaire.',
            'Capital and cadence — REQUIRED WHEN MISSING: new capital available immediately; periodically investable amount; expected monthly, quarterly, or occasional frequency; minimum liquidity or emergency reserve not to use; priority between investing and rebuilding liquidity.',
            'Capital and cadence — OPTIONAL WHEN MATERIAL: additional capital usable only under favourable conditions.',
            'Goals and horizon — REQUIRED WHEN MISSING: investment horizon; PAC objective (maintain current allocation, approach targets, reduce concentration, or increase specified exposures).',
            'Goals and horizon — OPTIONAL WHEN MATERIAL: intermediate deadlines; target allocation and tolerance ranges; limits by asset, asset type, sector, geography, currency, or declared risk level.',
            'Risk preferences — REQUIRED WHEN MISSING: user tolerance for volatility and temporary loss/maximum acceptable Drawdown; need to preserve capital; preference for stability, growth, income, or balance.',
            'Risk preferences — OPTIONAL WHEN MATERIAL: maximum high-risk percentage; assets or categories the user does not want to increase. These are user preferences, not metrics deducible from the portfolio.',
            'Operational constraints — REQUIRED WHEN MISSING AND MATERIAL: whether sales are allowed or the PAC must use only new purchases; usable brokers; minimum tradable amount or whole-share constraint when they change feasibility.',
            'Operational constraints — OPTIONAL WHEN MATERIAL: minimum commissions; distribution across multiple brokers; excluded assets; user-declared tax or liquidity constraints.',
        ),
        drawdownContext,
        section(
            'Asset Drawdown Comparison',
            'When supplied, compare only the compact observed-price fields current drawdown, maximum drawdown, maximum-episode recovery status, and remaining-to-peak percentage.',
            'Use observation count, available dates, coverage, and data-quality status to qualify sparse or partial Asset series. Do not request or reconstruct Asset Drawdown history.',
            'Use Asset Drawdown together with allocation, concentration, objectives, horizon, user tolerance, trend, and volatility; never treat being below a peak as a standalone reason to buy.',
        ),
        section('Subordinate Market Context', 'Use only the supplied small per-asset trend, momentum, volatility, recent-event, and Drawdown context; keep user objectives and constraints primary.'),
        section('PAC Scenarios', 'Present two or three conditional recurring-contribution scenarios with rationale and trade-offs when possible.', 'State which indispensable unanswered inputs prevent a concrete allocation and which optional answers would only refine it.'),
        evidence,
        external,
        limits,
    ]),
    'portfolio.rebalancing': contract('portfolio.rebalancing', [
        facts,
        section('Measured Allocation Gaps', 'Quantify only against supplied targets or tolerances.'),
        section('Uniform Asset Comparison', 'Compare every supplied asset on the same financial, trend, momentum, volatility, and coverage fields without inventing missing Risk metrics.'),
        section('Rebalancing Pathways', 'Compare cash-flow-only, one-time, and mixed pathways without transaction commands.'),
        drawdownContext,
        external,
        limits,
    ]),
    'portfolio.performance_attribution': contract('portfolio.performance_attribution', [
        facts,
        section('Positive and Negative Contributors', 'Keep the complete supplied universe and residual effects visible.'),
        section('Result Reconciliation', 'Separate realized, unrealized, income, costs, taxes, flows, and return metrics.'),
        limits,
    ]),
    'portfolio.market_events_review': contract('portfolio.market_events_review', [
        section(
            'Observed Portfolio Movements',
            'List every materially researched Asset movement using the supplied display name, exact period or dated extrema, movement magnitude, portfolio weight when available, coverage, and relevant LibreFolio trend/volatility context.',
            'Do not treat missing or partial history as a flat movement, and do not infer intraperiod paths that the supplied buckets do not show.',
        ),
        section(
            'Dated News Research',
            'For each external source provide publisher, title, URL, publication date, access date, source type, and the Asset/date window it may explain.',
            'Prefer primary issuer, exchange, regulator, central-bank, and government sources; distinguish established reporting from lower-quality secondary commentary.',
            'If web access is unavailable, state that clearly and do not fabricate citations, URLs, publication dates, or current events.',
        ),
        section(
            'Movement-to-Driver Assessment',
            'For each proposed link separate the observed LibreFolio movement from issuer-specific, sector/industry, and macro/market candidate drivers.',
            'Label confidence exactly as supported, inferred, or speculative. Explain timing and directional fit, cite corroborating or conflicting evidence, and never present temporal correlation as proven causation.',
        ),
        section('Cross-Portfolio Patterns', 'Identify shared dated drivers across multiple Assets only when evidence supports the common link; keep unrelated coincident moves separate.'),
        section('Unexplained or Weakly Explained Movements', 'List every material movement for which reliable dated evidence is absent, conflicting, too broad, or temporally mismatched. Never invent a driver.'),
        section('Limits and Follow-up Data', 'State source, timing, coverage, identity, and interpretation limits. Treat technical context as historical and subordinate, never as a forecast or recommendation.'),
    ]),
    'portfolio.income_review': contract('portfolio.income_review', [
        facts,
        section('Recorded Income Timeline', 'Use only the supplied dated recorded income entries and their per-currency conversion coverage.', 'Do not project, accrue, or forecast future coupons, dividends, or interest that the supplied timeline does not contain.'),
        section('Income Contributors and Concentration', 'Describe contributors and available concentration dimensions.'),
        section('Costs and Net Context', 'Keep gross income, fees, taxes, and net effects distinct.'),
        limits,
    ]),
    'portfolio.fifo_review': contract('portfolio.fifo_review', [
        facts,
        section('Open and Partial Lots', 'Present supplied current lots.'),
        section('Period Closures', 'Present lots closed inside the exported period.'),
        section('FIFO Results and Concentration', 'Keep cost, value, result, income, fee, tax, age, and valuation semantics distinct.'),
        limits,
    ]),
    'portfolio.technical_breadth': contract('portfolio.technical_breadth', [
        facts,
        section(
            'Aggregate Coverage and Event Digest',
            'Ground the breadth read in the supplied aggregate technical coverage, weighted and unweighted breadth, and recent-event digest.',
            'Do not require or reconstruct raw per-asset history in the response; deeper full technical detail is optional Additional Data.',
        ),
        section(
            'Breadth by Signal Family',
            'Separate the supplied weighted and unweighted trend, momentum, volatility, event, and other explicitly available signal families.',
            'Do not invent or reclassify missing risk metrics. If a family is unavailable, state that and do not infer it from another family.',
        ),
        evidence,
        limits,
    ]),
    'portfolio.description': contract('portfolio.description', [
        facts,
        section('Composition and Concentration', 'Describe available allocation dimensions and cash.'),
        section('Performance and Aggregate Technical Context', 'Keep performance and flows separate from supplied aggregate coverage, breadth, and recent-event digest.'),
        limits,
    ]),
    'broker.review': contract('broker.review', [
        facts,
        section('Holdings, Cash, and Concentration', 'Describe only the selected broker scope.'),
        section('Performance, Costs, Income, and FIFO', 'Keep methodologies and components distinct.'),
        section('Secondary Market Context', 'Use the supplied uniform asset comparison without turning the review into a complete Technical Export.'),
        drawdownContext,
        evidence,
        limits,
    ]),
    'broker.cost_efficiency': contract('broker.cost_efficiency', [
        facts,
        section(
            'Recorded Costs and Activity Coverage',
            'Report recorded fees, taxes, recorded total costs, typed cost contributors, source coverage, share-adjusted gross traded amount, trade/transaction counts, period, and currency exactly as supplied.',
            'Keep trading, FX, and other cost subcategories unavailable when the source does not classify them separately; never infer a subtype from free text or asset linkage.',
            'Distinguish recorded zero from unavailable source data and from not applicable. Unavailable is never zero; not applicable means inputs exist but the ratio has no meaningful denominator.',
        ),
        section(
            'Denominators and Ratios',
            'For every ratio, preserve the supplied status, formula, numerator, denominator, public unit, period, and coverage.',
            'Present a ratio value only when status is recorded. Explain unavailable and not-applicable reason codes without recomputing a different ratio.',
            'Keep fees, taxes, and total recorded costs distinct; do not substitute fees-plus-taxes for fees-only ratios.',
        ),
        section('Neutral Efficiency Considerations', 'Present conditional considerations, not instructions.'),
        limits,
    ]),
    'broker.concentration_context': contract('broker.concentration_context', [
        facts,
        section(
            'Concentration Dimensions',
            'Separate position, asset type, sector, geography, currency, and cash concentration.',
            'When the optional whole-portfolio comparator is supplied, contrast broker-scoped concentration against it; otherwise keep the analysis broker-scoped.',
            'Explicitly disclose any dimension whose coverage or liquidity is unknown rather than assuming full coverage or presence.',
        ),
        section('Aggregate Technical Context', 'Use only supplied aggregate coverage and breadth as secondary context.'),
        limits,
    ]),
    'broker.fifo_review': contract('broker.fifo_review', [facts, section('Open and Partial Lots', 'Present supplied current lots.'), section('Period Closures', 'Present supplied closures.'), section('Lot Results, Age, and Concentration', 'Keep valuation and result components distinct.'), limits]),
    'asset.trend_analysis': contract('asset.trend_analysis', [facts, section('Trend, Momentum, and Volatility', 'Separate horizons and preserve extrema dates.'), section('Technical Events', 'List material dated transitions without action language.'), external, limits]),
    'asset.position_review': contract('asset.position_review', [
        facts,
        section('Cost, Value, and P&L', 'Keep cost basis, valuation, realized, unrealized, income, fees, and taxes separate.'),
        section('Focused Market Context', 'Use supplied trend, momentum, volatility, limited history, and recent events without reconstructing a complete Trend Analysis.'),
        section('FIFO and Portfolio Role', 'Use only supplied lot and concentration context.', 'Acknowledge the supplied portfolio-role weight basis for this position and do not recompute or substitute a different weighting.'),
        drawdownContext,
        limits,
    ]),
    'fx.trend_review': contract('fx.trend_review', [facts, section('Direction, Trend, Momentum, and Volatility', 'Use quote-per-base semantics and preserve extrema dates.'), section('Technical Events', 'List material dated transitions.'), external, limits]),
    'fx.conversion_timing': contract('fx.conversion_timing', [
        facts,
        section(
            'Observed Conversion Timing Context',
            'Describe the observed range position as a location within the observed min-max range, never as a percentile or distributional rank.',
            'Use only the supplied observed returns, realized volatility, and source coverage or staleness.',
            'State that amount, deadline, spread, and fees are not supplied and must not be assumed or forecast.',
        ),
        section('Rate and Technical Context', 'Describe trend, momentum, volatility, and events.'),
        section('Neutral Timing Scenarios', 'Present multiple conditional approaches without point forecasts.'),
        external,
        limits,
    ]),
    'fx.exposure_impact': contract('fx.exposure_impact', [
        facts,
        section('Direct Exposure Links', 'Separate cash, trading-currency, and valuation-currency rows.'),
        section('Conditional Directional Impact', 'Use the supplied focused rate, return, volatility, trend, event, and coverage context without forecasting or look-through inference.'),
        external,
        limits,
    ]),
};

export function findAiExportResponseContract(analysisId: AiExportAnalysisId): AiExportResponseContractTemplate {
    return AI_EXPORT_RESPONSE_CONTRACTS[analysisId];
}
