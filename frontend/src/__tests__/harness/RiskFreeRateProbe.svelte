<script lang="ts">
    // A page's way to read the shared rate (RN-21): a `$derived` in a component, as `RiskLevelsPanel` and the lab do.
    import {riskFreeRate} from '$lib/features/risk/riskFreeRateStore.svelte';

    let rate = $derived(riskFreeRate.percent);
</script>

<span data-testid="risk-free-rate-probe">{rate}</span>
