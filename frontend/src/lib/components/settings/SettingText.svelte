<script lang="ts">
    /**
     * SettingText.svelte
     * Text/Email input with inline edit functionality
     */
    import {createEventDispatcher} from 'svelte';
    import {Check, Pencil, X} from 'lucide-svelte';

    const dispatch = createEventDispatcher<{
        change: string;
    }>();

    // Props
    export let value: string;
    export let type: 'text' | 'email' | 'url' = 'text';
    export let placeholder: string = '';
    export let readonly: boolean = false;
    export let maxlength: number | undefined = undefined;
    export let pattern: string | undefined = undefined;

    // State
    let isEditing = false;
    let editValue = value;
    let inputElement: HTMLInputElement | null = null;

    // Validation
    $: isValid = validateValue(editValue);

    function validateValue(val: string): boolean {
        if (!val.trim()) return false;

        if (type === 'email') {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(val);
        }

        if (type === 'url') {
            try {
                new URL(val);
                return true;
            } catch {
                return false;
            }
        }

        if (pattern) {
            const regex = new RegExp(pattern);
            return regex.test(val);
        }

        return true;
    }

    function startEdit() {
        if (readonly) return;
        editValue = value;
        isEditing = true;
        setTimeout(() => inputElement?.focus(), 50);
    }

    function saveEdit() {
        if (!isValid) return;
        value = editValue.trim();
        isEditing = false;
        dispatch('change', value);
    }

    function cancelEdit() {
        editValue = value;
        isEditing = false;
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Enter' && isValid) {
            saveEdit();
        } else if (event.key === 'Escape') {
            cancelEdit();
        }
    }
</script>

<div class="setting-text">
    {#if isEditing}
        <!-- Edit Mode -->
        <div class="edit-container">
            <input
                    bind:this={inputElement}
                    bind:value={editValue}
                    {type}
                    {placeholder}
                    {maxlength}
                    {pattern}
                    on:keydown={handleKeydown}
                    class="input"
                    class:invalid={!isValid}
            />
            <div class="actions">
                <button
                        type="button"
                        on:click={saveEdit}
                        disabled={!isValid}
                        class="action-btn save"
                        title="Save"
                >
                    <Check size={16}/>
                </button>
                <button
                        type="button"
                        on:click={cancelEdit}
                        class="action-btn cancel"
                        title="Cancel"
                >
                    <X size={16}/>
                </button>
            </div>
        </div>
    {:else}
        <!-- Display Mode -->
        <div class="display-container">
            <span class="value">{value}</span>
            {#if !readonly}
                <button
                        type="button"
                        on:click={startEdit}
                        class="edit-btn"
                        title="Edit"
                >
                    <Pencil size={14}/>
                </button>
            {/if}
        </div>
    {/if}
</div>

<style>
    .setting-text {
        width: 100%;
    }

    .edit-container {
        display: flex;
        gap: 0.5rem;
        align-items: center;
    }

    .input {
        flex: 1;
        padding: 0.5rem 0.75rem;
        border: 1px solid #d1d5db;
        border-radius: 0.375rem;
        font-size: 0.875rem;
        transition: all 0.15s ease;
    }

    .input:focus {
        outline: none;
        border-color: #1a4031;
        box-shadow: 0 0 0 3px rgba(26, 64, 49, 0.1);
    }

    .input.invalid {
        border-color: #ef4444;
    }

    :global(.dark) .input {
        background: #1e293b;
        border-color: #475569;
        color: #f8fafc;
    }

    :global(.dark) .input:focus {
        border-color: #22c55e;
        box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.1);
    }

    .actions {
        display: flex;
        gap: 0.25rem;
    }

    .action-btn {
        padding: 0.375rem;
        border-radius: 0.375rem;
        border: none;
        cursor: pointer;
        transition: all 0.15s ease;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .action-btn.save {
        background: #22c55e;
        color: white;
    }

    .action-btn.save:hover:not(:disabled) {
        background: #16a34a;
    }

    .action-btn.save:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .action-btn.cancel {
        background: #ef4444;
        color: white;
    }

    .action-btn.cancel:hover {
        background: #dc2626;
    }

    .display-container {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.5rem 0.75rem;
        background: #f9fafb;
        border-radius: 0.375rem;
        min-height: 2.5rem;
    }

    :global(.dark) .display-container {
        background: #1e293b;
    }

    .value {
        flex: 1;
        font-size: 0.875rem;
        color: #111827;
    }

    :global(.dark) .value {
        color: #f8fafc;
    }

    .edit-btn {
        padding: 0.25rem;
        background: transparent;
        border: none;
        color: #6b7280;
        cursor: pointer;
        border-radius: 0.25rem;
        transition: all 0.15s ease;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .edit-btn:hover {
        background: #e5e7eb;
        color: #1a4031;
    }

    :global(.dark) .edit-btn {
        color: #9ca3af;
    }

    :global(.dark) .edit-btn:hover {
        background: #334155;
        color: #22c55e;
    }
</style>
