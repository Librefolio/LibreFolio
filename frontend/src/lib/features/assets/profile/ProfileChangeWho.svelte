<!--
  ProfileChangeWho — the «Chi» cell of a change of the asset profile (plan 68, E6a; 87, A2): a value written by hand shows
  its author, avatar and username (round 36); a value of a source shows the source's icon, or its initials, and its name.
  A deleted author keeps the profile's words for a hand-written value. A value from before the profile existed (`legacy`)
  is the system's: the «S» on the coloured disc the Files page gives to what the installation itself uploaded.
-->
<script lang="ts">
    import UserAvatar from '$lib/components/ui/media/UserAvatar.svelte';
    import EnricherTile from '$lib/features/assets/enrichers/EnricherTile.svelte';
    import {initialAvatarDataUrl, SYSTEM_AVATAR_SEED} from '$lib/utils/files/initialAvatar';
    import type {ProfileSource} from './profileSources';

    interface Props {
        changeId: number;
        /** `user` for a value written by hand, else a source's code. */
        source: string;
        /** The name the cell shows: the author's username, or the source's name. */
        name: string;
        /** The author's avatar, for a value written by hand. */
        avatarUrl?: string | null;
        /** The source's icon, as it declares it. */
        icon?: ProfileSource['icon'];
    }

    let {changeId, source, name, avatarUrl = null, icon = null}: Props = $props();
</script>

<span class="inline-flex items-center gap-1.5 text-sm text-lf-secondary" data-testid="profile-change-who-{changeId}" data-source={source}>
    {#if source === 'user'}
        <UserAvatar username={name} {avatarUrl} />
    {:else if source === 'legacy'}
        <UserAvatar username={name} avatarUrl={initialAvatarDataUrl(name, SYSTEM_AVATAR_SEED)} />
    {:else}
        <EnricherTile code={source} {name} {icon} size="sm" />
    {/if}
    <span>{name}</span>
</span>
