// @vitest-environment jsdom
/**
 * FilePreviewModal — component test (Vitest + jsdom).
 *
 * Why a component test and not E2E: the modal is a pure controlled component. It
 * takes a `FilePreviewResponse` (or `loading` / `error`) in through props and
 * renders a header (icon + meta), a set of type-dependent action buttons, and one
 * of five bodies (image / pdf / table / markdown / text). The only things that
 * leave are `onRequestClose()` and `onSheetChange(name)`.
 *
 * The heavy renderers — EmbedPDF, cheetah-grid, marked+DOMPurify+KaTeX — all live
 * inside `$effect`s gated on `browser`, and the jsdom mock ships `browser = false`
 * (`src/__mocks__/$app/environment.ts`). So in this environment every async
 * renderer short-circuits and leaves its mount node empty, which is exactly what
 * makes the *synchronous* surface — the branch that picks a body per `preview_type`,
 * the meta line, the per-type action set, the zoom maths, the text/line split and
 * the encoding/label deriveds — reachable and deterministic from props alone.
 *
 * What it deliberately does NOT assert:
 *   - translated text. Titles, button labels and the "lines"/"sheet" captions come
 *     from the four-language catalogue. Every value asserted below is one the test
 *     itself passed in (`mime_type`, the "W × H" numbers, `error`) or a literal the
 *     component's own code returns (`Latin-1`, `Windows-1252`), never a translation.
 *   - the async-rendered content. The PDF canvas, the cheetah grid and the parsed
 *     markdown HTML are E2E's job (files.spec.ts already drives them in a real
 *     browser); here we assert only that the correct *mount node* is chosen.
 *   - CSS classes. Zoom is asserted through the <img> width attribute and its src,
 *     both semantic, neither a class.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import FilePreviewModal from './FilePreviewModal.svelte';

// jsdom does not implement Element.scrollTo; the image viewport reset calls it on
// mount. Real browsers have it (files.spec.ts drives the same path in Chromium), so
// this is an environment shim, not a product concern.
beforeAll(() => {
    HTMLElement.prototype.scrollTo = vi.fn();
});

/** Minimal-but-valid FilePreviewResponse per type; every builder is overridable. */
type Preview = Record<string, unknown>;

function imagePreview(over: Preview = {}): Preview {
    return {
        preview_type: 'image',
        filename: 'photo.png',
        mime_type: 'image/png',
        size_bytes: 2048,
        source_url: '/files/photo-full.png',
        preview_url: '/files/photo-thumb.png',
        download_url: '/download/photo.png',
        image_width: 100,
        image_height: 80,
        ...over,
    };
}

function textPreview(over: Preview = {}): Preview {
    return {
        preview_type: 'text',
        filename: 'notes.txt',
        mime_type: 'text/plain',
        size_bytes: 42,
        source_url: '/files/notes.txt',
        download_url: '/download/notes.txt',
        text_content: 'alpha\nbeta\ngamma',
        total_lines: 3,
        detected_encoding: 'utf-8',
        ...over,
    };
}

function markdownPreview(over: Preview = {}): Preview {
    return {
        preview_type: 'markdown',
        filename: 'readme.md',
        mime_type: 'text/markdown',
        size_bytes: 64,
        source_url: '/files/readme.md',
        download_url: '/download/readme.md',
        text_content: '# Title\n\nbody line',
        total_lines: 3,
        detected_encoding: 'utf-8',
        ...over,
    };
}

function tablePreview(over: Preview = {}): Preview {
    return {
        preview_type: 'table',
        filename: 'book.xlsx',
        mime_type: 'application/vnd.ms-excel',
        size_bytes: 512,
        source_url: '/files/book.xlsx',
        download_url: '/download/book.xlsx',
        table_rows: [
            ['a', 'b', 'c', 'd'],
            ['1', '2', '3', '4'],
        ],
        total_rows: 2,
        total_cols: 4,
        sheet_names: ['Sheet1', 'Sheet2'],
        active_sheet_name: 'Sheet1',
        ...over,
    };
}

function mount(props: Preview = {}) {
    const onRequestClose = vi.fn();
    const onSheetChange = vi.fn();
    const utils = render(FilePreviewModal, {open: true, onRequestClose, onSheetChange, ...props});
    return {onRequestClose, onSheetChange, ...utils};
}

const shell = () => screen.getByTestId('file-preview-shell');

describe('FilePreviewModal — body selection per type', () => {
    it('renders the image body and its meta, with no text-only actions', async () => {
        await setupI18n();
        mount({preview: imagePreview()});

        expect(screen.getByTestId('file-preview-modal')).toBeInTheDocument();
        const stage = screen.getByTestId('file-preview-image');
        // The <img> starts on the thumbnail (zoom 1) at the natural width we passed.
        const img = within(stage).getByRole('img');
        expect(img).toHaveAttribute('src', '/files/photo-thumb.png');
        expect(img).toHaveAttribute('width', '100');
        // Meta carries the mime and the dimensions the test itself supplied.
        expect(shell()).toHaveTextContent('image/png');
        expect(shell()).toHaveTextContent('100 × 80');
        // Image is neither text nor markdown → no copy button, no markdown toggle.
        expect(screen.queryByTestId('file-preview-copy')).toBeNull();
        expect(screen.queryByTestId('file-preview-markdown-toggle')).toBeNull();
    });

    it('renders the text body one node per line, with a copy button', async () => {
        await setupI18n();
        mount({preview: textPreview()});

        expect(screen.getByTestId('file-preview-text')).toBeInTheDocument();
        expect(within(screen.getByTestId('file-preview-text')).getAllByText(/alpha|beta|gamma/)).toHaveLength(3);
        expect(screen.getByTestId('file-preview-copy')).toBeInTheDocument();
        // No image/table/markdown bodies leak in.
        expect(screen.queryByTestId('file-preview-image')).toBeNull();
        expect(screen.queryByTestId('file-preview-grid')).toBeNull();
    });

    it('renders the markdown toggle and the rendered mount node by default', async () => {
        await setupI18n();
        mount({preview: markdownPreview()});

        expect(screen.getByTestId('file-preview-markdown-toggle')).toBeInTheDocument();
        // browser=false ⇒ the parse effect never runs, but the mount node is chosen.
        expect(screen.getByTestId('file-preview-markdown-rendered')).toBeInTheDocument();
        expect(screen.getByTestId('file-preview-copy')).toBeInTheDocument();
    });

    it('renders the table body: grid mount node, autofit hint and the sheet selector', async () => {
        await setupI18n();
        mount({preview: tablePreview()});

        expect(screen.getByTestId('file-preview-grid')).toBeInTheDocument();
        expect(screen.getByTestId('file-preview-autofit-hint')).toBeInTheDocument();
        // Two sheets ⇒ the selector is shown; its size label uses the numbers we passed.
        expect(screen.getByTestId('file-preview-sheet-select')).toBeInTheDocument();
        expect(shell()).toHaveTextContent('2 × 4');
    });

    it('hides the sheet selector when there is a single sheet', async () => {
        await setupI18n();
        mount({preview: tablePreview({sheet_names: ['Only']})});

        expect(screen.getByTestId('file-preview-grid')).toBeInTheDocument();
        expect(screen.queryByTestId('file-preview-sheet-select')).toBeNull();
    });

    it('derives the column count from the rows when total_cols is absent', async () => {
        await setupI18n();
        // No total_cols ⇒ tableCols = max row length = 3; total_rows drives the left number.
        mount({preview: tablePreview({total_cols: undefined, total_rows: 5, table_rows: [['a', 'b', 'c']]})});

        expect(shell()).toHaveTextContent('5 × 3');
    });
});

describe('FilePreviewModal — download and states', () => {
    it('points the download link at download_url and names it after the file', async () => {
        await setupI18n();
        mount({preview: imagePreview()});

        const link = screen.getByTestId('file-preview-download');
        expect(link).toHaveAttribute('href', '/download/photo.png');
        expect(link).toHaveAttribute('download', 'photo.png');
    });

    it('shows the loading state (busy shell, no body, no download)', async () => {
        await setupI18n();
        mount({preview: null, loading: true});

        expect(shell()).toHaveAttribute('data-busy', 'true');
        expect(screen.queryByTestId('file-preview-download')).toBeNull();
        expect(screen.queryByTestId('file-preview-image')).toBeNull();
        expect(screen.queryByTestId('file-preview-text')).toBeNull();
    });

    it('shows the error message verbatim (the error is a prop, not a translation)', async () => {
        await setupI18n();
        mount({preview: null, loading: false, error: 'Boom: could not read file'});

        expect(shell()).toHaveTextContent('Boom: could not read file');
        expect(screen.queryByTestId('file-preview-download')).toBeNull();
    });

    it('shows the no-data state when open with neither preview, loading nor error', async () => {
        await setupI18n();
        mount({preview: null, loading: false, error: null});

        // The shell mounts but nothing type-specific is chosen and no actions appear.
        expect(shell()).toHaveAttribute('data-busy', 'false');
        expect(screen.queryByTestId('file-preview-download')).toBeNull();
        expect(screen.queryByTestId('file-preview-image')).toBeNull();
        expect(screen.queryByTestId('file-preview-text')).toBeNull();
        expect(screen.queryByTestId('file-preview-grid')).toBeNull();
    });
});

describe('FilePreviewModal — encoding label branches', () => {
    it('renders "Latin-1" for latin-1', async () => {
        await setupI18n();
        mount({preview: textPreview({detected_encoding: 'latin-1'})});
        expect(shell()).toHaveTextContent('Latin-1');
    });

    it('renders "Windows-1252" for cp1252', async () => {
        await setupI18n();
        mount({preview: textPreview({detected_encoding: 'cp1252'})});
        expect(shell()).toHaveTextContent('Windows-1252');
    });

    it('uppercases an unknown encoding (ascii → ASCII)', async () => {
        await setupI18n();
        mount({preview: textPreview({detected_encoding: 'ascii'})});
        expect(shell()).toHaveTextContent('ASCII');
    });

    it('shows no encoding label for utf-8 (the empty branch, not an uppercased "UTF-8")', async () => {
        await setupI18n();
        mount({preview: textPreview({detected_encoding: 'utf-8'})});
        expect(shell()).not.toHaveTextContent('UTF-8');
    });
});

describe('FilePreviewModal — interactions', () => {
    it('zoom-in switches the image to the full source and grows it; reset restores both', async () => {
        await setupI18n();
        mount({preview: imagePreview()});

        const img = () => within(screen.getByTestId('file-preview-image')).getByRole('img');
        expect(img()).toHaveAttribute('src', '/files/photo-thumb.png');
        expect(img()).toHaveAttribute('width', '100');

        const zoomIn = screen.getByTestId('file-preview-zoom-in');
        await fireEvent.click(zoomIn);
        // zoom 1.25 ⇒ full-resolution source and width rounded up from 100 * 1.25.
        expect(img()).toHaveAttribute('src', '/files/photo-full.png');
        expect(img()).toHaveAttribute('width', '125');

        // The zoom cluster is [zoomOut, reset, zoomIn] in DOM order; index into that
        // already-filtered trio rather than its translated aria-label.
        const zoomButtons = within(zoomIn.parentElement as HTMLElement).getAllByRole('button');
        await fireEvent.click(zoomButtons[1]);
        expect(img()).toHaveAttribute('src', '/files/photo-thumb.png');
        expect(img()).toHaveAttribute('width', '100');
    });

    it('markdown toggle swaps the rendered mount node for the raw text body and back', async () => {
        await setupI18n();
        mount({preview: markdownPreview()});

        expect(screen.getByTestId('file-preview-markdown-rendered')).toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('file-preview-markdown-raw-btn'));
        // Raw mode falls through to the shared text body.
        expect(screen.getByTestId('file-preview-text')).toBeInTheDocument();
        expect(screen.queryByTestId('file-preview-markdown-rendered')).toBeNull();

        await fireEvent.click(screen.getByTestId('file-preview-markdown-rendered-btn'));
        expect(screen.getByTestId('file-preview-markdown-rendered')).toBeInTheDocument();
    });

    it('copy writes the current text content to the clipboard', async () => {
        await setupI18n();
        const writeText = vi.fn().mockResolvedValue(undefined);
        Object.defineProperty(globalThis.navigator, 'clipboard', {value: {writeText}, configurable: true});

        mount({preview: textPreview({text_content: 'copy me\nsecond'})});
        await fireEvent.click(screen.getByTestId('file-preview-copy'));

        expect(writeText).toHaveBeenCalledWith('copy me\nsecond');
    });

    it('changing the sheet calls onSheetChange with the chosen sheet name', async () => {
        await setupI18n();
        const {onSheetChange} = mount({preview: tablePreview()});

        const select = screen.getByTestId('file-preview-sheet-select');
        await fireEvent.change(select, {target: {value: 'Sheet2'}});

        expect(onSheetChange).toHaveBeenCalledWith('Sheet2');
    });

    it('Escape on the modal backdrop requests close', async () => {
        await setupI18n();
        const {onRequestClose} = mount({preview: imagePreview()});

        await fireEvent.keyDown(screen.getByTestId('file-preview-modal'), {key: 'Escape'});
        expect(onRequestClose).toHaveBeenCalledTimes(1);
    });
});
