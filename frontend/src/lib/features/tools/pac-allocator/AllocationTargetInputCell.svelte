<script lang="ts">
    import {t} from '$lib/i18n';
    import ExactDecimalInput from '$lib/components/ui/input/ExactDecimalInput.svelte';

    interface Props {
        value: string;
        disabled?: boolean;
        testid: string;
        onchange: (value: string) => void;
    }

    let {value, disabled = false, testid, onchange}: Props = $props();
</script>

<div class="flex items-center gap-1.5" onclick={(event) => event.stopPropagation()} role="presentation">
    <ExactDecimalInput {value} step="0.01" maxIntegerDigits={3} maxFractionDigits={12} ariaLabel={$t('tools.pacAllocator.rows.target')} {testid} className="min-h-8 !rounded-md !px-2 !py-1 text-right text-sm" {disabled} {onchange} />
    <span class="text-xs font-medium text-gray-500 dark:text-gray-400">%</span>
</div>
