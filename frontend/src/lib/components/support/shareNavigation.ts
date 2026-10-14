export interface ShareTab {
    readonly closed: boolean;
    navigate(url: string): void;
    close(): void;
}

/** Reserve during the click; the external destination is assigned only after copying. */
export function reserveShareTab(): ShareTab | null {
    const tab = window.open('about:blank', '_blank');
    if (!tab) return null;
    try {
        tab.opener = null;
        const referrer = tab.document.createElement('meta');
        referrer.name = 'referrer';
        referrer.content = 'no-referrer';
        tab.document.head.append(referrer);
    } catch (error) {
        tab.close();
        throw error;
    }
    return {
        get closed() {
            return tab.closed;
        },
        navigate: (url) => {
            // Parent-driven location changes can carry the parent's referrer.
            // A child-owned noreferrer link applies the policy to this navigation.
            const link = tab.document.createElement('a');
            link.href = url;
            link.target = '_self';
            link.rel = 'noopener noreferrer';
            link.referrerPolicy = 'no-referrer';
            link.hidden = true;
            tab.document.body.append(link);
            try {
                link.click();
            } finally {
                link.remove();
            }
        },
        close: () => tab.close(),
    };
}
