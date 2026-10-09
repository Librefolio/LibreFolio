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
 *
 * One renderer is reached on purpose: the PDF stage's *state*. The stage publishes
 * whether the pages in view are drawn (`data-state`, `aria-busy`), from the viewer's
 * own reports, and that wiring — subscribe once the viewer is up, decide on every
 * report, stop listening with the viewer — is the component's, not EmbedPDF's. So the
 * last block turns `browser` on for itself and hands the preview a fake EmbedPDF
 * (`@embedpdf/snippet` mocked): the fake records who listens and lets the test speak
 * for the viewer. What the reports mean is pdfPreviewState.test.ts's job; here only
 * that they reach the stage, and that nothing listens once the preview is gone.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import FilePreviewModal from './FilePreviewModal.svelte';

/**
 * `$app/environment` with a `browser` the PDF block can turn on. Every other block runs
 * as the shared mock does (`browser = false`): their renderers must stay asleep.
 */
const environment = vi.hoisted(() => ({browser: false, dev: true, building: false, version: 'test'}));
vi.mock('$app/environment', () => environment);

/**
 * A fake EmbedPDF viewer: what the preview handed `init`, who subscribed to which report,
 * and one stop per subscription. The registry resolves at once unless a test holds it.
 */
const viewer = vi.hoisted(() => {
    type Listener = (event?: unknown) => void;
    const opened: Listener[] = [];
    const failed: Listener[] = [];
    const tiles: Listener[] = [];
    const stops: Array<ReturnType<typeof vi.fn>> = [];
    const subscribe = (listeners: Listener[]) => (listener: Listener) => {
        listeners.push(listener);
        const stop = vi.fn();
        stops.push(stop);
        return stop;
    };
    const plugins: Record<string, unknown> = {
        'document-manager': {onDocumentOpened: subscribe(opened), onDocumentError: subscribe(failed)},
        tiling: {onTileRendering: subscribe(tiles)},
    };
    /** What `await viewer.registry` gives: the two plugins the preview asks for, by the ids the module exports. */
    const registry = {getPlugin: (id: string) => (id in plugins ? {provides: () => plugins[id]} : null)};
    const fake = {
        inits: [] as Array<Record<string, unknown>>,
        /** How many times the preview asked a viewer for its registry. */
        registryAsks: 0,
        registry,
        /** The promise a viewer's `registry` answers: resolved at once, unless a test holds it. */
        resolveRegistry: (): Promise<unknown> => Promise.resolve(registry),
        opened,
        failed,
        tiles,
        stops,
        reset() {
            fake.inits.length = 0;
            fake.registryAsks = 0;
            fake.resolveRegistry = () => Promise.resolve(registry);
            for (const list of [opened, failed, tiles, stops]) list.length = 0;
        },
        init(config: Record<string, unknown>) {
            fake.inits.push(config);
            return {
                get registry() {
                    fake.registryAsks += 1;
                    return fake.resolveRegistry();
                },
            };
        },
    };
    return fake;
});
vi.mock('@embedpdf/snippet', () => ({
    default: {init: (config: Record<string, unknown>) => viewer.init(config)},
    DocumentManagerPlugin: {id: 'document-manager'},
    TilingPlugin: {id: 'tiling'},
}));

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

function pdfPreview(over: Preview = {}): Preview {
    return {
        preview_type: 'pdf',
        filename: 'ebook.pdf',
        mime_type: 'application/pdf',
        size_bytes: 4096,
        source_url: '/files/ebook.pdf',
        download_url: '/download/ebook.pdf',
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

describe('FilePreviewModal — PDF stage state (fake EmbedPDF)', () => {
    /** Tiles as the viewer reports them for the pages in view (plugin-tiling's `visibleTiles`). */
    const ready = {status: 'ready', isFallback: false};
    const queued = {status: 'queued', isFallback: false};
    let scrollTo: ReturnType<typeof vi.spyOn>;

    beforeEach(async () => {
        await setupI18n();
        viewer.reset();
        environment.browser = true;
        // With `browser` on, ModalBase locks the page's scroll while open and puts it back on close: jsdom does not scroll.
        scrollTo = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    });

    afterEach(() => {
        // Unmounted here, before `browser` goes off and scrollTo comes back: the teardown is part of what is tested.
        cleanup();
        environment.browser = false;
        scrollTo.mockRestore();
    });

    /** The stage, once the viewer is up and the preview listens to its three reports — once each. */
    async function listening(): Promise<HTMLElement> {
        await waitFor(() => {
            expect(viewer.opened).toHaveLength(1);
            expect(viewer.failed).toHaveLength(1);
            expect(viewer.tiles).toHaveLength(1);
        });
        return screen.getByTestId('file-preview-pdf');
    }

    it('starts loading and busy, and hands the viewer the file and the stage', async () => {
        mount({preview: pdfPreview()});

        const stage = screen.getByTestId('file-preview-pdf');
        expect(stage).toHaveAttribute('data-state', 'loading');
        expect(stage).toHaveAttribute('aria-busy', 'true');

        await listening();
        expect(viewer.inits).toHaveLength(1);
        expect(viewer.inits[0]).toMatchObject({type: 'container', target: stage, src: '/files/ebook.pdf'});
        // Listening is not drawing: nothing reported yet, so the stage still says loading.
        expect(stage).toHaveAttribute('data-state', 'loading');
        expect(stage).toHaveAttribute('aria-busy', 'true');
    });

    it('is ready, and no longer busy, once the document opened and every tile in view is drawn', async () => {
        mount({preview: pdfPreview()});
        const stage = await listening();

        viewer.opened[0]();
        flushSync();
        expect(stage, 'opened, but no tile report yet').toHaveAttribute('data-state', 'loading');

        viewer.tiles[0]({documentId: 'doc', tiles: {0: [ready, queued]}});
        flushSync();
        expect(stage, 'a tile in view is still queued').toHaveAttribute('data-state', 'loading');
        expect(stage).toHaveAttribute('aria-busy', 'true');

        viewer.tiles[0]({documentId: 'doc', tiles: {0: [ready, ready], 1: [ready]}});
        flushSync();
        expect(stage).toHaveAttribute('data-state', 'ready');
        expect(stage).toHaveAttribute('aria-busy', 'false');
    });

    it('is error, and not busy, when the viewer reports the document failed — even after it was drawn', async () => {
        mount({preview: pdfPreview()});
        const stage = await listening();

        viewer.opened[0]();
        viewer.tiles[0]({documentId: 'doc', tiles: {0: [ready]}});
        flushSync();
        expect(stage).toHaveAttribute('data-state', 'ready');

        viewer.failed[0]({documentId: 'doc'});
        flushSync();
        expect(stage).toHaveAttribute('data-state', 'error');
        expect(stage).toHaveAttribute('aria-busy', 'false');
    });

    it('stops listening to every report when the preview closes', async () => {
        const view = mount({preview: pdfPreview()});
        await listening();
        expect(viewer.stops).toHaveLength(3);
        for (const stop of viewer.stops) expect(stop).not.toHaveBeenCalled();

        await view.rerender({open: false});

        for (const stop of viewer.stops) expect(stop).toHaveBeenCalledTimes(1);
    });

    it('stops listening to every report when the preview is unmounted', async () => {
        const view = mount({preview: pdfPreview()});
        await listening();
        expect(viewer.stops).toHaveLength(3);
        for (const stop of viewer.stops) expect(stop).not.toHaveBeenCalled();

        view.unmount();

        for (const stop of viewer.stops) expect(stop).toHaveBeenCalledTimes(1);
    });

    /** A registry the test releases: the viewer is up, and the preview waits on it. */
    function holdRegistry(): () => void {
        let release: () => void = () => {};
        const held = new Promise<unknown>((resolve) => {
            release = () => resolve(viewer.registry);
        });
        viewer.resolveRegistry = () => held;
        return release;
    }

    /**
     * Every job already queued has run: a task boundary, not a delay. What a release sets off in the
     * preview is a chain of microtasks only — longer than the source suggests, since Svelte's dev build
     * wraps each `await` of an effect in hops of its own (`$.track_reactivity_loss`) — and the event loop
     * runs every microtask before the next task. The positive case below proves the boundary is enough.
     */
    function queuedJobsRun(): Promise<void> {
        return new Promise((resolve) => setTimeout(resolve, 0));
    }

    it('listens to a viewer whose registry arrives late, while the preview is open', async () => {
        const release = holdRegistry();
        mount({preview: pdfPreview()});
        await waitFor(() => expect(viewer.registryAsks).toBe(1));
        expect(viewer.opened, 'nothing subscribed before the registry').toHaveLength(0);

        release();
        await queuedJobsRun();

        expect(viewer.opened).toHaveLength(1);
        expect(viewer.failed).toHaveLength(1);
        expect(viewer.tiles).toHaveLength(1);
    });

    it('never listens to a viewer whose registry arrives after the preview is gone', async () => {
        const release = holdRegistry();
        const view = mount({preview: pdfPreview()});
        await waitFor(() => expect(viewer.registryAsks).toBe(1));

        // The same late registry, behind the same boundary, as above; only, the preview is gone when it arrives.
        view.unmount();
        release();
        await queuedJobsRun();

        expect(viewer.opened).toHaveLength(0);
        expect(viewer.failed).toHaveLength(0);
        expect(viewer.tiles).toHaveLength(0);
        expect(viewer.stops).toHaveLength(0);
    });
});
