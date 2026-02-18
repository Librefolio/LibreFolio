<!--
  ImageEditModal - Modal for editing/cropping images before upload

  Features:
  - Wraps ImageCropper with modal UI
  - Preset configurations for different use cases
  - Handles upload to backend and returns URL
  - Supports avatar, broker-icon, and custom presets
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import {_} from '$lib/i18n';
    import {X, Upload, Loader2} from 'lucide-svelte';
    import {axiosInstance} from '$lib/api';
    import ImageCropper from './ImageCropper.svelte';
    import {
        IMAGE_PRESETS,
        getCroppedImage,
        blobToFile,
        type PresetName,
        type ImagePreset
    } from '$lib/utils/imageCrop';

    // Props
    export let open: boolean = false;
    export let file: File | null = null;
    export let preset: PresetName = 'custom';
    export let customConfig: Partial<ImagePreset> | null = null;

    const dispatch = createEventDispatcher<{
        complete: {url: string; file: File};
        cancel: void;
        error: {message: string};
    }>();

    // Internal state
    let imageSrc: string | null = null;
    let cropper: ImageCropper;
    let isUploading = false;
    let error: string | null = null;

    // Computed config from preset + custom overrides
    $: config = customConfig
        ? {...IMAGE_PRESETS[preset], ...customConfig}
        : IMAGE_PRESETS[preset];

    // Load image when file changes
    $: if (file && open) {
        loadImage(file);
    }

    // Cleanup when closed
    $: if (!open && imageSrc) {
        cleanup();
    }

    function loadImage(f: File) {
        if (imageSrc) {
            URL.revokeObjectURL(imageSrc);
        }
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

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            handleCancel();
        }
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            handleCancel();
        }
    }

    async function handleUpload() {
        if (!imageSrc || !file) return;

        const croppedAreaPixels = cropper?.getCroppedAreaPixels();
        if (!croppedAreaPixels) {
            error = 'Please select a crop area';
            return;
        }

        isUploading = true;
        error = null;

        try {
            // Get cropped image blob
            const blob = await getCroppedImage(
                imageSrc,
                croppedAreaPixels,
                config.outputWidth,
                config.outputHeight,
                config.outputFormat === 'auto' ? 'png' : config.outputFormat,
                config.outputQuality
            );

            // Convert to File
            const croppedFile = blobToFile(blob, file.name);

            // Upload to backend
            const formData = new FormData();
            formData.append('file', croppedFile);
            formData.append('description', `Cropped image (${preset})`);

            const response = await axiosInstance.post('/api/v1/uploads', formData);

            // Get URL from response
            const uploadedUrl = response.data.file?.url || response.data.url;

            if (!uploadedUrl) {
                throw new Error('No URL in upload response');
            }

            // Success - dispatch complete event
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

    // Get translated title
    $: modalTitle = $_(config.titleKey) || $_('uploads.editImage') || 'Edit Image';
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open && imageSrc}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="modal-backdrop" on:click={handleBackdropClick}>
        <div class="modal-content" role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <!-- Header -->
            <div class="modal-header">
                <h2 id="modal-title" class="modal-title">{modalTitle}</h2>
                <button
                    type="button"
                    class="close-btn"
                    on:click={handleCancel}
                    title={$_('common.close') || 'Close'}
                >
                    <X size={20} />
                </button>
            </div>

            <!-- Body -->
            <div class="modal-body">
                <ImageCropper
                    bind:this={cropper}
                    {imageSrc}
                    aspectRatio={config.aspectRatio}
                    showZoomSlider={true}
                    showAspectSelector={preset === 'custom'}
                />

                <!-- Preview info -->
                <div class="preview-info">
                    {#if config.outputWidth && config.outputHeight}
                        <span class="info-badge">
                            {$_('uploads.outputSize') || 'Output'}: {config.outputWidth}×{config.outputHeight}px
                        </span>
                    {/if}
                    <span class="info-badge">
                        {config.outputFormat === 'auto' ? 'PNG' : config.outputFormat.toUpperCase()}
                    </span>
                </div>

                <!-- Error message -->
                {#if error}
                    <div class="error-message">
                        {error}
                    </div>
                {/if}
            </div>

            <!-- Footer -->
            <div class="modal-footer">
                <button
                    type="button"
                    class="btn btn-secondary"
                    on:click={handleCancel}
                    disabled={isUploading}
                >
                    {$_('common.cancel') || 'Cancel'}
                </button>
                <button
                    type="button"
                    class="btn btn-primary"
                    on:click={handleUpload}
                    disabled={isUploading}
                >
                    {#if isUploading}
                        <Loader2 size={16} class="animate-spin" />
                        {$_('common.uploading') || 'Uploading...'}
                    {:else}
                        <Upload size={16} />
                        {$_('uploads.cropAndUpload') || 'Crop & Upload'}
                    {/if}
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    .modal-backdrop {
        position: fixed;
        inset: 0;
        z-index: 50;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: rgba(0, 0, 0, 0.6);
        padding: 1rem;
    }

    .modal-content {
        background: white;
        border-radius: 1rem;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        width: 100%;
        max-width: 600px;
        max-height: 90vh;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }

    :global(.dark) .modal-content {
        background: #1f2937;
        border: 1px solid #374151;
    }

    .modal-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1rem 1.5rem;
        border-bottom: 1px solid #e5e7eb;
        flex-shrink: 0;
    }

    :global(.dark) .modal-header {
        border-bottom-color: #374151;
    }

    .modal-title {
        font-size: 1.125rem;
        font-weight: 600;
        color: #111827;
        margin: 0;
    }

    :global(.dark) .modal-title {
        color: #f3f4f6;
    }

    .close-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 0.5rem;
        border: none;
        background: transparent;
        color: #6b7280;
        cursor: pointer;
        transition: all 0.15s;
    }

    .close-btn:hover {
        background: #f3f4f6;
        color: #374151;
    }

    :global(.dark) .close-btn:hover {
        background: #374151;
        color: #d1d5db;
    }

    .modal-body {
        flex: 1;
        overflow-y: auto;
        padding: 1.5rem;
        min-height: 0;
    }

    .preview-info {
        display: flex;
        gap: 0.5rem;
        margin-top: 1rem;
        flex-wrap: wrap;
    }

    .info-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        font-size: 0.75rem;
        font-weight: 500;
        background: #f3f4f6;
        color: #4b5563;
        border-radius: 9999px;
    }

    :global(.dark) .info-badge {
        background: #374151;
        color: #9ca3af;
    }

    .error-message {
        margin-top: 1rem;
        padding: 0.75rem 1rem;
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 0.5rem;
        color: #dc2626;
        font-size: 0.875rem;
    }

    :global(.dark) .error-message {
        background-color: rgba(220, 38, 38, 0.1);
        border-color: rgba(220, 38, 38, 0.3);
    }

    .modal-footer {
        display: flex;
        justify-content: flex-end;
        gap: 0.75rem;
        padding: 1rem 1.5rem;
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
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        border-radius: 0.5rem;
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

    /* Animate spin for loader */
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
</style>

