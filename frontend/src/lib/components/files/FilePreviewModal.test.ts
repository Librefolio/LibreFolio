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
 * that they reach the stage, and that nothing listens once the preview is gone. It
 * also checks what the preview hands the viewer — our engine and fonts, or nothing so
 * the viewer keeps its CDN defaults, and always the offline options — with the asset
 * resolution mocked (`pdfViewerAssets`: its HEAD probe would leave jsdom). And one
 * report leaves the preview as a request: a viewer left without a document asks to
 * close the preview — a viewer the preview drops itself never does.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {PdfErrorCode} from '@embedpdf/models';
import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {FilePreviewResponse} from '$lib/types';
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
 *
 * Each `init` makes one viewer (`viewers`), as the real one does: one open document, its own
 * `documentClosed` report and document count, and an element in the stage.
 */
const viewer = vi.hoisted(() => {
    type Listener = (event?: unknown) => void;
    const opened: Listener[] = [];
    const failed: Listener[] = [];
    const tiles: Listener[] = [];
    const closed: Listener[] = [];
    const stops: Array<ReturnType<typeof vi.fn>> = [];
    const subscribe = (listeners: Listener[]) => (listener: Listener) => {
        listeners.push(listener);
        const stop = vi.fn();
        stops.push(stop);
        return stop;
    };

    /**
     * One viewer. Its `documentClosed` report behaves as the real one (`Uo` in the snippet): the document is gone before
     * anyone hears it closed (the core reducer runs before the listeners), the last document closed is handed at once to a
     * late subscriber, a repeat of it is dropped, and a stopped listener hears nothing more.
     */
    function makeViewer() {
        const documents = new Set(['doc']);
        const live = new Set<Listener>();
        let last: string | undefined;
        const made = {
            /** The documents open in this viewer: what `getDocumentCount` counts. */
            documents,
            /** Every close this viewer reported, in order. */
            closedReports: [] as string[],
            /** The viewer closes a document: «Cancel» on its password prompt, «Close» on its error card (`closeDocument`). */
            close(id: string) {
                documents.delete(id);
                if (last === id) return;
                last = id;
                made.closedReports.push(id);
                for (const listener of [...live]) listener(id);
            },
            registry: null as unknown,
        };
        const plugins: Record<string, unknown> = {
            'document-manager': {
                onDocumentOpened: subscribe(opened),
                onDocumentError: subscribe(failed),
                onDocumentClosed(listener: Listener) {
                    closed.push(listener);
                    if (last !== undefined) listener(last);
                    live.add(listener);
                    const stop = vi.fn(() => live.delete(listener));
                    stops.push(stop);
                    return stop;
                },
                getDocumentCount: () => documents.size,
            },
            tiling: {onTileRendering: subscribe(tiles)},
        };
        /** What `await viewer.registry` gives: the two plugins the preview asks for, by the ids the module exports. */
        made.registry = {getPlugin: (id: string) => (id in plugins ? {provides: () => plugins[id]} : null)};
        return made;
    }

    /**
     * The element a viewer puts in the stage, as the real `<embedpdf-container>`. Taken out of the DOM it closes what is
     * still open, as unmounting the real one does — and when the real one does: its unmount destroys the plugin registry,
     * which awaits before any plugin closes a document, so the report comes once the DOM change is over (a microtask
     * later), never inside it.
     */
    function stageElement(onLeave: () => void): HTMLElement {
        const tag = 'fake-embedpdf-container';
        if (!customElements.get(tag)) {
            customElements.define(
                tag,
                class extends HTMLElement {
                    leave: (() => void) | undefined;
                    disconnectedCallback() {
                        this.leave?.();
                    }
                },
            );
        }
        const element = document.createElement(tag) as HTMLElement & {leave?: () => void};
        element.leave = onLeave;
        return element;
    }

    const fake = {
        inits: [] as Array<Record<string, unknown>>,
        /** The viewers `init` made, in order. */
        viewers: [] as Array<ReturnType<typeof makeViewer>>,
        /** When set, `init` throws it: the viewer cannot start. */
        initError: null as Error | null,
        /** How many times the preview asked a viewer for its registry. */
        registryAsks: 0,
        /** The promise a viewer's `registry` answers: resolved at once, unless a test holds it. */
        resolveRegistry: (registry: unknown): Promise<unknown> => Promise.resolve(registry),
        opened,
        failed,
        tiles,
        closed,
        stops,
        reset() {
            fake.inits.length = 0;
            fake.viewers.length = 0;
            fake.initError = null;
            fake.registryAsks = 0;
            fake.resolveRegistry = (registry) => Promise.resolve(registry);
            for (const list of [opened, failed, tiles, closed, stops]) list.length = 0;
        },
        init(config: Record<string, unknown>) {
            fake.inits.push(config);
            // A preview that keeps restarting the viewer would spin the test forever (every step here is a microtask, so
            // nothing else would ever run): past a few starts the fake stops answering, and the test can count them.
            if (fake.inits.length > 10) return {registry: new Promise(() => {})};
            if (fake.initError) throw fake.initError;
            const made = makeViewer();
            fake.viewers.push(made);
            const leave = () =>
                queueMicrotask(() => {
                    for (const id of [...made.documents]) made.close(id);
                });
            (config.target as HTMLElement | undefined)?.append(stageElement(leave));
            return {
                get registry() {
                    fake.registryAsks += 1;
                    return fake.resolveRegistry(made.registry);
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

/**
 * Where the viewer's assets come from, as the preview resolves them: what the test hands back, and the bases it was
 * asked about. Only `pdfViewerAssets` is replaced — its HEAD probe would leave jsdom for the network; the options every
 * preview gets (`pdfViewerOfflineOptions`) stay the module's own, so the test checks the real ones reach the viewer.
 */
const viewerAssets = vi.hoisted(() => ({next: {} as Record<string, unknown>, bases: [] as string[]}));
vi.mock('$lib/utils/files/pdfViewerAssets', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/utils/files/pdfViewerAssets')>()),
    pdfViewerAssets: async (base: string) => {
        viewerAssets.bases.push(base);
        return viewerAssets.next;
    },
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
        viewerAssets.next = {};
        viewerAssets.bases.length = 0;
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

    it('hands the viewer our engine and fonts when they answer, and turns off what a preview never loads', async () => {
        const fontFallback = {fonts: {204: [{url: 'http://localhost:3000/_app/immutable/assets/NotoSans-Regular.test.ttf', weight: 400}]}};
        viewerAssets.next = {wasmUrl: 'http://localhost:3000/_app/immutable/assets/pdfium.test.wasm', fontFallback};
        mount({preview: pdfPreview()});
        const stage = await listening();

        // Resolved against the page the preview is opened from: the URLs the viewer gets are absolute.
        expect(viewerAssets.bases).toEqual([document.baseURI]);
        const config = viewer.inits[0] as {wasmUrl?: unknown; fontFallback?: unknown; fonts?: {ui?: {family?: unknown; stylesheetUrl?: unknown}; signature?: unknown}; stamp?: {manifests?: unknown}};
        expect(config.wasmUrl).toBe('http://localhost:3000/_app/immutable/assets/pdfium.test.wasm');
        expect(config.fontFallback).toBe(fontFallback);
        // The interface in the app's own font, no stylesheet to fetch; no signature fonts; no stamp library.
        expect(config.fonts?.ui?.stylesheetUrl).toBeNull();
        expect(config.fonts?.ui?.family).toBe(getComputedStyle(stage).fontFamily);
        expect(config.fonts?.signature).toBeNull();
        expect(config.stamp?.manifests).toEqual([]);
    });

    it('leaves the viewer on its CDN defaults when our engine does not answer — and still turns off what a preview never loads', async () => {
        viewerAssets.next = {};
        mount({preview: pdfPreview()});
        await listening();

        const config = viewer.inits[0] as {fonts?: {ui?: {stylesheetUrl?: unknown}; signature?: unknown}; stamp?: {manifests?: unknown}};
        expect('wasmUrl' in config, 'a wasmUrl reached the viewer: it would not fall back on its own engine').toBe(false);
        expect('fontFallback' in config, 'a fontFallback reached the viewer: it would not fall back on its own fonts').toBe(false);
        expect(config.fonts?.ui?.stylesheetUrl).toBeNull();
        expect(config.fonts?.signature).toBeNull();
        expect(config.stamp?.manifests).toEqual([]);
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

    /**
     * A protected PDF: the engine cannot open it without its password, so the viewer reports the error — as it reports
     * it, with the Password code — and shows its own prompt; once the user types the password, it opens the document and
     * draws it. The error was the prompt, not the end (developer's decision: protected PDFs can be previewed).
     */
    const passwordMissing = {documentId: 'doc', message: 'Password required', code: PdfErrorCode.Password};

    it('is ready once a protected PDF opens after its password was asked', async () => {
        mount({preview: pdfPreview()});
        const stage = await listening();

        viewer.failed[0](passwordMissing);
        flushSync();
        expect(stage, 'the prompt is up: the document did not open').toHaveAttribute('data-state', 'error');

        // The password typed: the viewer opens the document, then draws the pages in view.
        viewer.opened[0]({id: 'doc', status: 'loaded'});
        flushSync();
        expect.soft(stage, 'opened after the password, not drawn yet').toHaveAttribute('data-state', 'loading');
        expect.soft(stage, 'opened after the password, not drawn yet').toHaveAttribute('aria-busy', 'true');

        viewer.tiles[0]({documentId: 'doc', tiles: {0: [ready, ready]}});
        flushSync();
        expect(stage, 'opened and drawn after the password').toHaveAttribute('data-state', 'ready');
        expect(stage, 'opened and drawn after the password').toHaveAttribute('aria-busy', 'false');
    });

    it('stays error when the viewer reports an error and nothing more: a PDF that does not open', async () => {
        mount({preview: pdfPreview()});
        const stage = await listening();

        viewer.failed[0](passwordMissing);
        flushSync();
        expect(stage).toHaveAttribute('data-state', 'error');
        expect(stage).toHaveAttribute('aria-busy', 'false');
    });

    it('stays error through a second error: a wrong password', async () => {
        mount({preview: pdfPreview()});
        const stage = await listening();

        viewer.failed[0](passwordMissing);
        flushSync();
        // The wrong password typed: the viewer tries again and reports the same error.
        viewer.failed[0]({...passwordMissing, message: 'Incorrect password'});
        flushSync();
        expect(stage).toHaveAttribute('data-state', 'error');
        expect(stage).toHaveAttribute('aria-busy', 'false');
    });

    it('stops listening to every report when the preview closes', async () => {
        const view = mount({preview: pdfPreview()});
        await listening();
        // One stop per report the preview listens to: opened, error and tiles at least.
        expect(viewer.stops.length).toBeGreaterThanOrEqual(3);
        for (const stop of viewer.stops) expect(stop).not.toHaveBeenCalled();

        await view.rerender({open: false});

        for (const stop of viewer.stops) expect(stop).toHaveBeenCalledTimes(1);
    });

    it('stops listening to every report when the preview is unmounted', async () => {
        const view = mount({preview: pdfPreview()});
        await listening();
        expect(viewer.stops.length).toBeGreaterThanOrEqual(3);
        for (const stop of viewer.stops) expect(stop).not.toHaveBeenCalled();

        view.unmount();

        for (const stop of viewer.stops) expect(stop).toHaveBeenCalledTimes(1);
    });

    /** A registry the test releases: the viewer is up, and the preview waits on it. */
    function holdRegistry(): () => void {
        let release: () => void = () => {};
        const held = new Promise<void>((resolve) => {
            release = resolve;
        });
        viewer.resolveRegistry = (registry) => held.then(() => registry);
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
        expect(viewer.closed).toHaveLength(0);
        expect(viewer.stops).toHaveLength(0);
    });

    /*
     * The viewer can be left with no document: «Cancel» on its password prompt and «Close» on its error card both close
     * the one it had (`closeDocument`), and all an empty viewer offers is to open a file of one's own — not what a
     * preview of this file is for. So the preview closes (developer's decision). Only the viewer emptying itself counts:
     * when the preview drops the viewer — closed, another file, the browser's own viewer as a fallback — the document
     * goes with it, and that is no request to close.
     */

    it('closes the preview when the viewer is left without a document', async () => {
        const view = mount({preview: pdfPreview()});
        await listening();
        await queuedJobsRun();
        const [shown] = viewer.viewers;

        shown.close('doc');

        await waitFor(() => expect(view.onRequestClose).toHaveBeenCalledTimes(1));
        // The page closes the preview, as the Files page does: the viewer leaving the stage is no second request.
        await view.rerender({open: false});
        await queuedJobsRun();
        expect(view.onRequestClose).toHaveBeenCalledTimes(1);
    });

    it('stays open when the viewer closes a document but still shows another', async () => {
        const {onRequestClose} = mount({preview: pdfPreview()});
        await listening();
        await queuedJobsRun();
        const [shown] = viewer.viewers;
        shown.documents.add('other');

        shown.close('doc');
        await queuedJobsRun();

        expect(shown.closedReports, 'the viewer reported the document closed').toEqual(['doc']);
        expect(shown.documents.size, 'and still shows one').toBe(1);
        expect(onRequestClose).not.toHaveBeenCalled();
    });

    it('stays open when it moves to another file: the viewer it drops closes its document on the way out', async () => {
        const view = mount({preview: pdfPreview()});
        await listening();
        await queuedJobsRun();

        // The builders are loose on purpose (any field, any value); `rerender` takes the component's own props.
        const otherFile = pdfPreview({filename: 'other.pdf', source_url: '/files/other.pdf'}) as unknown as FilePreviewResponse;
        await view.rerender({preview: otherFile});
        // The next viewer is up and listened to.
        await waitFor(() => expect(viewer.tiles).toHaveLength(2));
        await queuedJobsRun();

        const [dropped, next] = viewer.viewers;
        expect(viewer.inits.map((config) => config.src)).toEqual(['/files/ebook.pdf', '/files/other.pdf']);
        expect(dropped.closedReports, 'the dropped viewer closed its document as it left the stage').toEqual(['doc']);
        expect(next.documents.size, 'the next viewer shows its own').toBe(1);
        expect(view.onRequestClose).not.toHaveBeenCalled();
    });

    it('does not ask to close when it is closed: the viewer it drops closes its document on the way out', async () => {
        const view = mount({preview: pdfPreview()});
        await listening();
        await queuedJobsRun();

        await view.rerender({open: false});
        await queuedJobsRun();

        expect(viewer.viewers[0].closedReports, 'the dropped viewer closed its document as it left the stage').toEqual(['doc']);
        expect(view.onRequestClose).not.toHaveBeenCalled();
    });

    it('does not ask to close when the viewer cannot start and the browser shows the file instead', async () => {
        viewer.initError = new Error('The viewer did not start');
        const {onRequestClose} = mount({preview: pdfPreview()});

        await screen.findByTestId('file-preview-pdf-fallback');
        await queuedJobsRun();

        // The fallback stays: the viewer was started once, and the browser keeps showing the file.
        expect(viewer.inits.length, 'times the preview started the viewer').toBe(1);
        expect(screen.queryByTestId('file-preview-pdf-fallback')).not.toBeNull();
        expect(screen.queryByTestId('file-preview-pdf')).toBeNull();
        expect(onRequestClose).not.toHaveBeenCalled();
    });
});
