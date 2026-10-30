<!--
  LineShapePreviewProbe — test-only stand-in for LineShapePreview.svelte (Vitest + jsdom).

  The real preview draws an ECharts chart, which needs a canvas jsdom does not have. The welcome specs' subject is
  the form around it, so the probe keeps only what they read: the shape it was given, as `data-shape`.
-->
<script lang="ts">
    import type {LineShape} from '$lib/components/charts/lineShape';

    interface Props {
        shape: LineShape;
        height?: string;
    }

    let {shape}: Props = $props();
</script>

<div data-testid="line-shape-preview" data-shape={shape}></div>
