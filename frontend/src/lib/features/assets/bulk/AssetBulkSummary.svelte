<!--
  AssetBulkSummary — step 2 «Summary» of the bulk edit: what changes, before → after (lane 65, mockup-AB-v5, section 6).

  Three numbers (the assets that change, and per touched field how many change and to what), then a table, one row per
  changing asset with a cell per touched field: «before → after», or «already …» where the asset has the value. On a
  phone the table becomes one card per asset. A row with an open warning is amber, a blocked one red.
  Published state: `data-state` (`ok`, `warning`, `blocked`) and `data-asset-id` on each row/card, `data-unchanged` on a
  cell. Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {assetTypeBadgeClass, getAssetTypeIconUrl} from '$lib/utils/assetTypes';
    import {FIELD_LABEL_KEYS, type BulkFieldKey, type BulkValue, type ChangeSummary, type SummaryCell} from './assetBulkEdit';

    interface Props {
        summary: ChangeSummary;
        /** Assets with a warning still open: their row is amber. */
        warnedIds?: number[];
        /** Assets with a block: their row is red. */
        blockedIds?: number[];
    }

    let {summary, warnedIds = [], blockedIds = []}: Props = $props();

    function rowState(id: number): 'ok' | 'warning' | 'blocked' {
        return blockedIds.includes(id) ? 'blocked' : warnedIds.includes(id) ? 'warning' : 'ok';
    }

    function fileName(url: string): string {
        return decodeURIComponent(url.split(/[?#]/)[0].split('/').pop() ?? '') || url;
    }

    function flagLabel(value: boolean): string {
        return value ? $t('assets.bulkEdit.yes') : $t('assets.bulkEdit.no');
    }

    /** A plain value as text; the types are drawn as badges by the snippet. */
    function valueText(field: BulkFieldKey, value: BulkValue): string {
        if (typeof value === 'boolean') return flagLabel(value);
        if (field === 'icon_url') return value === null ? $t('assets.bulkEdit.iconNone') : fileName(String(value));
        if (value === null) return '—';
        return String(value);
    }
</script>

{#snippet valueView(field: BulkFieldKey, value: BulkValue)}
    {#if field === 'asset_type' && typeof value === 'string'}
        <span class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium {assetTypeBadgeClass(value)}" data-testid="asset-bulk-summary-type" data-asset-type={value}>
            <img src={getAssetTypeIconUrl(value)} alt="" class="h-3.5 w-3.5 object-contain" />
            {$t(`assets.types.${value}`)}
        </span>
    {:else}
        <span class="break-all text-lf-primary">{valueText(field, value)}</span>
    {/if}
{/snippet}

{#snippet cellView(cell: SummaryCell)}
    {#if cell.unchanged}
        <span class="inline-flex flex-wrap items-center gap-1 text-lf-muted" data-testid="asset-bulk-summary-cell" data-field={cell.field} data-unchanged="true">
            {$t('assets.bulkEdit.already')}
            {@render valueView(cell.field, cell.after)}
        </span>
    {:else}
        <span class="inline-flex flex-wrap items-center gap-1" data-testid="asset-bulk-summary-cell" data-field={cell.field} data-unchanged="false">
            <span class="text-lf-muted">{@render valueView(cell.field, cell.before)}</span>
            <span aria-hidden="true" class="text-lf-muted">→</span>
            {@render valueView(cell.field, cell.after)}
        </span>
    {/if}
{/snippet}

<div class="space-y-4" data-testid="asset-bulk-summary" data-changing={summary.changing} data-selected={summary.selected}>
    <!-- The numbers -->
    <div class="flex flex-wrap gap-3">
        <div class="rounded-xl border border-lf-subtle bg-lf-card px-4 py-3" data-testid="asset-bulk-summary-assets">
            <p class="text-[11px] font-semibold uppercase tracking-wider text-lf-muted">{$t('assets.bulkEdit.summaryAssets')}</p>
            <p class="text-2xl font-semibold text-lf-primary">{summary.changing}</p>
            <p class="text-xs text-lf-muted">{$t('assets.bulkEdit.summaryOf', {values: {changing: summary.changing, selected: summary.selected}})}</p>
        </div>
        {#each summary.fields as impact (impact.field)}
            <div class="rounded-xl border border-lf-subtle bg-lf-card px-4 py-3" data-testid="asset-bulk-summary-field-{impact.field}" data-changing={impact.changing}>
                <p class="text-[11px] font-semibold uppercase tracking-wider text-lf-muted">{$t(FIELD_LABEL_KEYS[impact.field])}</p>
                <p class="text-2xl font-semibold text-lf-primary">{impact.changing}</p>
                <p class="flex flex-wrap items-center gap-1 text-xs text-lf-muted"><span aria-hidden="true">→</span> {@render valueView(impact.field, impact.after)}</p>
            </div>
        {/each}
    </div>

    <!-- Table (from `sm`) -->
    <div class="hidden overflow-x-auto rounded-xl border border-lf-subtle sm:block">
        <table class="w-full text-left text-sm" data-testid="asset-bulk-summary-table">
            <thead class="bg-lf-panel text-xs text-lf-secondary">
                <tr>
                    <th class="px-3 py-2 font-medium">{$t('assets.bulkEdit.summaryAsset')}</th>
                    {#each summary.touched as field (field)}
                        <th class="px-3 py-2 font-medium">{$t(FIELD_LABEL_KEYS[field])}</th>
                    {/each}
                </tr>
            </thead>
            <tbody>
                {#each summary.rows as row (row.id)}
                    {@const state = rowState(row.id)}
                    <tr class="border-t border-lf-subtle {state === 'blocked' ? 'bg-lf-danger-soft' : state === 'warning' ? 'bg-lf-warning-soft' : ''}" data-testid="asset-bulk-summary-row" data-asset-id={row.id} data-state={state}>
                        <td class="px-3 py-2 font-medium text-lf-primary">
                            {#if state === 'warning'}<span aria-hidden="true">⚠️ </span>{:else if state === 'blocked'}<span aria-hidden="true">⛔ </span>{/if}{row.name}
                        </td>
                        {#each row.cells as cell (cell.field)}
                            <td class="px-3 py-2 align-top">{@render cellView(cell)}</td>
                        {/each}
                    </tr>
                {/each}
            </tbody>
        </table>
    </div>

    <!-- Cards (phone): one per asset -->
    <div class="space-y-2 sm:hidden" data-testid="asset-bulk-summary-cards">
        {#each summary.rows as row (row.id)}
            {@const state = rowState(row.id)}
            <div class="rounded-xl border p-3 {state === 'blocked' ? 'border-lf-danger-line bg-lf-danger-soft' : state === 'warning' ? 'border-lf-warning-line bg-lf-warning-soft' : 'border-lf-subtle bg-lf-card'}" data-testid="asset-bulk-summary-card" data-asset-id={row.id} data-state={state}>
                <p class="mb-1 text-sm font-medium text-lf-primary">{row.name}</p>
                <dl class="space-y-1 text-sm">
                    {#each row.cells as cell (cell.field)}
                        <div class="flex items-start justify-between gap-3">
                            <dt class="text-xs text-lf-muted">{$t(FIELD_LABEL_KEYS[cell.field])}</dt>
                            <dd class="text-right">{@render cellView(cell)}</dd>
                        </div>
                    {/each}
                </dl>
            </div>
        {/each}
    </div>

    <p class="text-xs text-lf-muted" data-testid="asset-bulk-summary-note">{$t('assets.bulkEdit.summaryNote')}</p>
</div>
