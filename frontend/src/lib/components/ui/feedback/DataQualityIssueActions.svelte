<!--
  DataQualityIssueActions — the action of one data-quality issue, drawn as a banner offers it (`dataQualityCta.ts`).

  `placement` says which half: `head` is the one button that fixes the whole category (shape `all`), drawn above what it
  fixes; `items` are the chips that act on one item each (shapes `each-asset` and `each-pair`), drawn under the message.
  A banner renders both halves where its layout wants them and gets nothing for a shape that is not the half's.
  Shared by `DataQualityBanner` (grouped mode) and `LotDataQualityBanner` (project 69, L4): one drawing, one set of
  `data-testid`s. The click is the parent's (`onaction`): the component opens, navigates and syncs nothing itself.
  Every chip is the standard `Button`, `variant="chip"` in the row's tone, `size="xs"` (85 BTN-2d).
-->
<script lang="ts">
    import {_} from '$lib/i18n';
    import {ArrowUpRight} from 'lucide-svelte';
    import Button from '$lib/components/ui/button/Button.svelte';
    import type {ButtonTone} from '$lib/components/ui/button/buttonClasses';
    import {DATA_QUALITY_TONE} from '$lib/theme/toneClasses';
    import {formatPairSlugHtml, formatPairSlugPlain} from '$lib/utils/currency/currencyFormat';
    import type {DataQualityIssue} from './DataQualityBanner.svelte';
    import {assetTargets, ctaIcon, ctaLabel, fixShape} from './dataQualityCta';

    interface Props {
        issue: DataQualityIssue;
        placement: 'head' | 'items';
        /** The row's tone (`DATA_QUALITY_TONE`, rule 12); the issue's own severity when absent. */
        tone?: ButtonTone;
        /**
         * @deprecated The chips are `Button variant="chip"` now and take `tone`: ignored, kept only until
         * `LotDataQualityBanner` passes `tone` instead.
         */
        chipClass?: string;
        onaction?: (action: string, target: string | null, issue: DataQualityIssue) => void;
        /** The issue code whose action is running: its button shows a spinner and is busy. */
        busyCode?: string | null;
    }

    let {issue, placement, tone, onaction, busyCode = null}: Props = $props();

    const shape = $derived(fixShape(issue));
    const action = $derived(issue.cta_action ?? '');
    const CtaIcon = $derived(ctaIcon(issue.cta_action));
    const pairs = $derived(issue.affected_fx_pairs ?? []);
    const chipTone = $derived<ButtonTone>(tone ?? DATA_QUALITY_TONE[issue.severity] ?? 'info');
    const translate = (key: string) => $_(key);

    function handleCta() {
        if (onaction && issue.cta_action) onaction(issue.cta_action, typeof issue.cta_target === 'string' ? issue.cta_target : null, issue);
    }
</script>

{#if placement === 'head' && shape === 'all'}
    <div>
        <Button variant="chip" tone={chipTone} size="xs" icon={CtaIcon} label={ctaLabel(translate, issue.cta_action)} busy={busyCode === issue.code} onclick={handleCta} data-testid="data-quality-cta-{issue.code}" />
    </div>
{:else if placement === 'items' && shape === 'each-asset'}
    <!-- One «go to asset» chip per affected asset: the chip is the item and its fix. A long name cuts, and the whole
         name shows on a long press, a rest or Tab while it is cut. -->
    <div class="flex flex-wrap gap-1.5 mt-0.5" data-testid="data-quality-nav-assets-{issue.code}">
        {#each assetTargets(issue) as tgt}
            <Button variant="chip" tone={chipTone} size="xs" icon={ArrowUpRight} label={tgt.name} truncate class="max-w-[16rem]" onclick={() => onaction?.('navigate_asset', String(tgt.id), issue)} data-testid="data-quality-nav-asset-{tgt.id}" />
        {/each}
    </div>
{:else if placement === 'items' && shape === 'each-pair'}
    <!-- One chip per pair, the action on that pair: adding or opening works on one pair at a time. The word is the pair
         with its flags; the name says the action and the pair. -->
    <div class="flex flex-wrap gap-1.5 mt-0.5" data-testid="data-quality-fx-pairs-{issue.code}">
        {#each pairs as pair (pair)}
            <Button variant="chip" tone={chipTone} size="xs" icon={CtaIcon} label="{ctaLabel(translate, issue.cta_action)}: {formatPairSlugPlain(pair)}" onclick={() => onaction?.(action, pair, issue)} data-testid="data-quality-fx-pair-{pair}">
                <span class="inline-flex items-center gap-0.5">{@html formatPairSlugHtml(pair)}</span>
            </Button>
        {/each}
    </div>
{/if}
