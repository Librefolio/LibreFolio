import type {ToolInput} from '$lib/features/tools/contracts';
import type {PacAllocationSourceAsset, PacAllocationSourceCashSource, PacAllocationSourceContext, PacAllocationUsageScope} from './allocationSource';

export type PacInput = ToolInput<'pac_allocator', '1.0.0'>;
export type RebalancerInput = ToolInput<'portfolio_rebalancer', '1.0.0'>;

export type PacAssetInput = NonNullable<PacInput['assets']>[number];
export type RebalanceHoldingInput = NonNullable<RebalancerInput['holdings']>[number];
export type AllocationTargetInput = NonNullable<PacInput['targets']>[number];
export type PacMoneyInput = NonNullable<PacInput['cash_balances']>[number];
export type PacContributionInput = NonNullable<PacInput['contributions']>[number];
export type PacRateInput = NonNullable<PacInput['valuation_rates']>[number];
export type AllocationBuyGridInput = NonNullable<PacAssetInput['buy_grid']>;

export interface PacRowSource {
    kind: 'portfolio_context' | 'catalog_candidate';
    assetId: number;
    candidateKey: string;
    assetActive: boolean;
    assetType: string;
    assetIconUrl: string | null;
    usageScope: PacAllocationUsageScope;
    contextKey: string | null;
    brokerId: number | null;
    brokerName: string | null;
    brokerIconUrl: string | null;
    brokerPortalUrl: string | null;
    brokerDefaultImportPlugin: string | null;
    ownershipSharePercent: string | null;
    sourceAsOfDate: string;
    quoteSource: string | null;
    quoteReferenceDate: string | null;
}

export interface PacAssetEditorValue extends PacAssetInput {
    name: string;
    buy_grid: AllocationBuyGridInput;
}

export interface RebalanceHoldingEditorValue extends RebalanceHoldingInput {
    name: string;
    quantity: string;
    quote: NonNullable<RebalanceHoldingInput['quote']>;
    buy_grid: AllocationBuyGridInput;
}

export interface PacEditorAsset {
    value: PacAssetEditorValue;
    source: PacAllocationSourceAsset | null;
    importedValue: PacAssetEditorValue | null;
    stale: boolean;
}

export interface RebalanceEditorHolding {
    value: RebalanceHoldingEditorValue;
    source: PacRowSource | null;
    importedValue: RebalanceHoldingEditorValue | null;
    stale: boolean;
}

export interface AllocationTargetDraft {
    instrument_key: string;
    name: string;
    target_percent: string;
}

export interface PacAssetChoice extends PacAllocationSourceAsset {
    selected: boolean;
    selectedSourceKeys: readonly string[];
    modifiedSourceKeys: readonly string[];
    staleSourceKeys: readonly string[];
}

export interface PacCashSourceState {
    mode: 'broker_copy' | 'manual';
    selectedBrokerIds: number[];
    sourceAsOfDate: string | null;
    sourceFingerprint: string | null;
    backendAggregatedBalances: PacMoneyInput[];
    manualBalances: PacMoneyInput[];
    sources: readonly PacAllocationSourceCashSource[];
    stale: boolean;
}

export type PacContributionMode = 'none' | 'custom';

export interface AllocationFundingDraft {
    cash: PacCashSourceState;
    contributionMode: PacContributionMode;
    contributions: PacContributionInput[];
}

export interface AllocationScenarioDraft extends AllocationFundingDraft {
    operation: 'analyze';
    report_currency: string;
    as_of_date: string;
    targets: AllocationTargetDraft[];
    valuationRates: PacRateInput[];
}

export interface PacDraft extends AllocationScenarioDraft {
    assets: PacEditorAsset[];
}

export interface RebalancerDraft extends AllocationScenarioDraft {
    holdings: RebalanceEditorHolding[];
}

export function allocationSourceKey(asset: PacAllocationSourceAsset, context: PacAllocationSourceContext | null): string {
    return context?.contextKey ?? asset.candidateKey;
}
