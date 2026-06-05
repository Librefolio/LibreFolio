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
    import Tooltip from '$lib/components/ui/feedback/Tooltip.svelte';

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

    let {columns, value = $bindable(''), readonly: isReadonly = false, minHeight = '200px', placeholder = '', onvalidchange, oninput, onchange}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let textareaEl: HTMLTextAreaElement | undefined = $state(undefined);
    let lineNumbersEl: HTMLDivElement | undefined = $state(undefined);

    // =========================================================================
    // Header logic
    // =========================================================================

    /** Expected header string derived from column definitions (display-only hint) */
    let expectedHeader = $derived('date;' + columns.map((c) => c.label).join(';'));

    // -------------------------------------------------------------------------
    // I-bis #5 (Batch 4.d-part3) — CSV resilience
    //
    // 1. Separator auto-detect: accept both ``;`` (editor native) and ``,``
    //    (export format from ``/backup/asset/{id}/prices?format=csv``). The
    //    first non-empty line is inspected; if it starts with ``date`` + sep,
    //    the sep is locked. This supports round-trip export→import without
    //    any manual normalization on the user side.
    //
    // 2. Tolerant header matching: columns are matched by **label name**
    //    (case-insensitive), NOT by positional index. Extra columns in the
    //    CSV that are not declared in ``columns`` prop are silently ignored
    //    (e.g. ``source_plugin_key``, ``fetched_at`` emitted by the export
    //    endpoint). Missing required columns produce a single consolidated
    //    error listing the missing labels.
    //
    // 3. The ``<`` inverse-direction trick (A<B ≡ B>A) is still honoured but
    //    only for the canonical header ordering — it degrades to a no-op
    //    once the new by-name mapping kicks in.
    // -------------------------------------------------------------------------

    interface HeaderMap {
        valid: boolean;
        separator: ';' | ',';
        /** Index of the ``date`` column in the CSV header parts (-1 = missing) */
        dateIdx: number;
        /** Mapping CsvColumnDef.key → column index in CSV (-1 = not present) */
        colIndices: Record<string, number>;
        /** Required column labels that are absent (including ``date``) */
        missingRequired: string[];
    }

    /** Detect the field separator from the first non-empty line. */
    function detectSeparator(rawLines: string[]): ';' | ',' {
        for (const line of rawLines) {
            const t = line.trim().toLowerCase();
            if (!t) continue;
            // Canonical case: header starts with "date" + sep
            if (t.startsWith('date;')) return ';';
            if (t.startsWith('date,')) return ',';
            // Fallback: whichever appears first in the line
            const iSemi = t.indexOf(';');
            const iComma = t.indexOf(',');
            if (iSemi >= 0 && (iComma < 0 || iSemi < iComma)) return ';';
            if (iComma >= 0) return ',';
            return ';';
        }
        return ';';
    }

    /** Parse a header line into a HeaderMap, resolving columns by name. */
    function parseHeaderLine(line: string, sep: ';' | ','): HeaderMap {
        const parts = line.split(sep).map((p) => p.trim().toLowerCase());
        // Honour the ``A<B`` inverse-direction syntax only in canonical mode
        // (keeps backward compatibility for the FX editor use case).
        const normalizedParts = parts.map((p) => {
            const m = p.match(/^([^<\s]+)\s*<\s*([^<\s]+)$/);
            return m ? `${m[2]}>${m[1]}` : p;
        });

        const dateIdx = normalizedParts.indexOf('date');
        const colIndices: Record<string, number> = {};
        const missingRequired: string[] = [];

        if (dateIdx < 0) missingRequired.push('date');

        for (const col of columns) {
            const idx = normalizedParts.indexOf(col.label.toLowerCase());
            colIndices[col.key] = idx;
            if (idx < 0 && col.required) missingRequired.push(col.label);
        }

        return {
            valid: missingRequired.length === 0,
            separator: sep,
            dateIdx,
            colIndices,
            missingRequired,
        };
    }

    function isHeaderLine(trimmed: string, sep: ';' | ','): boolean {
        // Accept as header any first non-empty line that contains the sep
        // AND has a ``date`` token. The by-name matching then decides if it's
        // actually valid (missingRequired list).
        if (!trimmed.includes(sep)) return false;
        const parts = trimmed
            .split(sep)
            .map((p) => p.trim().toLowerCase())
            .map((p) => {
                const m = p.match(/^([^<\s]+)\s*<\s*([^<\s]+)$/);
                return m ? `${m[2]}>${m[1]}` : p;
            });
        return parts.includes('date');
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

    /** Separator auto-detected from the first non-empty line. */
    let detectedSeparator = $derived(detectSeparator(lines));

    /** Parsed header info (by-name matching, tolerant to extra columns). */
    let headerMap: HeaderMap | null = $derived.by(() => {
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            if (!isHeaderLine(trimmed, detectedSeparator)) return null;
            return parseHeaderLine(trimmed, detectedSeparator);
        }
        return null;
    });

    /** Check if header is present and valid (all required columns matched). */
    let headerValid = $derived(headerMap !== null && headerMap.valid);

    let validations: LineValidation[] = $derived.by(() => {
        const sep = detectedSeparator;
        const hmap = headerMap;
        const result: LineValidation[] = lines.map((line, i): LineValidation => {
            const lineNumber = i + 1;
            const trimmed = line.trim();

            // Empty line
            if (!trimmed) return {lineNumber, text: line, valid: true};

            // Header line (first non-empty line) — validate as header
            if (i === lines.findIndex((l) => l.trim() !== '')) {
                if (hmap && hmap.valid) {
                    return {lineNumber, text: line, valid: true, isHeader: true};
                }
                if (hmap && !hmap.valid) {
                    // Header parsed but missing required columns
                    return {
                        lineNumber,
                        text: line,
                        valid: false,
                        isHeader: true,
                        error: `Missing required columns: ${hmap.missingRequired.join(', ')}`,
                    };
                }
                return {
                    lineNumber,
                    text: line,
                    valid: false,
                    isHeader: true,
                    error: `Expected header: ${expectedHeader}`,
                };
            }

            // If header is invalid, don't validate data rows
            if (!headerValid || !hmap) {
                return {lineNumber, text: line, valid: false, error: 'Fix header first'};
            }

            // Parse data row using the by-name column mapping (I-bis #5).
            const parts = trimmed.split(sep);
            // NOTE: extra columns (parts.length > declared header width) are
            // accepted and silently ignored — the header decides which slots
            // matter via ``hmap.colIndices`` / ``hmap.dateIdx``.

            const dateStr = (parts[hmap.dateIdx] ?? '').trim();

            // Validate date (YYYY-MM-DD)
            if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
                return {lineNumber, text: line, valid: false, error: `Invalid date format: "${dateStr}". Use YYYY-MM-DD`};
            }
            const dateObj = new Date(dateStr + 'T00:00:00Z');
            if (isNaN(dateObj.getTime())) {
                return {lineNumber, text: line, valid: false, error: `Invalid date: "${dateStr}"`};
            }

            // Parse each declared column by its CSV index (from header map).
            const values: Record<string, unknown> = {};
            let parseError: string | null = null;

            for (const col of columns) {
                const csvIdx = hmap.colIndices[col.key];
                const rawVal = csvIdx >= 0 ? (parts[csvIdx] ?? '').trim() : '';

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

    let errorCount = $derived(validations.filter((v) => !v.valid).length);
    let validDataCount = $derived(validations.filter((v) => v.parsed && !v.duplicate).length);
    let hasDuplicates = $derived(validations.some((v) => v.duplicate));

    // Emit valid parsed rows whenever validations change
    $effect(() => {
        const validRows = validations.filter((v) => v.parsed && !v.duplicate).map((v) => v.parsed!);
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
            {$t('csvImport.sep')} <kbd class="px-1.5 py-0.5 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700/50 font-mono text-xs text-gray-500 dark:text-gray-400">{detectedSeparator}</kbd>
            · {$t('csvImport.decimal')} <kbd class="px-1.5 py-0.5 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700/50 font-mono text-xs text-gray-500 dark:text-gray-400">.</kbd>
            / <kbd class="px-1.5 py-0.5 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700/50 font-mono text-xs text-gray-500 dark:text-gray-400">,</kbd>
            · {$t('csvImport.thousands')} <kbd class="px-1.5 py-0.5 rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700/50 font-mono text-xs text-gray-500 dark:text-gray-400">_</kbd>
        </span>
    </div>

    <!-- Editor area -->
    <div class="flex overflow-hidden" style="min-height: {minHeight};">
        <!-- Line numbers -->
        <div bind:this={lineNumbersEl} class="flex-shrink-0 w-10 bg-gray-50 dark:bg-slate-700/30 border-r border-gray-200 dark:border-slate-600 overflow-hidden select-none">
            {#each validations as v}
                <div
                    class="h-5 flex items-center justify-end pr-2 text-xs font-mono leading-5
                        {v.duplicate ? 'bg-amber-50 dark:bg-amber-900/20' : v.isHeader && v.valid ? 'bg-emerald-50 dark:bg-emerald-900/10' : v.valid ? '' : 'bg-red-50 dark:bg-red-900/20'}"
                >
                    {#if v.error}
                        <Tooltip text={v.error} position="right">
                            <span class={v.parsed && !v.duplicate ? 'text-emerald-500' : v.duplicate ? 'text-amber-500' : v.isHeader && v.valid ? 'text-emerald-600 dark:text-emerald-400' : v.valid ? 'text-gray-400 dark:text-gray-500' : 'text-red-500'}>{v.lineNumber}</span>
                        </Tooltip>
                    {:else}
                        <span class={v.parsed && !v.duplicate ? 'text-emerald-500' : v.duplicate ? 'text-amber-500' : v.isHeader && v.valid ? 'text-emerald-600 dark:text-emerald-400' : v.valid ? 'text-gray-400 dark:text-gray-500' : 'text-red-500'}>{v.lineNumber}</span>
                    {/if}
                </div>
            {/each}
        </div>

        <!-- Validation indicators -->
        <div class="flex-shrink-0 w-5">
            {#each validations as v}
                <div class="h-5 flex items-center justify-center text-xs leading-5">
                    {#if v.isHeader && v.valid}
                        <span class="text-emerald-600 dark:text-emerald-400">H</span>
                    {:else if v.parsed && !v.duplicate}
                        <span class="text-emerald-500">✓</span>
                    {:else if v.duplicate}
                        <span class="text-amber-500">⚠</span>
                    {:else if !v.valid}
                        {#if v.error}
                            <Tooltip text={v.error} position="right">
                                <span class="text-red-500">✗</span>
                            </Tooltip>
                        {:else}
                            <span class="text-red-500">✗</span>
                        {/if}
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
