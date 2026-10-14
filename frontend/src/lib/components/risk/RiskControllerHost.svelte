<script lang="ts">
    /**
     * One panel controller, created where this component is placed: the `{#if}` around it
     * decides when the controller exists, and so when it asks.
     *
     * A controller asks its base wave the moment it is created — its `$effect`s run in the
     * component that creates it — and it has no switch to hold that question. Where a
     * question must wait for something a neighbour settles, the boundary is the guard, as
     * for the correlation section's empty selection: the controller is created by a
     * component mounted under the condition, and it asks once, with what it was waiting
     * for. The lab's L3° waits this way for the benchmark picker to confirm a stored choice
     * (`AssetSetComparisonLevels`): created earlier, it would ask without the benchmark and
     * then again with it.
     *
     * It draws nothing. The host reads the controller through `bind:controller`.
     */
    import {untrack} from 'svelte';
    import {createRiskPanelController, type RiskControllerInputs, type RiskControllerOptions, type RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';

    interface Props {
        /** Read on every question, so the controller follows the host's inputs. */
        inputs: () => RiskControllerInputs;
        /** Read once: a controller's shape is fixed when it is created. */
        options?: RiskControllerOptions;
        controller?: RiskPanelController;
    }

    let {inputs, options = {}, controller = $bindable()}: Props = $props();

    // `options` once, on purpose (see its prop); `inputs` on every question.
    controller = createRiskPanelController(
        () => inputs(),
        untrack(() => ({...options})),
    );
</script>
