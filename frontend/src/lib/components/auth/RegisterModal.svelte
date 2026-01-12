<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {api} from '$lib/api';

    const dispatch = createEventDispatcher<{
        gotoLogin: { message?: string };
    }>();

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
        if (password.length < 8) {
            passwordError = $_('auth.validation.passwordMinLength');
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
            await api.post('/auth/register', {username, email, password});
            // Success - go back to login with message
            dispatch('gotoLogin', {message: $_('auth.accountCreated')});
        } catch (e: any) {
            // Handle specific error messages from backend
            const detail = e.data?.detail;
            if (typeof detail === 'string') {
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

<div class="w-full max-w-lg bg-libre-beige rounded-2xl shadow-2xl overflow-hidden flex flex-col font-sans">

    <!-- Header Section (Dark Green) -->
    <div class="bg-libre-green p-8 flex flex-col items-center justify-center space-y-2">
        <div class="flex items-center space-x-3 text-white">
            <img alt="LibreFolio" class="h-10 w-auto" src="/logo.png"/>
            <span class="text-2xl font-bold tracking-wide">LibreFolio</span>
        </div>
        <span class="text-white/80 text-sm">{$_('auth.registerTitle')}</span>
    </div>

    <!-- Body Section -->
    <div class="p-8 pt-6">
        <form class="space-y-4" on:submit|preventDefault={handleSubmit}>

            <!-- General Error Message -->
            {#if error}
                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded-lg text-sm">
                    {error}
                </div>
            {/if}

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
                        disabled={loading}
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
                        disabled={loading}
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
                <input
                        autocomplete="new-password"
                        bind:value={password}
                        class="w-full px-4 py-3 rounded-lg border bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:ring-1 transition-all disabled:opacity-50"
                        class:border-gray-400={!passwordError}
                        class:border-red-400={passwordError}
                        class:focus:border-libre-green={!passwordError}
                        class:focus:border-red-400={passwordError}
                        class:focus:ring-libre-green={!passwordError}
                        class:focus:ring-red-400={passwordError}
                        disabled={loading}
                        on:blur={validatePassword}
                        placeholder={$_('auth.password')}
                        type="password"
                />
                {#if passwordError}
                    <p class="text-red-600 text-xs mt-1">{passwordError}</p>
                {/if}
            </div>

            <!-- Confirm Password Input -->
            <div>
                <input
                        autocomplete="new-password"
                        bind:value={confirmPassword}
                        class="w-full px-4 py-3 rounded-lg border bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:ring-1 transition-all disabled:opacity-50"
                        class:border-gray-400={!confirmPasswordError}
                        class:border-red-400={confirmPasswordError}
                        class:focus:border-libre-green={!confirmPasswordError}
                        class:focus:border-red-400={confirmPasswordError}
                        class:focus:ring-libre-green={!confirmPasswordError}
                        class:focus:ring-red-400={confirmPasswordError}
                        disabled={loading}
                        on:blur={validateConfirmPassword}
                        placeholder={$_('auth.confirmPassword')}
                        type="password"
                />
                {#if confirmPasswordError}
                    <p class="text-red-600 text-xs mt-1">{confirmPasswordError}</p>
                {/if}
            </div>

            <!-- Register Button -->
            <button
                    class="w-full bg-libre-green text-white font-bold py-3 rounded-lg shadow-md hover:bg-opacity-90 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed mt-2"
                    disabled={loading}
                    type="submit"
            >
                {#if loading}
                    {$_('common.loading')}
                {:else}
                    {$_('auth.register')}
                {/if}
            </button>

            <!-- Login Link -->
            <div class="text-center pt-2 text-xs text-gray-600">
                <span>{$_('auth.hasAccount')} </span>
                <button
                        class="font-bold text-libre-dark hover:underline"
                        on:click={() => dispatch('gotoLogin', {})}
                        type="button"
                >
                    {$_('auth.loginHere')}
                </button>
            </div>

        </form>
    </div>
</div>

