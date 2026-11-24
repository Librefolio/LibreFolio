<!--
  GapFixToggle.svelte — the switch that keeps or drops one gap-fix correction, as a DataTable cell.

  The shared `editable-checkbox` cell draws the same switch, but without a testid or the facts of
  its row; this cell carries both (the correction's key, type, date and truth point), so the step
  and its tests can tell the corrections apart. The step owns the selection: a click only asks.
-->
<script lang="ts">
    import Switch from '$lib/components/ui/input/Switch.svelte';

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
    <!-- colour: closest role, to review: the on track was emerald-500 (a success green); switch role bg-lf-checked, alt bg-lf-success -->
    <Switch
        size="sm"
        semantics="pressed"
        checked={pressed}
        {label}
        title={label}
        onchange={(_next, event) => {
            event.stopPropagation();
            onToggle();
        }}
        testId="gapfix-proposal-toggle"
        data-key={proposalKey}
        data-type={type}
        data-date={date}
        data-point={point}
    />
</div>
