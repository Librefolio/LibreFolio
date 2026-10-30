<!--
  LineShapePicker — the three shapes a chart can draw its lines in (FB-3): segments, steps, smooth curve.

  A controlled segmented choice: it never changes `value`, it calls `onchange(next)`.
  Used by: ChartAestheticsSection (detail pages and the chart settings), the welcome tour, the user settings.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import {LINE_SHAPES, type LineShape} from './lineShape';

    interface Props {
        value: LineShape;
        onchange: (next: LineShape) => void;
        /** Prefix of the buttons' `data-testid` (`<prefix>-<shape>`). */
        testIdPrefix?: string;
        disabled?: boolean;
    }

    let {value, onchange, testIdPrefix = 'line-shape', disabled = false}: Props = $props();

    const LABEL_KEY: Record<LineShape, string> = {
        segments: 'chartSettings.lineShapeSegments',
        steps: 'chartSettings.lineShapeSteps',
        spline: 'chartSettings.lineShapeSpline',
    };
</script>

<div class="flex rounded-lg border border-lf-subtle overflow-hidden {disabled ? 'opacity-40 pointer-events-none' : ''}" data-testid={testIdPrefix} data-value={value} role="group" aria-label={$t('chartSettings.lineShape')}>
    {#each LINE_SHAPES as shape (shape)}
        <button
            aria-pressed={value === shape}
            class="px-2.5 py-1 text-sm sm:text-xs transition-colors {value === shape ? 'bg-lf-checked text-lf-on-checked' : 'bg-lf-card text-lf-muted hover:bg-lf-hover'}"
            data-testid="{testIdPrefix}-{shape}"
            {disabled}
            onclick={() => {
                if (!disabled) onchange(shape);
            }}
            type="button"
        >
            {$t(LABEL_KEY[shape])}
        </button>
    {/each}
</div>
