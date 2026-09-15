import type {OnboardingFlow} from '$lib/types/onboarding';

export const CORE_TOUR_STEP_IDS = ['intro.scene', 'intro.navigation', 'intro.dashboard', 'intro.transactions_nav', 'intro.brokers_nav', 'intro.fx_nav', 'intro.assets_nav', 'intro.tools_nav', 'intro.settings_nav'] as const;

export const TRANSACTIONS_PAGE_STEP_IDS = ['transactions.page.overview', 'transactions.page.add', 'transactions.page.import', 'transactions.page.columns'] as const;
export const TRANSACTION_CREATE_STEP_IDS = ['transaction.create.basics', 'transaction.create.amounts', 'transaction.create.details', 'transaction.create.save'] as const;
export const TRANSACTION_BULK_STEP_IDS = ['transaction.bulk.workspace', 'transaction.bulk.validation', 'transaction.bulk.selection', 'transaction.bulk.save'] as const;
export const BROKER_PAGE_STEP_IDS = ['broker.page.overview', 'broker.page.currency', 'broker.page.views', 'broker.page.add'] as const;
export const BROKER_GUIDE_STEP_IDS = ['broker.overview', 'broker.plugin', 'broker.icon'] as const;
export const BROKER_DETAIL_STEP_IDS = ['broker.detail.header', 'broker.detail.overview', 'broker.detail.positions', 'broker.detail.transactions', 'broker.detail.info'] as const;
export const FX_PAGE_STEP_IDS = ['fx.page.overview', 'fx.page.filters', 'fx.page.sync', 'fx.page.add'] as const;
export const FX_GUIDE_STEP_IDS = ['fx.currencies', 'fx.providers'] as const;
export const FX_DETAIL_STEP_IDS = ['fx.detail.header', 'fx.detail.provider', 'fx.detail.chart', 'fx.detail.editor'] as const;
export const ASSET_PAGE_STEP_IDS = ['asset.page.overview', 'asset.page.filters', 'asset.page.sync', 'asset.page.add'] as const;
export const ASSET_GUIDE_STEP_IDS = ['asset.search', 'asset.identity', 'asset.provider'] as const;
export const ASSET_DETAIL_STEP_IDS = ['asset.detail.header', 'asset.detail.chart', 'asset.detail.editor', 'asset.detail.metadata', 'asset.detail.risk'] as const;
export const IMPORT_GUIDE_STEP_IDS = ['import.upload', 'import.select', 'import.analyze', 'import.assets', 'import.fix', 'import.duplicates', 'import.review', 'import.bulk'] as const;

export type CoreTourStepId = (typeof CORE_TOUR_STEP_IDS)[number];
export type TransactionsPageStepId = (typeof TRANSACTIONS_PAGE_STEP_IDS)[number];
export type TransactionCreateStepId = (typeof TRANSACTION_CREATE_STEP_IDS)[number];
export type TransactionBulkStepId = (typeof TRANSACTION_BULK_STEP_IDS)[number];
export type BrokerPageStepId = (typeof BROKER_PAGE_STEP_IDS)[number];
export type BrokerGuideStepId = (typeof BROKER_GUIDE_STEP_IDS)[number];
export type BrokerDetailStepId = (typeof BROKER_DETAIL_STEP_IDS)[number];
export type FxPageStepId = (typeof FX_PAGE_STEP_IDS)[number];
export type FxGuideStepId = (typeof FX_GUIDE_STEP_IDS)[number];
export type FxDetailStepId = (typeof FX_DETAIL_STEP_IDS)[number];
export type AssetPageStepId = (typeof ASSET_PAGE_STEP_IDS)[number];
export type AssetGuideStepId = (typeof ASSET_GUIDE_STEP_IDS)[number];
export type AssetDetailStepId = (typeof ASSET_DETAIL_STEP_IDS)[number];
export type ImportGuideStepId = (typeof IMPORT_GUIDE_STEP_IDS)[number];
export type GuidePointerMode = 'none' | 'cursor';
export type GuideHighlightMode = 'none' | 'pulse';
export type GuidePanelPlacement = 'auto' | 'center' | 'top' | 'bottom' | 'left' | 'right';
export type GuideScrollPolicy = 'none' | 'nearest-if-hidden';
export type GuideStepId =
    | CoreTourStepId
    | TransactionsPageStepId
    | TransactionCreateStepId
    | TransactionBulkStepId
    | BrokerPageStepId
    | BrokerGuideStepId
    | BrokerDetailStepId
    | FxPageStepId
    | FxGuideStepId
    | FxDetailStepId
    | AssetPageStepId
    | AssetGuideStepId
    | AssetDetailStepId
    | ImportGuideStepId;
export type GuidedOnboardingFlow = Exclude<OnboardingFlow, 'welcome'>;
export type ContextualOnboardingFlow = Exclude<GuidedOnboardingFlow, 'intro_tour' | 'import_guide'>;

export interface GuideFlowDefinition {
    trigger: 'automatic' | 'contextual';
    steps: readonly GuideStepId[];
    completionMode?: 'flow' | 'steps';
    navigationMode?: 'sequence' | 'checkpoint';
}

export const ONBOARDING_GUIDE_CATALOG: Record<GuidedOnboardingFlow, GuideFlowDefinition> = {
    intro_tour: {
        trigger: 'automatic',
        steps: CORE_TOUR_STEP_IDS,
    },
    transactions_page_guide: {
        trigger: 'contextual',
        steps: TRANSACTIONS_PAGE_STEP_IDS,
    },
    transaction_create_guide: {
        trigger: 'contextual',
        steps: TRANSACTION_CREATE_STEP_IDS,
    },
    transaction_bulk_guide: {
        trigger: 'contextual',
        steps: TRANSACTION_BULK_STEP_IDS,
        completionMode: 'steps',
        navigationMode: 'checkpoint',
    },
    import_guide: {
        trigger: 'contextual',
        steps: IMPORT_GUIDE_STEP_IDS,
        completionMode: 'steps',
    },
    broker_page_guide: {
        trigger: 'contextual',
        steps: BROKER_PAGE_STEP_IDS,
    },
    broker_guide: {
        trigger: 'contextual',
        steps: BROKER_GUIDE_STEP_IDS,
    },
    broker_detail_guide: {
        trigger: 'contextual',
        steps: BROKER_DETAIL_STEP_IDS,
    },
    fx_page_guide: {
        trigger: 'contextual',
        steps: FX_PAGE_STEP_IDS,
    },
    fx_guide: {
        trigger: 'contextual',
        steps: FX_GUIDE_STEP_IDS,
    },
    fx_detail_guide: {
        trigger: 'contextual',
        steps: FX_DETAIL_STEP_IDS,
    },
    asset_page_guide: {
        trigger: 'contextual',
        steps: ASSET_PAGE_STEP_IDS,
    },
    asset_guide: {
        trigger: 'contextual',
        steps: ASSET_GUIDE_STEP_IDS,
    },
    asset_detail_guide: {
        trigger: 'contextual',
        steps: ASSET_DETAIL_STEP_IDS,
    },
};

export function firstGuideStep(flow: GuidedOnboardingFlow): GuideStepId {
    return ONBOARDING_GUIDE_CATALOG[flow].steps[0];
}

export function guideSteps(flow: GuidedOnboardingFlow): readonly GuideStepId[] {
    return ONBOARDING_GUIDE_CATALOG[flow].steps;
}

export function isStepManagedFlow(flow: GuidedOnboardingFlow): boolean {
    return ONBOARDING_GUIDE_CATALOG[flow].completionMode === 'steps';
}

export function isCheckpointFlow(flow: GuidedOnboardingFlow): boolean {
    return ONBOARDING_GUIDE_CATALOG[flow].navigationMode === 'checkpoint';
}
