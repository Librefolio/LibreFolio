<!--
  EventReconciliationRowButton.svelte — the action of one row in «Relink events» (plan 77, SEL-C, A4).

  A light button with the same icon and word as the bar's action (Q-SEL-3): «Link», «Create event», «Choose event». On a
  phone only the icon shows, and the name stays the word. Drawn by `DataTable` as a `custom` cell, in the column pinned
  on the right.
  Uses Svelte 5 runes.
-->
<script lang="ts">
    import type {Component} from 'svelte';

    interface Props {
        icon: Component<{size?: number; class?: string}>;
        label: string;
        testId: string;
        disabled?: boolean;
        onClick: () => void;
    }

    let {icon: Icon, label, testId, disabled = false, onClick}: Props = $props();
</script>

<button
    type="button"
    class="row-btn inline-flex items-center gap-1.5 rounded-md border border-lf-input bg-lf-card text-lf-primary hover:bg-lf-hover text-xs font-medium whitespace-nowrap transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-lf-focus"
    aria-label={label}
    data-testid={testId}
    {disabled}
    onclick={(event) => {
        event.stopPropagation();
        onClick();
    }}
>
    <Icon size={14} />
    <span class="lbl">{label}</span>
</button>

<style>
    .row-btn {
        height: 26px;
        padding: 0 0.5rem;
    }

    @media (max-width: 639px) {
        .row-btn {
            padding: 0 0.375rem;
        }

        .lbl {
            display: none;
        }
    }
</style>
