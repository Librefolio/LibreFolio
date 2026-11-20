<script lang="ts">
    /**
     * Portfolio rebalancer 2.0.0 renderer: the planner's shell under the Rebalancer profile (F3a of project 67).
     *
     * The registry mounts this component for `portfolio_rebalancer` (`T/registry.ts`). It only sets the Rebalancer profile,
     * which every planner component below reads once at birth, and hands its props to the common shell (plan §3 n. 4: the
     * planner stays in `T/pac-allocator/planner/`).
     */
    import type {CompatibleToolDescriptor} from '../contracts';
    import {REBALANCER_PLANNER_PROFILE, setPlannerProfile} from '../pac-allocator/planner/profile';
    import PlannerShell from '../pac-allocator/planner/PlannerShell.svelte';

    interface Props {
        descriptor: CompatibleToolDescriptor<'portfolio_rebalancer', '2.0.0'>;
        accountGeneration: number;
    }

    let {descriptor, accountGeneration}: Props = $props();

    setPlannerProfile(REBALANCER_PLANNER_PROFILE);
</script>

<PlannerShell {descriptor} {accountGeneration} />
