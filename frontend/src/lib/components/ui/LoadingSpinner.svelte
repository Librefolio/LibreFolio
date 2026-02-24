<!--
  LoadingSpinner - Reusable loading indicator

  Displays a centered loading text with optional spinner animation.
  Used across tabs, pages, and modals for consistent loading state.
-->
<script lang="ts">
    import {t} from '$lib/i18n';

    /** Custom loading text (defaults to i18n 'common.loading') */
    export let text: string = '';
    /** Vertical padding size */
    export let size: 'sm' | 'md' | 'lg' = 'md';
    /** Additional CSS class */
    export let className: string = '';
</script>

<div class="loading-spinner {size} {className}" role="status" aria-live="polite">
    <div class="spinner"></div>
    <span>{text || $t('common.loading') || 'Loading...'}</span>
</div>

<style>
    .loading-spinner {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        color: #6b7280;
        font-size: 0.875rem;
    }

    :global(.dark) .loading-spinner { color: #9ca3af; }

    .loading-spinner.sm { padding: 1rem 0; }
    .loading-spinner.md { padding: 2rem 0; }
    .loading-spinner.lg { padding: 3rem 0; }

    .spinner {
        width: 24px;
        height: 24px;
        border: 3px solid #e5e7eb;
        border-top-color: #1a4031;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }

    :global(.dark) .spinner {
        border-color: #374151;
        border-top-color: #10b981;
    }

    @keyframes spin {
        to { transform: rotate(360deg); }
    }
</style>

