<!--
  DataQualityIssueActions — the action of one data-quality issue, drawn as a banner offers it (`dataQualityCta.ts`).

  `placement` says which half: `head` is the one button that fixes the whole category (shape `all`), drawn above what it
  fixes; `items` are the chips that act on one item each (shapes `each-asset` and `each-pair`), drawn under the message.
  A banner renders both halves where its layout wants them and gets nothing for a shape that is not the half's.
  Shared by `DataQualityBanner` (grouped mode) and `LotDataQualityBanner` (project 69, L4): one drawing, one set of
  `data-testid`s. The click is the parent's (`onaction`): the component opens, navigates and syncs nothing itself.
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {ArrowUpRight, Loader2} from 'lucide-svelte';
    import {formatPairSlugHtml, formatPairSlugPlain} from '$lib/utils/currency/currencyFormat';
    import type {DataQualityIssue} from './DataQualityBanner.svelte';
    import {assetTargets, ctaIcon, ctaLabel, fixShape} from './dataQualityCta';

    interface Props {
        issue: DataQualityIssue;
        placement: 'head' | 'items';
        /** The chip and button classes of the row's severity (`STATUS_TONES.bannerChip`, rule 12). */
        chipClass: string;
        onaction?: (action: string, target: string | null, issue: DataQualityIssue) => void;
        /** The issue code whose action is running: its button shows a spinner and is disabled. */
        busyCode?: string | null;
    }

    let {issue, placement, chipClass, onaction, busyCode = null}: Props = $props();

    const shape = $derived(fixShape(issue));
    const action = $derived(issue.cta_action ?? '');
    const CtaIcon = $derived(ctaIcon(issue.cta_action));
    const pairs = $derived(issue.affected_fx_pairs ?? []);
    const translate = (key: string) => $_(key);

    function handleCta() {
        if (onaction && issue.cta_action) onaction(issue.cta_action, typeof issue.cta_target === 'string' ? issue.cta_target : null, issue);
    }
</script>

{#if placement === 'head' && shape === 'all'}
    <div>
        <button type="button" class="inline-flex items-center gap-1 px-2 py-0.5 rounded {chipClass} transition-colors font-medium text-[11px] shrink-0 disabled:opacity-60 disabled:cursor-not-allowed" onclick={handleCta} disabled={busyCode === issue.code} data-testid="data-quality-cta-{issue.code}">
            {#if busyCode === issue.code}
                <Loader2 size={11} class="animate-spin" />
            {:else}
                <CtaIcon size={11} />
            {/if}
            {ctaLabel(translate, issue.cta_action)}
        </button>
    </div>
{:else if placement === 'items' && shape === 'each-asset'}
    <!-- One «go to asset» chip per affected asset: the chip is the item and its fix. -->
    <div class="flex flex-wrap gap-1.5 mt-0.5" data-testid="data-quality-nav-assets-{issue.code}">
        {#each assetTargets(issue) as tgt}
            <button class="inline-flex items-center gap-1 px-2 py-0.5 rounded {chipClass} transition-colors font-medium text-[11px] min-w-0 max-w-[16rem]" onclick={() => onaction?.('navigate_asset', String(tgt.id), issue)} title={tgt.name} data-testid="data-quality-nav-asset-{tgt.id}">
                <ArrowUpRight size={11} class="shrink-0" />
                <span class="truncate">{tgt.name}</span>
            </button>
        {/each}
    </div>
{:else if placement === 'items' && shape === 'each-pair'}
    <!-- One chip per pair, the action on that pair: adding or opening works on one pair at a time. -->
    <div class="flex flex-wrap gap-1.5 mt-0.5" data-testid="data-quality-fx-pairs-{issue.code}">
        {#each pairs as pair (pair)}
            {@const label = `${ctaLabel(translate, issue.cta_action)}: ${formatPairSlugPlain(pair)}`}
            <button type="button" class="inline-flex items-center gap-1 px-2 py-0.5 rounded {chipClass} transition-colors font-medium text-[11px] min-w-0" onclick={() => onaction?.(action, pair, issue)} title={label} aria-label={label} data-testid="data-quality-fx-pair-{pair}">
                <CtaIcon size={11} class="shrink-0" />
                <span class="inline-flex items-center gap-0.5">{@html formatPairSlugHtml(pair)}</span>
            </button>
        {/each}
    </div>
{/if}
