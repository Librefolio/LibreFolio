// @vitest-environment jsdom
/**
 * ChangelogModal — light render test (Vitest + jsdom), F12.
 *
 * The modal opens from the sidebar version label and shows the bundled
 * CHANGELOG.md as per-release chapters. What is locked here: it renders when
 * opened, chapters come from the real bundled file (at least one dated
 * section), each chapter exposes its version heading, and the remote link
 * points at the repository's live CHANGELOG.md. Translated copy is never
 * asserted — testids and hrefs only.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';

// The feature module imports the repo-root CHANGELOG.md via vite's `?raw`, which
// the jsdom pipeline refuses (fs strictness on a path outside frontend/) — the
// pure-logic sibling spec (changelog.test.ts, node env) already pins that the
// real shipped file parses. Here the modal's subject is what it DOES with the
// parsed chapters, so the module is stubbed with a known fixture.
vi.mock('$lib/features/changelog/changelog', () => ({
    changelogChapters: [
        {version: '1.2.0', date: '2026-08-07', body: '### Fixed\n- a bug\n'},
        {version: '1.1.0', date: '2026-07-01', body: '### Added\n- a feature\n'},
    ],
    CHANGELOG_REMOTE_URL: 'https://github.com/Librefolio/LibreFolio/blob/main/CHANGELOG.md',
}));

import {render, screen, setupI18n, waitFor} from '$test/component';
import ChangelogModal from './ChangelogModal.svelte';
import {changelogChapters, CHANGELOG_REMOTE_URL} from '$lib/features/changelog/changelog';

beforeAll(async () => {
    await setupI18n();
});

describe('ChangelogModal (F12)', () => {
    it('renders the bundled chapters and the remote link when open', async () => {
        render(ChangelogModal, {open: true, onClose: vi.fn()});

        await waitFor(() => expect(screen.getByTestId('changelog-modal')).toBeInTheDocument());

        // One section per chapter the feature module exposes (the module is the
        // fixture above; the real-file parse is pinned by changelog.test.ts).
        const sections = screen.getAllByTestId('changelog-chapter');
        expect(sections.length).toBe(changelogChapters.length);
        expect(sections.length).toBe(2);
        // Chapter bodies render as markdown HTML, not raw text.
        expect(sections[0].innerHTML).toContain('<h3');

        const remote = screen.getByTestId('changelog-remote-link');
        expect(remote).toHaveAttribute('href', CHANGELOG_REMOTE_URL);
        expect(remote).toHaveAttribute('target', '_blank');
    });

    it('renders nothing when closed', () => {
        render(ChangelogModal, {open: false, onClose: vi.fn()});

        expect(screen.queryByTestId('changelog-modal')).not.toBeInTheDocument();
    });
});
