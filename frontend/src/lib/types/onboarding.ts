export const ONBOARDING_FLOWS = ['welcome', 'intro_tour', 'import_guide'] as const;

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

export interface OnboardingTransitionRequest {
    expected_version: number;
}

export interface OnboardingApi {
    getProgress(): Promise<OnboardingProgressResponse>;
    completeFlow(flow: OnboardingFlow, request: OnboardingTransitionRequest): Promise<OnboardingProgressItem>;
    skipFlow(flow: OnboardingFlow, request: OnboardingTransitionRequest): Promise<OnboardingProgressItem>;
}

export interface OnboardingReplayState {
    flow: OnboardingFlow;
    version: number;
    stepId: string;
    startedAt: number;
}
