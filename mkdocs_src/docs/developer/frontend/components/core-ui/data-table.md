# 📊 DataTable Component

The `DataTable` is a powerful, generic table component built with Svelte 5 Runes. It provides a rich set of features similar to Excel or advanced data grids.

<div class="lf-screenshot-carousel" data-carousel="datatable" data-carousel-interval="3000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="transactions" data-name="list" data-title="Transactions" alt="Transactions Table">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="assets" data-name="list-table" data-title="Assets" alt="Assets Table">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="FX Rates" alt="FX Rates Table">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="files" data-name="static-tab" data-title="Files" alt="Files Table">
</div>

## ⚡ Features

- **Sorting**: Click column headers to sort ASC/DESC.
- **Filtering**: Excel-style column filters (Text, Number, Date, Enum, Multi-enum, Size, Currency).
- **Pagination**: Client-side pagination in a floating balloon, with configurable page sizes — see
  [Pagination](#pagination).
- **Selection**: Row selection with checkboxes, "Select All" on the current page, and a
  "show selected only" filter in the checkbox header.
- **Column Management**: Resize columns in the table; show/hide and drag-to-reorder through
  `ColumnVisibilityToggle`, which the caller places in its own toolbar and hands the table instance
  (`tableRef`, plus `additionalTableRefs` to drive several tables at once); it works through the
  [public methods](#public-methods).
- **Persistence**: Page size, column order, widths and visibility overrides are saved to
  `localStorage` under per-user keys (`lf_{userId}_dataTable_{storageKey}_{suffix}`). Sorting and
  filters are not persisted; filters can round-trip through the URL (`initialFilters`,
  `onFiltersChange`).
- **Actions**: Per-row actions behind a **⋮** button in the actions column, and bulk actions on the
  selected rows. Actions with `requireConfirm` go through a [ConfirmModal](modals.md#confirmmodal).
- **Context Menu**: Right-click on a row opens the same menu as **⋮**, built from `rowActions`.
- **Sticky Columns**: The header, the selection column and pinned columns stick; the actions column
  sticks by default — see [Sticky columns](#sticky-columns).

## 💻 Usage

```svelte
<script lang="ts">
  import { DataTable } from '$lib/components/table';
  import type { ColumnDef, RowAction } from '$lib/components/table/types';
  import { Pencil, Trash2 } from 'lucide-svelte';

  // Define your data type
  type User = { id: string; name: string; role: string; };

  // Define columns
  const columns: ColumnDef<User>[] = [
    {
      id: 'name',
      header: 'Name',
      // Simple text cell
      cell: (row) => row.name,
      sortable: true,
      filterable: true,
      type: 'text'
    },
    {
      id: 'role',
      header: 'Role',
      // Badge cell
      cell: (row) => ({
        type: 'badge',
        text: row.role,
        variant: row.role === 'admin' ? 'success' : 'default'
      }),
      type: 'enum',
      enumOptions: [
        { value: 'admin', label: 'Admin' },
        { value: 'user', label: 'User' }
      ]
    }
  ];

  // Define row actions
  const rowActions: RowAction<User>[] = [
    {
      id: 'edit',
      icon: Pencil,
      label: 'Edit',
      onClick: (row) => console.log('Edit', row)
    },
    {
      id: 'delete',
      icon: Trash2,
      label: 'Delete',
      variant: 'danger',
      requireConfirm: true,
      onClick: (row) => console.log('Delete', row)
    }
  ];
</script>

<DataTable
  data={users}
  columns={columns}
  rowActions={rowActions}
  getRowId={(row) => row.id}
  storageKey="users-table"
/>
```

## 📋 Props

The source of truth is the `Props` interface of `lib/components/table/DataTable.svelte`.

**Data and identity**

| Prop | Type | Default | Description |
|:--|:--|:--|:--|
| `data` | `T[]` | **Required** | Rows to show. |
| `columns` | `ColumnDef<T>[]` | **Required** | Column definitions. |
| `getRowId` | `(row: T) => string` | **Required** | Unique id of a row. |
| `storageKey` | `string` | **Required** | Key of the persisted preferences. |
| `fullData` | `T[]` | — | Full dataset for the filter boundaries (min/max, currencies) when `data` is a pre-paginated slice. |
| `isLoading` | `boolean` | `false` | Shows a loading row (`dt-loading`). |
| `emptyMessage` | `string` | `common.noData` | Text of the empty table. |
| `tableLayout` | `'fixed' \| 'auto'` | `'fixed'` | `auto` lets columns grow to fill the space. |

**Selection**

| Prop | Type | Default | Description |
|:--|:--|:--|:--|
| `enableSelection` | `boolean` | `true` | `false` is the same as `selectionMode="none"`. |
| `selectionMode` | `'multi' \| 'single' \| 'none'` | `'multi'` | Checkboxes, single-row click selection, or none. |
| `selectionColumnWidth` | `string` | `'48px'` | Width of the checkbox column. |
| `initialSelectedIds` | `string[]` | — | Rows selected at mount (e.g. returning to a wizard step). |
| `selectedRowId` | `string \| null` | `null` | Controlled selection in `single` mode. |
| `onSelectionChange` | `(ids: string[]) => void` | — | Called when the selection changes. |
| `isRowSelectable` | `(row: T) => boolean` | — | `false` hides the checkbox (⊘ instead) and excludes the row from bulk selection. |
| `disabledRowTooltip` | `(row: T) => string \| null` | — | Tooltip of the ⊘ icon. |
| `enableTouchSelection` | `boolean` | `false` | A 500 ms long-press toggles the row's selection. Without it, a long-press runs `onRowDoubleClick`. |
| `onShowSelectedOnlyChange` | `(active: boolean) => void` | — | The "show selected only" toggle changed. |

**Rows and actions**

| Prop | Type | Default | Description |
|:--|:--|:--|:--|
| `onRowClick` | `(row: T) => void` | — | Row click. |
| `onRowDoubleClick` | `(row: T) => void` | — | Row double-click. |
| `getRowHref` | `(row: T) => string \| undefined` | — | Middle-click opens the URL in a new tab. |
| `getRowClass`, `getRowStyle` | `(row: T) => string` | — | Extra classes / inline style per row. |
| `getRowDisplayName` | `(row: T) => string` | — | Name of a row in the confirmation lists (falls back to the id). |
| `enableActions` | `boolean` | `true` | Shows the actions column when `rowActions` is given. |
| `rowActions` | `RowAction<T>[] \| (row: T) => RowAction<T>[]` | `[]` | Actions of each row (⋮ menu and context menu). |
| `bulkActions` | `BulkAction<T>[]` | `[]` | Actions on the selected rows. |
| `actionsColumnWidth` | `string` | `'64px'` | Width of the actions column. |
| `actionsLabel` | `string` | `table.actions` | Header and ⋮ label of the actions column. |
| `stickyActions` | `boolean` | `true` | Whether the actions column sticks to the right edge — see [Sticky columns](#sticky-columns). |
| `enableContextMenu` | `boolean` | `true` | Right-click menu on rows. |

**Columns, sorting, filters**

| Prop | Type | Default | Description |
|:--|:--|:--|:--|
| `enableSorting` | `boolean` | `true` | Column sorting. |
| `onSortChange` | `(state: SortState \| null) => void` | — | Sort changed or cleared. |
| `onRowOrderChange` | `(rowIds: string[]) => void` | — | Row ids in display order (after filters and sort, across all pages); called after mount and whenever that order changes. |
| `enableColumnFilters` | `boolean` | `true` | Column filters. |
| `initialFilters` | `Record<string, FilterValue>` | — | Filters applied at mount (from the URL). |
| `onFiltersChange` | `(filters) => void` | — | Filters changed (for URL sync). |
| `enableColumnResize` | `boolean` | `true` | Column resizing. |
| `onColumnResize` | `(columnId: string, width: number) => void` | — | A column was resized (to mirror widths across tables). |
| `stickyHeader` | `boolean` | `true` | Whether the header sticks to the top of the scroll viewport. |
| `footerCells` | `FooterCells<T>` | — | Aggregate footer, computed on the selected rows, or on the filtered rows when nothing is selected. |

**Pagination**

| Prop | Type | Default | Description |
|:--|:--|:--|:--|
| `enablePagination` | `boolean` | `true` | Client-side pagination. |
| `defaultPageSize` | `number` | `10` | Page size until the user picks one (the stored choice wins). |
| `pageSizeOptions` | `number[]` | `[10, 25, 50, 100, 0]` | Choices of the page-size menu; `0` means "all" (shown as ∞). |
| `alwaysShowPagination` | `boolean` | `false` | Show the bar whenever there is at least one row. |

`enableColumnVisibility` is accepted but not read: column visibility is driven from outside, through
`ColumnVisibilityToggle` and the [public methods](#public-methods).

## 📌 Sticky columns {: #sticky-columns }

- The **header** sticks to the top of the vertical scroll viewport (`stickyHeader`, default on).
- The **selection** column and the columns with `pinned: 'left' | 'right'` stick to their edge
  while the table scrolls horizontally.
- The **actions** column sticks to the right edge by default. With `stickyActions={false}` it
  scrolls with the table, and its header stays at the end of the table, aligned with its cells.
  The transactions table, the bulk editor and the import wizard tables turn it off.
- At 768 px and below, the actions column never sticks.

## 📄 Pagination {: #pagination }

The pagination bar (`DataTablePagination.svelte`) floats in a balloon that sticks to the bottom of
the scroll area. It appears when pagination is on and the filtered rows outnumber the smallest
non-zero entry of `pageSizeOptions` — or, with `alwaysShowPagination`, as soon as there is one row.
Changing the page size returns to the first page and is saved under the table's `storageKey`.

The page-size menu is positioned with **fixed** coordinates computed from its trigger
(`getFixedDropdownPosition`, `lib/utils/layout/dropdownPosition.ts`): it opens below the trigger,
or above it when there is no room, stays inside the viewport, scrolls internally when taller than
the screen, and follows the trigger on resize and on any scroll. So in a short table inside a
scrollable modal the menu is not clipped by the modal's overflow and every option stays reachable.

Short tables can offer smaller steps: the bulk editor and the import wizard pass
`pageSizeOptions={[5, 10, 25, 50, 0]}`-style lists.

## 🧭 Public methods {: #public-methods }

Bind the component (`bind:this={tableRef}`) to call them.

| Method | Description |
|:--|:--|
| `navigateToRowId(rowId)` | Moves to the page that holds the row (with the current filters and sort), highlights it with a short pulse and scrolls it into view (smooth, centred). Unknown ids are ignored. The highlight clears on the next row click or key press in the table. |
| `getSortedRowIds()` | Ids of all matching rows in display order, before pagination — check it first to tell a hidden row from a missing one. |
| `getPageRowIds()` | Ids of the rows on the current page. |
| `clearSelection()`, `toggleRowSelectionById(id)` | Selection control. |
| `clearFilters()` | Removes every column filter (and reports it through `onFiltersChange`). |
| `getColumnsForVisibility()`, `toggleColumnVisibilityById(id)`, `setColumnOrder(ids)`, `resetColumnLayout()`, `setColumnWidth(id, width)` | Column layout, for `ColumnVisibilityToggle` and for syncing widths across tables. |

`navigateToRowId` is how a banner or a list sends the user to a row: the bulk transaction editor
jumps to the row of a validation issue or of a todo (`getSortedRowIds()` first, and a warning toast
when the row is filtered out); the lots panel, `DataEditor` ("Add row", chart point click) and
`TransactionsTable` use it as well. The highlighted row carries `data-highlighted="true"`.

## 🔧 Column Definition (`ColumnDef<T>`)

The main fields; `lib/components/table/types.ts` has the full interface.

| Field | Type | Description |
|:--|:--|:--|
| `id` | `string` | Unique identifier for the column. |
| `header` | `string \| () => string` | Header text (a function for i18n). `headerHtml` replaces it with markup; `displayName` names the column in the visibility menu. |
| `cell` | `(row: T) => CellContent` | Cell content, see below. |
| `type` | `'text' \| 'number' \| 'date' \| 'enum' \| 'multi-enum' \| 'size' \| 'currency-stack' \| 'custom'` | Drives the filter UI and the sort. |
| `getValue` | `(row: T) => unknown` | Raw value for sorting and filtering, when it differs from the rendered cell. |
| `sortable`, `filterable`, `resizable` | `boolean` | Default `true`. |
| `width`, `minWidth`, `maxWidth` | `number` | Pixels. |
| `enumOptions` | `EnumOption[]` | `{value, label, iconUrl?, dotColor?, searchText?}` for `enum` columns. |
| `getMultiValue` | `(row: T) => string[]` | Values of a `multi-enum` row (e.g. tags). |
| `getCurrencyValue`, `currencyOptions` | — | `currency-stack` columns: `{code, amount}` of a row, and the currencies on offer. |
| `hiddenByDefault` | `boolean` | Hidden until the user shows it. |
| `pinned` | `'left' \| 'right'` | Sticky column. |
| `align` | `'left' \| 'center' \| 'right'` | Cell and header alignment. |
| `headerTooltip`, `headerTooltipUrl` | `string \| () => string` | Info icon on the header, optionally linking a documentation page. |
| `urlKey` | `string` | URL parameter of the column's filter (default: the id). |
| `integerOnly` | `boolean` | Integer-only number filter. |

## 🎨 Cell Content Types

The `cell` function can return a simple string/number or a structured object:

- **Text**: `string` or `number`
- **Icon + Text**: `{ type: 'icon-text', icon: Component, text: string, iconClass?: string }`
- **Image**: `{ type: 'image', src: string, alt: string, text?: string, fallbackIcon?: Component, size?: number, circle?: boolean }` (thumbnail with fallback icon, default 32 px)
- **Badge**: `{ type: 'badge', text: string, variant: 'success'|'warning'|'error'|'info'|'default', customStyle?: string }`
- **Date**: `{ type: 'date', value: Date | string, format?: 'date'|'datetime'|'time'|'relative' }`
- **Size**: `{ type: 'size', bytes: number }` (Auto-formats to KB/MB/GB, i18n-aware)
- **Link**: `{ type: 'link', text: string, href: string, external?: boolean }`
- **HTML**: `{ type: 'html', html: string, tooltip?: {...}, onClick?: () => void, testId?: string }`
- **Editable**: `editable-number`, `editable-text`, `editable-select`, `editable-checkbox` — inline
  inputs that report through their `onchange`
- **Custom**: `{ type: 'custom', component: Component, props: object }`

!!! warning "`html` is rendered as-is"

    `html` cells, `headerHtml` and `html` footer cells go through `{@html}` without sanitising.
    Escape every user- or provider-supplied value with `escapeHtml`
    (`$lib/utils/core/escapeHtml.ts`) when you build the string. The gate
    `frontend/src/htmlInterpolation.gate.test.ts` flags HTML templates that interpolate such a
    value unescaped.

## 📦 State Management (Internal)

The component uses Svelte 5 Runes for internal state:

- `$state` for sorting, pagination, filters, selection and the column layout.
- `$derived` for calculating filtered/sorted/paginated data efficiently.
- Preferences are read from `localStorage` on mount and written back when they change.
- The pure decision logic — cell value extraction, filter predicates, typed comparison, min/max and
  enum options — lives in `dataTableLogic.ts`, unit-tested in `dataTableLogic.test.ts`;
  `DataTable.test.ts` covers the wiring and the public methods.
