<script lang="ts">
    import {goto} from '$app/navigation';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import WelcomePage from '$lib/components/onboarding/WelcomePage.svelte';
    import {onboardingApi} from '$lib/features/onboarding/onboardingApi';
    import type {WelcomeCopy, WelcomeDraft} from '$lib/features/onboarding/welcome';
    import {auth, currentUser} from '$lib/stores/app/auth';
    import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent} from '$lib/stores/app/clientSession';
    import {onboarding} from '$lib/stores/app/onboarding.svelte';
    import {userSettings} from '$lib/stores/app/settings';
    import {safeScalar, safeString} from '$lib/types/common';

    let language = $state('en');
    let baseCurrency = $state('EUR');
    let avatarUrl = $state<string | null>(null);
    let settingsHydrated = $state(false);
    let hydratedUserId = $state<string | null>(null);
    let progressUserId = $state<string | null>(null);
    let outcome = $state<'completed' | 'skipped' | null>(null);

    let copy = $derived<WelcomeCopy>({
        productName: 'LibreFolio',
        title: $_('onboarding.welcome.title'),
        description: $_('onboarding.welcome.description'),
        defaultsHint: $_('onboarding.welcome.defaultsHint'),
        avatarLabel: $_('onboarding.welcome.avatarLabel'),
        avatarHint: $_('onboarding.welcome.avatarHint'),
        chooseAvatar: $_('onboarding.welcome.chooseAvatar'),
        removeAvatar: $_('onboarding.welcome.removeAvatar'),
        avatarAlt: $_('onboarding.welcome.avatarAlt'),
        languageLabel: $_('settings.language'),
        languageHint: $_('settings.languageHint'),
        currencyLabel: $_('settings.defaultCurrency'),
        currencyHint: $_('settings.defaultCurrencyHint'),
        themeHint: $_('onboarding.welcome.themeHint'),
        skip: $_('onboarding.welcome.skip'),
        skipHint: $_('onboarding.welcome.skipHint'),
        continue: $_('common.continue'),
        logout: $_('auth.logout'),
        completed: $_('onboarding.welcome.completed'),
        skipped: $_('onboarding.welcome.skipped'),
    });

    $effect(() => {
        const rawUserId = safeScalar($currentUser?.id);
        const userId = rawUserId === null ? null : String(rawUserId);
        if (!userId) {
            settingsHydrated = false;
            hydratedUserId = null;
            progressUserId = null;
            outcome = null;
            return;
        }
        if (progressUserId !== userId) {
            progressUserId = userId;
            void loadProgress();
        }
        if (hydratedUserId !== userId) {
            settingsHydrated = false;
            outcome = null;
        }
        if (!$userSettings || hydratedUserId === userId) return;
        language = safeString($userSettings.language) || 'en';
        baseCurrency = safeString($userSettings.base_currency) || 'EUR';
        avatarUrl = safeString($userSettings.avatar_url) || null;
        settingsHydrated = true;
        hydratedUserId = userId;
        outcome = null;
    });

    async function loadProgress(): Promise<void> {
        try {
            await onboarding.load(onboardingApi);
        } catch {
            // Controller publishes the error for the future shell integration.
        }
    }

    function welcomeVersion(): number {
        const flow = onboarding.findFlow('welcome');
        if (!flow) throw new Error('Welcome progress is not loaded');
        return flow.current_version;
    }

    async function completeWelcome(draft: WelcomeDraft): Promise<void> {
        const generation = getClientSessionGeneration();
        const userId = getClientSessionUserId();
        if (!userId) throw new Error('Welcome requires an authenticated user');
        const settings = await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put({
            language: draft.language,
            base_currency: draft.baseCurrency,
            avatar_url: draft.avatarUrl,
        });
        if (!isClientSessionCurrent(generation) || getClientSessionUserId() !== userId) return;
        userSettings.setDirect(settings);
        const completed = await onboarding.complete(onboardingApi, 'welcome', welcomeVersion());
        if (!completed) return;
        outcome = 'completed';
    }

    async function skipWelcome(): Promise<void> {
        const skipped = await onboarding.skip(onboardingApi, 'welcome', welcomeVersion());
        if (!skipped) return;
        outcome = 'skipped';
    }

    async function logout(): Promise<void> {
        await auth.logout();
        await goto('/');
    }
</script>

{#if onboarding.state === 'error'}
    <div class="flex min-h-full items-center justify-center bg-libre-beige p-4 dark:bg-slate-950" data-testid="welcome-bootstrap-error">
        <section class="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl dark:bg-slate-900" role="alert">
            <h1 class="text-xl font-semibold text-gray-900 dark:text-white">
                {$_('onboarding.errors.loadTitle')}
            </h1>
            <p class="mt-2 text-sm text-gray-600 dark:text-gray-300">
                {onboarding.error}
            </p>
            <div class="mt-5 flex justify-end gap-2">
                <button type="button" class="rounded-lg px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-800" onclick={logout} data-testid="welcome-bootstrap-logout">
                    {copy.logout}
                </button>
                <button type="button" class="rounded-lg bg-libre-green px-4 py-2 text-sm font-medium text-white" onclick={loadProgress} data-testid="welcome-bootstrap-retry">
                    {$_('common.retry')}
                </button>
            </div>
        </section>
    </div>
{:else if onboarding.state !== 'ready' || !settingsHydrated}
    <div class="flex min-h-full items-center justify-center bg-libre-beige p-4 dark:bg-slate-950" aria-busy="true" data-testid="welcome-bootstrap-loading">
        <p class="text-sm text-gray-600 dark:text-gray-300">
            {$_('common.loading')}
        </p>
    </div>
{:else}
    <WelcomePage {copy} username={safeString($currentUser?.username) ?? ''} bind:language bind:baseCurrency bind:avatarUrl {outcome} oncomplete={completeWelcome} onskip={skipWelcome} onlogout={logout} />
{/if}
