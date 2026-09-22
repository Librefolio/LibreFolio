/**
 * Files page composition, not a seeded-data integration test.
 * Every API response and avatar belongs to this browser context; all other API
 * calls, mutations and third-party requests are rejected. IDs may be reused
 * across workers because none of these records exists in the shared database.
 * Run in both desktop and mobile projects.
 */
import {test as base, expect} from './fixtures/playwright';
import type {Locator, Page} from './fixtures/playwright';
import type {BrimFile, UploadedFile} from '../src/lib/types/files';

const CREATED_AT = '2024-03-15T12:00:00Z';
const AVATAR_GOOD = '/review-uploader/avatars/atlas.svg';
const AVATAR_BROKEN = '/review-uploader/avatars/zephyr.svg';
const AVATAR_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><rect width="32" height="32" fill="#246849"/></svg>';
const BROKER_ID = 765432;
const USERS = [
    {id: 41, username: 'Review Atlas', avatar_url: AVATAR_GOOD},
    {id: 7, username: 'Review Zephyr', avatar_url: AVATAR_BROKEN},
    {id: 91, username: 'Review Nimbus', avatar_url: null},
];

function staticFile(id: string, original_name: string, uploaded_by_user_id: number): UploadedFile {
    return {
        id,
        original_name,
        uploaded_by_user_id,
        mime_type: 'text/plain',
        size_bytes: 128,
        uploaded_at: CREATED_AT,
        description: null,
        url: `/review-uploader/files/${id}`,
    };
}

const FILES = {
    atlas: staticFile('a0000000-0000-4000-8000-000000000041', 'review-scope-atlas.txt', 41),
    zephyr: staticFile('a0000000-0000-4000-8000-000000000007', 'review-scope-zephyr.txt', 7),
    nimbus: staticFile('a0000000-0000-4000-8000-000000000091', 'review-scope-nimbus.txt', 91),
    unknown: staticFile('a0000000-0000-4000-8000-000000008080', 'review-scope-unknown.txt', 8080),
    // Same uploader as Atlas, but excluded by the independent filename filter.
    outside: staticFile('a0000000-0000-4000-8000-000000000042', 'review-outside-scope.txt', 41),
};

function brimFile(file_id: string, filename: string, uploaded_by_user_id: number | null): BrimFile {
    return {
        file_id,
        filename,
        uploaded_by_user_id,
        size_bytes: 128,
        status: 'uploaded',
        uploaded_at: CREATED_AT,
        target_broker_id: BROKER_ID,
        compatible_plugins: [],
        parse_is_stale: false,
    };
}

const REPORTS = {
    atlas: brimFile('b0000000-0000-4000-8000-000000000041', 'review-atlas.csv', 41),
    unknown: brimFile('b0000000-0000-4000-8000-000000008080', 'review-unknown.csv', 8080),
    // Null is a valid BRIM wire identity, but NOT a valid UploadFileInfo owner.
    none: brimFile('b0000000-0000-4000-8000-000000000000', 'review-unattributed.csv', null),
};

type GetResponse = {
    body: unknown;
    requiredQuery?: Record<string, string>;
    optionalQuery?: Record<string, string>;
};

function matchesQuery(url: URL, response: GetResponse): boolean {
    const required = response.requiredQuery ?? {};
    const allowed = {...response.optionalQuery, ...required};
    return Object.entries(required).every(([key, value]) => url.searchParams.get(key) === value) && [...url.searchParams].every(([key, value]) => Object.hasOwn(allowed, key) && allowed[key] === value && url.searchParams.getAll(key).length === 1);
}

const test = base.extend<{uploaderPage: Page}>({
    uploaderPage: async ({page, baseURL}, use) => {
        if (!baseURL) throw new Error('Files uploader requires the runner-provided app baseURL');
        const origin = new URL(baseURL).origin;
        // These are the actual envelopes read by auth.checkAuth(), the protected
        // layout, brokerStore, ensurePluginIconsLoaded() and the Files route.
        // Zodios may materialize optional query defaults; only those documented
        // values are accepted, not arbitrary query strings or response shapes.
        const responses = new Map<string, GetResponse>([
            [
                '/api/v1/auth/me',
                {
                    body: {
                        user: {
                            id: 876543,
                            username: 'review-uploader-owned',
                            email: 'review-uploader@example.invalid',
                            is_active: true,
                            is_superuser: false,
                            created_at: CREATED_AT,
                        },
                    },
                },
            ],
            ['/api/v1/settings/user', {body: {language: 'en', base_currency: 'EUR', theme: 'light', avatar_url: null}}],
            ['/api/v1/settings/global', {body: {items: []}}],
            ['/api/v1/brokers/import/plugins', {body: []}],
            [
                '/api/v1/brokers',
                {
                    requiredQuery: {include_inaccessible: 'true'},
                    body: {
                        items: [
                            {
                                id: BROKER_ID,
                                name: 'Review uploader broker',
                                allow_cash_overdraft: false,
                                allow_asset_shorting: false,
                                is_active: true,
                                created_at: CREATED_AT,
                                updated_at: CREATED_AT,
                                icon_url: null,
                                default_import_plugin: null,
                                portal_url: null,
                                user_role: 'OWNER',
                                user_share_percentage: '1',
                            },
                        ],
                        inaccessible: [],
                    },
                },
            ],
            ['/api/v1/uploads', {body: {items: Object.values(FILES)}, optionalQuery: {my_files_only: 'false'}}],
            ['/api/v1/brokers/import/files', {body: Object.values(REPORTS)}],
            ['/api/v1/users/search', {body: {items: USERS}, requiredQuery: {q: ''}, optionalQuery: {admins: 'false'}}],
        ]);
        const unexpected: string[] = [];
        const handler: Parameters<Page['route']>[1] = async (route) => {
            const request = route.request();
            const url = new URL(request.url());
            const reject = async () => {
                unexpected.push(`${request.method()} ${url.origin}${url.pathname}${url.search}`);
                await route.abort('blockedbyclient');
            };
            if (request.method() !== 'GET' || url.origin !== origin) {
                await reject();
                return;
            }
            if (url.pathname === AVATAR_GOOD || url.pathname === AVATAR_BROKEN) {
                if (!matchesQuery(url, {body: null, requiredQuery: {img_preview: '32x32'}})) {
                    await reject();
                    return;
                }
                if (url.pathname === AVATAR_GOOD) {
                    await route.fulfill({status: 200, contentType: 'image/svg+xml', body: AVATAR_SVG});
                } else {
                    await route.fulfill({status: 404, contentType: 'text/plain', body: 'Owned missing avatar'});
                }
                return;
            }
            if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/review-uploader/')) {
                const response = responses.get(url.pathname);
                if (!response || !matchesQuery(url, response)) {
                    await reject();
                    return;
                }
                await route.fulfill({status: 200, json: response.body});
                return;
            }
            // Only the real app document and same-origin static bundles/assets
            // pass through. No successful catch-all API response is fabricated.
            await route.continue();
        };
        await page.route('**/*', handler);
        try {
            await use(page);
        } finally {
            // Unmount while the boundary is still installed, then release only
            // this spec's handler. No backend cleanup or shared storage deletion.
            if (!page.isClosed()) await page.goto('about:blank');
            await page.unroute('**/*', handler);
            expect(unexpected, 'Only the declared synthetic GET contracts may be requested').toEqual([]);
        }
    },
});

test.use({serviceWorkers: 'block'});

type TableType = 'static' | 'brim';

async function settledTable(page: Page, type: TableType) {
    const root = page.getByTestId('files-page');
    await expect(root).toBeVisible({timeout: 10_000});
    await expect(root).toHaveAttribute('data-busy', 'false');
    const table = root.getByTestId(`files-table-${type}`);
    await expect(table).toHaveAttribute('data-users-state', 'ready');
    await expect(table).toHaveAttribute('data-busy', 'false');
    return table;
}

function row(table: Locator, id: string) {
    return table.locator(`tbody tr[data-row-id="${id}"]`);
}

async function expectRows(table: Locator, expected: string[], allOwned: string[]) {
    // A positive row barrier precedes every absence assertion. All inputs fit
    // one page; no seeded row order or global database count is involved.
    expect(expected.length).toBeGreaterThan(0);
    for (const id of expected) await expect(row(table, id)).toBeVisible();
    for (const id of allOwned.filter((id) => !expected.includes(id))) await expect(row(table, id)).toHaveCount(0);
}

async function uploaderCell(table: Locator, id: string) {
    const header = table.getByTestId('dt-header-uploader');
    await expect(header).toBeAttached();
    const index = await header.evaluate((el) => (el as HTMLTableCellElement).cellIndex);
    // This index is derived from the identified column, not guessed from a row
    // position. It includes the real selection column and any visible columns.
    const cell = row(table, id).locator(':scope > td').nth(index);
    await cell.scrollIntoViewIfNeeded();
    await expect(cell).toBeVisible();
    return cell;
}

async function openUploader(table: Locator) {
    const trigger = table.getByTestId('col-filter-trigger-uploader');
    await trigger.click();
    const popover = table.getByTestId('dt-header-uploader').getByTestId('column-filter');
    await expect(popover).toBeVisible();
    await expect(popover).toHaveAttribute('data-filter-type', 'enum');
    return popover;
}

async function closeUploader(table: Locator) {
    const popover = table.getByTestId('dt-header-uploader').getByTestId('column-filter');
    await expect(popover).toBeVisible();
    await table.getByTestId('col-filter-trigger-uploader').click();
    await expect(popover).toBeHidden();
}

async function expectUrl(page: Page, tab: TableType, uploaders: string[], filename?: string) {
    await expect(page).toHaveURL((url) => url.pathname === '/files' && url.searchParams.get('tab') === tab && url.searchParams.get('filename') === (filename ?? null) && (url.searchParams.get('uploader') ?? '').split(',').sort().join(',') === [...uploaders].sort().join(','));
}

async function expectGrid(page: Page, expected: UploadedFile[]) {
    const root = page.getByTestId('files-page');
    expect(expected.length).toBeGreaterThan(0);
    for (const file of expected) {
        // FileGrid has no card testid. Its preview button is keyed by the file ID,
        // and its filename title is owned data, not translated interface prose.
        await expect(root.getByTestId(`file-grid-preview-${file.id}`)).toBeVisible();
        await expect(root.locator(`[title="${file.original_name}"]`)).toBeVisible();
    }
    await expect(root.getByTestId('files-table-static')).toHaveCount(0);
    const included = new Set(expected.map((file) => file.id));
    for (const file of Object.values(FILES).filter((file) => !included.has(file.id))) {
        await expect(root.getByTestId(`file-grid-preview-${file.id}`)).toHaveCount(0);
        await expect(root.locator(`[title="${file.original_name}"]`)).toHaveCount(0);
    }
}

async function loadedImage(image: Locator) {
    await expect(image).toBeVisible();
    await expect
        .poll(() =>
            image.evaluate((el) => {
                const img = el as HTMLImageElement;
                return img.complete && img.naturalWidth > 0;
            }),
        )
        .toBe(true);
}

test('uploader deep link and edited multi-selection survive list-grid-list and reload', async ({uploaderPage: page}) => {
    await page.goto('/files?tab=static&filename=review-scope&uploader=41,8080');
    let table = await settledTable(page, 'static');
    const allIds = Object.values(FILES).map((file) => file.id);
    await expectRows(table, [FILES.atlas.id, FILES.unknown.id], allIds);
    await expect(await uploaderCell(table, FILES.atlas.id)).toContainText('Review Atlas');
    await expect(await uploaderCell(table, FILES.unknown.id)).toContainText('#8080');
    let popover = await openUploader(table);
    await expect(popover.getByTestId('filter-enum-option-41')).toHaveAttribute('data-checked', 'true');
    await expect(popover.getByTestId('filter-enum-option-8080')).toHaveAttribute('data-checked', 'true');
    await expect(popover.getByTestId('filter-enum-option-7')).toHaveAttribute('data-checked', 'false');

    // Change the selection away from the initial URL to expose stale
    // initialFilters on remount; retain Atlas to check filename AND uploader.
    await popover.getByTestId('filter-enum-search').fill('Zephyr');
    await expect(popover.getByTestId('filter-enum-option-7')).toContainText('Review Zephyr');
    await popover.getByTestId('filter-enum-option-7').click();
    await popover.getByTestId('filter-enum-search-clear').click();
    await expect(popover.getByTestId('filter-enum-search')).toHaveValue('');
    await expect(popover.getByTestId('filter-enum-option-7')).toHaveAttribute('data-checked', 'true');
    await expect(popover.getByTestId('filter-enum-option-8080')).toHaveAttribute('data-checked', 'true');
    await closeUploader(table);
    const selected = [FILES.atlas, FILES.zephyr, FILES.unknown];
    await expectRows(
        table,
        selected.map((file) => file.id),
        allIds,
    );
    await expectUrl(page, 'static', ['41', '7', '8080'], 'review-scope');

    await page.getByTestId('view-mode-grid').click();
    await expectGrid(page, selected);
    await expectUrl(page, 'static', ['41', '7', '8080'], 'review-scope');
    await page.getByTestId('view-mode-list').click();
    table = await settledTable(page, 'static');
    await expectRows(
        table,
        selected.map((file) => file.id),
        allIds,
    );
    popover = await openUploader(table);
    for (const id of ['41', '7', '8080']) await expect(popover.getByTestId(`filter-enum-option-${id}`)).toHaveAttribute('data-checked', 'true');
    await expect(popover.getByTestId('filter-enum-option-91')).toHaveAttribute('data-checked', 'false');
    await closeUploader(table);

    // A new document must re-parse the serialized multi-filter, not inherit the
    // old Files page instance's currentFilters object.
    await page.reload();
    table = await settledTable(page, 'static');
    await expectRows(
        table,
        selected.map((file) => file.id),
        allIds,
    );
    await expectUrl(page, 'static', ['41', '7', '8080'], 'review-scope');
    await page.getByTestId('view-mode-grid').click();
    await expectGrid(page, selected);
});

test('BRIM URL keeps an unknown numeric uploader distinct from an absent owner', async ({uploaderPage: page}) => {
    await page.goto('/files?tab=brim&uploader=8080,__none__');
    let table = await settledTable(page, 'brim');
    const allIds = Object.values(REPORTS).map((file) => file.file_id);
    await expectRows(table, [REPORTS.unknown.file_id, REPORTS.none.file_id], allIds);
    await expect(await uploaderCell(table, REPORTS.unknown.file_id)).toContainText('#8080');
    let popover = await openUploader(table);
    await expect(popover.getByTestId('filter-enum-option-8080')).toHaveAttribute('data-checked', 'true');
    await expect(popover.getByTestId('filter-enum-option-__none__')).toHaveAttribute('data-checked', 'true');
    await expect(popover.getByTestId('filter-enum-option-41')).toHaveAttribute('data-checked', 'false');
    await popover.getByTestId('filter-enum-option-8080').click();
    await closeUploader(table);
    await expectRows(table, [REPORTS.none.file_id], allIds);
    await expectUrl(page, 'brim', ['__none__']);

    await page.reload();
    table = await settledTable(page, 'brim');
    await expectRows(table, [REPORTS.none.file_id], allIds);
    popover = await openUploader(table);
    await expect(popover.getByTestId('filter-enum-option-__none__')).toHaveAttribute('data-checked', 'true');
    await expect(popover.getByTestId('filter-enum-option-8080')).toHaveAttribute('data-checked', 'false');
    await popover.getByTestId('filter-enum-option-41').click();
    await closeUploader(table);
    await expectRows(table, [REPORTS.none.file_id, REPORTS.atlas.file_id], allIds);
    await expectUrl(page, 'brim', ['__none__', '41']);
});

test('uploader avatars load, fall back after real image errors, and retain circular 20px clipping', async ({uploaderPage: page}) => {
    await page.goto('/files?tab=static&filename=review-scope');
    const table = await settledTable(page, 'static');
    const goodCell = await uploaderCell(table, FILES.atlas.id);
    const good = goodCell.locator('img');
    await expect(good).toHaveAttribute('src', `${AVATAR_GOOD}?img_preview=32x32`);
    await loadedImage(good);
    await expect(goodCell).toContainText('Review Atlas');
    await expect(good.locator('xpath=following-sibling::span').locator('svg')).toBeHidden();

    const brokenCell = await uploaderCell(table, FILES.zephyr.id);
    const broken = brokenCell.locator('img');
    await expect(broken).toHaveAttribute('src', `${AVATAR_BROKEN}?img_preview=32x32`);
    // A real intercepted 404 fires the native error handler. No synthetic DOM
    // event and no negative assertion that could pass while an image is pending.
    await expect.poll(() => broken.evaluate((el) => (el as HTMLImageElement).complete)).toBe(true);
    await expect(broken.locator('xpath=following-sibling::span').locator('svg')).toBeVisible();
    await expect(broken).toBeHidden();
    await expect(brokenCell).toContainText('Review Zephyr');

    for (const file of [FILES.nimbus, FILES.unknown]) {
        const image = (await uploaderCell(table, file.id)).locator('img');
        await expect(image).toHaveAttribute('src', /^data:image\/svg\+xml,/);
        await loadedImage(image);
    }
    const popover = await openUploader(table);
    const goodOption = popover.getByTestId('filter-enum-option-41').locator('img');
    await expect(goodOption).toHaveAttribute('src', `${AVATAR_GOOD}?img_preview=32x32`);
    await loadedImage(goodOption);
    const brokenOption = popover.getByTestId('filter-enum-option-7');
    await expect(brokenOption).toContainText('Review Zephyr');
    await expect(brokenOption.locator('img')).toHaveAttribute('src', /^data:image\/svg\+xml,/);
    await loadedImage(brokenOption.locator('img'));
    await closeUploader(table);

    await goodCell.scrollIntoViewIfNeeded();
    const clip = good.locator('..');
    await expect(clip).toHaveCSS('overflow', 'hidden');
    await expect(clip).toHaveCSS('border-top-left-radius', '50%');
    await expect(good).toHaveAttribute('width', '20');
    await expect(good).toHaveAttribute('height', '20');
    await expect(clip).toHaveCSS('height', '20px');
    // Keep this contract exact: DataTable's current min-width:32px conflicts
    // with FilesTable's size:20 and makes the clipping box elliptical (32×20).
    // Do not bless that source defect by asserting only border-radius:50%.
    await expect(clip).toHaveCSS('width', '20px');
});
