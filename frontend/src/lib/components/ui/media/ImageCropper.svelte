<!--
  ImageCropper - Interactive image cropping component

  Uses cropperjs v2 (Web Components) for full-featured crop functionality.
  Supports zoom, rotation (live preview), flip, aspect ratio selection, free crop with handles.
-->
<script lang="ts">
    import {createEventDispatcher, onMount, onDestroy, tick} from 'svelte';
    import Cropper from 'cropperjs';
    // Note: cropperjs v2 uses Web Components, CSS is built-in
    import {_} from '$lib/i18n';
    import {ZoomIn, ZoomOut, RotateCcw, RotateCw, FlipHorizontal, FlipVertical, RefreshCw} from 'lucide-svelte';

    // Props
    export let imageSrc: string;
    export let aspectRatio: number = 1;  // NaN or 0 = free, 1 = square, 16/9, etc.
    export let minZoom: number = 1;
    export let maxZoom: number = 10;
    export let showZoomSlider: boolean = true;
    export let showAspectSelector: boolean = false;
    export let showRotateControls: boolean = true;
    export let aspectOptions: Array<{value: number; label: string}> = [
        {value: 1, label: '1:1'},
        {value: 16/9, label: '16:9'},
        {value: 4/3, label: '4:3'},
        {value: 3/4, label: '3:4'},
        {value: 0, label: $_('uploads.free') || 'Free'}
    ];

    const dispatch = createEventDispatcher<{
        change: {selection: {x: number; y: number; width: number; height: number}};
    }>();

    // Internal state
    let containerElement: HTMLDivElement;
    let cropper: Cropper | null = null;
    let currentAspect = aspectRatio;
    let currentZoom = 1;
    let currentRotation = 0;
    let scaleX = 1;
    let scaleY = 1;

    // Image dimensions for info display
    let imageWidth = 0;
    let imageHeight = 0;
    let cropWidth = 0;
    let cropHeight = 0;

    // Update aspect when prop changes
    $: currentAspect = aspectRatio;

    // Reactive: when imageSrc changes, recreate cropper
    $: if (imageSrc && containerElement) {
        initCropper();
    }

    onMount(() => {
        if (imageSrc && containerElement) {
            initCropper();
        }
    });

    onDestroy(() => {
        cropper?.destroy();
        cropper = null;
    });

    async function initCropper() {
        // Wait for DOM update
        await tick();

        // Destroy previous instance if exists
        if (cropper) {
            cropper.destroy();
        }

        // Clear container
        containerElement.innerHTML = '';

        // Determine aspect ratio (0 or NaN = free)
        const effectiveAspect = (currentAspect === 0 || isNaN(currentAspect)) ? NaN : currentAspect;

        // Create new Cropper instance with v2 API
        cropper = new Cropper(imageSrc, {
            container: containerElement,
        });

        // Wait for image to load
        const cropperImage = cropper.getCropperImage();
        const cropperSelection = cropper.getCropperSelection();
        const cropperCanvas = cropper.getCropperCanvas();

        if (cropperImage && cropperSelection && cropperCanvas) {
            // Configure selection
            if (!isNaN(effectiveAspect)) {
                cropperSelection.aspectRatio = effectiveAspect;
            }
            cropperSelection.initialCoverage = 0.8;
            cropperSelection.movable = true;
            cropperSelection.resizable = true;
            cropperSelection.zoomable = true;

            // Configure image
            cropperImage.rotatable = true;
            cropperImage.scalable = true;

            // Configure canvas
            cropperCanvas.background = true;

            // Listen for changes
            cropperSelection.addEventListener('change', (e: Event) => {
                const sel = e.target as any;
                cropWidth = Math.round(sel.width || 0);
                cropHeight = Math.round(sel.height || 0);
                dispatch('change', {
                    selection: {
                        x: sel.x || 0,
                        y: sel.y || 0,
                        width: cropWidth,
                        height: cropHeight
                    }
                });
            });

            // Get natural image dimensions
            cropperImage.$ready(() => {
                const img = cropperImage.$image;
                if (img) {
                    imageWidth = img.naturalWidth;
                    imageHeight = img.naturalHeight;
                }
            });
        }
    }

    // Control functions
    function zoomIn() {
        const cropperCanvas = cropper?.getCropperCanvas();
        if (cropperCanvas) {
            currentZoom = Math.min(currentZoom + 0.5, maxZoom);
            // Zoom is relative in v2, we use scale
            const img = cropper?.getCropperImage();
            img?.$zoom(1.5);
        }
    }

    function zoomOut() {
        const img = cropper?.getCropperImage();
        if (img) {
            currentZoom = Math.max(currentZoom - 0.5, minZoom);
            img.$zoom(0.67);  // 1/1.5
        }
    }

    function resetZoom() {
        const img = cropper?.getCropperImage();
        if (img) {
            img.$center('contain');
            currentZoom = 1;
        }
    }

    function rotateLeft() {
        const img = cropper?.getCropperImage();
        if (img) {
            img.$rotate(-15);
            currentRotation -= 15;
            if (currentRotation < -180) currentRotation += 360;
        }
    }

    function rotateRight() {
        const img = cropper?.getCropperImage();
        if (img) {
            img.$rotate(15);
            currentRotation += 15;
            if (currentRotation > 180) currentRotation -= 360;
        }
    }

    function resetRotation() {
        // Reset by re-initializing (v2 doesn't have rotateTo)
        currentRotation = 0;
        initCropper();
    }

    function flipH() {
        const img = cropper?.getCropperImage();
        if (img) {
            scaleX = scaleX === 1 ? -1 : 1;
            img.$scale(scaleX, scaleY);
        }
    }

    function flipV() {
        const img = cropper?.getCropperImage();
        if (img) {
            scaleY = scaleY === 1 ? -1 : 1;
            img.$scale(scaleX, scaleY);
        }
    }

    function resetAll() {
        currentZoom = 1;
        currentRotation = 0;
        scaleX = 1;
        scaleY = 1;
        initCropper();
    }

    function selectAspect(value: number) {
        currentAspect = value;
        const sel = cropper?.getCropperSelection();
        if (sel) {
            const effectiveAspect = (value === 0 || isNaN(value)) ? NaN : value;
            sel.aspectRatio = effectiveAspect;
        }
    }

    function handleZoomSliderChange() {
        // For slider, we can't directly set zoom in v2, so we work with relative zoom
        // This is a simplified approach
        const img = cropper?.getCropperImage();
        if (img) {
            // Calculate relative zoom from previous
            const factor = currentZoom;
            img.$zoom(factor / (factor - 0.1 || 1));
        }
    }

    function handleRotationSliderChange() {
        const img = cropper?.getCropperImage();
        if (img) {
            // Reset and apply new rotation
            const oldRotation = currentRotation;
            // v2 rotate is relative, so we need to track delta
            // For now, rotation slider triggers full reset + rotate
            // This is simplified - full implementation would track matrix
        }
    }

    // Exported methods for parent component
    export function getCropper(): Cropper | null {
        return cropper;
    }

    export async function getCroppedCanvas(options?: {width?: number; height?: number}): Promise<HTMLCanvasElement | null> {
        const sel = cropper?.getCropperSelection();
        if (!sel) return null;
        try {
            return await sel.$toCanvas(options);
        } catch {
            return null;
        }
    }

    export function getSelection(): {x: number; y: number; width: number; height: number} | null {
        const sel = cropper?.getCropperSelection();
        if (!sel) return null;
        return {
            x: sel.x,
            y: sel.y,
            width: sel.width,
            height: sel.height
        };
    }

    export function getImageDimensions(): {width: number; height: number} {
        return {width: imageWidth, height: imageHeight};
    }

    export function getCropDimensions(): {width: number; height: number} {
        return {width: cropWidth, height: cropHeight};
    }

    export function getTransform(): {rotation: number; scaleX: number; scaleY: number} {
        return {
            rotation: currentRotation,
            scaleX,
            scaleY
        };
    }
</script>

<div class="image-cropper">
    <!-- Crop Area -->
    <div class="crop-container" bind:this={containerElement}>
        <!-- Cropper v2 creates its own DOM structure here -->
    </div>

    <!-- Image Info -->
    <div class="image-info">
        <div class="info-row">
            <span class="info-label">{$_('uploads.inputSize') || 'Input'}:</span>
            <span class="info-value">{imageWidth} × {imageHeight} px</span>
        </div>
        <div class="info-row">
            <span class="info-label">{$_('uploads.selectionSize') || 'Selection'}:</span>
            <span class="info-value">{cropWidth} × {cropHeight} px</span>
        </div>
    </div>

    <!-- Controls -->
    <div class="controls">
        <!-- Aspect Ratio Selector -->
        {#if showAspectSelector}
            <div class="control-group">
                <span class="control-label">{$_('uploads.aspectRatio') || 'Aspect Ratio'}:</span>
                <div class="aspect-buttons">
                    {#each aspectOptions as opt}
                        <button
                            type="button"
                            class="aspect-btn"
                            class:active={currentAspect === opt.value}
                            on:click={() => selectAspect(opt.value)}
                        >
                            {opt.label}
                        </button>
                    {/each}
                </div>
            </div>
        {/if}

        <!-- Zoom Controls -->
        {#if showZoomSlider}
            <div class="control-group">
                <span class="control-label">{$_('uploads.zoom') || 'Zoom'}:</span>
                <div class="control-row">
                    <button type="button" class="control-btn" on:click={zoomOut} title={$_('uploads.zoomOut') || 'Zoom out'}>
                        <ZoomOut size={16} />
                    </button>
                    <span class="value-display">{currentZoom.toFixed(1)}×</span>
                    <button type="button" class="control-btn" on:click={zoomIn} title={$_('uploads.zoomIn') || 'Zoom in'}>
                        <ZoomIn size={16} />
                    </button>
                    <button type="button" class="control-btn small" on:click={resetZoom} title={$_('uploads.reset') || 'Reset'}>
                        <RefreshCw size={12} />
                    </button>
                </div>
            </div>
        {/if}

        <!-- Rotation & Flip Controls -->
        {#if showRotateControls}
            <div class="control-group">
                <span class="control-label">{$_('uploads.rotation') || 'Rotation'}:</span>
                <div class="control-row">
                    <button type="button" class="control-btn" on:click={rotateLeft} title="-15°">
                        <RotateCcw size={16} />
                    </button>
                    <span class="value-display">{Math.round(currentRotation)}°</span>
                    <button type="button" class="control-btn" on:click={rotateRight} title="+15°">
                        <RotateCw size={16} />
                    </button>
                    <button type="button" class="control-btn small" on:click={resetRotation} title={$_('uploads.reset') || 'Reset'}>
                        <RefreshCw size={12} />
                    </button>
                </div>
            </div>

            <div class="control-group">
                <span class="control-label">{$_('uploads.flip') || 'Flip'}:</span>
                <div class="control-row">
                    <button
                        type="button"
                        class="control-btn"
                        class:active={scaleX === -1}
                        on:click={flipH}
                        title={$_('uploads.flipHorizontal') || 'Flip horizontal'}
                    >
                        <FlipHorizontal size={16} />
                        <span class="btn-label">H</span>
                    </button>
                    <button
                        type="button"
                        class="control-btn"
                        class:active={scaleY === -1}
                        on:click={flipV}
                        title={$_('uploads.flipVertical') || 'Flip vertical'}
                    >
                        <FlipVertical size={16} />
                        <span class="btn-label">V</span>
                    </button>
                    <div class="separator"></div>
                    <button type="button" class="control-btn reset" on:click={resetAll} title={$_('uploads.resetAll') || 'Reset All'}>
                        <RotateCcw size={14} />
                        <span class="btn-label">{$_('uploads.resetAll') || 'Reset All'}</span>
                    </button>
                </div>
            </div>
        {/if}
    </div>
</div>

<style>
    .image-cropper {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        width: 100%;
    }

    .crop-container {
        position: relative;
        width: 100%;
        height: 300px;
        background: #1a1a1a;
        border-radius: 0.5rem;
        overflow: hidden;
    }

    @media (min-width: 640px) {
        .crop-container {
            height: 400px;
        }
    }

    /* Cropperjs v2 container styles */
    .crop-container :global(cropper-canvas) {
        width: 100%;
        height: 100%;
    }

    .image-info {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        padding: 0.75rem;
        background: #f3f4f6;
        border-radius: 0.375rem;
    }

    :global(.dark) .image-info {
        background: #374151;
    }

    .info-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
    }

    .info-label {
        color: #6b7280;
        font-weight: 500;
    }

    .info-value {
        color: #374151;
        font-family: monospace;
    }

    :global(.dark) .info-label {
        color: #9ca3af;
    }

    :global(.dark) .info-value {
        color: #e5e7eb;
    }

    .controls {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        padding: 0.5rem;
    }

    .control-group {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-wrap: wrap;
    }

    .control-label {
        font-size: 0.875rem;
        font-weight: 500;
        color: #4b5563;
        min-width: 70px;
    }

    :global(.dark) .control-label {
        color: #9ca3af;
    }

    .control-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex: 1;
        flex-wrap: wrap;
    }

    /* Aspect Selector */
    .aspect-buttons {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .aspect-btn {
        padding: 0.375rem 0.75rem;
        font-size: 0.75rem;
        font-weight: 500;
        border: 1px solid #d1d5db;
        border-radius: 0.375rem;
        background: white;
        color: #374151;
        cursor: pointer;
        transition: all 0.15s;
    }

    .aspect-btn:hover {
        border-color: #1a4031;
        color: #1a4031;
    }

    .aspect-btn.active {
        background: #1a4031;
        border-color: #1a4031;
        color: white;
    }

    :global(.dark) .aspect-btn {
        background: #374151;
        border-color: #4b5563;
        color: #d1d5db;
    }

    :global(.dark) .aspect-btn:hover {
        border-color: #10b981;
        color: #10b981;
    }

    :global(.dark) .aspect-btn.active {
        background: #10b981;
        border-color: #10b981;
        color: white;
    }

    /* Control buttons */
    .control-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.25rem;
        min-width: 32px;
        height: 32px;
        padding: 0 0.5rem;
        border-radius: 0.375rem;
        border: 1px solid #d1d5db;
        background: white;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.15s;
    }

    .control-btn.small {
        min-width: 24px;
        height: 24px;
        padding: 0 0.25rem;
    }

    .control-btn:hover {
        border-color: #1a4031;
        color: #1a4031;
    }

    .control-btn.active {
        background: #1a4031;
        border-color: #1a4031;
        color: white;
    }

    .control-btn.reset {
        background: #fef2f2;
        border-color: #fecaca;
        color: #dc2626;
    }

    .control-btn.reset:hover {
        background: #fee2e2;
        border-color: #f87171;
    }

    :global(.dark) .control-btn {
        background: #374151;
        border-color: #4b5563;
        color: #9ca3af;
    }

    :global(.dark) .control-btn:hover {
        border-color: #10b981;
        color: #10b981;
    }

    :global(.dark) .control-btn.active {
        background: #10b981;
        border-color: #10b981;
        color: white;
    }

    :global(.dark) .control-btn.reset {
        background: #450a0a;
        border-color: #7f1d1d;
        color: #f87171;
    }

    .btn-label {
        font-size: 0.75rem;
    }

    .value-display {
        font-size: 0.75rem;
        font-weight: 500;
        font-family: monospace;
        color: #6b7280;
        min-width: 3rem;
        text-align: center;
    }

    :global(.dark) .value-display {
        color: #9ca3af;
    }

    .separator {
        width: 1px;
        height: 20px;
        background: #d1d5db;
        margin: 0 0.25rem;
    }

    :global(.dark) .separator {
        background: #4b5563;
    }

    /* Cropperjs v2 dark mode overrides */
    :global(.dark) .crop-container :global(cropper-canvas) {
        --cropper-backdrop-color: rgba(0, 0, 0, 0.7);
        --cropper-outline-color: rgba(16, 185, 129, 0.75);
    }

    :global(.dark) .crop-container :global(cropper-selection) {
        --cropper-selection-outline-color: #10b981;
    }
</style>
