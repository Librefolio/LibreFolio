<!--
  A panel that starts closed: a title line with a chevron, and a body that opens under it.

  Used for the settings an administrator rarely needs (the space limit under the Files page's space bar, the automatic
  clean-up of the backups). It is a native `<details>`: the keyboard and assistive technology work as they should, and
  the body stays mounted while closed, so what was typed in it is kept.

  An optional `count` sits at the right end of the title line, small and muted: how many choices inside are on («1 of 6»),
  readable without opening the panel.

  An optional `control` (a switch for everything inside) sits at the right end of the title line too, after the count. It is
  beside the line and not inside it: a control inside a `<summary>` is not reachable on its own, and a folded `<details>`
  hides everything else it holds.

  Published state: `data-open` (`true|false`) on the root, which carries `testId`; the count, when given, is
  `{testId}-count`.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import {ChevronRight} from 'lucide-svelte';

    interface Props {
        /** The title line, already translated. */
        title: string;
        /** A short text at the right end of the title line, already translated («1 of 6»). Nothing is drawn when empty. */
        count?: string;
        testId?: string;
        /** Open when mounted (default: closed). */
        open?: boolean;
        /** A control at the right end of the title line, outside it. */
        control?: Snippet;
        children: Snippet;
    }

    let {title, count, testId, open = $bindable(false), control, children}: Props = $props();
</script>

{#snippet fold()}
    <details class="group rounded-lg border border-lf-subtle" data-testid={testId} data-open={open ? 'true' : 'false'} bind:open>
        <summary
            class="flex cursor-pointer list-none items-center gap-2 rounded-lg py-2 pl-3 text-sm font-medium text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus [&::-webkit-details-marker]:hidden {control
                ? 'pr-[4.5rem]'
                : 'pr-3'}"
            data-testid={testId ? `${testId}-toggle` : undefined}
        >
            <ChevronRight class="shrink-0 transition-transform group-open:rotate-90" size={16} aria-hidden="true" />
            {title}
            {#if count}
                <span class="ml-auto whitespace-nowrap text-xs font-normal tabular-nums text-lf-muted" data-testid={testId ? `${testId}-count` : undefined}>{count}</span>
            {/if}
        </summary>
        <div class="space-y-3 border-t border-lf-subtle px-3 py-3">
            {@render children()}
        </div>
    </details>
{/snippet}

{#if control}
    <div class="relative">
        {@render fold()}
        <div class="absolute right-3 top-1.5 flex h-6 items-center">{@render control()}</div>
    </div>
{:else}
    {@render fold()}
{/if}
