<!--
  ProfileKeyFigureCard — one key figure of the «Profilo» tab (plan 68, E4): the voice's label, its value in the period
  (or «non disponibile»), and, for a charted voice, the small chart of its steps (`PriceChartCompact`, the cards' own).
  The shell is the one of `RiskMetricCard`; the value sits under the label, as the mock wants.

  The card publishes `data-state` (`value`, `emptied`, `unavailable`): tests read it, never the text. A stale value (D1d)
  adds «confermato il …, non aggiornato» under it, in the warning role, and `data-stale="true"`. The clock opens the
  voice's history (`onhistory`, E6) and shows only when the card has a value and the page handles it.

  Pattern: Svelte 5 Runes, Tailwind CSS 4, colour roles only.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import PriceChartCompact from '$lib/components/charts/PriceChartCompact.svelte';
    import ProfileHistoryClock from './ProfileHistoryClock.svelte';
    import type {KeyFigureCard} from './profileTabState';

    interface Props {
        card: KeyFigureCard;
        /** The value as the tab writes it (`formatProfileValue`); unused when the card has no value. */
        text: string;
        /** Opens the voice's history (E6); without it the card has no clock. */
        onhistory?: (key: string) => void;
        /** «Confermato il …, non aggiornato» (D1d), when the value is stale; absent otherwise. */
        staleText?: string;
    }

    let {card, text, onhistory, staleText}: Props = $props();

    const label = $derived($t(`assets.profile.voices.${card.key}`));
    const shown = $derived(card.state === 'value' && text !== '');
</script>

<div class="@container bg-lf-card text-lf-primary rounded-xl border border-lf-subtle shadow-sm shadow-lf-shadow-card p-4 flex flex-col gap-2 min-w-0" data-testid="profile-key-figure-{card.key}" data-state={card.state} data-stale={shown && staleText ? 'true' : 'false'}>
    <div class="flex items-start justify-between gap-2">
        <p class="text-xs font-medium uppercase tracking-wide text-lf-muted line-clamp-2">{label}</p>
        {#if onhistory && card.state !== 'unavailable'}
            <ProfileHistoryClock voiceKey={card.key} testId="profile-key-figure-{card.key}-history" {onhistory} />
        {/if}
    </div>
    {#if shown}
        <p class="text-[clamp(1rem,8cqw,1.5rem)] font-bold tabular-nums break-words" data-testid="profile-key-figure-{card.key}-value">{text}</p>
        {#if staleText}
            <p class="text-xs text-lf-warning" data-testid="profile-key-figure-{card.key}-stale">{staleText}</p>
        {/if}
    {:else}
        <p class="text-sm italic text-lf-muted" data-testid="profile-key-figure-{card.key}-value">{$t('assets.profile.tab.notAvailable')}</p>
    {/if}
    {#if card.chart}
        <div data-testid="profile-key-figure-{card.key}-chart">
            <PriceChartCompact data={card.chart} height="40px" areaFill={false} showMiniAxis={false} colorByBaseline={false} lineShape="steps" />
        </div>
    {/if}
</div>
