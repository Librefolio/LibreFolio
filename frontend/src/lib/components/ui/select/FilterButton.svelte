<!--
  FilterButton — the button that opens a filter: an icon, a label, a chevron, and how many choices are on.

  Taken out of CheckMenu so that every filter button of the app looks and answers the same. With no choice on it is a
  quiet bordered button; with one or more (`count > 0`) it takes the info tint, and a small round badge shows the number.
  An empty choice means "every value", so a count of 0 is the neutral look.

  Test ids: `testId` on the button. It carries `aria-expanded` (`expanded`), and takes any other attribute
  (`aria-controls`, `aria-haspopup`, `data-*`…) through to the `<button>`.
-->
<script lang="ts">
    import {ChevronDown} from 'lucide-svelte';
    import type {ComponentType} from 'svelte';
    import type {HTMLButtonAttributes} from 'svelte/elements';

    interface Props extends Omit<HTMLButtonAttributes, 'class' | 'type'> {
        label: string;
        /** A lucide icon, typed as `TabBar` types its own: lucide-svelte still ships class components. */
        icon: ComponentType;
        /** How many choices are on. 0 = the neutral look. */
        count?: number;
        /** The popup it opens is open: turns the chevron and sets `aria-expanded`. */
        expanded?: boolean;
        /** The chevron at the right end (default). A button that opens a side panel may drop it. */
        chevron?: boolean;
        testId?: string;
        /** Extra classes: a layout concern (a margin, a width), never a colour. */
        class?: string;
    }

    let {label, icon: Icon, count = 0, expanded = false, chevron = true, testId, class: extra = '', ...rest}: Props = $props();

    let active = $derived(count > 0);
</script>

<button
    {...rest}
    type="button"
    class="inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors {active ? 'border-lf-info-line bg-lf-info-soft text-lf-info-on-soft' : 'border-lf-subtle text-lf-secondary hover:bg-lf-hover'} {extra}"
    aria-expanded={expanded}
    data-testid={testId}
>
    <Icon size={13} />
    {label}
    {#if active}
        <span class="rounded-full bg-lf-info px-1.5 text-[10px] font-semibold leading-4 text-lf-on-status">{count}</span>
    {/if}
    {#if chevron}
        <ChevronDown size={12} class="transition-transform {expanded ? 'rotate-180' : ''}" />
    {/if}
</button>
