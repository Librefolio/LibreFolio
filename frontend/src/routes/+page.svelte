<script lang="ts">
    import {onMount} from 'svelte';
    import {browser} from '$app/environment';
    import {goto} from '$app/navigation';
    import AnimatedBackground from '$lib/components/AnimatedBackground.svelte';
    import LoginModal from '$lib/components/auth/LoginModal.svelte';
    import RegisterModal from '$lib/components/auth/RegisterModal.svelte';
    import ForgotPasswordModal from '$lib/components/auth/ForgotPasswordModal.svelte';
    import LanguageSelector from '$lib/components/LanguageSelector.svelte';
    import ThemeToggle from '$lib/components/ui/ThemeToggle.svelte';
    import {auth} from '$lib/stores/auth';
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

    function handleGotoLogin(event: CustomEvent<{ message?: string }>) {
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

<AnimatedBackground/>

{#if checkingAuth}
    <!-- Loading while checking authentication -->
    <div class="min-h-screen flex items-center justify-center">
        <div class="text-libre-green text-xl">Loading...</div>
    </div>
{:else}
    <div class="min-h-screen flex items-center justify-center p-4">
        <!-- Language & Theme Selector (top right) -->
        <div class="fixed top-4 right-4 z-50 flex items-center space-x-2">
            <LanguageSelector variant="dropdown"/>
            <ThemeToggle />
        </div>

        <!-- Modal Container - Cambio istantaneo senza transizione -->
        {#if currentView === 'login'}
            <LoginModal
                    {redirectTo}
                    {successMessage}
                    on:gotoRegister={handleGotoRegister}
                    on:gotoForgot={handleGotoForgot}
            />
        {:else if currentView === 'register'}
            <RegisterModal
                    on:gotoLogin={handleGotoLogin}
            />
        {:else if currentView === 'forgot-password'}
            <ForgotPasswordModal
                    on:gotoLogin={handleGotoLoginSimple}
            />
        {/if}
    </div>
{/if}
