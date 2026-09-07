<script lang="ts">
    import {renderInlineMathText} from '$lib/utils/inlineMath';

    interface Props {
        icon: string;
        name: string;
        subtitle?: string;
        dataSubtitle?: string;
    }

    let {icon, name, subtitle = '', dataSubtitle = ''}: Props = $props();
    let renderedSubtitle = $derived(renderInlineMathText(subtitle));
</script>

<div class="flex w-full min-w-0 items-start gap-2 text-sm">
    <span class="emoji-flag mt-0.5 w-5 shrink-0 text-center text-base leading-none">{icon}</span>
    <div class="min-w-0 flex-1">
        <div class="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-0.5">
            <span class="shrink-0 font-medium text-gray-800 dark:text-gray-100">{name}</span>
            {#if subtitle}
                <span class="signal-option-subtitle min-w-0 flex-1 whitespace-normal text-[11px] leading-4 text-gray-400 dark:text-gray-500">{@html renderedSubtitle}</span>
            {/if}
        </div>
        {#if dataSubtitle}
            <span class="mt-0.5 block text-[10px] leading-4 text-gray-500 dark:text-gray-400">{dataSubtitle}</span>
        {/if}
    </div>
</div>

<style>
    .signal-option-subtitle :global(.katex) {
        font-size: 1em;
    }
</style>
