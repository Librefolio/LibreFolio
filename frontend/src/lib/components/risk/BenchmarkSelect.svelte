<!--
  BenchmarkSelect.svelte — the one benchmark picker every Risk surface mounts.

  Developer decision, 01/10/2026: wherever a page measures against a benchmark there is a
  picker, it opens on the current benchmark, and it is empty only when nothing is set. The
  Dashboard and Broker L3, the Asset Global lab and the asset page's Risk tab all mount this
  component, so the rule cannot drift apart page by page — which is how the old defect was
  born: each page filtered its own list, and a benchmark one page allowed vanished from
  another page's picker while that page still compared against it.

  - It opens on `resolveRiskBenchmark()`: the stored choice once the asset list confirms it.
    An id the list does not hold reads as `unknown` — placeholder, `value` null — and stays
    stored (see the store for why it is never cleared).
  - Only what the page measures leaves the list (`measuredAssetIds`), never the current
    choice: a choice that is also measured stays shown, with a ⚠ saying it cannot serve here.
  - Choosing writes the shared store first, then `state` and `value`, then `onchange`, so a
    page that reacts to the change already reads the same choice everywhere.
  - The root publishes `data-benchmark-id`, `data-benchmark-state` and `data-measured`, so a
    page and its tests read the state, not an icon or a label.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {AlertTriangle} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import AssetSelect from '$lib/components/ui/select/AssetSelect.svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import type {AssetInfo} from '$lib/stores/reference/assetStore';
    import {resolveRiskBenchmark, riskBenchmark, type RiskBenchmarkState} from '$lib/stores/risk/riskBenchmarkStore.svelte';

    interface Props {
        /** What this page measures: left out of the list, except the current choice. */
        measuredAssetIds?: number[];
        /** The current choice, resolved. Written by the picker; a parent binds it to read it. */
        value?: number | null;
        /** How far the picker got: `pending` while a stored id is being confirmed. */
        state?: RiskBenchmarkState;
        testid?: string;
        placeholder?: string;
        /** The page's own, already-translated wording for the ⚠, replacing the generic sentence. */
        measuredHint?: string;
        /** Classes of the box around the select, for the page's own width. */
        boxClass?: string;
        onchange?: (next: number | null) => void;
    }

    let {measuredAssetIds = [], value = $bindable(null), state: benchmarkState = $bindable('none'), testid = 'risk-benchmark-select', placeholder, measuredHint, boxClass = 'w-64', onchange}: Props = $props();

    // Synchronous on purpose: the first thing a page reads must already say whether there
    // is a stored choice to wait for. `onMount` would leave a frame that says `none`.
    benchmarkState = riskBenchmark.assetId === null ? 'none' : 'pending';

    /** Set once the reader chooses: from then on the mount-time check has nothing to say. */
    let readerChose = false;
    let loadFailed = $state(false);

    let measured = $derived(new Set(measuredAssetIds));
    let measuredChoice = $derived(value !== null && measured.has(value));
    let hint = $derived(measuredHint ?? $t('risk.benchmark.measuredHere'));

    onMount(() => {
        let mounted = true;
        void resolveRiskBenchmark().then((answer) => {
            if (!mounted || readerChose) return;
            // `value` before `state`: a page that waits on the state finds the value in place.
            value = answer.assetId;
            benchmarkState = answer.state;
        });
        return () => {
            mounted = false;
        };
    });

    /** The current choice stays on offer even when the page measures it: what is chosen must show. */
    function offered(asset: AssetInfo): boolean {
        return !measured.has(asset.id) || asset.id === value;
    }

    function choose(next: number | null): void {
        readerChose = true;
        riskBenchmark.set(next);
        benchmarkState = next === null ? 'none' : 'set';
        value = next;
        onchange?.(next);
    }
</script>

<div class="flex items-center gap-1.5" data-testid="{testid}-control" data-benchmark-id={value ?? ''} data-benchmark-state={benchmarkState} data-measured={measuredChoice ? 'true' : 'false'}>
    <div class={boxClass}>
        <AssetSelect
            {value}
            filter={offered}
            sections={[{key: 'benchmark', label: $t('assets.benchmarkSection'), match: (asset) => asset.is_benchmark === true}]}
            restLabel={$t('assets.otherAssetsSection')}
            compact
            dropdownPosition="auto"
            dropdownMinWidth={280}
            placeholder={placeholder ?? $t('risk.comparison.comparisonAsset')}
            {testid}
            onchange={choose}
            onLoadError={() => (loadFailed = true)}
        />
        {#if loadFailed}
            <p class="mt-1 text-[10px] text-red-500" data-testid="{testid}-load-error">{$t('signals.comparisonAsset.loadError')}</p>
        {/if}
    </div>
    {#if measuredChoice}
        <!-- `interactiveChild`: the ⚠ owns its semantics (an image a keyboard can reach), so the
             Tooltip wrapper adds no button role around it. -->
        <Tooltip text={hint} position="bottom" maxWidth="320px" interactiveChild={true}>
            <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
            <span class="inline-flex text-amber-600 dark:text-amber-400" data-testid="{testid}-measured" role="img" tabindex="0" aria-label={hint}>
                <AlertTriangle size={14} aria-hidden="true" />
            </span>
        </Tooltip>
    {/if}
</div>
