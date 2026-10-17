/**
 * «What's new since your last version» (C-54): which changelog chapters to show, once.
 *
 * The backend says whether there is anything new and from which release (`user.whats_new`, in the login and
 * `/auth/me`): `since` is the release whose changelog the user saw last — null for an account from before the
 * feature, which sees the running release's chapter only — and `release` the one the instance runs. The chapters come
 * from the changelog the app bundles: released ones only, never `[Unreleased]`, newest first as the file has them.
 */
import {compareVersions} from '$lib/features/update-check/updateCheck';
import type {ChangelogChapter} from './changelog';

export interface WhatsNew {
    since: string | null;
    release: string;
}

/** The chapters of `chapters` to show for `whatsNew`, in their order: `since < version ≤ release`, or `release` alone. */
export function whatsNewChapters<T extends ChangelogChapter>(chapters: readonly T[], whatsNew: WhatsNew | null | undefined): T[] {
    if (!whatsNew) return [];
    const {since, release} = whatsNew;
    return chapters.filter((chapter) => {
        if (chapter.version.trim().toLowerCase() === 'unreleased') return false;
        const toRelease = compareVersions(chapter.version, release);
        if (Number.isNaN(toRelease) || toRelease > 0) return false;
        if (since === null) return toRelease === 0;
        const toSince = compareVersions(chapter.version, since);
        return !Number.isNaN(toSince) && toSince > 0;
    });
}
