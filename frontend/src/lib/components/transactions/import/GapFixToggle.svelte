<!--
  GapFixToggle.svelte — the switch that keeps or drops one gap-fix correction, as a DataTable cell.

  The shared `editable-checkbox` cell draws the same switch, but without a testid or the facts of
  its row; this cell carries both (the correction's key, type, date and truth point), so the step
  and its tests can tell the corrections apart. The step owns the selection: a click only asks.
-->
<script lang="ts">
    interface Props {
        pressed: boolean;
        label: string;
        proposalKey: string;
        type: string;
        date: string;
        point: string;
        onToggle: () => void;
    }

    let {pressed, label, proposalKey, type, date, point, onToggle}: Props = $props();
</script>

<div class="flex justify-center">
    <button
        type="button"
        class="relative inline-flex h-5 w-9 cursor-pointer items-center rounded-full transition-colors {pressed ? 'bg-emerald-500' : 'bg-gray-300 dark:bg-slate-600'}"
        aria-pressed={pressed ? 'true' : 'false'}
        aria-label={label}
        title={label}
        onclick={(event) => {
            event.stopPropagation();
            onToggle();
        }}
        data-testid="gapfix-proposal-toggle"
        data-key={proposalKey}
        data-type={type}
        data-date={date}
        data-point={point}
    >
        <span class="inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform {pressed ? 'translate-x-[18px]' : 'translate-x-[3px]'}"></span>
    </button>
</div>
