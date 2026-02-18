<!--
  ImageCropper - Interactive image cropping component

  Uses svelte-easy-crop for crop functionality.
  Supports zoom, aspect ratio selection, and real-time preview.
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import Cropper from 'svelte-easy-crop';
    import type {CropArea} from 'svelte-easy-crop';
    import {_} from '$lib/i18n';
    import {ZoomIn, ZoomOut, RotateCcw} from 'lucide-svelte';

    // Props
    export let imageSrc: string;
    export let aspectRatio: number = 1;  // 0 = free, 1 = square, 16/9, etc.
    export let minZoom: number = 1;
    export let maxZoom: number = 3;
    export let showZoomSlider: boolean = true;
    export let showAspectSelector: boolean = false;
    export let aspectOptions: Array<{value: number; label: string}> = [
        {value: 1, label: '1:1'},
        {value: 16/9, label: '16:9'},
        {value: 4/3, label: '4:3'},
        {value: 0, label: 'Free'}
    ];

    const dispatch = createEventDispatcher<{
        cropcomplete: {percent: CropArea; pixels: CropArea};
    }>();

    // Internal state
    let crop = {x: 0, y: 0};
    let zoom = 1;
    let currentAspect = aspectRatio;
    let croppedAreaPixels: CropArea | null = null;

    // Update aspect when prop changes
    $: currentAspect = aspectRatio;

    // Handler for crop complete - use oncropcomplete prop format
    function handleCropComplete(event: {percent: CropArea; pixels: CropArea}) {
        croppedAreaPixels = event.pixels;
        dispatch('cropcomplete', event);
    }

    function resetZoom() {
        zoom = 1;
        crop = {x: 0, y: 0};
    }

    function zoomIn() {
        zoom = Math.min(zoom + 0.2, maxZoom);
    }

    function zoomOut() {
        zoom = Math.max(zoom - 0.2, minZoom);
    }

    function selectAspect(value: number) {
        currentAspect = value;
    }

    // Export method for parent to get crop area
    export function getCroppedAreaPixels(): CropArea | null {
        return croppedAreaPixels;
    }

    // Re-export CropArea type for consumers
    export type {CropArea};
</script>

<div class="image-cropper">
    <!-- Crop Area -->
    <div class="crop-container">
        <Cropper
            image={imageSrc}
            bind:crop
            bind:zoom
            aspect={currentAspect || 1}
            {minZoom}
            {maxZoom}
            oncropcomplete={handleCropComplete}
            showGrid={true}
            cropShape="rect"
        />
    </div>

    <!-- Controls -->
    <div class="controls">
        <!-- Aspect Ratio Selector -->
        {#if showAspectSelector}
            <div class="aspect-selector">
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
            <div class="zoom-controls">
                <span class="control-label">{$_('uploads.zoom') || 'Zoom'}:</span>
                <div class="zoom-row">
                    <button type="button" class="zoom-btn" on:click={zoomOut} title="Zoom out">
                        <ZoomOut size={16} />
                    </button>
                    <input
                        type="range"
                        class="zoom-slider"
                        min={minZoom}
                        max={maxZoom}
                        step={0.1}
                        bind:value={zoom}
                    />
                    <button type="button" class="zoom-btn" on:click={zoomIn} title="Zoom in">
                        <ZoomIn size={16} />
                    </button>
                    <span class="zoom-value">{zoom.toFixed(1)}x</span>
                    <button type="button" class="reset-btn" on:click={resetZoom} title="Reset">
                        <RotateCcw size={14} />
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

    .controls {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        padding: 0.5rem;
    }

    .control-label {
        font-size: 0.875rem;
        font-weight: 500;
        color: #4b5563;
        min-width: 80px;
    }

    :global(.dark) .control-label {
        color: #9ca3af;
    }

    /* Aspect Selector */
    .aspect-selector {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-wrap: wrap;
    }

    .aspect-buttons {
        display: flex;
        gap: 0.5rem;
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

    /* Zoom Controls */
    .zoom-controls {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-wrap: wrap;
    }

    .zoom-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex: 1;
        min-width: 200px;
    }

    .zoom-slider {
        flex: 1;
        height: 6px;
        border-radius: 3px;
        background: #e5e7eb;
        appearance: none;
        cursor: pointer;
    }

    .zoom-slider::-webkit-slider-thumb {
        appearance: none;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #1a4031;
        cursor: pointer;
    }

    :global(.dark) .zoom-slider {
        background: #4b5563;
    }

    :global(.dark) .zoom-slider::-webkit-slider-thumb {
        background: #10b981;
    }

    .zoom-btn,
    .reset-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 0.375rem;
        border: 1px solid #d1d5db;
        background: white;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.15s;
    }

    .zoom-btn:hover,
    .reset-btn:hover {
        border-color: #1a4031;
        color: #1a4031;
    }

    :global(.dark) .zoom-btn,
    :global(.dark) .reset-btn {
        background: #374151;
        border-color: #4b5563;
        color: #9ca3af;
    }

    :global(.dark) .zoom-btn:hover,
    :global(.dark) .reset-btn:hover {
        border-color: #10b981;
        color: #10b981;
    }

    .zoom-value {
        font-size: 0.75rem;
        font-weight: 500;
        color: #6b7280;
        min-width: 2.5rem;
        text-align: center;
    }

    :global(.dark) .zoom-value {
        color: #9ca3af;
    }
</style>

