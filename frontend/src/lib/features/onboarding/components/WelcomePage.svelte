<script lang="ts">
    import ImagePickerWrapper from '$lib/components/ui/media/ImagePickerWrapper.svelte';
    import type {WelcomeCopy, WelcomeDraft} from '$lib/features/onboarding/welcome';
    import WelcomeForm from './WelcomeForm.svelte';
    import LegalNotice from '$lib/features/legal/LegalNotice.svelte';

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

<div class="min-h-full bg-lf-page px-4 py-6 text-lf-primary sm:px-6 sm:py-10" data-testid="welcome-page" data-outcome={outcome ?? 'pending'}>
    <div class="mx-auto max-w-3xl">
        <header class="mb-6 flex items-center justify-between gap-4">
            <span class="flex items-center gap-2 text-lg font-bold text-lf-link">
                <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-lf-logo p-1 shadow-sm ring-1 ring-lf-subtle">
                    <img src="/logo.png" alt="" class="h-full w-full object-contain" />
                </span>
                {copy.productName}
            </span>
            <button type="button" class="rounded-lg px-3 py-2 text-sm text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus" onclick={onlogout} data-testid="welcome-logout">
                {copy.logout}
            </button>
        </header>

        <section class="rounded-3xl border border-lf-subtle bg-lf-card p-5 shadow-xl shadow-lf-shadow-card sm:p-8">
            <h1 class="text-2xl font-bold text-lf-primary sm:text-3xl">
                {copy.title}
            </h1>
            <p class="mt-2 text-lf-secondary">{copy.description}</p>
            <p class="mt-1 text-sm text-lf-muted">
                {copy.defaultsHint}
            </p>

            {#if outcome}
                <div class="mt-6 rounded-xl border border-lf-success-line bg-lf-success-soft p-4 text-sm text-lf-success-on-soft" role="status" data-testid="welcome-outcome">
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

        <!-- The legal notice of the instance (F09): under the card, before and after the welcome -->
        <div class="mt-4 px-1">
            <LegalNotice />
        </div>
    </div>
</div>

<ImagePickerWrapper bind:open={avatarPickerOpen} preset="avatar" title={copy.chooseAvatar} initialUrl={avatarUrl ?? ''} circularPreview={true} onchange={(url) => (avatarUrl = url || null)} />
