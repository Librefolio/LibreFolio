<!--
  AssetCalendarWindowControls — the window of the asset chart's rolling return: the presets, a custom
  duration in weeks, months or years, and the link to its documentation. Svelte 5 runes.
-->
<script lang="ts">
    import {_ as t} from '$lib/i18n';
    import DocsLink from '$lib/components/ui/DocsLink.svelte';
    import CompactDurationBadge from '$lib/components/ui/date/CompactDurationBadge.svelte';
    import {CALENDAR_RETURN_PRESETS, CALENDAR_RETURN_UNIT_LABEL_KEYS, calendarReturnWindowDays, type CalendarReturnPresetKey, type CalendarReturnWindowSelection, type CalendarReturnWindowUnit} from '$lib/components/charts/calendarReturnWindow';

    interface Props {
        /** The window in force. */
        selection: CalendarReturnWindowSelection;
        /** The custom duration being edited; kept by the page. */
        customAmount: number;
        customUnit: CalendarReturnWindowUnit;
        /** The custom duration's editor is open; the page closes it when the mode or the preset changes. */
        customEditing: boolean;
        onpreset: (preset: CalendarReturnPresetKey) => void;
        oncustom: (amount: number, unit: CalendarReturnWindowUnit) => void;
    }

    let {selection, customAmount = $bindable(), customUnit = $bindable(), customEditing = $bindable(), onpreset, oncustom}: Props = $props();

    let durationOptions = $derived([
        {
            value: 'weeks',
            label: $t('datePicker.granularity.weeksShort').toUpperCase(),
        },
        {
            value: 'months',
            label: $t('datePicker.granularity.monthsShort').toUpperCase(),
        },
        {
            value: 'years',
            label: $t('datePicker.granularity.yearsShort').toUpperCase(),
        },
    ]);
</script>

<div class="flex flex-wrap items-center gap-1.5" data-testid="asset-calendar-window-controls">
    <span class="text-xs text-lf-muted">{$t('chartSettings.params.window')}</span>
    {#each CALENDAR_RETURN_PRESETS as preset}
        <button
            class="min-w-10 px-2 py-1 rounded-md border text-xs font-medium transition-colors {selection.kind === 'preset' && selection.preset === preset.key ? 'border-lf-checked bg-lf-checked text-lf-on-checked' : 'border-lf-subtle text-lf-secondary hover:bg-lf-hover'}"
            data-testid={`asset-calendar-window-${preset.key}`}
            aria-pressed={selection.kind === 'preset' && selection.preset === preset.key}
            title={`${$t('chartSettings.params.window')}: ${preset.windowDays} ${$t('chartSettings.units.days')}`}
            onclick={() => onpreset(preset.key)}
        >
            {$t(CALENDAR_RETURN_UNIT_LABEL_KEYS[preset.unit], {values: {n: preset.count}})}
        </button>
    {/each}
    <CompactDurationBadge
        bind:amount={customAmount}
        bind:unit={customUnit}
        bind:editing={customEditing}
        active={selection.kind === 'custom'}
        options={durationOptions}
        customLabel={$t('common.custom')}
        min={1}
        buttonTestId="asset-calendar-window-custom"
        amountTestId="asset-calendar-custom-amount"
        unitTestId="asset-calendar-custom-unit"
        isAllowed={(amount, unit) =>
            unit !== 'days' &&
            calendarReturnWindowDays({
                ...selection,
                kind: 'custom',
                customAmount: amount,
                customUnit: unit,
            }) !== null}
        onapply={(amount, unit) => {
            if (unit !== 'days') {
                oncustom(amount, unit);
            }
        }}
    />
    <DocsLink path="user/assets/detail/chart/#rolling-return" label={$t('signals.riskRollingReturn.description')} size={14} testId="asset-calendar-return-docs" />
</div>
