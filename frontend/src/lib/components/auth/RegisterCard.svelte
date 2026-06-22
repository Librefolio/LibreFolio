<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {zodiosApi} from '$lib/api';
    import {isAxiosError} from 'axios';
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
                if (detail.includes('username')) {
                    error = $_('auth.validation.usernameTaken');
                } else if (detail.includes('email')) {
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

<div class="w-full max-w-lg bg-libre-beige rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans" data-testid="register-modal">
    <!-- Header Section (Dark Green) -->
    <div class="bg-libre-green p-8 flex flex-col items-center justify-center space-y-2">
        <div class="flex items-center space-x-3 text-white">
            <div class="w-10 h-10 rounded-lg flex items-center justify-center p-1" style="background:#fff">
                <img alt="LibreFolio" class="max-w-full max-h-full object-contain" src="/logo.png" />
            </div>
            <span class="text-2xl font-bold tracking-wide">LibreFolio</span>
        </div>
        <span class="text-white/80 text-sm">{$_('auth.registerTitle')}</span>
    </div>

    <!-- Body Section -->
    <div class="p-8 pt-6">
        <form class="space-y-4" data-testid="register-form" on:submit|preventDefault={handleSubmit}>
            <!-- General Error Message -->
            <InfoBanner dismissible message={error} ondismiss={() => (error = '')} variant="error" />

            <!-- Username Input -->
            <div>
                <input
                    autocomplete="username"
                    bind:value={username}
                    class="w-full px-4 py-3 rounded-lg border bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:ring-1 transition-all disabled:opacity-50"
                    class:border-gray-400={!usernameError}
                    class:border-red-400={usernameError}
                    class:focus:border-libre-green={!usernameError}
                    class:focus:border-red-400={usernameError}
                    class:focus:ring-libre-green={!usernameError}
                    class:focus:ring-red-400={usernameError}
                    data-testid="register-username"
                    disabled={loading}
                    id="register-username"
                    on:blur={validateUsername}
                    placeholder={$_('auth.username')}
                    type="text"
                />
                {#if usernameError}
                    <p class="text-red-600 text-xs mt-1">{usernameError}</p>
                {/if}
            </div>

            <!-- Email Input -->
            <div>
                <input
                    autocomplete="email"
                    bind:value={email}
                    class="w-full px-4 py-3 rounded-lg border bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:ring-1 transition-all disabled:opacity-50"
                    class:border-gray-400={!emailError}
                    class:border-red-400={emailError}
                    class:focus:border-libre-green={!emailError}
                    class:focus:border-red-400={emailError}
                    class:focus:ring-libre-green={!emailError}
                    class:focus:ring-red-400={emailError}
                    data-testid="register-email"
                    disabled={loading}
                    id="register-email"
                    on:blur={validateEmail}
                    placeholder={$_('auth.email')}
                    type="email"
                />
                {#if emailError}
                    <p class="text-red-600 text-xs mt-1">{emailError}</p>
                {/if}
            </div>

            <!-- Password Input -->
            <div>
                <PasswordInput autocomplete="new-password" bind:value={password} disabled={loading} hasError={!!passwordError} on:blur={validatePassword} placeholder={$_('auth.password')} testId="register-password" />
                <PasswordStrength {password} />
                {#if passwordError}
                    <p class="text-red-600 text-xs mt-1">{passwordError}</p>
                {/if}
            </div>

            <!-- Confirm Password Input -->
            <div>
                <PasswordInput autocomplete="new-password" bind:value={confirmPassword} disabled={loading} hasError={!!confirmPasswordError} on:blur={validateConfirmPassword} placeholder={$_('auth.confirmPassword')} testId="register-confirm-password" />
                {#if confirmPasswordError}
                    <p class="text-red-600 text-xs mt-1">{confirmPasswordError}</p>
                {/if}
            </div>

            <!-- Register Button -->
            <button class="w-full bg-libre-green text-white font-bold py-3 rounded-lg shadow-md hover:bg-opacity-90 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed mt-2" data-testid="register-submit" disabled={loading} type="submit">
                {#if loading}
                    {$_('common.loading')}
                {:else}
                    {$_('auth.register')}
                {/if}
            </button>

            <!-- Login Link -->
            <div class="text-center pt-2 text-xs text-gray-600">
                <span>{$_('auth.hasAccount')} </span>
                <button class="font-bold text-libre-dark hover:underline" data-testid="goto-login" on:click={() => dispatch('gotoLogin', {})} type="button">
                    {$_('auth.loginHere')}
                </button>
            </div>
        </form>
    </div>
</div>
