<script lang="ts">
    /**
     * SimulationHorizonField — the simulation horizon, in days or as `2y3m5d` (F-8).
     *
     * One field for the two panels that show it (`RiskAnalysisPanel`, `L4Simulation`). It owns the text and tells its
     * parent only the answer: `days`, the calendar days the engine takes, and `valid`, so a parent can keep its run
     * button off while the text is not a horizon. The reading is `horizonExpression.ts`, under test; the units follow
     * the interface language, from the catalogue.
     *
     * The text of a valid horizon never moves under the user's hands: `days` follows what is typed, not the other
     * way round, so the field is not rewritten to «826» while the reader is still adding a part.
     */
    import {CircleHelp} from 'lucide-svelte';

    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';
    import {_ as t} from '$lib/i18n';
    import {escapeHtml} from '$lib/utils/core/escapeHtml';

    import {HORIZON_MAX_DAYS, parseHorizon, type HorizonUnits} from './horizonExpression';

    interface Props {
        /** Calendar days the engine takes: the last valid reading. Bind it. */
        days: number;
        /** Whether the text is a horizon right now. Bind it to keep the run button off while it is not. */
        valid?: boolean;
        /** Called after a valid reading changes `days`. */
        onchange?: () => void;
        /** Classes of the input: each panel keeps its own width. */
        inputClass?: string;
        testId?: string;
        /**
         * Below the `sm` breakpoint, the label on the left and the input on the right of one row, with the days line under the input
         * in the flow, so it takes its own room and never lands on the field below (T-4, the parameters of `L4Simulation` on a
         * phone). From `sm` up the field is the column it always was.
         */
        phoneRow?: boolean;
    }

    let {days = $bindable(), valid = $bindable(true), onchange, inputClass = 'w-28', testId = 'risk-simulation-horizon', phoneRow = false}: Props = $props();

    // The initial text is the value the parent starts with; after that the text is the user's.
    let draft = $state(String(days));

    const units = $derived<HorizonUnits>({
        year: $t('risk.params.horizonExpr.units.year'),
        month: $t('risk.params.horizonExpr.units.month'),
        day: $t('risk.params.horizonExpr.units.day'),
    });

    const parsed = $derived(parseHorizon(draft, units));

    $effect(() => {
        valid = parsed.ok;
    });

    function handleInput(event: Event): void {
        draft = (event.currentTarget as HTMLInputElement).value;
        const next = parseHorizon(draft, units);
        if (next.ok && next.days !== days) {
            days = next.days;
            onchange?.();
        }
    }

    const errorText = $derived(parsed.ok ? '' : $t(`risk.params.horizonExpr.errors.${parsed.error}`, {values: {max: HORIZON_MAX_DAYS}}));

    /**
     * The tooltip: how to write it, as a bulleted list; and, while the text is not a horizon, the reason on top of it (F8,
     * developer's decision of 06/11/2026: the error is the red border and the reason in the tooltip, not a line that takes the
     * place of the days). Every text is escaped before it becomes markup.
     */
    const hintHtml = $derived.by(() => {
        const items = (['days', 'units', 'sum'] as const).map((key) => `<li>${escapeHtml($t(`risk.params.horizonExpr.hintItems.${key}`))}</li>`).join('');
        const reason = parsed.ok ? '' : `<p style="margin-bottom:4px;font-weight:600" data-testid="${testId}-reason">${escapeHtml(errorText)}</p>`;
        return `${reason}<ul style="list-style:disc;padding-left:1rem">${items}</ul>`;
    });
</script>

<!--
  Aligned with the fields beside it (F8): the label line and the input are all this field puts in the row's flow. The days the
  text comes to sit under the input in a line of their own, out of the flow (absolute), and the row that holds the field keeps the
  room for it (`pb-5`, whether or not there is a line to show), so the inputs of the row stay on one baseline and nothing moves
  when the line appears, changes or goes. With `phoneRow`, below `sm` the label and the input share one row and the days line is in
  the flow under the input: in a column of fields an absolute line would lie on the next one.
-->
<div class="relative flex flex-col gap-1 text-xs text-lf-muted" data-testid="{testId}-field" data-valid={parsed.ok} data-error={parsed.ok ? '' : parsed.error}>
    <label class={phoneRow ? 'flex items-center justify-between gap-3 sm:flex-col sm:items-stretch sm:justify-start sm:gap-1' : 'flex flex-col gap-1'}>
        <span class="flex items-center gap-1">
            {$t('risk.params.horizonDays')}
            <Tooltip html={hintHtml} position="top" testId="{testId}-hint">
                <CircleHelp size={13} class={parsed.ok ? 'text-lf-muted' : 'text-lf-danger'} aria-label={$t('risk.params.horizonExpr.hintLabel')} />
            </Tooltip>
        </span>
        <input
            type="text"
            inputmode="text"
            autocomplete="off"
            spellcheck="false"
            value={draft}
            oninput={handleInput}
            aria-invalid={!parsed.ok}
            aria-describedby="{testId}-days"
            class="rounded border border-lf-input bg-lf-field px-2 py-1 text-sm text-lf-primary hover:border-lf-input-hover focus:border-lf-focus focus:ring-1 focus:ring-lf-focus aria-invalid:border-lf-danger {inputClass}"
            data-testid={testId}
        />
    </label>
    <!-- The days it comes to; while the text is no horizon there are none to say, and the line keeps its place with a dash. -->
    <p id="{testId}-days" class="{phoneRow ? 'text-right sm:absolute sm:left-0 sm:top-full sm:mt-1 sm:text-left' : 'absolute left-0 top-full mt-1'} whitespace-nowrap text-[11px] leading-4 text-lf-muted" data-testid="{testId}-days" data-days={parsed.ok ? parsed.days : ''}>
        {parsed.ok ? $t('risk.params.horizonExpr.resultDays', {values: {days: parsed.days}}) : '\u2014'}
    </p>
</div>
