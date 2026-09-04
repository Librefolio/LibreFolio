/**
 * Dates, read the way the application reads them.
 *
 * Every spec that needed "today" used to write its own
 * `new Date().toISOString().slice(0, 10)`, and every one of those was wrong in
 * the same way: it answers in **UTC** while the app renders the **user's**
 * calendar. The two agree for 22 hours a day, so the specs passed — until they
 * were run between midnight and the runner's UTC offset, when `tx-clone` went
 * red on two tests asserting that a cloned row carries today's date.
 *
 * That is the whole failure mode of a copied helper: it is not that one copy is
 * wrong, it is that nobody can see the other three from where they are standing.
 *
 * The product's own version lives in `src/lib/utils/dateOnly.ts`, but Playwright
 * specs run outside the SvelteKit build and cannot resolve the `$lib` alias, so
 * the rule is restated here — once — rather than in each spec.
 */

/** Format a Date as `YYYY-MM-DD` on the local calendar, never in UTC. */
export function localIso(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** Today, as the application shows it to the user running these tests. */
export function todayIso(): string {
    return localIso(new Date());
}

/** `days` before today, on the local calendar. Negative values look forward. */
export function daysAgoIso(days: number): string {
    const d = new Date();
    d.setDate(d.getDate() - days);
    return localIso(d);
}
