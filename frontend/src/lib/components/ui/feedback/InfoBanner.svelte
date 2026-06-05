<!--
  InfoBanner — Reusable banner for info/warning/error/success messages.

  Consistent styling with dark mode. Supports slot content OR message prop.
  Optional dismiss button (X).

  Usage:
    <InfoBanner variant="warning">This is a warning!</InfoBanner>
    <InfoBanner variant="error" message={error} dismissible ondismiss={() => error = ''} />
    <InfoBanner variant="success" message="Done!" />
-->
<script lang="ts">
    import {AlertCircle, AlertTriangle, CheckCircle, Info, X} from 'lucide-svelte';
    import type {Snippet} from 'svelte';

    type Variant = 'warning' | 'info' | 'error' | 'success';

    interface Props {
        /** Banner variant — determines colors and default icon */
        variant?: Variant;
        /** Whether to show the default icon (true by default) */
        showIcon?: boolean;
        /** Text message (alternative to slot content) — banner hides when null/empty */
        message?: string | null;
        /** Show dismiss (X) button */
        dismissible?: boolean;
        /** Called when dismiss button is clicked */
        ondismiss?: () => void;
        /** Additional CSS classes for the outer container */
        class?: string;
        /** Content slot (used when message prop is not provided) */
        children?: Snippet;
    }

    let {variant = 'info', showIcon = true, message = undefined, dismissible = false, ondismiss, class: extraClass = '', children}: Props = $props();

    const variantStyles: Record<
        Variant,
        {
            container: string;
            icon: string;
        }
    > = {
        warning: {
            container: 'bg-amber-50 dark:bg-amber-900/10 border-amber-200 dark:border-amber-800/40 text-amber-700 dark:text-amber-200/60',
            icon: 'text-amber-500 dark:text-amber-500/50',
        },
        info: {
            container: 'bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800/40 text-blue-700 dark:text-blue-200/60',
            icon: 'text-blue-500 dark:text-blue-400/50',
        },
        error: {
            container: 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800/40 text-red-700 dark:text-red-200/60',
            icon: 'text-red-500 dark:text-red-400/50',
        },
        success: {
            container: 'bg-emerald-50 dark:bg-emerald-900/10 border-emerald-200 dark:border-emerald-800/40 text-emerald-700 dark:text-emerald-200/60',
            icon: 'text-emerald-500 dark:text-emerald-400/50',
        },
    };

    const defaultIcons: Record<Variant, typeof AlertTriangle> = {
        warning: AlertTriangle,
        info: Info,
        error: AlertCircle,
        success: CheckCircle,
    };

    /** When message prop is used, banner auto-hides if null/empty */
    let hasContent = $derived(message !== undefined ? !!message : true);
    let styles = $derived(variantStyles[variant]);
    let IconComponent = $derived(defaultIcons[variant]);
</script>

{#if hasContent}
    <div class="flex items-start gap-2 p-3 rounded-lg border text-xs {styles.container} {extraClass}" role={variant === 'error' ? 'alert' : 'status'}>
        {#if showIcon}
            <IconComponent size={16} class="{styles.icon} mt-0.5 shrink-0" />
        {/if}
        <div class="flex-1 min-w-0">
            {#if message}
                <span>{message}</span>
            {:else if children}
                {@render children()}
            {/if}
        </div>
        {#if dismissible && ondismiss}
            <button type="button" class="shrink-0 p-0.5 rounded opacity-60 hover:opacity-100 transition-opacity" onclick={ondismiss} aria-label="Dismiss">
                <X size={14} />
            </button>
        {/if}
    </div>
{/if}
