<!--
  ImagePickerWrapperProbe — test-only stand-in for ImagePickerWrapper.svelte (Vitest + jsdom).

  The real ImagePickerWrapper statically imports AssetPickerModal and ImageEditModal,
  which pull in the full asset-search/upload/crop graph. That graph is heavy enough
  that a worker importing it for a component test (WelcomePage.test.ts) runs the
  process out of memory — a unit test boundary defect, not a product failure: nothing
  about WelcomePage's own orchestration (open the picker, apply a chosen URL, clear
  the avatar) depends on the real picker's internals.

  This probe keeps only the contract WelcomePage relies on: a bindable `open`, the
  `onchange` callback used when a URL is "selected", and a stable, real ARIA dialog
  role so `getByRole('dialog')` behaves identically to the real modal while it is
  open. `select`/`remove` test controls let a spec simulate the two outcomes
  ImagePickerWrapper's own descendants normally drive (AssetPickerModal's `select`
  event and the "remove image" empty-string case) without mounting them.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<script lang="ts">
    interface Props {
        open?: boolean;
        zIndex?: number;
        title?: string;
        preset?: string;
        initialUrl?: string;
        circularPreview?: boolean;
        filterImages?: boolean;
        onchange?: (url: string) => void;
        oncancel?: () => void;
    }

    let {open = $bindable(false), title = '', onchange, oncancel}: Props = $props();
</script>

{#if open}
    <div aria-modal="true" role="dialog" data-testid="image-picker-wrapper-probe">
        <h2 data-testid="image-picker-wrapper-probe-title">{title}</h2>
        <button
            type="button"
            data-testid="image-picker-wrapper-probe-select"
            onclick={() => {
                open = false;
                onchange?.('https://example.test/picked.png');
            }}
        >
            select
        </button>
        <button
            type="button"
            data-testid="image-picker-wrapper-probe-remove"
            onclick={() => {
                open = false;
                onchange?.('');
            }}
        >
            remove
        </button>
        <button
            type="button"
            data-testid="image-picker-wrapper-probe-cancel"
            onclick={() => {
                open = false;
                oncancel?.();
            }}
        >
            cancel
        </button>
    </div>
{/if}
