<!--
  ImageCropper - Interactive image cropping component

  Uses cropperjs v2 (Web Components) for full-featured crop functionality.
  Supports zoom, rotation (live preview), flip, aspect ratio selection, free crop with handles.
-->
<script lang="ts">
    import {createEventDispatcher, onDestroy, onMount, tick} from 'svelte';
    import Cropper from 'cropperjs';
    // Note: cropperjs v2 uses Web Components, CSS is built-in
    import {_} from '$lib/i18n';
    import {FlipHorizontal, FlipVertical, RotateCcw, RotateCw, ZoomIn, ZoomOut} from 'lucide-svelte';

    // Props
    export let imageSrc: string;
    export let aspectRatio: number = 1;  // NaN or 0 = free, 1 = square, 16/9, etc.
    export let showZoomSlider: boolean = true;
    export let showRotateControls: boolean = true;

    const dispatch = createEventDispatcher<{
        change: { selection: { x: number; y: number; width: number; height: number } };
    }>();

    /** Helper to emit current selection state as a 'change' event */
    function dispatchCurrentChange() {
        const sel = cropper?.getCropperSelection();
        if (sel) {
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
        }
    }

    // Internal state
    let containerElement: HTMLDivElement;
    let cropWrapperElement: HTMLDivElement;
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

    // Guard against infinite event loop from clamping
    let isClamping = false;

    // Ready flag — true when cropper is fully initialized
    let cropperReady = false;

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
        // Register wheel listener with passive: false to allow preventDefault()
        // This avoids Chrome's "Added non-passive event listener to scroll-blocking 'wheel' event" warning
        if (cropWrapperElement) {
            cropWrapperElement.addEventListener('wheel', handleWheel, {passive: false});
        }
    });

    onDestroy(() => {
        cropper?.destroy();
        cropper = null;
        cropperReady = false;
        // Cleanup event listeners
        if (cropWrapperElement) {
            cropWrapperElement.removeEventListener('wheel', handleWheel);
        }
        document.removeEventListener('mousemove', handleMiddleMouseMove);
        document.removeEventListener('mouseup', handleMiddleMouseUp);
        document.removeEventListener('pointerup', stopActiveClamping);
        document.removeEventListener('pointercancel', stopActiveClamping);
    });

    // Placeholder for active clamping cleanup (set in initCropper)
    let stopActiveClamping: () => void = () => {
    };

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

    /**
     * Handle mouse wheel for unified zoom
     * - Wheel up: zoom in (enlarge selection, then zoom image)
     * - Wheel down: zoom out (shrink selection, then dezoom image)
     */
    function handleWheel(event: WheelEvent) {
        event.preventDefault();

        // deltaY < 0 = wheel up = zoom in
        // deltaY > 0 = wheel down = zoom out
        if (event.deltaY < 0) {
            zoomIn();
        } else {
            zoomOut();
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

            // Function to clamp selection within canvas bounds (uses atomic $change)
            let clampDepth = 0;
            let clampRAF: number | null = null;

            const clampSelectionToBounds = () => {
                if (isClamping || clampDepth > 2) return; // Prevent infinite loop + safety valve
                clampDepth++;

                const canvasRect = cropperCanvas.getBoundingClientRect();
                if (canvasRect.width === 0 || canvasRect.height === 0) {
                    clampDepth--;
                    return;
                }

                // Use canvas bounds as the constraint area
                const maxW = canvasRect.width;
                const maxH = canvasRect.height;

                let x = cropperSelection.x;
                let y = cropperSelection.y;
                let w = cropperSelection.width;
                let h = cropperSelection.height;

                // Clamp dimensions to canvas size
                if (w > maxW) w = maxW;
                if (h > maxH) h = maxH;

                // Clamp position - ensure selection stays entirely within canvas
                if (x < 0) x = 0;
                if (y < 0) y = 0;
                if (x + w > maxW) x = Math.max(0, maxW - w);
                if (y + h > maxH) y = Math.max(0, maxH - h);

                // Check if anything actually changed (tight threshold)
                const needsUpdate =
                    Math.abs(x - cropperSelection.x) > 0.1 ||
                    Math.abs(y - cropperSelection.y) > 0.1 ||
                    Math.abs(w - cropperSelection.width) > 0.1 ||
                    Math.abs(h - cropperSelection.height) > 0.1;

                if (needsUpdate) {
                    // Use atomic $change to avoid triggering multiple change events
                    isClamping = true;
                    cropperSelection.$change(x, y, w, h);
                    // Release guard after the frame settles, then update overlay
                    requestAnimationFrame(() => {
                        isClamping = false;
                        clampDepth = 0;
                        // Update ellipse overlay after clamping
                        updateEllipseOverlay();
                    });
                } else {
                    clampDepth--;
                    // Still update ellipse overlay to stay in sync
                    updateEllipseOverlay();
                }
            };

            // Active clamping during pointer interaction (prevents visible overflow)
            let isPointerActive = false;
            const startActiveClamp = () => {
                isPointerActive = true;
                const loop = () => {
                    if (!isPointerActive) return;
                    clampSelectionToBounds();
                    clampRAF = requestAnimationFrame(loop);
                };
                loop();
            };
            const stopActiveClamp = () => {
                isPointerActive = false;
                if (clampRAF) {
                    cancelAnimationFrame(clampRAF);
                    clampRAF = null;
                }
                // One final clamp
                clampSelectionToBounds();
            };

            // Listen for pointer events on selection to actively clamp during drag
            cropperSelection.addEventListener('pointerdown', startActiveClamp);
            document.addEventListener('pointerup', stopActiveClamp);
            document.addEventListener('pointercancel', stopActiveClamp);
            // Save reference for cleanup
            stopActiveClamping = stopActiveClamp;

            // Function to update selection info
            const updateSelectionInfo = () => {
                if (isClamping) return; // Skip if clamping is in progress

                // Update display values first
                clampSelectionToBounds();

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
                // Update ellipse overlay position
                updateEllipseOverlay();
            };

            // Listen for changes (resize, move, etc.)
            cropperSelection.addEventListener('change', updateSelectionInfo);

            // Initial update after a short delay to let cropperjs initialize
            setTimeout(updateSelectionInfo, 100);

            // Image dimensions already loaded above
            cropperReady = true;
        }
    }

    // Helper: convert degrees to radians
    function degreesToRadians(degrees: number): number {
        return degrees * (Math.PI / 180);
    }

    // Zoom thresholds for unified zoom behavior (percentages)
    const MIN_SELECTION_COVERAGE = 0.50;  // Minimum 50% coverage before switching to image dezoom
    const MAX_SELECTION_COVERAGE = 0.90;  // Maximum 90% coverage before switching to image zoom

    /**
     * Unified zoom system:
     * - Zoom IN (+): first SHRINK selection (crop tighter), then zoom image when selection is at minimum
     * - Zoom OUT (-): first ENLARGE selection (crop wider), then dezoom image when selection is at maximum
     */
    function zoomIn() {
        const sel = cropper?.getCropperSelection();
        const canvas = cropper?.getCropperCanvas();
        const img = cropper?.getCropperImage();

        if (!sel || !canvas || !img) return;

        const canvasRect = canvas.getBoundingClientRect();
        const imgRect = img.getBoundingClientRect();

        // Use the smaller of canvas and image for bounds
        const maxW = Math.min(canvasRect.width, imgRect.width);
        const maxH = Math.min(canvasRect.height, imgRect.height);

        // Coverage per axis
        const coverageW = sel.width / maxW;
        const coverageH = sel.height / maxH;

        // If ANY axis is at min coverage, zoom the image (enlarge background)
        if (coverageW <= MIN_SELECTION_COVERAGE || coverageH <= MIN_SELECTION_COVERAGE) {
            img.$zoom(0.1);
            currentZoom += 0.1;
        } else {
            // Shrink selection by 10% (crop tighter)
            scaleSelection(0.9);
        }
    }

    function zoomOut() {
        const sel = cropper?.getCropperSelection();
        const canvas = cropper?.getCropperCanvas();
        const img = cropper?.getCropperImage();

        if (!sel || !canvas || !img) return;

        const canvasRect = canvas.getBoundingClientRect();
        const imgRect = img.getBoundingClientRect();

        // Use the smaller of canvas and image for bounds
        const maxW = Math.min(canvasRect.width, imgRect.width);
        const maxH = Math.min(canvasRect.height, imgRect.height);

        // Coverage per axis
        const coverageW = sel.width / maxW;
        const coverageH = sel.height / maxH;

        // If ANY axis is at max coverage, dezoom the image (shrink background)
        if (coverageW >= MAX_SELECTION_COVERAGE || coverageH >= MAX_SELECTION_COVERAGE) {
            img.$zoom(-0.1);
            currentZoom -= 0.1;
        } else {
            // Enlarge selection by 10% (crop wider)
            scaleSelection(1.1);
        }
    }

    /**
     * Scale selection around its center while respecting aspect ratio.
     * Selection is always constrained to stay within canvas AND image bounds.
     */
    function scaleSelection(factor: number) {
        const sel = cropper?.getCropperSelection();
        const canvas = cropper?.getCropperCanvas();
        const img = cropper?.getCropperImage();

        if (!sel || !canvas || !img) return;

        const canvasRect = canvas.getBoundingClientRect();
        const imgRect = img.getBoundingClientRect();

        // Calculate valid bounds (intersection of canvas and image)
        const imgX = imgRect.left - canvasRect.left;
        const imgY = imgRect.top - canvasRect.top;

        // Effective bounds: intersection of canvas (0,0 to w,h) and image position
        const boundsLeft = Math.max(0, imgX);
        const boundsTop = Math.max(0, imgY);
        const boundsRight = Math.min(canvasRect.width, imgX + imgRect.width);
        const boundsBottom = Math.min(canvasRect.height, imgY + imgRect.height);
        const boundsWidth = boundsRight - boundsLeft;
        const boundsHeight = boundsBottom - boundsTop;

        // Current selection center
        const centerX = sel.x + sel.width / 2;
        const centerY = sel.y + sel.height / 2;

        // New dimensions
        let newWidth = sel.width * factor;
        let newHeight = sel.height * factor;

        // Minimum size: 20% of bounds or 30px, whichever is larger
        const minSize = Math.max(30, Math.min(boundsWidth, boundsHeight) * 0.2);
        if (newWidth < minSize || newHeight < minSize) {
            return;
        }

        // Maximum size: constrain to bounds
        if (newWidth > boundsWidth) {
            const ratio = boundsWidth / newWidth;
            newWidth = boundsWidth;
            newHeight *= ratio;
        }
        if (newHeight > boundsHeight) {
            const ratio = boundsHeight / newHeight;
            newHeight = boundsHeight;
            newWidth *= ratio;
        }

        // New position (centered on original center)
        let newX = centerX - newWidth / 2;
        let newY = centerY - newHeight / 2;

        // Clamp to stay within bounds
        newX = Math.max(boundsLeft, Math.min(newX, boundsRight - newWidth));
        newY = Math.max(boundsTop, Math.min(newY, boundsBottom - newHeight));

        // Apply new dimensions
        sel.x = newX;
        sel.y = newY;
        sel.width = newWidth;
        sel.height = newHeight;

        // Update display info
        cropWidth = Math.round(newWidth);
        cropHeight = Math.round(newHeight);
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

        // Notify parent of change
        dispatchCurrentChange();
    }


    function flipH() {
        const img = cropper?.getCropperImage();
        if (img) {
            scaleX = scaleX === 1 ? -1 : 1;
            img.$scale(scaleX, scaleY);
            dispatchCurrentChange();
        }
    }

    function flipV() {
        const img = cropper?.getCropperImage();
        if (img) {
            scaleY = scaleY === 1 ? -1 : 1;
            img.$scale(scaleX, scaleY);
            dispatchCurrentChange();
        }
    }

    export function resetAll() {
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
                    // Free aspect: selection EXACTLY on image, no extra margin
                    sel.x = imgX;
                    sel.y = imgY;
                    sel.width = imgW;
                    sel.height = imgH;
                } else {
                    // Fixed aspect: max size that fits in image, centered
                    let newW, newH;
                    if (imgW / imgH > currentAspect) {
                        // Image wider than aspect - height limited
                        newH = imgH;
                        newW = newH * currentAspect;
                    } else {
                        // Image taller than aspect - width limited
                        newW = imgW;
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

    export function selectAspect(value: number) {
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

    export function getImageDimensions(): { width: number; height: number } {
        return {width: imageWidth, height: imageHeight};
    }


    // Preview ellipse overlay
    export let showPreviewEllipse: boolean = false;

    // Ellipse overlay position (tracks selection in crop-container coordinates)
    let ellipseStyle = '';

    // Update ellipse overlay position to match selection
    function updateEllipseOverlay() {
        if (!showPreviewEllipse) {
            ellipseStyle = '';
            return;
        }
        const sel = cropper?.getCropperSelection();
        if (!sel) {
            ellipseStyle = '';
            return;
        }
        ellipseStyle = `left:${sel.x}px;top:${sel.y}px;width:${sel.width}px;height:${sel.height}px;`;
    }

    // React to showPreviewEllipse changes + selection changes
    $: if (showPreviewEllipse) updateEllipseOverlay();
    $: if (cropWidth || cropHeight) updateEllipseOverlay();

</script>

<div class="image-cropper" data-cropper-ready={cropperReady || undefined} data-testid="image-cropper">
    <!-- Crop Area with controls overlay -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
            bind:this={cropWrapperElement}
            class="crop-wrapper"
            on:contextmenu|preventDefault
            on:mousedown={handleMiddleMouseDown}
    >
        <div bind:this={containerElement} class="crop-container">
            <!-- Cropper v2 creates its own DOM structure here -->
        </div>

        <!-- Ellipse preview overlay: a real DOM element positioned over the selection -->
        {#if showPreviewEllipse && ellipseStyle}
            <div class="ellipse-overlay" style={ellipseStyle}></div>
        {/if}

        <!-- Controls overlay - right side -->
        {#if showZoomSlider || showRotateControls}
            <div class="controls-overlay">
                {#if showZoomSlider}
                    <button type="button" class="overlay-btn" on:click={zoomOut} title={$_('uploads.zoomOut') || 'Zoom out'} data-testid="cropper-zoom-out">
                        <ZoomOut size={16}/>
                    </button>
                    <button type="button" class="overlay-btn" on:click={zoomIn} title={$_('uploads.zoomIn') || 'Zoom in'} data-testid="cropper-zoom-in">
                        <ZoomIn size={16}/>
                    </button>
                {/if}

                {#if showRotateControls}
                    <button type="button" class="overlay-btn" on:click={rotateLeft} title="-15°" data-testid="cropper-rotate-left">
                        <RotateCcw size={16}/>
                    </button>
                    <button type="button" class="overlay-btn" on:click={rotateRight} title="+15°" data-testid="cropper-rotate-right">
                        <RotateCw size={16}/>
                    </button>

                    <div class="overlay-separator"></div>

                    <button type="button" class="overlay-btn" class:active={scaleX === -1} on:click={flipH} title={$_('uploads.flipHorizontal') || 'Flip H'}
                            data-testid="cropper-flip-h">
                        <FlipHorizontal size={16}/>
                    </button>
                    <button type="button" class="overlay-btn" class:active={scaleY === -1} on:click={flipV} title={$_('uploads.flipVertical') || 'Flip V'}
                            data-testid="cropper-flip-v">
                        <FlipVertical size={16}/>
                    </button>
                {/if}
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
        overflow: hidden;
        border-radius: 0.5rem;
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

    .overlay-btn.active {
        background: rgba(16, 185, 129, 0.9);
        color: white;
    }

    .overlay-btn.active:hover {
        background: #059669;
    }

    .overlay-separator {
        width: 24px;
        height: 1px;
        background: rgba(255, 255, 255, 0.3);
        margin: 0.125rem auto;
    }

    /* Ellipse preview overlay - positioned real DOM element on top of crop-container */
    .ellipse-overlay {
        position: absolute;
        border-radius: 50%;
        box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.45);
        border: 2px solid rgba(255, 255, 255, 0.5);
        pointer-events: none;
        z-index: 5;
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
