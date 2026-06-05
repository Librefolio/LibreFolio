<script lang="ts">
    import {onMount} from 'svelte';
    import {browser} from '$app/environment';
    import {goto} from '$app/navigation';
    import AnimatedBackground from '$lib/components/ui/AnimatedBackground.svelte';
    import LoginCard from '$lib/components/auth/LoginCard.svelte';
    import RegisterCard from '$lib/components/auth/RegisterCard.svelte';
    import ForgotPasswordCard from '$lib/components/auth/ForgotPasswordCard.svelte';
    import LanguageSelector from '$lib/components/layout/LanguageSelector.svelte';
    import HelpMenu from '$lib/components/layout/HelpMenu.svelte';
    import ThemeToggle from '$lib/components/ui/ThemeToggle.svelte';
    import {auth} from '$lib/stores/app/auth';
    import {_} from '$lib/i18n';
    import {Coffee} from 'lucide-svelte';
    import {page} from '$app/stores';

    // Auth view state (modals)
    type AuthView = 'login' | 'register' | 'forgot-password';
    let currentView: AuthView = 'login';

    // Success message (from registration)
    let successMessage = '';

    // Loading state while checking auth
    let checkingAuth = true;

    // Get redirect URL from query params (if coming from protected route)
    $: redirectTo = $page.url.searchParams.get('redirect') || '/dashboard';

    // Check if already authenticated and redirect
    onMount(async () => {
        if (browser) {
            const isAuth = await auth.checkAuth();
            if (isAuth) {
                goto('/dashboard');
                return;
            }
        }
        checkingAuth = false;
    });

    // Handle navigation between modals
    function handleGotoRegister() {
        auth.clearError();
        successMessage = '';
        currentView = 'register';
    }

    function handleGotoForgot() {
        auth.clearError();
        successMessage = '';
        currentView = 'forgot-password';
    }

    function handleGotoLogin(event: CustomEvent<{message?: string}>) {
        auth.clearError();
        successMessage = event.detail?.message || '';
        currentView = 'login';
    }

    function handleGotoLoginSimple() {
        auth.clearError();
        successMessage = '';
        currentView = 'login';
    }
</script>

<AnimatedBackground />

{#if checkingAuth}
    <!-- Loading while checking authentication -->
    <div class="min-h-screen flex items-center justify-center" data-testid="auth-loading">
        <div class="text-libre-green text-xl">Loading...</div>
    </div>
{:else}
    <div class="min-h-screen flex items-center justify-center p-4" data-testid="login-page">
        <!-- Language & Theme Selector (top right) -->
        <div class="fixed right-4 z-50 flex items-center space-x-2 safe-top-offset">
            <a href="https://www.buymeacoffee.com/librefolio" target="_blank" rel="noopener noreferrer" class="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-white/20 dark:hover:bg-slate-600 transition-colors text-amber-600 dark:text-amber-400" title={$_('help.buyMeACoffee')}>
                <span class="hidden sm:inline text-sm font-medium leading-5">{$_('help.buyMeACoffee')}</span>
                <Coffee size={20} class="flex-shrink-0" />
            </a>
            <ThemeToggle />
            <LanguageSelector />
            <HelpMenu />
        </div>

        <!-- Card Container - Cambio istantaneo senza transizione -->
        {#if currentView === 'login'}
            <LoginCard {redirectTo} {successMessage} on:gotoRegister={handleGotoRegister} on:gotoForgot={handleGotoForgot} />
        {:else if currentView === 'register'}
            <RegisterCard on:gotoLogin={handleGotoLogin} />
        {:else if currentView === 'forgot-password'}
            <ForgotPasswordCard on:gotoLogin={handleGotoLoginSimple} />
        {/if}
    </div>
{/if}
