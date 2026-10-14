<script lang="ts">
    import ImagePickerWrapper from '$lib/components/ui/media/ImagePickerWrapper.svelte';
    import type {WelcomeCopy, WelcomeDraft} from '$lib/features/onboarding/welcome';
    import WelcomeForm from './WelcomeForm.svelte';

    interface Props {
        copy: WelcomeCopy;
        username: string;
        language?: string;
        baseCurrency?: string;
        avatarUrl?: string | null;
        outcome?: 'completed' | 'skipped' | null;
        oncomplete: (draft: WelcomeDraft) => Promise<void>;
        onskip: () => Promise<void>;
        onlanguagechange?: (language: string) => void;
        onlogout: () => Promise<void> | void;
    }

    let {copy, username, language = $bindable('en'), baseCurrency = $bindable('EUR'), avatarUrl = $bindable(null), outcome = null, oncomplete, onskip, onlanguagechange, onlogout}: Props = $props();

    let busy = $state(false);
    let error = $state<string | null>(null);
    let avatarPickerOpen = $state(false);
    let initials = $derived(
        username
            .split(/\s+/)
            .filter(Boolean)
            .map((part) => part[0])
            .join('')
            .slice(0, 2)
            .toUpperCase() || '?',
    );

    async function run(action: () => Promise<void>) {
        busy = true;
        error = null;
        try {
            await action();
        } catch (actionError) {
            error = actionError instanceof Error ? actionError.message : 'Onboarding action failed';
        } finally {
            busy = false;
        }
    }
</script>

<div class="min-h-full bg-libre-beige px-4 py-6 dark:bg-slate-950 sm:px-6 sm:py-10" data-testid="welcome-page" data-outcome={outcome ?? 'pending'}>
    <div class="mx-auto max-w-3xl">
        <header class="mb-6 flex items-center justify-between gap-4">
            <span class="flex items-center gap-2 text-lg font-bold text-libre-green dark:text-emerald-300">
                <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-white p-1 shadow-sm ring-1 ring-gray-200 dark:ring-slate-700">
                    <img src="/logo.png" alt="" class="h-full w-full object-contain" />
                </span>
                {copy.productName}
            </span>
            <button type="button" class="rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green dark:text-gray-300 dark:hover:bg-slate-800" onclick={onlogout} data-testid="welcome-logout">
                {copy.logout}
            </button>
        </header>

        <section class="rounded-3xl border border-white/70 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900 sm:p-8">
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white sm:text-3xl">
                {copy.title}
            </h1>
            <p class="mt-2 text-gray-600 dark:text-gray-300">{copy.description}</p>
            <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                {copy.defaultsHint}
            </p>

            {#if outcome}
                <div class="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200" role="status" data-testid="welcome-outcome">
                    {outcome === 'completed' ? copy.completed : copy.skipped}
                </div>
            {:else}
                <div class="mt-8">
                    <WelcomeForm
                        {copy}
                        {initials}
                        bind:language
                        bind:baseCurrency
                        bind:avatarUrl
                        {busy}
                        {error}
                        onavatarrequest={() => (avatarPickerOpen = true)}
                        onavatarclear={() => (avatarUrl = null)}
                        {onlanguagechange}
                        onskip={() => run(onskip)}
                        onsubmit={(draft) => run(() => oncomplete(draft))}
                    />
                </div>
            {/if}
        </section>
    </div>
</div>

<ImagePickerWrapper bind:open={avatarPickerOpen} preset="avatar" title={copy.chooseAvatar} initialUrl={avatarUrl ?? ''} circularPreview={true} onchange={(url) => (avatarUrl = url || null)} />
