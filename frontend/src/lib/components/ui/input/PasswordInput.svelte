<script lang="ts">
    import type {ComponentType} from 'svelte';
    import {Eye, EyeOff} from 'lucide-svelte';
    import {_} from '$lib/i18n';

    type AutoFill = 'current-password' | 'new-password' | 'off' | 'on';

    // Props
    export let value: string = '';
    export let placeholder: string = '';
    export let disabled: boolean = false;
    export let autocomplete: AutoFill = 'current-password';
    export let hasError: boolean = false;
    export let id: string = '';
    export let name: string = '';
    export let testId: string = '';
    /** An icon drawn inside the field on the left, decorative (the lock of the credential forms). */
    export let icon: ComponentType | null = null;
    /**
     * A secret that is not an account's password (the password of a backup): the field is a plain text input drawn
     * masked by CSS, so that the browser and the password managers, which look for `type="password"`, never offer to
     * save it. The eye still shows it. Account fields (login, change of password) keep the real `type="password"`.
     */
    export let neverSaved: boolean = false;

    // Internal state
    let showPassword = false;

    function toggleVisibility() {
        showPassword = !showPassword;
    }
</script>

<div class="relative group">
    {#if icon}
        <svelte:component this={icon} aria-hidden="true" class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-lf-muted group-focus-within:text-lf-primary transition-colors" data-testid={testId ? `${testId}-icon` : undefined} size={20} />
    {/if}
    <input
        autocapitalize="none"
        autocomplete={neverSaved ? 'off' : autocomplete}
        bind:value
        class="w-full px-4 pr-12 py-3 rounded-lg border bg-lf-field text-lf-primary placeholder:text-lf-placeholder focus:outline-none focus:ring-1 transition-all disabled:opacity-50"
        class:pl-12={!!icon}
        class:lf-masked={neverSaved && !showPassword}
        class:border-lf-input={!hasError}
        class:border-lf-danger={hasError}
        class:hover:border-lf-input-hover={!hasError}
        class:focus:border-lf-focus={!hasError}
        class:focus:border-lf-danger={hasError}
        class:focus:ring-lf-focus={!hasError}
        class:focus:ring-lf-danger={hasError}
        data-1p-ignore={neverSaved ? '' : undefined}
        data-bwignore={neverSaved ? 'true' : undefined}
        data-form-type={neverSaved ? 'other' : undefined}
        data-lpignore={neverSaved ? 'true' : undefined}
        data-masked={neverSaved ? (showPassword ? 'false' : 'true') : undefined}
        data-testid={testId || undefined}
        {disabled}
        id={id || undefined}
        name={name || undefined}
        on:blur
        on:input
        on:keydown
        {placeholder}
        spellcheck="false"
        type={showPassword || neverSaved ? 'text' : 'password'}
    />
    <button
        aria-label={$_(showPassword ? 'auth.hidePassword' : 'auth.showPassword')}
        class="absolute right-3 top-1/2 -translate-y-1/2 text-lf-muted hover:text-lf-primary transition-colors p-1"
        {disabled}
        on:click={toggleVisibility}
        title={$_(showPassword ? 'auth.hidePassword' : 'auth.showPassword')}
        type="button"
    >
        {#if showPassword}
            <EyeOff size={20} />
        {:else}
            <Eye size={20} />
        {/if}
    </button>
</div>

<style>
    /* The dots of a masked text field (every supported browser: Chromium, Firefox, Safari). */
    .lf-masked {
        -webkit-text-security: disc;
    }
</style>
