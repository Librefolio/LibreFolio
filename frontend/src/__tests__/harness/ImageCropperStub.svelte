<!--
  ImageCropperStub — test-only stand-in for ImageCropper (Vitest + jsdom).

  The real cropper is cropperjs v2 painting a canvas, which jsdom cannot do: it never reports a selection, so
  ImageEditModal never leaves its init guard and its crop → upload path cannot be reached. The stub keeps the real
  cropper's public surface — the props ImageEditModal passes, the `change` event, `resetAll`, `selectAspect`,
  `getCropper` and `getImageDimensions` — and reports a selection only when the test clicks
  `image-cropper-stub-report`. Until then the modal sees what it saw with the real cropper in jsdom: a cropper that
  never reported.

  `getCropper()` answers an opaque token: its only reader is `getCroppedImageFromCropper`, which the spec replaces.

  A legacy component (`export let`, `createEventDispatcher`), as the real one: ImageEditModal binds it with
  `bind:this` and listens to it with `on:change`. The props are published as data attributes, which also keeps
  each of them read.

  Lives under `src/__tests__/`, excluded from coverage like every other harness here.
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';

    export let imageSrc: string;
    export let aspectRatio: number = 1;
    export let showZoomSlider: boolean = true;
    export let showRotateControls: boolean = true;
    export let showPreviewEllipse: boolean = false;

    const dispatch = createEventDispatcher<{change: {selection: {x: number; y: number; width: number; height: number}}}>();

    /** What getCropper() hands the modal; only the replaced getCroppedImageFromCropper ever reads it. */
    const CROPPER_TOKEN = Object.freeze({stub: 'image-cropper'});

    export function resetAll(): void {}

    /** Takes the aspect the modal passes; the stub has no selection to reshape. */
    export function selectAspect(): void {}

    export function getCropper(): object {
        return CROPPER_TOKEN;
    }

    export function getImageDimensions(): {width: number; height: number} {
        return {width: 640, height: 480};
    }

    function report(): void {
        dispatch('change', {selection: {x: 0, y: 0, width: 320, height: 240}});
    }
</script>

<button type="button" aria-label="image-cropper-stub-report" data-testid="image-cropper-stub-report" data-image-src={imageSrc} data-aspect-ratio={aspectRatio} data-zoom-slider={showZoomSlider} data-rotate-controls={showRotateControls} data-preview-ellipse={showPreviewEllipse} on:click={report}
></button>
