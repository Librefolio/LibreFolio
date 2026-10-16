<script lang="ts">
    import {availableLanguages} from '$lib/stores/app/language';
    import SettingCurrency from '$lib/features/settings/SettingCurrency.svelte';
    import SettingSelect from '$lib/features/settings/SettingSelect.svelte';
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

<form class="space-y-6 text-lf-primary" onsubmit={submit} aria-busy={busy} data-busy={busy ? 'true' : 'false'} data-testid="welcome-form">
    {#if error}
        <div class="rounded-xl border border-lf-danger-line bg-lf-danger-soft px-4 py-3 text-sm text-lf-danger-on-soft" role="alert" data-testid="welcome-error">
            {error}
        </div>
    {/if}

    <section class="rounded-2xl border border-lf-subtle p-4" aria-labelledby="welcome-avatar-label">
        <div class="flex flex-col gap-4 sm:flex-row sm:items-center">
            <div class="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full bg-lf-brand text-xl font-semibold text-lf-on-brand" data-testid="welcome-avatar-preview">
                {#if avatarUrl}
                    <img src={avatarUrl} alt={copy.avatarAlt} class="h-full w-full object-cover" />
                {:else}
                    <span aria-hidden="true">{initials}</span>
                    <span class="sr-only">{copy.avatarAlt}</span>
                {/if}
            </div>
            <div class="min-w-0 flex-1">
                <h2 id="welcome-avatar-label" class="text-sm font-semibold text-lf-primary">
                    {copy.avatarLabel}
                </h2>
                <p class="mt-1 text-xs text-lf-muted">
                    {copy.avatarHint}
                </p>
                <div class="mt-3 flex flex-wrap gap-2">
                    <button
                        type="button"
                        class="rounded-lg border border-lf-input px-3 py-2 text-sm text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:opacity-50"
                        disabled={busy}
                        onclick={onavatarrequest}
                        data-testid="welcome-avatar-choose"
                    >
                        {copy.chooseAvatar}
                    </button>
                    {#if avatarUrl}
                        <button
                            type="button"
                            class="rounded-lg px-3 py-2 text-sm text-lf-danger hover:bg-lf-danger-soft hover:text-lf-danger-on-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-danger disabled:opacity-50"
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

    <section class="space-y-1 rounded-2xl border border-lf-subtle p-4" data-testid="welcome-preferences">
        <div data-testid="welcome-language">
            <SettingSelect bind:value={language} options={languageOptions} label={copy.languageLabel} hint={copy.languageHint} isLocked={busy} embedded={true} onchange={onlanguagechange} />
        </div>
        <SettingCurrency bind:value={baseCurrency} label={copy.currencyLabel} hint={copy.currencyHint} isLocked={busy} testId="welcome-currency" embedded={true} />
        <p class="pt-3 text-xs text-lf-muted" data-testid="welcome-theme-hint">
            {copy.themeHint}
        </p>
    </section>

    <div class="flex items-center justify-between gap-3">
        <button type="button" class="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:opacity-50" disabled={busy} onclick={onskip} data-testid="welcome-skip">
            <LogOut size={16} />
            {copy.skip}
        </button>
        <button
            type="submit"
            class="rounded-lg bg-lf-action px-5 py-2.5 text-sm font-medium text-lf-on-action hover:bg-lf-action-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus disabled:cursor-not-allowed disabled:opacity-50"
            disabled={busy}
            data-testid="welcome-continue"
        >
            {copy.continue}
        </button>
    </div>
</form>
