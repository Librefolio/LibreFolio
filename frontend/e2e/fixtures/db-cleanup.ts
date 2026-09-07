/**
 * Shared-state cleanup helpers for E2E specs.
 *
 * ## Why this exists
 *
 * `Transaction` is a **global** table: it has no `user_id`, and isolation happens
 * at service level through broker access. So a spec that commits a transaction
 * and walks away leaves that row visible to every spec that runs afterwards.
 *
 * As long as the runner spent one Playwright process per spec, nobody noticed:
 * `globalSetup` re-populated the database before every invocation and wiped the
 * evidence. The moment specs are consolidated into one invocation — which is the
 * whole point of the parallel runner — the leftovers become other specs' input.
 *
 * Measured instance: `tx-clone.spec.ts` commits a real cloned pair, picking "the
 * first paired giver row on editable brokers". That is the `delete-safe` ETH
 * TRANSFER. `tx-delete.spec.ts` then deletes that pair and asserts no
 * `delete-safe` ETH row survives — and finds the clone.
 *
 * ## The rule
 *
 * **Whoever commits, cleans up.** A spec that writes to a global surface must
 * restore it, in its own `test.afterAll`, without depending on a fresh database.
 *
 * ## Why "everything new" is not the same as "mine"
 *
 * The first version of this helper took a snapshot before and deleted whatever was new
 * after. That reads "new" as "mine", which was true only while one Playwright process ran
 * at a time. Under concurrent workers the rows a neighbour is *currently using* are also
 * new, and this helper deleted them — or tried to, and failed with a 500 on a row the
 * neighbour had already removed, which is how the problem finally became visible.
 *
 * So ownership is now the **intersection** of two independent facts:
 *
 *   1. the id was reported by a `/transactions/commit` this page performed — proving it
 *      is ours, and catching rows created indirectly (a paired half, a promoted transfer)
 *      that the spec never named, because the commit response lists them too;
 *   2. the id was absent from the snapshot taken before the spec ran — proving we created
 *      it rather than merely touching it, so a split or promote of fixture data can never
 *      delete the fixture row it was derived from.
 *
 * Either fact alone is unsafe. Together they are exact.
 */
import type {Page} from './playwright';

const TX_ENDPOINT = '/api/v1/transactions';

/** Operations whose reported ids are rows that came into existence. */
const CREATING_OPERATIONS = new Set(['create', 'split', 'promote']);

interface CommitResultItem {
    operation: string;
    ids?: number[];
}

interface CommitBody {
    committed?: boolean;
    results?: CommitResultItem[];
}

/**
 * Every transaction id currently visible to the logged-in user.
 *
 * The page must already be authenticated: `page.request` shares the browser
 * context's cookie jar, and the API authenticates via an HTTP-only session
 * cookie.
 */
export async function snapshotTransactionIds(page: Page): Promise<Set<number>> {
    const res = await page.request.get(TX_ENDPOINT);
    if (!res.ok()) {
        throw new Error(`Transaction snapshot failed: ${res.status()} ${res.statusText()}`);
    }
    const rows = (await res.json()) as Array<{id: number}>;
    return new Set(rows.map((r) => r.id));
}

/** Handle returned by {@link trackTransactionWrites}. */
export interface TransactionWriteTracker {
    /** Delete the rows this page created since tracking began. Returns how many were removed. */
    cleanup: () => Promise<number>;
    /** Stop listening. Called by `cleanup`; exposed for specs that end tracking early. */
    stop: () => void;
}

/**
 * Start recording the transactions this page creates, and return the handle that removes
 * them again.
 *
 * Takes the "before" snapshot itself so the two halves of the ownership test cannot drift
 * apart: a caller that forgot the snapshot would silently fall back to deleting by response
 * alone, which is the unsafe half.
 */
export async function trackTransactionWrites(page: Page): Promise<TransactionWriteTracker> {
    const preexisting = await snapshotTransactionIds(page);
    const created = new Set<number>();

    const onResponse = (res: {url: () => string; ok: () => boolean; json: () => Promise<unknown>}) => {
        if (!res.url().includes(`${TX_ENDPOINT}/commit`) || !res.ok()) return;
        // Not awaited: Playwright buffers the body, and awaiting here would serialise the
        // handler against the page's own navigation.
        void res
            .json()
            .then((raw) => {
                const body = raw as CommitBody;
                if (body.committed !== true) return;
                for (const item of body.results ?? []) {
                    if (!CREATING_OPERATIONS.has(item.operation)) continue;
                    for (const id of item.ids ?? []) {
                        if (!preexisting.has(id)) created.add(id);
                    }
                }
            })
            .catch(() => {
                /* body unavailable (navigation, non-JSON): nothing to record */
            });
    };

    page.on('response', onResponse);
    const stop = () => page.off('response', onResponse);

    return {
        stop,
        async cleanup(): Promise<number> {
            stop();
            const ids = [...created];
            if (ids.length === 0) return 0;
            // A row may already be gone: deleting one half of a linked pair removes both.
            const stillThere = await snapshotTransactionIds(page);
            const deletes = ids.filter((id) => stillThere.has(id));
            if (deletes.length === 0) return 0;
            const res = await page.request.post(`${TX_ENDPOINT}/commit`, {
                data: {creates: [], updates: [], deletes},
            });
            if (!res.ok()) {
                throw new Error(`Transaction cleanup failed: ${res.status()} ${res.statusText()} — leftover ids ${deletes.join(', ')}`);
            }
            created.clear();
            return deletes.length;
        },
    };
}
