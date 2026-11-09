<!--
  PreferenceSourceBadge — where an interface preference's value comes from (lot UIP).

  - `global`: the user has not chosen this preference, so it follows the administrator's default (the GET of the user
    settings does not return the key). Information, not a warning: the info tint.
  - `auto`: the theme's value is «Auto», which leaves light or dark to the user's browser and system. A plain neutral chip.

  The chip is no control: its explanation is its `title`, and its words are the only thing a screen reader needs.
-->
<script lang="ts">
    import {_} from '$lib/i18n';

    interface Props {
        kind: 'global' | 'auto';
        testId: string;
    }

    let {kind, testId}: Props = $props();

    const tone = $derived(kind === 'global' ? 'bg-lf-info-soft text-lf-info-on-soft border-lf-info-line' : 'bg-lf-panel text-lf-secondary border-lf-subtle');
</script>

<span class="inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium {tone}" data-testid={testId} data-source={kind} title={$_(kind === 'global' ? 'settings.preferenceSource.globalHint' : 'settings.preferenceSource.autoHint')}>
    {$_(kind === 'global' ? 'settings.preferenceSource.global' : 'settings.preferenceSource.auto')}
</span>
