<!--
  AssetModalProfileRow — the «Dati del profilo» row of the asset window (plan 68, E8b; the mock «finestra-asset-profilo»).
  It opens the profile window over the asset window; the changes it hands back wait in the asset window and leave with
  «Crea Asset» or «Salva Modifiche».

  The row looks like «Ulteriori Info» and «Assegnazione Provider» above it. It says how many changes wait (a badge,
  `data-count`) and names their voices, in the order it is given (`profileRowSummary`: the catalogue's). A click, Enter
  or Space opens the window; `disabled` (the tour's preview) opens nothing.

  Pattern: Svelte 5 Runes, Tailwind CSS 4, colour roles only.
-->
<script lang="ts">
    import {ExternalLink, IdCard} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';

    interface Props {
        /** What waits: how many changes, and their voices (`profileRowSummary`). */
        summary: {count: number; keys: string[]};
        onopen: () => void;
        disabled?: boolean;
    }

    let {summary, onopen, disabled = false}: Props = $props();

    /** A voice by its label; one the catalogue does not list (a broker file's) by its key. */
    function voiceLabel(key: string): string {
        const label = $t(`assets.profile.voices.${key}`);
        return label === `assets.profile.voices.${key}` ? key : label;
    }

    function open() {
        if (!disabled) onopen();
    }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
    class="flex w-full items-center gap-2 rounded-lg border border-lf-subtle bg-lf-panel px-4 py-2.5 text-sm text-lf-secondary transition-colors select-none {disabled ? 'opacity-60' : 'cursor-pointer hover:bg-lf-neutral'} focus-visible:outline-2 focus-visible:outline-lf-focus"
    role="button"
    tabindex={disabled ? -1 : 0}
    aria-disabled={disabled ? 'true' : undefined}
    data-testid="asset-modal-profile-row"
    data-count={summary.count}
    onclick={open}
    onkeydown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            open();
        }
    }}
>
    <IdCard size={16} class="shrink-0" />
    <span class="shrink-0 font-medium">{$t('assets.profile.edit.title')}</span>
    {#if summary.count > 0}
        <span class="shrink-0 rounded-full bg-lf-warning-soft px-2 py-0.5 text-xs font-medium text-lf-warning-on-soft" data-testid="asset-modal-profile-pending">
            {$t('assets.profile.row.pending', {values: {count: summary.count}})}
        </span>
        <span class="min-w-0 flex-1 truncate text-xs text-lf-link" data-testid="asset-modal-profile-voices">{summary.keys.map(voiceLabel).join(', ')}</span>
    {:else}
        <span class="flex-1"></span>
    {/if}
    <ExternalLink size={14} class="shrink-0 text-lf-muted" />
</div>
