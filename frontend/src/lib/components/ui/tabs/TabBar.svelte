<script lang="ts">
    import type {ComponentType} from 'svelte';
    import {applyLinearShrink, innerContentWidth, type ShrinkTarget} from '$lib/utils/layout/labelShrink';
    import {guideAnchor} from '$lib/features/onboarding/guideAnchors.svelte';

    export interface TabItem {
        id: string;
        label: string;
        icon?: ComponentType | null;
        badge?: number;
        testId?: string;
        guideAnchor?: string;
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
         *  on tabs NOT filling full width to push its «Administration» group to the right via `sm:ml-auto`. */
        fillWidth?: boolean;
        /** Opt-in (default false — settings/files stay untouched): when a Tab's label would
         *  otherwise wrap onto a second line (e.g. FR "Vue d'ensemble"), shrink ALL labels in
         *  this bar UNIFORMLY (linear scale, real measurement — see labelShrink.ts) instead of
         *  letting it wrap or hiding it outright. `showLabels`/`hideLabelOnMobile` above remain
         *  the only things that ever make a label disappear entirely — this only ever resizes. */
        shrinkLabelsToFit?: boolean;
        /** Opt-in (default false — the other bars keep their markup): when the tabs do not fit, the row scrolls
         *  sideways instead of being clipped by the card around it (the settings bars, in French or Spanish on a
         *  narrow screen), and the active tab is kept whole in view — on a change of tab, a resize, or a language
         *  switch. The sides that hide tabs fade out (`data-fade`: none, start, end or both; a mask, no colour). The
         *  row still fills the bar when there is room, so a tab's `ml-auto` keeps pushing it to the right. */
        scrollable?: boolean;
    }

    let {tabs, activeTab = $bindable(''), onchange, class: className = '', hideLabelOnMobile = false, showLabels, fillWidth = false, shrinkLabelsToFit = false, scrollable = false}: Props = $props();

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

    // scrollable: the box that scrolls the row sideways, and the active tab kept whole inside it.
    let scrollerRef = $state<HTMLDivElement | null>(null);

    // scrollable: the sides where more tabs are hidden, faded by a mask (P13 a). No colour: the mask only takes alpha,
    // so the fade follows the bar's own roles in both themes. Whole literals, so Tailwind generates each class.
    type Fade = 'none' | 'start' | 'end' | 'both';
    const FADE_CLASSES: Record<Fade, string> = {
        none: '',
        start: 'mask-l-from-[calc(100%-1.5rem)]',
        end: 'mask-r-from-[calc(100%-1.5rem)]',
        both: 'mask-l-from-[calc(100%-1.5rem)] mask-r-from-[calc(100%-1.5rem)]',
    };
    let fade = $state<Fade>('none');

    /** Which sides hide tabs now: more on the left once scrolled, more on the right while the row is wider. */
    function updateFade() {
        const scroller = scrollerRef;
        if (!scroller) return;
        const start = scroller.scrollLeft > 1;
        const end = scroller.scrollLeft + scroller.clientWidth < scroller.scrollWidth - 1;
        fade = start && end ? 'both' : start ? 'start' : end ? 'end' : 'none';
    }

    /** Scrolls the bar — never the page — just enough to show the active tab whole. */
    function revealActiveTab() {
        const scroller = scrollerRef;
        const button = buttonRefs[activeTab];
        if (!scroller || !button) return;
        const bar = scroller.getBoundingClientRect();
        const tab = button.getBoundingClientRect();
        if (tab.left < bar.left) scroller.scrollLeft -= bar.left - tab.left;
        else if (tab.right > bar.right) scroller.scrollLeft += tab.right - bar.right;
    }

    $effect(() => {
        const el = scrollerRef;
        const row = containerRef;
        if (!el) return;
        const ro = new ResizeObserver(() => {
            revealActiveTab();
            updateFade();
        });
        ro.observe(el);
        // The row too: it can grow while the bar keeps its size (a web font arriving late).
        if (row) ro.observe(row);
        updateFade();
        return () => ro.disconnect();
    });

    // A change of tab, or of the labels' text (a language switch): revealed once the DOM shows it.
    $effect(() => {
        if (!scrollable) return;
        void activeTab;
        void tabs.map((t) => t.label).join('|');
        requestAnimationFrame(() => {
            revealActiveTab();
            updateFade();
        });
    });
</script>

{#snippet tabRow()}
    <div bind:this={containerRef} class={['flex border-b border-lf-subtle text-lf-primary', scrollable ? 'min-w-full w-max' : '', className].filter(Boolean).join(' ')} role="tablist">
        {#each tabs as tab (tab.id)}
            <button
                bind:this={buttonRefs[tab.id]}
                type="button"
                class={`flex items-center justify-center gap-2 px-3 py-4 sm:px-6 text-sm font-medium transition-all ${fillWidth ? 'flex-1' : 'flex-1 sm:flex-none'} border-b-2 -mb-px ${
                    activeTab === tab.id ? 'text-lf-link border-lf-focus bg-lf-selected' : 'border-transparent text-lf-muted hover:text-lf-secondary hover:bg-lf-hover hover:border-lf-subtle'
                } ${tab.className ?? ''}`.trim()}
                data-testid={tab.testId ?? `tab-${tab.id}`}
                use:guideAnchor={tab.guideAnchor ?? ''}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-label={tab.icon && showLabels === false ? tab.label : undefined}
                title={tab.label}
                onclick={() => handleTabClick(tab.id)}
            >
                {#if tab.icon}
                    <tab.icon size={18} />
                {/if}
                <!-- Only a tab with an icon may lose its label: an icon-less tab would be left empty. -->
                <span bind:this={labelRefs[tab.id]} class={!tab.icon ? '' : showLabels === false ? 'hidden' : showLabels === true ? '' : hideLabelOnMobile ? 'hidden sm:inline' : ''}>{tab.label}</span>
                {#if tab.badge != null && tab.badge > 0}
                    <span class="text-[10px] px-1.5 py-0.5 bg-lf-warning-soft text-lf-warning-on-soft rounded-full">
                        {tab.badge}
                    </span>
                {/if}
            </button>
        {/each}
    </div>
{/snippet}

{#if scrollable}
    <!-- Sideways scroll instead of clipping: the row is at least as wide as the bar, so ml-auto still pushes the
         right-hand group while the tabs fit, and wider than the bar when they do not. -->
    <div bind:this={scrollerRef} class={['overflow-x-auto [scrollbar-width:thin]', FADE_CLASSES[fade]].filter(Boolean).join(' ')} data-fade={fade} data-testid="tab-bar-scroller" onscroll={updateFade}>
        {@render tabRow()}
    </div>
{:else}
    {@render tabRow()}
{/if}
