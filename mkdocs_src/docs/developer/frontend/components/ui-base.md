# 🧱 UI Base Components

This section documents the generic, reusable components in `lib/components/ui/` that serve as building blocks for all composite components throughout the application.

---

## Modals

### ModalBase

The **foundation for all modals** in LibreFolio. Every modal in the application extends `ModalBase`.

- **Backdrop** with configurable opacity and click-outside-to-close
- **Escape** key to close
- **Focus trap** — Tab cycles within modal content
- **Configurable z-index** — Supports stacked modals (e.g., ImageEditModal over AssetPickerModal)
- **Scroll lock** — Prevents body scroll when modal is open
- **Animation** — Fade-in/out transition

**Props**: `isOpen`, `onClose`, `zIndex` (default: 50), `closeOnBackdrop` (default: true), `maxWidth`.

**Used by**: [BrokerModal](brokers/modals.md), [BrokerSharingModal](brokers/modals.md), [ImageEditModal](file-upload.md), [ChartSettingsModal](../../frontend/components/data-table.md), and all other modals.

### ConfirmModal

A confirmation dialog for **destructive actions**. Extends `ModalBase`.

- Displays a warning message with customizable title and body
- **Confirm** and **Cancel** buttons with configurable labels
- Confirm button styled as danger (red) by default
- Optional loading state on confirm button

**Used by**: `DeleteBrokerDialog`, file deletion, data editor row deletion.

---

## Feedback & Notifications

### ToastContainer

Global container for **toast notifications** (success, error, info, warning).

- Stacked notifications in bottom-right corner
- Auto-dismiss with configurable timeout
- Manual dismiss via close button
- Color-coded by severity

**Used by**: Global layout — mounted once in the root layout.

### InfoBanner

A **dismissible banner** for contextual information or warnings.

- Variants: `info`, `warning`, `error`, `success`
- Optional icon and dismiss button
- Inline within page content (not a toast)

**Used by**: `BrokerModal` (validation errors), settings pages, import previews.

### LoadingSpinner

A simple **animated spinner** for async loading states.

- Configurable size: `sm`, `md`, `lg`
- Optional label text below spinner

**Used by**: API calls, lazy-loaded content, search results.

### Tooltip

**Hover/focus tooltip** with automatic positioning.

- Positions: `top`, `bottom`, `left`, `right` (auto-adjusts to viewport)
- Delay before showing (prevents flicker on quick mouse movements)
- Accessible: shows on focus for keyboard users

**Used by**: Toolbar buttons, icon-only buttons, info badges.

---

## Date Pickers

### CalendarMonth

A **monthly calendar grid** component — the visual building block for date pickers.

- Displays a single month with day cells
- Highlights today, selected date, and date range
- Keyboard navigation within the grid
- Locale-aware (week starts on Monday for most locales)

**Used by**: `SingleDatePicker`, `DateRangePicker`.

### SingleDatePicker

A **single-date picker** dropdown with calendar.

- Opens a `CalendarMonth` in a dropdown
- Manual text input with date parsing
- Month/year navigation with arrows
- Formats date according to locale

**Used by**: [DataEditor](file-upload.md) (FX rate date), transaction forms.

### DateRangePicker

A **date range picker** with start and end dates.

- Two `CalendarMonth` grids side by side (current + next month)
- Visual highlight of selected range
- Preset ranges: Last 7 days, Last 30 days, Last year, All time
- Start and end date text inputs

**Used by**: Chart toolbar (FX detail page), report filters.

---

## UI Atoms

### ThemeToggle

A **light/dark/auto theme toggle** with animated icons.

- Three states: ☀️ Light, 🌙 Dark, 💻 Auto (follow system)
- Smooth icon transition animation
- Persists choice in user settings

**Used by**: [Settings PreferencesTab](settings.md), header.

### DocsLink

A **link to the MkDocs documentation** with book icon.

- Opens documentation in a new tab
- Configurable target path (defaults to docs root)

**Used by**: Header help menu.

### AnimatedBackground

**Animated SVG waves** for the login page background.

- Multiple layered wave paths with parallax animation
- Theme-aware colors (adapts to light/dark mode)
- Low CPU usage (CSS animations, no JS)

**Used by**: Login page (behind `LoginCard`/`RegisterCard`).

### OrderableList

A **drag-and-drop reorderable list**.

- Drag handles on each item
- Visual feedback during drag (elevated shadow, placeholder)
- Emits reordered array on drop

**Used by**: DataTable column reorder (in `DataTableToolbar`).

---

## Input Components

*Located in `lib/components/ui/input/`*

### PasswordInput

A **password field with visibility toggle** (eye icon).

- Toggle between `type="password"` and `type="text"`
- Eye / EyeOff icon from lucide-svelte

**Used by**: [LoginCard, RegisterCard](auth.md), `PasswordChangeModal`.

### PasswordStrength

A **password strength indicator** powered by `zxcvbn`.

- Color-coded strength bar (red → orange → yellow → green)
- Textual feedback and suggestions
- Score: 0 (very weak) to 4 (very strong)

**Used by**: [RegisterCard](auth.md) (below password field).

---

## Data Editor Components

*Located in `lib/components/ui/data-editor/`*

### DataEditor

An **inline tabular editor** for structured data (add, edit, delete rows).

- Editable cells with type-aware inputs (text, number, date)
- Add row button with empty row template
- Delete row with confirmation
- Validation per cell with error highlighting

**Used by**: FX Data Editor section (editing individual rates on the FX detail page).

### CsvEditor

A **CSV preview and editor** with column detection and per-row validation.

- Parses CSV content and displays as table
- Detects separator (`;`, `,`, `\t`) and header row
- Highlights rows with errors (red) or warnings (yellow)
- Editable cells for manual correction

**Used by**: `DataImportModal` (FX CSV import preview).

### DataImportModal

A **modal for importing data from CSV files**. Extends `ModalBase`.

- Drag & drop file upload zone
- Direction bar for FX pair direction (with swap button)
- Uses `CsvEditor` for preview
- Validation summary before import

**Used by**: FX detail page — "Import CSV" action. See [FX CSV Import](../../../user/fx/detail/data-editor.md) for user documentation.


