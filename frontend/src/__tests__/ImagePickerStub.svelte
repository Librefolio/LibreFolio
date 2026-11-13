<!--
  Stand-in for ImagePickerWrapper in component tests: while open it shows one button that «picks» a fixed icon URL.
-->
<script lang="ts">
    interface Props {
        open?: boolean;
        onchange?: (url: string) => void;
        // The real picker takes more props; a stand-in ignores them.
        [key: string]: unknown;
    }

    let {open = false, onchange}: Props = $props();
</script>

{#if open}
    <button type="button" data-testid="stub-icon-pick" onclick={() => onchange?.('https://example.test/icons/my%20logo.png')}>pick</button>
{/if}
