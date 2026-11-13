<script lang="ts">
    // Test fixture of planner/profileContext.test.ts: a Tool wrapper in miniature, setting a profile (or none) above a
    // probe, or above a real planner component given with its props.
    import {untrack, type Component} from 'svelte';
    import {setPlannerProfile, type PlannerProfile} from '../planner/profile';
    import ProfileProbe from './ProfileProbe.svelte';

    let {profile = null, child = null, childProps = {}}: {profile?: PlannerProfile | null; child?: Component<any> | null; childProps?: Record<string, unknown>} = $props();

    // Read once, while the wrapper is created, as a real wrapper does: a context is set only at creation.
    const initial = untrack(() => profile);
    if (initial !== null) setPlannerProfile(initial);
    const Child = untrack(() => child);
</script>

{#if Child}
    <Child {...childProps} />
{:else}
    <ProfileProbe />
{/if}
