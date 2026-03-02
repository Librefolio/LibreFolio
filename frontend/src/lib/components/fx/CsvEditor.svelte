<!--
  CsvEditor — Mini code-editor-like CSV textarea with line numbers and live validation.

  Features:
  - Line numbers on the left
  - Live validation per row (green ✅ / red ❌)
  - Header row awareness (first line = header, skipped in validation)
  - Parsed valid points emitted as events
  - Scroll-to-line API for bidirectional sync with chart
  - Error messages per line
-->
<script context="module" lang="ts">
    export interface ParsedRow {
        date: string;
        base: string;
        quote: string;
        value: number;
        lineNumber: number;
    }
</script>
<script lang="ts">
    import {createEventDispatcher, tick} from 'svelte';

    // =========================================================================
    // Props
    // =========================================================================

    /** Expected CSV header */
    export let header: string = 'date;base;quote;base2quote';
    /** Current CSV text content */
    export let value: string = '';
    /** Whether the editor is read-only */
    export let readonly: boolean = false;
    /** Minimum height of the textarea */
    export let minHeight: string = '200px';

    // =========================================================================
    // Events
    // =========================================================================

    const dispatch = createEventDispatcher<{
        /** Emitted when valid points change */
        change: ParsedRow[];
        /** Emitted on every input (raw text) */
        input: string;
    }>();

    // =========================================================================
    // Types
    // =========================================================================


    interface LineValidation {
        lineNumber: number;
        text: string;
        valid: boolean;
        error?: string;
        parsed?: ParsedRow;
    }

    // =========================================================================
    // State
    // =========================================================================

    let textareaEl: HTMLTextAreaElement;
    let lineNumbersEl: HTMLDivElement;

    // =========================================================================
    // Derived
    // =========================================================================

    $: lines = value.split('\n');
    $: lineCount = lines.length;

    $: validations = lines.map((line, i): LineValidation => {
        const lineNumber = i + 1;
        const trimmed = line.trim();

        // Empty line
        if (!trimmed) return {lineNumber, text: line, valid: true};

        // Header line (first non-empty line matching expected header)
        if (i === 0 && trimmed.toLowerCase().replace(/\s/g, '') === header.toLowerCase().replace(/\s/g, '')) {
            return {lineNumber, text: line, valid: true};
        }

        // Parse data row
        const parts = trimmed.split(';');
        if (parts.length !== 4) {
            return {lineNumber, text: line, valid: false, error: `Expected 4 columns, got ${parts.length}`};
        }

        const [dateStr, baseStr, quoteStr, valueStr] = parts.map(p => p.trim());

        // Validate date
        if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
            return {lineNumber, text: line, valid: false, error: `Invalid date format: "${dateStr}". Use YYYY-MM-DD`};
        }
        const dateObj = new Date(dateStr + 'T00:00:00Z');
        if (isNaN(dateObj.getTime())) {
            return {lineNumber, text: line, valid: false, error: `Invalid date: "${dateStr}"`};
        }

        // Validate currencies (ISO 4217: 3 uppercase letters)
        const baseCurrency = baseStr.toUpperCase();
        const quoteCurrency = quoteStr.toUpperCase();
        if (!/^[A-Z]{3}$/.test(baseCurrency)) {
            return {lineNumber, text: line, valid: false, error: `Invalid base currency: "${baseStr}"`};
        }
        if (!/^[A-Z]{3}$/.test(quoteCurrency)) {
            return {lineNumber, text: line, valid: false, error: `Invalid quote currency: "${quoteStr}"`};
        }
        if (baseCurrency === quoteCurrency) {
            return {lineNumber, text: line, valid: false, error: `Base and quote must differ`};
        }

        // Validate value
        const numValue = parseFloat(valueStr);
        if (isNaN(numValue) || numValue <= 0) {
            return {lineNumber, text: line, valid: false, error: `Invalid value: "${valueStr}". Must be > 0`};
        }

        return {
            lineNumber,
            text: line,
            valid: true,
            parsed: {date: dateStr, base: baseCurrency, quote: quoteCurrency, value: numValue, lineNumber},
        };
    });

    // Emit valid parsed rows whenever validations change
    $: {
        const validRows = validations
            .filter(v => v.parsed)
            .map(v => v.parsed!);
        dispatch('change', validRows);
    }

    $: errorCount = validations.filter(v => !v.valid).length;
    $: validDataCount = validations.filter(v => v.parsed).length;

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleInput() {
        dispatch('input', value);
    }

    function handleScroll() {
        // Sync line numbers scroll with textarea
        if (lineNumbersEl && textareaEl) {
            lineNumbersEl.scrollTop = textareaEl.scrollTop;
        }
    }

    // =========================================================================
    // Public API
    // =========================================================================

    /** Scroll to a specific line number (1-based) */
    export async function scrollToLine(lineNumber: number) {
        if (!textareaEl) return;
        await tick();

        // Approximate line height
        const lineHeight = textareaEl.scrollHeight / Math.max(lineCount, 1);
        const targetScroll = (lineNumber - 1) * lineHeight - textareaEl.clientHeight / 3;
        textareaEl.scrollTo({top: Math.max(0, targetScroll), behavior: 'smooth'});

        // Select the line
        const lines = value.split('\n');
        let startPos = 0;
        for (let i = 0; i < lineNumber - 1 && i < lines.length; i++) {
            startPos += lines[i].length + 1; // +1 for \n
        }
        const endPos = startPos + (lines[lineNumber - 1]?.length || 0);
        textareaEl.setSelectionRange(startPos, endPos);
        textareaEl.focus();
    }

    /** Append a new CSV row at the end */
    export function appendRow(date: string, base: string, quote: string, rate: number) {
        const newLine = `${date};${base};${quote};${rate}`;
        if (value.trim()) {
            value = value.trimEnd() + '\n' + newLine;
        } else {
            value = header + '\n' + newLine;
        }
        handleInput();
    }

    /** Update a specific line (1-based) with new values */
    export function updateLine(lineNumber: number, date: string, base: string, quote: string, rate: number) {
        const lineArray = value.split('\n');
        if (lineNumber > 0 && lineNumber <= lineArray.length) {
            lineArray[lineNumber - 1] = `${date};${base};${quote};${rate}`;
            value = lineArray.join('\n');
            handleInput();
        }
    }
</script>

<div class="csv-editor rounded-lg border border-gray-200 dark:border-slate-600 overflow-hidden bg-white dark:bg-slate-800">
    <!-- Status bar -->
    <div class="flex items-center justify-between px-3 py-1.5 bg-gray-50 dark:bg-slate-700/50 border-b border-gray-200 dark:border-slate-600 text-xs">
        <span class="text-gray-500 dark:text-gray-400">
            {validDataCount} valid row{validDataCount !== 1 ? 's' : ''}
            {#if errorCount > 0}
                <span class="text-red-500 dark:text-red-400 ml-2">• {errorCount} error{errorCount !== 1 ? 's' : ''}</span>
            {/if}
        </span>
        <span class="font-mono text-gray-400 dark:text-gray-500">{header}</span>
    </div>

    <!-- Editor area -->
    <div class="flex overflow-hidden" style="min-height: {minHeight};">
        <!-- Line numbers -->
        <div
            bind:this={lineNumbersEl}
            class="flex-shrink-0 w-10 bg-gray-50 dark:bg-slate-700/30 border-r border-gray-200 dark:border-slate-600 overflow-hidden select-none"
        >
            {#each validations as v}
                <div
                    class="h-5 flex items-center justify-end pr-2 text-xs font-mono leading-5
                        {v.valid ? '' : 'bg-red-50 dark:bg-red-900/20'}"
                    title={v.error || ''}
                >
                    <span class="{v.parsed ? 'text-emerald-500' : v.valid ? 'text-gray-400 dark:text-gray-500' : 'text-red-500'}">{v.lineNumber}</span>
                </div>
            {/each}
        </div>

        <!-- Validation indicators -->
        <div class="flex-shrink-0 w-5">
            {#each validations as v}
                <div class="h-5 flex items-center justify-center text-xs leading-5" title={v.error || ''}>
                    {#if v.parsed}
                        <span class="text-emerald-500">✓</span>
                    {:else if !v.valid}
                        <span class="text-red-500">✗</span>
                    {/if}
                </div>
            {/each}
        </div>

        <!-- Textarea -->
        <textarea
            bind:this={textareaEl}
            bind:value
            on:input={handleInput}
            on:scroll={handleScroll}
            class="flex-1 font-mono text-xs leading-5 p-0 pl-2 border-0 bg-transparent text-gray-700 dark:text-gray-300 focus:ring-0 resize-y overflow-y-auto"
            style="min-height: {minHeight};"
            {readonly}
            spellcheck="false"
            autocomplete="off"
            wrap="off"
        ></textarea>
    </div>
</div>

