<!--
  ProfileChangeBefore — the «Prima» cell of a change of the asset profile (87, A3): the value before, or a dash. The text
  wraps: it is the row's content.
-->
<script lang="ts">
    interface Props {
        before: string;
        changeId: number;
    }

    let {before, changeId}: Props = $props();
</script>

<span class="block whitespace-pre-line break-words text-sm text-lf-muted" data-testid="profile-change-before-{changeId}" data-empty={before === '' ? 'true' : 'false'}>{before || '—'}</span>
