<!--
  PortfolioAllocationTab — the «Allocazione» tab of the portfolio view (lane 80, issue #89, F2: the skeleton).

  Where am I exposed, looking at only a part? The user keeps some classes, takes buckets or assets out of the 100 %, and the
  backend (`POST /portfolio/allocation`) answers with the base, what the filter leaves out and what is excluded. This file
  holds the page-level pieces: the question, the three boxes, the filters (a column on a wide screen, behind the «Filters»
  button below `lg`, with the choices as chips) and the states (loading, failed, empty). The results (the dimension, the chart or
  the map, the table, the history and the class × dimension matrix) are `AllocationResults`, beside the filters.

  The question is the page's own scope (its brokers, `historyStart`, `end`, currency, `fullShare`: the report's), so the
  backend reads the report's engine run and a filter replays nothing. The tab asks nothing while the page cannot
  (`scope` null: the owned brokers are not known yet).

  Filters are remembered per page (`allocation-filters:dashboard`, `allocation-filters:broker:<id>`).

  Published state: `data-busy` (`true|false`) and `aria-busy` on the root, which carries `testId`.
-->
<script lang="ts">
    import {onDestroy, untrack} from 'svelte';
    import {Filter} from 'lucide-svelte';
    import {_} from '$lib/i18n';
    import {pageBusy} from '$lib/stores/app/pageBusy.svelte';
    import FilterButton from '$lib/components/ui/select/FilterButton.svelte';
    import SelectPopover from '$lib/components/ui/select/SelectPopover.svelte';
    import {createAllocationController} from '$lib/features/allocation/allocationController.svelte';
    import {allocationAskKey, type AllocationAsk} from '$lib/features/allocation/allocationQuery';
    import {filterChips, filtersStorageKey} from '$lib/features/allocation/allocationFilters';
    import {chipText, type Translate} from '$lib/features/allocation/allocationLabels';
    import {createMediaQuery} from '$lib/features/allocation/matchMedia.svelte';
    import AllocationBaseTiles from '$lib/features/allocation/AllocationBaseTiles.svelte';
    import AllocationFilterPanel from '$lib/features/allocation/AllocationFilterPanel.svelte';
    import AllocationChips from '$lib/features/allocation/AllocationChips.svelte';
    import AllocationResults from '$lib/features/allocation/AllocationResults.svelte';
    import type {PortfolioScope} from './portfolioDataScope';

    interface Props {
        testId: string;
        /** Which page this is: its filters are remembered under their own key. */
        page: {kind: 'portfolio'} | {kind: 'broker'; brokerId: number};
        /** The report's scope, or `null` while the page cannot ask yet (the owned brokers are not known). */
        scope: PortfolioScope | null;
        /** Bumped by «Aggiorna» and by a price catch-up: the tab asks again. */
        refreshVersion: number;
        /** The `pageBusy` key of this tab's request (the page's Refresh button waits for it). */
        busyKey: string;
        /** What the subtitle says about the brokers. */
        brokers: {kind: 'all'} | {kind: 'some'; n: number} | {kind: 'this'};
    }

    let {testId, page, scope, refreshVersion, busyKey, brokers}: Props = $props();

    // One controller for the life of the tab: the page does not change under it (a broker's page is mounted per broker).
    const controller = createAllocationController(untrack(() => filtersStorageKey(page)));
    onDestroy(() => controller.dispose());

    /** A popover below `lg`, a column from `lg` up: the filter panel is mounted once, so its test ids exist once. */
    const wide = createMediaQuery('(min-width: 1024px)');

    let lastKey = '';
    let lastAsk: AllocationAsk | null = null;

    $effect(() => {
        const current = scope;
        const version = refreshVersion;
        const ask: AllocationAsk | null = current ? {scope: current, dimension: controller.dimension, filters: controller.filters, includeHistory: controller.mode === 'history'} : null;
        if (!ask) return;
        const key = `${allocationAskKey(ask)}|v${version}`;
        untrack(() => {
            if (key === lastKey) return;
            lastKey = key;
            lastAsk = ask;
            // On the trigger, as `pageBusy` asks: a change of scope, period, filter or Refresh is a big request.
            void pageBusy.track(busyKey, () => controller.load(ask));
        });
    });

    function retry(): void {
        const ask = lastAsk;
        if (ask) void pageBusy.track(busyKey, () => controller.load(ask));
    }

    const view = $derived(controller.response);
    const t = (key: string, options?: Parameters<Translate>[1]) => $_(key, options as never);
    const assetNames = $derived(new Map((view?.assets ?? []).map((asset) => [asset.asset_id, asset.name])));
    const chipCount = $derived(filterChips(controller.filters).length);
    const nothingHeld = $derived(view !== null && view.classes.length === 0 && view.assets.length === 0);

    /** «Stocks · without Unclassified · all brokers»: the selection, then the brokers. */
    const subtitle = $derived.by(() => {
        const chips = filterChips(controller.filters);
        const selection = chips.length === 0 ? [$_('allocation.subtitle.all')] : chips.map((chip) => chipText(t, chip, assetNames));
        const where = brokers.kind === 'all' ? $_('allocation.subtitle.scopeAll') : brokers.kind === 'some' ? $_('allocation.subtitle.scopeBrokers', {values: {n: brokers.n}}) : $_('allocation.subtitle.scopeBroker');
        return [...selection, where].join(' · ');
    });
</script>

<div class="space-y-4" data-testid={testId} data-busy={controller.loading ? 'true' : 'false'} aria-busy={controller.loading ? 'true' : 'false'}>
    <header>
        <h2 class="text-lg font-semibold text-lf-primary">{$_('allocation.heading')}</h2>
        <p class="text-sm text-lf-secondary" data-testid="{testId}-subtitle">{subtitle}</p>
    </header>

    {#if view === null}
        {#if controller.failed}
            <div class="rounded-xl border border-lf-subtle bg-lf-card p-6 text-center" data-testid="{testId}-failed">
                <p class="text-sm text-lf-danger">{$_('allocation.failed')}</p>
                <button type="button" class="mt-3 rounded-lg border border-lf-subtle px-3 py-1.5 text-sm text-lf-secondary hover:bg-lf-hover" onclick={retry} data-testid="{testId}-retry">{$_('allocation.retry')}</button>
            </div>
        {:else}
            <div class="rounded-xl border border-lf-subtle bg-lf-card p-6 text-center text-sm text-lf-muted" data-testid="{testId}-loading">{$_('allocation.loading')}</div>
        {/if}
    {:else if nothingHeld}
        <div class="rounded-xl border border-lf-subtle bg-lf-card p-6 text-center text-sm italic text-lf-muted" data-testid="{testId}-empty">{$_('allocation.empty')}</div>
    {:else}
        {#if controller.failed}
            <div class="flex items-center justify-between gap-3 rounded-lg border border-lf-danger-line bg-lf-danger-soft px-3 py-2 text-sm text-lf-danger-on-soft" role="alert" data-testid="{testId}-failed">
                <span>{$_('allocation.failed')}</span>
                <button type="button" class="underline hover:no-underline" onclick={retry} data-testid="{testId}-retry">{$_('allocation.retry')}</button>
            </div>
        {/if}

        <AllocationBaseTiles {view} testId="{testId}-tiles" />

        <div class="grid gap-4 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]">
            {#if wide.matches}
                <aside class="self-start lg:sticky lg:top-4" data-testid="{testId}-filters-column">
                    <AllocationFilterPanel {view} filters={controller.filters} onchange={(next) => controller.setFilters(next)} testId="{testId}-filters" />
                </aside>
            {/if}

            <div class="min-w-0 space-y-3">
                {#if !wide.matches}
                    <div class="flex flex-wrap items-center gap-2">
                        <SelectPopover testId="{testId}-filters-popover" panelClass="w-[min(92vw,24rem)]" rootClass="relative inline-flex">
                            {#snippet trigger({open, toggle})}
                                <FilterButton label={$_('allocation.filters.button')} icon={Filter} count={chipCount} expanded={open} onclick={toggle} testId="{testId}-filters-button" />
                            {/snippet}
                            {#snippet children()}
                                <div class="max-h-[70vh] overflow-y-auto p-2">
                                    <AllocationFilterPanel {view} filters={controller.filters} onchange={(next) => controller.setFilters(next)} testId="{testId}-filters" />
                                </div>
                            {/snippet}
                        </SelectPopover>
                    </div>
                    <AllocationChips filters={controller.filters} {view} onchange={(next) => controller.setFilters(next)} testId="{testId}-chips" />
                {/if}
                <AllocationResults
                    {view}
                    dimension={controller.dimension}
                    onDimension={(next) => controller.setDimension(next)}
                    mode={controller.mode}
                    onMode={(next) => controller.setMode(next)}
                    loading={controller.loading}
                    filters={controller.filters}
                    onFilters={(next) => controller.setFilters(next)}
                    testId="{testId}-results"
                />
            </div>
        </div>
    {/if}
</div>
