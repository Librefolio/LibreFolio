<!--
  AllocationMatrix — Class × dimension of the WHOLE portfolio (lane 80, F4): one row per class, one column per bucket of the
  dimension chosen above (Area, Sector, Type), each cell the share of the portfolio the backend gave it. It does not move with the
  filters: the framed cells are what the filters keep (the class is on and the column is not taken out of the 100 %), so the user sees
  where the selection sits in the whole.

  - A click on a cell keeps only its class (and a click on that class again goes back to every class); a click on the class's name
    does the same. A column that is a bucket the dimension lets the user take out (Unknown, Other) toggles that exclusion.
  - Tinted with the checked role, in proportion to the heaviest cell: a drawing, not a number. The shares are the backend's,
    percentages: shown whatever the privacy toggle says. The amount is in the tooltip and masked with it.
  - What has no column (the cash in the geography, the securities in transit) is listed under the table with its reason, so the
    table and that line add up to the net worth.
  - Nothing is drawn in the asset dimension (the answer has no matrix there) and when no class is held.

  Test ids: `{testId}` (root), `-class-{CLASS}` (the class's name), `-col-{bucket}` (a column header), `-cell-{CLASS}-{bucket}`
  (`data-selected`, `data-share`), `-unattributed`.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import {ensureCountriesLoaded, getCountryInfo} from '$lib/stores/reference/countryStore';
    import {ensureSectorsLoaded, getSectorEmoji, sectorEmojiVersion} from '$lib/stores/reference/sectorStore';
    import {focusClass, isClassOn, setBucketExcluded, type AllocationFilters, type ExcludableBucket} from './allocationFilters';
    import type {AllocationResponse} from './allocationQuery';
    import {assetNamesOf, matrixModel} from './allocationView';
    import {classHint, classLabel, sliceLabel, type RowLabel, type Translate} from './allocationLabels';
    import {getAssetTypeIconUrl} from '$lib/utils/assetTypes';

    interface Props {
        view: AllocationResponse;
        filters: AllocationFilters;
        onchange: (next: AllocationFilters) => void;
        testId: string;
    }

    let {view, filters, onchange, testId}: Props = $props();

    $effect(() => {
        void ensureCountriesLoaded();
        void ensureSectorsLoaded();
    });
    const sectorVersion = $derived(sectorEmojiVersion());

    const t = (key: string, options?: Parameters<Translate>[1]) => $_(key, options as never);
    const model = $derived(matrixModel(view, (assetClass) => isClassOn(filters, assetClass), new Set(filters.excludeBuckets)));
    const excludable = $derived(new Set<string>(view.applicable_buckets));
    const names = $derived(assetNamesOf(view));

    function columnLabel(key: string): RowLabel {
        void sectorVersion;
        return sliceLabel({t, assetNames: names, country: getCountryInfo, sectorEmoji: getSectorEmoji}, view.dimension, key);
    }

    const share = (value: string | null): string => (value == null ? '—' : formatPercent(parseFloat(value), {digits: 1, signed: false}));

    /** The tint of a cell: the checked role, from nothing to about a third of it (the text keeps its contrast on it). */
    const tint = (intensity: number): string => (intensity > 0 ? `background-color: color-mix(in srgb, var(--lf-checked) ${Math.round(intensity * 32)}%, transparent)` : '');
</script>

{#if model && model.rows.length > 0 && model.columns.length > 0}
    <section class="rounded-xl border border-lf-subtle bg-lf-card p-4 shadow-sm shadow-lf-shadow-card" data-testid={testId} data-dimension={view.dimension}>
        <h3 class="text-sm font-semibold text-lf-primary">{$_('allocation.matrix.title', {values: {dimension: $_(`allocation.dimension.${view.dimension}`)}})}</h3>
        <p class="mt-0.5 text-xs text-lf-muted">{$_('allocation.matrix.hint')}</p>

        <div class="mt-3 overflow-x-auto">
            <table class="w-full border-separate border-spacing-1 text-xs">
                <thead>
                    <tr>
                        <th class="sticky left-0 bg-lf-card px-1 text-left font-medium text-lf-muted" scope="col">{$_('allocation.matrix.classHeader')}</th>
                        {#each model.columns as key (key)}
                            {@const label = columnLabel(key)}
                            {@const canExclude = excludable.has(key)}
                            <th class="px-0.5 font-normal" scope="col" title={label.text}>
                                {#if canExclude}
                                    <button
                                        type="button"
                                        class="w-full rounded px-1 py-0.5 hover:bg-lf-hover"
                                        onclick={() => onchange(setBucketExcluded(filters, key as ExcludableBucket, !filters.excludeBuckets.includes(key as ExcludableBucket)))}
                                        aria-label={label.text}
                                        data-testid="{testId}-col-{key}"
                                        data-excluded={filters.excludeBuckets.includes(key as ExcludableBucket) ? 'true' : 'false'}
                                    >
                                        {@render header(label)}
                                    </button>
                                {:else}
                                    <span class="block px-1 py-0.5" data-testid="{testId}-col-{key}" aria-label={label.text}>{@render header(label)}</span>
                                {/if}
                            </th>
                        {/each}
                    </tr>
                </thead>
                <tbody>
                    {#each model.rows as assetClass, rowIndex (assetClass)}
                        {@const hint = classHint(t, assetClass)}
                        <tr>
                            <th class="sticky left-0 bg-lf-card px-1 text-left font-medium text-lf-secondary" scope="row">
                                <button
                                    type="button"
                                    class="flex items-center gap-1.5 whitespace-nowrap rounded px-1 py-0.5 hover:bg-lf-hover"
                                    onclick={() => onchange(focusClass(filters, assetClass))}
                                    title={hint ? `${classLabel(t, assetClass)} (${hint})` : classLabel(t, assetClass)}
                                    data-testid="{testId}-class-{assetClass}"
                                >
                                    <img src={getAssetTypeIconUrl(assetClass)} alt="" class="h-4 w-4 shrink-0 object-contain" />
                                    {classLabel(t, assetClass)}
                                </button>
                            </th>
                            {#each model.cells[rowIndex] as cell (cell.key)}
                                {@const cellName = columnLabel(cell.key).text}
                                <td class="p-0">
                                    <button
                                        type="button"
                                        class="block w-full min-w-10 rounded px-1 py-1.5 text-center tabular-nums hover:brightness-95 {cell.present ? 'text-lf-primary' : 'text-lf-muted'} {cell.selected ? 'outline outline-2 -outline-offset-1 outline-lf-checked' : ''}"
                                        style={tint(cell.intensity)}
                                        onclick={() => onchange(focusClass(filters, cell.assetClass))}
                                        aria-label={cell.present
                                            ? $_('allocation.matrix.cell', {values: {class: classLabel(t, cell.assetClass), bucket: cellName, share: share(cell.shareOfPortfolio)}})
                                            : $_('allocation.matrix.cellEmpty', {values: {class: classLabel(t, cell.assetClass), bucket: cellName}})}
                                        title={cell.present ? formatCurrencyAmountPlain(cell.amount, view.currency, {sensitivity: 'personal'}) : undefined}
                                        data-testid="{testId}-cell-{cell.assetClass}-{cell.key}"
                                        data-selected={cell.selected ? 'true' : 'false'}
                                        data-share={cell.shareOfPortfolio ?? ''}
                                    >
                                        {cell.present ? share(cell.shareOfPortfolio) : '·'}
                                    </button>
                                </td>
                            {/each}
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        {#if model.unattributed.some((row) => row.amount !== 0)}
            <p class="mt-2 text-xs text-lf-muted" data-testid="{testId}-unattributed">
                {$_('allocation.matrix.unattributed')}
                {#each model.unattributed.filter((row) => row.amount !== 0) as row, index (row.reason)}{#if index > 0};
                    {/if}{$_(`allocation.unattributable.${row.reason}`)}
                    {formatCurrencyAmountPlain(row.amount, view.currency, {sensitivity: 'personal'})}{/each}
            </p>
        {/if}
    </section>
{/if}

{#snippet header(label: RowLabel)}
    {#if label.iconUrl}
        <img src={label.iconUrl} alt="" class="mx-auto h-4 w-4 object-contain" />
    {:else if label.glyph}
        <span class="emoji-flag text-sm leading-none" aria-hidden="true">{label.glyph}</span>
    {:else}
        <span class="block max-w-24 truncate">{label.text}</span>
    {/if}
{/snippet}
