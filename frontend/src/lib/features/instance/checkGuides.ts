/**
 * The guide of each security check: the section of the admin guide that explains it (workstream H, for the «Guide»
 * button of the Security tab, A's N69d).
 *
 * The data is `checkGuides.json`, read here and by the backend's test of the checks
 * (`backend/test_scripts/test_services/test_config_audit.py`): `server` holds every check of `GET /security/checks`, in
 * the order the server evaluates them, and `browser` the findings the browser adds itself
 * (`accounts.openRegistration`). A new check needs its entry there.
 *
 * A value is a path below `/mkdocs/`, `admin/<page>/#<anchor>`: no language and no leading `/`. `DocsLink` adds the
 * user's language; an anchor is an explicit one of the English page (`{: #anchor }`), the same in every translation.
 * The same guide serves every state of a check, passed ones included.
 */
import guides from './checkGuides.json';

/** Every check's guide, by the id of its finding: `server` and `browser` together. */
export const CHECK_GUIDES: Readonly<Record<string, string>> = Object.freeze({...guides.server, ...guides.browser});

/** The guide of a check, or `undefined` for an id that has none (then the tab shows no «Guide» button). */
export function checkGuidePath(checkId: string): string | undefined {
    return Object.hasOwn(CHECK_GUIDES, checkId) ? CHECK_GUIDES[checkId] : undefined;
}
