import {describe, expect, it} from 'vitest';
import en from '$lib/i18n/en.json';
import itCatalog from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import {BUY_ME_A_COFFEE_URL, PUBLIC_PROJECT_URL, SHARE_HASHTAGS, SOCIAL_SHARE_CONFIG, SOCIAL_SHARE_ORDER, buildSocialShareCopy, buildSocialShareUrl, withShareHashtags, type SocialPlatform} from './supportLinks';

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

// The developer's decision (06/10): one hashtag set, identical in every language and on all five
// socials, #LibreFolio first. Written out here on purpose: the product constant is checked against
// the decision, never the other way round.
const APPROVED_HASHTAGS = ['#LibreFolio', '#OpenSource', '#SelfHosted', '#PortfolioTracker', '#PersonalFinance'];
const APPROVED_HASHTAG_LINE = '#LibreFolio #OpenSource #SelfHosted #PortfolioTracker #PersonalFinance';

const CATALOGUES = {en, it: itCatalog, fr, es} as const;
type CatalogueLocale = keyof typeof CATALOGUES;
const CATALOGUE_LOCALES = Object.keys(CATALOGUES) as CatalogueLocale[];

// Positive control for the catalogue gate: a scan that finds nothing also finds no hashtag.
const SHARED_TEXT_KEYS = [...SOCIAL_SHARE_ORDER.map((platform) => SOCIAL_SHARE_CONFIG[platform].messageKey), 'support.share.reddit.title'];

// X counts any link as a 23-character t.co link, joined to the text by one separator.
const X_MAX_POST_LENGTH = 280;
const X_LINK_LENGTH = 23;
const X_LINK_SEPARATOR_LENGTH = 1;

function catalogueText(lang: CatalogueLocale, key: string): string {
    const value = key.split('.').reduce<unknown>((node, part) => (node && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), CATALOGUES[lang]);
    if (typeof value !== 'string') throw new Error(`Missing translation for ${lang}:${key}`);
    return value;
}

/** Every text a catalogue puts in front of a social audience: each `support.share.<platform>.message` and `.title`. */
function sharedCatalogueTexts(lang: CatalogueLocale): Array<{key: string; value: string}> {
    const texts: Array<{key: string; value: string}> = [];
    for (const [platform, node] of Object.entries(CATALOGUES[lang].support.share as Record<string, unknown>)) {
        if (!node || typeof node !== 'object') continue;
        for (const field of ['message', 'title'] as const) {
            const value = (node as Record<string, unknown>)[field];
            if (typeof value === 'string') texts.push({key: `support.share.${platform}.${field}`, value});
        }
    }
    return texts;
}

/** twitter-text v3 weighting: these code points count 1 on X, every other one counts 2 (CJK, emoji…). */
function countsOnceOnX(char: string): boolean {
    const codePoint = char.codePointAt(0) ?? 0;
    return codePoint <= 0x10ff || (codePoint >= 0x2000 && codePoint <= 0x200d) || (codePoint >= 0x2010 && codePoint <= 0x201f) || (codePoint >= 0x2032 && codePoint <= 0x2037);
}

describe('supportLinks — one hashtag set on every share', () => {
    it('SHARE_HASHTAGS is exactly the approved set, in the approved order', () => {
        expect(SHARE_HASHTAGS).toEqual(APPROVED_HASHTAGS);
    });

    it('SHARE_HASHTAGS starts with #LibreFolio, holds only valid hashtags (# + ASCII letters/digits, no spaces, no accents) and no duplicates', () => {
        expect(SHARE_HASHTAGS[0]).toBe('#LibreFolio');
        for (const tag of SHARE_HASHTAGS) {
            // At least one letter: a digits-only tag is not linked as a hashtag.
            expect(tag, `${tag} is not a hashtag every platform links`).toMatch(/^#[A-Za-z0-9]*[A-Za-z][A-Za-z0-9]*$/);
        }
        const folded = SHARE_HASHTAGS.map((tag) => tag.toLowerCase());
        expect(new Set(folded).size, 'duplicate tags (hashtags ignore case)').toBe(folded.length);
    });

    it('withShareHashtags appends one blank line, then the whole set joined by single spaces', () => {
        expect(withShareHashtags('ReviewSupport says hello')).toBe(`ReviewSupport says hello\n\n${APPROVED_HASHTAG_LINE}`);
    });

    it.each([' ', '\n', '\n\n', ' \t\n \n'])('withShareHashtags trims the trailing whitespace %j first, so exactly one blank line precedes the hashtags', (tail) => {
        expect(withShareHashtags(`ReviewSupport says hello${tail}`)).toBe(`ReviewSupport says hello\n\n${APPROVED_HASHTAG_LINE}`);
    });

    it('withShareHashtags leaves the rest of the message verbatim: leading spaces, inner newlines and blank lines, accents', () => {
        const message = '  ReviewSupport è già qui — ¡sí!\n\nSecond  paragraph\nthird line';
        expect(withShareHashtags(message)).toBe(`${message}\n\n${APPROVED_HASHTAG_LINE}`);
    });

    it('the copied text is the message, a blank line, the hashtag line, then the public link on its own line', () => {
        expect(buildSocialShareCopy(withShareHashtags('ReviewSupport says hello'))).toBe(`ReviewSupport says hello\n\n${APPROVED_HASHTAG_LINE}\n${PUBLIC_PROJECT_URL}`);
    });

    it.each(SOCIAL_SHARE_ORDER)('%s: the share URL built from withShareHashtags carries the hashtags exactly where the platform prefills text', (platform) => {
        const message = 'ReviewSupport says hello';
        const title = 'ReviewSupport short title';
        // Every query parameter, per platform: the hashtags may appear nowhere else.
        const expectedParams: Record<SocialPlatform, Record<string, string>> = {
            x: {text: `${message}\n\n${APPROVED_HASHTAG_LINE}`, url: PUBLIC_PROJECT_URL},
            reddit: {type: 'TEXT', selftext: 'true', title, text: `${message}\n\n${APPROVED_HASHTAG_LINE}\n${PUBLIC_PROJECT_URL}`},
            facebook: {u: PUBLIC_PROJECT_URL},
            instagram: {},
            tiktok: {},
        };
        const share = new URL(buildSocialShareUrl(platform, withShareHashtags(message), title));

        expect(`${share.origin}${share.pathname}`).toBe(SOCIAL_SHARE_CONFIG[platform].intentUrl);
        expect(Object.fromEntries(share.searchParams)).toEqual(expectedParams[platform]);
        expect(share.searchParams.get('title') ?? '', 'a share title never carries hashtags').not.toContain('#');
    });

    it.each(CATALOGUE_LOCALES)('catalogue gate, %s: no support.share.*.message and no support.share.reddit.title contains a # — hashtags come from SHARE_HASHTAGS only', (lang) => {
        const texts = sharedCatalogueTexts(lang);
        expect(
            texts.map(({key}) => key),
            `${lang}: the gate no longer reads every shared text`,
        ).toEqual(expect.arrayContaining(SHARED_TEXT_KEYS));

        const offenders = texts.filter(({value}) => value.includes('#')).map(({key, value}) => `${lang} ${key}: ${(value.match(/#\S*/g) ?? []).join(' ')}`);
        expect(offenders, `${lang}: hashtags belong to SHARE_HASHTAGS in supportLinks.ts, never to a catalogue`).toEqual([]);
    });

    it.each(CATALOGUE_LOCALES)('%s: withShareHashtags(x.message) fits the 280-character X post, counted in code points (Latin script counts 1 each on X) plus one separator and a 23-character t.co link', (lang) => {
        const post = new URL(buildSocialShareUrl('x', withShareHashtags(catalogueText(lang, SOCIAL_SHARE_CONFIG.x.messageKey))));
        const codePoints = [...(post.searchParams.get('text') ?? '')];

        expect(post.searchParams.get('url'), 'the link X counts as 23 characters').toBe(PUBLIC_PROJECT_URL);
        // The assumption behind counting code points, verified rather than trusted.
        expect(
            codePoints.filter((char) => !countsOnceOnX(char)),
            `${lang}: characters X counts twice, so the code-point count would be short`,
        ).toEqual([]);
        expect(codePoints.length + X_LINK_SEPARATOR_LENGTH + X_LINK_LENGTH, `${lang}: X post length`).toBeLessThanOrEqual(X_MAX_POST_LENGTH);
    });
});
