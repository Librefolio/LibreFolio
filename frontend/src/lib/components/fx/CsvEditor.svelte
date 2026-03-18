<!--
  CsvEditor — Mini code-editor-like CSV textarea with line numbers and live validation.

  Features:
  - 2-column format: date;rate with semantic header (date;VAL1>VAL2)
  - Header parsing with > and < direction support (< is normalized)
  - Line numbers on the left
  - Live validation per row (green ✓ / red ✗)
  - Duplicate date detection (yellow highlight)
  - Parsed valid points emitted via onvalidchange callback
  - Direction detection emitted via ondirectiondetect callback
  - Scroll-to-line API for bidirectional sync with chart
  - setHeader() API for programmatic header update (swap button)
  - Error messages per line

  Uses Svelte 5 runes ($state, $derived, $props).
-->
<script lang="ts">
    import {tick} from 'svelte';
    import {t} from '$lib/i18n';

    // =========================================================================
    // Types (exported for external use)
    // =========================================================================

    export interface ParsedRow {
        date: string;
        value: number;
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
            // Both present: last one is the decimal separator
            if (lastComma > lastDot) {
                // 1.000,50 → remove dots (thousands), replace comma (decimal)
                s = s.replace(/\./g, '').replace(',', '.');
            } else {
                // 1,000.50 → remove commas (thousands)
                s = s.replace(/,/g, '');
            }
        } else if (lastComma >= 0) {
            // Only comma: treat as decimal (0,6045 → 0.6045)
            s = s.replace(',', '.');
        }

        return parseFloat(s);
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Current CSV text content (bindable) */
        value?: string;
        /** The two currencies of the page context (used for header validation) */
        allowedCurrencies: [string, string];
        /** Whether the editor is read-only */
        readonly?: boolean;
        /** Minimum height of the textarea */
        minHeight?: string;
        /** Placeholder text when textarea is empty */
        placeholder?: string;
        /** Called when valid parsed rows change */
        onvalidchange?: (validRows: ParsedRow[], errorCount: number, hasDuplicates: boolean) => void;
        /** Called when direction is detected from header */
        ondirectiondetect?: (from: string, to: string) => void;
        /** Called on every input (raw text) */
        oninput?: (text: string) => void;
        /** Called when text content changes (for bind:value replacement) */
        onchange?: (text: string) => void;
    }

    let {
        value = $bindable(''),
        allowedCurrencies,
        readonly: isReadonly = false,
        minHeight = '200px',
        placeholder = '',
        onvalidchange,
        ondirectiondetect,
        oninput,
        onchange,
    }: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let textareaEl: HTMLTextAreaElement | undefined = $state(undefined);
    let lineNumbersEl: HTMLDivElement | undefined = $state(undefined);

    // =========================================================================
    // Header parsing
    // =========================================================================

    interface HeaderResult {
        valid: true;
        from: string;
        to: string;
    }
    interface HeaderError {
        valid: false;
        error: string;
    }

    function parseHeader(line: string): HeaderResult | HeaderError {
        const trimmed = line.trim().toLowerCase();
        // Match: date;VAL1>VAL2 or date;VAL1<VAL2
        const match = trimmed.match(/^date;([a-z]{3})([><])([a-z]{3})$/);
        if (!match) return {valid: false, error: 'Invalid header format. Expected: date;' + allowedCurrencies[0] + '>' + allowedCurrencies[1]};

        const [, cur1, sep, cur2] = match;
        // Normalize: always emit the semantic from→to direction
        // date;EUR>USD → from=EUR, to=USD
        // date;USD<EUR → from=EUR, to=USD (normalized: < means read backwards)
        const from = (sep === '>' ? cur1 : cur2).toUpperCase();
        const to = (sep === '>' ? cur2 : cur1).toUpperCase();

        // Check currencies are in the allowed pair
        const allowed = new Set(allowedCurrencies);
        if (!allowed.has(from) || !allowed.has(to)) {
            return {valid: false, error: `Only ${allowedCurrencies[0]} and ${allowedCurrencies[1]} are allowed on this page`};
        }
        if (from === to) return {valid: false, error: 'Base and quote must differ'};

        return {valid: true, from, to};
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

    /** Parsed header result (null if no header found yet) */
    let headerResult = $derived.by<HeaderResult | HeaderError | null>(() => {
        // Find first non-empty line
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed) return parseHeader(trimmed);
        }
        return null;
    });

    let headerValid = $derived(headerResult !== null && headerResult.valid);

    let validations: LineValidation[] = $derived.by(() => {
        const result: LineValidation[] = lines.map((line, i): LineValidation => {
            const lineNumber = i + 1;
            const trimmed = line.trim();

            // Empty line
            if (!trimmed) return {lineNumber, text: line, valid: true};

            // Header line (first non-empty line) — validate as header
            if (i === lines.findIndex(l => l.trim() !== '')) {
                const hr = parseHeader(trimmed);
                if (hr.valid) {
                    return {lineNumber, text: line, valid: true, isHeader: true};
                } else {
                    return {lineNumber, text: line, valid: false, error: hr.error, isHeader: true};
                }
            }

            // If header is invalid, don't validate data rows
            if (!headerValid) {
                return {lineNumber, text: line, valid: false, error: 'Fix header first'};
            }

            // Parse data row (2 columns: date;rate)
            const parts = trimmed.split(';');
            if (parts.length !== 2) {
                return {lineNumber, text: line, valid: false, error: `Expected 2 columns (date;rate), got ${parts.length}`};
            }

            const [dateStr, valueStr] = parts.map(p => p.trim());

            // Validate date (YYYY-MM-DD)
            if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) {
                return {lineNumber, text: line, valid: false, error: `Invalid date format: "${dateStr}". Use YYYY-MM-DD`};
            }
            const dateObj = new Date(dateStr + 'T00:00:00Z');
            if (isNaN(dateObj.getTime())) {
                return {lineNumber, text: line, valid: false, error: `Invalid date: "${dateStr}"`};
            }

            // Validate rate (positive number — supports . , _ formatting)
            const numValue = parseNumber(valueStr);
            if (isNaN(numValue) || numValue <= 0) {
                return {lineNumber, text: line, valid: false, error: `Invalid rate: "${valueStr}". Must be > 0`};
            }

            return {
                lineNumber,
                text: line,
                valid: true,
                parsed: {date: dateStr, value: numValue, lineNumber},
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

    // Emit direction when header is valid
    $effect(() => {
        if (headerResult && headerResult.valid) {
            ondirectiondetect?.(headerResult.from, headerResult.to);
        }
    });

    // =========================================================================
    // Handlers
    // =========================================================================

    function handleInput() {
        oninput?.(value);
        onchange?.(value);
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
        const allLines = value.split('\n');
        let startPos = 0;
        for (let i = 0; i < lineNumber - 1 && i < allLines.length; i++) {
            startPos += allLines[i].length + 1; // +1 for \n
        }
        const endPos = startPos + (allLines[lineNumber - 1]?.length || 0);
        textareaEl.setSelectionRange(startPos, endPos);
        textareaEl.focus();
    }

    /** Append a new CSV row at the end */
    export function appendRow(date: string, rate: number) {
        const newLine = `${date};${rate}`;
        if (value.trim()) {
            value = value.trimEnd() + '\n' + newLine;
        } else {
            // Pre-populate with header + new line
            value = `date;${allowedCurrencies[0]}>${allowedCurrencies[1]}\n` + newLine;
        }
        handleInput();
    }

    /** Programmatically set the entire text content (for import) */
    export function setText(text: string) {
        value = text;
        handleInput();
    }

    /** Update only the header row (called by swap button). Always writes with > */
    export function setHeader(from: string, to: string) {
        const lineArray = value.split('\n');
        // Find first non-empty line (the header)
        const headerIdx = lineArray.findIndex(l => l.trim() !== '');
        if (headerIdx >= 0) {
            lineArray[headerIdx] = `date;${from}>${to}`;
        } else {
            lineArray.unshift(`date;${from}>${to}`);
        }
        value = lineArray.join('\n');
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
        <span class="text-gray-400 dark:text-gray-500">{$t('csvImport.separatorHint')}</span>
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
            bind:this={textareaEl}
            bind:value
            oninput={handleInput}
            onscroll={handleScroll}
            class="flex-1 font-mono text-xs leading-5 p-0 pl-2 border-0 bg-transparent text-gray-700 dark:text-gray-300 focus:ring-0 resize-y overflow-y-auto"
            style="min-height: {minHeight};"
            readonly={isReadonly}
            {placeholder}
            spellcheck="false"
            autocomplete="off"
            wrap="off"
        ></textarea>
    </div>
</div>

