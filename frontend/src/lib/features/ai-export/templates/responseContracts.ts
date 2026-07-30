import type {AiExportAnalysisId} from '../catalog/shared';

export interface AiExportResponseContractSection {
    readonly title: string;
    readonly requirements: readonly string[];
}

export interface AiExportResponseContractTemplate {
    readonly id: string;
    readonly version: 1;
    readonly analysisId: AiExportAnalysisId;
    readonly sections: readonly AiExportResponseContractSection[];
}

function section(title: string, ...requirements: readonly string[]): AiExportResponseContractSection {
    return {title, requirements};
}

function contract(analysisId: AiExportAnalysisId, sections: readonly AiExportResponseContractSection[]): AiExportResponseContractTemplate {
    return {id: `${analysisId}.response`, version: 1, analysisId, sections};
}

const facts = section('LibreFolio Facts', 'State the relevant supplied facts, units, currencies, signs, periods, and scope.');
const evidence = section('Evidence and Interpretation', 'Connect conclusions to supplied data and dated technical buckets without inventing missing evidence.');
const external = section('External Context', 'When web access was used, cite source and dates and keep external facts separate from LibreFolio facts.');
const limits = section('Assumptions, Limits, and Questions', 'List data gaps, assumptions, unresolved user inputs, and interpretation limits.');

export const AI_EXPORT_RESPONSE_CONTRACTS: Readonly<Record<AiExportAnalysisId, AiExportResponseContractTemplate>> = {
    'portfolio.pac_planning': contract('portfolio.pac_planning', [facts, section('PAC Scenarios', 'Present two or three conditional recurring-contribution scenarios with rationale and trade-offs.'), evidence, external, limits]),
    'portfolio.rebalancing': contract('portfolio.rebalancing', [
        facts,
        section('Measured Allocation Gaps', 'Quantify only against supplied targets or tolerances.'),
        section('Rebalancing Pathways', 'Compare cash-flow-only, one-time, and mixed pathways without transaction commands.'),
        external,
        limits,
    ]),
    'portfolio.performance_attribution': contract('portfolio.performance_attribution', [
        facts,
        section('Positive and Negative Contributors', 'Keep the complete supplied universe and residual effects visible.'),
        section('Result Reconciliation', 'Separate realized, unrealized, income, costs, taxes, flows, and return metrics.'),
        limits,
    ]),
    'portfolio.income_review': contract('portfolio.income_review', [facts, section('Income Contributors and Concentration', 'Describe contributors and available concentration dimensions.'), section('Costs and Net Context', 'Keep gross income, fees, taxes, and net effects distinct.'), limits]),
    'portfolio.fifo_review': contract('portfolio.fifo_review', [
        facts,
        section('Open and Partial Lots', 'Present supplied current lots.'),
        section('Period Closures', 'Present lots closed inside the exported period.'),
        section('FIFO Results and Concentration', 'Keep cost, value, result, income, fee, tax, age, and valuation semantics distinct.'),
        limits,
    ]),
    'portfolio.technical_breadth': contract('portfolio.technical_breadth', [facts, section('Breadth by Signal Family', 'Separate weighted/unweighted trend, momentum, volatility, risk, and events.'), evidence, limits]),
    'portfolio.description': contract('portfolio.description', [facts, section('Composition and Concentration', 'Describe available allocation dimensions and cash.'), section('Performance and Technical Context', 'Keep performance, flows, and technical evidence separate.'), limits]),
    'broker.review': contract('broker.review', [facts, section('Holdings, Cash, and Concentration', 'Describe only the selected broker scope.'), section('Performance, Costs, Income, and FIFO', 'Keep methodologies and components distinct.'), evidence, limits]),
    'broker.cost_efficiency': contract('broker.cost_efficiency', [facts, section('Cost Contributors and Ratios', 'Use ratios only with supplied denominators.'), section('Neutral Efficiency Considerations', 'Present conditional considerations, not instructions.'), limits]),
    'broker.concentration_context': contract('broker.concentration_context', [facts, section('Concentration Dimensions', 'Separate positions, asset type, sector, geography, currency, and cash.'), evidence, limits]),
    'broker.fifo_review': contract('broker.fifo_review', [facts, section('Open and Partial Lots', 'Present supplied current lots.'), section('Period Closures', 'Present supplied closures.'), section('Lot Results, Age, and Concentration', 'Keep valuation and result components distinct.'), limits]),
    'asset.trend_analysis': contract('asset.trend_analysis', [facts, section('Trend, Momentum, and Volatility', 'Separate horizons and preserve extrema dates.'), section('Technical Events', 'List material dated transitions without action language.'), external, limits]),
    'asset.position_review': contract('asset.position_review', [facts, section('Cost, Value, and P&L', 'Keep cost basis, valuation, realized, unrealized, income, fees, and taxes separate.'), section('FIFO and Portfolio Role', 'Use only supplied lot and concentration context.'), limits]),
    'fx.trend_review': contract('fx.trend_review', [facts, section('Direction, Trend, Momentum, and Volatility', 'Use quote-per-base semantics and preserve extrema dates.'), section('Technical Events', 'List material dated transitions.'), external, limits]),
    'fx.conversion_timing': contract('fx.conversion_timing', [facts, section('Rate and Technical Context', 'Describe trend, momentum, volatility, and events.'), section('Neutral Timing Scenarios', 'Present multiple conditional approaches without forecasts.'), external, limits]),
    'fx.exposure_impact': contract('fx.exposure_impact', [
        facts,
        section('Direct Exposure Links', 'Separate cash, trading-currency, and valuation-currency rows.'),
        section('Conditional Directional Impact', 'Describe scenarios without forecasting and without look-through inference.'),
        external,
        limits,
    ]),
};

export function findAiExportResponseContract(analysisId: AiExportAnalysisId): AiExportResponseContractTemplate {
    return AI_EXPORT_RESPONSE_CONTRACTS[analysisId];
}
