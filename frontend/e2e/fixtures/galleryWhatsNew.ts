/**
 * Gallery, `changelog/whats-new-modal`: the «What's new since your last version» modal a signed-in user meets after an update.
 *
 * The lane runs with the feature off (`LIBREFOLIO_DISABLE_WHATS_NEW=1`): its `GET /api/v1/auth/me` says `user.whats_new: null`.
 * As `layout/whats-new.spec.ts` does, the page gets the value from here: the real answer, `user.whats_new` replaced
 * (`route.fetch()`, then fulfil; the two headers that describe the body in transit dropped), checked against the generated
 * schema. `POST /api/v1/auth/whats-new/seen` is answered 204 here and never reaches the lane: nothing is marked seen for the
 * shared user. `{since: null, release}` shows the release chapter alone; `release` is the newest released chapter of the
 * repository's CHANGELOG.md, the file the build bundles, read at run time — no version is written down here.
 *
 * Registered before the first navigation, the routes stay with the page for the whole test; the gallery's outer afterEach
 * drops them once the page has left (`leaveGalleryPage`).
 */
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {schemas} from '../../src/lib/api/generated';
import {expect, type Page} from './playwright';

const AUTH_ME_PATH = '/api/v1/auth/me';
const SEEN_PATH = '/api/v1/auth/whats-new/seen';

/** The newest released chapter (`## [x.y.z] - date`, with a body) of the repository's CHANGELOG.md. */
function newestReleasedVersion(): string {
    const path = fileURLToPath(new URL('../../../CHANGELOG.md', import.meta.url));
    const chapters: Array<{version: string; dated: boolean; body: boolean}> = [];
    for (const line of readFileSync(path, 'utf8').split('\n')) {
        const heading = /^## \[([^\]]+)\](?:\s*-\s*(.+?))?\s*$/.exec(line);
        if (heading) chapters.push({version: heading[1], dated: heading[2] !== undefined, body: false});
        else if (chapters.length > 0 && line.trim().length > 0) chapters[chapters.length - 1].body = true;
    }
    const released = chapters.filter((chapter) => /^\d+\.\d+\.\d+$/.test(chapter.version) && chapter.dated && chapter.body).map((chapter) => chapter.version);
    expect(released.length, 'positive control: CHANGELOG.md has a released chapter').toBeGreaterThan(0);
    return released.sort((a, b) => {
        const [x, y] = [a, b].map((version) => version.split('.').map(Number));
        return y[0] - x[0] || y[1] - x[1] || y[2] - x[2];
    })[0];
}

/** Have every load of `page` meet the modal for the newest release, and answer its «seen» here. Call before the first navigation. */
export async function serveGalleryWhatsNew(page: Page): Promise<void> {
    const release = newestReleasedVersion();
    await page.route(
        (url) => url.pathname === AUTH_ME_PATH,
        async (route, request) => {
            if (request.method() !== 'GET') return route.fallback();
            const response = await route.fetch();
            const headers = {...response.headers()};
            delete headers['content-encoding'];
            delete headers['content-length'];
            if (!response.ok()) return route.fulfill({status: response.status(), headers, body: await response.body()});
            const body = (await response.json()) as {user?: Record<string, unknown>};
            if (!body.user || !('whats_new' in body.user)) throw new Error(`the real GET ${AUTH_ME_PATH} has no user.whats_new: the stub changes the field, never adds it`);
            const changed = schemas.AuthMeResponse.parse({...body, user: {...body.user, whats_new: {since: null, release}}});
            await route.fulfill({status: response.status(), headers, json: changed});
        },
    );
    await page.route(
        (url) => url.pathname === SEEN_PATH,
        async (route, request) => route.fulfill({status: request.method() === 'POST' ? 204 : 405}),
    );
}
