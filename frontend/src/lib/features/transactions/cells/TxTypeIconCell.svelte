<!--
  TxTypeIconCell — transaction type icon with smart navigation:
  - Desktop: double-click opens the MkDocs doc page.
  - Mobile: long press (≥ 500ms) opens the MkDocs doc page.
  - Single click/tap: only shows the tooltip (no navigation).
  - Linked charges (project 66, F5): `↳` before the icon of a charge; after a parent's icon the badge «N charges», a
    button while the table folds (the table catches its click through `data-tx-charges-badge`), a label otherwise.

  Replaces the plain `<a href>` which opened the doc on every tap/click.
-->
<script lang="ts">
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {clearTimer} from '$lib/utils/core/clearTimer';
    import {ChevronDown, ChevronRight} from 'lucide-svelte';

    interface Props {
        iconUrl: string;
        label: string;
        docUrl: string;
        txId: number;
        /** A charge linked to a parent: `↳` before the icon. */
        isCharge?: boolean;
        /** A parent's charges: the badge after the icon; `interactive` while the table folds them. */
        charges?: {label: string; expanded: boolean; interactive: boolean} | null;
    }

    let {iconUrl, label, docUrl, txId, isCharge = false, charges = null}: Props = $props();

    let longPressTimer: ReturnType<typeof setTimeout> | null = null;
    /** Prevent the subsequent click from being processed after a long-press
     *  opens the doc (the touchend→click sequence would otherwise fire). */
    let suppressClick = false;

    function openDoc() {
        window.open(docUrl, '_blank', 'noopener,noreferrer');
    }

    function handleDblClick(e: MouseEvent) {
        e.preventDefault();
        e.stopPropagation();
        openDoc();
    }

    function handleTouchStart() {
        suppressClick = false;
        longPressTimer = setTimeout(() => {
            suppressClick = true;
            openDoc();
        }, 500);
    }

    function cancelLongPress() {
        longPressTimer = clearTimer(longPressTimer);
    }

    function handleClick(e: MouseEvent) {
        if (suppressClick) {
            e.preventDefault();
            e.stopPropagation();
            suppressClick = false;
        }
    }
</script>

{#if isCharge}<span class="mr-1.5 ml-1 inline-block align-middle text-base leading-none text-lf-muted" data-testid="tx-charge-arrow-{txId}" aria-hidden="true">↳</span>{/if}<Tooltip text={label} position="top">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <span class="tx-type-icon-link" data-testid="tx-type-icon-{txId}" aria-label={label} role="button" tabindex="-1" ondblclick={handleDblClick} onclick={handleClick} ontouchstart={handleTouchStart} ontouchend={cancelLongPress} ontouchmove={cancelLongPress} ontouchcancel={cancelLongPress}>
        <img src={iconUrl} alt={label} class="tx-type-icon" />
    </span>
</Tooltip>{#if charges}{#if charges.interactive}<button
            type="button"
            class="ml-1 inline-flex items-center gap-0.5 whitespace-nowrap rounded-full border border-lf-input bg-lf-card px-2 text-[11px] font-medium leading-5 text-lf-link hover:bg-lf-hover"
            data-tx-charges-badge={txId}
            data-testid="tx-charges-badge-{txId}"
            data-expanded={charges.expanded ? 'true' : 'false'}
            aria-expanded={charges.expanded}
            >{#if charges.expanded}<ChevronDown size={12} />{:else}<ChevronRight size={12} />{/if}{charges.label}</button
        >{:else}<span class="ml-1 inline-flex items-center whitespace-nowrap rounded-full bg-lf-neutral px-2 text-[11px] font-medium leading-5 text-lf-secondary" data-testid="tx-charges-badge-{txId}" data-expanded="false">{charges.label}</span>{/if}{/if}
