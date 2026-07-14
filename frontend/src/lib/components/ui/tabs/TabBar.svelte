<script lang="ts">
    import type {ComponentType} from 'svelte';
    import {applyLinearShrink, innerContentWidth, type ShrinkTarget} from '$lib/utils/layout/labelShrink';

    export interface TabItem {
        id: string;
        label: string;
        icon?: ComponentType | null;
        badge?: number;
        testId?: string;
        className?: string;
    }

    interface Props {
        tabs: TabItem[];
        activeTab?: string;
        onchange?: (id: string) => void;
        class?: string;
        hideLabelOnMobile?: boolean;
        /** Explicit label-visibility override (e.g. container-width driven, from PageToolbar).
         *  undefined (default) falls back to the existing hideLabelOnMobile/`sm:` viewport behavior. */
        showLabels?: boolean;
        /** When true, tabs always stretch to fill 100% of the available width (equal share each),
         *  at every breakpoint — not just below `sm:`. Default false preserves today's behavior
         *  (natural content width above `sm:`), needed e.g. by settings/+page.svelte which relies
         *  on tabs NOT filling full width to push its "admin" tab to the right via `sm:ml-auto`. */
        fillWidth?: boolean;
        /** Opt-in (default false — settings/files stay untouched): when a Tab's label would
         *  otherwise wrap onto a second line (e.g. FR "Vue d'ensemble"), shrink ALL labels in
         *  this bar UNIFORMLY (linear scale, real measurement — see labelShrink.ts) instead of
         *  letting it wrap or hiding it outright. `showLabels`/`hideLabelOnMobile` above remain
         *  the only things that ever make a label disappear entirely — this only ever resizes. */
        shrinkLabelsToFit?: boolean;
    }

    let {tabs, activeTab = $bindable(''), onchange, class: className = '', hideLabelOnMobile = false, showLabels, fillWidth = false, shrinkLabelsToFit = false}: Props = $props();

    function handleTabClick(tabId: string) {
        activeTab = tabId;
        onchange?.(tabId);
    }

    // Refs for the shrink-to-fit measurement below — plain objects (not $state) since they're
    // only ever read imperatively from the ResizeObserver/effect callbacks, never reactively.
    let containerRef = $state<HTMLDivElement | null>(null);
    let buttonRefs: Record<string, HTMLButtonElement> = {};
    let labelRefs: Record<string, HTMLSpanElement> = {};

    function remeasure() {
        if (!shrinkLabelsToFit || showLabels === false) return;
        const targets: ShrinkTarget[] = [];
        for (const tab of tabs) {
            const button = buttonRefs[tab.id];
            const label = labelRefs[tab.id];
            if (!button || !label || label.offsetParent === null) continue; // not rendered/visible right now
            // "Available width" = the button's own content box minus whatever its icon+gap
            // already claims — stable regardless of the label's OWN current font-size, so this
            // works correctly both when shrinking AND when growing back (e.g. locale switched
            // back to a shorter language, or the bar got wider). Badge (also a <span>, like the
            // label) is intentionally excluded by looking for a NON-span child specifically.
            const icon = Array.from(button.children).find((c) => c !== label && c.tagName !== 'SPAN') as HTMLElement | undefined;
            const gap = parseFloat(getComputedStyle(button).columnGap || '') || 8; // matches this bar's gap-2
            const iconWidth = icon ? icon.getBoundingClientRect().width + gap : 0;
            targets.push({label, availableWidth: innerContentWidth(button) - iconWidth});
        }
        applyLinearShrink(targets);
    }

    $effect(() => {
        const el = containerRef;
        if (!el || !shrinkLabelsToFit) return;
        const ro = new ResizeObserver(() => remeasure());
        ro.observe(el);
        return () => ro.disconnect();
    });

    // Re-measure whenever the rendered label TEXT changes (locale switch, tab list change) or
    // showLabels flips — discrete/infrequent, no debounce needed. Depending on the joined label
    // string (not the array reference) re-runs precisely when the rendered text actually changes.
    $effect(() => {
        if (!shrinkLabelsToFit) return;
        void tabs.map((t) => t.label).join('|');
        void showLabels;
        requestAnimationFrame(() => remeasure());
    });
</script>

<div bind:this={containerRef} class={`flex border-b border-gray-200 dark:border-slate-600 ${className}`.trim()} role="tablist">
    {#each tabs as tab (tab.id)}
        <button
            bind:this={buttonRefs[tab.id]}
            type="button"
            class={`flex items-center justify-center gap-2 px-3 py-4 sm:px-6 text-sm font-medium transition-all ${fillWidth ? 'flex-1' : 'flex-1 sm:flex-none'} border-b-2 -mb-px ${
                activeTab === tab.id
                    ? 'text-libre-green border-libre-green bg-libre-green/5 dark:text-emerald-400 dark:border-emerald-400 dark:bg-emerald-500/10'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-slate-800/50 hover:border-gray-300 dark:hover:border-slate-500'
            } ${tab.className ?? ''}`.trim()}
            data-testid={tab.testId ?? `tab-${tab.id}`}
            role="tab"
            aria-selected={activeTab === tab.id}
            title={tab.label}
            onclick={() => handleTabClick(tab.id)}
        >
            {#if tab.icon}
                <tab.icon size={18} />
            {/if}
            <span bind:this={labelRefs[tab.id]} class={showLabels === false ? 'hidden' : showLabels === true ? '' : hideLabelOnMobile ? 'hidden sm:inline' : ''}>{tab.label}</span>
            {#if tab.badge != null && tab.badge > 0}
                <span class="text-[10px] px-1.5 py-0.5 bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400 rounded-full">
                    {tab.badge}
                </span>
            {/if}
        </button>
    {/each}
</div>
