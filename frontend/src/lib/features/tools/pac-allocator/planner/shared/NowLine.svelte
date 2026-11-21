<!--
  «Now» under a name in the targets table (G5-1 of project 67, mockup screen 5 on a phone): today's weight of the row, while
  the «Now» column is hidden. A percentage, public; muted while the preview waits.
-->
<script lang="ts" module>
    export interface NowLineContent {
        text: string;
        /** The row's key, so a test finds its line. */
        key: string;
        stale: boolean;
    }
</script>

<script lang="ts">
    import {getPlannerProfile, testId} from '../profile';

    /** Read once, while the component is created: the Tool's profile (F1 of project 67), the PAC's when none is set. */
    const profile = getPlannerProfile();

    let {now}: {now: NowLineContent} = $props();
</script>

<span class="whitespace-nowrap font-mono text-xs {now.stale ? 'text-lf-muted' : 'text-lf-secondary'}" data-testid={testId('target-now-line', profile)} data-asset-key={now.key}>{now.text}</span>
