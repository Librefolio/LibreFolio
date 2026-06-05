import {goto} from '$app/navigation';

export function buildDateRangeUrl(currentHref: string, start: string, end: string): URL {
    const url = new URL(currentHref);
    url.searchParams.set('start', start);
    url.searchParams.set('end', end);
    return url;
}

export function replaceHistoryDateRange(start: string, end: string): void {
    if (typeof window === 'undefined' || typeof history === 'undefined') return;
    const url = buildDateRangeUrl(window.location.href, start, end);
    history.replaceState(history.state, '', url.toString());
}

export function gotoDateRange(start: string, end: string): Promise<void> {
    if (typeof window === 'undefined') return Promise.resolve();
    const url = buildDateRangeUrl(window.location.href, start, end);
    return goto(`${url.pathname}${url.search}`, {replaceState: true, noScroll: true, keepFocus: true});
}
