export const PUBLIC_PROJECT_URL = 'https://librefolio.github.io/LibreFolio/';
export const BUY_ME_A_COFFEE_URL = 'https://www.buymeacoffee.com/librefolio';

export type SocialPlatform = 'x' | 'reddit' | 'facebook' | 'instagram' | 'tiktok';

interface SocialShareConfig {
    label: string;
    intentUrl: string;
    messageKey: string;
    hintKey: string;
    brandClass: string;
    afterCopyKey?: string;
}

export const SOCIAL_SHARE_ORDER: SocialPlatform[] = ['x', 'reddit', 'facebook', 'instagram', 'tiktok'];

export const SOCIAL_SHARE_CONFIG: Record<SocialPlatform, SocialShareConfig> = {
    x: {
        label: 'X',
        intentUrl: 'https://twitter.com/intent/tweet',
        messageKey: 'support.share.x.message',
        hintKey: 'support.share.x.hint',
        brandClass: 'bg-slate-900 text-white hover:bg-slate-800 focus-visible:ring-slate-900/30 dark:bg-slate-700 dark:hover:bg-slate-600',
    },
    reddit: {
        label: 'Reddit',
        intentUrl: 'https://www.reddit.com/submit',
        messageKey: 'support.share.reddit.message',
        hintKey: 'support.share.reddit.hint',
        brandClass: 'bg-[#ff4500] text-white hover:bg-[#e03d00] focus-visible:ring-[#ff4500]/30',
    },
    facebook: {
        label: 'Facebook',
        intentUrl: 'https://www.facebook.com/sharer/sharer.php',
        messageKey: 'support.share.facebook.message',
        hintKey: 'support.share.facebook.hint',
        afterCopyKey: 'support.share.facebook.afterCopy',
        brandClass: 'bg-[#0866ff] text-white hover:bg-[#0758db] focus-visible:ring-[#0866ff]/30',
    },
    instagram: {
        label: 'Instagram',
        intentUrl: 'https://www.instagram.com/',
        messageKey: 'support.share.instagram.message',
        hintKey: 'support.share.instagram.hint',
        afterCopyKey: 'support.share.instagram.afterCopy',
        brandClass: 'bg-gradient-to-tr from-[#c13584] via-[#833ab4] to-[#405de6] text-white hover:brightness-95 focus-visible:ring-[#c13584]/30',
    },
    tiktok: {
        label: 'TikTok',
        intentUrl: 'https://www.tiktok.com/upload',
        messageKey: 'support.share.tiktok.message',
        hintKey: 'support.share.tiktok.hint',
        afterCopyKey: 'support.share.tiktok.afterCopy',
        brandClass: 'bg-black text-white hover:bg-slate-900 focus-visible:ring-[#25f4ee]/50 dark:bg-slate-800 dark:hover:bg-slate-700',
    },
};

export function buildSocialShareUrl(platform: SocialPlatform, text: string, title?: string): string {
    const config = SOCIAL_SHARE_CONFIG[platform];
    const params = new URLSearchParams();
    if (platform === 'instagram' || platform === 'tiktok') return config.intentUrl;
    if (platform === 'reddit') {
        if (!title?.trim()) throw new Error('A Reddit share title is required.');
        params.set('type', 'TEXT');
        params.set('selftext', 'true');
        params.set('title', title.trim());
        params.set('text', buildSocialShareCopy(text));
    } else if (platform === 'facebook') {
        params.set('u', PUBLIC_PROJECT_URL);
    } else {
        params.set('text', text);
        params.set('url', PUBLIC_PROJECT_URL);
    }
    return `${config.intentUrl}?${params.toString()}`;
}

export function buildSocialShareCopy(text: string): string {
    return `${text}\n${PUBLIC_PROJECT_URL}`;
}
