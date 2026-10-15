// @vitest-environment jsdom
/**
 * The login page (`routes/+page.svelte`) takes the message a link page left (accounts lot A5b).
 *
 * `/invite` and `/reset-password` end on the login page with something to say — the account was created, the password
 * was changed — and the login page is another route: the link page calls `setAuthFlash(message)` before `goto('/')`,
 * and the login page starts its success message from `takeAuthFlash()` (plan A5b.1), so it says it once. The other
 * half of the handoff is pinned in `authFlash.test.ts` and in the two link pages' tests; this file pins the reading
 * end: the message lands in `LoginCard`'s `login-success`, inside `login-page` (the frame keeps the test id every E2E
 * login waits on).
 *
 * What runs for real: the page, `AuthPageFrame` and `LoginCard`. What is replaced: `authFlash.ts` (a spy answering
 * like the real one — the message once, then `''`), the auth store (signed out, nothing loading), the bootstrap, the
 * instance configuration and the global settings (inert fakes), the generated client (never called here), and the
 * frame's decoration (no-op components). `$app/environment` stays the shared mock, `browser: false`, so the page skips
 * the session check and shows the login at once. `$lib/i18n` keeps its real exports with the identity as translator.
 *
 * Written red-first: the page does not read the flash yet, and `LoginCard`'s success box has no test id.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    return {
        instance: reactiveBox<{config: InstanceConfig}>({config: {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}}}),
        takeAuthFlash: vi.fn<() => string>().mockName('takeAuthFlash'),
        setAuthFlash: vi.fn((_message: string) => {}).mockName('setAuthFlash'),
        noopComponent: () => {},
    };
});

vi.mock('$lib/features/auth/authFlash', () => ({setAuthFlash: mocks.setAuthFlash, takeAuthFlash: mocks.takeAuthFlash}));
vi.mock('$lib/stores/app/auth', async () => {
    const {readable} = await import('svelte/store');
    return {
        auth: {checkAuth: vi.fn(() => Promise.resolve('anonymous')), clearError: vi.fn(), logout: vi.fn(() => Promise.resolve()), login: vi.fn(() => Promise.resolve(false))},
        authError: readable(null),
        isAuthLoading: readable(false),
        isAuthenticated: readable(false),
    };
});
vi.mock('$lib/features/onboarding/appBootstrap.svelte', () => ({
    appBootstrap: {state: 'idle', error: null, load: vi.fn(() => new Promise(() => {})), resolveDestination: vi.fn((path: string) => path)},
}));
vi.mock('$lib/features/onboarding/components/OnboardingBootstrapBlock.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/instance/instanceConfig.svelte', () => ({
    DEFAULT_INSTANCE_CONFIG: {profile: 'selfhosted', accounts: {registration_mode: 'open', registration_locked: false}},
    instanceConfig: {
        get config() {
            return mocks.instance.config;
        },
        get loaded() {
            return true;
        },
        get failed() {
            return false;
        },
        load: vi.fn(() => Promise.resolve()),
    },
}));
vi.mock('$lib/stores/app/globalSettings', async () => {
    const {readable} = await import('svelte/store');
    return {globalSettings: {subscribe: readable({}).subscribe, load: vi.fn(() => Promise.resolve())}};
});
vi.mock('$lib/api', () => ({zodiosApi: {}}));
vi.mock('$app/navigation', () => ({
    goto: vi.fn(() => Promise.resolve()),
    replaceState: vi.fn(),
    pushState: vi.fn(),
    invalidate: vi.fn(() => Promise.resolve()),
    invalidateAll: vi.fn(() => Promise.resolve()),
    preloadCode: vi.fn(() => Promise.resolve()),
    preloadData: vi.fn(() => Promise.resolve()),
    afterNavigate: vi.fn(),
    beforeNavigate: vi.fn(),
    onNavigate: vi.fn(),
}));
vi.mock('$lib/i18n', async (importOriginal) => {
    const {readable} = await import('svelte/store');
    const identity = readable((key: string) => key);
    return {...(await importOriginal<typeof import('$lib/i18n')>()), _: identity, t: identity};
});
// The frame's decoration: each reaches for stores, localStorage or the document, and none is the subject.
vi.mock('$lib/components/ui/ThemeToggle.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/layout/LanguageSelector.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/layout/HelpMenu.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/ui/AnimatedBackground.svelte', () => ({default: mocks.noopComponent}));

import {cleanup, render, screen, waitFor, within} from '$test/component';
import LoginPage from './+page.svelte';

/** Waits for the login page and returns it. */
async function loginPage(): Promise<HTMLElement> {
    await waitFor(() => expect(screen.getByTestId('login-page')).toBeInTheDocument());
    return screen.getByTestId('login-page');
}

beforeEach(() => {
    mocks.takeAuthFlash.mockReset();
    mocks.takeAuthFlash.mockReturnValue('');
});

afterEach(cleanup);

describe('the login page — the message a link page left', () => {
    it('shows it in login-success, inside login-page', async () => {
        // Like the real flash: the message once, then nothing.
        mocks.takeAuthFlash.mockReturnValueOnce('A message the link page left');

        render(LoginPage);

        const page = await loginPage();
        await waitFor(() => expect(within(page).getByTestId('login-success')).toHaveTextContent('A message the link page left'));
        expect(mocks.takeAuthFlash, 'the page reads the flash').toHaveBeenCalled();
    });

    it('shows no success message when no link page left one', async () => {
        render(LoginPage);

        const page = await loginPage();
        expect(within(page).getByTestId('login-modal'), 'premise: the login card is drawn').toBeInTheDocument();
        expect(within(page).queryByTestId('login-success')).toBeNull();
    });
});
