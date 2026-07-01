<script lang="ts">
    import {browser} from '$app/environment';
    import {t} from '$lib/i18n';
    import ModalBase from '$lib/components/ui/modals/ModalBase.svelte';
    import type {FilePreviewResponse} from '$lib/types';
    import {formatBytes} from '$lib/utils/files/upload';
    import {AlertCircle, Copy, Download, Eye, FileImage, FileSpreadsheet, FileText, LoaderCircle, Minus, Plus, RotateCcw, X} from 'lucide-svelte';
    import katex from 'katex';
    import 'katex/dist/katex.min.css';

    interface Props {
        open?: boolean;
        preview?: FilePreviewResponse | null;
        loading?: boolean;
        error?: string | null;
        onRequestClose?: () => void;
        onSheetChange?: (sheetName: string) => void;
        zIndex?: number;
    }

    type CheetahGridModule = {
        ListGrid: new (options: Record<string, unknown>) => {dispose?: () => void};
    };

    let {open = false, preview = null, loading = false, error = null, onRequestClose = () => {}, onSheetChange = () => {}, zIndex = 50}: Props = $props();

    let markdownMode: 'rendered' | 'raw' = $state('rendered');
    let copied = $state(false);
    let imageZoom = $state(1);
    let imageStage: HTMLDivElement | null = $state(null);
    let imageDragging = $state(false);
    let renderedMarkdown = $state('');
    let markdownError: string | null = $state(null);
    let pdfError: string | null = $state(null);
    let tableError: string | null = $state(null);

    let pdfHost: HTMLDivElement | null = $state(null);
    let tableHost: HTMLDivElement | null = $state(null);

    let markdownToken = 0;
    let pdfToken = 0;
    let tableToken = 0;
    let imageDragPointerId: number | null = null;
    let imageDragStartX = 0;
    let imageDragStartY = 0;
    let imageDragStartScrollLeft = 0;
    let imageDragStartScrollTop = 0;

    const previewType = $derived(preview?.preview_type ?? null);
    const sizeBytes = $derived(normalizeNumber(preview?.size_bytes));
    const textContent = $derived(normalizeString(preview?.text_content));
    const textLines = $derived(textContent.length > 0 ? textContent.split('\n') : []);
    const sheetNames = $derived(normalizeStringArray(preview?.sheet_names));
    const showSheetSelector = $derived(sheetNames.length > 1);
    const tableRows = $derived(normalizeTableRows(preview?.table_rows));
    const tableCols = $derived.by(() => {
        const explicitCols = normalizeNumber(preview?.total_cols);
        return explicitCols > 0 ? explicitCols : Math.max(...tableRows.map((row) => row.length), 0);
    });
    const totalRows = $derived(normalizeNumber(preview?.total_rows));
    const totalLines = $derived(normalizeNumber(preview?.total_lines));
    const imageWidth = $derived(normalizeNumber(preview?.image_width));
    const imageHeight = $derived(normalizeNumber(preview?.image_height));
    const detectedEncoding = $derived(normalizeString(preview?.detected_encoding));
    const activeSheetName = $derived(normalizeString(preview?.active_sheet_name));
    const formattedSize = $derived(preview ? formatBytes(sizeBytes) : '');
    const encodingLabel = $derived(formatDetectedEncoding(detectedEncoding));
    const tableSizeLabel = $derived(preview ? `${totalRows} × ${tableCols}` : '');
    const imagePreviewSource = $derived(normalizeString(preview?.preview_url));
    const imageFullSource = $derived(normalizeString(preview?.source_url));
    const imageSource = $derived((imageZoom > 1 ? imageFullSource : imagePreviewSource) || imagePreviewSource || imageFullSource);
    const canPanImage = $derived(imageZoom > 1);
    const imageDisplayWidth = $derived(imageWidth > 0 ? Math.max(Math.round(imageWidth * imageZoom), 1) : null);
    const imageDisplayHeight = $derived(imageHeight > 0 ? Math.max(Math.round(imageHeight * imageZoom), 1) : null);

    $effect(() => {
        if (!open) {
            markdownMode = 'rendered';
            copied = false;
            resetImageViewport();
            renderedMarkdown = '';
            markdownError = null;
            pdfError = null;
            tableError = null;
        }
    });

    $effect(() => {
        const currentImage = open && previewType === 'image' ? normalizeString(preview?.source_url) : '';
        if (!currentImage) return;

        resetImageViewport();
        queueMicrotask(() => {
            imageStage?.scrollTo({left: 0, top: 0});
        });
    });

    $effect(() => {
        const markdownText = open && previewType === 'markdown' && markdownMode === 'rendered' ? textContent : '';
        if (!browser || !markdownText) {
            renderedMarkdown = '';
            markdownError = null;
            return;
        }

        const token = ++markdownToken;
        markdownError = null;

        void (async () => {
            try {
                const [{marked}, dompurifyModule] = await Promise.all([import('marked'), import('dompurify')]);
                const cleanHtml = dompurifyModule.default.sanitize(await marked.parse(markdownText));
                const enrichedHtml = enrichMarkdownHtml(cleanHtml);
                if (token === markdownToken) {
                    renderedMarkdown = enrichedHtml;
                }
            } catch (err) {
                if (token === markdownToken) {
                    renderedMarkdown = '';
                    markdownError = err instanceof Error ? err.message : 'Failed to render markdown';
                }
            }
        })();
    });

    $effect(() => {
        const sourceUrl = open && previewType === 'pdf' ? (preview?.source_url ?? '') : '';
        const host = pdfHost;
        if (!browser || !host || !sourceUrl) {
            if (host) host.innerHTML = '';
            pdfError = null;
            return;
        }

        const token = ++pdfToken;
        pdfError = null;
        host.innerHTML = '';

        void (async () => {
            try {
                const {default: EmbedPDF} = await import('@embedpdf/snippet');
                await Promise.resolve(
                    EmbedPDF.init({
                        type: 'container',
                        target: host,
                        src: sourceUrl,
                        disabledCategories: ['annotation'],
                        ui: {
                            disabledCategories: ['panel-comment'],
                        },
                    }),
                );
            } catch (err) {
                if (token === pdfToken) {
                    pdfError = err instanceof Error ? err.message : 'Failed to render PDF';
                    host.innerHTML = '';
                }
            }
        })();

        return () => {
            host.innerHTML = '';
        };
    });

    $effect(() => {
        const host = tableHost;
        const rows = open && previewType === 'table' ? tableRows : [];
        const cols = open && previewType === 'table' ? tableCols : 0;

        if (!browser || !host || rows.length === 0 || cols === 0) {
            if (host) host.innerHTML = '';
            tableError = null;
            return;
        }

        const token = ++tableToken;
        host.innerHTML = '';
        tableError = null;
        let gridInstance: {dispose?: () => void} | null = null;

        void (async () => {
            try {
                const cheetahGrid = (await import('cheetah-grid')) as CheetahGridModule;
                if (token !== tableToken) return;
                const tableTheme = document.documentElement.classList.contains('dark') ? buildDarkSpreadsheetTheme() : 'MATERIAL_DESIGN';

                gridInstance = new cheetahGrid.ListGrid({
                    parentElement: host,
                    frozenColCount: 1,
                    defaultRowHeight: 30,
                    theme: tableTheme,
                    header: [
                        {field: '__rowNumber', caption: '#', width: 56},
                        ...Array.from({length: cols}, (_, index) => ({
                            field: `c${index}`,
                            caption: spreadsheetColumnLabel(index),
                            width: 140,
                        })),
                    ],
                    records: rows.map((row, rowIndex) => {
                        const record: Record<string, string | number> = {__rowNumber: rowIndex + 1};
                        for (let colIndex = 0; colIndex < cols; colIndex += 1) {
                            record[`c${colIndex}`] = row[colIndex] ?? '';
                        }
                        return record;
                    }),
                });
            } catch (err) {
                if (token === tableToken) {
                    tableError = err instanceof Error ? err.message : 'Failed to render spreadsheet preview';
                    host.innerHTML = '';
                }
            }
        })();

        return () => {
            gridInstance?.dispose?.();
            host.innerHTML = '';
        };
    });

    function spreadsheetColumnLabel(index: number): string {
        let label = '';
        let current = index;

        do {
            label = String.fromCharCode(65 + (current % 26)) + label;
            current = Math.floor(current / 26) - 1;
        } while (current >= 0);

        return label;
    }

    async function copyCurrentText() {
        if (!textContent) return;

        try {
            await navigator.clipboard.writeText(textContent);
            copied = true;
            window.setTimeout(() => {
                copied = false;
            }, 1500);
        } catch {
            copied = false;
        }
    }

    function zoomIn() {
        imageZoom = Math.min(imageZoom + 0.25, 4);
    }

    function zoomOut() {
        imageZoom = Math.max(imageZoom - 0.25, 0.25);
        if (imageZoom <= 1) {
            resetImageViewport();
        }
    }

    function resetZoom() {
        resetImageViewport();
    }

    function resetImageViewport() {
        imageZoom = 1;
        imageDragging = false;
        releaseImagePointerCapture();
        imageStage?.scrollTo({left: 0, top: 0});
    }

    function startImagePan(event: PointerEvent) {
        if (!canPanImage || !imageStage) return;
        if (event.pointerType === 'mouse' && event.button !== 0) return;

        imageDragging = true;
        imageDragPointerId = event.pointerId;
        imageDragStartX = event.clientX;
        imageDragStartY = event.clientY;
        imageDragStartScrollLeft = imageStage.scrollLeft;
        imageDragStartScrollTop = imageStage.scrollTop;
        imageStage.setPointerCapture?.(event.pointerId);
        event.preventDefault();
    }

    function handleImagePan(event: PointerEvent) {
        if (!imageDragging || !imageStage || imageDragPointerId !== event.pointerId) return;

        event.preventDefault();
        imageStage.scrollLeft = imageDragStartScrollLeft - (event.clientX - imageDragStartX);
        imageStage.scrollTop = imageDragStartScrollTop - (event.clientY - imageDragStartY);
    }

    function stopImagePan(event: PointerEvent) {
        if (imageDragPointerId !== event.pointerId) return;
        imageDragging = false;
        releaseImagePointerCapture();
    }

    function releaseImagePointerCapture() {
        if (!imageStage || imageDragPointerId === null) {
            imageDragPointerId = null;
            return;
        }

        try {
            imageStage.releasePointerCapture?.(imageDragPointerId);
        } catch {
            // Ignore lost-capture races while closing the modal.
        }
        imageDragPointerId = null;
    }

    function normalizeString(value: unknown): string {
        if (typeof value === 'string') return value;
        if (Array.isArray(value)) {
            const first = value.find((item) => typeof item === 'string');
            return typeof first === 'string' ? first : '';
        }
        return '';
    }

    function normalizeNumber(value: unknown): number {
        if (typeof value === 'number') return value;
        if (Array.isArray(value)) {
            const first = value.find((item) => typeof item === 'number');
            return typeof first === 'number' ? first : 0;
        }
        return 0;
    }

    function normalizeStringArray(value: unknown): string[] {
        if (!Array.isArray(value)) return [];
        return value.filter((item): item is string => typeof item === 'string');
    }

    function normalizeTableRows(value: unknown): string[][] {
        if (!Array.isArray(value)) return [];

        const directRows = value.filter((row): row is unknown[] => Array.isArray(row));
        if (directRows.every((row) => row.every((cell) => typeof cell === 'string'))) {
            return directRows as string[][];
        }

        const nestedMatrix = directRows.find((row) => row.every((cell) => Array.isArray(cell)));
        if (nestedMatrix) {
            return nestedMatrix.filter((row): row is unknown[] => Array.isArray(row)).map((row) => row.map((cell) => (typeof cell === 'string' ? cell : '')));
        }

        return directRows.map((row) => row.map((cell) => (typeof cell === 'string' ? cell : '')));
    }

    function formatDetectedEncoding(encoding: string): string {
        const normalized = encoding.trim().toLowerCase();
        if (!normalized || normalized === 'utf-8' || normalized === 'utf-8-sig') return '';
        if (normalized === 'latin-1') return 'Latin-1';
        if (normalized === 'cp1252') return 'Windows-1252';
        return normalized.toUpperCase();
    }

    function enrichMarkdownHtml(html: string): string {
        if (!browser || !html) return html;

        const documentFragment = new DOMParser().parseFromString(html, 'text/html');
        renderMarkdownBlockMath(documentFragment);
        renderMarkdownInlineMath(documentFragment);
        return documentFragment.body.innerHTML;
    }

    function renderMarkdownBlockMath(documentFragment: Document): void {
        for (const paragraph of Array.from(documentFragment.body.querySelectorAll('p'))) {
            if (paragraph.children.length > 0) continue;

            const content = paragraph.textContent?.trim() ?? '';
            if (!content.startsWith('$$') || !content.endsWith('$$')) continue;

            const formula = content.slice(2, -2).trim();
            if (!formula) continue;

            paragraph.innerHTML = katex.renderToString(formula, {
                throwOnError: false,
                displayMode: true,
            });
            paragraph.classList.add('markdown-math-block');
        }
    }

    function renderMarkdownInlineMath(documentFragment: Document): void {
        const walker = documentFragment.createTreeWalker(documentFragment.body, NodeFilter.SHOW_TEXT);
        const textNodes: Text[] = [];

        let currentNode = walker.nextNode();
        while (currentNode) {
            const textNode = currentNode as Text;
            if (shouldRenderInlineMath(textNode)) {
                textNodes.push(textNode);
            }
            currentNode = walker.nextNode();
        }

        for (const textNode of textNodes) {
            replaceInlineMath(documentFragment, textNode);
        }
    }

    function shouldRenderInlineMath(textNode: Text): boolean {
        const parent = textNode.parentElement;
        const text = textNode.nodeValue ?? '';
        if (!parent || !text.includes('$')) return false;
        return !parent.closest('code, pre, .katex, .katex-display');
    }

    function replaceInlineMath(documentFragment: Document, textNode: Text): void {
        const content = textNode.nodeValue ?? '';
        const matches = Array.from(content.matchAll(/\$([^$\n]+?)\$/g));
        if (matches.length === 0) return;

        const fragment = documentFragment.createDocumentFragment();
        let cursor = 0;

        for (const match of matches) {
            const fullMatch = match[0];
            const formula = match[1];
            const start = match.index ?? -1;
            if (start < cursor) continue;

            if (start > cursor) {
                fragment.append(documentFragment.createTextNode(content.slice(cursor, start)));
            }

            const wrapper = documentFragment.createElement('span');
            wrapper.innerHTML = katex.renderToString(formula, {
                throwOnError: false,
                displayMode: false,
            });
            while (wrapper.firstChild) {
                fragment.append(wrapper.firstChild);
            }

            cursor = start + fullMatch.length;
        }

        if (cursor < content.length) {
            fragment.append(documentFragment.createTextNode(content.slice(cursor)));
        }

        textNode.parentNode?.replaceChild(fragment, textNode);
    }

    function buildDarkSpreadsheetTheme() {
        return {
            color: '#e2e8f0',
            frozenRowsColor: '#cbd5e1',
            defaultBgColor: '#0f172a',
            frozenRowsBgColor: '#111827',
            selectionBgColor: 'rgba(37, 99, 235, 0.38)',
            highlightBgColor: '#1e293b',
            borderColor: '#334155',
            frozenRowsBorderColor: '#475569',
            highlightBorderColor: '#60a5fa',
            checkbox: {
                uncheckBgColor: '#0f172a',
                checkBgColor: '#2563eb',
                borderColor: '#64748b',
            },
            radioButton: {
                checkColor: '#60a5fa',
                checkBorderColor: '#60a5fa',
                uncheckBorderColor: '#64748b',
                uncheckBgColor: '#0f172a',
                checkBgColor: '#0f172a',
            },
            button: {
                color: '#e2e8f0',
                bgColor: '#2563eb',
            },
            tree: {
                lineColor: '#475569',
            },
            header: {
                sortArrowColor: '#94a3b8',
            },
            messages: {
                infoBgColor: '#1d4ed8',
                errorBgColor: '#b91c1c',
                warnBgColor: '#b45309',
            },
            indicators: {
                topLeftColor: '#475569',
            },
            underlayBackgroundColor: '#0f172a',
        };
    }
</script>

<ModalBase {open} {onRequestClose} maxWidth="5xl" contentClass="file-preview-modal" testId="file-preview-modal" {zIndex}>
    <div class="preview-shell">
        <div class="preview-header">
            <div class="preview-heading">
                <div class="preview-title-row">
                    {#if previewType === 'image'}
                        <FileImage size={18} />
                    {:else if previewType === 'table'}
                        <FileSpreadsheet size={18} />
                    {:else}
                        <FileText size={18} />
                    {/if}
                    <h3 class="preview-title">{preview?.filename || $t('common.preview')}</h3>
                </div>

                {#if preview}
                    <div class="preview-meta">
                        <span>{preview.mime_type}</span>
                        <span>•</span>
                        <span>{formattedSize}</span>
                        {#if previewType === 'text' || previewType === 'markdown'}
                            <span>•</span>
                            <span>{totalLines} {$t('uploads.previewLines')}</span>
                            {#if encodingLabel}
                                <span>•</span>
                                <span>{encodingLabel}</span>
                            {/if}
                        {:else if previewType === 'table'}
                            <span>•</span>
                            <span>{tableSizeLabel}</span>
                        {:else if previewType === 'image'}
                            <span>•</span>
                            <span>{imageWidth} × {imageHeight}</span>
                        {/if}
                    </div>
                {/if}
            </div>

            <div class="preview-actions">
                {#if previewType === 'markdown'}
                    <div class="preview-toggle" data-testid="file-preview-markdown-toggle">
                        <button class:active={markdownMode === 'rendered'} onclick={() => (markdownMode = 'rendered')} type="button" data-testid="file-preview-markdown-rendered-btn">
                            {$t('uploads.previewRendered')}
                        </button>
                        <button class:active={markdownMode === 'raw'} onclick={() => (markdownMode = 'raw')} type="button" data-testid="file-preview-markdown-raw-btn">
                            {$t('uploads.previewRaw')}
                        </button>
                    </div>
                {/if}

                {#if previewType === 'image'}
                    <div class="preview-toggle">
                        <button type="button" onclick={zoomOut} aria-label={$t('uploads.previewZoomOut')}>
                            <Minus size={16} />
                        </button>
                        <button type="button" onclick={resetZoom} aria-label={$t('common.reset')}>
                            <RotateCcw size={16} />
                        </button>
                        <button type="button" onclick={zoomIn} aria-label={$t('uploads.previewZoomIn')} data-testid="file-preview-zoom-in">
                            <Plus size={16} />
                        </button>
                    </div>
                {/if}

                {#if preview && (previewType === 'text' || previewType === 'markdown')}
                    <button class="icon-btn" type="button" onclick={copyCurrentText} title={$t('uploads.previewCopy')} data-testid="file-preview-copy">
                        <Copy size={16} />
                        <span>{copied ? $t('common.copied') : $t('uploads.previewCopy')}</span>
                    </button>
                {/if}

                {#if preview}
                    <a class="icon-btn" href={preview.download_url} download={preview.filename} data-testid="file-preview-download">
                        <Download size={16} />
                        <span>{$t('uploads.download')}</span>
                    </a>
                {/if}

                <button class="close-btn" type="button" onclick={onRequestClose} aria-label={$t('common.close')}>
                    <X size={18} />
                </button>
            </div>
        </div>

        {#if loading}
            <div class="preview-state">
                <div class="preview-spinner">
                    <LoaderCircle size={28} />
                </div>
                <p>{$t('common.loading')}</p>
            </div>
        {:else if error}
            <div class="preview-state error-state">
                <AlertCircle size={28} />
                <p>{error}</p>
            </div>
        {:else if preview}
            <div class="preview-body">
                {#if previewType === 'image'}
                    <div class="image-stage" class:pannable={canPanImage} class:dragging={imageDragging} bind:this={imageStage} data-testid="file-preview-image" onpointerdown={startImagePan} onpointermove={handleImagePan} onpointerup={stopImagePan} onpointercancel={stopImagePan}>
                        <div class="image-canvas">
                            <img src={imageSource} alt={preview.filename} width={imageDisplayWidth ?? undefined} height={imageDisplayHeight ?? undefined} draggable="false" decoding="async" />
                        </div>
                    </div>
                {:else if previewType === 'pdf'}
                    {#if pdfError}
                        <div class="preview-inline-error">
                            <AlertCircle size={18} />
                            <span>{$t('uploads.previewFallbackPdf')}</span>
                        </div>
                        <iframe class="pdf-fallback" src={preview.source_url} title={preview.filename} data-testid="file-preview-pdf-fallback"></iframe>
                    {:else}
                        <div class="pdf-stage" bind:this={pdfHost} data-testid="file-preview-pdf"></div>
                    {/if}
                {:else if previewType === 'table'}
                    <div class="table-stage">
                        <div class="table-toolbar">
                            {#if showSheetSelector}
                                <label>
                                    <span>{$t('uploads.previewSheet')}</span>
                                    <select value={activeSheetName} onchange={(event) => onSheetChange((event.currentTarget as HTMLSelectElement).value)} data-testid="file-preview-sheet-select">
                                        {#each sheetNames as sheetName}
                                            <option value={sheetName}>{sheetName}</option>
                                        {/each}
                                    </select>
                                </label>
                            {/if}

                            <div class="table-summary">
                                <Eye size={16} />
                                <span>{tableSizeLabel}</span>
                            </div>
                        </div>

                        {#if tableError}
                            <div class="preview-inline-error">
                                <AlertCircle size={18} />
                                <span>{$t('uploads.previewFallbackTable')}</span>
                            </div>
                            <div class="table-fallback">
                                <table>
                                    <tbody>
                                        {#each tableRows as row}
                                            <tr>
                                                {#each row as cell}
                                                    <td>{cell}</td>
                                                {/each}
                                            </tr>
                                        {/each}
                                    </tbody>
                                </table>
                            </div>
                        {:else}
                            <div class="grid-host" bind:this={tableHost} data-testid="file-preview-grid"></div>
                        {/if}
                    </div>
                {:else if previewType === 'markdown' && markdownMode === 'rendered'}
                    {#if markdownError}
                        <div class="preview-inline-error">
                            <AlertCircle size={18} />
                            <span>{markdownError}</span>
                        </div>
                    {/if}
                    <div class="markdown-stage" data-testid="file-preview-markdown-rendered">
                        {@html renderedMarkdown}
                    </div>
                {:else}
                    <div class="text-stage" data-testid="file-preview-text">
                        <div class="text-lines">
                            {#each textLines as line, index}
                                <div class="text-line">
                                    <span class="line-number">{index + 1}</span>
                                    <code>{line || ' '}</code>
                                </div>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>
        {:else}
            <div class="preview-state">
                <p>{$t('common.noData')}</p>
            </div>
        {/if}
    </div>
</ModalBase>

<style>
    .preview-shell {
        display: flex;
        flex-direction: column;
        height: 100%;
        min-height: 0;
        overflow: hidden;
    }

    .preview-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 1rem;
        border-bottom: 1px solid #e5e7eb;
        padding: 1rem 1.25rem;
        flex-shrink: 0;
    }

    .preview-heading {
        min-width: 0;
    }

    .preview-title-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-weight: 600;
    }

    .preview-title {
        margin: 0;
        font-size: 1.05rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .preview-meta {
        margin-top: 0.35rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        color: #64748b;
        font-size: 0.85rem;
    }

    .preview-actions {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .preview-toggle {
        display: inline-flex;
        align-items: center;
        border: 1px solid #cbd5e1;
        border-radius: 0.5rem;
        overflow: hidden;
    }

    .preview-toggle button,
    .icon-btn,
    .close-btn {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        border: none;
        background: white;
        color: #0f172a;
        cursor: pointer;
        text-decoration: none;
        padding: 0.55rem 0.8rem;
        font-size: 0.85rem;
    }

    .preview-toggle button.active {
        background: #1a4031;
        color: white;
    }

    .icon-btn,
    .close-btn {
        border: 1px solid #cbd5e1;
        border-radius: 0.5rem;
    }

    .close-btn {
        padding-inline: 0.65rem;
    }

    .preview-body {
        display: flex;
        flex-direction: column;
        flex: 1;
        min-height: 0;
        padding: 1rem 1.25rem 1.25rem;
        overflow: hidden;
        overscroll-behavior: contain;
    }

    .preview-state,
    .preview-inline-error {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        padding: 1.25rem;
        color: #64748b;
    }

    .preview-inline-error {
        justify-content: flex-start;
        padding-inline: 0;
        color: #b45309;
    }

    .error-state {
        color: #dc2626;
    }

    .preview-spinner {
        display: inline-flex;
        animation: spin 1s linear infinite;
    }

    .preview-spinner :global(svg) {
        animation: spin 1s linear infinite;
    }

    .image-stage,
    .pdf-stage,
    .pdf-fallback,
    .table-stage,
    .text-stage,
    .markdown-stage {
        flex: 1;
        min-height: 0;
    }

    .image-stage {
        overflow: auto;
        border-radius: 0.75rem;
        background: #f8fafc;
        padding: 1rem;
        overscroll-behavior: contain;
    }

    .image-stage.pannable {
        cursor: grab;
        touch-action: none;
    }

    .image-stage.dragging,
    .image-stage.dragging * {
        cursor: grabbing;
    }

    .image-canvas {
        width: max-content;
        min-width: 100%;
        min-height: 100%;
        display: flex;
        justify-content: center;
        align-items: flex-start;
    }

    .image-stage img {
        display: block;
        max-width: none;
        user-select: none;
        -webkit-user-drag: none;
        transition:
            width 0.12s ease,
            height 0.12s ease;
    }

    .pdf-stage,
    .pdf-fallback,
    .grid-host,
    .table-fallback {
        width: 100%;
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        background: white;
        overscroll-behavior: contain;
    }

    .pdf-stage,
    .pdf-fallback {
        border-color: #cbd5e1;
    }

    .pdf-stage,
    .pdf-fallback,
    .grid-host,
    .table-fallback {
        flex: 1;
        min-height: 0;
        height: auto;
    }

    .table-stage {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .table-toolbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        color: #64748b;
        font-size: 0.85rem;
    }

    .table-toolbar label {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
    }

    .table-toolbar select {
        border: 1px solid #cbd5e1;
        border-radius: 0.45rem;
        background: white;
        padding: 0.4rem 0.6rem;
        color: inherit;
    }

    .table-summary {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }

    .table-fallback {
        overflow: auto;
    }

    .table-fallback table {
        width: max-content;
        min-width: 100%;
        border-collapse: collapse;
    }

    .table-fallback td {
        border: 1px solid #e2e8f0;
        padding: 0.45rem 0.6rem;
        white-space: nowrap;
    }

    .text-stage {
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        background: white;
        color: #0f172a;
        overflow: auto;
        padding: 0.75rem 0 1rem;
        overscroll-behavior: contain;
    }

    .text-lines {
        display: flex;
        flex-direction: column;
        padding-block: 0.25rem;
    }

    .text-line {
        display: grid;
        grid-template-columns: 3rem minmax(0, 1fr);
        gap: 0.9rem;
        padding: 0.15rem 1.25rem 0.15rem 1.5rem;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 0.85rem;
        line-height: 1.55;
    }

    .text-line:hover {
        background: #f8fafc;
    }

    .line-number {
        color: #64748b;
        text-align: right;
        user-select: none;
    }

    .text-line code {
        white-space: pre-wrap;
        word-break: break-word;
        color: inherit;
        background: transparent;
        padding: 0;
    }

    .markdown-stage {
        overflow: auto;
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        background: white;
        padding: 1.25rem;
        overscroll-behavior: contain;
        color: #0f172a;
        line-height: 1.7;
    }

    .markdown-stage :global(h1),
    .markdown-stage :global(h2),
    .markdown-stage :global(h3) {
        margin-top: 1.2rem;
        margin-bottom: 0.6rem;
        line-height: 1.25;
        font-weight: 700;
    }

    .markdown-stage :global(h1) {
        font-size: 1.8rem;
    }

    .markdown-stage :global(h2) {
        font-size: 1.45rem;
    }

    .markdown-stage :global(h3) {
        font-size: 1.15rem;
    }

    .markdown-stage :global(h1:first-child),
    .markdown-stage :global(h2:first-child),
    .markdown-stage :global(h3:first-child),
    .markdown-stage :global(p:first-child) {
        margin-top: 0;
    }

    .markdown-stage :global(p),
    .markdown-stage :global(ul),
    .markdown-stage :global(ol) {
        margin: 0.75rem 0;
    }

    .markdown-stage :global(ul),
    .markdown-stage :global(ol) {
        padding-left: 1.4rem;
    }

    .markdown-stage :global(li + li) {
        margin-top: 0.35rem;
    }

    .markdown-stage :global(blockquote) {
        margin: 1rem 0;
        border-left: 4px solid #cbd5e1;
        border-radius: 0.5rem;
        background: #f8fafc;
        padding: 0.3rem 1rem;
        color: #475569;
    }

    .markdown-stage :global(table) {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
    }

    .markdown-stage :global(th),
    .markdown-stage :global(td) {
        border: 1px solid #e2e8f0;
        padding: 0.55rem 0.7rem;
        text-align: left;
        vertical-align: top;
    }

    .markdown-stage :global(th) {
        background: #f8fafc;
        font-weight: 600;
    }

    .markdown-stage :global(pre) {
        margin: 1rem 0;
        overflow: auto;
        border-radius: 0.75rem;
        background: #0f172a;
        color: #e2e8f0;
        padding: 1rem;
    }

    .markdown-stage :global(code) {
        background: #f1f5f9;
        border-radius: 0.35rem;
        padding: 0.1rem 0.3rem;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }

    .markdown-stage :global(pre code) {
        background: transparent;
        color: inherit;
        padding: 0;
    }

    .markdown-stage :global(hr) {
        border: none;
        border-top: 1px solid #e2e8f0;
        margin: 1.25rem 0;
    }

    .markdown-stage :global(.markdown-math-block) {
        overflow-x: auto;
    }

    .markdown-stage :global(.katex-display) {
        margin: 0.75rem 0;
    }

    :global(.dark) .preview-header {
        border-bottom-color: #334155;
    }

    :global(.dark) .preview-meta,
    :global(.dark) .table-toolbar,
    :global(.dark) .preview-state {
        color: #cbd5e1;
    }

    :global(.dark) .preview-toggle,
    :global(.dark) .icon-btn,
    :global(.dark) .close-btn,
    :global(.dark) .table-toolbar select,
    :global(.dark) .grid-host,
    :global(.dark) .table-fallback,
    :global(.dark) .markdown-stage {
        background: #0f172a;
        border-color: #334155;
        color: #e2e8f0;
    }

    :global(.dark) .pdf-stage,
    :global(.dark) .pdf-fallback {
        background: #0f172a;
        border-color: #475569;
        color: #e2e8f0;
    }

    :global(.dark) .preview-toggle button {
        background: #0f172a;
        color: #e2e8f0;
    }

    :global(.dark) .preview-toggle button.active {
        background: #1a4031;
    }

    :global(.dark) .image-stage {
        background: #0f172a;
    }

    :global(.dark) .text-stage {
        background: #111827;
        border-color: #334155;
        color: #e2e8f0;
    }

    :global(.dark) .text-line:hover {
        background: #1e293b;
    }

    :global(.dark) .table-fallback td {
        border-color: #334155;
    }

    :global(.dark) .markdown-stage :global(blockquote) {
        background: #1e293b;
        border-left-color: #475569;
        color: #cbd5e1;
    }

    :global(.dark) .markdown-stage :global(th),
    :global(.dark) .markdown-stage :global(td) {
        border-color: #334155;
    }

    :global(.dark) .markdown-stage :global(th) {
        background: #1e293b;
    }

    :global(.dark) .markdown-stage :global(code) {
        background: #1e293b;
    }

    :global(.file-preview-modal) {
        height: min(86dvh, 58rem);
        max-height: calc(100dvh - 2rem);
    }

    @keyframes spin {
        from {
            transform: rotate(0deg);
        }

        to {
            transform: rotate(360deg);
        }
    }
</style>
