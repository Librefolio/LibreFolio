<!--
  TxTypeIconCell — transaction type icon with smart navigation:
  - Desktop: double-click opens the MkDocs doc page.
  - Mobile: long press (≥ 500ms) opens the MkDocs doc page.
  - Single click/tap: only shows the tooltip (no navigation).

  Replaces the plain `<a href>` which opened the doc on every tap/click.
-->
<script lang="ts">
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

    interface Props {
        iconUrl: string;
        label: string;
        docUrl: string;
        txId: number;
    }

    let {iconUrl, label, docUrl, txId}: Props = $props();

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
        if (longPressTimer) {
            clearTimeout(longPressTimer);
            longPressTimer = null;
        }
    }

    function handleClick(e: MouseEvent) {
        if (suppressClick) {
            e.preventDefault();
            e.stopPropagation();
            suppressClick = false;
        }
    }
</script>

<Tooltip text={label} position="top">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <span class="tx-type-icon-link" data-testid="tx-type-icon-{txId}" aria-label={label} role="button" tabindex="-1" ondblclick={handleDblClick} onclick={handleClick} ontouchstart={handleTouchStart} ontouchend={cancelLongPress} ontouchmove={cancelLongPress} ontouchcancel={cancelLongPress}>
        <img src={iconUrl} alt={label} class="tx-type-icon" />
    </span>
</Tooltip>
