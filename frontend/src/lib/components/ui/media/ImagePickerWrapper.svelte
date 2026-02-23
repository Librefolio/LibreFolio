<!--
  ImagePickerWrapper - Encapsulates the full image picker flow:
    1. AssetPickerModal (URL / Existing / Upload)
    2. ImageEditModal (crop & edit for uploaded images)

  Deduplicates the pattern used identically in BrokerForm (icon)
  and ProfileTab (avatar), and any future image picker needs.

  Usage:
    <ImagePickerWrapper
        preset="avatar"
        title={$_('settings.selectAvatar')}
        initialUrl={avatarUrl}
        circularPreview={true}
        on:change={(e) => avatarUrl = e.detail.url}
        on:cancel={() => {}}
    />
-->
<script lang="ts">
    import {createEventDispatcher} from 'svelte';
    import AssetPickerModal from './AssetPickerModal.svelte';
    import ImageEditModal from './ImageEditModal.svelte';
    import type {PresetName} from '$lib/utils/imageCrop';

    // Props
    /** Whether the picker modal is open */
    export let open: boolean = false;
    /** Title for the AssetPickerModal */
    export let title: string = '';
    /** Preset for ImageEditModal (avatar, broker-icon, custom) */
    export let preset: PresetName = 'custom';
    /** Pre-populate URL input with existing value */
    export let initialUrl: string = '';
    /** Show circular preview overlay */
    export let circularPreview: boolean = false;
    /** Filter to only show images in the existing tab */
    export let filterImages: boolean = true;

    const dispatch = createEventDispatcher<{
        /** Emitted when a URL is selected (from URL tab, existing tab, or after upload+crop) */
        change: {url: string};
        /** Emitted when the picker is cancelled */
        cancel: void;
    }>();

    // Internal state
    let showImageEditor = false;
    let imageEditorFile: File | null = null;

    // Handle asset picker selection (URL or existing file)
    function handlePickerSelect(event: CustomEvent<{url: string}>) {
        const url = event.detail.url;
        if (!url || url === '__upload__') return;
        open = false;
        dispatch('change', {url});
    }

    // Handle asset picker upload request
    function handlePickerUpload(event: CustomEvent<{file: File}>) {
        imageEditorFile = event.detail.file;
        // Hide picker temporarily, show image editor
        open = false;
        showImageEditor = true;
    }

    // Handle picker cancel
    function handlePickerCancel() {
        open = false;
        dispatch('cancel');
    }

    // Handle image editor complete (upload done, got URL)
    function handleEditorComplete(event: CustomEvent<{url: string | null; file: File}>) {
        showImageEditor = false;
        imageEditorFile = null;
        if (event.detail.url) {
            dispatch('change', {url: event.detail.url});
        }
    }

    // Handle image editor cancel → re-open picker
    function handleEditorCancel() {
        showImageEditor = false;
        imageEditorFile = null;
        // Re-open the asset picker so user can try again
        open = true;
    }

    // Handle image editor error
    function handleEditorError(event: CustomEvent<{message: string}>) {
        console.error('ImagePickerWrapper: upload error:', event.detail.message);
    }
</script>

<!-- Asset Picker Modal -->
<AssetPickerModal
    {open}
    {title}
    {filterImages}
    {initialUrl}
    {circularPreview}
    on:select={handlePickerSelect}
    on:upload={handlePickerUpload}
    on:cancel={handlePickerCancel}
/>

<!-- Image Edit Modal (shown when user uploads from picker) -->
<ImageEditModal
    open={showImageEditor}
    file={imageEditorFile}
    {preset}
    on:complete={handleEditorComplete}
    on:cancel={handleEditorCancel}
    on:error={handleEditorError}
/>

