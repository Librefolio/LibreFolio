<!--
  Stand-in for LineChart in component tests: jsdom has no canvas for ECharts, and what a test of the component around it
  asks is the data it was handed — how many points, and the date the line starts on.
-->
<script lang="ts">
    interface Props {
        data?: Array<{date: string; value: number}>;
        // The real chart takes more props; a stand-in ignores them.
        [key: string]: unknown;
    }

    let {data = []}: Props = $props();
</script>

<div data-testid="stub-line-chart" data-points={data.length} data-first-date={data[0]?.date ?? ''}></div>
