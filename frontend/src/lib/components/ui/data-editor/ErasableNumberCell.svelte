<!--
  ErasableNumberCell - Number input cell with "eraser" affordance (F.5).

  Semantics:
  - `value == null` -> shows italic gray "not set" placeholder (input empty, no sample).
  - `value == -1`   -> sentinel for "user cleared this field"; displays "cleared"
                      italic; user can type a value or click the eraser to re-clear.
  - any other number -> displays the value; hovering shows the eraser button at left.
  - Clicking the eraser -> sets value to -1 sentinel (no confirm, row-level revert
                           action covers accidental clears).
  - Pressing `Delete` while the input is focused and empty -> same as eraser.

  The sentinel -1 is intercepted by the save path in AssetDataEditorSection which
  sends it verbatim to the backend where PriceHistory.bulk_upsert interprets it as
  "SET NULL" on the target column (F.4 MERGE refactor).

  Uses Svelte 5 runes.
-->
<script lang="ts">
    import {Eraser} from 'lucide-svelte';
    import {_ as t} from '$lib/i18n';

    interface Props {
        /** Current numeric value. `null`/`undefined` = not set. `-1` = user-cleared sentinel. */
        value: number | null | undefined;
        /** Decimal step for the native input. */
        step?: number;
        /** Minimum allowed value (values below this are clamped on commit). */
        min?: number;
        /**
         * Placeholder shown ONLY when the cell is focused for editing (ghost hint).
         * When the value is null the cell instead shows the i18n "Not set" label in
         * italic gray - no sample number is displayed, per user feedback.
         */
        placeholder?: string;
        /** Called when the user commits a new value (including `-1` sentinel). */
        onchange: (newValue: number | null) => void;
    }

    let {value, step = 0.01, min, placeholder = '', onchange}: Props = $props();

    let editing = $state(false);
    // IMPORTANT: `draft` is bound to `<input type="number" bind:value>`. Svelte 5
    // coerces numeric-input bindings to `number | null` automatically. Declaring
    // draft as string would make the runtime value a number after first keystroke,
    // and the subsequent `.trim()` call in commit() would throw silently (TypeError
    // "draft.trim is not a function") — with the net effect that `onchange` was
    // never fired and the parent's dirty tracker never saw the edit (I-bis #9).
    let draft = $state<number | null>(null);

    // Sync draft FROM incoming value only when we are NOT actively editing.
    // Guarded with equality check to avoid spurious writes that would interrupt the
    // user while they type (the input is bound to `draft`).
    $effect(() => {
        if (editing) return;
        const desired = value == null || value === -1 ? null : value;
        if (draft !== desired) draft = desired;
    });

    let isNotSet = $derived(value == null);
    let isCleared = $derived(value === -1);

    function commit() {
        if (draft === null || draft === undefined || Number.isNaN(draft)) {
            if (value !== null && value !== undefined) {
                onchange(null);
            }
        } else {
            let n = Number(draft);
            if (!Number.isNaN(n)) {
                if (min !== undefined && n < min) n = min;
                if (n !== value) onchange(n);
                draft = n;
            }
        }
        editing = false;
    }

    function handleEraseClick() {
        // No confirm dialog - row-level "Revert" action covers undo; adding a
        // confirm on every erase is too much friction (user feedback 2026-04-22).
        draft = null;
        editing = false;
        onchange(-1);
    }

    function handleKeyDown(ev: KeyboardEvent) {
        if (ev.key === 'Delete' && (draft === null || draft === undefined)) {
            ev.preventDefault();
            handleEraseClick();
        } else if (ev.key === 'Enter') {
            (ev.currentTarget as HTMLInputElement).blur();
        }
    }
</script>

<div class="relative flex items-center group pl-5" data-testid="erasable-number-cell">
    <!-- Eraser at LEFT (absolute) - hidden until hover/focus to avoid covering
         the number input up/down spinner arrows which live at the RIGHT side. -->
    <button
        type="button"
        class="absolute left-0 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity p-0.5 rounded text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400"
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
            class="w-full text-left text-xs italic text-red-400 dark:text-red-500 cursor-text px-1.5 py-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20"
            onclick={() => {
                draft = null;
                editing = true;
            }}
            title={$t('dataEditor.cell.clearField')}
        >
            - {$t('dataEditor.cell.notSet')} -
        </button>
    {:else}
        <input
            type="number"
            class="w-full text-xs font-mono px-1.5 py-1 bg-transparent border border-transparent focus:border-gray-300 dark:focus:border-slate-500 rounded focus:outline-none
                   {isNotSet && !editing ? 'italic text-gray-400 dark:text-gray-500' : 'text-gray-700 dark:text-gray-200'}"
            bind:value={draft}
            {step}
            {min}
            placeholder={isNotSet && !editing ? $t('dataEditor.cell.notSet') : placeholder}
            onfocus={() => (editing = true)}
            onblur={commit}
            onkeydown={handleKeyDown}
        />
    {/if}
</div>
