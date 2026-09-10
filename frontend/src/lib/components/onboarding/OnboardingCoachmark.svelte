<script lang="ts">
    import {browser} from '$app/environment';

    interface Props {
        open?: boolean;
        anchor?: HTMLElement | null;
        stepId: string;
        title: string;
        description: string;
        progressLabel?: string;
        backLabel?: string;
        nextLabel?: string;
        skipLabel?: string;
        pauseLabel?: string;
        busyLabel?: string;
        error?: string | null;
        showBack?: boolean;
        showNext?: boolean;
        showSkip?: boolean;
        showPause?: boolean;
        showBackdrop?: boolean;
        focusOnOpen?: boolean;
        onback?: () => void;
        onnext?: () => void;
        onskip?: () => void;
        onpause?: () => void;
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
        progressLabel = '',
        backLabel = 'Back',
        nextLabel = 'Next',
        skipLabel = 'Skip',
        pauseLabel = 'Pause',
        busyLabel = 'Waiting for this area...',
        error = null,
        showBack = true,
        showNext = true,
        showSkip = true,
        showPause = false,
        showBackdrop = false,
        focusOnOpen = true,
        onback,
        onnext,
        onskip,
        onpause,
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

    function pauseFromEscape(event: KeyboardEvent) {
        if (!open || event.key !== 'Escape') return;
        event.stopPropagation();
        onpause?.();
    }

    $effect(() => {
        if (!browser || !open) {
            anchorRect = null;
            return;
        }
        refreshPosition();
        const observer = anchor && typeof ResizeObserver !== 'undefined' ? new ResizeObserver(refreshPosition) : null;
        if (anchor) observer?.observe(anchor);
        window.addEventListener('resize', refreshPosition);
        window.addEventListener('scroll', refreshPosition, true);
        return () => {
            observer?.disconnect();
            window.removeEventListener('resize', refreshPosition);
            window.removeEventListener('scroll', refreshPosition, true);
        };
    });

    $effect(() => {
        if (!browser || !open || !anchor) return;
        const previousDescription = anchor.getAttribute('aria-describedby');
        anchor.setAttribute('aria-describedby', descriptionId);
        const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        anchor.scrollIntoView({
            block: 'center',
            inline: 'nearest',
            behavior: reduceMotion ? 'auto' : 'smooth',
        });
        return () => {
            if (anchor.getAttribute('aria-describedby') === descriptionId) {
                if (previousDescription) {
                    anchor.setAttribute('aria-describedby', previousDescription);
                } else {
                    anchor.removeAttribute('aria-describedby');
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

<svelte:window onkeydown={pauseFromEscape} />

{#if open}
    <div class="pointer-events-none fixed inset-0" style="z-index: 80;" data-testid="onboarding-coachmark" data-step-id={stepId} data-guide-state={guideState}>
        {#if showBackdrop}
            <div class="absolute inset-0 bg-black/35" data-testid="onboarding-coachmark-backdrop"></div>
        {/if}

        {#if anchorRect}
            <div class="absolute rounded-xl border-2 border-libre-green bg-libre-green/10 shadow-[0_0_0_4px_rgba(26,64,49,0.18)] motion-reduce:transition-none" style={highlightStyle} data-testid="onboarding-coachmark-highlight"></div>
        {/if}

        <div
            bind:this={panel}
            class="pointer-events-auto fixed left-4 right-4 rounded-2xl border border-gray-200 bg-white p-4 shadow-2xl outline-none dark:border-slate-700 dark:bg-slate-800 sm:left-auto sm:right-auto"
            class:bottom-sheet={mobile}
            style={mobile ? 'bottom:max(1rem, env(safe-area-inset-bottom));' : panelStyle}
            role="dialog"
            aria-modal="false"
            aria-labelledby={titleId}
            aria-describedby={descriptionId}
            aria-live="polite"
            tabindex="-1"
            data-testid="onboarding-coachmark-panel"
        >
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

            <div class="mt-4 flex flex-wrap items-center justify-end gap-2">
                {#if showSkip}
                    <button
                        type="button"
                        class="mr-auto rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green dark:text-gray-300 dark:hover:bg-slate-700"
                        onclick={onskip}
                        data-testid="onboarding-coachmark-skip"
                    >
                        {skipLabel}
                    </button>
                {/if}
                {#if showPause}
                    <button
                        type="button"
                        class="rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green dark:text-gray-300 dark:hover:bg-slate-700"
                        onclick={onpause}
                        data-testid="onboarding-coachmark-pause"
                    >
                        {pauseLabel}
                    </button>
                {/if}
                {#if showBack}
                    <button
                        type="button"
                        class="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-700"
                        onclick={onback}
                        data-testid="onboarding-coachmark-back"
                    >
                        {backLabel}
                    </button>
                {/if}
                {#if showNext}
                    <button type="button" class="rounded-lg bg-libre-green px-4 py-2 text-sm font-medium text-white hover:bg-libre-green/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-libre-green" onclick={onnext} data-testid="onboarding-coachmark-next">
                        {nextLabel}
                    </button>
                {/if}
            </div>
        </div>
    </div>
{/if}
