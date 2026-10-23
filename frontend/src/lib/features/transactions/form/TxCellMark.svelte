<!--
  TxCellMark — one cell of the transaction form, marked when «Validate now» found it wrong (V-37b).

  The wrapper publishes `data-cell` (which cell it is) and, only while the cell is wrong, `data-cell-invalid` (`required`
  or `format`): that is what the form's focus and the tests read. A missing required value gets a danger ring; a format
  error is already red on the control itself (its own border), so the wrapper adds no second one. Colours are roles only.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import type {TxFormCell, TxFormCheckKind} from './txFormChecks';

    interface Props {
        cell: TxFormCell;
        marks: Partial<Record<TxFormCell, TxFormCheckKind>>;
        children: Snippet;
    }

    let {cell, marks, children}: Props = $props();
    let kind = $derived(marks[cell]);
</script>

<div data-cell={cell} data-cell-invalid={kind} class="rounded-lg {kind === 'required' ? 'ring-1 ring-lf-danger' : ''}">
    {@render children()}
</div>
