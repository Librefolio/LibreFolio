<!--
  ImagePickerWrapper - Encapsulates the full image picker flow:
    1. AssetPickerModal (URL / Existing / Upload)
    2. ImageEditModal (crop & edit for uploaded images)

  Deduplicates the pattern used identically in BrokerForm (icon)
  and ProfileTab (avatar), and any future image picker needs.

  Svelte 5 runes.

  Usage:
    <ImagePickerWrapper
        preset="avatar"
        title={$_('settings.selectAvatar')}
        initialUrl={avatarUrl}
        circularPreview={true}
        onchange={(url) => avatarUrl = url}
        oncancel={() => {}}
    />
-->
<script lang="ts">
    import AssetPickerModal from './AssetPickerModal.svelte';
    import ImageEditModal from './ImageEditModal.svelte';
    import type {PresetName} from '$lib/utils/imageCrop';

    interface Props {
        /** Whether the picker modal is open */
        open?: boolean;
        /** Title for the AssetPickerModal */
        title?: string;
        /** Preset for ImageEditModal (avatar, broker-icon, asset-icon, custom) */
        preset?: PresetName;
        /** Pre-populate URL input with existing value */
        initialUrl?: string;
        /** Show circular preview overlay */
        circularPreview?: boolean;
        /** Filter to only show images in the existing tab */
        filterImages?: boolean;
        /** Callback when a URL is selected */
        onchange?: (url: string) => void;
        /** Callback when the picker is cancelled */
        oncancel?: () => void;
    }

    let {
        open = $bindable(false),
        title = '',
        preset = 'custom',
        initialUrl = '',
        circularPreview = false,
        filterImages = true,
        onchange,
        oncancel,
    }: Props = $props();

    // Internal state
    let showImageEditor = $state(false);
    let imageEditorFile = $state<File | null>(null);

    // Handle asset picker selection (URL or existing file)
    function handlePickerSelect(event: CustomEvent<{ url: string }>) {
        const url = event.detail.url;
        if (!url || url === '__upload__') return;
        open = false;
        onchange?.(url);
    }

    // Handle asset picker upload request
    function handlePickerUpload(event: CustomEvent<{ file: File }>) {
        imageEditorFile = event.detail.file;
        // Hide picker temporarily, show image editor
        open = false;
        showImageEditor = true;
    }

    // Handle picker cancel
    function handlePickerCancel() {
        open = false;
        oncancel?.();
    }

    // Handle image editor complete (upload done, got URL)
    function handleEditorComplete(event: CustomEvent<{ url: string | null; file: File }>) {
        showImageEditor = false;
        imageEditorFile = null;
        if (event.detail.url) {
            onchange?.(event.detail.url);
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
    function handleEditorError(event: CustomEvent<{ message: string }>) {
        console.error('ImagePickerWrapper: upload error:', event.detail.message);
    }
</script>

<!-- Asset Picker Modal -->
<AssetPickerModal
        {circularPreview}
        {filterImages}
        {initialUrl}
        on:cancel={handlePickerCancel}
        on:select={handlePickerSelect}
        on:upload={handlePickerUpload}
        {open}
        {title}
/>

<!-- Image Edit Modal (shown when user uploads from picker) -->
<ImageEditModal
        file={imageEditorFile}
        on:cancel={handleEditorCancel}
        on:complete={handleEditorComplete}
        on:error={handleEditorError}
        open={showImageEditor}
        {preset}
/>
