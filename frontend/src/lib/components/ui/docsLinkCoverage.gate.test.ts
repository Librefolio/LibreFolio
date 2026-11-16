/**
 * The docs icon on every panel (RN-13, B1: «DocsLink su tutti i pannelli»).
 *
 * The form the developer fixed on 24/09/2026: the book icon alone, on the right edge of the panel's header; its
 * tooltip explains THAT panel in a few sentences (its own key, even when two panels share a page); the click opens
 * the page, without anchor. One row per panel: the source that draws its header, the user or admin page it opens and
 * the key of its tooltip. Read in the source, as `scripts/docs_links.py` reads it — the same literal `path="…"` the link gate
 * checks against the built site (`dev.py mkdocs check-links`), so a row here is a link that exists there. A row is
 * added with its panel, group by group (inventory in the lane's notes, 16/11/2026); a panel that loses its icon fails
 * here by name.
 *
 * Out on purpose (coordinator, 16/11/2026): modals and the AI Export popover (a dialog is not a page panel), the
 * `/welcome` page, the old Asset Detail risk tab (replaced by RN-17).
 */
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {describe, expect, it} from 'vitest';

const SRC = resolve(__dirname, '../../..');

/** [source under `frontend/src`, docs path the icon opens, i18n key of its tooltip — the panel's own help] */
const PANELS: ReadonlyArray<readonly [string, string, string]> = [
    // Group 3 — the risk header of Dashboard and Broker (a prop: Asset Detail passes its own with RN-17).
    ['lib/features/risk/levels/RiskPanelHeader.svelte', 'user/dashboard/risk/', 'risk.docsHelp.header'],
    // Group 5 — brokers.
    ['routes/(app)/brokers/+page.svelte', 'user/brokers/', 'brokers.docsHelp.list'],
    ['routes/(app)/brokers/[id]/+page.svelte', 'user/brokers/info/', 'brokers.docsHelp.info'],
    ['routes/(app)/brokers/[id]/+page.svelte', 'user/brokers/sharing/', 'brokers.docsHelp.sharing'],
    // Group 8 — FX.
    ['routes/(app)/fx/+page.svelte', 'user/fx/', 'fx.docsHelp.list'],
    ['routes/(app)/fx/[pair]/+page.svelte', 'user/fx/detail/', 'fx.docsHelp.detail'],
    // Group 9 — files and backups.
    ['routes/(app)/files/+page.svelte', 'user/files/', 'uploads.docsHelp'],
    ['lib/features/backup/BackupsSection.svelte', 'admin/backup_restore/', 'backup.docsHelp'],
    // Group 11 — settings.
    ['lib/features/settings/tabs/ProfileTab.svelte', 'user/settings/profile/', 'settings.docsHelp.profile'],
    ['lib/features/settings/tabs/GlobalSettingsTab.svelte', 'admin/settings/', 'settings.docsHelp.global'],
    ['lib/features/settings/tabs/AboutTab.svelte', 'user/settings/about/', 'settings.docsHelp.about'],
    ['lib/features/settings/tabs/UsersTab.svelte', 'admin/users/', 'settings.docsHelp.users'],
    ['lib/features/settings/security/SecurityTab.svelte', 'admin/configuration_security/', 'settings.docsHelp.security'],
];

function escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

describe('every panel carries its docs icon (RN-13, B1)', () => {
    it.each(PANELS)('%s opens %s, its tooltip %s', (file, docsPath, helpKey) => {
        const source = readFileSync(resolve(SRC, file), 'utf-8');
        const link = new RegExp(`<DocsLink\\b[^>]*\\bpath=["']${escapeRegExp(docsPath)}["']`);
        const prop = new RegExp(`docsPath\\s*=\\s*["']${escapeRegExp(docsPath)}["']`);
        expect(link.test(source) || (source.includes('<DocsLink') && prop.test(source)), `${file} draws no docs icon opening ${docsPath}`).toBe(true);
        const help = new RegExp(`<DocsLink\\b[^>]*\\blabel=\\{\\$[_t]\\(['"]${escapeRegExp(helpKey)}['"]\\)\\}`);
        expect(help.test(source), `${file}: the icon's tooltip is not the panel's own help ${helpKey}`).toBe(true);
    });
});
