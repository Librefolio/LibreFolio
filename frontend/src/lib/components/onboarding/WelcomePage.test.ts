// @vitest-environment jsdom
/**
 * WelcomePage — logout/avatar/complete/skip orchestration.
 *
 * Two things are mocked, for two different reasons:
 *
 *  - `SettingCurrency` (via `WelcomeForm`) is swapped for the harness probe used by
 *    `WelcomeForm.test.ts`: the real `CurrencySearchSelect` child loads currencies/FX
 *    routes from the network on mount, which has nothing to do with this page's own
 *    orchestration (logout/avatar/complete/skip).
 *  - `ImagePickerWrapper` is swapped for a harness probe: the real component statically
 *    imports `AssetPickerModal`/`ImageEditModal`, pulling in the whole asset-search /
 *    upload / crop graph just to test that this page opens the picker and applies or
 *    clears whatever URL comes back — a unit test boundary defect (OOM under load),
 *    not something this page's own orchestration needs. The probe exposes a bindable
 *    `open`, a real `role="dialog"` while open, and `select`/`remove` controls that
 *    stand in for `AssetPickerModal`'s `select` event and the "remove image"
 *    empty-string case.
 *
 * `oncomplete`/`onskip`/`onlogout` are the actual contract under test — WelcomePage's
 * own `run()` wrapper is what must set/clear busy and surface a thrown message, so
 * every scenario drives those callbacks directly rather than asserting on the network
 * request a production `+page.svelte` would eventually make.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/components/settings/SettingCurrency.svelte', async () => ({
    default: (await import('$test/harness/SettingCurrencyProbe.svelte')).default,
}));

vi.mock('$lib/components/ui/media/ImagePickerWrapper.svelte', async () => ({
    default: (await import('$test/harness/ImagePickerWrapperProbe.svelte')).default,
}));

import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import type {WelcomeCopy} from '$lib/features/onboarding/welcome';
import OnboardingBootstrapBanner from './OnboardingBootstrapBanner.svelte';
import OnboardingBootstrapBlock from './OnboardingBootstrapBlock.svelte';
import WelcomePage from './WelcomePage.svelte';

const COPY: WelcomeCopy = {
    productName: 'PRODUCT_TOKEN',
    title: 'TITLE_TOKEN',
    description: 'DESCRIPTION_TOKEN',
    defaultsHint: 'DEFAULTS_HINT_TOKEN',
    avatarLabel: 'AVATAR_LABEL_TOKEN',
    avatarHint: 'AVATAR_HINT_TOKEN',
    chooseAvatar: 'CHOOSE_AVATAR_TOKEN',
    removeAvatar: 'REMOVE_AVATAR_TOKEN',
    avatarAlt: 'AVATAR_ALT_TOKEN',
    languageLabel: 'LANGUAGE_LABEL_TOKEN',
    languageHint: 'LANGUAGE_HINT_TOKEN',
    currencyLabel: 'CURRENCY_LABEL_TOKEN',
    currencyHint: 'CURRENCY_HINT_TOKEN',
    themeHint: 'THEME_HINT_TOKEN',
    skip: 'SKIP_TOKEN',
    skipHint: 'SKIP_HINT_TOKEN',
    continue: 'CONTINUE_TOKEN',
    logout: 'LOGOUT_TOKEN',
    completed: 'COMPLETED_TOKEN',
    skipped: 'SKIPPED_TOKEN',
};

beforeAll(async () => {
    await setupI18n();
});

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (error: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

interface MountProps {
    avatarUrl?: string | null;
    outcome?: 'completed' | 'skipped' | null;
}

function mount(props: MountProps = {}) {
    const oncomplete = vi.fn();
    const onskip = vi.fn();
    const onlogout = vi.fn();
    const utils = render(WelcomePage, {
        copy: COPY,
        username: 'Jane Doe',
        language: 'en',
        baseCurrency: 'EUR',
        avatarUrl: null,
        outcome: null,
        ...props,
        oncomplete,
        onskip,
        onlogout,
    });
    return {oncomplete, onskip, onlogout, ...utils};
}

describe('WelcomePage — logout', () => {
    it('calls onlogout directly, without going through the busy/error wrapper', async () => {
        const {onlogout} = mount();

        await fireEvent.click(screen.getByTestId('welcome-logout'));

        expect(onlogout).toHaveBeenCalledTimes(1);
        // Logout is not routed through run(): the form must not have flipped busy.
        expect(screen.getByTestId('welcome-form')).toHaveAttribute('data-busy', 'false');
    });
});

describe('WelcomePage — complete', () => {
    it('goes busy while oncomplete is pending, then clears busy with no error on success', async () => {
        const {oncomplete} = mount();
        const {promise, resolve} = deferred<void>();
        oncomplete.mockReturnValue(promise);

        await fireEvent.click(screen.getByTestId('welcome-continue'));
        expect(oncomplete).toHaveBeenCalledTimes(1);
        expect(oncomplete).toHaveBeenCalledWith({language: 'en', baseCurrency: 'EUR', avatarUrl: null});
        await waitFor(() => expect(screen.getByTestId('welcome-form')).toHaveAttribute('data-busy', 'true'));

        resolve();
        await waitFor(() => expect(screen.getByTestId('welcome-form')).toHaveAttribute('data-busy', 'false'));
        expect(screen.queryByTestId('welcome-error')).toBeNull();
    });

    it('surfaces the failure message and clears busy, without touching outcome', async () => {
        const {oncomplete} = mount({outcome: null});
        oncomplete.mockRejectedValue(new Error('COMPLETE_FAILED_TOKEN'));

        await fireEvent.click(screen.getByTestId('welcome-continue'));

        await waitFor(() => expect(screen.getByTestId('welcome-error')).toHaveTextContent('COMPLETE_FAILED_TOKEN'));
        expect(screen.getByTestId('welcome-form')).toHaveAttribute('data-busy', 'false');
        // outcome is caller-owned; a page-level failure must never fabricate one.
        expect(screen.getByTestId('welcome-page')).toHaveAttribute('data-outcome', 'pending');
        expect(screen.queryByTestId('welcome-outcome')).toBeNull();
    });

    it('wraps a non-Error rejection into a generic failure message', async () => {
        const {oncomplete} = mount();
        oncomplete.mockRejectedValue('nope');

        await fireEvent.click(screen.getByTestId('welcome-continue'));

        await waitFor(() => expect(screen.getByTestId('welcome-error')).toBeInTheDocument());
        expect(screen.getByTestId('welcome-error')).toHaveTextContent('Onboarding action failed');
    });
});

describe('WelcomePage — skip', () => {
    it('owns the permanent Skip above the form, runs it through busy, and clears busy on success', async () => {
        const {onskip} = mount();
        const {promise, resolve} = deferred<void>();
        onskip.mockReturnValue(promise);
        const form = screen.getByTestId('welcome-form');
        const skip = screen.getByTestId('welcome-skip');

        expect(form).not.toContainElement(skip);

        await fireEvent.click(skip);
        expect(onskip).toHaveBeenCalledTimes(1);
        await waitFor(() => expect(screen.getByTestId('welcome-form')).toHaveAttribute('data-busy', 'true'));
        expect(skip).toBeDisabled();

        resolve();
        await waitFor(() => expect(screen.getByTestId('welcome-form')).toHaveAttribute('data-busy', 'false'));
        expect(skip).toBeEnabled();
        expect(screen.queryByTestId('welcome-error')).toBeNull();
    });

    it('surfaces a skip failure without ever setting an outcome', async () => {
        const {onskip} = mount();
        onskip.mockRejectedValue(new Error('SKIP_FAILED_TOKEN'));

        await fireEvent.click(screen.getByTestId('welcome-skip'));

        await waitFor(() => expect(screen.getByTestId('welcome-error')).toHaveTextContent('SKIP_FAILED_TOKEN'));
        expect(screen.getByTestId('welcome-page')).toHaveAttribute('data-outcome', 'pending');
    });
});

describe('WelcomePage — outcome banner replaces the form', () => {
    it('renders the completed banner and hides the form entirely when outcome is set', () => {
        mount({outcome: 'completed'});

        expect(screen.getByTestId('welcome-page')).toHaveAttribute('data-outcome', 'completed');
        expect(screen.getByTestId('welcome-outcome')).toHaveTextContent('COMPLETED_TOKEN');
        expect(screen.queryByTestId('welcome-form')).toBeNull();
        expect(screen.queryByTestId('welcome-skip')).toBeNull();
    });

    it('renders the skipped banner for a skipped outcome', () => {
        mount({outcome: 'skipped'});

        expect(screen.getByTestId('welcome-outcome')).toHaveTextContent('SKIPPED_TOKEN');
    });
});

describe('WelcomePage — avatar orchestration', () => {
    it('choosing an avatar opens the picker dialog', async () => {
        mount();

        await fireEvent.click(screen.getByTestId('welcome-avatar-choose'));

        await waitFor(() => expect(screen.getByRole('dialog')).toBeInTheDocument());
    });

    it('clearing a staged avatar removes the image and the clear control', async () => {
        mount({avatarUrl: 'https://example.test/avatar.png'});
        expect(screen.getByRole('img', {name: 'AVATAR_ALT_TOKEN'})).toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('welcome-avatar-clear'));

        await waitFor(() => expect(screen.queryByRole('img')).toBeNull());
        expect(screen.queryByTestId('welcome-avatar-clear')).toBeNull();
    });
});

/**
 * OnboardingBootstrapBlock / OnboardingBootstrapBanner — the two bootstrap error
 * handles `appBootstrap` renders around the rest of the app (blocked full-screen vs.
 * degraded inline banner). Both are pure, prop-driven components: `error`, `onretry`
 * and (block-only) `onlogout` are the whole contract, so they are covered here
 * directly rather than through `appBootstrap` itself (see the singleton-injection
 * seam noted in onboarding.test.ts). Assertions target `data-testid`/ARIA roles and
 * the caller-supplied `error` string — never the i18n copy the component falls back
 * to when `error` is null.
 */
describe('OnboardingBootstrapBlock — blocked bootstrap handle', () => {
    it('renders as an alert and exposes retry/logout controls', () => {
        render(OnboardingBootstrapBlock, {error: null, onretry: vi.fn(), onlogout: vi.fn()});

        const region = screen.getByTestId('onboarding-bootstrap-blocked');
        expect(region).toBeInTheDocument();
        expect(screen.getByRole('alert')).toBeInTheDocument();
        expect(screen.getByTestId('onboarding-bootstrap-retry')).toBeInTheDocument();
        expect(screen.getByTestId('onboarding-bootstrap-logout')).toBeInTheDocument();
    });

    it('surfaces the caller-supplied error text verbatim (never a translated fallback) when one is provided', () => {
        render(OnboardingBootstrapBlock, {error: 'BOOTSTRAP_ERROR_TOKEN', onretry: vi.fn(), onlogout: vi.fn()});

        expect(screen.getByTestId('onboarding-bootstrap-blocked')).toHaveTextContent('BOOTSTRAP_ERROR_TOKEN');
    });

    it('calls onretry when the retry control is activated', async () => {
        const onretry = vi.fn();
        render(OnboardingBootstrapBlock, {error: null, onretry, onlogout: vi.fn()});

        await fireEvent.click(screen.getByTestId('onboarding-bootstrap-retry'));

        expect(onretry).toHaveBeenCalledTimes(1);
    });

    it('calls onlogout when the logout control is activated, independently of retry', async () => {
        const onretry = vi.fn();
        const onlogout = vi.fn();
        render(OnboardingBootstrapBlock, {error: null, onretry, onlogout});

        await fireEvent.click(screen.getByTestId('onboarding-bootstrap-logout'));

        expect(onlogout).toHaveBeenCalledTimes(1);
        expect(onretry).not.toHaveBeenCalled();
    });
});

describe('OnboardingBootstrapBanner — degraded bootstrap handle', () => {
    it('renders as a status region with a retry control', () => {
        render(OnboardingBootstrapBanner, {error: null, onretry: vi.fn()});

        expect(screen.getByTestId('onboarding-bootstrap-degraded')).toBeInTheDocument();
        expect(screen.getByRole('status')).toBeInTheDocument();
        expect(screen.getByTestId('onboarding-bootstrap-banner-retry')).toBeInTheDocument();
    });

    it('surfaces the caller-supplied error text verbatim when one is provided', () => {
        render(OnboardingBootstrapBanner, {error: 'DEGRADED_ERROR_TOKEN', onretry: vi.fn()});

        expect(screen.getByTestId('onboarding-bootstrap-degraded')).toHaveTextContent('DEGRADED_ERROR_TOKEN');
    });

    it('calls onretry when its retry control is activated', async () => {
        const onretry = vi.fn();
        render(OnboardingBootstrapBanner, {error: null, onretry});

        await fireEvent.click(screen.getByTestId('onboarding-bootstrap-banner-retry'));

        expect(onretry).toHaveBeenCalledTimes(1);
    });
});
