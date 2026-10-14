<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {isAxiosError} from 'axios';
    import {Lock, Mail, User} from 'lucide-svelte';
    import PasswordInput from '$lib/components/ui/input/PasswordInput.svelte';
    import PasswordStrength from '$lib/components/ui/input/PasswordStrength.svelte';
    import InfoBanner from '$lib/components/ui/feedback/InfoBanner.svelte';

    type _DispatchEvents = {
        gotoLogin: {message?: string};
    };
    const dispatch = createEventDispatcher();

    let username = '';
    let email = '';
    let password = '';
    let confirmPassword = '';
    let error = '';
    let loading = false;

    // Validation states
    let usernameError = '';
    let emailError = '';
    let passwordError = '';
    let confirmPasswordError = '';

    // Password rules for validation
    const passwordRules = {
        minLength: (pwd: string) => pwd.length >= 8,
        hasUppercase: (pwd: string) => /[A-Z]/.test(pwd),
        hasLowercase: (pwd: string) => /[a-z]/.test(pwd),
        hasNumber: (pwd: string) => /\d/.test(pwd),
        hasSpecial: (pwd: string) => /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/`~;']/.test(pwd),
    };

    function validateUsername() {
        if (username.length < 3) {
            usernameError = $_('auth.validation.usernameMinLength');
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
        const allPassed = Object.values(passwordRules).every((check) => check(password));
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
            await zodiosApi.register_api_v1_auth_register_post({username, email, password});
            // Success - go back to login with message
            dispatch('gotoLogin', {message: $_('auth.accountCreated')});
        } catch (e: unknown) {
            // Handle specific error messages from backend
            const detail = isAxiosError(e) ? e.response?.data?.detail : null;
            if (Array.isArray(detail)) {
                // Pydantic validation errors
                const firstError = detail[0];
                if (firstError?.loc?.includes('email')) {
                    if (firstError.msg?.includes('special-use') || firstError.msg?.includes('reserved')) {
                        error = $_('auth.validation.invalidEmailDomain');
                    } else {
                        error = $_('auth.validation.invalidEmail');
                    }
                } else if (firstError?.loc?.includes('username')) {
                    error = $_('auth.validation.usernameMinLength');
                } else if (firstError?.loc?.includes('password')) {
                    error = $_('auth.validation.passwordTooWeak');
                } else {
                    error = $_('auth.registrationFailed');
                }
            } else if (typeof detail === 'string') {
                // Case-folded, and that is the whole fix: the backend answers
                // "Username already taken" and "Email already registered", with
                // capitals, so `includes('username')` never matched and every
                // 400 fell through to `error = detail`. The two keys below were
                // therefore unreachable — eight translated strings, four
                // languages by two keys, that nobody could ever read — and a
                // user in Italian, French or Spanish got raw English instead.
                const lowered = detail.toLowerCase();
                if (lowered.includes('registration is disabled')) {
                    // The administrator has closed sign-ups (`auth.py:191`). It
                    // is the one string of the three that is not about the values
                    // the user typed, so it gets its own wording rather than the
                    // generic failure.
                    error = $_('auth.registrationDisabled');
                } else if (lowered.includes('username')) {
                    error = $_('auth.validation.usernameTaken');
                } else if (lowered.includes('email')) {
                    error = $_('auth.validation.emailTaken');
                } else {
                    error = detail;
                }
            } else {
                error = $_('auth.registrationFailed');
            }
        } finally {
            loading = false;
        }
    }
</script>

<div class="w-full max-w-lg bg-lf-card text-lf-primary border border-lf-subtle rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans" data-testid="register-modal">
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
                <PasswordStrength {password} />
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
