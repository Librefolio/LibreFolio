<!--
  LineShapePreview — a made-up chart with a signal over it, drawn in the shape the user is choosing (FB-3).
  Used by: the welcome page, next to the line shape picker.
-->
<script lang="ts">
    import LineChart from './LineChart.svelte';
    import type {LineShape} from './lineShape';
    import {previewPrice, previewSignal} from './lineShapePreviewData';

    interface Props {
        shape: LineShape;
        height?: string;
    }

    let {shape, height = '140px'}: Props = $props();

    const price = previewPrice();
    const signals = [previewSignal(price)];
</script>

<div data-testid="line-shape-preview" data-shape={shape}>
    <LineChart data={price} overlaySignals={signals} lineShape={shape} {height} colorByBaseline={false} showGradient={false} />
</div>
