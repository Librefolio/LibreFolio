<script lang="ts">
    /**
     * L1° for Asset Global — "how much can it hurt?", asked of each asset.
     *
     * **The reduction is a transposition, not a smaller L1.** The portfolio's L1
     * takes one scope and produces three figures on one increasing scale: a bad
     * day, a bad month, the worst fall. Here the scale becomes the *columns* and
     * the assets become the *rows*, so the reader compares instruments along a
     * ruler instead of reading one instrument's ruler. That is why this is a
     * component of its own and not `L1HowMuchItHurts` with a flag: a prop cannot
     * change the arity of the input, and a boolean that switches arity is two
     * components sharing a name.
     *
     * **No money, and not by suppression.** `assetSetLevels` has no `currency`
     * parameter and returns no amount, so there is no euro figure to remember to
     * hide. An asset set has no weights; an amount here would be an arithmetic
     * claim about a portfolio the reader never described.
     *
     * **Never a ranking.** The columns are sortable by the reader, never ordered
     * by verdict by the system, and no cell is coloured relative to its
     * neighbours. `03-mappa-livelli-pagine` gives this page "a comparison, never
     * a judgement", and a badge saying which asset is "worst" is a judgement
     * wearing a comparison's clothes. The one colour used is the same negative
     * sentiment the portfolio's L1 gives *every* loss, which distinguishes a fall
     * from a rise and not one asset from another.
     *
     * **A selected asset always has a row.** Rows come from the selection and the
     * cells are nullable. An analytic that could not measure an asset — too short
     * a series — leaves blanks with the reason in the section header, because a
     * missing row would read as "not selected" rather than "not measurable".
     */
    import {_ as t} from '$lib/i18n';
    import {formatPercent} from '$lib/utils/core/formatPercent';
    import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';

    import {buildAssetSetHurtRows} from './assetSetLevels';

    interface Props {
        assetIds: number[];
        assetLabels: ReadonlyMap<number, string>;
        dailyVar: RiskAnalyticResult | null;
        monthlyVar: RiskAnalyticResult | null;
        drawdown: RiskAnalyticResult | null;
        loading?: boolean;
    }

    let {assetIds, assetLabels, dailyVar, monthlyVar, drawdown, loading = false}: Props = $props();

    let rows = $derived(buildAssetSetHurtRows(assetIds, assetLabels, dailyVar, monthlyVar, drawdown));
    let hasAnyFigure = $derived(rows.some((row) => row.badDay !== null || row.badMonth !== null || row.worstFall !== null));

    /**
     * A loss drawn as a fall, with the typographic minus.
     *
     * `formatPercent` emits an ASCII hyphen and the level nets assert U+2212, so
     * the sign is prefixed here rather than delegated. Both glyphs draw as a
     * short stroke, so a mismatch is invisible on screen and surfaces only as a
     * failing string comparison — which is the worst place to discover it.
     *
     * The magnitude is taken as an absolute value because the two contracts
     * disagree on sign by design: the VaR pair arrives positive (`ge=0`), the
     * drawdown pair negative (`le=0`). Normalising in the helper would have
     * hidden which contract a number came from; normalising here, at the last
     * moment before it is drawn, does not.
     */
    function fall(fraction: number): string {
        return `\u2212${formatPercent(Math.abs(fraction), {scale: 100, signed: false, digits: 1})}`;
    }

    /** A rise drawn as a rise: the recovery a fall demands is a gain. */
    function rise(fraction: number): string {
        return `+${formatPercent(fraction, {scale: 100, signed: false, digits: 1})}`;
    }

    const DOCS = 'financial-theory/technical-analysis/risk-metrics';

    /**
     * The columns, in the order that carries the argument.
     *
     * Increasing in horizon from left to right — one day, one month, the whole
     * window — because the defect the redesign exists to cure was a one-day loss
     * printed beside a multi-year drawdown with no declared change of scale. The
     * reader summed them. Transposing the table does not make that safe; only the
     * ordering and the headings do.
     */
    const COLUMNS = [
        {id: 'badDay', docs: `${DOCS}/conditional-value-at-risk/`},
        {id: 'badMonth', docs: `${DOCS}/conditional-value-at-risk/`},
        {id: 'worstFall', docs: `${DOCS}/max-drawdown/`},
        {id: 'currentFall', docs: `${DOCS}/current-drawdown/`},
        {id: 'toPeak', docs: `${DOCS}/max-drawdown/`},
    ] as const;
</script>

<div class="space-y-3" data-testid="risk-asset-set-l1">
    <p class="text-xs text-gray-500 dark:text-gray-400">{$t('risk.assetSet.levels.l1.description')}</p>

    {#if loading && !hasAnyFigure}
        <div class="h-32 animate-pulse rounded-lg bg-gray-100 dark:bg-slate-700" data-testid="risk-asset-set-l1-loading"></div>
    {:else if rows.length === 0}
        <p class="py-4 text-center text-sm text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-l1-empty">{$t('risk.states.empty')}</p>
    {:else}
        <div class="w-full overflow-x-auto">
            <table class="w-full text-sm" data-testid="risk-asset-set-l1-table" data-row-count={rows.length}>
                <thead>
                    <tr class="border-b border-gray-100 text-xs text-gray-500 dark:border-slate-700 dark:text-gray-400">
                        <th class="py-2 pr-3 text-left font-medium">{$t('risk.assetSet.levels.asset')}</th>
                        {#each COLUMNS as column (column.id)}
                            <th class="py-2 pl-3 text-right font-medium whitespace-nowrap">
                                <span class="inline-flex items-center gap-1">
                                    {$t(`risk.assetSet.levels.l1.columns.${column.id}`)}
                                    <a class="text-gray-400 hover:text-blue-500 dark:text-gray-500" href="/mkdocs/{column.docs}" target="_blank" rel="noopener noreferrer" aria-label={$t(`risk.assetSet.levels.l1.columns.${column.id}`)} data-testid="risk-asset-set-l1-docs-{column.id}">&#9432;</a>
                                </span>
                            </th>
                        {/each}
                    </tr>
                </thead>
                <tbody>
                    {#each rows as row (row.assetId)}
                        <tr class="border-b border-gray-50 last:border-0 dark:border-slate-800" data-testid="risk-asset-set-l1-row" data-asset-id={row.assetId}>
                            <td class="py-2 pr-3 text-gray-700 dark:text-gray-200" data-testid="risk-asset-set-l1-name">{row.name}</td>

                            <td class="py-2 pl-3 text-right tabular-nums text-red-600 dark:text-red-400" data-testid="risk-asset-set-l1-badDay" data-measured={row.badDay !== null}>
                                {row.badDay === null ? '\u2014' : fall(row.badDay)}
                            </td>
                            <td class="py-2 pl-3 text-right tabular-nums text-red-600 dark:text-red-400" data-testid="risk-asset-set-l1-badMonth" data-measured={row.badMonth !== null}>
                                {row.badMonth === null ? '\u2014' : fall(row.badMonth)}
                            </td>

                            <!-- The deepest fall carries its own duration and recovery state as a
                                 second line: they refine one figure rather than standing as two
                                 more risks, exactly as the portfolio's L1 keeps its acquired
                                 measures as sub-rows instead of promoting them to cards. -->
                            <td class="py-2 pl-3 text-right tabular-nums text-red-600 dark:text-red-400" data-testid="risk-asset-set-l1-worstFall" data-measured={row.worstFall !== null} data-recovery={row.recovery ?? ''}>
                                {row.worstFall === null ? '\u2014' : fall(row.worstFall)}
                                {#if row.worstFallDays !== null && row.worstFall !== null}
                                    <span class="block text-[10px] font-normal text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-l1-worstFall-days">
                                        {$t('risk.assetSet.levels.l1.lastedDays', {values: {days: row.worstFallDays}})}
                                    </span>
                                {/if}
                            </td>

                            <td class="py-2 pl-3 text-right tabular-nums text-red-600 dark:text-red-400" data-testid="risk-asset-set-l1-currentFall" data-measured={row.currentFall !== null}>
                                {row.currentFall === null ? '\u2014' : fall(row.currentFall)}
                            </td>

                            <!-- The number that teaches the asymmetry: a 50% fall needs a +100%
                                 rise, not a +50% one. Drawn as a gain, because it is one. -->
                            <td class="py-2 pl-3 text-right tabular-nums text-gray-600 dark:text-gray-300" data-testid="risk-asset-set-l1-toPeak" data-measured={row.toPeak !== null}>
                                {row.toPeak === null ? '\u2014' : rise(row.toPeak)}
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        <!-- An em-dash means "this asset could not be measured over this window",
             not "zero". Said once under the table rather than in every blank cell,
             and said at all because a dash is otherwise indistinguishable from a
             figure that failed to load. -->
        <p class="text-[11px] text-gray-400 dark:text-gray-500" data-testid="risk-asset-set-l1-blank-note">{$t('risk.assetSet.levels.blankNote')}</p>
    {/if}
</div>
