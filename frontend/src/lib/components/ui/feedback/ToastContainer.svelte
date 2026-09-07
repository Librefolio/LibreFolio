<!--
  ToastContainer — renders active toast notifications at top-center.
  Place once in the app layout. Toasts auto-dismiss with visual countdown bar.

  Usage (from any component):
    import { toasts } from '$lib/stores/app/toastStore.svelte';
    toasts.success('Done!');
    toasts.error('Failed', 10000);
-->
<script lang="ts">
    import {fly} from 'svelte/transition';
    import {toasts, type ToastVariant} from '$lib/stores/app/toastStore.svelte';
    import {AlertCircle, AlertTriangle, CheckCircle, Info, X} from 'lucide-svelte';

    const variantStyles: Record<ToastVariant, string> = {
        success: 'bg-emerald-600 text-white',
        error: 'bg-red-600 text-white',
        warning: 'bg-amber-500 text-white',
        info: 'bg-blue-500 text-white',
    };

    const variantIcons: Record<ToastVariant, typeof AlertTriangle> = {
        success: CheckCircle,
        error: AlertCircle,
        warning: AlertTriangle,
        info: Info,
    };

    /**
     * Swipe-to-dismiss.
     *
     * The ✕ is a 12px target in a corner — fine with a mouse, poor with a thumb. Dragging
     * the toast away is the gesture people already expect from a notification, so the
     * pointer handlers below add it for right, left and up. The ✕ stays exactly as it is:
     * it is the keyboard- and screen-reader-reachable path, and a gesture can never be that.
     *
     * Pointer events (not touch events) so the same code covers finger, pen and mouse.
     */
    const SWIPE_THRESHOLD_PX = 60;

    let drag = $state<{id: string; startX: number; startY: number; dx: number; dy: number} | null>(null);

    function onPointerDown(event: PointerEvent, id: string) {
        // Ignore secondary buttons and anything starting on the dismiss button.
        if (event.button !== 0) return;
        if ((event.target as HTMLElement | null)?.closest('button')) return;
        drag = {id, startX: event.clientX, startY: event.clientY, dx: 0, dy: 0};
        (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
    }

    function onPointerMove(event: PointerEvent, id: string) {
        if (!drag || drag.id !== id) return;
        drag = {...drag, dx: event.clientX - drag.startX, dy: event.clientY - drag.startY};
    }

    function onPointerUp(event: PointerEvent, id: string) {
        if (!drag || drag.id !== id) return;
        const {dx, dy} = drag;
        drag = null;
        (event.currentTarget as HTMLElement).releasePointerCapture?.(event.pointerId);
        // Up counts only when it dominates: a mostly-horizontal drag should not be read
        // as "up" just because it drifted.
        const dismissed = Math.abs(dx) >= SWIPE_THRESHOLD_PX || (-dy >= SWIPE_THRESHOLD_PX && -dy > Math.abs(dx));
        if (dismissed) toasts.dismiss(id);
    }

    function dragStyle(id: string): string {
        if (!drag || drag.id !== id) return '';
        const {dx, dy} = drag;
        // Follow the finger horizontally, but only upwards vertically — dragging a toast
        // down over the page it belongs to is not a dismissal.
        const ty = Math.min(0, dy);
        const travel = Math.max(Math.abs(dx), -ty);
        const opacity = Math.max(0.35, 1 - travel / (SWIPE_THRESHOLD_PX * 2.5));
        return `transform: translate(${dx}px, ${ty}px); opacity: ${opacity}; transition: none;`;
    }
</script>

{#if toasts.items.length > 0}
    <div class="fixed top-4 left-1/2 -translate-x-1/2 z-[9999] flex flex-col gap-2 max-w-sm pointer-events-none">
        {#each toasts.items as toast (toast.id)}
            {@const Icon = variantIcons[toast.variant]}
            <div
                class="pointer-events-auto relative rounded-lg shadow-lg overflow-hidden touch-pan-y select-none {variantStyles[toast.variant]}"
                data-testid="toast-{toast.variant}"
                onpointercancel={(e) => onPointerUp(e, toast.id)}
                onpointerdown={(e) => onPointerDown(e, toast.id)}
                onpointermove={(e) => onPointerMove(e, toast.id)}
                onpointerup={(e) => onPointerUp(e, toast.id)}
                style={dragStyle(toast.id)}
                transition:fly={{y: -30, duration: 250}}
            >
                <div class="flex flex-col items-center gap-1 px-4 py-3 text-sm leading-snug text-center">
                    <div class="flex items-start gap-1.5">
                        <Icon size={15} class="shrink-0 mt-0.5" />
                        <span class="flex-1 whitespace-pre-line text-left">{@html toast.message}</span>
                    </div>
                    <button class="shrink-0 p-0.5 rounded hover:bg-white/20 transition-colors absolute top-1.5 right-1.5" onclick={() => toasts.dismiss(toast.id)} aria-label="Dismiss">
                        <X size={12} />
                    </button>
                </div>
                {#if toast.duration > 0}
                    <div class="h-0.5 w-full bg-white/15">
                        <div class="h-full bg-white/40 toast-countdown-bar" style="animation-duration: {toast.duration}ms"></div>
                    </div>
                {/if}
            </div>
        {/each}
    </div>
{/if}

<style>
    .toast-countdown-bar {
        width: 100%;
        animation-name: shrink;
        animation-timing-function: linear;
        animation-fill-mode: forwards;
    }

    @keyframes shrink {
        from {
            width: 100%;
        }
        to {
            width: 0%;
        }
    }
</style>
