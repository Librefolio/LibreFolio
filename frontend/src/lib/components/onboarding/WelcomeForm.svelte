<script lang="ts">
    import {availableLanguages} from '$lib/stores/app/language';
    import SettingCurrency from '$lib/components/settings/SettingCurrency.svelte';
    import SettingSelect from '$lib/components/settings/SettingSelect.svelte';
    import {LogOut} from 'lucide-svelte';
    import type {SelectOption} from '$lib/components/ui/select';
    import type {WelcomeCopy, WelcomeDraft} from '$lib/features/onboarding/welcome';

    interface Props {
        copy: WelcomeCopy;
        initials: string;
        language?: string;
        baseCurrency?: string;
        avatarUrl?: string | null;
        busy?: boolean;
        error?: string | null;
        onavatarrequest?: () => void;
        onavatarclear?: () => void;
        onlanguagechange?: (language: string) => void;
        onskip?: () => void;
        onsubmit?: (draft: WelcomeDraft) => void;
    }

    let {copy, initials, language = $bindable('en'), baseCurrency = $bindable('EUR'), avatarUrl = $bindable(null), busy = false, error = null, onavatarrequest, onavatarclear, onlanguagechange, onskip, onsubmit}: Props = $props();

    const languageOptions: SelectOption[] = availableLanguages.map((item) => ({
        value: item.code,
        label: item.name,
        icon: item.flag,
    }));

    function submit(event: SubmitEvent) {
        event.preventDefault();
        onsubmit?.({language, baseCurrency, avatarUrl});
    }
</script>

<form class="space-y-6" onsubmit={submit} aria-busy={busy} data-busy={busy ? 'true' : 'false'} data-testid="welcome-form">
    {#if error}
        <div class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200" role="alert" data-testid="welcome-error">
            {error}
        </div>
    {/if}

    <section class="rounded-2xl border border-gray-200 p-4 dark:border-slate-700" aria-labelledby="welcome-avatar-label">
        <div class="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div class="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full bg-libre-green text-xl font-semibold text-white" data-testid="welcome-avatar-preview">
                {#if avatarUrl}
                    <img src={avatarUrl} alt={copy.avatarAlt} class="h-full w-full object-cover" />
                {:else}
                    <span aria-hidden="true">{initials}</span>
                    <span class="sr-only">{copy.avatarAlt}</span>
                {/if}
            </div>
            <div class="min-w-0 flex-1">
                <h2 id="welcome-avatar-label" class="text-sm font-semibold text-gray-800 dark:text-gray-100">
                    {copy.avatarLabel}
                </h2>
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {copy.avatarHint}
                </p>
                <div class="mt-3 flex flex-wrap gap-2">
                    <button
                        type="button"
                        class="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:opacity-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-700"
                        disabled={busy}
                        onclick={onavatarrequest}
                        data-testid="welcome-avatar-choose"
                    >
                        {copy.chooseAvatar}
                    </button>
                    {#if avatarUrl}
                        <button
                            type="button"
                            class="rounded-lg px-3 py-2 text-sm text-red-600 hover:bg-red-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-600 disabled:opacity-50 dark:text-red-300 dark:hover:bg-red-950/30"
                            disabled={busy}
                            onclick={onavatarclear}
                            data-testid="welcome-avatar-clear"
                        >
                            {copy.removeAvatar}
                        </button>
                    {/if}
                </div>
            </div>
        </div>
    </section>

    <section class="space-y-1 rounded-2xl border border-gray-200 p-4 dark:border-slate-700" data-testid="welcome-preferences">
        <div data-testid="welcome-language">
            <SettingSelect bind:value={language} options={languageOptions} label={copy.languageLabel} hint={copy.languageHint} isLocked={busy} embedded={true} onchange={onlanguagechange} />
        </div>
        <SettingCurrency bind:value={baseCurrency} label={copy.currencyLabel} hint={copy.currencyHint} isLocked={busy} testId="welcome-currency" embedded={true} />
        <p class="pt-3 text-xs text-gray-500 dark:text-gray-400" data-testid="welcome-theme-hint">
            {copy.themeHint}
        </p>
    </section>

    <div class="flex items-center justify-between gap-3">
        <button
            type="button"
            class="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:opacity-50 dark:text-gray-300 dark:hover:bg-slate-800"
            disabled={busy}
            onclick={onskip}
            data-testid="welcome-skip"
        >
            <LogOut size={16} />
            {copy.skip}
        </button>
        <button
            type="submit"
            class="rounded-lg bg-libre-green px-5 py-2.5 text-sm font-medium text-white hover:bg-libre-green/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:cursor-not-allowed disabled:opacity-50"
            disabled={busy}
            data-testid="welcome-continue"
        >
            {copy.continue}
        </button>
    </div>
</form>
