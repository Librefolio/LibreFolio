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
        /** Other header names read as this column, tried only when `label` itself is absent. */
        aliases?: string[];
        /** Data type for validation */
        type: 'number' | 'string';
        /** Whether this column must have a non-empty value */
        required: boolean;
        /** Optional domain parser. Return null when the value is unknown/invalid. */
        parse?: (raw: string) => unknown | null;
        /** Optional validation after parsing. Return an error message when invalid. */
        validate?: (value: unknown) => string | null;
        /**
         * Part of a line's identity together with its date (or identity column): two lines are
         * duplicates only when their date and every `matchKey` value are equal. The events import
         * marks `type`, since one date holds a DIVIDEND and a SPLIT.
         */
        matchKey?: boolean;
    }

    export interface CsvIdentityDef {
        key: string;
        label: string;
        parse?: (raw: string) => string | null;
    }

    export interface DatedParsedRow {
        kind: 'dated';
        date: string;
        values: Record<string, unknown>;
        lineNumber: number;
    }

    export interface IdentifiedParsedRow {
        kind: 'identified';
        identity: string;
        values: Record<string, unknown>;
        lineNumber: number;
    }

    export type ParsedRow = DatedParsedRow | IdentifiedParsedRow;

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

        if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(s)) {
            return Number.NaN;
        }
        const value = Number(s);
        return Number.isFinite(value) ? value : Number.NaN;
    }

    /** Parse one RFC 4180-style record, including quoted separators and escaped quotes. */
    function parseRecord(line: string, separator: ';' | ','): string[] | null {
        const fields: string[] = [];
        let field = '';
        let quoted = false;

        for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
                if (quoted && line[i + 1] === '"') {
                    field += '"';
                    i++;
                } else if (quoted || field.length === 0) {
                    quoted = !quoted;
                } else {
                    field += char;
                }
            } else if (char === separator && !quoted) {
                fields.push(field);
                field = '';
            } else {
                field += char;
            }
        }
        if (quoted) return null;
        fields.push(field);
        return fields;
    }

    // =========================================================================
    // Props
    // =========================================================================

    interface Props {
        /** Column definitions (determines expected CSV structure) */
        columns: CsvColumnDef[];
        /** Primary identity column. Defaults to the legacy required date column. */
        identity?: CsvIdentityDef;
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

    let {columns, identity, value = $bindable(''), readonly: isReadonly = false, minHeight = '200px', placeholder = '', onvalidchange, oninput, onchange}: Props = $props();

    // =========================================================================
    // State
    // =========================================================================

    let textareaEl: HTMLTextAreaElement | undefined = $state(undefined);
    let lineNumbersEl: HTMLDivElement | undefined = $state(undefined);

    // =========================================================================
    // Header logic
    // =========================================================================

    /** Expected header string derived from column definitions (display-only hint) */
    let identityLabel = $derived(identity?.label ?? 'date');
    let expectedHeader = $derived(identityLabel + ';' + columns.map((c) => c.label).join(';'));

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
        /** Index of the primary identity column in the CSV header parts. */
        identityIdx: number;
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
        const record = parseRecord(line.replace(/^\uFEFF/, ''), sep);
        const parts = (record ?? []).map((p) => p.trim().toLowerCase());
        // Honour the ``A<B`` inverse-direction syntax only in canonical mode
        // (keeps backward compatibility for the FX editor use case).
        const normalizedParts = parts.map((p) => {
            const m = p.match(/^([^<\s]+)\s*<\s*([^<\s]+)$/);
            return m ? `${m[2]}>${m[1]}` : p;
        });

        const identityIdx = normalizedParts.indexOf(identityLabel.toLowerCase());
        const colIndices: Record<string, number> = {};
        const missingRequired: string[] = [];

        if (identityIdx < 0) missingRequired.push(identityLabel);

        for (const col of columns) {
            const idx = [col.label, ...(col.aliases ?? [])].map((name) => normalizedParts.indexOf(name.toLowerCase())).find((i) => i >= 0) ?? -1;
            colIndices[col.key] = idx;
            if (idx < 0 && col.required) missingRequired.push(col.label);
        }

        return {
            valid: missingRequired.length === 0,
            separator: sep,
            identityIdx,
            colIndices,
            missingRequired,
        };
    }

    function isHeaderLine(trimmed: string, sep: ';' | ','): boolean {
        // Accept as header any first non-empty line that contains the sep
        // AND has a ``date`` token. The by-name matching then decides if it's
        // actually valid (missingRequired list).
        if (!trimmed.includes(sep)) return false;
        const parts = (parseRecord(trimmed.replace(/^\uFEFF/, ''), sep) ?? [])
            .map((p) => p.trim().toLowerCase())
            .map((p) => {
                const m = p.match(/^([^<\s]+)\s*<\s*([^<\s]+)$/);
                return m ? `${m[2]}>${m[1]}` : p;
            });
        return parts.includes(identityLabel.toLowerCase());
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
                        error: $t('csvImport.errors.missingColumns', {values: {columns: hmap.missingRequired.join(', ')}}),
                    };
                }
                return {
                    lineNumber,
                    text: line,
                    valid: false,
                    isHeader: true,
                    error: $t('csvImport.errors.expectedHeader', {values: {header: expectedHeader}}),
                };
            }

            // If header is invalid, don't validate data rows
            if (!headerValid || !hmap) {
                return {lineNumber, text: line, valid: false, error: $t('csvImport.errors.fixHeaderFirst')};
            }

            // Parse data row using the by-name column mapping (I-bis #5).
            const parts = parseRecord(trimmed, sep);
            if (!parts) {
                return {lineNumber, text: line, valid: false, error: $t('csvImport.errors.invalidQuotedField')};
            }
            // NOTE: extra columns (parts.length > declared header width) are
            // accepted and silently ignored — the header decides which slots
            // matter via ``hmap.colIndices`` / ``hmap.dateIdx``.

            const identityRaw = (parts[hmap.identityIdx] ?? '').trim();
            let parsedIdentity = identityRaw;
            if (identity) {
                parsedIdentity = identity.parse ? (identity.parse(identityRaw) ?? '') : identityRaw;
                if (!identityRaw || !parsedIdentity) {
                    return {lineNumber, text: line, valid: false, error: $t('csvImport.errors.invalidIdentity', {values: {label: identity.label, value: identityRaw}})};
                }
            } else {
                if (!/^\d{4}-\d{2}-\d{2}$/.test(identityRaw)) {
                    return {lineNumber, text: line, valid: false, error: $t('csvImport.errors.invalidDateFormat', {values: {value: identityRaw}})};
                }
                const dateObj = new Date(identityRaw + 'T00:00:00Z');
                if (isNaN(dateObj.getTime())) {
                    return {lineNumber, text: line, valid: false, error: $t('csvImport.errors.invalidDate', {values: {value: identityRaw}})};
                }
            }

            // Parse each declared column by its CSV index (from header map).
            const values: Record<string, unknown> = {};
            let parseError: string | null = null;

            for (const col of columns) {
                const csvIdx = hmap.colIndices[col.key];
                const rawVal = csvIdx >= 0 ? (parts[csvIdx] ?? '').trim() : '';

                if (!rawVal) {
                    if (col.required) {
                        parseError = $t('csvImport.errors.requiredEmpty', {values: {column: col.label}});
                        break;
                    }
                    values[col.key] = null;
                    continue;
                }

                if (col.type === 'number') {
                    const num = col.parse ? col.parse(rawVal) : parseNumber(rawVal);
                    if (num === null || typeof num !== 'number' || !Number.isFinite(num)) {
                        parseError = $t('csvImport.errors.invalidNumber', {values: {column: col.label, value: rawVal}});
                        break;
                    }
                    values[col.key] = num;
                } else {
                    const parsed = col.parse ? col.parse(rawVal) : rawVal;
                    if (parsed === null) {
                        parseError = $t('csvImport.errors.invalidValue', {values: {column: col.label, value: rawVal}});
                        break;
                    }
                    values[col.key] = parsed;
                }
                const validationError = col.validate?.(values[col.key]);
                if (validationError) {
                    parseError = validationError;
                    break;
                }
            }

            if (parseError) {
                return {lineNumber, text: line, valid: false, error: parseError};
            }

            return {
                lineNumber,
                text: line,
                valid: true,
                parsed: identity ? {kind: 'identified', identity: parsedIdentity, values, lineNumber} : {kind: 'dated', date: identityRaw, values, lineNumber},
            };
        });

        // Duplicate detection: a line is keyed by its date (or identity) and its matchKey values
        const matchColumns = columns.filter((c) => c.matchKey);
        const duplicateLabel = [identityLabel, ...matchColumns.map((c) => c.label)].join(' · ');
        const duplicateKey = (parsed: ParsedRow): string => [parsed.kind === 'dated' ? parsed.date : parsed.identity, ...matchColumns.map((c) => String(parsed.values[c.key] ?? ''))].join(' · ');
        const identityCount = new Map<string, number[]>();
        for (const v of result) {
            if (v.parsed) {
                const key = duplicateKey(v.parsed);
                const indices = identityCount.get(key) ?? [];
                indices.push(v.lineNumber);
                identityCount.set(key, indices);
            }
        }
        for (const [key, indices] of identityCount) {
            if (indices.length > 1) {
                for (const v of result) {
                    if (v.parsed && duplicateKey(v.parsed) === key) {
                        v.duplicate = true;
                        v.error = $t('csvImport.errors.duplicate', {values: {label: duplicateLabel, key}});
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

<div class="csv-editor rounded-lg border border-lf-subtle overflow-hidden bg-lf-field text-lf-primary">
    <!-- Status bar -->
    <div class="flex items-center justify-between px-3 py-1.5 bg-lf-panel border-b border-lf-subtle text-xs">
        <span class="text-lf-muted">
            {validDataCount} valid row{validDataCount !== 1 ? 's' : ''}
            {#if errorCount > 0}
                <span class="text-lf-danger ml-2" data-state="invalid">• {errorCount} error{errorCount !== 1 ? 's' : ''}</span>
            {/if}
            {#if hasDuplicates}
                <span class="text-lf-warning ml-2">• duplicate {identityLabel}s</span>
            {/if}
        </span>
        <span class="inline-flex items-center gap-1.5 text-lf-muted text-[10px]">
            {$t('csvImport.sep')} <kbd class="px-1.5 py-0.5 rounded border border-lf-subtle bg-lf-card font-mono text-xs text-lf-muted">{detectedSeparator}</kbd>
            · {$t('csvImport.decimal')} <kbd class="px-1.5 py-0.5 rounded border border-lf-subtle bg-lf-card font-mono text-xs text-lf-muted">.</kbd>
            / <kbd class="px-1.5 py-0.5 rounded border border-lf-subtle bg-lf-card font-mono text-xs text-lf-muted">,</kbd>
            · {$t('csvImport.thousands')} <kbd class="px-1.5 py-0.5 rounded border border-lf-subtle bg-lf-card font-mono text-xs text-lf-muted">_</kbd>
        </span>
    </div>

    <!-- Editor area -->
    <div class="flex overflow-hidden" style="min-height: {minHeight};">
        <!-- Line numbers -->
        <div bind:this={lineNumbersEl} class="flex-shrink-0 w-10 bg-lf-panel border-r border-lf-subtle overflow-hidden select-none">
            {#each validations as v}
                <div
                    class="h-5 flex items-center justify-end pr-2 text-xs font-mono leading-5
                        {v.duplicate ? 'bg-lf-warning-soft' : v.isHeader && v.valid ? 'bg-lf-success-soft' : v.valid ? '' : 'bg-lf-danger-soft'}"
                >
                    {#if v.error}
                        <Tooltip text={v.error} position="right">
                            <span class={v.parsed && !v.duplicate ? 'text-lf-success' : v.duplicate ? 'text-lf-warning' : v.isHeader && v.valid ? 'text-lf-success' : v.valid ? 'text-lf-muted' : 'text-lf-danger'}>{v.lineNumber}</span>
                        </Tooltip>
                    {:else}
                        <span class={v.parsed && !v.duplicate ? 'text-lf-success' : v.duplicate ? 'text-lf-warning' : v.isHeader && v.valid ? 'text-lf-success' : v.valid ? 'text-lf-muted' : 'text-lf-danger'}>{v.lineNumber}</span>
                    {/if}
                </div>
            {/each}
        </div>

        <!-- Validation indicators -->
        <div class="flex-shrink-0 w-5">
            {#each validations as v}
                <div class="h-5 flex items-center justify-center text-xs leading-5">
                    {#if v.isHeader && v.valid}
                        <span class="text-lf-success">H</span>
                    {:else if v.parsed && !v.duplicate}
                        <span class="text-lf-success" data-state="valid">✓</span>
                    {:else if v.duplicate}
                        <span class="text-lf-warning">⚠</span>
                    {:else if !v.valid}
                        {#if v.error}
                            <Tooltip text={v.error} position="right">
                                <span class="text-lf-danger" data-state="invalid">✗</span>
                            </Tooltip>
                        {:else}
                            <span class="text-lf-danger" data-state="invalid">✗</span>
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
            class="flex-1 font-mono text-xs leading-5 p-0 pl-2 border-0 bg-transparent text-lf-primary placeholder:text-lf-placeholder focus:ring-0 resize-y overflow-y-auto"
            data-testid="csv-editor-input"
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
