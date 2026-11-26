<!--
  ProfileChangeWhat — the «Dopo» cell of a change of the asset profile (plan 68, E6a; 87, A3): the value after and, in
  small, the note the two values do not say. The kind is on `data-kind` (`profileChanges.changeKind`), the handle the
  tests read instead of the translated text. The text wraps: it is the row's content.

  On a phone (`compact`, the mock's shot 14) the table has this one column: the value before over the value after, each
  with its name, then in small the day, the voice (the panel only) and who wrote it.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import type {ChangeKind} from './profileChanges';
    import ProfileChangeBefore from './ProfileChangeBefore.svelte';
    import ProfileChangeWho from './ProfileChangeWho.svelte';
    import type {ProfileSource} from './profileSources';

    interface Props {
        kind: ChangeKind;
        before: string;
        after: string;
        note: string;
        changeId: number;
        /** The phone's second line: the day, the voice when the host shows it, and who wrote it. */
        compact?: {when: string; voice?: string; source: string; name: string; avatarUrl?: string | null; icon?: ProfileSource['icon']} | null;
    }

    let {kind, before, after, note, changeId, compact = null}: Props = $props();
</script>

{#snippet afterValue()}
    <span class="block whitespace-normal" data-testid="profile-change-what-{changeId}" data-kind={kind}>
        <span class="block whitespace-pre-line break-words text-sm {after === '' ? 'text-lf-muted' : 'text-lf-primary'}" data-testid="profile-change-after-{changeId}">{after || '—'}</span>
        {#if note}<span class="mt-0.5 block break-words text-xs text-lf-secondary" data-testid="profile-change-note-{changeId}">{note}</span>{/if}
    </span>
{/snippet}

{#if compact}
    {#if before !== ''}
        <span class="block text-[11px] font-medium text-lf-muted">{$t('assets.profile.changes.columns.before')}</span>
        <ProfileChangeBefore {before} {changeId} />
        <span class="mt-1 block text-[11px] font-medium text-lf-muted">{$t('assets.profile.changes.columns.after')}</span>
    {/if}
    {@render afterValue()}
    <span class="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 whitespace-normal text-xs text-lf-muted" data-testid="profile-change-detail-{changeId}">
        <span class="font-mono">{compact.when}</span>
        {#if compact.voice}<span aria-hidden="true">·</span><span>{compact.voice}</span>{/if}
        <span aria-hidden="true">·</span>
        <ProfileChangeWho {changeId} source={compact.source} name={compact.name} avatarUrl={compact.avatarUrl ?? null} icon={compact.icon ?? null} />
    </span>
{:else}
    {@render afterValue()}
{/if}
