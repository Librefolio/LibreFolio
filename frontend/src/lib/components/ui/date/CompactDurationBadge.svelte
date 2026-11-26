<!--
  CompactDurationBadge — the «Custom» window beside the period presets: a toggle that opens its inline editor. A standard
  Button (85 BTN-2d), the presets' size; chosen by hand it is amber like its editor (`pressed` + `tone="warning"`, C4+C5).
  `drp-trigger` stays on the button itself: the pickers' click-outside reads it, and the presets' row groups its buttons
  by their parent to see a wrap (a wrapper would hide this one from it).
-->
<script lang="ts">
    import Button from '$lib/components/ui/button/Button.svelte';
    import {numericArrows} from '$lib/actions/numericArrows';
    import {SimpleSelect} from '$lib/components/ui/select';
    import type {SelectOption} from '$lib/components/ui/select/types';
    import {isOutsideClick} from '$lib/utils/core/clickOutside';
    import {onMount, untrack} from 'svelte';

    type DurationUnit = 'days' | 'weeks' | 'months' | 'years';

    interface Props {
        amount?: number;
        unit?: DurationUnit;
        editing?: boolean;
        active?: boolean;
        options: SelectOption[];
        customLabel: string;
        min?: number;
        max?: number;
        buttonTestId?: string;
        amountTestId?: string;
        unitTestId?: string;
        buttonElement?: HTMLElement;
        editorElement?: HTMLDivElement | null;
        isAllowed?: (amount: number, unit: DurationUnit) => boolean;
        onapply?: (amount: number, unit: DurationUnit) => void;
    }

    let {amount = $bindable(3), unit = $bindable('years'), editing = $bindable(false), active = false, options, customLabel, min = 1, max, buttonTestId, amountTestId, unitTestId, buttonElement = $bindable(), editorElement = $bindable(null), isAllowed, onapply}: Props = $props();

    let draftAmount = $state(untrack(() => amount));
    let draftUnit: DurationUnit = $state(untrack(() => unit));
    let previousDraftAmount = untrack(() => draftAmount);
    let previousDraftUnit = untrack(() => draftUnit);

    function isDraftValid(): boolean {
        return Number.isSafeInteger(draftAmount) && draftAmount >= min && (max === undefined || draftAmount <= max) && options.some((option) => option.value === draftUnit && !option.disabled && !option.header) && (isAllowed?.(draftAmount, draftUnit) ?? true);
    }

    function applyDraftIfValid(): void {
        if (!isDraftValid()) return;
        amount = draftAmount;
        unit = draftUnit;
        onapply?.(amount, unit);
    }

    function toggleEditing(event: MouseEvent): void {
        event.stopPropagation();
        draftAmount = amount;
        draftUnit = unit;
        previousDraftAmount = draftAmount;
        previousDraftUnit = draftUnit;
        editing = true;
        applyDraftIfValid();
    }

    function handleUnitChange(value: string): void {
        draftUnit = value as DurationUnit;
    }

    $effect(() => {
        if (!editing) {
            draftAmount = amount;
            draftUnit = unit;
            previousDraftAmount = amount;
            previousDraftUnit = unit;
            return;
        }
        const changed = draftAmount !== previousDraftAmount || draftUnit !== previousDraftUnit;
        previousDraftAmount = draftAmount;
        previousDraftUnit = draftUnit;
        if (changed && isDraftValid()) {
            queueMicrotask(applyDraftIfValid);
        }
    });

    let selectedUnitLabel = $derived(options.find((option) => option.value === unit)?.label ?? unit);

    onMount(() => {
        function handleDocumentClick(event: MouseEvent): void {
            if (editing && isOutsideClick(event.target, (element) => !!element.closest('.drp-trigger') || !!element.closest('[data-simpleselect-dropdown]'))) {
                editing = false;
            }
        }
        document.addEventListener('click', handleDocumentClick);
        return () => document.removeEventListener('click', handleDocumentClick);
    });
</script>

{#if editing}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
        bind:this={editorElement}
        class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-lf-warning-soft text-lf-warning-on-soft rounded-lg border border-lf-warning-line drp-trigger"
        role="group"
        data-valid={isDraftValid() ? 'true' : 'false'}
        onclick={(event) => event.stopPropagation()}
        onkeydown={(event) => {
            if (event.key === 'Escape') editing = false;
        }}
    >
        <input
            type="number"
            use:numericArrows
            bind:value={draftAmount}
            data-testid={amountTestId}
            {min}
            {max}
            step="1"
            aria-invalid={!isDraftValid()}
            class="zoom-guard-exempt w-8 px-0.5 py-0.5 text-xs text-center border-none bg-transparent text-lf-warning-on-soft focus:ring-0 focus:outline-none [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        />
        <SimpleSelect value={draftUnit} {options} onchange={handleUnitChange} class="inline-block w-auto" dropdownPosition="auto" compact showChevron={false} testId={unitTestId} />
    </div>
{:else}
    <Button label={active ? `${amount}${selectedUnitLabel}` : customLabel} size="sm" compact segment pressed={active} tone="warning" class="drp-trigger" bind:element={buttonElement} onclick={toggleEditing} data-testid={buttonTestId} data-active={active ? 'true' : 'false'} />
{/if}
