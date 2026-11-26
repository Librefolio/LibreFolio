/**
 * initialAvatar.ts — an initial on a coloured disc, as an SVG data URL: what the Files table draws for an uploader without
 * a picture, and the asset profile for the system (87, A2). The disc's colour follows the `seed`, so the same uploader
 * has the same disc wherever it is drawn.
 */
import {getStringColor} from '$lib/utils/colors';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {fileAvatarInitialColor} from '$lib/theme/drawnColors';
import {chartRoles} from '$lib/theme/roleColors';
import {isDarkTheme} from '$lib/theme/themeMode';

/** The seed of what the installation itself uploaded or wrote (user 0): the Files page's «System» disc. */
export const SYSTEM_AVATAR_SEED = 'uploader:0';

/** The initial of `label` on the disc of `seed`, read in the theme of the moment it is built. */
export function initialAvatarDataUrl(label: string, seed: string): string {
    const initial = (label.trim().charAt(0) || '?').toUpperCase();
    const bg = getStringColor(seed).text;
    // An SVG data URL cannot follow a `var()`: the initial is the role that reads best on this disc, read when the
    // avatar is built. Its two candidates are near-black and near-white in both themes.
    const fg = fileAvatarInitialColor(chartRoles(isDarkTheme()), bg);
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none"><rect width="32" height="32" rx="16" fill="${bg}"/><text x="16" y="21" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="15" font-weight="700" fill="${fg}">${escapeHtml(initial)}</text></svg>`;
    return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}
