<script lang="ts">
    import {page} from '$app/stores';
    import {_} from 'svelte-i18n';
    import AnimatedBackground from '$lib/components/ui/AnimatedBackground.svelte';
</script>

<AnimatedBackground />

<div class="min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-md bg-lf-card text-lf-primary border border-lf-raised rounded-2xl shadow-2xl shadow-lf-shadow overflow-hidden">
        <!-- Header (brand green) -->
        <div class="bg-lf-brand p-6 flex flex-col items-center justify-center">
            <div class="text-6xl text-lf-on-brand mb-2">
                {$page.status}
            </div>
            <div class="text-lf-on-brand text-lg font-semibold">
                {#if $page.status === 404}
                    {$_('error.pageNotFound')}
                {:else}
                    {$_('error.somethingWentWrong')}
                {/if}
            </div>
        </div>

        <!-- Body -->
        <div class="p-8 text-center">
            <p class="text-lf-secondary mb-6">
                {#if $page.status === 404}
                    {$_('error.pageNotFoundMessage')}
                {:else}
                    {$page.error?.message || $_('error.unexpectedError')}
                {/if}
            </p>

            <div class="flex flex-col space-y-3">
                <a class="w-full bg-lf-action text-lf-on-action font-bold py-3 rounded-lg shadow-md hover:bg-lf-action-hover transition-all text-center" href="/dashboard">
                    {$_('error.goToDashboard')}
                </a>
                <a class="w-full border border-lf-focus text-lf-link font-bold py-3 rounded-lg hover:bg-lf-action hover:text-lf-on-action transition-all text-center" href="/">
                    {$_('error.goToHome')}
                </a>
            </div>
        </div>
    </div>
</div>

<style>
    /* Inherits from app.css - no extra styles needed */
</style>
