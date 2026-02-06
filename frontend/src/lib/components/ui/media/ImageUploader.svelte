<script lang="ts">
    /**
     * ImageUploader - Drag & drop image upload with resize
     *
     * Features:
     * - Drag & drop + file browser
     * - Size selection: original / avatar (200px) / icon (50px)
     * - Client-side resize with Canvas API
     * - Preserves transparency for PNG/WebP
     * - Preview before upload
     * - Supports JPEG, PNG, WebP, GIF
     */
    import {createEventDispatcher} from 'svelte';
    import {t} from '$lib/i18n';

    export let accept: string = 'image/jpeg,image/png,image/webp,image/gif';
    export let maxSizeMB: number = 10;
    export let showSizeSelector: boolean = true;

    type ImageSize = 'original' | 'avatar' | 'icon';

    const dispatch = createEventDispatcher<{
        upload: { file: File; size: ImageSize };
        error: { message: string };
    }>();

    const SIZE_CONFIG = {
        original: {width: 0, height: 0, label: 'Original'},
        avatar: {width: 200, height: 200, label: 'Avatar (200×200)'},
        icon: {width: 50, height: 50, label: 'Icon (50×50)'}
    };

    let selectedSize: ImageSize = 'original';
    let isDragging = false;
    let previewUrl: string | null = null;
    let selectedFile: File | null = null;
    let resizedFile: File | null = null;
    let fileInput: HTMLInputElement;

    function handleDragOver(event: DragEvent) {
        event.preventDefault();
        isDragging = true;
    }

    function handleDragLeave() {
        isDragging = false;
    }

    function handleDrop(event: DragEvent) {
        event.preventDefault();
        isDragging = false;

        const files = event.dataTransfer?.files;
        if (files && files.length > 0) {
            handleFile(files[0]);
        }
    }

    function handleFileSelect(event: Event) {
        const input = event.target as HTMLInputElement;
        if (input.files && input.files.length > 0) {
            handleFile(input.files[0]);
        }
    }

    async function handleFile(file: File) {
        // Validate type
        const validTypes = accept.split(',').map(t => t.trim());
        if (!validTypes.includes(file.type)) {
            dispatch('error', {message: `Invalid file type. Allowed: ${accept}`});
            return;
        }

        // Validate size
        if (file.size > maxSizeMB * 1024 * 1024) {
            dispatch('error', {message: `File too large. Max: ${maxSizeMB}MB`});
            return;
        }

        selectedFile = file;
        previewUrl = URL.createObjectURL(file);

        // Auto-process if size is selected
        if (selectedSize !== 'original') {
            await processResize();
        } else {
            resizedFile = file;
        }
    }

    async function processResize() {
        if (!selectedFile || !previewUrl) return;

        if (selectedSize === 'original') {
            resizedFile = selectedFile;
            // Reset preview to original
            if (previewUrl) URL.revokeObjectURL(previewUrl);
            previewUrl = URL.createObjectURL(selectedFile);
            return;
        }

        const config = SIZE_CONFIG[selectedSize];

        try {
            resizedFile = await resizeImage(selectedFile, config.width, config.height);
            // Update preview
            if (previewUrl) URL.revokeObjectURL(previewUrl);
            previewUrl = URL.createObjectURL(resizedFile);
        } catch (err) {
            dispatch('error', {message: 'Failed to resize image'});
        }
    }

    async function resizeImage(file: File, maxWidth: number, maxHeight: number): Promise<File> {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => {
                // Calculate new dimensions (maintain aspect ratio, only shrink)
                let width = img.width;
                let height = img.height;

                if (width > maxWidth || height > maxHeight) {
                    const ratio = Math.min(maxWidth / width, maxHeight / height);
                    width = Math.round(width * ratio);
                    height = Math.round(height * ratio);
                }

                // Create canvas
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;

                const ctx = canvas.getContext('2d');
                if (!ctx) {
                    reject(new Error('Cannot get canvas context'));
                    return;
                }

                // Draw resized image
                ctx.drawImage(img, 0, 0, width, height);

                // Determine output format (preserve transparency)
                let mimeType = file.type;
                let extension = file.name.split('.').pop() || 'png';

                if (mimeType === 'image/gif') {
                    // GIF loses animation when resized, convert to PNG
                    mimeType = 'image/png';
                    extension = 'png';
                }

                // Convert to blob
                canvas.toBlob((blob) => {
                    if (!blob) {
                        reject(new Error('Failed to create blob'));
                        return;
                    }

                    const newName = file.name.replace(/\.[^.]+$/, `.${extension}`);
                    resolve(new File([blob], newName, {type: mimeType}));
                }, mimeType, 0.9);
            };

            img.onerror = () => reject(new Error('Failed to load image'));
            img.src = URL.createObjectURL(file);
        });
    }

    function triggerFileInput() {
        fileInput?.click();
    }

    function confirmUpload() {
        if (resizedFile) {
            dispatch('upload', {file: resizedFile, size: selectedSize});
        }
    }

    function cancel() {
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
        }
        previewUrl = null;
        selectedFile = null;
        resizedFile = null;
        if (fileInput) {
            fileInput.value = '';
        }
    }

    // Re-process when size changes
    $: if (selectedFile && selectedSize) {
        processResize();
    }
</script>

<div class="image-uploader">
    {#if !previewUrl}
        <!-- Drop zone -->
        <div
                class="drop-zone"
                class:dragging={isDragging}
                on:dragover={handleDragOver}
                on:dragleave={handleDragLeave}
                on:drop={handleDrop}
                on:click={triggerFileInput}
                on:keydown={(e) => e.key === 'Enter' && triggerFileInput()}
                role="button"
                tabindex="0"
        >
            <svg class="upload-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <p class="drop-text">{$t('uploads.dropOrClick')}</p>
            <p class="drop-hint">{$t('uploads.maxSize', {values: {size: maxSizeMB}})}</p>
        </div>

        <input
                bind:this={fileInput}
                type="file"
                {accept}
                on:change={handleFileSelect}
                class="hidden-input"
        />
    {:else}
        <!-- Preview -->
        <div class="preview-container">
            <img src={previewUrl} alt="Preview" class="preview-image"/>

            {#if showSizeSelector}
                <div class="size-selector">
                    <span class="size-label">{$t('uploads.imageSize')}:</span>
                    <div class="size-options">
                        {#each Object.entries(SIZE_CONFIG) as [key, config]}
                            <label class="size-option">
                                <input
                                        type="radio"
                                        name="imageSize"
                                        value={key}
                                        bind:group={selectedSize}
                                />
                                <span>{config.label}</span>
                            </label>
                        {/each}
                    </div>
                </div>
            {/if}

            <div class="preview-actions">
                <button type="button" class="btn btn-secondary" on:click={cancel}>
                    {$t('common.cancel')}
                </button>
                <button type="button" class="btn btn-primary" on:click={confirmUpload}>
                    {$t('uploads.upload')}
                </button>
            </div>
        </div>
    {/if}
</div>

<style>
    .image-uploader {
        width: 100%;
    }

    .drop-zone {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        border: 2px dashed #d1d5db;
        border-radius: 0.5rem;
        background-color: #f9fafb;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .drop-zone:hover,
    .drop-zone.dragging {
        border-color: #1a4031;
        background-color: #f0fdf4;
    }

    .upload-icon {
        width: 3rem;
        height: 3rem;
        color: #9ca3af;
        margin-bottom: 0.5rem;
    }

    .drop-text {
        font-size: 0.875rem;
        color: #374151;
        margin: 0;
    }

    .drop-hint {
        font-size: 0.75rem;
        color: #9ca3af;
        margin: 0.25rem 0 0;
    }

    .hidden-input {
        display: none;
    }

    .preview-container {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .preview-image {
        max-width: 100%;
        max-height: 300px;
        object-fit: contain;
        border-radius: 0.5rem;
        border: 1px solid #e5e7eb;
    }

    .size-selector {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .size-label {
        font-size: 0.875rem;
        font-weight: 500;
        color: #374151;
    }

    .size-options {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
    }

    .size-option {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.875rem;
        color: #4b5563;
        cursor: pointer;
    }

    .preview-actions {
        display: flex;
        gap: 0.5rem;
        justify-content: flex-end;
    }

    .btn {
        padding: 0.5rem 1rem;
        border-radius: 0.375rem;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .btn-secondary {
        background-color: white;
        border: 1px solid #d1d5db;
        color: #374151;
    }

    .btn-secondary:hover {
        background-color: #f3f4f6;
    }

    .btn-primary {
        background-color: #1a4031;
        border: 1px solid #1a4031;
        color: white;
    }

    .btn-primary:hover {
        background-color: #143326;
    }
</style>

