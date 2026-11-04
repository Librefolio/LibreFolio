/**
 * Opening a tab of the Settings page, whichever bar it sits in (release 1.3, workstream A, lot A8b; decision P13 b).
 *
 * The top bar holds Profile, Preferences, Plugins, About and, for an administrator only, «Administration»
 * (`settings-tab-administration`, on the right). The group stands for its members — Global Settings (`admin`), Users,
 * Backup, Email and Security —, every one of them an administrator's, which a second bar inside `settings-subtabs`
 * shows while one of them is open. A member of the instance has no group, no second bar and no member tab (N69-2,
 * decision D4 a; `routes/(app)/settings/+page.svelte`, `settingsTabs.ts`). A member tab is therefore never clicked
 * from the top bar: {@link openSettingsTab} goes through the group.
 *
 * `?tab=` needs no helper: `?tab={member}` opens that member directly inside its group (the second bar drawn for an
 * administrator), and `?tab=administration` opens the group's first member.
 */
import {expect, type Locator, type Page} from './playwright';

/** The members of the «Administration» group, in the order of the registry (`settingsTabs.ts`). */
export const ADMINISTRATION_TAB_IDS: readonly string[] = ['admin', 'users', 'backup', 'email', 'security'];

/** The group's own id: the suffix of its tab, `settings-tab-administration`, and a `?tab=` value. */
export const ADMINISTRATION_GROUP_ID = 'administration';

// Budgets: deadlines, never delays.
/** From a navigation to the bars drawn: the app's auth check and bootstrap, then the page's first render. */
const BAR_MS = 20_000;
/** A click on a tab already on screen, and the selection it makes. */
const SELECT_MS = 5_000;

/** Click `tab` once it is drawn, and return once it reads selected. */
async function selectTab(tab: Locator, testId: string, drawnMs: number): Promise<void> {
    await expect(tab, `${testId} is drawn`).toBeVisible({timeout: drawnMs});
    await tab.click();
    await expect(tab, `${testId} is selected once clicked`).toHaveAttribute('aria-selected', 'true', {timeout: SELECT_MS});
}

/**
 * Open Settings tab `id` — a tab of the top bar, or a member of «Administration» — on the Settings page already on
 * view, and return once that tab reads `aria-selected="true"`.
 *
 * - Not a member (`profile`, `preferences`, `plugins`, `about`, or `administration` itself): its tab is clicked.
 * - A member: «Administration» is clicked and read selected; then, when the second bar is drawn (an administrator), the
 *   member's tab in it is clicked and read selected — `admin` too, since clicking the group while another member is open
 *   keeps that member open. Only an administrator has the group, and sees all its members, so the second bar is always
 *   there (N69-2, decision D4 a); without it, the helper opens nothing more for `admin`, and throws for any other
 *   member. A member of the instance has no group at all: for any member tab, the helper fails on the group's tab,
 *   never drawn.
 *
 * Reading the second bar once is deterministic, not a probe: the page derives the top bar's selection and the second
 * bar from the same `activeTab`, so the update that marks the group selected draws the second bar too, or leaves it
 * out for good. Once the group reads `aria-selected="true"`, `count()` gives the final answer.
 */
export async function openSettingsTab(page: Page, id: string): Promise<void> {
    if (!ADMINISTRATION_TAB_IDS.includes(id)) {
        await selectTab(page.getByTestId(`settings-tab-${id}`), `settings-tab-${id}`, BAR_MS);
        return;
    }
    const groupTestId = `settings-tab-${ADMINISTRATION_GROUP_ID}`;
    await selectTab(page.getByTestId(groupTestId), groupTestId, BAR_MS);
    const subtabs = page.getByTestId('settings-subtabs');
    if ((await subtabs.count()) === 0) {
        if (id !== 'admin') {
            throw new Error(`openSettingsTab('${id}'): «Administration» drew no second bar, which an administrator always has since N69-2 (every member of the group is theirs), so settings-tab-${id} cannot be opened`);
        }
        return;
    }
    await selectTab(subtabs.getByTestId(`settings-tab-${id}`), `settings-subtabs › settings-tab-${id}`, SELECT_MS);
}
