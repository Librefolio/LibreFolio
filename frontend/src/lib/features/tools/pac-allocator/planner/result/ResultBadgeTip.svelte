<!--
  R11.10: a result badge with its explanation on hover, tap or focus. The same badges, in the header
  of the Result and in the tiles of the Proof.
-->
<script lang="ts">
    import {t} from '$lib/i18n';
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {BADGE} from '../ui';
    import type {ResultBadge} from './model';

    interface Props {
        badge: ResultBadge;
    }

    let {badge}: Props = $props();
</script>

<Tooltip text={$t(badge.help.key, {default: badge.help.fallback})} maxWidth="320px">
    <span class={BADGE[badge.tone]}>{$t(badge.key, {default: badge.fallback})}</span>
</Tooltip>
