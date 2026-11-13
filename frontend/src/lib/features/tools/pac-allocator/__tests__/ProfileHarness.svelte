<script lang="ts">
    // Test fixture of planner/profileContext.test.ts: a Tool wrapper in miniature, setting a profile (or none) above a probe.
    import {setPlannerProfile, type PlannerProfile} from '../planner/profile';
    import ProfileProbe from './ProfileProbe.svelte';

    let {profile = null}: {profile?: PlannerProfile | null} = $props();

    if (profile !== null) setPlannerProfile(profile);
</script>

<ProfileProbe />
