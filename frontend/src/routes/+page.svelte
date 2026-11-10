<script lang="ts">
    import {onMount} from 'svelte';
    import {browser} from '$app/environment';
    import {goto} from '$app/navigation';
    import AnimatedBackground from '$lib/components/ui/AnimatedBackground.svelte';
    import AuthPageFrame from '$lib/features/auth/AuthPageFrame.svelte';
    import LoginCard from '$lib/features/auth/LoginCard.svelte';
    import RegisterCard from '$lib/features/auth/RegisterCard.svelte';
    import ForgotPasswordCard from '$lib/features/auth/ForgotPasswordCard.svelte';
    import {takeAuthFlash, takeAuthFlashTone} from '$lib/features/auth/authFlash';
    import {auth} from '$lib/stores/app/auth';
    import {isAuthenticated} from '$lib/stores/app/auth';
    import {appBootstrap} from '$lib/features/onboarding/appBootstrap.svelte';
    import OnboardingBootstrapBlock from '$lib/features/onboarding/components/OnboardingBootstrapBlock.svelte';
    import {page} from '$app/stores';
    import {safeInternalPath} from '$lib/utils/internalPath';

    // Auth view state (modals)
    type AuthView = 'login' | 'register' | 'forgot-password';
    let currentView: AuthView = 'login';

    // Success message: from the registration card, or left by a link page (invitation, password reset)
    let successMessage = takeAuthFlash();
    // and how it is drawn: a warning when the account was created but its activation email was held
    let successTone: 'success' | 'warning' = takeAuthFlashTone();

    // Loading state while checking auth
    let checkingAuth = true;

    // Where to go after signing in: the page the user was on (`?redirect=`), when it is an in-app path.
    $: redirectTo = safeInternalPath($page.url.searchParams.get('redirect'));

    async function routeAuthenticated(requestedPath: string): Promise<void> {
        checkingAuth = true;
        const state = await appBootstrap.load();
        if (state === 'blocked') {
            checkingAuth = false;
            return;
        }
        if (state === 'ready' || state === 'degraded') {
            await goto(appBootstrap.resolveDestination(requestedPath), {
                replaceState: true,
            });
        }
    }

    // Check if already authenticated and redirect. Any other answer shows the login, as before: here the
    // page asked for is the login itself.
    onMount(async () => {
        if (browser) {
            if ((await auth.checkAuth()) === 'authenticated') {
                await routeAuthenticated(redirectTo);
                return;
            }
        }
        checkingAuth = false;
    });

    // Handle navigation between modals
    function handleGotoRegister() {
        auth.clearError();
        successMessage = '';
        successTone = 'success';
        currentView = 'register';
    }

    function handleGotoForgot() {
        auth.clearError();
        successMessage = '';
        successTone = 'success';
        currentView = 'forgot-password';
    }

    function handleGotoLogin(event: CustomEvent<{message?: string; tone?: 'warning'}>) {
        auth.clearError();
        successMessage = event.detail?.message || '';
        successTone = event.detail?.tone ?? 'success';
        currentView = 'login';
    }

    function handleGotoLoginSimple() {
        auth.clearError();
        successMessage = '';
        successTone = 'success';
        currentView = 'login';
    }

    async function retryBootstrap(): Promise<void> {
        checkingAuth = true;
        const state = await appBootstrap.load(true);
        if (state === 'ready' || state === 'degraded') {
            await goto(appBootstrap.resolveDestination(redirectTo), {
                replaceState: true,
            });
            return;
        }
        checkingAuth = false;
    }

    async function logout(): Promise<void> {
        await auth.logout();
        checkingAuth = false;
    }
</script>

<AnimatedBackground />

{#if checkingAuth}
    <!-- Loading while checking authentication -->
    <div class="min-h-screen flex items-center justify-center" data-testid="auth-loading">
        <div class="text-lf-link text-xl">Loading...</div>
    </div>
{:else if $isAuthenticated && appBootstrap.state === 'blocked'}
    <OnboardingBootstrapBlock error={appBootstrap.error} onretry={retryBootstrap} onlogout={logout} />
{:else}
    <AuthPageFrame testId="login-page">
        <!-- Card Container - instant swap, no transition -->
        {#if currentView === 'login'}
            <LoginCard {redirectTo} {successMessage} {successTone} onAuthenticated={routeAuthenticated} on:gotoRegister={handleGotoRegister} on:gotoForgot={handleGotoForgot} />
        {:else if currentView === 'register'}
            <RegisterCard on:gotoLogin={handleGotoLogin} />
        {:else if currentView === 'forgot-password'}
            <ForgotPasswordCard on:gotoLogin={handleGotoLoginSimple} />
        {/if}
    </AuthPageFrame>
{/if}
