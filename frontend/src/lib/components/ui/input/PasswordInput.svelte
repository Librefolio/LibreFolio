<script lang="ts">
    import {Eye, EyeOff} from 'lucide-svelte';

    type AutoFill = 'current-password' | 'new-password' | 'off' | 'on';

    // Props
    export let value: string = '';
    export let placeholder: string = '';
    export let disabled: boolean = false;
    export let autocomplete: AutoFill = 'current-password';
    export let hasError: boolean = false;
    export let id: string = '';
    export let testId: string = '';

    // Internal state
    let showPassword = false;

    function toggleVisibility() {
        showPassword = !showPassword;
    }
</script>

<div class="relative">
    <input
            {id}
            data-testid={testId || undefined}
            type={showPassword ? 'text' : 'password'}
            bind:value
            {placeholder}
            {disabled}
            {autocomplete}
            class="w-full px-4 py-3 pr-12 rounded-lg border bg-transparent text-libre-dark placeholder-gray-500 focus:outline-none focus:ring-1 transition-all disabled:opacity-50"
            class:border-gray-400={!hasError}
            class:border-red-400={hasError}
            class:focus:border-libre-green={!hasError}
            class:focus:border-red-400={hasError}
            class:focus:ring-libre-green={!hasError}
            class:focus:ring-red-400={hasError}
            on:blur
            on:input
            on:keydown
    />
    <button
            type="button"
            tabindex="-1"
            on:click={toggleVisibility}
            class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 transition-colors p-1"
            title={showPassword ? 'Hide password' : 'Show password'}
            {disabled}
    >
        {#if showPassword}
            <EyeOff size={20}/>
        {:else}
            <Eye size={20}/>
        {/if}
    </button>
</div>

