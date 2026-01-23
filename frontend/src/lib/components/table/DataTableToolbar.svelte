<!--
  DataTableToolbar - Toolbar with bulk actions and column visibility toggle
-->
<script lang="ts">
	import { t } from '$lib/i18n';
	import { Eye, EyeOff, RotateCcw, GripVertical, ChevronUp, ChevronDown } from 'lucide-svelte';
	import type { Component } from 'svelte';

	interface ColumnInfo {
		id: string;
		header: string | (() => string);
	}

	interface BulkActionInfo {
		id: string;
		icon: Component;
		label: string | (() => string);
		variant?: 'default' | 'danger';
		onClick: () => void;
	}

	interface Props {
		selectedCount: number;
		columns: ColumnInfo[];
		columnVisibility: Record<string, boolean>;
		bulkActions: BulkActionInfo[];
		onToggleColumn: (columnId: string) => void;
		onResetColumns: () => void;
		onReorderColumns?: (newOrder: string[]) => void;
	}

	let { selectedCount, columns, columnVisibility, bulkActions, onToggleColumn, onResetColumns, onReorderColumns }: Props = $props();

	let showColumnDropdown = $state(false);

	// Drag & drop state
	let draggedColumnId = $state<string | null>(null);
	let dragOverColumnId = $state<string | null>(null);

	function getColumnLabel(col: ColumnInfo): string {
		return typeof col.header === 'function' ? col.header() : col.header;
	}

	function getActionLabel(action: BulkActionInfo): string {
		return typeof action.label === 'function' ? action.label() : action.label;
	}

	function isColumnVisible(columnId: string): boolean {
		return columnVisibility[columnId] !== false;
	}

	// Drag handlers
	function handleDragStart(columnId: string) {
		draggedColumnId = columnId;
	}

	function handleDragOver(e: DragEvent, columnId: string) {
		e.preventDefault();
		if (draggedColumnId && draggedColumnId !== columnId) {
			dragOverColumnId = columnId;
		}
	}

	function handleDragLeave() {
		dragOverColumnId = null;
	}

	function handleDrop(e: DragEvent, targetColumnId: string) {
		e.preventDefault();
		if (draggedColumnId && draggedColumnId !== targetColumnId && onReorderColumns) {
			// Calculate new order
			const currentOrder = columns.map(c => c.id);
			const draggedIndex = currentOrder.indexOf(draggedColumnId);
			const targetIndex = currentOrder.indexOf(targetColumnId);

			// Remove dragged item and insert at target position
			const newOrder = [...currentOrder];
			newOrder.splice(draggedIndex, 1);
			newOrder.splice(targetIndex, 0, draggedColumnId);

			onReorderColumns(newOrder);
		}
		draggedColumnId = null;
		dragOverColumnId = null;
	}

	function handleDragEnd() {
		draggedColumnId = null;
		dragOverColumnId = null;
	}

	// Mobile: move column up/down with buttons
	function moveColumnUp(columnId: string) {
		if (!onReorderColumns) return;
		const currentOrder = columns.map(c => c.id);
		const index = currentOrder.indexOf(columnId);
		if (index > 0) {
			const newOrder = [...currentOrder];
			[newOrder[index - 1], newOrder[index]] = [newOrder[index], newOrder[index - 1]];
			onReorderColumns(newOrder);
		}
	}

	function moveColumnDown(columnId: string) {
		if (!onReorderColumns) return;
		const currentOrder = columns.map(c => c.id);
		const index = currentOrder.indexOf(columnId);
		if (index < currentOrder.length - 1) {
			const newOrder = [...currentOrder];
			[newOrder[index], newOrder[index + 1]] = [newOrder[index + 1], newOrder[index]];
			onReorderColumns(newOrder);
		}
	}

	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.column-dropdown-container')) {
			showColumnDropdown = false;
		}
	}

	$effect(() => {
		if (showColumnDropdown) {
			document.addEventListener('click', handleClickOutside);
			return () => document.removeEventListener('click', handleClickOutside);
		}
	});
</script>

<div class="toolbar">
	<div class="toolbar-left">
		<!-- Empty or can add other controls later -->
	</div>
	<div class="toolbar-right">
		{#if selectedCount > 0}
			<span class="selected-count">{selectedCount} {$t('table.selected')}</span>
			<div class="bulk-actions">
				{#each bulkActions as action}
					<button
						type="button"
						class="bulk-btn"
						class:danger={action.variant === 'danger'}
						onclick={action.onClick}
						title={getActionLabel(action)}
					>
						<action.icon size={16} />
					</button>
				{/each}
			</div>
			<div class="divider"></div>
		{/if}
		<div class="column-dropdown-container">
			<button
				type="button"
				class="toolbar-btn"
				onclick={() => showColumnDropdown = !showColumnDropdown}
				title={$t('table.showColumns') || 'Show/Hide Columns'}
			>
				<Eye size={16} />
			</button>
			{#if showColumnDropdown}
				<div class="column-dropdown">
					<div class="dropdown-header">{$t('table.showColumns')}</div>
					<div class="dropdown-content">
					{#each columns as col}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<!-- svelte-ignore a11y_click_events_have_key_events -->
						<div
							class="column-option"
							class:dragging={draggedColumnId === col.id}
							class:drag-over={dragOverColumnId === col.id}
							draggable="true"
							role="button"
							tabindex="0"
							ondragstart={() => handleDragStart(col.id)}
							ondragover={(e) => handleDragOver(e, col.id)}
							ondragleave={handleDragLeave}
							ondrop={(e) => handleDrop(e, col.id)}
							ondragend={handleDragEnd}
							onclick={(e) => {
								const target = e.target as HTMLElement;
								if (!target.closest('.col-drag') && !target.closest('.col-reorder')) {
									onToggleColumn(col.id);
								}
							}}
							onkeydown={(e) => {
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									onToggleColumn(col.id);
								}
							}}
						>
								<span class="col-visibility-icon">
									{#if isColumnVisible(col.id)}
										<Eye size={16} />
									{:else}
										<EyeOff size={16} />
									{/if}
								</span>
								<span class="col-name">{getColumnLabel(col)}</span>
								<!-- Desktop: drag handle -->
								<span class="col-drag desktop-only"><GripVertical size={14} /></span>
								<!-- Mobile: up/down buttons -->
								<span class="col-reorder mobile-only">
									<button
										type="button"
										class="reorder-btn"
										onclick={(e) => { e.stopPropagation(); moveColumnUp(col.id); }}
										disabled={columns.indexOf(col) === 0}
									>
										<ChevronUp size={12} />
									</button>
									<button
										type="button"
										class="reorder-btn"
										onclick={(e) => { e.stopPropagation(); moveColumnDown(col.id); }}
										disabled={columns.indexOf(col) === columns.length - 1}
									>
										<ChevronDown size={12} />
									</button>
								</span>
							</div>
						{/each}
					</div>
					<button type="button" class="reset-btn" onclick={onResetColumns}>
						<RotateCcw size={14} />
						<span>Reset</span>
					</button>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.toolbar { display: flex; justify-content: flex-end; align-items: center; padding: 0.375rem 0; gap: 0.75rem; }
	.toolbar-left { display: flex; align-items: center; gap: 0.75rem; }
	.toolbar-right { display: flex; align-items: center; gap: 0.5rem; }
	.selected-count { font-size: 0.8125rem; color: #1a4031; font-weight: 500; }
	:global(.dark) .selected-count { color: #4ade80; }
	.bulk-actions { display: flex; gap: 0.25rem; }
	.divider { width: 1px; height: 1.5rem; background: #e2e8f0; }
	:global(.dark) .divider { background: #334155; }
	.bulk-btn { display: flex; align-items: center; justify-content: center; width: 28px; height: 28px; border: none; border-radius: 6px; background: #f1f5f9; color: #64748b; cursor: pointer; transition: all 0.15s; }
	.bulk-btn:hover { background: #e2e8f0; color: #0f172a; }
	.bulk-btn.danger { color: #dc2626; }
	.bulk-btn.danger:hover { background: #fef2f2; color: #b91c1c; }
	:global(.dark) .bulk-btn { background: #334155; color: #94a3b8; }
	:global(.dark) .bulk-btn:hover { background: #475569; color: #f1f5f9; }
	:global(.dark) .bulk-btn.danger { color: #f87171; }
	:global(.dark) .bulk-btn.danger:hover { background: #7f1d1d; color: #fecaca; }
	.toolbar-btn { display: flex; align-items: center; justify-content: center; width: 28px; height: 28px; border: none; border-radius: 6px; background: #f1f5f9; color: #64748b; cursor: pointer; transition: all 0.15s; }
	.toolbar-btn:hover { background: #e2e8f0; color: #0f172a; }
	:global(.dark) .toolbar-btn { background: #334155; color: #94a3b8; }
	:global(.dark) .toolbar-btn:hover { background: #475569; color: #f1f5f9; }
	.column-dropdown-container { position: relative; }
	.column-dropdown { position: absolute; top: 100%; right: 0; margin-top: 0.25rem; min-width: 200px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); z-index: 50; overflow: hidden; }
	:global(.dark) .column-dropdown { background: #1e293b; border-color: #334155; }
	.dropdown-header { padding: 0.625rem 0.875rem; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #94a3b8; border-bottom: 1px solid #e2e8f0; }
	:global(.dark) .dropdown-header { border-bottom-color: #334155; }
	.dropdown-content { max-height: 240px; overflow-y: auto; }
	.column-option { display: flex; align-items: center; gap: 0.5rem; width: 100%; padding: 0.5rem 0.875rem; background: transparent; color: #475569; font-size: 0.875rem; text-align: left; cursor: pointer; transition: all 0.15s; border-left: 3px solid transparent; }
	.column-option:hover { background: #f8fafc; }
	.column-option.dragging { opacity: 0.5; background: #e2e8f0; cursor: grabbing; }
	.column-option.drag-over { border-left-color: #1a4031; background: #f1f5f9; }
	:global(.dark) .column-option { color: #e2e8f0; }
	:global(.dark) .column-option:hover { background: #334155; }
	:global(.dark) .column-option.dragging { background: #475569; }
	:global(.dark) .column-option.drag-over { border-left-color: #4ade80; background: #1e293b; }
	.col-visibility-icon { display: flex; color: #64748b; flex-shrink: 0; }
	:global(.dark) .col-visibility-icon { color: #94a3b8; }
	.col-name { flex: 1; user-select: none; }
	.col-drag { display: flex; color: #cbd5e1; cursor: grab; padding: 0.25rem; }
	.col-drag:hover { color: #94a3b8; }
	:global(.dark) .col-drag { color: #475569; }
	:global(.dark) .col-drag:hover { color: #94a3b8; }

	/* Mobile/Desktop visibility */
	.desktop-only { display: flex; }
	.mobile-only { display: none; }
	@media (max-width: 768px) {
		.desktop-only { display: none; }
		.mobile-only { display: flex; }
		.column-option { cursor: default; }
	}

	/* Reorder buttons for mobile */
	.col-reorder { display: flex; flex-direction: column; gap: 1px; }
	.reorder-btn { display: flex; align-items: center; justify-content: center; width: 20px; height: 16px; border: none; border-radius: 3px; background: #f1f5f9; color: #64748b; cursor: pointer; transition: all 0.15s; }
	.reorder-btn:hover:not(:disabled) { background: #e2e8f0; color: #0f172a; }
	.reorder-btn:disabled { opacity: 0.3; cursor: not-allowed; }
	:global(.dark) .reorder-btn { background: #334155; color: #94a3b8; }
	:global(.dark) .reorder-btn:hover:not(:disabled) { background: #475569; color: #f1f5f9; }

	.reset-btn { display: flex; align-items: center; justify-content: center; gap: 0.375rem; width: 100%; padding: 0.625rem; border: none; border-top: 1px solid #e2e8f0; background: #f8fafc; color: #64748b; font-size: 0.8125rem; cursor: pointer; transition: all 0.15s; }
	.reset-btn:hover { background: #f1f5f9; color: #0f172a; }
	:global(.dark) .reset-btn { background: #0f172a; border-top-color: #334155; color: #94a3b8; }
	:global(.dark) .reset-btn:hover { background: #1e293b; color: #f1f5f9; }
</style>
