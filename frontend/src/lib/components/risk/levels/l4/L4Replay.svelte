<script lang="ts">
    import {Play, RotateCcw} from 'lucide-svelte';

    import {schemas} from '$lib/api';
    import {_ as t} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import DateRangePicker from '$lib/components/ui/date/DateRangePicker.svelte';
    import SimpleSelect from '$lib/components/ui/select/SimpleSelect.svelte';
    import {riskMetadata, riskOutput, singleValue} from '$lib/risk/riskTypes';
    import {buildHistoricalReplayParameters} from '$lib/risk/riskRequest';
    import type {RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';

    import {formatCurrencyAmount} from '../../riskAnalysisHelpers';
    import {warningSentence} from '../warningSentence';
    import TornadoChart from './TornadoChart.svelte';
    import {formatReplayDate, formatReplayShare, replayCoverageWarning, replayExclusions, replayNothingLeft, replayOptions, replaySuggestion, tornadoRows, type ReplayExclusionGroup, type ReplayExclusions, type TornadoRow} from './scenarioHelpers';

    /**
     * L4 rung 1 — historical replay: real returns, from a real period.
     *
     * The closest rung to observed data, and the only one of the three that is
     * not an opinion: it takes today's composition through what actually
     * happened. That is still a *backtest* and not a record — the composition is
     * today's, not the one held at the time.
     *
     * **What it says about the assets it could not replay** (D372, 02/10/2026).
     * The engine leaves out, on its own, every asset whose prices do not cover
     * the period, and this block says so beside the number: the strong warning
     * above the total when most of the portfolio is out, then the excluded
     * assets grouped by reason, with their weight on a portfolio. When the
     * period's edges are what excluded them, the backend proposes the part of
     * the period in which they all have prices, and one click replays it. The
     * section around the block keeps only the status line: its mounts hand it
     * `replaySectionView`, so nothing is read twice.
     *
     * There is no manual exclusion and no stand-in here: the developer removed
     * the first and kept the second for later (`TODO_FUTURI.md`).
     */
    interface Props {
        controller: RiskPanelController;
        assetNames: Record<number, string>;
        currency: string;
        dateStart: string;
        dateEnd: string;
        /**
         * Whether this surface may state amounts in money — `undefined` means
         * "decide from the answer".
         *
         * Two separate questions hide here, and conflating them produced two
         * wrong designs in a row. **How it is known**: reading the scope off
         * `metadata` is fail-closed, because a caller cannot forget it; a prop
         * alone is fail-open, so a future mount on `asset_set` that omits it
         * brings the euros back. **What is returned**: `''` makes the amount
         * absent, which is right everywhere, whereas the `—` of
         * `formatScopedCurrencyAmount` is right inside a card and wrong inside a
         * sentence — "would have ended the period at −12.30% —" reads as a
         * number that failed to load, not as one that does not apply.
         *
         * So the default is derived from the payload and the prop is an explicit
         * override. The condition is the one `formatScopedCurrencyAmount`
         * already uses, reused rather than restated, so the guards across the
         * subsystem converge on the same predicate even where the string differs.
         */
        showMoney?: boolean;
    }

    let {controller, assetNames, currency, dateStart, dateEnd, showMoney: showMoneyOverride}: Props = $props();

    let presetId = $state('');
    /**
     * The replay window follows the panel's window until someone overrides it.
     *
     * Seeding plain state from the prop would freeze the initial value: the
     * reader could narrow the analysis period in the header and then run a
     * replay over the *old* period, with the form showing the old dates and no
     * hint that they stopped being the panel's. An override that starts null
     * keeps the two bound while leaving the box editable.
     */
    let startOverride = $state<string | null>(null);
    let endOverride = $state<string | null>(null);
    let start = $derived(startOverride ?? dateStart);
    let end = $derived(endOverride ?? dateEnd);

    let options = $derived(replayOptions(controller.scenarioCatalog, $currentLanguage));
    let result = $derived(controller.replayResult);
    let output = $derived(riskOutput(result, schemas.RiskStressOutput));
    let scopeKind = $derived(singleValue(riskMetadata(result)?.scope) ?? '');
    let showMoney = $derived(showMoneyOverride ?? scopeKind === 'portfolio');
    let rows = $derived(tornadoRows(output));
    let exclusions = $derived(replayExclusions(result));
    let suggestion = $derived(replaySuggestion(result));
    let coverage = $derived(replayCoverageWarning(result));
    let nothingLeft = $derived(replayNothingLeft(result));
    /** The catalogue crisis behind the dates, when one with both ends is chosen. */
    let crisis = $derived.by(() => {
        const option = options.find((candidate) => candidate.value === presetId);
        return option?.start && option.end ? {start: option.start, end: option.end} : null;
    });
    /**
     * The crisis the answer on screen was asked over: set when Run goes out over exactly the
     * crisis's dates. A crisis chosen and then edited by hand is not the question any more, so
     * the note below must not speak of it.
     */
    let askedCrisis = $state<{start: string; end: string} | null>(null);
    /** The proposal lies inside the crisis that was asked and is shorter than it: replaying it covers only part of the crisis. */
    let partOfCrisis = $derived(suggestion !== null && askedCrisis !== null && suggestion.start >= askedCrisis.start && suggestion.end <= askedCrisis.end && (suggestion.start > askedCrisis.start || suggestion.end < askedCrisis.end));

    /** Literal keys, one per reason, so the i18n audit finds them. */
    const REASON_KEYS: Record<string, string> = {
        no_prices_in_window: 'risk.levels.l4.replayReasonNoPrices',
        starts_after_window_start: 'risk.levels.l4.replayReasonStartsLate',
        stale_at_window_start: 'risk.levels.l4.replayReasonStaleAtStart',
        stale_at_window_end: 'risk.levels.l4.replayReasonStaleAtEnd',
        missing_fx: 'risk.levels.l4.replayReasonMissingFx',
        manual_exclusion: 'risk.levels.l4.replayReasonManual',
    };

    $effect(() => {
        controller.registerLauncher('replay', run);
    });

    async function run(): Promise<void> {
        askedCrisis = crisis !== null && start === crisis.start && end === crisis.end ? crisis : null;
        await controller.runGuarded('replay', () => ({
            code: 'stress',
            mode: 'current_composition',
            parameters: buildHistoricalReplayParameters({
                start,
                end,
                missingHistoryPolicy: 'manual_proxy_or_exclude',
                proxyAssets: [],
                excludedAssetIds: [],
            }),
        }));
    }

    function applyPreset(id: string): void {
        presetId = id;
        const option = options.find((candidate) => candidate.value === id);
        if (option?.start) startOverride = option.start;
        if (option?.end) endOverride = option.end;
        // A new period is a new question, so the old answer must go rather than
        // sit under a changed form looking like a reply to it.
        controller.resetAnalysis('replay');
    }

    function changePeriod(nextStart: string, nextEnd: string): void {
        startOverride = nextStart;
        endOverride = nextEnd;
        controller.resetAnalysis('replay');
    }

    /** One click: the proposed dates, and the replay over them. The proposal promises a result, so no second step. */
    function applySuggestion(): void {
        if (!suggestion) return;
        startOverride = suggestion.start;
        endOverride = suggestion.end;
        void run();
    }

    function name(assetId: number): string {
        return assetNames[assetId] ?? `#${assetId}`;
    }

    function reasonLabel(reason: string): string {
        return $t(REASON_KEYS[reason] ?? 'risk.levels.l4.replayReasonOther');
    }

    /**
     * The header names the treatment the backend applied, read off the payload: on a portfolio
     * the excluded weight is carried as cash at zero return, on a selection the assets are
     * omitted, and as soon as one was omitted the residual wording would misdescribe it.
     */
    function excludedHeader(value: ReplayExclusions): string {
        if (value.treatment === 'zero_return_residual' && value.weightTotal !== null) {
            return $t('risk.levels.l4.replayExcludedResidual', {values: {count: value.count, weight: formatReplayShare(value.weightTotal, $currentLanguage)}});
        }
        return $t('risk.levels.l4.replayExcludedOmitted', {values: {count: value.count}});
    }

    function rowLabel(row: TornadoRow): string {
        return row.assetId === undefined ? (row.bucketId ?? '') : name(row.assetId);
    }

    function rowAmount(row: TornadoRow): string {
        return !showMoney || row.amount === null ? '' : formatCurrencyAmount(String(row.amount), currency);
    }
</script>

<div class="space-y-3" data-testid="risk-replay">
    <div class="flex flex-wrap items-end gap-2">
        <div class="flex flex-col gap-1 text-xs text-gray-500 dark:text-gray-400">
            <span>{$t('risk.stress.preset')}</span>
            <SimpleSelect value={presetId} options={options.map((option) => ({value: option.value, label: option.label}))} compact dropdownPosition="auto" ariaLabel={$t('risk.stress.preset')} onchange={applyPreset} testId="risk-replay-preset" />
        </div>
        <div class="flex flex-col gap-1 text-xs text-gray-500 dark:text-gray-400" data-testid="risk-replay-period">
            <span>{$t('risk.levels.l4.replayPeriod')}</span>
            <DateRangePicker {start} {end} showPresets={false} showCustomWindow={false} compact onchange={changePeriod} />
        </div>
        <button type="button" class="flex items-center gap-1.5 rounded-lg bg-libre-green px-3 py-1.5 text-sm text-white hover:bg-primary-600 disabled:opacity-50" onclick={run} disabled={controller.replayLoading} data-testid="risk-replay-run">
            <Play size={14} />
            {$t('risk.actions.runReplay')}
        </button>
    </div>

    {#if output}
        {#if coverage}
            <!-- Above the total: it changes what the total means. -->
            <p class="rounded-lg bg-amber-50 p-2 text-xs font-medium text-amber-800 dark:bg-amber-900/20 dark:text-amber-200" data-testid="risk-replay-coverage">{warningSentence(coverage, $t)}</p>
        {/if}
        <!-- The sentence is withheld, not degraded, when the scope has no aggregate.
             `stress.py::_historical` sets `portfolio_return` on every weighted scope —
             0.0 at worst — and leaves it null on the unweighted ones, so this guard
             can never fire on a portfolio. A `—` is right inside a card and wrong
             inside a sentence: a set of assets has no composition return, so the
             per-asset bars below are the whole answer. -->
        {#if output.portfolio_return != null}
            {@const total = output.portfolio_return}
            <p class="text-sm text-gray-700 dark:text-gray-200" data-testid="risk-replay-total">
                {$t('risk.levels.l4.replayTotal', {
                    values: {
                        percent: `${total < 0 ? '−' : '+'}${(Math.abs(total) * 100).toFixed(2)}%`,
                        amount: !showMoney || output.impact_amount == null ? '' : formatCurrencyAmount(output.impact_amount, currency),
                    },
                })}
            </p>
        {/if}
        <TornadoChart {rows} label={rowLabel} amount={rowAmount} testId="risk-replay-tornado" />
        {#if exclusions}
            <div class="space-y-1 text-xs text-gray-600 dark:text-gray-300" data-testid="risk-replay-excluded" data-count={exclusions.count} data-treatment={exclusions.treatment ?? undefined} data-weight-total={exclusions.weightTotal ?? undefined}>
                <p class="font-medium" data-testid="risk-replay-excluded-header">{excludedHeader(exclusions)}</p>
                {@render excludedGroups(exclusions.groups)}
            </div>
        {/if}
        {@render suggestionButton()}
    {:else if nothingLeft}
        <div class="space-y-2 rounded-lg bg-amber-50 p-3 text-xs text-amber-800 dark:bg-amber-900/20 dark:text-amber-200" data-testid="risk-replay-nothing">
            <p class="font-medium">{$t('risk.levels.l4.replayNothing')}</p>
            {#if exclusions}
                {@render excludedGroups(exclusions.groups)}
            {/if}
            {@render suggestionButton()}
        </div>
    {/if}
</div>

{#snippet excludedGroups(groups: ReplayExclusionGroup[])}
    <ul class="space-y-0.5">
        {#each groups as group (group.reason)}
            <li data-testid="risk-replay-excluded-group" data-reason={group.reason}>
                <span data-testid="risk-replay-excluded-reason">{reasonLabel(group.reason)}</span>:
                {#each group.assets as asset, index (asset.assetId)}{index > 0 ? ', ' : ''}<span data-testid="risk-replay-excluded-asset" data-asset-id={asset.assetId} data-weight={asset.weight ?? undefined}
                        >{name(asset.assetId)}{asset.weight === null ? '' : ` (${formatReplayShare(asset.weight, $currentLanguage)})`}</span
                    >{/each}
            </li>
        {/each}
    </ul>
{/snippet}

{#snippet suggestionButton()}
    {#if suggestion}
        <div class="flex flex-wrap items-center gap-2">
            <button
                type="button"
                class="flex items-center gap-1.5 rounded-lg border border-libre-green px-2.5 py-1 text-xs text-libre-green hover:bg-green-50 disabled:opacity-50 dark:hover:bg-green-900/20"
                onclick={applySuggestion}
                disabled={controller.replayLoading}
                data-testid="risk-replay-suggested"
                data-start={suggestion.start}
                data-end={suggestion.end}
                data-recovers={suggestion.recovers.length}
            >
                <RotateCcw size={13} />
                {$t('risk.levels.l4.replaySuggested', {values: {start: formatReplayDate(suggestion.start, $currentLanguage), end: formatReplayDate(suggestion.end, $currentLanguage), count: suggestion.recovers.length}})}
            </button>
            {#if partOfCrisis}
                <span class="text-gray-500 dark:text-gray-400" data-testid="risk-replay-suggested-partial">{$t('risk.levels.l4.replaySuggestedPartial')}</span>
            {/if}
        </div>
    {/if}
{/snippet}
