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

    // Track last initialized src to avoid re-init loops
    let lastInitializedSrc: string | null = null;

    // Update aspect when prop changes
    $: currentAspect = aspectRatio;

    // Reactive: when imageSrc changes, recreate cropper (but only if src actually changed)
    $: if (imageSrc && containerElement && imageSrc !== lastInitializedSrc) {
        lastInitializedSrc = imageSrc;
        initCropper();
    }

    // Middle mouse button drag state
    let isMiddleDragging = false;
    let lastMouseX = 0;
    let lastMouseY = 0;

    onMount(() => {
        // Initial setup handled by reactive block
    });

    onDestroy(() => {
        cropper?.destroy();
        cropper = null;
        // Cleanup event listeners
        document.removeEventListener('mousemove', handleMiddleMouseMove);
        document.removeEventListener('mouseup', handleMiddleMouseUp);
    });

    // Middle mouse button handlers for panning
    function handleMiddleMouseDown(event: MouseEvent) {
        if (event.button === 1) {  // Middle button
            event.preventDefault();
            isMiddleDragging = true;
            lastMouseX = event.clientX;
            lastMouseY = event.clientY;
            document.addEventListener('mousemove', handleMiddleMouseMove);
            document.addEventListener('mouseup', handleMiddleMouseUp);
        }
    }

    function handleMiddleMouseMove(event: MouseEvent) {
        if (!isMiddleDragging) return;

        const img = cropper?.getCropperImage();
        if (img) {
            const deltaX = event.clientX - lastMouseX;
            const deltaY = event.clientY - lastMouseY;
            img.$move(deltaX, deltaY);
            lastMouseX = event.clientX;
            lastMouseY = event.clientY;
        }
    }

    function handleMiddleMouseUp(event: MouseEvent) {
        if (event.button === 1) {
            isMiddleDragging = false;
            document.removeEventListener('mousemove', handleMiddleMouseMove);
            document.removeEventListener('mouseup', handleMiddleMouseUp);
        }
    }

    async function initCropper() {
        // Wait for DOM update
        await tick();

        // Destroy previous instance if exists
        if (cropper) {
            cropper.destroy();
            cropper = null;
        }

        // Clear container
        if (containerElement) {
            containerElement.innerHTML = '';
        }

        if (!imageSrc || !containerElement) {
            return;
        }

        // Determine aspect ratio (0 or NaN = free)
        const effectiveAspect = (currentAspect === 0 || isNaN(currentAspect)) ? NaN : currentAspect;

        // Create image element first (cropperjs v2 needs an element, not a URL)
        const imgElement = document.createElement('img');
        imgElement.style.display = 'block';
        imgElement.style.maxWidth = '100%';
        imgElement.crossOrigin = 'anonymous';

        // Wait for image to load before creating cropper
        try {
            await new Promise<void>((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Image load timeout'));
                }, 10000); // 10 second timeout

                imgElement.onload = () => {
                    clearTimeout(timeout);
                    imageWidth = imgElement.naturalWidth;
                    imageHeight = imgElement.naturalHeight;
                    resolve();
                };
                imgElement.onerror = () => {
                    clearTimeout(timeout);
                    reject(new Error('Failed to load image'));
                };

                // Set src AFTER setting handlers
                imgElement.src = imageSrc;
            });
        } catch (e) {
            console.error('Image load error:', e);
            return;
        }

        // Append image to container
        containerElement.appendChild(imgElement);

        // Small delay to ensure DOM is ready
        await new Promise(resolve => setTimeout(resolve, 50));

        // Create new Cropper instance with v2 API
        cropper = new Cropper(imgElement, {
            container: containerElement,
        });

        // Wait for cropper to be ready
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
            cropperSelection.zoomable = false;
            cropperSelection.multiple = false;
            cropperSelection.keyboard = false;
            cropperSelection.slottable = false;  // Prevent drawing new selections

            // Configure image - allow dragging
            cropperImage.rotatable = true;
            cropperImage.scalable = true;
            cropperImage.translatable = true;

            // Configure canvas
            cropperCanvas.background = true;
            cropperCanvas.slottable = false;  // Prevent drawing new selections on canvas

            // Change "select" handle to "move" so clicking outside selection moves the image
            // instead of creating a new selection
            const selectHandle = cropperCanvas.querySelector('cropper-handle[action="select"]');
            if (selectHandle) {
                // Change action from "select" to "move" - this makes the canvas draggable
                selectHandle.setAttribute('action', 'move');
            }

            // NOTE: Shade overlay is configured via CSS Variables (--theme-color)
            // on cropper-canvas, not via JavaScript setAttribute

            // Function to update selection info
            const updateSelectionInfo = () => {
                cropWidth = Math.round(cropperSelection.width || 0);
                cropHeight = Math.round(cropperSelection.height || 0);
                dispatch('change', {
                    selection: {
                        x: cropperSelection.x || 0,
                        y: cropperSelection.y || 0,
                        width: cropWidth,
                        height: cropHeight
                    }
                });
            };

            // Listen for changes (resize, move, etc.)
            cropperSelection.addEventListener('change', updateSelectionInfo);

            // Initial update after a short delay to let cropperjs initialize
            setTimeout(updateSelectionInfo, 100);

            // Image dimensions already loaded above
        }
    }

    // Helper: convert degrees to radians
    function degreesToRadians(degrees: number): number {
        return degrees * (Math.PI / 180);
    }

    // Zoom thresholds for unified zoom behavior
    const MIN_SELECTION_SIZE = 50;  // Minimum selection size in pixels before switching to image zoom
    const MAX_SELECTION_COVERAGE = 0.95;  // Maximum coverage of canvas before switching to image zoom

    /**
     * Unified zoom system:
     * - Zoom IN: first enlarge selection, then zoom image when selection is at max
     * - Zoom OUT: first shrink selection, then dezoom image when selection is at min
     */
    function zoomIn() {
        const sel = cropper?.getCropperSelection();
        const canvas = cropper?.getCropperCanvas();
        const img = cropper?.getCropperImage();

        if (!sel || !canvas || !img) return;

        const canvasRect = canvas.getBoundingClientRect();
        const imgRect = img.getBoundingClientRect();

        // Check if selection is near maximum size (relative to visible image)
        const selectionCoverageW = sel.width / Math.min(canvasRect.width, imgRect.width);
        const selectionCoverageH = sel.height / Math.min(canvasRect.height, imgRect.height);
        const maxCoverage = Math.max(selectionCoverageW, selectionCoverageH);

        if (maxCoverage >= MAX_SELECTION_COVERAGE) {
            // Selection at max - zoom the image instead
            img.$zoom(0.1);
            currentZoom += 0.1;
        } else {
            // Enlarge selection by 10%
            scaleSelection(1.1);
        }
    }

    function zoomOut() {
        const sel = cropper?.getCropperSelection();
        const img = cropper?.getCropperImage();

        if (!sel || !img) return;

        // Check if selection is at minimum size
        const minDimension = Math.min(sel.width, sel.height);

        if (minDimension <= MIN_SELECTION_SIZE) {
            // Selection at min - dezoom the image instead
            img.$zoom(-0.1);
            currentZoom -= 0.1;
        } else {
            // Shrink selection by 10%
            scaleSelection(0.9);
        }
    }

    /**
     * Scale selection around its center while respecting aspect ratio
     */
    function scaleSelection(factor: number) {
        const sel = cropper?.getCropperSelection();
        const canvas = cropper?.getCropperCanvas();
        const img = cropper?.getCropperImage();

        if (!sel || !canvas || !img) return;

        const canvasRect = canvas.getBoundingClientRect();
        const imgRect = img.getBoundingClientRect();

        // Current selection center
        const centerX = sel.x + sel.width / 2;
        const centerY = sel.y + sel.height / 2;

        // New dimensions
        let newWidth = sel.width * factor;
        let newHeight = sel.height * factor;

        // Constrain to min size
        if (newWidth < MIN_SELECTION_SIZE || newHeight < MIN_SELECTION_SIZE) {
            return;
        }

        // Constrain to canvas/image bounds
        const maxWidth = Math.min(canvasRect.width, imgRect.width);
        const maxHeight = Math.min(canvasRect.height, imgRect.height);

        if (newWidth > maxWidth) {
            const ratio = maxWidth / newWidth;
            newWidth = maxWidth;
            newHeight *= ratio;
        }
        if (newHeight > maxHeight) {
            const ratio = maxHeight / newHeight;
            newHeight = maxHeight;
            newWidth *= ratio;
        }

        // Calculate image bounds relative to canvas
        const imgX = imgRect.left - canvasRect.left;
        const imgY = imgRect.top - canvasRect.top;

        // New position (centered)
        let newX = centerX - newWidth / 2;
        let newY = centerY - newHeight / 2;

        // Keep selection within image bounds
        newX = Math.max(imgX, Math.min(newX, imgX + imgRect.width - newWidth));
        newY = Math.max(imgY, Math.min(newY, imgY + imgRect.height - newHeight));

        // Apply new dimensions
        sel.x = newX;
        sel.y = newY;
        sel.width = newWidth;
        sel.height = newHeight;

        // Update display info
        cropWidth = Math.round(newWidth);
        cropHeight = Math.round(newHeight);
    }

    function resetZoom() {
        const img = cropper?.getCropperImage();
        if (img) {
            img.$center('contain');
            currentZoom = 1;
        }
        // Also reset selection to 80% coverage
        setTimeout(() => {
            const sel = cropper?.getCropperSelection();
            if (sel) {
                sel.$center();
            }
        }, 50);
    }

    function rotateLeft() {
        rotateImage(-15);
    }

    function rotateRight() {
        rotateImage(15);
    }

    /**
     * Rotate image around the center of the selection.
     *
     * The challenge: cropperjs rotates around the image's visual center,
     * but we want to rotate around the selection center.
     *
     * Solution: Use the cropper-image element's bounding rect directly
     * (it IS the visible image area) to find the visual center.
     */
    function rotateImage(degrees: number) {
        const img = cropper?.getCropperImage();
        const sel = cropper?.getCropperSelection();
        const canvas = cropper?.getCropperCanvas();
        if (!img || !canvas) return;

        const radians = degreesToRadians(degrees);

        if (sel && sel.width > 0 && sel.height > 0) {
            // Get the actual visual bounds of canvas
            const canvasRect = canvas.getBoundingClientRect();

            // The cropper-image element itself represents the transformed image
            // Its bounding rect gives us the visual bounds after all transforms
            const imgRect = img.getBoundingClientRect();

            // Image center in canvas coordinates (relative to canvas top-left)
            const imgCenterX = (imgRect.left + imgRect.width / 2) - canvasRect.left;
            const imgCenterY = (imgRect.top + imgRect.height / 2) - canvasRect.top;

            // Selection center in canvas coordinates
            const selCenterX = sel.x + sel.width / 2;
            const selCenterY = sel.y + sel.height / 2;

            // Vector from image center (pivot) to selection center
            const dx = selCenterX - imgCenterX;
            const dy = selCenterY - imgCenterY;

            // After rotation, this vector becomes:
            const cos = Math.cos(radians);
            const sin = Math.sin(radians);
            const dxRotated = dx * cos - dy * sin;
            const dyRotated = dx * sin + dy * cos;

            // Compensation needed to keep selection center fixed
            const compensateX = dx - dxRotated;
            const compensateY = dy - dyRotated;

            // Apply rotation then translation
            img.$rotate(radians);
            img.$move(compensateX, compensateY);
        } else {
            // No selection - simple rotation
            img.$rotate(radians);
        }

        // Update rotation state
        currentRotation += degrees;
        if (currentRotation > 180) currentRotation -= 360;
        if (currentRotation < -180) currentRotation += 360;
    }

    function resetRotation() {
        // Reset by re-initializing (v2 doesn't have rotateTo)
        currentRotation = 0;
        forceReinit();
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

        // Reset image transform and selection
        const img = cropper?.getCropperImage();
        const sel = cropper?.getCropperSelection();
        const canvas = cropper?.getCropperCanvas();

        if (img && sel && canvas) {
            // Reset image to initial state
            img.$resetTransform();
            img.$center('contain');

            // Wait for transform to settle, then position selection on the image
            setTimeout(() => {
                // Get the image's bounding box in canvas space
                // The cropper-image element itself represents the transformed image
                const imgRect = img.getBoundingClientRect();
                const canvasRect = canvas.getBoundingClientRect();

                // Calculate image position relative to canvas
                const imgX = imgRect.left - canvasRect.left;
                const imgY = imgRect.top - canvasRect.top;
                const imgW = imgRect.width;
                const imgH = imgRect.height;

                if (isNaN(currentAspect) || currentAspect === 0) {
                    // Free aspect - selection covers full image
                    sel.x = imgX;
                    sel.y = imgY;
                    sel.width = imgW;
                    sel.height = imgH;
                } else {
                    // Fixed aspect - center on image with 80% coverage
                    const coverage = 0.8;
                    // Calculate max size that fits in image with aspect ratio
                    let newW, newH;
                    if (imgW / imgH > currentAspect) {
                        // Image wider than aspect - height limited
                        newH = imgH * coverage;
                        newW = newH * currentAspect;
                    } else {
                        // Image taller than aspect - width limited
                        newW = imgW * coverage;
                        newH = newW / currentAspect;
                    }
                    sel.x = imgX + (imgW - newW) / 2;
                    sel.y = imgY + (imgH - newH) / 2;
                    sel.width = newW;
                    sel.height = newH;
                }
            }, 100);
        } else {
            // Fallback: full re-init
            forceReinit();
        }
    }

    // Force re-initialization of cropper (for reset functions)
    function forceReinit() {
        lastInitializedSrc = null;
        if (imageSrc && containerElement) {
            lastInitializedSrc = imageSrc;
            initCropper();
        }
    }

    function selectAspect(value: number) {
        currentAspect = value;
        const sel = cropper?.getCropperSelection();
        if (!sel) return;

        const effectiveAspect = (value === 0 || isNaN(value)) ? NaN : value;

        // Get current selection dimensions and center
        const oldWidth = sel.width;
        const oldHeight = sel.height;
        const centerX = sel.x + oldWidth / 2;
        const centerY = sel.y + oldHeight / 2;

        // Calculate current diagonal
        const oldDiagonal = Math.sqrt(oldWidth * oldWidth + oldHeight * oldHeight);

        // Calculate new dimensions that maintain the same diagonal length
        let newWidth: number, newHeight: number;

        if (isNaN(effectiveAspect)) {
            // Free aspect - keep current dimensions
            newWidth = oldWidth;
            newHeight = oldHeight;
        } else {
            // For aspect ratio r = w/h, and diagonal d:
            // w^2 + h^2 = d^2
            // w = r * h
            // (r*h)^2 + h^2 = d^2
            // h^2 * (r^2 + 1) = d^2
            // h = d / sqrt(r^2 + 1)
            newHeight = oldDiagonal / Math.sqrt(effectiveAspect * effectiveAspect + 1);
            newWidth = effectiveAspect * newHeight;
        }

        // Calculate new position to keep centered
        const newX = centerX - newWidth / 2;
        const newY = centerY - newHeight / 2;

        // Apply new aspect ratio and dimensions
        sel.aspectRatio = effectiveAspect;
        sel.$change(newX, newY, newWidth, newHeight);
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
    <!-- Crop Area with controls overlay -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
        class="crop-wrapper"
        on:mousedown={handleMiddleMouseDown}
        on:contextmenu|preventDefault
    >
        <div class="crop-container" bind:this={containerElement}>
            <!-- Cropper v2 creates its own DOM structure here -->
        </div>

        <!-- Controls overlay - right side -->
        {#if showZoomSlider || showRotateControls}
            <div class="controls-overlay">
                {#if showZoomSlider}
                    <button type="button" class="overlay-btn" on:click={zoomOut} title={$_('uploads.zoomOut') || 'Zoom out'}>
                        <ZoomOut size={16} />
                    </button>
                    <button type="button" class="overlay-btn" on:click={zoomIn} title={$_('uploads.zoomIn') || 'Zoom in'}>
                        <ZoomIn size={16} />
                    </button>
                {/if}

                {#if showRotateControls}
                    <button type="button" class="overlay-btn" on:click={rotateLeft} title="-15°">
                        <RotateCcw size={16} />
                    </button>
                    <button type="button" class="overlay-btn" on:click={rotateRight} title="+15°">
                        <RotateCw size={16} />
                    </button>
                {/if}

                <button type="button" class="overlay-btn reset" on:click={resetAll} title={$_('uploads.resetAll') || 'Reset All'}>
                    <RefreshCw size={14} />
                </button>
            </div>
        {/if}
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

    <!-- BOTTOM CONTROLS: Preset & Flip -->
    <div class="bottom-controls">
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

        <!-- Flip Controls -->
        {#if showRotateControls}
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

    /* Crop wrapper with overlay controls */
    .crop-wrapper {
        position: relative;
        width: 100%;
    }

    /* Controls overlay - positioned on right side of image */
    .controls-overlay {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        z-index: 10;
        background: rgba(0, 0, 0, 0.5);
        padding: 0.25rem;
        border-radius: 0.375rem;
    }

    .overlay-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border: none;
        border-radius: 0.25rem;
        background: rgba(255, 255, 255, 0.9);
        color: #374151;
        cursor: pointer;
        transition: all 0.15s;
    }

    .overlay-btn:hover {
        background: white;
        color: #1a4031;
    }

    .overlay-btn.reset {
        background: rgba(239, 68, 68, 0.9);
        color: white;
    }

    .overlay-btn.reset:hover {
        background: #dc2626;
    }

    /* Bottom controls - Preset & Flip */
    .bottom-controls {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        padding: 0.5rem;
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

    .control-btn:hover {
        border-color: #1a4031;
        color: #1a4031;
    }

    .control-btn.active {
        background: #1a4031;
        border-color: #1a4031;
        color: white;
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

    .btn-label {
        font-size: 0.75rem;
    }



    /* ==========================================================================
       CROPPERJS V2 - CLEAN CORNER HANDLES STYLE (like reference image)
       Solo linee bianche agli angoli, niente punti o quadrati
       ========================================================================== */

    /* Configurazione Variabili Globali per Cropper v2 */
    .crop-container :global(cropper-canvas) {
        /* Questa è la chiave per l'overlay scuro - usa CSS Variables */
        --theme-color: rgba(0, 0, 0, 0.5);
        --cropper-backdrop-color: rgba(0, 0, 0, 0.3);
    }

    /* Hide ALL default cropper visual elements that we don't want */
    .crop-container :global(cropper-handle) {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* Hide any default blue points/dots */
    .crop-container :global(cropper-handle)::before,
    .crop-container :global(cropper-handle)::after {
        display: none !important;
    }

    /* Hide crosshair if present */
    .crop-container :global(cropper-crosshair) {
        display: none !important;
    }

    /* Selection box - white outline, TRANSPARENT inside (show original image) */
    .crop-container :global(cropper-selection) {
        --cropper-selection-outline-width: 2px;
        --cropper-selection-outline-color: rgba(255, 255, 255, 0.9);
        outline: 2px solid rgba(255, 255, 255, 0.9) !important;
        outline-offset: -1px;
        background-color: transparent !important;
        background: transparent !important;
    }

    /* Make sure selection area shows the image clearly (no overlay) */
    .crop-container :global(cropper-selection)::before,
    .crop-container :global(cropper-selection)::after {
        display: none !important;
    }


    /* Corner handles - L-shaped white lines */
    .crop-container :global(cropper-handle[action="nw-resize"]) {
        width: 20px !important;
        height: 20px !important;
        background: transparent !important;
        border-top: 3px solid white !important;
        border-left: 3px solid white !important;
        border-right: none !important;
        border-bottom: none !important;
    }

    .crop-container :global(cropper-handle[action="ne-resize"]) {
        width: 20px !important;
        height: 20px !important;
        background: transparent !important;
        border-top: 3px solid white !important;
        border-right: 3px solid white !important;
        border-left: none !important;
        border-bottom: none !important;
    }

    .crop-container :global(cropper-handle[action="sw-resize"]) {
        width: 20px !important;
        height: 20px !important;
        background: transparent !important;
        border-bottom: 3px solid white !important;
        border-left: 3px solid white !important;
        border-top: none !important;
        border-right: none !important;
    }

    .crop-container :global(cropper-handle[action="se-resize"]) {
        width: 20px !important;
        height: 20px !important;
        background: transparent !important;
        border-bottom: 3px solid white !important;
        border-right: 3px solid white !important;
        border-top: none !important;
        border-left: none !important;
    }

    /* Side handles - thin white lines */
    .crop-container :global(cropper-handle[action="n-resize"]),
    .crop-container :global(cropper-handle[action="s-resize"]) {
        width: 40px !important;
        height: 3px !important;
        background-color: white !important;
        border: none !important;
        border-radius: 0 !important;
    }

    .crop-container :global(cropper-handle[action="e-resize"]),
    .crop-container :global(cropper-handle[action="w-resize"]) {
        width: 3px !important;
        height: 40px !important;
        background-color: white !important;
        border: none !important;
        border-radius: 0 !important;
    }

    /* Grid lines inside selection - subtle */
    .crop-container :global(cropper-grid) {
        opacity: 0.3;
    }

    /* ==========================================================================
       DARK MODE OVERRIDES
       ========================================================================== */

    :global(.dark) .crop-container :global(cropper-canvas) {
        --theme-color: rgba(0, 0, 0, 0.7);
        --cropper-backdrop-color: rgba(0, 0, 0, 0.8);
    }

    :global(.dark) .crop-container :global(cropper-selection) {
        --cropper-selection-outline-color: rgba(255, 255, 255, 0.9);
        outline-color: rgba(255, 255, 255, 0.9) !important;
    }


    /* Dark mode handles - keep white, no green */
    :global(.dark) .crop-container :global(cropper-handle) {
        background-color: transparent !important;
        border-color: white !important;
    }

    :global(.dark) .crop-container :global(cropper-handle[action="n-resize"]),
    :global(.dark) .crop-container :global(cropper-handle[action="s-resize"]),
    :global(.dark) .crop-container :global(cropper-handle[action="e-resize"]),
    :global(.dark) .crop-container :global(cropper-handle[action="w-resize"]) {
        background-color: white !important;
    }
</style>
