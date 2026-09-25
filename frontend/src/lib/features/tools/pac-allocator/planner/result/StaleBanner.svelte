<script lang="ts">
    import {t} from '$lib/i18n';
    import {BUTTON_SECONDARY, NOTICE} from '../ui';

    interface Props {
        resultRevision: number;
        draftRevision: number;
        onreview: () => void;
        ondiscard: () => void;
    }

    let {resultRevision, draftRevision, onreview, ondiscard}: Props = $props();

    const KEY = 'tools.pacAllocator.planner.result.stale';
</script>

<div class="{NOTICE.warning} space-y-2" role="status" data-testid="pac-planner-stale" data-result-revision={resultRevision} data-draft-revision={draftRevision}>
    <p class="font-semibold">{$t(`${KEY}.title`, {default: 'Result not up to date'})}</p>
    <p>{$t(`${KEY}.body`, {default: 'You changed the configuration after this calculation. The values and orders below can still be consulted, but they no longer describe the current draft.'})}</p>
    <p class="tabular-nums">{$t(`${KEY}.revisions`, {default: 'Result snapshot rev. {result} · Current draft rev. {draft}', values: {result: resultRevision, draft: draftRevision}})}</p>
    <div class="flex flex-wrap gap-2">
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-stale-review" onclick={onreview}>{$t(`${KEY}.review`, {default: 'Back to Review'})}</button>
        <button type="button" class={BUTTON_SECONDARY} data-testid="pac-planner-stale-discard" onclick={ondiscard}>{$t(`${KEY}.discard`, {default: 'Discard the previous result'})}</button>
    </div>
</div>
