<!--
  ProfileClassification — the countries and the sectors of the «Profilo» tab (plan 68, E4), with today's two components
  (`GeographyMap`, `AllocationPieChart`, as the old metadata panel drew them).

  «dati al» chooses the day: the days a composition changed in the period, newest first (`compositionDays`); the
  composition drawn is the one of that day (`compositionAt`). A part with no composition that day says so and draws no
  chart; each part publishes `data-state` (`value`, `unavailable`).

  Pattern: Svelte 5 Runes, Tailwind CSS 4, colour roles only.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import AllocationPieChart from '$lib/components/charts/AllocationPieChart.svelte';
    import GeographyMap from '$lib/components/charts/GeographyMap.svelte';
    import {currentLanguage} from '$lib/stores/app/language';
    import {uiLocale} from '$lib/stores/app/uiLocale';
    import type {ProfileVoices} from './profileStore';
    import {compositionAt, compositionDays, formatProfileDay} from './profileTabState';

    interface Props {
        voices: ProfileVoices;
    }

    let {voices}: Props = $props();

    const days = $derived(compositionDays(voices));
    let chosen = $state<string | null>(null);
    /** The day drawn: the one chosen while the period still has it, else the newest. */
    const day = $derived(chosen !== null && days.includes(chosen) ? chosen : (days[0] ?? null));
    const composition = $derived(day === null ? {geography: null, sector: null} : compositionAt(voices, day));
    const geography = $derived(composition.geography && Object.keys(composition.geography).length ? composition.geography : null);
    const sectors = $derived(composition.sector && Object.keys(composition.sector).length ? Object.entries(composition.sector).map(([name, weight]) => ({name, value: weight * 100, amount: 0})) : null);
</script>

<div class="flex flex-col gap-3" data-testid="profile-classification">
    <div class="flex flex-wrap items-center justify-between gap-2">
        <h3 class="text-xs font-semibold uppercase tracking-wide text-lf-muted">{$t('assets.profile.groups.classification')}</h3>
        {#if days.length}
            <select
                class="rounded-lg border border-lf-input bg-lf-field px-2 py-1 text-xs text-lf-primary hover:border-lf-input-hover focus:border-lf-focus focus:ring-1 focus:ring-lf-focus"
                aria-label={$t('assets.profile.groups.classification')}
                data-testid="profile-classification-day"
                value={day}
                onchange={(event) => (chosen = (event.currentTarget as HTMLSelectElement).value)}
            >
                {#each days as option (option)}
                    <option value={option}>{$t('assets.profile.tab.dataAsOf', {values: {date: formatProfileDay(option, uiLocale())}})}</option>
                {/each}
            </select>
        {/if}
    </div>
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div class="rounded-lg bg-lf-panel p-3" data-testid="profile-classification-geography" data-state={geography ? 'value' : 'unavailable'}>
            <h4 class="mb-2 text-xs font-medium text-lf-muted">{$t('assets.profile.voices.geography')}</h4>
            {#if geography}
                <GeographyMap data={geography} height="280px" language={$currentLanguage} />
            {:else}
                <p class="text-sm italic text-lf-muted">{$t('assets.profile.tab.notAvailable')}</p>
            {/if}
        </div>
        <div class="rounded-lg bg-lf-panel p-3" data-testid="profile-classification-sector" data-state={sectors ? 'value' : 'unavailable'}>
            <h4 class="mb-2 text-xs font-medium text-lf-muted">{$t('assets.profile.voices.sector')}</h4>
            {#if sectors}
                <AllocationPieChart data={sectors} height="280px" />
            {:else}
                <p class="text-sm italic text-lf-muted">{$t('assets.profile.tab.notAvailable')}</p>
            {/if}
        </div>
    </div>
</div>
