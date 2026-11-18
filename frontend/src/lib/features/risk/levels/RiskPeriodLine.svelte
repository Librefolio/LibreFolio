<script lang="ts">
    import {_ as t} from '$lib/i18n';

    import {dayFormatter} from '../eligibility';
    import RiskFreeRateField from '../RiskFreeRateField.svelte';

    /**
     * The period and the currency the figures below are measured on (RN-11, Q14), one line shared by every risk
     * surface: the levels' header (`RiskPanelHeader`: Dashboard, Broker) and the lab above its sections. The period is
     * the one asked for, the page's; when the analysis starts later, the level's box says so (the warning
     * `analysis_starts_late`). An open end reads «from {start}».
     *
     * Under it, the reader's risk-free rate (RN-21): one more condition of the figures below, so it sits where the
     * others are said, on every surface that says them (the consultant, 17/11/2026).
     */
    interface Props {
        dateStart: string;
        dateEnd: string;
        currency: string;
        testId?: string;
    }

    let {dateStart, dateEnd, currency, testId = 'risk-period'}: Props = $props();

    // The formatter is taken inside, so a language switch — which re-runs `$t` — formats the days anew.
    let text = $derived.by(() => {
        const day = dayFormatter();
        return dateEnd ? $t('risk.period.range', {values: {start: day(dateStart), end: day(dateEnd), currency}}) : $t('risk.period.open', {values: {start: day(dateStart), currency}});
    });
</script>

{#if dateStart}
    <p class="text-xs text-lf-muted" data-testid={testId} data-start={dateStart} data-end={dateEnd} data-currency={currency}>{text}</p>
{/if}
<RiskFreeRateField />
