# Frontend Components

This section documents the reusable UI components in LibreFolio.

## Component Categories

### Table Components (`lib/components/table/`)

- [DataTable](data-table.md) - Generic data table with advanced features
- DataTablePagination - Sticky pagination balloon
- DataTableToolbar - Bulk actions, column visibility, reorder
- DataTableColumnFilter - Excel-style column filters
- **ModalBase** - Base component for ALL modals (backdrop, click-outside, Escape, focus trap, z-index)
- ConfirmModal - Confirmation dialog for destructive actions (uses ModalBase)

### Authentication (`lib/components/auth/`)

- [Auth Components](auth.md) - **LoginCard**, **RegisterCard**, **ForgotPasswordCard**
- PasswordStrengthMeter - zxcvbn-based password strength indicator
- AnimatedBackground - Animated waves background for login page

!!! note
    These were renamed from `*Modal` to `*Card` because they are card-style forms, not modals.

### Settings (`lib/components/settings/`)

- [Settings Components](settings.md) - User preferences and global settings
- SettingsLayout - Two-column layout with sidebar categories
- PreferencesTab - User preference fields (language, currency, theme)
- GlobalSettingsTab - Admin-only global settings
- **ProfileTab** - User profile with avatar (editable via AssetPickerModal)
- AboutTab - System info and version

### Media Components (`lib/components/ui/media/`)

- [File Upload](file-upload.md) - Multi-file uploader with validation
- **ImageCropper** - cropperjs v2 wrapper (zoom, rotate, flip, free crop)
- **ImageEditModal** - Full image editor (presets, output size, format, quality)
- **FileEditModal** - File rename modal for non-image files
- **AssetPickerModal** - 3-tab picker (Existing files / URL / Upload)
- **ImagePickerWrapper** - Wraps AssetPicker + ImageEdit flow
- **FileUploader** - Upload area with edit/restore per file
- LazyImage - Image with lazy loading and fallback
- **FileGrid** - Shared grid component for files page and asset picker

### Select Components (`lib/components/ui/select/`)

- **BaseDropdown** - Base dropdown with click-outside, keyboard nav, positioning
- **SimpleSelect** - Select from options (like native `<select>`)
- **SearchSelect** - Fuzzy search dropdown (replaces old FuzzySelect)

### Broker Components (`lib/components/brokers/`)

- BrokerCard - Broker display card with icon
- BrokerForm - Create/edit broker form
- **BrokerIcon** - Smart icon with fallback chain (icon_url → favicon → plugin → Briefcase)
- BrokerImportFilesModal - BRIM file import
- BrokerSearchSelect - Broker selector with search and icons
- DeleteBrokerDialog - Confirmation for broker deletion

## Component Guidelines

- **ModalBase**: ALL modals extend `ModalBase.svelte` with configurable z-index
- **Svelte 5 Runes**: Use `$state`, `$derived`, `$effect`, `$props`
- **Event handling**: Use `onclick` instead of `on:click` (Svelte 5 syntax)
- **Styling**: Tailwind CSS utilities + dark mode with `dark:` prefix
- **Accessibility**: Keyboard navigation, ARIA labels, focus management
- **i18n**: All user-facing text via `$t('key')` translation function
