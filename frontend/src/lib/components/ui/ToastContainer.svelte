<!--
  ToastContainer — renders active toast notifications at top-center.
  Place once in the app layout. Toasts auto-dismiss with visual countdown bar.

  Usage (from any component):
    import { toasts } from '$lib/stores/toastStore.svelte';
    toasts.success('Done!');
    toasts.error('Failed', 10000);
-->
<script lang="ts">
    import {fly} from 'svelte/transition';
    import {toasts, type ToastVariant} from '$lib/stores/toastStore.svelte';
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
</script>

{#if toasts.items.length > 0}
    <div class="fixed top-4 left-1/2 -translate-x-1/2 z-[9999] flex flex-col gap-2 max-w-sm pointer-events-none">
        {#each toasts.items as toast (toast.id)}
            {@const Icon = variantIcons[toast.variant]}
            <div class="pointer-events-auto relative rounded-lg shadow-lg overflow-hidden {variantStyles[toast.variant]}" data-testid="toast-{toast.variant}" transition:fly={{y: -30, duration: 250}}>
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
