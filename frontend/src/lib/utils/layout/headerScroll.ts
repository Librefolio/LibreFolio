export function clampDocumentScrollY(scrollY: number, maxScrollY: number): number {
    if (!Number.isFinite(scrollY)) return 0;
    if (!Number.isFinite(maxScrollY) || maxScrollY <= 0) return 0;
    return Math.min(Math.max(scrollY, 0), maxScrollY);
}

export function getDocumentScrollMaxY(): number {
    if (typeof window === 'undefined' || typeof document === 'undefined') return 0;
    const scrollElement = document.scrollingElement ?? document.documentElement;
    const scrollHeight = scrollElement?.scrollHeight ?? document.documentElement.scrollHeight;
    return Math.max(0, scrollHeight - window.innerHeight);
}

export function getDocumentScrollY(): number {
    if (typeof window === 'undefined' || typeof document === 'undefined') return 0;
    const scrollElement = document.scrollingElement ?? document.documentElement;
    return clampDocumentScrollY(window.scrollY ?? scrollElement?.scrollTop ?? 0, getDocumentScrollMaxY());
}
