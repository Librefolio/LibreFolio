import type {OnboardingFlow} from '$lib/types/onboarding';

export const CORE_TOUR_STEP_IDS = ['intro.scene', 'intro.dashboard', 'intro.navigation', 'intro.transactions_nav', 'intro.brokers_nav', 'intro.fx_nav', 'intro.assets_nav', 'intro.tools_nav', 'intro.settings_nav'] as const;

export const BROKER_GUIDE_STEP_IDS = ['broker.overview', 'broker.plugin', 'broker.icon'] as const;
export const FX_GUIDE_STEP_IDS = ['fx.currencies', 'fx.providers'] as const;
export const ASSET_GUIDE_STEP_IDS = ['asset.search', 'asset.identity', 'asset.provider'] as const;
export const IMPORT_GUIDE_STEP_IDS = ['import.upload', 'import.select', 'import.analyze', 'import.assets', 'import.fix', 'import.duplicates', 'import.review', 'import.bulk'] as const;

export type CoreTourStepId = (typeof CORE_TOUR_STEP_IDS)[number];
export type BrokerGuideStepId = (typeof BROKER_GUIDE_STEP_IDS)[number];
export type FxGuideStepId = (typeof FX_GUIDE_STEP_IDS)[number];
export type AssetGuideStepId = (typeof ASSET_GUIDE_STEP_IDS)[number];
export type ImportGuideStepId = (typeof IMPORT_GUIDE_STEP_IDS)[number];
export type GuideStepId = CoreTourStepId | BrokerGuideStepId | FxGuideStepId | AssetGuideStepId | ImportGuideStepId;
export type GuidedOnboardingFlow = Exclude<OnboardingFlow, 'welcome'>;

export interface GuideFlowDefinition {
    trigger: 'automatic' | 'contextual';
    presentation: 'spotlight' | 'pointer';
    steps: readonly GuideStepId[];
}

export const ONBOARDING_GUIDE_CATALOG: Record<GuidedOnboardingFlow, GuideFlowDefinition> = {
    intro_tour: {
        trigger: 'automatic',
        presentation: 'spotlight',
        steps: CORE_TOUR_STEP_IDS,
    },
    broker_guide: {
        trigger: 'contextual',
        presentation: 'pointer',
        steps: BROKER_GUIDE_STEP_IDS,
    },
    fx_guide: {
        trigger: 'contextual',
        presentation: 'pointer',
        steps: FX_GUIDE_STEP_IDS,
    },
    asset_guide: {
        trigger: 'contextual',
        presentation: 'pointer',
        steps: ASSET_GUIDE_STEP_IDS,
    },
    import_guide: {
        trigger: 'contextual',
        presentation: 'pointer',
        steps: IMPORT_GUIDE_STEP_IDS,
    },
};

export function firstGuideStep(flow: GuidedOnboardingFlow): GuideStepId {
    return ONBOARDING_GUIDE_CATALOG[flow].steps[0];
}

export function guideSteps(flow: GuidedOnboardingFlow): readonly GuideStepId[] {
    return ONBOARDING_GUIDE_CATALOG[flow].steps;
}
