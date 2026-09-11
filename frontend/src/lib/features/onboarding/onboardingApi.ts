import {z} from 'zod';

import {axiosInstance} from '$lib/api';
import type {OnboardingApi, OnboardingFlow, OnboardingProgressItem, OnboardingProgressResponse, OnboardingTransitionRequest, OnboardingWelcomeCompleteRequest} from '$lib/types/onboarding';

const progressItemSchema = z
    .object({
        flow: z.enum(['welcome', 'intro_tour', 'broker_guide', 'fx_guide', 'asset_guide', 'import_guide']),
        status: z.enum(['pending', 'completed', 'skipped']),
        version: z.number().int().positive(),
        current_version: z.number().int().positive(),
        update_available: z.boolean(),
        created_at: z.string(),
        updated_at: z.string(),
        completed_at: z.string().nullable(),
        skipped_at: z.string().nullable(),
    })
    .strict();

const progressResponseSchema = z.object({flows: z.array(progressItemSchema)}).strict();

function parseItem(value: unknown): OnboardingProgressItem {
    return progressItemSchema.parse(value);
}

export const onboardingApi: OnboardingApi = {
    async getProgress(): Promise<OnboardingProgressResponse> {
        const response = await axiosInstance.get('/api/v1/settings/onboarding');
        return progressResponseSchema.parse(response.data);
    },

    async completeFlow(flow: OnboardingFlow, request: OnboardingTransitionRequest): Promise<OnboardingProgressItem> {
        const response = await axiosInstance.post(`/api/v1/settings/onboarding/${flow}/complete`, request);
        return parseItem(response.data);
    },

    async completeWelcome(request: OnboardingWelcomeCompleteRequest): Promise<OnboardingProgressItem> {
        const response = await axiosInstance.post('/api/v1/settings/onboarding/welcome/complete', request);
        return parseItem(response.data);
    },

    async skipFlow(flow: OnboardingFlow, request: OnboardingTransitionRequest): Promise<OnboardingProgressItem> {
        const response = await axiosInstance.post(`/api/v1/settings/onboarding/${flow}/skip`, request);
        return parseItem(response.data);
    },
};
