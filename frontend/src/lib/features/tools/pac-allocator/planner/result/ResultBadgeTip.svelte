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

<!-- Lot MG: a value of the badge (its margin) in its text, and a line after the help (what the margin is). -->
<Tooltip text={[$t(badge.help.key, {default: badge.help.fallback, values: badge.help.values}), ...(badge.help.extra ? [$t(badge.help.extra.key, {default: badge.help.extra.fallback, values: badge.help.extra.values})] : [])].join(' ')} maxWidth="320px">
    <span class={BADGE[badge.tone]}>{$t(badge.key, {default: badge.fallback, values: badge.values})}</span>
</Tooltip>
