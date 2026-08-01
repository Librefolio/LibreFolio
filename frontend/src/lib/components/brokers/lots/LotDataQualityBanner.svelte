<!--
  LotDataQualityBanner — foldable data-quality banner for the FIFO lots analysis.

  The backend emits ONE issue per lot for lot-scoped codes (e.g. REFERENCE_PRICE_UNAVAILABLE),
  which the old flat banner rendered as N identical rows. This component instead:
   - groups issues by code (dedup → one message per category);
   - folds behind a "N warning(s)" header, collapsed by default (like the dashboard banner);
   - lists the affected lots per category as clickable chips (lot label + opening date, plus a
     #index when several lots share the same opening day);
   - clicking a chip calls onLotClick(lotId) → the parent pulses that lot's bubble in the price chart.

  Svelte 5 runes, dark mode, data-testid selectors.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {currentLanguage} from '$lib/stores/app/language';
    import {AlertTriangle, AlertCircle, Info, ChevronDown, ChevronUp, Crosshair} from 'lucide-svelte';
    import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';

    type IssueSeverity = 'error' | 'warning' | 'info';

    interface Props {
        /** Raw FIFO data-quality issues (one per lot for lot-scoped codes). */
        issues: DataQualityIssue[];
        /** lot_id → opening_date (ISO) for the visible lots — resolves message_params.lot_id into a
         *  labelled chip whose click pulses the matching bubble. Lots absent here get no chip. */
        lotDates: Map<number, string>;
        /** Click on a lot chip → pulse that lot's bubble in the price chart. */
        onLotClick?: (lotId: number) => void;
    }

    let {issues, lotDates, onLotClick}: Props = $props();

    let expanded = $state(false);

    const severityOrder: Record<string, number> = {error: 0, warning: 1, info: 2};

    interface LotChip {
        lotId: number;
        label: string;
    }
    interface IssueGroup {
        code: string;
        severity: IssueSeverity;
        messageKey: string;
        messageParams: Record<string, string | number | boolean | null | undefined>;
        lots: LotChip[];
    }

    function formatDate(value: string): string {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString($currentLanguage || undefined, {year: 'numeric', month: 'short', day: 'numeric'});
    }

    /** Group issues by code (dedup the repeated per-lot banners), resolving each issue's lot_id into a
     *  chip. Within a group, lots opened on the same day get a #index suffix to disambiguate them. */
    let groups = $derived.by((): IssueGroup[] => {
        const byCode = new Map<string, {code: string; severity: IssueSeverity; messageKey: string; messageParams: Record<string, string | number | boolean | null | undefined>; lotIds: number[]}>();
        for (const issue of issues) {
            let group = byCode.get(issue.code);
            if (!group) {
                group = {code: issue.code, severity: issue.severity, messageKey: issue.message_i18n_key, messageParams: issue.message_params ?? {}, lotIds: []};
                byCode.set(issue.code, group);
            }
            const raw = issue.message_params?.lot_id;
            const lotId = typeof raw === 'number' ? raw : typeof raw === 'string' ? Number(raw) : NaN;
            if (Number.isFinite(lotId) && lotDates.has(lotId) && !group.lotIds.includes(lotId)) {
                group.lotIds.push(lotId);
            }
        }
        const result: IssueGroup[] = [];
        for (const group of byCode.values()) {
            const sortedIds = [...group.lotIds].sort((a, b) => (lotDates.get(a) ?? '').localeCompare(lotDates.get(b) ?? '') || a - b);
            const perDate = new Map<string, number>();
            for (const id of sortedIds) {
                const iso = lotDates.get(id) ?? '';
                perDate.set(iso, (perDate.get(iso) ?? 0) + 1);
            }
            const seen = new Map<string, number>();
            const lots: LotChip[] = sortedIds.map((id) => {
                const iso = lotDates.get(id) ?? '';
                const base = $_('brokers.lots.lotLabel', {values: {date: formatDate(iso)}});
                const total = perDate.get(iso) ?? 1;
                const index = (seen.get(iso) ?? 0) + 1;
                seen.set(iso, index);
                return {lotId: id, label: total > 1 ? `${base} #${index}` : base};
            });
            result.push({code: group.code, severity: group.severity, messageKey: group.messageKey, messageParams: group.messageParams, lots});
        }
        return result.sort((a, b) => (severityOrder[a.severity] ?? 9) - (severityOrder[b.severity] ?? 9));
    });

    let errorCount = $derived(groups.filter((group) => group.severity === 'error').length);
    let warningCount = $derived(groups.filter((group) => group.severity === 'warning').length);

    function headerText(): string {
        if (errorCount === 0 && warningCount === 0) return $_('dataQuality.headerInfoOnly');
        const parts: string[] = [];
        if (errorCount > 0) parts.push($_('dataQuality.headerErrors', {values: {errors: errorCount}}));
        if (warningCount > 0) parts.push($_('dataQuality.headerWarnings', {values: {warnings: warningCount}}));
        return parts.join(', ');
    }

    function groupedSeverity(): IssueSeverity {
        if (errorCount > 0) return 'error';
        if (warningCount > 0) return 'warning';
        return 'info';
    }

    function severityStyles(severity: IssueSeverity) {
        if (severity === 'error' || severity === 'warning') {
            return {
                container: 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400',
                chip: 'bg-amber-100 dark:bg-amber-800/40 hover:bg-amber-200 dark:hover:bg-amber-700/40',
            };
        }
        return {
            container: 'bg-sky-50 dark:bg-sky-900/20 border-sky-200 dark:border-sky-800 text-sky-700 dark:text-sky-400',
            chip: 'bg-sky-100 dark:bg-sky-800/40 hover:bg-sky-200 dark:hover:bg-sky-700/40',
        };
    }

    function severityIcon(severity: IssueSeverity) {
        if (severity === 'error') return AlertCircle;
        if (severity === 'warning') return AlertTriangle;
        return Info;
    }
</script>

{#if groups.length > 0}
    {@const styles = severityStyles(groupedSeverity())}
    <div class="border rounded-xl text-sm {styles.container} flex flex-col" data-testid="lot-data-quality-banner" role="status">
        <!-- Header — a toggle that folds/unfolds the whole list ("N warning(s)" when collapsed). -->
        <button type="button" class="flex items-center gap-2 font-medium p-4 w-full text-left" onclick={() => (expanded = !expanded)} aria-expanded={expanded} data-testid="lot-data-quality-toggle">
            {#if errorCount > 0 || warningCount > 0}
                <AlertTriangle size={16} class="shrink-0" />
            {:else}
                <Info size={16} class="shrink-0" />
            {/if}
            <span class="flex-1 min-w-0">{headerText()}</span>
            {#if expanded}
                <ChevronUp size={16} class="shrink-0 opacity-70" />
            {:else}
                <ChevronDown size={16} class="shrink-0 opacity-70" />
            {/if}
        </button>

        <!-- One row per category (revealed on expand): message + affected-lot chips. -->
        {#if expanded}
            <div class="flex flex-col gap-3 px-4 pb-4 ml-6">
                {#each groups as group (group.code)}
                    {@const Icon = severityIcon(group.severity)}
                    <div class="flex flex-col gap-1.5 text-xs" data-testid="lot-data-quality-issue-{group.code}">
                        <div class="flex items-center gap-2 flex-wrap min-w-0">
                            <Icon size={13} class="shrink-0" />
                            <span>{$_(group.messageKey, {values: group.messageParams})}</span>
                        </div>
                        {#if group.lots.length > 0}
                            <div class="flex flex-wrap items-center gap-1.5 mt-0.5">
                                <span class="opacity-70 text-[11px]">{$_('dataQuality.affectedLots')}</span>
                                {#each group.lots as lot (lot.lotId)}
                                    <button type="button" class="inline-flex items-center gap-1 px-2 py-0.5 rounded {styles.chip} transition-colors font-medium text-[11px] min-w-0" onclick={() => onLotClick?.(lot.lotId)} data-testid="lot-data-quality-chip-{lot.lotId}">
                                        <Crosshair size={10} class="shrink-0" />
                                        <span class="truncate">{lot.label}</span>
                                    </button>
                                {/each}
                            </div>
                        {/if}
                    </div>
                {/each}
            </div>
        {/if}
    </div>
{/if}
