# File Upload Components

*Status: Draft - Components implemented, documentation in progress*

## Overview

File upload components with multi-file support, validation, and preview.

## Components

### FileUploader

Multi-file uploader with:

- Drag & drop support
- Click to browse
- File type validation
- Size validation
- Progress indicator
- Preview for images
- Remove before upload

## Files

```
frontend/src/lib/components/ui/
├── FileUploader.svelte
└── LazyImage.svelte
```

## Basic Usage

```svelte
<script lang="ts">
  import FileUploader from '$lib/components/ui/FileUploader.svelte';
  
  function handleUpload(event: CustomEvent<{ files: File[] }>) {
    const { files } = event.detail;
    // Upload files to server
  }
</script>

<FileUploader
  accept="image/*,.pdf,.csv"
  maxSize={10 * 1024 * 1024}
  multiple={true}
  onupload={handleUpload}
/>
```

## Props

| Prop       | Type      | Default | Description            |
|------------|-----------|---------|------------------------|
| `accept`   | `string`  | `*`     | Accepted file types    |
| `maxSize`  | `number`  | `10MB`  | Max file size in bytes |
| `multiple` | `boolean` | `true`  | Allow multiple files   |
| `disabled` | `boolean` | `false` | Disable upload         |

## Events

| Event    | Payload               | Description            |
|----------|-----------------------|------------------------|
| `upload` | `{ files: File[] }`   | Files ready for upload |
| `error`  | `{ message: string }` | Validation error       |

## Validation

- File type checking against `accept` prop
- File size checking against `maxSize` prop
- Client-side only (server validates again)

## Future Enhancements

- [ ] Image crop before upload
- [ ] Chunk upload for large files
- [ ] Upload progress per file
