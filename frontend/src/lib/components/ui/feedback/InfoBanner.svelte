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
            /** The dismiss button's hover, a step down the family (designer, round 3: no opacity on it). */
            dismiss: string;
        }
    > = {
        warning: {
            container: 'bg-lf-warning-soft border-lf-warning-line text-lf-warning-on-soft',
            icon: 'text-lf-warning',
            dismiss: 'hover:bg-lf-warning-line',
        },
        info: {
            container: 'bg-lf-info-soft border-lf-info-line text-lf-info-on-soft',
            icon: 'text-lf-info',
            dismiss: 'hover:bg-lf-info-line',
        },
        error: {
            container: 'bg-lf-danger-soft border-lf-danger-line text-lf-danger-on-soft',
            icon: 'text-lf-danger',
            dismiss: 'hover:bg-lf-danger-line',
        },
        success: {
            container: 'bg-lf-success-soft border-lf-success-line text-lf-success-on-soft',
            icon: 'text-lf-success',
            dismiss: 'hover:bg-lf-success-line',
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
    <div class="flex items-start gap-2 p-3 rounded-lg border text-xs {styles.container} {extraClass}" data-testid="info-banner-{variant}" role={variant === 'error' ? 'alert' : 'status'}>
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
            <button type="button" class="shrink-0 p-0.5 rounded transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-lf-focus {styles.dismiss}" onclick={ondismiss} aria-label="Dismiss">
                <X size={14} />
            </button>
        {/if}
    </div>
{/if}
