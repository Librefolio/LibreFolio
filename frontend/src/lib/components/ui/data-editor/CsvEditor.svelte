<!--
  CsvEditor — Generic N-column CSV textarea with line numbers and live validation.

  Features:
  - Configurable columns via CsvColumnDef[] prop
  - Header auto-generated from column labels: date;col1;col2;...
  - Live validation per row (green ✓ / red ✗)
  - Optional columns: missing fields (trailing omission or ;;) become null
  - Required columns validated (must be non-empty)
  - Duplicate date detection (yellow highlight)
  - Parsed valid points emitted via onvalidchange callback
  - Scroll-to-line API
  - Error messages per line

  Uses Svelte 5 runes ($state, $derived, $props).
-->
<script lang="ts">
    import {tick} from 'svelte';
    import {t} from '$lib/i18n';

    // =========================================================================
    // Types (exported for external use)
    // =========================================================================

    /** Column definition for CSV parsing */
    export interface CsvColumnDef {
        /** Unique key used in ParsedRow.values */
        key: string;
        /** Display label (appears in header row) */
        label: string;
        /** Data type for validation */
        type: 'number' | 'string';
        /** Whether this column must have a non-empty value */
        required: boolean;
    }

    export interface ParsedRow {
        date: string;
        values: Record<string, unknown>;
        lineNumber: number;
    }

    // =========================================================================
    // Number parsing — supports . and , as decimal, _ as thousands separator
    // =========================================================================

    /**
     * Parse a number string with flexible formatting:
     * - `_` stripped (thousands separator, like JS/Rust: 1_000_000)
     * - Both `.` and `,` present: last one = decimal separator, other = thousands
     * - Only `,`: treated as decimal separator (0,6045 → 0.6045)
     * - Only `.`: standard parseFloat
     */
    function parseNumber(raw: string): number {
        let s = raw.replace(/_/g, '');
        const lastDot = s.lastIndexOf('.');
        const lastComma = s.lastIndexOf(',');

        if (lastDot >= 0 && lastComma >= 0) {
            if (lastComma > lastDot) {
                s = s.replace(/\./g, '').replace(',', '.');
            } else {
                s = s.replace(/,/g, '');
            }
        } else if (lastComma >= 0) {
            s = s.replace(',', '.');
        }

        return parseFloat(s);
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Column definitions (determines expected CSV structure) */
        columns: CsvColumnDef[];
        /** Current CSV text content (bindable) */
        value?: string;
        /** Whether the editor is read-only */
        readonly?: boolean;
        /** Minimum height of the textarea */
        minHeight?: string;
        /** Placeholder text when textarea is empty */
        placeholder?: string;
        /** Called when valid parsed rows change */
        onvalidchange?: (validRows: ParsedRow[], errorCount: number, hasDuplicates: boolean) => void;
        /** Called on every input (raw text) */
        oninput?: (text: string) => void;
        /** Called when text content changes (for bind:value replacement) */
        onchange?: (text: string) => void;
    }

    let {
        columns,
        value = $bindable(''),
        readonly: isReadonly = false,
        minHeight = '200px',
        placeholder = '',
        onvalidchange,
        oninput,
        onchange,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let textareaEl: HTMLTextAreaElement | undefined = $state(undefined);
    let lineNumbersEl: HTMLDivElement | undefined = $state(undefined);

    // =========================================================================
    // Header logic
    // =========================================================================

    /** Expected header string derived from column definitions */
    let expectedHeader = $derived('date;' + columns.map(c => c.label).join(';'));

    /** Total number of columns including date */
    let totalCols = $derived(1 + columns.length);

    function isHeaderLine(trimmed: string): boolean {
        if (trimmed.toLowerCase() === expectedHeader.toLowerCase()) return true;
        // Also accept < as inverse direction: A<B is equivalent to B>A
        const normalized = trimmed.replace(/([^;<\s]+)\s*<\s*([^;<\s]+)/g, '$2>$1');
        return normalized.toLowerCase() === expectedHeader.toLowerCase();
    }

    // =========================================================================
    // Derived
    // =========================================================================

    interface LineValidation {
        lineNumber: number;
        text: string;
        valid: boolean;
        error?: string;
        parsed?: ParsedRow;
        duplicate?: boolean;
        isHeader?: boolean;
    }

    let lines = $derived(value.split('\n'));
    let lineCount = $derived(lines.length);

    /** Check if header is present and valid */
    let headerValid = $derived.by(() => {
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed) return isHeaderLine(trimmed);
        }
        return false;
    });

    let validations: LineValidation[] = $derived.by(() => {
        const result: LineValidation[] = lines.map((line, i): LineValidation => {
            const lineNumber = i + 1;
            const trimmed = line.trim();

            // Empty line
            if (!trimmed) return {lineNumber, text: line, valid: true};

            // Header line (first non-empty line) — validate as header
            if (i === lines.findIndex(l => l.trim() !== '')) {
                if (isHeaderLine(trimmed)) {
                    return {lineNumber, text: line, valid: true, isHeader: true};
                } else {
                    return {
                        lineNumber, text: line, valid: false, isHeader: true,
                        error: `Expected header: ${expectedHeader}`,
                    };
                }
            }

            // If header is invalid, don't validate data rows
            if (!headerValid) {
                return {lineNumber, text: line, valid: false, error: 'Fix header first'};
            }

            // Parse data row (N columns: date;col1;col2;...)
            const parts = trimmed.split(';');
            if (parts.length > totalCols) {
                return {
                    lineNumber, text: line, valid: false,
                    error: `Too many columns: expected max ${totalCols}, got ${parts.length}`,
                };
            }

            const dateStr = parts[0].trim();

            // Validate date (YYYY-MM-DD)
            if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
                return {lineNumber, text: line, valid: false, error: `Invalid date format: "${dateStr}". Use YYYY-MM-DD`};
            }
            const dateObj = new Date(dateStr + 'T00:00:00Z');
            if (isNaN(dateObj.getTime())) {
                return {lineNumber, text: line, valid: false, error: `Invalid date: "${dateStr}"`};
            }

            // Parse each column value
            const values: Record<string, unknown> = {};
            let parseError: string | null = null;

            for (let c = 0; c < columns.length; c++) {
                const col = columns[c];
                const rawVal = (parts[c + 1] ?? '').trim();

                if (!rawVal) {
                    if (col.required) {
                        parseError = `Required column "${col.label}" is empty`;
                        break;
                    }
                    values[col.key] = null;
                    continue;
                }

                if (col.type === 'number') {
                    const num = parseNumber(rawVal);
                    if (isNaN(num)) {
                        parseError = `Invalid number in "${col.label}": "${rawVal}"`;
                        break;
                    }
                    values[col.key] = num;
                } else {
                    values[col.key] = rawVal;
                }
            }

            if (parseError) {
                return {lineNumber, text: line, valid: false, error: parseError};
            }

            return {
                lineNumber,
                text: line,
                valid: true,
                parsed: {date: dateStr, values, lineNumber},
            };
        });

        // Duplicate date detection
        const dateCount = new Map<string, number[]>();
        for (const v of result) {
            if (v.parsed) {
                const indices = dateCount.get(v.parsed.date) ?? [];
                indices.push(v.lineNumber);
                dateCount.set(v.parsed.date, indices);
            }
        }
        for (const [date, indices] of dateCount) {
            if (indices.length > 1) {
                for (const v of result) {
                    if (v.parsed && v.parsed.date === date) {
                        v.duplicate = true;
                        v.error = `Duplicate date: ${date}`;
                    }
                }
            }
        }

        return result;
    });

    let errorCount = $derived(validations.filter(v => !v.valid).length);
    let validDataCount = $derived(validations.filter(v => v.parsed && !v.duplicate).length);
    let hasDuplicates = $derived(validations.some(v => v.duplicate));

    // Emit valid parsed rows whenever validations change
    $effect(() => {
        const validRows = validations
            .filter(v => v.parsed && !v.duplicate)
            .map(v => v.parsed!);
        onvalidchange?.(validRows, errorCount, hasDuplicates);
    });

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleInput() {
        oninput?.(value);
        onchange?.(value);
    }

    function handleScroll() {
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

        const lineHeight = textareaEl.scrollHeight / Math.max(lineCount, 1);
        const targetScroll = (lineNumber - 1) * lineHeight - textareaEl.clientHeight / 3;
        textareaEl.scrollTo({top: Math.max(0, targetScroll), behavior: 'smooth'});

        const allLines = value.split('\n');
        let startPos = 0;
        for (let i = 0; i < lineNumber - 1 && i < allLines.length; i++) {
            startPos += allLines[i].length + 1;
        }
        const endPos = startPos + (allLines[lineNumber - 1]?.length || 0);
        textareaEl.setSelectionRange(startPos, endPos);
        textareaEl.focus();
    }

    /** Programmatically set the entire text content (for import) */
    export function setText(text: string) {
        value = text;
        handleInput();
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
            {#if hasDuplicates}
                <span class="text-amber-500 dark:text-amber-400 ml-2">• duplicate dates</span>
            {/if}
        </span>
        <span class="inline-flex items-center gap-1.5 text-gray-400 dark:text-gray-500 text-[10px]">
            {$t('csvImport.sep')} <kbd
                class="px-1.5 py-0.5 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700/50 font-mono text-xs text-gray-500 dark:text-gray-400">;</kbd>
            · {$t('csvImport.decimal')} <kbd
                class="px-1.5 py-0.5 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700/50 font-mono text-xs text-gray-500 dark:text-gray-400">.</kbd>
            / <kbd
                class="px-1.5 py-0.5 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700/50 font-mono text-xs text-gray-500 dark:text-gray-400">,</kbd>
            · {$t('csvImport.thousands')} <kbd
                class="px-1.5 py-0.5 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700/50 font-mono text-xs text-gray-500 dark:text-gray-400">_</kbd>
        </span>
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
                        {v.duplicate ? 'bg-amber-50 dark:bg-amber-900/20' : v.isHeader && v.valid ? 'bg-emerald-50 dark:bg-emerald-900/10' : v.valid ? '' : 'bg-red-50 dark:bg-red-900/20'}"
                        title={v.error || ''}
                >
                    <span class="{v.parsed && !v.duplicate ? 'text-emerald-500' : v.duplicate ? 'text-amber-500' : v.isHeader && v.valid ? 'text-emerald-600 dark:text-emerald-400' : v.valid ? 'text-gray-400 dark:text-gray-500' : 'text-red-500'}">{v.lineNumber}</span>
                </div>
            {/each}
        </div>

        <!-- Validation indicators -->
        <div class="flex-shrink-0 w-5">
            {#each validations as v}
                <div class="h-5 flex items-center justify-center text-xs leading-5" title={v.error || ''}>
                    {#if v.isHeader && v.valid}
                        <span class="text-emerald-600 dark:text-emerald-400">H</span>
                    {:else if v.parsed && !v.duplicate}
                        <span class="text-emerald-500">✓</span>
                    {:else if v.duplicate}
                        <span class="text-amber-500">⚠</span>
                    {:else if !v.valid}
                        <span class="text-red-500">✗</span>
                    {/if}
                </div>
            {/each}
        </div>

        <!-- Textarea -->
        <textarea
                autocomplete="off"
                bind:this={textareaEl}
                bind:value
                class="flex-1 font-mono text-xs leading-5 p-0 pl-2 border-0 bg-transparent text-gray-700 dark:text-gray-300 focus:ring-0 resize-y overflow-y-auto"
                oninput={handleInput}
                onscroll={handleScroll}
                {placeholder}
                readonly={isReadonly}
                spellcheck="false"
                style="min-height: {minHeight};"
                wrap="off"
        ></textarea>
    </div>
</div>

