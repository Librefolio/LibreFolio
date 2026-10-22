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
- **Column Management**: Resize columns by dragging a header cell's right edge, with a mouse, a
  finger or a pen — see [Column resize](#column-resize); show/hide and drag-to-reorder through
  `ColumnVisibilityToggle`, which the caller places in its own toolbar and hands the table instance
  (`tableRef`, plus `additionalTableRefs` to drive several tables at once); it works through the
  [public methods](#public-methods).
- **Persistence**: Page size, column order, widths and visibility overrides are saved to
  `localStorage` under per-user keys (`lf_{userId}_dataTable_{storageKey}_{suffix}`). Sorting and
  filters are not persisted; filters can round-trip through the URL (`initialFilters`,
  `onFiltersChange`). A column absent from `columns` for a while — the Assets and FX tables'
  Δ period columns until the backend lists the periods, or those longer than a short date range —
  keeps its saved place, visibility and width: the table adds only the columns it has never seen,
  at their natural place (right after the last column that precedes them in `columns`), and a
  reorder in `ColumnVisibilityToggle`, which lists only the columns present, puts an absent column
  back right after the one it followed. `resetColumnLayout()` returns to the defaults of the
  columns present and forgets the absent ones.
- **Actions**: Per-row actions behind a **⋮** button in the actions column, and bulk actions on the
  selected rows. Actions with `requireConfirm` go through a [ConfirmModal](modals.md#confirmmodal).
- **Context Menu**: Right-click on a row opens the same menu as **⋮**, built from `rowActions`.
- **Sticky Columns**: The header row sticks inside the table's scroll area; the selection column,
  pinned columns and, by default, the actions column stick to their edge while the table scrolls
  sideways — on phones the selection and actions columns scroll with it. See
  [Sticky columns](#sticky-columns).

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
| `tableLayout` | `'fixed' \| 'auto'` | `'fixed'` | `fixed` sizes the columns from their header cells' widths; `auto` from their content as well, so a width becomes a preference — see [Column resize](#column-resize). |

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
| `stickyActions` | `boolean` | `true` | Whether the actions column sticks to the right edge, above 768 px — see [Sticky columns](#sticky-columns). |
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
| `enableColumnResize` | `boolean` | `true` | Resize handles on the data columns (a column opts out with `resizable: false`) — see [Column resize](#column-resize). |
| `onColumnResize` | `(columnId: string, width: number) => void` | — | Called at the end of a resize with the width written for the column, to mirror it on other tables through `setColumnWidth`. |
| `stickyHeader` | `boolean` | `true` | Whether the header row sticks to the top of the table's own scroll area — not the page; see [Sticky columns](#sticky-columns). |
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

- The **header** row sticks to the top of the table's own scroll area, `div.table-wrapper`
  (`data-testid="dt-scroll"`), never to the page (`stickyHeader`, default on). The wrapper's
  `overflow-x: auto` makes its `overflow-y` compute to `auto` too, so the wrapper is the scroll
  container its sticky cells stick within: the header sticks only when the wrapper itself scrolls
  vertically, which needs a bounded height on it. When the page scrolls, the header leaves with the
  table.
- The **selection** column (`th-select`/`td-select`, `left: 0`) and the columns with
  `pinned: 'left' | 'right'` stick to their edge while the table scrolls horizontally.
- The **actions** column (`th-actions`/`td-actions`, `right: 0`) sticks to the right edge by
  default. With `stickyActions={false}` it scrolls with the table, and its header stays at the end
  of the table, aligned with its cells. The transactions table, the bulk editor and the import
  wizard tables turn it off.
- At **768 px and below** (the `@media (max-width: 768px)` block of `DataTable.svelte`), the
  selection and actions columns scroll with the table — header, body and footer cells alike
  (decision D-Y17). The body and footer cells become `position: static`; the header cells drop only
  their horizontal pin (`left: auto; right: auto`) and keep `position: sticky` — and, with
  `stickyHeader`, `top: 0` — so the header row still sticks inside its scroll area. Data columns
  with `pinned` keep their pin at every width.
- A **row's tint** keeps the fixed cells opaque. A body row paints the card and, over it, the tint
  of its state, `--dt-row-tint` (hover, selected, highlighted, analyzed), as one image layer
  (`linear-gradient(tint, tint)` over `--lf-surface-card`). `--dt-row-tint` is registered with
  `@property` (`<color>`), so a change of state fades. The row is therefore opaque, and the fixed
  cells, which inherit its background, hide what scrolls under them. A list that tints its rows
  through `getRowClass` sets `--dt-row-tint` on the row, **never the row's `background`** — a
  translucent background would let the scrolling cells show through the fixed ones. Example:
  `AssetTable`, whose `asset-row-inactive` class sets `--dt-row-tint: var(--lf-warning-soft)` for
  the inactive asset.
- A **deleted row** (`tr.row-deleted`, set through `getRowClass` by the data editor and the transactions bulk editor) is not faded with `opacity`: its cells are
  opaque (the danger tint at 55 % over the card) and a veil (`td::after`, the same background at
  45 %, `pointer-events: none`) fades the content, so fixed cells never show what scrolls beneath
  (TC-21).

The header and body cells of the two columns carry test ids: `dt-select-header` and
`dt-select-cell-{rowId}`, `dt-actions-header` and `dt-actions-cell-{rowId}` (the footer cells have
none). `frontend/e2e/layout/datatable-mobile.spec.ts`, run by
`./dev.py test front-utility datatable-mobile`, checks the phone layout at 390 px on the
transactions table (`stickyActions={false}`) and on the Files static list (sticky actions), and
guards the header row's stickiness inside a scroll area it bounds to the header and two rows.

!!! note "Undoing a pin takes a more specific selector"

    `thead.sticky-header th` (0,1,2), the rule that makes the header cells sticky, outranks a bare
    `.th-actions` (0,1,0): a plain `.th-actions { position: static }` leaves the **Actions** header
    pinned at the right edge while its **⋮** cells scroll away. Each phone override is one class
    more specific than the pin it undoes — `.datatable .th-select` against `.th-select`,
    `.datatable .th-actions.th-fixed` against `.th-actions.th-fixed`, `.datatable .td-select` and
    `.datatable .td-actions` against `.td-fixed` — and the header cells change only `left` and
    `right`, never `position`. These are the specificities of the source selectors: Svelte's
    scoping class adds the same to every rule.

## 📏 Column resize {: #column-resize }

A data column's header cell ends in a resize handle: `span.resize-handle` in
`DataTableColumnHeader.svelte`, the cell's last 6 px, with `cursor: col-resize`, transparent until
the cell is hovered. It is there when `enableColumnResize` is on and the column is not
`resizable: false`; the selection and actions columns have none. The drag runs in
`DataTable.svelte` (decision D-Y18):

- **Any pointer.** The handle answers Pointer Events: `startResize`, its `onpointerdown`, captures
  the pointer, and `pointermove`, `pointerup` and `pointercancel` listeners on `document` follow
  it, so a mouse, a finger or a pen resizes the column. Only the primary mouse button starts a
  drag, and the moves and releases of other pointers are ignored. `touch-action: none` on the
  handle keeps a finger drag from panning the table. The listeners are removed when the drag ends,
  or when the table unmounts mid-drag.
- **The drawn width follows the pointer.** The drag starts from the width the column is drawn at
  (the header cell's `getBoundingClientRect().width`), not the configured one, and aims at that
  width plus the pointer's travel, clamped to the column's `minWidth` (default 50) and `maxWidth`
  (default 600). A table that shares its spare width among its columns — `tableLayout="auto"`, or a
  fixed table narrower than its box — draws a column wider than the width it is given, so
  `fitDrawnWidth()` writes a width (and the same `min-width`) on the header cell, measures the cell
  and corrects the width — first assuming the drawn width is proportional to the given one, then
  by a few secant steps — until the drawn width matches the target. On a fixed table wider than its
  box the first guess is exact.
- **A resized column keeps its width.** A column whose width differs from its default
  (`width ?? 150`) — resized, restored from `localStorage` or set through `setColumnWidth` — also
  gets that width as its header cell's `min-width` (`columnMinWidth()`), so an auto-layout table
  keeps it, for example on a narrow screen where `auto` would otherwise draw every column at its
  minimum. The other columns keep `minWidth || 60`; `resetColumnLayout()` restores the default
  widths, and with them those minimums.
- **End of the drag.** On `pointerup` or `pointercancel` the widths are saved to `localStorage`,
  and `onColumnResize(columnId, width)` receives the width written: on a table with spare width it
  is smaller than the drawn one. It is the value `setColumnWidth` takes on the tables that mirror
  the resize.

E2E specs find the handle by what it is to the pointer — the element under the header cell's right
edge whose computed cursor is `col-resize` — never by its class (`datatable-resize.spec.ts`,
`risk-lab.spec.ts`, `risk-analysis.spec.ts`): keep that cursor on the handle.
`frontend/e2e/layout/datatable-resize.spec.ts`, run by
`./dev.py test front-utility datatable-resize`, drags it with a mouse on the Files static list
(`tableLayout="auto"`) at 1280 px and at 390 px, where the table is wider than its box and the
table's scroll width must grow with the column (a resized column keeps its width); on the
transactions table (fixed, the control); and with a finger at 390 px on the transactions table, to
test the input path alone: every drag must change the drawn width by its own length, within 4 px.

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
| `width`, `minWidth`, `maxWidth` | `number` | Pixels. `width` defaults to 150. A resize stays within `minWidth` (default 50) and `maxWidth` (default 600); the header cell's `min-width` is `minWidth` (default 60) until the column's width differs from its default — see [Column resize](#column-resize). |
| `enumOptions` | `EnumOption[]` | `{value, label, iconUrl?, dotColor?, searchText?}` for `enum` columns. |
| `getMultiValue` | `(row: T) => string[]` | Values of a `multi-enum` row (e.g. tags). |
| `getCurrencyValue`, `currencyOptions` | — | `currency-stack` columns: `{code, amount}` of a row, and the currencies on offer. |
| `hiddenByDefault` | `boolean` | Hidden until the user shows it. |
| `pinned` | `'left' \| 'right'` | Sticks to that edge while the table scrolls sideways, at every width — see [Sticky columns](#sticky-columns). |
| `align` | `'left' \| 'center' \| 'right'` | Cell and header alignment. |
| `headerTooltip`, `headerTooltipUrl` | `string \| () => string` | `headerTooltip` alone puts a tooltip on the header label. With `headerTooltipUrl` as well, an info icon appears that opens the documentation page in a new tab. |
| `headerTooltipLinkMode` | `'direct' \| 'gesture'` | How the info icon opens the page: a plain link (`'direct'`, the default), or a button that opens it on double click, Shift+Enter or long press (`'gesture'`). |
| `urlKey` | `string` | URL parameter of the column's filter (default: the id). |
| `integerOnly` | `boolean` | Integer-only number filter. |

## 📅 Date filter {: #date-filter }

The filter of a `date` column (`DataTableColumnFilter.svelte`) is a `DateRangePicker` without
presets (`compact`, `stacked`), and it applies a `DateFilter`, `{type: 'date', from?, to?}`
(`types.ts`). Either end may stay blank: `matchesColumnFilter` (`dataTableLogic.ts`) drops a row only
before `from` or after `to`, as does `TransactionsTable`'s own pre-filter, so a date in «From» alone
keeps the rows from that day on, and one in «To» alone the rows up to that day. In the URL the filter
reads `from,to`, either side empty (`lib/utils/urlFilters.ts`); the Transactions page keeps its own
`date_start` and `date_end` (`routes/(app)/transactions/filterState.ts`).

The picker cannot make a filter of one day
([No range of a single day](datePickers.md#no-single-day-range)). Until Y-N65, a date typed in
«From» alone filled «To» with the same date, so the filter kept that day only. A one-day filter that
arrives through the URL still applies as it is.

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

    `html` cells, `headerHtml` and `html` footer cells go through `{@html}` without sanitising, in
    `DataTableCellContent.svelte` (cells and footer cells) and `DataTableColumnHeader.svelte`
    (`headerHtml`), both listed as reviewed sinks in `frontend/src/htmlSink.gate.test.ts`.
    Escape every user- or provider-supplied value with `escapeHtml`
    (`$lib/utils/core/escapeHtml.ts`) when you build the string. The gate
    `frontend/src/htmlInterpolation.gate.test.ts` flags HTML templates that interpolate such a
    value unescaped.

## 📦 State Management (Internal)

The component uses Svelte 5 Runes for internal state:

- `$state` for sorting, pagination, filters, selection and the column layout.
- `$derived` for calculating filtered/sorted/paginated data efficiently.
- Preferences are read from `localStorage` on mount and written back when they change.
- The pure decision logic — cell value extraction, filter predicates, typed comparison, min/max,
  enum options and the column-order rules (`withNewColumns` for the effect that syncs the order
  with `columns`, `reorderKeepingAbsent` for `setColumnOrder`) — lives in `dataTableLogic.ts`,
  unit-tested in `dataTableLogic.test.ts`; `DataTable.test.ts` covers the wiring and the public
  methods.

**Where DataTable's code lives.** Consumers use `DataTable.svelte` only. It renders two children
that are internal — `table/index.ts` does not export them — and that hold markup and styles, but no
table state:

| File | Holds |
|:--|:--|
| `DataTable.svelte` | The public API (the `Props` interface and the public methods), all the table's state (`$state`, `$derived`), its effects and its handlers. The structure of the table: `table`, `thead`, `tbody`, `tfoot`; the rows with their handlers (click, double click, middle click, context menu, long press); every `th` and `td` with its classes, sticky offsets and test ids; the selection and actions columns, the loading and empty rows, the pagination, the context menu and the two confirm modals. And the styles of all that, structural rules included: sticky columns, z-index, row states. |
| `DataTableColumnHeader.svelte` | The content of one data-column header (`div.header-content` inside `th.th-data`): the sort button with the `header` text or the `headerHtml`, wrapped in the `headerTooltip` when there is one; with a `headerTooltipUrl` as well, the info icon — a link, or with `headerTooltipLinkMode: 'gesture'` a button that opens the URL on double click, Shift+Enter or long press; the filter button and its `DataTableColumnFilter` popover; the resize handle. The parent's state and handlers arrive as props under their parent names, and `openFilterColumnId` is bound, since the parent owns it; the header's only `$state` is `filterBtn`, the popover's anchor. The tooltip's long-press timer stays in the parent, whose `onDestroy` cancels it. |
| `DataTableCellContent.svelte` | The switch over the kinds of `CellContent` listed above, with their styles and the input handling of the editable kinds. Footer cells render through it too — `FooterCellContent` (text, number or `html`) is a subset of `CellContent` — so a clickable `html` footer cell with a `testId` now carries its `data-testid`, exactly like a body cell. |
| `dataTableLogic.ts` | The pure logic of the last bullet above. Each component imports what it uses: the parent the filter predicate, the comparison and the column-order rules, the header the filter's boundaries and options, the cell `formatCellDate`. |

Like the parent, each child imports `$lib/theme/components/table.css`, the area file of the
`--lf-cmp-datatable-*` tokens it reads: the token gate
(`frontend/src/themeComponentTokens.gate.test.ts`) requires that import in every component that
reads a token. Svelte scopes styles per component, so the selectors that cross the boundary use
`:global` — the parent's `:has(:global(.cell-editable-select-wrapper))`, on the `td` and the
`tbody tr` that hold an editable select, and the header's `:global(th:hover) .resize-handle` — and
Svelte checks neither against the other side's markup: a rename there breaks them silently. The
`.filter-btn` rules are in both files, the same in each: the parent's for the "show selected only"
toggle of the selection header, the header's for the column filter.
