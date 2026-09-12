import type {ToolInput} from '$lib/features/tools/contracts';
import type {PacAllocationSourceAsset, PacAllocationSourceCashSource, PacAllocationUsageScope} from './allocationSource';

export type PacInput = ToolInput<'pac_allocator', '1.0.0'>;
export type PacInputRow = NonNullable<PacInput['rows']>[number];
export type PacDraftRow = PacInputRow & {
    quote: NonNullable<PacInputRow['quote']>;
    buy_grid: NonNullable<PacInputRow['buy_grid']>;
};
export type PacMoneyInput = NonNullable<PacInput['cash_balances']>[number];
export type PacContributionInput = NonNullable<PacInput['contributions']>[number];
export type PacRateInput = NonNullable<PacInput['valuation_rates']>[number];

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

export type PacRowOrigin = 'manual' | 'portfolio_context' | 'catalog_candidate' | 'manual_duplicate';

export interface PacEditorRow {
    value: PacDraftRow;
    origin: PacRowOrigin;
    source: PacRowSource | null;
    importedValue: PacDraftRow | null;
    stale: boolean;
}

export interface PacAssetChoice extends PacAllocationSourceAsset {
    selected: boolean;
    selectedSourceKeys: readonly string[];
    modifiedSourceKeys: readonly string[];
    staleSourceKeys: readonly string[];
}

export interface PacCashSourceState {
    mode: 'not_supplied' | 'none' | 'broker_copy' | 'manual';
    selectedBrokerIds: number[];
    sourceAsOfDate: string | null;
    sourceFingerprint: string | null;
    backendAggregatedBalances: PacMoneyInput[];
    manualBalances: PacMoneyInput[];
    sources: readonly PacAllocationSourceCashSource[];
    stale: boolean;
}

export type PacContributionMode = 'not_supplied' | 'none' | 'custom';

export interface PacDraft {
    operation: 'analyze';
    report_currency: string;
    as_of_date: string;
    rows: PacEditorRow[];
    cash: PacCashSourceState;
    contributionMode: PacContributionMode;
    contributions: PacContributionInput[];
    allowFx: boolean;
    valuationRates: PacRateInput[];
}
