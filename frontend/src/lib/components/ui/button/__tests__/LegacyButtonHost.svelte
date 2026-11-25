<!--
  Test host for Button.test.ts: a parent written in Svelte 4 syntax (no runes, `export let`), as the components not
  migrated yet are. Svelte 5 components take callbacks as props, so a legacy parent passes `onclick={handler}`, not
  `on:click`. Under `__tests__`: no production scan reads it (isProductionSource of theme-roles.mjs).
-->
<script>
    import Button from '../Button.svelte';

    /** @type {(event: MouseEvent) => void} */
    export let onpress = () => {};
    export let label = 'Legacy';
</script>

<Button {label} onclick={onpress} data-testid="legacy-host-button" />
