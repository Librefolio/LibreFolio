<!--
  ImageCropper - Interactive image cropping component

  Uses svelte-easy-crop for crop functionality.
  Supports zoom, rotation, flip, aspect ratio selection, and real-time preview.
  Note: Rotation is applied during final crop processing, not in live preview.
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import Cropper from 'svelte-easy-crop';
    import type {CropArea} from 'svelte-easy-crop';
    import {_} from '$lib/i18n';
    import {ZoomIn, ZoomOut, RotateCcw, FlipHorizontal, FlipVertical, Minus, Plus} from 'lucide-svelte';

    // Props
    export let imageSrc: string;
    export let aspectRatio: number = 1;  // 0 = free (uses 4:3), 1 = square, 16/9, etc.
    export let minZoom: number = 0.5;
    export let maxZoom: number = 10;  // Allow very aggressive zoom
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
        cropcomplete: {percent: CropArea; pixels: CropArea};
    }>();

    // Internal state
    let crop = {x: 0, y: 0};
    let zoom = 1;
    let rotation = 0;  // -180 to +180 degrees
    let flipH = false;
    let flipV = false;
    let currentAspect = aspectRatio;
    let croppedAreaPixels: CropArea | null = null;

    // Image dimensions for info display
    let imageWidth = 0;
    let imageHeight = 0;

    // Update aspect when prop changes
    $: currentAspect = aspectRatio;

    // Effective aspect for cropper (Free uses 4:3 as svelte-easy-crop doesn't support true free)
    $: effectiveAspect = currentAspect === 0 ? 4/3 : currentAspect;

    // Load image dimensions
    $: if (imageSrc) {
        const img = new Image();
        img.onload = () => {
            imageWidth = img.naturalWidth;
            imageHeight = img.naturalHeight;
        };
        img.src = imageSrc;
    }

    // Handler for crop complete - use oncropcomplete prop format
    function handleCropComplete(event: {percent: CropArea; pixels: CropArea}) {
        croppedAreaPixels = event.pixels;
        dispatch('cropcomplete', event);
    }

    function resetAll() {
        zoom = 1;
        rotation = 0;
        flipH = false;
        flipV = false;
        crop = {x: 0, y: 0};
    }

    function zoomIn() {
        zoom = Math.min(zoom + 0.5, maxZoom);
    }

    function zoomOut() {
        zoom = Math.max(zoom - 0.5, minZoom);
    }

    function rotateBy(degrees: number) {
        let newRotation = rotation + degrees;
        // Clamp to -180 to +180
        if (newRotation > 180) newRotation = -180 + (newRotation - 180);
        if (newRotation < -180) newRotation = 180 + (newRotation + 180);
        rotation = newRotation;
    }

    function toggleFlipH() {
        flipH = !flipH;
    }

    function toggleFlipV() {
        flipV = !flipV;
    }

    function selectAspect(value: number) {
        currentAspect = value;
    }

    // Export method for parent to get crop area
    export function getCroppedAreaPixels(): CropArea | null {
        return croppedAreaPixels;
    }

    // Export rotation and flip state for crop processing
    export function getTransform(): {rotation: number; flipH: boolean; flipV: boolean} {
        return {rotation, flipH, flipV};
    }

    // Export image dimensions
    export function getImageDimensions(): {width: number; height: number} {
        return {width: imageWidth, height: imageHeight};
    }

    // Re-export CropArea type for consumers
    export type {CropArea};
</script>

<div class="image-cropper">
    <!-- Crop Area -->
    <div class="crop-container">
        <div class="cropper-wrapper" style="transform: scaleX({flipH ? -1 : 1}) scaleY({flipV ? -1 : 1})">
            <Cropper
                image={imageSrc}
                bind:crop
                bind:zoom
                aspect={effectiveAspect}
                {minZoom}
                {maxZoom}
                oncropcomplete={handleCropComplete}
                showGrid={true}
                cropShape="rect"
            />
        </div>

        <!-- Rotation indicator overlay (when rotation != 0) -->
        {#if rotation !== 0}
            <div class="rotation-indicator">
                {$_('uploads.rotationAppliedOnSave') || 'Rotation applied on save'}: {rotation}°
            </div>
        {/if}
    </div>

    <!-- Image Info -->
    {#if imageWidth && imageHeight}
        <div class="image-info">
            <span class="info-text">{$_('uploads.inputSize') || 'Input Size'}: {imageWidth}×{imageHeight}px</span>
            {#if croppedAreaPixels}
                <span class="info-text">{$_('uploads.selectionSize') || 'Selection'}: {Math.round(croppedAreaPixels.width)}×{Math.round(croppedAreaPixels.height)}px</span>
            {/if}
        </div>
    {/if}

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
                {#if currentAspect === 0}
                    <span class="aspect-note">({$_('uploads.freeNote') || 'Uses 4:3'})</span>
                {/if}
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
                    <input
                        type="range"
                        class="slider"
                        min={minZoom}
                        max={maxZoom}
                        step={0.1}
                        bind:value={zoom}
                    />
                    <button type="button" class="control-btn" on:click={zoomIn} title={$_('uploads.zoomIn') || 'Zoom in'}>
                        <ZoomIn size={16} />
                    </button>
                    <span class="value-display">{zoom.toFixed(1)}x</span>
                </div>
            </div>
        {/if}

        <!-- Rotation & Flip Controls -->
        {#if showRotateControls}
            <div class="control-group">
                <span class="control-label">{$_('uploads.rotation') || 'Rotation'}:</span>
                <div class="control-row">
                    <button type="button" class="control-btn" on:click={() => rotateBy(-15)} title="-15°">
                        <Minus size={16} />
                    </button>
                    <input
                        type="range"
                        class="slider rotation-slider"
                        min={-180}
                        max={180}
                        step={1}
                        bind:value={rotation}
                    />
                    <button type="button" class="control-btn" on:click={() => rotateBy(15)} title="+15°">
                        <Plus size={16} />
                    </button>
                    <span class="value-display">{rotation}°</span>
                </div>
            </div>

            <div class="control-group">
                <span class="control-label">{$_('uploads.flip') || 'Flip'}:</span>
                <div class="control-row">
                    <button type="button" class="control-btn" class:active={flipH} on:click={toggleFlipH} title={$_('uploads.flipHorizontal') || 'Flip horizontal'}>
                        <FlipHorizontal size={16} />
                        <span class="btn-label">H</span>
                    </button>
                    <button type="button" class="control-btn" class:active={flipV} on:click={toggleFlipV} title={$_('uploads.flipVertical') || 'Flip vertical'}>
                        <FlipVertical size={16} />
                        <span class="btn-label">V</span>
                    </button>
                    <div class="separator"></div>
                    <button type="button" class="control-btn reset" on:click={resetAll} title={$_('uploads.reset') || 'Reset'}>
                        <RotateCcw size={14} />
                        <span class="btn-label">{$_('uploads.reset') || 'Reset'}</span>
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

    .cropper-wrapper {
        width: 100%;
        height: 100%;
    }

    @media (min-width: 640px) {
        .crop-container {
            height: 400px;
        }
    }

    /* Rotation indicator overlay */
    .rotation-indicator {
        position: absolute;
        bottom: 8px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.75);
        color: #fbbf24;
        font-size: 0.75rem;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        pointer-events: none;
        z-index: 10;
    }

    .image-info {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        justify-content: center;
        padding: 0.5rem;
        background: #f3f4f6;
        border-radius: 0.375rem;
    }

    :global(.dark) .image-info {
        background: #374151;
    }

    .info-text {
        font-size: 0.75rem;
        color: #6b7280;
        font-family: monospace;
    }

    :global(.dark) .info-text {
        color: #9ca3af;
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

    .aspect-note {
        font-size: 0.75rem;
        color: #9ca3af;
        font-style: italic;
    }

    /* Slider */
    .slider {
        flex: 1;
        min-width: 80px;
        height: 6px;
        border-radius: 3px;
        background: #e5e7eb;
        appearance: none;
        cursor: pointer;
    }

    .rotation-slider {
        min-width: 100px;
    }

    .slider::-webkit-slider-thumb {
        appearance: none;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #1a4031;
        cursor: pointer;
    }

    :global(.dark) .slider {
        background: #4b5563;
    }

    :global(.dark) .slider::-webkit-slider-thumb {
        background: #10b981;
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
</style>

