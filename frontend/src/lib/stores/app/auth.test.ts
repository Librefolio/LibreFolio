import {beforeEach, describe, expect, it, vi} from 'vitest';

const loginApi = vi.hoisted(() => vi.fn());
const logoutApi = vi.hoisted(() => vi.fn());
const meApi = vi.hoisted(() => vi.fn());

vi.mock('$app/environment', () => ({browser: false}));
vi.mock('$app/navigation', () => ({goto: vi.fn()}));
vi.mock('$lib/api', () => ({
    zodiosApi: {
        login_api_v1_auth_login_post: loginApi,
        logout_api_v1_auth_logout_post: logoutApi,
        get_me_api_v1_auth_me_get: meApi,
    },
}));
vi.mock('$lib/debug', () => ({
    debug: {
        log: vi.fn(),
        warn: vi.fn(),
        error: vi.fn(),
        info: vi.fn(),
    },
}));
vi.mock('$lib/stores/app/language', () => ({
    currentLanguage: {set: vi.fn()},
}));
vi.mock('$lib/stores/app/settings', () => ({
    userSettings: {setDirect: vi.fn()},
}));
vi.mock('$lib/stores/app/donationPopupStore.svelte', () => ({
    donationPopup: {trigger: vi.fn()},
}));

import {auth, getAuthState} from './auth';

function user(id: number, username: string) {
    return {
        id,
        username,
        email: `${username}@example.com`,
        is_admin: false,
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
    };
}

describe('auth operation ordering', () => {
    beforeEach(() => {
        auth.reset();
        loginApi.mockReset();
        logoutApi.mockReset();
        meApi.mockReset();
    });

    it('ignores a stale checkAuth response that resolves after login', async () => {
        let resolveCheck: (value: unknown) => void = () => undefined;
        meApi.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    resolveCheck = resolve;
                }),
        );
        loginApi.mockResolvedValueOnce({
            user: user(2, 'new-user'),
            user_settings: null,
            show_donation_popup: false,
        });

        const staleCheck = auth.checkAuth();
        expect(await auth.login('new-user', 'password')).toBe(true);

        resolveCheck({user: user(1, 'old-user')});
        expect(await staleCheck).toBe(false);
        expect(getAuthState().user?.id).toBe(2);
    });
});
