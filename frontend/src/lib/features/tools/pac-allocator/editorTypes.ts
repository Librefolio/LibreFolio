import type {ToolInput} from '$lib/features/tools/contracts';
import type {PacAllocationSourceAsset} from './allocationSource';

export type PacInput = ToolInput<'pac_allocator', '1.0.0'>;
export type PacInputRow = NonNullable<PacInput['rows']>[number];
export type PacDraftRow = PacInputRow & {
    quote: NonNullable<PacInputRow['quote']>;
    buy_grid: NonNullable<PacInputRow['buy_grid']>;
};
export type PacMoneyInput = NonNullable<PacInput['cash_balances']>[number];
export type PacRateInput = NonNullable<PacInput['valuation_rates']>[number];

export interface PacRowSource {
    assetId: number;
    contextKey: string;
    brokerId: number;
    brokerName: string;
    ownershipSharePercent: string;
    sourceAsOfDate: string;
    quoteSource: string | null;
    quoteReferenceDate: string | null;
}

export interface PacEditorRow {
    value: PacDraftRow;
    origin: 'manual' | 'portfolio' | 'duplicate';
    source: PacRowSource | null;
    importedValue: PacDraftRow | null;
    stale: boolean;
}

export interface PacAssetChoice extends PacAllocationSourceAsset {
    selectedContextKeys: readonly string[];
    modifiedContextKeys: readonly string[];
    staleContextKeys: readonly string[];
}

export interface PacDraft {
    operation: 'analyze';
    report_currency: string;
    as_of_date: string;
    rows: PacEditorRow[];
    cashMode: 'not_supplied' | 'none' | 'custom';
    cashBalances: PacMoneyInput[];
    contributionMode: 'not_supplied' | 'none' | 'custom';
    contributions: PacMoneyInput[];
    allowFx: boolean;
    valuationRates: PacRateInput[];
}
