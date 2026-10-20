<!--
UserAvatar — an account's avatar in a 24 px circle, or its initial when it has none (N69-4, D8 a).

An image uploaded to the app is asked for at preview size (`img_preview=48x48`, sharp on a 2x screen); an address on
another site is used as it is. The initial takes the scheme of the user pickers (`UserSearchSelect`): the muted text on
a neutral disc, and no colour of its own per user (the colour programme's condition, 19/10).
-->
<script lang="ts">
    import LazyImage from '$lib/components/ui/media/LazyImage.svelte';

    interface Props {
        username: string;
        avatarUrl: string | null;
        /** Extra attributes for the root, such as a test id. */
        testId?: string;
    }

    let {username, avatarUrl, testId}: Props = $props();

    const UPLOADS = '/api/v1/uploads/';

    const source = $derived(avatarUrl ? (avatarUrl.startsWith(UPLOADS) ? `${avatarUrl}${avatarUrl.includes('?') ? '&' : '?'}img_preview=48x48` : avatarUrl) : null);
    const initial = $derived(username.trim().charAt(0).toUpperCase() || '?');
</script>

<span class="inline-flex h-6 w-6 shrink-0 overflow-hidden rounded-full" data-avatar={source ? 'image' : 'initial'} data-testid={testId}>
    {#if source}
        <LazyImage src={source} alt={username} circle placeholder="avatar" />
    {:else}
        <span class="flex h-full w-full items-center justify-center rounded-full bg-lf-neutral text-[10px] font-semibold text-lf-muted" aria-hidden="true">{initial}</span>
    {/if}
</span>
