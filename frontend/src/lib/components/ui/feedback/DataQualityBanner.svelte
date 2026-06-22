<!--
  DataQualityBanner — Unified data quality issue banner component.

  Two modes:
  - grouped: aggregated view for dashboard (single container, sorted by severity)
  - flat: one banner per issue for asset/forex detail pages

  CTA actions are emitted via `onaction` — the parent decides whether to open a modal,
  navigate, or trigger a sync. The component does not call goto() directly.

  Active IssueCodes: MISSING_PRICE, STALE_PRICE, MISSING_FX_MARKET, NAV_INCOMPLETE,
  MWRR_NOT_CALCULABLE (portfolio); ASSET_ARCHIVED, RANGE_BEFORE_FIRST_DATA,
  FX_PAIR_MISSING, FX_PAIR_NO_DATA, FX_PAIR_PARTIAL_GAP (asset/fx detail).

  Svelte 5 runes, dark mode, data-testid.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {AlertTriangle, AlertCircle, Info, ChevronDown, ChevronUp, ArrowLeftRight, Coins, ArrowUpRight} from 'lucide-svelte';
    import {getCurrencyInfo} from '$lib/stores/reference/currencyStore';

    /** Matches backend DataQualityIssue DTO. Only fields that are actively populated. */
    export interface DataQualityIssue {
        domain: string;
        code: string;
        severity: 'error' | 'warning' | 'info';
        message_i18n_key: string;
        message_params?: Record<string, string | number | boolean | null | undefined>;
        count?: number | null;
        affected_asset_ids?: number[];
        affected_asset_names?: string[];
        affected_fx_pairs?: string[];
        /** CTA intent: 'add_fx_pair' | 'navigate_asset' | 'navigate_fx' */
        cta_action?: string | null;
        /** Target identifier — asset_id string or fx pair slug */
        cta_target?: string | null;
        group_key?: string | null;
    }

    type IssueSeverity = 'error' | 'warning' | 'info';

    interface Props {
        /** Array of data quality issues to display */
        issues: DataQualityIssue[];
        /** grouped: dashboard (single container); flat: detail pages (one per issue) */
        mode?: 'grouped' | 'flat';
        /** Called when a CTA button is clicked. Parent handles modals/navigation. */
        onaction?: (action: string, target: string | null, issue: DataQualityIssue) => void;
    }

    let {issues, mode = 'flat', onaction}: Props = $props();

    let expanded = $state(false);

    const severityOrder: Record<string, number> = {error: 0, warning: 1, info: 2};

    let sortedIssues = $derived([...issues].sort((a, b) => (severityOrder[a.severity] ?? 9) - (severityOrder[b.severity] ?? 9)));

    let errorCount = $derived(issues.filter((i) => i.severity === 'error').length);
    let warningCount = $derived(issues.filter((i) => i.severity === 'warning').length);

    // Grouped mode: show first 3 issues, expand on demand
    const COLLAPSE_THRESHOLD = 3;
    let visibleIssues = $derived(expanded ? sortedIssues : sortedIssues.slice(0, COLLAPSE_THRESHOLD));
    let hasMore = $derived(sortedIssues.length > COLLAPSE_THRESHOLD);

    function getSeverityStyles(severity: IssueSeverity) {
        if (severity === 'error' || severity === 'warning') {
            return {
                container: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400',
                button: 'bg-amber-100 dark:bg-amber-800/40 hover:bg-amber-200 dark:hover:bg-amber-700/40',
            };
        }
        return {
            container: 'bg-sky-50 dark:bg-sky-900/20 border-sky-200 dark:border-sky-800 text-sky-700 dark:text-sky-400',
            button: 'bg-sky-100 dark:bg-sky-800/40 hover:bg-sky-200 dark:hover:bg-sky-700/40',
        };
    }

    function getIcon(severity: IssueSeverity) {
        if (severity === 'error') return AlertCircle;
        if (severity === 'warning') return AlertTriangle;
        return Info;
    }

    function handleCta(issue: DataQualityIssue) {
        if (onaction && issue.cta_action) {
            const target = typeof issue.cta_target === 'string' ? issue.cta_target : null;
            onaction(issue.cta_action, target, issue);
        }
    }

    function getCtaLabel(action: string | null | undefined): string {
        if (!action) return '';
        const key = `dataQuality.cta.${action}`;
        const translated = $_(key);
        return translated !== key ? translated : action.replace(/_/g, ' ');
    }

    /** Select CTA icon based on action type */
    function getCtaIcon(action: string | null | undefined) {
        if (action === 'add_fx_pair') return Coins;
        return ArrowUpRight;
    }

    function formatFxPair(slug: string): {baseFlag: string; baseCode: string; quoteFlag: string; quoteCode: string} {
        const parts = slug.includes('/') ? slug.split('/') : slug.split('-');
        const base = parts[0]?.toUpperCase() ?? '';
        const quote = parts[1]?.toUpperCase() ?? '';
        return {
            baseFlag: getCurrencyInfo(base).flag_emoji ?? '',
            baseCode: base,
            quoteFlag: getCurrencyInfo(quote).flag_emoji ?? '',
            quoteCode: quote,
        };
    }

    function getGroupedSeverity(): IssueSeverity {
        if (errorCount > 0) return 'error';
        if (warningCount > 0) return 'warning';
        return 'info';
    }

    /** Smart header: only mentions non-zero error/warning counts */
    function getHeaderText(): string {
        if (errorCount === 0 && warningCount === 0) {
            return $_('dataQuality.headerInfoOnly');
        }
        const parts: string[] = [];
        if (errorCount > 0) parts.push($_('dataQuality.headerErrors', {values: {errors: errorCount}}));
        if (warningCount > 0) parts.push($_('dataQuality.headerWarnings', {values: {warnings: warningCount}}));
        return parts.join(', ');
    }
</script>

{#if issues.length === 0}
    <!-- No issues — render nothing -->
{:else if mode === 'grouped'}
    <!-- Grouped mode (dashboard): single container, issues sorted by severity -->
    {@const groupSeverity = getGroupedSeverity()}
    {@const styles = getSeverityStyles(groupSeverity)}
    <div class="border rounded-xl p-4 text-sm {styles.container} flex flex-col gap-2" data-testid="data-quality-banner" role="status">
        <!-- Header -->
        <div class="flex items-center gap-2 font-medium">
            {#if errorCount > 0 || warningCount > 0}
                <AlertTriangle size={16} class="shrink-0" />
            {:else}
                <Info size={16} class="shrink-0" />
            {/if}
            <span>{getHeaderText()}</span>
        </div>

        <!-- Issue rows -->
        <div class="flex flex-col gap-1.5 ml-6">
            {#each visibleIssues as issue (issue.code + (issue.group_key ?? ''))}
                {@const Icon = getIcon(issue.severity)}
                {@const CtaIcon = getCtaIcon(issue.cta_action)}
                <div class="flex items-start sm:items-center gap-2 text-xs flex-col sm:flex-row" data-testid="data-quality-issue-{issue.code}">
                    <div class="flex items-center gap-2 flex-wrap min-w-0 flex-1">
                        <Icon size={13} class="shrink-0 mt-0.5 sm:mt-0" />
                        <span>{$_(issue.message_i18n_key, {values: issue.message_params ?? {}})}</span>
                        <!-- Affected asset names (compact, dimmed) -->
                        {#if (issue.affected_asset_names?.length ?? 0) > 0}
                            <span class="opacity-70 text-[11px]">
                                ({issue.affected_asset_names?.slice(0, 3).join(', ')}{(issue.affected_asset_names?.length ?? 0) > 3 ? ` +${(issue.affected_asset_names?.length ?? 0) - 3}` : ''})
                            </span>
                        {/if}
                        <!-- Affected FX pairs (with flags) -->
                        {#if (issue.affected_fx_pairs?.length ?? 0) > 0}
                            <span class="inline-flex items-center gap-1 opacity-70 text-[11px]">
                                {#each (issue.affected_fx_pairs ?? []).slice(0, 3) as pair}
                                    {@const fx = formatFxPair(pair)}
                                    <span class="inline-flex items-center gap-0.5">
                                        <span class="emoji-flag">{fx.baseFlag}</span>{fx.baseCode}<ArrowLeftRight size={9} /><span class="emoji-flag">{fx.quoteFlag}</span>{fx.quoteCode}
                                    </span>
                                {/each}
                                {#if (issue.affected_fx_pairs?.length ?? 0) > 3}
                                    <span>+{(issue.affected_fx_pairs?.length ?? 0) - 3}</span>
                                {/if}
                            </span>
                        {/if}
                    </div>
                    <!-- CTA -->
                    {#if issue.cta_action}
                        <button class="inline-flex items-center gap-1 px-2 py-0.5 rounded {styles.button} transition-colors font-medium text-[11px] shrink-0" onclick={() => handleCta(issue)} data-testid="data-quality-cta-{issue.code}">
                            <CtaIcon size={11} />
                            {getCtaLabel(issue.cta_action)}
                        </button>
                    {/if}
                </div>
            {/each}
        </div>

        <!-- Show more / less toggle (only when >3 issues) -->
        {#if hasMore}
            <button class="flex items-center gap-1 text-xs opacity-70 hover:opacity-100 transition-opacity ml-6 mt-1" onclick={() => (expanded = !expanded)} data-testid="data-quality-toggle">
                {#if expanded}
                    <ChevronUp size={12} />
                    {$_('dataQuality.hideDetails')}
                {:else}
                    <ChevronDown size={12} />
                    {$_('dataQuality.showDetails', {values: {count: sortedIssues.length - COLLAPSE_THRESHOLD}})}
                {/if}
            </button>
        {/if}
    </div>
{:else}
    <!-- Flat mode (asset/forex detail): one banner per issue -->
    {#each sortedIssues as issue (issue.code + (issue.group_key ?? ''))}
        {@const styles = getSeverityStyles(issue.severity)}
        {@const Icon = getIcon(issue.severity)}
        {@const CtaIcon = getCtaIcon(issue.cta_action)}
        <div class="border rounded-xl px-4 py-2.5 text-xs flex flex-col sm:flex-row items-start sm:items-center gap-2 {styles.container}" data-testid="data-quality-issue-{issue.code}" role="status">
            <!-- Left: icon + message + FX pairs + asset context -->
            <div class="flex items-center gap-2 flex-wrap min-w-0 flex-1">
                <Icon size={14} class="shrink-0" />
                <span>{$_(issue.message_i18n_key, {values: issue.message_params ?? {}})}</span>
                <!-- FX pairs with flags -->
                {#if (issue.affected_fx_pairs?.length ?? 0) > 0}
                    {#each issue.affected_fx_pairs ?? [] as pair}
                        {@const fx = formatFxPair(pair)}
                        <span class="font-medium inline-flex items-center gap-1">
                            <span class="emoji-flag">{fx.baseFlag}</span>
                            {fx.baseCode}
                            <ArrowLeftRight size={10} class="shrink-0" />
                            <span class="emoji-flag">{fx.quoteFlag}</span>
                            {fx.quoteCode}
                        </span>
                    {/each}
                {/if}
                <!-- Asset context (dimmed, in parens) -->
                {#if (issue.affected_asset_names?.length ?? 0) > 0}
                    <span class="inline-flex items-center gap-1 text-[11px] opacity-60">
                        ({issue.affected_asset_names?.slice(0, 2).join(', ')}{(issue.affected_asset_names?.length ?? 0) > 2 ? ` +${(issue.affected_asset_names?.length ?? 0) - 2}` : ''})
                    </span>
                {/if}
            </div>
            <!-- Right: CTA -->
            {#if issue.cta_action}
                <div class="flex items-center gap-1 self-end sm:self-auto sm:ml-auto">
                    <button class="inline-flex items-center gap-1 px-2 py-0.5 rounded {styles.button} transition-colors font-medium" onclick={() => handleCta(issue)} data-testid="data-quality-cta-{issue.code}">
                        <CtaIcon size={13} />
                        {getCtaLabel(issue.cta_action)}
                    </button>
                </div>
            {/if}
        </div>
    {/each}
{/if}
