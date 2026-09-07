<!--
  TooltipProbe — test-only stand-in for Tooltip.svelte (Vitest + jsdom).

  The real Tooltip positions its floating panel with getBoundingClientRect —
  all zeros in jsdom, where a "top" tooltip provably flips to "bottom" — so the
  position a *caller asked for* is unobservable through the real component
  here. What IS observable is the prop as it arrives: this stub publishes it
  as `data-position`, letting a spec assert which side of a trigger a caller
  requested (the F10 contract: DataTable column-header tooltips open upward).

  Lives under `src/__tests__/`, excluded from coverage like every harness.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';

    interface Props {
        text?: string;
        html?: string;
        math?: boolean;
        position?: 'top' | 'bottom' | 'left' | 'right';
        maxWidth?: string;
        wrapperClass?: string;
        interactiveChild?: boolean;
        children?: Snippet;
    }

    let {position = 'top', children}: Props = $props();
</script>

<span data-testid="tooltip-probe" data-position={position}>{@render children?.()}</span>
