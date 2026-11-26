<!--
  LinkBadge — a link drawn as a badge: a thin edge in the link colour, the text in it, a tint under the pointer. It leads
  from a summary to the view behind it: the asset page's header to that asset's transactions, the Dashboard's allocation
  card to its Allocation tab.

  With `href` it is an anchor, otherwise a button that calls `onclick`. The content (an icon, a text, a count) is the
  caller's.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';

    interface Props {
        /** Where it leads: an anchor. Without it, a button. */
        href?: string;
        onclick?: (event: MouseEvent) => void;
        testId?: string;
        children: Snippet;
    }

    let {href, onclick, testId, children}: Props = $props();
</script>

<svelte:element
    this={href ? 'a' : 'button'}
    {href}
    type={href ? undefined : 'button'}
    role={href ? 'link' : 'button'}
    {onclick}
    class="inline-flex shrink-0 cursor-pointer items-center gap-1 whitespace-nowrap rounded-full border border-lf-focus px-2 py-0.5 text-xs font-medium text-lf-link hover:bg-lf-selected focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus"
    data-testid={testId}
>
    {@render children()}
</svelte:element>
