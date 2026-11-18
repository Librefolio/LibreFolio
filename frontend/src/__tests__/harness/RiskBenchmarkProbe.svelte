<script lang="ts">
    // A page's way to read the shared benchmark: a `$derived` in a component.
    import {riskBenchmark} from '$lib/features/risk/riskBenchmarkStore.svelte';

    let assetId = $derived(riskBenchmark.assetId);
</script>

<span data-testid="risk-benchmark-probe">{assetId ?? 'none'}</span>
