<!--
  ImageEditModal - Modal for editing/cropping images before upload

  Features:
  - Wraps ImageCropper with modal UI
  - Preset configurations for different use cases
  - Handles upload to backend and returns URL
  - Editable output size with scale factor
  - Preview ellipse overlay for circular crops
  - Quality control for JPEG/WebP
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {Eye, EyeOff, Loader2, Lock, RefreshCw, Upload, X} from 'lucide-svelte';
    import {uploadFile} from '$lib/utils/files/upload';
    import ImageCropper from './ImageCropper.svelte';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import {blobToFile, getCroppedImageFromCropper, IMAGE_PRESETS, type PresetName} from '$lib/utils/files/imageCrop';

    // Props
    export let open: boolean = false;
    export let file: File | null = null;
    export let preset: PresetName = 'custom';
    export let customConfig: Partial<{aspectRatio: number; outputWidth: number | null; outputHeight: number | null; outputQuality: number}> | null = null;
    export let allowPresetChange: boolean = true;
    export let uploadOnComplete: boolean = true;

    type _DispatchEvents = {
        complete: {url: string | null; file: File};
        cancel: void;
        error: {message: string};
    };
    const dispatch = createEventDispatcher();

    const presetOptions: Array<{value: PresetName; labelKey: string}> = [
        {value: 'avatar', labelKey: 'common.avatar'},
        {value: 'broker-icon', labelKey: 'common.icon'},
        {value: 'custom', labelKey: 'common.custom'},
    ];

    const aspectOptions: Array<{value: number; label: string}> = [
        {value: 1, label: '1:1'},
        {value: 16 / 9, label: '16:9'},
        {value: 4 / 3, label: '4:3'},
        {value: 3 / 4, label: '3:4'},
        {value: 0, label: 'Free'},
    ];

    // Internal state
    let imageSrc: string | null = null;
    let cropper: ImageCropper;
    let isUploading = false;
    let error: string | null = null;
    let currentPreset: PresetName = preset;
    let hasChanges = false;
    let showCloseConfirm = false;

    // File name editing
    let editedFileName: string = '';
    let outputFormat: 'png' | 'jpeg' | 'webp' = 'png';
    let outputQuality: number = 90;

    // Output size (editable)
    let outputWidth: number | null = null;
    let outputHeight: number | null = null;

    // Selection dimensions (from cropper)
    let selectionWidth: number = 0;
    let selectionHeight: number = 0;

    // Image original dimensions (from cropper)
    let imageWidth: number = 0;
    let imageHeight: number = 0;

    // Preview ellipse
    let showEllipsePreview: boolean = false;

    // Current aspect ratio for aspect buttons
    let currentAspect: number = 1;

    // Track first initialization to auto-resetAll
    let needsInit: boolean = true;

    // Initialize when file changes
    $: if (file && open) {
        const nameParts = file.name.split('.');
        if (nameParts.length > 1) nameParts.pop();
        editedFileName = nameParts.join('.');
        if (file.type === 'image/jpeg') outputFormat = 'jpeg';
        else if (file.type === 'image/webp') outputFormat = 'webp';
        else outputFormat = 'png';
    }

    // Reset state when modal opens
    $: if (open) {
        currentPreset = preset;
        hasChanges = false;
        showCloseConfirm = false;
        showEllipsePreview = preset === 'avatar' || preset === 'broker-icon';
        needsInit = true;
    }

    // Computed config from preset
    $: config = customConfig ? {...IMAGE_PRESETS[currentPreset], ...customConfig} : IMAGE_PRESETS[currentPreset];

    // Update output size when preset changes
    $: {
        if (config.outputWidth && config.outputHeight) {
            outputWidth = config.outputWidth;
            outputHeight = config.outputHeight;
        } else {
            outputWidth = null;
            outputHeight = null;
        }
        outputQuality = Math.round(config.outputQuality * 100);
        currentAspect = config.aspectRatio;
    }

    // Computed scale factor — always show when output differs from selection
    $: scaleFactor = (() => {
        const ow = outputWidth || selectionWidth;
        const sw = selectionWidth;
        if (!sw || sw === 0) return 1;
        return ow / sw;
    })();

    // Effective output (what will actually be produced)
    $: effectiveOutputWidth = outputWidth || selectionWidth;
    $: effectiveOutputHeight = outputHeight || selectionHeight;

    // Load image
    $: if (file && open) {
        loadImage(file);
    }
    $: if (!open && imageSrc) {
        cleanup();
    }

    function loadImage(f: File) {
        if (imageSrc) URL.revokeObjectURL(imageSrc);
        imageSrc = URL.createObjectURL(f);
        error = null;
    }

    function cleanup() {
        if (imageSrc) {
            URL.revokeObjectURL(imageSrc);
            imageSrc = null;
        }
        error = null;
        isUploading = false;
    }

    function handleCancel() {
        cleanup();
        dispatch('cancel');
    }

    function requestClose() {
        if (hasChanges) {
            showCloseConfirm = true;
        } else {
            handleCancel();
        }
    }

    function confirmClose() {
        showCloseConfirm = false;
        handleCancel();
    }

    function cancelClose() {
        showCloseConfirm = false;
    }

    let suppressChanges = false;

    function handleCropperChange(e: CustomEvent<{selection: {width: number; height: number}}>) {
        if (e.detail?.selection) {
            selectionWidth = Math.round(e.detail.selection.width);
            selectionHeight = Math.round(e.detail.selection.height);
        }
        // Sync image dimensions from cropper
        const dims = cropper?.getImageDimensions?.();
        if (dims) {
            imageWidth = dims.width;
            imageHeight = dims.height;
        }

        // Auto-resetAll on first init to align selection properly
        if (needsInit && cropper?.resetAll) {
            needsInit = false;
            suppressChanges = true;
            // Small delay to let cropper finish its initial setup
            setTimeout(() => {
                cropper?.resetAll?.();
                hasChanges = false; // Reset the changes flag after init
                // Keep suppressing for a bit longer to catch post-resetAll events
                setTimeout(() => {
                    suppressChanges = false;
                }, 300);
            }, 200);
            return;
        }

        if (!suppressChanges) {
            hasChanges = true;
        }
    }

    function handleOutputWidthInput(e: Event) {
        const val = parseInt((e.target as HTMLInputElement).value);
        if (isNaN(val) || val <= 0) return;
        const w = Math.min(val, selectionWidth || val);
        outputWidth = w;
        if (selectionWidth > 0 && selectionHeight > 0) {
            const ratio = selectionWidth / selectionHeight;
            outputHeight = Math.round(w / ratio);
        }
        hasChanges = true;
    }

    function handleOutputHeightInput(e: Event) {
        const val = parseInt((e.target as HTMLInputElement).value);
        if (isNaN(val) || val <= 0) return;
        const h = Math.min(val, selectionHeight || val);
        outputHeight = h;
        if (selectionWidth > 0 && selectionHeight > 0) {
            const ratio = selectionWidth / selectionHeight;
            outputWidth = Math.round(h * ratio);
        }
        hasChanges = true;
    }

    function handleScaleInput(e: Event) {
        const val = parseFloat((e.target as HTMLInputElement).value);
        if (isNaN(val) || val <= 0 || val > 1) return;
        outputWidth = Math.round(selectionWidth * val);
        outputHeight = Math.round(selectionHeight * val);
        hasChanges = true;
    }

    function incrementQuality() {
        outputQuality = Math.min(100, outputQuality + 10);
        hasChanges = true;
    }

    function decrementQuality() {
        outputQuality = Math.max(10, outputQuality - 10);
        hasChanges = true;
    }

    function selectPreset(p: PresetName) {
        currentPreset = p;
        showEllipsePreview = p === 'avatar' || p === 'broker-icon';
        // Apply aspect ratio to cropper
        const presetConfig = IMAGE_PRESETS[p];
        if (cropper?.selectAspect) {
            cropper.selectAspect(presetConfig.aspectRatio);
        }
        currentAspect = presetConfig.aspectRatio;
        hasChanges = true;
    }

    function selectAspectRatio(value: number) {
        currentAspect = value;
        if (cropper?.selectAspect) {
            cropper.selectAspect(value);
        }
        hasChanges = true;
    }

    async function handleUpload() {
        if (!imageSrc || !file) return;
        const cropperInstance = cropper?.getCropper?.();
        if (!cropperInstance) {
            error = 'Cropper not ready';
            return;
        }

        isUploading = true;
        error = null;

        try {
            const blob = await getCroppedImageFromCropper(cropperInstance, outputWidth, outputHeight, outputFormat, outputQuality / 100);
            const finalFileName = `${editedFileName || 'image'}.${outputFormat === 'jpeg' ? 'jpg' : outputFormat}`;
            const croppedFile = blobToFile(blob, finalFileName);

            if (!uploadOnComplete) {
                cleanup();
                dispatch('complete', {url: null, file: croppedFile});
                return;
            }

            const uploadedUrl = await uploadFile(croppedFile, `Cropped image (${currentPreset})`);
            cleanup();
            dispatch('complete', {url: uploadedUrl, file: croppedFile});
        } catch (err) {
            console.error('Upload failed:', err);
            error = err instanceof Error ? err.message : 'Upload failed';
            dispatch('error', {message: error});
        } finally {
            isUploading = false;
        }
    }

    $: modalTitle = $_(config.titleKey) || $_('uploads.editImage') || 'Edit Image';
</script>

<ModalBase maxWidth="800px" noTransition={false} onRequestClose={requestClose} open={open && !!imageSrc} zIndex={50}>
    <div aria-labelledby="modal-title" aria-modal="true" class="modal-content-inner" data-testid="image-edit-modal" role="dialog">
        <!-- Header -->
        <div class="modal-header">
            <h2 class="modal-title" id="modal-title">{modalTitle}</h2>
            <div class="header-actions">
                {#if hasChanges}
                    <button type="button" class="header-btn reset" on:click={() => cropper?.resetAll?.()} title={$_('uploads.resetAll') || 'Reset All'} data-testid="image-edit-reset">
                        <RefreshCw size={16} />
                    </button>
                {/if}
                <button class="header-btn" data-testid="image-edit-close" on:click={requestClose} title={$_('common.close') || 'Close'} type="button">
                    <X size={20} />
                </button>
            </div>
        </div>

        <!-- Body -->
        <div class="modal-body">
            <!-- Row 1: File name + quality (if JPEG/WebP) -->
            <div class="filename-row">
                <div class="filename-editor">
                    <input bind:value={editedFileName} class="filename-input" data-testid="image-edit-filename" on:input={() => (hasChanges = true)} placeholder="image" type="text" />
                    <select bind:value={outputFormat} class="format-select" on:change={() => (hasChanges = true)}>
                        <option value="png">.png</option>
                        <option value="jpeg">.jpg</option>
                        <option value="webp">.webp</option>
                    </select>
                </div>
                {#if outputFormat !== 'png'}
                    <div class="quality-spinner">
                        <button type="button" class="spin-btn" on:click={decrementQuality}>−</button>
                        <span class="quality-value">{outputQuality}%</span>
                        <button type="button" class="spin-btn" on:click={incrementQuality}>+</button>
                    </div>
                {/if}
            </div>

            <!-- Cropper with ellipse preview toggle on left -->
            <div class="cropper-section">
                <!-- Ellipse toggle - LEFT side -->
                <button class="ellipse-toggle" class:active={showEllipsePreview} data-testid="image-edit-ellipse-toggle" on:click={() => (showEllipsePreview = !showEllipsePreview)} title={showEllipsePreview ? 'Hide preview' : 'Show preview'} type="button">
                    {#if showEllipsePreview}
                        <Eye size={16} />
                    {:else}
                        <EyeOff size={16} />
                    {/if}
                </button>

                <ImageCropper aspectRatio={config.aspectRatio} bind:this={cropper} imageSrc={imageSrc || ''} on:change={handleCropperChange} showPreviewEllipse={showEllipsePreview} showRotateControls={true} showZoomSlider={true} />
            </div>

            <!-- === BOTTOM PANEL (2 columns) === -->
            <div class="bottom-panel" data-testid="image-edit-controls-panel">
                <!-- Left column: Info (Input/Selection) + Output/Scale -->
                <div class="panel-col">
                    <div class="panel-row info-row">
                        <span class="panel-label">{$_('uploads.inputSize') || 'Input'}:</span>
                        <span class="info-value">{imageWidth} × {imageHeight} px</span>
                    </div>
                    <div class="panel-row info-row">
                        <span class="panel-label">{$_('uploads.selectionSize') || 'Selection'}:</span>
                        <span class="info-value">{selectionWidth} × {selectionHeight} px</span>
                    </div>

                    <div class="panel-row">
                        <span class="panel-label">{$_('uploads.outputSize') || 'Output'}:</span>
                        <div class="dimensions-group">
                            <input class="dim-input" max={selectionWidth || 9999} min="1" on:input={handleOutputWidthInput} type="number" value={effectiveOutputWidth} />
                            <span class="dim-sep">×</span>
                            <input class="dim-input" max={selectionHeight || 9999} min="1" on:input={handleOutputHeightInput} type="number" value={effectiveOutputHeight} />
                            <span class="dim-unit">px</span>
                            <Lock class="lock-icon" size={12} />
                        </div>
                    </div>

                    <div class="panel-row">
                        <span class="panel-label">{$_('uploads.scale') || 'Scale'}:</span>
                        <div class="scale-group">
                            <!-- Spacer to align with the Y (second) dim-input -->
                            <span class="scale-spacer"></span>
                            <span class="scale-x">×</span>
                            <input class="scale-input" max="1" min="0.01" on:input={handleScaleInput} step="0.01" type="number" value={scaleFactor.toFixed(2)} />
                        </div>
                    </div>
                </div>

                <!-- Right column: Preset + Aspect ratio -->
                <div class="panel-col">
                    {#if allowPresetChange}
                        <div class="panel-row">
                            <span class="panel-label">{$_('uploads.outputPreset') || 'Preset'}:</span>
                            <div class="preset-buttons">
                                {#each presetOptions as opt}
                                    <button type="button" class="preset-btn" class:active={currentPreset === opt.value} on:click={() => selectPreset(opt.value)}>
                                        {$_(opt.labelKey) || opt.value}
                                    </button>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    {#if currentPreset === 'custom'}
                        <div class="panel-row">
                            <span class="panel-label">{$_('uploads.aspectRatio') || 'Ratio'}:</span>
                            <div class="aspect-buttons">
                                {#each aspectOptions as opt}
                                    <button type="button" class="aspect-btn" class:active={currentAspect === opt.value} on:click={() => selectAspectRatio(opt.value)}>
                                        {opt.label}
                                    </button>
                                {/each}
                            </div>
                        </div>
                    {/if}
                </div>
            </div>

            {#if error}
                <div class="error-message">{error}</div>
            {/if}
        </div>

        <!-- Footer -->
        <div class="modal-footer">
            <button class="btn btn-secondary" data-testid="image-edit-cancel" disabled={isUploading} on:click={requestClose} type="button">
                {$_('common.cancel') || 'Cancel'}
            </button>
            <button class="btn btn-primary" data-testid="image-edit-confirm" disabled={isUploading} on:click={handleUpload} type="button">
                {#if isUploading}
                    <Loader2 size={16} class="animate-spin" />
                    {$_('common.uploading') || 'Uploading...'}
                {:else}
                    <Upload size={16} />
                    {#if uploadOnComplete}
                        {$_('uploads.cropAndUpload') || 'Crop & Upload'}
                    {:else}
                        {$_('uploads.crop') || 'Crop'}
                    {/if}
                {/if}
            </button>
        </div>
    </div>
</ModalBase>

<!-- Confirmation dialog for closing with unsaved changes -->
<ModalBase maxWidth="sm" onRequestClose={cancelClose} open={showCloseConfirm} zIndex={60}>
    <div class="confirm-dialog" data-testid="image-edit-confirm-dialog">
        <div class="confirm-header">
            <span class="confirm-icon">⚠️</span>
            <h3>{$_('common.discardChanges') || 'Discard changes?'}</h3>
        </div>
        <p class="confirm-message">
            {$_('common.discardChangesMessage') || 'You have unsaved changes. Are you sure you want to close?'}
        </p>
        <div class="confirm-actions">
            <button class="btn btn-secondary" on:click={cancelClose}>
                {$_('common.cancel') || 'Cancel'}
            </button>
            <button class="btn btn-warning" on:click={confirmClose}>
                {$_('common.discardAndClose') || 'Discard & Close'}
            </button>
        </div>
    </div>
</ModalBase>

<style>
    /* Backdrop and outer modal-content handled by ModalBase */
    .modal-content-inner {
        display: flex;
        flex-direction: column;
        overflow: hidden;
        max-height: 90vh;
    }

    /* Header */
    .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.625rem 1rem;
        border-bottom: 1px solid #e5e7eb;
        flex-shrink: 0;
    }

    :global(.dark) .modal-header {
        border-bottom-color: #374151;
    }

    .modal-title {
        font-size: 1rem;
        font-weight: 600;
        color: #111827;
        margin: 0;
    }

    :global(.dark) .modal-title {
        color: #f3f4f6;
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .header-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 30px;
        height: 30px;
        border-radius: 0.375rem;
        border: none;
        background: transparent;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.15s;
    }

    .header-btn:hover {
        background: #f3f4f6;
        color: #374151;
    }

    .header-btn.reset {
        background: rgba(245, 158, 11, 0.1);
        color: #f59e0b;
    }

    .header-btn.reset:hover {
        background: rgba(245, 158, 11, 0.2);
        color: #d97706;
    }

    :global(.dark) .header-btn:hover {
        background: #374151;
        color: #d1d5db;
    }

    /* Body */
    .modal-body {
        flex: 1;
        overflow-y: auto;
        padding: 0.75rem 1rem;
        min-height: 0;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    /* Filename row: [input.ext] [quality?] */
    .filename-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .filename-editor {
        display: flex;
        flex: 1;
        min-width: 0;
    }

    .filename-input {
        flex: 1;
        padding: 0.375rem 0.5rem;
        font-size: 0.8125rem;
        border: 1px solid #d1d5db;
        border-right: none;
        border-radius: 0.375rem 0 0 0.375rem;
        background: white;
        color: #374151;
        outline: none;
    }

    .filename-input:focus {
        border-color: #1a4031;
    }

    :global(.dark) .filename-input {
        background: #374151;
        border-color: #4b5563;
        color: #f3f4f6;
    }

    :global(.dark) .filename-input:focus {
        border-color: #10b981;
    }

    .format-select {
        padding: 0.375rem 0.5rem;
        font-size: 0.8125rem;
        border: 1px solid #d1d5db;
        border-radius: 0 0.375rem 0.375rem 0;
        background: #f3f4f6;
        color: #374151;
        cursor: pointer;
        outline: none;
    }

    :global(.dark) .format-select {
        background: #4b5563;
        border-color: #4b5563;
        color: #f3f4f6;
    }

    /* Quality spinner (inline with filename) */
    .quality-spinner {
        display: flex;
        align-items: center;
        border: 1px solid #d1d5db;
        border-radius: 0.375rem;
        overflow: hidden;
        flex-shrink: 0;
    }

    :global(.dark) .quality-spinner {
        border-color: #4b5563;
    }

    .spin-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border: none;
        background: #f3f4f6;
        color: #374151;
        cursor: pointer;
        font-size: 0.8125rem;
        font-weight: 600;
        transition: all 0.1s;
    }

    .spin-btn:hover {
        background: #e5e7eb;
    }

    :global(.dark) .spin-btn {
        background: #374151;
        color: #d1d5db;
    }

    :global(.dark) .spin-btn:hover {
        background: #4b5563;
    }

    .quality-value {
        padding: 0 0.375rem;
        font-size: 0.6875rem;
        font-family: monospace;
        color: #374151;
        min-width: 32px;
        text-align: center;
    }

    :global(.dark) .quality-value {
        color: #e5e7eb;
    }

    /* Cropper section with eye toggle on LEFT */
    .cropper-section {
        position: relative;
    }

    .ellipse-toggle {
        position: absolute;
        top: 0.5rem;
        left: 0.5rem;
        z-index: 10;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 30px;
        height: 30px;
        border: none;
        border-radius: 0.25rem;
        background: rgba(0, 0, 0, 0.5);
        color: rgba(255, 255, 255, 0.7);
        cursor: pointer;
        transition: all 0.15s;
    }

    .ellipse-toggle:hover {
        background: rgba(0, 0, 0, 0.7);
        color: white;
    }

    .ellipse-toggle.active {
        background: rgba(16, 185, 129, 0.8);
        color: white;
    }

    /* ========= BOTTOM PANEL (2 columns) ========= */
    .bottom-panel {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem 1rem;
        padding: 0.625rem 0.75rem;
        background: #f3f4f6;
        border-radius: 0.5rem;
    }

    :global(.dark) .bottom-panel {
        background: #1a2332;
    }

    .panel-col {
        display: flex;
        flex-direction: column;
        gap: 0.375rem;
    }

    .panel-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .panel-label {
        font-size: 0.6875rem;
        font-weight: 500;
        color: #6b7280;
        min-width: 48px;
    }

    :global(.dark) .panel-label {
        color: #9ca3af;
    }

    /* Preset buttons */
    .preset-buttons,
    .aspect-buttons {
        display: flex;
        gap: 0.25rem;
        flex-wrap: wrap;
    }

    .preset-btn,
    .aspect-btn {
        padding: 0.1875rem 0.5rem;
        font-size: 0.625rem;
        font-weight: 500;
        border: 1px solid #d1d5db;
        border-radius: 0.25rem;
        background: white;
        color: #374151;
        cursor: pointer;
        transition: all 0.15s;
    }

    .preset-btn:hover,
    .aspect-btn:hover {
        border-color: #1a4031;
        color: #1a4031;
    }

    .preset-btn.active,
    .aspect-btn.active {
        background: #1a4031;
        border-color: #1a4031;
        color: white;
    }

    :global(.dark) .preset-btn,
    :global(.dark) .aspect-btn {
        background: #374151;
        border-color: #4b5563;
        color: #d1d5db;
    }

    :global(.dark) .preset-btn:hover,
    :global(.dark) .aspect-btn:hover {
        border-color: #10b981;
        color: #10b981;
    }

    :global(.dark) .preset-btn.active,
    :global(.dark) .aspect-btn.active {
        background: #10b981;
        border-color: #10b981;
        color: white;
    }

    /* Dimensions */
    .dimensions-group {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .dim-input {
        width: 52px;
        padding: 0.1875rem 0.25rem;
        font-size: 0.6875rem;
        font-family: monospace;
        border: 1px solid #d1d5db;
        border-radius: 0.25rem;
        background: white;
        color: #374151;
        text-align: center;
        outline: none;
    }

    .dim-input:focus {
        border-color: #1a4031;
    }

    :global(.dark) .dim-input {
        background: #374151;
        border-color: #4b5563;
        color: #f3f4f6;
    }

    :global(.dark) .dim-input:focus {
        border-color: #10b981;
    }

    .dim-sep {
        color: #9ca3af;
        font-size: 0.6875rem;
    }

    .dim-unit {
        font-size: 0.625rem;
        color: #9ca3af;
    }

    :global(.lock-icon) {
        color: #9ca3af;
        margin-left: 0.125rem;
    }

    /* Scale */
    .scale-group {
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }

    .scale-spacer {
        width: 52px; /* matches dim-input width */
        display: inline-block;
    }

    .scale-x {
        font-size: 0.625rem;
        color: #9ca3af;
    }

    .scale-input {
        width: 56px;
        padding: 0.1875rem 0.25rem;
        font-size: 0.6875rem;
        font-family: monospace;
        border: 1px solid #d1d5db;
        border-radius: 0.25rem;
        background: white;
        color: #374151;
        text-align: center;
        outline: none;
    }

    .scale-input:focus {
        border-color: #1a4031;
    }

    :global(.dark) .scale-input {
        background: #374151;
        border-color: #4b5563;
        color: #f3f4f6;
    }

    /* Info values (right column) */
    .info-row {
        gap: 0.375rem;
    }

    .info-value {
        font-size: 0.6875rem;
        font-family: monospace;
        color: #4b5563;
    }

    :global(.dark) .info-value {
        color: #9ca3af;
    }

    /* Error */
    .error-message {
        padding: 0.5rem 0.75rem;
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 0.375rem;
        color: #dc2626;
        font-size: 0.8125rem;
    }

    :global(.dark) .error-message {
        background-color: rgba(220, 38, 38, 0.1);
        border-color: rgba(220, 38, 38, 0.3);
    }

    /* Footer */
    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        padding: 0.625rem 1rem;
        border-top: 1px solid #e5e7eb;
        background: #f9fafb;
        flex-shrink: 0;
    }

    :global(.dark) .modal-footer {
        background: #111827;
        border-top-color: #374151;
    }

    .btn {
        display: inline-flex;
        align-items: center;
        gap: 0.375rem;
        padding: 0.375rem 0.875rem;
        font-size: 0.8125rem;
        font-weight: 500;
        border-radius: 0.375rem;
        border: none;
        cursor: pointer;
        transition: all 0.15s;
    }

    .btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-primary {
        background: #1a4031;
        color: white;
    }

    .btn-primary:hover:not(:disabled) {
        background: #143326;
    }

    :global(.dark) .btn-primary {
        background: #10b981;
    }

    :global(.dark) .btn-primary:hover:not(:disabled) {
        background: #059669;
    }

    .btn-secondary {
        background: #e5e7eb;
        color: #374151;
    }

    .btn-secondary:hover:not(:disabled) {
        background: #d1d5db;
    }

    :global(.dark) .btn-secondary {
        background: #374151;
        color: #d1d5db;
    }

    :global(.dark) .btn-secondary:hover:not(:disabled) {
        background: #4b5563;
    }

    :global(.animate-spin) {
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }

    /* Confirmation Dialog — backdrop handled by ModalBase */
    .confirm-dialog {
        background: white;
        border-radius: 0.75rem;
        padding: 1.5rem;
        width: 100%;
    }

    :global(.dark) .confirm-dialog {
        background: #1f2937;
        border: 1px solid #374151;
    }

    .confirm-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.75rem;
    }

    .confirm-icon {
        font-size: 1.5rem;
    }

    .confirm-header h3 {
        margin: 0;
        font-size: 1rem;
        font-weight: 600;
        color: #d97706;
    }

    :global(.dark) .confirm-header h3 {
        color: #fbbf24;
    }

    .confirm-message {
        color: #6b7280;
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }

    :global(.dark) .confirm-message {
        color: #9ca3af;
    }

    .confirm-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
    }

    .btn-warning {
        background: #f59e0b;
        color: white;
        border: none;
    }

    .btn-warning:hover {
        background: #d97706;
    }

    /* Mobile: single column */
    @media (max-width: 520px) {
        .bottom-panel {
            grid-template-columns: 1fr;
        }
    }
</style>
