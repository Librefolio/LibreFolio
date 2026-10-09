<script lang="ts">
    import {createEventDispatcher, onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {auth, authError, isAuthLoading} from '$lib/stores/app/auth';
    import {globalSettings} from '$lib/stores/app/globalSettings';
    import {goto} from '$app/navigation';
    import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';

    type _DispatchEvents = {
        gotoRegister: void;
        gotoForgot: void;
    };
    const dispatch = createEventDispatcher();

    export let redirectTo = '/dashboard';
    export let successMessage = '';
    export let onAuthenticated: ((requestedPath: string) => Promise<void>) | undefined = undefined;

    let username = '';
    let password = '';

    // Public settings: whether registration is open decides the register link below.
    onMount(() => {
        void globalSettings.load();
    });

    async function handleSubmit() {
        username = username.trim();
        const success = await auth.login(username, password);
        if (success) {
            if (onAuthenticated) {
                await onAuthenticated(redirectTo);
            } else {
                await goto(redirectTo);
            }
        }
    }
</script>

<div class="w-full max-w-lg bg-libre-beige rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans" data-testid="login-modal">
    <!-- Header Section (Dark Green) -->
    <div class="bg-libre-green p-8 flex flex-col items-center justify-center space-y-3">
        <div class="flex items-center space-x-3 text-white">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center p-1" style="background:#fff">
                <img alt="LibreFolio" class="max-w-full max-h-full object-contain" src="/logo.png" />
            </div>
            <span class="text-2xl font-bold tracking-wide">LibreFolio</span>
        </div>
    </div>

    <!-- Body Section (Beige) -->
    <div class="p-8 pt-10">
        <form class="space-y-5" data-testid="login-form" on:submit|preventDefault={handleSubmit}>
            <!-- Success Message (from registration) -->
            {#if successMessage}
                <div class="bg-green-100 border border-green-400 text-green-700 px-4 py-2 rounded-lg text-sm">
                    {successMessage}
                </div>
            {/if}

            <!-- Error Message -->
            {#if $authError}
                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded-lg text-sm" data-testid="login-error">
                    {'key' in $authError ? $_($authError.key) : $authError.message}
                </div>
            {/if}

            <!-- Username Input -->
            <div class="relative">
                <label class="sr-only" for="login-username">{$_('auth.usernameOrEmail')}</label>
                <input
                    autocapitalize="none"
                    autocomplete="username"
                    bind:value={username}
                    class="w-full px-4 py-3 rounded-lg border border-gray-400 bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:border-libre-green focus:ring-1 focus:ring-libre-green transition-all disabled:opacity-50"
                    data-testid="login-username"
                    disabled={$isAuthLoading}
                    id="login-username"
                    name="username"
                    placeholder={$_('auth.usernameOrEmail')}
                    spellcheck="false"
                    type="text"
                />
            </div>

            <!-- Password Input -->
            <div>
                <label class="sr-only" for="login-password">{$_('auth.password')}</label>
                <PasswordInput autocomplete="current-password" bind:value={password} disabled={$isAuthLoading} id="login-password" name="password" placeholder={$_('auth.password')} testId="login-password" />
            </div>

            <!-- Forgot Password Link -->
            <div class="flex justify-end">
                <button class="text-xs font-semibold text-libre-dark hover:text-libre-green underline decoration-1 underline-offset-2" data-testid="goto-forgot" on:click={() => dispatch('gotoForgot')} type="button">
                    {$_('auth.forgotPassword')}
                </button>
            </div>

            <!-- Login Button -->
            <button class="w-full bg-libre-green text-white font-bold py-3 rounded-lg shadow-md hover:bg-opacity-90 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed" data-testid="login-submit" disabled={$isAuthLoading} type="submit">
                {#if $isAuthLoading}
                    {$_('common.loading')}
                {:else}
                    {$_('auth.login')}
                {/if}
            </button>

            <!-- Register Link: hidden only once the instance says registration is closed; unknown keeps it -->
            {#if $globalSettings.enable_registration !== false}
                <div class="text-center pt-2 text-xs text-gray-600">
                    <span>{$_('auth.noAccount')} </span>
                    <button class="font-bold text-libre-dark hover:underline" data-testid="goto-register" on:click={() => dispatch('gotoRegister')} type="button">
                        {$_('auth.registerHere')}
                    </button>
                </div>
            {/if}
        </form>
    </div>
</div>
