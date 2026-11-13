<script lang="ts">
    // Test fixture of planner/profileContext.test.ts: a Tool wrapper in miniature, setting a profile (or none) above a probe.
    import {untrack} from 'svelte';
    import {setPlannerProfile, type PlannerProfile} from '../planner/profile';
    import ProfileProbe from './ProfileProbe.svelte';

    let {profile = null}: {profile?: PlannerProfile | null} = $props();

    // Read once, while the wrapper is created, as a real wrapper does: a context is set only at creation.
    const initial = untrack(() => profile);
    if (initial !== null) setPlannerProfile(initial);
</script>

<ProfileProbe />
