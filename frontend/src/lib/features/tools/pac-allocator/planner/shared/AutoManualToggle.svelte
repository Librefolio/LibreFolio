<!--
  «Auto | Manual» for a fact LibreFolio can supply (an Asset price, an FX rate): the same pill pair
  as the WAC preview of the transaction form, so the two switches read alike.
-->
<script lang="ts">
    import {t} from '$lib/i18n';

    interface Props {
        manual: boolean;
        /** Names the fact for assistive technology: «Price of VWCE». */
        label: string;
        onchange: (manual: boolean) => void;
        testid: string;
    }

    let {manual, label, onchange, testid}: Props = $props();

    const ON_AUTO = 'bg-libre-green/10 font-medium text-libre-green';
    const ON_MANUAL = 'bg-gray-200 font-medium text-gray-700 dark:bg-slate-700 dark:text-gray-200';
    const OFF = 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300';
</script>

<div class="flex shrink-0 items-center gap-1 text-xs" role="group" aria-label={label} data-testid={testid} data-mode={manual ? 'manual' : 'auto'}>
    <button type="button" class="rounded px-1.5 py-0.5 {manual ? OFF : ON_AUTO}" aria-pressed={!manual} data-testid="{testid}-auto" onclick={() => manual && onchange(false)}>
        {$t('tools.pacAllocator.planner.mode.auto', {default: 'Auto'})}
    </button>
    <span class="text-gray-300 dark:text-gray-600" aria-hidden="true">|</span>
    <button type="button" class="rounded px-1.5 py-0.5 {manual ? ON_MANUAL : OFF}" aria-pressed={manual} data-testid="{testid}-manual" onclick={() => !manual && onchange(true)}>
        {$t('tools.pacAllocator.planner.mode.manual', {default: 'Manual'})}
    </button>
</div>
