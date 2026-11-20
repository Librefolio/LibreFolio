<script lang="ts">
    /**
     * PAC allocator 2.0.0 renderer: the planner's shell under the PAC profile (F1 of project 67).
     *
     * The registry mounts this component for `pac_allocator` (`T/registry.ts`). It only sets the PAC profile, which every
     * planner component below reads once at birth, and hands its props to the common shell.
     */
    import type {CompatibleToolDescriptor} from '../../contracts';
    import {PLANNER_CONTRACT_VERSION, PLANNER_TOOL_CODE} from './defaults';
    import {PAC_PLANNER_PROFILE, setPlannerProfile} from './profile';
    import PlannerShell from './PlannerShell.svelte';

    interface Props {
        descriptor: CompatibleToolDescriptor<typeof PLANNER_TOOL_CODE, typeof PLANNER_CONTRACT_VERSION>;
        accountGeneration: number;
    }

    let {descriptor, accountGeneration}: Props = $props();

    setPlannerProfile(PAC_PLANNER_PROFILE);
</script>

<PlannerShell {descriptor} {accountGeneration} />
