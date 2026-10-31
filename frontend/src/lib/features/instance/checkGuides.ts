/**
 * Who can solve each security check, and where its help is (workstream H, for the «Guide» and «Contact support» buttons
 * of the Security tab, A's N69d and FB-27).
 *
 * The data is `checkGuides.json`, read here and by the backend's test of the checks
 * (`backend/test_scripts/test_services/test_config_audit.py`): `server` holds every check of `GET /security/checks`, in
 * the order the server evaluates them, and `browser` the findings the browser adds itself
 * (`accounts.openRegistration`, `platform.blockedScript`). A new check needs its entry there, and the entry says who
 * solves it:
 * - `guide`: the administrator, alone. `path` is a path below `/mkdocs/`, `admin/<page>/#<anchor>`: no language and no
 *   leading `/`. `DocsLink` adds the user's language; an anchor is an explicit one of the English page
 *   (`{: #anchor }`), the same in every translation. The same guide serves every state of a check, passed ones
 *   included. A limit that also applies to a self-hosted instance (`backup.upload_limit`) is a `guide`.
 * - `support`: whoever hosts the instance. The button writes to the instance's support address
 *   (`LIBREFOLIO_SUPPORT_URL`) with the check's code, never a page of the guide.
 */
import guides from './checkGuides.json';

/** The help of a check: a section of the administrator's guide, or the instance's support. */
export type CheckHelp = {kind: 'guide'; path: string} | {kind: 'support'};

/** Every check's help, by the id of its finding: `server` and `browser` together. */
export const CHECK_HELP: Readonly<Record<string, CheckHelp>> = Object.freeze({...guides.server, ...guides.browser} as Record<string, CheckHelp>);

/** The help of a check, or `undefined` for an id that has none (then the tab shows no button). */
export function checkHelp(checkId: string): CheckHelp | undefined {
    return Object.hasOwn(CHECK_HELP, checkId) ? CHECK_HELP[checkId] : undefined;
}

/** Every check that has a guide, by id: its path. A check for the host's support has no entry here. */
export const CHECK_GUIDES: Readonly<Record<string, string>> = Object.freeze(Object.fromEntries(Object.entries(CHECK_HELP).flatMap(([id, help]) => (help.kind === 'guide' ? [[id, help.path]] : []))));

/** The guide of a check, or `undefined` for an id that has none or whose help is the host's support. */
export function checkGuidePath(checkId: string): string | undefined {
    return Object.hasOwn(CHECK_GUIDES, checkId) ? CHECK_GUIDES[checkId] : undefined;
}
