<script lang="ts">
    import {getIndexColor} from '$lib/utils/colors';

    interface Props {
        value: string;
        index: number;
    }

    let {value, index}: Props = $props();

    let width = $derived.by(() => {
        const parsed = Number(value.replace(',', '.'));
        return Number.isFinite(parsed) ? Math.max(0, Math.min(100, parsed)) : 0;
    });
    let color = $derived(getIndexColor(index, 205).vivid);
</script>

<div class="min-w-28" aria-hidden="true">
    <div class="h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div class="h-full rounded-full transition-[width]" style={`width:${width}%;background:${color}`}></div>
    </div>
</div>
