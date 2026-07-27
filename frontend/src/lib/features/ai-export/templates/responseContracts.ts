import {AI_EXPORT_FRONTEND_RESPONSE_CONTRACT_VERSION, type AiExportDomain, type AiExportTask, type AiExportTaskForDomain} from '../catalog/shared';

export interface AiExportResponseContractSection {
    readonly title: string;
    readonly requirements: readonly string[];
}

export interface AiExportResponseContractTemplate {
    readonly templateId: string;
    readonly contractId: string;
    readonly version: typeof AI_EXPORT_FRONTEND_RESPONSE_CONTRACT_VERSION;
    readonly domain: AiExportDomain;
    readonly task: AiExportTask;
    readonly sections: readonly AiExportResponseContractSection[];
}

function section(title: string, ...requirements: readonly string[]): AiExportResponseContractSection {
    return {title, requirements};
}

function defineResponseContract<D extends AiExportDomain>(domain: D, task: AiExportTaskForDomain<D>, sections: readonly AiExportResponseContractSection[]): AiExportResponseContractTemplate {
    const contractId = `${domain}.${task}`;
    return {
        templateId: `aiExport.responseContracts.${contractId}.v1`,
        contractId,
        version: AI_EXPORT_FRONTEND_RESPONSE_CONTRACT_VERSION,
        domain,
        task,
        sections,
    };
}

export const AI_EXPORT_RESPONSE_CONTRACTS = {
    pac_planning: defineResponseContract('portfolio', 'pac_planning', [
        section('Portfolio Summary', 'State only snapshot facts relevant to the accumulation plan.'),
        section('Allocation and Concentration', 'Describe material allocation and concentration facts without inventing a target.'),
        section('Areas That May Deserve Additional Capital', 'Explain evidence, uncertainty, and diversification rationale.'),
        section('Technical Context as Secondary Evidence', 'Keep technical observations descriptive and subordinate to portfolio context.'),
        section('Two or Three PAC Scenarios', 'Present distinct monthly allocation options with rationale and trade-offs.'),
        section('Assumptions and Missing User Information', 'List budget, horizon, preferences, constraints, and other unresolved inputs.'),
        section('Optional Recent Web Context', 'Include only when web research was enabled; keep sources and claims separate from snapshot facts.'),
    ]),
    rebalancing: defineResponseContract('portfolio', 'rebalancing', [
        section('Current Portfolio Facts', 'Summarize current allocation and concentration from the snapshot.'),
        section('Target Allocation and Tolerance Inputs', 'State supplied targets and identify missing targets or tolerance ranges.'),
        section('Measured Allocation Gaps', 'Quantify differences only where current and target values are both available.'),
        section('Rebalancing Pathways', 'Compare gradual, one-time, and mixed pathways without transaction commands.'),
        section('Cash-Flow-Only Pathway', 'Describe how future contributions could change allocation over time.'),
        section('Constraints, Costs, and Tax Caveats', 'Separate measured costs from tax or execution uncertainties.'),
        section('Assumptions and Missing Information', 'List every material assumption and unresolved user choice.'),
        section('Optional Web Context', 'Include only when enabled and clearly label it as external context.'),
    ]),
    performance_attribution: defineResponseContract('portfolio', 'performance_attribution', [
        section('Absolute Result', 'State the selected-period result and currency.'),
        section('Positive Contributors', 'Rank or group positive contribution facts without hiding residual effects.'),
        section('Negative Contributors', 'Rank or group negative contribution facts without hiding residual effects.'),
        section('Realized vs Unrealized', 'Keep realized and unrealized components separate.'),
        section('Income, Costs, and Taxes', 'Show each component separately and explain its effect on the result.'),
        section('TWRR, MWRR, and ROI Interpretation', 'Interpret only metrics present in the snapshot and distinguish their semantics.'),
        section('Cash Flow Effect', 'Explain external cash-flow effects separately from investment performance.'),
    ]),
    income_review: defineResponseContract('portfolio', 'income_review', [
        section('Period Income Summary', 'State gross income facts for the selected period.'),
        section('Income Contributors', 'Identify material positive contributors and their snapshot context.'),
        section('Income Concentration', 'Describe concentration by available asset, broker, currency, or income dimensions.'),
        section('Fees, Taxes, and Net Cash-Flow Context', 'Keep gross income, costs, and taxes separate.'),
        section('Reinvestment or Spending Context', 'Frame implications conditionally on user goals.'),
        section('Data Gaps and Assumptions', 'List missing yield, tax, timing, or classification information.'),
        section('Neutral Options to Evaluate', 'Present non-prescriptive considerations supported by the snapshot.'),
    ]),
    technical_breadth: defineResponseContract('portfolio', 'technical_breadth', [
        section('Coverage', 'State eligible, analyzed, and omitted universe and NAV coverage.'),
        section('Long-Term Trend Breadth', 'Describe long-term weighted and unweighted breadth with declared semantics.'),
        section('Short/Medium Trend Breadth', 'Describe shorter-horizon breadth separately from long-term breadth.'),
        section('Momentum Breadth', 'Describe momentum states without treating them as action signals.'),
        section('Volatility Observations', 'Summarize volatility breadth and notable dispersion.'),
        section('Recent Technical Events', 'Group material recent events and retain dates and targets.'),
        section('Limits of Analyzed Universe', 'Explain coverage, missing indicators, sampling, and selection limits.'),
    ]),
    portfolio_description: defineResponseContract('portfolio', 'portfolio_description', [
        section('Portfolio Snapshot', 'Summarize capital, NAV, market value, cash, and selected-period context.'),
        section('Allocation and Diversification', 'Describe available allocation dimensions and their semantics.'),
        section('Concentration Observations', 'Identify material concentrations without inventing a preferred target.'),
        section('Performance and Cash-Flow Context', 'Separate performance, contributions, income, costs, and taxes.'),
        section('Technical Context as Secondary Evidence', 'Use technical facts only when they change the interpretation.'),
        section('Data Quality and Coverage', 'State omissions, stale values, selection rules, and coverage.'),
        section('Assumptions and Questions', 'Separate assumptions from questions requiring user input.'),
    ]),
    asset_snapshot: defineResponseContract('asset', 'asset_snapshot', [
        section('Asset Identity and Market Snapshot', 'State identity, classification, currencies, and current market facts.'),
        section('Price and Return Facts', 'Describe selected-period prices, returns, extrema, and valuation source.'),
        section('Portfolio Holding Context', 'Include position and FIFO facts only when present.'),
        section('Technical State', 'Keep technical values and states descriptive.'),
        section('Events and Corporate Context', 'Separate measured events from note or provider context.'),
        section('Coverage and Data Quality', 'State missing price, signal, event, and sampling coverage.'),
        section('Optional Web Context', 'Include only when enabled and keep external facts separate.'),
    ]),
    asset_trend_analysis: defineResponseContract('asset', 'asset_trend_analysis', [
        section('Snapshot Facts', 'State current price, selected range, normalized return, and data source facts.'),
        section('Long-Term Trend', 'Describe long-horizon trend evidence.'),
        section('Short- and Medium-Term Trend', 'Describe shorter-horizon evidence separately.'),
        section('Momentum', 'Summarize momentum values, states, and changes.'),
        section('Volatility and Drawdown', 'Describe volatility, extrema, and drawdown facts.'),
        section('Recent Technical Events', 'List material dated events without action language.'),
        section('Optional Web Context', 'Include only when enabled and cite it as external context.'),
        section('Assumptions and Limits', 'State coverage, sampling, and interpretation limits.'),
    ]),
    position_review: defineResponseContract('asset', 'position_review', [
        section('Position Snapshot', 'State quantity, value, weight, broker scope, and valuation source.'),
        section('Cost Basis and Valuation', 'Keep cost basis and market valuation concepts separate.'),
        section('Realized and Unrealized Results', 'Report each component separately.'),
        section('FIFO Lot Context', 'Describe only the lot detail actually present.'),
        section('Income, Fees, and Taxes', 'Keep each amount and semantic separate.'),
        section('Portfolio Role and Concentration', 'Describe concentration without inventing a target role.'),
        section('Risks, Limits, and Questions', 'State missing prices, estimated values, scope limits, and user questions.'),
    ]),
    asset_pac_timing_context: defineResponseContract('asset', 'asset_pac_timing_context', [
        section('Long-Term Trend', 'Describe long-term trend facts.'),
        section('Distance from Averages', 'State measured distances and the averages used.'),
        section('Momentum', 'Describe momentum values and states.'),
        section('Volatility/Drawdown', 'State volatility and drawdown context.'),
        section('Recent Technical Events', 'List relevant dated events as observations.'),
        section('Optional Web Context', 'Include only when enabled and keep it separate from snapshot facts.'),
        section('Neutral Timing Scenarios', 'Present multiple conditional options, assumptions, and trade-offs.'),
    ]),
    drawdown_recovery: defineResponseContract('asset', 'drawdown_recovery', [
        section('Snapshot Facts', 'State selected range, current price, and valuation source.'),
        section('Peak-to-Trough Drawdown', 'Identify measured peak, trough, magnitude, and dates.'),
        section('Current Recovery Progress', 'Quantify recovery only where supported.'),
        section('Trend and Momentum Context', 'Describe current technical context without prediction.'),
        section('Volatility and Recent Events', 'Connect dated observations without claiming causality.'),
        section('Comparable Historical Episodes in Snapshot', 'Use only episodes represented by the supplied data.'),
        section('Optional Web Context', 'Include only when enabled and label external claims.'),
        section('Assumptions and Limits', 'State window, sampling, and missing-data limits.'),
    ]),
    fx_trend_review: defineResponseContract('fx', 'fx_trend_review', [
        section('Snapshot Facts', 'State pair direction, current rate, date, provider, and selected range.'),
        section('Direction and Magnitude', 'Describe selected-period movement in the declared quote-per-base direction.'),
        section('Trend State', 'Separate long-, medium-, and short-horizon trend evidence.'),
        section('Momentum and Volatility', 'Describe momentum, extrema, volatility, and drawdown facts.'),
        section('Recent Technical Events', 'List material dated events without trading language.'),
        section('Optional Web Context', 'Include only when enabled and keep macro context separate from rate facts.'),
        section('Assumptions and Limits', 'State provider, sampling, inversion, triangulation, and coverage limits.'),
    ]),
    fx_exposure_impact: defineResponseContract('fx', 'fx_exposure_impact', [
        section('FX Pair Snapshot Facts', 'State direction, rate, selected range, and source facts.'),
        section('Linked Cash Exposure', 'List authoritative cash-currency links separately.'),
        section('Linked Position Exposure', 'Separate trading- and valuation-currency links.'),
        section('Directional Impact Scenarios', 'Describe conditional effects without forecasting.'),
        section('Concentration and Sensitivity', 'Explain material linked exposure and uncertainty.'),
        section('Optional Web Context', 'Include only when enabled and label external macro context.'),
        section('Assumptions and Linkage Limits', 'State that linkage is not look-through exposure and list missing links.'),
    ]),
    fx_conversion_timing_context: defineResponseContract('fx', 'fx_conversion_timing_context', [
        section('Snapshot Facts', 'State pair direction, current rate, selected range, and provider.'),
        section('Current Rate Context', 'Describe location within observed extrema and sampled history.'),
        section('Trend and Momentum', 'Separate trend and momentum observations.'),
        section('Volatility and Drawdown', 'State measured uncertainty and drawdown facts.'),
        section('Neutral Timing Scenarios', 'Present multiple conditional conversion approaches as options.'),
        section('Optional Web Context', 'Include only when enabled and keep it separate from snapshot facts.'),
        section('Assumptions and Limits', 'State horizon, execution, provider, and data-window assumptions.'),
    ]),
    broker_review: defineResponseContract('broker', 'broker_review', [
        section('Broker Snapshot', 'State broker identity, NAV, market value, cash, and selected range.'),
        section('Holdings and Cash', 'Describe positions and cash without implying whole-portfolio coverage.'),
        section('Performance and Contributions', 'Separate performance from external capital flows.'),
        section('Concentration', 'Describe position and available allocation concentration.'),
        section('Costs, Taxes, and Income', 'Keep all three components separate.'),
        section('FIFO and Activity Context', 'Summarize FIFO and latest transaction facts only when present.'),
        section('Coverage and Data Quality', 'State access, selection, coverage, and missing data.'),
        section('Questions and Neutral Options', 'List unresolved inputs and non-prescriptive considerations.'),
    ]),
    broker_cost_efficiency: defineResponseContract('broker', 'broker_cost_efficiency', [
        section('Broker Cost Snapshot', 'State selected-period fee and tax totals.'),
        section('Fees and Taxes by Source', 'Separate categories and contributors where available.'),
        section('Cost Concentration', 'Identify material concentration without hiding small residuals.'),
        section('Cost Relative to Activity and Assets', 'Use ratios only when supported by snapshot denominators.'),
        section('Income Offset Context', 'Keep gross income and costs separate while describing their relationship.'),
        section('Data Gaps and Assumptions', 'List missing fee taxonomy, activity, or comparison context.'),
        section('Neutral Efficiency Options', 'Present operational considerations without transaction commands.'),
    ]),
    broker_concentration_context: defineResponseContract('broker', 'broker_concentration_context', [
        section('Broker Snapshot', 'State broker-scope NAV, holdings, cash, and selection facts.'),
        section('Position Concentration', 'Describe largest positions and concentration metrics.'),
        section('Asset-Type, Sector, Geography, and Currency Concentration', 'Keep each available dimension separate.'),
        section('Cash Concentration', 'Describe cash composition and currency when present.'),
        section('Technical Breadth as Secondary Context', 'Use breadth only as descriptive supporting evidence.'),
        section('Coverage and Selection Limits', 'State included entities, NAV coverage, and omitted dimensions.'),
        section('Neutral Diversification Questions', 'Frame unresolved diversification choices as questions.'),
    ]),
    broker_fifo_lot_review: defineResponseContract('broker', 'broker_fifo_lot_review', [
        section('FIFO Scope and Method', 'State broker scope, matching method, selected range, and aggregation level.'),
        section('Open and Partial Lots', 'Summarize counts, values, and residual cost basis.'),
        section('Closed-Lot Summary', 'Report aggregate closure facts without implying fragment history.'),
        section('Residual Cost Basis', 'Describe residual basis and valuation source separately.'),
        section('Realized and Unrealized Results', 'Keep result components separate.'),
        section('Lot Age and Concentration', 'Describe average age, oldest lots, and concentration.'),
        section('Income, Fees, and Taxes', 'Keep each component and semantic separate.'),
        section('Data Limits and Questions', 'State aggregation, coverage, estimated-at-cost, short, and in-transit limits.'),
    ]),
} satisfies Readonly<Record<AiExportTask, AiExportResponseContractTemplate>>;

export function findAiExportResponseContract(domain: AiExportDomain, task: AiExportTask): AiExportResponseContractTemplate | undefined {
    const template = AI_EXPORT_RESPONSE_CONTRACTS[task];
    return template.domain === domain ? template : undefined;
}
