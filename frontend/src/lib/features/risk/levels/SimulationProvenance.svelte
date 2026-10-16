<script lang="ts">
    import {AlertTriangle} from 'lucide-svelte';

    import {_ as t} from '$lib/i18n';

    import type {ProvenanceEntry, SimulationProvenance} from './simulationProvenance';

    /**
     * The assumptions behind the cone, stated by the cone.
     *
     * Every string here comes from a field the backend sent. Nothing is inferred
     * from the shape of today's backend, because the sentence this replaces was
     * doing exactly that: it read "without costs, cash flows, inflation or
     * rebalancing" in four catalogues, regardless of what the run had done.
     */
    interface Props {
        provenance: SimulationProvenance | null;
    }

    let {provenance}: Props = $props();

    const NS = 'risk.levels.l4.provenance';

    /**
     * An enum value's label, falling back to the value itself.
     *
     * Regime names arrive from the backend and this catalogue cannot know them in
     * advance. Without the fallback an unrecognised one would render as its own
     * dotted key — which looks like a bug in the page rather than a value the
     * page has never been told about.
     */
    function valueLabel(value: string): string {
        return $t(`${NS}.values.${value}`, {default: value});
    }

    function entryText(entry: ProvenanceEntry): string {
        if (entry.key === 'regime' && entry.value !== null && entry.number !== null) {
            return $t(`${NS}.regimeValue`, {values: {regime: valueLabel(entry.value), days: entry.number}});
        }
        if (entry.value !== null) return valueLabel(entry.value);
        if (entry.key === 'blockLength' && entry.number !== null) return $t(`${NS}.days`, {values: {count: entry.number}});
        return entry.number === null ? '' : String(entry.number);
    }

    function effectList(effects: readonly string[]): string {
        return effects.map((effect) => $t(`${NS}.effects.${effect}`)).join(', ');
    }
</script>

{#if provenance}
    <div class="mt-3 space-y-2 rounded-lg bg-gray-50 px-3 py-2 dark:bg-slate-800/60" data-testid="risk-l4-provenance">
        <div>
            <p class="text-xs font-medium text-gray-700 dark:text-gray-200">{$t(`${NS}.title`)}</p>
            <p class="text-xs text-gray-500 dark:text-gray-400">{$t(`${NS}.hint`)}</p>
        </div>

        {#if provenance.entries.length > 0}
            <dl class="grid grid-cols-1 gap-x-4 gap-y-1 text-xs sm:grid-cols-2">
                {#each provenance.entries as entry (entry.key)}
                    <div class="flex justify-between gap-2" data-testid="risk-l4-provenance-{entry.key}">
                        <dt class="text-gray-500 dark:text-gray-400">{$t(`${NS}.labels.${entry.key}`)}</dt>
                        <dd class="text-right font-medium text-gray-700 dark:text-gray-200">{entryText(entry)}</dd>
                    </div>
                {/each}
            </dl>
        {/if}

        {#if provenance.inclusions.length > 0}
            <p class="text-xs text-gray-600 dark:text-gray-300" data-testid="risk-l4-provenance-includes">
                {$t(`${NS}.includes`)}: {effectList(provenance.inclusions)}
            </p>
        {/if}

        {#if provenance.exclusions.length > 0}
            <p class="text-xs text-gray-600 dark:text-gray-300" data-testid="risk-l4-provenance-excludes">
                {$t(`${NS}.excludes`)}: {effectList(provenance.exclusions)}
            </p>
        {/if}

        {#if provenance.truncation}
            <div class="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 dark:bg-amber-900/20" data-testid="risk-l4-provenance-truncation">
                <AlertTriangle size={14} class="mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
                <p class="text-xs text-amber-800 dark:text-amber-200">
                    {$t(`${NS}.truncation`, {values: {declared: provenance.truncation.declaredDays, applied: provenance.truncation.appliedDays}})}
                </p>
            </div>
        {/if}
    </div>
{/if}
