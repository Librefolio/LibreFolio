<!--
  Test harness for Button.test.ts (85 BTN-2·0, C2): two Buttons inside a ButtonGroup — segments — and one outside it,
  the control case of the context.
-->
<script lang="ts">
    import Button from '../Button.svelte';
    import ButtonGroup from '../ButtonGroup.svelte';

    let {mode = 'grid'}: {mode?: 'grid' | 'list'} = $props();
</script>

<ButtonGroup label="View" data-testid="probe-group">
    <Button label="Grid" pressed={mode === 'grid'} data-testid="probe-grid" />
    <Button label="List" pressed={mode === 'list'} data-testid="probe-list" />
</ButtonGroup>
<Button label="Outside" pressed={false} data-testid="probe-outside" />
