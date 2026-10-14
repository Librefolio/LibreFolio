export const ONBOARDING_FLOWS = [
    'welcome',
    'intro_tour',
    'transactions_page_guide',
    'transaction_create_guide',
    'transaction_bulk_guide',
    'import_guide',
    'broker_page_guide',
    'broker_guide',
    'broker_detail_guide',
    'fx_page_guide',
    'fx_guide',
    'fx_detail_guide',
    'asset_page_guide',
    'asset_guide',
    'asset_detail_guide',
] as const;

export type OnboardingFlow = (typeof ONBOARDING_FLOWS)[number];
export type OnboardingStatus = 'pending' | 'completed' | 'skipped';
export type OnboardingLoadState = 'idle' | 'loading' | 'ready' | 'error';

export interface OnboardingStepProgressItem {
    step_id: string;
    status: OnboardingStatus;
    version: number;
    current_version: number;
    update_available: boolean;
    created_at: string;
    updated_at: string;
    completed_at: string | null;
    skipped_at: string | null;
}

export interface OnboardingProgressItem {
    flow: OnboardingFlow;
    status: OnboardingStatus;
    version: number;
    current_version: number;
    update_available: boolean;
    created_at: string;
    updated_at: string;
    completed_at: string | null;
    skipped_at: string | null;
    steps?: OnboardingStepProgressItem[];
}

export interface OnboardingProgressResponse {
    flows: OnboardingProgressItem[];
}

export function isOnboardingProgressDue(progress: OnboardingProgressItem | null | undefined): boolean {
    return progress != null && (progress.status === 'pending' || progress.version < progress.current_version);
}

export function isOnboardingStepProgressDue(progress: OnboardingStepProgressItem | null | undefined): boolean {
    return progress != null && (progress.status === 'pending' || progress.version < progress.current_version);
}

export interface OnboardingTransitionRequest {
    expected_version: number;
}

export interface OnboardingWelcomeSettings {
    language: 'en' | 'it' | 'fr' | 'es';
    base_currency: string;
    avatar_url: string | null;
}

export interface OnboardingWelcomeCompleteRequest extends OnboardingTransitionRequest {
    welcome_settings: OnboardingWelcomeSettings;
}

export interface OnboardingApi {
    getProgress(): Promise<OnboardingProgressResponse>;
    completeFlow(flow: OnboardingFlow, request: OnboardingTransitionRequest): Promise<OnboardingProgressItem>;
    completeWelcome(request: OnboardingWelcomeCompleteRequest): Promise<OnboardingProgressItem>;
    skipFlow(flow: OnboardingFlow, request: OnboardingTransitionRequest): Promise<OnboardingProgressItem>;
    completeStep(flow: OnboardingFlow, stepId: string, request: OnboardingTransitionRequest): Promise<OnboardingProgressItem>;
    skipStep(flow: OnboardingFlow, stepId: string, request: OnboardingTransitionRequest): Promise<OnboardingProgressItem>;
}

export interface OnboardingReplayState {
    flow: OnboardingFlow;
    version: number;
    stepId: string;
    mode?: 'automatic' | 'replay';
    remainingStepIds?: string[];
    startedAt: number;
    returnTo?: string;
}
