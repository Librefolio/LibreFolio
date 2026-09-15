<script lang="ts">
    import {browser} from '$app/environment';
    import {ArrowLeft, ArrowRight, LogOut, MousePointer2, X} from 'lucide-svelte';
    import type {GuideHighlightMode, GuidePanelPlacement, GuidePointerMode, GuideScrollPolicy} from '$lib/features/onboarding/onboardingGuideCatalog';

    interface Props {
        open?: boolean;
        suspended?: boolean;
        anchor?: HTMLElement | null;
        stepId: string;
        title: string;
        description: string;
        actionHint?: string;
        pointer?: GuidePointerMode;
        highlight?: GuideHighlightMode;
        backdrop?: boolean;
        panelPlacement?: GuidePanelPlacement;
        scrollPolicy?: GuideScrollPolicy;
        advanceOnTarget?: boolean;
        progressLabel?: string;
        backLabel?: string;
        nextLabel?: string;
        skipLabel?: string;
        closeLabel?: string;
        busyLabel?: string;
        error?: string | null;
        showBack?: boolean;
        backDisabled?: boolean;
        showNext?: boolean;
        showNextArrow?: boolean;
        showSkip?: boolean;
        showClose?: boolean;
        focusOnOpen?: boolean;
        busy?: boolean;
        onback?: () => void;
        onnext?: () => void;
        onskip?: () => void;
        onclose?: () => void;
        ontargetactivate?: () => void;
    }

    interface AnchorRect {
        left: number;
        top: number;
        right: number;
        bottom: number;
        width: number;
        height: number;
    }

    interface PanelGeometry {
        left: number;
        top: number;
        width: number;
        height: number;
        placement: Exclude<GuidePanelPlacement, 'auto'>;
    }

    let {
        open = false,
        suspended = false,
        anchor = null,
        stepId,
        title,
        description,
        actionHint = '',
        pointer = 'none',
        highlight = 'none',
        backdrop = false,
        panelPlacement = 'auto',
        scrollPolicy = 'nearest-if-hidden',
        advanceOnTarget = false,
        progressLabel = '',
        backLabel = 'Back',
        nextLabel = 'Next',
        skipLabel = 'Skip',
        closeLabel = 'Close',
        busyLabel = 'Waiting for this area...',
        error = null,
        showBack = true,
        backDisabled = false,
        showNext = true,
        showNextArrow = true,
        showSkip = true,
        showClose = true,
        focusOnOpen = true,
        busy = false,
        onback,
        onnext,
        onskip,
        onclose,
        ontargetactivate,
    }: Props = $props();

    let panel = $state<HTMLElement | null>(null);
    let panelRect = $state<AnchorRect | null>(null);
    let anchorRect = $state<AnchorRect | null>(null);
    let candidateRect: AnchorRect | null = null;
    let stableFrames = 0;
    let targetStable = $state(false);
    let geometryState = $state<'waiting' | 'revalidating' | 'stable'>('waiting');
    let viewportWidth = $state(0);
    let viewportHeight = $state(0);
    let mobile = $state(false);
    let focusedStepId = '';
    let panelHovered = $state(false);
    let panelFocused = $state(false);
    let baseSubdued = $state(false);
    let panelSubdued = $derived(baseSubdued && !panelHovered && !panelFocused);

    const titleId = 'onboarding-coachmark-title';
    const descriptionId = 'onboarding-coachmark-description';
    const safeMargin = 16;
    const targetGap = 16;
    const cursorPadding = 6;
    const cursorGlyphTip = 3;
    let guideState = $derived(error ? 'error' : anchorRect && targetStable ? 'anchored' : 'waiting');
    let highlightStyle = $derived.by(() => {
        const rect = anchorRect;
        return rect ? `left:${Math.max(rect.left - 6, 4)}px;top:${Math.max(rect.top - 6, 4)}px;width:${Math.max(rect.width + 12, 12)}px;height:${Math.max(rect.height + 12, 12)}px;` : '';
    });
    let targetCenterX = $derived(anchorRect ? anchorRect.left + anchorRect.width / 2 : 0);
    let targetCenterY = $derived(anchorRect ? anchorRect.top + anchorRect.height / 2 : 0);
    let panelGeometry = $derived.by(() => resolvePanelGeometry());
    let panelStyle = $derived(`left:${panelGeometry.left}px;top:${panelGeometry.top}px;width:${panelGeometry.width}px;`);
    let pointerStyle = $derived(`left:${targetCenterX - cursorPadding - cursorGlyphTip}px;top:${targetCenterY - cursorPadding - cursorGlyphTip}px;`);
    let panelMeasureKey = $derived([stepId, panelPlacement, anchorRect?.left ?? '', anchorRect?.top ?? '', anchorRect?.width ?? '', anchorRect?.height ?? '', viewportWidth, viewportHeight, mobile, title, description, actionHint, error ?? ''].join(':'));

    function clamp(value: number, minimum: number, maximum: number): number {
        return Math.min(Math.max(value, minimum), Math.max(maximum, minimum));
    }

    function intersectsTarget(candidate: PanelGeometry, target: AnchorRect): boolean {
        return candidate.left < target.right + targetGap && candidate.left + candidate.width > target.left - targetGap && candidate.top < target.bottom + targetGap && candidate.top + candidate.height > target.top - targetGap;
    }

    function insideViewport(candidate: PanelGeometry): boolean {
        return candidate.left >= safeMargin && candidate.top >= safeMargin && candidate.left + candidate.width <= viewportWidth - safeMargin && candidate.top + candidate.height <= viewportHeight - safeMargin;
    }

    function panelCandidate(placement: Exclude<GuidePanelPlacement, 'auto'>, width: number, height: number, target: AnchorRect): PanelGeometry {
        const centerX = target.left + target.width / 2;
        const centerY = target.top + target.height / 2;
        if (placement === 'left') {
            return {left: target.left - width - targetGap, top: clamp(centerY - height / 2, safeMargin, viewportHeight - height - safeMargin), width, height, placement};
        }
        if (placement === 'right') {
            return {left: target.right + targetGap, top: clamp(centerY - height / 2, safeMargin, viewportHeight - height - safeMargin), width, height, placement};
        }
        if (placement === 'top') {
            return {left: clamp(centerX - width / 2, safeMargin, viewportWidth - width - safeMargin), top: target.top - height - targetGap, width, height, placement};
        }
        if (placement === 'bottom') {
            return {left: clamp(centerX - width / 2, safeMargin, viewportWidth - width - safeMargin), top: target.bottom + targetGap, width, height, placement};
        }
        return {
            left: (viewportWidth - width) / 2,
            top: (viewportHeight - height) / 2,
            width,
            height,
            placement,
        };
    }

    function resolvePanelGeometry(): PanelGeometry {
        const width = Math.min(360, Math.max(viewportWidth - safeMargin * 2, 0));
        const height = Math.min(panelRect?.height ?? 220, Math.max(viewportHeight - safeMargin * 2, 0));
        const centered: PanelGeometry = {
            left: Math.max((viewportWidth - width) / 2, safeMargin),
            top: Math.max((viewportHeight - height) / 2, safeMargin),
            width,
            height,
            placement: 'center',
        };
        const target = anchorRect;
        if (!target || viewportWidth === 0 || viewportHeight === 0) return centered;

        const available: Array<{placement: Exclude<GuidePanelPlacement, 'auto' | 'center'>; space: number}> = [
            {placement: 'right', space: viewportWidth - target.right},
            {placement: 'left', space: target.left},
            {placement: 'bottom', space: viewportHeight - target.bottom},
            {placement: 'top', space: target.top},
        ];
        available.sort((first, second) => second.space - first.space);
        const automaticOrder = available.map(({placement}) => placement);
        const requestedOrder = panelPlacement === 'auto' ? automaticOrder : [panelPlacement, ...automaticOrder.filter((placement) => placement !== panelPlacement)];
        const placements = [...new Set<Exclude<GuidePanelPlacement, 'auto'>>([...requestedOrder, 'center'])];
        const candidates = placements.map((placement) => panelCandidate(placement, width, height, target));
        return candidates.find((candidate) => insideViewport(candidate) && !intersectsTarget(candidate, target)) ?? candidates.find(insideViewport) ?? centered;
    }

    function toAnchorRect(rect: DOMRect): AnchorRect {
        return {
            left: rect.left,
            top: rect.top,
            right: rect.right,
            bottom: rect.bottom,
            width: rect.width,
            height: rect.height,
        };
    }

    function rectsMatch(first: AnchorRect | null, second: AnchorRect): boolean {
        if (!first) return false;
        return Math.abs(first.left - second.left) < 0.5 && Math.abs(first.top - second.top) < 0.5 && Math.abs(first.width - second.width) < 0.5 && Math.abs(first.height - second.height) < 0.5;
    }

    function guideScrollRoot(element: HTMLElement): HTMLElement | null {
        const explicit = element.closest<HTMLElement>('[data-guide-scroll-root]');
        if (explicit) return explicit;
        let candidate = element.parentElement;
        while (candidate && candidate !== document.body) {
            const style = window.getComputedStyle(candidate);
            if (/(auto|scroll|overlay)/.test(`${style.overflowX} ${style.overflowY}`)) return candidate;
            candidate = candidate.parentElement;
        }
        return null;
    }

    function refreshPosition(commitTransient = false) {
        if (!browser) return;
        viewportWidth = window.innerWidth;
        viewportHeight = window.innerHeight;
        mobile = window.matchMedia('(max-width: 640px)').matches;
        if (!anchor?.isConnected) {
            anchorRect = null;
            candidateRect = null;
            stableFrames = 0;
            targetStable = false;
            geometryState = 'waiting';
            return;
        }
        const measured = toAnchorRect(anchor.getBoundingClientRect());
        if (commitTransient && anchorRect) {
            anchorRect = measured;
            candidateRect = measured;
            stableFrames = 1;
            targetStable = true;
            geometryState = 'revalidating';
            return;
        }
        if (rectsMatch(candidateRect, measured)) {
            stableFrames += 1;
        } else {
            candidateRect = measured;
            stableFrames = 1;
        }
        if (stableFrames >= 2) {
            if (!rectsMatch(anchorRect, measured)) anchorRect = measured;
            targetStable = true;
            geometryState = 'stable';
        } else {
            if (anchorRect) {
                targetStable = true;
                geometryState = 'revalidating';
            } else {
                targetStable = false;
                geometryState = 'waiting';
            }
        }
    }

    function refreshPanelRect() {
        panelRect = panel?.isConnected ? toAnchorRect(panel.getBoundingClientRect()) : null;
    }

    function closeFromEscape(event: KeyboardEvent) {
        if (!open || suspended || busy || event.key !== 'Escape') return;
        event.stopPropagation();
        onclose?.();
    }

    $effect(() => {
        if (!browser || !open) {
            anchorRect = null;
            panelRect = null;
            targetStable = false;
            geometryState = 'waiting';
            return;
        }
        candidateRect = null;
        stableFrames = 0;
        targetStable = false;
        geometryState = 'waiting';
        let stabilityFrame: number | null = null;
        const measureUntilStable = () => {
            refreshPosition();
            if (geometryState !== 'stable') {
                stabilityFrame = requestAnimationFrame(measureUntilStable);
            } else {
                stabilityFrame = null;
            }
        };
        const scheduleStableMeasurement = () => {
            if (anchorRect) {
                targetStable = true;
                geometryState = 'revalidating';
            } else {
                targetStable = false;
                geometryState = 'waiting';
            }
            stableFrames = 0;
            if (stabilityFrame == null) stabilityFrame = requestAnimationFrame(measureUntilStable);
        };
        const observer = anchor && typeof ResizeObserver !== 'undefined' ? new ResizeObserver(scheduleStableMeasurement) : null;
        if (anchor) observer?.observe(anchor);
        const motionRoot = anchor?.closest<HTMLElement>('.modal-content, nav') ?? anchor;
        let motionFrame: number | null = null;
        const followMotion = () => {
            refreshPosition(true);
            refreshPanelRect();
            const animations = typeof motionRoot?.getAnimations === 'function' ? motionRoot.getAnimations({subtree: true}) : [];
            if (animations.some((animation) => animation.playState === 'running')) {
                motionFrame = requestAnimationFrame(followMotion);
            } else {
                motionFrame = null;
                scheduleStableMeasurement();
            }
        };
        const startFollowingMotion = () => {
            if (anchorRect) {
                targetStable = true;
                geometryState = 'revalidating';
            } else {
                targetStable = false;
                geometryState = 'waiting';
            }
            stableFrames = 0;
            if (stabilityFrame != null) cancelAnimationFrame(stabilityFrame);
            stabilityFrame = null;
            if (motionFrame == null) motionFrame = requestAnimationFrame(followMotion);
        };
        const finishFollowingMotion = () => {
            if (motionFrame != null) cancelAnimationFrame(motionFrame);
            motionFrame = null;
            scheduleStableMeasurement();
        };
        motionRoot?.addEventListener('transitionrun', startFollowingMotion);
        motionRoot?.addEventListener('transitionend', finishFollowingMotion);
        motionRoot?.addEventListener('transitioncancel', finishFollowingMotion);
        window.addEventListener('resize', scheduleStableMeasurement);
        const scrollRoot = anchor ? guideScrollRoot(anchor) : null;
        const followScroll = () => {
            refreshPosition(true);
            scheduleStableMeasurement();
        };
        window.addEventListener('scroll', followScroll);
        scrollRoot?.addEventListener('scroll', followScroll);
        const runningAnimations = typeof motionRoot?.getAnimations === 'function' ? motionRoot.getAnimations({subtree: true}) : [];
        if (runningAnimations.some((animation) => animation.playState === 'running')) {
            startFollowingMotion();
        } else {
            scheduleStableMeasurement();
        }
        return () => {
            observer?.disconnect();
            if (stabilityFrame != null) cancelAnimationFrame(stabilityFrame);
            if (motionFrame != null) cancelAnimationFrame(motionFrame);
            motionRoot?.removeEventListener('transitionrun', startFollowingMotion);
            motionRoot?.removeEventListener('transitionend', finishFollowingMotion);
            motionRoot?.removeEventListener('transitioncancel', finishFollowingMotion);
            window.removeEventListener('resize', scheduleStableMeasurement);
            window.removeEventListener('scroll', followScroll);
            scrollRoot?.removeEventListener('scroll', followScroll);
        };
    });

    $effect(() => {
        if (!browser || !open || suspended || !anchor || !advanceOnTarget) return;
        const linkedAnchor = anchor;
        const activate = () => ontargetactivate?.();
        linkedAnchor.addEventListener('click', activate, {capture: true});
        return () => linkedAnchor.removeEventListener('click', activate, {capture: true});
    });

    $effect(() => {
        void stepId;
        void error;
        void suspended;
        baseSubdued = false;
        if (!browser || !open || suspended) return;
        const timer = window.setTimeout(() => {
            baseSubdued = true;
        }, 3_000);
        return () => window.clearTimeout(timer);
    });

    $effect(() => {
        void panelMeasureKey;
        if (!browser || !open || !panel) {
            panelRect = null;
            return;
        }
        let secondFrame: number | null = null;
        const frame = requestAnimationFrame(() => {
            refreshPanelRect();
            secondFrame = requestAnimationFrame(refreshPanelRect);
        });
        const observer = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(refreshPanelRect) : null;
        observer?.observe(panel);
        return () => {
            cancelAnimationFrame(frame);
            if (secondFrame != null) cancelAnimationFrame(secondFrame);
            observer?.disconnect();
        };
    });

    $effect(() => {
        if (!browser || !open || !anchor) return;
        const linkedAnchor = anchor;
        const previousDescription = linkedAnchor.getAttribute('aria-describedby');
        linkedAnchor.setAttribute('aria-describedby', descriptionId);
        let scrollFrame: number | null = null;
        if (targetStable && scrollPolicy === 'nearest-if-hidden') {
            scrollFrame = requestAnimationFrame(() => {
                const rect = linkedAnchor.getBoundingClientRect();
                const scrollRoot = guideScrollRoot(linkedAnchor);
                const appHeader = scrollRoot ? null : document.querySelector<HTMLElement>('[data-testid="app-header"]');
                const bounds = scrollRoot?.getBoundingClientRect() ?? {
                    left: 0,
                    top: 0,
                    right: window.innerWidth,
                    bottom: window.innerHeight,
                };
                const safeTop = Math.max(bounds.top, (appHeader?.getBoundingClientRect().bottom ?? 0) + 8);
                const outsideBounds = rect.right <= bounds.left || rect.left >= bounds.right || rect.bottom <= bounds.top || rect.top >= bounds.bottom;
                const obscuredByHeader = !scrollRoot && rect.top < safeTop && rect.bottom > bounds.top;
                if (!scrollRoot && rect.top < safeTop) {
                    window.scrollBy({
                        top: rect.top - safeTop,
                        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
                    });
                } else if (outsideBounds) {
                    linkedAnchor.scrollIntoView({
                        block: 'nearest',
                        inline: 'nearest',
                        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
                    });
                } else if (obscuredByHeader) {
                    window.scrollBy({
                        top: rect.top - safeTop,
                        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
                    });
                }
            });
        }
        return () => {
            if (scrollFrame != null) cancelAnimationFrame(scrollFrame);
            if (linkedAnchor.getAttribute('aria-describedby') === descriptionId) {
                if (previousDescription) {
                    linkedAnchor.setAttribute('aria-describedby', previousDescription);
                } else {
                    linkedAnchor.removeAttribute('aria-describedby');
                }
            }
        };
    });

    $effect(() => {
        if (!open) {
            focusedStepId = '';
            return;
        }
        if (!browser || suspended || !focusOnOpen || !panel || focusedStepId === stepId) return;
        focusedStepId = stepId;
        const frame = requestAnimationFrame(() => panel?.focus({preventScroll: true}));
        return () => cancelAnimationFrame(frame);
    });
</script>

<svelte:window onkeydown={closeFromEscape} />

{#if open}
    <div
        class="pointer-events-none fixed inset-0"
        class:invisible={suspended}
        style="z-index: 80;"
        data-testid="onboarding-coachmark"
        data-step-id={stepId}
        data-guide-state={guideState}
        data-geometry-state={geometryState}
        data-placement={panelGeometry.placement}
        data-panel-placement={panelGeometry.placement}
        data-pointer={pointer}
        data-highlight={highlight}
        data-target-stable={targetStable ? 'true' : 'false'}
        data-target-center-x={targetStable ? targetCenterX : ''}
        data-target-center-y={targetStable ? targetCenterY : ''}
        data-pointer-hotspot-x={pointer === 'cursor' && targetStable ? targetCenterX : ''}
        data-pointer-hotspot-y={pointer === 'cursor' && targetStable ? targetCenterY : ''}
        aria-hidden={suspended}
    >
        {#if backdrop}
            {#if anchorRect && targetStable}
                <div class="pointer-events-auto fixed left-0 right-0 top-0 bg-black/45" style={`height:${Math.max(anchorRect.top - 8, 0)}px;`} data-testid="onboarding-spotlight-top"></div>
                <div class="pointer-events-auto fixed bottom-0 left-0 right-0 bg-black/45" style={`top:${Math.min(anchorRect.bottom + 8, viewportHeight)}px;`} data-testid="onboarding-spotlight-bottom"></div>
                <div class="pointer-events-auto fixed left-0 bg-black/45" style={`top:${Math.max(anchorRect.top - 8, 0)}px;width:${Math.max(anchorRect.left - 8, 0)}px;height:${Math.max(anchorRect.height + 16, 0)}px;`} data-testid="onboarding-spotlight-left"></div>
                <div class="pointer-events-auto fixed right-0 bg-black/45" style={`top:${Math.max(anchorRect.top - 8, 0)}px;left:${Math.min(anchorRect.right + 8, viewportWidth)}px;height:${Math.max(anchorRect.height + 16, 0)}px;`} data-testid="onboarding-spotlight-right"></div>
            {:else}
                <div class="pointer-events-auto absolute inset-0 bg-black/45" data-testid="onboarding-coachmark-backdrop"></div>
            {/if}
        {/if}

        {#if anchorRect && targetStable && highlight === 'pulse'}
            <div class="absolute animate-pulse rounded-xl border-4 border-emerald-400 bg-transparent shadow-[0_0_0_5px_rgba(52,211,153,0.4),0_0_28px_rgba(52,211,153,0.95)] motion-reduce:animate-none" style={highlightStyle} data-testid="onboarding-coachmark-highlight"></div>
        {/if}

        {#if pointer === 'cursor' && anchorRect && targetStable}
            <div class="pointer-events-none fixed z-[82] animate-bounce rounded-full bg-white/70 p-1.5 text-libre-green/80 shadow-lg motion-reduce:animate-none dark:bg-slate-800/70 dark:text-emerald-300/80" style={pointerStyle} aria-hidden="true" data-testid="onboarding-coachmark-pointer">
                <MousePointer2 size={18} />
            </div>
        {/if}

        <div
            bind:this={panel}
            class="pointer-events-auto fixed z-[83] rounded-2xl border border-gray-200 p-4 shadow-2xl outline-none transition-colors duration-500 motion-reduce:transition-none dark:border-slate-700 {panelSubdued ? 'bg-white/80 backdrop-blur-sm dark:bg-slate-800/80' : 'bg-white dark:bg-slate-800'}"
            style={panelStyle}
            role="dialog"
            aria-modal="false"
            aria-labelledby={titleId}
            aria-describedby={descriptionId}
            aria-live="polite"
            aria-busy={busy}
            tabindex="-1"
            data-testid="onboarding-coachmark-panel"
            data-subdued={panelSubdued ? 'true' : 'false'}
            onmouseenter={() => (panelHovered = true)}
            onmouseleave={() => (panelHovered = false)}
            onfocusin={(event) => {
                if (event.target !== panel) panelFocused = true;
            }}
            onfocusout={(event) => {
                if (!panel?.contains(event.relatedTarget as Node | null)) panelFocused = false;
            }}
        >
            <div class="mb-3 flex items-start justify-between gap-3" data-testid="onboarding-coachmark-top-actions">
                {#if showSkip}
                    <button
                        type="button"
                        class="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-sm text-gray-600 hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:opacity-50 dark:text-gray-300 dark:hover:bg-slate-700"
                        onclick={onskip}
                        disabled={busy}
                        data-testid="onboarding-coachmark-skip"
                    >
                        <LogOut size={15} />
                        {skipLabel}
                    </button>
                {:else}
                    <span></span>
                {/if}
                {#if showClose}
                    <button
                        type="button"
                        class="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:opacity-50 dark:text-gray-300 dark:hover:bg-slate-700"
                        aria-label={closeLabel}
                        onclick={onclose}
                        disabled={busy}
                        data-testid="onboarding-coachmark-close"
                    >
                        <X size={18} />
                    </button>
                {/if}
            </div>
            {#if progressLabel}
                <p class="mb-1 text-xs font-semibold uppercase tracking-wide text-libre-green dark:text-emerald-300" data-testid="onboarding-coachmark-progress">
                    {progressLabel}
                </p>
            {/if}
            <h2 id={titleId} class="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {title}
            </h2>
            <p id={descriptionId} class="mt-2 text-sm leading-6 text-gray-600 dark:text-gray-300">
                {error ?? (guideState === 'waiting' ? busyLabel : description)}
            </p>
            {#if actionHint && guideState === 'anchored' && !error}
                <p class="mt-3 flex items-center gap-2 text-xs font-medium text-libre-green dark:text-emerald-300" data-testid="onboarding-coachmark-action-hint">
                    <MousePointer2 size={14} />
                    {actionHint}
                </p>
            {/if}

            {#if showBack || showNext}
                <div class="mt-5 flex items-center justify-between gap-3" data-testid="onboarding-coachmark-navigation">
                    <div>
                        {#if showBack}
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:opacity-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-700"
                                onclick={onback}
                                disabled={busy || backDisabled}
                                data-testid="onboarding-coachmark-back"
                            >
                                <ArrowLeft size={15} />
                                {backLabel}
                            </button>
                        {/if}
                    </div>
                    <div>
                        {#if showNext}
                            <button
                                type="button"
                                class="inline-flex items-center gap-1.5 rounded-lg bg-libre-green px-4 py-2 text-sm font-medium text-white hover:bg-libre-green/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green disabled:opacity-50"
                                onclick={onnext}
                                disabled={busy}
                                data-testid="onboarding-coachmark-next"
                            >
                                {nextLabel}
                                {#if showNextArrow}<ArrowRight size={15} />{/if}
                            </button>
                        {/if}
                    </div>
                </div>
            {/if}
        </div>
    </div>
{/if}
