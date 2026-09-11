<script lang="ts">
    import {browser} from '$app/environment';
    import {ArrowLeft, ArrowRight, LogOut, MousePointer2, X} from 'lucide-svelte';

    interface Props {
        open?: boolean;
        anchor?: HTMLElement | null;
        stepId: string;
        title: string;
        description: string;
        actionHint?: string;
        presentation?: 'spotlight' | 'pointer';
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
        showSkip?: boolean;
        showClose?: boolean;
        showBackdrop?: boolean;
        focusOnOpen?: boolean;
        busy?: boolean;
        onback?: () => void;
        onnext?: () => void;
        onskip?: () => void;
        onclose?: () => void;
    }

    interface AnchorRect {
        left: number;
        top: number;
        right: number;
        bottom: number;
        width: number;
        height: number;
    }

    let {
        open = false,
        anchor = null,
        stepId,
        title,
        description,
        actionHint = '',
        presentation = 'pointer',
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
        showSkip = true,
        showClose = true,
        showBackdrop = false,
        focusOnOpen = true,
        busy = false,
        onback,
        onnext,
        onskip,
        onclose,
    }: Props = $props();

    let panel: HTMLElement | null = $state(null);
    let anchorRect: AnchorRect | null = $state(null);
    let viewportWidth = $state(0);
    let viewportHeight = $state(0);
    let mobile = $state(false);
    let focusedStepId = '';

    const titleId = 'onboarding-coachmark-title';
    const descriptionId = 'onboarding-coachmark-description';
    let guideState = $derived(error ? 'error' : anchorRect ? 'anchored' : 'waiting');
    let highlightStyle = $derived.by(() => {
        const rect = anchorRect;
        return rect ? `left:${Math.max(rect.left - 6, 4)}px;top:${Math.max(rect.top - 6, 4)}px;width:${Math.max(rect.width + 12, 12)}px;height:${Math.max(rect.height + 12, 12)}px;` : '';
    });
    let pointerStyle = $derived.by(() => {
        const rect = anchorRect;
        if (!rect) return '';
        const left = Math.min(Math.max(rect.right + 6, 8), Math.max(viewportWidth - 34, 8));
        const top = Math.min(Math.max(rect.top - 14, 8), Math.max(viewportHeight - 34, 8));
        return `left:${left}px;top:${top}px;`;
    });
    let panelStyle = $derived.by(() => {
        if (mobile) return '';
        if (!anchorRect || viewportWidth === 0 || viewportHeight === 0) {
            return 'left:50%;top:50%;width:min(360px,calc(100vw - 2rem));transform:translate(-50%,-50%);';
        }
        const panelWidth = Math.min(360, viewportWidth - 32);
        const estimatedHeight = 220;
        const left = Math.min(Math.max(anchorRect.left, 16), Math.max(viewportWidth - panelWidth - 16, 16));
        const below = anchorRect.bottom + 14;
        const top = below + estimatedHeight <= viewportHeight ? below : Math.max(anchorRect.top - estimatedHeight - 14, 16);
        return `left:${left}px;top:${top}px;width:${panelWidth}px;`;
    });

    function refreshPosition() {
        if (!browser) return;
        viewportWidth = window.innerWidth;
        viewportHeight = window.innerHeight;
        mobile = window.matchMedia('(max-width: 640px)').matches;
        if (!anchor?.isConnected) {
            anchorRect = null;
            return;
        }
        const rect = anchor.getBoundingClientRect();
        anchorRect = {
            left: rect.left,
            top: rect.top,
            right: rect.right,
            bottom: rect.bottom,
            width: rect.width,
            height: rect.height,
        };
    }

    function closeFromEscape(event: KeyboardEvent) {
        if (!open || busy || event.key !== 'Escape') return;
        event.stopPropagation();
        onclose?.();
    }

    $effect(() => {
        if (!browser || !open) {
            anchorRect = null;
            return;
        }
        refreshPosition();
        const observer = anchor && typeof ResizeObserver !== 'undefined' ? new ResizeObserver(refreshPosition) : null;
        if (anchor) observer?.observe(anchor);
        const motionRoot = anchor?.closest('nav') ?? anchor;
        let motionFrame: number | null = null;
        const followMotion = () => {
            refreshPosition();
            const animations = typeof motionRoot?.getAnimations === 'function' ? motionRoot.getAnimations({subtree: true}) : [];
            if (animations.some((animation) => animation.playState === 'running')) {
                motionFrame = requestAnimationFrame(followMotion);
            } else {
                motionFrame = null;
            }
        };
        const startFollowingMotion = () => {
            if (motionFrame == null) motionFrame = requestAnimationFrame(followMotion);
        };
        const finishFollowingMotion = () => {
            if (motionFrame != null) cancelAnimationFrame(motionFrame);
            motionFrame = null;
            refreshPosition();
        };
        startFollowingMotion();
        motionRoot?.addEventListener('transitionrun', startFollowingMotion);
        motionRoot?.addEventListener('transitionend', finishFollowingMotion);
        motionRoot?.addEventListener('transitioncancel', finishFollowingMotion);
        window.addEventListener('resize', refreshPosition);
        window.addEventListener('scroll', refreshPosition, true);
        return () => {
            observer?.disconnect();
            if (motionFrame != null) cancelAnimationFrame(motionFrame);
            motionRoot?.removeEventListener('transitionrun', startFollowingMotion);
            motionRoot?.removeEventListener('transitionend', finishFollowingMotion);
            motionRoot?.removeEventListener('transitioncancel', finishFollowingMotion);
            window.removeEventListener('resize', refreshPosition);
            window.removeEventListener('scroll', refreshPosition, true);
        };
    });

    $effect(() => {
        if (!browser || !open || !anchor) return;
        const linkedAnchor = anchor;
        const previousDescription = linkedAnchor.getAttribute('aria-describedby');
        linkedAnchor.setAttribute('aria-describedby', descriptionId);
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        linkedAnchor.scrollIntoView({
            block: 'center',
            inline: 'nearest',
            behavior: reduceMotion ? 'auto' : 'smooth',
        });
        return () => {
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
        if (!browser || !focusOnOpen || !panel || focusedStepId === stepId) return;
        focusedStepId = stepId;
        const frame = requestAnimationFrame(() => panel?.focus({preventScroll: true}));
        return () => cancelAnimationFrame(frame);
    });
</script>

<svelte:window onkeydown={closeFromEscape} />

{#if open}
    <div class="pointer-events-none fixed inset-0" style="z-index: 80;" data-testid="onboarding-coachmark" data-step-id={stepId} data-guide-state={guideState}>
        {#if presentation === 'spotlight' || showBackdrop}
            {#if anchorRect}
                <div class="pointer-events-auto fixed left-0 right-0 top-0 bg-black/45" style={`height:${Math.max(anchorRect.top - 8, 0)}px;`} data-testid="onboarding-spotlight-top"></div>
                <div class="pointer-events-auto fixed bottom-0 left-0 right-0 bg-black/45" style={`top:${Math.min(anchorRect.bottom + 8, viewportHeight)}px;`} data-testid="onboarding-spotlight-bottom"></div>
                <div class="pointer-events-auto fixed left-0 bg-black/45" style={`top:${Math.max(anchorRect.top - 8, 0)}px;width:${Math.max(anchorRect.left - 8, 0)}px;height:${Math.max(anchorRect.height + 16, 0)}px;`} data-testid="onboarding-spotlight-left"></div>
                <div class="pointer-events-auto fixed right-0 bg-black/45" style={`top:${Math.max(anchorRect.top - 8, 0)}px;left:${Math.min(anchorRect.right + 8, viewportWidth)}px;height:${Math.max(anchorRect.height + 16, 0)}px;`} data-testid="onboarding-spotlight-right"></div>
            {:else}
                <div class="pointer-events-auto absolute inset-0 bg-black/45" data-testid="onboarding-coachmark-backdrop"></div>
            {/if}
        {/if}

        {#if anchorRect && presentation === 'spotlight'}
            <div class="absolute animate-pulse rounded-xl border-4 border-emerald-400 bg-transparent shadow-[0_0_0_5px_rgba(52,211,153,0.4),0_0_28px_rgba(52,211,153,0.95)] motion-reduce:animate-none" style={highlightStyle} data-testid="onboarding-coachmark-highlight"></div>
        {/if}

        {#if anchorRect}
            <div class="pointer-events-none fixed z-[82] animate-bounce rounded-full bg-white p-1.5 text-libre-green shadow-lg motion-reduce:animate-none dark:bg-slate-800 dark:text-emerald-300" style={pointerStyle} aria-hidden="true" data-testid="onboarding-coachmark-pointer">
                <MousePointer2 size={18} />
            </div>
        {/if}

        <div
            bind:this={panel}
            class="pointer-events-auto fixed left-4 right-4 rounded-2xl border border-gray-200 bg-white p-4 shadow-2xl outline-none dark:border-slate-700 dark:bg-slate-800 sm:left-auto sm:right-auto"
            class:bottom-sheet={mobile && presentation === 'spotlight'}
            style={mobile ? (presentation === 'spotlight' ? 'bottom:max(1rem, env(safe-area-inset-bottom));' : 'top:max(1rem, env(safe-area-inset-top));') : panelStyle}
            role="dialog"
            aria-modal="false"
            aria-labelledby={titleId}
            aria-describedby={descriptionId}
            aria-live="polite"
            aria-busy={busy}
            tabindex="-1"
            data-testid="onboarding-coachmark-panel"
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
                                <ArrowRight size={15} />
                            </button>
                        {/if}
                    </div>
                </div>
            {/if}
        </div>
    </div>
{/if}
