import {escapeHtml} from './escapeHtml';

type EntityLinkTarget = {kind: 'asset'; id: number} | {kind: 'fx'; slug: string};

/** Only known internal detail routes may be embedded in a toast's HTML. */
export function entityDetailLinkHtml(target: EntityLinkTarget, label: string): string {
    let href: string;
    if (target.kind === 'asset') {
        if (!Number.isSafeInteger(target.id) || target.id <= 0) {
            throw new Error('Asset detail links require a positive integer ID');
        }
        href = `/assets/${target.id}`;
    } else {
        if (target.slug.length !== 7 || !/^[A-Z]{3}-[A-Z]{3}$/.test(target.slug)) {
            throw new Error('FX detail links require an AAA-BBB pair slug');
        }
        href = `/fx/${target.slug}`;
    }
    return `<a href="${href}" class="underline font-semibold hover:no-underline" data-testid="toast-${target.kind}-link">${escapeHtml(label)}</a>`;
}
