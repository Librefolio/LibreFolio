<!--
  TweenedValue — Smoothly animates between numeric values.

  Renders a formatted number that tweens from old → new value using
  svelte/motion's tweened store. Never disappears or "pops" — the number
  smoothly transitions between states.

  Props:
  - value: The target numeric value
  - format: Formatter function (value → display string). Default: 2 decimal places.
  - duration: Animation duration in ms (default: 600)
  - loading: When true, shows a skeleton pulse instead of the value
  - class: Additional CSS classes for the value element

  Usage:
    <TweenedValue value={navAmount} format={(v) => formatMoney('EUR', v)} />
    <TweenedValue value={percentValue} format={(v) => `${v.toFixed(2)}%`} duration={800} />

  Pattern: Svelte 5 Runes, no popup effect.
-->
<script lang="ts">
    import {tweened} from 'svelte/motion';
    import {cubicOut} from 'svelte/easing';

    interface Props {
        /** Target numeric value to animate to */
        value: number;
        /** Format function: converts tweened number to display string */
        format?: (value: number) => string;
        /** Animation duration in milliseconds */
        duration?: number;
        /** Show skeleton placeholder instead of value */
        loading?: boolean;
        /** Additional CSS classes */
        class?: string;
    }

    let {value, format = (v: number) => v.toFixed(2), duration = 900, loading = false, class: className = ''}: Props = $props();

    const displayValue = tweened(0, {duration: 900, easing: cubicOut});

    $effect(() => {
        displayValue.set(value, {duration});
    });
</script>

{#if loading}
    <span class="inline-block h-6 w-20 bg-gray-200 dark:bg-slate-700 rounded animate-pulse align-middle"></span>
{:else}
    <span class={className}>{format($displayValue)}</span>
{/if}
