<script lang="ts">
    import {createEventDispatcher, onMount} from 'svelte';
    import {_} from '$lib/i18n';
    import {auth, authError, isAuthLoading} from '$lib/stores/app/auth';
    import {instanceConfig} from '$lib/features/instance/instanceConfig.svelte';
    import {goto} from '$app/navigation';
    import {Lock, User} from 'lucide-svelte';
    import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
    import VerificationNotice from '$lib/features/email/VerificationNotice.svelte';

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

    // The public configuration of the instance: whether anyone may register decides the register link below.
    onMount(() => {
        void instanceConfig.load();
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

<div class="w-full max-w-lg bg-lf-card text-lf-primary border border-lf-raised rounded-2xl shadow-2xl shadow-lf-shadow overflow-hidden flex flex-col font-sans" data-testid="login-modal">
    <!-- Header Section (brand green) -->
    <div class="bg-lf-brand p-8 flex flex-col items-center justify-center space-y-3">
        <div class="flex items-center space-x-3 text-lf-on-brand">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center p-1 bg-lf-logo">
                <img alt="LibreFolio" class="max-w-full max-h-full object-contain" src="/logo.png" />
            </div>
            <span class="text-2xl font-bold tracking-wide">LibreFolio</span>
        </div>
    </div>

    <!-- Body Section -->
    <div class="p-8 pt-10">
        <form class="space-y-5" data-testid="login-form" on:submit|preventDefault={handleSubmit}>
            <!-- Success Message (from registration) -->
            {#if successMessage}
                <div class="bg-lf-success-soft border border-lf-success-line text-lf-success-on-soft px-4 py-2 rounded-lg text-sm" data-testid="login-success">
                    {successMessage}
                </div>
            {/if}

            <!-- Error Message -->
            {#if $authError?.key === 'email.verification.loginRequired'}
                <!-- An account waiting for its email verification (workstream E): «send the link again» with these credentials -->
                <VerificationNotice {password} {username} />
            {:else if $authError}
                <div class="bg-lf-danger-soft border border-lf-danger-line text-lf-danger-on-soft px-4 py-2 rounded-lg text-sm" data-testid="login-error">
                    {$_($authError.key)}
                </div>
            {/if}

            <!-- Username Input -->
            <div class="relative group">
                <label class="sr-only" for="login-username">{$_('auth.usernameOrEmail')}</label>
                <User aria-hidden="true" class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-lf-muted group-focus-within:text-lf-primary transition-colors" data-testid="login-username-icon" size={20} />
                <input
                    autocapitalize="none"
                    autocomplete="username"
                    bind:value={username}
                    class="w-full pl-12 pr-4 py-3 rounded-lg border border-lf-input hover:border-lf-input-hover bg-lf-field text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:border-lf-focus focus:ring-1 focus:ring-lf-focus transition-all disabled:opacity-50"
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
                <PasswordInput autocomplete="current-password" bind:value={password} disabled={$isAuthLoading} icon={Lock} id="login-password" name="password" placeholder={$_('auth.password')} testId="login-password" />
            </div>

            <!-- Forgot Password Link -->
            <div class="flex justify-end">
                <button class="text-xs font-semibold text-lf-link hover:text-lf-primary underline decoration-1 underline-offset-2" data-testid="goto-forgot" on:click={() => dispatch('gotoForgot')} type="button">
                    {$_('auth.forgotPassword')}
                </button>
            </div>

            <!-- Login Button -->
            <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed" data-testid="login-submit" disabled={$isAuthLoading} type="submit">
                {#if $isAuthLoading}
                    {$_('common.loading')}
                {:else}
                    {$_('auth.login')}
                {/if}
            </button>

            <!-- Register Link: while anyone may register, or while the instance has no account (its first account can be
                 created in any mode, decision 36); until the instance answers, its default (open) keeps it -->
            {#if instanceConfig.config.accounts.registration_mode === 'open' || instanceConfig.config.accounts.first_account_open === true}
                <div class="text-center pt-2 text-xs text-lf-secondary">
                    <span>{$_('auth.noAccount')} </span>
                    <button class="font-bold text-lf-link hover:underline" data-testid="goto-register" on:click={() => dispatch('gotoRegister')} type="button">
                        {$_('auth.registerHere')}
                    </button>
                </div>
            {/if}
        </form>
    </div>
</div>
