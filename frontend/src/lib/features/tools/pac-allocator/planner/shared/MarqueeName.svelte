<!--
  R11.6: a name inside a table cell. When it does not fit, it scrolls by itself (the project
  marquee, `scrollOnOverflow`) instead of being cut; the full text is also in the tooltip.
-->
<script lang="ts">
    import {scrollOnOverflow} from '$lib/actions/scrollOnOverflow';
    import {overflowScrollTextClass} from '$lib/utils/overflowScroll';

    interface Props {
        text: string;
    }

    let {text}: Props = $props();
</script>

<span use:scrollOnOverflow class="{overflowScrollTextClass} font-medium text-lf-primary" title={text}>{text}</span>
