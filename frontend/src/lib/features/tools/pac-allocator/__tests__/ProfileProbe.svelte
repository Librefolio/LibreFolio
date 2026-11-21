<script lang="ts">
    // Test fixture of planner/profileContext.test.ts: reads the profile once, as a planner component does at birth.
    import {getPlannerProfile} from '../planner/profile';

    const profile = getPlannerProfile();
</script>

<span data-testid="profile-probe" data-tool={profile.toolCode} data-correlation={profile.correlationPrefix}></span>
