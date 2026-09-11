export const ONBOARDING_FLOWS = ['welcome', 'intro_tour', 'broker_guide', 'fx_guide', 'asset_guide', 'import_guide'] as const;

export type OnboardingFlow = (typeof ONBOARDING_FLOWS)[number];
export type OnboardingStatus = 'pending' | 'completed' | 'skipped';
export type OnboardingLoadState = 'idle' | 'loading' | 'ready' | 'error';

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
}

export interface OnboardingProgressResponse {
    flows: OnboardingProgressItem[];
}

export function isOnboardingProgressDue(progress: OnboardingProgressItem | null | undefined): boolean {
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
}

export interface OnboardingReplayState {
    flow: OnboardingFlow;
    version: number;
    stepId: string;
    startedAt: number;
    returnTo?: string;
}
