<!--
  EmphasisText — a catalogue text with its line breaks (`\n`) and its words that matter (`**…**`), as text nodes: one
  block per line, `<strong>` for the marked words (lot E4 of project 71). It renders inside the caller's element, which
  keeps the size, the colour, the alignment, `aria-live` and the test id.
-->
<script lang="ts">
    import {emphasisLines} from './emphasisText';

    interface Props {
        text: string;
    }

    let {text}: Props = $props();

    const lines = $derived(emphasisLines(text));
</script>

{#each lines as line, index (index)}<span class="block" class:mt-1.5={index > 0} data-line={index}
        >{#each line as piece, at (at)}{#if piece.strong}<strong class="font-semibold">{piece.text}</strong>{:else}{piece.text}{/if}{/each}</span
    >{/each}
