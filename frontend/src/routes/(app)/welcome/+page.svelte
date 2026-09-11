<script lang="ts">
    import {goto} from '$app/navigation';
    import {page} from '$app/stores';
    import {tick} from 'svelte';
    import {waitLocale} from 'svelte-i18n';
    import {_, locale, type SupportedLocale} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import WelcomePage from '$lib/components/onboarding/WelcomePage.svelte';
    import {onboardingApi} from '$lib/features/onboarding/onboardingApi';
    import {onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';
    import type {WelcomeCopy, WelcomeDraft} from '$lib/features/onboarding/welcome';
    import {auth, currentUser} from '$lib/stores/app/auth';
    import {currentLanguage} from '$lib/stores/app/language';
    import {getClientSessionGeneration, getClientSessionUserId, isClientSessionCurrent} from '$lib/stores/app/clientSession';
    import {onboarding} from '$lib/stores/app/onboarding.svelte';
    import {userSettings} from '$lib/stores/app/settings';
    import {safeScalar, safeString} from '$lib/types/common';

    let language = $state('en');
    let baseCurrency = $state('EUR');
    let avatarUrl = $state<string | null>(null);
    let settingsHydrated = $state(false);
    let hydratedUserId = $state<string | null>(null);
    let outcome = $state<'completed' | 'skipped' | null>(null);
    let actionInFlight = $state(false);
    let persistedLanguage = $state<SupportedLocale>('en');
    let localePreviewSequence = 0;
    let welcomeFlow = $derived(onboarding.findFlow('welcome'));
    let welcomeReplay = $derived(welcomeFlow ? onboarding.hasReplay('welcome', welcomeFlow.current_version) : false);

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
        skip: $_(welcomeReplay ? 'onboarding.actions.exitTour' : 'onboarding.welcome.skip'),
        skipHint: '',
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
            outcome = null;
            return;
        }
        if (hydratedUserId !== userId) {
            settingsHydrated = false;
            outcome = null;
        }
        if (!$userSettings || hydratedUserId === userId) return;
        language = (safeString($userSettings.language) || 'en') as SupportedLocale;
        persistedLanguage = language as SupportedLocale;
        baseCurrency = safeString($userSettings.base_currency) || 'EUR';
        avatarUrl = safeString($userSettings.avatar_url) || null;
        settingsHydrated = true;
        hydratedUserId = userId;
        outcome = null;
    });

    $effect(() => {
        const flow = onboarding.findFlow('welcome');
        if (actionInFlight || !settingsHydrated || !flow || flow.status === 'pending' || outcome !== null) return;
        if (onboarding.hasReplay('welcome', flow.current_version)) return;
        void goto(safeReturnTo() ?? '/dashboard', {replaceState: true});
    });

    function welcomeVersion(): number {
        const flow = onboarding.findFlow('welcome');
        if (!flow) throw new Error('Welcome progress is not loaded');
        return flow.current_version;
    }

    function safeReturnTo(): string | undefined {
        const value = $page.url.searchParams.get('returnTo');
        if (!value || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return undefined;
        return value;
    }

    async function continueAfterWelcome(): Promise<void> {
        const returnTo = safeReturnTo();
        const introStarted = onboardingGuide.maybeStartIntro(returnTo);
        await goto(introStarted ? '/dashboard' : (returnTo ?? '/dashboard'), {
            replaceState: true,
        });
    }

    async function previewLanguage(nextLanguage: string): Promise<void> {
        const next = nextLanguage as SupportedLocale;
        const request = ++localePreviewSequence;
        locale.set(next);
        await waitLocale(next);
        if (request !== localePreviewSequence) return;
        await tick();
    }

    async function restorePersistedLanguage(): Promise<void> {
        localePreviewSequence += 1;
        currentLanguage.set(persistedLanguage);
        await waitLocale(persistedLanguage);
        await tick();
    }

    async function completeWelcome(draft: WelcomeDraft): Promise<void> {
        const generation = getClientSessionGeneration();
        const userId = getClientSessionUserId();
        if (!userId) throw new Error('Welcome requires an authenticated user');
        actionInFlight = true;
        try {
            const version = welcomeVersion();
            const welcomeSettings = {
                language: draft.language as 'en' | 'it' | 'fr' | 'es',
                base_currency: draft.baseCurrency,
                avatar_url: draft.avatarUrl,
            };
            const replay = onboarding.hasReplay('welcome', version);
            const updatedSettings = replay ? await zodiosApi.update_user_settings_endpoint_api_v1_settings_user_put(welcomeSettings) : null;
            const completed = replay
                ? true
                : await onboarding.completeWelcome(onboardingApi, {
                      expected_version: version,
                      welcome_settings: welcomeSettings,
                  });
            if (!completed || !isClientSessionCurrent(generation) || getClientSessionUserId() !== userId) return;
            const currentSettings = userSettings.get();
            if (updatedSettings) {
                userSettings.setDirect(updatedSettings);
            } else if (currentSettings) {
                userSettings.setDirect({
                    ...currentSettings,
                    language: draft.language as 'en' | 'it' | 'fr' | 'es',
                    base_currency: draft.baseCurrency,
                    avatar_url: draft.avatarUrl,
                });
            }
            currentLanguage.set(draft.language as 'en' | 'it' | 'fr' | 'es');
            await waitLocale(draft.language);
            await tick();
            if (!isClientSessionCurrent(generation) || getClientSessionUserId() !== userId) return;
            onboarding.clearReplay('welcome', version);
            outcome = 'completed';
            await continueAfterWelcome();
        } finally {
            actionInFlight = false;
        }
    }

    async function skipWelcome(): Promise<void> {
        actionInFlight = true;
        try {
            const version = welcomeVersion();
            const replay = onboarding.hasReplay('welcome', version);
            const skipped = replay || (await onboarding.skip(onboardingApi, 'welcome', version));
            if (!skipped) return;
            await restorePersistedLanguage();
            onboarding.clearReplay('welcome', version);
            outcome = 'skipped';
            await continueAfterWelcome();
        } finally {
            actionInFlight = false;
        }
    }

    async function logout(): Promise<void> {
        await restorePersistedLanguage();
        await auth.logout();
        await goto('/');
    }
</script>

{#if !onboarding.findFlow('welcome') || !settingsHydrated}
    <div class="flex min-h-full items-center justify-center bg-libre-beige p-4 dark:bg-slate-950" aria-busy="true" data-testid="welcome-bootstrap-loading">
        <p class="text-sm text-gray-600 dark:text-gray-300">
            {$_('common.loading')}
        </p>
    </div>
{:else}
    <WelcomePage {copy} username={safeString($currentUser?.username) ?? ''} bind:language bind:baseCurrency bind:avatarUrl {outcome} oncomplete={completeWelcome} onskip={skipWelcome} onlanguagechange={(nextLanguage) => void previewLanguage(nextLanguage)} onlogout={logout} />
{/if}
