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
    import type {UploadScope} from '$lib/types';

    import {numericArrows} from '$lib/actions/numericArrows';
    // Props
    export let open: boolean = false;
    export let zIndex: number = 50;
    export let file: File | null = null;
    export let preset: PresetName = 'custom';
    export let customConfig: Partial<{aspectRatio: number; outputWidth: number | null; outputHeight: number | null; outputQuality: number}> | null = null;
    export let allowPresetChange: boolean = true;
    export let uploadOnComplete: boolean = true;
    /** Who sees the uploaded image: common for the image pickers (icons, logos, photos, avatars); the Files page passes personal */
    export let scope: UploadScope = 'common';

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

    /**
     * The cropper reports `data-cropper-ready` as soon as it can paint, but this modal keeps
     * discarding change events for ~500ms after that while it runs its own `resetAll` pass.
     * Edits made in that window are silently dropped (`hasChanges` stays false), so the state
     * has to be observable: `aria-busy` for assistive tech, `data-edit-ready` for anything
     * that needs to know when an edit will actually be recorded.
     */
    let editReady: boolean = false;

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
        editReady = false;
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
                    editReady = true;
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

            const uploadedUrl = await uploadFile(croppedFile, `Cropped image (${currentPreset})`, scope);
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

<ModalBase maxWidth="800px" noTransition={false} onRequestClose={requestClose} open={open && !!imageSrc} {zIndex}>
    <div aria-labelledby="modal-title" aria-modal="true" aria-busy={!editReady} class="modal-content-inner" data-edit-ready={editReady || undefined} data-testid="image-edit-modal" role="dialog">
        <!-- Header -->
        <div class="modal-header">
            <h2 class="modal-title" id="modal-title">{modalTitle}</h2>
            <div class="header-actions">
                {#if hasChanges}
                    <button type="button" class="header-btn reset" disabled={!editReady} on:click={() => cropper?.resetAll?.()} title={$_('common.resetAllChanges') || 'Reset All'} data-testid="image-edit-reset">
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
                    <input bind:value={editedFileName} class="filename-input" data-testid="image-edit-filename" disabled={!editReady} on:input={() => (hasChanges = true)} placeholder="image" type="text" />
                    <select bind:value={outputFormat} class="format-select" data-testid="image-edit-format" disabled={!editReady} on:change={() => (hasChanges = true)}>
                        <option value="png">.png</option>
                        <option value="jpeg">.jpg</option>
                        <option value="webp">.webp</option>
                    </select>
                </div>
                {#if outputFormat !== 'png'}
                    <div class="quality-spinner" data-testid="image-edit-quality">
                        <button type="button" class="spin-btn" disabled={!editReady} on:click={decrementQuality}>−</button>
                        <span class="quality-value">{outputQuality}%</span>
                        <button type="button" class="spin-btn" disabled={!editReady} on:click={incrementQuality}>+</button>
                    </div>
                {/if}
            </div>

            <!-- Cropper with ellipse preview toggle on left -->
            <div class="cropper-section">
                <!-- Ellipse toggle - LEFT side -->
                <button class="ellipse-toggle" class:active={showEllipsePreview} data-testid="image-edit-ellipse-toggle" disabled={!editReady} on:click={() => (showEllipsePreview = !showEllipsePreview)} title={showEllipsePreview ? 'Hide preview' : 'Show preview'} type="button">
                    {#if showEllipsePreview}
                        <Eye size={16} />
                    {:else}
                        <EyeOff size={16} />
                    {/if}
                </button>

                <ImageCropper aspectRatio={config.aspectRatio} bind:this={cropper} imageSrc={imageSrc || ''} on:change={handleCropperChange} showPreviewEllipse={showEllipsePreview} showRotateControls={true} showZoomSlider={true} />

                <!--
                    Init guard. handleCropperChange() calls resetAll() ~200 ms after the
                    cropper first reports, so a crop/rotate/zoom made in that window is
                    thrown away without a word. The cropper is not a form control, so
                    `disabled` cannot reach it — an overlay is the only way to say "not
                    yet". It disappears with editReady (~500 ms).
                -->
                {#if !editReady}
                    <div aria-hidden="true" class="cropper-guard" data-testid="image-edit-init-guard">
                        <Loader2 class="animate-spin" size={24} />
                    </div>
                {/if}
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
                            <input class="dim-input" disabled={!editReady} max={selectionWidth || 9999} min="1" on:input={handleOutputWidthInput} type="number" use:numericArrows value={effectiveOutputWidth} />
                            <span class="dim-sep">×</span>
                            <input class="dim-input" disabled={!editReady} max={selectionHeight || 9999} min="1" on:input={handleOutputHeightInput} type="number" use:numericArrows value={effectiveOutputHeight} />
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
                            <input class="scale-input" disabled={!editReady} max="1" min="0.01" on:input={handleScaleInput} step="0.01" type="number" use:numericArrows={{step: 0.01}} value={scaleFactor.toFixed(2)} />
                        </div>
                    </div>
                </div>

                <!-- Right column: Preset + Aspect ratio -->
                <div class="panel-col">
                    {#if allowPresetChange}
                        <div class="panel-row">
                            <span class="panel-label">{$_('uploads.outputPreset') || 'Preset'}:</span>
                            <div class="preset-buttons" data-testid="image-edit-preset-row">
                                {#each presetOptions as opt}
                                    <button type="button" class="preset-btn" class:active={currentPreset === opt.value} disabled={!editReady} on:click={() => selectPreset(opt.value)}>
                                        {$_(opt.labelKey) || opt.value}
                                    </button>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    {#if currentPreset === 'custom'}
                        <div class="panel-row">
                            <span class="panel-label">{$_('uploads.aspectRatio') || 'Ratio'}:</span>
                            <div class="aspect-buttons" data-testid="image-edit-aspect-row">
                                {#each aspectOptions as opt}
                                    <button type="button" class="aspect-btn" class:active={currentAspect === opt.value} disabled={!editReady} on:click={() => selectAspectRatio(opt.value)}>
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
            <button class="btn btn-primary" data-testid="image-edit-confirm" disabled={isUploading || !editReady} on:click={handleUpload} type="button">
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
<ModalBase maxWidth="sm" onRequestClose={cancelClose} open={showCloseConfirm} zIndex={zIndex + 10}>
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
        border-bottom: 1px solid var(--lf-border-subtle);
        flex-shrink: 0;
    }

    .modal-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--lf-text-primary);
        margin: 0;
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
        color: var(--lf-text-muted);
        cursor: pointer;
        transition: all 0.15s;
    }

    .header-btn:hover {
        background: var(--lf-surface-hover);
        color: var(--lf-text-secondary);
    }

    .header-btn.reset {
        background: var(--lf-warning-soft);
        color: var(--lf-warning);
    }

    .header-btn.reset:hover {
        background: var(--lf-warning-line);
        color: var(--lf-warning-on-soft);
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
        border: 1px solid var(--lf-border-input);
        border-right: none;
        border-radius: 0.375rem 0 0 0.375rem;
        background: var(--lf-surface-field);
        color: var(--lf-text-primary);
        outline: none;
    }

    .filename-input::placeholder {
        color: var(--lf-text-placeholder);
    }

    .filename-input:focus {
        border-color: var(--lf-focus);
    }

    .format-select {
        padding: 0.375rem 0.5rem;
        font-size: 0.8125rem;
        border: 1px solid var(--lf-border-input);
        border-radius: 0 0.375rem 0.375rem 0;
        background: var(--lf-surface-panel);
        color: var(--lf-text-primary);
        cursor: pointer;
        outline: none;
    }

    .format-select:focus {
        border-color: var(--lf-focus);
    }

    /* Quality spinner (inline with filename) */
    .quality-spinner {
        display: flex;
        align-items: center;
        border: 1px solid var(--lf-border-input);
        border-radius: 0.375rem;
        overflow: hidden;
        flex-shrink: 0;
    }

    .spin-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border: none;
        background: var(--lf-surface-panel);
        color: var(--lf-text-secondary);
        cursor: pointer;
        font-size: 0.8125rem;
        font-weight: 600;
        transition: all 0.1s;
    }

    .spin-btn:hover {
        background: var(--lf-surface-neutral);
    }

    .quality-value {
        padding: 0 0.375rem;
        font-size: 0.6875rem;
        font-family: monospace;
        color: var(--lf-text-primary);
        min-width: 32px;
        text-align: center;
    }

    /* Cropper section with eye toggle on LEFT */
    .cropper-section {
        position: relative;
    }

    .cropper-guard {
        position: absolute;
        inset: 0;
        z-index: 10;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 0.5rem;
        background: color-mix(in oklab, var(--lf-surface-card) 55%, transparent);
        color: var(--lf-link);
        cursor: progress;
    }

    .filename-input:disabled,
    .format-select:disabled,
    .dim-input:disabled,
    .scale-input:disabled,
    .spin-btn:disabled,
    .preset-btn:disabled,
    .aspect-btn:disabled,
    .ellipse-toggle:disabled,
    .header-btn:disabled {
        cursor: not-allowed;
        opacity: 0.5;
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
        background: color-mix(in oklab, var(--lf-surface-overlay) 80%, transparent);
        color: color-mix(in oklab, var(--lf-on-overlay) 70%, transparent);
        cursor: pointer;
        transition: all 0.15s;
    }

    .ellipse-toggle:hover {
        background: var(--lf-surface-overlay);
        color: var(--lf-on-overlay);
    }

    .ellipse-toggle.active {
        background: color-mix(in oklab, var(--lf-checked) 80%, transparent);
        color: var(--lf-on-checked);
    }

    /* ========= BOTTOM PANEL (2 columns) ========= */
    .bottom-panel {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem 1rem;
        padding: 0.625rem 0.75rem;
        background: var(--lf-surface-panel);
        border-radius: 0.5rem;
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
        color: var(--lf-text-muted);
        min-width: 48px;
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
        border: 1px solid var(--lf-border-input);
        border-radius: 0.25rem;
        background: var(--lf-surface-card);
        color: var(--lf-text-secondary);
        cursor: pointer;
        transition: all 0.15s;
    }

    .preset-btn:hover,
    .aspect-btn:hover {
        border-color: var(--lf-focus);
        color: var(--lf-link);
    }

    .preset-btn.active,
    .aspect-btn.active {
        background: var(--lf-checked);
        border-color: var(--lf-checked);
        color: var(--lf-on-checked);
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
        border: 1px solid var(--lf-border-input);
        border-radius: 0.25rem;
        background: var(--lf-surface-field);
        color: var(--lf-text-primary);
        text-align: center;
        outline: none;
    }

    .dim-input:focus {
        border-color: var(--lf-focus);
    }

    .dim-sep {
        color: var(--lf-text-muted);
        font-size: 0.6875rem;
    }

    .dim-unit {
        font-size: 0.625rem;
        color: var(--lf-text-muted);
    }

    :global(.lock-icon) {
        color: var(--lf-text-muted);
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
        color: var(--lf-text-muted);
    }

    .scale-input {
        width: 56px;
        padding: 0.1875rem 0.25rem;
        font-size: 0.6875rem;
        font-family: monospace;
        border: 1px solid var(--lf-border-input);
        border-radius: 0.25rem;
        background: var(--lf-surface-field);
        color: var(--lf-text-primary);
        text-align: center;
        outline: none;
    }

    .scale-input:focus {
        border-color: var(--lf-focus);
    }

    /* Info values (right column) */
    .info-row {
        gap: 0.375rem;
    }

    .info-value {
        font-size: 0.6875rem;
        font-family: monospace;
        color: var(--lf-text-secondary);
    }

    /* Error */
    .error-message {
        padding: 0.5rem 0.75rem;
        background-color: var(--lf-danger-soft);
        border: 1px solid var(--lf-danger-line);
        border-radius: 0.375rem;
        color: var(--lf-danger-on-soft);
        font-size: 0.8125rem;
    }

    /* Footer */
    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        padding: 0.625rem 1rem;
        border-top: 1px solid var(--lf-border-subtle);
        background: var(--lf-surface-panel);
        flex-shrink: 0;
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
        background: var(--lf-action);
        color: var(--lf-on-action);
    }

    .btn-primary:hover:not(:disabled) {
        background: var(--lf-action-hover);
    }

    .btn-secondary {
        background: var(--lf-surface-card);
        color: var(--lf-text-secondary);
        box-shadow: inset 0 0 0 1px var(--lf-border-subtle);
    }

    .btn-secondary:hover:not(:disabled) {
        background: var(--lf-surface-hover);
        color: var(--lf-text-primary);
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
        background: var(--lf-surface-card);
        border-radius: 0.75rem;
        padding: 1.5rem;
        width: 100%;
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
        color: var(--lf-warning);
    }

    .confirm-message {
        color: var(--lf-text-muted);
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }

    .confirm-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
    }

    .btn-warning {
        background: var(--lf-warning);
        color: var(--lf-on-status);
        border: none;
    }

    .btn-warning:hover {
        background: var(--lf-warning-hover);
    }

    /* Mobile: single column */
    @media (max-width: 520px) {
        .bottom-panel {
            grid-template-columns: 1fr;
        }
    }
</style>
