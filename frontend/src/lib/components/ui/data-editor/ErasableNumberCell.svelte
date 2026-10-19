<!--
  ErasableNumberCell - Number input cell with "eraser" affordance (F.5).

  Semantics:
  - `value == null` -> shows italic gray "not set" placeholder (input empty, no sample).
  - `value === 'clear'` (CLEARED_CELL, N92) -> "user cleared this field"; displays "cleared"
                      italic; user can type a value or click the eraser to re-clear.
  - any other number -> displays the value; hovering shows the eraser button at left.
  - Clicking the eraser -> sets value to 'clear' (no confirm, row-level revert
                           action covers accidental clears).
  - Pressing `Delete` while the input is focused and empty -> same as eraser.

  The save path in AssetDataEditorSection sends 'clear' as it is: the backend's
  bulk_upsert_prices empties the target column (N92). A -1, which a CSV import can
  bring, is just a negative number, never a clear.

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Eraser} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';
    import {decimalArrowStep, normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';
    import {CLEARED_CELL} from './DataEditorTypes';

    interface Props {
        /** Current numeric value. `null`/`undefined` = not set. `CLEARED_CELL` = cleared by the user (N92). */
        value: number | typeof CLEARED_CELL | null | undefined;
        /** Minimum allowed value (values below this are clamped on commit). */
        min?: number;
        /**
         * Placeholder shown ONLY when the cell is focused for editing (ghost hint).
         * When the value is null the cell instead shows the i18n "Not set" label in
         * italic gray - no sample number is displayed, per user feedback.
         */
        placeholder?: string;
        /** Called when the user commits a new value (including `CLEARED_CELL`). */
        onchange: (newValue: number | typeof CLEARED_CELL | null) => void;
    }

    let {value, min, placeholder = '', onchange}: Props = $props();

    let editing = $state(false);
    // `draft` is a STRING buffer, not a number. The input is `type="text"` on purpose:
    // `type="number"` is parsed by the browser against its own locale, so a user typing
    // "5,9" on an Italian keyboard hands us an empty value and watches their digits
    // vanish. We keep the raw keystrokes and normalise the separator on commit.
    let draft: string = $state('');

    // Sync draft FROM incoming value only when we are NOT actively editing.
    // Guarded with equality check to avoid spurious writes that would interrupt the
    // user while they type (the input is bound to `draft`).
    $effect(() => {
        if (editing) return;
        const desired = value == null || value === CLEARED_CELL ? '' : String(value);
        if (draft !== desired) draft = desired;
    });

    let isNotSet = $derived(value == null);
    let isCleared = $derived(value === CLEARED_CELL);

    function commit() {
        const normalized = normalizeDecimalInput(draft ?? '');
        if (normalized === '') {
            if (value !== null && value !== undefined) onchange(null);
        } else {
            let n = Number(normalized);
            if (!Number.isNaN(n)) {
                if (min !== undefined && n < min) n = min;
                if (n !== value) onchange(n);
                draft = String(n);
            }
        }
        editing = false;
    }

    function handleEraseClick() {
        // No confirm dialog - row-level "Revert" action covers undo; adding a
        // confirm on every erase is too much friction (user feedback 2026-04-22).
        draft = '';
        editing = false;
        onchange(CLEARED_CELL);
    }

    function handleKeyDown(ev: KeyboardEvent) {
        if (ev.key === 'Delete' && (draft ?? '') === '') {
            ev.preventDefault();
            handleEraseClick();
            return;
        }
        if (ev.key === 'Enter') {
            (ev.currentTarget as HTMLInputElement).blur();
            return;
        }
        const stepped = decimalArrowStep(ev, draft ?? '');
        if (stepped !== null) draft = stepped;
    }
</script>

<div class="relative flex items-center group pl-5 text-lf-primary" data-testid="erasable-number-cell">
    <!-- Eraser at LEFT (absolute) - hidden until hover/focus to avoid covering
         the number input up/down spinner arrows which live at the RIGHT side. -->
    <button
        type="button"
        class="absolute left-0 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity p-0.5 rounded text-lf-muted hover:text-lf-danger"
        onclick={handleEraseClick}
        onmousedown={(e) => e.preventDefault()}
        title={$t('dataEditor.cell.clearField')}
        data-testid="erasable-cell-eraser"
        tabindex="-1"
    >
        <Eraser size={12} />
    </button>

    {#if isCleared && !editing}
        <!-- Cleared state: italic red. Click re-enters edit mode with empty draft. -->
        <button
            type="button"
            class="w-full text-left text-xs italic text-lf-danger cursor-text px-1.5 py-1 rounded hover:bg-lf-danger-soft"
            onclick={() => {
                draft = '';
                editing = true;
            }}
            title={$t('dataEditor.cell.clearField')}
        >
            - {$t('dataEditor.cell.notSet')} -
        </button>
    {:else}
        <input
            type="text"
            inputmode="decimal"
            autocomplete="off"
            class="w-full text-xs font-mono px-1.5 py-1 bg-transparent border border-transparent focus:border-lf-focus rounded focus:outline-none placeholder:text-lf-placeholder
                   {isNotSet && !editing ? 'italic text-lf-muted' : 'text-lf-primary'}"
            bind:value={draft}
            placeholder={isNotSet && !editing ? $t('dataEditor.cell.notSet') : placeholder}
            onfocus={() => (editing = true)}
            onblur={commit}
            onkeydown={handleKeyDown}
        />
    {/if}
</div>
