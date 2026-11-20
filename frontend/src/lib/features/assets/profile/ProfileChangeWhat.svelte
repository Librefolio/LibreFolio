<!--
  ProfileChangeWhat — the «Cosa è cambiato» cell of a change of the asset profile (plan 68, E6a): the sentence, and its
  kind on `data-kind` (`profileChanges.changeKind`), the handle the tests read instead of the translated text. The
  sentence wraps: it is the row's content.

  On a phone (`compact`, the mock's shot 14) the table has this one column: under the sentence, in small, the day, the
  voice (the panel only) and who wrote it.
-->
<script lang="ts">
    import type {ChangeKind} from './profileChanges';
    import ProfileChangeWho from './ProfileChangeWho.svelte';

    interface Props {
        kind: ChangeKind;
        text: string;
        changeId: number;
        /** The phone's second line: the day, the voice when the host shows it, and who wrote it. */
        compact?: {when: string; voice?: string; source: string; name: string; avatarUrl?: string | null} | null;
    }

    let {kind, text, changeId, compact = null}: Props = $props();
</script>

<span class="block whitespace-normal break-words text-sm text-lf-secondary" data-testid="profile-change-what-{changeId}" data-kind={kind}>{text}</span>
{#if compact}
    <span class="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 whitespace-normal text-xs text-lf-muted" data-testid="profile-change-detail-{changeId}">
        <span class="font-mono">{compact.when}</span>
        {#if compact.voice}<span aria-hidden="true">·</span><span>{compact.voice}</span>{/if}
        <span aria-hidden="true">·</span>
        <ProfileChangeWho {changeId} source={compact.source} name={compact.name} avatarUrl={compact.avatarUrl ?? null} />
    </span>
{/if}
