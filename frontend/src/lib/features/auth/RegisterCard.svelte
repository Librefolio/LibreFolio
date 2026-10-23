<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {Lock, Mail, User} from 'lucide-svelte';
    import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
    import PasswordStrength from '$lib/components/ui/input/PasswordStrength.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';
    import {minutesUntil} from '$lib/features/email/emailText';
    import {describeRegistrationError} from './registrationErrors';

    type _DispatchEvents = {
        gotoLogin: {message?: string; tone?: 'warning'};
    };
    const dispatch = createEventDispatcher();

    /** The token of an invitation link (the `/invite` page): sent with the form, it sets the role of the account. */
    export let inviteToken: string | null = null;
    /** The address the administrator wrote on the invitation: a suggestion, the field stays editable. */
    export let initialEmail = '';
    /** The invitation creates an administrator. */
    export let grantsAdmin = false;

    let username = '';
    let email = initialEmail;
    let password = '';
    let confirmPassword = '';
    let error = '';
    let loading = false;

    // Validation states
    let usernameError = '';
    let emailError = '';
    let passwordError = '';
    let confirmPasswordError = '';

    // The rules are the app's own, read from PasswordStrength (`bind:valid`, decision 37): this card keeps no copy of them.
    let passwordRulesMet = false;

    function validateUsername() {
        if (username.length < 3) {
            usernameError = $_('auth.validation.usernameMinLength');
            return false;
        }
        // The sign-in reads a name with @ as an email address: the server refuses it (A-21a)
        if (username.includes('@')) {
            usernameError = $_('auth.validation.usernameNoAt');
            return false;
        }
        usernameError = '';
        return true;
    }

    function validateEmail() {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            emailError = $_('auth.validation.invalidEmail');
            return false;
        }
        emailError = '';
        return true;
    }

    function validatePassword() {
        // Check all password rules
        const allPassed = passwordRulesMet;
        if (!allPassed) {
            passwordError = $_('auth.validation.passwordTooWeak');
            return false;
        }
        passwordError = '';
        return true;
    }

    function validateConfirmPassword() {
        if (password !== confirmPassword) {
            confirmPasswordError = $_('auth.validation.passwordsNoMatch');
            return false;
        }
        confirmPasswordError = '';
        return true;
    }

    async function handleSubmit() {
        error = '';

        // Strip leading/trailing whitespace (mobile keyboards often add trailing spaces)
        username = username.trim();
        email = email.trim();

        // Run all validations
        const isUsernameValid = validateUsername();
        const isEmailValid = validateEmail();
        const isPasswordValid = validatePassword();
        const isConfirmValid = validateConfirmPassword();

        if (!isUsernameValid || !isEmailValid || !isPasswordValid || !isConfirmValid) {
            return;
        }

        loading = true;
        try {
            const answer = await zodiosApi.register_api_v1_auth_register_post(inviteToken ? {username, email, password, invite_token: inviteToken} : {username, email, password});
            // Success - go back to login with message
            // An account waiting for its email verification (workstream E) is told to open the link first, or, when its
            // email was held (lot E-26), to sign in and ask for a new one; a server without the field means «sending»
            // and the held case is a warning, not a success
            const held = answer.verification_required && answer.verification_email === 'held';
            const retryAfter = answer.verification_retry_after_seconds;
            // and how long until it fits again: the server's time (the longest of the counters that stopped it), in minutes
            const message = !answer.verification_required ? $_('auth.accountCreated') : held ? $_('email.verification.registeredHeld', {values: {minutes: minutesUntil(typeof retryAfter === 'number' ? retryAfter : null)}}) : $_('email.verification.registered');
            dispatch('gotoLogin', held ? {message, tone: 'warning'} : {message});
        } catch (e: unknown) {
            const described = describeRegistrationError(e);
            error = 'key' in described ? $_(described.key) : described.raw;
        } finally {
            loading = false;
        }
    }
</script>

<div class="w-full max-w-lg bg-lf-card text-lf-primary border border-lf-raised rounded-2xl shadow-2xl shadow-lf-shadow overflow-hidden flex flex-col font-sans" data-testid="register-modal">
    <!-- Header Section (brand green); no subtitle: the Register button says it (designer, round 1) -->
    <div class="bg-lf-brand p-8 flex flex-col items-center justify-center space-y-2">
        <div class="flex items-center space-x-3 text-lf-on-brand">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center p-1 bg-lf-logo">
                <img alt="LibreFolio" class="max-w-full max-h-full object-contain" src="/logo.png" />
            </div>
            <span class="text-2xl font-bold tracking-wide">LibreFolio</span>
        </div>
    </div>

    <!-- Body Section -->
    <div class="p-8 pt-6">
        <form class="space-y-4" data-testid="register-form" on:submit|preventDefault={handleSubmit}>
            <!-- General Error Message -->
            <InfoBanner dismissible message={error} ondismiss={() => (error = '')} variant="error" />

            {#if inviteToken}
                <div data-testid="register-invite-notice">
                    <InfoBanner message={$_('auth.invite.notice')} variant="info" />
                </div>
                {#if grantsAdmin}
                    <div data-testid="register-invite-admin-notice">
                        <InfoBanner message={$_('auth.invite.adminNotice')} variant="warning" />
                    </div>
                {/if}
            {/if}

            <!-- Username Input -->
            <div>
                <label class="sr-only" for="register-username">{$_('auth.username')}</label>
                <div class="relative group">
                    <User aria-hidden="true" class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-lf-muted group-focus-within:text-lf-primary transition-colors" data-testid="register-username-icon" size={20} />
                    <input
                        autocapitalize="none"
                        autocomplete="username"
                        bind:value={username}
                        class="w-full pl-12 pr-4 py-3 rounded-lg border bg-lf-field text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:ring-1 transition-all disabled:opacity-50"
                        class:border-lf-input={!usernameError}
                        class:border-lf-danger={usernameError}
                        class:hover:border-lf-input-hover={!usernameError}
                        class:focus:border-lf-focus={!usernameError}
                        class:focus:border-lf-danger={usernameError}
                        class:focus:ring-lf-focus={!usernameError}
                        class:focus:ring-lf-danger={usernameError}
                        data-testid="register-username"
                        disabled={loading}
                        id="register-username"
                        name="username"
                        on:blur={validateUsername}
                        placeholder={$_('auth.username')}
                        spellcheck="false"
                        type="text"
                    />
                </div>
                {#if usernameError}
                    <p class="text-lf-danger text-xs mt-1">{usernameError}</p>
                {/if}
            </div>

            <!-- Email Input -->
            <div>
                <label class="sr-only" for="register-email">{$_('auth.email')}</label>
                <div class="relative group">
                    <Mail aria-hidden="true" class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-lf-muted group-focus-within:text-lf-primary transition-colors" data-testid="register-email-icon" size={20} />
                    <input
                        autocomplete="email"
                        bind:value={email}
                        class="w-full pl-12 pr-4 py-3 rounded-lg border bg-lf-field text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:ring-1 transition-all disabled:opacity-50"
                        class:border-lf-input={!emailError}
                        class:border-lf-danger={emailError}
                        class:hover:border-lf-input-hover={!emailError}
                        class:focus:border-lf-focus={!emailError}
                        class:focus:border-lf-danger={emailError}
                        class:focus:ring-lf-focus={!emailError}
                        class:focus:ring-lf-danger={emailError}
                        data-testid="register-email"
                        disabled={loading}
                        id="register-email"
                        name="email"
                        on:blur={validateEmail}
                        placeholder={$_('auth.email')}
                        type="email"
                    />
                </div>
                {#if emailError}
                    <p class="text-lf-danger text-xs mt-1">{emailError}</p>
                {/if}
            </div>

            <!-- Password Input -->
            <div>
                <label class="sr-only" for="register-password">{$_('auth.password')}</label>
                <PasswordInput autocomplete="new-password" bind:value={password} disabled={loading} hasError={!!passwordError} icon={Lock} id="register-password" name="new-password" on:blur={validatePassword} placeholder={$_('auth.password')} testId="register-password" />
                <PasswordStrength {password} bind:valid={passwordRulesMet} />
                {#if passwordError}
                    <p class="text-lf-danger text-xs mt-1">{passwordError}</p>
                {/if}
            </div>

            <!-- Confirm Password Input -->
            <div>
                <label class="sr-only" for="register-confirm-password">{$_('auth.confirmPassword')}</label>
                <PasswordInput
                    autocomplete="new-password"
                    bind:value={confirmPassword}
                    disabled={loading}
                    hasError={!!confirmPasswordError}
                    icon={Lock}
                    id="register-confirm-password"
                    name="confirm-password"
                    on:blur={validateConfirmPassword}
                    placeholder={$_('auth.confirmPassword')}
                    testId="register-confirm-password"
                />
                {#if confirmPasswordError}
                    <p class="text-lf-danger text-xs mt-1">{confirmPasswordError}</p>
                {/if}
            </div>

            <!-- Register Button -->
            <button class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed mt-2" data-testid="register-submit" disabled={loading} type="submit">
                {#if loading}
                    {$_('common.loading')}
                {:else}
                    {$_('auth.register')}
                {/if}
            </button>

            <!-- Login Link -->
            <div class="text-center pt-2 text-xs text-lf-secondary">
                <span>{$_('auth.hasAccount')} </span>
                <button class="font-bold text-lf-link hover:underline" data-testid="goto-login" on:click={() => dispatch('gotoLogin', {})} type="button">
                    {$_('auth.loginHere')}
                </button>
            </div>
        </form>
    </div>
</div>
