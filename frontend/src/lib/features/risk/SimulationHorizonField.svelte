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
    }

    let {days = $bindable(), valid = $bindable(true), onchange, inputClass = 'w-28', testId = 'risk-simulation-horizon'}: Props = $props();

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
</script>

<div class="flex flex-col gap-1 text-xs text-lf-muted" data-testid="{testId}-field" data-valid={parsed.ok}>
    <label class="flex flex-col gap-1">
        <span class="flex items-center gap-1">
            {$t('risk.params.horizonDays')}
            <Tooltip text={$t('risk.params.horizonExpr.hint')} position="top" testId="{testId}-hint">
                <CircleHelp size={13} class="text-lf-muted" aria-label={$t('risk.params.horizonExpr.hintLabel')} />
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
            aria-describedby="{testId}-note"
            class="rounded border border-lf-input bg-lf-field px-2 py-1 text-sm text-lf-primary hover:border-lf-input-hover focus:border-lf-focus focus:ring-1 focus:ring-lf-focus aria-invalid:border-lf-danger {inputClass}"
            data-testid={testId}
        />
    </label>
    <!-- Always one line: the days the text comes to, or what is wrong with it, so the row does not jump. -->
    <p id="{testId}-note" class="min-h-4 text-[11px] {parsed.ok ? 'text-lf-muted' : 'text-lf-danger'}" data-testid={parsed.ok ? `${testId}-days` : `${testId}-error`} data-days={parsed.ok ? parsed.days : ''} data-error={parsed.ok ? '' : parsed.error}>
        {parsed.ok ? $t('risk.params.horizonExpr.resultDays', {values: {days: parsed.days}}) : errorText}
    </p>
</div>
