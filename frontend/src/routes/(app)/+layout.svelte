<script lang="ts">
    import {onMount} from 'svelte';
    import {browser} from '$app/environment';
    import {page} from '$app/stores';
    import {afterNavigate, goto, preloadCode} from '$app/navigation';
    import {_, i18nLoading, initI18n} from '$lib/i18n';
    import {trackNavigation} from '$lib/stores/app/navigationStore';
    import {seedFromUrl} from '$lib/stores/dateRangeStore.svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {auth, isAuthenticated, isAuthInitialized, isSignOutRequested} from '$lib/stores/app/auth';
    import {appBootstrap} from '$lib/features/onboarding/appBootstrap.svelte';
    import {createOnboardingRouteSettlementCoordinator, runOwnedOnboardingRouteSettlement} from '$lib/features/onboarding/onboardingRouteSettlement';
    import {debug, isDebugEnabled} from '$lib/debug';
    import {getUserStorage} from '$lib/utils/storage';
    import Sidebar from '$lib/components/layout/Sidebar.svelte';
    import Header from '$lib/components/layout/Header.svelte';
    import ToastContainer from '$lib/components/ui/feedback/ToastContainer.svelte';
    import {donationPopup} from '$lib/stores/app/donationPopupStore.svelte';
    import {updateAvailable} from '$lib/features/update-check/updateCheckStore.svelte';
    import {checkForNewerRelease} from '$lib/features/update-check/updateCheck';
    import {zodiosApi} from '$lib/api';
    import {get, toStore} from 'svelte/store';
    import OnboardingBootstrapBlock from '$lib/components/onboarding/OnboardingBootstrapBlock.svelte';
    import OnboardingBootstrapBanner from '$lib/components/onboarding/OnboardingBootstrapBanner.svelte';
    import OnboardingOverlayHost from '$lib/components/onboarding/OnboardingOverlayHost.svelte';
    import DeferredAppPopups from '$lib/components/onboarding/DeferredAppPopups.svelte';
    import {onboardingGuide} from '$lib/features/onboarding/onboardingGuide.svelte';
    import {loginUrl} from '$lib/utils/internalPath';
    import ServerUnreachable from '$lib/components/layout/ServerUnreachable.svelte';

    // Sidebar state for mobile
    let sidebarOpen = false;

    // Sidebar collapsed state
    let sidebarCollapsed = false;

    // Running app version, fetched for the admin-only update prompt (F14)
    let appVersion = '';
    let isWelcomeRoute = false;
    let requestedPath = '';
    let onboardingDestination = '';
    let onboardingRouteReady = false;
    // Intentionally non-reactive: releasing ownership must not replay the snapshot just settled.
    const onboardingRouteSettlement = createOnboardingRouteSettlementCoordinator();

    // Initialize i18n
    initI18n();

    // As in the root layout: only the first dictionary shows the loading screen. A later
    // language switch keeps the app mounted, so no page is rebuilt and no draft is lost.
    let i18nBooted = false;
    $: if (!$i18nLoading) i18nBooted = true;

    // Track SPA navigation depth for smart back-navigation
    afterNavigate((nav) => {
        const url = nav.to?.url;
        trackNavigation(nav.type, url ? url.pathname + url.search : undefined);
        // On fresh page load (enter = bookmark/refresh/direct link), seed global date range from URL
        if (nav.type === 'enter' && url) {
            seedFromUrl(url.searchParams);
        }
    });

    onMount(async () => {
        debug.log('AppLayout', 'onMount started');

        // Sync language store with i18n after mount
        currentLanguage.init();

        // Load sidebar collapsed state from user-scoped localStorage
        if (browser) {
            const saved = getUserStorage('sidebar-collapsed', 'false');
            sidebarCollapsed = saved === 'true';
        }

        // Debug-only console command to force the donation popup open, without needing
        // 50 real logins. Not shipped in production builds (see $lib/debug).
        //   window.librefolioDebug.showDonationPopup()
        if (browser && isDebugEnabled()) {
            window.librefolioDebug = {
                ...window.librefolioDebug,
                showDonationPopup: () => donationPopup.forceShow(),
                // F14: force the update-available modal with a fake future release
                showUpdateModal: () => updateAvailable.show({version: '99.0.0', url: 'https://github.com/Librefolio/LibreFolio/releases', name: 'Debug test'}),
            };
            debug.log('AppLayout', 'Registered window.librefolioDebug.showDonationPopup()/.showUpdateModal()');
        }

        // Who is signed in: only a 401 leads to the login, and it keeps the page asked for.
        if (browser) await checkAuthAndStart();
    });

    /**
     * A server that has not answered after this long gets the retry panel. The check itself goes on: a
     * late answer still starts the app (or leads to the login), and Retry overtakes it.
     */
    const AUTH_SLOW_MS = 5000;
    // The retry panel is on screen: the server was slow, down or answering 5xx.
    let authUnreachable = false;
    // A check younger than AUTH_SLOW_MS is in flight: Retry stays disabled, the panel busy.
    let authCheckBusy = false;

    function currentPath(): string {
        const {pathname, search} = get(page).url;
        return pathname + search;
    }

    async function checkAuthAndStart(): Promise<void> {
        debug.log('AppLayout', 'Starting auth check');
        authCheckBusy = true;
        const slowTimer = setTimeout(() => {
            authUnreachable = true;
            authCheckBusy = false;
        }, AUTH_SLOW_MS);
        const outcome = await auth.checkAuth();
        clearTimeout(slowTimer);
        debug.log('AppLayout', 'Auth check result:', outcome);
        // A newer check (a Retry) owns the screen; this answer changes nothing.
        if (outcome === 'superseded') return;
        authCheckBusy = false;
        if (outcome === 'unreachable') {
            authUnreachable = true;
            return;
        }
        authUnreachable = false;
        if (outcome === 'unauthenticated') {
            debug.log('AppLayout', 'Not authenticated, redirecting to the login');
            goto(loginUrl(currentPath()));
            return;
        }
        await startAuthenticatedApp();
    }

    async function startAuthenticatedApp(): Promise<void> {
        debug.log('AppLayout', 'Loading authenticated app bootstrap');
        await loadAndSettleOnboardingRoute();

        // Preload JS for common routes in background so navigation
        // is instant — only code is prefetched, data is still lazy.
        Promise.all(['/dashboard', '/fx', '/assets', '/brokers', '/transactions', '/settings', '/files', '/tools'].map((r) => preloadCode(r).catch(() => {}))).catch(() => {});

        // F14: admins only — probe GitHub for a newer stable release
        // (throttled to once an hour, CHECK_INTERVAL_MS in updateCheck.ts;
        // silent on offline installs).
        if (get(auth).user?.is_superuser) {
            void (async () => {
                try {
                    const info = await zodiosApi.get_system_info_api_v1_system_info_get();
                    appVersion = info.app_version;
                    const release = await checkForNewerRelease(info.app_version);
                    if (release) updateAvailable.show(release);
                } catch {
                    // system info unreachable — no prompt
                }
            })();
        }
    }

    // Reactive redirect when the session ends after initialization. A sign-out the user asked for goes to a
    // plain login; a session that ended on its own (a 401 seen by the store) keeps the page to come back to.
    $: if (browser && $isAuthInitialized && !$isAuthenticated) {
        debug.log('AppLayout', 'Reactive redirect triggered');
        goto(isSignOutRequested() ? '/' : loginUrl($page.url.pathname + $page.url.search));
    }

    // This layout is a legacy component: its `$:` statements do not track runes state such as
    // `appBootstrap.ready`. Through a store, the route gate re-runs when the bootstrap settles,
    // so a due redirect shows `onboarding-redirecting` instead of painting the requested page.
    const bootstrapReady = toStore(() => appBootstrap.ready);

    $: isWelcomeRoute = $page.route.id === '/(app)/welcome';
    $: requestedPath = $page.url.pathname + $page.url.search;
    $: onboardingDestination = $bootstrapReady && isWelcomeRoute && onboardingGuide.active?.flow === 'intro_tour' ? '/dashboard' : $bootstrapReady ? appBootstrap.resolveDestination(requestedPath) : requestedPath;
    $: onboardingRouteReady = isWelcomeRoute || !$bootstrapReady || onboardingDestination === requestedPath;
    $: if (
        browser &&
        $isAuthenticated &&
        appBootstrap.ready &&
        !isWelcomeRoute &&
        onboardingRouteSettlement.claimReactive({
            state: appBootstrap.state,
            currentPath: requestedPath,
            isWelcomeRoute,
            destination: onboardingDestination,
        })
    ) {
        if (!onboardingRouteReady) {
            void goto(onboardingDestination, {replaceState: true});
        } else {
            onboardingGuide.maybeStartIntro();
        }
    }

    function toggleSidebar() {
        sidebarOpen = !sidebarOpen;
    }

    function setSidebarOpen(open: boolean) {
        sidebarOpen = open;
    }

    async function loadAndSettleOnboardingRoute(force = false): Promise<void> {
        await runOwnedOnboardingRouteSettlement({
            coordinator: onboardingRouteSettlement,
            loadBootstrap: () => appBootstrap.load(force),
            readSettlementInput: (state) => ({
                state,
                currentPath: $page.url.pathname + $page.url.search,
                isWelcomeRoute: $page.route.id === '/(app)/welcome',
                resolveDestination: (path) => appBootstrap.resolveDestination(path),
                navigate: (destination, options) => goto(destination, options),
                startIntro: () => onboardingGuide.maybeStartIntro(),
            }),
        });
    }

    async function retryBootstrap(): Promise<void> {
        await loadAndSettleOnboardingRoute(true);
    }

    async function logout(): Promise<void> {
        await auth.logout();
    }
</script>

{#if !i18nBooted}
    <!-- Loading screen while the first translations load -->
    <div class="min-h-screen flex items-center justify-center bg-libre-beige dark:bg-slate-900">
        <div class="text-libre-green dark:text-green-400 text-xl">Loading...</div>
    </div>
{:else if $isAuthenticated && appBootstrap.state === 'blocked'}
    <OnboardingBootstrapBlock error={appBootstrap.error} onretry={retryBootstrap} onlogout={logout} />
{:else if $isAuthenticated && !appBootstrap.ready}
    <div class="min-h-screen flex items-center justify-center bg-libre-beige dark:bg-slate-900" data-testid="app-bootstrap-loading">
        <div class="text-libre-green dark:text-green-400 text-xl">{$_('common.loading')}</div>
    </div>
{:else if $isAuthenticated && !onboardingRouteReady}
    <div class="min-h-screen flex items-center justify-center bg-libre-beige dark:bg-slate-900" data-testid="onboarding-redirecting">
        <div class="text-libre-green dark:text-green-400 text-xl">{$_('common.loading')}</div>
    </div>
{:else if $isAuthenticated && isWelcomeRoute}
    <div class="min-h-screen bg-libre-beige dark:bg-slate-900" data-testid="welcome-shell">
        <slot />
    </div>
{:else if $isAuthenticated}
    <div class="min-h-screen bg-libre-beige dark:bg-slate-900" inert={onboardingGuide.active?.flow === 'intro_tour'} data-guide-inert={onboardingGuide.active?.flow === 'intro_tour' ? 'true' : 'false'} data-testid="app-shell">
        <!-- Sidebar -->
        <Sidebar bind:isOpen={sidebarOpen} bind:collapsed={sidebarCollapsed} />

        <!-- Main Content Area -->
        <div class="min-h-screen flex flex-col transition-all duration-300 {sidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'}">
            <!-- Header -->
            <Header onToggleSidebar={toggleSidebar} {sidebarOpen} guideActive={onboardingGuide.active !== null} routeKey={$page.url.pathname + $page.url.search} />

            <!-- Page Content -->
            <main class="flex-1 p-4 lg:p-6">
                {#if appBootstrap.state === 'degraded'}
                    <OnboardingBootstrapBanner error={appBootstrap.error} onretry={retryBootstrap} />
                {/if}
                <slot />
            </main>
        </div>
    </div>
    <ToastContainer />
    <OnboardingOverlayHost currentPath={$page.url.pathname + $page.url.search} onrequestsidebar={setSidebarOpen} />
    <DeferredAppPopups guideActive={onboardingGuide.active !== null} currentVersion={appVersion} />
{:else if authUnreachable}
    <ServerUnreachable busy={authCheckBusy} onretry={() => void checkAuthAndStart()} />
{:else}
    <!-- Loading while checking auth -->
    <div class="min-h-screen flex items-center justify-center bg-libre-beige dark:bg-slate-900" data-testid="app-auth-checking">
        <div class="text-libre-green dark:text-green-400 text-xl">Checking authentication...</div>
    </div>
{/if}
