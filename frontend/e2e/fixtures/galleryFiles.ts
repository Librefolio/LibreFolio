/**
 * Gallery — the Files page (`/files`): its two tabs, the static grid, and the preview of one seeded file of each kind.
 *
 * ## One page load, every combination
 *
 * A test loads the page once and switches language and theme through the header for each of the eight combinations. The
 * page follows a switch in place — every label it prints reads the dictionary as it renders — with one exception: the
 * static grid prints each card's size once, when the card mounts (FileGrid.svelte, `formatBytes`, which reads the
 * dictionary without subscribing to it). So the grid test enters the grid again in each combination: a fresh grid, in the
 * language of its shot, the way a user who opens the grid finds it.
 *
 * ## The file by its name
 *
 * Every preview shot opens a file the populate always creates ({@link FILES_SAMPLES}), found by its name through the API
 * and reached through its own row (`row-actions-<id>`) — never the first row of whatever the table lists today.
 *
 * ## Ready, from what the page publishes
 *
 * No wait for the network and no wait for the clock: each shot waits for its subject.
 * - The page: the files loaded (`files-page[data-busy=false]`), the uploaders resolved (`data-users-state=ready` on the
 *   table, so no row still says `User #id`), and every image on screen arrived ({@link imagesInViewLoaded}): the
 *   thumbnails and avatars are previews the server resizes on demand, and the table loads them lazily.
 * - A preview: the dialog open and its file fetched (`file-preview-shell[data-busy=false]`), then what each kind draws —
 *   the picture decoded, the PDF's pages drawn (`file-preview-pdf[data-state=ready]`, pdfPreviewState.ts) and its page
 *   controls faded out, the markdown rendered with its formula and the fonts it uses, the text's lines, the spreadsheet's
 *   canvas painted and still.
 */

import {expect, type Locator, type Page} from './playwright';
import {parkPointer} from './galleryRiskLab';

const API = '/api/v1';

/**
 * The seeded files the preview shots open, by name (backend/test_scripts/test_db/populate_mock_data.py):
 * - `image`: one of the 30 default avatars (`seed_default_avatars`, backend/staticResources/Avatars);
 * - `pdf`: the EmbedPDF sample (`upload_static_resources`, backend/staticResources/FilePreviewSamples);
 * - `markdown`, `text`: the two samples `upload_static_resources` writes — the markdown with headings, a table, code and
 *   KaTeX math, inline and in a block;
 * - `csv`: Charles Schwab's sample report (`upload_broker_reports`), which previews as a table of 120 rows × 8 columns.
 */
export const FILES_SAMPLES = {
    image: 'men_01.png',
    pdf: 'ebook.pdf',
    markdown: 'preview_markdown_sample.md',
    text: 'preview_notes_sample.txt',
    csv: 'schwab-export.csv',
} as const;

/** How long the server may take to list the files or resolve the uploaders, on a busy lane. */
const LIST_TIMEOUT = 20_000;

/** How long the images on screen may take: the server resizes each preview on its first request. */
const IMAGES_TIMEOUT = 20_000;

/** The id of the one file `name` names, out of `files` as `id` reads them. */
function onlyId<T>(files: readonly T[], name: string, nameOf: (file: T) => unknown, id: (file: T) => unknown, where: string): string {
    const matches = files.filter((file) => nameOf(file) === name);
    const found = matches.length === 1 ? id(matches[0]) : null;
    if (typeof found !== 'string') throw new Error(`${where}: "${name}" names ${matches.length} files, expected one — check populate_mock_data.py`);
    return found;
}

/** The id of the static resource named `name`: the session's own listing (`GET /uploads`), the one the page shows. */
export async function staticFileId(page: Page, name: string): Promise<string> {
    const response = await page.request.get(`${API}/uploads`);
    expect(response.ok(), `GET ${API}/uploads: HTTP ${response.status()}`).toBe(true);
    const items = ((await response.json()) as {items?: Array<{id?: unknown; original_name?: unknown}>}).items ?? [];
    return onlyId(
        items,
        name,
        (file) => file.original_name,
        (file) => file.id,
        'the static resources',
    );
}

/** The id of the broker report named `name`: the session's own listing (`GET /brokers/import/files`), the one the page shows. */
export async function brimFileId(page: Page, name: string): Promise<string> {
    const response = await page.request.get(`${API}/brokers/import/files`);
    expect(response.ok(), `GET ${API}/brokers/import/files: HTTP ${response.status()}`).toBe(true);
    const files = (await response.json()) as Array<{file_id?: unknown; filename?: unknown}>;
    return onlyId(
        files,
        name,
        (file) => file.filename,
        (file) => file.file_id,
        'the broker reports',
    );
}

/**
 * Every image of `scope` on screen has arrived: fetched, decoded, with a size. Read in the page, shadow roots included (a
 * locator crosses them: the PDF viewer draws its pages inside one). An image counts where it is drawn — or would be: one
 * the page hides while it loads (LazyImage keeps it out of the layout until then) or after it failed (DataTable draws a
 * fallback icon in its place) has no box of its own, so its holder's box decides, and a failed one is a red, naming its
 * source, not a shot with a hole in it. Left alone: images off screen — the table loads them lazily, so they never arrive
 * until scrolled to — and a lazy image the page hides, which the browser never asks for.
 */
export async function imagesInViewLoaded(scope: Locator, what: string, timeout = IMAGES_TIMEOUT): Promise<void> {
    await expect
        .poll(
            () =>
                scope.locator('img').evaluateAll((images) =>
                    images.flatMap((element) => {
                        const image = element as HTMLImageElement;
                        const shown = image.getClientRects().length > 0;
                        if (!shown && image.loading === 'lazy' && !image.complete) return [];
                        const box = (shown ? image : image.parentElement)?.getBoundingClientRect();
                        if (!box || box.width === 0 || box.height === 0) return [];
                        if (box.bottom <= 0 || box.right <= 0 || box.top >= window.innerHeight || box.left >= window.innerWidth) return [];
                        if (image.complete && image.naturalWidth > 0) return [];
                        return [(image.currentSrc || image.getAttribute('src') || '(no source yet)').slice(0, 120)];
                    }),
                ),
            {message: `${what}: an image on screen has not arrived`, timeout},
        )
        .toEqual([]);
}

/**
 * The page and its table are ready to be shot: the files listed, the uploaders resolved — until then a row says `User
 * #id` beside a placeholder avatar — at least one row drawn, and every image of the table on screen arrived.
 */
export async function filesTableReady(page: Page, table: Locator, what: string): Promise<void> {
    await expect(page.getByTestId('files-page'), `${what}: the files never finished loading`).toHaveAttribute('data-busy', 'false', {timeout: LIST_TIMEOUT});
    await expect(table, `${what}: the table is not on the page`).toBeVisible();
    await expect(table, `${what}: the uploaders were never resolved`).toHaveAttribute('data-users-state', 'ready', {timeout: LIST_TIMEOUT});
    await expect(table.locator('tr[data-row-id]').first(), `${what}: the table has no row`).toBeVisible();
    await imagesInViewLoaded(table, what);
}

/** The app in `theme`, through the header's toggle — the spec's setTheme, with the theme read back instead of a 100 ms wait. */
export async function chooseTheme(page: Page, theme: 'light' | 'dark'): Promise<void> {
    const current = () => page.evaluate(() => (document.documentElement.classList.contains('dark') ? 'dark' : 'light'));
    if ((await current()) !== theme) await page.getByTestId('theme-toggle').click();
    await expect.poll(current, {message: `the app did not switch to the ${theme} theme`}).toBe(theme);
}

/** The language menu the switch opened is closed again: nothing of it in the shot. */
export async function languageMenuClosed(page: Page): Promise<void> {
    await expect(page.getByTestId('language-selector'), 'the language menu is still open').toHaveAttribute('data-menu-open', 'false');
}

/**
 * Open the preview of the file `fileId` from its own row — its actions menu, then Preview — and end on the dialog open with
 * the file fetched (`file-preview-shell[data-busy=false]`) and the row's menu gone.
 */
export async function openPreview(page: Page, table: Locator, fileId: string, what: string): Promise<Locator> {
    await expect(table.locator(`tr[data-row-id="${fileId}"]`), `${what}: the file's row is not in the table`).toBeVisible();
    await table.getByTestId(`row-actions-${fileId}`).click();
    const preview = page.getByTestId('context-menu-action-preview');
    await expect(preview, `${what}: the row offers no preview`).toBeVisible();
    await preview.click();
    await expect(page.getByTestId('context-menu'), `${what}: the row's menu stayed open`).toHaveCount(0);
    const modal = page.getByTestId('file-preview-modal');
    await expect(modal, `${what}: the preview did not open`).toBeVisible();
    await expect(modal.getByTestId('file-preview-shell'), `${what}: the preview never arrived`).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
    return modal;
}

/** Close the preview with Escape, as a user does, and end on the dialog gone. */
export async function closePreview(modal: Locator, what: string): Promise<void> {
    await modal.press('Escape');
    await expect(modal, `${what}: Escape did not close the preview`).toBeHidden();
}

/** The image preview holds its picture: fetched, decoded — ready to be drawn — with a size. Returns the stage. */
export async function imagePreviewReady(modal: Locator, what: string): Promise<Locator> {
    const stage = modal.getByTestId('file-preview-image');
    await expect(stage, `${what}: the image stage is not shown`).toBeVisible();
    const image = stage.locator('img');
    await expect(image, `${what}: the stage holds no picture`).toBeVisible();
    await expect
        .poll(
            () =>
                image.evaluate(async (element) => {
                    const picture = element as HTMLImageElement;
                    // decode() settles once the picture can be drawn, and rejects if it failed: read again until the deadline.
                    await picture.decode().catch(() => undefined);
                    return picture.complete ? picture.naturalWidth : 0;
                }),
            {message: `${what}: the picture never arrived`, timeout: IMAGES_TIMEOUT},
        )
        .toBeGreaterThan(0);
    return stage;
}

/**
 * The PDF preview has drawn its pages: the stage reports `ready` (the document opened and every tile of the pages in view
 * drawn, pdfPreviewState.ts), the viewer's toolbar is up, every tile's image has arrived, and nothing changes between two
 * readings — a redraw (after the viewer fits the page to its box) turns the stage back to `loading`. Generous: the viewer
 * fetches its engine (pdfium WASM) and renders the tiles before it is ready. Then the viewer's page controls are gone
 * ({@link pageControlsGone}). Returns the stage.
 */
export async function pdfPreviewReady(modal: Locator, what: string): Promise<Locator> {
    const stage = modal.getByTestId('file-preview-pdf');
    await expect(stage, `${what}: the PDF viewer never drew its pages`).toHaveAttribute('data-state', 'ready', {timeout: 60_000});
    await expect(stage).toHaveAttribute('aria-busy', 'false');
    await expect(stage.locator('[data-epdf-i]').first(), `${what}: the viewer's toolbar is not drawn`).toBeVisible();
    await imagesInViewLoaded(stage, what);
    let previous = '';
    await expect
        .poll(
            async () => {
                const state = await stage.getAttribute('data-state');
                const tiles = await stage.locator('img').evaluateAll((images) =>
                    images
                        .map((element) => {
                            const box = element.getBoundingClientRect();
                            const image = element as HTMLImageElement;
                            return `${Math.round(box.x)},${Math.round(box.y)},${Math.round(box.width)},${Math.round(box.height)}:${image.complete ? image.naturalWidth : '…'}`;
                        })
                        .join('|'),
                );
                const now = `${state}#${tiles}`;
                const still = state === 'ready' && now === previous;
                previous = now;
                return still;
            },
            {message: `${what}: the PDF viewer is still drawing`, timeout: 15_000, intervals: [150, 250]},
        )
        .toBe(true);
    await pageControlsGone(stage, what);
    return stage;
}

/**
 * The viewer's page controls — the `‹ 1 4 ›` pill over the page, EmbedPDF's `page-controls` overlay — are gone. They show
 * on any scroll of the viewer, its first layout included, and fade out (300 ms) 4 s after the last one: a shot inside that
 * window catches them over the page, or half faded, depending on how fast the run is. So the shot waits for their end
 * state, read off what is drawn: no part of them (their icons, the page field, the page count — the leaves, since the
 * wrappers around them paint nothing and keep their full opacity) with any opacity left, and no fade still running. The
 * overlay must be there (the sample has four pages): a viewer that renamed it would put the pill back in the shots unseen.
 */
async function pageControlsGone(stage: Locator, what: string): Promise<void> {
    const controls = stage.locator('[data-overlay-id="page-controls"]');
    await expect(controls, `${what}: the viewer has no page controls overlay any more — check how it hides them`).toHaveCount(1);
    // A pointer resting on them keeps them shown (their mouseenter): parked off the viewer first.
    await parkPointer(stage.page());
    const reading = () =>
        controls.evaluate((overlay) => {
            const parts = Array.from(overlay.querySelectorAll('*')).filter((element) => element.childElementCount === 0 && element.getClientRects().length > 0);
            const drawn = parts.filter((part) => {
                let opacity = 1;
                for (let node: Element | null = part; node && node !== overlay.parentElement; node = node.parentElement) opacity *= Number(getComputedStyle(node).opacity);
                return opacity > 0;
            }).length;
            const fading = overlay.getAnimations({subtree: true}).filter((animation) => animation.playState === 'running').length;
            return drawn === 0 && fading === 0 ? 'gone' : `${drawn} of ${parts.length} parts drawn, ${fading} fade(s) running`;
        });
    // Logged: what the controls showed when the pages were ready, so the run says this waited for something.
    const first = await reading();
    await expect.poll(reading, {message: `${what}: the viewer's page controls are still over the page`, timeout: 15_000}).toBe('gone');
    console.log(`  ⏳ ${what}: page controls ${first} → gone`);
}

/**
 * The markdown preview is rendered: the sample's title as a heading, and its block formula typeset by KaTeX (its MathML,
 * in display mode, sits beside the drawn formula) — then the web fonts KaTeX draws with have arrived. Returns the stage.
 */
export async function markdownPreviewReady(page: Page, modal: Locator, what: string): Promise<Locator> {
    const rendered = modal.getByTestId('file-preview-markdown-rendered');
    await expect(rendered, `${what}: the rendered markdown is not shown`).toBeVisible();
    await expect(rendered.locator('h1'), `${what}: the markdown was never rendered`).toBeVisible({timeout: 20_000});
    await expect(rendered.locator('math[display="block"]').first(), `${what}: the block formula was not typeset`).toBeAttached();
    await fontsLoaded(page);
    return rendered;
}

/** The text preview shows the file's lines. Returns the stage. */
export async function textPreviewReady(modal: Locator, what: string): Promise<Locator> {
    const text = modal.getByTestId('file-preview-text');
    await expect(text, `${what}: the text is not shown`).toBeVisible();
    await expect(text.locator('code').first(), `${what}: the text has no line`).toBeVisible();
    return text;
}

/**
 * The spreadsheet preview is painted: the grid's canvas exists, is sized, holds pixels — a canvas just created is blank
 * and as still as a finished one — and two readings of its pixels in a row agree. The grid (cheetah-grid) draws on the
 * next frames after it mounts, on nothing the page publishes. Returns the grid.
 */
export async function gridPreviewReady(modal: Locator, what: string): Promise<Locator> {
    const grid = modal.getByTestId('file-preview-grid');
    await expect(grid, `${what}: the grid is not shown`).toBeVisible();
    let previous = '';
    await expect
        .poll(
            async () => {
                const now = await grid.locator('canvas').evaluateAll((canvases) =>
                    canvases
                        .map((element) => {
                            const canvas = element as HTMLCanvasElement;
                            if (canvas.width === 0 || canvas.height === 0) return 'empty';
                            const context = canvas.getContext('2d');
                            if (!context) return 'unreadable';
                            const pixels = new Uint32Array(context.getImageData(0, 0, canvas.width, canvas.height).data.buffer);
                            let hash = 0;
                            let painted = false;
                            for (let index = 0; index < pixels.length; index += 1) {
                                if (pixels[index] !== 0) painted = true;
                                hash = (Math.imul(hash, 31) + pixels[index]) | 0;
                            }
                            return painted ? `${canvas.width}x${canvas.height}:${hash}` : 'blank';
                        })
                        .join('|'),
                );
                const drawn = now !== '' && !now.split('|').some((reading) => reading === 'empty' || reading === 'blank' || reading === 'unreadable');
                const still = drawn && now === previous;
                previous = now;
                return still;
            },
            {message: `${what}: the grid is not painted yet, or still painting`, timeout: 15_000, intervals: [150, 250]},
        )
        .toBe(true);
    return grid;
}

/**
 * Every web font the page uses has arrived. Reading a box lays the page out, which is when the browser asks for the fonts
 * its text needs; `document.fonts.ready` then settles once none is still loading.
 */
export async function fontsLoaded(page: Page): Promise<void> {
    await expect
        .poll(
            () =>
                page.evaluate(async () => {
                    document.body.getBoundingClientRect();
                    await document.fonts.ready;
                    return document.fonts.status;
                }),
            {message: 'a web font of the shot is still loading', timeout: 15_000},
        )
        .toBe('loaded');
}
