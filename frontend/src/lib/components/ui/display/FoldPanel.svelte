<!--
  A panel that starts closed: a title line with a chevron, and a body that opens under it.

  Used for the settings an administrator rarely needs (the space limit under the Files page's space bar, the automatic
  clean-up of the backups). It is a native `<details>`: the keyboard and assistive technology work as they should, and
  the body stays mounted while closed, so what was typed in it is kept.

  Published state: `data-open` (`true|false`) on the root, which carries `testId`.
-->
<script lang="ts">
    import type {Snippet} from 'svelte';
    import {ChevronRight} from 'lucide-svelte';

    interface Props {
        /** The title line, already translated. */
        title: string;
        testId?: string;
        /** Open when mounted (default: closed). */
        open?: boolean;
        children: Snippet;
    }

    let {title, testId, open = $bindable(false), children}: Props = $props();
</script>

<details class="group rounded-lg border border-lf-subtle" data-testid={testId} data-open={open ? 'true' : 'false'} bind:open>
    <summary
        class="flex cursor-pointer list-none items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-lf-secondary hover:bg-lf-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lf-focus [&::-webkit-details-marker]:hidden"
        data-testid={testId ? `${testId}-toggle` : undefined}
    >
        <ChevronRight class="shrink-0 transition-transform group-open:rotate-90" size={16} aria-hidden="true" />
        {title}
    </summary>
    <div class="space-y-3 border-t border-lf-subtle px-3 py-3">
        {@render children()}
    </div>
</details>
