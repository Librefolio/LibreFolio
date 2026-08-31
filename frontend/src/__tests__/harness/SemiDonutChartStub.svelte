<!--
  SemiDonutChartStub — test-only stand-in for SemiDonutChart (Vitest + jsdom).

  Two reasons it exists, and the second is the interesting one.

  1. The real chart cannot run here. `SemiDonutChart` calls `echarts.init` on its
     container and ECharts draws through a canvas 2D context, which jsdom does not
     implement: `getContext('2d')` answers `null` and zrender dies on
     `Cannot set properties of null (setting 'dpr')`. The chart only survives a
     short spec by accident — `waitForRenderableContainer` spends four animation
     frames waiting for a non-zero box before it initialises, so a test that
     finishes quickly unmounts the container first. Any spec that lives longer
     than four frames takes the crash as an unhandled error. Whether the donut
     paints is E2E ground in any case, and `broker-sharing.spec.ts` already asserts
     a canvas with a non-zero bitmap.

  2. It makes the panel's `chartSlices` readable. That derivation drops owners
     whose rounded share is 0 and rewrites each avatar URL with a preview suffix —
     real logic, and in production its only consumer is a canvas, so no test at any
     level can see it. The stub publishes the array it was handed as `data-slices`
     (JSON), which turns an invisible computation into an assertable value.

  Lives under `src/__tests__/`, excluded from coverage by `vitest.config.ts`, so it
  cannot inflate the numbers it exists to improve.
-->
<script lang="ts">
    interface OwnerSlice {
        name: string;
        percentage: number;
        avatarUrl?: string | null;
    }

    interface Props {
        data?: OwnerSlice[];
        availableLabel?: string;
        height?: string;
    }

    let {data = [], availableLabel = '', height = ''}: Props = $props();
</script>

<div data-testid="semi-donut-stub" data-slices={JSON.stringify(data)} data-slice-count={data.length} data-available-label={availableLabel} data-height={height}></div>
