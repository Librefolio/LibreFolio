<script lang="ts">
    import {t, locale} from '$lib/i18n';
    import {daysBetween} from '../draft.svelte';
    import {formatPlannerDate} from '../format';
    import {BADGE} from '../ui';

    interface Props {
        /** Reference date of the fact (`YYYY-MM-DD`), `null` when unknown. */
        date: string | null;
        /** Scenario date the fact is compared with. */
        asOf: string;
        /** A value typed by the user: it has no source age. */
        manual?: boolean;
        testid?: string;
    }

    let {date, asOf, manual = false, testid}: Props = $props();

    const days = $derived(date ? daysBetween(date, asOf) : null);
    const state = $derived(manual ? 'manual' : days === null ? 'unknown' : days === 0 ? 'same' : days > 0 ? 'before' : 'after');
    const asOfText = $derived(formatPlannerDate(asOf, $locale));
</script>

<span class={state === 'same' || state === 'manual' ? BADGE.neutral : state === 'after' ? BADGE.danger : BADGE.warning} data-testid={testid} data-age={state} data-days={days ?? ''}>
    {#if state === 'manual'}
        {$t('tools.pacAllocator.planner.age.manual', {default: 'Entered by hand'})}
    {:else if state === 'same'}
        {$t('tools.pacAllocator.planner.age.sameDay', {default: 'Of the day'})}
    {:else if state === 'before'}
        {$t('tools.pacAllocator.planner.age.daysBefore', {default: '{count, plural, one {# day} other {# days}} before {date}', values: {count: days ?? 0, date: asOfText}})}
    {:else if state === 'after'}
        {$t('tools.pacAllocator.planner.age.after', {default: 'After the scenario date {date}', values: {date: asOfText}})}
    {:else}
        {$t('tools.pacAllocator.planner.age.unknown', {default: 'Date unknown'})}
    {/if}
</span>
