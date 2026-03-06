<!--
  InfoBanner — Reusable banner component for info/warning/error/success messages.

  Provides consistent styling across the app with proper dark mode support.
  Accepts a variant and optional icon override.

  Usage:
    <InfoBanner variant="warning">This is a warning!</InfoBanner>
    <InfoBanner variant="info">Some helpful information.</InfoBanner>
    <InfoBanner variant="error">Something went wrong.</InfoBanner>
    <InfoBanner variant="success">Operation completed!</InfoBanner>
-->
<script lang="ts">
    import {AlertTriangle, Info, AlertCircle, CheckCircle} from 'lucide-svelte';
    import type {Snippet} from 'svelte';

    type Variant = 'warning' | 'info' | 'error' | 'success';

    interface Props {
        /** Banner variant — determines colors and default icon */
        variant?: Variant;
        /** Whether to show the default icon (true by default) */
        showIcon?: boolean;
        /** Additional CSS classes for the outer container */
        class?: string;
        /** Content slot */
        children: Snippet;
    }

    let {
        variant = 'info',
        showIcon = true,
        class: extraClass = '',
        children,
    }: Props = $props();

    const variantStyles: Record<Variant, {
        container: string;
        icon: string;
    }> = {
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

    let styles = $derived(variantStyles[variant]);
    let IconComponent = $derived(defaultIcons[variant]);
</script>

<div class="flex items-start gap-2 p-3 rounded-lg border text-xs {styles.container} {extraClass}">
    {#if showIcon}
        <IconComponent size={16} class="{styles.icon} mt-0.5 shrink-0" />
    {/if}
    <div class="flex-1 min-w-0">
        {@render children()}
    </div>
</div>

