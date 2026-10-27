<script lang="ts">
    /**
     * The page the `(app)` layout shows instead of the app while the active accounts outnumber the plan (A5-7): the choice
     * for an administrator, the wait for anyone else. The role is the one the server named at sign-in (`$auth.user`), but
     * it is only a choice of page: every rule is the server's, which answers 423 to an ordinary user on the choice's routes.
     */
    import {auth} from '$lib/stores/app/auth';
    import UserLimitChoicePage from './UserLimitChoicePage.svelte';
    import UserLimitWaitingPage from './UserLimitWaitingPage.svelte';

    interface Props {
        onlogout: () => void;
    }

    let {onlogout}: Props = $props();
</script>

{#if $auth.user?.is_superuser === true}
    <UserLimitChoicePage {onlogout} />
{:else}
    <UserLimitWaitingPage {onlogout} />
{/if}
