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
 * The mechanism below is deliberately id-based rather than response-based: take a
 * snapshot before, delete whatever is new after. It therefore also catches rows
 * created indirectly (a paired half, a promoted transfer) that the spec never
 * named — which is exactly the kind of write that gets forgotten.
 */
import type {Page} from './playwright';

const TX_ENDPOINT = '/api/v1/transactions';

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

/**
 * Delete every transaction that appeared after `before` was taken.
 *
 * Returns how many rows were removed, so a spec can assert it cleaned up what it
 * thinks it created. Deleting one half of a linked pair removes both, so ids that
 * have already gone are skipped rather than retried.
 */
export async function deleteTransactionsCreatedSince(page: Page, before: Set<number>): Promise<number> {
    const now = await snapshotTransactionIds(page);
    const created = [...now].filter((id) => !before.has(id));
    if (created.length === 0) return 0;

    const res = await page.request.post(`${TX_ENDPOINT}/commit`, {
        data: {creates: [], updates: [], deletes: created},
    });
    if (!res.ok()) {
        throw new Error(`Transaction cleanup failed: ${res.status()} ${res.statusText()} — leftover ids ${created.join(', ')}`);
    }
    return created.length;
}
