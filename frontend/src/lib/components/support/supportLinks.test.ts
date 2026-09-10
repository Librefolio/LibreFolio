import {describe, expect, it} from 'vitest';
import {BUY_ME_A_COFFEE_URL, PUBLIC_PROJECT_URL, SOCIAL_SHARE_CONFIG, buildSocialShareCopy, buildSocialShareUrl} from './supportLinks';

describe('supportLinks — public support destinations', () => {
    it('pins the public project and donation URLs to the shared support pages', () => {
        expect(PUBLIC_PROJECT_URL).toBe('https://librefolio.github.io/LibreFolio/');
        expect(BUY_ME_A_COFFEE_URL).toBe('https://www.buymeacoffee.com/librefolio');
    });
});

describe('supportLinks — social share URLs', () => {
    it('builds each platform contract without inventing unsupported prefills', () => {
        const message = 'ReviewSupport says hello\n#ReviewSupport #LibreFolio';
        const redditTitle = 'ReviewSupport short title';
        const xShare = new URL(buildSocialShareUrl('x', message));
        const redditShare = new URL(buildSocialShareUrl('reddit', message, redditTitle));
        const facebookShare = new URL(buildSocialShareUrl('facebook', message));
        const instagramShare = new URL(buildSocialShareUrl('instagram', message));
        const tiktokShare = new URL(buildSocialShareUrl('tiktok', message));

        expect(`${xShare.origin}${xShare.pathname}`).toBe(SOCIAL_SHARE_CONFIG.x.intentUrl);
        expect(xShare.searchParams.get('text')).toBe(message);
        expect(xShare.searchParams.get('url')).toBe(PUBLIC_PROJECT_URL);

        expect(`${redditShare.origin}${redditShare.pathname}`).toBe(SOCIAL_SHARE_CONFIG.reddit.intentUrl);
        expect(redditShare.searchParams.get('type')).toBe('TEXT');
        expect(redditShare.searchParams.get('selftext')).toBe('true');
        expect(redditShare.searchParams.get('title')).toBe(redditTitle);
        expect(redditShare.searchParams.get('text')).toBe(buildSocialShareCopy(message));
        expect(redditShare.searchParams.get('url')).toBeNull();

        expect(`${facebookShare.origin}${facebookShare.pathname}`).toBe(SOCIAL_SHARE_CONFIG.facebook.intentUrl);
        expect(facebookShare.searchParams.get('u')).toBe(PUBLIC_PROJECT_URL);
        expect(facebookShare.searchParams.get('text')).toBeNull();
        expect(facebookShare.searchParams.get('title')).toBeNull();

        expect(instagramShare.toString()).toBe(SOCIAL_SHARE_CONFIG.instagram.intentUrl);
        expect(instagramShare.search).toBe('');

        expect(`${tiktokShare.origin}${tiktokShare.pathname}`).toBe(SOCIAL_SHARE_CONFIG.tiktok.intentUrl);
        expect(tiktokShare.search).toBe('');
    });

    it('requires a separate Reddit title but keeps it optional elsewhere', () => {
        expect(() => buildSocialShareUrl('x', 'ReviewSupport body only')).not.toThrow();
        expect(() => buildSocialShareUrl('facebook', 'ReviewSupport body only')).not.toThrow();
        expect(() => buildSocialShareUrl('instagram', 'ReviewSupport body only')).not.toThrow();
        expect(() => buildSocialShareUrl('tiktok', 'ReviewSupport body only')).not.toThrow();
        expect(() => buildSocialShareUrl('reddit', 'ReviewSupport body only')).toThrow('A Reddit share title is required.');

        const redditShare = new URL(buildSocialShareUrl('reddit', 'ReviewSupport body only', '  ReviewSupport short title  '));
        expect(redditShare.searchParams.get('title')).toBe('ReviewSupport short title');
    });

    it('URL-encodes test-owned punctuation without leaking or rewriting it', () => {
        const text = 'ReviewSupport ß &?= / #%\nline 2';
        const title = 'ReviewSupport ß &?= / #%';
        const xShare = buildSocialShareUrl('x', text);
        const redditShare = buildSocialShareUrl('reddit', text, title);
        const parsedX = new URL(xShare);
        const parsedReddit = new URL(redditShare);

        expect(xShare).toContain('%C3%9F');
        expect(xShare).toContain('%26');
        expect(xShare).toContain('%23');
        expect(redditShare).toContain('%C3%9F');
        expect(redditShare).toContain('%26');
        expect(redditShare).toContain('%23');
        expect(parsedX.searchParams.get('text')).toBe(text);
        expect(parsedX.searchParams.get('url')).toBe(PUBLIC_PROJECT_URL);
        expect(parsedReddit.searchParams.get('title')).toBe(title);
        expect(parsedReddit.searchParams.get('text')).toBe(buildSocialShareCopy(text));
    });
});

describe('supportLinks — copy payload', () => {
    it('always appends the fixed public project URL to the share message', () => {
        expect(buildSocialShareCopy('ReviewSupport copy')).toBe(`ReviewSupport copy\n${PUBLIC_PROJECT_URL}`);
    });
});
