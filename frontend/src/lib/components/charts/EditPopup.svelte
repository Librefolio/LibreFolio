<!-- EditPopup — STUB. Will be implemented in Step 6.
     Click on data point to show popup for editing the value. Active only in edit mode. -->
<script lang="ts">
    interface Props { visible?: boolean; date?: string; value?: number; onSave?: (date: string, value: number) => void; onClose?: () => void; }
    let { visible = false, date = '', value = 0, onSave, onClose }: Props = $props();
</script>
{#if visible}
<div class="absolute z-50 bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-gray-200 dark:border-slate-600 p-3 min-w-48">
    <div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">{date}</div>
    <input type="number" class="w-full px-2 py-1 border rounded text-sm dark:bg-slate-700 dark:border-slate-600" bind:value step="0.0001" />
    <div class="flex gap-2 mt-2">
        <button class="px-3 py-1 text-xs bg-libre-green text-white rounded hover:bg-libre-green/90" on:click={() => onSave?.(date, value)}>Save</button>
        <button class="px-3 py-1 text-xs bg-gray-200 dark:bg-slate-600 rounded hover:bg-gray-300" on:click={() => onClose?.()}>Cancel</button>
    </div>
</div>
{/if}
