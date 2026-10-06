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
  - The root publishes `data-benchmark-id`, `data-benchmark-state`, `data-measured` and
    `data-eligibility`, so a page and its tests read the state, not an icon or a label.

  ELIGIBILITY (D378: the same on every page). It draws F's asset picker panel, which keeps the
  assets the engine says cannot be measured over the period in a read-only section of their
  own, with the engine's reasons. The verdicts come either from the page (`verdicts`, the lab's
  own answer for its catalogue) or from the page's period (`period` + `currency`), which the
  picker asks the engine about itself: once per question for the session (`queryEligibility`),
  after a short pause, an answer to an outdated question being ignored. With neither there are
  no verdicts and every asset is selectable, as before. A failed question locks nothing.

  A stored choice the engine says cannot be measured is not tried (D378, developer: «Non lo
  prova: la riga del benchmark sparisce, e il motivo lo dice solo il selettore»): the picker
  publishes `blocked`, keeps the choice stored and in the trigger, and every page asks its
  comparison on `set` only. With a period, a choice waits as `pending` until its verdict is
  known, so no page asks a comparison it would then have to drop.
-->
<script lang="ts">
    import {onMount} from 'svelte';
    import {AlertTriangle} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import AssetPickerPanel from '$lib/components/ui/select/AssetPickerPanel.svelte';
    import {assetSelectOrder, type PickerVerdict} from '$lib/components/ui/select/assetPicker';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {assetStoreVersion, ensureAssetsLoaded, getAllAssets, type AssetInfo} from '$lib/stores/reference/assetStore';
    import {queryEligibility} from '$lib/stores/risk/riskStore.svelte';
    import {resolveRiskBenchmark, riskBenchmark, type RiskBenchmarkState} from '$lib/stores/risk/riskBenchmarkStore.svelte';
    import {EMPTY_VERDICTS, dayFormatter, describeEligibility, type EligibilityVerdicts} from './eligibility';

    interface Props {
        /** What this page measures: left out of the list, except the current choice. */
        measuredAssetIds?: number[];
        /** The current choice, resolved. Written by the picker; a parent binds it to read it. */
        value?: number | null;
        /** How far the picker got: `pending` while a choice is being confirmed, `blocked` when it cannot be measured here. */
        state?: RiskBenchmarkState;
        testid?: string;
        placeholder?: string;
        /** The page's own, already-translated wording for the ⚠, replacing the generic sentence. */
        measuredHint?: string;
        /** Classes of the box around the select, for the page's own width. */
        boxClass?: string;
        onchange?: (next: number | null) => void;
        /** The page's own verdicts, already worded: used as they are, and nothing is asked. */
        verdicts?: ReadonlyMap<number, PickerVerdict>;
        /** The page's period: with `currency`, the picker asks the engine itself. Ignored when `verdicts` is given. */
        period?: {start: string; end: string};
        currency?: string;
    }

    let {measuredAssetIds = [], value = $bindable(null), state: benchmarkState = $bindable('none'), testid = 'risk-benchmark-select', placeholder, measuredHint, boxClass = 'w-64', onchange, verdicts: givenVerdicts, period, currency}: Props = $props();

    const ELIGIBILITY_DEBOUNCE_MS = 300;

    const initialState: RiskBenchmarkState = riskBenchmark.assetId === null ? 'none' : 'pending';
    /** Where the choice itself stands, before its verdict: the store's resolution, or the reader's choice. */
    let baseState = $state<RiskBenchmarkState>(initialState);
    // Synchronous on purpose: the first thing a page reads must already say whether there
    // is a stored choice to wait for. `onMount` would leave a frame that says `none`.
    benchmarkState = initialState;

    /** Set once the reader chooses: from then on the mount-time check has nothing to say. */
    let readerChose = false;
    let loading = $state(true);
    let loadFailed = $state(false);

    let measured = $derived(new Set(measuredAssetIds));
    let measuredChoice = $derived(value !== null && measured.has(value));
    let hint = $derived(measuredHint ?? $t('risk.benchmark.measuredHere'));

    /** The current choice stays on offer even when the page measures it: what is chosen must show. */
    function offered(asset: AssetInfo): boolean {
        return !measured.has(asset.id) || asset.id === value;
    }

    let catalogue = $derived.by(() => {
        void $assetStoreVersion;
        return assetSelectOrder(getAllAssets().filter(offered));
    });
    let catalogueIds = $derived(catalogue.map((asset) => asset.id).sort((left, right) => left - right));

    /** The picker asks the engine itself only when the page gave a period and no verdicts of its own. */
    let asksItself = $derived(givenVerdicts === undefined && Boolean(period) && Boolean(currency));
    /** The question, once the catalogue it is about has loaded. */
    let question = $derived(asksItself && period && currency && !loading ? {key: `${period.start}|${period.end}|${currency}|${catalogueIds.join(',')}`, ids: catalogueIds, period, currency} : null);
    let answer = $state<{key: string; verdicts: EligibilityVerdicts; failed: boolean} | null>(null);
    /** Bumped to ask again when the cache was emptied while the question was in flight. */
    let retry = $state(0);

    $effect(() => {
        const asked = question;
        void retry;
        if (asked === null) return;
        const timer = setTimeout(() => {
            queryEligibility(asked.ids, asked.period, asked.currency).then(
                (verdicts) => {
                    // An answer to a question the page no longer asks is not this page's answer.
                    if (question?.key !== asked.key) return;
                    // `null`: the cache was emptied while it was asked (a sync, a session change). Not an answer: ask again.
                    if (verdicts === null) retry += 1;
                    else answer = {key: asked.key, verdicts, failed: false};
                },
                (error) => {
                    if (question?.key !== asked.key) return;
                    console.error('[Risk] Benchmark eligibility unavailable:', error);
                    answer = {key: asked.key, verdicts: EMPTY_VERDICTS, failed: true};
                },
            );
        }, ELIGIBILITY_DEBOUNCE_MS);
        return () => clearTimeout(timer);
    });

    let eligibility = $derived.by((): 'none' | 'given' | 'pending' | 'ready' | 'failed' => {
        if (givenVerdicts !== undefined) return 'given';
        if (!asksItself) return 'none';
        // Waiting covers the catalogue's own load: a choice must never read `set` on its way to `blocked`.
        if (question === null || answer?.key !== question.key) return 'pending';
        return answer.failed ? 'failed' : 'ready';
    });

    let askedView = $derived.by((): ReadonlyMap<number, PickerVerdict> | undefined => {
        const known = question !== null && answer?.key === question.key && !answer.failed ? answer.verdicts : null;
        if (!known || !currency) return undefined;
        const formatDay = dayFormatter($currentLanguage);
        const view = new Map<number, PickerVerdict>();
        for (const [assetId, item] of known.items) view.set(assetId, describeEligibility(item, known, currency, $t, formatDay));
        return view;
    });
    let panelVerdicts = $derived(givenVerdicts ?? askedView);

    /** What a page reads: a confirmed choice waits for its verdict when the picker asks, and is `blocked` when it cannot be measured. */
    function published(base: RiskBenchmarkState, choice: number | null): RiskBenchmarkState {
        if (base !== 'set' || choice === null) return base;
        if (eligibility === 'pending') return 'pending';
        return panelVerdicts?.get(choice)?.level === 'ineligible' ? 'blocked' : 'set';
    }

    $effect(() => {
        benchmarkState = published(baseState, value);
    });

    onMount(() => {
        let mounted = true;
        void resolveRiskBenchmark().then((resolution) => {
            if (!mounted || readerChose) return;
            // `value` before `state`: a page that waits on the state finds the value in place.
            value = resolution.assetId;
            baseState = resolution.state;
            benchmarkState = published(baseState, value);
        });
        ensureAssetsLoaded().then(
            () => {
                if (mounted) loading = false;
            },
            () => {
                if (!mounted) return;
                loading = false;
                loadFailed = true;
            },
        );
        return () => {
            mounted = false;
        };
    });

    function choose(next: number | null): void {
        readerChose = true;
        riskBenchmark.set(next);
        baseState = next === null ? 'none' : 'set';
        benchmarkState = published(baseState, next);
        value = next;
        onchange?.(next);
    }
</script>

<div class="flex items-center gap-1.5" data-testid="{testid}-control" data-benchmark-id={value ?? ''} data-benchmark-state={benchmarkState} data-measured={measuredChoice ? 'true' : 'false'} data-eligibility={eligibility}>
    <div class={boxClass}>
        <AssetPickerPanel
            mode="single"
            assets={catalogue}
            verdicts={panelVerdicts}
            blockedLabel={$t('risk.benchmark.blocked')}
            {value}
            sections={[{key: 'benchmark', label: $t('assets.benchmarkSection'), match: (asset) => asset.is_benchmark === true}]}
            restLabel={$t('assets.otherAssetsSection')}
            dropdownPosition="auto"
            dropdownMinWidth={280}
            placeholder={placeholder ?? $t('risk.comparison.comparisonAsset')}
            {loading}
            testId={testid}
            onchange={choose}
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
