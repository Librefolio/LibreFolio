<!--
  ProfileHistoryClock — the clock that opens a voice's «Storia del dato» (plan 68, E6/E6b2): the same small button on a
  key figure card and beside the titles of the countries, the sectors and «Descrizione». Its name says which voice
  («Storia del dato: …»), for the screen reader and as the hint.

  Pattern: Svelte 5 Runes, colour roles only.
-->
<script lang="ts">
    import {History} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';

    interface Props {
        /** The voice whose history opens. */
        voiceKey: string;
        testId: string;
        onhistory: (key: string) => void;
    }

    let {voiceKey, testId, onhistory}: Props = $props();

    const name = $derived($t('assets.profile.tab.history', {values: {voice: $t(`assets.profile.voices.${voiceKey}`)}}));
</script>

<button type="button" class="shrink-0 rounded text-lf-muted hover:text-lf-primary focus-visible:outline-2 focus-visible:outline-lf-focus" aria-label={name} title={name} data-testid={testId} onclick={() => onhistory(voiceKey)}>
    <History size={15} />
</button>
