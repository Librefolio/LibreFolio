<!--
  ProfileChangeWho — the «Chi» cell of a change of the asset profile (plan 68, E6a): a value written by hand shows its
  author, avatar and username (round 36); a value of a source shows the source's name. A deleted author keeps the
  profile's words for a hand-written value. A value from before the profile existed (`legacy`) is the system's: the
  initial avatar «S» and «System», as the Files page names what the installation itself uploaded (81 U26a).
-->
<script lang="ts">
    import UserAvatar from '$lib/components/ui/media/UserAvatar.svelte';

    interface Props {
        changeId: number;
        /** `user` for a value written by hand, else a source's code. */
        source: string;
        /** The name the cell shows: the author's username, or the source's name. */
        name: string;
        /** The author's avatar, for a value written by hand. */
        avatarUrl?: string | null;
    }

    let {changeId, source, name, avatarUrl = null}: Props = $props();
</script>

<span class="inline-flex items-center gap-1.5 text-sm text-lf-secondary" data-testid="profile-change-who-{changeId}" data-source={source}>
    {#if source === 'user'}
        <UserAvatar username={name} {avatarUrl} />
    {:else if source === 'legacy'}
        <UserAvatar username={name} avatarUrl={null} />
    {:else}
        <span class="inline-flex h-5 min-w-5 items-center justify-center rounded bg-lf-panel px-1 text-[10px] font-semibold uppercase text-lf-muted" aria-hidden="true">{name.slice(0, 2)}</span>
    {/if}
    <span>{name}</span>
</span>
