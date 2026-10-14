<!--
  The small «?» next to a label: its explanation opens in a tooltip on hover or focus, and the
  whole text is also in the accessible name, so a screen reader does not need the tooltip.
  With `math`, the tooltip typesets the inline LaTeX ($…$) and keeps the line breaks; consecutive
  lines that start with «• » become a bulleted list. `spoken` then gives the same explanation in
  words for the accessible name.
-->
<script lang="ts">
    import {CircleHelp} from 'lucide-svelte';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {HELP_BUTTON} from '../ui';
    import {tipHtml} from './tipHtml';

    interface Props {
        label: string;
        help: string;
        math?: boolean;
        spoken?: string;
        testid?: string;
    }

    let {label, help, math = false, spoken, testid}: Props = $props();

    const html = $derived(math ? tipHtml(help) : '');
</script>

<Tooltip text={help} {html} {math} position="top" maxWidth="320px" interactiveChild>
    <button type="button" aria-label="{label}: {spoken ?? help}" class={HELP_BUTTON} data-testid={testid}><CircleHelp size={13} aria-hidden="true" /></button>
</Tooltip>
